# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Orchestratore della generazione persistita di un documento
#        (Tranche I). Pipeline:
#         1. valida user + scope emittente (PermissionResolver);
#         2. chiede al DB, in una domanda sola, il modello e la versione con
#            cui si stampa (`fn_risolvi_template_applicabile`, la porta unica):
#            senza modello indicato i due livelli (predefinito dell'emittente,
#            se no lo standard), con il modello indicato la sua verifica;
#         3. rilegge la versione detta dal DB (corpo HTML/CSS per il render);
#         4. risolve context_builder via registry (`get_builder_del_template`,
#            whitelist Decisione 18+74)
#            e chiede al DB se la versione legge la forma dei dati del
#            builder (`documenti.fn_guard_versione_contesto`, 2026-09-30);
#         5. richiede al builder il context (responsabilita' del dominio
#            sorgente: sicurezza, scope, lookup);
#         6. invoca render_service.render_pdf -> bytes (engine WEASYPRINT v1);
#         7. calcola hashes audit (context/template/pdf), nome_file dal
#            pattern del template e progressivo per (sorgente_tipo+uid+riga);
#         8. transazione atomica: INSERT documento_generato +
#            documento_generato_file + evento `GENERATO` + storage.write
#            dentro lo stesso `with`;
#         9. cleanup STORAGE_ORPHAN best-effort se il commit fallisce
#            post-write (file scritto, record DB rolled back).
#
#        Decisioni di design rilevate:
#         - render PRIMA del DB (Decisione 32: render fail = niente record,
#           niente evento orfano da loggare);
#         - INSERT eventi senza `tx_id` esplicito (Decisione 76);
#         - storage_key derivata da pdf_hash (dedup naturale a parita' di
#           contenuto, idempotente per re-render dello stesso input);
#         - hashes via JSON canonical (sort_keys=True, default=str) +
#           UTF-8 bytes;
#         - tipo_file via lookup codice (`PDF_FINALE`, no hardcoded ID).
# ------------------------------------------------------------

from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import IntegrityError, transaction

from apps.core.api.constants import DEFAULT_LIMIT
from apps.core.services.error_manager import ErrorManager
from apps.core.services.error_messages_fallback import USER_MESSAGE_FALLBACK
from apps.core.services.parameter_service import ParameterService
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
    translate_db_errors,
)
from apps.documenti.db.documenti_repository import DocumentiRepository
from apps.documenti.services._scope import (
    guard_emittente_in_scope,
    guard_user_authenticated,
    resolve_emittente_scope,
)
from apps.documenti.services.context_builders.base import DocumentContextBuilder
from apps.documenti.services.context_builders.registry import get_builder_del_template
from apps.documenti.services.render_service import RisolviAsset, render_pdf
from apps.documenti.services.storage import (
    DocumentStorage,
    get_storage,
    leggi_da_storage,
)
from apps.documenti.services.template_service import TemplateService

logger = logging.getLogger(__name__)

# Codici errore. Tutti gia' registrati in
# `apps.core.services.error_policies` (Tranche B + F + G).
E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"
E_RENDER_FAILED = "E_DOCUMENTI_RENDER_FAILED"
E_STORAGE_FAILED = "E_DOCUMENTI_STORAGE_FAILED"
E_VERSIONE_CONTESTO_NON_VERIFICABILE = "E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE"
E_TEMPLATE_NON_RISOLTO = "E_DOCUMENTI_TEMPLATE_NON_RISOLTO"

# Codice del tipo file usato in v1 (seed `tipi_file_documento` Fase A).
# Memoria feedback_no_hardcoded_ids: lookup per codice, non ID numerici.
_CODICE_TIPO_FILE_PDF_FINALE = "PDF_FINALE"

# Codice tipo file per gli allegati caricati dall'utente sul documento
# generato (file secondari, `is_principale=false`). Seed DB dedicato
# (brief 2026-05-27): senza il tipo file ALLEGATO attivo l'INSERT fallisce
# sul guard `trgfn_child_requires_active_parent`.
_CODICE_TIPO_FILE_ALLEGATO = "ALLEGATO"

# Tipo evento della ristampa fedele (percorso 3). Distinto da `GENERATO`
# perche' NON e' un'emissione: nessun documento nuovo, nessun progressivo.
# ⚠️ Prerequisito DB: va aggiunto al CHECK
# `chk_documenti_generati_eventi_evento_tipo` (set chiuso). Finche' non c'e',
# l'INSERT dell'evento viene rifiutato e il servizio logga senza negare il PDF.
_EVENTO_RISTAMPA_FEDELE = "RISTAMPA_FEDELE"

# MIME canonical del file principale generato in v1.
_MIME_PDF = "application/pdf"

# Whitelist MIME ammessi per gli allegati (decisione 2026-05-27 con Tid:
# PDF + immagini). Allineata al pattern asset (`template_asset_admin_service`):
# nessun upload generico libero.
_MIME_WHITELIST_ALLEGATO: frozenset[str] = frozenset({
    "application/pdf",
    "image/jpeg",
    "image/png",
})

# Fallback estensione per MIME allegato (usato se file_name senza estensione).
_MIME_EXT_FALLBACK_ALLEGATO: dict[str, str] = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
}

# Parametro `config.parameters` per il limite size di un singolo allegato.
_PARAM_ALLEGATO_MAX_MB = "documenti_allegato_upload_max_mb"

# Lunghezza massima del file_name allegato persistito.
_MAX_ALLEGATO_FILE_NAME_LEN = 255

# Ordinamento e flag is_principale per il file principale (unico in v1).
_ORDINAMENTO_PRINCIPALE = 1
_IS_PRINCIPALE_DEFAULT = True

# Fallback ext quando il pattern file_name non termina in .pdf esplicito.
_EXT_PDF = "pdf"

# Mapping vincoli DB testata documento_generati -> codici applicativi.
# Solo i piu' probabili in scrittura runtime: i CHECK (hash_len, stato,
# titolo_non_vuoto) sono violazioni di programmazione, non di input.
_DOCUMENTO_UNIQUE_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "uq_documenti_generati_sorgente_progressivo": (
        E_VALIDATION,
        "Race su progressivo sorgente: riprovare la generazione.",
    ),
}

# Sentinel C-0 (P-1, brief-be-fe-processi-fatturazione §4): "scope non passato"
# e' diverso da "scope None". Default = deriva lo scope dallo user (path web,
# invariato per i 6 domini).
# ⭐ Il path PROCESSO (worker headless) passa `emittente_scope` ESPLICITO — la
# lista di UN emittente, quello del proprio utente tecnico — e `user=None`
# (audit a None: l'attore e' in `app.jwt_user`).
# ⛔ Fino al 2026-09-05 passava `None` («vede tutto») su un canale `BYPASSRLS`:
# era la porta da cui un worker generava il documento di qualunque azienda. Il
# canale non esiste piu' e quella combinazione e' rifiutata (R-2/R-4).
_SCOPE_DA_UTENTE: Any = object()


