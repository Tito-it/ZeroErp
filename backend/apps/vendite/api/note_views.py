# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Cablaggio note partizionate dei 6 domini del ciclo attivo vendite sul
#        building block apps.core.partitioned_note_*. Qui vive SOLO il cablaggio
#        (service factory + view): i parametri di partizione stanno in
#        `apps/vendite/db/note_repositories.py`, perche' li consuma anche il
#        service del dettaglio fattura (contatore note) e un service non puo'
#        importare da `api/`. Aggiungere un dominio = una istanza repo la` +
#        una factory e una coppia di view qui.
# Note: il `target_tipo` delle view (nomi dei serializer e delle classi nello
#       schema OpenAPI) si legge dall'istanza del repository, non si riscrive:
#       fino al 2026-10-25 era una seconda copia del codice della partizione.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.api.partitioned_note_views import make_note_views
from apps.core.services.partitioned_note_service import PartitionedNoteService
from apps.vendite.db.note_repositories import (
    NOTE_REPO_CONTRATTO,
    NOTE_REPO_DDT,
    NOTE_REPO_FATTURA,
    NOTE_REPO_OFFERTA,
    NOTE_REPO_ORDINE,
    NOTE_REPO_PREVENTIVO,
)


# Scopo: Factory dei service note preventivo. Il service e' istanziato
#        per-request per evitare accumulo di stato fra richieste concorrenti
#        (il repo, senza stato runtime, resta condiviso).
def _preventivo_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=NOTE_REPO_PREVENTIVO)


ApiPreventivoNoteList, ApiPreventivoNoteDetail = make_note_views(
    area_funzionale="vendite",
    parent_path_param="preventivo_id",
    service_factory=_preventivo_service_factory,
    target_tipo=NOTE_REPO_PREVENTIVO.target_tipo,
    model_permission=("vendite", "preventivo"),
)


# Scopo: Factory dei service note contratto.
def _contratto_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=NOTE_REPO_CONTRATTO)


ApiContrattoNoteList, ApiContrattoNoteDetail = make_note_views(
    area_funzionale="vendite",
    parent_path_param="contratto_id",
    service_factory=_contratto_service_factory,
    target_tipo=NOTE_REPO_CONTRATTO.target_tipo,
    model_permission=("vendite", "contratto"),
)


# Scopo: Factory dei service note offerta commerciale.
def _offerta_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=NOTE_REPO_OFFERTA)


ApiOffertaNoteList, ApiOffertaNoteDetail = make_note_views(
    area_funzionale="vendite",
    parent_path_param="offerta_id",
    service_factory=_offerta_service_factory,
    target_tipo=NOTE_REPO_OFFERTA.target_tipo,
    model_permission=("vendite", "offerta_commerciale"),
)


# Scopo: Factory dei service note ordine di vendita.
def _ordine_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=NOTE_REPO_ORDINE)


ApiOrdineNoteList, ApiOrdineNoteDetail = make_note_views(
    area_funzionale="vendite",
    parent_path_param="ordine_id",
    service_factory=_ordine_service_factory,
    target_tipo=NOTE_REPO_ORDINE.target_tipo,
    model_permission=("vendite", "ordine"),
)


# Scopo: Factory dei service note DDT di vendita.
def _ddt_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=NOTE_REPO_DDT)


ApiDdtNoteList, ApiDdtNoteDetail = make_note_views(
    area_funzionale="vendite",
    parent_path_param="ddt_id",
    service_factory=_ddt_service_factory,
    target_tipo=NOTE_REPO_DDT.target_tipo,
    model_permission=("vendite", "ddt"),
)


# Scopo: Factory dei service note fattura.
def _fattura_service_factory() -> PartitionedNoteService:
    return PartitionedNoteService(repo=NOTE_REPO_FATTURA)


ApiFatturaNoteList, ApiFatturaNoteDetail = make_note_views(
    area_funzionale="vendite",
    parent_path_param="fattura_id",
    service_factory=_fattura_service_factory,
    target_tipo=NOTE_REPO_FATTURA.target_tipo,
    model_permission=("vendite", "fattura"),
)
