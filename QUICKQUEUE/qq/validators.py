from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class MinimumLengthOnlyValidator:
    """Require only a minimum password length, without character-type rules."""

    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("Password must be at least 8 characters."),
                code="password_too_short",
            )

    def get_help_text(self):
        return _("Password must be at least 8 characters.")
