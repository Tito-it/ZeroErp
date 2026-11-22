# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'ORDINAMENTO DI PARTENZA di una lista configurabile, applicato dal
#        backend in un punto solo (BE25 (2) di brief-db-revisione-ui, Q37 (a)
#        di Tid del 2026-11-20; la sede centrale approvata da Tid il
#        2026-11-22). Una GET di una lista che dichiara `lista_codice` e non
#        porta `order_by` riceve l'ordinamento risolto dal DB
#        (`ui.fn_ordinamento_lista`: il preset di base dell'utente, senza le
#        colonne che non puo' ordinare, col campo sorgente), e la risposta lo
#        dice in `meta.ordinamento`.
# Note: ⭐ PERCHE' QUI E NON IN OGNI VISTA. Prima lo stesso fatto stava in tre
#       sedi che dovevano concordare: l'`ordinamento_default` del preset,
#       l'`orderBy` dello store e il `default` del repository. La base view
#       conosce gia' la lista (`lista_codice`, lo stesso attributo del cancello
#       di perimetro) e l'utente: mettere l'ordinamento risolto nella RICHIESTA
#       lo fa arrivare a ogni lettore a valle senza toccarlo —
#       `parse_list_params`, le letture dirette della query e l'export, che
#       dichiara anche lui `lista_codice`. Un ordinamento scritto vista per
#       vista sarebbe stato ottanta copie della stessa regola.
#       ⚠️ Si applica la PRIMA voce del preset: `sql_order_clause` ordina per
#       una colonna piu' lo spareggio tecnico (deciso da Tid il 2026-11-22). Un
#       ordinamento a piu' voci sara' un'estensione di quel BB.
#       ⚠️ Il `default` del repository resta, ed e' la regola dell'API SENZA
#       preset: vale quando la lista non ha un preset di base o il preset non
#       dichiara un ordinamento (la funzione risponde con un elenco vuoto).
#       ⛔ Una richiesta che porta `order_by` non si tocca: il clic
#       dell'operatore sull'intestazione vince, e non si ricorda (Q39 §6).
#       ⭐ PROPOSTO, NON APPLICATO (`/verifica` del 2026-11-22). La base view
#       mette la voce nella query; la sede unica della risoluzione delle chiavi
#       (`apps.core.db._helpers.colonna_ordinamento`) la conferma quando sta
#       nella whitelist del repository, e solo allora la risposta la dice in
#       `meta.ordinamento`. Una lista che ordina nel browser non risolve
#       chiavi e non dice niente. Una chiave fuori whitelist (una colonna
#       `ordinabile` a catalogo, che l'amministratore puo' accendere, su un
#       campo che il codice non sa ordinare) e' `OrdinamentoPropostoRifiutato`:
#       la base view ritira la proposta, scrive il difetto nel log e rilegge la
#       lista senza (`ritira_ordinamento_di_partenza`). Senza, ogni apertura
#       della lista sarebbe un 400 su una richiesta che non ordinava niente.
#       Per le colonne del SEED il presidio resta statico:
#       `test_whitelist_copre_le_colonne_ordinabili` e
#       `test_ogni_lista_codice_ha_la_whitelist_a_registro`.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from apps.core.db.lista_catalogo_repository import fetch_ordinamento_lista
from apps.core.services.permissions_resolver import PermissionResolver
from apps.core.services.request_context import proponi_ordinamento

logger = logging.getLogger(__name__)

# I metodi che leggono una lista. Le scritture non si ordinano.
_METODI_DI_LETTURA = frozenset({"GET", "HEAD"})


# Scopo: la LETTURA dei fatti, in una funzione sola: l'ordinamento risolto
#        della lista per l'utente, con l'emittente della risoluzione della
#        configurazione (`PermissionResolver.get_emittente_for_user`, lo stesso
#        di `UiService.get_lista_config`: l'ordine e' quello che l'utente vede).
# ⭐ E' il punto che i test API senza DB mockano (`JwtMockedApiTest`), come lo
#    scope del cancello di perimetro: si spegne la lettura, non il BB.
def ordinamento_risolto(lista_codice: str, *, user: Any) -> list[dict[str, str]]:
    return fetch_ordinamento_lista(
        lista_codice,
        auth_user_id=user.id,
        emittente_fiscale_id=PermissionResolver.get_emittente_for_user(user),
    )


# Scopo: applica alla richiesta l'ordinamento di partenza della lista, se la
#        richiesta non ne porta uno. Scrive `order_by`/`order_dir` nella query
#        della richiesta e lo PROPONE (il `meta` lo dice se il repository
#        lo accetta).
# Perimetro: solo GET/HEAD di un utente autenticato; la lettura e'
#        `ordinamento_risolto`.
# Risultato atteso: niente; la richiesta e' cambiata solo se c'era un
#        ordinamento da applicare.
def applica_ordinamento_di_partenza(request: Any, *, lista_codice: str) -> None:
    if request.method not in _METODI_DI_LETTURA:
        return
    query = request._request.GET
    if (query.get("order_by") or "").strip():
        return
    voci = ordinamento_risolto(lista_codice, user=request.user)
    prima = next((v for v in voci if v.get("campo_sorgente")), None)
    if prima is None:
        return
    ordinamento = {
        "order_by": str(prima["campo_sorgente"]),
        "order_dir": str(prima["dir"]),
        "col": str(prima["col"]),
    }
    # ⚠️ La query di Django e' immutabile: se ne mette una copia al suo posto.
    #    `request.query_params` di DRF e' la stessa `_request.GET`, quindi la
    #    vedono tutti e due i modi di leggerla.
    nuova = query.copy()
    nuova["order_by"] = ordinamento["order_by"]
    nuova["order_dir"] = ordinamento["order_dir"]
    nuova._mutable = False
    # La query di prima, per `ritira_ordinamento_di_partenza`.
    request._request._query_senza_ordinamento_di_partenza = query
    request._request.GET = nuova
    # ⭐ PROPOSTO, non applicato: lo diventa quando il repository risolve la
    #    chiave nella sua whitelist (`colonna_ordinamento`). Solo allora la
    #    risposta lo dice in `meta.ordinamento`.
    proponi_ordinamento(ordinamento)


# Scopo: ritira la proposta: rimette la query della richiesta com'era e
#        dimentica l'ordinamento proposto. La chiama `DomainAPIView` quando il
#        repository rifiuta la chiave proposta (`OrdinamentoPropostoRifiutato`),
#        prima di rileggere la lista: la richiesta torna «senza ordinamento»,
#        direzione compresa, qualunque sia il modo in cui il repository legge
#        `order_by` e `order_dir`.
# ⚠️ Il rifiuto e' un difetto del CATALOGO, non dell'operatore: una colonna
#    `ordinabile` (la puo' accendere l'amministratore) su un campo che il
#    repository non sa ordinare, messa in testa al preset. Si scrive nel log
#    perche' qualcuno la corregga; la lista intanto si apre col suo default.
def ritira_ordinamento_di_partenza(request: Any, *, lista_codice: str) -> None:
    django_request = request._request
    originale = getattr(django_request, "_query_senza_ordinamento_di_partenza", None)
    if originale is not None:
        logger.warning(
            "ordinamento_di_partenza.rifiutato lista=%s order_by=%s: la colonna "
            "del preset e' ordinabile a catalogo ma fuori dalla whitelist del "
            "repository; la lista si legge col suo default.",
            lista_codice, django_request.GET.get("order_by"),
        )
        django_request.GET = originale
        del django_request._query_senza_ordinamento_di_partenza
    proponi_ordinamento(None)
