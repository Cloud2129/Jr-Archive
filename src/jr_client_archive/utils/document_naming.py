"""Renders the configurable auto-rename pattern (``AppSettings.document_naming_pattern``)
into an actual, filesystem-safe file stem.

Unknown placeholders and missing values both resolve to an empty string
rather than raising, so a user-edited pattern referencing a field that
happens to be blank on a given document degrades gracefully instead of
blocking the rename.
"""

from __future__ import annotations

import re
from datetime import date

from jr_client_archive.domain.client import ClientRead
from jr_client_archive.utils.text import normalize_token

_MULTI_UNDERSCORE = re.compile(r"_+")


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return ""


def render_document_stem(
    pattern: str,
    *,
    client: ClientRead,
    document_type: str | None,
    category: str | None,
    document_date: date | None,
) -> str:
    fields = _SafeDict(
        client_code=client.client_code,
        first_name=client.first_name or "",
        last_name=client.last_name or "",
        company_name=client.company_name or "",
        fiscal_code=client.fiscal_code or "",
        vat_number=client.vat_number or "",
        practice_number=client.practice_number or "",
        document_type=document_type or "",
        category=category or "",
        document_date=document_date.isoformat() if document_date else "",
    )
    rendered = pattern.format_map(fields)
    sanitized = normalize_token(rendered)
    collapsed = _MULTI_UNDERSCORE.sub("_", sanitized).strip("_")
    return collapsed or client.client_code
