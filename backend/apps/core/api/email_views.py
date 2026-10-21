# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: API email per operatori: outbox (bozze), allegati, log.
#        Visibilita' basata su ambito e reparto dell'operatore.
# Note: ⭐ CHI VEDE QUALE MAIL LO DECIDE IL DATABASE, non queste view: le policy
#       RLS di `config.email_log`, `config.email_outbox` e
#       `config.email_allegato` passano tutte da `script.fn_scope_email_ambito`
#       (SISTEMA: super admin; REPARTO: stesso reparto; OPERATORE: l'autore;
#       sempre in AND con l'emittente nel perimetro), in lettura e in scrittura.
#       Una bozza o un allegato fuori perimetro qui arriva come «non trovato».
#       ⛔ Fino al 2026-09-25 le view tenevano una seconda sede della regola
#       (un controllo di proprieta' sulla bozza e il filtro
#       `creato_da_user_id` della lista bozze): tolta con
#       brief-db-email-visibilita-per-ambito §6.4.3 — e sbagliava, perche'
#       negava ai colleghi le bozze di REPARTO.
#       ⭐ ECCEZIONE, dal 2026-09-26 (Tid): la LISTA DEL LOG
#       (`EmailLogOperatoreListView`, sola lettura) ha `skip_area_check` e la
#       apre ogni operatore — le proprie mail e quelle del proprio reparto, per
#       la RLS. Un livello d'area sopra sarebbe una seconda regola accanto a
#       quella del modello. Brief: brief-db-email-visibilita-per-ambito §9.6.
#       ⛔ Tutte le ALTRE view stanno sotto l'area `config` — LETTURA per leggere,
#       TUTTO per preparare, modificare e SPEDIRE — per decisione di Tid
#       (2026-09-12). Fino a quel giorno dichiaravano anche
#       `skip_area_check = True`, che era MUTO (la catena legge lo skip solo se
#       l'area non si risolve): il comportamento e' lo stesso, il codice adesso
#       lo dice. ⚠️ Non e' un'API «per tutti gli operatori»: sei di queste
#       scrivono senza `post_permission`, e con lo skip attivo qualunque
#       identita' autenticata potrebbe spedire dall'account aziendale. Se un
#       giorno dovra' aprirsi oltre `config`, prima un'azione di processo a
#       catalogo (`invia_email`) e la schermata (D7), poi lo skip — mai il
#       contrario. Presidiato da `core/tests/test_skip_area_check_registro.py`.
# ------------------------------------------------------------

from __future__ import annotations

import os
from typing import Any

from django.http import FileResponse, JsonResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request

