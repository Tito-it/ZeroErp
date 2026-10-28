"""
Indice test eseguiti:
1) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_ok
2) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_requires_idempotency_key
3) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_v1_requires_jwt
4) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_livello_sul_documento
5) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_senza_livello_403
6) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_azione_dalla_riga — se la riga ha un'azione, decide lei
7) VenditeResetLottoDraftApiTests.test_reset_lotto_draft_dichiara_il_passaggio — verso lo stato d'annullo, niente post_permission
"""

import json
from unittest.mock import patch, Mock

from django.test import Client
from apps.core.db.documento_modello_repository import StatoDocumento
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest
from apps.core.tests._helpers.operatore_di_prova import operatore_di_prova


_REPO_MODELLO = "apps.core.api.permissions.DocumentoModelloRepository"


# La riga del passaggio verso lo stato d'annullo, come la legge la catena dei
# permessi: lo stato dal vocabolario, l'azione dalla matrice (None = decide il
# livello sul documento).
def _riga_annullo(repo_cls: Mock, azione: str | None) -> None:
    repo = repo_cls.return_value
    repo.stato_di_annullo.return_value = StatoDocumento(id=9, codice="ANNULLATA")
    repo.azione_del_passaggio.return_value = azione


class VenditeResetLottoDraftApiTests(JwtMockedApiTest):
    # Scopo: Prepara il contesto comune del test.
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    # Scopo: Verifica il caso `test_reset_lotto_draft_ok`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    @patch("apps.vendite.api.views.fn_annulla_lotto_da_draft")
    def test_reset_lotto_draft_ok(self, mocked_service, _mock_auth):
        mocked_service.return_value = {
            "updated_lotti": 1,
            "updated_attivita": 2,
            "deleted_fatture": 3,
            "deleted_righe": 4,
        }
        response = self.client.post(
            "/api/v1/vendite/lotti/123/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-reset-1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["updated_lotti"], 1)
        mocked_service.assert_called_once_with(lotto_id=123)

    # Scopo: Verifica il caso `test_reset_lotto_draft_requires_idempotency_key`.
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate", return_value=(Mock(), None))
    def test_reset_lotto_draft_requires_idempotency_key(self, _mock_auth):
        response = self.client.post(
            "/api/v1/vendite/lotti/123/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()["error"]
        self.assertEqual(body["code"], "E_IDEMPOTENCY_KEY_REQUIRED")

    # Scopo: Verifica il caso `test_reset_lotto_draft_v1_requires_jwt`.
    def test_reset_lotto_draft_v1_requires_jwt(self):
        response = self.client.post(
            "/api/v1/vendite/lotti/123/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-reset-2"},
        )
        self.assertEqual(response.status_code, 401)

    # Scopo: Q-F2 — l'annullo del lotto in bozza chiede il SOLO livello sul
    #        documento: la riga del passaggio DRAFT -> ANNULLATA non ha azione,
    #        non c'e' niente di fiscale da disfare. Prima chiedeva
    #        `reset_lotto_draft`, ritirata dal catalogo (brief-modello-documento-
    #        vendita §15.8 punto 3).
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch(_REPO_MODELLO)
    @patch("apps.core.api.permissions.PermissionResolver")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.fn_annulla_lotto_da_draft")
    def test_reset_lotto_draft_livello_sul_documento(
        self, mocked_service, mock_auth, resolver, repo_cls, _mock_load, _mock_save,
    ):
        _riga_annullo(repo_cls, None)
        mock_auth.return_value = (operatore_di_prova(user_id=42), None)
        resolver.is_super_admin.return_value = False
        resolver.get_area_schema_db.return_value = "vendite"
        resolver.get_livello_area.return_value = "TUTTO"
        mocked_service.return_value = {
            "updated_lotti": 1, "updated_attivita": 0,
            "deleted_fatture": 0, "deleted_righe": 0,
        }
        response = self.client.post(
            "/api/v1/vendite/lotti/123/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-perm-ok-1"},
        )
        self.assertEqual(response.status_code, 200)
        resolver.check_azione.assert_not_called()
        resolver.get_livello_area.assert_called()
        repo_cls.return_value.azione_del_passaggio.assert_called_once_with(
            "vendite.fatturazione_lotti", 123, "ANNULLATA",
        )

    # Scopo: senza il livello sul documento -> 403, e nessuna azione chiesta.
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch(_REPO_MODELLO)
    @patch("apps.core.api.permissions.PermissionResolver")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.fn_annulla_lotto_da_draft")
    def test_reset_lotto_draft_senza_livello_403(
        self, mocked_service, mock_auth, resolver, repo_cls, _mock_load, _mock_save,
    ):
        _riga_annullo(repo_cls, None)
        mock_auth.return_value = (operatore_di_prova(user_id=42), None)
        resolver.is_super_admin.return_value = False
        resolver.get_area_schema_db.return_value = "vendite"
        resolver.get_livello_area.return_value = "LETTURA"
        response = self.client.post(
            "/api/v1/vendite/lotti/123/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-perm-deny-1"},
        )
        self.assertEqual(response.status_code, 403)
        resolver.check_azione.assert_not_called()
        mocked_service.assert_not_called()

    # Scopo: il gate lo dice la MATRICE, non la view: se la riga del passaggio
    #        verso l'annullo prende un'azione, si chiede quella (e il livello
    #        d'area non basta piu').
    @patch("apps.core.api.permissions.save_user_cache")
    @patch("apps.core.api.permissions.load_user_cache", return_value=None)
    @patch(_REPO_MODELLO)
    @patch("apps.core.api.permissions.PermissionResolver")
    @patch("rest_framework_simplejwt.authentication.JWTAuthentication.authenticate")
    @patch("apps.vendite.api.views.fn_annulla_lotto_da_draft")
    def test_reset_lotto_draft_azione_dalla_riga(
        self, mocked_service, mock_auth, resolver, repo_cls, _mock_load, _mock_save,
    ):
        _riga_annullo(repo_cls, "azione_di_prova")
        mock_auth.return_value = (operatore_di_prova(user_id=42), None)
        resolver.is_super_admin.return_value = False
        resolver.check_azione.return_value = False
        resolver.get_livello_area.return_value = "TUTTO"
        response = self.client.post(
            "/api/v1/vendite/lotti/123/reset-draft/",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "idem-perm-riga-1"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(resolver.check_azione.call_args.args[1], "azione_di_prova")
        mocked_service.assert_not_called()

    # Scopo: la dichiarazione — verso lo stato d'annullo del vocabolario, e
    #        nessun `post_permission` accanto (vincerebbe sul passaggio).
    def test_reset_lotto_draft_dichiara_il_passaggio(self) -> None:
        from apps.core.api.permissions import PassaggioDocumento
        from apps.vendite.api.views import ApiResetLottoDraft

        self.assertEqual(ApiResetLottoDraft.post_passaggio, PassaggioDocumento(
            testata="vendite.fatturazione_lotti", documento_kwarg="lotto_id",
            stato_del_modello="annullo",
        ))
        self.assertIsNone(getattr(ApiResetLottoDraft, "post_permission", None))
