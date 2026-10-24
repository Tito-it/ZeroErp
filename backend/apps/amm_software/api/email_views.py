# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API admin per gestione account email, template email e log email.
#        Tutti gli endpoint richiedono ruolo ADMIN.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers

from apps.core.api.schema_da_contratto import schema_da_contratto
from apps.core.api.schema_email import TIPI_EMAIL
from rest_framework.request import Request

from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.openapi_params import param_ricerca_full
from apps.core.api.payload_validators import (
    optional_bool,
    qp_iso_date_optional,
    corpo_oggetto,
    optional_int,
    paginated_envelope,
    parse_list_params,
)
from apps.core.api.success_responses import success_response
from apps.core.db.email_repository import EmailRepository
from apps.core.services.email_service import (
    E_EMAIL_ACCOUNT_NOT_FOUND,
    EmailDispatchService,
    smtp_non_configurato,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.error_messages_fallback import USER_MESSAGE_FALLBACK
from apps.core.services.testata_guard import o_not_found
from apps.core.services.html_sanitizer_service import sanitize_email_html
from apps.core.services.payload_helpers import PayloadValidator

from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT

E_EMAIL_ADMIN = "E_EMAIL_ADMIN"
# Validator stateless del modulo (solo il codice).
_V_EMAIL = PayloadValidator(validation_code=E_EMAIL_ADMIN)

# I «non trovato» dell'amministrazione email (brief-db-codici-non-trovato-
# email-e-permessi §2): `E_EMAIL_ADMIN` resta per i soli dati errati.
E_EMAIL_TEMPLATE_NOT_FOUND = "E_EMAIL_TEMPLATE_NOT_FOUND"
E_EMAIL_LOG_NOT_FOUND = "E_EMAIL_LOG_NOT_FOUND"


# Scopo: L'account email per id, o 404 `E_EMAIL_ACCOUNT_NOT_FOUND`. Sede unica
#        per dettaglio, modifica, eliminazione e test (regola del 2, ok Tid
#        2026-10-09).
def _account_o_404(repo: EmailRepository, account_id: int) -> dict[str, Any]:
    return o_not_found(
        repo.get_account(account_id),
        code=E_EMAIL_ACCOUNT_NOT_FOUND,
        message=USER_MESSAGE_FALLBACK[E_EMAIL_ACCOUNT_NOT_FOUND],
        detail=f"email_account_id={account_id}",
    )


# Scopo: Il template email per id, o 404 `E_EMAIL_TEMPLATE_NOT_FOUND`. Sede
#        unica per dettaglio, modifica, eliminazione e anteprima (regola del 2,
#        ok Tid 2026-10-09).
def _template_o_404(repo: EmailRepository, template_id: int) -> dict[str, Any]:
    return o_not_found(
        repo.get_template(template_id),
        code=E_EMAIL_TEMPLATE_NOT_FOUND,
        message=USER_MESSAGE_FALLBACK[E_EMAIL_TEMPLATE_NOT_FOUND],
        detail=f"email_template_id={template_id}",
    )

# Chiavi ammesse nella PATCH di un account email: il contratto dell'operatore.
# `smtp_password` e' la password IN CHIARO (la cifra il repository); `meta`
# (esito dell'ultimo test) la scrive solo l'endpoint di test.
_ACCOUNT_PATCH_KEYS: frozenset[str] = frozenset({
    "codice", "descrizione", "smtp_host", "smtp_port", "smtp_use_tls",
    "smtp_use_ssl", "smtp_username", "smtp_password", "email_from",
    "email_reply_to", "unita_organizzativa_id", "attivo",
})

# Le chiavi che la PATCH di un template email sa scrivere (2026-09-26, stessa
# regola dell'account): una chiave fuori lista e' un 400, non uno scarto.
_TEMPLATE_PATCH_KEYS: frozenset[str] = frozenset({
    "codice", "oggetto", "corpo_html", "corpo_testo", "lingua", "attivo",
    "unita_organizzativa_id", "tipo_prestazione_id", "variabili_disponibili",
})

# In CREAZIONE le chiavi sono le stesse della PATCH (i gestori leggono
# esattamente quelle), e fuori contratto e' un 400 come nella PATCH.
# ⭐ Dichiarato il 2026-09-26: prima la creazione leggeva le chiavi una per una
#    e ignorava in silenzio le altre, mentre la PATCH accanto le rifiutava.
_ACCOUNT_CREATE_KEYS: frozenset[str] = _ACCOUNT_PATCH_KEYS
_TEMPLATE_CREATE_KEYS: frozenset[str] = _TEMPLATE_PATCH_KEYS

# ── Schemi OpenAPI dei corpi: le chiavi dal contratto ────────────────────
_ACCOUNT_CREATE_REQUEST = schema_da_contratto(
    "AmmEmailAccountCreateReq", _ACCOUNT_CREATE_KEYS, tipi=TIPI_EMAIL,
    obbligatorie=("codice", "descrizione", "email_from"),
)
_ACCOUNT_PATCH_REQUEST = schema_da_contratto(
    "AmmEmailAccountPatchReq", _ACCOUNT_PATCH_KEYS, tipi=TIPI_EMAIL,
)
_TEMPLATE_CREATE_REQUEST = schema_da_contratto(
    "AmmEmailTemplateCreateReq", _TEMPLATE_CREATE_KEYS, tipi=TIPI_EMAIL,
    obbligatorie=("codice", "oggetto", "corpo_html"),
)
_TEMPLATE_PATCH_REQUEST = schema_da_contratto(
    "AmmEmailTemplatePatchReq", _TEMPLATE_PATCH_KEYS, tipi=TIPI_EMAIL,
)


# L'anteprima di un template: le variabili con cui renderlo (facoltative).
_PREVIEW_REQUEST = inline_serializer(
    name="AmmEmailTemplatePreviewReq",
    fields={"variabili": serializers.DictField(required=False, allow_null=True)},
)



# Scopo: Deriva la capability di test connessione di un account email.
#        Restituisce (can_test, test_reason). `can_test=True` significa che
#        il pulsante test in UI puo' essere abilitato; `test_reason` e' una
#        chiave i18n (lato FE) usata come tooltip quando `can_test=False`.
#        Casi gestiti:
#          - account inattivo            → ("amm.email_test_reason_inactive")
#          - host vuoto/placeholder      → il test si puo' PREMERE, e dira' di no
#          - password SMTP non impostata → ("amm.email_test_reason_no_password")
def _derive_test_capability(account: dict[str, Any]) -> tuple[bool, str | None]:
    if not account.get("attivo"):
        return False, "amm.email_test_reason_inactive"
    # ⛔ IL PREDICATO NON SI RISCRIVE QUI: `smtp_non_configurato` e' la sede
    #    unica, e questa era la seconda copia — proprio sotto un commento che
    #    dichiarava di aver centralizzato la definizione (regola del 2).
    if smtp_non_configurato(account):
        # ⚠️ Il pulsante resta ATTIVO ed e' voluto: dal 2026-09-11 il test su un
        #    account col placeholder risponde «SMTP non configurato» invece di
        #    «OK». Spegnerlo qui toglierebbe a chi guarda l'unico modo di
        #    sentirselo dire — e prima quel test rispondeva OK, cioe' il verde
        #    che ha ingannato una persona vera.
        return True, None
    if not account.get("has_smtp_password"):
        return False, "amm.email_test_reason_no_password"
    return True, None


# Scopo: Estrae da `meta` jsonb i campi "ultimo esito test" usati dalla UI.
#        Default coerenti se l'account non e' mai stato testato.
def _extract_last_test(account: dict[str, Any]) -> dict[str, Any]:
    meta = account.get("meta") or {}
    return {
        "last_test_at": meta.get("last_test_at"),
        "last_test_outcome": meta.get("last_test_outcome"),
        "last_test_message": meta.get("last_test_message"),
    }


# Scopo: Arricchisce il dict account con capability + ultimo esito test e
#        rimuove i campi grezzi (`has_smtp_password`, `meta`) dal payload
#        esposto al FE. Single source of truth: lookup `amm.email_*`.
def _enrich_account_with_capability(account: dict[str, Any]) -> dict[str, Any]:
    can_test, test_reason = _derive_test_capability(account)
    last_test = _extract_last_test(account)
    enriched = {
        **{k: v for k, v in account.items() if k != "meta"},
        "can_test": can_test,
        "test_reason": test_reason,
        **last_test,
    }
    enriched.pop("has_smtp_password", None)
    return enriched


# -------------------------------------------------------
# Account Email — CRUD
# -------------------------------------------------------


class EmailAccountListView(AdminAPIView):
    """GET: lista account email. POST: crea account email."""

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: dict},
    )
    # Scopo: Lista paginata account email con filtro ricerca e ordinamento.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(
            request.query_params, default_order="codice",
            default_limit=DEFAULT_LIMIT, max_limit=MAX_LIMIT,
        )
        repo = EmailRepository()
        results, total = repo.list_accounts(
            search=p["search"],
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(request=_ACCOUNT_CREATE_REQUEST, responses={200: dict})
    # Scopo: Crea un nuovo account email SMTP.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            _V_EMAIL.validate_allowed_keys(
                payload, allowed=_ACCOUNT_CREATE_KEYS, message="Campi dell'account non ammessi.",
            )
            codice = (payload.get("codice") or "").strip().upper()
            ErrorManager.require(bool(codice), code=E_EMAIL_ADMIN, message="Codice obbligatorio.")

            descrizione = (payload.get("descrizione") or "").strip()
            ErrorManager.require(bool(descrizione), code=E_EMAIL_ADMIN, message="Descrizione obbligatoria.")

            smtp_host = (payload.get("smtp_host") or "").strip()
            email_from = (payload.get("email_from") or "").strip()
            ErrorManager.require(bool(email_from), code=E_EMAIL_ADMIN, message="email_from obbligatorio.")

            repo = EmailRepository()
            account_id = repo.create_account(
                codice=codice,
                descrizione=descrizione,
                smtp_host=smtp_host,
                smtp_port=optional_int(payload, "smtp_port") or 587,
                smtp_use_tls=optional_bool(payload, "smtp_use_tls", default=True),
                smtp_use_ssl=optional_bool(payload, "smtp_use_ssl", default=False),
                smtp_username=(payload.get("smtp_username") or "").strip(),
                smtp_password=(payload.get("smtp_password") or ""),
                email_from=email_from,
                email_reply_to=(payload.get("email_reply_to") or "").strip() or None,
                unita_organizzativa_id=optional_int(payload, "unita_organizzativa_id"),
                attivo=optional_bool(payload, "attivo", default=True),
            )
            return repo.get_account(account_id) or {}

        return handle_post_json(request, handler=_handler)


