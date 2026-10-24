# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Service admin per ciclo vita versione template documentale
#        (Tranche F). 5 metodi pubblici:
#        - create_versione (sempre BOZZA)
#        - update_versione (consentito solo su BOZZA — defense lato BE
#          + trigger DB A1 protect_pubblicata)
#        - delete_versione (hard DELETE — trigger DB A2 block_delete
#          rifiuta non-BOZZA o gia' usate da documenti generati)
#        - clone_versione (la copia la fa il DB, `fn_crea_bozza_da_versione`,
#          con le sostituzioni del payload)
#        - pubblica_versione (transizione atomica BOZZA -> PUBBLICATA con
#          valido_dal NOT NULL guard; EXCLUDE GiST DB blocca overlap con
#          altre PUBBLICATE attive — errore parlante via mapper; la forma
#          dei dati del builder del template passa al verbo DB, che rifiuta
#          una versione che ne legge un'altra)
#
#        `versione_contesto` = la forma dei dati che la versione dichiara di
#        leggere (brief-db-documenti-versione-contesto-template): obbligatoria
#        in create, modificabile solo in BOZZA, copiata dal clone. Una BOZZA
#        puo' dichiarare una forma che il builder non produce ancora (D-C4):
#        e' cosi' che si prepara la versione successiva.
#
#        Scope emittente derivato dal template (404 unificato no leak).
#        Validazione payload via PayloadValidator + map_integrity_error
#        per guardrail DB.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, NoReturn

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db import IntegrityError, transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import (
    PayloadValidator,
    map_integrity_error,
)
from apps.documenti.db.documenti_repository import DocumentiRepository
from apps.documenti.services.context_builders import get_builder_del_template
from apps.documenti.services.template_service import TemplateService

# Codici errore registrati in apps.core.services.error_policies.
E_VALIDATION = "E_DOCUMENTI_VALIDATION"
E_NOT_FOUND = "E_DOCUMENTI_NOT_FOUND"
E_VERSIONE_PUBBLICATA_IMMUTABILE = "E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE"
E_VERSIONE_DELETE_BLOCKED = "E_DOCUMENTI_VERSIONE_DELETE_BLOCKED"
E_VERSIONE_OVERLAP = "E_DOCUMENTI_VERSIONE_OVERLAP"

# Chiavi ammesse in payload create versione (no `versione`/`stato` —
# calcolati dal service; no `template_documento_id` — dal path).
_CREATE_KEYS: frozenset[str] = frozenset({
    "titolo",
    "formato_template",
    "html_template",
    "css_template",
    "markdown_template",
    "render_engine_id",
    "page_format",
    "page_orientation",
    "margin_top_mm",
    "margin_right_mm",
    "margin_bottom_mm",
    "margin_left_mm",
    "valido_dal",
    "valido_al",
    "versione_contesto",
    "context_schema",
    "meta",
    "attivo",
})

# Chiavi ammesse in payload update versione.
_UPDATE_KEYS: frozenset[str] = _CREATE_KEYS

# Chiavi ammesse in payload clone (override sui campi del source).
# Il rest viene copiato; questi sono i pochi che ha senso cambiare.
_CLONE_KEYS: frozenset[str] = frozenset({
    "titolo",
    "valido_dal",
    "valido_al",
    "attivo",
    "meta",
})

# Chiavi ammesse in payload pubblica.
_PUBBLICA_KEYS: frozenset[str] = frozenset({
    "valido_dal",
    "valido_al",
})


# Mapping vincoli DB -> codici applicativi parlanti.
_UNIQUE_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "uq_template_documenti_versioni_template_versione": (
        E_VALIDATION,
        "Numero versione gia' presente per il template (race condition: riprovare).",
    ),
    # Codice overlap dedicato (409) — simmetrico a E_VENDITE_PROMO_OVERLAP /
    # E_VENDITE_LISTINO_VERSIONE_OVERLAP. Testo allineato a error_policies
    # (error_translator preferisce ServiceError.message su policy.user_message).
    "ex_template_documenti_versioni_no_overlap_pubblicata": (
        E_VERSIONE_OVERLAP,
        "Le date di validita' si sovrappongono con un'altra versione "
        "PUBBLICATA attiva del template. Chiudi quella esistente prima "
        "di pubblicare la nuova.",
    ),
}


