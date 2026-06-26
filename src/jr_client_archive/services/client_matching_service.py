"""Heuristic engine behind the drag&drop client-recognition flow.

When a file is dropped without a target client (e.g. onto the main window
rather than a specific dossier), this ranks the active clients by how
likely the filename is to belong to them. Two kinds of signal are combined,
and the *highest* one wins per client - rather than summing them - because a
single exact identifier match (codice fiscale, partita IVA, codice cliente,
numero pratica) is already as confident as matching gets and shouldn't be
diluted by a mediocre fuzzy name score from the same client.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from jr_client_archive.domain.client import ClientRead
from jr_client_archive.domain.client_match import ClientMatchRead
from jr_client_archive.domain.enums import ClientType
from jr_client_archive.utils.text import normalize_token

_EXACT_SCORE = 100.0
_MIN_SCORE = 55.0
_MAX_RESULTS = 5


def match_clients(filename: str, clients: list[ClientRead]) -> list[ClientMatchRead]:
    normalized_filename = normalize_token(filename)

    candidates = []
    for client in clients:
        score, reason = _best_signal(normalized_filename, client)
        if score >= _MIN_SCORE:
            candidates.append(ClientMatchRead(client=client, score=score, reason=reason))

    candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    return candidates[:_MAX_RESULTS]


def _best_signal(normalized_filename: str, client: ClientRead) -> tuple[float, str]:
    exact_signals = (
        (client.client_code, "Codice cliente"),
        (client.fiscal_code, "Codice fiscale"),
        (client.vat_number, "Partita IVA"),
        (client.practice_number, "Numero pratica"),
    )
    for value, reason in exact_signals:
        if value and normalize_token(value) in normalized_filename:
            return _EXACT_SCORE, reason

    name = _comparable_name(client)
    if not name:
        return 0.0, ""
    fuzzy_score = fuzz.token_set_ratio(
        normalized_filename.replace("_", " "), normalize_token(name).replace("_", " ")
    )
    return fuzzy_score, "Corrispondenza nome"


def _comparable_name(client: ClientRead) -> str:
    if client.client_type == ClientType.COMPANY:
        return client.company_name or ""
    return f"{client.last_name or ''} {client.first_name or ''}".strip()
