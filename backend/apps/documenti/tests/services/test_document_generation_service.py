# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `DocumentGenerationService` (Tranche I). Mock-only:
#        repo + reader + storage + render_pdf + get_builder_del_template +
#        PermissionResolver. Verifica:
#         - happy path: pipeline completa con resolution template/versione,
#           builder context, render, INSERT 3 record + storage.write,
#           ritorno con id/uid/storage_uri/hashes;
#         - autenticazione: anon/None -> E_DOCUMENTI_VALIDATION pre-DB;
#         - scope emittente: out-of-scope -> rifiutato;
#         - modello e versione: UNA domanda alla porta del DB
#           (repo.risolvi_template_applicabile), col modello indicato quando
#           c'e'; il modello indicato si legge prima dentro lo scope (404
#           fuori perimetro, la porta non parte); i rifiuti del DB (non
#           risolto, senza predefinito, non coerente, non stampabile) escono
#           col loro codice; lo standard stampa per l'emittente del documento;
#         - la versione e' quella detta dal DB, riletta per id (non leggibile =
#           invariante rotta);
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
#   3. genera_documento_modello_indicato_verificato_dalla_porta
#   4. genera_documento_template_default_via_risolvi_applicabile
#   5. genera_documento_no_template_match_raises_not_found
#   5b. genera_documento_no_default_among_existing_raises_helpful
#   5c. genera_documento_con_standard_passa_coerenza
#   5d. genera_documento_risolto_non_rileggibile_invariante
#   6. genera_documento_modello_indicato_non_coerente_codice_del_db
#   7. genera_documento_modello_indicato_fuori_perimetro_not_found
#   8. genera_documento_modello_indicato_non_stampabile_codice_del_db
#   8b. genera_documento_versione_risolta_non_rileggibile_invariante
#   9. genera_documento_context_builder_code_vuoto_raises
#  10. genera_documento_render_pdf_solleva_propaga_no_db
#  11. genera_documento_render_pdf_empty_raises
#  12. genera_documento_file_name_pattern_var_mancante_raises
#  13. genera_documento_tipo_file_pdf_finale_mancante_raises
#  14. genera_documento_tipo_file_pdf_finale_non_attivo_raises
#  15. genera_documento_integrity_error_progressivo_mapped
#  16. genera_documento_storage_write_fail_no_cleanup
#  17. genera_documento_commit_fail_storage_orphan_cleanup
#  21. genera_documento_con_allegati_persiste_file_secondari
#  22. genera_documento_allegato_mime_non_ammesso_raises
#  23. genera_documento_allegato_troppo_grande_raises
#  24. aggiungi_allegati_append_persiste_file (+ evento ALLEGATO_AGGIUNTO)
#  25. aggiungi_allegati_documento_inesistente_raises_not_found
#  26. aggiungi_allegati_lista_vuota_raises_validation
#  27. genera_documento_path_sistema_completo_audit_none (C-0)
#  28. genera_documento_scope_none_senza_canale_sistema_raises (C-0)
#  29. genera_documento_scope_esplicito_guard_emittente (C-0)
#  30. genera_documento_path_sistema_template_override_usa_repo (C-0)
#  31. genera_documento_forma_dei_dati_rifiutata_niente_render (2026-09-30)
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


# Argomenti default per `genera_documento`.
_GENERA_DEFAULT: dict[str, Any] = {
    "emittente_fiscale_id": 11,
    "sorgente_tipo_id": 10,
    "sorgente_id": 100,
    "sorgente_riga": None,
}


# =====================================================================
# Happy path
# =====================================================================


