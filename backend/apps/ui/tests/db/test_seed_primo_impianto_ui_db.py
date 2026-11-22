# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le tabelle di catalogo di `ui` sul DATABASE VERO dopo l'iscrizione al
#        seed di primo impianto (brief-db-seed-primo-impianto-non-si-riscrive
#        §16.15, ricadute R-UI1, R-UI2, R-UI-sup): definizioni, colonne e
#        preset nati dal seed portano il segno e i campi del software, non si
#        cancellano, e i campi del software non si cambiano.
# Note: ⭐ Prova la GIUNTURA, che i mock non vedono: la `LEFT JOIN LATERAL`
#       su `dbops.fn_seed_superficie` nelle letture admin, il `text[]` che
#       arriva come lista, il codice del guard che arriva al client col suo
#       campo (409, `fields`) attraverso i service admin senza mappature.
#       ⚠️ Le righe di seed non si nominano per id né per codice: si prendono
#       dalla superficie (`nata_dal_seed`), così il test non dipende dai CSV.
#       ⚠️ Gli elenchi dei campi del software non si ricopiano qui: sono
#       proprio l'elenco che il backend non deve tenere. Si prova che c'è il
#       campo che il guard ferma di sicuro (`codice`).
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Tutto in transazione
#       ANNULLATA; ogni rifiuto atteso in un savepoint.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) SeedPrimoImpiantoUiDbTests.test_la_superficie_nelle_letture_admin
   lista e dettaglio delle tre tabelle: la riga di seed ha `nata_dal_seed` e
   `codice` fra i campi del software; quella creata dal test no, e l'elenco
   e' vuoto (mai NULL).
2) SeedPrimoImpiantoUiDbTests.test_le_righe_di_seed_non_si_cancellano
   R-UI1: il DELETE dei tre service admin su una riga di seed e' 409
   `E_SEED_RIGA_NON_CANCELLABILE`.
3) SeedPrimoImpiantoUiDbTests.test_i_campi_del_software_non_si_cambiano
   R-UI2: il `codice` di una riga di seed e' 409 `E_SEED_COLONNA_DEL_SOFTWARE`
   col campo acceso; un campo dell'installazione (la descrizione del preset)
   si cambia.
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any

from django.db import transaction

from apps.core.services.error_translator import ErrorTranslator
from apps.core.tests.db_e2e import Annulla, apri_transazione_annullata, richiedi_db_provvisto
from apps.ui.db.ui_admin_repository import UiAdminRepository
from apps.ui.services.lista_colonna_admin_service import ListaColonnaAdminService
from apps.ui.services.lista_definizione_admin_service import ListaDefinizioneAdminService
from apps.ui.services.lista_preset_admin_service import ListaPresetAdminService


class SeedPrimoImpiantoUiDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # La sonda e' la sede della superficie: senza, il database e'
        # precedente al §16.15 e questi test non hanno materia.
        richiedi_db_provvisto("dbops.fn_seed_superficie(regclass,text,text[])")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.repo = UiAdminRepository()
        self.def_seed = self._prima_di_seed(self.repo.list_definizioni_admin(), "definizione")
        self.col_seed = self._prima_di_seed(
            self.repo.list_colonne_by_lista_admin(self.def_seed["id"]), "colonna",
        )
        self.preset_seed = self._prima_di_seed(
            [
                p
                for d in self.repo.list_definizioni_admin()
                if d["nata_dal_seed"]
                for p in self.repo.list_preset_by_lista(d["id"])
            ],
            "preset",
        )

    def _prima_di_seed(self, righe: list[dict[str, Any]], cosa: str) -> dict[str, Any]:
        for riga in righe:
            if riga["nata_dal_seed"]:
                return riga
        self.skipTest(f"nessun {cosa} di `ui` nato dal seed su questa installazione")

    # Scopo: il rifiuto atteso dentro un savepoint, letto come lo legge il client.
    def _rifiuto(self, gesto: Callable[[], Any]) -> Any:
        try:
            with transaction.atomic():
                gesto()
        except Exception as exc:  # si esamina la traduzione, qualunque sia
            return ErrorTranslator.to_api_error(exc)
        self.fail("il gesto doveva essere rifiutato")

    def test_la_superficie_nelle_letture_admin(self) -> None:
        lista_id = self.repo.create_definizione({
            "codice": "ui.test_seed_superficie",
            "descrizione": "Lista del test della superficie",
            "schema_dati": "ui",
            "vista_sql": None,
            "attivo": False,
        })
        colonna_id = self.repo.create_colonna({
            "lista_id": lista_id,
            "codice": "seed_sup_info",
            "etichetta": "Info",
            "tipo_colonna": "informazione",
            "tipo_dato": "string",
            "ordine_default": 1,
            # Spenta: la definizione del test e' spenta, e una colonna accesa
            # sotto una lista spenta la rifiuta il DB (child_requires_active_parent).
            "attivo": False,
            # Senza campo sorgente non si esporta (U25, giro 4 di brief-db-revisione-ui).
            "esportabile": False,
        })
        preset_id = self.repo.create_preset({
            "lista_id": lista_id,
            "codice": "seed_sup_sistema",
            "descrizione": "Preset del test",
            "ambito": "sistema",
        })

        dettagli = {
            "definizione": (
                self.repo.get_definizione_admin(self.def_seed["id"]),
                self.repo.get_definizione_admin(lista_id),
            ),
            "colonna": (
                self.repo.get_colonna_admin(self.col_seed["id"]),
                self.repo.get_colonna_admin(colonna_id),
            ),
            "preset": (
                self.repo.get_preset(self.preset_seed["id"]),
                self.repo.get_preset(preset_id),
            ),
        }
        for cosa, (seed, mia) in dettagli.items():
            with self.subTest(cosa=cosa):
                assert seed is not None and mia is not None
                self.assertIs(seed["nata_dal_seed"], True)
                self.assertIsInstance(seed["campi_del_software"], list)
                self.assertIn("codice", seed["campi_del_software"])
                self.assertIs(mia["nata_dal_seed"], False)
                self.assertEqual(mia["campi_del_software"], [])

        # Le liste portano la stessa superficie del dettaglio.
        liste = {
            "definizione": ({r["id"]: r for r in self.repo.list_definizioni_admin()}, lista_id),
            "colonna": ({r["id"]: r for r in self.repo.list_colonne_by_lista_admin(lista_id)}, colonna_id),
            "preset": ({r["id"]: r for r in self.repo.list_preset_by_lista(lista_id)}, preset_id),
        }
        for cosa, (per_id, mio_id) in liste.items():
            with self.subTest(lista=cosa):
                self.assertIs(per_id[mio_id]["nata_dal_seed"], False)
                self.assertEqual(per_id[mio_id]["campi_del_software"], [])
        self.assertEqual(
            {r["id"]: r for r in self.repo.list_definizioni_admin()}[self.def_seed["id"]]["campi_del_software"],
            dettagli["definizione"][0]["campi_del_software"],
        )

    def test_le_righe_di_seed_non_si_cancellano(self) -> None:
        gesti = {
            "definizione": lambda: ListaDefinizioneAdminService().delete_definizione(self.def_seed["id"]),
            "colonna": lambda: ListaColonnaAdminService().delete_colonna(self.col_seed["id"]),
            "preset": lambda: ListaPresetAdminService().delete_preset(self.preset_seed["id"]),
        }
        for cosa, gesto in gesti.items():
            with self.subTest(cosa=cosa):
                errore = self._rifiuto(gesto)
                self.assertEqual(errore.code, "E_SEED_RIGA_NON_CANCELLABILE")
                self.assertEqual(ErrorTranslator.get_http_status(errore), 409)

    def test_i_campi_del_software_non_si_cambiano(self) -> None:
        gesti = {
            # ⚠️ Dal giro 4 di brief-db-revisione-ui (BE12) il `codice` di
            #    definizione e colonna non e' piu' nel PATCH: il gesto del seed
            #    si prova su un altro campo del software.
            "definizione": lambda: ListaDefinizioneAdminService().update_definizione(
                self.def_seed["id"], {"descrizione": "Rinominata dall'installazione"},
            ),
            "colonna": lambda: ListaColonnaAdminService().update_colonna(
                self.col_seed["id"], {"formato": "test_seed_formato"},
            ),
            "preset": lambda: ListaPresetAdminService().update_preset(
                self.preset_seed["id"], {"codice": "test_seed_rinomina"},
            ),
        }
        campo_del_software = {"definizione": "descrizione", "colonna": "formato", "preset": "codice"}
        campo_del_software = {"definizione": "descrizione", "colonna": "formato", "preset": "codice"}
        for cosa, gesto in gesti.items():
            with self.subTest(cosa=cosa):
                errore = self._rifiuto(gesto)
                self.assertEqual(errore.code, "E_SEED_COLONNA_DEL_SOFTWARE")
                self.assertEqual(ErrorTranslator.get_http_status(errore), 409)
                self.assertIn(campo_del_software[cosa], errore.fields)

        # Un campo dell'installazione su una riga di seed si cambia.
        try:
            with transaction.atomic():
                ListaPresetAdminService().update_preset(
                    self.preset_seed["id"], {"descrizione": "Descritta dall'installazione"},
                )
                preset = self.repo.get_preset(self.preset_seed["id"])
                assert preset is not None
                self.assertEqual(preset["descrizione"], "Descritta dall'installazione")
                raise Annulla
        except Annulla:
            pass