class EmailAccountDetailView(AdminAPIView):
    """GET: dettaglio account. PATCH: modifica account. DELETE: elimina account."""

    @extend_schema(responses={200: dict})
    # Scopo: Dettaglio singolo account email per ID. Aggiunge le capability
    #        `can_test`/`test_reason` + ultimo esito test (`last_test_at`,
    #        `last_test_outcome`, `last_test_message`) usate dalla UI per
    #        gating del pulsante "Testa connessione" (Fase 6).
    def get(self, request: Request, account_id: int) -> JsonResponse:
        return success_response(_enrich_account_with_capability(_account_o_404(EmailRepository(), account_id)))

    @extend_schema(request=_ACCOUNT_PATCH_REQUEST, responses={200: dict})
    # Scopo: Aggiorna parzialmente un account email.
    # ⛔ Dal 2026-09-26 una chiave fuori `_ACCOUNT_PATCH_KEYS` e' un 400
    #    `E_EMAIL_ADMIN`, non piu' uno scarto silenzioso (un PATCH che «riesce»
    #    senza aver scritto il campo). Il drawer admin (`EmailAccountDrawer`)
    #    manda solo queste chiavi — verificato quel giorno.
    def patch(self, request: Request, account_id: int) -> JsonResponse:
        data = corpo_oggetto(request)
        repo = EmailRepository()
        _account_o_404(repo, account_id)
        _V_EMAIL.validate_allowed_keys(
            data, allowed=_ACCOUNT_PATCH_KEYS, message="Campi dell'account non modificabili.",
        )

        update_fields: dict[str, Any] = {}
        for field in ("codice", "descrizione", "smtp_host", "smtp_username",
                       "email_from", "email_reply_to"):
            if field in data:
                update_fields[field] = data[field].strip() if isinstance(data[field], str) else data[field]
        if "smtp_port" in data:
            update_fields["smtp_port"] = optional_int(data, "smtp_port")
        # In PATCH un flag presente vuole un booleano: `null` e' un 400, non
        # un «spegni» (con `optional_bool` il null valeva il default False).
        for field in ("smtp_use_tls", "smtp_use_ssl", "attivo"):
            if field in data:
                update_fields[field] = _V_EMAIL.require_bool(data, field)
        if "unita_organizzativa_id" in data:
            update_fields["unita_organizzativa_id"] = optional_int(data, "unita_organizzativa_id")
        if "smtp_password" in data and data["smtp_password"]:
            update_fields["smtp_password"] = data["smtp_password"]
        if "codice" in update_fields and update_fields["codice"]:
            update_fields["codice"] = update_fields["codice"].upper()

        # ⛔ Un PATCH senza campi e' un 400, non un 200 che non scrive (Tid,
        #    2026-10-20, brief-be-verifica-documentazione-api §A2).
        _V_EMAIL.require_campi_da_aggiornare(update_fields)
        repo.update_account(account_id, **update_fields)
        result = repo.get_account(account_id)
        return success_response(_enrich_account_with_capability(result) if result else {})

    @extend_schema(responses={204: None})
    # Scopo: Elimina un account email.
    def delete(self, request: Request, account_id: int) -> JsonResponse:
        repo = EmailRepository()
        # La lettura prima della cancellazione da' il 404 dalla sede unica.
        _account_o_404(repo, account_id)
        repo.delete_account(account_id)
        return JsonResponse({}, status=204)


