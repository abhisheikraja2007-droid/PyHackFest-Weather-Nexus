"""
Django settings for weather_nexus project.
Uses pymongo directly (no djongo ORM - raw MongoDB queries for best performance).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-weather-nexus-hackathon-2024"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "weather_nexus.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "analytics" / "templates"],
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "weather_nexus.wsgi.application"

# ─── Database (not using Django ORM — raw pymongo) ────────────────────────
DATABASES = {}  # empty; all DB ops go through pymongo

# ─── Static files ──────────────────────────────────────────────────────────
STATIC_URL = "/static/"
_STATIC_DIR = BASE_DIR / "analytics" / "static"
STATICFILES_DIRS = [_STATIC_DIR] if _STATIC_DIR.exists() else []

# ─── MongoDB Connection Settings ───────────────────────────────────────────
MONGO_URI  = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB   = os.environ.get("MONGO_DB",  "weather_nexus")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
