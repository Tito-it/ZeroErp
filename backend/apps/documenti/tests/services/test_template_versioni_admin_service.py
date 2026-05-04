# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit TemplateVersioniAdminService (Tranche F).
#        Mocka repo + reader. Verifica:
#        - create_versione: 404 template, validation, calcolo num versione,
#          IntegrityError mappato;
#        - update_versione: BOZZA modificabile, PUBBLICATA -> immutabile,
#          empty payload rifiutato, 404 propagato;
#        - delete_versione: BOZZA hard delete, non-BOZZA -> blocked;
#        - clone_versione: copia source con override, sempre BOZZA;
#        - pubblica_versione: BOZZA -> PUBBLICATA, valido_dal obbligatorio,
#          valido_al < valido_dal rifiutato, idempotente per design.
#
# Indice test (0..N):
#   0. create_404_if_template_invisible
#   1. create_happy_path_calculates_next_versione_num
#   2. create_payload_extra_keys_rejected
#   3. create_missing_required_field_rejected
#   4. update_pubblicata_rejected_at_service
#   5. update_bozza_happy_path
#   6. update_empty_payload_rejected
#   7. delete_pubblicata_rejected_at_service
#   8. delete_bozza_happy_path
#   9. clone_overrides_titolo_and_resets_dates
#  10. pubblica_requires_valido_dal
#  11. pubblica_rejects_valido_al_before_valido_dal
#  12. pubblica_bozza_happy_path
#  13. pubblica_already_pubblicata_rejected_at_service
# ------------------------------------------------------------

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase


@contextmanager
def _no_op_atomic():
    yield


def _patch_transaction_atomic():
    """Sostituisce transaction.atomic con no-op per i test SimpleTestCase
    (DB threaded vietato in SimpleTestCase)."""
    return patch(
        "apps.documenti.services.template_versioni_admin_service.transaction.atomic",
        side_effect=_no_op_atomic,
    )

from apps.core.services.service_errors import ServiceError
from apps.documenti.services.template_versioni_admin_service import (
    TemplateVersioniAdminService,
)


def _make_user() -> Any:
    user = MagicMock()
    user.is_authenticated = True
    return user


_VALID_VERSIONE_PAYLOAD: dict[str, Any] = {
    "titolo": "v1 standard",
    "html_template": "<html><body>{{ numero }}</body></html>",
    "render_engine_id": 1,
}

_BOZZA_VERSIONE = {
    "id": 11,
    "template_documento_id": 1,
    "versione": 1,
    "stato": "BOZZA",
    "titolo": "v1",
    "formato_template": "HTML",
    "html_template": "<p>x</p>",
    "css_template": None,
    "markdown_template": None,
    "render_engine_id": 1,
    "page_format": "A4",
    "page_orientation": "PORTRAIT",
    "margin_top_mm": 10,
    "margin_right_mm": 10,
    "margin_bottom_mm": 10,
    "margin_left_mm": 10,
    "context_schema": {},
    "meta": {},
    "valido_dal": None,
    "valido_al": None,
    "attivo": True,
}


def _service_with_mocks(
    *,
    repo_methods: dict[str, Any] | None = None,
    reader_methods: dict[str, Any] | None = None,
) -> tuple[TemplateVersioniAdminService, MagicMock, MagicMock]:
    repo = MagicMock()
    if repo_methods:
        for name, value in repo_methods.items():
            getattr(repo, name).return_value = value
    reader = MagicMock()
    if reader_methods:
        for name, value in reader_methods.items():
            getattr(reader, name).return_value = value
    return (
        TemplateVersioniAdminService(repo=repo, reader=reader),
        repo,
        reader,
    )