class EmailAccountTestView(AdminAPIView):
    """POST: testa la connessione SMTP di un account.

    Oltre al risultato del test (`success`/`message`), persiste in
    `email_account.meta` l'ultimo esito (`last_test_outcome`,
    `last_test_at`, `last_test_message`) e ritorna il payload arricchito
    con le stesse capability del detail (`can_test`, `test_reason`).
    Cosi' il FE puo' aggiornare in-place la riga senza una GET extra.
    """

    @extend_schema(request=None, responses={200: dict})
    # Scopo: Verifica connessione SMTP senza inviare email. Persiste l'esito
    #        in meta jsonb e ritorna risultato + capability aggiornate.
    def post(self, request: Request, account_id: int) -> JsonResponse:
        repo = EmailRepository()
        # Verifica esistenza prima del test SMTP per dare errore 4xx coerente.
        _account_o_404(repo, account_id)

        service = EmailDispatchService()
        test_result = service.test_connection(account_id)
        outcome = "SUCCESS" if test_result.get("success") else "FAILED"
        tested_at = datetime.now(timezone.utc).isoformat()
        repo.update_account_last_test(
            account_id,
            outcome=outcome,
            tested_at=tested_at,
            message=test_result.get("message"),
        )

        # Rilegge il detail per ottenere meta aggiornato + capability fresche.
        refreshed = repo.get_account(account_id)
        assert refreshed is not None
        return success_response({
            "success": bool(test_result.get("success")),
            "message": test_result.get("message"),
            **_enrich_account_with_capability(refreshed),
        })