from apps.core.api.base_views import DomainAPIView
from apps.core.api.endpoint_helpers import handle_post_json
from apps.core.api.openapi_params import param_ricerca_full
from apps.core.api.payload_validators import (
    corpo_oggetto,
    optional_int,
    pagina_da_query,
    parse_list_params,
    qp_int_optional,
    qp_iso_date_optional,
)
from apps.core.api.success_responses import success_response
from apps.core.db.email_repository import EmailRepository
from apps.core.services.email_allegati_storage import E_EMAIL_OP, percorso_allegato
from apps.core.services.email_outbox_service import DRAFT_EDITABILI, EmailOutboxService
from apps.core.api.schema_da_contratto import schema_da_contratto
from apps.core.api.schema_email import TIPI_EMAIL
from apps.core.services.email_constants import AMBITI_EMAIL, elenco_stati_email_log
from apps.core.services.auth_helpers import (
    extract_emittente_attivo_from_request,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.error_messages_fallback import USER_MESSAGE_FALLBACK
from apps.core.services.testata_guard import o_not_found

from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT

# Codici dei «non trovato» degli allegati e del file perso sullo storage
# (brief-db-codici-non-trovato-email-e-permessi §2): `E_EMAIL_OP` resta per i
# soli dati errati della richiesta.
E_EMAIL_ALLEGATO_NOT_FOUND = "E_EMAIL_ALLEGATO_NOT_FOUND"
E_EMAIL_ALLEGATO_FILE_MANCANTE = "E_EMAIL_ALLEGATO_FILE_MANCANTE"
E_EMITTENTE_NON_RISOLTO = "E_EMITTENTE_NON_RISOLTO"


# ⭐ Il vocabolario vive in `services/email_constants.py`, non qui: lo usa anche
#    il repository, e un repository che importa una view per sapere una regola di
#    dominio ha il livello sbagliato. Qui si ri-esporta col nome storico, cosi'
#    chi lo importava da questo modulo non si accorge dello spostamento.
AMBITI_OUTBOX = AMBITI_EMAIL

# ── Schemi OpenAPI dei corpi ──────────────────────────────────────────────
# La bozza da template: le chiavi che `EmailPrepareView` legge. L'ambito ha il
# suo dominio da `AMBITI_OUTBOX` (la stessa costante che il gestore controlla).
_PREPARE_REQUEST = inline_serializer(
    name="CoreEmailPrepareReq",
    fields={
        "codice_template": serializers.CharField(),
        "destinatario": serializers.CharField(),
        "ambito": serializers.ChoiceField(choices=sorted(AMBITI_OUTBOX)),
        "unita_organizzativa_id": serializers.IntegerField(
            required=False, allow_null=True,
            help_text="Obbligatoria con ambito REPARTO.",
        ),
        "lingua": serializers.CharField(required=False, allow_null=True),
        "variabili": serializers.DictField(required=False, allow_null=True),
        "destinatari_cc": serializers.ListField(
            child=serializers.CharField(), required=False, allow_null=True,
        ),
    },
)
# La modifica di una bozza: le chiavi dal contratto del service.
_BOZZA_PATCH_REQUEST = schema_da_contratto(
    "CoreEmailBozzaPatchReq", DRAFT_EDITABILI, tipi=TIPI_EMAIL,
)
# Un allegato alla bozza: multipart, campo `file`.
_ALLEGATO_UPLOAD_REQUEST = inline_serializer(
    name="CoreEmailAllegatoUploadReq",
    fields={"file": serializers.FileField()},
)



class EmailPrepareView(DomainAPIView):
    """POST: prepara bozza email da template + variabili."""

    area_funzionale = "config"

    @extend_schema(request=_PREPARE_REQUEST, responses={200: dict})
    # Scopo: Prepara una bozza email renderizzando un template con variabili.
    #
    # ⛔ `ambito` E' OBBLIGATORIO, e dal 2026-09-05 non ha piu' un default.
    #    Valeva `SISTEMA` quando il client taceva — cioe' «nessuno ha detto
    #    l'ambito» e «email di sistema» erano lo stesso valore. Su quella
    #    colonna il database sta per montare una policy di lettura che tratta
    #    `SISTEMA` come segreto di sistema (reset password, alert): un valore di
    #    RIPIEGO non puo' fare da cancello di sicurezza, o basta un campo
    #    dimenticato per classificare come segreta una bozza qualunque.
    #    ⇒ Chi crea una bozza dichiara di che cosa e'. Brief:
    #    brief-db-processi-automatici-residui-be §1-octies, punto 1.
    def post(self, request: Request) -> JsonResponse:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            codice_template = (payload.get("codice_template") or "").strip()
            ErrorManager.require(bool(codice_template), code=E_EMAIL_OP, message="codice_template obbligatorio.")

            destinatario = (payload.get("destinatario") or "").strip()
            ErrorManager.require(bool(destinatario), code=E_EMAIL_OP, message="destinatario obbligatorio.")

            ambito = (payload.get("ambito") or "").strip().upper()
            ErrorManager.require(
                ambito in AMBITI_OUTBOX,
                code=E_EMAIL_OP,
                message=(
                    "Indicare l'ambito della bozza: "
                    f"{', '.join(AMBITI_OUTBOX)}."
                ),
                context={"field": "ambito"},
            )

            # ⭐ L'emittente della bozza e' quello ATTIVO di chi la crea, letto
            #    dal claim del token — la stessa fonte che la RLS usa per
            #    filtrare. ⛔ Non si deduce dal template ne' dall'unita'
            #    organizzativa: sarebbe una seconda regola di perimetro accanto
            #    a quella vera.
            # ⚠️ Per `SISTEMA` resta `None`: quelle righe non appartengono a
            #    nessuna azienda, e il CHECK del database lo pretende
            #    (`chk_email_outbox_ambito_emittente`). Sugli altri ambiti
            #    l'emittente c'e' per forza — se manca, si ferma qui con una
            #    frase, invece di sbattere sul vincolo.
            emittente_fiscale_id = (
                None if ambito == "SISTEMA"
                else extract_emittente_attivo_from_request(request)
            )
            # ⭐ E' la condizione di `E_EMITTENTE_NON_RISOLTO` (la modalita'
            #    «Tutti gli emittenti», di sola lettura): un codice solo per
            #    tutte le tabelle che vogliono l'azienda di chi agisce, col suo
            #    400 voluto — il rimedio e' scegliere l'azienda in alto
            #    (brief-db-codici-non-trovato-email-e-permessi §9.2). Fino al
            #    2026-10-09 usciva come `E_EMAIL_OP`.
            ErrorManager.require(
                ambito == "SISTEMA" or emittente_fiscale_id is not None,
                code=E_EMITTENTE_NON_RISOLTO,
                message=USER_MESSAGE_FALLBACK[E_EMITTENTE_NON_RISOLTO],
                detail=f"ambito={ambito}",
            )

            # ⛔ `REPARTO` senza unita' organizzativa lo rifiuta il database
            #    (`chk_email_outbox_reparto_uo`). Prima non capitava — nessuno
            #    mandava `REPARTO`, perche' il default copriva tutto; da quando
            #    l'ambito si dichiara, quel ramo e' raggiungibile e va chiuso
            #    QUI, con una frase, invece di far arrivare l'operatore a una
            #    violazione di vincolo.
            unita_organizzativa_id = optional_int(payload, "unita_organizzativa_id")
            ErrorManager.require(
                ambito != "REPARTO" or unita_organizzativa_id is not None,
                code=E_EMAIL_OP,
                message="Una bozza di reparto deve indicare l'unita' organizzativa.",
                context={"field": "unita_organizzativa_id"},
            )

            service = EmailOutboxService()
            return service.prepare_draft(
                codice_template=codice_template,
                destinatario=destinatario,
                variabili=payload.get("variabili") or {},
                unita_organizzativa_id=unita_organizzativa_id,
                tipo_prestazione_id=optional_int(payload, "tipo_prestazione_id"),
                lingua=(payload.get("lingua") or "it").strip(),
                ambito=ambito,
                emittente_fiscale_id=emittente_fiscale_id,
                pratica_id=optional_int(payload, "pratica_id"),
                auth_user_id=optional_int(payload, "auth_user_id"),
                creato_da_user_id=request.user.id,
                destinatari_cc=payload.get("destinatari_cc"),
            )

        return handle_post_json(request, handler=_handler)


class EmailOutboxListView(DomainAPIView):
    """GET: lista bozze email visibili all'operatore."""

    area_funzionale = "config"
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
    # ⛔ Nessun filtro di perimetro qui: la visibilita' per ambito/reparto la
    #    applica la RLS (vedi testa del file).
    def get(self, request: Request) -> JsonResponse:
        qp = request.query_params
        limit, offset = pagina_da_query(qp)
        repo = EmailRepository()

        results, total = repo.list_outbox(
            stato=qp.get("stato") or None,
            pratica_id=qp_int_optional(qp.get("pratica_id"), "pratica_id", min_val=1),
            limit=limit,
            offset=offset,
        )
        return success_response({"count": total, "results": results})


class EmailOutboxDetailView(DomainAPIView):
    """GET: dettaglio bozza. PATCH: modifica bozza."""

    area_funzionale = "config"

    @extend_schema(responses={200: dict})
    # Scopo: Dettaglio bozza email con allegati.
    def get(self, request: Request, outbox_id: int) -> JsonResponse:
        return success_response(EmailOutboxService().get_bozza(outbox_id))

    @extend_schema(request=_BOZZA_PATCH_REQUEST, responses={200: dict})
    # Scopo: Modifica oggetto, corpo, CC di una bozza DRAFT.
    def patch(self, request: Request, outbox_id: int) -> JsonResponse:
        # ⛔ La bozza la legge (e la rifiuta, 404) il verbo del service: la
        #    view non la rilegge prima — sarebbe un secondo controllo uguale.
        # ⛔ Il payload passa INTERO: le chiavi estranee le rifiuta il service
        #    con un 400 (2026-09-26). Fino a quel giorno la view le filtrava qui
        #    e un campo sbagliato «riusciva» senza essere scritto.
        service = EmailOutboxService()
        result = service.update_draft(outbox_id, **dict(corpo_oggetto(request)))
        return success_response(result)


class EmailOutboxSendView(DomainAPIView):
    """POST: conferma e invia una bozza DRAFT."""

    area_funzionale = "config"

    @extend_schema(request=None, responses={200: dict})
    # Scopo: Conferma e invia una bozza email (DRAFT -> SENT).
    def post(self, request: Request, outbox_id: int) -> JsonResponse:
        service = EmailOutboxService()
        result = service.confirm_and_send(outbox_id)
        return success_response(result)


class EmailOutboxCancelView(DomainAPIView):
    """POST: annulla una bozza DRAFT."""

    area_funzionale = "config"

    @extend_schema(request=None, responses={200: dict})
    # Scopo: Annulla una bozza email (DRAFT -> CANCELLED).
    def post(self, request: Request, outbox_id: int) -> JsonResponse:
        service = EmailOutboxService()
        result = service.cancel_draft(outbox_id)
        return success_response(result)


# -------------------------------------------------------
# Allegati
# -------------------------------------------------------


class EmailAllegatoUploadView(DomainAPIView):
    """POST: upload allegato per una bozza outbox (multipart)."""

    area_funzionale = "config"
    parser_classes = [MultiPartParser]

    @extend_schema(request={"multipart/form-data": _ALLEGATO_UPLOAD_REQUEST}, responses={200: dict})
    # Scopo: Upload file allegato a una bozza DRAFT.
    def post(self, request: Request, outbox_id: int) -> JsonResponse:
        # ⛔ La bozza la legge (e la rifiuta, 404) `add_attachment`: la view
        #    non la rilegge prima.
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

    @extend_schema(responses={200: dict})
    # Scopo: Lista allegati di una bozza outbox.
    def get(self, request: Request, outbox_id: int) -> JsonResponse:
        outbox = EmailOutboxService().get_bozza(outbox_id)
        return success_response({"results": outbox.get("allegati", [])})


# Scopo: L'allegato per id, o 404 `E_EMAIL_ALLEGATO_NOT_FOUND` (inesistente o
#        fuori perimetro RLS: la stessa risposta). Sede unica per rimozione e
#        download (regola del 2, 2026-10-09).
def _allegato_o_404(allegato_id: int) -> dict[str, Any]:
    return o_not_found(
        EmailRepository().get_allegato(allegato_id),
        code=E_EMAIL_ALLEGATO_NOT_FOUND,
        message=USER_MESSAGE_FALLBACK[E_EMAIL_ALLEGATO_NOT_FOUND],
        detail=f"email_allegato_id={allegato_id}",
    )


class EmailAllegatoDeleteView(DomainAPIView):
    """DELETE: rimuove un allegato (file + record DB)."""

    area_funzionale = "config"

    @extend_schema(responses={204: None})
    # Scopo: Elimina un allegato da una bozza.
    def delete(self, request: Request, allegato_id: int) -> JsonResponse:
        _allegato_o_404(allegato_id)

        service = EmailOutboxService()
        service.remove_attachment(allegato_id)
        return JsonResponse({}, status=204)


class EmailAllegatoDownloadView(DomainAPIView):
    """GET: download file allegato."""

    area_funzionale = "config"

    @extend_schema(responses={200: bytes})
    # Scopo: Download file allegato per ID.
    def get(self, request: Request, allegato_id: int) -> FileResponse:
        allegato = _allegato_o_404(allegato_id)

        # Guard contro il path traversal nel BB condiviso con l'invio SMTP.
        abs_path = percorso_allegato(allegato["file_path"])
        # ⚠️ 500, non 404: la riga c'e' e il file no — un guasto dello
        #    storage, su cui l'operatore non puo' fare niente (brief §2).
        ErrorManager.require(
            os.path.exists(abs_path),
            code=E_EMAIL_ALLEGATO_FILE_MANCANTE,
            message=USER_MESSAGE_FALLBACK[E_EMAIL_ALLEGATO_FILE_MANCANTE],
            detail=f"email_allegato_id={allegato_id}",
        )

        return FileResponse(
            open(abs_path, "rb"),
            content_type=allegato["mime_type"],
            as_attachment=True,
            filename=allegato["nome_file"],
        )


# -------------------------------------------------------
# Log Email — Consultazione operatore (con visibilita')
# -------------------------------------------------------


# ⛔ LO SCOPE NON STA QUI, E NON VA AGGIUNTO: lo tiene la RLS su
#    `config.email_log` — `rls_email_log_ambito` → `script.fn_scope_email_ambito`
#    (dal 2026-09-25: SISTEMA al super admin, REPARTO al reparto, OPERATORE
#    all'autore, sempre in AND con l'emittente; piu' il processo
#    `send_pending_emails`, che deve poter ritentare). Un filtro applicativo
#    qui sarebbe una SECONDA SEDE della stessa regola.
# ⚠️ Fino al 2026-09-11 il docstring diceva «per ambito/reparto», e i due
#    parametri che il repository espone per quello (`ambito`,
#    `unita_organizzativa_id`) non sono mai stati passati: la frase prometteva
#    un filtro che non c'era (piano-be-fe-endpoint-senza-porta §1.1). Dal
#    2026-09-25 l'ambito e il reparto li applica la policy
#    (brief-db-email-visibilita-per-ambito): la promessa e' vera, e la sede e'
#    il database.
# ⚠️ Il docstring resta UNA RIGA di proposito: drf-spectacular lo pubblica come
#    descrizione dell'operazione nello schema OpenAPI, e le note di
#    implementazione non appartengono a un contratto pubblico.
# ⭐ `skip_area_check` e NESSUNA `area_funzionale` (i due insieme non
#    convivono: lo skip sarebbe muto). E' una sola lettura, trasversale ai
#    domini come il profilo o i lookup: le mail nascono da pratiche, vendite,
#    inviti. Chi vede quale riga lo decide la RLS (sopra), non un'area.
# ⛔ Non vale per le bozze: spedire resta sotto `config` finche' non esiste
#    l'azione di processo `invia_email` (testa del file).
class EmailLogOperatoreListView(DomainAPIView):
    """GET: log email inviate, nel perimetro dell'operatore."""

    skip_area_check = True
    is_search_endpoint = True

    @extend_schema(
        parameters=[
            # Stessa query della lista `config.email_log` (`list_logs`): le
            # colonne e la soglia sono quelle della sua dichiarazione nel
            # repository, lette dal catalogo della lista.
            param_ricerca_full(),
            OpenApiParameter(name="stato", type=str, required=False),
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
    # Scopo: Lista log email nel perimetro dell'operatore (lo tiene la RLS).
    # ⛔ Fino al 2026-09-26 non leggeva `order_by`/`order_dir`: la lista
    #    configurabile manda l'ordinamento della colonna cliccata, e qui veniva
    #    ignorato in silenzio. Stessa lettura della gemella admin
    #    (`amm_software/api/email_views.EmailLogListView`), stesso default DESC.
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
            pratica_id=optional_int({"v": qp.get("pratica_id")}, "v"),
            data_da=qp_iso_date_optional(qp.get("data_da"), "data_da"),
            data_a=qp_iso_date_optional(qp.get("data_a"), "data_a"),
            limit=p["limit"],
            offset=p["offset"],
            order_by=p["order_by"],
            # Assente = `None`: il default DESC dei log (il piu' recente in
            # cima) lo applica `EmailRepository.list_logs`, in una sede sola.
            order_dir=p["order_dir"],
        )
        return success_response({"count": total, "results": results})


# ⭐ Il vocabolario del filtro «stato» della lista qui sopra: stessa porta
#    (skip d'area, sola lettura), perche' chi puo' aprire la lista deve poter
#    filtrare. Fino al 2026-09-26 stava in `/amm-software/lookup/email-log-stati/`
#    (`AdminAPIView`): per un operatore sarebbe stato un 403 dentro una
#    schermata aperta. Ritirato lo stesso giorno: una rotta, due schermate.
# ⭐ Envelope `{"results": [...]}` (api.md, «L'envelope di un lookup»): la
#    rotta admin rendeva la lista nuda e chi la consumava doveva ricordarsi un
#    transform.
class EmailLogStatiLookupView(DomainAPIView):
    """GET: gli stati possibili di una mail nel log, per il filtro della lista."""

    skip_area_check = True

    @extend_schema(responses={200: dict})
    # Scopo: Restituisce gli stati del log con la loro descrizione, in ordine.
    def get(self, request: Request) -> JsonResponse:
        del request
        return success_response({"results": elenco_stati_email_log()})
