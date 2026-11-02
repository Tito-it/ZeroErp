# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#          valido_al < valido_dal delegato al DB, idempotente per design.
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
#  11. pubblica_delega_ordine_date_al_db
#  12. pubblica_bozza_happy_path
#  13. pubblica_already_pubblicata_rejected_at_service
#  14. pubblica_overlap_mappato_a_codice_dedicato
#  15. create_senza_forma_dei_dati_rifiutata (2026-09-30)
#  16. update_bozza_cambia_la_forma_dei_dati (2026-09-30)
#  17. clone_copia_la_forma_dei_dati (2026-09-30)
#  18. pubblica_passa_la_forma_del_builder_del_template (2026-09-30)
#  19. pubblica_builder_non_registrato_rifiutata (2026-09-30)
#  20. update_valori_di_vocabolario_vanno_al_db_senza_copia (2026-10-04)
#  21. update_fk_vocabolario_mappata_sul_campo (2026-10-04)
#
#  `versione_contesto` (brief-db-documenti-versione-contesto-template): la
#  forma dei dati che la versione legge. Obbligatoria in create, cambia solo
#  in BOZZA, il clone la copia; alla pubblicazione il service passa al verbo
#  DB la forma del builder del template (`CONTEXT_VERSION`), e il confronto
#  lo fa il DB (provato sul DB vero in test_versione_contesto_db).
# ------------------------------------------------------------

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
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
from apps.documenti.services.context_builders import (
    get_builder_del_template as _get_builder_vero,
)
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
    "versione_contesto": 2,
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
    "versione_contesto": 1,
    "context_schema": {},
    "meta": {},
    "valido_dal": None,
    "valido_al": None,
    "attivo": True,
}

# Il template della versione: il suo builder dice la forma da pubblicare.
_TEMPLATE = {"id": 1, "context_builder_code": "BUILDER_DI_PROVA"}


