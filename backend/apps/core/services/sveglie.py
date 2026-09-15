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
#        ⭐ E DAL 2026-09-14 STA QUI ANCHE LA RIGA DI COMANDO (`comando`, l'argv
#        dopo `bin/run-command.sh`), e il template `.service` porta il segnaposto
#        `__COMANDO__` che l'installer rende come gia' `__ONCALENDAR__`. Il
#        motivo e' «Esegui ora» (analisi-riavvio-processi-da-interfaccia.md
#        §4.1-bis, brief-db-avvio-manuale-di-un-processo.md): il pulsante lancia
#        LO STESSO comando del timer, meno l'orario, e il backend non puo'
#        leggerlo da un file `.service`. Una sede sola: la riga che il timer
#        esegue E' quella che il pulsante esegue, e non possono divergere.
#        ⛔ Un `comando` ricopiato qui ACCANTO a una riga cablata nel template
#        sarebbe la seconda sede — quella che resta indietro, e qui «indietro»
#        vuol dire un pulsante che lancia una cosa diversa dal timer. Lo
#        presidia `scripts/tests/test-install-timers.sh` (nessun `ExecStart`
#        cablato; l'unit reso porta l'argv di qui).
#
#        ⭐ E DAL 2026-09-15 STA QUI ANCHE `avvio_manuale` — «questa sveglia e'
#        candidata a «Esegui ora»?» — obbligatorio come `abilita` e per la
#        stessa ragione. Decisione di Tid (piano-be-fe-avvio-manuale §3.2,
#        brief §8.5 punto 2): il drenatore ASPETTA il sottoprocesso e intanto
#        non drena altro, quindi a mano si lanciano solo comandi BREVI; un
#        comando lungo per natura (i due giri di fatturazione) e il drenatore
#        stesso non sono candidati, e «non candidato» deve avere una SEDE.
#        ⛔ Non e' `abilita`: quella dice se il TIMER e' acceso su questa
#        installazione, questa se il PULSANTE ha senso — i due timer di
#        fatturazione sono spenti oggi per un'altra ragione (SDI sospeso), e il
#        giorno in cui si accendono il pulsante deve restare spento. Il modello
#        ammette `abilita = true` su un comando lungo: si progetta su quello.
#        ⛔ E non e' una lista di esclusioni in Python: sarebbe la seconda sede
#        della whitelist, quella che resta indietro alla prima sveglia nuova.
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
BACKEND_DIR = Path(__file__).resolve().parents[3]
DEPLOY_DIR = BACKEND_DIR / "deploy"
TEMPLATE_DIR = DEPLOY_DIR / "systemd"
_PERCORSO_SVEGLIE = DEPLOY_DIR / "sveglie.json"
# Il wrapper che systemd esegue (`ExecStart=… run-command.sh __COMANDO__`) ed
# e' lo STESSO che «Esegui ora» lancia come sottoprocesso: carica `env.sh` e
# chiama `manage.py` col venv giusto. Sta qui perche' la sua posizione e' un
# fatto del layout, e il layout si calcola una volta.
RUN_COMMAND = BACKEND_DIR / "bin" / "run-command.sh"

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

# I token di `comando` finiscono in DUE posti che li leggono in modo diverso:
# la riga `ExecStart=` dell'unit (systemd la spezza sugli spazi, espande `%x`
# come specifier e `$VAR` dall'ambiente) e l'argv di un `subprocess` (che passa
# ogni token intero). ⛔ Un token con uno spazio darebbe due esecuzioni DIVERSE
# dello «stesso» comando; uno con `%` o `$` una riga che systemd riscrive. E
# l'installer li interpola con `sed`, dove `|`, `&` e `\` hanno un significato.
# ⇒ Whitelist stretta, e si allarga quando un comando VERO ne ha bisogno: un
#    cancello che boccia un carattere di troppo si vede in CI, uno che ne lascia
#    passare uno di meno si vede sull'host. Il primo token e' il nome di un
#    management command Django (`test_sveglie.py` prova che esista).
_COMANDO_AMMESSO = re.compile(r"^[a-z][a-z0-9_]*$")
_ARGOMENTO_AMMESSO = re.compile(r"^-{0,2}[A-Za-z0-9][A-Za-z0-9._:/=-]*$")


# Scopo: una sveglia dichiarata — l'unit systemd che fa partire un processo.
# ⚠️ La chiave e' `unit`, NON `processo_codice`: un processo puo' avere piu'
#    sveglie (`run_fatturazione_batch` ne ha due, una per corsia). Chiavare sul
#    processo avrebbe fatto sparire una delle due in silenzio.
@dataclass(frozen=True)
class Sveglia:
    unit: str
    processo_codice: str
    forma: str
    # L'argv dopo `bin/run-command.sh`: `("digest_presidi", "--cadenza",
    # "settimanale")`. E' la riga resa nell'`ExecStart` del template, ed e' la
    # riga che «Esegui ora» lancera' come sottoprocesso — la stessa, per
    # costruzione.
    comando: tuple[str, ...]
    oncalendar: str | None
    abilita: bool
    # «Esegui ora» ha senso su questa sveglia? Dichiarato, non dedotto: un
    # timer puo' essere acceso (`abilita`) e non candidato (comando lungo), o
    # candidato e spento su questa installazione. Vedi header.
    avvio_manuale: bool
    nota: str

    # Scopo: vero se questa sveglia e' un timer con una cadenza dichiarata.
    @property
    def e_timer(self) -> bool:
        return self.forma == FORMA_TIMER