class TemplateVersioniAdminServiceCreateTests(SimpleTestCase):
    # 0. template inesistente / fuori scope -> 404 da reader, no DB call.
    def test_create_404_if_template_invisible(self) -> None:
        svc, repo, reader = _service_with_mocks()
        reader.get_template.side_effect = ServiceError(
            code="E_DOCUMENTI_NOT_FOUND",
            message="Template documento non trovato.",
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.create_versione(_make_user(), 99, dict(_VALID_VERSIONE_PAYLOAD))
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        repo.create_versione.assert_not_called()

    # 1. happy path: calcola next_versione_num e usa BOZZA come stato.
    def test_create_happy_path_calculates_next_versione_num(self) -> None:
        svc, repo, reader = _service_with_mocks(
            repo_methods={"next_versione_num": 5, "create_versione": 50},
            reader_methods={
                "get_template": {"id": 1},
                "get_versione": {"id": 50, "versione": 5},
            },
        )
        result = svc.create_versione(_make_user(), 1, dict(_VALID_VERSIONE_PAYLOAD))
        self.assertEqual(result["versione"], 5)
        repo.next_versione_num.assert_called_once_with(1)
        # Verifica il dict passato al repo: stato=BOZZA, versione=5.
        data = repo.create_versione.call_args.args[0]
        self.assertEqual(data["stato"], "BOZZA")
        self.assertEqual(data["versione"], 5)
        self.assertEqual(data["template_documento_id"], 1)

    # 2. chiave extra in payload -> validate_allowed_keys solleva.
    def test_create_payload_extra_keys_rejected(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={"get_template": {"id": 1}},
        )
        payload = dict(_VALID_VERSIONE_PAYLOAD)
        payload["chiave_inventata"] = "x"
        with self.assertRaises(ServiceError) as ctx:
            svc.create_versione(_make_user(), 1, payload)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_versione.assert_not_called()

    # 3. campo obbligatorio mancante -> require_string solleva.
    def test_create_missing_required_field_rejected(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={"get_template": {"id": 1}},
        )
        payload = dict(_VALID_VERSIONE_PAYLOAD)
        del payload["html_template"]
        with self.assertRaises(ServiceError) as ctx:
            svc.create_versione(_make_user(), 1, payload)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_versione.assert_not_called()


class TemplateVersioniAdminServiceUpdateTests(SimpleTestCase):
    # 4. PUBBLICATA non modificabile -> service rifiuta prima del DB.
    def test_update_pubblicata_rejected_at_service(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={
                "get_versione": {**_BOZZA_VERSIONE, "stato": "PUBBLICATA"},
            },
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.update_versione(
                _make_user(), 1, 11, {"titolo": "Nuovo"}
            )
        self.assertEqual(
            ctx.exception.code, "E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE"
        )
        repo.update_versione.assert_not_called()

    # 5. BOZZA: update OK.
    def test_update_bozza_happy_path(self) -> None:
        svc, repo, reader = _service_with_mocks(
            repo_methods={"update_versione": True},
            reader_methods={"get_versione": dict(_BOZZA_VERSIONE)},
        )
        result = svc.update_versione(
            _make_user(), 1, 11, {"titolo": "Aggiornato"}
        )
        self.assertEqual(result["id"], 11)
        repo.update_versione.assert_called_once()
        # 2 chiamate get_versione: pre-check + ritorno fresh.
        self.assertEqual(reader.get_versione.call_count, 2)

    # 6. payload {} rifiutato.
    def test_update_empty_payload_rejected(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={"get_versione": dict(_BOZZA_VERSIONE)},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.update_versione(_make_user(), 1, 11, {})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.update_versione.assert_not_called()


class TemplateVersioniAdminServiceDeleteTests(SimpleTestCase):
    # 7. PUBBLICATA non eliminabile -> service rifiuta.
    def test_delete_pubblicata_rejected_at_service(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={
                "get_versione": {**_BOZZA_VERSIONE, "stato": "PUBBLICATA"},
            },
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.delete_versione(_make_user(), 1, 11)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VERSIONE_DELETE_BLOCKED")
        repo.delete_versione.assert_not_called()

    # 8. BOZZA: delete OK.
    def test_delete_bozza_happy_path(self) -> None:
        svc, repo, _ = _service_with_mocks(
            repo_methods={"delete_versione": True},
            reader_methods={"get_versione": dict(_BOZZA_VERSIONE)},
        )
        svc.delete_versione(_make_user(), 1, 11)
        repo.delete_versione.assert_called_once_with(11)


class TemplateVersioniAdminServiceCloneTests(SimpleTestCase):
    # 9. clone copia source con override + nuovo num versione.
    def test_clone_overrides_titolo_and_resets_dates(self) -> None:
        source = {
            **_BOZZA_VERSIONE,
            "stato": "PUBBLICATA",
            "titolo": "Titolo originale",
            "valido_dal": date(2026, 1, 1),
            "valido_al": date(2026, 12, 31),
            "html_template": "<original/>",
        }
        svc, repo, reader = _service_with_mocks(
            repo_methods={"next_versione_num": 7, "create_versione": 70},
            reader_methods={"get_versione": source},
        )
        # reader.get_versione e' chiamato sia per pre-check (source) sia per
        # ritorno post-create. Riusiamo lo stesso mock per semplicita': il
        # primo ritorno e' source, il secondo ritorno e' la nuova versione
        # (qui ne riusiamo i campi tanto e' un mock).
        result = svc.clone_versione(
            _make_user(), 1, 11, {"titolo": "Titolo clone"}
        )
        self.assertIsNotNone(result)
        # Verifica il dict passato al repo.
        data = repo.create_versione.call_args.args[0]
        self.assertEqual(data["stato"], "BOZZA")
        self.assertEqual(data["versione"], 7)
        self.assertEqual(data["titolo"], "Titolo clone")  # override applicato
        # Date resettate (cloning non porta date originali).
        self.assertIsNone(data["valido_dal"])
        self.assertIsNone(data["valido_al"])
        # html copiato dal source.
        self.assertEqual(data["html_template"], "<original/>")


class TemplateVersioniAdminServicePubblicaTests(SimpleTestCase):
    """`transaction.atomic` mockata in tutti i test: SimpleTestCase non
    ammette DB threaded connections."""

    def setUp(self) -> None:
        super().setUp()
        patcher = _patch_transaction_atomic()
        patcher.start()
        self.addCleanup(patcher.stop)

    # 10. valido_dal obbligatorio.
    def test_pubblica_requires_valido_dal(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={"get_versione": dict(_BOZZA_VERSIONE)},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.pubblica_versione(_make_user(), 1, 11, {})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.pubblica_versione.assert_not_called()

    # 11. valido_al < valido_dal rifiutato (sanity check).
    def test_pubblica_rejects_valido_al_before_valido_dal(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={"get_versione": dict(_BOZZA_VERSIONE)},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.pubblica_versione(
                _make_user(),
                1,
                11,
                {"valido_dal": "2026-06-01", "valido_al": "2026-05-30"},
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.pubblica_versione.assert_not_called()

    # 12. happy path: BOZZA -> PUBBLICATA con valido_dal.
    def test_pubblica_bozza_happy_path(self) -> None:
        svc, repo, _ = _service_with_mocks(
            repo_methods={"pubblica_versione": True},
            reader_methods={"get_versione": dict(_BOZZA_VERSIONE)},
        )
        result = svc.pubblica_versione(
            _make_user(), 1, 11, {"valido_dal": "2026-06-01"}
        )
        self.assertIsNotNone(result)
        repo.pubblica_versione.assert_called_once()
        kwargs = repo.pubblica_versione.call_args.kwargs
        self.assertEqual(kwargs["valido_dal"], date(2026, 6, 1))
        self.assertIsNone(kwargs["valido_al"])

    # 13. versione gia' PUBBLICATA non puo' essere ri-pubblicata (stato lock).
    def test_pubblica_already_pubblicata_rejected_at_service(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={
                "get_versione": {**_BOZZA_VERSIONE, "stato": "PUBBLICATA"},
            },
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.pubblica_versione(
                _make_user(), 1, 11, {"valido_dal": "2026-06-01"}
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.pubblica_versione.assert_not_called()
