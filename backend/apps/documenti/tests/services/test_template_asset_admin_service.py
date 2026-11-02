# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit TemplateAssetAdminService (Tranche G — debito test H1).
#        Mocka repo + reader + storage + ParameterService +
#        PermissionResolver. Verifica:
#        - upload: validazione payload (chiavi extra, campi mancanti,
#          file_name vuoto, file_bytes vuoto, oversize), scope emittente
#          (admin globale, in/out scope, anon), risoluzione tipo asset,
#          MIME whitelist per ciascun codice_interno (LOGO/IMMAGINE/FIRMA/
#          PDF/CSS/ALTRO), tipo asset inesistente o non attivo, dedup via
#          IntegrityError uq_template_asset_emittente_sha256 mappata a
#          messaggio applicativo, valido_al < valido_dal delegato al DB,
#          storage_key derivata `assets/<emittente>/<sha>.<ext>`, sequenza
#          INSERT -> write -> commit, cleanup STORAGE_ORPHAN su commit
#          fallito post-write (best-effort, non maschera l'eccezione);
#        - update: validazione id positivo, propagazione 404 dal reader,
#          rifiuto immutabili file (storage_key/sha256/file_size/mime/file_name)
#          e anag (codice/codice_interno/asset_tipo_id/emittente_fiscale_id)
#          PRIMA di altre validazioni, validate_allowed_keys, payload
#          vuoto post-validate, ordine date delegato al DB, attivo=None rifiutato,
#          IntegrityError mappata, repo False -> NOT_FOUND.
#
# Indice test (0..N):
#   0. upload_admin_globale_happy_path_storage_key_e_sequenza
#   1. upload_operator_emittente_in_scope_ok
#   2. upload_operator_emittente_fuori_scope_raises_validation
#   3. upload_anonymous_user_raises_validation
#   4. upload_payload_extra_keys_raises
#   5. upload_payload_missing_required_field_raises
#   6. upload_file_bytes_vuoto_raises
#   7. upload_file_oversize_raises_with_param_limit
#   8. upload_tipo_asset_inesistente_raises
#   9. upload_tipo_asset_non_attivo_raises
#  10. upload_tipo_asset_altro_non_ammesso
#  11. upload_mime_fuori_whitelist_per_tipo_raises
#  12. upload_mime_ammesso_per_ogni_tipo_whitelisted
#  13. upload_file_name_vuoto_raises
#  14. upload_dedup_sha256_integrity_error_mapped
#  15. upload_delega_ordine_date_al_db
#  16. upload_storage_orphan_cleanup_on_commit_fail
#  17. upload_storage_write_fail_no_cleanup_atomic_rollback
#  18. update_happy_path_via_reader_fresh
#  19. update_asset_id_non_positivo_raises_no_db
#  20. update_immutable_file_field_rejected_before_other_validation
#  21. update_immutable_anag_field_rejected_before_other_validation
#  22. update_payload_extra_key_raises
#  23. update_empty_payload_raises
#  24. update_delega_ordine_date_al_db
#  25. update_attivo_none_rifiutato
#  26. update_unique_violation_mapped
#  27. update_repo_false_raises_not_found
# ------------------------------------------------------------

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.documenti.services.template_asset_admin_service import (
    TemplateAssetAdminService,
)


# Scopo: Sostituisce transaction.atomic con un context manager no-op
#        (SimpleTestCase non puo' aprire transazioni reali).
@contextmanager
def _no_op_atomic():
    yield


# Scopo: Patch helper per il transaction.atomic del modulo service.
def _patch_transaction_atomic_noop():
    return patch(
        "apps.documenti.services.template_asset_admin_service.transaction.atomic",
        side_effect=_no_op_atomic,
    )


# Scopo: Context manager custom che simula un commit DB fallito al
#        `__exit__` per esercitare il cleanup STORAGE_ORPHAN.
class _CommitFailingAtomic:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, tb):
        if exc_type is None:
            raise IntegrityError("simulated commit failure")
        return False


