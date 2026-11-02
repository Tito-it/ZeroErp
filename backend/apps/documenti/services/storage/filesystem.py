# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Implementazione filesystem locale di DocumentStorage.
#        Persiste i file documentali sotto DOCUMENTI_STORAGE_ROOT
#        (settings Django) prefissati con `documenti_storage_prefix`
#        (config.parameters). storage_uri ritornato:
#        'filesystem:<prefix>/<key>'.
#        Provider di default v1 (Decisione 72). MinIO/S3 entreranno
#        come ulteriori implementazioni della stessa interfaccia.
# ------------------------------------------------------------

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import ClassVar

from apps.core.services.error_manager import ErrorManager
from apps.documenti.services.storage.base import DocumentStorage


class FilesystemDocumentStorage(DocumentStorage):
    """Storage documentale su filesystem locale."""

    PROVIDER: ClassVar[str] = "filesystem"

    def __init__(self, *, root: Path, prefix: str) -> None:
        # Scopo: root = directory base assoluta sul disco;
        #        prefix = chiave logica iniziale comune a tutti gli storage_uri
        #        (es. 'documenti/'). Combinati determinano il path fisico finale.
        self._root = root.resolve()
        self._prefix = prefix.strip("/")

    # Scopo: Persiste content sul filesystem e ritorna storage_uri stabile.
    #        Valida la chiave (no path traversal), crea le directory mancanti
    #        e scrive ATOMICAMENTE: tempfile nello stesso filesystem + os.replace
    #        (rename atomico su POSIX). Un crash a meta' scrittura lascia il
    #        tempfile orfano (cleanup nel finally), mai un file persistente
    #        parziale: protegge l'invariante "documenti_generati_file.storage_uri
    #        => file completo o assente".
    def write(
        self,
        key: str,
        content: bytes,
        *,
        content_type: str | None = None,
    ) -> str:
        normalized_key = self._normalize_key(key)
        target_path = self._resolve_path(normalized_key)
        # mkdir parents idempotente; il rename finale sovrascrivera' eventuali file pre-esistenti.
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Tempfile nella STESSA directory di destinazione: garantisce che
        # os.replace sia un rename atomico (stesso filesystem). NamedTempFile
        # con delete=False perche' il rename finale si occupa del path.
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=".tmp-", suffix=target_path.suffix, dir=target_path.parent
        )
        try:
            with os.fdopen(tmp_fd, "wb") as fp:
                fp.write(content)
            os.replace(tmp_path, target_path)
        except Exception:
            # Cleanup best-effort del tempfile orfano. missing_ok evita race
            # se il rename ha gia' consumato il path.
            Path(tmp_path).unlink(missing_ok=True)
            raise
        return self._build_storage_uri(normalized_key)

    # Scopo: Legge il file persistito dato lo storage_uri ritornato da write().
    def read(self, storage_uri: str) -> bytes:
        target_path = self._resolve_path(self._extract_key(storage_uri))
        if not target_path.exists():
            ErrorManager.raise_error(
                code="E_DOCUMENTI_STORAGE_FAILED",
                message="File documento non trovato sullo storage.",
                detail=f"storage_uri={storage_uri}",
            )
        return target_path.read_bytes()

    # Scopo: Cancella il file. Best-effort: ritorna False se gia' assente,
    #        non solleva. Errori IO inattesi vengono propagati come
    #        ServiceError E_DOCUMENTI_STORAGE_FAILED.
    def delete(self, storage_uri: str) -> bool:
        target_path = self._resolve_path(self._extract_key(storage_uri))
        try:
            target_path.unlink(missing_ok=False)
            return True
        except FileNotFoundError:
            return False
        except OSError as exc:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_STORAGE_FAILED",
                message="Errore eliminazione file documento.",
                detail=f"storage_uri={storage_uri}, errno={exc.errno}",
            )

    # Scopo: Verifica esistenza file persistito.
    def exists(self, storage_uri: str) -> bool:
        target_path = self._resolve_path(self._extract_key(storage_uri))
        return target_path.is_file()

    # Scopo: Pubblica `_build_storage_uri` per il codice di lettura post-fact.
    #        Il caller ha solo la `storage_key` letta dal DB e ricostruisce
    #        lo storage_uri prima di passare a `read/delete/exists`.
    def build_storage_uri(self, key: str) -> str:
        return self._build_storage_uri(self._normalize_key(key))

    # ---- helper interni ------------------------------------------------------

    # Scopo: Normalizza la chiave logica e blocca path traversal.
    #        Le chiavi vivono nello spazio relativo a (root + prefix); non
    #        ammettono leading slash, segmenti '..', o backslash su Windows.
    def _normalize_key(self, key: str) -> str:
        if not key or not key.strip():
            ErrorManager.raise_error(
                code="E_DOCUMENTI_VALIDATION",
                message="Chiave storage vuota.",
            )
        cleaned = key.strip().replace("\\", "/").lstrip("/")
        # Blocca path traversal: '..' come segmento o sequenza letterale.
        segments = cleaned.split("/")
        for segment in segments:
            if segment in ("", ".", ".."):
                ErrorManager.raise_error(
                    code="E_DOCUMENTI_VALIDATION",
                    message="Chiave storage non valida (path traversal).",
                    detail=f"key={key!r}",
                )
        return cleaned

    # Scopo: Costruisce path fisico assoluto a partire dalla chiave normalizzata.
    #        Defense-in-depth: il path risultante deve restare dentro `root`,
    #        anche se il normalize ha gia' filtrato i casi noti.
    def _resolve_path(self, normalized_key: str) -> Path:
        target = (self._root / self._prefix / normalized_key).resolve()
        try:
            target.relative_to(self._root)
        except ValueError:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_VALIDATION",
                message="Chiave storage non valida (out of root).",
                detail=f"key={normalized_key!r}",
            )
        return target

    # Scopo: Costruisce lo storage_uri stabile salvato su DB.
    #        Formato: 'filesystem:<prefix>/<key>' (prefix incluso per
    #        rendere il riferimento auto-contenuto in caso di cambio di
    #        DOCUMENTI_STORAGE_ROOT senza ribaselining dei record).
    def _build_storage_uri(self, normalized_key: str) -> str:
        prefixed = f"{self._prefix}/{normalized_key}" if self._prefix else normalized_key
        return f"{self.PROVIDER}:{prefixed}"

    # Scopo: Estrae la chiave dal formato storage_uri ritornato da write.
    #        Solleva se il provider non corrisponde (defense-in-depth: in v1 c'e'
    #        un solo provider attivo, ma uno storage_uri legacy con provider
    #        diverso e' uno stato inconsistente che va segnalato).
    def _extract_key(self, storage_uri: str) -> str:
        if ":" not in storage_uri:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_VALIDATION",
                message="storage_uri malformato.",
                detail=f"storage_uri={storage_uri!r}",
            )
        provider, _, prefixed_key = storage_uri.partition(":")
        if provider != self.PROVIDER:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_STORAGE_FAILED",
                message="Provider storage non corrisponde.",
                detail=f"atteso={self.PROVIDER}, trovato={provider}",
            )
        # Ritorniamo la parte oltre al prefix per riallineare al normalize.
        if self._prefix and prefixed_key.startswith(f"{self._prefix}/"):
            return prefixed_key[len(self._prefix) + 1:]
        return prefixed_key.lstrip("/")


# Scopo: Costruisce un'istanza FilesystemDocumentStorage dalla configurazione
#        Django + parametri runtime. Esposta separatamente dal selector
#        principale per consentire ai test di iniettare un root temporaneo.
def build_filesystem_storage(*, root: Path, prefix: str) -> FilesystemDocumentStorage:
    if not root.exists():
        # mkdir best-effort al primo bootstrap (idempotente, niente errore se gia' presente).
        root.mkdir(parents=True, exist_ok=True)
    return FilesystemDocumentStorage(root=root, prefix=prefix)
