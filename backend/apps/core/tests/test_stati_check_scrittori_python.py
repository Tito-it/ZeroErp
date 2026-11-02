# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LA META' PYTHON DEL PRESIDIO C1 («uno stato previsto dal modello e
#        mai scritto»). Il database classifica ogni valore ammesso da un CHECK
#        di stato con `dbops.vw_stati_check_scrittori`; i valori che scrive un
#        repository Python il database non li puo' vedere, e stanno nel registro
#        `dbops.stati_check_dichiarazioni` con `canale = APPLICAZIONE`. Questo
#        test e' chi VERIFICA quella dichiarazione — senza di lui e' un'esenzione
#        permanente scritta in un CSV. Risposta alla richiesta §6 di
#        `docs/it/dev/work-done/brief-db-presidio-stati-mai-scritti.md`, ed e'
#        il gemello di `db/pgtap/dbops/test-stati-check-scrittori-v1.sql`.
#
#        UNA SEDE SOLA PER LA CLASSIFICAZIONE (guida presidi §6.3). Qui non si
#        rifa' la misura del DB: la si LEGGE dalla vista, sul database provvisto
#        (`richiedi_db_provvisto`). Se questo file rifacesse il giro su
#        `pg_constraint` a modo suo, i due lati risponderebbero cose diverse
#        sullo stesso valore — e' il difetto che la prima misura del brief ha
#        gia' pagato (18 colonne contro 32, per una regex che vedeva un solo
#        cast).
#
#        ⚠️ RICHIEDE IL DB VERO, stessa opt-in `ZEROERP_TEST_DB_E2E=1` del
#        cancello del terzo lato (accesa in CI da `ci-validate.yaml`). Non
#        scrive nulla: legge la vista e i sorgenti Python.
# ------------------------------------------------------------

"""Indice test previsti (tutti opt-in `ZEROERP_TEST_DB_E2E=1`).

 1) test_ogni_dichiarazione_applicazione_ha_uno_scrittore_python
       verso 1, IL VERSO DI RITIRO CHE IL DB NON PUO' FARE — ogni riga
       `DICHIARATO_APPLICAZIONE` deve avere almeno un `.py` non di test che
       la scrive secondo il criterio sotto. Rosso su una dichiarazione che
       nessun file soddisfa piu'.
 2) test_nessun_non_dichiarato_e_scritto_da_python
       verso 2, IL VERSO PERMISSIVO — una riga `NON_DICHIARATO` che un `.py`
       soddisfa e' una dichiarazione MANCANTE: rosso, con l'istruzione di
       dichiararla `APPLICAZIONE` nel CSV del registro.
 3) test_la_misura_non_e_degradata
       sanity — la vista risponde, il registro ha righe `APPLICAZIONE`, i
       sorgenti sono stati letti. Senza, i due versi sopra sarebbero verdi
       per sottrazione.

IL CRITERIO, ed e' scritto qui perche' un verde va letto sapendo cosa copre.
Un valore e' «scritto da Python» se esiste un `.py` non di test (commenti e
docstring esclusi) che contiene il LETTERALE (`'FATTO'` o `"FATTO"`) e:

  * DIRETTO — nomina la tabella (`nome_tabella` come parola) oppure una delle
    funzioni DB che la scrivono (`scrittori_tabella`, senza schema); oppure
  * INDIRETTO, il SECONDO SALTO — nomina un simbolo (`def`/`class`) definito
    in un file «scrittore» del punto sopra, e in NESSUN file che scrittore non
    e'. E' la forma di `scrittori_indiretti` nella vista del DB: la funzione
    che chiama uno scrittore passandogli il valore.

⭐ PERCHE' IL SECONDO SALTO NON E' UN ALLARGAMENTO DI COMODO. Il §6 del brief
   chiedeva letterale e tabella «nello stesso file», e misurato il 2026-09-21
   quel criterio dava ROSSO su 8 righe su 26 — tutte della stessa forma: il
   letterale nel SERVICE (`update_outbox_stato(outbox_id, "READY")`,
   `severity="ERROR"`, `STATI_DOCUMENTO_INTERNO`), la tabella nel REPOSITORY
   (o in `famiglie.py`, o in un mixin). Non e' un'eccezione: e' l'architettura
   a tre layer di `api.md` — il service decide il valore, il repository scrive
   la tabella — quindi un criterio a un file solo boccia la forma CORRETTA del
   codice. Il salto e' sul modello, non sulle sette righe.

⛔ E il legame «nomina un simbolo» senza il vincolo di unicita' e' RUMORE:
   `get`, `post`, `list` sono definiti ovunque, e con quelli il criterio
   accendeva 4 righe `ESENTE` (2026-09-21). Con «definito SOLO in file
   scrittori» le quattro spariscono e le 26 restano.

⚠️ LIMITI DICHIARATI (gli stessi della vista, sul lato Python):
   a) nominare non e' scrivere: un letterale in un `WHERE` di un repository
      che scrive quella tabella conta come scrittura;
   b) due salti e non tre: un valore che passa per tre file resta invisibile;
   c) un valore che arriva da una VARIABILE di un altro file (non un letterale
      nel chiamante) non si vede.
   Un caso invisibile si dichiara `ESENTE` con la ragione, come a DB.
"""

