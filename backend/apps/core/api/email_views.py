# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API email per operatori: outbox (bozze), allegati, log.
#        Visibilita' basata su ambito e reparto dell'operatore.
# ------------------------------------------------------------

from __future__ import annotations

import os
from typing import Any

from django.http import FileResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.payload_validators import optional_int
from apps.core.api.success_responses import success_response
from apps.core.db.email_repository import EmailRepository
from apps.core.services.email_outbox_service import EmailOutboxService, _get_attachments_root
from apps.core.services.error_manager import ErrorManager

from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT

E_EMAIL_OP = "E_EMAIL_OP"


# Scopo: Verifica che l'operatore possa accedere a una bozza outbox.
#        Superuser bypassa. Altrimenti: l'operatore deve essere il creatore.
# Scopo: Verifica che l'operatore possa accedere a un allegato.
#        Risale all'outbox padre e applica ownership check.
#        Se nessun outbox padre trovato, nega l'accesso (fail-closed).
def _check_allegato_access(request: Request, repo: EmailRepository, allegato: dict[str, Any]) -> None:
    if request.user.is_superuser:
        return
    outbox_id = allegato.get("email_outbox_id")
    if outbox_id:
        outbox = repo.get_outbox(outbox_id)
        if outbox:
            _check_outbox_access(request, outbox)
            return
    # Nessun outbox padre: nega accesso per sicurezza (fail-closed)
    ErrorManager.require(False, code=E_EMAIL_OP, message="Non hai accesso a questo allegato.")


def _check_outbox_access(request: Request, outbox: dict[str, Any]) -> None:
    if request.user.is_superuser:
        return
    ErrorManager.require(
        outbox.get("creato_da_user_id") == request.user.id,
        code=E_EMAIL_OP,
        message="Non hai accesso a questa bozza.",
    )


class EmailPrepareView(DomainAPIView):
    """POST: prepara bozza email da template + variabili."""

    area_funzionale = "config"
    skip_area_check = True

    @extend_schema(responses={200: dict})
    # Scopo: Prepara una bozza email renderizzando un template con variabili.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            codice_template = (payload.get("codice_template") or "").strip()
            ErrorManager.require(bool(codice_template), code=E_EMAIL_OP, message="codice_template obbligatorio.")

            destinatario = (payload.get("destinatario") or "").strip()
            ErrorManager.require(bool(destinatario), code=E_EMAIL_OP, message="destinatario obbligatorio.")

            service = EmailOutboxService()
            return service.prepare_draft(
                codice_template=codice_template,
                destinatario=destinatario,
                variabili=payload.get("variabili") or {},
                unita_organizzativa_id=optional_int(payload, "unita_organizzativa_id"),
                tipo_prestazione_id=optional_int(payload, "tipo_prestazione_id"),
                lingua=(payload.get("lingua") or "it").strip(),
                ambito=(payload.get("ambito") or "SISTEMA").strip(),
                pratica_id=optional_int(payload, "pratica_id"),
                auth_user_id=optional_int(payload, "auth_user_id"),
                creato_da_user_id=request.user.id,
                destinatari_cc=payload.get("destinatari_cc"),
            )

        return handle_post_json(request, handler=_handler)


class EmailOutboxListView(DomainAPIView):
    """GET: lista bozze email visibili all'operatore."""

    area_funzionale = "config"
    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="stato", type=str, required=False),
            OpenApiParameter(name="pratica_id", type=int, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
        ],
        responses={200: dict},
    )
    # Scopo: Lista bozze email con visibilita' per ambito/reparto.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        repo = EmailRepository()

        # L'operatore vede le proprie bozze; la logica di visibilita'
        # per ambito/reparto sara' raffinata quando il profilo utente
        # includera' l'unita_organizzativa_id
        results, total = repo.list_outbox(
            creato_da_user_id=request.user.id if not request.user.is_superuser else None,
            stato=qp.get("stato") or None,
            pratica_id=optional_int({"v": qp.get("pratica_id")}, "v"),
            limit=min(optional_int({"v": qp.get("limit")}, "v") or DEFAULT_LIMIT, MAX_LIMIT),
            offset=optional_int({"v": qp.get("offset")}, "v") or 0,
        )
        return success_response({"count": total, "results": results})


