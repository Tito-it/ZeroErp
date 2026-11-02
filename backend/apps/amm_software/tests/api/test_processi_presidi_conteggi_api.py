# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP di GET /amm-software/processi/presidi/conteggi/ — la
#        testata dei presidi per il PALLINO della topbar (decisione #8 di Tid,
#        2026-09-18; piano-be-fe-osservabilita-pallino-e-superfici §2.2).
#        Repository MOCKATO, nessun database.
# Note: ⚠️ La rotta sta sotto `processi/`, dove `<str:codice>/` prende tutto:
#        il test 2 pinna che `presidi/conteggi/` arrivi a QUESTA view e non al
#        dettaglio di un processo che si chiama «presidi» — lo stesso ordine
#        gia' scritto per `presidi/`, e l'unico modo di sbagliarlo e' spostare
#        una riga in `urls_v1.py` senza che niente fallisca.
#
# Indice test:
#   1. senza JWT -> 401
#   2. la view e' una AdminAPIView, e la rotta porta a QUESTA view (non al
#      dettaglio processo)
#   3. ok -> 200 {totale, con_righe, non_letti}, e il repository viene letto
#      LEGGERO (`con_righe=False`)
#   4. un presidio non letto NON e' un errore della risposta: e' `non_letti`
# ------------------------------------------------------------
from unittest.mock import Mock, patch

from django.test import Client
from django.urls import resolve

from apps.amm_software.api.views import (
    ProcessiDetailView,
    ProcessiPresidiConteggiView,
)
from apps.core.api.base_views import AdminAPIView
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
# I repository che il service costruisce da se': si sostituiscono dove il
# service li importa.
_SVC = "apps.core.services.processi_service"
_PRESIDI_REPO = f"{_SVC}.PresidiRepository"
_PROCESSI_REPO = f"{_SVC}.ProcessiRepository"
_URL = "/api/v1/amm-software/processi/presidi/conteggi/"


# Scopo: un superuser: `AdminAPIView` lo fa passare da `is_superuser`.
def _mock_user() -> Mock:
    return Mock(id=9, username="op9", is_superuser=True, is_authenticated=True)


def _riga(vista: str, conteggio, errore=None) -> dict:
    return {
        "vista": vista, "descrizione": "d", "conteggio": conteggio,
        "righe": [], "troncato": False, "elencabili": True,
        "errore": errore, "da_guardare": bool(errore) or (conteggio or 0) > 0,
    }


class ProcessiPresidiConteggiApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # 1. Senza JWT -> 401.
    def test_richiede_jwt(self) -> None:
        self.assertEqual(self.client.get(_URL).status_code, 401)

    # 2. La porta e' `AdminAPIView`, e la rotta porta a QUESTA view.
    def test_porta_admin_e_rotta(self) -> None:
        self.assertTrue(issubclass(ProcessiPresidiConteggiView, AdminAPIView))
        match = resolve(_URL)
        self.assertIs(match.func.view_class, ProcessiPresidiConteggiView)
        self.assertIsNot(match.func.view_class, ProcessiDetailView)
        # Nessun permesso decorativo: la fiducia sta nella classe base.
        self.assertFalse(hasattr(ProcessiPresidiConteggiView, "get_permission"))

    # 3. Il caso buono: i tre numeri, e la lettura e' quella LEGGERA.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_PROCESSI_REPO)
    @patch(_PRESIDI_REPO)
    def test_ok_tre_numeri_lettura_leggera(self, presidi_cls, _repo, _auth) -> None:
        presidi_cls.return_value.stato_presidi.return_value = [
            _riga("dbops.vw_a", 0),
            _riga("dbops.vw_b", 4),
        ]
        resp = self.client.get(_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(
            resp.json()["data"], {"totale": 2, "con_righe": 1, "non_letti": 0},
        )
        presidi_cls.return_value.stato_presidi.assert_called_once_with(con_righe=False)

    # 4. Un presidio non letto viaggia come `non_letti`, non come 500: la
    #    cecita' si conta, e il pallino la mostra come «chiede un occhio».
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_PROCESSI_REPO)
    @patch(_PRESIDI_REPO)
    def test_non_letto_si_conta_non_si_solleva(self, presidi_cls, _repo, _auth) -> None:
        presidi_cls.return_value.stato_presidi.return_value = [
            _riga("dbops.vw_a", 0),
            _riga("dbops.vw_cade", None, errore="connessione persa"),
        ]
        resp = self.client.get(_URL)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(
            resp.json()["data"], {"totale": 2, "con_righe": 0, "non_letti": 1},
        )