# Scopo: Costruisce un user MagicMock autenticato di default.
def _make_user(*, is_authenticated: bool = True) -> Any:
    user = MagicMock()
    user.is_authenticated = is_authenticated
    return user


# Payload upload base, valido per LOGO + image/png.
_VALID_UPLOAD_METADATI: dict[str, Any] = {
    "codice": "LOGO-PRINC",
    "codice_interno": "LOGO_PRINC",
    "descrizione": "Logo aziendale principale",
    "asset_tipo_id": 1,
    "emittente_fiscale_id": 11,
    "attivo": True,
}

_FILE_BYTES_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
_MIME_PNG = "image/png"
_FNAME_PNG = "logo.png"


# Scopo: Costruisce TemplateAssetAdminService con repo + reader + storage
#        + ParameterService mockati. Niente DB ne' filesystem.
def _service_with_mocks(
    *,
    repo_methods: dict[str, Any] | None = None,
    reader_methods: dict[str, Any] | None = None,
    storage_methods: dict[str, Any] | None = None,
    params_int: int | None = 25,
) -> tuple[TemplateAssetAdminService, MagicMock, MagicMock, MagicMock, MagicMock]:
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
    params = MagicMock()
    if params_int is not None:
        params.get_parameter_int.return_value = params_int
    svc = TemplateAssetAdminService(
        repo=repo, reader=reader, storage=storage, params=params,
    )
    return svc, repo, reader, storage, params


def _tipo_asset_row(codice: str, *, attivo: bool = True) -> dict[str, Any]:
    return {"id": 1, "codice_interno": codice, "attivo": attivo}


# =====================================================================
# Upload asset
# =====================================================================


class TemplateAssetAdminServiceUploadHappyPathTests(SimpleTestCase):
    """Upload: happy path admin globale + sequenza INSERT -> write -> commit."""

    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_admin_globale_happy_path_storage_key_e_sequenza(
        self, _mock_scope
    ) -> None:
        # 0. Tipo LOGO + MIME image/png + size sotto limite -> tutto OK.
        svc, repo, reader, storage, params = _service_with_mocks(
            repo_methods={"create_asset": 99, "get_tipo_asset": _tipo_asset_row("LOGO")},
            reader_methods={"get_asset": {"id": 99, "codice": "LOGO-PRINC"}},
            storage_methods={"write": "file:///var/documenti/assets/11/abc.png"},
        )

        with _patch_transaction_atomic_noop():
            result = svc.upload_asset(
                _make_user(),
                dict(_VALID_UPLOAD_METADATI),
                _FILE_BYTES_PNG,
                _MIME_PNG,
                _FNAME_PNG,
            )

        self.assertEqual(result["id"], 99)
        # repo.create_asset chiamato con sha256 + storage_key derivati.
        repo.create_asset.assert_called_once()
        data = repo.create_asset.call_args.args[0]
        self.assertEqual(data["mime_type"], "image/png")
        self.assertEqual(data["file_name"], "logo.png")
        self.assertEqual(data["file_size_bytes"], len(_FILE_BYTES_PNG))
        self.assertTrue(data["sha256"])
        self.assertEqual(len(data["sha256"]), 64)  # hex sha256
        # storage_key stabile = assets/<emittente>/<sha>.<ext>.
        self.assertTrue(data["storage_key"].startswith("assets/11/"))
        self.assertTrue(data["storage_key"].endswith(".png"))
        # storage.write chiamato dopo create_asset (controllo ordine).
        self.assertEqual(
            [c[0] for c in repo.method_calls if c[0] == "create_asset"], ["create_asset"]
        )
        storage.write.assert_called_once()
        write_args = storage.write.call_args
        self.assertEqual(write_args.args[0], data["storage_key"])
        self.assertEqual(write_args.args[1], _FILE_BYTES_PNG)
        self.assertEqual(write_args.kwargs.get("content_type"), "image/png")
        # Ritorno via reader.get_asset fresh.
        reader.get_asset.assert_called_once()
        # Param size cap e' stato letto (limite default 25MB).
        params.get_parameter_int.assert_called_with("documenti_asset_upload_max_mb")


