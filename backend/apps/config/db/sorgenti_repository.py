# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lettura di `config.sorgenti` per codice: la sorgente ATTIVA con un
#        `codice_interno`, con id, chiave del nodo e tabella del documento.
# ------------------------------------------------------------

# PERCHE' ESISTE (regola del 2, ok Tid 2026-10-11). La stessa lettura c'era tre
# volte, ognuna con la sua forma:
#   DocumentiRepository.get_sorgente_tipo_id_by_codice  → {id, codice, attivo},
#       e il chiamante scartava a mano le inattive;
#   ResiRepository.get_sorgente_tipo_id_by_codice       → solo l'id, attive;
#   VenditeRepository.get_lineage_sorgente              → {id, key_selector,
#       target_table}, attive.
# Tutti i chiamanti volevano la stessa cosa: la sorgente attiva, o niente.
# ⭐ L'attivita' la decide QUI, una volta: una sorgente spenta non e' «trovata
#    ma da scartare», non c'e'. Il codice si passa con le costanti di
#    `apps.config.sorgenti`.

from __future__ import annotations

from typing import TypedDict

from django.db import connection


class SorgenteRow(TypedDict):
    id: int
    codice: str
    # Come si scrive la chiave del nodo del documento nel grafo e nelle
    # pratiche: 'id' (id reso a testo) o 'uid' (convenzione di
    # config/manual/sorgenti.md).
    key_selector: str
    # La tabella del documento (regclass seedata), per tradurre un id in uid.
    # ⚠️ NULLABLE nel modello (`config.sorgenti.target_table`): NULL resta None,
    #    mai la stringa 'None' (la lettura del lineage faceva `str()` sul NULL).
    target_table: str | None


class SorgentiRepository:
    """Lettura di config.sorgenti per codice_interno."""

    # Scopo: la sorgente ATTIVA col `codice_interno` dato (chiave immutabile;
    #        `codice` e' l'etichetta, mutabile).
    # Risultato atteso: la riga, o None se il codice non esiste o la sorgente e'
    #        spenta — per chi chiama le due cose sono la stessa: non si usa.
    def get_sorgente_attiva(self, codice_interno: str) -> SorgenteRow | None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.id, s.codice, s.key_selector, s.target_table::text
                  FROM config.sorgenti s
                 WHERE s.codice_interno = %s
                   AND s.attivo IS TRUE
                """,
                [codice_interno],
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": int(row[0]),
            "codice": str(row[1]),
            "key_selector": str(row[2]),
            "target_table": None if row[3] is None else str(row[3]),
        }
