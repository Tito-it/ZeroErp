# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La cancellazione di una colonna di lista che sta in un preset, sul
#        DATABASE VERO (BE4 di brief-db-revisione-ui, Q18 decisa da Tid il
#        2026-11-19): la FK `fk_lista_preset_colonna_lista_colonna` e' NO
#        ACTION, e il service rifiuta con E_UI_COLONNA_IN_USO nominando i
#        preset, sia dal controllo preventivo sia dalla FK. Dal giro 2b
#        (U14, 2026-11-21) le FK dei preset verso la colonna sono due, la
#        sola colonna e la composita (colonna, lista): la mappa le porta
#        tutte e due, e la composita rifiuta anche una colonna di un'altra
#        lista nella composizione.
# Note: ⭐ Prova la GIUNTURA che i mock non vedono: la query dei preset che
#       compongono la colonna, e il testo dell'IntegrityError di PostgreSQL che
#       la mappa `fk_constraints` deve riconoscere per nome.
#       ⚠️ Lista, colonna e preset li costruisce il test: nessuna riga di seed,
#       nessun id cablato. Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
#       Tutto in transazione ANNULLATA; ogni rifiuto atteso in un savepoint.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) CancellazioneColonnaDbTests.test_colonna_in_un_preset_rifiutata_coi_codici
   il controllo preventivo: 409 E_UI_COLONNA_IN_USO, il messaggio nomina il
   preset; la colonna resta.
2) CancellazioneColonnaDbTests.test_la_fk_dei_preset_ha_lo_stesso_rifiuto
   il controllo preventivo saltato (il preset nato in mezzo): la FK NO ACTION
   ferma il DELETE e arriva lo stesso codice, non il ripiego generico.
3) CancellazioneColonnaDbTests.test_colonna_fuori_dai_preset_si_cancella
   tolta dal preset, la colonna si cancella: il preset vuoto non la ferma.
4) CancellazioneColonnaDbTests.test_colonna_di_un_altra_lista_fuori_dal_preset
   l'altro lato della stessa FK composita (giro 2b, U14): una colonna di
   un'altra lista non entra nel preset; 400 E_UI_PRESET_VALIDAZIONE col campo
   `colonne`, non il ripiego generico.
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

from django.db import connection, transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.ui.db.ui_admin_repository import UiAdminRepository
from apps.ui.services.lista_colonna_admin_service import (
    E_COLONNA_IN_USE,
    ListaColonnaAdminService,
)
from apps.ui.services.lista_preset_admin_service import (
    E_PRESET_VALIDATION,
    ListaPresetAdminService,
)


class CancellazioneColonnaDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.repo = UiAdminRepository()
        lista_id = self.repo.create_definizione({
            "codice": "ui.test_cancella_colonna",
            "descrizione": "Lista del test della cancellazione di colonna",
            "schema_dati": "ui",
            "vista_sql": None,
            "attivo": False,
        })
        # Spenta: sotto una lista spenta una colonna accesa la rifiuta il DB.
        self.colonna_id = self.repo.create_colonna({
            "lista_id": lista_id,
            "codice": "test_canc_info",
            "etichetta": "Info",
            "tipo_colonna": "informazione",
            "tipo_dato": "string",
            "ordine_default": 1,
            "attivo": False,
            # Senza campo sorgente non si esporta (U25, giro 4 di brief-db-revisione-ui).
            "esportabile": False,
        })
        preset_id = self.repo.create_preset({
            "lista_id": lista_id,
            "codice": "test_canc_sistema",
            "descrizione": "Preset del test",
            "ambito": "sistema",
        })
        self.preset_id = preset_id
        self.repo.replace_preset_colonne(
            preset_id, [{"colonna_id": self.colonna_id, "ordine": 1}],
        )
        self.svc = ListaColonnaAdminService()

    # Scopo: il rifiuto atteso dentro un savepoint, letto come lo legge il client.
    def _rifiuto(self, gesto: Callable[[], Any]) -> Any:
        try:
            with transaction.atomic():
                gesto()
        except Exception as exc:  # si esamina la traduzione, qualunque sia
            return ErrorTranslator.to_api_error(exc)
        self.fail("il gesto doveva essere rifiutato")

    def _colonna_esiste(self) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM ui.lista_colonna WHERE id = %s", [self.colonna_id],
            )
            return cursor.fetchone() is not None

    def test_colonna_in_un_preset_rifiutata_coi_codici(self) -> None:
        self.assertEqual(
            self.repo.preset_con_colonna(self.colonna_id), ["test_canc_sistema"],
        )
        errore = self._rifiuto(lambda: self.svc.delete_colonna(self.colonna_id))
        self.assertEqual(errore.code, E_COLONNA_IN_USE)
        self.assertEqual(ErrorTranslator.get_http_status(errore), 409)
        self.assertIn("test_canc_sistema", errore.message)
        self.assertTrue(self._colonna_esiste())

    def test_la_fk_dei_preset_ha_lo_stesso_rifiuto(self) -> None:
        with patch.object(
            UiAdminRepository, "preset_con_colonna", autospec=True, return_value=[],
        ):
            errore = self._rifiuto(lambda: self.svc.delete_colonna(self.colonna_id))
        self.assertEqual(errore.code, E_COLONNA_IN_USE)
        self.assertEqual(ErrorTranslator.get_http_status(errore), 409)
        self.assertIn("preset", errore.message)
        self.assertTrue(self._colonna_esiste())

    def test_colonna_fuori_dai_preset_si_cancella(self) -> None:
        self.repo.replace_preset_colonne(self.preset_id, [])
        esito = self.svc.delete_colonna(self.colonna_id)
        self.assertEqual(esito, {"deleted": True, "id": self.colonna_id})
        self.assertFalse(self._colonna_esiste())

    def test_colonna_di_un_altra_lista_fuori_dal_preset(self) -> None:
        altra_lista_id = self.repo.create_definizione({
            "codice": "ui.test_cancella_colonna_altra",
            "descrizione": "L'altra lista del test",
            "schema_dati": "ui",
            "vista_sql": None,
            "attivo": False,
        })
        altra_colonna_id = self.repo.create_colonna({
            "lista_id": altra_lista_id,
            "codice": "test_canc_altra",
            "etichetta": "Altra",
            "tipo_colonna": "informazione",
            "tipo_dato": "string",
            "ordine_default": 1,
            "attivo": False,
            # Senza campo sorgente non si esporta (U25, giro 4 di brief-db-revisione-ui).
            "esportabile": False,
        })
        errore = self._rifiuto(lambda: ListaPresetAdminService().replace_preset_colonne(
            self.preset_id, {"colonne": [{"colonna_id": altra_colonna_id, "ordine": 1}]},
        ))
        self.assertEqual(errore.code, E_PRESET_VALIDATION)
        self.assertEqual(ErrorTranslator.get_http_status(errore), 400)
        self.assertIn("della lista del preset", errore.message)
        self.assertEqual(errore.fields, ("colonne",))