class TemplateAssetAdminServiceUploadScopeTests(SimpleTestCase):
    """Upload: scope emittente — admin/in scope/out scope/anon."""

    # 1. operatore con emittente nello scope -> create OK.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=[11, 22],
    )
    def test_upload_operator_emittente_in_scope_ok(self, _mock_scope) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            repo_methods={"create_asset": 7, "get_tipo_asset": _tipo_asset_row("LOGO")},
            reader_methods={"get_asset": {"id": 7}},
            storage_methods={"write": "file:///x"},
        )
        with _patch_transaction_atomic_noop():
            svc.upload_asset(
                _make_user(),
                dict(_VALID_UPLOAD_METADATI),
                _FILE_BYTES_PNG,
                _MIME_PNG,
                _FNAME_PNG,
            )
        repo.create_asset.assert_called_once()

    # 2. operatore con emittente fuori scope -> E_DOCUMENTI_VALIDATION,
    #    no DB call, no storage write.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=[1, 2],
    )
    def test_upload_operator_emittente_fuori_scope_raises_validation(
        self, _mock_scope
    ) -> None:
        svc, repo, _, storage, _ = _service_with_mocks()
        with self.assertRaises(ServiceError) as ctx:
            svc.upload_asset(
                _make_user(),
                dict(_VALID_UPLOAD_METADATI),
                _FILE_BYTES_PNG,
                _MIME_PNG,
                _FNAME_PNG,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_asset.assert_not_called()
        storage.write.assert_not_called()

    # 3. user anon o None -> E_DOCUMENTI_VALIDATION subito, no DB.
    def test_upload_anonymous_user_raises_validation(self) -> None:
        svc, repo, _, _, _ = _service_with_mocks()
        with self.assertRaises(ServiceError) as ctx:
            svc.upload_asset(
                _make_user(is_authenticated=False),
                dict(_VALID_UPLOAD_METADATI),
                _FILE_BYTES_PNG,
                _MIME_PNG,
                _FNAME_PNG,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_asset.assert_not_called()

        with self.assertRaises(ServiceError):
            svc.upload_asset(
                None,
                dict(_VALID_UPLOAD_METADATI),
                _FILE_BYTES_PNG,
                _MIME_PNG,
                _FNAME_PNG,
            )
        repo.create_asset.assert_not_called()


class TemplateAssetAdminServiceUploadPayloadTests(SimpleTestCase):
    """Upload: validazione payload metadati + file_bytes."""

    # 4. chiave extra in metadati -> validate_allowed_keys solleva.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_payload_extra_keys_raises(self, _mock_scope) -> None:
        svc, repo, _, _, _ = _service_with_mocks()
        payload = dict(_VALID_UPLOAD_METADATI)
        payload["chiave_inventata"] = "x"
        with self.assertRaises(ServiceError) as ctx:
            svc.upload_asset(
                _make_user(), payload, _FILE_BYTES_PNG, _MIME_PNG, _FNAME_PNG,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_asset.assert_not_called()

    # 5. campo richiesto mancante -> require_string solleva.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_payload_missing_required_field_raises(
        self, _mock_scope
    ) -> None:
        svc, repo, _, _, _ = _service_with_mocks()
        payload = dict(_VALID_UPLOAD_METADATI)
        del payload["codice"]
        with self.assertRaises(ServiceError) as ctx:
            svc.upload_asset(
                _make_user(), payload, _FILE_BYTES_PNG, _MIME_PNG, _FNAME_PNG,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_asset.assert_not_called()

    # 6. file_bytes vuoto -> E_DOCUMENTI_VALIDATION (pre-DB).
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_file_bytes_vuoto_raises(self, _mock_scope) -> None:
        svc, repo, _, storage, _ = _service_with_mocks(
            repo_methods={"get_tipo_asset": _tipo_asset_row("LOGO")},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.upload_asset(
                _make_user(),
                dict(_VALID_UPLOAD_METADATI),
                b"",
                _MIME_PNG,
                _FNAME_PNG,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_asset.assert_not_called()
        storage.write.assert_not_called()

    # 7. file oversize -> E_DOCUMENTI_VALIDATION con limite parlante dal param.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_file_oversize_raises_with_param_limit(
        self, _mock_scope
    ) -> None:
        # Limite molto basso (1 MB) per esercitare il guard.
        svc, repo, _, _, params = _service_with_mocks(
            repo_methods={"get_tipo_asset": _tipo_asset_row("LOGO")},
            params_int=1,
        )
        oversize_bytes = b"\x00" * (2 * 1024 * 1024)  # 2MB > 1MB limit
        with self.assertRaises(ServiceError) as ctx:
            svc.upload_asset(
                _make_user(),
                dict(_VALID_UPLOAD_METADATI),
                oversize_bytes,
                _MIME_PNG,
                _FNAME_PNG,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        # Messaggio parlante con MB.
        self.assertIn("1 MB", ctx.exception.message)
        repo.create_asset.assert_not_called()

    # 13. file_name vuoto -> E_DOCUMENTI_VALIDATION (sanitize fallisce).
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_file_name_vuoto_raises(self, _mock_scope) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            repo_methods={"get_tipo_asset": _tipo_asset_row("LOGO")},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.upload_asset(
                _make_user(),
                dict(_VALID_UPLOAD_METADATI),
                _FILE_BYTES_PNG,
                _MIME_PNG,
                "",
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_asset.assert_not_called()

    # 15. valido_al < valido_dal NON lo giudica il service: arriva al DB, dove
    #     il guard comune delle date risponde E_DATA_AL_MINORE_DAL col campo
    #     (provato sul DB vero in apps/core/tests/db/test_date_validita_guard_comune_db).
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_delega_ordine_date_al_db(self, _mock_scope) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            repo_methods={"create_asset": 99, "get_tipo_asset": _tipo_asset_row("LOGO")},
            reader_methods={"get_asset": {"id": 99}},
            storage_methods={"write": "file:///var/documenti/assets/11/abc.png"},
        )
        payload = dict(_VALID_UPLOAD_METADATI)
        payload["valido_dal"] = date(2026, 6, 1)
        payload["valido_al"] = date(2026, 5, 1)
        with _patch_transaction_atomic_noop():
            svc.upload_asset(
                _make_user(), payload, _FILE_BYTES_PNG, _MIME_PNG, _FNAME_PNG,
            )
        data = repo.create_asset.call_args.args[0]
        self.assertEqual(
            (data["valido_dal"], data["valido_al"]),
            (date(2026, 6, 1), date(2026, 5, 1)),
        )


class TemplateAssetAdminServiceUploadTipoAssetTests(SimpleTestCase):
    """Upload: risoluzione tipo asset + MIME whitelist."""

    # 8. tipo asset inesistente -> E_DOCUMENTI_VALIDATION.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_tipo_asset_inesistente_raises(self, _mock_scope) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            repo_methods={"get_tipo_asset": None},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.upload_asset(
                _make_user(),
                dict(_VALID_UPLOAD_METADATI),
                _FILE_BYTES_PNG,
                _MIME_PNG,
                _FNAME_PNG,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_asset.assert_not_called()

    # 9. tipo asset esistente ma non attivo -> E_DOCUMENTI_VALIDATION.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_tipo_asset_non_attivo_raises(self, _mock_scope) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            repo_methods={"get_tipo_asset": _tipo_asset_row("LOGO", attivo=False)},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.upload_asset(
                _make_user(),
                dict(_VALID_UPLOAD_METADATI),
                _FILE_BYTES_PNG,
                _MIME_PNG,
                _FNAME_PNG,
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.create_asset.assert_not_called()

    # 10. ALTRO non e' in whitelist v1 -> upload rifiutato esplicitamente.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_tipo_asset_altro_non_ammesso(self, _mock_scope) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            repo_methods={"get_tipo_asset": _tipo_asset_row("ALTRO")},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.upload_asset(
                _make_user(),
                dict(_VALID_UPLOAD_METADATI),
                _FILE_BYTES_PNG,
                "application/octet-stream",
                "blob.bin",
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertIn("ALTRO", ctx.exception.message)
        repo.create_asset.assert_not_called()

    # 11. MIME fuori whitelist per tipo (PDF su LOGO) -> rifiutato.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_mime_fuori_whitelist_per_tipo_raises(
        self, _mock_scope
    ) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            repo_methods={"get_tipo_asset": _tipo_asset_row("LOGO")},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.upload_asset(
                _make_user(),
                dict(_VALID_UPLOAD_METADATI),
                _FILE_BYTES_PNG,
                "application/pdf",  # PDF non ammesso su LOGO
                "x.pdf",
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertIn("MIME", ctx.exception.message)
        repo.create_asset.assert_not_called()

    # 12. MIME ammesso per ciascun tipo whitelisted (LOGO/IMMAGINE/FIRMA/PDF/CSS).
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_mime_ammesso_per_ogni_tipo_whitelisted(
        self, _mock_scope
    ) -> None:
        # Coppie (codice_interno, mime, file_name) ammesse.
        casi = [
            ("LOGO", "image/png", "logo.png"),
            ("IMMAGINE", "image/jpeg", "img.jpg"),
            ("FIRMA", "image/svg+xml", "firma.svg"),
            ("PDF", "application/pdf", "doc.pdf"),
            ("CSS", "text/css", "stile.css"),
        ]
        for codice, mime, fname in casi:
            with self.subTest(codice=codice, mime=mime):
                svc, repo, _, storage, _ = _service_with_mocks(
                    repo_methods={
                        "create_asset": 1,
                        "get_tipo_asset": _tipo_asset_row(codice),
                    },
                    reader_methods={"get_asset": {"id": 1}},
                    storage_methods={"write": "file:///x"},
                )
                with _patch_transaction_atomic_noop():
                    svc.upload_asset(
                        _make_user(),
                        dict(_VALID_UPLOAD_METADATI),
                        _FILE_BYTES_PNG,
                        mime,
                        fname,
                    )
                repo.create_asset.assert_called_once()
                data = repo.create_asset.call_args.args[0]
                self.assertEqual(data["mime_type"], mime)


class TemplateAssetAdminServiceUploadIntegrityTests(SimpleTestCase):
    """Upload: dedup naturale + cleanup STORAGE_ORPHAN."""

    # 14. dedup naturale: IntegrityError sha256 -> mappata a messaggio parlante.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_dedup_sha256_integrity_error_mapped(
        self, _mock_scope
    ) -> None:
        svc, repo, _, storage, _ = _service_with_mocks(
            repo_methods={"get_tipo_asset": _tipo_asset_row("LOGO")},
        )
        repo.create_asset.side_effect = IntegrityError(
            'duplicate key value violates unique constraint '
            '"uq_template_asset_emittente_sha256"'
        )
        with _patch_transaction_atomic_noop():
            with self.assertRaises(ServiceError) as ctx:
                svc.upload_asset(
                    _make_user(),
                    dict(_VALID_UPLOAD_METADATI),
                    _FILE_BYTES_PNG,
                    _MIME_PNG,
                    _FNAME_PNG,
                )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertIn("sha256", ctx.exception.message.lower())
        # storage.write NON deve essere stato chiamato (INSERT prima di write,
        # IntegrityError esce dal try interno).
        storage.write.assert_not_called()

    # 16. commit DB fallisce post-write -> cleanup STORAGE_ORPHAN best-effort.
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    @patch(
        "apps.documenti.services.template_asset_admin_service.transaction.atomic",
        side_effect=lambda: _CommitFailingAtomic(),
    )
    def test_upload_storage_orphan_cleanup_on_commit_fail(
        self, _mock_atomic, _mock_scope
    ) -> None:
        svc, _, _, storage, _ = _service_with_mocks(
            repo_methods={"create_asset": 99, "get_tipo_asset": _tipo_asset_row("LOGO")},
            storage_methods={"write": "file:///x", "delete": True},
        )
        with self.assertRaises(IntegrityError):
            svc.upload_asset(
                _make_user(),
                dict(_VALID_UPLOAD_METADATI),
                _FILE_BYTES_PNG,
                _MIME_PNG,
                _FNAME_PNG,
            )
        # Cleanup chiamato sull'uri ritornato dal write.
        storage.write.assert_called_once()
        storage.delete.assert_called_once_with("file:///x")

    # 17. storage.write fallisce -> atomic rollback, niente cleanup
    #     (need_cleanup ancora False, file mai esistito).
    @patch(
        "apps.documenti.services._scope.PermissionResolver.get_emittenti_pk_ids",
        return_value=None,
    )
    def test_upload_storage_write_fail_no_cleanup_atomic_rollback(
        self, _mock_scope
    ) -> None:
        svc, repo, _, storage, _ = _service_with_mocks(
            repo_methods={"create_asset": 99, "get_tipo_asset": _tipo_asset_row("LOGO")},
        )
        storage.write.side_effect = OSError("disk full")
        with _patch_transaction_atomic_noop():
            with self.assertRaises(OSError):
                svc.upload_asset(
                    _make_user(),
                    dict(_VALID_UPLOAD_METADATI),
                    _FILE_BYTES_PNG,
                    _MIME_PNG,
                    _FNAME_PNG,
                )
        repo.create_asset.assert_called_once()
        # storage.delete NON chiamato: il file non e' mai stato scritto,
        # niente da pulire (storage_uri rimane None).
        storage.delete.assert_not_called()


# =====================================================================
# Update metadati
# =====================================================================


class TemplateAssetAdminServiceUpdateTests(SimpleTestCase):
    """Update: validazione + immutabili + propagazione 404 + IntegrityError."""

    # 18. happy path: reader visibility OK, repo update True, ritorno via
    #     reader.get_asset fresh.
    def test_update_happy_path_via_reader_fresh(self) -> None:
        svc, repo, reader, _, _ = _service_with_mocks(
            repo_methods={"update_asset_metadati": True},
            reader_methods={"get_asset": {"id": 42, "codice": "LOGO-A"}},
        )
        result = svc.update_asset_metadati(
            _make_user(), 42, {"descrizione": "Nuova descr."},
        )
        self.assertEqual(result["id"], 42)
        # reader chiamato 2 volte: pre-check visibilita' + ritorno fresh.
        self.assertEqual(reader.get_asset.call_count, 2)
        repo.update_asset_metadati.assert_called_once()

    # 19. asset_id non positivo -> E_DOCUMENTI_VALIDATION subito, no DB.
    def test_update_asset_id_non_positivo_raises_no_db(self) -> None:
        svc, repo, reader, _, _ = _service_with_mocks()
        for bad in (0, -1):
            with self.subTest(asset_id=bad):
                with self.assertRaises(ServiceError) as ctx:
                    svc.update_asset_metadati(
                        _make_user(), bad, {"descrizione": "X"},
                    )
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.update_asset_metadati.assert_not_called()
        reader.get_asset.assert_not_called()

    # 20. immutabili FILE in payload -> errore parlante PRIMA di altre
    #     validation (es. chiave extra).
    def test_update_immutable_file_field_rejected_before_other_validation(
        self,
    ) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            reader_methods={"get_asset": {"id": 42}},
        )
        for field in (
            "storage_key", "sha256", "file_size_bytes", "mime_type", "file_name",
        ):
            with self.subTest(field=field):
                with self.assertRaises(ServiceError) as ctx:
                    svc.update_asset_metadati(
                        _make_user(), 42, {field: "x", "chiave_extra": "y"},
                    )
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
                # message parla di campi non aggiornabili (precedenza sul
                # check chiavi extra che verrebbe dopo).
                self.assertIn("non aggiornabili", ctx.exception.message.lower())
                self.assertIn(field, str(ctx.exception.detail or ""))
        repo.update_asset_metadati.assert_not_called()

    # 21. immutabili ANAG -> stesso comportamento.
    def test_update_immutable_anag_field_rejected_before_other_validation(
        self,
    ) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            reader_methods={"get_asset": {"id": 42}},
        )
        for field in (
            "codice", "codice_interno", "asset_tipo_id", "emittente_fiscale_id",
        ):
            with self.subTest(field=field):
                with self.assertRaises(ServiceError) as ctx:
                    svc.update_asset_metadati(
                        _make_user(), 42, {field: "x"},
                    )
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
                self.assertIn("non aggiornabili", ctx.exception.message.lower())
                self.assertIn(field, str(ctx.exception.detail or ""))
        repo.update_asset_metadati.assert_not_called()

    # 22. chiave extra (non immutabile, non whitelisted) -> validate_allowed_keys.
    def test_update_payload_extra_key_raises(self) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            reader_methods={"get_asset": {"id": 42}},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.update_asset_metadati(
                _make_user(), 42, {"chiave_inventata": "x"},
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.update_asset_metadati.assert_not_called()

    # 23. payload {} dopo validate -> "Nessun campo aggiornabile presente".
    def test_update_empty_payload_raises(self) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            reader_methods={"get_asset": {"id": 42}},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.update_asset_metadati(_make_user(), 42, {})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.update_asset_metadati.assert_not_called()

    # 24. In update l'ordine delle date lo giudica il DB (come il 15).
    def test_update_delega_ordine_date_al_db(self) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            repo_methods={"update_asset_metadati": True},
            reader_methods={"get_asset": {"id": 42}},
        )
        svc.update_asset_metadati(
            _make_user(),
            42,
            {"valido_dal": date(2026, 6, 1), "valido_al": date(2026, 5, 1)},
        )
        data = repo.update_asset_metadati.call_args.args[1]
        self.assertEqual(
            (data["valido_dal"], data["valido_al"]),
            (date(2026, 6, 1), date(2026, 5, 1)),
        )

    # 25. attivo=None esplicito -> rifiutato (non ammesso NULL).
    def test_update_attivo_none_rifiutato(self) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            reader_methods={"get_asset": {"id": 42}},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.update_asset_metadati(_make_user(), 42, {"attivo": None})
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.update_asset_metadati.assert_not_called()

    # 26. UNIQUE violato in update -> mappato a E_DOCUMENTI_VALIDATION.
    def test_update_unique_violation_mapped(self) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            reader_methods={"get_asset": {"id": 42}},
        )
        repo.update_asset_metadati.side_effect = IntegrityError(
            'duplicate key value violates unique constraint '
            '"uq_template_asset_emittente_codice"'
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.update_asset_metadati(
                _make_user(), 42, {"descrizione": "X"},
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")

    # 27. repo ritorna False (rowcount=0) -> E_DOCUMENTI_NOT_FOUND.
    def test_update_repo_false_raises_not_found(self) -> None:
        svc, repo, _, _, _ = _service_with_mocks(
            repo_methods={"update_asset_metadati": False},
            reader_methods={"get_asset": {"id": 42}},
        )
        with self.assertRaises(ServiceError) as ctx:
            svc.update_asset_metadati(
                _make_user(), 42, {"descrizione": "X"},
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        repo.update_asset_metadati.assert_called_once()
