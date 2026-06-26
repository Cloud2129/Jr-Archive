"""Import every ORM model so ``Base.metadata`` is fully populated.

Anything that calls ``Database.create_all()`` or runs an Alembic
autogenerate must go through this package first.
"""

from jr_client_archive.db.models.audit import AuditLogEntry
from jr_client_archive.db.models.client import Client
from jr_client_archive.db.models.custom_field import CustomFieldDefinition, CustomFieldValue
from jr_client_archive.db.models.document import Document, DocumentHistoryEntry, Tag
from jr_client_archive.db.models.folder import Folder
from jr_client_archive.db.models.license import LicenseStateRow
from jr_client_archive.db.models.setting import AppSettingRow

__all__ = [
    "AuditLogEntry",
    "Client",
    "CustomFieldDefinition",
    "CustomFieldValue",
    "Document",
    "DocumentHistoryEntry",
    "Tag",
    "Folder",
    "LicenseStateRow",
    "AppSettingRow",
]
