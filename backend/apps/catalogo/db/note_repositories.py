# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Istanze del BB `PartitionedNoteRepository` per le due partizioni di
#        `catalogo.note`: le note di un articolo e quelle di un legame di
#        distinta. Stanno nel layer `db/` come quelle di vendita
#        (`apps/vendite/db/note_repositories.py`): i parametri di partizione
#        sono un fatto di accesso ai dati, non di routing.
# ⭐ Dal 2026-11-11 (giro 4 di brief-db-revisione-catalogo, D16/R6) le note di
#    catalogo hanno la forma di quelle degli altri schemi, e passano dallo
#    stesso BB: fino a quel giorno `catalogo_service` ne aveva una copia sua
#    (estrazione del payload, traduzione dei vincoli, CRUD).
# ⚠️ Nessuna nota di RIGA: una nota di catalogo annota l'anagrafica intera
#    (`chk_note_catalogo_ancora_documento`), quindi nessun `child_table`.
#    Le chiavi dei padri sono UUID (`target_id_uuid=True`).
# ------------------------------------------------------------

from __future__ import annotations

from apps.catalogo.db.catalogo_bom_repository import (
    NOTA_TARGET_ARTICOLO,
    NOTA_TARGET_COMPONENTE,
)
from apps.core.db.partitioned_note_repository import PartitionedNoteRepository

NOTE_REPO_ARTICOLO = PartitionedNoteRepository(
    partition_table="catalogo.note_articoli",
    target_tipo=NOTA_TARGET_ARTICOLO,
    parent_table="catalogo.articoli",
    parent_pk="id",
    target_id_uuid=True,
)

NOTE_REPO_ARTICOLO_COMPONENTE = PartitionedNoteRepository(
    partition_table="catalogo.note_articoli_componenti",
    target_tipo=NOTA_TARGET_COMPONENTE,
    parent_table="catalogo.articoli_componenti",
    parent_pk="id",
    target_id_uuid=True,
)
