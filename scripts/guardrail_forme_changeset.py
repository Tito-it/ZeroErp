#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Guardrail CI — le forme che passano la lettura e muoiono all'apply
#
# COSA PRESIDIA. Otto regole scritte nella documentazione e ricadute piu'
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


def sqlcheck_booleano(cs: dict) -> list[Violazione]:
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


def punto_e_virgola(cs: dict) -> list[Violazione]:
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


def begin_atomic_da_solo(cs: dict) -> list[Violazione]:
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


def log_cinque_argomenti(cs: dict) -> list[Violazione]:
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


def unique_ignorato(cs: dict) -> list[Violazione]:
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


# (nome, regola, inizio del perimetro; None = tutta la storia)
REGOLE_CHANGESET: list[tuple[str, Callable[[dict], list[Violazione]], tuple[int, int] | None]] = [
    ("sqlcheck-booleano", sqlcheck_booleano, None),
    ("punto-e-virgola", punto_e_virgola, None),
    ("begin-atomic-da-solo", begin_atomic_da_solo, None),
    # ⚠️ Due regole partono da oggi: changelog mergiati le violano, e le revisioni
    #   successive degli stessi oggetti le hanno gia' corrette.
    ("log-cinque-argomenti", log_cinque_argomenti, (20261112, 1)),
    ("unique-ignorato", unique_ignorato, (20261112, 1)),
]


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
        percorsi = yaml_espliciti or gc.file_changelog(["--tutto"], None)
        for percorso in percorsi:
            m = gc.FILENAME_RE.match(percorso.name)
            chiave = (int(m.group(1)), int(m.group(2))) if m else None
            try:
                changeset = gc.changeset(percorso)
            except yaml.YAMLError as exc:
                print(f"❌ YAML illeggibile: {percorso}\n   {exc}", file=sys.stderr)
                return 1
            esaminati += 1
            for nome, regola, inizio in REGOLE_CHANGESET:
                if not (yaml_espliciti or tutto or inizio is None
                        or (chiave is not None and chiave >= inizio)):
                    continue
                viol: list[Violazione] = []
                for cs in changeset:
                    viol.extend(regola(cs))
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
