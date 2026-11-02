# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le misure «righe per pagina» sul DATABASE PROVVISTO
#        (brief-db-misure-pagina-catalogo §6): la lettura unica per
#        l'applicazione e il rifiuto di una misura fuori catalogo, da ENTRAMBI
#        i punti che la scrivono (preset e preferenza utente).
# Note: ⭐ La giuntura, non la regola. La regola la provano i pgTAP
#       (`ui/test-misure-pagina-v1`); qui si prova il TRASPORTO: il 2026-09-30
#       i due tetti del backend (`MAX_LIMIT`, `_MAX_PAGINA_DIMENSIONE`) sono
#       stati ritirati, e al loro posto l'operatore deve ricevere il rifiuto
#       del DB — codice `E_UI_MISURA_PAGINA_NON_AMMESSA`, status 400 — passando
#       da `ErrorTranslator.to_api_error`, lo stesso punto del middleware.
#       ⚠️ La misura rifiutata si COSTRUISCE dal catalogo (la massima + 1),
#       non si scrive: un numero fisso smetterebbe di essere «fuori» il giorno
#       in cui il CSV lo aggiunge. Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) MisurePaginaDbTests.test_la_lettura_lega_e_i_default_sono_misure_ammesse
2) MisurePaginaDbTests.test_preset_con_misura_fuori_catalogo_400
3) MisurePaginaDbTests.test_preferenza_con_misura_fuori_catalogo_400
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto
from apps.ui.db.ui_repository import UiRepository
from apps.ui.services.lista_preset_admin_service import ListaPresetAdminService

_CODICE = "E_UI_MISURA_PAGINA_NON_AMMESSA"


class MisurePaginaDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def _fuori_catalogo(self) -> int:
        with connection.cursor() as cur:
            cur.execute("SELECT max(misura) + 1 FROM ui.misure_pagina")
            riga = cur.fetchone()
        assert riga is not None and riga[0] is not None, "catalogo misure vuoto"
        return int(riga[0])

    def _rifiuto(self, esegui) -> None:
        with self.assertRaises(Annulla):
            with transaction.atomic():
                with self.assertRaises(Exception) as ctx:
                    with transaction.atomic():
                        esegui()
                api_error = ErrorTranslator.to_api_error(ctx.exception)
                self.assertEqual(api_error.code, _CODICE)
                self.assertEqual(ErrorTranslator.get_http_status(api_error), 400)
                raise Annulla

    def test_la_lettura_lega_e_i_default_sono_misure_ammesse(self) -> None:
        esito = UiRepository().get_misure_pagina()
        misure = esito["misure"]
        self.assertTrue(misure, "nessuna misura a catalogo")
        self.assertTrue(all(isinstance(m, int) for m in misure))
        self.assertEqual(misure, sorted(misure))
        self.assertIn(esito["default_compatta"], misure)
        self.assertIn(esito["default_pagina"], misure)

    def test_preset_con_misura_fuori_catalogo_400(self) -> None:
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM ui.lista_preset ORDER BY id LIMIT 1")
            riga = cur.fetchone()
        if riga is None:
            self.skipTest("nessun ui.lista_preset di seed su cui appoggiare l'UPDATE")
        preset_id = int(riga[0])
        misura = self._fuori_catalogo()
        self._rifiuto(
            lambda: ListaPresetAdminService().update_preset(
                None, preset_id, {"pagina_dimensione": misura},
            )
        )

    def test_preferenza_con_misura_fuori_catalogo_400(self) -> None:
        misura = self._fuori_catalogo()

        def esegui() -> None:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT m.auth_user_id FROM dbops.fn_pgtap_crea_emittente_operatore() m"
                )
                uid = int(cur.fetchone()[0])
                cur.execute("SELECT id FROM ui.lista_definizione ORDER BY id LIMIT 1")
                lista = cur.fetchone()
            assert lista is not None, "nessuna ui.lista_definizione di seed"
            UiRepository().upsert_preferenza(
                auth_user_id=uid,
                lista_id=int(lista[0]),
                configurazione={"pagina_dimensione": misura},
                preset_base_id=None,
                preset_base_data_update=None,
            )

        self._rifiuto(esegui)