# -------------------------------------------------------
# Template Email — CRUD
# -------------------------------------------------------


class EmailTemplateListView(AdminAPIView):
    """GET: lista template email. POST: crea template email."""

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="codice", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: dict},
    )
    # Scopo: Lista paginata template email con filtro per codice, ricerca e
    #        ordinamento.
    def get(self, request: Request) -> JsonResponse:
        p = parse_list_params(
            request.query_params, default_order="",
            default_limit=DEFAULT_LIMIT, max_limit=MAX_LIMIT,
        )
        repo = EmailRepository()
        results, total = repo.list_templates(
            search=p["search"],
            codice=request.query_params.get("codice") or None,
            limit=p["limit"],
            offset=p["offset"],
            # `order_by` vuoto = nessuna scelta dell'operatore: il repository
            # tiene il suo default a due chiavi (codice + lingua).
            order_by=p["order_by"] or None,
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))

    @extend_schema(request=_TEMPLATE_CREATE_REQUEST, responses={200: dict})
    # Scopo: Crea un nuovo template email.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            _V_EMAIL.validate_allowed_keys(
                payload, allowed=_TEMPLATE_CREATE_KEYS, message="Campi del template non ammessi.",
            )
            codice = (payload.get("codice") or "").strip().upper()
            ErrorManager.require(bool(codice), code=E_EMAIL_ADMIN, message="Codice obbligatorio.")

            oggetto = (payload.get("oggetto") or "").strip()
            ErrorManager.require(bool(oggetto), code=E_EMAIL_ADMIN, message="Oggetto obbligatorio.")

            corpo_html = (payload.get("corpo_html") or "").strip()
            ErrorManager.require(bool(corpo_html), code=E_EMAIL_ADMIN, message="Corpo HTML obbligatorio.")

            repo = EmailRepository()
            template_id = repo.create_template(
                codice=codice,
                oggetto=oggetto,
                corpo_html=corpo_html,
                corpo_testo=(payload.get("corpo_testo") or "").strip() or None,
                lingua=(payload.get("lingua") or "it").strip(),
                unita_organizzativa_id=optional_int(payload, "unita_organizzativa_id"),
                tipo_prestazione_id=optional_int(payload, "tipo_prestazione_id"),
                variabili_disponibili=payload.get("variabili_disponibili"),
                attivo=optional_bool(payload, "attivo", default=True),
            )
            return repo.get_template(template_id) or {}

        return handle_post_json(request, handler=_handler)


