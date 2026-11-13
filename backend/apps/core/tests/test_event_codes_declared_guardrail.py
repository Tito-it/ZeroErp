# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: IL RUBINETTO DEI CODICI EVENTO — ogni `event_code` che il backend
#        scrive sul giornale `vendite.event_log` deve essere dichiarato nel
#        catalogo `config.eventi_dominio`. Consegna **BE-9** del brief
#        `brief-db-event-log-scope-e-riga-parlante.md` §5.
#
#        PERCHE' UN CANCELLO E NON UNA FK (decisione D-18, imposta dalla D-12).
#        La mossa ovvia sarebbe una FK su `event_code`. Sarebbe sbagliata: una
#        scrittura rifiutata perche' il codice non e' ancora a catalogo e' **il
#        diario che smette di scrivere per un problema di configurazione** —
#        cioe' esattamente cio' che la D-12 vieta. Il diario rifiuta solo
#        quando non sa dire *di chi e'* la riga; un codice ignoto non glielo
#        impedisce. Il codice ignoto entra, e a protestare e' la **BUILD**.
#
#        ⛔ E QUESTO CANCELLO NON POTEVA ESSERE IL GEMELLO DI QUELLO DEI CODICI
#        ERRORE, che legge `pg_proc`:
#
#          | | chi scrive il codice | dove si guarda |
#          | errore | il DATABASE, in PL/pgSQL | `pg_proc`: c'e' la sorgente |
#          | evento | il BACKEND, in Python    | ⛔ in `pg_proc` niente |
#
#        Una vista su `pg_proc` per i codici evento tornerebbe **vuota per
#        sempre**: il peggior tipo di presidio, quello che dice sempre «tutto a
#        posto» perche' guarda nel posto sbagliato. La misura sta qui, dove i
#        codici sono scritti.
#
#        ⭐ E LA SORGENTE DEL CATALOGO E' IL CSV IN GIT, NON IL DATABASE — a
#        differenza del cancello del terzo lato, che ha bisogno di un DB vero e
#        di `ZEROERP_TEST_DB_E2E=1`. Due ragioni:
#          1. il CSV *e'* la sede dichiarata dei dati di `80_data` (AGENTS.md:
#             «i dati di 80_data si cambiano dal CSV, non con UPDATE diretti»),
#             quindi e' la verita', non una copia;
#          2. cosi' il cancello gira **sempre**, anche senza database — e un
#             presidio che gira solo quando c'e' l'ambiente giusto e' un
#             presidio che un giorno non gira.
#
#        ⚠️ IL COMPLEMENTARE STA LATO DB e fa un altro lavoro:
#        `dbops.vw_eventi_non_dichiarati` elenca i codici GIA' FINITI nel
#        registro senza essere dichiarati — la deriva che nessun controllo sul
#        sorgente vede (un codice costruito a runtime, o scritto da qualcosa
#        che non e' il backend). E' data-dependent e su un ambiente senza
#        traffico e' cieca: e' una spia da guardare, non un semaforo che ferma.
# ------------------------------------------------------------

"""Indice test previsti.

 1) test_ogni_codice_evento_usato_e_dichiarato
       il rubinetto: un `event_code` scritto dal backend e assente dal
       catalogo fa fallire la build.
 2) test_nessun_codice_evento_usato_e_obsoleto
       il verso gemello di quello dei codici errore: un codice che il catalogo
       ha deprecato con `obsoleto_dal` non deve comparire in un punto di
       scrittura.
 3) test_ogni_entity_type_usato_e_GIORNALABILE
       ⭐ l'altra colonna a catalogo, e il buco piu' facile: un refuso in
       `entity_type` passa OGNI cancello e fallisce solo a runtime. Non basta
       «esiste nel catalogo»: deve avere un modo di risoluzione dell'emittente.
 4) test_la_misura_non_e_degradata
       sanity: cataloghi e punti di scrittura non vuoti. Senza, un'estrazione
       che si rompe rende il cancello silenziosamente verde — che e'
       l'etichetta rassicurante peggiore di un presidio assente.
"""

