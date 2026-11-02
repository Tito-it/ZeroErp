# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Mettere il `request_id` su OGNI riga di log, invece che su quelle in
#        cui qualcuno si e' ricordato di scriverlo a mano.
#
#        E' la consegna BE-8 (Passo 2 di `analisi-osservabilita-log.md`): il
#        `request_id` esisteva gia' come contextvar ed era gia' scritto in
#        `dbops.request_log`, ma nella riga di log Python non c'era. Risultato:
#        di una richiesta si sapeva l'esito (la riga in `request_log`) e non si
#        sapeva **cosa aveva fatto** — i log applicativi non si potevano legare
#        alla richiesta che li aveva prodotti.
#
# ⭐ PERCHE' UN FILTRO E NON UN ARGOMENTO NEL MESSAGGIO. Scriverlo a mano
#    funziona — `api.exception` lo faceva — ma vale solo dove qualcuno se lo
#    ricorda, ed e' la forma di difetto che questo progetto ha gia' incontrato
#    piu' volte: una cosa che tutti devono scrivere e nessuno governa. Nel
#    filtro la correlazione diventa una proprieta' del canale di log, non una
#    disciplina di chi scrive.
#
# ⚠️ IL FILTRO VA SU TUTTI GLI HANDLER CHE USANO IL FORMATO `verbose`, non su un
#    logger. Un filtro attaccato a un logger non vale per i suoi figli, e il
#    formato cita `%(request_id)s`: un record che arrivasse senza l'attributo
#    farebbe fallire la FORMATTAZIONE, cioe' perderebbe la riga di log proprio
#    mentre si sta cercando di capire cosa e' successo. Attaccandolo agli
#    handler, ogni record passa di qui prima di essere formattato.
#
# ⚠️ Fuori da una richiesta HTTP il contextvar e' vuoto — worker della coda,
#    comandi di management, shell — e li' il valore e' `-`. Non e' un ripiego:
#    e' l'informazione giusta, «questa riga non appartiene a nessuna richiesta».
#    ⭐ Ed e' il segnaposto gia' in uso: `api.exception` scriveva `request_id=-`
#    con la stessa convenzione.
# ------------------------------------------------------------

from __future__ import annotations

import logging

# Il valore per le righe che non nascono da una richiesta HTTP. Un trattino e
# non la stringa vuota: in una riga di log a campi separati da spazi, il vuoto
# sposterebbe le colonne e renderebbe il formato non piu' tagliabile.
NESSUNA_RICHIESTA = "-"


class RequestIdFilter(logging.Filter):
    """Aggiunge `request_id` a ogni record, prendendolo dal contesto richiesta.

    Non filtra niente: ritorna sempre `True`. E' un filtro solo perche' e' il
    punto di aggancio che `logging` offre per arricchire un record prima della
    formattazione — il nome della classe base dice il meccanismo, non lo scopo.
    """

    # Scopo: Arricchisce il record col `request_id` corrente e lo lascia passare.
    #
    # ⚠️ L'import sta DENTRO il metodo di proposito: `settings.LOGGING` viene
    #    costruito mentre Django si configura, e questo modulo viene importato
    #    da li'. Un import di `apps.core.services` in testa al file tirerebbe
    #    dentro il pacchetto (e con lui il translator e le settings) prima che
    #    le settings esistano.
    def filter(self, record: logging.LogRecord) -> bool:
        from apps.core.services.request_context import get_request_id

        try:
            request_id = get_request_id()
        except Exception:  # un log non deve mai far fallire il chiamante
            request_id = None
        record.request_id = request_id or NESSUNA_RICHIESTA
        return True
