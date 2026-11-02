# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Facade lettura template documentali. Gestisce lo scope
#        emittente derivandolo dal Django user (whitelist via
#        PermissionResolver.get_emittenti_pk_ids), valida gli input
#        (id positivi, codici stato) e mappa i 404 in
#        ServiceError(E_DOCUMENTI_NOT_FOUND).
#        Contratto write (CRUD admin) atterra in PR successive.
# ------------------------------------------------------------

from __future__ import annotations

from io import BytesIO
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from PIL import Image, ImageOps

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.permissions_resolver import PermissionResolver
from apps.documenti.db.documenti_repository import DocumentiRepository
from apps.documenti.services.context_builders import versione_contesto_registrata
from apps.documenti.services.storage import DocumentStorage, get_storage, leggi_da_storage

E_VALIDATION = "E_DOCUMENTI_VALIDATION"

# Lato massimo (px) della miniatura di un asset immagine. Il pannello la
# mostra in 2rem: 128 px restano nitidi anche su uno schermo ad alta densita'.
LATO_MINIATURA = 128

# Set CHECK chiuso v1 — coerente con DDL template_documenti_versioni.
_STATI_VERSIONE_VALIDI: frozenset[str] = frozenset({"BOZZA", "PUBBLICATA", "OBSOLETA"})