from __future__ import annotations

import ast
from unittest import TestCase

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.tests._repo import repo_root
from apps.core.tests._seed_csv import SEED_DIR, seed_csv

_BACKEND = repo_root() / "backend"
_APPS = _BACKEND / "apps"
_SEED = SEED_DIR / "config"
_CATALOGO = _SEED / "eventi_dominio.csv"
_CATALOGO_TIPI = _SEED / "tipi_entita.csv"

# Il kwarg che veicola un codice evento verso il giornale. Uno solo, ed e' il
# nome del parametro di `EventLogRepositoryMixin.log_event`: se un giorno
# cambiasse, il test 3 se ne accorge (l'estrazione tornerebbe vuota).
_CODE_KWARG = "event_code"

# Il kwarg del TIPO DI ENTITA'. Stessa provenienza: e' il parametro di
# `EventLogRepositoryMixin.log_event`.
_TIPO_KWARG = "entity_type"

# Codici ammessi pur non essendo a catalogo. Vuota per scelta: ogni voce
# andrebbe motivata in una riga, altrimenti il cancello diventa un elenco di
# deroghe — la forma in cui questi registri non calano mai.
_ALLOWLIST: dict[str, str] = {}


# Scopo: il catalogo dei codici evento, letto dal CSV di `80_data`.
#        Ritorna {codice: obsoleto_dal}, `None` dove il seed dice NULL.
def _catalogo() -> dict[str, str | None]:
    return {
        riga["codice"]: riga["obsoleto_dal"]
        for riga in seed_csv(_CATALOGO)
        if riga["codice"]
    }


# Scopo: il catalogo dei tipi di entita', letto dal CSV di `80_data`.
#        Ritorna {codice: modo_risoluzione_emittente_grezzo}.
#
# ⭐ La colonna `modo_risoluzione_emittente` NON e' un dettaglio: e' cio' che
#    distingue le DUE LETTURE dello stesso catalogo. Il *bersaglio* di un errore
#    puo' puntare a qualunque tipo; il *giornale* accetta solo quelli da cui
#    l'emittente si sa derivare. `TASK_RUN` sta a catalogo col modo a NULL, ed e'
#    il caso che dimostra la differenza: scriverlo in `event_log` viene
#    rifiutato dal trigger — che e' esattamente il difetto da cui si viene.
#
# ⛔ La cella del modo vale il LETTERALE "NULL" del loader Liquibase, che per
#    Python e' una stringa piena, quindi verissima: letto a mano, `TASK_RUN`
#    (modo = NULL) risultava GIORNALABILE e il cancello lo avrebbe lasciato
#    passare (trovato dal test di sanity, non a occhio). Il BB `seed_csv` lo
#    da' `None`, come il caricatore: niente token scritto qui.
def _catalogo_tipi() -> dict[str, str | None]:
    return {
        riga["codice"]: riga["modo_risoluzione_emittente"]
        for riga in seed_csv(_CATALOGO_TIPI)
        if riga["codice"]
    }


# Scopo: costanti di modulo che valorizzano un codice evento
#        (`_EV_AVVIO = "PIPELINE_STARTED"`). Senza risolverle il cancello
#        perderebbe i punti di scrittura che le usano — ed e' la forma in cui
#        un codice si sfila senza che nessuno lo abbia nascosto apposta.
def _costanti_modulo(tree: ast.Module) -> dict[str, str]:
    costanti: dict[str, str] = {}
    for nodo in ast.walk(tree):
        if not isinstance(nodo, ast.Assign):
            continue
        valore = nodo.value
        if not (isinstance(valore, ast.Constant) and isinstance(valore.value, str)):
            continue
        for target in nodo.targets:
            if isinstance(target, ast.Name):
                costanti[target.id] = valore.value
    return costanti