from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path
from unittest import TestCase

from apps.core.tests._repo import repo_root, sorgente_senza_commenti
from apps.core.tests.db_e2e import richiedi_db_provvisto

# La misura canonica, lato DB. Il registro (`dbops.stati_check_dichiarazioni`)
# non si legge direttamente: la vista lo ha gia' incrociato e ne espone il
# `canale` e la `ragione` — leggerlo a parte sarebbe una seconda lettura.
_VISTA = "dbops.vw_stati_check_scrittori"
_CSV_REGISTRO = "db/changelog/migrations_v2/80_data/sql/dbops/stati_check_dichiarazioni.csv"

_RADICE_APPS = "backend/apps"


# Scopo: il sorgente senza le DOCSTRING (modulo, classe, funzione). Ai commenti
#        `#`/`--` pensa `sorgente_senza_commenti`; le docstring sono prosa
#        uguale, e questo presidio si e' acceso su una: `commesse_source_handlers`
#        nomina `attivita_consumi` solo nella docstring di `HandlerConsumi`, e
#        con quella riga era «scrittore» di una tabella che non tocca —
#        accendendo un falso positivo su un valore `ESENTE` (2026-09-21).
# ⚠️ Si azzerano le RIGHE della docstring, non si tocca il resto: cosi' i
#    numeri di riga restano quelli del file, utile a chi legge un rosso.
def _senza_docstring(testo: str, tree: ast.Module) -> str:
    righe = testo.split("\n")
    for nodo in ast.walk(tree):
        if not isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not nodo.body:
            continue
        primo = nodo.body[0]
        if (
            isinstance(primo, ast.Expr)
            and isinstance(primo.value, ast.Constant)
            and isinstance(primo.value.value, str)
            and primo.end_lineno is not None
        ):
            for i in range(primo.lineno - 1, primo.end_lineno):
                righe[i] = ""
    return "\n".join(righe)


class _Sorgenti:
    """I `.py` non di test di `backend/apps`, letti UNA volta per la classe.

    `testo[file]` e' il sorgente senza commenti ne' docstring; `simboli[file]`
    i nomi di `def`/`class` che il file definisce; `definiti_in[nome]` i file
    che definiscono quel nome — serve al vincolo di unicita' del secondo salto.
    """

    # Scopo: legge e indicizza tutti i sorgenti applicativi.
    def __init__(self, radice: Path) -> None:
        self.testo: dict[str, str] = {}
        self.simboli: dict[str, set[str]] = {}
        self.definiti_in: dict[str, set[str]] = defaultdict(set)
        for percorso in sorted(radice.rglob("*.py")):
            posix = percorso.as_posix()
            if "/tests/" in posix or percorso.name.startswith("test_"):
                continue
            rel = percorso.relative_to(radice.parent).as_posix()
            grezzo = percorso.read_text(encoding="utf-8")
            tree = ast.parse(grezzo)
            self.testo[rel] = sorgente_senza_commenti(_senza_docstring(grezzo, tree))
            nomi = {
                nodo.name
                for nodo in ast.walk(tree)
                if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and not nodo.name.startswith("__")
            }
            self.simboli[rel] = nomi
            for nome in nomi:
                self.definiti_in[nome].add(rel)


