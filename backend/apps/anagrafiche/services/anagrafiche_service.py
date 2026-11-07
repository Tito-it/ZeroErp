# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade generica dello schema anagrafiche per le operazioni che non
#        appartengono a nessun sottodominio (oggi: il lookup delle risorse umane).
# Note: Nasce col brief-db-modifiche-certe-ciclo-vendita-e-articolo (§5.5,
#       voce 4): il responsabile della commessa e' una `risorsa_umana_id`
#       (D-A), e nessun lookup di risorse umane esisteva fuori da `pratiche`,
#       dove e' per reparto. Naming `<schema>_service.py` come da AGENTS.md.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.anagrafiche.db.anagrafiche_repository import AnagraficheRepository
from apps.core.api.search_validators import require_min_search_length


class AnagraficheService:
    """Facade per le letture generiche dello schema anagrafiche."""

    def __init__(self, repo: AnagraficheRepository | None = None) -> None:
        self._repo = repo or AnagraficheRepository()

    # Scopo: Lookup delle risorse umane attive per un picker («chi governa»):
    #        ricerca libera opzionale sul nome (min 3 caratteri, come ogni
    #        ricerca testuale del progetto). Ritorna `{"results": [...]}`,
    #        l'envelope di ogni lookup dedicato (api.md §L'envelope di un lookup).
    def lookup_risorse_umane(self, *, search: str | None = None) -> dict[str, Any]:
        termine = (search or "").strip() or None
        require_min_search_length(termine, field_name="search")
        return {"results": self._repo.list_risorse_umane_lookup(search=termine)}
