# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'accesso al DB del provisioning di sviluppo: l'ambiente
#        dell'installazione e il verbo che crea, o rimette a posto, gli utenti
#        e i dati di prova (`anagrafiche.fn_provisiona_dati_di_sviluppo`).
# Note: Brief brief-db-processi-accensione-per-ambiente §5-ter.3 e
#       brief-be-utenti-di-sviluppo T-1. Il verbo e' SECURITY DEFINER e in
#       PRODUZIONE non parte: il backend lo chiama e basta, non scrive
#       etichette ne' dati di prova per conto suo.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import TypedDict, cast

from django.db import connection

from apps.core.db._helpers import rows_to_list


class RadiceDiProva(TypedDict):
    """Una riga del verbo: una radice dei dati di prova."""
    tipo: str              # CREDENZIALE / SOGGETTO
    chiave: str            # username, o codice di prova del soggetto
    radice_id: str         # auth_user.id o soggetti.id, come testo
    esito: str             # creata / riallineata
    secondo_fattore: bool | None  # solo per le credenziali


class DatiDiSviluppoRepository:
    """Ambiente dell'installazione e verbo del provisioning di sviluppo."""

    # Scopo: L'ambiente dichiarato (`SVILUPPO` / `PRODUZIONE`), o None se
    #        l'installazione non l'ha ancora dichiarato. Si chiede al lettore
    #        che DESCRIVE (`script.fn_ambiente_dichiarato`), che non solleva:
    #        il command vuole dire lui perche' si ferma. ⛔ Nessuna cache: lo si
    #        chiede a ogni corsa.
    def ambiente_dichiarato(self) -> str | None:
        with connection.cursor() as cursor:
            cursor.execute("SELECT script.fn_ambiente_dichiarato()")
            row = cursor.fetchone()
        assert row is not None
        return row[0]

    # Scopo: Chiama il verbo con gli hash Django delle password
    #        (username → hash; un utente assente tiene la sua) e restituisce
    #        una riga per radice. Le GUC di sessione le governa il verbo.
    def provisiona(self, password_hash: dict[str, str]) -> list[RadiceDiProva]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT tipo, chiave, radice_id, esito, secondo_fattore
                  FROM anagrafiche.fn_provisiona_dati_di_sviluppo(%s::jsonb)
                """,
                [json.dumps(password_hash)],
            )
            return cast(list[RadiceDiProva], rows_to_list(cursor))
