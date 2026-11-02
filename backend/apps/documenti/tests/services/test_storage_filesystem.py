# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit per FilesystemDocumentStorage. Coprono il
#        roundtrip write/read/delete/exists, la guard path
#        traversal sulla chiave logica, il dispatch su provider
#        mismatch nello storage_uri. Non richiedono DB
#        (SimpleTestCase) e isolano lo stato su tempdir.
#
# Indice test (0..N):
#   0. write_returns_storage_uri_with_provider_prefix
#   1. read_returns_written_bytes
#   2. read_missing_raises_storage_failed
#   3. delete_existing_returns_true
#   4. delete_missing_returns_false_no_raise
#   5. exists_true_for_persisted, false_for_missing
#   6. write_blocks_path_traversal_dotdot
#   7. write_blocks_path_traversal_backslash
#   8. write_blocks_empty_key
#   9. write_strips_leading_slash
#  10. read_blocks_provider_mismatch
#  11. write_is_atomic_no_orphan_tempfile_after_failure
#  12. write_overwrites_existing_file_atomically
# ------------------------------------------------------------

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.documenti.services.storage.filesystem import (
    FilesystemDocumentStorage,
    build_filesystem_storage,
)


class FilesystemDocumentStorageTests(SimpleTestCase):
    """Roundtrip + guard sulla implementazione filesystem."""

    def setUp(self) -> None:
        # Scopo: tempdir isolato per ogni test, cleanup automatico via addCleanup.
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.storage = build_filesystem_storage(root=self.root, prefix="documenti")

    # 0. write ritorna storage_uri con prefisso provider.
    def test_write_returns_storage_uri_with_provider_prefix(self) -> None:
        uri = self.storage.write("templates/123/header.png", b"PNG_BYTES")
        self.assertEqual(uri, "filesystem:documenti/templates/123/header.png")

    # 1. read riproduce i bytes scritti.
    def test_read_returns_written_bytes(self) -> None:
        uri = self.storage.write("templates/1/v1/header.html", b"<html/>")
        self.assertEqual(self.storage.read(uri), b"<html/>")

    # 2. read di file inesistente solleva E_DOCUMENTI_STORAGE_FAILED.
    def test_read_missing_raises_storage_failed(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.storage.read("filesystem:documenti/never/written.bin")
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_STORAGE_FAILED")

    # 3. delete su file esistente ritorna True.
    def test_delete_existing_returns_true(self) -> None:
        uri = self.storage.write("a/b/c.txt", b"x")
        self.assertTrue(self.storage.delete(uri))
        self.assertFalse(self.storage.exists(uri))

    # 4. delete idempotente: file mancante ritorna False senza sollevare.
    def test_delete_missing_returns_false_no_raise(self) -> None:
        self.assertFalse(
            self.storage.delete("filesystem:documenti/missing/file.bin")
        )

    # 5. exists riflette la presenza fisica.
    def test_exists_true_for_persisted_false_for_missing(self) -> None:
        uri = self.storage.write("ok.txt", b"ok")
        self.assertTrue(self.storage.exists(uri))
        self.assertFalse(
            self.storage.exists("filesystem:documenti/elsewhere.txt")
        )

    # 6. path traversal con `..` blocca con E_DOCUMENTI_VALIDATION.
    def test_write_blocks_path_traversal_dotdot(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.storage.write("../etc/passwd", b"x")
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")

    # 7. backslash su `..\foo` viene normalizzato e bloccato.
    def test_write_blocks_path_traversal_backslash(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.storage.write("..\\etc\\passwd", b"x")
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")

    # 8. chiave vuota o whitespace blocca con E_DOCUMENTI_VALIDATION.
    def test_write_blocks_empty_key(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.storage.write("   ", b"x")
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")

    # 9. leading slash viene strippato e la write procede.
    def test_write_strips_leading_slash(self) -> None:
        uri = self.storage.write("/templates/1/footer.html", b"<f/>")
        self.assertEqual(uri, "filesystem:documenti/templates/1/footer.html")
        self.assertEqual(self.storage.read(uri), b"<f/>")

    # 10. read su storage_uri di provider diverso solleva storage_failed.
    def test_read_blocks_provider_mismatch(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.storage.read("s3:bucket/foo.bin")
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_STORAGE_FAILED")


class FilesystemDocumentStorageNoPrefixTests(SimpleTestCase):
    """Variante: prefix vuoto. La storage_uri non riporta prefisso."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_write_without_prefix_uri_format(self) -> None:
        storage = FilesystemDocumentStorage(root=self.root, prefix="")
        uri = storage.write("a/b.txt", b"x")
        self.assertEqual(uri, "filesystem:a/b.txt")
        self.assertEqual(storage.read(uri), b"x")


class FilesystemDocumentStorageAtomicWriteTests(SimpleTestCase):
    """Atomic write: tempfile + os.replace, no file parziali su crash."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.storage = build_filesystem_storage(root=self.root, prefix="documenti")

    # 11. crash a meta' write -> nessun tempfile orfano residuo, file
    #     persistente NON creato (invariante: o file completo o assente).
    def test_write_is_atomic_no_orphan_tempfile_after_failure(self) -> None:
        target_dir = self.root / "documenti" / "templates" / "1"
        # Forza fallimento dell'os.replace finale per simulare crash.
        with patch(
            "apps.documenti.services.storage.filesystem.os.replace",
            side_effect=OSError("EIO simulato"),
        ):
            with self.assertRaises(OSError):
                self.storage.write("templates/1/header.html", b"<html/>")

        # File destinazione NON deve esistere (write fallita atomicamente).
        self.assertFalse((target_dir / "header.html").exists())

        # Tempfile orfano: nessun file `.tmp-*` residuo nella dir di destinazione.
        if target_dir.exists():
            tmp_residui = list(target_dir.glob(".tmp-*"))
            self.assertEqual(tmp_residui, [], msg=f"tempfile orfani: {tmp_residui!r}")

    # 12. overwrite atomico: il secondo write sostituisce il primo senza
    #     stati intermedi visibili (rename atomico).
    def test_write_overwrites_existing_file_atomically(self) -> None:
        uri1 = self.storage.write("a/b.txt", b"v1")
        self.assertEqual(self.storage.read(uri1), b"v1")
        uri2 = self.storage.write("a/b.txt", b"v2")
        self.assertEqual(uri1, uri2)
        self.assertEqual(self.storage.read(uri2), b"v2")
