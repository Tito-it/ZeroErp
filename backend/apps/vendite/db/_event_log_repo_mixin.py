# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block repository per la scrittura sul giornale
#        `vendite.event_log`, via `vendite.fn_log_event`.
#
#        ESTRAZIONE REGOLA-DEL-2 (consegna BE-6 del brief
#        `brief-db-event-log-scope-e-riga-parlante.md` §5). Il metodo era
#        COPIA CARBONE in `pipeline_repository.py` e `commesse_repository.py`
#        — stessa firma, stesso SQL, stessi default. Finche' restavano due,
#        ogni modifica alla firma della funzione DB si scriveva due volte, e
#        bastava che una restasse indietro perche' meta' del backend
#        smettesse di scrivere il diario senza che nessuno lo notasse.
#
#        ⭐ E' successo davvero, ed e' il motivo per cui l'estrazione viene
#        PRIMA dell'adeguamento della firma e non dopo: `fn_log_event` ha
#        perso tre parametri in un giorno solo (`p_actor`/`p_source` con L1,
#        `p_domain` con L4), e con due copie l'adeguamento andava fatto due
#        volte a ogni giro.
#
# ── LA FIRMA E' A SEI, E LE TRE COSE CHE NON SI PASSANO PIU' ────────
#   `fn_log_event(entity_type, entity_id, event_code, severity,
#                 correlation_id, payload)`
#
#   ⛔ `actor` e `source` NON esistono piu' (D-6): erano costanti su 386
#      righe su 386 — `service:django` e `django` — mentre «chi» lo dice
#      gia' `user_insert`, che funziona anche sul canale batch.
#   ⛔ `domain` NON esiste piu' (D-18): e' una PROPRIETA' del codice evento e
#      vive in `config.eventi_dominio`. Passarlo dal chiamante voleva dire
#      permettergli di scriverne uno diverso da quello del codice, cioe' due
#      verita' che nessun vincolo puo' tenere allineate.
#
#   ⭐ E non si passano nemmeno PERIMETRO, CHI e SCADENZA
#      (`emittente_soggetto_ruolo_id`, `auth_user_id`, `cleanup_at`): li
#      deriva `trg_event_log_a10_deriva_scope_ins`, perche' sono fatti che il
#      database conosce e il chiamante no.
#
# ── ⚠️ QUESTA SCRITTURA PUO' FALLIRE, E VA AVVOLTA ──────────────────
#   Dal 2026-08-22 il giornale RIFIUTA una riga di cui non sa dire di chi e':
#   `entity_type` fuori vocabolario, o `entity_id` che non trova niente. Sono
#   `P0001` con codice registrato (`E_EVENT_LOG_ENTITY_TYPE_IGNOTO`,
#   `E_EVENT_LOG_SCOPE_NON_RISOLTO`), quindi si scoprono in test — ma a
#   runtime un difetto del diario NON deve mai diventare il messaggio che
#   legge l'operatore, ne' far fallire il lavoro che il diario descrive
#   (D-15). Il posto dove avvolgerla e' il telaio `_diagnostica_best_effort`
#   del `pipeline_runner`, non un `try` dentro questo mixin: qui si scrive,
#   la politica di fallimento la decide chi chiama.
# ------------------------------------------------------------

from __future__ import annotations

import json
from typing import Any

from django.db import connection


class EventLogRepositoryMixin:
    """Building block di scrittura sul giornale `vendite.event_log`.

    Non richiede attributi di classe: la tabella e la funzione sono una sola.
    Si innesta su qualunque repository che debba lasciare una traccia
    sull'entita' che sta lavorando.
    """

    # Scopo: Scrive un evento sul giornale `vendite.event_log` e ne
    #        restituisce l'id.
    #
    #        Perimetro: una riga per FATTO accaduto su UN'entita' del
    #        vocabolario `config.tipi_entita` che abbia un modo di risoluzione
    #        dell'emittente — oggi LOTTO, COMMESSA, FATTURA. Risultato atteso:
    #        l'id della riga scritta, oppure un `P0001` se il giornale non
    #        riesce a dire di chi e' la riga.
    #
    # ⚠️ `entity_id` e' la PK `id` della tabella puntata, SEMPRE. Non un
    #    segnaposto, non uno zero, non un id «che nascera' dopo»: la
    #    derivazione del perimetro va a cercarlo davvero, e se non lo trova
    #    rifiuta la riga.
    # ⚠️ `severity` ammette INFO | WARN | ERROR e nient'altro (CHECK
    #    `chk_event_log_severity`). ⛔ "WARNING" NON e' un valore: e' il
    #    difetto BE-1, che ha tenuto `EMITTIBILITA_FALLITA` fuori dal registro
    #    per mesi.
    # ⚠️ `event_code` non ha una FK verso `config.eventi_dominio`, ed e'
    #    deliberato (D-12: il diario non smette di scrivere per un problema di
    #    configurazione). A protestare per un codice non dichiarato e' la
    #    BUILD, non questa chiamata — vedi il cancello dei codici evento.
    def log_event(
        self,
        *,
        entity_type: str,
        entity_id: int,
        event_code: str,
        severity: str = "INFO",
        correlation_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT vendite.fn_log_event(
                    %s, %s, %s, %s, %s::uuid, %s::jsonb
                )
                """,
                [
                    entity_type,
                    entity_id,
                    event_code,
                    severity,
                    correlation_id,
                    # ⚠️ Serializzato QUI e non col `_to_jsonb_param` della
                    #    sottoclasse: `pipeline_repository` tipizza il suo su
                    #    `LottoPipelineMeta` e restituisce `None` sul vuoto,
                    #    mentre un payload di evento e' un dict qualunque e il
                    #    vuoto e' `{}`. Appoggiarsi al metodo dell'ospite
                    #    legherebbe il building block alla forma di uno dei due
                    #    chiamanti — ed e' una riga, non un helper.
                    json.dumps(payload or {}),
                ],
            )
            row = cursor.fetchone()
        assert row is not None
        return int(row[0])
