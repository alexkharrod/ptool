"""
Django settings for mysite project.
"""

import os
from pathlib import Path

import dj_database_url
from load_dotenv import load_dotenv

load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Security ────────────────────────────────────────────────────────────────

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "SECRET_KEY environment variable is not set. "
        "Please add it to your .env file before starting the server."
    )

DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Trust Railway's proxy headers so HTTPS works correctly
CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS if host not in ("localhost", "127.0.0.1")
]

# ─── Redirect URLs ───────────────────────────────────────────────────────────

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = "/login/"

# ─── Application definition ──────────────────────────────────────────────────

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "products",
    "users",
    "quotes",
    "scouting",
    "widget_tweaks",
    "axes",
]

# Add Cloudinary if configured
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL")

# Anthropic API — used for business card scanning in scouting
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
if CLOUDINARY_URL:
    INSTALLED_APPS += ["cloudinary", "cloudinary_storage"]
    DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# ─── Middleware ───────────────────────────────────────────────────────────────

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # Serve static files efficiently
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "mysite.middleware.PtoolAccessMiddleware",
]

ROOT_URLCONF = "mysite.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mysite.wsgi.application"

# ─── Database ────────────────────────────────────────────────────────────────
# Uses DATABASE_URL env var on Railway (PostgreSQL).
# Falls back to local SQLite when DATABASE_URL is not set.

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'instance/db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_USER_MODEL = "users.CustomUser"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ─── Password validation ─────────────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── Axes (brute-force protection) ───────────────────────────────────────────
# Lock account after 5 failed login attempts; auto-unlock after 1 hour.

AXES_FAILURE_LIMIT        = 5          # failed attempts before lockout
AXES_COOLOFF_TIME         = 1          # hours until auto-unlock
AXES_RESET_ON_SUCCESS     = True       # reset counter on successful login
AXES_LOCKOUT_TEMPLATE     = "lockout.html"
AXES_LOCKOUT_PARAMETERS   = [["username", "ip_address"]]  # lock by username+IP pair — prevents Railway proxy from locking all users on one bad attempt

# ─── Internationalisation ────────────────────────────────────────────────────

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ─── Static files ────────────────────────────────────────────────────────────
# WhiteNoise serves static files directly from Django — no separate web server needed.

STATIC_URL = "static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ─── Media files ─────────────────────────────────────────────────────────────
# Cloudinary is used in production (when CLOUDINARY_URL is set).
# Local filesystem is used in development.

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ─── Upload limits ───────────────────────────────────────────────────────────
# Business card scans are sent as base64 JSON, using Django's in-memory parser.
# Raise the limit to 10 MB to handle resized images comfortably.

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# ─── Misc ────────────────────────────────────────────────────────────────────

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
