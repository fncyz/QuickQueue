from rest_framework import serializers

from qq.models import DocumentTemplate, Resident


class DocumentTemplateSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentTemplate
        fields = ("id", "service", "service_name", "name", "template_file", "file_url", "version", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "version", "created_at", "updated_at")
        extra_kwargs = {"template_file": {"write_only": True}}

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.template_file:
            return None
        url = obj.template_file.url
        return request.build_absolute_uri(url) if request else url

    def validate_template_file(self, value):
        allowed = {".pdf", ".doc", ".docx", ".odt", ".html", ".txt"}
        name = value.name.lower()
        if not any(name.endswith(ext) for ext in allowed):
            raise serializers.ValidationError("Upload a PDF, DOC, DOCX, ODT, HTML, or TXT template.")
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Template files must not exceed 10MB.")
        return value


class ResidentSerializer(serializers.ModelSerializer):
    barangay = serializers.CharField(source="barangay.name")
    username = serializers.CharField(source="user.username", read_only=True)
    sex_display = serializers.CharField(source="get_sex_display", read_only=True)

    class Meta:
        model = Resident
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "middle_name",
            "suffix",
            "birthdate",
            "sex",
            "sex_display",
            "email",
            "contact_number",
            "province",
            "municipality",
            "barangay",
            "age",
            "created_at",
        ]


from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from qq.models import (
    Barangay,
    Resident,
)



class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)

    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)

    middle_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    suffix = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )

    birthdate = serializers.DateField()

    sex = serializers.ChoiceField(
        choices=Resident.Sex.choices,
    )

    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    contact_number = serializers.CharField(
        max_length=15,
    )

    barangay = serializers.PrimaryKeyRelatedField(
        queryset=Barangay.objects.all(),
    )

    terms_accepted = serializers.BooleanField()

    def validate(self, attrs):
        if not attrs["terms_accepted"]:
            raise serializers.ValidationError(
                {
                    "terms_accepted": "You must accept the Terms and Conditions."
                }
            )

        return attrs

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Username already exists."
            )
        return value

    def validate_email(self, value):
        if not value:
            return None
        if Resident.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email address is already registered.")
        return value

    def validate_contact_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Contact number must contain digits only.")
        if Resident.objects.filter(contact_number=value).exists():
            raise serializers.ValidationError("Contact number is already registered.")
        return value

    def create(self, validated_data):
        validated_data.pop("terms_accepted")

        with transaction.atomic():
            user = User(username=validated_data.pop("username"))
            user.set_unusable_password()
            user.save()

            resident = Resident.objects.create(
                user=user,
                terms_accepted_at=timezone.now(),
                **validated_data,
            )

        return resident

    from qq.models import Barangay

class BarangaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Barangay
        fields = [
            "id",
            "name",
        ]
