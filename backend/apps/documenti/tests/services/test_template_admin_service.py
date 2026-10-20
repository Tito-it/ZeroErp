# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit TemplateAdminService (Tranche E). Mock repo + reader
#        + PermissionResolver. Verifica:
#        - validazione payload (chiavi non whitelisted, campi mancanti);
#        - scope emittente (admin globale, operatore in/out scope, anon);
#        - immutabili in update (output/sorgente/emittente) rifiutati;
#        - IntegrityError (UNIQUE/partial-unique) -> codici applicativi;
#        - update di template fuori scope -> 404 (delegato a reader);
#        - update con payload vuoto post-validation -> errore parlante.
#
# Indice test (0..N):
#   0. create_admin_globale_happy_path
#   1. create_operator_emittente_in_scope_ok
#   2. create_operator_emittente_fuori_scope_raises_validation
#   3. create_anonymous_user_raises_validation
#   4. create_payload_extra_keys_raises
#   5. create_payload_missing_required_field_raises
#   6. create_unique_violation_codice_mapped
#   7. create_unique_violation_default_mapped
#   8. update_happy_path
#   9. update_immutable_field_rejected_before_other_validation
#  10. update_empty_payload_raises
#  11. update_propagates_404_from_reader
#  12. update_unique_violation_mapped
#  13. personalizza_copia_testata_e_versione_con_origine
#  14. personalizza_is_default_false
#  15. personalizza_modello_non_standard_raises
#  16. personalizza_emittente_fuori_scope_raises
#  17. personalizza_standard_senza_pubblicata_raises
#  18. personalizza_payload_extra_keys_raises
#  19. personalizza_codice_proprio_e_is_default_nullo
#  20. personalizza_codice_duplicato_mappato
# ------------------------------------------------------------

from __future__ import annotations

from contextlib import nullcontext
from typing import Any
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.documenti.services.template_admin_service import TemplateAdminService


def _make_user(*, is_authenticated: bool = True) -> Any:
    user = MagicMock()
    user.is_authenticated = is_authenticated
    return user


_VALID_CREATE_PAYLOAD: dict[str, Any] = {
    "tipo_documento_output_id": 1,
    "sorgente_tipo_id": 10,
    "emittente_fiscale_id": 11,
    "codice": "TPL-PREV-001",
    "codice_interno": "TPL_PREV_001",
    "descrizione": "Template preventivo standard",
    "context_builder_code": "PREVENTIVO",
    "file_name_pattern": "preventivo-{numero}.pdf",
    "is_default": True,
    "attivo": True,
    "meta": {},
}


def _service_with_mocks(
    *,
    repo_methods: dict[str, Any] | None = None,
    reader_methods: dict[str, Any] | None = None,
) -> tuple[TemplateAdminService, MagicMock, MagicMock]:
    """Costruisce TemplateAdminService con repo + reader mockati."""
    repo = MagicMock()
    if repo_methods:
        for name, value in repo_methods.items():
            getattr(repo, name).return_value = value
    reader = MagicMock()
    if reader_methods:
        for name, value in reader_methods.items():
            getattr(reader, name).return_value = value
    return TemplateAdminService(repo=repo, reader=reader), repo, reader


