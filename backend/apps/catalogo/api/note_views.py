# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Cablaggio delle note di catalogo (articolo, legame di distinta) sul
#        building block apps.core.partitioned_note_*: service factory e view.
#        I parametri di partizione stanno in `apps/catalogo/db/note_repositories.py`.
# ⭐ Dal 2026-11-11 (brief-db-revisione-catalogo, giro 4): prima le note di
#    catalogo avevano view, service e repository propri, e il dettaglio di una
#    nota stava su una rotta a parte (`/catalogo/note/<id>/`). Ora le rotte
#    sono quelle del BB, sotto il padre (`…/note/<note_id>/`).
# ⚠️ `catalogo.note` e' una lista GLOBALE (perimetro_emittente = false a
#    catalogo): niente cancello di perimetro (`perimetro_emittente=False`).
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.catalogo.db.note_repositories import (
    NOTE_REPO_ARTICOLO,
    NOTE_REPO_ARTICOLO_COMPONENTE,
)
from apps.catalogo.services.catalogo_service import fn_verifica_componente_dell_articolo
from apps.core.api.partitioned_note_views import make_note_views
from apps.core.services.partitioned_note_service import PartitionedNoteService


def _articolo_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=NOTE_REPO_ARTICOLO)


def _componente_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=NOTE_REPO_ARTICOLO_COMPONENTE)


# Scopo: ⛔ il legame dell'URL e' dell'articolo dell'URL, o 404: un legame di
#        un altro articolo non si legge ne' si annota da questo percorso.
def _legame_dell_articolo(path_kwargs: dict[str, Any]) -> None:
    fn_verifica_componente_dell_articolo(path_kwargs["articolo_id"], path_kwargs["comp_id"])


ApiArticoloNoteList, ApiArticoloNoteDetail = make_note_views(
    area_funzionale="catalogo",
    parent_path_param="articolo_id",
    service_factory=_articolo_service_factory,
    target_tipo=NOTE_REPO_ARTICOLO.target_tipo,
    model_permission=("catalogo", "articolo"),
    perimetro_emittente=False,
    supporta_righe=NOTE_REPO_ARTICOLO.supports_riga,
)

ApiComponenteNoteList, ApiComponenteNoteDetail = make_note_views(
    area_funzionale="catalogo",
    parent_path_param="comp_id",
    service_factory=_componente_service_factory,
    target_tipo=NOTE_REPO_ARTICOLO_COMPONENTE.target_tipo,
    model_permission=("catalogo", "articolo"),
    perimetro_emittente=False,
    supporta_righe=NOTE_REPO_ARTICOLO_COMPONENTE.supports_riga,
    cancello_padre=_legame_dell_articolo,
)
