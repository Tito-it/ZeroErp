# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Interfaccia astratta DocumentStorage. Le implementazioni
#        concrete (filesystem v1, s3/minio in futuro) persistono
#        i file documentali (asset template, PDF generati) e
#        ritornano uno storage_uri stabile da memorizzare su DB.
#        Lo storage_uri e' opaco per il caller: contiene il
#        prefisso di provider (es. 'filesystem:...') che il
#        selector usa per ri-instradare read/delete/exists.
# ------------------------------------------------------------

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from apps.core.services.error_manager import ErrorManager


class DocumentStorage(ABC):
    """
    Interfaccia astratta per il provider di storage documentale.

    Contratto:
    - `write(key, content)` persiste il file e ritorna lo storage_uri
      stabile (es. 'filesystem:templates/123/v1/header.png') da salvare
      su `documenti.documenti_generati_file.storage_uri` o equivalente.
    - `read/delete/exists` accettano lo storage_uri ritornato da write.
    - `delete` e' **best-effort**: se il file non esiste ritorna False
      senza sollevare. Le operazioni di cleanup post-fail commit non
      devono propagare errori (Decisione 72 + evento STORAGE_ORPHAN).
    - le chiavi logiche (`key`) NON devono contenere path traversal
      (`..`, leading `/`); la validazione e' a cura dell'implementazione.

    Le credenziali eventuali NON sono attributi della classe: provengono
    da env/secret manager dietro `documenti_storage_secret_ref`.
    """

    PROVIDER: ClassVar[str] = ""

    @abstractmethod
    def write(
        self,
        key: str,
        content: bytes,
        *,
        content_type: str | None = None,
    ) -> str:
        """
        Persiste `content` con chiave logica `key`. Ritorna lo storage_uri
        stabile da memorizzare su DB.
        """

    @abstractmethod
    def read(self, storage_uri: str) -> bytes:
        """Legge il file persistito dato lo storage_uri."""

    @abstractmethod
    def build_storage_uri(self, key: str) -> str:
        """
        Costruisce lo storage_uri stabile per una chiave logica senza
        toccare il file. Usato dal codice di lettura post-fact (Tranche K
        download) che ha la `storage_key` salvata su DB ma non lo
        `storage_uri` ritornato dal write originale.
        """

    @abstractmethod
    def delete(self, storage_uri: str) -> bool:
        """
        Cancella il file. Best-effort:
        - True se il file e' stato eliminato in questa chiamata;
        - False se il file non esisteva piu' (no-op silenzioso);
        - solleva ServiceError solo per errori inattesi (permessi, IO).
        """

    @abstractmethod
    def exists(self, storage_uri: str) -> bool:
        """Verifica esistenza del file persistito."""


# Scopo: Legge il file di una `storage_key` salvata su DB e traduce
#        QUALUNQUE errore dello storage (file mancante, permessi, IO) in
#        `E_DOCUMENTI_STORAGE_FAILED`, con il messaggio e il detail del
#        chiamante: e' lui a sapere QUALE file mancava (documento, asset).
# ⭐ ESTRATTO IL 2026-10-01 (regola del 2, ok di Tid): il blocco
#    «build_storage_uri + read + except -> E_STORAGE_FAILED» stava in
#    quattro punti — `download_documento`, `download_documento_file`,
#    `TemplateService.download_asset` e il risolutore degli asset del render.
#    Nel risolutore mancava, e un errore di IO usciva dal render come
#    «risorsa non ammessa», indicando il template invece del disco.
#    Funzione e non metodo: i chiamanti ricevono lo storage dalla factory,
#    e nei test e' un doppio che non eredita da `DocumentStorage`.
def leggi_da_storage(
    storage: DocumentStorage,
    storage_key: str,
    *,
    message: str,
    detail: str,
) -> bytes:
    try:
        return storage.read(storage.build_storage_uri(storage_key))
    except Exception:
        ErrorManager.raise_error(
            code="E_DOCUMENTI_STORAGE_FAILED",
            message=message,
            detail=detail,
        )
