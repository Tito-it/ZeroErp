#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Guardrail CI — le forme che passano la lettura e muoiono all'apply
#
# COSA PRESIDIA. Tredici regole scritte nella documentazione e ricadute piu'
#   volte, ognuna con la sua sede. Hanno in comune che si vedono LEGGENDO il
#   file, senza database, e che la prova a mano spesso non le prende:
#
#   sqlcheck-booleano      una sqlCheck che attende t/f/true/false: Liquibase
#                          legge un boolean come t/f, e la condizione scritta
#                          «true» non e' mai soddisfatta (linee-guida-sql §11.13)
#   punto-e-virgola        un dollar-quote chiuso e subito dopo un'altra
#                          istruzione senza `;`: e' il corpo copiato dalla doc
#                          auto-generata, che finisce con `$function$` nudo
#                          (liquibase-setup-workflow §2)
#   begin-atomic-da-solo   un `BEGIN ATOMIC` che divide il suo `sql:` con
#                          un'altra istruzione: pgjdbc dopo l'END non spezza
#                          piu', e il server rifiuta i comandi multipli
#                          (linee-guida-sql §5c)
#   log-cinque-argomenti   `fn_log_and_raise_error` chiamata con cinque
#                          argomenti: la firma variadica non si risolve, il
#                          variadico vuoto va scritto (`VARIADIC ARRAY[]::text[]`)
#                          (Messaggi di Errore e Generazione Log)
#   unique-ignorato        `where:` su `addUniqueConstraint` (Liquibase lo
#                          ignora: nasce un vincolo totale) e un change dentro
#                          `columns:` di `addColumn` (non eseguito)
#                          (linee-guida-sql §11.12)
#   messaggi-segnaposto    nel CSV dei messaggi d'errore un `%` non seguito da
#                          `s` o `%`, o un `id` ripetuto: format() solleva 22023
#                          e l'errore di dominio sparisce (Messaggi di Errore)
#   csv-fine-riga-misti    un CSV di migrations_v2 con righe che finiscono in
#                          `\r\n` e righe in `\n`: e' l'append fatto con
#                          csv.writer (CRLF di default), e la verifica di §11.2
#                          (COPY in una temp table) muore su un «ritorno carrello
#                          non quotato» (linee-guida-sql §11.2)
#   jsonb-punto-di-domanda l'operatore jsonb `?` scritto nella forma che si
#                          rompe: singolo FUORI da un dollar-quote (JDBC lo prende
#                          per un segnaposto), raddoppiato DENTRO un corpo (resta
#                          `??`). La forma che vale ovunque e' jsonb_exists()
#                          (linee-guida-sql §11.12)
#   django-alla-create     in 00_schema/20_code, un riferimento a `django.*` che si
#                          risolve alla CREATE: un `%TYPE` su una colonna django,
#                          una funzione LANGUAGE sql o una vista che lo nomina, una
#                          FK verso django. Al CREATE lo schema puo' non esistere
#                          (linee-guida-sql §5g e §11.9)
#   type-perso             un parametro o una colonna di RETURNS TABLE che nella
#                          revisione precedente della STESSA funzione era ancorato
#                          con `%TYPE` e torna a un tipo nudo senza il commento che
#                          ne dice la ragione: e' il corpo ripreso dalla doc
#                          auto-generata, che scioglie i tipi (linee-guida-sql §5g)
#   id-senza-type          un parametro o una colonna di RETURNS TABLE di nome
#                          `*_id` con un tipo nudo e senza la ragione accanto: un
#                          id e' quasi sempre il riflesso di una colonna, e si
#                          ancora con `%TYPE` (linee-guida-sql §5g; Tid 2026-11-12:
#                          la regola intera resta alla revisione, il guardrail
#                          guarda gli id)
#   nullvalue-vuoto        un caricatore con `nullValue: ""` il cui CSV ha una
#                          cella vuota in una colonna dichiarata STRING e nullable
#                          nella tabella: Liquibase scrive '' dove si voleva NULL,
#                          e l'assenza ha due forme (linee-guida-sql §11.7). La
#                          nullabilita' si legge dalla doc auto-generata. Guarda
#                          tutti i caricatori, perche' un append a un CSV non fa
#                          nascere un changeSet nuovo; i casi noti stanno in
#                          NULLVALUE_DEBITO, che non tiene righe morte
#   pgtap-pgagent-owner    un pgTAP che legge `pgagent.*` senza
#                          `-- pgtap-runner: owner` nelle prime 80 righe: il
#                          runner lo esegue come applicazione, che sullo schema
#                          pgagent non ha USAGE (guida pgTAP)
#
# PERIMETRO. Le regole sui changelog guardano solo `changes`, mai `rollback`,
#   e un perimetro per regola: dalla storia intera quando la storia e' pulita,
#   da quando la regola e' presidiata quando un changelog mergiato la viola
#   (i file mergiati non si toccano). I CSV e i pgTAP si guardano tutti.
#
# ECCEZIONI: si DICHIARANO in testa al file (YAML, `#`; pgTAP, `--`):
#     # <regola>: ammesso — <perche', in chiaro>
#   e il cancello le stampa come debito dichiarato invece di fermarsi.
#
# ⚠️ COSA NON PRESIDIA: non e' un parser SQL. Riconosce commenti, letterali e
#   dollar-quote (scripts/_guardrail_comune.py) e cerca forme precise; un SQL
#   sbagliato in un altro modo lo vede solo il migrate.
#
# Uso (read-only, nessun database):
#   python scripts/guardrail_forme_changeset.py              # perimetro
#   python scripts/guardrail_forme_changeset.py --tutto      # storia intera, per misurare
#   python scripts/guardrail_forme_changeset.py <file>...    # solo questi (YAML, CSV o pgTAP)
# Exit 0 se pulito, 1 se trova una forma non dichiarata.
# ------------------------------------------------------------

