# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il dizionario dei TIPI delle chiavi dei contratti email — bozze
#        (`core`), template e account (`amm_software`) — per il building block
#        `schema_da_contratto`. Una chiave, un tipo: `oggetto` e' lo stesso
#        testo nella bozza e nel template.
# Note: ⭐ I tipi vengono dalle colonne (docs/it/dbzero/config/tabelle/
#       email_*.md). `smtp_password` non e' una colonna (si salva cifrata): e'
#       un testo in sola scrittura.
# ------------------------------------------------------------

from __future__ import annotations

from apps.core.api.schema_da_contratto import (
    Tipi,
    booleano,
    intero,
    json,
    lista_di_testi,
    testo,
)

TIPI_EMAIL: Tipi = {
    # ── contenuto (bozza e template) ─────────────────────────
    "oggetto": (testo, False),
    "corpo_html": (testo, False),
    "corpo_testo": (testo, True),
    "lingua": (testo, False),
    # ── destinatari (bozza) ──────────────────────────────────
    "destinatario": (testo, False),
    "destinatari_cc": (lista_di_testi, True),
    # ── anagrafica (template e account) ──────────────────────
    "codice": (testo, False),
    "descrizione": (testo, False),
    "attivo": (booleano, False),
    "unita_organizzativa_id": (intero, True),
    "tipo_prestazione_id": (intero, True),
    "variabili_disponibili": (json, False),
    # ── account SMTP ─────────────────────────────────────────
    "smtp_host": (testo, False),
    "smtp_port": (intero, False),
    "smtp_use_tls": (booleano, False),
    "smtp_use_ssl": (booleano, False),
    "smtp_username": (testo, False),
    "smtp_password": (testo, False),
    "email_from": (testo, False),
    "email_reply_to": (testo, True),
}
