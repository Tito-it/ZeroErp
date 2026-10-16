# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Smoke test HTTP di POST /amm-software/processi/<codice>/esegui-ora/:
#        la porta (`AdminAPIView`), l'header obbligatorio, la cattura dello
#        scope PRIMA di accodare e i parametri di accodamento. Repository
#        MOCKATI, nessun database (piano-be-fe-avvio-manuale §5.5, «view»).
# Note: ⚠️ La sede della fiducia e' `AdminAPIView` (v1 solo SUPER_ADMIN,
#        brief §8.5): il test 3 lo pinna sulla CLASSE, non sul comportamento —
#        un `post_permission` decorativo non lo vedrebbe nessuno.
#        ⭐ La terna dello scope si cattura col BB `scope_operatore_da_request`
#        (in `coda_lavori.scope`): i suoi tre nomi si mockano LA', come nei
#        test del giro di fatturazione.
#
# Indice test:
#   1. senza JWT -> 401
#   2. senza Idempotency-Key -> 400
#   3. la view e' una AdminAPIView, e la rotta risolve
#   4. JWT senza identita_id -> E_CODA_SCOPE_OPERATORE_INVALIDO, niente accoda
#   5. ok -> 200 {job_id, stato, unit}; accoda con scope catturato, run_as
#      OPERATORE, chiave per unit, payload {processo_codice, unit}
#   6. unit assente -> 400 con `fields: ["unit"]`, niente accoda
# ------------------------------------------------------------

import json
from unittest.mock import Mock, patch

from django.test import Client, override_settings
from django.urls import resolve

from apps.amm_software.api.views import ProcessiEseguiOraView
from apps.core.api.base_views import AdminAPIView
from apps.core.services.avvio_manuale import JOB_TYPE_ESEGUI_PROCESSO, chiave_idempotenza
from apps.core.services.processi import PROCESSO_DIGEST_PRESIDI
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.core.tests._sveglie import prima_sveglia_candidata

_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SCOPE = "apps.core.services.coda_lavori.scope"
_RESOLVER_SCOPE = f"{_SCOPE}.PermissionResolver"
_EXTRACT_IDENTITA = f"{_SCOPE}.extract_identita_id_from_request"
_EXTRACT_EMITTENTE = f"{_SCOPE}.extract_emittente_attivo_from_request"
# I due repository che il service costruisce da se': si sostituiscono dove il
# service li importa.
_SVC = "apps.core.services.processi_service"
_PROCESSI_REPO = f"{_SVC}.ProcessiRepository"
_CODA_REPO = f"{_SVC}.CodaLavoriRepository"

_URL = f"/api/v1/amm-software/processi/{PROCESSO_DIGEST_PRESIDI}/esegui-ora/"


# Scopo: un superuser con identita' reale: `AdminAPIView` lo fa passare da
#        `is_superuser`, e lo scope prende id e username veri.
def _mock_user(user_id: int = 9, username: str = "op9") -> Mock:
    return Mock(id=user_id, username=username, is_superuser=True, is_authenticated=True)