class GeneraDocumentoHappyPathTests(SimpleTestCase):
    """Pipeline completa: resolve template + versione + builder + render + INSERTs."""

    # 0. happy path: tutti i mock OK, ritorno dict completo.
    def test_genera_documento_happy_path_pipeline_completa(self) -> None:
        template = template_row()
        versione = versione_row()
        svc, repo, reader, storage = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "0190a000-0000-0000-0000-000000000001"),
                "create_documento_generato_file": 123,
                "emit_evento_documento": 7,
                "get_tipo_file_documento_by_codice": {"id": 2, "codice": "PDF_FINALE", "attivo": True},
            },
            storage_methods={"write": "filesystem:documenti/11/abc.pdf"},
        )
        with patch_scope(None), patch_get_builder({"numero": 42}), \
                patch_render(b"PDF-bytes") as mock_render, \
                patch.object(DocumentGenerationService, "_risolutore_asset") as mock_ris:
            with _patch_transaction_atomic_noop():
                result = svc.genera_documento(
                    make_user(),
                    **_GENERA_DEFAULT,
                )

        # Gli asset: quelli dell'emittente del template, solo attivi e validi.
        mock_ris.assert_called_once_with(11, solo_validi=True)
        self.assertIs(mock_render.call_args.kwargs["risolvi_asset"], mock_ris.return_value)

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
        repo.risolvi_template_applicabile.assert_called_once()
        # La versione e' quella scelta dalla risoluzione (P-2), riletta per id:
        # nessuna seconda ricerca con filtri del BE.
        repo.get_versione.assert_called_once_with(7, 12)
        # Il patto versione/forma dei dati chiesto al DB: la versione
        # pubblicata (12) e la forma del builder (2).
        repo.guard_versione_contesto.assert_called_once_with(12, 2)
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
        # La chiave del documento nella colonna del suo tipo (giro D.1): la
        # coppia del DB, scritta e usata per il progressivo — la stessa.
        repo.chiave_sorgente.assert_called_once_with(sorgente_tipo_id=10, chiave="100")
        self.assertEqual(documento_data["sorgente_id"], 100)
        self.assertIsNone(documento_data["sorgente_uid"])
        repo.next_progressivo_sorgente.assert_called_once_with(
            sorgente_tipo_id=10, sorgente_id=100, sorgente_uid=None, sorgente_riga=None,
        )
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
        svc, repo, _, storage = service_with_mocks()
        with self.assertRaises(ServiceError) as ctx:
            svc.genera_documento(make_user(is_authenticated=False), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.risolvi_template_applicabile.assert_not_called()
        storage.write.assert_not_called()

        with self.assertRaises(ServiceError):
            svc.genera_documento(None, **_GENERA_DEFAULT)
        repo.risolvi_template_applicabile.assert_not_called()

    # 2. operatore con emittente fuori scope -> rifiutato.
    def test_genera_documento_emittente_fuori_scope_raises_validation(self) -> None:
        svc, repo, _, storage = service_with_mocks()
        with patch_scope([1, 2]):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.risolvi_template_applicabile.assert_not_called()
        storage.write.assert_not_called()


# =====================================================================
# Resolve template
# =====================================================================


class GeneraDocumentoResolveTemplateTests(SimpleTestCase):
    # 3. modello indicato: si legge DENTRO lo scope, poi lo verifica la porta
    #    del DB (stessa funzione dei due livelli, quarto argomento); la
    #    versione e' quella che la porta restituisce.
    def test_genera_documento_modello_indicato_verificato_dalla_porta(self) -> None:
        template = template_row(template_id=42)
        svc, repo, reader, _ = service_with_mocks(
            repo_methods={
                "get_template": template,
                "risolvi_template_applicabile": {
                    "template_documento_id": 42, "livello": "INDICATO",
                    "template_versione_id": 12,
                },
                "get_versione": versione_row(),
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "uid-x"),
                "create_documento_generato_file": 1,
                "emit_evento_documento": 1,
                "get_tipo_file_documento_by_codice": {"id": 2, "codice": "PDF_FINALE", "attivo": True},
            },
            storage_methods={"write": "fs:x"},
        )
        with patch_scope([11]), patch_get_builder({"numero": 1}), patch_render():
            with _patch_transaction_atomic_noop():
                svc.genera_documento(
                    make_user(),
                    template_documento_id=42,
                    **_GENERA_DEFAULT,
                )
        repo.get_template.assert_called_once_with(42, emittente_ids_scope=[11])
        repo.risolvi_template_applicabile.assert_called_once_with(
            sorgente_tipo_id=10, emittente_fiscale_id=11,
            tipo_documento_output_id=None, template_documento_id=42,
        )
        repo.get_versione.assert_called_once_with(42, 12)
        reader.get_template.assert_not_called()

    # 4. nessun id -> la risoluzione del DB via repo.
    def test_genera_documento_template_default_via_risolvi_applicabile(self) -> None:
        template = template_row()
        versione = versione_row()
        svc, repo, reader, _ = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "uid-x"),
                "create_documento_generato_file": 1,
                "emit_evento_documento": 1,
                "get_tipo_file_documento_by_codice": {"id": 2, "codice": "PDF_FINALE", "attivo": True},
            },
            storage_methods={"write": "fs:x"},
        )
        with patch_scope(None), patch_get_builder({"numero": 1}), patch_render():
            with _patch_transaction_atomic_noop():
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        repo.risolvi_template_applicabile.assert_called_once()
        reader.get_template.assert_not_called()

    # 5. il DB non risolve (ne' modello dell'emittente ne' standard): il suo
    #    codice arriva com'e' al ServiceError, niente documento.
    def test_genera_documento_no_template_match_raises_not_found(self) -> None:
        svc, repo, _, storage = service_with_mocks()
        repo.risolvi_template_applicabile.side_effect = make_db_error(
            "Nessun modello di stampa per questo documento",
            codice="E_DOCUMENTI_TEMPLATE_NON_RISOLTO",
        )
        with patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_TEMPLATE_NON_RISOLTO")
        repo.get_template.assert_not_called()
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 5b. modelli suoi attivi ma nessun predefinito (strada B): il codice del
    #     DB, non lo standard e non un messaggio scritto in Python.
    def test_genera_documento_no_default_among_existing_raises_helpful(self) -> None:
        svc, repo, _, storage = service_with_mocks()
        repo.risolvi_template_applicabile.side_effect = make_db_error(
            "nessuno e' segnato come predefinito",
            codice="E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO",
        )
        with patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO")
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 5b-bis. la chiave della stampa (giro D.1): un rifiuto di
    #     `script.fn_sorgente_chiave` (qui il tipo spento) arriva come
    #     ServiceError col codice del DB — mai un DatabaseError grezzo, che
    #     dalla view uscirebbe 500 — e PRIMA di scegliere il modello.
    def test_genera_documento_chiave_rifiutata_dal_db_e_service_error(self) -> None:
        svc, repo, _, storage = service_with_mocks()
        repo.chiave_sorgente.side_effect = make_db_error(
            "Configurazione sorgente mancante o non attiva", codice="E_SORG_CONF",
        )
        with patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_SORG_CONF")
        repo.risolvi_template_applicabile.assert_not_called()
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 5c. risolto lo STANDARD (emittente NULL): passa la coerenza e stampa
    #     per l'emittente del documento.
    def test_genera_documento_con_standard_passa_coerenza(self) -> None:
        template = template_row(emittente=None, standard=True)
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                **risolto(template, livello="STANDARD"),
                "get_versione": versione_row(),
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "uid-x"),
                "create_documento_generato_file": 1,
                "emit_evento_documento": 1,
                "get_tipo_file_documento_by_codice": {"id": 2, "codice": "PDF_FINALE", "attivo": True},
            },
            storage_methods={"write": "fs:x"},
        )
        with patch_scope([11]), patch_get_builder({"numero": 1}), patch_render():
            with _patch_transaction_atomic_noop():
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        repo.risolvi_template_applicabile.assert_called_once_with(
            sorgente_tipo_id=10, emittente_fiscale_id=11, tipo_documento_output_id=None,
            template_documento_id=None,
        )
        # Lo standard si rilegge col perimetro dell'utente: il repository lo ammette.
        repo.get_template.assert_called_once_with(7, emittente_ids_scope=[11])
        documento_data = repo.create_documento_generato.call_args.args[0]
        self.assertEqual(documento_data["emittente_fiscale_id"], 11)
        self.assertEqual(documento_data["template_documento_id"], 7)

    # 5d. il DB risolve un id che poi non si rilegge: patto rotto ->
    #     RuntimeError (500 senza codice), non un 404 che lo maschera.
    def test_genera_documento_risolto_non_rileggibile_invariante(self) -> None:
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                **risolto(template_row()),
                "get_template": None,
            },
        )
        with patch_scope([11]):
            with self.assertRaises(RuntimeError):
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 6. modello indicato non adatto al documento (di un'altra azienda, di
    #    un'altra sorgente, di un altro tipo): lo dice il DB, col suo codice.
    #    Fino al 2026-10-21 lo diceva una copia BE della regola, che il tipo
    #    non lo guardava.
    def test_genera_documento_modello_indicato_non_coerente_codice_del_db(self) -> None:
        svc, repo, _, storage = service_with_mocks(
            repo_methods={"get_template": template_row(template_id=42, emittente=22)},
        )
        repo.risolvi_template_applicabile.side_effect = make_db_error(
            "Il modello di stampa «TPL-PREV» non e' adatto a questo documento: e' di un'altra azienda.",
            codice="E_DOCUMENTI_TEMPLATE_NON_COERENTE",
        )
        with patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(
                    make_user(),
                    template_documento_id=42,
                    **_GENERA_DEFAULT,
                )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_TEMPLATE_NON_COERENTE")
        repo.get_versione.assert_not_called()
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 7. modello indicato fuori dal perimetro dell'operatore (o inesistente):
    #    404 come ogni lettura, e la porta non parte — il suo rifiuto
    #    nominerebbe il modello di un'azienda che l'operatore non vede.
    def test_genera_documento_modello_indicato_fuori_perimetro_not_found(self) -> None:
        svc, repo, _, storage = service_with_mocks(
            repo_methods={"get_template": None},
        )
        with patch_scope([11]):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(
                    make_user(),
                    template_documento_id=42,
                    **_GENERA_DEFAULT,
                )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        repo.risolvi_template_applicabile.assert_not_called()
        storage.write.assert_not_called()


# =====================================================================
# Resolve versione
# =====================================================================


class GeneraDocumentoResolveVersioneTests(SimpleTestCase):
    # 8. modello indicato che oggi non puo' stampare (spento, o senza versione
    #    pubblicata valida oggi): il codice del DB, con la sede unica di «puo'
    #    stampare». Fino al 2026-10-21 il BE cercava la versione da se' e un
    #    modello spento stampava ancora.
    def test_genera_documento_modello_indicato_non_stampabile_codice_del_db(self) -> None:
        svc, repo, _, storage = service_with_mocks(
            repo_methods={"get_template": template_row(template_id=42)},
        )
        repo.risolvi_template_applicabile.side_effect = make_db_error(
            "Il modello di stampa «TPL-PREV» oggi non può stampare: è disattivato.",
            codice="E_DOCUMENTI_TEMPLATE_NON_STAMPABILE",
        )
        with patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(
                    make_user(), template_documento_id=42, **_GENERA_DEFAULT,
                )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_TEMPLATE_NON_STAMPABILE")
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 8b. la versione che la porta ha scelto non si rilegge -> il patto del DB
    #     e' rotto: RuntimeError, non un 404 dell'operatore.
    def test_genera_documento_versione_risolta_non_rileggibile_invariante(self) -> None:
        svc, repo, _, storage = service_with_mocks(
            repo_methods={**risolto(template_row()), "get_versione": None},
        )
        with patch_scope(None):
            with self.assertRaisesRegex(RuntimeError, "versione risolta"):
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()


# =====================================================================
# Context builder + render + nome file
# =====================================================================


class GeneraDocumentoBuilderRenderTests(SimpleTestCase):
    # 9. context_builder_code vuoto sul template -> E_DOCUMENTI_VALIDATION.
    def test_genera_documento_context_builder_code_vuoto_raises(self) -> None:
        template = template_row(builder_code="")
        versione = versione_row()
        svc, repo, _, _ = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
            },
        )
        with patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_documento_generato.assert_not_called()

    # 10. render_pdf solleva -> propagato senza INSERT (Decisione 32).
    def test_genera_documento_render_pdf_solleva_propaga_no_db(self) -> None:
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
                    message="WeasyPrint missing font",
                ),
            ):
                with self.assertRaises(ServiceError) as ctx:
                    svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 11. render_pdf ritorna bytes vuoti -> E_DOCUMENTI_RENDER_FAILED.
    def test_genera_documento_render_pdf_empty_raises(self) -> None:
        template = template_row()
        versione = versione_row()
        svc, repo, _, _ = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
            },
        )
        with patch_scope(None), patch_get_builder({"numero": 1}), patch_render(b""):
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        repo.create_documento_generato.assert_not_called()

    # 12. file_name_pattern usa una variabile non presente nel context.
    def test_genera_documento_file_name_pattern_var_mancante_raises(self) -> None:
        template = template_row(file_name_pattern="preventivo-{numero_inesistente}.pdf")
        versione = versione_row()
        svc, repo, _, _ = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
            },
        )
        with patch_scope(None), patch_get_builder({"numero": 1}), patch_render():
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_RENDER_FAILED")
        self.assertIn("file_name", ctx.exception.message.lower())
        repo.create_documento_generato.assert_not_called()