# Scopo: regex «una di queste parole intere».
def _parole(nomi: set[str]) -> re.Pattern[str]:
    return re.compile(r"\b(" + "|".join(re.escape(n) for n in sorted(nomi)) + r")\b")


# Scopo: i file Python che scrivono `valore` sulla tabella, secondo il criterio
#        in testa al file. Ritorna (diretti, indiretti), entrambi ordinati.
def _scrittori_python(
    sorgenti: _Sorgenti, nome_tabella: str, valore: str, scrittori_db: str | None
) -> tuple[list[str], list[str]]:
    # I nomi che fanno di un file uno «scrittore»: la tabella, e le funzioni DB
    # che la scrivono (`vendite.fn_log_event` -> `fn_log_event`).
    nomi_scrittori = {nome_tabella} | {
        fn.split(".")[-1] for fn in (scrittori_db or "").split(", ") if fn
    }
    rx_scrittori = _parole(nomi_scrittori)
    file_scrittori = {f for f, t in sorgenti.testo.items() if rx_scrittori.search(t)}

    rx_letterale = re.compile(r"(['\"])" + re.escape(valore) + r"\1")
    con_letterale = {f for f, t in sorgenti.testo.items() if rx_letterale.search(t)}

    diretti = sorted(con_letterale & file_scrittori)

    # Secondo salto: i simboli definiti SOLO in file scrittori. Un nome definito
    # anche altrove (`get`, `post`) non lega niente.
    simboli = {
        s
        for f in file_scrittori
        for s in sorgenti.simboli[f]
        if sorgenti.definiti_in[s] <= file_scrittori
    }
    indiretti: list[str] = []
    if simboli:
        rx_simboli = _parole(simboli)
        indiretti = sorted(
            f for f in con_letterale - file_scrittori if rx_simboli.search(sorgenti.testo[f])
        )
    return diretti, indiretti


