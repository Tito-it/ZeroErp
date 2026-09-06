# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il vocabolario di `ambito` per la famiglia email — mirror dichiarato dei
#        CHECK `chk_email_log_ambito` e `chk_email_outbox_ambito`, che sono la
#        stessa regola su due tabelle.
# Note: ⛔ STA QUI E NON IN UNA VIEW, ed e' il motivo per cui questo modulo
#        esiste. Fino al 2026-09-06 `AMBITI_OUTBOX` viveva in
#        `apps/core/api/email_views.py`: il repository che ne aveva bisogno
#        avrebbe dovuto importare una view — cioe' il livello piu' esterno — per
#        sapere una regola di dominio. Un vocabolario non appartiene a chi lo
#        valida per primo.
#        ⚠️ Il confronto col catalogo lo fa
#        `apps/core/tests/db/test_email_outbox_ambito_guardrail.py`: qui c'e' la
#        copia, la' la prova che segua l'originale.
# ------------------------------------------------------------

from __future__ import annotations


# ⭐ `SISTEMA` non e' un ambito come gli altri, ed e' il motivo per cui ha una
#    costante sua: e' il ramo su cui la policy RLS di `config.email_log` e
#    `config.email_outbox` decide che la riga la legge SOLO il super admin (o
#    l'identita' tecnica del processo che spedisce). Le email che porta —
#    reset password, alert — valgono quanto una credenziale.
# ⛔ Non e' un valore di ripiego: fino al 2026-09-05 l'API lo metteva per default
#    quando il client taceva, quindi «nessuno ha dichiarato l'ambito» e «email di
#    sistema» erano lo stesso valore. Una colonna con un default non puo' fare da
#    cancello di sicurezza.
AMBITO_SISTEMA = "SISTEMA"
AMBITO_REPARTO = "REPARTO"
AMBITO_OPERATORE = "OPERATORE"

# ⚠️ L'ordine e' quello del CHECK a database, e il confronto e' su insiemi: qui
#    conta che ci siano tutti, non la sequenza.
AMBITI_EMAIL: tuple[str, ...] = (AMBITO_SISTEMA, AMBITO_REPARTO, AMBITO_OPERATORE)