class EmailOutboxDetailView(DomainAPIView):
    """GET: dettaglio bozza. PATCH: modifica bozza."""

    area_funzionale = "config"
    skip_area_check = True

    @extend_schema(responses={200: dict})
    # Scopo: Dettaglio bozza email con allegati. Verifica proprieta'.
    def get(self, request: Request, outbox_id: int) -> JsonResponse:
        repo = EmailRepository()
        result = repo.get_outbox(outbox_id)
        ErrorManager.require(result is not None, code=E_EMAIL_OP, message="Bozza non trovata.")
        assert result is not None
        _check_outbox_access(request, result)
        return success_response(result)

    @extend_schema(responses={200: dict})
    # Scopo: Modifica oggetto, corpo, CC di una bozza DRAFT. Verifica proprieta'.
    def patch(self, request: Request, outbox_id: int) -> JsonResponse:
        repo = EmailRepository()
        outbox = repo.get_outbox(outbox_id)
        ErrorManager.require(outbox is not None, code=E_EMAIL_OP, message="Bozza non trovata.")
        assert outbox is not None
        _check_outbox_access(request, outbox)

        data = request.data
        service = EmailOutboxService()
        result = service.update_draft(outbox_id, **{
            k: data[k] for k in ("oggetto", "corpo_html", "corpo_testo", "destinatari_cc", "destinatario")
            if k in data
        })
        return success_response(result)


class EmailOutboxSendView(DomainAPIView):
    """POST: conferma e invia una bozza DRAFT."""

    area_funzionale = "config"
    skip_area_check = True

    @extend_schema(responses={200: dict})
    # Scopo: Conferma e invia una bozza email (DRAFT -> SENT). Verifica proprieta'.
    def post(self, request: Request, outbox_id: int) -> JsonResponse:
        repo = EmailRepository()
        outbox = repo.get_outbox(outbox_id)
        ErrorManager.require(outbox is not None, code=E_EMAIL_OP, message="Bozza non trovata.")
        assert outbox is not None
        _check_outbox_access(request, outbox)

        service = EmailOutboxService()
        result = service.confirm_and_send(outbox_id)
        return success_response(result)


class EmailOutboxCancelView(DomainAPIView):
    """POST: annulla una bozza DRAFT."""

    area_funzionale = "config"
    skip_area_check = True

    @extend_schema(responses={200: dict})
    # Scopo: Annulla una bozza email (DRAFT -> CANCELLED). Verifica proprieta'.
    def post(self, request: Request, outbox_id: int) -> JsonResponse:
        repo = EmailRepository()
        outbox = repo.get_outbox(outbox_id)
        ErrorManager.require(outbox is not None, code=E_EMAIL_OP, message="Bozza non trovata.")
        assert outbox is not None
        _check_outbox_access(request, outbox)

        service = EmailOutboxService()
        result = service.cancel_draft(outbox_id)
        return success_response(result)


# -------------------------------------------------------
# Allegati
# -------------------------------------------------------


class EmailAllegatoUploadView(DomainAPIView):
    """POST: upload allegato per una bozza outbox (multipart)."""

    area_funzionale = "config"
    skip_area_check = True
    parser_classes = [MultiPartParser]

    @extend_schema(responses={200: dict})
    # Scopo: Upload file allegato a una bozza DRAFT. Verifica proprieta'.
    def post(self, request: Request, outbox_id: int) -> JsonResponse:
        repo = EmailRepository()
        outbox = repo.get_outbox(outbox_id)
        ErrorManager.require(outbox is not None, code=E_EMAIL_OP, message="Bozza non trovata.")
        assert outbox is not None
        _check_outbox_access(request, outbox)

        uploaded = request.FILES.get("file")
        ErrorManager.require(uploaded is not None, code=E_EMAIL_OP, message="File non fornito.")
        assert uploaded is not None

        service = EmailOutboxService()
        result = service.add_attachment(
            outbox_id=outbox_id,
            file_name=uploaded.name or "allegato",
            file_content=uploaded.read(),
            mime_type=uploaded.content_type or "application/octet-stream",
        )
        return success_response(result)