class EmailTemplateDetailView(AdminAPIView):
    """GET: dettaglio template. PATCH: modifica. DELETE: elimina."""

    @extend_schema(responses={200: dict})
    # Scopo: Dettaglio singolo template email per ID (incluso corpo).
    def get(self, request: Request, template_id: int) -> JsonResponse:
        repo = EmailRepository()
        return success_response(_template_o_404(repo, template_id))

    @extend_schema(request=_TEMPLATE_PATCH_REQUEST, responses={200: dict})
    # Scopo: Aggiorna parzialmente un template email.
    # ⛔ Dal 2026-09-26 una chiave fuori `_TEMPLATE_PATCH_KEYS` e' un 400
    #    `E_EMAIL_ADMIN`, non uno scarto silenzioso. `EmailTemplateDrawer`
    #    manda `oggetto`, `corpo_html`, `corpo_testo` — verificato quel giorno.
    def patch(self, request: Request, template_id: int) -> JsonResponse:
        data = corpo_oggetto(request)
        repo = EmailRepository()
        _template_o_404(repo, template_id)
        _V_EMAIL.validate_allowed_keys(
            data, allowed=_TEMPLATE_PATCH_KEYS, message="Campi del template non modificabili.",
        )

        update_fields: dict[str, Any] = {}
        for field in ("codice", "oggetto", "corpo_html", "corpo_testo", "lingua"):
            if field in data:
                val = (data[field] or "").strip() if data[field] else None
                update_fields[field] = val
        if "attivo" in data:  # vedi la PATCH dell'account: null e' un 400
            update_fields["attivo"] = _V_EMAIL.require_bool(data, "attivo")
        if "unita_organizzativa_id" in data:
            update_fields["unita_organizzativa_id"] = optional_int(data, "unita_organizzativa_id")
        if "tipo_prestazione_id" in data:
            update_fields["tipo_prestazione_id"] = optional_int(data, "tipo_prestazione_id")
        if "variabili_disponibili" in data:
            update_fields["variabili_disponibili"] = data["variabili_disponibili"]
        if "codice" in update_fields and update_fields["codice"]:
            update_fields["codice"] = update_fields["codice"].upper()

        # ⛔ Un PATCH senza campi e' un 400, non un 200 che non scrive (Tid,
        #    2026-10-20, brief-be-verifica-documentazione-api §A2).
        _V_EMAIL.require_campi_da_aggiornare(update_fields)
        repo.update_template(template_id, **update_fields)
        return success_response(repo.get_template(template_id) or {})

    @extend_schema(responses={204: None})
    # Scopo: Elimina un template email.
    def delete(self, request: Request, template_id: int) -> JsonResponse:
        repo = EmailRepository()
        # La lettura prima della cancellazione da' il 404 dalla sede unica.
        _template_o_404(repo, template_id)
        repo.delete_template(template_id)
        return JsonResponse({}, status=204)