# =====================================================================
# Tipo file lookup
# =====================================================================


class GeneraDocumentoTipoFileTests(SimpleTestCase):
    # 13. tipo PDF_FINALE assente -> E_DOCUMENTI_VALIDATION pre-INSERT.
    def test_genera_documento_tipo_file_pdf_finale_mancante_raises(self) -> None:
        template = template_row()
        versione = versione_row()
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
                "get_tipo_file_documento_by_codice": None,
            },
        )
        with patch_scope(None), patch_get_builder({"numero": 1}), patch_render():
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 14. tipo PDF_FINALE presente ma non attivo -> rifiutato.
    def test_genera_documento_tipo_file_pdf_finale_non_attivo_raises(self) -> None:
        template = template_row()
        versione = versione_row()
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
                "get_tipo_file_documento_by_codice": {
                    "id": 2, "codice": "PDF_FINALE", "attivo": False,
                },
            },
        )
        with patch_scope(None), patch_get_builder({"numero": 1}), patch_render():
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
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
        template = template_row()
        versione = versione_row()
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
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
        with patch_scope(None), patch_get_builder({"numero": 1}), patch_render():
            with _patch_transaction_atomic_noop():
                with self.assertRaises(ServiceError) as ctx:
                    svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertIn("progressivo", ctx.exception.message.lower())
        # storage.write non chiamato: INSERT prima di write nel try interno.
        storage.write.assert_not_called()

    # 16. storage.write fallisce -> atomic rollback, no cleanup.
    def test_genera_documento_storage_write_fail_no_cleanup(self) -> None:
        template = template_row()
        versione = versione_row()
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
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
        with patch_scope(None), patch_get_builder({"numero": 1}), patch_render():
            with _patch_transaction_atomic_noop():
                with self.assertRaises(OSError):
                    svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        repo.create_documento_generato.assert_called_once()
        # Niente cleanup: il file non e' mai stato scritto (storage_uri None).
        storage.delete.assert_not_called()

    # 18. context con Decimal/date -> orchestrator normalizza JSON-safe
    #     prima di passare a `create_documento_generato.context_json`. Senza
    #     normalizzazione psycopg solleverebbe TypeError sull'INSERT jsonb.
    def test_genera_documento_context_decimal_date_jsonificato(self) -> None:
        template = template_row()
        versione = versione_row()
        svc, repo, _, _ = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
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
        with patch_scope(None), patch_get_builder(decimal_context), patch_render():
            with _patch_transaction_atomic_noop():
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)

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
        template = template_row()
        versione = versione_row()
        same_context = {"numero": 7, "voce": "X"}

        def _build_svc():
            svc, repo, _, _ = service_with_mocks(
                repo_methods={
                    **risolto(template),
                    "get_versione": versione,
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

        with patch_scope(None), patch_get_builder(same_context), patch_render(b"BYTES"):
            with _patch_transaction_atomic_noop():
                svc1, repo1 = _build_svc()
                svc1.genera_documento(make_user(), **_GENERA_DEFAULT)
                svc2, repo2 = _build_svc()
                svc2.genera_documento(make_user(), **_GENERA_DEFAULT)

        h1 = repo1.create_documento_generato.call_args.args[0]["context_hash"]
        h2 = repo2.create_documento_generato.call_args.args[0]["context_hash"]
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    # 20. input guard: id non positivi rifiutati pre-DB.
    def test_genera_documento_input_guard_su_input_scalari(self) -> None:
        svc, repo, _, _ = service_with_mocks()
        bad_inputs = [
            {"emittente_fiscale_id": 0},
            {"emittente_fiscale_id": -1},
            {"sorgente_tipo_id": 0},
            {"sorgente_id": 0},
            {"sorgente_riga": 0},
        ]
        for override in bad_inputs:
            with self.subTest(override=override):
                args = {**_GENERA_DEFAULT, **override}
                with patch_scope(None):
                    with self.assertRaises(ServiceError) as ctx:
                        svc.genera_documento(make_user(), **args)
                self.assertEqual(
                    ctx.exception.code, "E_DOCUMENTI_VALIDATION",
                )
        # Nessuna chiamata DB per nessuno degli input invalid.
        repo.risolvi_template_applicabile.assert_not_called()
        repo.chiave_sorgente.assert_not_called()
        repo.create_documento_generato.assert_not_called()

    # 17. commit DB fail post-write -> cleanup STORAGE_ORPHAN best-effort.
    @patch(
        "apps.documenti.services.document_generation_service.transaction.atomic",
        side_effect=lambda: _CommitFailingAtomic(),
    )
    def test_genera_documento_commit_fail_storage_orphan_cleanup(
        self, _mock_atomic
    ) -> None:
        template = template_row()
        versione = versione_row()
        svc, _, _, storage = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
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
        with patch_scope(None), patch_get_builder({"numero": 1}), patch_render():
            with self.assertRaises(IntegrityError):
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        # Cleanup chiamato sull'uri del file scritto pre-commit.
        storage.write.assert_called_once()
        storage.delete.assert_called_once_with("fs:abc")


# =====================================================================
# Allegati (file secondari)
# =====================================================================


# Scopo: Lookup tipo file multi-codice (PDF_FINALE + ALLEGATO) per i test
#        che generano documento con allegati.
def _tipo_file_lookup(codice: str) -> dict[str, Any] | None:
    return {
        "PDF_FINALE": {"id": 2, "codice": "PDF_FINALE", "attivo": True},
        "ALLEGATO": {"id": 9, "codice": "ALLEGATO", "attivo": True},
    }.get(codice)


# Scopo: Imposta un ParameterService mock sul service (limite size allegato).
def _mock_params(svc: DocumentGenerationService, max_mb: int = 25) -> None:
    params = MagicMock()
    params.get_parameter_int.return_value = max_mb
    svc._params = params  # type: ignore[attr-defined]


class GeneraDocumentoAllegatiTests(SimpleTestCase):
    """genera_documento con allegati: persist file secondari + validazione."""

    # 21. allegato valido -> 2 file persistiti (principale + allegato),
    #     allegato is_principale=False, ordinamento 2, tipo ALLEGATO.
    def test_genera_documento_con_allegati_persiste_file_secondari(self) -> None:
        template = template_row()
        versione = versione_row()
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "uid-x"),
                "create_documento_generato_file": 123,
                "emit_evento_documento": 1,
            },
            storage_methods={"write": "fs:x"},
        )
        repo.get_tipo_file_documento_by_codice.side_effect = _tipo_file_lookup
        _mock_params(svc)
        allegati = [{
            "file_bytes": b"%PDF-1.4 allegato",
            "mime_type": "application/pdf",
            "file_name": "condizioni.pdf",
        }]
        with patch_scope(None), patch_get_builder({"numero": 1}), patch_render():
            with _patch_transaction_atomic_noop():
                result = svc.genera_documento(
                    make_user(), allegati=allegati, **_GENERA_DEFAULT,
                )

        self.assertEqual(repo.create_documento_generato_file.call_count, 2)
        calls = repo.create_documento_generato_file.call_args_list
        principale = calls[0].args[0]
        allegato = calls[1].args[0]
        self.assertEqual(principale["is_principale"], True)
        self.assertEqual(principale["ordinamento"], 1)
        self.assertEqual(allegato["is_principale"], False)
        self.assertEqual(allegato["ordinamento"], 2)
        self.assertEqual(allegato["file_tipo_id"], 9)
        self.assertEqual(allegato["file_name"], "condizioni.pdf")
        self.assertEqual(allegato["mime_type"], "application/pdf")
        # 2 write storage: principale + allegato.
        self.assertEqual(storage.write.call_count, 2)
        # Return espone gli allegati persistiti.
        self.assertEqual(len(result["allegati"]), 1)
        self.assertEqual(result["allegati"][0]["file_name"], "condizioni.pdf")
        self.assertEqual(result["allegati"][0]["ordinamento"], 2)

    # 22. allegato con MIME non ammesso -> VALIDATION fail-fast (pre-render,
    #     pre-DB). Nessuna chiamata a template/render/INSERT.
    def test_genera_documento_allegato_mime_non_ammesso_raises(self) -> None:
        svc, repo, _, storage = service_with_mocks()
        _mock_params(svc)
        allegati = [{
            "file_bytes": b"testo",
            "mime_type": "text/plain",
            "file_name": "note.txt",
        }]
        with self.assertRaises(ServiceError) as ctx:
            svc.genera_documento(make_user(), allegati=allegati, **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.risolvi_template_applicabile.assert_not_called()
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()

    # 23. allegato oltre il limite size -> VALIDATION.
    def test_genera_documento_allegato_troppo_grande_raises(self) -> None:
        svc, repo, _, storage = service_with_mocks()
        _mock_params(svc, max_mb=1)
        allegati = [{
            "file_bytes": b"x" * (2 * 1024 * 1024),  # 2 MB > 1 MB
            "mime_type": "application/pdf",
            "file_name": "grosso.pdf",
        }]
        with self.assertRaises(ServiceError) as ctx:
            svc.genera_documento(make_user(), allegati=allegati, **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()


class AggiungiAllegatiTests(SimpleTestCase):
    """aggiungi_allegati: append a documento esistente (post-emissione)."""

    # 24. append allegato a documento esistente: scope OK -> persist file
    #     secondario con ordinamento da get_next_file_ordinamento.
    def test_aggiungi_allegati_append_persiste_file(self) -> None:
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                "get_documento_generato": {
                    "id": 99, "emittente_fiscale_id": 11, "pdf_hash": "abc",
                },
                "get_next_file_ordinamento": 2,
                "create_documento_generato_file": 50,
            },
            storage_methods={"write": "fs:y"},
        )
        repo.get_tipo_file_documento_by_codice.side_effect = _tipo_file_lookup
        _mock_params(svc)
        allegati = [{
            "file_bytes": b"%PDF-1.4 a",
            "mime_type": "application/pdf",
            "file_name": "extra.pdf",
        }]
        with patch_scope(None):
            with _patch_transaction_atomic_noop():
                result = svc.aggiungi_allegati(make_user(), 99, allegati)

        self.assertEqual(result["documento_id"], 99)
        self.assertEqual(len(result["allegati"]), 1)
        repo.create_documento_generato_file.assert_called_once()
        file_data = repo.create_documento_generato_file.call_args.args[0]
        self.assertEqual(file_data["documento_generato_id"], 99)
        self.assertEqual(file_data["file_tipo_id"], 9)
        self.assertEqual(file_data["is_principale"], False)
        self.assertEqual(file_data["ordinamento"], 2)
        storage.write.assert_called_once()
        # Evento timeline ALLEGATO_AGGIUNTO emesso nella stessa transazione.
        repo.emit_evento_documento.assert_called_once()
        evento = repo.emit_evento_documento.call_args.args[0]
        self.assertEqual(evento["evento_tipo"], "ALLEGATO_AGGIUNTO")
        self.assertEqual(evento["documento_generato_id"], 99)
        self.assertEqual(evento["esito"], "OK")
        self.assertEqual(evento["detail"]["n_allegati"], 1)

    # 25. documento inesistente / fuori scope -> NOT_FOUND, no persist.
    def test_aggiungi_allegati_documento_inesistente_raises_not_found(self) -> None:
        svc, repo, _, storage = service_with_mocks(
            repo_methods={"get_documento_generato": None},
        )
        _mock_params(svc)
        allegati = [{
            "file_bytes": b"x", "mime_type": "application/pdf", "file_name": "a.pdf",
        }]
        with patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.aggiungi_allegati(make_user(), 999, allegati)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        repo.create_documento_generato_file.assert_not_called()
        storage.write.assert_not_called()

    # 26. lista allegati vuota -> VALIDATION (niente da aggiungere).
    def test_aggiungi_allegati_lista_vuota_raises_validation(self) -> None:
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                "get_documento_generato": {
                    "id": 99, "emittente_fiscale_id": 11, "pdf_hash": "abc",
                },
            },
        )
        _mock_params(svc)
        with patch_scope(None):
            with self.assertRaises(ServiceError) as ctx:
                svc.aggiungi_allegati(make_user(), 99, [])
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_documento_generato_file.assert_not_called()
        storage.write.assert_not_called()


