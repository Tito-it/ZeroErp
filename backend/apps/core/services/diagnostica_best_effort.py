# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL TELAIO DELLE SCRITTURE DI DIAGNOSI — «best-effort, ma mai in
#        silenzio». Una scrittura che serve a RACCONTARE un fatto (un diario,
#        una marcatura d'errore, una riga di log funzionale) non deve mai
#        prendere il posto del fatto che racconta: se fallisce, il lavoro
#        prosegue — ma il fallimento lascia una riga nel log tecnico.
#
#        ⭐ QUELLA RIGA E' TUTTA LA DIFFERENZA fra «best-effort» e «silenzio».
#        Ingoiare senza traccia ricrea il difetto BE-1: `EMITTIBILITA_FALLITA`
#        scriveva `severity="WARNING"`, il CHECK la rifiutava, e per MESI il
#        registro e' rimasto a zero righe senza che nessuno se ne accorgesse.
#        E' la decisione D-15 del brief `brief-db-event-log-scope-e-riga-parlante`:
#        **fail-loud nel DB, best-effort nel BE**.
#
# ── PERCHE' VIVE IN `core` E NON NEL RUNNER ────────────────────────
#   Nasce dentro `pipeline_runner` il 2026-08-21, alla terza copia di uno
#   stesso `try/except/log_error_only` (marcatore di errore del LOTTO,
#   marcatura della FATTURA fallita, riscrittura del TASK RUN). E' salito qui
#   alla QUINTA, quando `commesse_service` ha avuto lo stesso bisogno sul
#   ramo push: un telaio che vive dentro uno dei suoi utenti si copia al
#   primo utente che sta altrove.
#
# ⚠️ INGOIA QUALUNQUE ECCEZIONE DI PROPOSITO. Chi lo usa sta gia' gestendo un
#    fallimento, oppure sta scrivendo un contorno: il secondo errore non ha
#    diritto di prendere il posto del primo, ne' di diventare il messaggio che
#    l'operatore sta aspettando.
# ⛔ NON usarlo per una scrittura che fa parte del LAVORO. Se il dato deve
#    esserci perche' il risultato sia corretto, un fallimento va sollevato:
#    questo telaio e' per cio' che DESCRIVE il lavoro, non per cio' che lo
#    compone.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.db import transaction

from apps.core.services.error_manager import ErrorManager

# Il codice con cui il fallimento di una scrittura di diagnosi si presenta nel
# log tecnico. Uno solo, e volutamente generico: la cosa che identifica il
# guasto e' il `function_name` piu' il `contesto` passati dal chiamante, non un
# codice per ogni sede.
#
# ⭐ ERA `E_PIPELINE_MARK_ERROR` FINO AL 2026-08-23, e il cambio racconta
#    qualcosa. Quel codice era nato quando il telaio viveva dentro
#    `pipeline_runner`, e da quando serve anche il push commesse **mentiva due
#    volte**: il NOME diceva «PIPELINE» — chi avesse cercato i guasti del push
#    per codice non li avrebbe trovati — e la CLASSE era `DATO_ERRATO`, cioe'
#    400, su un guasto interno in cui non c'e' nessun dato sbagliato di nessuna
#    persona e chi ha fatto la richiesta non puo' farci niente.
#    Il codice nuovo e' `TECNICO`, ed e' stato coniato dal team DB su richiesta
#    (catalogo 987).
#
# ⚠️ E il vecchio NON e' stato ritirato nello stesso momento, di proposito: si
#    deprecano i codici **dopo** che nessuno li solleva piu', non prima. Ora che
#    questa costante e' spostata, `E_PIPELINE_MARK_ERROR` (699) puo' prendere il
#    suo `obsoleto_dal` — ed e' l'unica cosa che resta da fare al team DB.
CODICE_DIAGNOSTICA_FALLITA = "E_DIAGNOSTICA_NON_REGISTRATA"


# Scopo: Esegue una scrittura di diagnosi senza che un suo fallimento possa
#        propagarsi al chiamante, lasciando pero' traccia in `dbops.error_log`.
#
#        Perimetro: qualunque scrittura di contorno (diario, marcatura,
#        log funzionale) che sopravvive o meno al lavoro che descrive, ma non
#        deve mai deciderne l'esito. Risultato atteso: nessuna eccezione verso
#        il chiamante, e — in caso di guasto — una riga nel log tecnico con il
#        contesto necessario a capire *quale* scrittura non e' passata.
#
# ⛔ IL SAVEPOINT NON E' UN DETTAGLIO: e' cio' che rende il telaio usabile
#    DENTRO una transazione, ed e' il modo in cui questa funzione sbaglierebbe
#    in silenzio se qualcuno lo togliesse «perche' tanto c'e' il try».
#
#    In PostgreSQL, quando un comando fallisce, l'INTERA transazione entra in
#    stato abortito: ingoiare l'eccezione lato Python non la recupera, e il
#    comando successivo muore con «current transaction is aborted». Il `try`
#    da solo, quindi, non protegge niente — sposta solo il punto in cui il giro
#    si rompe, rendendo il guasto piu' difficile da leggere di prima.
#
#    L'`atomic()` annidato apre un SAVEPOINT: il fallimento della scrittura di
#    diagnosi rolla indietro SOLO lei, e la transazione del chiamante prosegue
#    sana. Fuori da una transazione ne apre una minima attorno alla scrittura,
#    che e' inerte.
#
#    ⚠️ Le tre scritture per cui il telaio e' nato stavano tutte FUORI
#    dall'`atomic` dello step, ed e' il motivo per cui fin qui il savepoint non
#    era servito. Con BE-7 il telaio avvolge anche gli eventi di
#    `PIPELINE_STARTED` / `STEP_COMPLETED` / `PIPELINE_COMPLETED`, che stanno
#    DENTRO: senza savepoint, un evento rifiutato avrebbe continuato a
#    uccidere il giro — cioe' il difetto che BE-7 esiste per chiudere.
#
# ⚠️ `contesto` non e' decorativo: e' l'unico modo per distinguere due
#    fallimenti dello stesso telaio. Ci vanno le COORDINATE (quale lotto,
#    quale commessa, quale fattura), non una frase.
def diagnostica_best_effort(
    azione: Callable[[], object],
    *,
    contesto: dict[str, Any],
    function_name: str,
) -> None:
    try:
        with transaction.atomic():
            azione()
    except Exception as exc:  # vedi l'intestazione: e' il mestiere
        # Qui la transazione del chiamante e' di nuovo sana (savepoint rollato
        # indietro), quindi questa scrittura puo' davvero avvenire: e' la riga
        # che distingue «best-effort» da «silenzio».
        ErrorManager.log_error_only(
            code=CODICE_DIAGNOSTICA_FALLITA,
            context={**contesto, "mark_error": str(exc)},
            area="backend",
            function_name=function_name,
        )
