# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Cablaggio note partizionate (vendite.note_preventivo, note_contratto)
#        sul building block apps.core.partitioned_note_*. Una entry per dominio
#        sorgente: aggiungere ordini/DDT/fatture/AF si riduce a clonare 3 righe.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.api.partitioned_note_views import make_note_views
from apps.core.db.partitioned_note_repository import PartitionedNoteRepository
from apps.core.services.partitioned_note_service import PartitionedNoteService

# Scopo: Factory dei service note preventivo. Istanza repo singleton-friendly
#        (no stato runtime); il service e' istanziato per-request per evitare
#        accumulo di stato fra richieste concorrenti.
_PREVENTIVO_REPO = PartitionedNoteRepository(
    partition_table="vendite.note_preventivo",
    target_tipo="PREVENTIVO",
    parent_table="vendite.preventivi",
    parent_pk="id",
    child_table="vendite.preventivi_righe",
    child_parent_fk="preventivo_id",
)


def _preventivo_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=_PREVENTIVO_REPO)


ApiPreventivoNoteList, ApiPreventivoNoteDetail = make_note_views(
    area_funzionale="vendite",
    parent_path_param="preventivo_id",
    service_factory=_preventivo_service_factory,
    target_tipo="PREVENTIVO",
    model_permission=("vendite", "preventivo"),
)


# Scopo: Factory dei service note contratto.
_CONTRATTO_REPO = PartitionedNoteRepository(
    partition_table="vendite.note_contratto",
    target_tipo="CONTRATTO",
    parent_table="vendite.contratti",
    parent_pk="id",
    child_table="vendite.contratti_righe",
    child_parent_fk="contratto_id",
)


def _contratto_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=_CONTRATTO_REPO)


ApiContrattoNoteList, ApiContrattoNoteDetail = make_note_views(
    area_funzionale="vendite",
    parent_path_param="contratto_id",
    service_factory=_contratto_service_factory,
    target_tipo="CONTRATTO",
    model_permission=("vendite", "contratto"),
)
