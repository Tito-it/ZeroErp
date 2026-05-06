# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `DocumentGenerationService` (Tranche I). Mock-only:
#        repo + reader + storage + render_pdf + registry.get_builder +
#        PermissionResolver. Verifica:
#         - happy path: pipeline completa con resolution template/versione,
#           builder context, render, INSERT 3 record + storage.write,
#           ritorno con id/uid/storage_uri/hashes;
#         - autenticazione: anon/None -> E_DOCUMENTI_VALIDATION pre-DB;
#         - scope emittente: out-of-scope -> rifiutato;
#         - resolve template: via override id -> reader.get_template;
#           via default `is_default=true` -> repo.find_template_applicabile;
#           nessun match -> E_DOCUMENTI_NOT_FOUND;
#         - coerenza template-input: emittente o sorgente_tipo del template
#           diverso da quanto richiesto -> E_DOCUMENTI_VALIDATION;
#         - resolve versione PUBBLICATA: nessuna match -> NOT_FOUND;
#         - context_builder_code vuoto sul template -> VALIDATION;
#         - render fail (eccezione): propagato senza INSERT (Decisione 32);
#         - render output vuoto -> E_DOCUMENTI_RENDER_FAILED;
#         - file_name_pattern con variabile mancante -> RENDER_FAILED parlante;
#         - lookup tipo_file PDF_FINALE assente / non attivo -> VALIDATION;
#         - IntegrityError sul progressivo -> mappato;
#         - storage.write fail -> atomic rollback, no cleanup;
#         - commit fail post-write -> cleanup STORAGE_ORPHAN best-effort.
#
# Indice test (0..N):
#   0. genera_documento_happy_path_pipeline_completa
#   1. genera_documento_anon_user_raises_validation
#   2. genera_documento_emittente_fuori_scope_raises_validation
#   3. genera_documento_template_via_id_esplicito_usa_reader
#   4. genera_documento_template_default_via_find_applicabile
#   5. genera_documento_no_template_match_raises_not_found
#   6. genera_documento_template_emittente_incoerente_raises
#   7. genera_documento_template_sorgente_tipo_incoerente_raises
#   8. genera_documento_no_versione_pubblicata_raises_not_found
#   9. genera_documento_context_builder_code_vuoto_raises
#  10. genera_documento_render_pdf_solleva_propaga_no_db
#  11. genera_documento_render_pdf_empty_raises
#  12. genera_documento_file_name_pattern_var_mancante_raises
#  13. genera_documento_tipo_file_pdf_finale_mancante_raises
#  14. genera_documento_tipo_file_pdf_finale_non_attivo_raises
#  15. genera_documento_integrity_error_progressivo_mapped
#  16. genera_documento_storage_write_fail_no_cleanup
#  17. genera_documento_commit_fail_storage_orphan_cleanup
# ------------------------------------------------------------

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)


# Scopo: Sostituisce transaction.atomic con un context manager no-op
#        (SimpleTestCase non puo' aprire transazioni reali).
@contextmanager
def _no_op_atomic():
    yield


def _patch_transaction_atomic_noop():
    return patch(
        "apps.documenti.services.document_generation_service.transaction.atomic",
        side_effect=_no_op_atomic,
    )


# Scopo: Context manager che simula commit fail al `__exit__` per il
#        test STORAGE_ORPHAN cleanup.
class _CommitFailingAtomic:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, tb):
        if exc_type is None:
            raise IntegrityError("simulated commit failure")
        return False


# Scopo: User mock autenticato.
def _make_user(*, is_authenticated: bool = True, user_id: int = 5) -> Any:
    user = MagicMock()
    user.is_authenticated = is_authenticated
    user.id = user_id
    return user


