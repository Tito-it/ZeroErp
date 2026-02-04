from __future__ import annotations

from contextvars import ContextVar

# Contesto richiesta API (request_id/idempotency_key) accessibile nei layer core.

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_idempotency_key_var: ContextVar[str | None] = ContextVar("idempotency_key", default=None)


def set_request_context(*, request_id: str | None, idempotency_key: str | None) -> None:
    _request_id_var.set(request_id)
    _idempotency_key_var.set(idempotency_key)


def clear_request_context() -> None:
    set_request_context(request_id=None, idempotency_key=None)


def get_request_id() -> str | None:
    return _request_id_var.get()


def get_idempotency_key() -> str | None:
    return _idempotency_key_var.get()