# Scopo: legge e valida il `comando` di una voce: una lista NON vuota di token,
#        il primo un nome di management command, gli altri argomenti senza
#        spazi ne' metacaratteri (vedi `_ARGOMENTO_AMMESSO`).
# ⛔ Obbligatorio per OGNI forma, non solo per i timer: anche un servizio sempre
#    acceso ha un `ExecStart`, e una regola con un'eccezione sono due regole.
#    Che «Esegui ora» valga solo per i timer lo decide chi rende il pulsante,
#    sulla `forma` — non questo file.
# ⛔ Una LISTA, mai una stringa: una stringa andrebbe spezzata sugli spazi, e
#    «come si spezza» sarebbe una regola scritta due volte (qui e in systemd).
def _leggi_comando(unit: str, grezzo: object) -> tuple[str, ...]:
    if not isinstance(grezzo, list) or not grezzo:
        raise ValueError(
            f"{_PERCORSO_SVEGLIE}: {unit}: 'comando' e' obbligatorio ed e' una lista "
            f"di token non vuota (l'argv dopo bin/run-command.sh)"
        )
    token = [str(x) for x in grezzo]
    if not _COMANDO_AMMESSO.match(token[0]):
        raise ValueError(
            f"{_PERCORSO_SVEGLIE}: {unit}: il primo token di 'comando' dev'essere "
            f"il nome di un management command (minuscole, cifre, underscore): "
            f"{token[0]!r}"
        )
    for arg in token[1:]:
        if not _ARGOMENTO_AMMESSO.match(arg):
            raise ValueError(
                f"{_PERCORSO_SVEGLIE}: {unit}: argomento di 'comando' non ammesso: "
                f"{arg!r} (niente spazi, quote, %, $, |, & — systemd e "
                f"subprocess lo leggerebbero in due modi diversi)"
            )
    return tuple(token)


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

        comando = _leggi_comando(unit, riga.get("comando"))

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

        # ⛔ `avvio_manuale` SI DICHIARA, per la stessa ragione di `abilita`: con
        #    un default a `false` una sveglia nuova non avrebbe mai il pulsante
        #    senza che nessuno l'abbia deciso; con un default a `true` un
        #    comando lungo lo avrebbe. Nessuno dei due silenzi e' una decisione.
        #    ⚠️ Obbligatorio anche su `forma = servizio`, dove vale `false` per
        #    natura: una regola con un'eccezione sono due regole (come per
        #    `comando`), e il pulsante lo decide comunque chi lo rende, sulla
        #    `forma`.
        if "avvio_manuale" not in riga or not isinstance(riga["avvio_manuale"], bool):
            raise ValueError(
                f"{_PERCORSO_SVEGLIE}: {unit}: 'avvio_manuale' è obbligatorio e "
                f"dev'essere true o false (e' «Esegui ora» un gesto sensato su "
                f"questa sveglia?)"
            )
        if forma == FORMA_SERVIZIO and riga["avvio_manuale"]:
            raise ValueError(
                f"{_PERCORSO_SVEGLIE}: {unit}: un servizio sempre acceso non si "
                f"avvia a mano (non c'e' una corsa da lanciare): 'avvio_manuale' "
                f"dev'essere false"
            )

        sveglie.append(Sveglia(
            unit=unit,
            processo_codice=processo,
            forma=forma,
            comando=comando,
            oncalendar=str(oncalendar) if oncalendar else None,
            # Già validato bool qui sopra: un `bool(...)` in più direbbe che il
            # valore può non esserlo, cioè il contrario di quanto appena imposto.
            abilita=riga["abilita"],
            avvio_manuale=riga["avvio_manuale"],
            nota=str(riga.get("nota") or ""),
        ))

    return tuple(sveglie)


# Scopo: le sveglie dichiarate per un processo (zero, una o piu').
def sveglie_di_processo(processo_codice: str) -> tuple[Sveglia, ...]:
    return tuple(s for s in carica_sveglie() if s.processo_codice == processo_codice)


# Scopo: la sveglia `unit` FRA QUELLE DEL PROCESSO, o None. E' la risoluzione
#        con cui «Esegui ora» traduce cio' che il client manda (un codice
#        processo e una unit) nel dichiarato: il verbo la usa per rifiutare
#        PRIMA di accodare, l'handler per rifiutare PRIMA di lanciare.
# ⛔ La coppia si guarda INSIEME: cercare la unit da sola risolverebbe anche
#    una sveglia di un altro processo, e il lavoro si registrerebbe sotto il
#    processo sbagliato senza che niente fallisca.
def sveglia_di_processo(processo_codice: str, unit: str) -> Sveglia | None:
    for sveglia in sveglie_di_processo(processo_codice):
        if sveglia.unit == unit:
            return sveglia
    return None