def _template_row(
    *,
    template_id: int = 7,
    emittente: int = 11,
    sorgente_tipo: int = 10,
    tipo_output: int = 1,
    builder_code: str = "PREVENTIVO",
    file_name_pattern: str = "preventivo-{numero}.pdf",
    descrizione: str = "Preventivo standard",
) -> dict[str, Any]:
    return {
        "id": template_id,
        "codice": "TPL-PREV",
        "codice_interno": "TPL_PREV",
        "descrizione": descrizione,
        "emittente_fiscale_id": emittente,
        "sorgente_tipo_id": sorgente_tipo,
        "tipo_documento_output_id": tipo_output,
        "context_builder_code": builder_code,
        "file_name_pattern": file_name_pattern,
        "is_default": True,
        "attivo": True,
    }


def _versione_row(*, versione_id: int = 12) -> dict[str, Any]:
    return {
        "id": versione_id,
        "versione": 1,
        "stato": "PUBBLICATA",
        "html_template": "<p>{{ numero }}</p>",
        "css_template": "p { font-size: 10pt; }",
        "markdown_template": None,
        "render_engine_codice": "WEASYPRINT",
    }


def _service_with_mocks(
    *,
    repo_methods: dict[str, Any] | None = None,
    reader_methods: dict[str, Any] | None = None,
    storage_methods: dict[str, Any] | None = None,
) -> tuple[DocumentGenerationService, MagicMock, MagicMock, MagicMock]:
    repo = MagicMock()
    if repo_methods:
        for name, value in repo_methods.items():
            getattr(repo, name).return_value = value
    reader = MagicMock()
    if reader_methods:
        for name, value in reader_methods.items():
            getattr(reader, name).return_value = value
    storage = MagicMock()
    if storage_methods:
        for name, value in storage_methods.items():
            getattr(storage, name).return_value = value
    svc = DocumentGenerationService(
        repo=repo, reader=reader, storage=storage,
    )
    # Hook today() deterministico per i test (idempotente).
    svc._today = lambda: date(2026, 5, 4)  # type: ignore[method-assign]
    return svc, repo, reader, storage


def _patch_render(return_value: bytes = b"%PDF-1.4 fake"):
    return patch(
        "apps.documenti.services.document_generation_service.render_pdf",
        return_value=return_value,
    )


def _patch_get_builder(context: dict[str, Any] | None = None):
    """Patch registry.get_builder con un MagicMock ritornante un builder
    il cui `build_context` ritorna `context`."""
    builder = MagicMock()
    builder.build_context.return_value = context if context is not None else {"numero": 1}
    return patch(
        "apps.documenti.services.document_generation_service.get_builder",
        return_value=builder,
    )


def _patch_scope(value: list[int] | None):
    return patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_ids",
        return_value=value,
    )


# Argomenti default per `genera_documento`.
_GENERA_DEFAULT: dict[str, Any] = {
    "emittente_fiscale_id": 11,
    "sorgente_tipo_id": 10,
    "sorgente_id": 100,
    "sorgente_uid": "uid-100",
    "sorgente_riga": None,
}


# =====================================================================
# Happy path
# =====================================================================


