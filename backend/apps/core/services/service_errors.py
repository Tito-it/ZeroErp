from typing import Any

# Modello errore applicativo unico riusabile da tutti i servizi Django.


class ServiceError(Exception):
    """Errore applicativo standard con metadati utili per API/UI."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        detail: str | None = None,
        hint: str | None = None,
        tx_id: str | None = None,
        retryable: bool = False,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail or message)
        self.code = code
        self.message = message
        self.detail = detail
        self.hint = hint
        self.tx_id = tx_id
        self.retryable = retryable
        self.context = context or {}
