# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I CAMPI FERMI PER MODELLO sulle righe admin di `ui`, sul DATABASE
#        PROVVISTO (`/verifica` di brief-db-revisione-ui, BE12): lista e
#        dettaglio di definizioni, colonne e preset portano
#        `non_editable_fields`, letto da `dbops.fn_non_editable_fields` nella
#        SELECT (`_sql_campi_bloccati`). Il FE ne spegne i campi e li toglie dal
#        PATCH (BB `campoFermo`), al posto del `campo === 'codice'` cablato.
# Note: ⭐ La giuntura, non la regola: quali colonne il DB blocca lo dicono i
#       suoi trigger di lock. Qui si prova che arrivano, come lista, in tutte e
#       sei le letture, e che c'e' il campo che il lucchetto ferma di sicuro
#       (il `codice`, `E_UI_*_CODICE_IMMUTABILE`; il `lista_id` del posto del
#       preset). L'elenco intero non si ricopia: e' proprio cio' che il
#       backend non deve tenere. Righe COSTRUITE, transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) CampiFermiRigheAdminDbTests.test_definizione_lista_e_dettaglio
2) CampiFermiRigheAdminDbTests.test_colonna_lista_e_dettaglio
3) CampiFermiRigheAdminDbTests.test_preset_lista_e_dettaglio
"""
from __future__ import annotations

import unittest
from typing import Any

from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.ui.db.ui_admin_repository import UiAdminRepository
from apps.ui.services.lista_colonna_admin_service import ListaColonnaAdminService
from apps.ui.services.lista_definizione_admin_service import ListaDefinizioneAdminService
from apps.ui.services.lista_preset_admin_service import ListaPresetAdminService

_LISTA = "ui.test_campi_fermi"


def _riga(righe: list[dict[str, Any]], record_id: int) -> dict[str, Any]:
    return next(r for r in righe if r["id"] == record_id)


class CampiFermiRigheAdminDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("dbops.fn_non_editable_fields(text,text,text)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        repo = UiAdminRepository()
        self.lista_id = repo.create_definizione({
            "codice": _LISTA,
            "descrizione": "Campi fermi delle righe admin",
            "schema_dati": "ui",
            "vista_sql": None,
            "attivo": True,
        })
        self.colonna_id = repo.create_colonna({
            "lista_id": self.lista_id,
            "codice": "fermi_info",
            "etichetta": "Info",
            "campo_sorgente": "info",
            "tipo_colonna": "informazione",
            "tipo_dato": "string",
            "ordine_default": 1,
            "attivo": True,
        })
        self.preset_id = repo.create_preset({
            "lista_id": self.lista_id,
            "codice": "fermi_sistema",
            "descrizione": "Preset di sistema",
            "ambito": "sistema",
            "attivo": True,
        })

    # Due letture, un contratto: la riga della lista (da cui parte il drawer) e
    # il dettaglio (che il drawer riceve dopo il salvataggio).
    def _assert_fermo(self, righe: tuple[dict[str, Any], ...], campo: str) -> None:
        for riga in righe:
            fermi = riga["non_editable_fields"]
            self.assertIsInstance(fermi, list)
            self.assertIn(campo, fermi)

    def test_definizione_lista_e_dettaglio(self) -> None:
        service = ListaDefinizioneAdminService()
        self._assert_fermo((
            _riga(service.list_definizioni_admin()["results"], self.lista_id),
            service.get_definizione(self.lista_id),
        ), "codice")

    def test_colonna_lista_e_dettaglio(self) -> None:
        service = ListaColonnaAdminService()
        self._assert_fermo((
            _riga(service.list_colonne_admin(self.lista_id)["results"], self.colonna_id),
            service.get_colonna(self.colonna_id),
        ), "codice")

    def test_preset_lista_e_dettaglio(self) -> None:
        service = ListaPresetAdminService()
        self._assert_fermo((
            _riga(service.list_preset(self.lista_id)["results"], self.preset_id),
            service.get_preset(self.preset_id),
        ), "lista_id")
