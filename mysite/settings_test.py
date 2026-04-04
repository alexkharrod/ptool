"""
Test settings — uses local SQLite so tests never touch the Railway database.

Usage:
    python manage.py test --settings=mysite.settings_test
"""

from .settings import *  # noqa: F401, F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",  # noqa: F405
    }
}

# Speed up password hashing in tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Suppress logging noise during tests
LOGGING = {}

# Cloudinary — skip real uploads during tests
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Bypass WhiteNoise manifest storage — no collectstatic needed in tests
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
