"""
analytics/db.py — Singleton pymongo client shared across all views.
"""
import pymongo
from django.conf import settings

_client = None
_db     = None


def get_db():
    global _client, _db
    if _db is None:
        _client = pymongo.MongoClient(settings.MONGO_URI)
        _db     = _client[settings.MONGO_DB]
    return _db
