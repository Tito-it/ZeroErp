# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test HTTP contract endpoint API commesse (§25.6).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) VenditeCommesseApiTests.test_post_run_commesse_push_ok
2) VenditeCommesseApiTests.test_post_run_commesse_push_v1_requires_jwt
3) VenditeCommesseApiTests.test_post_run_commesse_push_skipped
4) VenditeCommesseApiTests.test_get_commesse_push_log_ok
5) VenditeCommesseApiTests.test_get_commesse_push_log_v1_requires_jwt
6) VenditeCommesseApiTests.test_get_commesse_push_log_not_found
7) VenditeCommesseApiTests.test_get_commessa_stato_ok
8) VenditeCommesseApiTests.test_get_commessa_stato_v1_requires_jwt
9) VenditeCommesseApiTests.test_get_commessa_stato_not_found
10) VenditeCommesseApiTests.test_get_commessa_attivita_ok
11) VenditeCommesseApiTests.test_get_commessa_attivita_v1_requires_jwt
12) VenditeCommesseApiTests.test_finestra_fuori_limite_e_400
13) VenditeCommesseApiTests.test_get_commessa_attivita_con_filtri
14) VenditeCommesseApiTests.test_run_commesse_push_post_permission_allowed
15) VenditeCommesseApiTests.test_run_commesse_push_post_permission_denied
15-bis) VenditeCommesseApiTests.test_commessa_stato_azione_della_riga_concessa
15-ter) VenditeCommesseApiTests.test_commessa_stato_azione_della_riga_negata
15-quater) VenditeCommesseApiTests.test_commessa_stato_riga_senza_azione_livello_sul_documento
15-quinquies) VenditeCommesseApiTests.test_commessa_stato_dichiara_il_passaggio
16) VenditeCommesseApiTests.test_post_commessa_attivita_approva_ok
17) VenditeCommesseApiTests.test_post_commessa_attivita_approva_selezione
18) VenditeCommesseApiTests.test_post_commessa_attivita_approva_requires_jwt
19) VenditeCommesseApiTests.test_post_commessa_attivita_approva_validation
20) VenditeCommesseApiTests.test_post_approva_competenza_ok
21) VenditeCommesseApiTests.test_post_approva_competenza_requires_jwt
22) VenditeCommesseApiTests.test_approva_competenza_post_permission_allowed
23) VenditeCommesseApiTests.test_commessa_attivita_approva_post_permission_denied

