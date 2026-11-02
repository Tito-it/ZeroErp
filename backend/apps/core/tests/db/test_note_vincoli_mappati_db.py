# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Ogni CHECK e ogni FK delle partizioni di `vendite.note` ha la sua voce
#        nelle mappe di `PartitionedNoteService`, e ogni voce delle mappe
#        nomina un vincolo che esiste (F-7 di
#        analisi-be-difetti-emersi-verifica-doc-api-core).
#
# ⛔ PERCHE' ESISTE. Un vincolo non mappato non da' errore: la violazione cade
#    sul `fallback_code` `E_NOTA_VALIDATION`, 400, col messaggio generico. Fino
#    al 2026-10-07 succedeva per tutti i vincoli locali di offerta, ordine, DDT
#    e fattura — le mappe conoscevano solo preventivo e contratto, e nessun
#    test ne nominava i vincoli. I nomi locali non seguono un prefisso solo
#    (`offnote`, `ordini_note`, `ordnote`), quindi una partizione nuova scritta
#    «per analogia» resterebbe scoperta in silenzio.
#
# ⭐ SI LEGGE LA STRUTTURA, non i dati: `pg_constraint` delle partizioni
#    (`pg_inherits` della madre), cioe' il progetto scritto. Vale anche su un
#    database ricostruito da zero.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#    Solo letture.
# ------------------------------------------------------------

"""Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`).

0. test_la_madre_ha_partizioni
1. test_ogni_vincolo_delle_partizioni_e_mappato
2. test_ogni_voce_delle_mappe_nomina_un_vincolo_vero
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection

from apps.core.services.partitioned_note_service import (
    _CHECK_CONSTRAINTS,
    _FK_CONSTRAINTS,
)
from apps.core.tests.db_e2e import richiedi_db_provvisto

_SQL_VINCOLI = """
    SELECT DISTINCT c.conname
      FROM pg_inherits i
      JOIN pg_constraint c ON c.conrelid = i.inhrelid
     WHERE i.inhparent = 'vendite.note'::regclass
       AND c.contype IN ('c', 'f')
"""


# Scopo: i nomi dei CHECK e delle FK di tutte le partizioni di `vendite.note`.
def _vincoli_partizioni() -> set[str]:
    with connection.cursor() as cur:
        cur.execute(_SQL_VINCOLI)
        return {r[0] for r in cur.fetchall()}


class NoteVincoliMappatiTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 0) Senza partizioni i due test sotto sarebbero verdi per sottrazione.
    def test_la_madre_ha_partizioni(self) -> None:
        self.assertTrue(_vincoli_partizioni(), "vendite.note senza partizioni")

    # 1) Un vincolo senza voce esce `E_NOTA_VALIDATION` col messaggio generico.
    def test_ogni_vincolo_delle_partizioni_e_mappato(self) -> None:
        mappati = set(_CHECK_CONSTRAINTS) | set(_FK_CONSTRAINTS)
        self.assertEqual(sorted(_vincoli_partizioni() - mappati), [])

    # 2) Una voce che non nomina niente e' un nome sbagliato: il vincolo vero
    #    resta scoperto (e' il difetto di `fk_listini_utility`, catalogo BB).
    def test_ogni_voce_delle_mappe_nomina_un_vincolo_vero(self) -> None:
        mappati = set(_CHECK_CONSTRAINTS) | set(_FK_CONSTRAINTS)
        self.assertEqual(sorted(mappati - _vincoli_partizioni()), [])