class DocumentGenerationService:
    """Orchestratore generazione persistita di un documento."""

    # Scopo: Costruzione con dipendenze iniettabili. Storage e parameters
    #        sono lazy: i test mockano repo + storage senza toccare il
    #        filesystem, e il render_pdf e' patchabile dal modulo.
    def __init__(
        self,
        repo: DocumentiRepository | None = None,
        reader: TemplateService | None = None,
        storage: DocumentStorage | None = None,
        params: ParameterService | None = None,
    ) -> None:
        self._repo = repo or DocumentiRepository()
        self._reader = reader or TemplateService(repo=self._repo)
        self._storage_factory = (lambda: storage) if storage else get_storage
        self._params = params or ParameterService()
        self._v = PayloadValidator(validation_code=E_VALIDATION)

    # =================================================================
    # Comando pubblico: genera documento persistito
    # =================================================================

    # Scopo: Genera e persiste un documento PDF a partire da una sorgente.
    #        Il caller fornisce gli identificativi della sorgente
    #        (`sorgente_tipo_id`, `sorgente_uid`, opzionale `sorgente_riga`)
    #        e l'`emittente_fiscale_id`. Modello e versione li dice il DB
    #        (`_resolve_template`): coi due livelli (predefinito dell'emittente,
    #        se no lo standard), o verificando l'override esplicito
    #        `template_documento_id`. Ritorna un dict con id+uid+nome_file
    #        del documento generato + storage_uri del file persistito.
    #        C-0: `emittente_scope` separa CHI AUTORIZZA da COSA GENERA —
    #        default sentinel = deriva dallo `user` (path web, invariato);
    #        il path sistema passa lo scope gia' risolto (None = vede tutto,
    #        perimetro esplicito obbligatorio, vedi `_resolve_scope_chiamante`).
    def genera_documento(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        *,
        emittente_fiscale_id: int,
        sorgente_tipo_id: int,
        sorgente_id: int,
        sorgente_uid: str,
        sorgente_riga: int | None = None,
        tipo_documento_output_id: int | None = None,
        template_documento_id: int | None = None,
        allegati: list[dict[str, Any]] | None = None,
        locale: str = "it-IT",
        emittente_scope: Any = _SCOPE_DA_UTENTE,
    ) -> dict[str, Any]:
        # 0) guard input scalari (errore parlante PRIMA dei round-trip DB).
        self._v.guard_positive_int(emittente_fiscale_id, field="emittente_fiscale_id")
        self._v.guard_positive_int(sorgente_tipo_id, field="sorgente_tipo_id")
        self._v.guard_positive_int(sorgente_id, field="sorgente_id")
        self._v.guard_non_empty_string(sorgente_uid, field="sorgente_uid")
        if sorgente_riga is not None:
            self._v.guard_positive_int(sorgente_riga, field="sorgente_riga")

        # 0-bis) valida+prepara gli allegati PRIMA del render (fail-fast su
        #        MIME/size: niente render sprecato se un allegato e' invalido).
        #        Lista vuota se nessun allegato: persist solo del principale.
        allegati_prep = self._valida_e_prepara_allegati(
            allegati, emittente_fiscale_id,
        )

        # 1) autorizzazione: path web deriva lo scope dallo user (auth guard
        #    + un solo round-trip, riusato in `_resolve_template`); path
        #    sistema riceve lo scope gia' risolto dal chiamante (C-0).
        scope = self._resolve_scope_chiamante(user, emittente_scope)
        guard_emittente_in_scope(scope, emittente_fiscale_id)

        # 2-3) il modello e la versione con cui si stampa, dal DB in una
        #      domanda sola, anche quando il chiamante indica il modello: e' il
        #      DB a dire se va bene per questo documento (emittente, sorgente,
        #      tipo) e se oggi puo' stampare.
        template, versione = self._resolve_template(
            user,
            scope=scope,
            emittente_fiscale_id=emittente_fiscale_id,
            sorgente_tipo_id=sorgente_tipo_id,
            tipo_documento_output_id=tipo_documento_output_id,
            template_documento_id=template_documento_id,
        )

        # 4) risolve il builder e chiede al DB se la versione legge la forma
        #    dei dati che il builder produce: PRIMA di costruire il contesto e
        #    di renderizzare, perche' un rifiuto dopo (il trigger sull'INSERT
        #    della stampa) lascerebbe un PDF da buttare.
        builder = get_builder_del_template(template)
        self._guard_versione_contesto(versione, builder)

        # 5) costruisce il context
        context = self._build_context_for_sorgente(
            user, builder, sorgente_id, locale=locale,
        )

        # 6) render PDF (fuori transazione: render fail = niente record DB)
        pdf_bytes = render_pdf(
            template_versione=versione,
            context=context,
            risolvi_asset=self._risolutore_asset(
                emittente_fiscale_id, solo_validi=True,
            ),
        )
        if not pdf_bytes:
            ErrorManager.raise_error(
                code=E_RENDER_FAILED,
                message="Render ha restituito output PDF vuoto.",
            )

        # 7) compute hashes + nome_file + progressivo + storage_key.
        #    Il context viene normalizzato JSON-safe una sola volta:
        #    - serve sia per il context_hash deterministico (hash su rappresentazione
        #      canonica) sia per `documenti_generati.context_json` (jsonb DDL),
        #      che psycopg serializza a json.dumps -> TypeError su Decimal/date
        #      se passassimo il context raw del builder.
        context_canonical = self._json_canonical(context)
        context_json_safe = json.loads(context_canonical)
        context_hash = self._sha256_text(context_canonical)
        template_hash = self._compute_template_hash(versione)
        pdf_hash = self._sha256_bytes(pdf_bytes)
        nome_file = self._format_nome_file(template, context)
        titolo = self._build_titolo(template)
        ext = self._resolve_extension(nome_file)
        storage_key = f"documenti/{emittente_fiscale_id}/{pdf_hash}.{ext}"

        # 8) lookup tipo_file PDF_FINALE (no ID hardcoded)
        tipo_file = self._repo.get_tipo_file_documento_by_codice(
            _CODICE_TIPO_FILE_PDF_FINALE
        )
        ErrorManager.require(
            tipo_file is not None and tipo_file.get("attivo"),
            code=E_VALIDATION,
            message="Tipo file 'PDF_FINALE' non configurato o non attivo.",
        )
        assert tipo_file is not None
        tipo_file_id = tipo_file["id"]

        # 8-bis) lookup tipo_file ALLEGATO solo se ci sono allegati (no ID
        #        hardcoded). Risolto fuori dalla transazione: errore parlante
        #        prima di INSERT/storage.
        tipo_allegato_id: int | None = None
        if allegati_prep:
            tipo_allegato_id = self._resolve_tipo_allegato_id()

        # 9) sequenza atomica: INSERT 3 record + storage.write
        progressivo = self._repo.next_progressivo_sorgente(
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_uid=sorgente_uid,
            sorgente_riga=sorgente_riga,
        )

        documento_data: dict[str, Any] = {
            "tipo_documento_output_id": template["tipo_documento_output_id"],
            "template_documento_id": template["id"],
            "template_versione_id": versione["id"],
            "sorgente_tipo_id": sorgente_tipo_id,
            "sorgente_uid": sorgente_uid,
            "sorgente_riga": sorgente_riga,
            "progressivo_sorgente": progressivo,
            "stato": "GENERATO",
            "titolo": titolo,
            "nome_file": nome_file,
            "context_json": context_json_safe,
            "context_hash": context_hash,
            "template_hash": template_hash,
            "pdf_hash": pdf_hash,
            "generato_da_user_id": getattr(user, "id", None),
            "emittente_fiscale_id": emittente_fiscale_id,
            "meta": {},
        }
        file_data: dict[str, Any] = {
            "file_tipo_id": tipo_file_id,
            "mime_type": _MIME_PDF,
            "file_name": nome_file,
            "file_size_bytes": len(pdf_bytes),
            "storage_key": storage_key,
            "sha256": pdf_hash,
            "ordinamento": _ORDINAMENTO_PRINCIPALE,
            "is_principale": _IS_PRINCIPALE_DEFAULT,
            "meta": {},
        }
        evento_data_template: dict[str, Any] = {
            "evento_tipo": "GENERATO",
            "user_id": getattr(user, "id", None),
            "esito": "OK",
            "messaggio": None,
            "detail": {
                "size_bytes": len(pdf_bytes),
                "pdf_hash": pdf_hash,
            },
            "meta": {},
        }

        storage = self._storage_factory()
        # Tutti gli storage_uri scritti nella transazione (principale +
        # allegati): in caso di commit fallito vanno ripuliti tutti.
        written_uris: list[str] = []
        allegati_persistiti: list[dict[str, Any]] = []
        need_cleanup = False
        try:
            with transaction.atomic():
                try:
                    documento_id, documento_uid = self._repo.create_documento_generato(
                        documento_data,
                    )
                except IntegrityError as exc:
                    map_integrity_error(
                        exc,
                        unique_constraints=_DOCUMENTO_UNIQUE_CONSTRAINTS,
                        fallback_code=E_VALIDATION,
                        fallback_message="Violazione vincolo DB su documento generato.",
                        context={
                            "sorgente_tipo_id": sorgente_tipo_id,
                            "sorgente_uid": sorgente_uid,
                            "progressivo": progressivo,
                        },
                    )
                file_data["documento_generato_id"] = documento_id
                self._repo.create_documento_generato_file(file_data)

                evento_data = {
                    **evento_data_template,
                    "documento_generato_id": documento_id,
                }
                self._repo.emit_evento_documento(evento_data)

                # write storage solo dopo INSERT OK: se write fallisce,
                # transaction.atomic fa rollback dei 3 record DB ->
                # nessun stato incoerente.
                written_uris.append(storage.write(
                    storage_key, pdf_bytes, content_type=_MIME_PDF,
                ))

                # Allegati come file secondari (ALLEGATO, is_principale=false),
                # ordinamento progressivo a partire da 2 (principale = 1).
                if allegati_prep:
                    assert tipo_allegato_id is not None
                    allegati_persistiti = self._persisti_allegati(
                        storage,
                        documento_generato_id=documento_id,
                        tipo_allegato_id=tipo_allegato_id,
                        prepared=allegati_prep,
                        ordinamento_start=_ORDINAMENTO_PRINCIPALE + 1,
                        written_uris=written_uris,
                    )

                # Da questo punto in poi: l'uscita dal `with` fa il commit;
                # se il commit fallisce, i file sono gia' su disk -> cleanup
                # nel finally. Il record DB risulta rolled back, l'evento
                # STORAGE_ORPHAN non e' linkabile (FK NOT NULL su
                # documento_generato_id) -> log warning + cleanup file.
                need_cleanup = True
            need_cleanup = False  # commit OK
        finally:
            if need_cleanup and written_uris:
                self._cleanup_storage_orphans(storage, written_uris, pdf_hash)

        # `generato_at` non viene incluso nel return: il valore autoritativo
        # e' lato DB (default `now()`); il caller fa lookup se gli serve.
        return {
            "id": documento_id,
            "uid": documento_uid,
            "nome_file": nome_file,
            "titolo": titolo,
            "pdf_hash": pdf_hash,
            # storage_uri del file principale (primo scritto nella tx).
            "storage_uri": written_uris[0] if written_uris else None,
            "size_bytes": len(pdf_bytes),
            "progressivo_sorgente": progressivo,
            "template_documento_id": template["id"],
            "template_versione_id": versione["id"],
            "allegati": allegati_persistiti,
        }

    # =================================================================
    # Comandi pubblici aggiuntivi (Tranche K)
    # =================================================================

    # Scopo: Anteprima PDF a richiesta (Decisione 30): renderizza il
    #        documento ma NON lo persiste (no INSERT, no storage.write,
    #        no evento). Ritorna i bytes per streaming response. Il
    #        caller decide il `Content-Disposition` (inline vs attachment)
    #        e, in genere, NON chiama dopo `genera_documento` perche' la
    #        timeline non logga `ANTEPRIMA` (set chiuso v1).
    def anteprima_documento(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        *,
        emittente_fiscale_id: int,
        sorgente_tipo_id: int,
        sorgente_id: int,
        tipo_documento_output_id: int | None = None,
        template_documento_id: int | None = None,
        locale: str = "it-IT",
    ) -> dict[str, Any]:
        # Stessa pipeline di `genera_documento` step 0..6 senza persist.
        self._v.guard_positive_int(emittente_fiscale_id, field="emittente_fiscale_id")
        self._v.guard_positive_int(sorgente_tipo_id, field="sorgente_tipo_id")
        self._v.guard_positive_int(sorgente_id, field="sorgente_id")
        guard_user_authenticated(user)
        assert user is not None
        scope = resolve_emittente_scope(user)
        guard_emittente_in_scope(scope, emittente_fiscale_id)

        template, versione = self._resolve_template(
            user,
            scope=scope,
            emittente_fiscale_id=emittente_fiscale_id,
            sorgente_tipo_id=sorgente_tipo_id,
            tipo_documento_output_id=tipo_documento_output_id,
            template_documento_id=template_documento_id,
        )
        # Anche l'anteprima: una versione che legge un'altra forma darebbe a
        # video un documento incompleto, senza nessun errore.
        builder = get_builder_del_template(template)
        self._guard_versione_contesto(versione, builder)
        context = self._build_context_for_sorgente(
            user, builder, sorgente_id, locale=locale,
        )
        pdf_bytes = render_pdf(
            template_versione=versione,
            context=context,
            risolvi_asset=self._risolutore_asset(
                emittente_fiscale_id, solo_validi=True,
            ),
        )
        if not pdf_bytes:
            ErrorManager.raise_error(
                code=E_RENDER_FAILED,
                message="Render anteprima ha restituito output PDF vuoto.",
            )

        nome_file = self._format_nome_file(template, context)
        return {
            "pdf_bytes": pdf_bytes,
            "nome_file": nome_file,
            "size_bytes": len(pdf_bytes),
            "mime_type": _MIME_PDF,
        }

    # Scopo: Lista paginata documenti generati per una sorgente (es. tutti
    #        i PDF generati a partire da un dato preventivo). Building
    #        block riusabile da qualsiasi dominio sorgente: il caller
    #        applica i propri permessi a livello view + scope emittente
    #        applicato qui via `PermissionResolver`.
    def list_documenti_per_sorgente(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        *,
        sorgente_tipo_id: int,
        sorgente_uid: str,
        sorgente_riga: int | None = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        search: str | None = None,
        order_by: str | None = None,
        order_dir: str | None = None,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(sorgente_tipo_id, field="sorgente_tipo_id")
        self._v.guard_non_empty_string(sorgente_uid, field="sorgente_uid")
        if sorgente_riga is not None:
            self._v.guard_positive_int(sorgente_riga, field="sorgente_riga")
        guard_user_authenticated(user)
        assert user is not None
        scope = resolve_emittente_scope(user)
        rows, total = self._repo.list_documenti_per_sorgente(
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_uid=sorgente_uid,
            sorgente_riga=sorgente_riga,
            emittente_ids_scope=scope,
            limit=limit,
            offset=offset,
            search=search,
            order_by=order_by,
            order_dir=order_dir,
        )
        return {"results": rows, "total_count": total}

    # Scopo: Download PDF persistito + emit evento `SCARICATO` (Decisione 31:
    #        log ad ogni download). Pipeline:
    #         1. guard id + auth + scope;
    #         2. lookup `documenti_generati` (404 unificato no leak);
    #         3. lookup file principale (404 se mai persistito);
    #         4. read storage tramite `leggi_da_storage(storage, key)`;
    #         5. emit evento `SCARICATO/OK` in transazione separata
    #            (non bloccare il download se l'INSERT log fallisce: il
    #            file e' la priorita');
    #         6. ritorna bytes + metadati per FileResponse del caller.
    def download_documento(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        documento_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(documento_id, field="documento_id")
        guard_user_authenticated(user)
        assert user is not None
        scope = resolve_emittente_scope(user)

        documento = self._repo.get_documento_generato(
            documento_id, emittente_ids_scope=scope,
        )
        ErrorManager.require(
            documento is not None,
            code=E_NOT_FOUND,
            message="Documento generato non trovato.",
            detail=f"documento_id={documento_id}",
        )
        assert documento is not None

        file_row = self._repo.get_documento_generato_file_principale(documento_id)
        ErrorManager.require(
            file_row is not None,
            code=E_NOT_FOUND,
            message="File principale del documento non trovato.",
            detail=f"documento_id={documento_id}",
        )
        assert file_row is not None

        pdf_bytes = leggi_da_storage(
            self._storage_factory(), file_row["storage_key"],
            message="Errore lettura file documento dallo storage.",
            detail=f"documento_id={documento_id}",
        )

        # Emit evento SCARICATO in tx separata: il download e' la priorita'.
        # Se il log fallisce (es. tx rollback per FK race) il file e' gia'
        # tornato al client, l'audit e' best-effort.
        try:
            with transaction.atomic():
                self._repo.emit_evento_documento({
                    "documento_generato_id": documento_id,
                    "evento_tipo": "SCARICATO",
                    "user_id": getattr(user, "id", None),
                    "esito": "OK",
                    "messaggio": None,
                    "detail": {
                        "size_bytes": len(pdf_bytes),
                        "pdf_hash": documento.get("pdf_hash"),
                    },
                    "meta": {},
                })
        except Exception:
            logger.exception(
                "documenti.documento.evento_scaricato_fallito documento_id=%s",
                documento_id,
            )

        return {
            "pdf_bytes": pdf_bytes,
            "nome_file": documento["nome_file"],
            "mime_type": file_row["mime_type"],
            "size_bytes": int(file_row["file_size_bytes"]),
            "documento_id": documento_id,
        }

    # Scopo: RISTAMPA FEDELE (percorso 3, brief-ristampa-fedele-documenti):
    #        ri-renderizza un documento **com'era**, dalla versione di template
    #        con cui nacque e dal contesto CONGELATO di allora. E' l'unico
    #        percorso che mantiene la promessa del modello sui documenti privi
    #        di file salvato, e l'unico modo di verificare che un file
    #        conservato sia davvero quello giusto.
    #
    #        Le tre cose che lo distinguono da `genera_documento`, e che sono
    #        il motivo per cui esiste:
    #         1. la versione e' quella **pinnata** sul documento
    #            (`template_versione_id`), caricata anche se OBSOLETA — NON la
    #            pubblicata di oggi;
    #         2. il contesto e' quello **letto** da `context_json` — NON
    #            ricostruito dai dati correnti (sarebbe un documento nuovo
    #            travestito da vecchio);
    #         3. NON persiste nulla: nessuna riga in `documenti_generati`,
    #            nessun progressivo consumato, nessuno stato sorgente toccato.
    #            L'unica scrittura e' l'evento di audit (decisione Tid §8.3).
    #
    #        Fedelta' (decisione Tid §8.2 — "soluzione 1"): il confronto
    #        autoritativo e' sul **contenuto** (`context_hash` + `template_hash`
    #        letti dallo snapshot: gli ingredienti sono gli stessi per
    #        costruzione). Il `pdf_hash` viene ricalcolato e confrontato, ma una
    #        differenza di BYTE non e' un errore: un renderer puo' non essere
    #        deterministico fra versioni della libreria (font, metadati, data di
    #        produzione). Il risultato lo DICHIARA (`pdf_hash_match`) invece di
    #        nasconderlo — e il caller decide come presentarlo.
    #        Ritorna i bytes per lo streaming + i metadati di fedelta'.
    def ristampa_fedele(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        documento_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(documento_id, field="documento_id")
        guard_user_authenticated(user)
        assert user is not None
        scope = resolve_emittente_scope(user)

        # 1) snapshot congelato (testata + context_json), con scope emittente.
        documento = self._repo.get_documento_generato_snapshot(
            documento_id, emittente_ids_scope=scope,
        )
        ErrorManager.require(
            documento is not None,
            code=E_NOT_FOUND,
            message="Documento generato non trovato.",
            detail=f"documento_id={documento_id}",
        )
        assert documento is not None

        # 2) versione PINNATA (anche OBSOLETA: e' quella di allora).
        versione_id = documento.get("template_versione_id")
        ErrorManager.require(
            versione_id is not None,
            code=E_VALIDATION,
            message=(
                "Documento senza versione di template: non e' ristampabile "
                "fedelmente."
            ),
            detail=f"documento_id={documento_id}",
        )
        assert versione_id is not None
        versione = self._repo.get_versione_by_id(int(versione_id))
        ErrorManager.require(
            versione is not None,
            code=E_NOT_FOUND,
            message="Versione di template del documento non trovata.",
            detail=f"documento_id={documento_id} versione_id={versione_id}",
        )
        assert versione is not None

        # 3) contesto CONGELATO. Deve essere un oggetto: `context_json` e'
        #    jsonb NOT NULL a DB, ma un documento con contesto vuoto non e'
        #    ri-renderizzabile e va detto invece di produrre un PDF a campi
        #    vuoti (il render e' StrictUndefined: fallirebbe comunque, ma con
        #    un messaggio che parla di Jinja e non del documento).
        context = documento.get("context_json")
        ErrorManager.require(
            isinstance(context, dict) and len(context) > 0,
            code=E_VALIDATION,
            message=(
                "Documento senza contesto congelato: non e' ristampabile "
                "fedelmente."
            ),
            detail=f"documento_id={documento_id}",
        )
        assert isinstance(context, dict)

        # 4) render con gli ingredienti di allora. Nessun controllo della forma
        #    dei dati: la coppia versione/contesto l'ha gia' verificata il
        #    trigger sull'INSERT della stampa, e nessuna delle due e' cambiata.
        #    Gli asset sono quelli dell'emittente del documento, anche se oggi
        #    scaduti o disattivati: sono immutabili e non si cancellano, quindi
        #    il `codice_interno` scritto nella versione indica il file di allora
        #    (decisione Tid 2026-10-01).
        pdf_bytes = render_pdf(
            template_versione=versione,
            context=context,
            risolvi_asset=self._risolutore_asset(
                int(documento["emittente_fiscale_id"]), solo_validi=False,
            ),
        )
        if not pdf_bytes:
            ErrorManager.raise_error(
                code=E_RENDER_FAILED,
                message="Ristampa fedele ha restituito output PDF vuoto.",
            )

        # 5) verifica di fedelta'. Il template_hash ricalcolato sulla versione
        #    caricata deve coincidere con quello congelato: se diverge, la
        #    versione e' stata modificata dopo la generazione — cosa che il DB
        #    impedisce sulle PUBBLICATE, quindi qui significherebbe un
        #    documento nato da una versione poi cambiata in BOZZA. Non blocca
        #    (il PDF e' comunque il piu' fedele ottenibile) ma va dichiarato.
        pdf_hash_atteso = documento.get("pdf_hash")
        pdf_hash_ristampa = self._sha256_bytes(pdf_bytes)
        template_hash_atteso = documento.get("template_hash")
        template_hash_ricalcolato = self._compute_template_hash(versione)

        risultato = {
            "pdf_bytes": pdf_bytes,
            "nome_file": documento["nome_file"],
            "mime_type": _MIME_PDF,
            "size_bytes": len(pdf_bytes),
            "documento_id": documento_id,
            "template_versione_id": int(versione_id),
            "versione": versione.get("versione"),
            "versione_stato": versione.get("stato"),
            # Fedelta' dichiarata, non presunta (decisione §8.2).
            "pdf_hash_atteso": pdf_hash_atteso,
            "pdf_hash_ristampa": pdf_hash_ristampa,
            "pdf_hash_match": pdf_hash_ristampa == pdf_hash_atteso,
            "template_hash_match": template_hash_ricalcolato == template_hash_atteso,
        }

        if not risultato["pdf_hash_match"]:
            # Non e' un errore (§8.2): il contenuto e' fedele, i byte no.
            # Va loggato perche' e' il segnale con cui ci si accorge di un
            # cambio di motore di render.
            logger.info(
                "documenti.ristampa_fedele.pdf_hash_diverso documento_id=%s "
                "atteso=%s ottenuto=%s template_hash_match=%s",
                documento_id, pdf_hash_atteso, pdf_hash_ristampa,
                risultato["template_hash_match"],
            )

        # 6) evento di audit (decisione Tid §8.3: la ristampa lascia traccia).
        #    E' l'UNICA scrittura del percorso, e resta best-effort come il
        #    `SCARICATO` del download: il PDF e' gia' prodotto, un fallimento
        #    del log non deve negarlo all'operatore.
        #    ⚠️ Prerequisito DB: `RISTAMPA_FEDELE` nel CHECK
        #    `chk_documenti_generati_eventi_evento_tipo` (brief al team DB).
        #    Finche' non c'e', l'INSERT viene rifiutato e qui si logga.
        try:
            with transaction.atomic():
                self._repo.emit_evento_documento({
                    "documento_generato_id": documento_id,
                    "evento_tipo": _EVENTO_RISTAMPA_FEDELE,
                    "user_id": getattr(user, "id", None),
                    # `WARN` e non un valore nuovo: il CHECK `esito` ammette
                    # OK|KO|WARN e "fedele nel contenuto ma non nei byte" e'
                    # esattamente un warning, non un fallimento.
                    "esito": "OK" if risultato["pdf_hash_match"] else "WARN",
                    "messaggio": (
                        None if risultato["pdf_hash_match"]
                        else "Ristampa fedele nel contenuto, non nei byte."
                    ),
                    "detail": {
                        "size_bytes": len(pdf_bytes),
                        "template_versione_id": int(versione_id),
                        "pdf_hash_atteso": pdf_hash_atteso,
                        "pdf_hash_ristampa": pdf_hash_ristampa,
                        "pdf_hash_match": risultato["pdf_hash_match"],
                        "template_hash_match": risultato["template_hash_match"],
                    },
                    "meta": {},
                })
        except Exception:
            logger.exception(
                "documenti.ristampa_fedele.evento_fallito documento_id=%s",
                documento_id,
            )

        return risultato

    # Scopo: Aggiunge allegati (file secondari) a un documento generato
    #        gia' esistente (modalita' "append" del building block: l'utente
    #        allega altri file dopo l'emissione, finche' lo stato sorgente lo
    #        consente — la regola di stato vive lato dominio). Pipeline:
    #         1. guard id + auth + scope emittente;
    #         2. lookup documento (404 unificato no leak);
    #         3. valida+prepara allegati (MIME/size) usando l'emittente del
    #            documento per lo storage_key;
    #         4. transazione atomica: INSERT righe file secondarie + storage
    #            write, ordinamento progressivo dopo i file esistenti;
    #         5. cleanup STORAGE_ORPHAN best-effort se il commit fallisce.
    #        Ritorna l'elenco degli allegati persistiti (id + nome + size).
    def aggiungi_allegati(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        documento_id: int,
        allegati: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(documento_id, field="documento_id")
        guard_user_authenticated(user)
        assert user is not None
        scope = resolve_emittente_scope(user)

        documento = self._repo.get_documento_generato(
            documento_id, emittente_ids_scope=scope,
        )
        ErrorManager.require(
            documento is not None,
            code=E_NOT_FOUND,
            message="Documento generato non trovato.",
            detail=f"documento_id={documento_id}",
        )
        assert documento is not None

        emittente_fiscale_id = int(documento["emittente_fiscale_id"])
        prepared = self._valida_e_prepara_allegati(allegati, emittente_fiscale_id)
        ErrorManager.require(
            len(prepared) > 0,
            code=E_VALIDATION,
            message="Nessun allegato valido da aggiungere.",
        )
        tipo_allegato_id = self._resolve_tipo_allegato_id()

        storage = self._storage_factory()
        written_uris: list[str] = []
        allegati_persistiti: list[dict[str, Any]] = []
        need_cleanup = False
        try:
            with transaction.atomic():
                ordinamento_start = self._repo.get_next_file_ordinamento(
                    documento_id,
                )
                allegati_persistiti = self._persisti_allegati(
                    storage,
                    documento_generato_id=documento_id,
                    tipo_allegato_id=tipo_allegato_id,
                    prepared=prepared,
                    ordinamento_start=ordinamento_start,
                    written_uris=written_uris,
                )
                need_cleanup = True
                # Evento timeline: l'aggiunta allegati post-emissione
                # (modalita' append) emette ALLEGATO_AGGIUNTO. Nella stessa
                # transazione del persist: se l'INSERT evento fallisce, il
                # rollback + cleanup storage mantengono la coerenza.
                self._repo.emit_evento_documento({
                    "documento_generato_id": documento_id,
                    "evento_tipo": "ALLEGATO_AGGIUNTO",
                    "user_id": getattr(user, "id", None),
                    "esito": "OK",
                    "messaggio": None,
                    "detail": {
                        "n_allegati": len(allegati_persistiti),
                        "file_ids": [a["id"] for a in allegati_persistiti],
                        "size_bytes_tot": sum(
                            a["size_bytes"] for a in allegati_persistiti
                        ),
                    },
                    "meta": {},
                })
            need_cleanup = False
        finally:
            if need_cleanup and written_uris:
                self._cleanup_storage_orphans(
                    storage, written_uris, documento.get("pdf_hash"),
                )

        return {
            "documento_id": documento_id,
            "allegati": allegati_persistiti,
        }

    # Scopo: Download di uno specifico file (principale o allegato) di un
    #        documento, per id riga. Mirror di `download_documento` ma per
    #        file arbitrario: scope sul documento + emit evento `SCARICATO`.
    def download_documento_file(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        documento_id: int,
        file_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(documento_id, field="documento_id")
        self._v.guard_positive_int(file_id, field="file_id")
        guard_user_authenticated(user)
        assert user is not None
        scope = resolve_emittente_scope(user)

        documento = self._repo.get_documento_generato(
            documento_id, emittente_ids_scope=scope,
        )
        ErrorManager.require(
            documento is not None,
            code=E_NOT_FOUND,
            message="Documento generato non trovato.",
            detail=f"documento_id={documento_id}",
        )
        assert documento is not None

        file_row = self._repo.get_documento_generato_file(documento_id, file_id)
        ErrorManager.require(
            file_row is not None,
            code=E_NOT_FOUND,
            message="File del documento non trovato.",
            detail=f"documento_id={documento_id} file_id={file_id}",
        )
        assert file_row is not None

        file_bytes = leggi_da_storage(
            self._storage_factory(), file_row["storage_key"],
            message="Errore lettura file documento dallo storage.",
            detail=f"documento_id={documento_id} file_id={file_id}",
        )

        try:
            with transaction.atomic():
                self._repo.emit_evento_documento({
                    "documento_generato_id": documento_id,
                    "evento_tipo": "SCARICATO",
                    "user_id": getattr(user, "id", None),
                    "esito": "OK",
                    "messaggio": None,
                    "detail": {
                        "file_id": file_id,
                        "size_bytes": int(file_row["file_size_bytes"]),
                        "sha256": file_row.get("sha256"),
                    },
                    "meta": {},
                })
        except Exception:
            logger.exception(
                "documenti.documento.evento_scaricato_file_fallito "
                "documento_id=%s file_id=%s",
                documento_id, file_id,
            )

        return {
            "pdf_bytes": file_bytes,
            "nome_file": file_row["file_name"],
            "mime_type": file_row["mime_type"],
            "size_bytes": int(file_row["file_size_bytes"]),
            "documento_id": documento_id,
            "file_id": file_id,
        }

    # Scopo: Lista file (principale + allegati) di un documento, con scope
    #        emittente sul documento. Usata dalla UI per elencare gli
    #        allegati e offrirne il download per id.
    def list_documento_files(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        documento_id: int,
    ) -> dict[str, Any]:
        self._v.guard_positive_int(documento_id, field="documento_id")
        guard_user_authenticated(user)
        assert user is not None
        scope = resolve_emittente_scope(user)

        documento = self._repo.get_documento_generato(
            documento_id, emittente_ids_scope=scope,
        )
        ErrorManager.require(
            documento is not None,
            code=E_NOT_FOUND,
            message="Documento generato non trovato.",
            detail=f"documento_id={documento_id}",
        )
        assert documento is not None
        files = self._repo.list_documento_generato_files(documento_id)
        return {"results": files, "total_count": len(files)}

    # =================================================================
    # Helpers privati
    # =================================================================

    # Scopo: C-0 — risolve lo scope emittente del chiamante separando CHI
    #        AUTORIZZA da COSA GENERA. Sentinel (default) = path web: auth
    #        guard + `resolve_emittente_scope(user)` come sempre. Scope
    #        esplicito = path caller-resolved: il chiamante ha gia' deciso
    #        (un worker passa la lista di UN emittente: il proprio). ⛔ Dal
    #        2026-09-05 la combinazione `scope=None + user=None` — «nessun
    #        utente e nessun perimetro» — NON e' piu' ammessa da nessun canale:
    #        o si dice chi si e', o si dice per quale azienda si genera.
    def _resolve_scope_chiamante(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        emittente_scope: Any,
    ) -> list[int] | None:
        if emittente_scope is _SCOPE_DA_UTENTE:
            guard_user_authenticated(user)
            assert user is not None
            return resolve_emittente_scope(user)
        # Fail-fast parlante su input malformato del chiamante (lo scope
        # esplicito e' un contratto interno: lista di id oppure None).
        ErrorManager.require(
            emittente_scope is None or isinstance(emittente_scope, list),
            code=E_VALIDATION,
            message="emittente_scope non valido: attesa lista di id o None.",
            detail=f"emittente_scope={type(emittente_scope).__name__}",
        )
        # ⛔ SENZA UTENTE E SENZA PERIMETRO NON SI GENERA PIU' (2026-09-05,
        #    residuo R-4 del cantiere «nessun processo senza operatore»).
        #    Fino a ieri quella combinazione era ammessa su una connessione
        #    `BYPASSRLS`: era la porta da cui un worker produceva il documento
        #    di QUALUNQUE azienda senza dire per conto di chi.
        #    ⭐ Adesso il worker della coda stampa gira con l'identita'
        #    dell'utente tecnico e passa il perimetro esplicito
        #    (`emittente_scope=[id]`), quindi questo ramo non ha piu' nessun
        #    chiamante legittimo — e restare aperto lo renderebbe di nuovo
        #    raggiungibile per distrazione.
        #    ⛔ E NON si e' sostituito il guard con «la connessione ha un utente
        #    in sessione?»: sarebbe stato un secondo criterio accanto a quello
        #    che il database applica gia' — la GUC la impone il chiamante, e un
        #    guard che la legge crede al chiamante. Qui si pretende il DATO:
        #    o dici chi sei, o dici per quale azienda stai generando.
        ErrorManager.require(
            not (emittente_scope is None and user is None),
            code=E_VALIDATION,
            message=(
                "Generazione senza utente e senza perimetro emittente: "
                "il processo non dichiara per conto di chi genera."
            ),
            detail=(
                "Passare `emittente_scope=[<emittente_fiscale_id>]` — il "
                "perimetro dell'utente tecnico del processo — oppure lo user "
                "della richiesta."
            ),
        )
        return emittente_scope

    # Scopo: Il modello e la versione con cui si stampa questo documento,
    #        chiesti alla porta unica del DB (`repo.risolvi_template_applicabile`
    #        -> `documenti.fn_risolvi_template_applicabile`,
    #        brief-db-modelli-documento-standard §10.3 K-2). Ritorna
    #        `(template, versione)`. Una chiamata, due ingressi:
    #         a) nessun modello indicato -> il DB lo SCEGLIE coi due livelli:
    #            il predefinito dell'emittente se ha modelli suoi che possono
    #            stampare, se no lo standard. `tipo_documento_output_id` si
    #            passa quando il chiamante lo ha; senza, il DB lo deduce se il
    #            candidato e' uno;
    #         b) modello indicato (`template_documento_id`: l'override della
    #            coda di stampa, il parametro delle viste) -> il DB lo
    #            VERIFICA: adatto al documento (E_DOCUMENTI_TEMPLATE_NON_COERENTE,
    #            motivo SORGENTE / TIPO / EMITTENTE) e stampabile oggi
    #            (E_DOCUMENTI_TEMPLATE_NON_STAMPABILE, motivo MODELLO_SPENTO /
    #            NESSUNA_VERSIONE_VALIDA).
    #        I rifiuti escono come ServiceError col codice del DB, anche per il
    #        worker della coda di stampa, che scrive il motivo sulla riga.
    # ⚠️ Il perimetro resta del BE, ed e' l'unica cosa che si controlla qui: il
    #    modello indicato si legge PRIMA dentro lo scope (404, come ogni
    #    lettura). Senza, il rifiuto del DB nominerebbe il codice di un modello
    #    di un'azienda che l'operatore non vede; e un id che non e' un modello
    #    arriverebbe al DB come argomento rotto (500) invece che come «non
    #    trovato».
    # ⛔ Ritirati il 2026-10-21 (§11.2 B-2): `_guard_template_coerente`, la
    #    copia BE della regola 4 di `trgfn_documenti_generati_check_coerenza`
    #    (non guardava il tipo del modello indicato), e
    #    `_resolve_versione_pubblicata` con `_today`, la seconda copia di «puo'
    #    stampare», gia' divergente: non guardava se il modello era attivo, e
    #    usava il giorno del BE invece di `script.fn_data_operativa()`.
    def _resolve_template(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        *,
        scope: list[int] | None,
        emittente_fiscale_id: int,
        sorgente_tipo_id: int,
        tipo_documento_output_id: int | None,
        template_documento_id: int | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        indicato: dict[str, Any] | None = None
        if template_documento_id is not None:
            self._v.guard_positive_int(template_documento_id, field="template_documento_id")
            indicato = self._repo.get_template(
                template_documento_id, emittente_ids_scope=scope,
            )
            ErrorManager.require(
                indicato is not None,
                code=E_NOT_FOUND,
                message="Template documento non trovato.",
                detail=f"template_id={template_documento_id}",
            )

        with translate_db_errors(
            context={
                "sorgente_tipo_id": sorgente_tipo_id,
                "emittente_fiscale_id": emittente_fiscale_id,
                "tipo_documento_output_id": tipo_documento_output_id,
                "template_documento_id": template_documento_id,
            },
            fallback_code=E_TEMPLATE_NON_RISOLTO,
            fallback_message=USER_MESSAGE_FALLBACK[E_TEMPLATE_NON_RISOLTO],
        ):
            risolto = self._repo.risolvi_template_applicabile(
                sorgente_tipo_id=sorgente_tipo_id,
                emittente_fiscale_id=emittente_fiscale_id,
                tipo_documento_output_id=tipo_documento_output_id,
                template_documento_id=template_documento_id,
            )
        template_id = int(risolto["template_documento_id"])
        template = indicato if indicato is not None else self._repo.get_template(
            template_id, emittente_ids_scope=scope,
        )
        # Il modello risolto e' dell'emittente del documento (gia' in scope) o
        # standard (sempre in scope); la versione l'ha appena scelta il DB per
        # quel modello. Non trovarli e' il patto del DB rotto, non un 404
        # dell'operatore. RuntimeError e non `assert`: dipende da cosa risponde
        # il DB, e il controllo resta acceso anche con `python -O`.
        if template is None:
            raise RuntimeError(f"template risolto {risolto!r} non leggibile")
        versione = self._repo.get_versione(template_id, int(risolto["template_versione_id"]))
        if versione is None:
            raise RuntimeError(f"versione risolta {risolto!r} non leggibile")
        return template, versione

    # Scopo: Il patto versione/forma dei dati, chiesto al DB prima del render
    #        (R-3 di brief-db-documenti-versione-contesto-template): la
    #        versione deve leggere `CONTEXT_VERSION` del builder, da cui esce
    #        anche `_meta.context_version`. La regola e' della funzione DB, qui
    #        si traduce solo il rifiuto: 409 E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA
    #        con la frase a catalogo, che nomina versione, template e le due
    #        forme. Stesso ServiceError anche per il worker della coda di
    #        stampa, che scrive il motivo sulla riga.
    def _guard_versione_contesto(
        self, versione: dict[str, Any], builder: DocumentContextBuilder,
    ) -> None:
        with translate_db_errors(
            context={
                "template_versione_id": versione["id"],
                "versione_contesto": builder.CONTEXT_VERSION,
                "context_code": builder.CODE,
            },
            fallback_code=E_VERSIONE_CONTESTO_NON_VERIFICABILE,
            fallback_message=USER_MESSAGE_FALLBACK[E_VERSIONE_CONTESTO_NON_VERIFICABILE],
        ):
            self._repo.guard_versione_contesto(
                versione["id"], builder.CONTEXT_VERSION,
            )

    # Scopo: Invoca `build_context(sorgente_id)` sul builder gia' risolto.
    def _build_context_for_sorgente(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        builder: DocumentContextBuilder,
        sorgente_id: int,
        *,
        locale: str,
    ) -> dict[str, Any]:
        return builder.build_context(
            sorgente_id,
            auth_user_id=getattr(user, "id", None),
            locale=locale,
        )

    # Scopo: Espande il pattern `file_name_pattern` del template con il
    #        context. v1: usa `str.format(**context)` (no Jinja qui — il
    #        pattern e' una stringa breve, non un template HTML). KeyError
    #        / IndexError -> E_DOCUMENTI_RENDER_FAILED parlante.
    def _format_nome_file(
        self, template: dict[str, Any], context: dict[str, Any],
    ) -> str:
        pattern = template.get("file_name_pattern") or ""
        if not pattern:
            # Fallback deterministico se pattern assente: codice template
            # + estensione PDF (e' garantito non vuoto da DDL CHECK).
            return f"{template['codice']}.pdf"
        try:
            return str.format(pattern, **context)
        except (KeyError, IndexError) as exc:
            ErrorManager.raise_error(
                code=E_RENDER_FAILED,
                message=(
                    "Variabile mancante nel context per il pattern "
                    f"file_name '{pattern}'."
                ),
                detail=f"missing={exc!r}",
            )

    # Scopo: Titolo applicativo del documento generato. v1: descrizione
    #        del template (sempre valorizzata) come fallback codice.
    def _build_titolo(self, template: dict[str, Any]) -> str:
        descr = (template.get("descrizione") or "").strip()
        if descr:
            return descr
        return str(template.get("codice") or "Documento")

    # Scopo: SHA256 hex su stringa UTF-8.
    def _sha256_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    # Scopo: SHA256 hex su bytes.
    def _sha256_bytes(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    # Scopo: Il risolutore degli asset di UN render (contratto `RisolviAsset`
    #        di `render_service`): `asset:<codice_interno>` -> (contenuto,
    #        mime_type), letto dallo storage dentro il perimetro di UN
    #        emittente, quello del template. Nessun livello globale e nessun
    #        ripiego (§4.3 del brief, Tid 2026-10-01): un asset che non c'e' e'
    #        E_DOCUMENTI_RENDER_FAILED, perche' un logo generico al suo posto
    #        darebbe un PDF sbagliato senza errore.
    #        ⭐ Si crea per render (factory): la cache dei file letti e' stato,
    #        e non si condivide fra due render.
    #        ⚠️ L'impronta del file letto si confronta con `sha256` della riga:
    #        la riga e' immutabile a DB, il file sul disco no, e la ristampa
    #        fedele si regge proprio su "stesso codice_interno, stessi byte".
    def _risolutore_asset(
        self, emittente_fiscale_id: int, *, solo_validi: bool,
    ) -> RisolviAsset:
        letti: dict[str, tuple[bytes, str]] = {}

        def risolvi(codice_interno: str) -> tuple[bytes, str]:
            if codice_interno in letti:
                return letti[codice_interno]
            asset = self._repo.get_asset_per_render(
                emittente_fiscale_id, codice_interno, solo_validi=solo_validi,
            )
            ErrorManager.require(
                asset is not None,
                code=E_RENDER_FAILED,
                message=(
                    "Il template richiama un asset che l'emittente non ha"
                    + (" attivo e valido oggi." if solo_validi else ".")
                ),
                detail=(
                    f"asset:{codice_interno} "
                    f"emittente_fiscale_id={emittente_fiscale_id}"
                ),
            )
            assert asset is not None
            # ⚠️ Un errore di IO va tradotto QUI (`leggi_da_storage`): dal
            #    fetcher di WeasyPrint un'eccezione qualunque uscirebbe come
            #    «risorsa non ammessa», e si cercherebbe l'errore nel template.
            contenuto = leggi_da_storage(
                self._storage_factory(), asset["storage_key"],
                message="Errore lettura asset documentale dallo storage.",
                detail=f"asset_id={asset['id']} asset:{codice_interno}",
            )
            ErrorManager.require(
                self._sha256_bytes(contenuto) == asset["sha256"],
                code=E_STORAGE_FAILED,
                message=(
                    "Il file dell'asset sullo storage non corrisponde "
                    "all'impronta registrata."
                ),
                detail=f"asset_id={asset['id']} asset:{codice_interno}",
            )
            letti[codice_interno] = (contenuto, asset["mime_type"])
            return letti[codice_interno]

        return risolvi

    # Scopo: Serializzazione JSON canonica del context (sort_keys + default=str
    #        per oggetti non-serializzabili come Decimal/date). Il risultato
    #        e' deterministico: stesso context -> stesso `context_hash`.
    def _json_canonical(self, value: Any) -> str:
        return json.dumps(
            value, sort_keys=True, ensure_ascii=False, default=str,
        )

    # Scopo: SHA256 della concatenazione html|css|markdown. Il template_hash
    #        identifica univocamente il payload-template usato per quel
    #        render: utile per auditing e riconoscimento di re-render dopo
    #        cambio versione.
    #        Separator: NULL byte (`\x00`) — non puo' apparire in HTML/CSS/
    #        markdown valido (collision-proof rispetto a separator
    #        markdown-style come `--CSS--`).
    def _compute_template_hash(self, versione: dict[str, Any]) -> str:
        html = versione.get("html_template") or ""
        css = versione.get("css_template") or ""
        markdown = versione.get("markdown_template") or ""
        composite = f"{html}\x00{css}\x00{markdown}"
        return self._sha256_text(composite)

    # Scopo: Estrae estensione lower-case dal nome_file (default 'pdf').
    def _resolve_extension(self, nome_file: str) -> str:
        _, ext = os.path.splitext(nome_file or "")
        ext = ext.lstrip(".").lower().strip()
        if ext and ext.isalnum() and len(ext) <= 10:
            return ext
        return _EXT_PDF

    # =================================================================
    # Helpers privati — allegati (file secondari)
    # =================================================================

    # Scopo: Valida e normalizza la lista di allegati in input. Ogni allegato
    #        e' un dict `{file_bytes, mime_type, file_name}` (il view estrae
    #        i bytes da request.FILES). Controlli fail-fast:
    #         - file non vuoto;
    #         - MIME ∈ whitelist (PDF/jpeg/png);
    #         - size <= `documenti_allegato_upload_max_mb`.
    #        Ritorna lista di record pronti per il persist (sha256 +
    #        storage_key deterministici, file_name sanitizzato). Lista vuota
    #        se `allegati` e' None/vuoto (caso "solo principale").
    def _valida_e_prepara_allegati(
        self,
        allegati: list[dict[str, Any]] | None,
        emittente_fiscale_id: int,
    ) -> list[dict[str, Any]]:
        if not allegati:
            return []
        max_mb = self._params.get_parameter_int(_PARAM_ALLEGATO_MAX_MB)
        max_bytes = max_mb * 1024 * 1024
        prepared: list[dict[str, Any]] = []
        for idx, allegato in enumerate(allegati):
            file_bytes = allegato.get("file_bytes")
            mime = (allegato.get("mime_type") or "").strip().lower()
            name = allegato.get("file_name") or ""
            if not isinstance(file_bytes, (bytes, bytearray)) or len(file_bytes) == 0:
                ErrorManager.raise_error(
                    code=E_VALIDATION,
                    message="Allegato vuoto o non leggibile.",
                    detail=f"allegato_index={idx} file_name={name!r}",
                )
            if mime not in _MIME_WHITELIST_ALLEGATO:
                ErrorManager.raise_error(
                    code=E_VALIDATION,
                    message=(
                        "Tipo file allegato non ammesso. "
                        "Ammessi: PDF, JPEG, PNG."
                    ),
                    detail=f"allegato_index={idx} mime={mime!r}",
                )
            size = len(file_bytes)
            if size > max_bytes:
                ErrorManager.raise_error(
                    code=E_VALIDATION,
                    message=f"Allegato troppo grande. Limite: {max_mb} MB.",
                    detail=f"allegato_index={idx} size_bytes={size} max_bytes={max_bytes}",
                )
            file_bytes_immutable = bytes(file_bytes)
            sha = self._sha256_bytes(file_bytes_immutable)
            ext = self._resolve_extension_allegato(name, mime)
            prepared.append({
                "file_bytes": file_bytes_immutable,
                "mime_type": mime,
                "file_name": self._sanitize_file_name_allegato(name),
                "file_size_bytes": size,
                "sha256": sha,
                "storage_key": f"documenti/{emittente_fiscale_id}/{sha}.{ext}",
            })
        return prepared

    # Scopo: Risolve l'id del tipo file ALLEGATO (lookup per codice, no ID
    #        hardcoded). Errore parlante se il seed manca o e' disattivato.
    def _resolve_tipo_allegato_id(self) -> int:
        tipo = self._repo.get_tipo_file_documento_by_codice(
            _CODICE_TIPO_FILE_ALLEGATO,
        )
        ErrorManager.require(
            tipo is not None and tipo.get("attivo"),
            code=E_VALIDATION,
            message="Tipo file 'ALLEGATO' non configurato o non attivo.",
        )
        assert tipo is not None
        return int(tipo["id"])

    # Scopo: INSERT righe file secondarie + storage write per gli allegati,
    #        dentro una transazione gia' aperta dal caller. Accumula gli
    #        storage_uri scritti in `written_uris` (per cleanup orfani lato
    #        caller). Ritorna i metadati degli allegati persistiti.
    def _persisti_allegati(
        self,
        storage: DocumentStorage,
        *,
        documento_generato_id: int,
        tipo_allegato_id: int,
        prepared: list[dict[str, Any]],
        ordinamento_start: int,
        written_uris: list[str],
    ) -> list[dict[str, Any]]:
        persistiti: list[dict[str, Any]] = []
        for offset, allegato in enumerate(prepared):
            ordinamento = ordinamento_start + offset
            file_data = {
                "documento_generato_id": documento_generato_id,
                "file_tipo_id": tipo_allegato_id,
                "mime_type": allegato["mime_type"],
                "file_name": allegato["file_name"],
                "file_size_bytes": allegato["file_size_bytes"],
                "storage_key": allegato["storage_key"],
                "sha256": allegato["sha256"],
                "ordinamento": ordinamento,
                "is_principale": False,
                "meta": {},
            }
            file_id = self._repo.create_documento_generato_file(file_data)
            # write storage dopo INSERT OK: rollback tx -> nessuno stato
            # incoerente; cleanup file in caso di commit fallito.
            written_uris.append(storage.write(
                allegato["storage_key"],
                allegato["file_bytes"],
                content_type=allegato["mime_type"],
            ))
            persistiti.append({
                "id": file_id,
                "file_name": allegato["file_name"],
                "mime_type": allegato["mime_type"],
                "size_bytes": allegato["file_size_bytes"],
                "ordinamento": ordinamento,
            })
        return persistiti

    # Scopo: Cleanup best-effort dei file storage scritti quando il commit DB
    #        fallisce (STORAGE_ORPHAN). Non solleva: logga e prosegue per non
    #        mascherare l'eccezione originale del commit.
    def _cleanup_storage_orphans(
        self,
        storage: DocumentStorage,
        written_uris: list[str],
        pdf_hash: str | None,
    ) -> None:
        for uri in written_uris:
            try:
                storage.delete(uri)
                logger.warning(
                    "documenti.documento.storage_orphan_cleanup_ok "
                    "storage_uri=%s pdf_hash=%s",
                    uri, pdf_hash,
                )
            except Exception:
                logger.exception(
                    "documenti.documento.storage_orphan_cleanup_failed "
                    "storage_uri=%s pdf_hash=%s",
                    uri, pdf_hash,
                )

    # Scopo: Estensione lower-case dell'allegato dal file_name; fallback al
    #        MIME se l'estensione manca o non e' plausibile.
    def _resolve_extension_allegato(self, file_name: str, mime: str) -> str:
        _, ext = os.path.splitext(file_name or "")
        ext = ext.lstrip(".").lower().strip()
        if ext and ext.isalnum() and len(ext) <= 10:
            return ext
        return _MIME_EXT_FALLBACK_ALLEGATO.get(mime, "bin")

    # Scopo: Sanitizza il nome file allegato: basename (no path traversal) +
    #        troncamento alla lunghezza massima. Fallback se vuoto.
    def _sanitize_file_name_allegato(self, file_name: str) -> str:
        base = os.path.basename((file_name or "").strip().replace("\\", "/"))
        base = base.strip() or "allegato"
        return base[:_MAX_ALLEGATO_FILE_NAME_LEN]
