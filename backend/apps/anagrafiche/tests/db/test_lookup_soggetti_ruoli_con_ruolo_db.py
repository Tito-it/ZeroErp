# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il lookup soggetti-ruoli con `con_ruolo` toglie le righe «senza
#        ruolo» e lascia i ruoli di ogni tipo; senza il filtro le tiene.
#        Provato sul DATABASE VERO, coi soggetti costruiti.
# Note: Il difetto che presidia non da' errore (collaudo DDT di Tid,
#       2026-10-10): il campo destinatario del DDT salva un soggetto_ruolo_id,
#       e una riga «senza ruolo» scelta li' lasciava il campo vuoto in
#       silenzio. Il filtro e' nel ramo SQL della UNION: un mock non lo vede.
#       ⚠️ I soggetti si COSTRUISCONO (`dbops.fn_pgtap_crea_soggetto_pg`, ruolo
#       FO da `dbops.fn_pgtap_crea_soggetto_ruolo`), in transazione ANNULLATA.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) LookupSoggettiRuoliConRuoloDbTests.test_senza_filtro_tiene_la_riga_senza_ruolo
2) LookupSoggettiRuoliConRuoloDbTests.test_con_ruolo_toglie_la_riga_senza_ruolo
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto

# Un termine che sta solo nei soggetti costruiti qui.
_TERMINE = "ZqConRuoloLookup"


class LookupSoggettiRuoliConRuoloDbTests(unittest.TestCase):

    def setUp(self):
        richiedi_db_provvisto()

    # Scopo: due soggetti col termine — uno senza ruoli, uno con un ruolo FO —
    #        e la ricerca del repository, in una transazione che si annulla.
    def _cerca(self, *, con_ruolo: bool) -> tuple[list[dict], str, str]:
        from apps.anagrafiche.db.soggetti_repository import SoggettiRepository

        esito: dict = {}
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_soggetto_pg(%s)::text",
                    [f"{_TERMINE} senza ruolo"],
                )
                senza = cur.fetchone()[0]
                cur.execute(
                    "SELECT dbops.fn_pgtap_crea_soggetto_pg(%s)::text",
                    [f"{_TERMINE} fornitore"],
                )
                con = cur.fetchone()[0]
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s::uuid, 'FO')", [con])
                righe, _tot = SoggettiRepository().search_ruoli_lookup(
                    q=_TERMINE, tipo_ruolo=None, emittente_ids=None, limit=50,
                    con_ruolo=con_ruolo,
                )
                esito.update(righe=righe, senza=senza, con=con)
                raise Annulla
        except Annulla:
            pass
        return esito["righe"], esito["senza"], esito["con"]

    # 1. Senza filtro: il soggetto senza ruoli c'e', con la riga a ruolo NULL.
    def test_senza_filtro_tiene_la_riga_senza_ruolo(self):
        righe, senza, con = self._cerca(con_ruolo=False)
        per_soggetto = {str(r["soggetto_id"]): r for r in righe}
        self.assertIn(senza, per_soggetto)
        self.assertIsNone(per_soggetto[senza]["soggetto_ruolo_id"])
        self.assertIsNotNone(per_soggetto[con]["soggetto_ruolo_id"])

    # 2. Con `con_ruolo`: la riga «senza ruolo» sparisce, il fornitore resta
    #    (il filtro non restringe il TIPO, come farebbe `tipo_ruolo`).
    def test_con_ruolo_toglie_la_riga_senza_ruolo(self):
        righe, senza, con = self._cerca(con_ruolo=True)
        soggetti = {str(r["soggetto_id"]) for r in righe}
        self.assertNotIn(senza, soggetti)
        self.assertIn(con, soggetti)
        self.assertTrue(all(r["soggetto_ruolo_id"] is not None for r in righe))
