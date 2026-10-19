from html import escape
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import content_disposition_header
from django.utils import timezone

from qq.models import Barangay, BarangayStaff, DocumentTemplate, Notification, Service


def _admin_barangay(user):
    try:
        return user.barangay_profile
    except Barangay.DoesNotExist:
        pass
    try:
        staff = user.staff_profile
    except BarangayStaff.DoesNotExist as error:
        raise Http404("This account is not assigned to a barangay.") from error
    if staff.role != BarangayStaff.Role.ADMIN:
        return None
    return staff.barangay


def _template_for_admin(user, pk):
    barangay = _admin_barangay(user)
    if barangay is None:
        raise Http404("This document template is available to barangay administrators only.")
    return get_object_or_404(
        DocumentTemplate.objects.select_related("service"), pk=pk, barangay=barangay
    )


def _preview_page(filename, body, *, notice=""):
    notice_html = f'<p class="notice">{escape(notice)}</p>' if notice else ""
    response = HttpResponse(
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<style>body{margin:0;padding:38px;background:#e9edf3;color:#172b4d;font:14px/1.7 Arial,sans-serif}"
        ".page{width:min(816px,calc(100% - 30px));min-height:960px;margin:auto;padding:64px 72px;background:#fff;"
        "box-shadow:0 3px 18px #1b335329;box-sizing:border-box}.notice{margin:0 0 28px;padding:12px 15px;"
        "border-radius:8px;background:#eef5ff;color:#1558ad;font-weight:600}p{margin:0 0 14px;white-space:pre-wrap}"
        "h1{margin:0 0 24px;font-size:20px}@media(max-width:650px){body{padding:15px}.page{width:100%;"
        "min-height:calc(100vh - 30px);padding:30px 24px}}</style></head><body><main class=\"page\">"
        f"<h1>{escape(filename)}</h1>{notice_html}{body}</main></body></html>",
        content_type="text/html; charset=utf-8",
    )
    response["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'"
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _xml_paragraphs(archive, member):
    root = ElementTree.fromstring(archive.read(member))
    paragraphs = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] not in {"p", "h"}:
            continue
        text = "".join(element.itertext()).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


@login_required(login_url="signin")
def barangay_document_templates(request):
    barangay = _admin_barangay(request.user)
    if barangay is None:
        return redirect("staff_document_processing")
    return render(request, "barangay_admin/document_templates.html", {
        "active_page": "templates", "barangay": barangay, "today": timezone.localdate(),
        "services": Service.objects.filter(is_active=True).order_by("name"),
        "unread_notifications": Notification.objects.filter(appointment__barangay=barangay, admin_is_read=False).count(),
    })


@login_required(login_url="signin")
def barangay_document_template_preview(request, pk):
    template = _template_for_admin(request.user, pk)
    filename = Path(template.template_file.name).name
    extension = Path(filename).suffix.lower()

    if extension == ".pdf":
        response = FileResponse(
            template.template_file.open("rb"), content_type="application/pdf"
        )
        response["Content-Disposition"] = content_disposition_header(False, filename)
        response["X-Content-Type-Options"] = "nosniff"
        return response

    if extension in {".docx", ".odt"}:
        try:
            with template.template_file.open("rb") as stored_file:
                payload = stored_file.read()
            with ZipFile(BytesIO(payload)) as archive:
                member = "word/document.xml" if extension == ".docx" else "content.xml"
                paragraphs = _xml_paragraphs(archive, member)
            body = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
            if not body:
                body = "<p>No previewable text was found in this document.</p>"
            return _preview_page(
                filename,
                body,
                notice="Simplified browser preview. Download the original for exact formatting.",
            )
        except (BadZipFile, KeyError, ElementTree.ParseError, OSError):
            return _preview_page(
                filename,
                "<p>This document could not be rendered safely in the browser.</p>",
                notice="Preview unavailable. Use Download Template to open the original file.",
            )

    if extension == ".txt":
        try:
            with template.template_file.open("rb") as stored_file:
                text = stored_file.read().decode("utf-8", errors="replace")
            return _preview_page(filename, f"<p>{escape(text)}</p>")
        except OSError:
            pass

    return _preview_page(
        filename,
        "<p>An accurate browser preview is not available for this file format.</p>",
        notice="Preview unavailable. Use Download Template to open the original file.",
    )


@login_required(login_url="signin")
def barangay_document_template_download(request, pk):
    template = _template_for_admin(request.user, pk)
    filename = Path(template.template_file.name).name
    return FileResponse(
        template.template_file.open("rb"),
        as_attachment=True,
        filename=filename,
        content_type="application/octet-stream",
    )
