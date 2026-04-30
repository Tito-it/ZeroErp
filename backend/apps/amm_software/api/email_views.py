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
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request

from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_int
from apps.core.api.success_responses import success_response
from apps.core.db.email_repository import EmailRepository
from apps.core.services.email_service import SMTP_PLACEHOLDER_HOST, EmailDispatchService
from apps.core.services.error_manager import ErrorManager
from apps.core.services.html_sanitizer_service import sanitize_email_html

from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT

E_EMAIL_ADMIN = "E_EMAIL_ADMIN"


# Scopo: Deriva la capability di test connessione di un account email.
#        Restituisce (can_test, test_reason). `can_test=True` significa che
#        il pulsante test in UI puo' essere abilitato; `test_reason` e' una
#        chiave i18n (lato FE) usata come tooltip quando `can_test=False`.
#        Casi gestiti:
#          - account inattivo            → ("amm.email_test_reason_inactive")
#          - host vuoto/placeholder      → console mode, test sempre OK
#          - password SMTP non impostata → ("amm.email_test_reason_no_password")
def _derive_test_capability(account: dict[str, Any]) -> tuple[bool, str | None]:
    if not account.get("attivo"):
        return False, "amm.email_test_reason_inactive"
    smtp_host = (account.get("smtp_host") or "").strip()
    # In console mode (host vuoto o placeholder) non serve credenziale:
    # il test ritorna sempre successo, quindi e' sempre abilitabile.
    if not smtp_host or smtp_host == SMTP_PLACEHOLDER_HOST:
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
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
        ],
        responses={200: dict},
    )
    # Scopo: Lista paginata account email con filtro ricerca.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        repo = EmailRepository()
        results, total = repo.list_accounts(
            search=qp.get("search") or None,
            limit=min(optional_int({"v": qp.get("limit")}, "v") or DEFAULT_LIMIT, MAX_LIMIT),
            offset=optional_int({"v": qp.get("offset")}, "v") or 0,
        )
        return success_response({"count": total, "results": results})

    @extend_schema(responses={200: dict})
    # Scopo: Crea un nuovo account email SMTP.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
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
                smtp_use_tls=bool(payload.get("smtp_use_tls", True)),
                smtp_use_ssl=bool(payload.get("smtp_use_ssl", False)),
                smtp_username=(payload.get("smtp_username") or "").strip(),
                smtp_password=(payload.get("smtp_password") or ""),
                email_from=email_from,
                email_reply_to=(payload.get("email_reply_to") or "").strip() or None,
                unita_organizzativa_id=optional_int(payload, "unita_organizzativa_id"),
                attivo=bool(payload.get("attivo", True)),
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
        repo = EmailRepository()
        result = repo.get_account(account_id)
        ErrorManager.require(result is not None, code=E_EMAIL_ADMIN, message="Account non trovato.")
        assert result is not None
        return success_response(_enrich_account_with_capability(result))

    @extend_schema(responses={200: dict})
    # Scopo: Aggiorna parzialmente un account email.
    def patch(self, request: Request, account_id: int) -> JsonResponse:
        data = request.data
        repo = EmailRepository()
        ErrorManager.require(
            repo.get_account(account_id) is not None,
            code=E_EMAIL_ADMIN, message="Account non trovato.",
        )

        update_fields: dict[str, Any] = {}
        for field in ("codice", "descrizione", "smtp_host", "smtp_username",
                       "email_from", "email_reply_to"):
            if field in data:
                update_fields[field] = data[field].strip() if isinstance(data[field], str) else data[field]
        if "smtp_port" in data:
            update_fields["smtp_port"] = optional_int(data, "smtp_port")
        for field in ("smtp_use_tls", "smtp_use_ssl", "attivo"):
            if field in data:
                update_fields[field] = bool(data[field])
        if "unita_organizzativa_id" in data:
            update_fields["unita_organizzativa_id"] = optional_int(data, "unita_organizzativa_id")
        if "smtp_password" in data and data["smtp_password"]:
            update_fields["smtp_password"] = data["smtp_password"]
        if "codice" in update_fields and update_fields["codice"]:
            update_fields["codice"] = update_fields["codice"].upper()

        repo.update_account(account_id, **update_fields)
        result = repo.get_account(account_id)
        return success_response(_enrich_account_with_capability(result) if result else {})

    @extend_schema(responses={204: None})
    # Scopo: Elimina un account email.
    def delete(self, request: Request, account_id: int) -> JsonResponse:
        repo = EmailRepository()
        deleted = repo.delete_account(account_id)
        ErrorManager.require(deleted, code=E_EMAIL_ADMIN, message="Account non trovato.")
        return JsonResponse({}, status=204)


class EmailAccountTestView(AdminAPIView):
    """POST: testa la connessione SMTP di un account.

    Oltre al risultato del test (`success`/`message`), persiste in
    `email_account.meta` l'ultimo esito (`last_test_outcome`,
    `last_test_at`, `last_test_message`) e ritorna il payload arricchito
    con le stesse capability del detail (`can_test`, `test_reason`).
    Cosi' il FE puo' aggiornare in-place la riga senza una GET extra.
    """

    @extend_schema(responses={200: dict})
    # Scopo: Verifica connessione SMTP senza inviare email. Persiste l'esito
    #        in meta jsonb e ritorna risultato + capability aggiornate.
    def post(self, request: Request, account_id: int) -> JsonResponse:
        repo = EmailRepository()
        # Verifica esistenza prima del test SMTP per dare errore 4xx coerente.
        account = repo.get_account(account_id)
        ErrorManager.require(account is not None, code=E_EMAIL_ADMIN, message="Account non trovato.")
        assert account is not None

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
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="codice", type=str, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
        ],
        responses={200: dict},
    )
    # Scopo: Lista paginata template email con filtro per codice e ricerca.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        repo = EmailRepository()
        results, total = repo.list_templates(
            search=qp.get("search") or None,
            codice=qp.get("codice") or None,
            limit=min(optional_int({"v": qp.get("limit")}, "v") or DEFAULT_LIMIT, MAX_LIMIT),
            offset=optional_int({"v": qp.get("offset")}, "v") or 0,
        )
        return success_response({"count": total, "results": results})

    @extend_schema(responses={200: dict})
    # Scopo: Crea un nuovo template email.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
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
                attivo=bool(payload.get("attivo", True)),
            )
            return repo.get_template(template_id) or {}

        return handle_post_json(request, handler=_handler)


