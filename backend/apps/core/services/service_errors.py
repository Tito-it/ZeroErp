# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Definizioni errori di servizio core.
# ------------------------------------------------------------


from typing import Any

from apps.core.services.db_error_fields import Bersaglio

# Modello errore applicativo unico riusabile da tutti i servizi Django.

# Scopo: ⭐ Il codice del dato in ingresso non valido (tipo, forma, chiave
#        fuori contratto), in un posto solo. E' anche quello in cui
#        `ErrorTranslator` traduce un `ValueError`/`TypeError` arrivato nudo.
# ⛔ Non ridefinirlo nei moduli, e non scriverlo come stringa: fino al
#    2026-09-27 stava in due costanti locali e in una dozzina di letterali.
E_VALIDATION_INPUT = "E_VALIDATION_INPUT"

# Scopo: la configurazione dell'installazione che manca (ambiente non
#        dichiarato, wrapper dei comandi assente sull'host, parametro senza
#        valore): `TECNICO`, il rimedio e' di chi installa. In un posto solo,
#        come `E_VALIDATION_INPUT`.
E_CONFIG_MANCANTE = "E_CONFIG_MANCANTE"


class ServiceError(Exception):
    """Errore applicativo standard con metadati utili per API/UI."""

    # Scopo: Inizializza la istanza.
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
        fields: tuple[str, ...] | None = None,
        targets: tuple[Bersaglio, ...] | None = None,
    ) -> None:
        super().__init__(detail or message)
        self.code = code
        self.message = message
        self.detail = detail
        self.hint = hint
        self.tx_id = tx_id
        self.retryable = retryable
        self.context = context or {}
        # ⭐ I due canali strutturati del database, dal 2026-08-24. Prima
        #    esistevano solo per il `DatabaseError` che arriva NUDO al
        #    middleware: appena un service traduceva — cioe' sempre, in ogni
        #    dominio — il campo da correggere e il bersaglio si perdevano qui.
        #    ⚠️ `fields` NON sostituisce la convenzione `context={"field": ...}`
        #    dei 62 punti che costruiscono un ServiceError a mano: quella resta,
        #    e il translator la legge per prima (e' l'esplicito del chiamante).
        self.fields = fields
        self.targets = targets
