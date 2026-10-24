# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'alert scadenze dei listini (`ListiniRepository.listini_in_scadenza`)
#        sul DB vero, coi casi COSTRUITI (brief-be-verifica-documentazione-api
#        §C1, 2026-10-21).
#        `validita` e' `daterange(valido_dal, valido_al, '[]')`, che PostgreSQL
#        normalizza in `[)`: `upper(validita)` e' `valido_al + 1`. La query
#        leggeva la scadenza e il successore da `upper()`, quindi:
#          - un successore CONTIGUO (`valido_dal = valido_al + 1`, il caso
#            normale) non contava, perche' `valido_dal > upper()` e' falso: la
#            versione risultava «in scadenza senza successore»;
#          - `valido_al` e `giorni_rimanenti` uscivano con un giorno in piu'.
#        ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1`; tutto in una transazione annullata.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) ListiniInScadenzaDbTests.test_senza_successore_e_in_scadenza_col_giorno_giusto
2) ListiniInScadenzaDbTests.test_il_successore_contiguo_la_toglie_dall_alert
"""
from __future__ import annotations

import unittest
from uuid import uuid4

from django.db import connection, transaction

from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.listini_repository import ListiniRepository


class ListiniInScadenzaDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: un listino con la versione ATTIVA che scade fra 5 giorni; se
    #        `successore`, una BOZZA che parte il giorno dopo. Ritorna
    #        (versione_id, alert delle versioni di QUEL listino).
    def _alert(self, *, successore: bool) -> tuple[int, list[dict]]:
        etichetta = f"scadenza {uuid4().hex[:8]}"
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    cur.execute(
                        "SELECT m.utility_id, (SELECT script.fn_data_operativa()) AS oggi"
                        "  FROM dbops.fn_pgtap_crea_mondo_cliente(%s) m",
                        [etichetta],
                    )
                    utility_id, oggi = cur.fetchone()
                    cur.execute(
                        "SELECT * FROM dbops.fn_pgtap_crea_listino(%s, %s, %s::date - 10, %s::date + 5)",
                        [utility_id, etichetta, oggi, oggi],
                    )
                    listino_id, versione_id, _tipologia = cur.fetchone()
                    if successore:
                        cur.execute(
                            "INSERT INTO vendite.listini_versioni"
                            " (listino_id, codice_versione, valido_dal, valido_al, stato)"
                            " VALUES (%s, 'PGTAP_V2', %s::date + 6, NULL, 'BOZZA')",
                            [listino_id, oggi],
                        )
                righe = [
                    r for r in ListiniRepository().listini_in_scadenza(30)
                    if r["listino_id"] == listino_id
                ]
                self._oggi = oggi
                return versione_id, righe
            finally:
                transaction.set_rollback(True)

    def test_senza_successore_e_in_scadenza_col_giorno_giusto(self) -> None:
        versione_id, righe = self._alert(successore=False)
        self.assertEqual([r["versione_id"] for r in righe], [versione_id])
        from datetime import timedelta

        self.assertEqual(righe[0]["valido_al"], self._oggi + timedelta(days=5))
        self.assertEqual(righe[0]["giorni_rimanenti"], 5)

    def test_il_successore_contiguo_la_toglie_dall_alert(self) -> None:
        _versione_id, righe = self._alert(successore=True)
        self.assertEqual(righe, [])