class EmailTemplateDetailView(AdminAPIView):
    """GET: dettaglio template. PATCH: modifica. DELETE: elimina."""

    @extend_schema(responses={200: dict})
    # Scopo: Dettaglio singolo template email per ID (incluso corpo).
    def get(self, request: Request, template_id: int) -> JsonResponse:
        repo = EmailRepository()
        result = repo.get_template(template_id)
        ErrorManager.require(result is not None, code=E_EMAIL_ADMIN, message="Template non trovato.")
        return success_response(result or {})

    @extend_schema(responses={200: dict})
    # Scopo: Aggiorna parzialmente un template email.
    def patch(self, request: Request, template_id: int) -> JsonResponse:
        data = request.data
        repo = EmailRepository()
        ErrorManager.require(
            repo.get_template(template_id) is not None,
            code=E_EMAIL_ADMIN, message="Template non trovato.",
        )

        update_fields: dict[str, Any] = {}
        for field in ("codice", "oggetto", "corpo_html", "corpo_testo", "lingua"):
            if field in data:
                val = (data[field] or "").strip() if data[field] else None
                update_fields[field] = val
        if "attivo" in data:
            update_fields["attivo"] = bool(data["attivo"])
        if "unita_organizzativa_id" in data:
            update_fields["unita_organizzativa_id"] = optional_int(data, "unita_organizzativa_id")
        if "tipo_prestazione_id" in data:
            update_fields["tipo_prestazione_id"] = optional_int(data, "tipo_prestazione_id")
        if "variabili_disponibili" in data:
            update_fields["variabili_disponibili"] = data["variabili_disponibili"]
        if "codice" in update_fields and update_fields["codice"]:
            update_fields["codice"] = update_fields["codice"].upper()

        repo.update_template(template_id, **update_fields)
        return success_response(repo.get_template(template_id) or {})

    @extend_schema(responses={204: None})
    # Scopo: Elimina un template email.
    def delete(self, request: Request, template_id: int) -> JsonResponse:
        repo = EmailRepository()
        deleted = repo.delete_template(template_id)
        ErrorManager.require(deleted, code=E_EMAIL_ADMIN, message="Template non trovato.")
        return JsonResponse({}, status=204)


class EmailTemplatePreviewView(AdminAPIView):
    """POST: preview template renderizzato con variabili di esempio.

    Il `corpo_html` viene sanificato lato BE con whitelist tag/attr/protocol
    (vedi `html_sanitizer_service.sanitize_email_html`). Il FE puo'
    quindi rendere il payload come "trusted preview" dentro un iframe
    sandbox (defense-in-depth — Fase 6 amm-software).
    """

    @extend_schema(responses={200: dict})
    # Scopo: Renderizza un template con variabili di esempio e sanifica
    #        l'HTML risultante prima di restituirlo al client.
    def post(self, request: Request, template_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            variabili = payload.get("variabili") or {}
            repo = EmailRepository()
            template = repo.get_template(template_id)
            ErrorManager.require(template is not None, code=E_EMAIL_ADMIN, message="Template non trovato.")
            assert template is not None

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
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="stato", type=str, required=False),
            OpenApiParameter(name="ambito", type=str, required=False),
            OpenApiParameter(name="pratica_id", type=int, required=False),
            OpenApiParameter(name="data_da", type=str, required=False, description="Data inizio (YYYY-MM-DD)"),
            OpenApiParameter(name="data_a", type=str, required=False, description="Data fine (YYYY-MM-DD)"),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
        ],
        responses={200: dict},
    )
    # Scopo: Lista paginata log email con filtri. Admin vede tutti gli ambiti.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        repo = EmailRepository()
        results, total = repo.list_logs(
            search=qp.get("search") or None,
            stato=qp.get("stato") or None,
            ambito=qp.get("ambito") or None,
            unita_organizzativa_id=optional_int({"v": qp.get("unita_organizzativa_id")}, "v"),
            pratica_id=optional_int({"v": qp.get("pratica_id")}, "v"),
            data_da=qp.get("data_da") or None,
            data_a=qp.get("data_a") or None,
            limit=min(optional_int({"v": qp.get("limit")}, "v") or DEFAULT_LIMIT, MAX_LIMIT),
            offset=optional_int({"v": qp.get("offset")}, "v") or 0,
        )
        return success_response({"count": total, "results": results})


class EmailLogDetailView(AdminAPIView):
    """GET: dettaglio singolo log email con corpo inviato."""

    @extend_schema(responses={200: dict})
    # Scopo: Dettaglio email inviata con corpo esatto e metadati.
    def get(self, request: Request, log_id: int) -> JsonResponse:
        repo = EmailRepository()
        result = repo.get_log(log_id)
        ErrorManager.require(result is not None, code=E_EMAIL_ADMIN, message="Log email non trovato.")
        return success_response(result or {})