class GeneraDocumentoHappyPathTests(SimpleTestCase):
    """Pipeline completa: resolve template + versione + builder + render + INSERTs."""

    # 0. happy path: tutti i mock OK, ritorno dict completo.
    def test_genera_documento_happy_path_pipeline_completa(self) -> None:
        template = _template_row()
        versione = _versione_row()
        svc, repo, reader, storage = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": versione,
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "0190a000-0000-0000-0000-000000000001"),
                "create_documento_generato_file": 123,
                "emit_evento_documento": 7,
                "get_tipo_file_documento_by_codice": {"id": 2, "codice": "PDF_FINALE", "attivo": True},
            },
            storage_methods={"write": "filesystem:documenti/11/abc.pdf"},
        )
        with _patch_scope(None), _patch_get_builder({"numero": 42}), _patch_render(b"PDF-bytes"):
            with _patch_transaction_atomic_noop():
                result = svc.genera_documento(
                    _make_user(),
                    **_GENERA_DEFAULT,
                )

        self.assertEqual(result["id"], 99)
        self.assertTrue(result["uid"].startswith("0190a000"))
        self.assertEqual(result["nome_file"], "preventivo-42.pdf")
        self.assertEqual(result["titolo"], "Preventivo standard")
        self.assertEqual(result["size_bytes"], len(b"PDF-bytes"))
        self.assertEqual(result["progressivo_sorgente"], 1)
        self.assertEqual(result["template_documento_id"], 7)
        self.assertEqual(result["template_versione_id"], 12)
        self.assertEqual(result["storage_uri"], "filesystem:documenti/11/abc.pdf")
        self.assertEqual(len(result["pdf_hash"]), 64)  # sha256 hex

        # Verifica chiamate repo nell'ordine atteso.
        repo.find_template_applicabile.assert_called_once()
        repo.get_versione_pubblicata_attiva.assert_called_once()
        repo.next_progressivo_sorgente.assert_called_once()
        repo.create_documento_generato.assert_called_once()
        repo.create_documento_generato_file.assert_called_once()
        repo.emit_evento_documento.assert_called_once()
        repo.get_tipo_file_documento_by_codice.assert_called_once_with("PDF_FINALE")

        # storage.write con storage_key derivata = documenti/<emittente>/<pdf_hash>.pdf.
        write_args = storage.write.call_args
        storage_key = write_args.args[0]
        self.assertTrue(storage_key.startswith("documenti/11/"))
        self.assertTrue(storage_key.endswith(".pdf"))
        self.assertEqual(write_args.args[1], b"PDF-bytes")
        self.assertEqual(write_args.kwargs.get("content_type"), "application/pdf")

        # Documento INSERT con context_json + hashes corretti.
        documento_data = repo.create_documento_generato.call_args.args[0]
        self.assertEqual(documento_data["template_documento_id"], 7)
        self.assertEqual(documento_data["template_versione_id"], 12)
        self.assertEqual(documento_data["sorgente_uid"], "uid-100")
        self.assertEqual(documento_data["progressivo_sorgente"], 1)
        self.assertEqual(documento_data["context_json"], {"numero": 42})
        self.assertEqual(len(documento_data["context_hash"]), 64)
        self.assertEqual(len(documento_data["template_hash"]), 64)
        self.assertEqual(len(documento_data["pdf_hash"]), 64)
        self.assertEqual(documento_data["generato_da_user_id"], 5)
        self.assertEqual(documento_data["emittente_fiscale_id"], 11)

        # File INSERT collegato al documento.
        file_data = repo.create_documento_generato_file.call_args.args[0]
        self.assertEqual(file_data["documento_generato_id"], 99)
        self.assertEqual(file_data["file_tipo_id"], 2)
        self.assertEqual(file_data["mime_type"], "application/pdf")
        self.assertEqual(file_data["file_name"], "preventivo-42.pdf")
        self.assertEqual(file_data["is_principale"], True)
        self.assertEqual(file_data["ordinamento"], 1)

        # Evento GENERATO senza tx_id (Decisione 76 — la popola automation).
        evento_data = repo.emit_evento_documento.call_args.args[0]
        self.assertEqual(evento_data["documento_generato_id"], 99)
        self.assertEqual(evento_data["evento_tipo"], "GENERATO")
        self.assertEqual(evento_data["esito"], "OK")
        self.assertEqual(evento_data["user_id"], 5)
        self.assertNotIn("tx_id", evento_data)


# =====================================================================
# Auth + scope
# =====================================================================


