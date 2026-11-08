# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: la LISTA delle righe di una fattura (`GET fatture/<id>/righe/lista/`
#        e `…/export/`, lista `vendite.fattura_righe`) e il suo service
#        (brief-db-liste-righe-documento, lotto C). Mock di repository,
#        cancello e UI: nessun accesso DB (CI-compatible).
# ------------------------------------------------------------

"""⛔ PERCHE' QUESTO FILE ESISTE.

Le view nascono dalla stessa factory dei quattro documenti gemelli, ma la
fattura ne usa un ramo che loro non usano: lo scope dell'operatore passato al
service (`con_scope`), perche' la testata si legge col filtro applicativo come
nel dettaglio. E il service legge PRIMA la testata: una fattura fuori scope e'
un 404, non una lista vuota — la vista e' `security_invoker` e risponderebbe
zero righe, cioe' «questa fattura non ha righe».

Indice test:

 1) test_lista_pagina_con_lo_scope_dell_operatore
 2) test_lista_ed_export_col_cancello_della_fattura
 3) test_export_alza_il_tetto_e_porta_lo_scope
 4) test_lista_ed_export_col_permesso_della_fattura
 5) test_service_fuori_scope_404_senza_leggere_le_righe
 6) test_service_legge_la_pagina_dopo_la_testata
"""

from unittest import TestCase
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import Client
from django.urls import resolve

from apps.core.services.service_errors import ServiceError
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.ui.tests._coda_export import coda_export_finta
from apps.vendite.services.vendite_service import list_fattura_righe_pagina

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_GUARD = "apps.core.services.perimetro_emittente.guard_lista_per_codice"
_PAGINA = "apps.vendite.services.vendite_service.list_fattura_righe_pagina"
_BASE = "/api/v1/vendite/fatture/835/righe/lista/"
# ⚠️ Lo scope si sostituisce qui e non con un utente non-superuser: quello
#    farebbe interrogare il DB ai permessi. Si prova che la view lo PASSA.
_SCOPE = "apps.ui.api.lista_figlia_views.get_scope_user_id"


class TestFatturaRigheListaApi(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        cache.clear()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE, return_value=42)
    @patch(_PAGINA)
    def test_lista_pagina_con_lo_scope_dell_operatore(self, pagina, _scope, _auth) -> None:
        pagina.return_value = ([{"riga_key": "R:1"}], 3)
        resp = self.client.get(f"{_BASE}?search=canone&order_by=importo_riga&order_dir=desc&limit=10")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["count"], 3)
        pagina.assert_called_once_with(
            835, search="canone", order_by="importo_riga", order_dir="desc",
            limit=10, offset=0, auth_user_id=42,
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE, return_value=42)
    def test_lista_ed_export_col_cancello_della_fattura(self, _scope, _auth) -> None:
        for suffisso in ("", "export/"):
            cache.clear()
            with self.subTest(export=bool(suffisso)), patch(_GUARD) as guard, \
                    patch(_PAGINA, return_value=([], 0)), coda_export_finta():
                resp = self.client.get(f"{_BASE}{suffisso}?emittente_fiscale_id=3")
                self.assertEqual(resp.status_code, 200)
                guard.assert_called_once()
                self.assertEqual(guard.call_args.kwargs["lista_codice"], "vendite.fattura_righe")
                self.assertEqual(guard.call_args.kwargs["emittente_esplicito"], 3)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SCOPE, return_value=42)
    @patch(_PAGINA)
    def test_export_alza_il_tetto_e_porta_lo_scope(self, pagina, _scope, _auth) -> None:
        pagina.return_value = ([{"riga_key": "R:1"}], 1)
        with coda_export_finta("righe.csv"):
            resp = self.client.get(f"{_BASE}export/?formato=csv")
        self.assertEqual(resp.status_code, 200)
        kwargs = pagina.call_args.kwargs
        self.assertEqual((kwargs["limit"], kwargs["max_limit"]), (EXPORT_MAX_ROWS + 1, EXPORT_MAX_ROWS + 1))
        self.assertEqual(kwargs["auth_user_id"], 42)

    def test_lista_ed_export_col_permesso_della_fattura(self) -> None:
        for suffisso in ("", "export/"):
            with self.subTest(export=bool(suffisso)):
                view = resolve(f"{_BASE}{suffisso}").func.view_class
                self.assertEqual(view.model_permission, ("vendite", "fattura"))


class FatturaRighePaginaServiceTests(TestCase):

    @patch("apps.vendite.services.vendite_service.FattureRepository", autospec=True)
    @patch("apps.vendite.services.vendite_service.VenditeRepository", autospec=True)
    def test_service_fuori_scope_404_senza_leggere_le_righe(self, venditore, fatture) -> None:
        venditore.return_value.get_fattura_testata.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            list_fattura_righe_pagina(835, auth_user_id=42, limit=10)
        self.assertEqual(ctx.exception.code, "E_FATTURA_NON_TROVATA")
        venditore.return_value.get_fattura_testata.assert_called_once_with(835, auth_user_id=42)
        fatture.return_value.list_righe_pagina.assert_not_called()

    @patch("apps.vendite.services.vendite_service.FattureRepository", autospec=True)
    @patch("apps.vendite.services.vendite_service.VenditeRepository", autospec=True)
    def test_service_legge_la_pagina_dopo_la_testata(self, venditore, fatture) -> None:
        venditore.return_value.get_fattura_testata.return_value = {"id": 835}
        fatture.return_value.list_righe_pagina.return_value = ([], 0)
        list_fattura_righe_pagina(835, search="x", limit=10, offset=20)
        fatture.return_value.list_righe_pagina.assert_called_once()
        args, kwargs = fatture.return_value.list_righe_pagina.call_args
        self.assertEqual(args, (835,))
        self.assertEqual((kwargs["search"], kwargs["limit"], kwargs["offset"]), ("x", 10, 20))
