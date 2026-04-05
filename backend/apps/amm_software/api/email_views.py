# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API admin per gestione account email, template email e log email.
#        Tutti gli endpoint richiedono ruolo ADMIN.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request

from apps.core.api.base_views import AdminAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_int
from apps.core.api.success_responses import success_response
from apps.core.db.email_repository import EmailRepository
from apps.core.services.email_service import EmailDispatchService
from apps.core.services.error_manager import ErrorManager

from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT

E_EMAIL_ADMIN = "E_EMAIL_ADMIN"


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
    # Scopo: Dettaglio singolo account email per ID.
    def get(self, request: Request, account_id: int) -> JsonResponse:
        repo = EmailRepository()
        result = repo.get_account(account_id)
        ErrorManager.require(result is not None, code=E_EMAIL_ADMIN, message="Account non trovato.")
        return success_response(result or {})

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
        return success_response(repo.get_account(account_id) or {})

    @extend_schema(responses={204: None})
    # Scopo: Elimina un account email.
    def delete(self, request: Request, account_id: int) -> JsonResponse:
        repo = EmailRepository()
        deleted = repo.delete_account(account_id)
        ErrorManager.require(deleted, code=E_EMAIL_ADMIN, message="Account non trovato.")
        return JsonResponse({}, status=204)


class EmailAccountTestView(AdminAPIView):
    """POST: testa la connessione SMTP di un account."""

    @extend_schema(responses={200: dict})
    # Scopo: Verifica connessione SMTP senza inviare email.
    def post(self, request: Request, account_id: int) -> JsonResponse:
        service = EmailDispatchService()
        result = service.test_connection(account_id)
        return success_response(result)


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
    """POST: preview template renderizzato con variabili di esempio."""

    @extend_schema(responses={200: dict})
    # Scopo: Renderizza un template con variabili di esempio per anteprima.
    def post(self, request: Request, template_id: int) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            variabili = payload.get("variabili") or {}
            repo = EmailRepository()
            template = repo.get_template(template_id)
            ErrorManager.require(template is not None, code=E_EMAIL_ADMIN, message="Template non trovato.")
            assert template is not None

            service = EmailDispatchService()
            return {
                "oggetto": service.render_template(template["oggetto"], variabili),
                "corpo_html": service.render_template(template["corpo_html"], variabili),
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