class GeneraDocumentoAuthScopeTests(SimpleTestCase):
    # 1. user anon o None -> E_DOCUMENTI_VALIDATION subito, no DB.
    def test_genera_documento_anon_user_raises_validation(self) -> None:
        svc, repo, _, storage = _service_with_mocks()
        with self.assertRaises(ServiceError) as ctx:
            svc.genera_documento(_make_user(is_authenticated=False), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.find_template_applicabile.assert_not_called()
        storage.write.assert_not_called()

        with self.assertRaises(ServiceError):
            svc.genera_documento(None, **_GENERA_DEFAULT)
        repo.find_template_applicabile.assert_not_called()

    # 2. operatore con emittente fuori scope -> rifiutato.
    def test_genera_documento_emittente_fuori_scope_raises_validation(self) -> None:
        svc, repo, _, storage = _service_with_mocks()
        with _patch_scope([1, 2]):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.find_template_applicabile.assert_not_called()
        storage.write.assert_not_called()


# =====================================================================
# Resolve template
# =====================================================================


class GeneraDocumentoResolveTemplateTests(SimpleTestCase):
    # 3. template via id esplicito -> reader.get_template, NO find_applicabile.
    def test_genera_documento_template_via_id_esplicito_usa_reader(self) -> None:
        template = _template_row(template_id=42)
        versione = _versione_row()
        svc, repo, reader, _ = _service_with_mocks(
            repo_methods={
                "get_versione_pubblicata_attiva": versione,
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "uid-x"),
                "create_documento_generato_file": 1,
                "emit_evento_documento": 1,
                "get_tipo_file_documento_by_codice": {"id": 2, "codice": "PDF_FINALE", "attivo": True},
            },
            reader_methods={"get_template": template},
            storage_methods={"write": "fs:x"},
        )
        with _patch_scope(None), _patch_get_builder({"numero": 1}), _patch_render():
            with _patch_transaction_atomic_noop():
                svc.genera_documento(
                    _make_user(),
                    template_documento_id=42,
                    **_GENERA_DEFAULT,
                )
        reader.get_template.assert_called_once()
        repo.find_template_applicabile.assert_not_called()

    # 4. nessun id -> find_template_applicabile via repo.
    def test_genera_documento_template_default_via_find_applicabile(self) -> None:
        template = _template_row()
        versione = _versione_row()
        svc, repo, reader, _ = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": versione,
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "uid-x"),
                "create_documento_generato_file": 1,
                "emit_evento_documento": 1,
                "get_tipo_file_documento_by_codice": {"id": 2, "codice": "PDF_FINALE", "attivo": True},
            },
            storage_methods={"write": "fs:x"},
        )
        with _patch_scope(None), _patch_get_builder({"numero": 1}), _patch_render():
            with _patch_transaction_atomic_noop():
                svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        repo.find_template_applicabile.assert_called_once()
        reader.get_template.assert_not_called()

    # 5. nessun template applicabile -> E_DOCUMENTI_NOT_FOUND. count_*_no_default
    #    a 0 = caso "nessun template per la coppia", messaggio generico.
    def test_genera_documento_no_template_match_raises_not_found(self) -> None:
        svc, repo, _, storage = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": None,
                "count_templates_attivi_no_default": 0,
            },
        )
        with _patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        # Caso "nessun template": messaggio generico, non quello "manca default".
        self.assertIn("Nessun template applicabile", ctx.exception.message)
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 5b. template attivi presenti per la coppia ma nessuno con is_default=true:
    #     l'errore deve essere parlante per l'admin (UX: fix con un click).
    def test_genera_documento_no_default_among_existing_raises_helpful(self) -> None:
        svc, repo, _, storage = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": None,
                "count_templates_attivi_no_default": 3,
            },
        )
        with _patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        self.assertIn("predefinito", ctx.exception.message)
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 6. template id esplicito ma emittente del template != richiesto -> rifiutato.
    def test_genera_documento_template_emittente_incoerente_raises(self) -> None:
        template = _template_row(emittente=22)  # mismatch su request emittente=11
        svc, repo, _, storage = _service_with_mocks(
            reader_methods={"get_template": template},
        )
        with _patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(
                    _make_user(),
                    template_documento_id=42,
                    **_GENERA_DEFAULT,
                )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertIn("emittente", ctx.exception.message.lower())
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 7. template id esplicito ma sorgente_tipo del template != richiesto.
    def test_genera_documento_template_sorgente_tipo_incoerente_raises(self) -> None:
        template = _template_row(sorgente_tipo=99)  # mismatch su request 10
        svc, repo, _, storage = _service_with_mocks(
            reader_methods={"get_template": template},
        )
        with _patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(
                    _make_user(),
                    template_documento_id=42,
                    **_GENERA_DEFAULT,
                )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertIn("sorgente", ctx.exception.message.lower())
        repo.create_documento_generato.assert_not_called()


