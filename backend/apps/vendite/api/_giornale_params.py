# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il CONTRATTO DI LISTA delle due Storie per entita' — il giornale di
#        una fattura (`fatture_views.ApiFatturaGiornale`) e quello di un lotto
#        (`views.ApiLottoGiornale`) — dichiarato una volta: parametri OpenAPI,
#        lettura dalla query string, nome del parametro dell'emittente.
#
# ⭐ Nasce il 2026-09-27 (brief-db-liste-datatable-grezze §3.1, decisione di
#    Tid): le due Storie diventano la lista a catalogo `vendite.giornale` —
#    la stessa del giornale trasversale — e prendono il contratto di lista
#    standard (`limit`/`offset`/`order_by`/`order_dir`) al posto di quello
#    loro (`page`/`page_size`/`sort_by`/`sort_dir`). Le due view stanno in due
#    moduli diversi: senza una sede comune il contratto sarebbe stato scritto
#    due volte, e il primo parametro aggiunto a una sola delle due avrebbe
#    fatto divergere due schede che a video sono la stessa lista.
# ⚠️ I filtri propri di UNA Storia restano nella sua view: «solo problemi»
#    (`info`) e' del lotto e solo suo.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiParameter

from apps.core.api.openapi_params import descrizione_order_by
from apps.core.api.payload_validators import parse_list_params, qp_bool_optional
from apps.vendite.db.vendite_repository import GIORNALE_ORDINE_DEFAULT, GIORNALE_SORT_COLUMNS

# Il parametro con cui una Storia riceve l'emittente del documento che la apre
# (`DomainAPIView.lista_emittente_param`).
# ⭐ Perche' serve: `vendite.giornale` e' `perimetro_emittente = t` e
#    `multi_emittente = f` a catalogo, quindi chi ha piu' emittenti nello scope
#    riceverebbe `E_UI_LISTA_EMITTENTE_DA_SCEGLIERE` DENTRO un drawer gia'
#    aperto su un documento che l'emittente lo dichiara. E' la richiesta a
#    sciogliere l'ambiguita', come nel tab dei registri dell'emittente.
# ⚠️ E' il SOGGETTO-RUOLO (`emittente_soggetto_ruolo_id`, NOT NULL su fatture e
#    lotti, e nel dettaglio di entrambi), non la PK di `emittenti_fiscali`
#    (`feedback_emittente_pk_vs_soggetto_ruolo`).
# ⛔ NON e' un filtro e non autorizza niente: il perimetro delle righe e'
#    l'entita' del path, e a dire se la si vede e' il cancello di TESTATA del
#    service (404 unificato). Il parametro dice solo che la schermata e'
#    leggibile — un valore sbagliato non mostra una riga in piu'.
EMITTENTE_PARAM_GIORNALE_ENTITA = "emittente_soggetto_ruolo_id"

PARAMS_LISTA_GIORNALE_ENTITA = [
    OpenApiParameter(name="limit", type=int, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(name="offset", type=int, location=OpenApiParameter.QUERY, required=False),
    OpenApiParameter(
        name="order_by", type=str, location=OpenApiParameter.QUERY, required=False,
        description=descrizione_order_by(
            GIORNALE_SORT_COLUMNS,
            f"Default `{GIORNALE_ORDINE_DEFAULT} DESC` (il preset di "
            "`vendite.giornale`); `gravita` ordina il rango e, dentro, il tempo "
            "dal piu' recente. Fuori whitelist -> 400.",
        ),
    ),
    OpenApiParameter(name="order_dir", type=str, location=OpenApiParameter.QUERY, required=False,
                     description="asc | desc; assente = desc."),
    OpenApiParameter(
        name=EMITTENTE_PARAM_GIORNALE_ENTITA, type=int, location=OpenApiParameter.QUERY,
        required=False,
        description=(
            "L'emittente (soggetto-ruolo) del documento che apre la Storia: "
            "scioglie il cancello di perimetro della lista per chi ha piu' "
            "emittenti nello scope. Non filtra le righe — il perimetro e' "
            "l'entita' del path."
        ),
    ),
    OpenApiParameter(
        name="ritirate", type=bool, location=OpenApiParameter.QUERY, required=False,
        description=(
            "Include anche le segnalazioni RITIRATE (`disabilitato`), che di "
            "default sono nascoste perche' appartengono a un tentativo poi "
            "rifatto. Quante ne sono state nascoste lo dice `ritirate_count`."
        ),
    ),
]


# Scopo: i parametri comuni delle due Storie dalla query string, pronti per il
#        service: paginazione e ordinamento dal BB (`parse_list_params`, con
#        `order_dir` assente = `None` che il repository legge come DESC) e
#        `ritirate` strict (`?ritirate=banana` e' un 400, non un `True` per
#        caso — api.md §Query params).
def parametri_lista_giornale_entita(qp: Any) -> dict[str, Any]:
    p = parse_list_params(qp, default_order=GIORNALE_ORDINE_DEFAULT)
    return {
        "limit": p["limit"],
        "offset": p["offset"],
        "order_by": p["order_by"],
        "order_dir": p["order_dir"],
        "includi_ritirate": qp_bool_optional(qp.get("ritirate"), "ritirate") is True,
    }