from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path
from typing import Callable

import yaml

# ⭐ Lettura dei changelog e primitive lessicali in un posto solo.
import _guardrail_comune as gc

PGTAP = gc.ROOT / "db" / "pgtap"
MESSAGGI = gc.BASE / "80_data" / "sql" / "config" / "messaggi_errore.csv"

Violazione = tuple[str, str]   # (dove, estratto)


# ── Regole sui changeSet ────────────────────────────────────────────────


# Scopo: le sqlCheck di un nodo di preConditions, a qualunque profondita'
#        (and/or/not le annidano).
def _sql_check(nodo) -> list[dict]:
    fuori: list[dict] = []
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            if k == "sqlCheck" and isinstance(v, dict):
                fuori.append(v)
            else:
                fuori.extend(_sql_check(v))
    elif isinstance(nodo, list):
        for v in nodo:
            fuori.extend(_sql_check(v))
    return fuori


def sqlcheck_booleano(cs: dict, _percorso: Path) -> list[Violazione]:
    fuori = []
    for chk in _sql_check(cs.get("preConditions")):
        atteso = str(chk.get("expectedResult", "")).strip().lower()
        if atteso in ("t", "f", "true", "false"):
            fuori.append((f"preConditions, sqlCheck expectedResult «{chk.get('expectedResult')}»",
                          " ".join(str(chk.get("sql", "")).split())[:150]))
    return fuori


# Le parole che aprono un'istruzione nuova: dopo un dollar-quote chiuso, una di
# queste senza `;` in mezzo vuol dire che il `;` manca. `LANGUAGE`, `SET`,
# `IMMUTABLE`… dopo un corpo sono clausole della stessa istruzione, e non ci sono.
ISTRUZIONE_NUOVA_RE = re.compile(
    r"(COMMENT|GRANT|REVOKE|CREATE|ALTER|DROP|SELECT|DO|INSERT|UPDATE|DELETE|PERFORM)\b",
    re.IGNORECASE)


# Scopo: la posizione del primo carattere che non e' spazio ne' commento, da `i`.
def _salta_vuoto(sql: str, i: int) -> int:
    n = len(sql)
    while i < n:
        if sql[i].isspace():
            i += 1
        elif sql.startswith("--", i):
            fine = sql.find("\n", i)
            i = n if fine < 0 else fine
        elif sql.startswith("/*", i):
            i = gc.fine_commento_blocco(sql, i).pos
        else:
            break
    return i


def punto_e_virgola(cs: dict, _percorso: Path) -> list[Violazione]:
    fuori = []
    for _sezione, sql in gc.blocchi_sql(cs):
        for d in gc.dollar_di_primo_livello(sql):
            dopo = _salta_vuoto(sql, d.fine)
            m = ISTRUZIONE_NUOVA_RE.match(sql, dopo)
            if m:
                riga = sql.count("\n", 0, d.chiusura) + 1
                fuori.append((f"sql, riga ~{riga}: dopo il {d.tag} di chiusura comincia "
                              f"«{m.group(1)}» senza `;`",
                              sql[d.chiusura:dopo + 40].replace("\n", " ⏎ ")[:150]))
    return fuori