class TemplateService:
    """Facade lettura template + versioni. Risolve scope emittente operatore."""

    def __init__(
        self,
        repo: DocumentiRepository | None = None,
        storage: DocumentStorage | None = None,
    ) -> None:
        self._repo = repo or DocumentiRepository()
        self._v = PayloadValidator(validation_code=E_VALIDATION)
        self._storage_factory = (lambda: storage) if storage is not None else get_storage

    # Scopo: Lista template paginata con scope emittente automatico per
    #        l'utente loggato. Admin globale (None) vede tutto; operatore
    #        riceve la whitelist dei suoi emittenti.
    def list_templates(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        *,
        attivo: bool | None = True,
        tipo_documento_output_id: int | None = None,
        sorgente_tipo_id: int | None = None,
        emittente_fiscale_id: int | None = None,
        standard: bool | None = None,
        search: str | None = None,
        order_by: str = "codice",
        order_dir: str = "asc",
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        emittente_ids_scope = self._resolve_emittente_scope(user)
        rows, total = self._repo.list_templates(
            attivo=attivo,
            tipo_documento_output_id=tipo_documento_output_id,
            sorgente_tipo_id=sorgente_tipo_id,
            emittente_fiscale_id=emittente_fiscale_id,
            standard=standard,
            search=search,
            emittente_ids_scope=emittente_ids_scope,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        return {"results": rows, "total_count": total}

    # Scopo: Con che cosa stampa ogni azienda del perimetro dell'utente (una
    #        riga per azienda × documento, con l'esito della risoluzione: vedi
    #        `DocumentiRepository.list_risoluzione_emittenti`). Lo legge il
    #        pannello sopra la lista Modelli documento: «si usa lo standard»,
    #        «nessun predefinito». `emittente_fiscale_id` restringe a
    #        un'azienda (il filtro della lista).
    def list_risoluzione_emittenti(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        *,
        emittente_fiscale_id: int | None = None,
    ) -> dict[str, Any]:
        rows = self._repo.list_risoluzione_emittenti(
            emittente_ids_scope=self._resolve_emittente_scope(user),
            emittente_fiscale_id=emittente_fiscale_id,
        )
        return {"results": rows, "total_count": len(rows)}

    # Scopo: Dettaglio template per id, con scope emittente. 404 esplicito
    #        sia per id inesistente sia per scope non autorizzato (no
    #        leak di esistenza fuori scope).
    def get_template(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(template_id, field="template_id")
        emittente_ids_scope = self._resolve_emittente_scope(user)
        row = self._repo.get_template(
            template_id, emittente_ids_scope=emittente_ids_scope
        )
        ErrorManager.require(
            row is not None,
            code="E_DOCUMENTI_NOT_FOUND",
            message="Template documento non trovato.",
            detail=f"template_id={template_id}",
        )
        assert row is not None
        # La forma dei dati che il builder del template produce OGGI: e' un
        # fatto del codice (`CONTEXT_VERSION`), non del DB, e il dettaglio lo
        # porta perche' chi prepara una versione sappia quale forma dichiarare
        # (una versione si pubblica e stampa solo se legge questa). `None` =
        # builder non registrato: il template non genera ne' si pubblica.
        row["versione_contesto_builder"] = versione_contesto_registrata(
            row.get("context_builder_code"),
        )
        return row

    # Scopo: Lista versioni di un template. Pre-verifica che il template
    #        sia visibile all'utente (404 unificato) prima di proiettare
    #        le versioni.
    def list_versioni(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
        *,
        attivo: bool | None = True,
        stato: str | None = None,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        self.get_template(user, template_id)  # 404 se fuori scope
        if stato is not None and stato not in _STATI_VERSIONE_VALIDI:
            ErrorManager.raise_error(
                code="E_DOCUMENTI_VALIDATION",
                message=f"Stato versione non valido: '{stato}'.",
                detail=f"ammessi={sorted(_STATI_VERSIONE_VALIDI)!r}",
            )
        rows, total = self._repo.list_versioni(
            template_id, attivo=attivo, stato=stato, search=search,
            order_by=order_by, order_dir=order_dir, limit=limit, offset=offset,
        )
        # Stessa forma di `list_templates`: la view ne fa l'envelope paginato.
        return {"results": rows, "total_count": total}

    # Scopo: Dettaglio versione (incluso payload HTML/CSS/markdown).
    #        Pre-verifica template visibile, poi recupera la versione e
    #        valida il binding template <-> versione (defense-in-depth).
    def get_versione(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
        versione_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(versione_id, field="versione_id")
        self.get_template(user, template_id)  # 404 se template fuori scope
        row = self._repo.get_versione(template_id, versione_id)
        ErrorManager.require(
            row is not None,
            code="E_DOCUMENTI_NOT_FOUND",
            message="Versione template non trovata.",
            detail=f"template_id={template_id}, versione_id={versione_id}",
        )
        assert row is not None
        return row

    # Scopo: Lista asset paginata con scope emittente automatico.
    def list_asset(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        *,
        attivo: bool | None = True,
        asset_tipo_id: int | None = None,
        emittente_fiscale_id: int | None = None,
        search: str | None = None,
        utilizzabili: bool | None = None,
        order_by: str = "codice",
        order_dir: str = "asc",
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> dict[str, Any]:
        emittente_ids_scope = self._resolve_emittente_scope(user)
        rows, total = self._repo.list_asset(
            attivo=attivo,
            asset_tipo_id=asset_tipo_id,
            emittente_fiscale_id=emittente_fiscale_id,
            search=search,
            emittente_ids_scope=emittente_ids_scope,
            utilizzabili=utilizzabili,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
            offset=offset,
        )
        return {"results": rows, "total_count": total}

    # Scopo: Dettaglio asset per id, con scope emittente. 404 unificato
    #        sia per id inesistente sia per scope non autorizzato.
    def get_asset(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        asset_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(asset_id, field="asset_id")
        emittente_ids_scope = self._resolve_emittente_scope(user)
        row = self._repo.get_asset(
            asset_id, emittente_ids_scope=emittente_ids_scope
        )
        ErrorManager.require(
            row is not None,
            code="E_DOCUMENTI_NOT_FOUND",
            message="Asset documentale non trovato.",
            detail=f"asset_id={asset_id}",
        )
        assert row is not None
        return row

    # Scopo: Scarica il binario di un asset documentale rispettando lo
    #        stesso scope emittente del dettaglio. GET puro: nessun evento
    #        o mutazione, solo lettura da storage applicativo.
    def download_asset(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        asset_id: int,
    ) -> dict[str, Any]:
        asset = self.get_asset(user, asset_id)
        file_bytes = leggi_da_storage(
            self._storage_factory(), asset["storage_key"],
            message="Errore lettura asset documentale dallo storage.",
            detail=f"asset_id={asset_id}",
        )

        return {
            "asset_id": asset_id,
            "file_bytes": file_bytes,
            "file_name": asset["file_name"],
            "mime_type": asset["mime_type"],
            "size_bytes": int(asset["file_size_bytes"]),
        }

    # Scopo: La miniatura di un asset immagine, per riconoscerlo a colpo
    #        d'occhio nell'editor dei template senza scaricare il file intero.
    #        Stesso scope emittente del dettaglio. Raster -> PNG di lato al
    #        massimo `LATO_MINIATURA`; SVG -> il file cosi' com'e' (e'
    #        vettoriale: lo rimpicciolisce il browser, e Pillow non lo legge).
    #        `etag` dipende dall'impronta del file (immutabile a DB) e dal lato:
    #        se il client ne porta uno uguale fra `etag_noti` la risposta e'
    #        «non modificata» (`file_bytes` None) e il file non si legge.
    # ⚠️ Lo scope si controlla PRIMA dell'ETag: un 304 dato senza controllo
    #    confermerebbe a chiunque che l'asset esiste.
    def miniatura_asset(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        asset_id: int,
        *,
        etag_noti: list[str] | None = None,
    ) -> dict[str, Any]:
        asset = self.get_asset(user, asset_id)
        mime_type = asset["mime_type"] or ""
        ErrorManager.require(
            mime_type.startswith("image/"),
            code=E_VALIDATION,
            message="L'asset non e' un'immagine: non ha una miniatura.",
            detail=f"asset_id={asset_id} mime_type={mime_type}",
        )
        etag = f'"{asset["sha256"]}-{LATO_MINIATURA}"'
        if etag in (etag_noti or []):
            return {"etag": etag, "file_bytes": None, "mime_type": None}

        contenuto = leggi_da_storage(
            self._storage_factory(), asset["storage_key"],
            message="Errore lettura asset documentale dallo storage.",
            detail=f"asset_id={asset_id}",
        )
        if mime_type == "image/svg+xml":
            return {"etag": etag, "file_bytes": contenuto, "mime_type": mime_type}
        return {
            "etag": etag,
            "file_bytes": _miniatura_png(contenuto, asset_id),
            "mime_type": "image/png",
        }

    # ---- helper interni ------------------------------------------------------

    # Scopo: Risolve la lista degli emittenti autorizzati per l'utente.
    #        Admin globale + superuser = None (vede tutto). Operatore
    #        ottiene una whitelist di id `emittenti_fiscali.id` (puntiamo
    #        ad una tabella che usa la PK reale, vedi memoria
    #        feedback_emittente_pk_vs_soggetto_ruolo).
    def _resolve_emittente_scope(
        self, user: AbstractBaseUser | AnonymousUser | None,
    ) -> list[int] | None:
        if user is None or not getattr(user, "is_authenticated", False):
            # Caller non autenticato non dovrebbe arrivare qui (DomainAPIView
            # gia' applica JWT); difensivamente ritorniamo lista vuota
            # = nessun risultato, mai panel-leak.
            return []
        return PermissionResolver.get_emittenti_pk_ids(user)


# Scopo: Riduce un'immagine raster a PNG di lato al massimo `LATO_MINIATURA`,
#        conservando le proporzioni e la trasparenza (i loghi la usano).
#        L'orientamento EXIF si applica prima: una foto girata dal telefono
#        resterebbe storta. Di una GIF animata si prende il primo fotogramma.
#        Un file che Pillow non sa leggere (corrotto, o abbastanza grande da
#        far scattare la guardia contro le «decompression bomb") e'
#        E_DOCUMENTI_RENDER_FAILED.
def _miniatura_png(contenuto: bytes, asset_id: int) -> bytes:
    try:
        with Image.open(BytesIO(contenuto)) as originale:
            originale.draft("RGB", (LATO_MINIATURA, LATO_MINIATURA))
            immagine = ImageOps.exif_transpose(originale)
            immagine.thumbnail((LATO_MINIATURA, LATO_MINIATURA))
            if immagine.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                immagine = immagine.convert("RGBA")
            uscita = BytesIO()
            immagine.save(uscita, format="PNG", optimize=True)
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        ErrorManager.raise_error(
            code="E_DOCUMENTI_RENDER_FAILED",
            message="Miniatura non generabile: il file non e' un'immagine leggibile.",
            detail=f"asset_id={asset_id} {type(exc).__name__}: {exc}",
        )
    return uscita.getvalue()