class EmailAllegatoListView(DomainAPIView):
    """GET: lista allegati di una bozza outbox."""

    area_funzionale = "config"
    skip_area_check = True

    @extend_schema(responses={200: dict})
    # Scopo: Lista allegati di una bozza outbox. Verifica proprieta'.
    def get(self, request: Request, outbox_id: int) -> JsonResponse:
        repo = EmailRepository()
        outbox = repo.get_outbox(outbox_id)
        ErrorManager.require(outbox is not None, code=E_EMAIL_OP, message="Bozza non trovata.")
        assert outbox is not None
        _check_outbox_access(request, outbox)
        return success_response({"results": outbox.get("allegati", [])})


class EmailAllegatoDeleteView(DomainAPIView):
    """DELETE: rimuove un allegato (file + record DB)."""

    area_funzionale = "config"
    skip_area_check = True

    @extend_schema(responses={204: None})
    # Scopo: Elimina un allegato da una bozza. Verifica proprieta' outbox.
    def delete(self, request: Request, allegato_id: int) -> JsonResponse:
        repo = EmailRepository()
        allegato = repo.get_allegato(allegato_id)
        ErrorManager.require(allegato is not None, code=E_EMAIL_OP, message="Allegato non trovato.")
        assert allegato is not None
        _check_allegato_access(request, repo, allegato)

        service = EmailOutboxService()
        service.remove_attachment(allegato_id)
        return JsonResponse({}, status=204)


class EmailAllegatoDownloadView(DomainAPIView):
    """GET: download file allegato."""

    area_funzionale = "config"
    skip_area_check = True

    @extend_schema(responses={200: bytes})
    # Scopo: Download file allegato per ID. Verifica proprieta' outbox.
    def get(self, request: Request, allegato_id: int) -> FileResponse:
        repo = EmailRepository()
        allegato = repo.get_allegato(allegato_id)
        ErrorManager.require(allegato is not None, code=E_EMAIL_OP, message="Allegato non trovato.")
        assert allegato is not None
        _check_allegato_access(request, repo, allegato)

        rel_path = allegato["file_path"]
        root = _get_attachments_root()
        abs_path = os.path.normpath(os.path.join(root, rel_path))
        # Guard: previeni path traversal — il path risolto deve restare dentro root
        ErrorManager.require(
            abs_path.startswith(os.path.normpath(root)),
            code=E_EMAIL_OP, message="Path allegato non valido.",
        )
        ErrorManager.require(os.path.exists(abs_path), code=E_EMAIL_OP, message="File non trovato su storage.")

        return FileResponse(
            open(abs_path, "rb"),  # noqa: SIM115
            content_type=allegato["mime_type"],
            as_attachment=True,
            filename=allegato["nome_file"],
        )


# -------------------------------------------------------
# Log Email — Consultazione operatore (con visibilita')
# -------------------------------------------------------


class EmailLogOperatoreListView(DomainAPIView):
    """GET: log email visibili all'operatore (per ambito/reparto)."""

    area_funzionale = "config"
    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, required=False),
            OpenApiParameter(name="stato", type=str, required=False),
            OpenApiParameter(name="pratica_id", type=int, required=False),
            OpenApiParameter(name="limit", type=int, required=False),
            OpenApiParameter(name="offset", type=int, required=False),
        ],
        responses={200: dict},
    )
    # Scopo: Lista log email con filtro visibilita' per operatore.
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        repo = EmailRepository()
        results, total = repo.list_logs(
            search=qp.get("search") or None,
            stato=qp.get("stato") or None,
            pratica_id=optional_int({"v": qp.get("pratica_id")}, "v"),
            limit=min(optional_int({"v": qp.get("limit")}, "v") or DEFAULT_LIMIT, MAX_LIMIT),
            offset=optional_int({"v": qp.get("offset")}, "v") or 0,
        )
        return success_response({"count": total, "results": results})