@override_settings(API_STRONG_IDEMPOTENCY_ENABLED=False)
class ProcessiEseguiOraApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        self.unit = prima_sveglia_candidata(PROCESSO_DIGEST_PRESIDI).unit

    # Scopo: POST con il corpo dato e l'header, salvo `senza_chiave`.
    def _post(self, body: dict, *, senza_chiave: bool = False):
        headers = {} if senza_chiave else {"Idempotency-Key": "k-esegui-1"}
        return self.client.post(
            _URL, data=json.dumps(body), content_type="application/json", headers=headers,
        )

    # 1. Senza JWT -> 401.
    def test_richiede_jwt(self) -> None:
        self.assertEqual(self._post({"unit": self.unit}).status_code, 401)

    # 2. Senza Idempotency-Key -> 400: e' un verbo che scrive.
    @patch(_AUTH, return_value=(_mock_user(), None))
    def test_richiede_idempotency_key(self, _auth) -> None:
        self.assertEqual(self._post({"unit": self.unit}, senza_chiave=True).status_code, 400)

    # 3. La porta e' `AdminAPIView`, e la rotta porta a QUESTA view.
    def test_porta_admin_e_rotta(self) -> None:
        self.assertTrue(issubclass(ProcessiEseguiOraView, AdminAPIView))
        self.assertIs(resolve(_URL).func.view_class, ProcessiEseguiOraView)
        # Nessun `post_permission` decorativo: la fiducia sta nella classe base.
        self.assertFalse(hasattr(ProcessiEseguiOraView, "post_permission"))

    # 4. Terna incompleta: rifiuto PRIMA di accodare, col codice che il
    #    drenatore solleverebbe un minuto dopo.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_IDENTITA, return_value=None)
    @patch(_PROCESSI_REPO)
    @patch(_CODA_REPO)
    def test_senza_identita_rifiuta_prima_di_accodare(self, coda_cls, _repo, _extract, _auth) -> None:
        resp = self._post({"unit": self.unit})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "E_CODA_SCOPE_OPERATORE_INVALIDO")
        coda_cls.return_value.accoda.assert_not_called()

    # 5. Il caso buono: 200 con l'handle, e `accoda` con tutto quello che il
    #    drenatore e la UI code si aspettano.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_EMITTENTE, return_value=None)
    @patch(_EXTRACT_IDENTITA, return_value=5)
    @patch(_RESOLVER_SCOPE)
    @patch(_PROCESSI_REPO)
    @patch(_CODA_REPO)
    def test_ok_accoda(self, coda_cls, repo_cls, resolver, _extract, _extract_ef, _auth) -> None:
        resolver.get_emittenti_pk_ids.return_value = None  # admin globale
        repo_cls.return_value.get_processo.return_value = {"codice": PROCESSO_DIGEST_PRESIDI}
        # Acceso, detto: un MagicMock al posto della lettura passerebbe per caso.
        repo_cls.return_value.acceso_processo.return_value = True
        coda = coda_cls.return_value
        coda.lavori_vivi_per_chiave.return_value = {}
        coda.accoda.return_value = 777
        resp = self._post({"unit": self.unit})
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["data"], {"job_id": 777, "stato": "PENDING", "unit": self.unit})
        kwargs = coda.accoda.call_args.kwargs
        self.assertEqual(kwargs["job_type"], JOB_TYPE_ESEGUI_PROCESSO)
        self.assertEqual(kwargs["run_as"], "OPERATORE")
        self.assertEqual(kwargs["idempotency_key"], chiave_idempotenza(self.unit))
        self.assertEqual(kwargs["payload"], {"processo_codice": PROCESSO_DIGEST_PRESIDI, "unit": self.unit})
        self.assertEqual(kwargs["scope"], {
            "auth_user_id": 9, "username": "op9", "identita_id": 5,
            "emittente_attivo_id": None, "emittente_ids": None, "scope_key": "ALL",
        })

    # 6. `unit` assente: 400 parlante col campo da accendere, niente accoda.
    @patch(_AUTH, return_value=(_mock_user(), None))
    @patch(_EXTRACT_EMITTENTE, return_value=None)
    @patch(_EXTRACT_IDENTITA, return_value=5)
    @patch(_RESOLVER_SCOPE)
    @patch(_PROCESSI_REPO)
    @patch(_CODA_REPO)
    def test_unit_assente_400_con_campo(self, coda_cls, repo_cls, resolver, _extract, _extract_ef, _auth) -> None:
        resolver.get_emittenti_pk_ids.return_value = None
        repo_cls.return_value.get_processo.return_value = {"codice": PROCESSO_DIGEST_PRESIDI}
        resp = self._post({})
        self.assertEqual(resp.status_code, 400)
        errore = resp.json()["error"]
        self.assertEqual(errore["code"], "E_VALIDATION_INPUT")
        self.assertEqual(errore.get("fields"), ["unit"])
        coda_cls.return_value.accoda.assert_not_called()
