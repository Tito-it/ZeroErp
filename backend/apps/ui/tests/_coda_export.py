# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: la coda di un export di lista (`build_export_response`) FINTA, per i
#        test API in `SimpleTestCase`: configurazione della lista, colonne e
#        render mockati sui moduli che il BB legge (`export_helpers`), cosi'
#        la view arriva a rispondere 200 senza database.
# Note: ⭐ Nato il 2026-09-29 per le liste figlie (`build_lista_figlia_views`):
#       i test del cancello chiamavano anche l'export SENZA questa coda, e
#       l'export andava al DB, rispondeva 500 e il test non guardava lo stato
#       — un cancello giusto davanti a una view rotta passava verde, con un
#       traceback nell'output.
#       ⚠️ Gli altri test di export del backend (una dozzina) scrivono ancora
#       la loro coda a mano, con colonne e file propri: rientrano qui solo
#       quando la forma e' la stessa.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from unittest.mock import MagicMock, patch

_BASE = "apps.ui.api.export_helpers"


# Scopo: finge la coda dell'export e restituisce il mock di
#        `ListaExportService` (il render: `render.call_args.kwargs` dice cosa
#        e' finito nel file — `lista_codice`, `filtri_applicati`).
@contextmanager
def coda_export_finta(nome_file: str = "lista.csv") -> Iterator[MagicMock]:
    with ExitStack() as stack:
        ui_svc = stack.enter_context(patch(f"{_BASE}.UiService"))
        ui_repo = stack.enter_context(patch(f"{_BASE}.UiRepository", autospec=True))
        render_cls = stack.enter_context(patch(f"{_BASE}.ListaExportService"))
        ui_svc.return_value.get_lista_config.return_value = {"colonne": [], "pagina_dimensione": 10}
        ui_repo.return_value.list_colonne_by_codice.return_value = []
        render_cls.return_value.render.return_value = (b"x\n", "text/csv; charset=utf-8", nome_file)
        render_cls.select_colonne_visibili_da_config.return_value = []
        yield render_cls