VenditeCommessaOneriApiTests (porta oneri §A1 + gate prezzo N5/N7 §C1):
24) test_post_onere_ok
25) test_post_onere_requires_jwt
26) test_post_onere_errore_dominio
27) test_post_onere_permission_denied
28) test_post_onere_permission_allowed
29) test_endpoint_prezzo_richiedono_permesso_override
VenditeCommessaTestataApiTests (Blocco C, brief-db-modifiche-certe-ciclo-vendita-e-articolo):
30) test_patch_testata_ok_risponde_col_dettaglio
31) test_patch_testata_requires_jwt
32) test_patch_testata_errore_di_validazione_400_col_campo
"""

import json

from unittest.mock import ANY, Mock, patch

from django.test import Client
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

from apps.core.services.service_errors import ServiceError
from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova


class VenditeCommesseApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # ------------------------------------------------------------------ #
    # POST /api/v1/vendite/commesse/push/run/                            #
    # ------------------------------------------------------------------ #

    # Scopo: push ok → 200 con stato COMPLETATO.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_commesse_push")
    def test_post_run_commesse_push_ok(self, mocked_push, _mock_auth):
        mocked_push.return_value = {
            "stato": "COMPLETATO",
            "dry_run": False,
            "push_log_id": 10,
            "durata_ms": 150,
            "handlers": [{"handler_name": "HandlerA", "created": 2, "updated": 0, "skipped": 0, "errors": []}],
        }
        response = self.client.post(
            "/api/v1/vendite/commesse/push/run/",
            data=json.dumps({"dry_run": False}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-push-ok-1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["stato"], "COMPLETATO")
        self.assertEqual(data["push_log_id"], 10)
        mocked_push.assert_called_once()

    # Scopo: endpoint V1 richiede JWT.
    def test_post_run_commesse_push_v1_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/commesse/push/run/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-push-auth-1"},
        )
        self.assertEqual(response.status_code, 401)

    # Scopo: lock occupato → 200 con stato SKIPPED.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.pr_run_commesse_push")
    def test_post_run_commesse_push_skipped(self, mocked_push, _mock_auth):
        mocked_push.return_value = {
            "stato": "SKIPPED",
            "dry_run": False,
            "push_log_id": None,
            "durata_ms": 0,
            "handlers": [],
        }
        response = self.client.post(
            "/api/v1/vendite/commesse/push/run/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-push-skip-1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["stato"], "SKIPPED")

    # ------------------------------------------------------------------ #
    # GET /api/v1/vendite/commesse/push/<log_id>/                        #
    # ------------------------------------------------------------------ #

    # Scopo: push log trovato → 200.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_commesse_push_log")
    def test_get_commesse_push_log_ok(self, mocked_log, _mock_auth):
        mocked_log.return_value = {
            "id": 5,
            "run_at": "2026-02-26T10:00:00",
            "dry_run": False,
            "source_types": ["SRC_A"],
            "risultato": {"HandlerA": {"created": 1}},
            "stato": "COMPLETATO",
            "durata_ms": 100,
        }
        response = self.client.get("/api/v1/vendite/commesse/push/5/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["id"], 5)
        mocked_log.assert_called_once_with(push_log_id=5)

    # Scopo: endpoint V1 richiede JWT.
    def test_get_commesse_push_log_v1_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/commesse/push/5/")
        self.assertEqual(response.status_code, 401)

    # Scopo: push log non trovato → 404.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_commesse_push_log")
    def test_get_commesse_push_log_not_found(self, mocked_log, _mock_auth):
        mocked_log.side_effect = ServiceError(
            code="E_COMMESSA_PUSH_LOG_NOT_FOUND",
            message="Push log non trovato.",
            detail="id=999",
        )
        response = self.client.get("/api/v1/vendite/commesse/push/999/")
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_COMMESSA_PUSH_LOG_NOT_FOUND")

    # ------------------------------------------------------------------ #
    # GET /api/v1/vendite/commesse/<id>/stato/                           #
    # ------------------------------------------------------------------ #

    # Scopo: commessa trovata → 200 con contatori.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_commessa_stato")
    def test_get_commessa_stato_ok(self, mocked_stato, _mock_auth):
        mocked_stato.return_value = {
            "commessa_id": 1,
            "total_attivita": 10,
            "total_approvate": 8,
            "total_emesse": 5,
        }
        response = self.client.get("/api/v1/vendite/commesse/1/stato/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["commessa_id"], 1)
        self.assertEqual(data["total_attivita"], 10)
        mocked_stato.assert_called_once_with(commessa_id=1)

    # Scopo: endpoint V1 richiede JWT.
    def test_get_commessa_stato_v1_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/commesse/1/stato/")
        self.assertEqual(response.status_code, 401)

    # Scopo: commessa non trovata → 404.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_get_commessa_stato")
    def test_get_commessa_stato_not_found(self, mocked_stato, _mock_auth):
        mocked_stato.side_effect = ServiceError(
            code="E_COMMESSA_NOT_FOUND",
            message="Commessa non trovata.",
            detail="id=999",
        )
        response = self.client.get("/api/v1/vendite/commesse/999/stato/")
        self.assertEqual(response.status_code, 404)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_COMMESSA_NOT_FOUND")

    # ------------------------------------------------------------------ #
    # GET /api/v1/vendite/commesse/<id>/attivita/                        #
    # ------------------------------------------------------------------ #

    # Scopo: lista attivita ok → 200.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_commessa_attivita")
    def test_get_commessa_attivita_ok(self, mocked_list, _mock_auth):
        mocked_list.return_value = {
            "commessa_id": 1,
            "count": 0,
            "results": [],
        }
        response = self.client.get("/api/v1/vendite/commesse/1/attivita/?limit=20&offset=0")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["commessa_id"], 1)
        self.assertEqual(data["count"], 0)
        mocked_list.assert_called_once_with(
            commessa_id=1, stato_emissione=None, stato_approvazione=None,
            competenza_mese=None, limit=20, offset=0,
            order_by=None, order_dir=None,
            tipo_movimento=None,
        )

    # Scopo: endpoint V1 richiede JWT.
    def test_get_commessa_attivita_v1_requires_jwt(self):
        response = self.client.get("/api/v1/vendite/commesse/1/attivita/")
        self.assertEqual(response.status_code, 401)

    # Scopo: filtri opzionali propagati al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_commessa_attivita")
    def test_get_commessa_attivita_con_filtri(self, mocked_list, _mock_auth):
        mocked_list.return_value = {"commessa_id": 1, "count": 0, "results": []}
        response = self.client.get(
            "/api/v1/vendite/commesse/1/attivita/?stato_emissione=NON_EMESSA&stato_approvazione=APPROVATA&competenza_mese=2026-02-01"
        )
        self.assertEqual(response.status_code, 200)
        mocked_list.assert_called_once_with(
            commessa_id=1, stato_emissione="NON_EMESSA", stato_approvazione="APPROVATA",
            competenza_mese="2026-02-01", limit=DEFAULT_LIMIT, offset=0,
            order_by=None, order_dir=None,
            tipo_movimento=None,
        )

    # Scopo: order_by/order_dir propagati al service (7° lotto liste, 2026-08-03).
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_list_commessa_attivita")
    def test_get_commessa_attivita_con_ordinamento(self, mocked_list, _mock_auth):
        mocked_list.return_value = {"commessa_id": 1, "count": 0, "results": []}
        response = self.client.get(
            "/api/v1/vendite/commesse/1/attivita/?order_by=data_attivita&order_dir=desc"
        )
        self.assertEqual(response.status_code, 200)
        mocked_list.assert_called_once_with(
            commessa_id=1, stato_emissione=None, stato_approvazione=None,
            competenza_mese=None, limit=DEFAULT_LIMIT, offset=0,
            order_by="data_attivita", order_dir="desc",
            tipo_movimento=None,
        )

    # Scopo: ⛔ la finestra fuori limite e' un 400 della view (`pagina_da_query`,
    #        Tid 2026-10-21), e il service non parte. Fino a quel giorno la view
    #        la riduceva in silenzio e i due service avevano un loro guard,
    #        che via HTTP non scattava piu'.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_commessa_registro")
    @patch("apps.vendite.api.views.fn_list_commessa_attivita")
    def test_finestra_fuori_limite_e_400(self, mocked_list, mocked_registro, _mock_auth):
        for rotta in ("attivita", "registro"):
            for qs in ("limit=500", "limit=0", "offset=-1"):
                with self.subTest(rotta=rotta, qs=qs):
                    response = self.client.get(f"/api/v1/vendite/commesse/1/{rotta}/?{qs}")
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json()["error"]["code"], "E_VALIDATION_INPUT")
        mocked_list.assert_not_called()
        mocked_registro.assert_not_called()

    # ------------------------------------------------------------------ #
    # POST /api/v1/vendite/commesse/push/run/ — post_permission          #
    # ------------------------------------------------------------------ #

    # Scopo: Verifica che post_permission="run_commesse_push" consenta l'accesso con azione abilitata.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=True)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")
    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.pr_run_commesse_push")
    def test_run_commesse_push_post_permission_allowed(
        self, mocked_push, mock_auth, _mock_ruolo, _mock_app, mock_azione, _mock_load, _mock_save
    ):
        user = operatore_di_prova(user_id=42)
        mock_auth.return_value = (user, None)
        mocked_push.return_value = {
            "stato": "COMPLETATO", "dry_run": False,
            "push_log_id": 10, "durata_ms": 100, "handlers": [],
        }
        response = self.client.post(
            "/api/v1/vendite/commesse/push/run/",
            data=json.dumps({"dry_run": False}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-perm-ok-1"},
        )
        self.assertEqual(response.status_code, 200)
        mock_azione.assert_called_once()
        self.assertEqual(mock_azione.call_args.args[1], "run_commesse_push")

    # Scopo: Verifica che post_permission="run_commesse_push" neghi l'accesso con azione disabilitata.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=False)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")

    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    def test_run_commesse_push_post_permission_denied(
        self, mock_auth, _mock_ruolo, _mock_app, mock_azione, _mock_load, _mock_save
    ):
        user = operatore_di_prova(user_id=42)
        mock_auth.return_value = (user, None)
        response = self.client.post(
            "/api/v1/vendite/commesse/push/run/",
            data=json.dumps({"dry_run": False}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-perm-deny-1"},
        )
        self.assertEqual(response.status_code, 403)
        mock_azione.assert_called_once()
        self.assertEqual(mock_azione.call_args.args[1], "run_commesse_push")

    # ------------------------------------------------------------------ #
    # POST /api/v1/vendite/commesse/<id>/stato/ — dalla riga del passaggio #
    # ------------------------------------------------------------------ #
    # L'azione la legge la catena dalla riga della matrice (`PassaggioDocumento`,
    # M-3, brief-modello-documento-vendita §14.6 punto 2): il repository del
    # passaggio e' mockato, la lettura vera la prova
    # `vendite/tests/db/test_commessa_cambia_stato_db`.

    # Scopo: con l'azione della riga (qui «chiudi») la transizione passa, e
    #        l'azione chiesta e' quella che la riga dice.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.api.permissions.DocumentoModelloRepository", autospec=True)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=True)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")
    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.cambia_stato_commessa")
    def test_commessa_stato_azione_della_riga_concessa(
        self, mocked_cambia, mock_auth, _mock_ruolo, _mock_app, mock_azione, repo_cls, _mock_load, _mock_save
    ):
        mock_auth.return_value = (operatore_di_prova(user_id=42), None)
        repo_cls.return_value.azione_del_passaggio.return_value = "cambia_stato_commessa"
        mocked_cambia.return_value = {"commessa_id": 1, "stato_da": "PRONTA_FATTURAZIONE", "stato_a": "CHIUSA"}
        response = self.client.post(
            "/api/v1/vendite/commesse/1/stato/",
            data=json.dumps({"nuovo_stato": "CHIUSA"}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-stato-ok-1"},
        )
        self.assertEqual(response.status_code, 200)
        repo_cls.return_value.azione_del_passaggio.assert_called_once_with("vendite.commesse", 1, "CHIUSA")
        mock_azione.assert_called_once()
        self.assertEqual(mock_azione.call_args.args[1], "cambia_stato_commessa")
        mocked_cambia.assert_called_once_with(
            commessa_id=1, nuovo_stato="CHIUSA", legami_confermati=None,
        )

    # Scopo: senza l'azione della riga la transizione e' negata (403) e il
    #        service NON viene invocato.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.api.permissions.DocumentoModelloRepository", autospec=True)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=False)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")
    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.cambia_stato_commessa")
    def test_commessa_stato_azione_della_riga_negata(
        self, mocked_cambia, mock_auth, _mock_ruolo, _mock_app, mock_azione, repo_cls, _mock_load, _mock_save
    ):
        mock_auth.return_value = (operatore_di_prova(user_id=42), None)
        repo_cls.return_value.azione_del_passaggio.return_value = "cambia_stato_commessa"
        response = self.client.post(
            "/api/v1/vendite/commesse/1/stato/",
            data=json.dumps({"nuovo_stato": "ANNULLATA"}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-stato-deny-1"},
        )
        self.assertEqual(response.status_code, 403)
        mock_azione.assert_called_once()
        self.assertEqual(mock_azione.call_args.args[1], "cambia_stato_commessa")
        mocked_cambia.assert_not_called()

    # Scopo: C-1, cambio visibile — l'annullo della bozza e' una riga senza
    #        azione: decide il livello sul documento, `cambia_stato_commessa`
    #        non si chiede (prima il `post_permission` la chiedeva sempre).
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.api.permissions.DocumentoModelloRepository", autospec=True)
    @patch("apps.core.api.permissions.PermissionResolver")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.cambia_stato_commessa")
    def test_commessa_stato_riga_senza_azione_livello_sul_documento(
        self, mocked_cambia, mock_auth, resolver, repo_cls, _mock_load, _mock_save,
    ):
        mock_auth.return_value = (operatore_di_prova(user_id=42), None)
        resolver.is_super_admin.return_value = False
        resolver.get_area_schema_db.return_value = "vendite"
        resolver.get_livello_area.return_value = "TUTTO"
        mock_azione, mock_livello = resolver.check_azione, resolver.get_livello_area
        repo_cls.return_value.azione_del_passaggio.return_value = None
        mocked_cambia.return_value = {"commessa_id": 1, "stato_da": "BOZZA", "stato_a": "ANNULLATA"}
        response = self.client.post(
            "/api/v1/vendite/commesse/1/stato/",
            data=json.dumps({"nuovo_stato": "ANNULLATA"}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-stato-bozza-1"},
        )
        self.assertEqual(response.status_code, 200)
        mock_azione.assert_not_called()
        mock_livello.assert_called()
        mocked_cambia.assert_called_once()

    # Scopo: la view legge l'azione dalla riga, non la dichiara: nessun
    #        `post_permission` accanto (M-3, §14.6 punto 2).
    def test_commessa_stato_dichiara_il_passaggio(self) -> None:
        from apps.core.api.permissions import PassaggioDocumento
        from apps.vendite.api.views import ApiCommessaStato

        self.assertEqual(ApiCommessaStato.post_passaggio, PassaggioDocumento(
            testata="vendite.commesse", documento_kwarg="commessa_id", campo_stato="nuovo_stato",
        ))
        self.assertIsNone(getattr(ApiCommessaStato, "post_permission", None))

    # ------------------------------------------------------------------ #
    # POST /api/v1/vendite/commesse/<id>/attivita/approva/ (A-1)         #
    # ------------------------------------------------------------------ #

    # Scopo: approvazione ok → 200 con contatore righe approvate.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.approva_commessa_attivita")
    def test_post_commessa_attivita_approva_ok(self, mocked_approva, _mock_auth):
        mocked_approva.return_value = {"commessa_id": 42, "approvate": 5}
        response = self.client.post(
            "/api/v1/vendite/commesse/42/attivita/approva/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-approva-1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["approvate"], 5)
        mocked_approva.assert_called_once_with(
            commessa_id=42, righe_ids=None, user=ANY,
        )

    # Scopo: selezione righe → passthrough righe_ids al service.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.approva_commessa_attivita")
    def test_post_commessa_attivita_approva_selezione(self, mocked_approva, _mock_auth):
        mocked_approva.return_value = {"commessa_id": 42, "approvate": 2}
        response = self.client.post(
            "/api/v1/vendite/commesse/42/attivita/approva/",
            data=json.dumps({"righe_ids": [10, 11]}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-approva-2"},
        )
        self.assertEqual(response.status_code, 200)
        mocked_approva.assert_called_once_with(
            commessa_id=42, righe_ids=[10, 11], user=ANY,
        )

    # Scopo: endpoint richiede JWT.
    def test_post_commessa_attivita_approva_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/commesse/42/attivita/approva/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-approva-auth-1"},
        )
        self.assertEqual(response.status_code, 401)

    # Scopo: ServiceError di validazione dal service → 400 con codice.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.approva_commessa_attivita")
    def test_post_commessa_attivita_approva_validation(self, mocked_approva, _mock_auth):
        mocked_approva.side_effect = ServiceError(
            code="E_COMMESSA_VALIDATION", message="righe_ids non valido.",
        )
        response = self.client.post(
            "/api/v1/vendite/commesse/42/attivita/approva/",
            data=json.dumps({"righe_ids": []}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-approva-3"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_COMMESSA_VALIDATION")

    # ------------------------------------------------------------------ #
    # POST /api/v1/vendite/fatturazione/approva-competenza/ (A-2)        #
    # ------------------------------------------------------------------ #

    # Scopo: massiva ok → 200 con contatori commesse/approvate.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.approva_attivita_competenza")
    def test_post_approva_competenza_ok(self, mocked_massiva, _mock_auth):
        from datetime import date as _date

        mocked_massiva.return_value = {
            "competenza_mese": "2026-07-01", "commesse": 2, "approvate": 3,
        }
        response = self.client.post(
            "/api/v1/vendite/fatturazione/approva-competenza/",
            data=json.dumps({"competenza_mese": "2026-07-15"}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-massiva-1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["commesse"], 2)
        self.assertEqual(data["approvate"], 3)
        mocked_massiva.assert_called_once_with(
            competenza_mese=_date(2026, 7, 15), commessa_ids=None, user=ANY,
        )

    # Scopo: endpoint richiede JWT.
    def test_post_approva_competenza_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/fatturazione/approva-competenza/",
            data=json.dumps({"competenza_mese": "2026-07-01"}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-massiva-auth-1"},
        )
        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------ #
    # post_permission = "approva_attivita_commessa" (A-1 + A-2)          #
    # ------------------------------------------------------------------ #

    # Scopo: azione abilitata → 200 e codename corretto verificato (A-2).
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=True)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")
    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.approva_attivita_competenza")
    def test_approva_competenza_post_permission_allowed(
        self, mocked_massiva, mock_auth, _mock_ruolo, _mock_app, mock_azione, _mock_load, _mock_save
    ):
        user = operatore_di_prova(user_id=42)
        user.username = "op1"
        mock_auth.return_value = (user, None)
        mocked_massiva.return_value = {
            "competenza_mese": "2026-07-01", "commesse": 0, "approvate": 0,
        }
        response = self.client.post(
            "/api/v1/vendite/fatturazione/approva-competenza/",
            data=json.dumps({"competenza_mese": "2026-07-01"}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-massiva-perm-ok-1"},
        )
        self.assertEqual(response.status_code, 200)
        mock_azione.assert_called_once()
        self.assertEqual(mock_azione.call_args.args[1], "approva_attivita_commessa")

    # Scopo: azione disabilitata → 403 sul singolo (A-1), stesso codename.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=False)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")
    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    def test_commessa_attivita_approva_post_permission_denied(
        self, mock_auth, _mock_ruolo, _mock_app, mock_azione, _mock_load, _mock_save
    ):
        user = operatore_di_prova(user_id=42)
        mock_auth.return_value = (user, None)
        response = self.client.post(
            "/api/v1/vendite/commesse/42/attivita/approva/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-approva-perm-deny-1"},
        )
        self.assertEqual(response.status_code, 403)
        mock_azione.assert_called_once()
        self.assertEqual(mock_azione.call_args.args[1], "approva_attivita_commessa")


class VenditeCommessaOneriApiTests(JwtMockedApiTest):
    """POST /api/v1/vendite/commesse/<id>/oneri/ — porta oneri (§A1) e gate
    `prezzo_override_manuale` sugli endpoint prezzo N5/N7 (§C1)."""

    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    def _payload(self, **override):
        payload = {
            "articolo_onere_id": "3f1c9a52-0d5e-4c7b-9a10-2b6d8e4f0011",
            "importo": "150.00",
            "tipo_doc_fiscale_id": 7,
            "motivo": "trasferta cantiere",
        }
        payload.update(override)
        return payload

    def _post_oneri(self, *, key: str, payload=None):
        return self.client.post(
            "/api/v1/vendite/commesse/42/oneri/",
            data=json.dumps(self._payload() if payload is None else payload),
            content_type="application/json",
            headers={"Idempotency-Key": key},
        )

    # Scopo: carico onere ok → 200 con l'id della riga creata; payload inoltrato
    #        al service con i nomi di dominio attesi.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.aggiungi_onere_commessa")
    def test_post_onere_ok(self, mocked_service, _mock_auth):
        mocked_service.return_value = {
            "commessa_id": 42, "attivita_id": 5150, "importo": "150.00",
        }
        response = self._post_oneri(key="idem-onere-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["attivita_id"], 5150)
        kwargs = mocked_service.call_args.kwargs
        self.assertEqual(kwargs["commessa_id"], 42)
        self.assertEqual(kwargs["tipo_doc_fiscale_id"], 7)
        self.assertEqual(kwargs["motivo"], "trasferta cantiere")
        # Istanza non passata dalla UI: la deriva il service dal BA della commessa.
        self.assertIsNone(kwargs["istanza_utility_id"])

    # Scopo: endpoint protetto — senza JWT nessun accesso.
    def test_post_onere_requires_jwt(self):
        response = self._post_oneri(key="idem-onere-jwt")
        self.assertEqual(response.status_code, 401)

    # Scopo: errore di dominio del service → envelope con il codice originale
    #        (l'operatore legge "articolo non valido", non "errore generico").
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.aggiungi_onere_commessa")
    def test_post_onere_errore_dominio(self, mocked_service, _mock_auth):
        mocked_service.side_effect = ServiceError(
            code="E_ONERE_ARTICOLO_MANCANTE",
            message="Articolo-onere non valido.",
        )
        response = self._post_oneri(key="idem-onere-err")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "E_ONERE_ARTICOLO_MANCANTE")

    # Scopo: la race sul progressivo (guard DB 557) è un CONFLITTO di
    #        concorrenza ritentabile, non un input errato → envelope 409, non
    #        400. Blinda la policy registrata per l'handoff §5 del brief DB.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.aggiungi_onere_commessa")
    def test_post_onere_segment_duplicato_409(self, mocked_service, _mock_auth):
        mocked_service.side_effect = ServiceError(
            code="E_ONERE_SEGMENT_DUPLICATO",
            message="Onere non creato per una modifica concorrente. Riprovare.",
        )
        response = self._post_oneri(key="idem-onere-race")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "E_ONERE_SEGMENT_DUPLICATO")

    # Scopo: gate all'ingresso (§4c.5) — senza `carica_voce_manuale` niente
    #        caricamento oneri, e il service non viene nemmeno interpellato.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=False)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")
    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.aggiungi_onere_commessa")
    def test_post_onere_permission_denied(
        self, mocked_service, mock_auth, _mock_sa, _mock_ruolo, mock_azione, _mock_load, _mock_save,
    ):
        user = operatore_di_prova(user_id=42)
        mock_auth.return_value = (user, None)

        response = self._post_oneri(key="idem-onere-deny")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(mock_azione.call_args.args[1], "carica_voce_manuale")
        mocked_service.assert_not_called()

    # Scopo: gate abilitato → passa, con il codename giusto.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=True)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")
    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.aggiungi_onere_commessa")
    def test_post_onere_permission_allowed(
        self, mocked_service, mock_auth, _mock_sa, _mock_ruolo, mock_azione, _mock_load, _mock_save,
    ):
        user = operatore_di_prova(user_id=42)
        mock_auth.return_value = (user, None)
        mocked_service.return_value = {
            "commessa_id": 42, "attivita_id": 5150, "importo": "150.00",
        }

        response = self._post_oneri(key="idem-onere-allow")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_azione.call_args.args[1], "carica_voce_manuale")

    # ------------------------------------------------------------------ #
    # Gate prezzo N5/N7 (§C1 — chiusura della trappola T2)               #
    # ------------------------------------------------------------------ #

    # Scopo: i tre endpoint prezzo di commessa esigono `prezzo_override_manuale`.
    #        Prima bastava la scrittura sull'area vendite: questo test documenta
    #        la chiusura di T2 e impedisce che il gate venga rimosso in futuro.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.check_azione", return_value=False)
    @patch("apps.core.services.permissions_resolver.PermissionResolver.get_ruolo_applicativo", return_value="OPERATORE")
    @patch("apps.core.services.permissions_resolver.PermissionResolver.is_super_admin", return_value=False)
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    def test_endpoint_prezzo_richiedono_permesso_override(
        self, mock_auth, _mock_sa, _mock_ruolo, mock_azione, _mock_load, _mock_save,
    ):
        user = operatore_di_prova(user_id=42)
        mock_auth.return_value = (user, None)

        percorsi = (
            ("riallinea-prezzo", {}),
            ("variazione-prezzo-eccezionale", {"prezzo": "10", "motivo": "x"}),
            ("sblocca-prezzo", {"motivo": "x"}),
        )
        for idx, (azione, payload) in enumerate(percorsi):
            mock_azione.reset_mock()
            with self.subTest(azione=azione):
                response = self.client.post(
                    f"/api/v1/vendite/commesse/42/attivita/7/{azione}/",
                    data=json.dumps(payload),
                    content_type="application/json",
                    headers={"Idempotency-Key": f"idem-prezzo-deny-{idx}"},
                )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(mock_azione.call_args.args[1], "prezzo_override_manuale")


# Scopo: `PATCH /vendite/commesse/<id>/` — la testata leggibile (descrizione +
#        responsabile). Contratto HTTP: il payload arriva al service per
#        posizione (id, payload), la risposta e' il dettaglio, gli errori del
#        service diventano envelope con `fields` (il campo si accende).
class VenditeCommessaTestataApiTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.aggiorna_commessa_testata")
    def test_patch_testata_ok_risponde_col_dettaglio(self, mocked_upd, _mock_auth):
        mocked_upd.return_value = {"commessa_id": 1, "descrizione": "Impianto", "responsabile_display": "Bianchi"}
        response = self.client.patch(
            "/api/v1/vendite/commesse/1/",
            data=json.dumps({"descrizione": "Impianto", "responsabile_risorsa_umana_id": 7}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["descrizione"], "Impianto")
        mocked_upd.assert_called_once_with(
            1, {"descrizione": "Impianto", "responsabile_risorsa_umana_id": 7},
        )

    def test_patch_testata_requires_jwt(self):
        response = self.client.patch(
            "/api/v1/vendite/commesse/1/",
            data=json.dumps({"descrizione": "x"}), content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.aggiorna_commessa_testata")
    def test_patch_testata_errore_di_validazione_400_col_campo(self, mocked_upd, _mock_auth):
        mocked_upd.side_effect = ServiceError(
            code="E_COMMESSA_VALIDATION",
            message="Il responsabile deve essere una risorsa umana attiva.",
            context={"field": "responsabile_risorsa_umana_id"},
        )
        response = self.client.patch(
            "/api/v1/vendite/commesse/1/",
            data=json.dumps({"responsabile_risorsa_umana_id": 7}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        errore = response.json()["error"]
        self.assertEqual(errore["code"], "E_COMMESSA_VALIDATION")
        self.assertEqual(errore["fields"], ["responsabile_risorsa_umana_id"])