# I valori ammessi di formato del template, formato e orientamento della
# pagina: la FK sui tre vocabolari (`documenti.formati_template`,
# `formati_pagina`, `orientamenti_pagina`, chiave `codice_interno`).
# ⛔ Nessuna copia dell'insieme qui: fino al 2026-10-04 erano tre `frozenset`
#    accanto ai CHECK, e la copia del frontend era gia' divergente
#    (brief-db-vocabolari-versione-template §2). Il rifiuto lo da' la FK.
_FK_CONSTRAINTS: dict[str, tuple[str, str, str]] = {
    "fk_template_documenti_versioni_formati_template": (
        E_VALIDATION,
        "Formato template non valido.",
        "formato_template",
    ),
    "fk_template_documenti_versioni_formati_pagina": (
        E_VALIDATION,
        "Formato pagina non valido.",
        "page_format",
    ),
    "fk_template_documenti_versioni_orientamenti_pagina": (
        E_VALIDATION,
        "Orientamento pagina non valido.",
        "page_orientation",
    ),
}


# Mapping CHECK constraint del DDL -> codici applicativi (frammento case-insensitive).
_CHECK_CONSTRAINTS: dict[str, tuple[str, ...]] = {
    "chk_template_documenti_versioni_versione_pos": (
        E_VALIDATION,
        "Il numero versione deve essere positivo.",
    ),
    "chk_template_documenti_versioni_stato": (
        E_VALIDATION,
        "Stato versione non valido.",
    ),
    "chk_template_documenti_versioni_margini_non_neg": (
        E_VALIDATION,
        "I margini di pagina non possono essere negativi.",
    ),
    "chk_template_documenti_versioni_titolo_non_vuoto": (
        E_VALIDATION,
        "Il titolo della versione non puo' essere vuoto.",
    ),
    "chk_template_documenti_versioni_valido_dal_pubblicata": (
        E_VALIDATION,
        "Una versione PUBBLICATA deve avere valido_dal valorizzato.",
    ),
    "chk_template_documenti_versioni_versione_contesto_pos": (
        E_VALIDATION,
        "La forma dei dati letta dalla versione deve essere un intero positivo.",
        "versione_contesto",
    ),
}


# Mapping codici sollevati da fn_log_and_raise_error nei trigger A1/A2.
# `map_integrity_error` non lo intercetta direttamente (sono RAISE di P0001,
# non IntegrityError), ma una guard service-side tradurra' in errori puliti.
# Qui mantengo solo la mappa applicativa per documentazione.


