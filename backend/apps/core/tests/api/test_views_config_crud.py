# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Le view del pannello «Gestione tabelle» chiedono il permesso
#        sull'OGGETTO a cui appartiene la tabella della rotta, non sull'area
#        del pannello (D-3 §7.1 del brief del modello, D-5; brief-db-pannello-
#        config-verbo-generico §6). La view DICHIARA l'oggetto
#        (`oggetto_permesso_da_richiesta`), la catena di `ZeroERPPermission`
#        lo applica (D-P7). Lista e resolver mockati: CI-safe.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) OggettoDallaRottaTests.test_rel_del_pannello_dichiara_l_oggetto_della_lista
2) OggettoDallaRottaTests.test_rel_fuori_pannello_non_ha_oggetto
3) OggettoDallaRottaTests.test_ogni_view_con_rel_usa_il_mixin
4) CatenaSullOggettoTests.test_il_livello_si_chiede_sull_oggetto_e_sulla_sua_area
5) CatenaSullOggettoTests.test_tutto_su_config_non_scrive_le_causali
6) CatenaSullOggettoTests.test_senza_oggetto_resta_l_area_della_classe
7) CatenaSullOggettoTests.test_sulla_sola_classe_nega
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.api import views_config_crud as mod
from apps.core.api.permissions import MotivoDiniego, ZeroERPPermission
from apps.core.api.views_config_crud import (
    ConfigTableMetadataView,
    ConfigTableRecordDetailView,
    ConfigTableRecordsView,
    ConfigTablesListView,
)
from apps.core.services.auth_constants import RUOLO_APPLICATIVO_OPERATORE
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova

_VOCE = "apps.core.api.views_config_crud.TabelleGestibiliRepository.voce"


def _voce(rel: str, app_label: str, model_name: str, *, pannello: bool = True) -> dict:
    schema, table = rel.split(".", 1)
    return {"rel": rel, "schema": schema, "table": table, "app_label": app_label,
            "model_name": model_name, "lookup": True, "pannello": pannello}


# Scopo: il resolver come lo vede la catena: operatore, non super admin,
#        TUTTO su config e LETTURA su ogni altro oggetto.
def _resolver() -> MagicMock:
    mock = patch("apps.core.api.permissions.PermissionResolver").start()
    mock.get_ruolo_applicativo.return_value = RUOLO_APPLICATIVO_OPERATORE
    mock.is_super_admin.return_value = False
    mock.get_area_schema_db.side_effect = lambda app_label, _model: app_label
    mock.get_livello_area.side_effect = (
        lambda _user, area, cache=None: "TUTTO" if area == "config" else "LETTURA"
    )
    mock.get_livello_oggetto.side_effect = (
        lambda _user, _app, _model, area, cache=None: "TUTTO" if area == "config" else "LETTURA"
    )
    return mock


def _view(classe: type, rel: str) -> object:
    view = classe()
    view.kwargs = {"rel": rel, "pk": 1}
    return view


class OggettoDallaRottaTests(SimpleTestCase):

    # 1. L'oggetto si legge dalla lista, non si ricava dal nome: la chiave puo'
    #    non essere la convenzione (vendite.listini e' ('vendite', 'listino')).
    @patch(_VOCE, return_value=_voce("vendite.listini", "vendite", "listino"), autospec=True)
    def test_rel_del_pannello_dichiara_l_oggetto_della_lista(self, _voce_m) -> None:
        view = _view(ConfigTableRecordsView, "vendite.listini")
        self.assertEqual(view.oggetto_permesso_da_richiesta(), ("vendite", "listino"))

    # 2. Fuori pannello (assente, o solo lookup): nessun oggetto; la rel la
    #    rifiuta poi il service con 400.
    def test_rel_fuori_pannello_non_ha_oggetto(self) -> None:
        for voce in (None, _voce("pagamenti.enti_incasso", "pagamenti", "enti_incasso", pannello=False)):
            with self.subTest(voce=voce), patch(_VOCE, return_value=voce, autospec=True):
                view = _view(ConfigTableRecordDetailView, "x.y")
                self.assertIsNone(view.oggetto_permesso_da_richiesta())

    # 3. Ogni view che nomina una tabella dichiara l'oggetto; l'elenco delle
    #    tabelle (senza rel) resta sull'area del pannello.
    def test_ogni_view_con_rel_usa_il_mixin(self) -> None:
        for view in (ConfigTableMetadataView, ConfigTableRecordsView, ConfigTableRecordDetailView):
            self.assertTrue(issubclass(view, mod._PermessoSullOggettoMixin), view.__name__)
        self.assertFalse(issubclass(ConfigTablesListView, mod._PermessoSullOggettoMixin))


