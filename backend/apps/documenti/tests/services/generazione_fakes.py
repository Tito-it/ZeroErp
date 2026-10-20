# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I finti comuni ai test unitari di `DocumentGenerationService`:
#        utente, righe di modello e versione, il service coi collaboratori
#        mockati e le patch di render, builder e perimetro.
# Note: Modulo di supporto ai test, non un modulo di test: il nome non comincia
#       per `test` apposta, cosi' il runner non lo raccoglie.
# ------------------------------------------------------------

"""Perche' esiste.

Estratto il 2026-10-20 (regola del 2) da tre moduli di test dello stesso
service: `test_document_generation_service`, `..._k` e `test_ristampa_fedele`.
Le copie erano gia' divergenti (il `_template_row` di `_k` non sapeva
costruire lo standard, `_versione_row` aveva il CSS in uno solo, l'oggi fisso
solo in uno), e il giorno della risoluzione a due livelli il mock della
risoluzione andava scritto due volte.

⚠️ Un `MagicMock` senza `spec` accetta qualunque nome: `service_with_mocks`
configura i metodi che gli si passano, anche se il repository non li ha piu'.
La giuntura vera la prova `tests/db/` (e mypy, per le chiamate dirette).
"""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)

_SERVICE = "apps.documenti.services.document_generation_service"


# Scopo: User mock (autenticato di default).
def make_user(*, is_authenticated: bool = True, user_id: int = 5) -> Any:
    user = MagicMock()
    user.is_authenticated = is_authenticated
    user.id = user_id
    return user


# Scopo: La riga di un modello come la rilegge `get_template`. `standard=True`
#        con `emittente=None` e' il modello standard (CHECK a DB).
def template_row(
    *,
    template_id: int = 7,
    emittente: int | None = 11,
    sorgente_tipo: int = 10,
    tipo_output: int = 1,
    builder_code: str = "PREVENTIVO",
    file_name_pattern: str = "preventivo-{numero}.pdf",
    descrizione: str = "Preventivo standard",
    standard: bool = False,
) -> dict[str, Any]:
    return {
        "id": template_id,
        "codice": "TPL-PREV",
        "codice_interno": "TPL_PREV",
        "descrizione": descrizione,
        "emittente_fiscale_id": emittente,
        "sorgente_tipo_id": sorgente_tipo,
        "tipo_documento_output_id": tipo_output,
        "context_builder_code": builder_code,
        "file_name_pattern": file_name_pattern,
        "is_default": True,
        "attivo": True,
        "standard": standard,
    }


# Scopo: I mock della risoluzione per default, da spargere in
#        `repo_methods`: il DB risponde con l'id, il livello e la versione
#        che stampa (P-2), il repository rilegge la riga del modello. La riga
#        della versione la da' il chiamante, come `get_versione`.
def risolto(
    template: dict[str, Any],
    *,
    livello: str = "EMITTENTE",
    versione_id: int = 12,
) -> dict[str, Any]:
    return {
        "risolvi_template_applicabile": {
            "template_documento_id": template["id"],
            "livello": livello,
            "template_versione_id": versione_id,
        },
        "get_template": template,
    }


# Scopo: La versione PUBBLICATA attiva del modello.
def versione_row(*, versione_id: int = 12) -> dict[str, Any]:
    return {
        "id": versione_id,
        "versione": 1,
        "stato": "PUBBLICATA",
        "html_template": "<p>{{ numero }}</p>",
        "css_template": "p { font-size: 10pt; }",
        "markdown_template": None,
        "render_engine_codice": "WEASYPRINT",
    }


# Scopo: Il service con repository, reader e storage mockati; ogni voce dei
#        dizionari e' il `return_value` del metodo omonimo. Ritorna
#        `(svc, repo, reader, storage)`.
def service_with_mocks(
    *,
    repo_methods: dict[str, Any] | None = None,
    reader_methods: dict[str, Any] | None = None,
    storage_methods: dict[str, Any] | None = None,
) -> tuple[DocumentGenerationService, MagicMock, MagicMock, MagicMock]:
    repo = MagicMock()
    for name, value in (repo_methods or {}).items():
        getattr(repo, name).return_value = value
    reader = MagicMock()
    for name, value in (reader_methods or {}).items():
        getattr(reader, name).return_value = value
    storage = MagicMock()
    for name, value in (storage_methods or {}).items():
        getattr(storage, name).return_value = value
    svc = DocumentGenerationService(
        repo=repo, reader=reader, storage=storage,
    )
    # Hook today() deterministico per i test (idempotente).
    svc._today = lambda: date(2026, 5, 4)  # type: ignore[method-assign]
    return svc, repo, reader, storage


def patch_render(return_value: bytes = b"%PDF-1.4 fake"):
    return patch(f"{_SERVICE}.render_pdf", return_value=return_value)


# Scopo: Patch di get_builder_del_template con un builder il cui
#        `build_context` ritorna `context`.
def patch_get_builder(context: dict[str, Any] | None = None):
    builder = MagicMock()
    builder.CODE = "PREVENTIVO"
    # La forma dei dati del builder: arriva al guard prima del render.
    builder.CONTEXT_VERSION = 2
    builder.build_context.return_value = context if context is not None else {"numero": 1}
    return patch(f"{_SERVICE}.get_builder_del_template", return_value=builder)


# Scopo: Il perimetro emittenti dell'utente (None = vede tutto).
def patch_scope(value: list[int] | None = None):
    return patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=value,
    )