def _patch_builder(forma: int = 1):
    """Il registry dei builder con un builder finto per `BUILDER_DI_PROVA`:
    i test non dipendono dalla forma che i builder di produzione hanno oggi."""
    builder = MagicMock()
    builder.CONTEXT_VERSION = forma
    return patch(
        "apps.documenti.services.template_versioni_admin_service.get_builder_del_template",
        return_value=builder,
    )


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
        self.assertEqual(data["versione_contesto"], 2)

    # 15. La forma dei dati e' obbligatoria e senza default: assente, zero o
    #     non intera -> 400 col campo, nessuna scrittura.
    def test_create_senza_forma_dei_dati_rifiutata(self) -> None:
        for forma in (None, 0, -1, "due"):
            with self.subTest(forma=forma):
                svc, repo, _ = _service_with_mocks(
                    reader_methods={"get_template": {"id": 1}},
                )
                payload = dict(_VALID_VERSIONE_PAYLOAD)
                if forma is None:
                    del payload["versione_contesto"]
                else:
                    payload["versione_contesto"] = forma
                with self.assertRaises(ServiceError) as ctx:
                    svc.create_versione(_make_user(), 1, payload)
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
                self.assertEqual(ctx.exception.context.get("field"), "versione_contesto")
                repo.create_versione.assert_not_called()

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

    def test_update_bozza_accetta_margini_decimali_stringa(self) -> None:
        svc, repo, _ = _service_with_mocks(
            repo_methods={"update_versione": True},
            reader_methods={"get_versione": dict(_BOZZA_VERSIONE)},
        )

        svc.update_versione(
            _make_user(),
            1,
            11,
            {
                "margin_top_mm": "15.00",
                "margin_right_mm": "16.50",
                "margin_bottom_mm": 17,
                "margin_left_mm": "0",
            },
        )

        data = repo.update_versione.call_args.args[1]
        self.assertEqual(data["margin_top_mm"], 15.0)
        self.assertEqual(data["margin_right_mm"], 16.5)
        self.assertEqual(data["margin_bottom_mm"], 17)
        self.assertEqual(data["margin_left_mm"], 0.0)

    # 16. In BOZZA la forma si cambia: e' cosi' che si prepara la versione
    #     che leggera' la forma successiva (D-C4). Da PUBBLICATA no: lo dice
    #     il test 4 (service) e il trigger A1 a DB.
    def test_update_bozza_cambia_la_forma_dei_dati(self) -> None:
        svc, repo, _ = _service_with_mocks(
            repo_methods={"update_versione": True},
            reader_methods={"get_versione": dict(_BOZZA_VERSIONE)},
        )
        svc.update_versione(_make_user(), 1, 11, {"versione_contesto": 2})
        self.assertEqual(
            repo.update_versione.call_args.args[1], {"versione_contesto": 2},
        )

    # 6. payload {} rifiutato.
    def test_update_empty_payload_rejected(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={"get_versione": dict(_BOZZA_VERSIONE)},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.update_versione(_make_user(), 1, 11, {})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.update_versione.assert_not_called()


    # 20. Formato del sorgente, formato e orientamento della pagina: nessuna
    #     copia dell'insieme nel service (brief-db-vocabolari-versione-template,
    #     R-BE-V1). Un valore che il vocabolario non ha arriva al DB com'e':
    #     il giudice e' la FK. `A5` e `MARKDOWN` sono quelli che la copia del
    #     frontend offriva e il DB rifiutava (§2 del brief).
    def test_update_valori_di_vocabolario_vanno_al_db_senza_copia(self) -> None:
        svc, repo, _ = _service_with_mocks(
            repo_methods={"update_versione": True},
            reader_methods={"get_versione": dict(_BOZZA_VERSIONE)},
        )
        payload = {
            "formato_template": "MARKDOWN",
            "page_format": "A5",
            "page_orientation": "OBLIQUO",
        }
        svc.update_versione(_make_user(), 1, 11, dict(payload))
        self.assertEqual(repo.update_versione.call_args.args[1], payload)

    # 21. La FK di ciascun vocabolario, violata, e' un 400 sul suo campo: il
    #     form accende l'input giusto. Fino al 2026-10-04 la mappa nominava i
    #     tre CHECK, ritirati dal DB: la violazione sarebbe caduta nel
    #     ripiego senza campo.
    def test_update_fk_vocabolario_mappata_sul_campo(self) -> None:
        casi = {
            "fk_template_documenti_versioni_formati_template": "formato_template",
            "fk_template_documenti_versioni_formati_pagina": "page_format",
            "fk_template_documenti_versioni_orientamenti_pagina": "page_orientation",
        }
        for vincolo, campo in casi.items():
            with self.subTest(vincolo=vincolo):
                svc, repo, _ = _service_with_mocks(
                    reader_methods={"get_versione": dict(_BOZZA_VERSIONE)},
                )
                repo.update_versione.side_effect = IntegrityError(
                    'insert or update on table "template_documenti_versioni" '
                    f'violates foreign key constraint "{vincolo}"'
                )
                with self.assertRaises(ServiceError) as ctx:
                    svc.update_versione(_make_user(), 1, 11, {campo: "X"})
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
                self.assertEqual(ctx.exception.context.get("field"), campo)


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
    # 9. clone: la copia la fa il DB (`fn_crea_bozza_da_versione`, §10.3
    #    K-6), elenco dei campi e numero suoi. Il BE passa origine, modello e
    #    le sole sostituzioni date dal payload; le assenti arrivano None (le
    #    date: senza data, si fissano alla pubblicazione).
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
            repo_methods={"crea_bozza_da_versione": 70},
            reader_methods={"get_versione": source},
        )
        result = svc.clone_versione(
            _make_user(), 1, 11, {"titolo": "Titolo clone"}
        )
        self.assertIsNotNone(result)
        repo.crea_bozza_da_versione.assert_called_once_with(
            11, template_documento_id=1, titolo="Titolo clone",
            valido_dal=None, valido_al=None, attivo=None, meta=None,
        )
        repo.create_versione.assert_not_called()
        repo.next_versione_num.assert_not_called()
        # La versione restituita e' la nuova, riletta nel suo template.
        self.assertEqual(reader.get_versione.call_args.args[1:], (1, 70))

    # 17. Le sostituzioni del payload (date, attivo, meta) arrivano al DB; la
    #     forma dei dati e il corpo li copia lui dall'origine.
    def test_clone_copia_la_forma_dei_dati(self) -> None:
        svc, repo, _ = _service_with_mocks(
            repo_methods={"crea_bozza_da_versione": 40},
            reader_methods={
                "get_versione": {**_BOZZA_VERSIONE, "versione_contesto": 3},
            },
        )
        svc.clone_versione(_make_user(), 1, 11, {
            "valido_dal": "2026-11-01", "attivo": False, "meta": {"nota": "x"},
        })
        kwargs = repo.crea_bozza_da_versione.call_args.kwargs
        self.assertEqual(kwargs["valido_dal"], date(2026, 11, 1))
        self.assertIs(kwargs["attivo"], False)
        self.assertEqual(kwargs["meta"], {"nota": "x"})
        self.assertIsNone(kwargs["titolo"])


