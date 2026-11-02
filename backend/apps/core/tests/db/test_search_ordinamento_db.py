# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le colonne ordinabili della ricerca universale: il mirror del backend
#        (`search_validators.ALLOWED_ORDER_COLUMNS`) e la whitelist di
#        `p_order_by` in `script.fn_search_soggetti_universale` dicono la
#        STESSA cosa, sul database vero.
# Note: ⭐ Nasce il 2026-10-10 (brief-db-ricerca-universale-tetto-10000 §7.3):
#       il DB aveva tolto `utility_list` dalle colonne ordinabili e il mirror
#       lo lasciava passare — il 400 educato diventava un rifiuto del DB con un
#       codice di debito. Due copie della stessa regola divergono in silenzio,
#       e questo e' il presidio della seconda.
#       ⭐ Si prova nei due versi: ogni colonna del mirror la accetta il DB, e
#       una colonna che il DB rifiuta il mirror non la ammette.
#       ⚠️ Il whitelist si controlla prima di leggere: le chiamate tornano
#       zero righe (nessun contesto operatore, la RLS) e va bene, qui conta
#       solo se la funzione SOLLEVA.
#       ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) SearchOrdinamentoDbTests.test_ogni_colonna_del_mirror_la_accetta_il_db
2) SearchOrdinamentoDbTests.test_le_colonne_che_il_db_rifiuta_non_sono_nel_mirror
"""
from __future__ import annotations

import unittest

from django.db import DatabaseError, connection, transaction

from apps.core.api.search_validators import ALLOWED_ORDER_COLUMNS
from apps.core.db.search_repository import SearchRepository
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto

# Colonne che il DB rifiuta e che un client potrebbe chiedere: le altre colonne
# che la funzione restituisce, ma su cui non si ordina.
# ⭐ `utility_list` ed `emittente_ragione_sociale` sono aggregati della sola
#    pagina (D-2): ordinarci sopra vorrebbe dire aggregare tutte le
#    corrispondenze.
_RIFIUTATE_DAL_DB = ("utility_list", "emittente_ragione_sociale")


class SearchOrdinamentoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        # ⚠️ Il ruolo cliente: e' quello per cui la colonna `utility_list` c'e'.
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM config.tipi_ruoli WHERE codice_interno = 'CL'")
            riga = cur.fetchone()
        self.assertIsNotNone(riga, "tipo ruolo CL assente dal catalogo")
        assert riga is not None
        self.tipo_ruolo_id = riga[0]

    # Scopo: True se la funzione accetta l'ordinamento, False se lo rifiuta.
    # ⚠️ Savepoint per chiamata: un rifiuto annulla la transazione, e le
    #    chiamate dopo fallirebbero tutte per quel motivo.
    def _db_accetta(self, colonna: str) -> bool:
        try:
            with transaction.atomic():
                SearchRepository().search_soggetti(
                    search_term="zzz-ordinamento", tipo_ruolo_id=self.tipo_ruolo_id,
                    order_by=colonna, order_dir="ASC",
                )
        except DatabaseError:
            return False
        return True

    def test_ogni_colonna_del_mirror_la_accetta_il_db(self) -> None:
        self.assertEqual(
            sorted(c for c in ALLOWED_ORDER_COLUMNS if not self._db_accetta(c)), [],
            "colonne ammesse dal backend che il DB rifiuta: il client riceve il "
            "codice di debito E_PARAMETRO_INVALIDO invece del 400 E_SEARCH_VALIDATION",
        )

    def test_le_colonne_che_il_db_rifiuta_non_sono_nel_mirror(self) -> None:
        for colonna in _RIFIUTATE_DAL_DB:
            with self.subTest(colonna=colonna):
                # ⭐ Prima si prova che il DB la rifiuta davvero: altrimenti il
                #    test passerebbe su una colonna che nel frattempo e'
                #    diventata ordinabile, e il mirror resterebbe indietro.
                self.assertFalse(self._db_accetta(colonna))
                self.assertNotIn(colonna, ALLOWED_ORDER_COLUMNS)