BEGIN_ATOMIC_RE = re.compile(r"\bBEGIN\s+ATOMIC\b", re.IGNORECASE)
CREATE_RE = re.compile(r"^CREATE\b", re.IGNORECASE)
END_FINALE_RE = re.compile(r"\bEND\s*;?\s*$", re.IGNORECASE)


def begin_atomic_da_solo(cs: dict, _percorso: Path) -> list[Violazione]:
    fuori = []
    for _sezione, sql in gc.blocchi_sql(cs):
        if not BEGIN_ATOMIC_RE.search(sql):
            continue
        testo = gc.spoglia(sql, prosa_dopo_is=True).strip()
        quanti = len(BEGIN_ATOMIC_RE.findall(testo))
        if not quanti:
            continue
        if quanti > 1 or not CREATE_RE.match(testo) or not END_FINALE_RE.search(testo):
            riga = testo.count("\n", 0, BEGIN_ATOMIC_RE.search(testo).start()) + 1
            fuori.append((f"sql, riga ~{riga}: il `sql:` con il BEGIN ATOMIC contiene "
                          "altre istruzioni", testo.split("\n", 1)[0][:150]))
    return fuori


CHIAMATA_LOG_RE = re.compile(r"\bfn_log_and_raise_error\s*\(", re.IGNORECASE)
FUNCTION_PRIMA_RE = re.compile(r"\bFUNCTION\s+(?:\w+\.)?$", re.IGNORECASE)


# Scopo: gli argomenti di primo livello della chiamata che apre in `i` (sulla
#        parentesi), in un testo gia' spogliato di commenti e letterali.
def _argomenti(testo: str, i: int) -> list[str]:
    profondita, inizio, fuori = 0, i + 1, []
    for j in range(i, len(testo)):
        c = testo[j]
        if c in "([":
            profondita += 1
        elif c in ")]":
            profondita -= 1
            if profondita == 0:
                fuori.append(testo[inizio:j])
                return fuori
        elif c == "," and profondita == 1:
            fuori.append(testo[inizio:j])
            inizio = j + 1
    return fuori


def log_cinque_argomenti(cs: dict, _percorso: Path) -> list[Violazione]:
    fuori = []
    for _sezione, sql in gc.blocchi_sql(cs):
        if not CHIAMATA_LOG_RE.search(sql):
            continue
        testo = gc.spoglia(sql, prosa_dopo_is=True)
        for m in CHIAMATA_LOG_RE.finditer(testo):
            # La firma della funzione stessa (CREATE/COMMENT/DROP FUNCTION …) non
            # e' una chiamata.
            if FUNCTION_PRIMA_RE.search(testo[max(0, m.start() - 40):m.start()]):
                continue
            argomenti = _argomenti(testo, m.end() - 1)
            if len(argomenti) == 5 and not any("VARIADIC" in a.upper() for a in argomenti):
                riga = testo.count("\n", 0, m.start()) + 1
                fuori.append((f"sql, riga ~{riga}: fn_log_and_raise_error con cinque argomenti",
                              " ".join(testo[m.start():m.start() + 150].split())))
    return fuori


def unique_ignorato(cs: dict, _percorso: Path) -> list[Violazione]:
    fuori = []
    for cambio in gc.cambi(cs):
        auc = cambio.get("addUniqueConstraint")
        if isinstance(auc, dict) and "where" in auc:
            fuori.append(("addUniqueConstraint con `where:`, che Liquibase ignora",
                          f"{auc.get('tableName')} ({auc.get('columnNames')}): where {auc.get('where')}"))
        ac = cambio.get("addColumn")
        if isinstance(ac, dict):
            for col in ac.get("columns") or []:
                if isinstance(col, dict):
                    estranee = [k for k in col if k != "column"]
                    if estranee:
                        fuori.append(("addColumn con un change dentro `columns:`, che non viene eseguito",
                                      f"{ac.get('tableName')}: {', '.join(estranee)}"))
    return fuori