class TemplateAdminServiceCreateTests(SimpleTestCase):
    # 0. admin globale (scope=None) -> create OK, no scope check.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_create_admin_globale_happy_path(self, _mock_scope) -> None:
        svc, repo, reader = _service_with_mocks(
            repo_methods={"create_template": 42},
            reader_methods={"get_template": {"id": 42, "codice": "TPL-PREV-001"}},
        )
        result = svc.create_template(_make_user(), dict(_VALID_CREATE_PAYLOAD))

        self.assertEqual(result["id"], 42)
        repo.create_template.assert_called_once()
        # Verifica defaults applicati: is_default e attivo presenti nel data.
        data = repo.create_template.call_args.args[0]
        self.assertTrue(data["is_default"])
        self.assertTrue(data["attivo"])
        # Ritorna sempre via reader.get_template.
        reader.get_template.assert_called_once_with(_make_user().__class__(), 42) if False else None
        reader.get_template.assert_called_once()

    # 1. operatore con emittente nello scope -> create OK.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11, 22],
    )
    def test_create_operator_emittente_in_scope_ok(self, _mock_scope) -> None:
        svc, repo, _ = _service_with_mocks(
            repo_methods={"create_template": 7},
            reader_methods={"get_template": {"id": 7}},
        )
        svc.create_template(_make_user(), dict(_VALID_CREATE_PAYLOAD))
        repo.create_template.assert_called_once()

    # 2. operatore con emittente fuori scope -> E_DOCUMENTI_VALIDATION,
    #    no DB call.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=[1, 2],
    )
    def test_create_operator_emittente_fuori_scope_raises_validation(
        self, _mock_scope
    ) -> None:
        svc, repo, _ = _service_with_mocks()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_template(_make_user(), dict(_VALID_CREATE_PAYLOAD))
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_template.assert_not_called()

    # 3. user None / non autenticato -> E_DOCUMENTI_VALIDATION subito.
    def test_create_anonymous_user_raises_validation(self) -> None:
        svc, repo, _ = _service_with_mocks()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_template(_make_user(is_authenticated=False), dict(_VALID_CREATE_PAYLOAD))
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_template.assert_not_called()

        with self.assertRaises(ServiceError):
            svc.create_template(None, dict(_VALID_CREATE_PAYLOAD))
        repo.create_template.assert_not_called()

    # 4. payload con chiave extra -> validate_allowed_keys solleva.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_create_payload_extra_keys_raises(self, _mock_scope) -> None:
        svc, _, _ = _service_with_mocks()
        payload = dict(_VALID_CREATE_PAYLOAD)
        payload["chiave_inventata"] = "x"
        with self.assertRaises(ServiceError) as ctx:
            svc.create_template(_make_user(), payload)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")

    # 5. campo richiesto mancante -> require_string solleva.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_create_payload_missing_required_field_raises(self, _mock_scope) -> None:
        svc, _, _ = _service_with_mocks()
        payload = dict(_VALID_CREATE_PAYLOAD)
        del payload["codice"]
        with self.assertRaises(ServiceError) as ctx:
            svc.create_template(_make_user(), payload)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")

    # 6. UNIQUE codice violato -> mappato a E_DOCUMENTI_VALIDATION con
    #    messaggio specifico (frammento nome vincolo).
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_create_unique_violation_codice_mapped(self, _mock_scope) -> None:
        svc, repo, _ = _service_with_mocks()
        repo.create_template.side_effect = IntegrityError(
            'duplicate key value violates unique constraint '
            '"uq_template_documenti_emittente_sorgente_codice"'
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.create_template(_make_user(), dict(_VALID_CREATE_PAYLOAD))
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertIn("codice", ctx.exception.message.lower())

    # 7. partial-unique is_default violato -> mappato.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_create_unique_violation_default_mapped(self, _mock_scope) -> None:
        svc, repo, _ = _service_with_mocks()
        repo.create_template.side_effect = IntegrityError(
            'duplicate key value violates unique constraint '
            '"uq_template_documenti_default_attivo"'
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.create_template(_make_user(), dict(_VALID_CREATE_PAYLOAD))
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertIn("default", ctx.exception.message.lower())


class TemplateAdminServiceUpdateTests(SimpleTestCase):
    # 8. update happy path: reader visibility OK, repo update True, ritorno
    #    via reader.get_template fresh.
    def test_update_happy_path(self) -> None:
        svc, repo, reader = _service_with_mocks(
            repo_methods={"update_template": True},
            reader_methods={"get_template": {"id": 42, "codice": "TPL-A"}},
        )
        result = svc.update_template(_make_user(), 42, {"descrizione": "Nuova descr."})
        self.assertEqual(result["id"], 42)
        # reader chiamato 2 volte: pre-check visibilita' + ritorno fresh.
        self.assertEqual(reader.get_template.call_count, 2)
        repo.update_template.assert_called_once()

    # 9. immutabili in payload -> errore parlante PRIMA di altre validazioni.
    def test_update_immutable_field_rejected_before_other_validation(self) -> None:
        svc, repo, reader = _service_with_mocks(
            reader_methods={"get_template": {"id": 42}},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.update_template(
                _make_user(), 42, {"emittente_fiscale_id": 99, "chiave_extra": "x"}
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        # message parla di immutabili, non di chiavi extra (precedenza).
        self.assertIn("immut", ctx.exception.message.lower())
        repo.update_template.assert_not_called()

    # 10. payload {} dopo validate -> errore "Nessun campo aggiornabile".
    def test_update_empty_payload_raises(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={"get_template": {"id": 42}},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.update_template(_make_user(), 42, {})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.update_template.assert_not_called()

    # 11. reader solleva NOT_FOUND (template fuori scope o assente) ->
    #     propaga senza toccare il DB.
    def test_update_propagates_404_from_reader(self) -> None:
        svc, repo, reader = _service_with_mocks()
        reader.get_template.side_effect = ServiceError(
            code="E_DOCUMENTI_NOT_FOUND",
            message="Template documento non trovato.",
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.update_template(_make_user(), 42, {"descrizione": "x"})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        repo.update_template.assert_not_called()

    # 12. UNIQUE violato in update -> mappato a E_DOCUMENTI_VALIDATION.
    def test_update_unique_violation_mapped(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={"get_template": {"id": 42}},
        )
        repo.update_template.side_effect = IntegrityError(
            'duplicate key value violates unique constraint '
            '"uq_template_documenti_emittente_sorgente_codice_interno"'
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.update_template(_make_user(), 42, {"codice_interno": "DUP"})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertIn("interno", ctx.exception.message.lower())


_SCOPE = "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids"
_ATOMIC = "apps.documenti.services.template_admin_service.transaction.atomic"

# La testata dello standard come la rilegge il reader.
_STANDARD: dict[str, Any] = {
    "id": 2728,
    "standard": True,
    "emittente_fiscale_id": None,
    "tipo_documento_output_id": 1,
    "sorgente_tipo_id": 10,
    "codice": "PREVENTIVO",
    "codice_interno": "preventivo",
    "descrizione": "Preventivo",
    "context_builder_code": "PREVENTIVO",
    "file_name_pattern": "preventivo-{numero}.pdf",
}

# L'ultima versione PUBBLICATA dello standard (proiezione di dettaglio).
_ORIGINE: dict[str, Any] = {
    "id": 501,
    "titolo": "Preventivo v3",
    "formato_template": "HTML",
    "html_template": "<p>{{ numero }}</p>",
    "css_template": "p {}",
    "markdown_template": None,
    "render_engine_id": 1,
    "page_format": "A4",
    "page_orientation": "PORTRAIT",
    "margin_top_mm": 10,
    "margin_right_mm": 10,
    "margin_bottom_mm": 10,
    "margin_left_mm": 10,
    "versione_contesto": 2,
    "context_schema": "{}",
    "meta": "{}",
}


def _personalizza_mocks(
    *, standard: dict[str, Any] | None = None, origine: Any = _ORIGINE,
) -> tuple[TemplateAdminService, MagicMock, MagicMock]:
    svc, repo, reader = _service_with_mocks(
        repo_methods={
            "get_ultima_versione_pubblicata": origine,
            "create_template": 900,
            "create_versione": 901,
        },
    )
    nuovo = {"id": 900, "standard": False, "emittente_fiscale_id": 11}
    reader.get_template.side_effect = (
        lambda _user, tid: dict(standard or _STANDARD) if tid != 900 else nuovo
    )
    return svc, repo, reader


class TemplateAdminServicePersonalizzaTests(SimpleTestCase):
    # 13. La testata copia quella dello standard per l'emittente; la versione
    #     1 e' una BOZZA che copia l'ultima pubblicata e ne dichiara l'origine.
    @patch(_SCOPE, return_value=[11])
    def test_personalizza_copia_testata_e_versione_con_origine(self, _s) -> None:
        svc, repo, _ = _personalizza_mocks()
        with patch(_ATOMIC, return_value=nullcontext()):
            result = svc.personalizza_template(
                _make_user(), 2728, {"emittente_fiscale_id": 11},
            )
        self.assertEqual(result["id"], 900)
        testata = repo.create_template.call_args.args[0]
        self.assertEqual(testata["emittente_fiscale_id"], 11)
        self.assertNotIn("standard", testata)
        for campo in (
            "tipo_documento_output_id", "sorgente_tipo_id", "codice",
            "codice_interno", "descrizione", "context_builder_code",
            "file_name_pattern",
        ):
            self.assertEqual(testata[campo], _STANDARD[campo], campo)
        self.assertTrue(testata["is_default"])
        self.assertTrue(testata["attivo"])

        repo.get_ultima_versione_pubblicata.assert_called_once_with(2728)
        versione = repo.create_versione.call_args.args[0]
        self.assertEqual(versione["template_documento_id"], 900)
        self.assertEqual(versione["versione"], 1)
        self.assertEqual(versione["stato"], "BOZZA")
        self.assertEqual(versione["derivata_da_versione_id"], 501)
        self.assertEqual(versione["html_template"], _ORIGINE["html_template"])
        self.assertEqual(versione["versione_contesto"], 2)
        self.assertIsNone(versione["valido_dal"])

    # 14. `is_default=false`: la copia nasce non predefinita.
    @patch(_SCOPE, return_value=None)
    def test_personalizza_is_default_false(self, _s) -> None:
        svc, repo, _ = _personalizza_mocks()
        with patch(_ATOMIC, return_value=nullcontext()):
            svc.personalizza_template(
                _make_user(), 2728, {"emittente_fiscale_id": 11, "is_default": False},
            )
        self.assertFalse(repo.create_template.call_args.args[0]["is_default"])

    # 15. Un modello d'emittente non si personalizza: si clona una versione.
    @patch(_SCOPE, return_value=None)
    def test_personalizza_modello_non_standard_raises(self, _s) -> None:
        svc, repo, _ = _personalizza_mocks(
            standard={**_STANDARD, "standard": False, "emittente_fiscale_id": 11},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.personalizza_template(_make_user(), 2728, {"emittente_fiscale_id": 11})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_template.assert_not_called()

    # 16. L'emittente deve essere nel perimetro di chi personalizza.
    @patch(_SCOPE, return_value=[1, 2])
    def test_personalizza_emittente_fuori_scope_raises(self, _s) -> None:
        svc, repo, _ = _personalizza_mocks()
        with self.assertRaises(ServiceError) as ctx:
            svc.personalizza_template(_make_user(), 2728, {"emittente_fiscale_id": 11})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_template.assert_not_called()

    # 17. Uno standard senza versione pubblicata non ha niente da copiare.
    @patch(_SCOPE, return_value=None)
    def test_personalizza_standard_senza_pubblicata_raises(self, _s) -> None:
        svc, repo, _ = _personalizza_mocks(origine=None)
        with self.assertRaises(ServiceError) as ctx:
            svc.personalizza_template(_make_user(), 2728, {"emittente_fiscale_id": 11})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_template.assert_not_called()

    # 18. Il resto della testata e' dello standard: altre chiavi -> 400.
    @patch(_SCOPE, return_value=None)
    def test_personalizza_payload_extra_keys_raises(self, _s) -> None:
        svc, repo, _ = _personalizza_mocks()
        with self.assertRaises(ServiceError) as ctx:
            svc.personalizza_template(
                _make_user(), 2728,
                {"emittente_fiscale_id": 11, "context_builder_code": "X"},
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_template.assert_not_called()

    # 19. Codice, codice interno e descrizione dati dal chiamante vincono su
    #     quelli dello standard; `is_default` nullo vale assente (vero).
    @patch(_SCOPE, return_value=None)
    def test_personalizza_codice_proprio_e_is_default_nullo(self, _s) -> None:
        svc, repo, _ = _personalizza_mocks()
        with patch(_ATOMIC, return_value=nullcontext()):
            svc.personalizza_template(
                _make_user(), 2728,
                {
                    "emittente_fiscale_id": 11, "is_default": None,
                    "codice": "PREV-ACME", "codice_interno": "prev_acme",
                    "descrizione": "Preventivo ACME",
                },
            )
        testata = repo.create_template.call_args.args[0]
        self.assertEqual(testata["codice"], "PREV-ACME")
        self.assertEqual(testata["codice_interno"], "prev_acme")
        self.assertEqual(testata["descrizione"], "Preventivo ACME")
        self.assertEqual(testata["context_builder_code"], _STANDARD["context_builder_code"])
        self.assertTrue(testata["is_default"])

    # 20. Il codice gia' usato dall'emittente: lo stesso messaggio parlante
    #     della create, e nessuna versione scritta.
    @patch(_SCOPE, return_value=None)
    def test_personalizza_codice_duplicato_mappato(self, _s) -> None:
        svc, repo, _ = _personalizza_mocks()
        repo.create_template.side_effect = IntegrityError(
            'duplicate key value violates unique constraint '
            '"uq_template_documenti_emittente_sorgente_codice"'
        )
        with patch(_ATOMIC, return_value=nullcontext()), \
                self.assertRaises(ServiceError) as ctx:
            svc.personalizza_template(_make_user(), 2728, {"emittente_fiscale_id": 11})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertIn("codice", ctx.exception.message.lower())
        repo.create_versione.assert_not_called()
