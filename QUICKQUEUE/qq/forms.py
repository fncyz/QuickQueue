from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from qq.models import Barangay, BarangayStaff


class BarangayForm(forms.ModelForm):
    """Shared validated form for barangay editing."""

    class Meta:
        model = Barangay
        fields = "__all__"
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].strip().split())
        duplicate = Barangay.objects.filter(name__iexact=name)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("A barangay with this name already exists.")
        return name

    def clean_address(self):
        return self.cleaned_data["address"].strip()

    def clean_contact_number(self):
        return self.cleaned_data["contact_number"].strip()

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip()


class SuperAdminBarangayForm(BarangayForm):
    """Portal form that deliberately leaves administrator assignment to Phase 5."""

    class Meta(BarangayForm.Meta):
        fields = ("name", "address", "contact_number", "email", "is_active")


class BarangayAdminCreateForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    barangay = forms.ModelChoiceField(queryset=Barangay.objects.none())
    password1 = forms.CharField(label="Temporary Password", help_text="Password must be at least 8 characters. The administrator must replace it at first login.", widget=forms.PasswordInput(attrs={"minlength": 8}))
    password2 = forms.CharField(label="Confirm Temporary Password", widget=forms.PasswordInput(attrs={"minlength": 8}))
    is_active = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assigned_ids = set(Barangay.objects.exclude(user_id=None).values_list("id", flat=True))
        assigned_ids.update(BarangayStaff.objects.filter(role=BarangayStaff.Role.ADMIN).values_list("barangay_id", flat=True))
        self.fields["barangay"].queryset = Barangay.objects.exclude(pk__in=assigned_ids).order_by("name")

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 != password2:
            self.add_error("password2", "The two password fields do not match.")
        elif password1:
            candidate = User(
                username=cleaned.get("username", ""),
                first_name=cleaned.get("first_name", ""),
                last_name=cleaned.get("last_name", ""),
                email=cleaned.get("email", ""),
            )
            try:
                validate_password(password1, candidate)
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned


class BarangayAdminEditForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    barangay = forms.ModelChoiceField(queryset=Barangay.objects.none())
    is_active = forms.BooleanField(required=False)

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        current_barangay = getattr(user, "barangay_profile", None)
        if current_barangay is None and hasattr(user, "staff_profile"):
            current_barangay = user.staff_profile.barangay
        assigned_ids = set(Barangay.objects.exclude(user_id=None).exclude(user=user).values_list("id", flat=True))
        assigned_ids.update(
            BarangayStaff.objects.filter(role=BarangayStaff.Role.ADMIN)
            .exclude(user=user).values_list("barangay_id", flat=True)
        )
        self.fields["barangay"].queryset = Barangay.objects.exclude(pk__in=assigned_ids).order_by("name")
        if not self.is_bound:
            self.initial.update({
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "barangay": current_barangay,
                "is_active": user.is_active,
            })

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email


class SuperAdminProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A user with this email address already exists.")
        return email


class AdministrativePasswordResetForm(forms.Form):
    superuser_password = forms.CharField(label="Your System Administrator Password", widget=forms.PasswordInput)
    temporary_password1 = forms.CharField(label="Temporary Password", help_text="Password must be at least 8 characters.", widget=forms.PasswordInput(attrs={"minlength": 8}))
    temporary_password2 = forms.CharField(label="Confirm Temporary Password", widget=forms.PasswordInput(attrs={"minlength": 8}))

    def __init__(self, *args, superuser, target_user, **kwargs):
        self.superuser = superuser
        self.target_user = target_user
        super().__init__(*args, **kwargs)

    def clean_superuser_password(self):
        password = self.cleaned_data["superuser_password"]
        if not self.superuser.check_password(password):
            raise forms.ValidationError("Your System Administrator password is incorrect.")
        return password

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("temporary_password1")
        if password1 != cleaned.get("temporary_password2"):
            self.add_error("temporary_password2", "The temporary passwords do not match.")
        elif password1:
            try:
                validate_password(password1, self.target_user)
            except ValidationError as error:
                self.add_error("temporary_password1", error)
        return cleaned
