# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lettura del DICHIARATO di deploy dei processi automatici — chi sveglia
#        ogni processo del backend e con quale cadenza.
# Note: ⭐ LA SEDE E' UNA SOLA, ed e' `backend/deploy/sveglie.json`. Questo
#        modulo la LEGGE, non la ridichiara: l'altro lettore e'
#        `backend/bin/install-timers.sh`, che dallo stesso file prende
#        l'`OnCalendar` da sostituire nei template e la lista di cosa
#        abilitare. Due programmi, un file.
#
#        ⛔ PERCHE' ESISTE, e non e' un'astrazione di comodo. Fino al
#        2026-09-06 lo stesso fatto — «ogni quanto ci si aspetta questo
#        processo» — era scritto in DUE posti che non si conoscevano:
#        l'`OnCalendar` cablato dentro `install-timers.sh` e
#        `WORKER_ATTIVO_SOGLIA_MINUTI = 10` in `coda_lavori/gestione_service.py`.
#        Il secondo copriva due processi su sei con un margine di 10x e 5x sulle
#        rispettive cadenze, e il perche' non era scritto da nessuna parte. Due
#        scritture dello stesso fatto prima o poi dissentono, e qui la
#        divergenza sarebbe stata muta: un pallino verde su un worker fermo.
#
#        ⭐ LA CADENZA STA QUI; LA TOLLERANZA NO (dal 2026-09-11). Sono due
#        fatti diversi, e il JSON per cinque giorni li ha tenuti insieme:
#          · la CADENZA e' COME il deploy onora il processo — dipende dall'host,
#            dal fuso, dal carico — e vive dove vive il deploy, cioe' qui. E' la
#            stessa ragione per cui il team DB ha rifiutato di dichiarare la
#            cadenza dei job pgAgent su `dbops.processi`: pgAgent la sa gia';
#          · la TOLLERANZA («se sto bene lascio un segno almeno ogni N minuti»)
#            e' il CONTRATTO del processo, uguale su ogni installazione — e il
#            lettore che ne ha piu' bisogno sta nel DATABASE: il panorama
#            `dbops.vw_processi_programmazione` dice `MUTO` sui COMMAND col
#            contratto, e il guardiano pgAgent del digest legge solo il catalogo.
#            ⇒ vive in `dbops.processi.tolleranza_minuti` (brief
#            `brief-db-quattro-processi-senza-presidio.md` §10.2, D5), la legge
#            `ProcessiRepository.contratti_liveness`, e `carica_sveglie` la
#            RIFIUTA se ricompare nel JSON: una sede sola resta una sede sola.
#        ⚠️ Il deploy puo' VIOLARE il contratto (un timer piu' lento della
#        tolleranza): quella verifica e' `test_contratto_liveness_vs_deploy`,
#        che confronta l'`oncalendar` di qui con il seed del catalogo nel repo.
#
#        ⚠️ Il dichiarato e' il DEFAULT di progetto, non lo stato di un host.
#        Un host puo' avere un `OnCalendar` diverso (l'installer sostituisce un
#        placeholder) o un timer spento a mano: per sapere cosa sta girando
#        DAVVERO si guarda `maintenance.job_run_log`. Il confronto fra i due e'
#        il punto — una promessa senza verifica invecchia come tutte.
# ------------------------------------------------------------

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# ⭐ IL LAYOUT DEL DEPLOY SI CALCOLA QUI, UNA VOLTA. Questo modulo sta in
#    `backend/apps/core/services/`, quindi `parents[3]` è `backend/`.
# ⛔ Non si ricopia altrove, nemmeno in un test: una seconda aritmetica di
#    percorso che punta alla cartella sbagliata non fallisce — trova zero file e
#    passa. È il «verde per sottrazione», e su un presidio che deve accorgersi
#    di ciò che MANCA sarebbe il difetto peggiore possibile.
DEPLOY_DIR = Path(__file__).resolve().parents[3] / "deploy"
TEMPLATE_DIR = DEPLOY_DIR / "systemd"
_PERCORSO_SVEGLIE = DEPLOY_DIR / "sveglie.json"

# ⭐ QUI si definisce il vocabolario delle forme: il JSON non ha uno schema, e
#    questa è la sua unica dichiarazione in codice.
# ⚠️ `install-timers.sh` ci RAMIFICA sopra (deve sapere se scrivere anche un
#    `.timer`), e non è una copia della regola: è un consumatore dell'enum, che
#    come questo si ferma su un valore che non conosce. Una forma nuova va
#    insegnata a entrambi — e nessuno dei due può ignorarla in silenzio.
FORMA_TIMER = "timer"
FORMA_SERVIZIO = "servizio"
_FORME = (FORMA_TIMER, FORMA_SERVIZIO)

# Il nome dell'unit finisce interpolato in un percorso di file e passato a
# `systemctl`. ⛔ Il file è versionato e passa da PR, ma un refuso con una barra
# scriverebbe FUORI da `/etc/systemd/system` senza che niente lo dica: stesso
# presidio che il progetto applica agli identificatori SQL interpolati
# (`PartitionedNoteRepository`, `emittente_scope_helpers`).
_UNIT_AMMESSA = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


