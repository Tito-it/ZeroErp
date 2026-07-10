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


# Scopo: Factory dei service note offerta commerciale. Partizione
#        'OFFERTA' (target_tipo varchar(16) ammette solo 7 caratteri;
#        'OFFERTA_COMMERCIALE' (19) e' troppo lungo — vedi doc
#        `vendite.note_offerte_commerciali`). Il child_table
#        `vendite.offerte_commerciali_eccezioni` collega le note di RIGA
#        via FK `offerta_id` (verificata su dbzero/vendite/tabelle).
_OFFERTA_REPO = PartitionedNoteRepository(
    partition_table="vendite.note_offerte_commerciali",
    target_tipo="OFFERTA",
    parent_table="vendite.offerte_commerciali",
    parent_pk="id",
    child_table="vendite.offerte_commerciali_eccezioni",
    child_parent_fk="offerta_id",
)


def _offerta_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=_OFFERTA_REPO)


ApiOffertaNoteList, ApiOffertaNoteDetail = make_note_views(
    area_funzionale="vendite",
    parent_path_param="offerta_id",
    service_factory=_offerta_service_factory,
    target_tipo="OFFERTA",
    model_permission=("vendite", "offerta_commerciale"),
)


# Scopo: Factory dei service note ordine di vendita. Partizione 'ORDINE'
#        (target_tipo varchar(16): 'ORDINE' = 6 char, ok). Il child_table
#        `vendite.ordini_righe` collega le note di RIGA via FK `ordine_id`
#        (note_ordini.target_riga_id → ordini_righe.id).
_ORDINE_REPO = PartitionedNoteRepository(
    partition_table="vendite.note_ordini",
    target_tipo="ORDINE",
    parent_table="vendite.ordini",
    parent_pk="id",
    child_table="vendite.ordini_righe",
    child_parent_fk="ordine_id",
)


def _ordine_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=_ORDINE_REPO)


ApiOrdineNoteList, ApiOrdineNoteDetail = make_note_views(
    area_funzionale="vendite",
    parent_path_param="ordine_id",
    service_factory=_ordine_service_factory,
    target_tipo="ORDINE",
    model_permission=("vendite", "ordine"),
)


# Scopo: Factory dei service note DDT di vendita. Partizione 'DDT'
#        (target_tipo varchar(16): 'DDT' = 3 char, ok). Il child_table
#        `vendite.ddt_righe` collega le note di RIGA via FK `ddt_id`
#        (note_ddt.target_riga_id -> ddt_righe.id).
_DDT_REPO = PartitionedNoteRepository(
    partition_table="vendite.note_ddt",
    target_tipo="DDT",
    parent_table="vendite.ddt",
    parent_pk="id",
    child_table="vendite.ddt_righe",
    child_parent_fk="ddt_id",
)


def _ddt_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=_DDT_REPO)


ApiDdtNoteList, ApiDdtNoteDetail = make_note_views(
    area_funzionale="vendite",
    parent_path_param="ddt_id",
    service_factory=_ddt_service_factory,
    target_tipo="DDT",
    model_permission=("vendite", "ddt"),
)
