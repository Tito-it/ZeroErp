# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Selector get_storage() — istanzia il provider DocumentStorage
#        attivo leggendo `documenti_storage_provider` da config.parameters
#        e i parametri ausiliari (prefix, base_url, ecc.). Provider
#        whitelisted v1: 'filesystem'. S3/MinIO entreranno come ulteriori
#        rami di dispatch quando arrivano le rispettive implementazioni.
# ------------------------------------------------------------

from __future__ import annotations

from pathlib import Path

from django.conf import settings

from apps.core.services.error_manager import ErrorManager
from apps.core.services.parameter_service import ParameterService
from apps.documenti.services.storage.base import DocumentStorage
from apps.documenti.services.storage.filesystem import (
    build_filesystem_storage,
)


# Scopo: Costruisce e ritorna il DocumentStorage attivo per l'istanza ZeroERP
#        corrente. Una sola istanza per processo non e' garantita: il caller
#        decide se cachare. Il selector legge sempre i parametri freschi per
#        consentire il cambio provider senza restart (caso operativo raro).
def get_storage() -> DocumentStorage:
    params = ParameterService()
    provider = params.get_parameter("documenti_storage_provider").strip().lower()

    if provider == "filesystem":
        prefix = params.get_parameter("documenti_storage_prefix").strip()
        root = _resolve_filesystem_root()
        return build_filesystem_storage(root=root, prefix=prefix)

    ErrorManager.raise_error(
        code="E_DOCUMENTI_VALIDATION",
        message=f"Provider storage documenti non supportato: '{provider}'.",
        detail="Provider attesi v1: filesystem.",
    )


# Scopo: Risolve la root del filesystem provider.
#        Fonte unica: settings.DOCUMENTI_STORAGE_ROOT (sempre valorizzato
#        da settings.py — env override o default <BASE_DIR>/var/documenti).
#        Settings mancante = misconfigurazione di deployment, errore esplicito.
def _resolve_filesystem_root() -> Path:
    raw = getattr(settings, "DOCUMENTI_STORAGE_ROOT", None)
    if not raw:
        ErrorManager.raise_error(
            code="E_DOCUMENTI_STORAGE_FAILED",
            message="DOCUMENTI_STORAGE_ROOT non configurato.",
            detail="Verificare settings.py o env var DOCUMENTI_STORAGE_ROOT.",
        )
    return Path(raw)