# Scopo: una sveglia dichiarata — l'unit systemd che fa partire un processo.
# ⚠️ La chiave e' `unit`, NON `processo_codice`: un processo puo' avere piu'
#    sveglie (`run_fatturazione_batch` ne ha due, una per corsia). Chiavare sul
#    processo avrebbe fatto sparire una delle due in silenzio.
@dataclass(frozen=True)
class Sveglia:
    unit: str
    processo_codice: str
    forma: str
    oncalendar: str | None
    abilita: bool
    nota: str

    # Scopo: vero se questa sveglia e' un timer con una cadenza dichiarata.
    @property
    def e_timer(self) -> bool:
        return self.forma == FORMA_TIMER


# Scopo: carica e valida il dichiarato. Cache di modulo: il file e' un dato di
#        progetto, non cambia sotto un processo vivo.
# ⛔ FAIL-LOUD su ogni difetto di forma. Un file di deploy letto «al meglio»
#    darebbe una sveglia in meno senza dirlo, ed e' esattamente il guasto-per-
#    assenza che questo cantiere esiste per togliere.
@lru_cache(maxsize=1)
def carica_sveglie() -> tuple[Sveglia, ...]:
    with _PERCORSO_SVEGLIE.open(encoding="utf-8") as fh:
        dati = json.load(fh)

    righe = dati.get("sveglie")
    if not isinstance(righe, list) or not righe:
        raise ValueError(f"{_PERCORSO_SVEGLIE}: la chiave 'sveglie' manca o e' vuota")

    sveglie: list[Sveglia] = []
    visti: set[str] = set()
    for riga in righe:
        unit = str(riga.get("unit") or "")
        if not unit:
            raise ValueError(f"{_PERCORSO_SVEGLIE}: una voce non ha 'unit'")
        if not _UNIT_AMMESSA.match(unit):
            raise ValueError(
                f"{_PERCORSO_SVEGLIE}: nome di unit non ammesso: {unit!r} "
                f"(minuscole, cifre, punto, trattino, underscore)"
            )
        if unit in visti:
            raise ValueError(f"{_PERCORSO_SVEGLIE}: unit duplicata: {unit}")
        visti.add(unit)

        forma = str(riga.get("forma") or "")
        if forma not in _FORME:
            raise ValueError(
                f"{_PERCORSO_SVEGLIE}: {unit}: forma '{forma}' non ammessa "
                f"(attese: {', '.join(_FORME)})"
            )

        oncalendar = riga.get("oncalendar")
        # ⚠️ Un timer senza cadenza non e' un timer: l'installer scriverebbe un
        #    unit che systemd rifiuta, e lo scoprirebbe l'host, non la CI.
        if forma == FORMA_TIMER and not oncalendar:
            raise ValueError(f"{_PERCORSO_SVEGLIE}: {unit}: timer senza 'oncalendar'")
        if forma == FORMA_SERVIZIO and oncalendar:
            raise ValueError(
                f"{_PERCORSO_SVEGLIE}: {unit}: un servizio sempre acceso non ha "
                f"una cadenza da dichiarare"
            )

        processo = str(riga.get("processo_codice") or "")
        if not processo:
            raise ValueError(f"{_PERCORSO_SVEGLIE}: {unit}: manca 'processo_codice'")

        # ⛔ LA TOLLERANZA NON STA PIU' QUI (vedi header). Non si ignora la
        #    chiave: chi la riscrive crede di aver dichiarato qualcosa, e un
        #    numero letto da nessuno e' peggio di un errore.
        if "tolleranza_minuti" in riga:
            raise ValueError(
                f"{_PERCORSO_SVEGLIE}: {unit}: 'tolleranza_minuti' non e' piu' "
                f"un campo del dichiarato di deploy — il contratto di liveness "
                f"vive in dbops.processi.tolleranza_minuti (seed "
                f"80_data/sql/dbops/processi.csv)"
            )

        # ⛔ `abilita` SI DICHIARA, non si omette. Con un default il silenzio
        #    varrebbe «spento» — cioè un processo nuovo che non parte, che è
        #    esattamente il guasto-per-assenza per cui questo file esiste. Il
        #    default sicuro è quello che nasconde meglio la dimenticanza.
        if "abilita" not in riga or not isinstance(riga["abilita"], bool):
            raise ValueError(
                f"{_PERCORSO_SVEGLIE}: {unit}: 'abilita' è obbligatorio e "
                f"dev'essere true o false"
            )

        sveglie.append(Sveglia(
            unit=unit,
            processo_codice=processo,
            forma=forma,
            oncalendar=str(oncalendar) if oncalendar else None,
            # Già validato bool qui sopra: un `bool(...)` in più direbbe che il
            # valore può non esserlo, cioè il contrario di quanto appena imposto.
            abilita=riga["abilita"],
            nota=str(riga.get("nota") or ""),
        ))

    return tuple(sveglie)


# Scopo: le sveglie dichiarate per un processo (zero, una o piu').
def sveglie_di_processo(processo_codice: str) -> tuple[Sveglia, ...]:
    return tuple(s for s in carica_sveglie() if s.processo_codice == processo_codice)