# Scopo: l'operatore jsonb `?` nella forma che si rompe. Fuori da un dollar-quote
#        JDBC prende un `?` singolo per un segnaposto, e va raddoppiato; dentro un
#        corpo il raddoppio resta letterale. Un dollar-quote dopo IS e' prosa.
def jsonb_punto_di_domanda(cs: dict, _percorso: Path) -> list[Violazione]:
    fuori: list[Violazione] = []
    for _sezione, sql in gc.blocchi_sql(cs):
        if "?" not in sql:
            continue
        pezzi_fuori: list[tuple[int, str]] = []
        corpi: list[tuple[int, str]] = []
        inizio = 0
        for d in gc.dollar_di_primo_livello(sql):
            pezzi_fuori.append((inizio, sql[inizio:d.apertura]))
            if not gc.IS_PRIMA_RE.search(gc.spoglia(sql[:d.apertura]).rstrip()):
                corpi.append((d.corpo, sql[d.corpo:d.chiusura]))
            inizio = d.fine
        pezzi_fuori.append((inizio, sql[inizio:]))
        for base, pezzo, vietato, dove in (
                [(b, t, 1, "fuori da un dollar-quote: JDBC lo prende per un segnaposto")
                 for b, t in pezzi_fuori]
                + [(b, t, 2, "dentro un corpo: il raddoppio resta `??`") for b, t in corpi]):
            pulito = gc.spoglia(pezzo, prosa_dopo_is=True)
            for m in re.finditer(r"\?+", pulito):
                if len(m.group(0)) == vietato:
                    riga = sql.count("\n", 0, base) + pulito.count("\n", 0, m.start()) + 1
                    fuori.append((f"sql, riga ~{riga}: `{m.group(0)}` {dove}; si scrive jsonb_exists()",
                                  pulito.split("\n")[pulito.count("\n", 0, m.start())].strip()[:150]))
    return fuori