class CatenaSullOggettoTests(SimpleTestCase):

    def tearDown(self) -> None:
        patch.stopall()

    # 4. La catena chiede il livello sull'oggetto dichiarato, con l'area che
    #    ne dice il resolver (fn_area_di_oggetto) — non sull'area della classe.
    @patch(_VOCE, return_value=_voce("magazzino.causali", "magazzino", "causali"), autospec=True)
    def test_il_livello_si_chiede_sull_oggetto_e_sulla_sua_area(self, _voce_m) -> None:
        resolver = _resolver()
        esito = ZeroERPPermission.valuta(
            operatore_di_prova(user_id=3), _view(ConfigTableRecordsView, "magazzino.causali"),
            method="GET", cache={},
        )
        self.assertTrue(esito.consentito)
        resolver.get_area_schema_db.assert_called_once_with("magazzino", "causali")
        args = resolver.get_livello_oggetto.call_args.args
        self.assertEqual(args[1:], ("magazzino", "causali", "magazzino"))
        resolver.get_livello_area.assert_not_called()

    # 5. Il caso del §7.1 del brief del modello: TUTTO su Configurazione e
    #    LETTURA su Magazzino. Si leggono le causali, non si scrivono — in
    #    creazione e in modifica.
    @patch(_VOCE, return_value=_voce("magazzino.causali", "magazzino", "causali"), autospec=True)
    def test_tutto_su_config_non_scrive_le_causali(self, _voce_m) -> None:
        _resolver()
        for classe, metodo in (
            (ConfigTableRecordsView, "POST"),
            (ConfigTableRecordDetailView, "PATCH"),
        ):
            with self.subTest(metodo=metodo):
                esito = ZeroERPPermission.valuta(
                    operatore_di_prova(user_id=3), _view(classe, "magazzino.causali"), method=metodo, cache={},
                )
                self.assertFalse(esito.consentito)
                self.assertIs(esito.motivo, MotivoDiniego.LIVELLO_INSUFFICIENTE)
                self.assertEqual(esito.area, "magazzino")

    # 6. Una rel senza oggetto (fuori pannello) resta sull'area della classe:
    #    l'ingresso lo decide «config», il rifiuto lo da' il service.
    @patch(_VOCE, return_value=None, autospec=True)
    def test_senza_oggetto_resta_l_area_della_classe(self, _voce_m) -> None:
        resolver = _resolver()
        esito = ZeroERPPermission.valuta(
            operatore_di_prova(user_id=3), _view(ConfigTableRecordsView, "x.y"), method="POST", cache={},
        )
        self.assertTrue(esito.consentito)
        self.assertEqual(resolver.get_livello_area.call_args.args[1], "config")
        resolver.get_livello_oggetto.assert_not_called()

    # 7. Sulla sola classe (i tool dell'assistente) non c'e' la richiesta, e
    #    l'area della classe non e' quella dell'oggetto: si nega, senza
    #    nemmeno leggere la lista.
    @patch(_VOCE, autospec=True)
    def test_sulla_sola_classe_nega(self, voce_m) -> None:
        _resolver()
        for classe in (ConfigTableMetadataView, ConfigTableRecordsView, ConfigTableRecordDetailView):
            with self.subTest(view=classe.__name__):
                esito = ZeroERPPermission.valuta(operatore_di_prova(user_id=3), classe, method="GET", cache={})
                self.assertFalse(esito.consentito)
                self.assertIs(esito.motivo, MotivoDiniego.OGGETTO_SENZA_RICHIESTA)
        voce_m.assert_not_called()
