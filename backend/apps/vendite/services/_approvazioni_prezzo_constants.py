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

# Stato preventivo "bozza" (codice_interno in `config.stati_doc_preventivi`).
# La descrizione mostrata all'utente e' "Bozza" ma il codice tecnico e' DRAFT.
STATO_PREVENTIVO_DRAFT = "DRAFT"
