# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le mappe vincolo -> codice dei legami conto bancario
#        (`conti_bancari_service._VINCOLI_LEGAME_*`) e la struttura vera delle
#        due tabelle dicono la stessa cosa, nei due versi (E-7 di
#        analisi-be-difetti-emersi-verifica-doc-api-core, 2026-10-07).
#
# ⛔ PERCHE' ESISTE. Una voce col nome sbagliato non da' errore: la violazione
#    cade sul ripiego generico, e il campo non si accende. Le unicita' del
#    legame RUOLO sono INDICI parziali, non vincoli: chi cercasse il nome solo
#    in `pg_constraint` li darebbe per inesistenti.
#
# ⭐ SI LEGGE LA STRUTTURA (pg_constraint + indici unici), non i dati.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    Solo letture.
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

1. test_ogni_voce_nomina_un_vincolo_o_indice_vero
2. test_ogni_vincolo_e_indice_unico_e_mappato
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection

from apps.anagrafiche.services.conti_bancari_service import (
    _VINCOLI_LEGAME_RUOLO,
    _VINCOLI_LEGAME_SOGGETTO,
)
from apps.core.tests.db_e2e import richiedi_db_provvisto

_TABELLE = {
    "anagrafiche.soggetti_conti_bancari": _VINCOLI_LEGAME_SOGGETTO,
    "anagrafiche.soggetti_ruoli_conti_bancari": _VINCOLI_LEGAME_RUOLO,
}

# CHECK, FK, UNIQUE, EXCLUDE della tabella, piu' gli indici UNIQUE che non
# sono vincoli (indici parziali). PK e NOT NULL esclusi: non arrivano mai
# come violazione nominata da tradurre (la PK e' generata, il NOT NULL lo
# nomina gia' `diagnostica_db` con la colonna).
_SQL_NOMI = """
    SELECT conname FROM pg_constraint
     WHERE conrelid = %s::regclass AND contype IN ('c', 'f', 'u', 'x')
    UNION
    SELECT ci.relname
      FROM pg_index i JOIN pg_class ci ON ci.oid = i.indexrelid
     WHERE i.indrelid = %s::regclass AND i.indisunique AND NOT i.indisprimary
"""


# Scopo: i nomi che una violazione su `tabella` puo' riportare.
def _nomi(tabella: str) -> set[str]:
    with connection.cursor() as cur:
        cur.execute(_SQL_NOMI, [tabella, tabella])
        return {r[0] for r in cur.fetchall()}


# Scopo: i nomi di una mappa `_VINCOLI_LEGAME_*`, tutte le categorie.
def _mappati(vincoli: dict[str, dict[str, tuple]]) -> set[str]:
    return {nome for mappa in vincoli.values() for nome in mappa}


class ContiBancariVincoliMappatiTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def test_ogni_voce_nomina_un_vincolo_o_indice_vero(self) -> None:
        for tabella, vincoli in _TABELLE.items():
            with self.subTest(tabella=tabella):
                self.assertEqual(sorted(_mappati(vincoli) - _nomi(tabella)), [])

    def test_ogni_vincolo_e_indice_unico_e_mappato(self) -> None:
        for tabella, vincoli in _TABELLE.items():
            with self.subTest(tabella=tabella):
                self.assertEqual(sorted(_nomi(tabella) - _mappati(vincoli)), [])