class TemplateVersioniAdminServicePubblicaTests(SimpleTestCase):
    """`transaction.atomic` mockata in tutti i test: SimpleTestCase non
    ammette DB threaded connections."""

    def setUp(self) -> None:
        super().setUp()
        patcher = _patch_transaction_atomic()
        patcher.start()
        self.addCleanup(patcher.stop)
        builder_patcher = _patch_builder(forma=4)
        self.get_builder = builder_patcher.start()
        self.addCleanup(builder_patcher.stop)

    # 10. valido_dal obbligatorio.
    def test_pubblica_requires_valido_dal(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={"get_versione": dict(_BOZZA_VERSIONE)},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.pubblica_versione(_make_user(), 1, 11, {})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.pubblica_versione.assert_not_called()

    # 11. valido_al < valido_dal NON lo giudica il service: arriva al DB, dove
    #     il guard comune delle date risponde E_DATA_AL_MINORE_DAL col campo
    #     (provato sul DB vero in apps/core/tests/db/test_date_validita_guard_comune_db).
    def test_pubblica_delega_ordine_date_al_db(self) -> None:
        svc, repo, _ = _service_with_mocks(
            repo_methods={"pubblica_versione": True},
            reader_methods={
                "get_versione": dict(_BOZZA_VERSIONE), "get_template": _TEMPLATE,
            },
        )
        svc.pubblica_versione(
            _make_user(),
            1,
            11,
            {"valido_dal": "2026-06-01", "valido_al": "2026-05-30"},
        )
        repo.pubblica_versione.assert_called_once_with(
            11, valido_dal=date(2026, 6, 1), valido_al=date(2026, 5, 30),
            versione_contesto=4,
        )

    # 12. happy path: BOZZA -> PUBBLICATA con valido_dal.
    def test_pubblica_bozza_happy_path(self) -> None:
        svc, repo, _ = _service_with_mocks(
            repo_methods={"pubblica_versione": True},
            reader_methods={
                "get_versione": dict(_BOZZA_VERSIONE), "get_template": _TEMPLATE,
            },
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

    # 14. EXCLUDE parziale ripristinato 2026-06-02 (migration 20260602-05):
    #     overlap fra versioni PUBBLICATE attive -> codice 409 dedicato
    #     E_DOCUMENTI_VERSIONE_OVERLAP (armonizzazione, prima era E_DOCUMENTI_VALIDATION).
    def test_pubblica_overlap_mappato_a_codice_dedicato(self) -> None:
        svc, repo, _ = _service_with_mocks(
            reader_methods={
                "get_versione": dict(_BOZZA_VERSIONE), "get_template": _TEMPLATE,
            },
        )
        repo.pubblica_versione.side_effect = IntegrityError(
            'conflicting key value violates exclusion constraint '
            '"ex_template_documenti_versioni_no_overlap_pubblicata"'
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.pubblica_versione(
                _make_user(), 1, 11, {"valido_dal": "2026-06-01"}
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VERSIONE_OVERLAP")
        self.assertIn("sovrappongono", (ctx.exception.message or "").lower())

    # 18. La forma che arriva al verbo e' quella del builder DEL TEMPLATE
    #     (risolto dal suo `context_builder_code`), non quella dichiarata
    #     dalla versione: il confronto e' del DB, che rifiuta se differiscono.
    def test_pubblica_passa_la_forma_del_builder_del_template(self) -> None:
        svc, repo, _ = _service_with_mocks(
            repo_methods={"pubblica_versione": True},
            reader_methods={
                "get_versione": {**_BOZZA_VERSIONE, "versione_contesto": 1},
                "get_template": _TEMPLATE,
            },
        )
        svc.pubblica_versione(_make_user(), 1, 11, {"valido_dal": "2026-06-01"})
        self.get_builder.assert_called_once_with(_TEMPLATE)
        self.assertEqual(repo.pubblica_versione.call_args.kwargs["versione_contesto"], 4)

    # 19. Un template il cui builder non e' registrato non ha una forma con cui
    #     confrontare: la pubblicazione si ferma al registry (400), senza
    #     arrivare al verbo. Registry vero, non il finto del setUp.
    def test_pubblica_builder_non_registrato_rifiutata(self) -> None:
        self.get_builder.side_effect = _get_builder_vero
        svc, repo, _ = _service_with_mocks(
            reader_methods={
                "get_versione": dict(_BOZZA_VERSIONE),
                "get_template": {"id": 1, "context_builder_code": "NON_REGISTRATO"},
            },
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.pubblica_versione(_make_user(), 1, 11, {"valido_dal": "2026-06-01"})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.pubblica_versione.assert_not_called()