class StatiCheckScrittoriPythonTests(TestCase):
    """La meta' Python del presidio C1: verifica le righe `APPLICAZIONE`.

    ⚠️ Salta se lo schema non c'e', FALLISCE se c'e' ma manca la vista — la
    stessa distinzione di `test_error_codes_db_policy_guardrail`: un database
    usa-e-getta e' una condizione d'ambiente; schema Liquibase presente e
    presidio assente e' un difetto (changeSet `20260921-16` non applicato).
    """

    righe: list[dict]
    sorgenti: _Sorgenti

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("SELECT to_regclass(%s) IS NOT NULL", [_VISTA])
            row = cur.fetchone()
            assert row is not None
            if not row[0]:
                raise AssertionError(
                    f"schema Liquibase presente ma la misura del presidio C1 no: "
                    f"{_VISTA} MANCANTE. Applicare il changeSet 20260921-16 "
                    "(brief-db-presidio-stati-mai-scritti §3-ter.4)."
                )
            cur.execute(
                f"SELECT esito, schema_tabella, nome_tabella, colonna, valore, "
                f"scrittori_tabella, ragione FROM {_VISTA}"
            )
            colonne = [c[0] for c in cur.description]
            cls.righe = [dict(zip(colonne, r, strict=True)) for r in cur.fetchall()]

        cls.sorgenti = _Sorgenti(repo_root() / _RADICE_APPS)

    # Scopo: etichetta leggibile di una riga della vista.
    @staticmethod
    def _chiave(r: dict) -> str:
        return f"{r['schema_tabella']}.{r['nome_tabella']}.{r['colonna']} = '{r['valore']}'"

    # Scopo: verso 1 — la dichiarazione deve essere ancora vera. Una riga
    #        `APPLICAZIONE` che nessun `.py` soddisfa piu' e' un valore che il
    #        DB non scrive (per costruzione: e' nel registro) e che il Python
    #        ha smesso di scrivere: e' tornato «mai scritto», e il registro lo
    #        copre. E' il verso di ritiro che il DB non puo' fare da solo.
    def test_ogni_dichiarazione_applicazione_ha_uno_scrittore_python(self):
        orfane: list[str] = []
        for r in self.righe:
            if r["esito"] != "DICHIARATO_APPLICAZIONE":
                continue
            diretti, indiretti = _scrittori_python(
                self.sorgenti, r["nome_tabella"], r["valore"], r["scrittori_tabella"]
            )
            if not diretti and not indiretti:
                orfane.append(f"  - {self._chiave(r)}\n      registro: {r['ragione']}")
        if orfane:
            self.fail(
                f"{len(orfane)} dichiarazioni APPLICAZIONE che nessun `.py` non di "
                f"test soddisfa piu' (letterale + tabella/scrittore, anche al "
                f"secondo salto):\n" + "\n".join(orfane) + "\n\n"
                "O il valore e' davvero tornato «mai scritto» — allora e' un C1 "
                "vero: si scrive chi lo scrive, o si riclassifica ESENTE con la "
                f"ragione in {_CSV_REGISTRO} — oppure il criterio di questo test "
                "non vede piu' il punto che lo scrive (limiti in testa al file): "
                "si guarda il codice, non si allarga il criterio per far tacere "
                "il rosso."
            )

    # Scopo: verso 2 — il verso permissivo. Una riga `NON_DICHIARATO` e' gia'
    #        rossa nel pgTAP; ma se un `.py` la soddisfa, la risposta giusta
    #        NON e' «scrivere uno scrittore a DB»: e' dichiararla APPLICAZIONE,
    #        perche' lo scrittore c'e' ed e' Python. Senza questo verso il
    #        registro potrebbe calare di nascosto nel verso sbagliato
    #        (dichiarando ESENTE cio' che l'applicazione scrive).
    def test_nessun_non_dichiarato_e_scritto_da_python(self):
        da_dichiarare: list[str] = []
        for r in self.righe:
            if r["esito"] != "NON_DICHIARATO":
                continue
            diretti, indiretti = _scrittori_python(
                self.sorgenti, r["nome_tabella"], r["valore"], r["scrittori_tabella"]
            )
            if diretti or indiretti:
                da_dichiarare.append(
                    f"  - {self._chiave(r)}  <- {', '.join(diretti or indiretti)}"
                )
        if da_dichiarare:
            self.fail(
                f"{len(da_dichiarare)} valori NON_DICHIARATO che un `.py` non di "
                f"test scrive:\n" + "\n".join(da_dichiarare) + "\n\n"
                f"Dichiarali `APPLICAZIONE` in {_CSV_REGISTRO} (canale "
                "APPLICAZIONE, ragione con il file che li scrive) e chiedi al "
                "team DB di riapplicare il changeSet 20260921-19. Non ESENTE: "
                "ESENTE dice «nessuno lo scrive», e qui lo scrive l'applicazione."
            )

    # Scopo: sanity della misura. Una vista vuota, un registro senza righe
    #        APPLICAZIONE o una scansione che non ha letto niente renderebbero
    #        i due versi sopra verdi per sottrazione.
    def test_la_misura_non_e_degradata(self):
        self.assertGreater(len(self.righe), 50, f"{_VISTA} sospetta: la misura sembra degradata")
        applicazione = [r for r in self.righe if r["esito"] == "DICHIARATO_APPLICAZIONE"]
        self.assertGreater(
            len(applicazione), 0,
            "nessuna riga DICHIARATO_APPLICAZIONE: o il registro e' vuoto o la "
            "vista non lo incrocia piu' — in entrambi i casi il verso 1 non "
            "presidia niente",
        )
        self.assertGreater(
            len(self.sorgenti.testo), 100,
            "scansione dei sorgenti sospetta: troppo pochi `.py` letti",
        )
        # I due strumenti del criterio devono funzionare su un caso costruito:
        # senza questa prova, una regex rotta farebbe passare il verso 2 e
        # bocciare tutto il verso 1 — e il secondo si vedrebbe, il primo no.
        self.assertEqual(
            _senza_docstring('def f():\n    """doc\n    string"""\n    return "X"\n',
                             ast.parse('def f():\n    """doc\n    string"""\n    return "X"\n')),
            'def f():\n\n\n    return "X"\n',
        )