# =====================================================================
# Resolve versione
# =====================================================================


class GeneraDocumentoResolveVersioneTests(SimpleTestCase):
    # 8. nessuna versione PUBBLICATA attiva -> E_DOCUMENTI_NOT_FOUND.
    def test_genera_documento_no_versione_pubblicata_raises_not_found(self) -> None:
        template = _template_row()
        svc, repo, _, storage = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": None,
            },
        )
        with _patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()


# =====================================================================
# Context builder + render + nome file
# =====================================================================


class GeneraDocumentoBuilderRenderTests(SimpleTestCase):
    # 9. context_builder_code vuoto sul template -> E_DOCUMENTI_VALIDATION.
    def test_genera_documento_context_builder_code_vuoto_raises(self) -> None:
        template = _template_row(builder_code="")
        versione = _versione_row()
        svc, repo, _, _ = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": versione,
            },
        )
        with _patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_documento_generato.assert_not_called()

    # 10. render_pdf solleva -> propagato senza INSERT (Decisione 32).
    def test_genera_documento_render_pdf_solleva_propaga_no_db(self) -> None:
        template = _template_row()
        versione = _versione_row()
        svc, repo, _, storage = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": versione,
            },
        )
        with _patch_scope(None), _patch_get_builder({"numero": 1}):
            with patch(
                "apps.documenti.services.document_generation_service.render_pdf",
                side_effect=ServiceError(
                    code="E_DOCUMENTI_RENDER_FAILED",
                    message="WeasyPrint missing font",
                ),
            ):
                with self.assertRaises(ServiceError) as ctx:
                    svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 11. render_pdf ritorna bytes vuoti -> E_DOCUMENTI_RENDER_FAILED.
    def test_genera_documento_render_pdf_empty_raises(self) -> None:
        template = _template_row()
        versione = _versione_row()
        svc, repo, _, _ = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": versione,
            },
        )
        with _patch_scope(None), _patch_get_builder({"numero": 1}), _patch_render(b""):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        repo.create_documento_generato.assert_not_called()

    # 12. file_name_pattern usa una variabile non presente nel context.
    def test_genera_documento_file_name_pattern_var_mancante_raises(self) -> None:
        template = _template_row(file_name_pattern="preventivo-{numero_inesistente}.pdf")
        versione = _versione_row()
        svc, repo, _, _ = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": versione,
            },
        )
        with _patch_scope(None), _patch_get_builder({"numero": 1}), _patch_render():
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        self.assertIn("file_name", ctx.exception.message.lower())
        repo.create_documento_generato.assert_not_called()


# =====================================================================
# Tipo file lookup
# =====================================================================


class GeneraDocumentoTipoFileTests(SimpleTestCase):
    # 13. tipo PDF_FINALE assente -> E_DOCUMENTI_VALIDATION pre-INSERT.
    def test_genera_documento_tipo_file_pdf_finale_mancante_raises(self) -> None:
        template = _template_row()
        versione = _versione_row()
        svc, repo, _, storage = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": versione,
                "get_tipo_file_documento_by_codice": None,
            },
        )
        with _patch_scope(None), _patch_get_builder({"numero": 1}), _patch_render():
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 14. tipo PDF_FINALE presente ma non attivo -> rifiutato.
    def test_genera_documento_tipo_file_pdf_finale_non_attivo_raises(self) -> None:
        template = _template_row()
        versione = _versione_row()
        svc, repo, _, storage = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": versione,
                "get_tipo_file_documento_by_codice": {
                    "id": 2, "codice": "PDF_FINALE", "attivo": False,
                },
            },
        )
        with _patch_scope(None), _patch_get_builder({"numero": 1}), _patch_render():
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()


