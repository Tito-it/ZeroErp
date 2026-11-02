# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I vocabolari della famiglia email: `ambito` — mirror dichiarato dei
#        CHECK `chk_email_log_ambito` e `chk_email_outbox_ambito`, che sono la
#        stessa regola su due tabelle — e `stato` del log (`chk_email_log_stato`).
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

from typing import Any


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


# ⭐ GLI STATI DI `config.email_log`, con la frase che l'operatore legge nel
#    filtro. Mirror dichiarato di `chk_email_log_stato`, confrontato col
#    catalogo da `apps/core/tests/db/test_email_log_stati_guardrail.py`.
# ⚠️ Fino al 2026-09-26 viveva in `amm_software_service`, servito da una rotta
#    `AdminAPIView`: il vocabolario c'era solo per il super admin. Da quando la
#    lista del log e' aperta a ogni operatore anche il filtro deve esserlo, e un
#    vocabolario che serve due schermate non appartiene al pannello di una.
# ⛔ L'ordine della tupla E' l'ordine di uscita (`ordering` lo dichiara, e il
#    test lo pretende): «default-first», SENT come stato finale piu' frequente.
STATI_EMAIL_LOG_DESCRIZIONI: tuple[tuple[str, str, int], ...] = (
    ("SENT",    "Inviata",                                  1),
    ("PENDING", "In attesa di invio",                       2),
    ("RETRY",   "Tentativo successivo programmato",         3),
    ("FAILED",  "Invio fallito",                            4),
    # ⭐ `SIMULATA` (2026-09-11): la mail e' stata STAMPATA a video invece che
    #    spedita — sviluppo senza SMTP. E' terminale e VOLUTA, e per questo non
    #    e' `FAILED`; e non e' `SENT` perche' non e' arrivata a nessuno.
    #    ⚠️ La frase dice l'esito, non il canale: chi legge il giornale chiede
    #    «e' arrivata?», non «da quale strada e' uscita».
    ("SIMULATA", "Simulata — non spedita",                  5),
)

STATI_EMAIL_LOG: frozenset[str] = frozenset(c for c, _d, _o in STATI_EMAIL_LOG_DESCRIZIONI)


# Scopo: Gli stati del log come righe di lookup, nell'ordine dichiarato.
def elenco_stati_email_log() -> list[dict[str, Any]]:
    return [
        {"codice": codice, "descrizione": descrizione, "ordering": ordering}
        for codice, descrizione, ordering in STATI_EMAIL_LOG_DESCRIZIONI
    ]
