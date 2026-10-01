# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: la LISTA delle righe di un contratto (`GET contratti/<id>/righe/lista/`
#        e `…/export/`, lista `vendite.contratto_righe`) e il suo service
#        (brief-db-liste-righe-documento, lotto D). Mock di repository,
#        cancello e UI: nessun accesso DB (CI-compatible).
# ------------------------------------------------------------

"""⛔ PERCHE' QUESTO FILE ESISTE.

Le view nascono dalla factory dei documenti gemelli, e sbagliarne un parametro
non da' errore: un kwarg del padre sbagliato arriva al service come `None`, un
nome sbagliato del parametro emittente lascia chi vede piu' emittenti davanti a
`E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` a drawer aperto. E il service legge PRIMA
la testata: la funzione su un contratto che l'operatore non vede risponde zero
righe, cioe' «questo contratto non ha righe» invece di «non lo vedi».

Indice test:

 1) test_lista_pagina_col_contratto_del_percorso
 2) test_lista_ed_export_col_cancello_del_contratto
 3) test_export_alza_il_tetto
 4) test_lista_ed_export_col_permesso_del_contratto
 5) test_la_risorsa_righe_resta_senza_cancello_di_lista
 6) test_service_fuori_perimetro_404_senza_leggere_le_righe
 7) test_service_legge_la_pagina_dopo_la_testata
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
from apps.vendite.services.contratti_service import ContrattiService

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_GUARD = "apps.core.services.perimetro_emittente.guard_lista_per_codice"
_SERVICE = "apps.vendite.api.views_contratti.ContrattiService"
_BASE = "/api/v1/vendite/contratti/42/righe/lista/"


class TestContrattoRigheListaApi(JwtMockedApiTest):

    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        cache.clear()

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SERVICE)
    def test_lista_pagina_col_contratto_del_percorso(self, svc, _auth) -> None:
        svc.return_value.list_righe_pagina.return_value = ([{"riga_key": "A:7"}], 3)
        resp = self.client.get(f"{_BASE}?search=canone&order_by=prezzo_finale&order_dir=desc&limit=10")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["count"], 3)
        self.assertEqual(resp.json()["data"]["results"], [{"riga_key": "A:7"}])
        svc.return_value.list_righe_pagina.assert_called_once_with(
            42, search="canone", order_by="prezzo_finale", order_dir="desc",
            limit=10, offset=0,
        )

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SERVICE)
    def test_lista_ed_export_col_cancello_del_contratto(self, svc, _auth) -> None:
        svc.return_value.list_righe_pagina.return_value = ([], 0)
        for suffisso in ("", "export/"):
            cache.clear()
            with self.subTest(export=bool(suffisso)), patch(_GUARD) as guard, coda_export_finta():
                resp = self.client.get(f"{_BASE}{suffisso}?emittente_fiscale_id=3")
                self.assertEqual(resp.status_code, 200)
                guard.assert_called_once()
                self.assertEqual(guard.call_args.kwargs["lista_codice"], "vendite.contratto_righe")
                self.assertEqual(guard.call_args.kwargs["emittente_esplicito"], 3)

    @patch(_AUTH, return_value=(Mock(), None))
    @patch(_SERVICE)
    def test_export_alza_il_tetto(self, svc, _auth) -> None:
        svc.return_value.list_righe_pagina.return_value = ([{"riga_key": "A:7"}], 1)
        with coda_export_finta("righe.csv"):
            resp = self.client.get(f"{_BASE}export/?formato=csv")
        self.assertEqual(resp.status_code, 200)
        kwargs = svc.return_value.list_righe_pagina.call_args.kwargs
        self.assertEqual((kwargs["limit"], kwargs["max_limit"]), (EXPORT_MAX_ROWS + 1, EXPORT_MAX_ROWS + 1))
        self.assertNotIn("auth_user_id", kwargs)

    def test_lista_ed_export_col_permesso_del_contratto(self) -> None:
        for suffisso in ("", "export/"):
            with self.subTest(export=bool(suffisso)):
                view = resolve(f"{_BASE}{suffisso}").func.view_class
                self.assertEqual(view.model_permission, ("vendite", "contratto"))

    # ⭐ Il percorso suo esiste per questo: `…/righe/` serve anche il POST di
    #    creazione, e un cancello di lista li' rifiuterebbe la creazione a chi
    #    vede piu' emittenti (decisione di Tid del lotto A).
    def test_la_risorsa_righe_resta_senza_cancello_di_lista(self) -> None:
        view = resolve("/api/v1/vendite/contratti/42/righe/").func.view_class
        self.assertIsNone(getattr(view, "lista_codice", None))


class ContrattoRighePaginaServiceTests(TestCase):

    @patch("apps.vendite.services.contratti_service.ContrattoRigheListaRepository")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_service_fuori_perimetro_404_senza_leggere_le_righe(self, contratti, righe) -> None:
        contratti.return_value.get_stato_codice.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            ContrattiService().list_righe_pagina(42, limit=10)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")
        contratti.return_value.get_stato_codice.assert_called_once_with(42)
        righe.return_value.list_righe_pagina.assert_not_called()

    @patch("apps.vendite.services.contratti_service.ContrattoRigheListaRepository")
    @patch("apps.vendite.services.contratti_service.ContrattiRepository")
    def test_service_legge_la_pagina_dopo_la_testata(self, contratti, righe) -> None:
        contratti.return_value.get_stato_codice.return_value = "DRAFT"
        righe.return_value.list_righe_pagina.return_value = ([], 0)
        ContrattiService().list_righe_pagina(42, search="x", limit=10, offset=20)
        args, kwargs = righe.return_value.list_righe_pagina.call_args
        self.assertEqual(args, (42,))
        self.assertEqual((kwargs["search"], kwargs["limit"], kwargs["offset"]), ("x", 10, 20))
