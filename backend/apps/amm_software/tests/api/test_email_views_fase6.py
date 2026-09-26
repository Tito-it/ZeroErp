# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari API Fase 6 — capability test connessione SMTP
#        + sanitizzazione preview template email.
#        Mock EmailRepository/EmailDispatchService, no DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_detail_account_inactive_can_test_false — account non attivo → can_test=false + reason inactive
 2) test_detail_account_no_password_can_test_false — host SMTP reale ma no password → can_test=false + reason no_password
 3) test_detail_account_active_with_password_can_test_true — happy path → can_test=true, reason None
 4) test_detail_account_console_mode_can_test_true — host vuoto/placeholder → can_test=true (console mode)
 5) test_detail_strips_meta_and_has_smtp_password — campi grezzi rimossi, last_test_* presenti
 6) test_test_endpoint_persists_outcome_success — POST test SMTP success → meta updated SUCCESS
 7) test_test_endpoint_persists_outcome_failed — POST test SMTP failed → meta updated FAILED
 8) test_test_endpoint_returns_enriched_payload — response include can_test + last_test_*
 9) test_test_endpoint_account_not_found — POST con id inesistente → ServiceError
10) test_preview_sanitizes_corpo_html — script/event handler/javascript: rimossi dalla preview
11) test_preview_oggetto_not_sanitized — oggetto e' testo plain, render_template ma no sanitize
12) test_patch_payload_del_drawer_passa — PATCH account col payload reale del drawer → update_account
13) test_patch_chiave_estranea_rifiutata — PATCH account con chiave fuori contratto → 400 E_EMAIL_ADMIN
14) test_patch_template_payload_del_drawer_passa — PATCH template col payload reale del drawer
15) test_patch_template_chiave_estranea_rifiutata — PATCH template con chiave fuori contratto → 400
"""

import json
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.amm_software.api.email_views import (
    EmailAccountDetailView,
    EmailAccountTestView,
    EmailTemplateDetailView,
    EmailTemplatePreviewView,
)
from apps.core.services.error_manager import ServiceError


def _admin_request(method: str = "GET", body: dict | None = None) -> MagicMock:
    request = MagicMock()
    request.method = method
    user = MagicMock()
    user.id = 99
    user.is_authenticated = True
    user.is_superuser = True
    request.user = user
    request.query_params = {}
    if body is not None:
        request.body = json.dumps(body).encode("utf-8")
    return request


REPO_PATH = "apps.amm_software.api.email_views.EmailRepository"
DISPATCH_PATH = "apps.amm_software.api.email_views.EmailDispatchService"


# =================================================================
# EmailAccountDetailView — capability can_test/test_reason
# =================================================================


class TestEmailAccountDetailCapability(TestCase):
    """View GET /api/v1/amm-software/email-accounts/<id>/ — capability test (Fase 6)."""

    @patch(REPO_PATH)
    def test_detail_account_inactive_can_test_false(self, mock_repo_cls: MagicMock) -> None:
        # Scopo: account inattivo → can_test=False + reason "amm.email_test_reason_inactive".
        mock_repo_cls.return_value.get_account.return_value = {
            "id": 1, "codice": "MAIN", "attivo": False,
            "smtp_host": "smtp.example.it", "has_smtp_password": True,
            "meta": {},
        }
        view = EmailAccountDetailView()
        view.check_permissions = MagicMock()
        response = view.get(_admin_request(), 1)

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertFalse(body["data"]["can_test"])
        self.assertEqual(body["data"]["test_reason"], "amm.email_test_reason_inactive")

    @patch(REPO_PATH)
    def test_detail_account_no_password_can_test_false(self, mock_repo_cls: MagicMock) -> None:
        # Scopo: host SMTP reale + account attivo ma senza password → reason no_password.
        mock_repo_cls.return_value.get_account.return_value = {
            "id": 1, "codice": "MAIN", "attivo": True,
            "smtp_host": "smtp.example.it", "has_smtp_password": False,
            "meta": {},
        }
        view = EmailAccountDetailView()
        view.check_permissions = MagicMock()
        response = view.get(_admin_request(), 1)

        body = json.loads(response.content)
        self.assertFalse(body["data"]["can_test"])
        self.assertEqual(body["data"]["test_reason"], "amm.email_test_reason_no_password")

    @patch(REPO_PATH)
    def test_detail_account_active_with_password_can_test_true(self, mock_repo_cls: MagicMock) -> None:
        # Scopo: happy path → can_test=True, test_reason=None.
        mock_repo_cls.return_value.get_account.return_value = {
            "id": 1, "codice": "MAIN", "attivo": True,
            "smtp_host": "smtp.example.it", "has_smtp_password": True,
            "meta": {},
        }
        view = EmailAccountDetailView()
        view.check_permissions = MagicMock()
        response = view.get(_admin_request(), 1)

        body = json.loads(response.content)
        self.assertTrue(body["data"]["can_test"])
        self.assertIsNone(body["data"]["test_reason"])

    @patch(REPO_PATH)
    def test_detail_account_console_mode_can_test_true(self, mock_repo_cls: MagicMock) -> None:
        # Scopo: host vuoto o placeholder → console mode, test sempre OK
        # anche senza password, perche' non viene aperta connessione SMTP reale.
        for host in ("", "smtp.example.com"):
            with self.subTest(smtp_host=host):
                mock_repo_cls.return_value.get_account.return_value = {
                    "id": 1, "codice": "MAIN", "attivo": True,
                    "smtp_host": host, "has_smtp_password": False,
                    "meta": {},
                }
                view = EmailAccountDetailView()
                view.check_permissions = MagicMock()
                response = view.get(_admin_request(), 1)
                body = json.loads(response.content)
                self.assertTrue(body["data"]["can_test"])
                self.assertIsNone(body["data"]["test_reason"])

    @patch(REPO_PATH)
    def test_detail_strips_meta_and_has_smtp_password(self, mock_repo_cls: MagicMock) -> None:
        # Scopo: i campi grezzi `has_smtp_password` e `meta` non devono essere
        # esposti al FE; al loro posto last_test_at/_outcome/_message dal meta.
        mock_repo_cls.return_value.get_account.return_value = {
            "id": 1, "codice": "MAIN", "attivo": True,
            "smtp_host": "smtp.example.it", "has_smtp_password": True,
            "meta": {
                "last_test_outcome": "SUCCESS",
                "last_test_at": "2026-04-29T10:00:00+00:00",
                "last_test_message": "OK",
            },
        }
        view = EmailAccountDetailView()
        view.check_permissions = MagicMock()
        response = view.get(_admin_request(), 1)

        body = json.loads(response.content)
        data = body["data"]
        self.assertNotIn("has_smtp_password", data)
        self.assertNotIn("meta", data)
        self.assertEqual(data["last_test_outcome"], "SUCCESS")
        self.assertEqual(data["last_test_at"], "2026-04-29T10:00:00+00:00")
        self.assertEqual(data["last_test_message"], "OK")



# =================================================================
# EmailAccountDetailView — PATCH: chiavi estranee rifiutate (2026-09-26)
# =================================================================


class TestEmailAccountPatchChiavi(TestCase):
    """View PATCH /api/v1/amm-software/email-accounts/<id>/ — whitelist chiavi."""

    @patch(REPO_PATH)
    def test_patch_payload_del_drawer_passa(self, mock_repo_cls: MagicMock) -> None:
        # Scopo: il payload che il drawer manda davvero (DEFAULT_FORM di
        # EmailAccountDrawer, senza password) arriva al repository.
        repo = mock_repo_cls.return_value
        repo.get_account.return_value = {"id": 1, "codice": "MAIN", "attivo": True, "meta": {}}
        request = _admin_request("PATCH")
        request.data = {
            "codice": "main", "descrizione": "Principale", "smtp_host": "smtp.x.it",
            "smtp_port": 587, "smtp_use_tls": True, "smtp_use_ssl": False,
            "smtp_username": "u", "email_from": "a@x.it", "email_reply_to": "",
            "unita_organizzativa_id": None, "attivo": True,
        }
        view = EmailAccountDetailView()
        view.check_permissions = MagicMock()
        response = view.patch(request, 1)

        self.assertEqual(response.status_code, 200)
        kwargs = repo.update_account.call_args.kwargs
        self.assertEqual(kwargs["codice"], "MAIN")
        self.assertNotIn("smtp_password", kwargs)

    @patch(REPO_PATH)
    def test_patch_chiave_estranea_rifiutata(self, mock_repo_cls: MagicMock) -> None:
        # Scopo: ⛔ una chiave fuori contratto (qui `meta`, che scrive solo
        # l'endpoint di test) e' un 400 `E_EMAIL_ADMIN`, non uno scarto
        # silenzioso: il repository non viene toccato.
        repo = mock_repo_cls.return_value
        repo.get_account.return_value = {"id": 1, "codice": "MAIN", "attivo": True, "meta": {}}
        request = _admin_request("PATCH")
        request.data = {"descrizione": "X", "meta": {"last_test_outcome": "SUCCESS"}}
        view = EmailAccountDetailView()
        view.check_permissions = MagicMock()
        with self.assertRaises(ServiceError) as ctx:
            view.patch(request, 1)
        self.assertEqual(ctx.exception.code, "E_EMAIL_ADMIN")
        self.assertIn("meta", ctx.exception.detail)
        repo.update_account.assert_not_called()


class TestEmailTemplatePatchChiavi(TestCase):
    """View PATCH /api/v1/amm-software/email-templates/<id>/ — whitelist chiavi."""

    @patch(REPO_PATH)
    def test_patch_template_payload_del_drawer_passa(self, mock_repo_cls: MagicMock) -> None:
        # Scopo: il payload di `EmailTemplateDrawer` arriva al repository.
        repo = mock_repo_cls.return_value
        repo.get_template.return_value = {"id": 3, "codice": "T"}
        request = _admin_request("PATCH")
        request.data = {"oggetto": "Ciao", "corpo_html": "<p>x</p>", "corpo_testo": None}
        view = EmailTemplateDetailView()
        view.check_permissions = MagicMock()
        response = view.patch(request, 3)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(repo.update_template.call_args.kwargs["oggetto"], "Ciao")

    @patch(REPO_PATH)
    def test_patch_template_chiave_estranea_rifiutata(self, mock_repo_cls: MagicMock) -> None:
        # Scopo: ⛔ una chiave fuori contratto e' un 400 `E_EMAIL_ADMIN`, non
        # uno scarto silenzioso: il repository non viene toccato.
        repo = mock_repo_cls.return_value
        repo.get_template.return_value = {"id": 3, "codice": "T"}
        request = _admin_request("PATCH")
        request.data = {"oggetto": "Ciao", "campo_ignoto": 1}
        view = EmailTemplateDetailView()
        view.check_permissions = MagicMock()
        with self.assertRaises(ServiceError) as ctx:
            view.patch(request, 3)
        self.assertEqual(ctx.exception.code, "E_EMAIL_ADMIN")
        repo.update_template.assert_not_called()

# =================================================================
# EmailAccountTestView — POST persiste outcome + ritorna detail enriched
# =================================================================


class TestEmailAccountTestEndpoint(TestCase):
    """View POST /api/v1/amm-software/email-accounts/<id>/test/ (Fase 6)."""

    @patch(DISPATCH_PATH)
    @patch(REPO_PATH)
    def test_test_endpoint_persists_outcome_success(
        self, mock_repo_cls: MagicMock, mock_dispatch_cls: MagicMock
    ) -> None:
        # Scopo: test SMTP success → repo.update_account_last_test chiamato con SUCCESS.
        repo = mock_repo_cls.return_value
        repo.get_account.side_effect = [
            # Prima chiamata: verifica esistenza
            {"id": 1, "codice": "MAIN", "attivo": True, "smtp_host": "smtp.example.it",
             "has_smtp_password": True, "meta": {}},
            # Seconda chiamata: refresh post-test (con meta aggiornato)
            {"id": 1, "codice": "MAIN", "attivo": True, "smtp_host": "smtp.example.it",
             "has_smtp_password": True,
             "meta": {"last_test_outcome": "SUCCESS", "last_test_at": "now", "last_test_message": "OK"}},
        ]
        mock_dispatch_cls.return_value.test_connection.return_value = {
            "success": True, "message": "Connessione SMTP riuscita."
        }

        view = EmailAccountTestView()
        view.check_permissions = MagicMock()
        response = view.post(_admin_request("POST"), 1)

        self.assertEqual(response.status_code, 200)
        repo.update_account_last_test.assert_called_once()
        kwargs = repo.update_account_last_test.call_args.kwargs
        self.assertEqual(kwargs["outcome"], "SUCCESS")
        self.assertEqual(kwargs["message"], "Connessione SMTP riuscita.")
        self.assertIn("tested_at", kwargs)

    @patch(DISPATCH_PATH)
    @patch(REPO_PATH)
    def test_test_endpoint_persists_outcome_failed(
        self, mock_repo_cls: MagicMock, mock_dispatch_cls: MagicMock
    ) -> None:
        # Scopo: test SMTP failed → outcome FAILED in meta.
        repo = mock_repo_cls.return_value
        repo.get_account.side_effect = [
            {"id": 1, "codice": "MAIN", "attivo": True, "smtp_host": "smtp.example.it",
             "has_smtp_password": True, "meta": {}},
            {"id": 1, "codice": "MAIN", "attivo": True, "smtp_host": "smtp.example.it",
             "has_smtp_password": True,
             "meta": {"last_test_outcome": "FAILED", "last_test_at": "now",
                      "last_test_message": "Errore SMTP: timeout"}},
        ]
        mock_dispatch_cls.return_value.test_connection.return_value = {
            "success": False, "message": "Errore SMTP: timeout"
        }

        view = EmailAccountTestView()
        view.check_permissions = MagicMock()
        response = view.post(_admin_request("POST"), 1)

        self.assertEqual(response.status_code, 200)
        kwargs = repo.update_account_last_test.call_args.kwargs
        self.assertEqual(kwargs["outcome"], "FAILED")
        self.assertEqual(kwargs["message"], "Errore SMTP: timeout")

    @patch(DISPATCH_PATH)
    @patch(REPO_PATH)
    def test_test_endpoint_returns_enriched_payload(
        self, mock_repo_cls: MagicMock, mock_dispatch_cls: MagicMock
    ) -> None:
        # Scopo: response include success + message + capability + last_test_*.
        repo = mock_repo_cls.return_value
        repo.get_account.side_effect = [
            {"id": 1, "codice": "MAIN", "attivo": True, "smtp_host": "smtp.example.it",
             "has_smtp_password": True, "meta": {}},
            {"id": 1, "codice": "MAIN", "attivo": True, "smtp_host": "smtp.example.it",
             "has_smtp_password": True,
             "meta": {"last_test_outcome": "SUCCESS",
                      "last_test_at": "2026-04-29T10:00:00+00:00",
                      "last_test_message": "OK"}},
        ]
        mock_dispatch_cls.return_value.test_connection.return_value = {
            "success": True, "message": "OK"
        }

        view = EmailAccountTestView()
        view.check_permissions = MagicMock()
        response = view.post(_admin_request("POST"), 1)
        body = json.loads(response.content)
        data = body["data"]

        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "OK")
        self.assertTrue(data["can_test"])
        self.assertIsNone(data["test_reason"])
        self.assertEqual(data["last_test_outcome"], "SUCCESS")
        self.assertEqual(data["last_test_at"], "2026-04-29T10:00:00+00:00")

    @patch(DISPATCH_PATH)
    @patch(REPO_PATH)
    def test_test_endpoint_account_not_found(
        self, mock_repo_cls: MagicMock, mock_dispatch_cls: MagicMock
    ) -> None:
        # Scopo: id inesistente → ServiceError prima del test SMTP (no chiamata dispatch).
        repo = mock_repo_cls.return_value
        repo.get_account.return_value = None

        view = EmailAccountTestView()
        view.check_permissions = MagicMock()
        with self.assertRaises(ServiceError):
            view.post(_admin_request("POST"), 9999)

        mock_dispatch_cls.return_value.test_connection.assert_not_called()
        repo.update_account_last_test.assert_not_called()


# =================================================================
# EmailTemplatePreviewView — sanitize HTML
# =================================================================


class TestEmailTemplatePreviewSanitize(TestCase):
    """View POST /api/v1/amm-software/email-templates/<id>/preview/ (Fase 6)."""

    @patch(DISPATCH_PATH)
    @patch(REPO_PATH)
    def test_preview_sanitizes_corpo_html(
        self, mock_repo_cls: MagicMock, mock_dispatch_cls: MagicMock
    ) -> None:
        # Scopo: il corpo_html nella response NON deve contenere tag/attr pericolosi.
        # Whitelist gestita da sanitize_email_html (testato isolatamente).
        repo = mock_repo_cls.return_value
        repo.get_template.return_value = {
            "id": 1, "oggetto": "Hello {{nome}}",
            "corpo_html": '<p>Hi {{nome}}</p><script>alert(1)</script><a href="javascript:bad()">x</a>',
            "corpo_testo": None,
        }
        # render_template e' deterministico: sostituisce {{nome}} con il valore.
        svc = mock_dispatch_cls.return_value
        svc.render_template.side_effect = lambda text, vars_: text.replace(
            "{{nome}}", vars_.get("nome", "")
        )

        view = EmailTemplatePreviewView()
        view.check_permissions = MagicMock()
        response = view.post(_admin_request("POST", body={"variabili": {"nome": "Tid"}}), 1)

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        corpo = body["data"]["corpo_html"]
        self.assertNotIn("<script>", corpo)
        self.assertNotIn("alert(1)", corpo)
        self.assertNotIn("javascript:", corpo)
        self.assertIn("Hi Tid", corpo)

    @patch(DISPATCH_PATH)
    @patch(REPO_PATH)
    def test_preview_oggetto_not_sanitized(
        self, mock_repo_cls: MagicMock, mock_dispatch_cls: MagicMock
    ) -> None:
        # Scopo: l'oggetto e' testo (Subject header), non HTML — non sanitizzato.
        # Importante per evitare che un < o > letterali vengano escapati.
        mock_repo_cls.return_value.get_template.return_value = {
            "id": 1, "oggetto": "Re: 1 < 2", "corpo_html": "<p>x</p>", "corpo_testo": None,
        }
        mock_dispatch_cls.return_value.render_template.side_effect = lambda t, v: t

        view = EmailTemplatePreviewView()
        view.check_permissions = MagicMock()
        response = view.post(_admin_request("POST", body={"variabili": {}}), 1)

        body = json.loads(response.content)
        self.assertEqual(body["data"]["oggetto"], "Re: 1 < 2")
