# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Costanti del workflow autorizzazioni prezzi (Sprint E listini v5).
#        Single source-of-truth importabile da altri service del dominio
#        (preventivi_service, eventuali futuri ordini/fatture).
# ------------------------------------------------------------

# Stati applicabili al campo `vendite.preventivi_righe.stato_approvazione_prezzo`
# (ENUM nativo `config.stato_approvazione_prezzo`). Coerente col seed DB.
STATO_APPROVAZIONE_PENDING = "PENDING"
STATO_APPROVAZIONE_APPROVED = "APPROVED"
STATO_APPROVAZIONE_REJECTED = "REJECTED"

# Set degli stati che "congelano" il preventivo (vedi
# `preventivi_service.get_preventivo`: filter capability + freeze pricing).
STATI_FREEZE_PREVENTIVO = frozenset({
    STATO_APPROVAZIONE_PENDING,
    STATO_APPROVAZIONE_REJECTED,
})

# Codici azione di processo (`config.azioni_processo.permission_codename`).
# Granularita' per permettere a operatori specifici override autonomo o
# approvazione delle richieste pendenti.
AZIONE_OVERRIDE_PREZZO = "prezzo_override_manuale"
AZIONE_APPROVA_PREZZO = "approva_prezzo_override"

# Chiave nel meta della pratica APPROVAZIONE_PREZZO che linka alla riga
# preventivo target. Mantenere allineato col FE
# `ApprovazioniPrezzoListView.META_KEY_RIGA_PREVENTIVO_ID`.
META_KEY_RIGA_PREVENTIVO_ID = "riga_preventivo_id"

# Refactor 2026-05-19 (BE porting gate riga contratti): pratiche
# APPROVAZIONE_PREZZO possono avere come sorgente preventivi O contratti
# (DB simmetrizzato col brief `brief-db-contratti-righe-approvazione-prezzo-simmetria-l3.md`).
# Il discriminator vive nel meta della pratica:
#   - `sorgente` = "preventivo" | "contratto"
#   - chiave `riga_*_id` corrispondente
# Per le pratiche legacy (senza `sorgente` nel meta) il fallback e' preventivo
# coerente con la prima implementazione Sprint E. Il FE legge `sorgente` per
# routing verso /righe/<id>/approva-prezzo/ (preventivi) o
# /righe-contratto/<id>/approva-prezzo/ (contratti).
META_KEY_RIGA_CONTRATTO_ID = "riga_contratto_id"
META_KEY_SORGENTE = "sorgente"
# ⚠️ Prefisso `META_`: sono i VALORI della chiave `sorgente` nel meta della
#    pratica (minuscoli, scritti nei dati), non i codici di `config.sorgenti`.
#    Fino al 2026-10-19 si chiamavano `SORGENTE_PREVENTIVO`/`_CONTRATTO`/
#    `_OFFERTA`, come le costanti di `apps.config.sorgenti` con valori diversi:
#    in un modulo che importava entrambi vinceva l'ultimo import, in silenzio.
#    Il passaggio ai codici delle sorgenti e' un lotto di
#    brief-db-grammatica-unica-documenti (§7.9, le approvazioni di prezzo).
META_SORGENTE_PREVENTIVO = "preventivo"
META_SORGENTE_CONTRATTO = "contratto"

# Refactor 2026-06-01 (gate L1/L2/L3 sulle offerte): terza sorgente del
# workflow L3. Le offerte commerciali hanno eccezioni OVERRIDE/AGGIUNTA col
# prezzo manuale, simmetriche alle righe contratto. Il DB ha colonne
# `stato_approvazione_prezzo`/`pratica_approvazione_prezzo_id` su
# `vendite.offerte_commerciali_eccezioni` (migration 20260601-01).
META_KEY_RIGA_OFFERTA_ID = "riga_offerta_id"
META_SORGENTE_OFFERTA = "offerta"

# Stato preventivo "bozza" (codice_interno in `config.stati_doc_preventivi`).
# La descrizione mostrata all'utente e' "Bozza" ma il codice tecnico e' DRAFT.
STATO_PREVENTIVO_DRAFT = "DRAFT"
