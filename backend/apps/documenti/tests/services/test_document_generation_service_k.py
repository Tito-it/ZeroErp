# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `DocumentGenerationService` per i comandi Tranche K
#        (anteprima, list_documenti_per_sorgente, download). Mock-only.
#        Il file e' separato da `test_document_generation_service.py` per
#        contenere la lunghezza per Tranche.
#
#        Indice test (0..N):
#         0. anteprima_happy_path_no_persist
#         0b. anteprima_con_standard
#         1. anteprima_anon_user_raises_validation
#         2. anteprima_render_solleva_propaga_no_persist
#         3. anteprima_input_guard_su_id
#         4. list_per_sorgente_happy_path_paginato
#         5. list_per_sorgente_input_guard_su_id_non_positivo
#         6. list_per_sorgente_anon_user_raises_validation
#         7. download_happy_path_legge_storage_emit_scaricato
#         8. download_documento_inesistente_raises_not_found
#         9. download_file_principale_assente_raises_not_found
#        10. download_storage_read_fail_raises_storage_failed
#        11. download_emit_evento_fallisce_ritorna_comunque_bytes
#        12. download_input_guard_id_non_positivo
# ------------------------------------------------------------

from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_error_fakes import make_db_error
from apps.documenti.services.document_generation_service import (
    DocumentGenerationService,
)
from apps.documenti.tests.services.generazione_fakes import (
    make_user,
    patch_get_builder,
    patch_render,
    patch_scope,
    risolto,
    service_with_mocks,
    template_row,
    versione_row,
)


# =====================================================================
# Anteprima
# =====================================================================


class AnteprimaDocumentoTests(SimpleTestCase):
    """anteprima_documento: render senza persist (Decisione 30)."""

    # 0. happy path: ritorna pdf_bytes + nome_file, NESSUNA chiamata
    #    create_documento_generato/storage.write/emit_evento_documento.
    def test_anteprima_happy_path_no_persist(self) -> None:
        template = template_row()
        versione = versione_row()
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
            },
        )
        with patch_scope(None), patch_get_builder({"numero": 42}), \
                patch_render(b"PDF") as mock_render, \
                patch.object(DocumentGenerationService, "_risolutore_asset") as mock_ris:
            result = svc.anteprima_documento(
                make_user(),
                emittente_fiscale_id=11,
                sorgente_tipo_id=10,
                sorgente_id=100,
            )
        self.assertEqual(result["pdf_bytes"], b"PDF")
        # Gli asset: quelli dell'emittente del documento, solo attivi e validi.
        mock_ris.assert_called_once_with(11, solo_validi=True)
        self.assertIs(mock_render.call_args.kwargs["risolvi_asset"], mock_ris.return_value)
        self.assertEqual(result["nome_file"], "preventivo-42.pdf")
        self.assertEqual(result["mime_type"], "application/pdf")
        # Anche l'anteprima chiede al DB il patto versione/forma dei dati.
        repo.guard_versione_contesto.assert_called_once_with(12, 2)
        # Nessuna persistenza.
        repo.create_documento_generato.assert_not_called()
        repo.create_documento_generato_file.assert_not_called()
        repo.emit_evento_documento.assert_not_called()
        storage.write.assert_not_called()

    # 0b. anteprima con lo STANDARD (emittente NULL): passa la coerenza, e gli
    #     asset restano quelli dell'emittente del DOCUMENTO.
    def test_anteprima_con_standard(self) -> None:
        template = template_row(emittente=None, standard=True)
        svc, repo, _, _ = service_with_mocks(
            repo_methods={
                **risolto(template, livello="STANDARD"),
                "get_versione": versione_row(),
            },
        )
        with patch_scope([11]), patch_get_builder({"numero": 42}), \
                patch_render(b"PDF"), \
                patch.object(DocumentGenerationService, "_risolutore_asset") as mock_ris:
            result = svc.anteprima_documento(
                make_user(),
                emittente_fiscale_id=11,
                sorgente_tipo_id=10,
                sorgente_id=100,
            )
        self.assertEqual(result["pdf_bytes"], b"PDF")
        mock_ris.assert_called_once_with(11, solo_validi=True)

    # 1. user anon -> rifiutato pre-DB.
    def test_anteprima_anon_user_raises_validation(self) -> None:
        svc, repo, _, _ = service_with_mocks()
        with self.assertRaises(ServiceError) as ctx:
            svc.anteprima_documento(
                make_user(is_authenticated=False),
                emittente_fiscale_id=11,
                sorgente_tipo_id=10,
                sorgente_id=100,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.risolvi_template_applicabile.assert_not_called()

    # 2. render_pdf solleva -> propaga senza persist.
    def test_anteprima_render_solleva_propaga_no_persist(self) -> None:
        template = template_row()
        versione = versione_row()
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
            },
        )
        with patch_scope(None), patch_get_builder({"numero": 1}):
            with patch(
                "apps.documenti.services.document_generation_service.render_pdf",
                side_effect=ServiceError(
                    code="E_DOCUMENTI_RENDER_FAILED",
                    message="font missing",
                ),
            ):
                with self.assertRaises(ServiceError) as ctx:
                    svc.anteprima_documento(
                        make_user(),
                        emittente_fiscale_id=11,
                        sorgente_tipo_id=10,
                        sorgente_id=100,
                    )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 3. id non positivi -> rifiutati pre-DB.
    def test_anteprima_input_guard_su_id(self) -> None:
        svc, repo, _, _ = service_with_mocks()
        for override in [
            {"emittente_fiscale_id": 0},
            {"sorgente_tipo_id": -1},
            {"sorgente_id": 0},
        ]:
            with self.subTest(override=override):
                kwargs = {
                    "emittente_fiscale_id": 11,
                    "sorgente_tipo_id": 10,
                    "sorgente_id": 100,
                    **override,
                }
                with patch_scope(None):
                    with self.assertRaises(ServiceError) as ctx:
                        svc.anteprima_documento(make_user(), **kwargs)
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.risolvi_template_applicabile.assert_not_called()