# =====================================================================
# C-0 — path sistema (scope separato dallo user, cockpit Fase C)
# =====================================================================


def _patch_bypassrls(value: bool):
    return patch(
        "apps.core.services.system_context.connection_role_bypasses_rls",
        return_value=value,
    )


class GeneraDocumentoContestoSistemaTests(SimpleTestCase):
    """C-0: `emittente_scope` esplicito separa chi autorizza da cosa genera.

    ⭐ Riscritti il 2026-09-05 (R-4). Il «path sistema» non e' piu' «nessun
    utente e nessun perimetro su una connessione BYPASSRLS»: e' un processo
    che ha un'IDENTITA' e dichiara il PERIMETRO su cui sta lavorando
    (`emittente_scope=[id]`, quello del suo utente tecnico). La vecchia
    combinazione era la porta da cui un worker generava il documento di
    qualunque azienda.

    Indice test (27..30):
     27. path processo (user=None, scope esplicito) -> pipeline completa,
         audit a None, PermissionResolver MAI interpellato
     28. ⛔ user=None + scope=None -> VALIDATION fail-loud SEMPRE, su qualsiasi
         canale: niente accesso repo/storage
     29. scope esplicito lista: guard emittente si applica senza auth guard
     30. template override in path processo -> repo.get_template (non reader)
    """

    # 27. path processo: pipeline completa senza utente, ma CON perimetro.
    def test_genera_documento_path_processo_completo_audit_none(self) -> None:
        template = template_row()
        versione = versione_row()
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                **risolto(template),
                "get_versione": versione,
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "uid-sys"),
                "create_documento_generato_file": 1,
                "emit_evento_documento": 1,
                "get_tipo_file_documento_by_codice": {"id": 2, "codice": "PDF_FINALE", "attivo": True},
            },
            storage_methods={"write": "fs:sys"},
        )
        with patch_scope([1]) as scope_mock, \
                patch_get_builder({"numero": 7}), patch_render():
            with _patch_transaction_atomic_noop():
                result = svc.genera_documento(
                    None,
                    # ⭐ Il perimetro dell'utente tecnico, non «vedo tutto».
                    emittente_scope=[11],
                    **_GENERA_DEFAULT,
                )
        self.assertEqual(result["id"], 99)
        # Lo scope NON viene derivato dallo user: il chiamante l'ha risolto.
        scope_mock.assert_not_called()
        documento_data = repo.create_documento_generato.call_args.args[0]
        self.assertIsNone(documento_data["generato_da_user_id"])
        evento_data = repo.emit_evento_documento.call_args.args[0]
        self.assertIsNone(evento_data["user_id"])
        storage.write.assert_called_once()

    # 28. ⛔ user=None + scope=None -> fail-loud SEMPRE (R-4, 2026-09-05).
    #     Prima dipendeva dal canale: su una connessione BYPASSRLS passava, ed
    #     era la porta. Adesso non c'e' nessun canale che la apra: o si dice chi
    #     si e', o si dice per quale azienda si genera.
    def test_genera_documento_senza_utente_e_senza_perimetro_raises(self) -> None:
        svc, repo, _, storage = service_with_mocks()
        with self.assertRaises(ServiceError) as ctx:
            svc.genera_documento(None, emittente_scope=None, **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.risolvi_template_applicabile.assert_not_called()
        storage.write.assert_not_called()

    # 29. scope esplicito lista: emittente fuori whitelist -> rifiutato,
    #     senza passare dall'auth guard (user=None ammesso).
    def test_genera_documento_scope_esplicito_guard_emittente(self) -> None:
        svc, repo, _, storage = service_with_mocks()
        with self.assertRaises(ServiceError) as ctx:
            svc.genera_documento(
                None, emittente_scope=[1, 2], **_GENERA_DEFAULT,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.risolvi_template_applicabile.assert_not_called()
        storage.write.assert_not_called()

    # 30. override template in path processo: repo.get_template con lo scope
    #     del chiamante, il reader (che pretende auth) non viene toccato, e la
    #     porta del DB verifica il modello indicato come sul path web.
    def test_genera_documento_path_processo_template_override_usa_repo(self) -> None:
        template = template_row(template_id=42)
        versione = versione_row()
        svc, repo, reader, _ = service_with_mocks(
            repo_methods={
                "get_template": template,
                "risolvi_template_applicabile": {
                    "template_documento_id": 42, "livello": "INDICATO",
                    "template_versione_id": 12,
                },
                "get_versione": versione,
                "next_progressivo_sorgente": 1,
                "create_documento_generato": (99, "uid-sys"),
                "create_documento_generato_file": 1,
                "emit_evento_documento": 1,
                "get_tipo_file_documento_by_codice": {"id": 2, "codice": "PDF_FINALE", "attivo": True},
            },
            storage_methods={"write": "fs:sys"},
        )
        with patch_get_builder({"numero": 7}), patch_render():
            with _patch_transaction_atomic_noop():
                svc.genera_documento(
                    None,
                    emittente_scope=[11],
                    template_documento_id=42,
                    **_GENERA_DEFAULT,
                )
        repo.get_template.assert_called_once_with(42, emittente_ids_scope=[11])
        reader.get_template.assert_not_called()
        self.assertEqual(
            repo.risolvi_template_applicabile.call_args.kwargs["template_documento_id"], 42,
        )


# =====================================================================
# Il patto versione/forma dei dati (2026-09-30)
# =====================================================================


class GeneraDocumentoVersioneContestoTests(SimpleTestCase):
    # 31. La versione pubblicata legge un'altra forma: il rifiuto del DB
    #     arriva PRIMA di costruire il contesto e di renderizzare — nessun PDF
    #     da buttare, nessuna riga, nessun file. La traduzione vera del
    #     rifiuto (P0001 -> 409 col codice) e' provata sul DB in
    #     tests/db/test_versione_contesto_db.
    def test_genera_documento_forma_dei_dati_rifiutata_niente_render(self) -> None:
        svc, repo, _, storage = service_with_mocks(
            repo_methods={
                **risolto(template_row()),
                "get_versione": versione_row(),
            },
        )
        repo.guard_versione_contesto.side_effect = ServiceError(
            code="E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA",
            message="La versione legge un'altra forma.",
        )
        with patch_scope(None), patch_get_builder() as get_builder, \
                patch_render() as render:
            with self.assertRaises(ServiceError) as ctx:
                svc.genera_documento(make_user(), **_GENERA_DEFAULT)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA")
        get_builder.return_value.build_context.assert_not_called()
        render.assert_not_called()
        repo.create_documento_generato.assert_not_called()
        storage.write.assert_not_called()