# Scopo: tutti i codici evento passati a un punto di scrittura, con file e riga
#        del primo uso. La posizione non e' decorativa: un elenco di codici
#        senza posizione non e' azionabile, e un cancello non azionabile viene
#        spento.
def _codici_usati(kwarg: str = _CODE_KWARG) -> dict[str, str]:
    usati: dict[str, str] = {}
    for file in sorted(_APPS.rglob("*.py")):
        if "/tests/" in file.as_posix() or file.name.startswith("test_"):
            continue
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover — non parsabile: non e' compito nostro
            continue
        costanti = _costanti_modulo(tree)
        for nodo in ast.walk(tree):
            if not isinstance(nodo, ast.Call):
                continue
            for kw in nodo.keywords:
                if kw.arg != kwarg:
                    continue
                codice = None
                if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    codice = kw.value.value
                elif isinstance(kw.value, ast.Name):
                    codice = costanti.get(kw.value.id)
                if codice:
                    posizione = f"{file.relative_to(_BACKEND)}:{nodo.lineno}"
                    usati.setdefault(codice, posizione)
    return usati


class EventCodesDeclaredGuardrail(TestCase):
    # Scopo: il rubinetto. Un codice evento scritto dal backend e assente da
    #        `config.eventi_dominio` fa fallire la build — non la scrittura.
    def test_ogni_codice_evento_usato_e_dichiarato(self):
        catalogo = _catalogo()
        mancanti = {
            codice: posizione
            for codice, posizione in _codici_usati().items()
            if codice not in catalogo and codice not in _ALLOWLIST
        }
        if mancanti:
            righe = "\n".join(f"  - {c}  ({p})" for c, p in sorted(mancanti.items()))
            self.fail(
                f"{len(mancanti)} codici evento scritti dal backend non sono "
                f"dichiarati nel catalogo:\n{righe}\n\n"
                f"Aggiungerli in {_CATALOGO.name} (codice, dominio, "
                "etichetta_key, obsoleto_dal, note) e chiedere al team DB di "
                "riapplicare il mirror del seed. ⚠️ Il `dominio` e' una "
                "PROPRIETA' del codice, non un secondo asse: un codice "
                "appartiene a un dominio solo. ⛔ Non si aggiunge una voce in "
                "_ALLOWLIST: un codice che nessuno ha dichiarato e' un codice "
                "che nessuno sa leggere."
            )

    # Scopo: il verso gemello di quello dei codici errore. Un codice deprecato
    #        con `obsoleto_dal` non deve comparire in un punto di scrittura:
    #        chi lo usa oggi sta scrivendo righe NUOVE sotto un nome che il
    #        catalogo ha dichiarato superato.
    def test_nessun_codice_evento_usato_e_obsoleto(self):
        oggi = oggi_aziendale().isoformat()
        obsoleti = {
            codice
            for codice, obsoleto_dal in _catalogo().items()
            # Confronto lessicografico su ISO-8601, che ordina come le date.
            if obsoleto_dal is not None and obsoleto_dal <= oggi
        }
        usati_obsoleti = {
            codice: posizione
            for codice, posizione in _codici_usati().items()
            if codice in obsoleti and codice not in _ALLOWLIST
        }
        if usati_obsoleti:
            righe = "\n".join(
                f"  - {c}  ({p})" for c, p in sorted(usati_obsoleti.items())
            )
            self.fail(
                f"{len(usati_obsoleti)} codici evento OBSOLETI sono ancora "
                f"scritti dal backend:\n{righe}\n\n"
                "Sostituirli col codice che li ha rimpiazzati, oppure — se la "
                "deprecazione era prematura — riaprirli nel catalogo."
            )

    # Scopo: ⭐ IL TIPO DI ENTITA' DEVE ESSERE GIORNALABILE, non solo esistere.
    #
    #        E' il buco piu' facile del giro: `entity_type` e' una stringa che
    #        nessun cancello guardava. Un refuso — «LOTTTO» — passa i test, passa
    #        la CI, e fallisce alla prima scrittura vera con
    #        `E_EVENT_LOG_ENTITY_TYPE_IGNOTO`; in un ramo d'errore (dove il
    #        diario tipicamente scrive) lo si scopre mesi dopo, che e' la storia
    #        di BE-1.
    #
    # ⚠️ E il criterio NON e' «esiste nel catalogo», ma «esiste **e ha un modo**»:
    #    `TASK_RUN` e' a catalogo e il giornale lo rifiuta lo stesso. Un
    #    controllo di sola esistenza avrebbe lasciato passare proprio la riga
    #    che la D-3 ha espulso da `event_log`.
    def test_ogni_entity_type_usato_e_giornalabile(self):
        tipi = _catalogo_tipi()
        usati = _codici_usati(_TIPO_KWARG)

        ignoti = {t: p for t, p in usati.items() if t not in tipi}
        senza_modo = {
            t: p for t, p in usati.items() if t in tipi and not tipi[t]
        }
        if ignoti or senza_modo:
            righe = "\n".join(
                [f"  - {t}  ({p})  → non e' a catalogo" for t, p in sorted(ignoti.items())]
                + [
                    f"  - {t}  ({p})  → a catalogo ma SENZA modo di risoluzione: "
                    "il giornale lo rifiuta"
                    for t, p in sorted(senza_modo.items())
                ]
            )
            self.fail(
                f"{len(ignoti) + len(senza_modo)} `entity_type` scritti dal "
                f"backend che il giornale non accetta:\n{righe}\n\n"
                f"I tipi giornalabili sono: "
                f"{', '.join(sorted(t for t, m in tipi.items() if m))}. "
                f"Un tipo nuovo si aggiunge in {_CATALOGO_TIPI.name} CON il suo "
                "`modo_risoluzione_emittente`, e il modo va insegnato a "
                "`script.fn_resolve_emittente_sr_id` (team DB)."
            )

    # Scopo: sanity. Se l'estrazione si rompe (kwarg rinominato, CSV spostato)
    #        i due test sopra diventano verdi per SOTTRAZIONE: passano
    #        smettendo di verificare, che e' indistinguibile da un verde vero
    #        se ci si ferma all'esito.
    def test_la_misura_non_e_degradata(self):
        self.assertTrue(
            _CATALOGO.is_file(), f"catalogo dei codici evento non trovato: {_CATALOGO}"
        )
        self.assertGreaterEqual(
            len(_catalogo()), 5, "catalogo sospetto: estrazione dal CSV fallita"
        )
        self.assertGreaterEqual(
            len(_codici_usati()),
            4,
            "nessun punto di scrittura trovato: l'estrazione AST non misura "
            f"piu' niente (kwarg '{_CODE_KWARG}' rinominato?)",
        )
        self.assertTrue(
            _CATALOGO_TIPI.is_file(),
            f"catalogo dei tipi di entita' non trovato: {_CATALOGO_TIPI}",
        )
        # ⚠️ Almeno un tipo giornalabile: se la colonna del modo sparisse o
        #    cambiasse nome, il test 3 diventerebbe verde per sottrazione —
        #    «nessun tipo ha un modo» e quindi «nessun uso e' valido» sarebbe
        #    un rosso, ma «la colonna non esiste» darebbe stringhe vuote ovunque.
        self.assertTrue(
            any(_catalogo_tipi().values()),
            "nessun tipo giornalabile: la colonna `modo_risoluzione_emittente` "
            "non si sta leggendo",
        )
        self.assertGreaterEqual(
            len(_codici_usati(_TIPO_KWARG)),
            2,
            f"nessun `{_TIPO_KWARG}` trovato: estrazione degradata",
        )