class TemplateVersioniAdminService:
    """Service admin write per versioni template documentale."""

    def __init__(
        self,
        repo: DocumentiRepository | None = None,
        reader: TemplateService | None = None,
    ) -> None:
        self._repo = repo or DocumentiRepository()
        self._reader = reader or TemplateService(repo=self._repo)
        self._v = PayloadValidator(validation_code=E_VALIDATION)

    # =================================================================
    # Create versione (sempre BOZZA)
    # =================================================================

    # Scopo: Crea una nuova versione BOZZA per un template. Il numero
    #        versione e' calcolato come MAX(versione)+1 nello stesso
    #        template; lo stato e' fissato a 'BOZZA' (transizione a
    #        PUBBLICATA passa solo da pubblica_versione).
    def create_versione(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        # 404 unificato se template assente o fuori scope.
        self._reader.get_template(user, template_id)

        self._v.validate_allowed_keys(
            payload,
            allowed=_CREATE_KEYS,
            message="Payload versione template non valido.",
        )
        data = self._build_create_data(payload)
        data["template_documento_id"] = int(template_id)
        data["stato"] = "BOZZA"
        data["versione"] = self._repo.next_versione_num(template_id)

        try:
            new_id = self._repo.create_versione(data)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                check_constraints=_CHECK_CONSTRAINTS,
                fallback_code=E_VALIDATION,
                fallback_message="Violazione vincolo DB su versione template.",
                context={
                    "template_documento_id": template_id,
                    "versione": data["versione"],
                },
            )

        return self._reader.get_versione(user, template_id, new_id)

    # =================================================================
    # Update versione (solo BOZZA)
    # =================================================================

    # Scopo: Aggiorna una versione esistente. Pre-check stato BOZZA lato
    #        service (errore parlante prima del trigger DB). Il trigger
    #        A1 (protect_pubblicata) e' la difesa finale per una race
    #        improbabile: pubblica_versione concorrente che cambia stato
    #        BOZZA -> PUBBLICATA tra il check service e l'UPDATE.
    def update_versione(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
        versione_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(versione_id, field="versione_id")
        # get_versione ritorna 404 unificato se template fuori scope o
        # versione orfana di altro template (binding template_id).
        existing = self._reader.get_versione(user, template_id, versione_id)
        self._guard_stato_modificabile(existing)

        self._v.validate_allowed_keys(
            payload,
            allowed=_UPDATE_KEYS,
            message="Payload versione template non valido.",
        )
        data = self._build_update_data(payload)
        self._v.require_campi_da_aggiornare(
            data,
            detail=f"allowed_keys={sorted(_UPDATE_KEYS)!r}",
        )

        try:
            updated = self._repo.update_versione(versione_id, data)
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                check_constraints=_CHECK_CONSTRAINTS,
                fallback_code=E_VALIDATION,
                fallback_message="Violazione vincolo DB su versione template.",
                context={"template_id": template_id, "versione_id": versione_id},
            )
        ErrorManager.require(
            updated,
            code=E_NOT_FOUND,
            message="Versione template non trovata.",
            detail=f"versione_id={versione_id}",
        )
        return self._reader.get_versione(user, template_id, versione_id)

    # =================================================================
    # Delete versione (solo BOZZA non usata)
    # =================================================================

    # Scopo: Elimina fisicamente una versione BOZZA. Il trigger DB A2
    #        e' la difesa finale: se OLD.stato in ('PUBBLICATA','OBSOLETA')
    #        o se ci sono documenti_generati collegati, IntegrityError
    #        -> E_DOCUMENTI_VERSIONE_DELETE_BLOCKED. Pre-check stato lato
    #        service per messaggio piu' parlante prima del DB.
    def delete_versione(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
        versione_id: int,
    ) -> None:
        self._v.guard_positive_int(versione_id, field="versione_id")
        existing = self._reader.get_versione(user, template_id, versione_id)
        if existing["stato"] != "BOZZA":
            ErrorManager.raise_error(
                code=E_VERSIONE_DELETE_BLOCKED,
                message="Solo versioni in stato BOZZA possono essere eliminate.",
                detail=f"stato_corrente={existing['stato']!r}",
            )

        try:
            deleted = self._repo.delete_versione(versione_id)
        except IntegrityError as exc:
            # Caso documenti_generati collegati: il trigger DB A2 solleva
            # P0001 con codice nostro; map_integrity_error per il fallback.
            map_integrity_error(
                exc,
                fallback_code=E_VERSIONE_DELETE_BLOCKED,
                fallback_message=(
                    "Eliminazione versione bloccata: gia' usata da documenti generati."
                ),
                context={"versione_id": versione_id},
            )
        ErrorManager.require(
            deleted,
            code=E_NOT_FOUND,
            message="Versione template non trovata.",
            detail=f"versione_id={versione_id}",
        )

    # =================================================================
    # Clone versione (SELECT source + INSERT BOZZA con override)
    # =================================================================

    # Scopo: Clona una versione esistente (qualunque stato) in una nuova
    #        versione BOZZA. Utile per editare partendo da una PUBBLICATA
    #        senza modificarla (immutabile). Il payload puo' sostituire
    #        titolo, valido_dal/al, attivo, meta.
    #        La copia la fa il DB (`repo.crea_bozza_da_versione` ->
    #        `documenti.fn_crea_bozza_da_versione`, §10.3 K-6): elenco dei campi
    #        copiati e numero della versione sono suoi. Qui la forma del payload
    #        e il perimetro (la versione d'origine si legge dentro lo scope,
    #        legata al suo template).
    # ⛔ Fino al 2026-10-21 l'elenco dei campi stava qui (`dati_bozza_copiata`,
    #    usato anche da «personalizza») e il numero lo calcolava
    #    `next_versione_num`: con «personalizza» nel DB, sarebbero stati due.
    def clone_versione(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
        source_versione_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(source_versione_id, field="versione_id")
        # 404 se source assente o template fuori scope.
        self._reader.get_versione(user, template_id, source_versione_id)

        self._v.validate_allowed_keys(
            payload,
            allowed=_CLONE_KEYS,
            message="Payload clone versione non valido.",
        )

        # Sostituzioni dal payload; una chiave assente vale «come l'origine»
        # (per le date: senza data, si fissano alla pubblicazione).
        titolo = (
            self._v.require_string(payload, "titolo", max_len=500)
            if "titolo" in payload else None
        )
        valido_dal = self._v.optional_date(payload, "valido_dal") if "valido_dal" in payload else None
        valido_al = self._v.optional_date(payload, "valido_al") if "valido_al" in payload else None
        # L'ordine delle date lo giudica il DB: guard comune
        # `script.trgfn_guard_date_validita`, E_DATA_AL_MINORE_DAL col campo
        # `valido_al` (dal 2026-09-23).
        attivo: bool | None = None
        if "attivo" in payload:
            v = self._v.optional_bool(payload, "attivo")
            ErrorManager.require(
                v is not None,
                code=E_VALIDATION,
                message="Il campo 'attivo' non puo' essere NULL.",
                detail="field=attivo",
            )
            attivo = bool(v)
        meta = self._v.optional_meta(payload) if "meta" in payload else None

        try:
            new_id = self._repo.crea_bozza_da_versione(
                source_versione_id,
                template_documento_id=int(template_id),
                titolo=titolo,
                valido_dal=valido_dal,
                valido_al=valido_al,
                attivo=attivo,
                meta=meta,
            )
        except IntegrityError as exc:
            map_integrity_error(
                exc,
                unique_constraints=_UNIQUE_CONSTRAINTS,
                fk_constraints=_FK_CONSTRAINTS,
                check_constraints=_CHECK_CONSTRAINTS,
                fallback_code=E_VALIDATION,
                fallback_message="Violazione vincolo DB nel clone versione.",
                context={
                    "template_documento_id": template_id,
                    "source_versione_id": source_versione_id,
                },
            )

        return self._reader.get_versione(user, template_id, new_id)

    # =================================================================
    # Pubblica versione (BOZZA -> PUBBLICATA atomic)
    # =================================================================

    # Scopo: Transizione atomica BOZZA -> PUBBLICATA. Richiede valido_dal
    #        non NULL. Il DB rifiuta overlap di range con altre PUBBLICATE
    #        attive (EXCLUDE GiST). Il service esegue UPDATE ATOMIC con
    #        WHERE stato='BOZZA' (idempotente per design: una seconda
    #        chiamata su versione gia' pubblicata torna 404 per "non in
    #        BOZZA" piuttosto che modificare lo stato).
    def pubblica_versione(
        self,
        user: AbstractBaseUser | AnonymousUser | None,
        template_id: int,
        versione_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._v.guard_positive_int(versione_id, field="versione_id")
        existing = self._reader.get_versione(user, template_id, versione_id)
        if existing["stato"] != "BOZZA":
            ErrorManager.raise_error(
                code=E_VALIDATION,
                message="Solo versioni in stato BOZZA possono essere pubblicate.",
                detail=f"stato_corrente={existing['stato']!r}",
            )

        self._v.validate_allowed_keys(
            payload,
            allowed=_PUBBLICA_KEYS,
            message="Payload pubblicazione non valido.",
        )
        valido_dal = self._v.require_date(payload, "valido_dal")
        valido_al: date | None = None
        if "valido_al" in payload:
            valido_al = self._v.optional_date(payload, "valido_al")

        # L'ordine delle date lo giudica il DB: guard comune
        # `script.trgfn_guard_date_validita`, E_DATA_AL_MINORE_DAL col campo
        # `valido_al` (dal 2026-09-23).

        # La forma dei dati che il builder del template produce oggi: il verbo
        # DB pubblica solo una versione che dichiara di leggere quella (409
        # E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA). Un builder assente o non
        # registrato e' E_DOCUMENTI_VALIDATION dal registry (lo stesso rifiuto
        # della generazione): senza builder non c'e' forma con cui confrontare.
        template = self._reader.get_template(user, template_id)
        forma_builder = get_builder_del_template(template).CONTEXT_VERSION

        with transaction.atomic():
            try:
                published = self._repo.pubblica_versione(
                    versione_id, valido_dal=valido_dal, valido_al=valido_al,
                    versione_contesto=forma_builder,
                )
            except IntegrityError as exc:
                map_integrity_error(
                    exc,
                    unique_constraints=_UNIQUE_CONSTRAINTS,
                    fk_constraints=_FK_CONSTRAINTS,
                    check_constraints=_CHECK_CONSTRAINTS,
                    fallback_code=E_VALIDATION,
                    fallback_message="Violazione vincolo DB in pubblicazione versione.",
                    context={"template_id": template_id, "versione_id": versione_id},
                )
            ErrorManager.require(
                published,
                code=E_VALIDATION,
                message="Pubblicazione fallita: la versione potrebbe essere stata gia' pubblicata.",
                detail=f"versione_id={versione_id}",
            )
        return self._reader.get_versione(user, template_id, versione_id)

    # =================================================================
    # Helpers privati
    # =================================================================

    # Scopo: Defense lato service: una versione modificabile e' BOZZA.
    #        Il trigger DB A1 e' il guardrail finale (race condition fra
    #        check service e UPDATE).
    def _guard_stato_modificabile(self, versione: dict[str, Any]) -> None:
        if versione["stato"] != "BOZZA":
            ErrorManager.raise_error(
                code=E_VERSIONE_PUBBLICATA_IMMUTABILE,
                message="Versione non modificabile: stato non BOZZA.",
                detail=f"stato_corrente={versione['stato']!r}",
            )

    # Scopo: Compone il dict da passare al repository per create.
    #        Campi obbligatori: titolo, html_template, render_engine_id,
    #        versione_contesto.
    #        Tutti gli altri seguono i default DDL/DB.
    def _build_create_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        # Campi obbligatori (require_required=True).
        data["titolo"] = self._v.require_string(payload, "titolo", max_len=500)
        data["html_template"] = self._v.require_string(
            payload, "html_template", max_len=10_000_000
        )
        data["render_engine_id"] = self._v.require_positive_int(
            payload, "render_engine_id"
        )
        # ⛔ Nessun default: la forma la dichiara chi scrive la versione (il
        #    DB non ne ha, e un default sarebbe una forma dichiarata da nessuno).
        data["versione_contesto"] = self._v.require_positive_int(
            payload, "versione_contesto"
        )
        self._fill_optional_versione_fields(data, payload)
        # In create `attivo` ha default applicativo True (no ErrorManager guard).
        if "attivo" in payload:
            v = self._v.optional_bool(payload, "attivo")
            data["attivo"] = bool(v) if v is not None else True
        return data

    # Scopo: Compone il dict per update ignorando chiavi assenti. Stessa
    #        validazione del create per i campi presenti, ma `titolo`,
    #        `html_template`, `render_engine_id` opzionali. `attivo` non
    #        ammette `null` esplicito (NOT NULL DDL).
    def _build_update_data(self, payload: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        # Campi "obbligatori in create" qui opzionali.
        if "titolo" in payload:
            data["titolo"] = self._v.require_string(payload, "titolo", max_len=500)
        if "html_template" in payload:
            data["html_template"] = self._v.require_string(
                payload, "html_template", max_len=10_000_000
            )
        if "render_engine_id" in payload:
            data["render_engine_id"] = self._v.require_positive_int(
                payload, "render_engine_id"
            )
        if "versione_contesto" in payload:
            data["versione_contesto"] = self._v.require_positive_int(
                payload, "versione_contesto"
            )
        self._fill_optional_versione_fields(data, payload)
        if "attivo" in payload:
            v = self._v.optional_bool(payload, "attivo")
            ErrorManager.require(
                v is not None,
                code=E_VALIDATION,
                message="Il campo 'attivo' non puo' essere NULL.",
                detail="field=attivo",
            )
            data["attivo"] = bool(v)
        return data

    # Scopo: Helper condiviso fra create e update — valida e mappa i campi
    #        opzionali strutturalmente identici (formato/payload aux/page
    #        layout/validita/context_schema/meta). NON include i 3 campi
    #        "obbligatori in create" (gestiti dal chiamante) ne' `attivo`
    #        (logica diversa fra create e update).
    def _fill_optional_versione_fields(
        self, data: dict[str, Any], payload: dict[str, Any]
    ) -> None:
        if "formato_template" in payload:
            data["formato_template"] = self._v.require_string(
                payload, "formato_template", max_len=30
            )
        if "css_template" in payload:
            v = payload["css_template"]
            data["css_template"] = (
                None if v is None else self._v.require_string(
                    payload, "css_template", max_len=10_000_000
                )
            )
        if "markdown_template" in payload:
            v = payload["markdown_template"]
            data["markdown_template"] = (
                None if v is None else self._v.require_string(
                    payload, "markdown_template", max_len=10_000_000
                )
            )
        if "page_format" in payload:
            data["page_format"] = self._v.require_string(
                payload, "page_format", max_len=30
            )
        if "page_orientation" in payload:
            data["page_orientation"] = self._v.require_string(
                payload, "page_orientation", max_len=20
            )
        for key in (
            "margin_top_mm", "margin_right_mm", "margin_bottom_mm", "margin_left_mm",
        ):
            if key in payload:
                data[key] = _coerce_non_negative_number(payload[key], field=key)
        if "valido_dal" in payload:
            data["valido_dal"] = self._v.optional_date(payload, "valido_dal")
        if "valido_al" in payload:
            data["valido_al"] = self._v.optional_date(payload, "valido_al")
        # L'ordine delle date lo giudica il DB: guard comune
        # `script.trgfn_guard_date_validita`, E_DATA_AL_MINORE_DAL col campo
        # `valido_al` (dal 2026-09-23).
        if "context_schema" in payload:
            cs = payload["context_schema"]
            if cs is not None and not isinstance(cs, dict):
                ErrorManager.raise_error(
                    code=E_VALIDATION,
                    message="context_schema deve essere un oggetto JSON.",
                )
            if cs is not None:
                data["context_schema"] = cs
        if "meta" in payload:
            m = self._v.optional_meta(payload)
            if m is not None:
                data["meta"] = m


def _coerce_non_negative_number(value: Any, *, field: str) -> int | float:
    if isinstance(value, bool):
        _raise_invalid_margin(field, value)
    if isinstance(value, int):
        if value < 0:
            _raise_invalid_margin(field, value)
        return value
    if isinstance(value, float):
        if value < 0:
            _raise_invalid_margin(field, value)
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            _raise_invalid_margin(field, value)
        try:
            parsed = Decimal(raw)
        except (InvalidOperation, ValueError):
            _raise_invalid_margin(field, value)
        if parsed < 0:
            _raise_invalid_margin(field, value)
        return float(parsed)
    _raise_invalid_margin(field, value)


def _raise_invalid_margin(field: str, value: Any) -> NoReturn:
    ErrorManager.raise_error(
        code=E_VALIDATION,
        message=f"Margine '{field}' non valido.",
        detail=f"atteso numero non negativo, ricevuto {value!r}",
    )
