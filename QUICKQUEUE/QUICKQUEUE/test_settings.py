from .settings import *  # noqa: F403


# Tests must never connect to the configured production PostgreSQL service.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    }
}

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["chat"] = "1000/min"  # noqa: F405
