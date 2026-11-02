# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Istanze del BB `PartitionedNoteRepository` per i 6 domini note del
#        ciclo attivo vendite (una per partizione di `vendite.note`).
#        Vivono nel layer `db/` e non nella view perche' i parametri di
#        partizione sono un fatto di ACCESSO AI DATI, non di routing: oltre
#        alle view note (`api/note_views.py`) li consuma ora anche
#        `vendite_service.get_fattura_dettaglio`, che conta le note per il
#        badge del drawer — e un service non puo' importare da `api/` senza
#        invertire i layer. Punto unico: aggiungere un dominio note = una
#        istanza qui, zero duplicazione dei nomi di tabella.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.db.partitioned_note_repository import PartitionedNoteRepository

# Le istanze sono singleton-friendly (nessuno stato runtime: solo i nomi degli
# identifier SQL, validati per regex nel `__init__` del BB). Il *service*
# `PartitionedNoteService` resta invece per-request — vedi le factory in
# `api/note_views.py`.

NOTE_REPO_PREVENTIVO = PartitionedNoteRepository(
    partition_table="vendite.note_preventivo",
    target_tipo="PREVENTIVO",
    parent_table="vendite.preventivi",
    parent_pk="id",
    child_table="vendite.preventivi_righe",
    child_parent_fk="preventivo_id",
)

NOTE_REPO_CONTRATTO = PartitionedNoteRepository(
    partition_table="vendite.note_contratto",
    target_tipo="CONTRATTO",
    parent_table="vendite.contratti",
    parent_pk="id",
    child_table="vendite.contratti_righe",
    child_parent_fk="contratto_id",
)

# ⭐ Il `target_tipo` di ogni istanza e' un codice di `config.tipi_entita` (la
# FK del padre `vendite.note` lo pretende, e il confine della partizione e' quel
# codice): dal 2026-10-25 `ORDINE_VENDITA`, `DDT_VENDITA`, `OFFERTA_COMMERCIALE`
# (lotto 3 di brief-db-grammatica-unica-documenti). Un codice senza partizione
# non arriva a nessun vincolo: lo rifiuta il routing di PostgreSQL.

# Partizione 'OFFERTA_COMMERCIALE'. Il child_table
# `vendite.offerte_commerciali_eccezioni` collega le note di RIGA via FK
# `offerta_id` (verificata su dbzero/vendite/tabelle).
NOTE_REPO_OFFERTA = PartitionedNoteRepository(
    partition_table="vendite.note_offerte_commerciali",
    target_tipo="OFFERTA_COMMERCIALE",
    parent_table="vendite.offerte_commerciali",
    parent_pk="id",
    child_table="vendite.offerte_commerciali_eccezioni",
    child_parent_fk="offerta_id",
)

# Partizione 'ORDINE_VENDITA'. Il child_table `vendite.ordini_righe` collega le
# note di RIGA via FK `ordine_id` (note_ordini.target_riga_id -> ordini_righe.id).
NOTE_REPO_ORDINE = PartitionedNoteRepository(
    partition_table="vendite.note_ordini",
    target_tipo="ORDINE_VENDITA",
    parent_table="vendite.ordini",
    parent_pk="id",
    child_table="vendite.ordini_righe",
    child_parent_fk="ordine_id",
)

# Partizione 'DDT_VENDITA'. Il child_table `vendite.ddt_righe` collega le note
# di RIGA via FK `ddt_id` (note_ddt.target_riga_id -> ddt_righe.id).
NOTE_REPO_DDT = PartitionedNoteRepository(
    partition_table="vendite.note_ddt",
    target_tipo="DDT_VENDITA",
    parent_table="vendite.ddt",
    parent_pk="id",
    child_table="vendite.ddt_righe",
    child_parent_fk="ddt_id",
)

# Partizione 'FATTURA' (`vendite.note_fatture` e' definita
# FOR VALUES IN ('FATTURA')). Il
# child_table `vendite.fatture_righe` collega le note di RIGA via FK
# `fattura_id` (note_fatture.target_riga_id -> fatture_righe.id).
# Sesto e ultimo dominio note del ciclo attivo: nessuna migration, la partizione
# e il suo trigger di validazione esistono gia' a DB.
# La nota resta scrivibile anche su fattura congelata: il congelamento di
# `trgfn_fattura_satellite_guard_congelamento` protegge gli IMPORTI della
# fattura, non l'annotazione operativa che ci gira intorno.
# ⚠️ `vendite.note_fatture` NON ha policy RLS (a differenza di `fatture`,
# `fatture_righe` e `fatture_riepiloghi_iva`): ogni lettura che parte da qui
# — incluso il `count_for_parent` del badge — deve passare PRIMA dal cancello
# di scope sulla testata. Cfr. brief-db-rls-satelliti-fattura-portale.
NOTE_REPO_FATTURA = PartitionedNoteRepository(
    partition_table="vendite.note_fatture",
    target_tipo="FATTURA",
    parent_table="vendite.fatture",
    parent_pk="id",
    child_table="vendite.fatture_righe",
    child_parent_fk="fattura_id",
)