class EmailTemplatePreviewView(AdminAPIView):
    """POST: preview template renderizzato con variabili di esempio.

    Il `corpo_html` viene sanificato lato BE con whitelist tag/attr/protocol
    (vedi `html_sanitizer_service.sanitize_email_html`). Il FE puo'
    quindi rendere il payload come "trusted preview" dentro un iframe
    sandbox (defense-in-depth — Fase 6 amm-software).
    """

    # Una LETTURA che viaggia in POST: permesso di lettura e niente
    # `Idempotency-Key` (brief-be-verifica-documentazione-api §A5).
    post_accesso = "view"

    @extend_schema(request=_PREVIEW_REQUEST, responses={200: dict})
    # Scopo: Renderizza un template con variabili di esempio e sanifica
    #        l'HTML risultante prima di restituirlo al client.
    def post(self, request: Request, template_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            variabili = payload.get("variabili") or {}
            repo = EmailRepository()
            template = _template_o_404(repo, template_id)

            service = EmailDispatchService()
            rendered_html = service.render_template(template["corpo_html"], variabili)
            return {
                "oggetto": service.render_template(template["oggetto"], variabili),
                "corpo_html": sanitize_email_html(rendered_html),
                "corpo_testo": service.render_template(template["corpo_testo"], variabili)
                if template.get("corpo_testo") else None,
            }

        return handle_post_json(request, handler=_handler)


# -------------------------------------------------------
# Log Email — Consultazione
# -------------------------------------------------------


class EmailLogListView(AdminAPIView):
    """GET: lista log email con filtri (admin vede tutto)."""

    is_search_endpoint = True

    @extend_schema(
        parameters=[
            param_ricerca_full(),
            OpenApiParameter(name="stato", type=str, required=False),
            OpenApiParameter(name="ambito", type=str, required=False),
            OpenApiParameter(name="pratica_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False, description="Data inizio (YYYY-MM-DD)"),
            OpenApiParameter(name="data_a", type=str, required=False, description="Data fine (YYYY-MM-DD)"),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
            OpenApiParameter(name="order_by", type=str, required=False),
            OpenApiParameter(name="order_dir", type=str, required=False),
        ],
        responses={200: dict},
    )
    # Scopo: Lista paginata log email con filtri e ordinamento. Admin vede
    #        tutti gli ambiti.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        p = parse_list_params(
            qp, default_order="data_insert",
            default_limit=DEFAULT_LIMIT, max_limit=MAX_LIMIT,
        )
        repo = EmailRepository()
        results, total = repo.list_logs(
            search=p["search"],
            stato=qp.get("stato") or None,
            ambito=qp.get("ambito") or None,
            unita_organizzativa_id=optional_int({"v": qp.get("unita_organizzativa_id")}, "v"),
            pratica_id=optional_int({"v": qp.get("pratica_id")}, "v"),
            data_da=qp_iso_date_optional(qp.get("data_da"), "data_da"),
            data_a=qp_iso_date_optional(qp.get("data_a"), "data_a"),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            # Assente = `None`: il default DESC dei log (il piu' recente in
            # testa) lo applica `EmailRepository.list_logs`, in una sede sola.
            order_dir=p["order_dir"],
        )
        return success_response(paginated_envelope(results, total, p["page"], p["limit"]))


class EmailLogDetailView(AdminAPIView):
    """GET: dettaglio singolo log email con corpo inviato."""

    @extend_schema(responses={200: dict})
    # Scopo: Dettaglio email inviata con corpo esatto e metadati.
    def get(self, request: Request, log_id: int) -> JsonResponse:
        repo = EmailRepository()
        # Fuori perimetro RLS e inesistente: lo stesso 404.
        return success_response(o_not_found(
            repo.get_log(log_id),
            code=E_EMAIL_LOG_NOT_FOUND,
            message=USER_MESSAGE_FALLBACK[E_EMAIL_LOG_NOT_FOUND],
            detail=f"email_log_id={log_id}",
        ))
