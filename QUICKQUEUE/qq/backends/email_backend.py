import ssl

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend
from django.utils.functional import cached_property


class EmailBackend(SMTPEmailBackend):
    """
    SMTP backend that can relax SSL verification for local development
    when a network proxy or antivirus intercepts TLS traffic.
    """

    @cached_property
    def ssl_context(self):
        if getattr(settings, "EMAIL_SSL_INSECURE", False):
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context

        if self.ssl_certfile or self.ssl_keyfile:
            context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
            context.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)
            return context

        return ssl.create_default_context()