# =====================================================================
# List per sorgente
# =====================================================================


class ListPerSorgenteTests(SimpleTestCase):
    """list_documenti_per_sorgente: paginato + scope + guards."""

    # 4. happy path: ritorna {results, total_count}.
    def test_list_per_sorgente_happy_path_paginato(self) -> None:
        svc, repo, _, _ = service_with_mocks(
            repo_methods={
                "list_documenti_per_sorgente": (
                    [{"id": 99, "uid": "uid-x"}],
                    1,
                ),
            },
        )
        with patch_scope([11, 22]):
            result = svc.list_documenti_per_sorgente(
                make_user(),
                sorgente_tipo_id=10,
                sorgente_id=100,
                limit=20,
                offset=0,
            )
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(len(result["results"]), 1)
        repo.list_documenti_per_sorgente.assert_called_once()
        kwargs = repo.list_documenti_per_sorgente.call_args.kwargs
        self.assertEqual(kwargs["emittente_ids_scope"], [11, 22])
        # La chiave con cui la stampa è scritta (giro D.1): la coppia del DB
        # per l'id dell'entità, la stessa di `genera_documento`.
        repo.chiave_sorgente.assert_called_once_with(sorgente_tipo_id=10, chiave="100")
        self.assertEqual(kwargs["sorgente_id"], 100)
        self.assertIsNone(kwargs["sorgente_uid"])
        self.assertEqual(kwargs["limit"], 20)
        self.assertEqual(kwargs["offset"], 0)

    # 5. id dell'entità non positivo -> VALIDATION pre-DB.
    def test_list_per_sorgente_input_guard_su_id_non_positivo(self) -> None:
        svc, repo, _, _ = service_with_mocks()
        for bad in (0, -1):
            with self.subTest(sorgente_id=bad):
                with patch_scope(None):
                    with self.assertRaises(ServiceError) as ctx:
                        svc.list_documenti_per_sorgente(
                            make_user(),
                            sorgente_tipo_id=10,
                            sorgente_id=bad,
                        )
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.chiave_sorgente.assert_not_called()
        repo.list_documenti_per_sorgente.assert_not_called()

    # 5-bis. documento che il DB non trova o non mostra: il codice di
    #        `script.fn_sorgente_chiave` arriva come ServiceError (la view lo
    #        rende 404, il tool AI lo riceve come errore di dominio), mai un
    #        DatabaseError grezzo.
    def test_list_per_sorgente_chiave_rifiutata_dal_db_e_service_error(self) -> None:
        svc, repo, _, _ = service_with_mocks()
        repo.chiave_sorgente.side_effect = make_db_error(
            "Riferimento sorgente non trovato", codice="E_SORG_NOT_FOUND",
        )
        with patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.list_documenti_per_sorgente(
                    make_user(), sorgente_tipo_id=10, sorgente_id=100,
                )
        self.assertEqual(ctx.exception.code, "E_SORG_NOT_FOUND")
        repo.list_documenti_per_sorgente.assert_not_called()

    # 6. user anon -> VALIDATION pre-DB.
    def test_list_per_sorgente_anon_user_raises_validation(self) -> None:
        svc, repo, _, _ = service_with_mocks()
        with self.assertRaises(ServiceError) as ctx:
            svc.list_documenti_per_sorgente(
                make_user(is_authenticated=False),
                sorgente_tipo_id=10,
                sorgente_id=100,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.list_documenti_per_sorgente.assert_not_called()


# =====================================================================
# Download
# =====================================================================


class DownloadDocumentoTests(SimpleTestCase):
    """download_documento: storage.read + emit `SCARICATO` (Decisione 31)."""

    # 7. happy path: legge storage + emit evento + ritorna bytes/metadati.
    def test_download_happy_path_legge_storage_emit_scaricato(self) -> None:
        documento = {
            "id": 99,
            "uid": "uid-x",
            "nome_file": "preventivo-1.pdf",
            "pdf_hash": "c" * 64,
        }
        file_row = {
            "storage_key": "documenti/11/abc.pdf",
            "mime_type": "application/pdf",
            "file_name": "preventivo-1.pdf",
            "file_size_bytes": 4096,
        }
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                "get_documento_generato": documento,
                "get_documento_generato_file_principale": file_row,
                "emit_evento_documento": 1,
            },
            storage_methods={
                "build_storage_uri": "filesystem:documenti/11/abc.pdf",
                "read": b"PDF-bytes",
            },
        )
        with patch_scope(None):
            with patch(
                "apps.documenti.services.document_generation_service.transaction.atomic",
            ):
                result = svc.download_documento(make_user(), 99)

        self.assertEqual(result["pdf_bytes"], b"PDF-bytes")
        self.assertEqual(result["nome_file"], "preventivo-1.pdf")
        self.assertEqual(result["mime_type"], "application/pdf")
        self.assertEqual(result["size_bytes"], 4096)
        # storage.read invocato con l'uri ricostruito da build_storage_uri.
        storage.build_storage_uri.assert_called_once_with("documenti/11/abc.pdf")
        storage.read.assert_called_once_with("filesystem:documenti/11/abc.pdf")
        # Evento SCARICATO emesso.
        repo.emit_evento_documento.assert_called_once()
        evento_data = repo.emit_evento_documento.call_args.args[0]
        self.assertEqual(evento_data["evento_tipo"], "SCARICATO")
        self.assertEqual(evento_data["esito"], "OK")
        self.assertEqual(evento_data["documento_generato_id"], 99)
        # Niente tx_id esplicito (Decisione 76).
        self.assertNotIn("tx_id", evento_data)

    # 8. documento inesistente -> NOT_FOUND, no read storage.
    def test_download_documento_inesistente_raises_not_found(self) -> None:
        svc, repo, _, storage = service_with_mocks(
            repo_methods={"get_documento_generato": None},
        )
        with patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.download_documento(make_user(), 999)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        storage.read.assert_not_called()
        repo.emit_evento_documento.assert_not_called()

    # 9. file principale assente -> NOT_FOUND (record DB orfano post-cleanup
    #    STORAGE_ORPHAN o documento creato senza file principale).
    def test_download_file_principale_assente_raises_not_found(self) -> None:
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                "get_documento_generato": {"id": 99, "nome_file": "x.pdf", "pdf_hash": "h"},
                "get_documento_generato_file_principale": None,
            },
        )
        with patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.download_documento(make_user(), 99)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        storage.read.assert_not_called()
        repo.emit_evento_documento.assert_not_called()

    # 10. storage.read solleva -> E_DOCUMENTI_STORAGE_FAILED (mappato).
    def test_download_storage_read_fail_raises_storage_failed(self) -> None:
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                "get_documento_generato": {"id": 99, "nome_file": "x.pdf", "pdf_hash": "h"},
                "get_documento_generato_file_principale": {
                    "storage_key": "documenti/11/abc.pdf",
                    "mime_type": "application/pdf",
                    "file_name": "x.pdf",
                    "file_size_bytes": 100,
                },
            },
            storage_methods={"build_storage_uri": "fs:abc"},
        )
        storage.read.side_effect = OSError("storage offline")
        with patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.download_documento(make_user(), 99)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_STORAGE_FAILED")
        # Niente evento se storage fail.
        repo.emit_evento_documento.assert_not_called()

    # 11. emit evento solleva -> log warning ma il download riesce comunque
    #     (audit best-effort, file e' la priorita').
    def test_download_emit_evento_fallisce_ritorna_comunque_bytes(self) -> None:
        svc, repo, _, _ = service_with_mocks(
            repo_methods={
                "get_documento_generato": {"id": 99, "nome_file": "x.pdf", "pdf_hash": "h"},
                "get_documento_generato_file_principale": {
                    "storage_key": "documenti/11/abc.pdf",
                    "mime_type": "application/pdf",
                    "file_name": "x.pdf",
                    "file_size_bytes": 100,
                },
            },
            storage_methods={"build_storage_uri": "fs:abc", "read": b"BYTES"},
        )
        repo.emit_evento_documento.side_effect = RuntimeError("DB issue")
        with patch_scope(None):
            with patch(
                "apps.documenti.services.document_generation_service.transaction.atomic",
            ):
                result = svc.download_documento(make_user(), 99)
        self.assertEqual(result["pdf_bytes"], b"BYTES")

    # 12. id non positivo -> VALIDATION pre-DB.
    def test_download_input_guard_id_non_positivo(self) -> None:
        svc, repo, _, _ = service_with_mocks()
        for bad in (0, -1):
            with self.subTest(id=bad):
                with patch_scope(None):
                    with self.assertRaises(ServiceError) as ctx:
                        svc.download_documento(make_user(), bad)
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.get_documento_generato.assert_not_called()