DJANGO_TYPE_RE = re.compile(r"\bdjango\.\w+\.\w+%TYPE", re.IGNORECASE)
DJANGO_RE = re.compile(r"\bdjango\.\w+", re.IGNORECASE)
CREATE_FUNZIONE_RE = re.compile(r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:FUNCTION|PROCEDURE)\b", re.IGNORECASE)
CREATE_VISTA_RE = re.compile(r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?(?:MATERIALIZED\s+)?VIEW\b", re.IGNORECASE)
LANGUAGE_SQL_RE = re.compile(r"\bLANGUAGE\s+sql\b", re.IGNORECASE)
FK_DJANGO_RE = re.compile(r"\bREFERENCES\s+django\.", re.IGNORECASE)


def django_alla_create(cs: dict, percorso: Path) -> list[Violazione]:
    try:
        fase = percorso.relative_to(gc.BASE).parts[0]
    except ValueError:
        fase = "00_schema" if "00_schema" in percorso.parts else (
            "20_code" if "20_code" in percorso.parts else "")
    if fase not in ("00_schema", "20_code"):
        return []
    fuori: list[Violazione] = []
    for _sezione, sql in gc.blocchi_sql(cs):
        if not DJANGO_RE.search(sql):
            continue
        for a, b in gc.istruzioni(sql):
            pulito = gc.spoglia(sql[a:b], prosa_dopo_is=True)
            if not DJANGO_RE.search(pulito):
                continue
            motivo = None
            if DJANGO_TYPE_RE.search(pulito):
                motivo = "`%TYPE` su una colonna di django"
            elif CREATE_FUNZIONE_RE.search(pulito) and LANGUAGE_SQL_RE.search(pulito):
                motivo = "una funzione LANGUAGE sql che nomina django"
            elif CREATE_VISTA_RE.search(pulito):
                motivo = "una vista che nomina django"
            elif FK_DJANGO_RE.search(pulito):
                motivo = "una FK verso django fuori da 90_end"
            if motivo:
                testa = len(sql[a:b]) - len(sql[a:b].lstrip())
                riga = sql.count("\n", 0, a + testa) + 1
                fuori.append((f"sql, istruzione da riga ~{riga}: {motivo}",
                              " ".join(pulito.split())[:150]))
    return fuori


# ── type-perso: la storia delle firme, in ordine di applicazione ─────────

CREATE_FUNZIONE_NOME_RE = re.compile(
    r"\bCREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+([\w.\"]+)\s*\(", re.IGNORECASE)
RETURNS_TABLE_RE = re.compile(r"\s*RETURNS\s+TABLE\s*\(", re.IGNORECASE)
MODI = ("IN", "OUT", "INOUT", "VARIADIC")

Firma = dict[str, tuple[bool, bool]]   # voce -> (ha %TYPE, ha la ragione accanto)


# Scopo: le voci fra le parentesi che aprono in `i`, come (inizio, fine) nel
#        testo ORIGINALE, saltando commenti, letterali e dollar-quote.
def _voci(sql: str, i: int) -> tuple[list[tuple[int, int]], int]:
    profondita, inizio, fuori, j, n = 0, i + 1, [], i, len(sql)
    while j < n:
        if sql.startswith("--", j):
            fine = sql.find("\n", j)
            j = n if fine < 0 else fine
            continue
        if sql.startswith("/*", j):
            j = gc.fine_commento_blocco(sql, j).pos
            continue
        if sql[j] == "'":
            j = gc.fine_letterale(sql, j).pos
            continue
        c = sql[j]
        if c == "(":
            profondita += 1
        elif c == ")":
            profondita -= 1
            if profondita == 0:
                fuori.append((inizio, j))
                return fuori, j + 1
        elif c == "," and profondita == 1:
            fuori.append((inizio, j))
            inizio = j + 1
        j += 1
    return fuori, n


# Scopo: (nome della voce, ha %TYPE, ha la ragione accanto) per una voce della
#        firma. La ragione e' un commento sulla stessa riga del nome, o una riga
#        di solo commento subito sopra.
def _voce(sql: str, a: int, b: int, saltare_modo: bool) -> tuple[str, bool, bool] | None:
    testo = gc.spoglia(sql[a:b], prosa_dopo_is=False)
    parole = testo.split()
    if saltare_modo and parole and parole[0].upper() in MODI:
        parole = parole[1:]
    if len(parole) < 2:
        return None
    nome = parole[0].strip('"').lower()
    m = re.search(r"\b" + re.escape(parole[0]) + r"\b", sql[a:b])
    pos = a + (m.start() if m else 0)
    righe = sql.split("\n")
    r = sql.count("\n", 0, pos)
    ragione = "--" in righe[r] or (r > 0 and righe[r - 1].strip().startswith("--"))
    return nome, "%TYPE" in testo.upper(), ragione


# Scopo: le firme delle funzioni create in un blocco, come {nome: Firma}.
def _firme(sql: str) -> dict[str, Firma]:
    fuori: dict[str, Firma] = {}
    pulito = gc.spoglia(sql, prosa_dopo_is=True)
    if not CREATE_FUNZIONE_NOME_RE.search(pulito):
        return fuori
    for a, b in gc.istruzioni(sql):
        m = CREATE_FUNZIONE_NOME_RE.search(sql, a, b)
        if not m or not CREATE_FUNZIONE_NOME_RE.match(gc.spoglia(sql[a:b]).lstrip()):
            continue
        nome = m.group(1).replace('"', "").lower()
        firma: Firma = {}
        voci, dopo = _voci(sql, m.end() - 1)
        for va, vb in voci:
            v = _voce(sql, va, vb, saltare_modo=True)
            if v:
                firma["parametro " + v[0]] = (v[1], v[2])
        rt = RETURNS_TABLE_RE.match(sql, dopo)
        if rt:
            colonne, _ = _voci(sql, rt.end() - 1)
            for va, vb in colonne:
                v = _voce(sql, va, vb, saltare_modo=False)
                if v:
                    firma["colonna " + v[0]] = (v[1], v[2])
        fuori[nome] = firma
    return fuori


# Scopo: le voci `*_id` con un tipo nudo e senza ragione accanto.
def id_senza_type(firme_ora: dict[str, Firma]) -> list[Violazione]:
    fuori: list[Violazione] = []
    for nome, ora in firme_ora.items():
        nudi = [voce for voce, (ancorato, ragione) in ora.items()
                if voce.endswith("_id") and not ancorato and not ragione]
        if nudi:
            fuori.append((f"{nome}: un id con tipo nudo, senza %TYPE ne' ragione accanto",
                          ", ".join(nudi)[:150]))
    return fuori


# Scopo: le voci che nella firma precedente della stessa funzione erano ancorate
#        con %TYPE e ora sono tipi nudi, senza ragione accanto.
def type_perso(firme_prima: dict[str, Firma], firme_ora: dict[str, Firma]) -> list[Violazione]:
    fuori: list[Violazione] = []
    for nome, ora in firme_ora.items():
        prima = firme_prima.get(nome)
        if not prima:
            continue
        persi = [voce for voce, (ancorato, _r) in prima.items()
                 if ancorato and voce in ora and not ora[voce][0] and not ora[voce][1]]
        if persi:
            fuori.append((f"{nome}: perso il %TYPE della revisione precedente",
                          ", ".join(persi)[:150]))
    return fuori


# ── nullvalue-vuoto ─────────────────────────────────────────────────────

# I caricatori che oggi scrivono '' in una colonna testo nullable: debito noto,
# con la sede della correzione. Una riga che non viola piu' e' una riga morta, e
# il cancello la segnala: si toglie nello stesso giro in cui si corregge il mirror.
# Vuoto dal 2026-11-12 (brief-db-nullvalue-vuoto-cinque-mirror): un caso nuovo si
# corregge, non si registra qui.
NULLVALUE_DEBITO = {
}
COLONNA_DOC_RE = re.compile(r"^\|\s*(\w+)\s*\|\s*([^|]+?)\s*\|\s*(YES|NO)\s*\|")
TESTO_RE = re.compile(r"^(text|character varying|varchar|character|char)\b", re.IGNORECASE)


# Scopo: le colonne di TESTO nullable di una tabella, dalla doc auto-generata
#        (solo li' una cella vuota diventa ''); None se la pagina non c'e'.
def _nullable(schema: str, tabella: str) -> dict[str, bool] | None:
    pagina = gc.ROOT / "docs" / "it" / "dbzero" / schema / "tabelle" / f"{tabella}.md"
    if not pagina.exists():
        return None
    fuori: dict[str, bool] = {}
    for riga in pagina.read_text(encoding="utf-8").split("\n"):
        m = COLONNA_DOC_RE.match(riga)
        if m:
            fuori[m.group(1)] = m.group(3) == "YES" and bool(TESTO_RE.match(m.group(2)))
    return fuori


def nullvalue_vuoto(cs: dict, percorso: Path) -> list[Violazione]:
    fuori: list[Violazione] = []
    for cambio in gc.cambi(cs):
        for tipo in ("loadData", "loadUpdateData"):
            ld = cambio.get(tipo)
            if not isinstance(ld, dict) or ld.get("nullValue", None) != "" or not ld.get("file"):
                continue
            csv_path = (percorso.parent / ld["file"]) if ld.get("relativeToChangelogFile") \
                else (gc.ROOT / "db" / "changelog" / ld["file"])
            nullable = _nullable(ld.get("schemaName", "public"), ld.get("tableName", ""))
            if not csv_path.exists() or nullable is None:
                continue
            stringhe = {c["name"] for col in ld.get("columns") or [] if isinstance(col, dict)
                        for c in [col.get("column")]
                        if isinstance(c, dict) and str(c.get("type", "")).upper() == "STRING"}
            with csv_path.open(encoding="utf-8", newline="") as fh:
                vuote = sorted({col for r in csv.DictReader(fh) for col, v in r.items()
                                if v == "" and col in stringhe and nullable.get(col)})
            if vuote:
                fuori.append((f"{tipo} di {ld.get('schemaName')}.{ld.get('tableName')} con nullValue \"\": "
                              "celle vuote in colonne testo nullable, scritte come ''",
                              ", ".join(vuote)[:150]))
    return fuori


# (nome, regola, inizio del perimetro; None = tutta la storia)
REGOLE_CHANGESET: list[tuple[str, Callable[[dict, Path], list[Violazione]], tuple[int, int] | None]] = [
    ("sqlcheck-booleano", sqlcheck_booleano, None),
    ("punto-e-virgola", punto_e_virgola, None),
    ("begin-atomic-da-solo", begin_atomic_da_solo, None),
    # ⚠️ Due regole partono da oggi: changelog mergiati le violano, e le revisioni
    #   successive degli stessi oggetti le hanno gia' corrette.
    ("log-cinque-argomenti", log_cinque_argomenti, (20261112, 1)),
    ("unique-ignorato", unique_ignorato, (20261112, 1)),
    # ⚠️ Anche queste due partono da oggi, per lo stesso motivo.
    ("jsonb-punto-di-domanda", jsonb_punto_di_domanda, (20261112, 31)),
    ("django-alla-create", django_alla_create, (20261112, 31)),
]

# type-perso e id-senza-type partono da oggi: la storia ne ha centinaia.
INIZIO_TYPE_PERSO = (20261112, 31)


# Scopo: l'ordine di applicazione di un changelog: data, numero, nome.
def _ordine(percorso: Path) -> tuple[int, int, str]:
    m = gc.FILENAME_RE.match(percorso.name)
    return (int(m.group(1)), int(m.group(2)), percorso.name) if m else (0, 0, percorso.name)


# ── Regole sui file ─────────────────────────────────────────────────────


SEGNAPOSTO_RE = re.compile(r"%(.?)")


def messaggi_segnaposto(percorso: Path) -> list[Violazione]:
    testo = percorso.read_text(encoding="utf-8")
    fuori: list[Violazione] = []
    visti: dict[str, int] = {}
    for n, riga in enumerate(csv.DictReader(io.StringIO(testo)), start=2):
        ident = (riga.get("id") or "").strip()
        if ident:
            if ident in visti:
                fuori.append((f"riga {n}: id {ident} ripetuto (gia' a riga {visti[ident]})",
                              riga.get("codice") or ""))
            else:
                visti[ident] = n
        messaggio = riga.get("messaggio") or ""
        i = 0
        while i < len(messaggio):
            if messaggio[i] == "%":
                seguito = messaggio[i + 1:i + 2]
                if seguito in ("s", "%"):
                    i += 2
                    continue
                fuori.append((f"riga {n}: segnaposto «%{seguito}» non valido per format()",
                              f"{riga.get('codice')}: {messaggio[:120]}"))
                break
            i += 1
    return fuori


def csv_fine_riga_misti(percorso: Path) -> list[Violazione]:
    righe = percorso.read_bytes().split(b"\n")
    if righe and righe[-1] == b"":
        righe.pop()
    crlf = [n for n, r in enumerate(righe, start=1) if r.endswith(b"\r")]
    if not crlf or len(crlf) == len(righe):
        return []
    return [(f"{len(crlf)} righe su {len(righe)} finiscono in \\r\\n, la prima e' la {crlf[0]}",
             "fine riga di un file solo: csv.writer va aperto con lineterminator='\\n'")]


PGAGENT_RE = re.compile(r"\bpgagent\.\w+", re.IGNORECASE)
RUNNER_OWNER_RE = re.compile(r"^--\s*pgtap-runner:\s*owner\s*$", re.MULTILINE)


def pgtap_pgagent_owner(percorso: Path) -> list[Violazione]:
    testo = percorso.read_text(encoding="utf-8")
    if not PGAGENT_RE.search(testo):
        return []
    codice = gc.spoglia(testo, prosa_dopo_is=True)
    m = PGAGENT_RE.search(codice)
    if not m:
        return []
    testa = "\n".join(testo.split("\n")[:80])
    if RUNNER_OWNER_RE.search(testa):
        return []
    riga = codice.count("\n", 0, m.start()) + 1
    return [(f"riga {riga}: legge {m.group(0)} senza `-- pgtap-runner: owner` nelle prime 80 righe",
             testo.split("\n")[riga - 1].strip()[:150])]


# ── Il giro ─────────────────────────────────────────────────────────────


# Scopo: il motivo dichiarato per `regola` in testa al file (YAML con `#`,
#        pgTAP con `--`), oppure None.
def _dichiarato(testo: str, regola: str) -> str | None:
    return gc.marcatore(testo, regola) or gc.marcatore(
        re.sub(r"^--", "#", testo, flags=re.MULTILINE), regola)


def main() -> int:
    argomenti = sys.argv[1:]
    tutto = "--tutto" in argomenti
    espliciti = [Path(a).resolve() for a in argomenti if a != "--tutto"]

    trovate: list[tuple[str, str, str, str]] = []   # (regola, file, dove, estratto)
    dichiarate: list[tuple[str, str, str, int]] = []
    esaminati = 0

    def registra(regola: str, percorso: Path, viol: list[Violazione]) -> None:
        if not viol:
            return
        rel = gc.rel(percorso)
        motivo = _dichiarato(percorso.read_text(encoding="utf-8", errors="replace"), regola)
        if motivo:
            dichiarate.append((regola, rel, motivo, len(viol)))
            return
        for dove, estratto in viol:
            trovate.append((regola, rel, dove, estratto))

    # I changelog: un perimetro per regola, su un solo giro dei file.
    yaml_espliciti = [p for p in espliciti if p.suffix.lower() in (".yaml", ".yml")]
    if yaml_espliciti or not espliciti:
        # ⭐ Tutta la storia, in ordine di applicazione: type-perso confronta ogni
        #   firma con la revisione precedente della stessa funzione, anche quando
        #   si esaminano solo i file passati.
        storia = sorted(gc.file_changelog(["--tutto"], None), key=_ordine)
        da_esaminare = set(yaml_espliciti) if yaml_espliciti else None
        percorsi = sorted(set(storia) | set(yaml_espliciti), key=_ordine)
        firme: dict[str, Firma] = {}
        nv_visti: set[str] = set()
        for percorso in percorsi:
            m = gc.FILENAME_RE.match(percorso.name)
            chiave = (int(m.group(1)), int(m.group(2))) if m else None
            try:
                changeset = gc.changeset(percorso)
            except yaml.YAMLError as exc:
                print(f"❌ YAML illeggibile: {percorso}\n   {exc}", file=sys.stderr)
                return 1
            in_esame = da_esaminare is None or percorso in da_esaminare
            firme_ora: dict[str, Firma] = {}
            for cs in changeset:
                for _sezione, sql in gc.blocchi_sql(cs):
                    firme_ora.update(_firme(sql))
            if in_esame:
                esaminati += 1
                if yaml_espliciti or tutto or (chiave is not None and chiave >= INIZIO_TYPE_PERSO):
                    registra("type-perso", percorso, type_perso(firme, firme_ora))
                    registra("id-senza-type", percorso, id_senza_type(firme_ora))
            firme.update(firme_ora)
            if not in_esame:
                continue
            viol_nv: list[Violazione] = []
            for cs in changeset:
                viol_nv.extend(nullvalue_vuoto(cs, percorso))
            if percorso.name in NULLVALUE_DEBITO:
                if viol_nv:
                    dichiarate.append(("nullvalue-vuoto", gc.rel(percorso),
                                       "debito noto, " + NULLVALUE_DEBITO[percorso.name], len(viol_nv)))
                elif not yaml_espliciti:
                    trovate.append(("nullvalue-vuoto", gc.rel(percorso),
                                    "riga morta di NULLVALUE_DEBITO: il mirror non scrive piu' ''",
                                    "togliere la riga dal registro"))
                nv_visti.add(percorso.name)
            else:
                registra("nullvalue-vuoto", percorso, viol_nv)
            for nome, regola, inizio in REGOLE_CHANGESET:
                if not (yaml_espliciti or tutto or inizio is None
                        or (chiave is not None and chiave >= inizio)):
                    continue
                viol: list[Violazione] = []
                for cs in changeset:
                    viol.extend(regola(cs, percorso))
                registra(nome, percorso, viol)

    # I file: CSV dei changelog e pgTAP.
    if espliciti:
        csv_file = [p for p in espliciti if p.suffix.lower() == ".csv"]
        pgtap_file = [p for p in espliciti if p.suffix.lower() == ".sql"]
    else:
        csv_file = sorted(gc.BASE.rglob("*.csv"))
        pgtap_file = sorted(PGTAP.rglob("*.sql"))
    for percorso in csv_file:
        esaminati += 1
        registra("csv-fine-riga-misti", percorso, csv_fine_riga_misti(percorso))
        if percorso.name == MESSAGGI.name:
            registra("messaggi-segnaposto", percorso, messaggi_segnaposto(percorso))
    for percorso in pgtap_file:
        esaminati += 1
        registra("pgtap-pgagent-owner", percorso, pgtap_pgagent_owner(percorso))

    for regola, rel, motivo, quante in dichiarate:
        print(f"⚠️  debito dichiarato [{regola}] ({quante}): {rel}\n    motivo: {motivo}")

    if not trovate:
        print(f"✅ guardrail forme dei changeSet: {esaminati} file esaminati, nessuna forma "
              "che muore all'apply")
        return 0

    print(f"❌ {len(trovate)} forme che muoiono all'apply (o che Liquibase ignora)\n",
          file=sys.stderr)
    for regola, rel, dove, estratto in trovate:
        print(f"  [{regola}] {rel}\n      {dove}\n      → {estratto}", file=sys.stderr)
    print(
        "\nOgni regola ha la sua sede, scritta in testa a scripts/guardrail_forme_changeset.py.\n"
        "Un'eccezione vera si dichiara in testa al file:\n"
        "    # <regola>: ammesso — <perche', in chiaro>      (YAML)\n"
        "    -- <regola>: ammesso — <perche', in chiaro>     (pgTAP)",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
