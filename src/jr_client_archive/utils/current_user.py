"""Resolve the identity recorded against every audit/history entry.

There is no login system yet, so 'who did this' is the OS account name.
Kept behind one function so a future authentication phase only needs to
change this one place.
"""

from __future__ import annotations

import getpass


def get_current_username() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return "utente"
