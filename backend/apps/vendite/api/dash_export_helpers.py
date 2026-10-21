# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block per gli endpoint di export delle liste dei CRUSCOTTI
#        (situazione aperta, backlog, competenza fatturazione). Estratto alla
#        prima scrittura e non alla seconda perche' le liste sono CINQUE e
#        condividono la stessa identica coda: chiamare la fn di lista del
#        service in modalita' EXPORT, sfilare `results` e `count`
#        dall'envelope, e passare tutto al building block generico
#        `build_export_response`.
#
#        ⚠️ La modalita' export si chiede con `max_rows`, NON con un
#        `limit` gigante: il tetto di `MAX_LIMIT` righe PER PAGINA e' un guard di
#        interfaccia condiviso da tutte le liste del progetto
#        (`pagina_da_query`), e chiedere 10.001 righe di pagina lo viola —
#        difetto misurato al primo download reale (2026-08-15). Con `max_rows`
#        la paginazione e' saltata e il perimetro esce intero; il tetto che
#        vale per l'export e' un altro, `EXPORT_MAX_ROWS`, presidiato dal
#        building block generico.
#
#        Differenza rispetto agli export di dominio (clienti, contratti…):
#        li' il service espone una `list_*` che ritorna la coppia
#        (results, total); qui le fn dei cruscotti ritornano gia' l'ENVELOPE
#        paginato, perche' nascono per la dashboard. Invece di aggiungere una
#        seconda firma a cinque funzioni si adatta qui, in un punto solo.
#
#        Lo scope emittente NON viaggia da qui: e' interamente DB-side (RLS
#        invoker + GUC commesse), esattamente come per gli endpoint di lista
#        gemelli. Un export non deve poter vedere piu' della lista che copia.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable

from django.http import HttpResponse
from rest_framework.request import Request

from apps.core.services.locale_formatters import format_for_export
from apps.ui.api.export_helpers import build_export_response, parse_export_format
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS


# Scopo: Rende i filtri di dominio adatti al blocco «Filtri applicati» del file.
#        Due cose, entrambe imparate rompendo:
#
#        1. il renderer fa `json.dumps` di questo dict (riga commentata del CSV
#           / foglio dedicato dell'XLSX), e un `datetime.date` NON e' JSON
#           serializzabile: il primo download del cruscotto competenza e'
#           fallito con «Object of type date is not JSON serializable».
#           Backlog e Situazione aperta passavano solo perche' non hanno
#           filtri data. Le date si convertono col formatter CENTRALIZZATO
#           (`format_for_export`, IT), mai con uno strftime inline;
#        2. i filtri NON impostati non vanno scritti: `None`, stringa vuota e
#           `solo_ritardo: false` significano «filtro assente», ed elencarli
#           come applicati e' una descrizione falsa del perimetro del file.
def _filtri_leggibili(filtri: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for chiave, valore in filtri.items():
        if valore is None or valore == "" or valore is False:
            continue
        if isinstance(valore, (date, datetime)):
            out[chiave] = format_for_export(
                valore, tipo_dato="datetime" if isinstance(valore, datetime) else "date",
            )
        else:
            out[chiave] = valore
    return out


# Scopo: i filtri normalizzati, con le etichette risolte al posto dei valori
#        grezzi sulle sole chiavi che il chiamante traduce.
# ⚠️ L'override vale solo sulle chiavi sopravvissute alla normalizzazione: un
#        filtro assente resta assente, un'etichetta non lo resuscita.
def _filtri_leggibili_con_etichette(
    filtri: dict[str, Any], etichette: dict[str, Any] | None,
) -> dict[str, Any]:
    out = _filtri_leggibili(filtri)
    if not etichette:
        return out
    for chiave, etichetta in etichette.items():
        if chiave in out and etichetta:
            out[chiave] = etichetta
    return out


# Scopo: Coda invariante dell'export di una lista cruscotto.
#        Argomenti:
#          - request: la request DRF (porta `?formato=csv|xlsx`);
#          - lista_codice: catalogo colonne (es. 'vendite.dash_backlog_documenti'),
#            che decide quali colonne finiscono nel file e in quale ordine —
#            la preferenza dell'operatore, non una lista fissa nel codice;
#          - fetch: la fn di lista del service, invocata con
#            `max_rows=EXPORT_MAX_ROWS + 1` (il +1 intercetta l'overflow come
#            per le altre liste) piu' i filtri gia' parsati;
#          - filtri: kwargs di dominio da passare a `fetch`, ed e' anche cio'
#            che finisce come metadato «filtri applicati» dentro il file.
#        Risultato: HttpResponse col file, oppure sollevazione con codice
#        registrato se il formato non e' valido o si supera il cap righe.
def build_dash_export_response(
    request: Request,
    *,
    lista_codice: str,
    fetch: Callable[..., dict[str, Any]],
    filtri: dict[str, Any],
    etichette_filtri: dict[str, Any] | None = None,
) -> HttpResponse:
    # Formato PRIMA della query: su formato invalido non si paga il fetch.
    # ⚠️ Il parametro e' `formato` (italiano) e non `format`: quest'ultimo e'
    # magic per la content-negotiation DRF e intercetterebbe la chiamata
    # prima della view.
    fmt = parse_export_format(request)

    # `max_rows` (non `page_size`): salta la paginazione invece di violarne
    # il tetto. Il +1 serve a far scattare il guard di limite sotto quando il
    # perimetro supera EXPORT_MAX_ROWS, invece di troncare in silenzio.
    envelope = fetch(max_rows=EXPORT_MAX_ROWS + 1, **filtri)
    results = list(envelope.get("results") or [])
    total = int(envelope.get("count") or 0)

    return build_export_response(
        request,
        lista_codice=lista_codice,
        results=results,
        total=total,
        # I filtri di dominio sono gia' leggibili (codici brevi: area,
        # classe, stadio, mese), ma vanno NORMALIZZATI per il file — vedi
        # `_filtri_leggibili`. `etichette_filtri` permette a una view di
        # SOSTITUIRE il valore di singole chiavi con l'etichetta risolta (un
        # `registro_id=4` non dice niente a chi apre il foglio un mese dopo).
        # ⛔ E' un merge su cio' che e' gia' stato normalizzato, NON un
        #    rimpiazzo del dizionario intero: col rimpiazzo ogni view che
        #    volesse tradurre UNA chiave dovrebbe ricopiarsi tutte le altre, e
        #    il giorno che ne nasce una nuova sparirebbe dal file in silenzio —
        #    proprio dalla riga che promette di dire quale perimetro si sta
        #    guardando.
        # ⚠️ Solo le chiavi GIA' presenti: un filtro non impostato non deve
        #    ricomparire come applicato per via di un'etichetta.
        filtri_applicati=_filtri_leggibili_con_etichette(filtri, etichette_filtri),
        fmt=fmt,
    )
