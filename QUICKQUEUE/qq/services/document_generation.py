import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from qq.models import DocumentTemplate, GeneratedDocument


WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-z][a-z0-9_]*)\s*}}")


@dataclass(frozen=True)
class DocumentGenerationResult:
    content: bytes
    filename: str
    replaced_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    unknown_fields: tuple[str, ...]


def template_values(ticket):
    appointment = ticket.appointment
    resident = appointment.resident
    barangay = appointment.barangay
    full_name = " ".join(filter(None, [
        resident.first_name,
        resident.middle_name,
        resident.last_name,
        resident.suffix,
    ]))
    address = ", ".join(filter(None, [
        appointment.sitio,
        barangay.name,
        resident.municipality,
        resident.province,
    ]))
    today = timezone.localdate()
    return {
        "resident_full_name": full_name,
        "resident_first_name": resident.first_name,
        "resident_middle_name": resident.middle_name,
        "resident_last_name": resident.last_name,
        "resident_suffix": resident.suffix,
        "resident_address": address,
        "barangay_name": barangay.name,
        "sitio_purok": appointment.sitio,
        "contact_number": resident.contact_number,
        "birthdate": resident.birthdate.strftime("%B %d, %Y") if resident.birthdate else "",
        "resident_age": str(resident.age) if resident.birthdate else "",
        "appointment_id": f"QQ-{appointment.created_at.year}-{appointment.pk:05d}",
        "queue_number": ticket.queue_number,
        "service_name": appointment.service.name,
        "appointment_date": appointment.appointment_date.strftime("%B %d, %Y") if appointment.appointment_date else "",
        "processing_date": today.strftime("%B %d, %Y"),
        "date_issued": today.strftime("%B %d, %Y"),
        "document_reference_number": f"DOC-{appointment.created_at.year}-{ticket.pk:06d}",
        "municipality_city": resident.municipality,
        "purpose": appointment.purpose,
    }


def _replace_paragraph_placeholders(paragraph, values):
    text_nodes = paragraph.findall(f".//{{{WORD_NAMESPACE}}}t")
    node_text = [node.text or "" for node in text_nodes]
    combined = "".join(node_text)
    matches = list(PLACEHOLDER_PATTERN.finditer(combined))
    if not matches:
        return set(), set(), set()

    offsets = []
    cursor = 0
    for index, value in enumerate(node_text):
        offsets.extend([index] * len(value))
        cursor += len(value)

    output = ["" for _ in text_nodes]
    replaced = set()
    missing = set()
    unknown = set()
    position = 0

    def copy_original(start, end):
        for char_index in range(start, end):
            output[offsets[char_index]] += combined[char_index]

    for match in matches:
        copy_original(position, match.start())
        field = match.group(1)
        if field not in values:
            unknown.add(field)
            copy_original(match.start(), match.end())
        elif values[field] in (None, ""):
            missing.add(field)
            copy_original(match.start(), match.end())
        else:
            output[offsets[match.start()]] += str(values[field])
            replaced.add(field)
        position = match.end()
    copy_original(position, len(combined))

    for node, value in zip(text_nodes, output):
        node.text = value
        if value.startswith(" ") or value.endswith(" "):
            node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return replaced, missing, unknown


def populate_docx(template, ticket):
    if Path(template.template_file.name).suffix.lower() != ".docx":
        raise ValueError("Automatic generation currently supports DOCX templates only.")
    with template.template_file.open("rb") as source:
        source_bytes = source.read()

    values = template_values(ticket)
    replaced = set()
    missing = set()
    unknown = set()
    output_stream = io.BytesIO()
    try:
        with zipfile.ZipFile(io.BytesIO(source_bytes), "r") as source_zip:
            if sum(item.file_size for item in source_zip.infolist()) > 50 * 1024 * 1024:
                raise ValueError("The DOCX template expands beyond the safe processing limit.")
            with zipfile.ZipFile(output_stream, "w", zipfile.ZIP_DEFLATED) as output_zip:
                for item in source_zip.infolist():
                    data = source_zip.read(item.filename)
                    if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                        root = ElementTree.fromstring(data)
                        for paragraph in root.findall(f".//{{{WORD_NAMESPACE}}}p"):
                            found, absent, unsupported = _replace_paragraph_placeholders(
                                paragraph, values
                            )
                            replaced.update(found)
                            missing.update(absent)
                            unknown.update(unsupported)
                        data = ElementTree.tostring(
                            root, encoding="utf-8", xml_declaration=True
                        )
                    output_zip.writestr(item, data)
    except (zipfile.BadZipFile, ElementTree.ParseError) as error:
        raise ValueError("The uploaded DOCX template is invalid or damaged.") from error

    if not replaced and not missing and not unknown:
        raise ValueError(
            "This DOCX template has no recognized {{ field_name }} placeholders. "
            "The original template was not modified."
        )

    filename = f"DOC-{ticket.appointment.created_at.year}-{ticket.pk:06d}.docx"
    return DocumentGenerationResult(
        content=output_stream.getvalue(),
        filename=filename,
        replaced_fields=tuple(sorted(replaced)),
        missing_fields=tuple(sorted(missing)),
        unknown_fields=tuple(sorted(unknown)),
    )


def generate_document(ticket, user):
    template = DocumentTemplate.objects.filter(
        barangay=ticket.appointment.barangay,
        service=ticket.appointment.service,
        is_active=True,
    ).first()
    if not template:
        raise ValueError("No active document template is configured for this service.")
    result = populate_docx(template, ticket)
    old_storage = None
    old_name = ""
    new_storage = None
    new_name = ""
    try:
        with transaction.atomic():
            generated, _ = GeneratedDocument.objects.select_for_update().get_or_create(
                ticket=ticket,
                defaults={"template": template, "generated_by": user},
            )
            if generated.document_file:
                old_storage = generated.document_file.storage
                old_name = generated.document_file.name
            generated.template = template
            generated.generated_by = user
            generated.status = GeneratedDocument.Status.GENERATED
            generated.document_file.save(
                result.filename, ContentFile(result.content), save=False
            )
            new_storage = generated.document_file.storage
            new_name = generated.document_file.name
            generated.save()
    except Exception as error:
        if new_storage and new_name and new_name != old_name:
            try:
                new_storage.delete(new_name)
            except Exception:
                pass
        raise ValueError(
            "The generated document could not be saved to persistent storage."
        ) from error
    if old_storage and old_name and old_name != generated.document_file.name:
        try:
            old_storage.delete(old_name)
        except Exception:
            pass
    return generated, result
