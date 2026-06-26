"""Application layer: orchestrates services into user-facing use cases.

This is where, starting in Phase 2, code like "create a client, then create
its folder, then log the audit entry" will live - coordination that is
more than one service's job but is still not UI. The UI layer calls into
``application``, never directly into ``services`` or ``repositories``.
"""