# =====================================================================
# Integrity error + storage cleanup
# =====================================================================


class GeneraDocumentoTransactionalTests(SimpleTestCase):
    """Pattern transazionale: integrity error, write fail, commit fail."""

    # 15. IntegrityError uq_progressivo -> mappato a E_DOCUMENTI_VALIDATION.
    def test_genera_documento_integrity_error_progressivo_mapped(self) -> None:
        template = _template_row()
        versione = _versione_row()
        svc, repo, _, storage = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": versione,
                "next_progressivo_sorgente": 1,
                "get_tipo_file_documento_by_codice": {
                    "id": 2, "codice": "PDF_FINALE", "attivo": True,
                },
            },
        )
        repo.create_documento_generato.side_effect = IntegrityError(
            'duplicate key value violates unique constraint '
            '"uq_documenti_generati_sorgente_progressivo"'
        )
        with _patch_scope(None), _patch_get_builder({"numero": 1}), _patch_render():
            with _patch_transaction_atomic_noop():
                with self.assertRaises(ServiceError) as ctx:
                    svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertIn("progressivo", ctx.exception.message.lower())
        # storage.write non chiamato: INSERT prima di write nel try interno.
        storage.write.assert_not_called()

    # 16. storage.write fallisce -> atomic rollback, no cleanup.
    def test_genera_documento_storage_write_fail_no_cleanup(self) -> None:
        template = _template_row()
        versione = _versione_row()
        svc, repo, _, storage = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": versione,
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "uid-x"),
                "create_documento_generato_file": 1,
                "emit_evento_documento": 1,
                "get_tipo_file_documento_by_codice": {
                    "id": 2, "codice": "PDF_FINALE", "attivo": True,
                },
            },
        )
        storage.write.side_effect = OSError("disk full")
        with _patch_scope(None), _patch_get_builder({"numero": 1}), _patch_render():
            with _patch_transaction_atomic_noop():
                with self.assertRaises(OSError):
                    svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        repo.create_documento_generato.assert_called_once()
        # Niente cleanup: il file non e' mai stato scritto (storage_uri None).
        storage.delete.assert_not_called()

    # 18. context con Decimal/date -> orchestrator normalizza JSON-safe
    #     prima di passare a `create_documento_generato.context_json`. Senza
    #     normalizzazione psycopg solleverebbe TypeError sull'INSERT jsonb.
    def test_genera_documento_context_decimal_date_jsonificato(self) -> None:
        template = _template_row()
        versione = _versione_row()
        svc, repo, _, _ = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": versione,
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "uid-x"),
                "create_documento_generato_file": 1,
                "emit_evento_documento": 1,
                "get_tipo_file_documento_by_codice": {
                    "id": 2, "codice": "PDF_FINALE", "attivo": True,
                },
            },
            storage_methods={"write": "fs:x"},
        )
        # Context con tipi non-JSON-encodable nativamente.
        decimal_context = {
            "numero": 1,
            "totale": Decimal("123.45"),
            "data_doc": date(2026, 5, 4),
            "righe": [{"importo": Decimal("50.00")}],
        }
        with _patch_scope(None), _patch_get_builder(decimal_context), _patch_render():
            with _patch_transaction_atomic_noop():
                svc.genera_documento(_make_user(), **_GENERA_DEFAULT)

        documento_data = repo.create_documento_generato.call_args.args[0]
        json_ctx = documento_data["context_json"]
        # Nessun Decimal residuo: convertito a stringa via default=str.
        self.assertNotIsInstance(json_ctx["totale"], Decimal)
        self.assertEqual(json_ctx["totale"], "123.45")
        self.assertEqual(json_ctx["data_doc"], "2026-05-04")
        self.assertNotIsInstance(json_ctx["righe"][0]["importo"], Decimal)

    # 19. context_hash deterministico: due chiamate con stesso input ->
    #     stesso hash. Garantisce dedup logico promesso dalla doc Tranche I.
    def test_genera_documento_context_hash_deterministico(self) -> None:
        template = _template_row()
        versione = _versione_row()
        same_context = {"numero": 7, "voce": "X"}

        def _build_svc():
            svc, repo, _, _ = _service_with_mocks(
                repo_methods={
                    "find_template_applicabile": template,
                    "get_versione_pubblicata_attiva": versione,
                    "next_progressivo_sorgente": 1,
                    "create_documento_generato": (99, "uid-x"),
                    "create_documento_generato_file": 1,
                    "emit_evento_documento": 1,
                    "get_tipo_file_documento_by_codice": {
                        "id": 2, "codice": "PDF_FINALE", "attivo": True,
                    },
                },
                storage_methods={"write": "fs:x"},
            )
            return svc, repo

        with _patch_scope(None), _patch_get_builder(same_context), _patch_render(b"BYTES"):
            with _patch_transaction_atomic_noop():
                svc1, repo1 = _build_svc()
                svc1.genera_documento(_make_user(), **_GENERA_DEFAULT)
                svc2, repo2 = _build_svc()
                svc2.genera_documento(_make_user(), **_GENERA_DEFAULT)

        h1 = repo1.create_documento_generato.call_args.args[0]["context_hash"]
        h2 = repo2.create_documento_generato.call_args.args[0]["context_hash"]
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    # 20. input guard: id non positivi e sorgente_uid vuoto rifiutati pre-DB.
    def test_genera_documento_input_guard_su_input_scalari(self) -> None:
        svc, repo, _, _ = _service_with_mocks()
        bad_inputs = [
            {"emittente_fiscale_id": 0},
            {"emittente_fiscale_id": -1},
            {"sorgente_tipo_id": 0},
            {"sorgente_id": 0},
            {"sorgente_uid": ""},
            {"sorgente_uid": "   "},
            {"sorgente_riga": 0},
        ]
        for override in bad_inputs:
            with self.subTest(override=override):
                args = {**_GENERA_DEFAULT, **override}
                with _patch_scope(None):
                    with self.assertRaises(ServiceError) as ctx:
                        svc.genera_documento(_make_user(), **args)
                self.assertEqual(
                    ctx.exception.code, "E_DOCUMENTI_VALIDATION",
                )
        # Nessuna chiamata DB per nessuno degli input invalid.
        repo.find_template_applicabile.assert_not_called()
        repo.create_documento_generato.assert_not_called()

    # 17. commit DB fail post-write -> cleanup STORAGE_ORPHAN best-effort.
    @patch(
        "apps.documenti.services.document_generation_service.transaction.atomic",
        side_effect=lambda: _CommitFailingAtomic(),
    )
    def test_genera_documento_commit_fail_storage_orphan_cleanup(
        self, _mock_atomic
    ) -> None:
        template = _template_row()
        versione = _versione_row()
        svc, _, _, storage = _service_with_mocks(
            repo_methods={
                "find_template_applicabile": template,
                "get_versione_pubblicata_attiva": versione,
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "uid-x"),
                "create_documento_generato_file": 1,
                "emit_evento_documento": 1,
                "get_tipo_file_documento_by_codice": {
                    "id": 2, "codice": "PDF_FINALE", "attivo": True,
                },
            },
            storage_methods={"write": "fs:abc", "delete": True},
        )
        with _patch_scope(None), _patch_get_builder({"numero": 1}), _patch_render():
            with self.assertRaises(IntegrityError):
                svc.genera_documento(_make_user(), **_GENERA_DEFAULT)
        # Cleanup chiamato sull'uri del file scritto pre-commit.
        storage.write.assert_called_once()
        storage.delete.assert_called_once_with("fs:abc")
