# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Handler del job `CHIUSURA_SCADENZE`: chiude per scadenza lo stato
#        gestionale delle tabelle configurate in
#        `dbops.automazione_chiusura_scadenze`, PER UN'AZIENDA ALLA VOLTA.
#
#        ⭐ QUESTO E' IL LAVORO CHE PRIMA FACEVA pgAgent. Dal 2026-09-05 il job
#        notturno «sveglia e non lavora»: chiama `dbops.fn_accoda_chiusura_scadenze`,
#        che mette in coda un lavoro per ogni azienda del roster con l'identita'
#        tecnica di quell'azienda. Qui si esegue, minuti dopo, dentro il
#        drenatore.
#
#        ⭐ IL PERIMETRO NON E' UN PARAMETRO, ed e' il punto del cantiere:
#        `dbops.fn_apply_chiusura_scadenze` e' `SECURITY INVOKER`, quindi vede
#        cio' che vede l'identita' con cui gira. Il drenatore ha gia' aperto
#        `operator_identity_context` con l'utente tecnico dell'azienda, e la RLS
#        fa il resto. ⛔ Passare l'emittente come argomento sarebbe una SECONDA
#        sede del perimetro — quella che si dimentica.
# Note: ⚠️ Se `draina_coda_lavori` non gira, le scadenze NON si chiudono. Il
#        guasto non e' piu' un job che muore, e' un lavoro che nessuno prende:
#        lo nomina `dbops.vw_coda_lavori_da_guardare` (riga «mai preso»), che il
#        pannello dei processi mostra.
#        Brief: work-done/piano-be-fe-processi-automatici-identita-e-perimetro.md §lotto 4
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.db import connection

from apps.core.db._helpers import coerce_jsonb_dict

logger = logging.getLogger(__name__)

# handler_code seedato in `dbops.coda_lavori_tipi` per il tipo CHIUSURA_SCADENZE.
HANDLER_CODE = "chiusura_scadenze_default"


# Scopo: Esegue la chiusura per scadenza nel perimetro dell'identita' corrente.
#        `payload`: `{emittente_fiscale_id, emittente_codice}` — scritti dal
#        produttore SQL. `scope`: la terna dell'utente tecnico piu' l'emittente
#        congelato all'accodamento; il drenatore l'ha gia' applicata.
#
# ⚠️ Il payload NON decide niente: l'azienda serve a dire, nell'esito, PER CHI
#    e' girato questo lavoro. Un esito che porta solo dei conteggi si legge male
#    quando le aziende sono tre e i lavori pure.
# ⛔ Nessun `p_classe`: la funzione lo ammette (`DEFAULT NULL` = tutti i
#    bersagli) e il produttore non lo passa. Aggiungerlo qui vorrebbe dire
#    inventare un filtro che nessuno ha chiesto e che il job notturno non
#    userebbe — superficie morta con l'aria di un'opzione.
def chiusura_scadenze_handler(
    payload: dict[str, Any], *, scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    emittente_codice = (payload or {}).get("emittente_codice")
    with connection.cursor() as cursor:
        cursor.execute("SELECT dbops.fn_apply_chiusura_scadenze()")
        riga = cursor.fetchone()
    # 🔴 `coerce_jsonb_dict` e NON `dict(...)`, ed e' una riga che e' costata
    #    quattro notti (corretta il 2026-09-09).
    #    `dbops.fn_apply_chiusura_scadenze()` dichiara `RETURNS jsonb` e
    #    costruisce un oggetto JSON ben formato — ma **il backend Django per
    #    psycopg 3 non decodifica i `jsonb` fuori dall'ORM**: su un cursor RAW
    #    quel valore arriva come `str`.
    #    ⇒ `dict("{...}")` itera i CARATTERI, e ogni carattere e' una sequenza di
    #    lunghezza 1 dove ne servono 2: `ValueError: dictionary update sequence
    #    element #0 has length 1; 2 is required`. E' l'errore con cui il job ha
    #    fallito quattro notti di fila (5-8 settembre), due volte per notte,
    #    tentativi esauriti, dentro `dbops.vw_coda_lavori_da_guardare`.
    # ⛔ Il rimedio non era da inventare: `coerce_jsonb_dict` esiste dal
    #    2026-06-11, e la sua docstring descrive **questa** condizione. Questo era
    #    un call site scritto dopo l'estrazione del building block, che non l'ha
    #    cercato.
    # ⚠️ **E non era l'unico a non usarlo**, come questa riga ha detto per
    #    mezza giornata: altri OTTO punti facevano la stessa coercizione **a
    #    mano** (`ui/db/{ui,dashboard}_repository`,
    #    `core/db/{auth,search,email}_repository`, `invito_operatore_service`).
    #    ⛔ Il difetto di quella riga non era il numero sbagliato: era che
    #    «l'unico» chiude il discorso, e un discorso chiuso non si riapre.
    # ✅ Chiusi tutti e otto il 2026-09-09, e non con `coerce_jsonb_dict`: con
    #    **`jsonb_out`**, che conserva la loro semantica (un JSON illeggibile
    #    esplode invece di diventare `{}`). ⭐ La differenza NON e' di stile —
    #    su `auth_repository.registra_tentativo_login` il ripiego a `{}` avrebbe
    #    dato `result.get("bloccato") is None`, cioe' **account non bloccato**:
    #    un fail-OPEN su un percorso di autenticazione.
    # ⭐ Da quel giorno la copia numero nove non nasce: la vieta
    #    `apps/core/tests/test_coercizione_jsonb_dal_bb`, registro a **zero**.
    #    Ed e' il presidio che a questo call site sarebbe servito — era stato
    #    scritto DOPO l'estrazione del BB, e non l'aveva cercato.
    esito: dict[str, Any] = coerce_jsonb_dict(riga[0]) if riga else {}

    logger.info(
        "chiusura_scadenze.eseguita emittente=%s esito=%s",
        emittente_codice, esito,
    )
    # ⚠️ L'esito del database si consegna INTERO e sotto una chiave sua: e' un
    #    riepilogo per tabella, e appiattirlo qui vorrebbe dire decidere adesso
    #    quali bersagli esistono — che e' una configurazione, non un contratto.
    return {
        "emittente_fiscale_id": (payload or {}).get("emittente_fiscale_id"),
        "emittente_codice": emittente_codice,
        "chiusure": esito,
    }


# Scopo: Registra l'handler nel registry della coda. Chiamata da
#        `CoreConfig.ready()`: registrazione esplicita al boot, mai
#        auto-discovery — stesso patto degli altri due handler di coda.
def register() -> None:
    from apps.core.services.coda_lavori.handler_registry import register_handler
    register_handler(HANDLER_CODE, chiusura_scadenze_handler)
