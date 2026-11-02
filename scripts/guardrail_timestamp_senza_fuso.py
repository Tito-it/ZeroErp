#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Guardrail CI — `timestamp` SENZA fuso nei changeSet Liquibase nuovi
#
# COSA PRESIDIA, in una riga:
#   «in PostgreSQL `TIMESTAMP` nudo e' `timestamp without time zone`: un
#    changeSet che lo scrive fa nascere una colonna, un parametro o un
#    RETURNS che perde il fuso alla scrittura».
#
# PERCHE' ESISTE. Il 2026-09-20 la valutazione del modello di dominio (voce
#   V-3) ha contato 671 colonne `timestamptz` e 4 senza fuso nel dominio —
#   ma 22 senza fuso e ZERO con nello schema `ui`, 8 shadow di `storico`
#   nate prima del generatore, due funzioni con `p_as_of timestamp` e un
#   RETURNS TABLE senza fuso. Tutte nate da DDL scritte cosi':
#
#     data_insert  TIMESTAMP NOT NULL DEFAULT now(),
#
#   che sembra «un timestamp» e invece e' l'orario LOCALE della sessione che
#   inserisce. E le sessioni sono due: il backend Django connette in UTC
#   (USE_TZ = True), psql e Liquibase in Europe/Rome. Lo stesso now() scritto
#   da due sessioni in quella colonna vale due istanti diversi, e la riga non
#   ricorda quale. Decisione di Tid: nessuna eccezione, si allinea tutto
#   (changeSet 20260920-02..-07) — e questo cancello e' perche' non rinasca.
#
# COME FUNZIONA. Cammina i changelog di migrations_v2 con data >= 2026-09-20
#   (PERIMETRO: quelli mergiati prima non si toccano — e' la regola del
#   progetto — e il difetto che portavano lo sana 20260920-02..-07; il
#   database vivo lo presidia db/pgtap/dbops/test-nessun-timestamp-senza-fuso-v1).
#   Per ogni changeSet guarda SOLO `changes` (un `rollback` che rimette il
#   tipo vecchio e' legittimo) e cerca due forme:
#   · nei blocchi `sql:`, la parola `timestamp` — anche `timestamp(n)` —
#     NON seguita da `with time zone`, a commenti e letterali tolti (un
#     COMMENT ON che dice «timestamp» non e' un tipo) e con i dollar-quote
#     resi trasparenti (dentro un corpo plpgsql il tipo CONTA: e' il DECLARE
#     o il RETURNS). `timestamptz` non e' una parola a se' e non viene presa;
#     `clock_timestamp()`, `to_timestamp()`, `CURRENT_TIMESTAMP` nemmeno
#     (l'underscore e' parte della parola).
#     ⚠️ Un'istruzione che COMINCIA con DROP e' esente: nomina la firma
#     VECCHIA per toglierla (`DROP FUNCTION f(text, timestamp without time
#     zone)`), non dichiara niente di nuovo.
#   · nei change nativi (`createTable`, `addColumn`, `modifyDataType`, ...),
#     un `type:` che sia `timestamp`, `timestamp(n)`, `timestamp without time
#     zone` o `datetime` (che Liquibase traduce in `TIMESTAMP WITHOUT TIME
#     ZONE` su PostgreSQL).
#
# ESCLUSIONI: si DICHIARANO, non si spiegano solo in prosa. Un file che ha
#   un motivo vero per un `timestamp` senza fuso lo scrive in testa:
#     # timestamp-senza-fuso: ammesso — <perche', in chiaro>
#   e il cancello lo stampa come debito dichiarato invece di fermarsi.
#   ⛔ «E' una data, il fuso non conta» non e' un motivo: e' un `date`.
#
# ⚠️ COSA NON PRESIDIA: il cast `::timestamp` su un valore che e' gia' un
#   istante (spoglia il fuso in lettura, non in scrittura) viene preso
#   anche lui perche' e' la stessa parola — ma un `timestamp` che entra da
#   una funzione di estensione, da un CSV (Liquibase legge le colonne come
#   STRING) o da un DDL a mano fuori dal changelog lo vede solo il pgTAP.
#
# Uso (read-only, nessun database):
#   python scripts/guardrail_timestamp_senza_fuso.py            # perimetro (>= 20260920)
#   python scripts/guardrail_timestamp_senza_fuso.py <path>...  # solo questi file
#   python scripts/guardrail_timestamp_senza_fuso.py --tutto    # storia intera, per misurare
# Exit 0 se pulito, 1 se trova un timestamp senza fuso non dichiarato.
# ------------------------------------------------------------

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# ⭐ Il parser YAML in C dove c'e' (scripts/_yaml_veloce.py): il costo di
#   questi cancelli e' tutto nel parsing. `yaml` resta per `yaml.YAMLError`.
from _yaml_veloce import carica as carica_yaml

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "db" / "changelog" / "migrations_v2"
FILENAME_RE = re.compile(r"^(\d{8})-\d{2}.*\.(ya?ml)$", re.IGNORECASE)
# ⭐ Il perimetro: da quando la regola esiste. I changelog precedenti non si
#   toccano (mergiati) e il loro difetto lo sana 20260920-02..-07.
DATA_INIZIO = "20260920"
MARCATORE_RE = re.compile(r"^#\s*timestamp-senza-fuso:\s*ammesso\s*[—-]\s*(\S.*)$", re.MULTILINE)
DOLLAR_RE = re.compile(r"\$[A-Za-z_][A-Za-z_0-9]*\$|\$\$")
IS_PRIMA_RE = re.compile(r"\bIS$", re.IGNORECASE)
# `timestamp` come parola intera, con eventuale precisione, e cio' che segue.
TIMESTAMP_RE = re.compile(r"\btimestamp\b(\s*\(\s*\d+\s*\))?", re.IGNORECASE)
WITH_TZ_RE = re.compile(r"\s*with\s+time\s+zone\b", re.IGNORECASE)
TIPO_NATIVO_RE = re.compile(
    r"^\s*(timestamp(\s*\(\s*\d+\s*\))?(\s+without\s+time\s+zone)?|datetime)\s*$",
    re.IGNORECASE)
# I change nativi che portano un `type:` di colonna (Liquibase).
CHANGE_CON_COLONNE = ("createTable", "addColumn", "modifyDataType", "createIndex")


# Scopo: toglie commenti e letterali a quote singole dal blocco SQL, lasciando
#        il resto AL SUO POSTO (stesse righe) cosi' i numeri di riga restano
#        veri; i dollar-quote sono resi trasparenti — il corpo di una
#        funzione si esamina, e' li' che vivono DECLARE e RETURNS.
#        Stesso tokenizer del cancello dei letterali (commenti /* */ annidati).
def spoglia(sql: str) -> str:
    fuori: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        if sql.startswith("--", i):
            fine = sql.find("\n", i)
            i = n if fine < 0 else fine
            continue
        if sql.startswith("/*", i):
            profondita = 1
            j = i + 2
            while j < n and profondita > 0:
                if sql.startswith("/*", j):
                    profondita += 1
                    j += 2
                    continue
                if sql.startswith("*/", j):
                    profondita -= 1
                    j += 2
                    continue
                if sql[j] == "\n":
                    fuori.append("\n")
                j += 1
            i = j
            continue
        if sql[i] == "$":
            m = DOLLAR_RE.match(sql, i)
            if m:
                # ⚠️ Un dollar-quote dopo `IS` e' PROSA (COMMENT ON ... IS
                #   $c$ ... $c$), non un corpo: si toglie come un letterale.
                #   Misurato: 20260207-02 dice «colonna timestamp di base»
                #   nel COMMENT di fn_apply_cleanup_at, e non e' un tipo.
                prima = "".join(fuori).rstrip()
                if IS_PRIMA_RE.search(prima):
                    tag = m.group(0)
                    chiusura = sql.find(tag, m.end())
                    fine = n if chiusura < 0 else chiusura + len(tag)
                    fuori.append("\n" * sql.count("\n", i, fine))
                    i = fine
                    continue
                i = m.end()
                continue
        if sql[i] == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        j += 2
                        continue
                    break
                if sql[j] == "\n":
                    fuori.append("\n")
                j += 1
            i = j + 1
            continue
        fuori.append(sql[i])
        i += 1
    return "".join(fuori)


# Scopo: le occorrenze di `timestamp` senza fuso in un blocco SQL, come
#        (riga, estratto). Esenta le istruzioni che cominciano con DROP.
def timestamp_nudi(sql: str) -> list[tuple[int, str]]:
    testo = spoglia(sql)
    trovati: list[tuple[int, str]] = []
    for m in TIMESTAMP_RE.finditer(testo):
        if WITH_TZ_RE.match(testo, m.end()):
            continue
        inizio_istr = testo.rfind(";", 0, m.start()) + 1
        prima_parola = testo[inizio_istr:m.start()].strip().split(None, 1)
        if prima_parola and prima_parola[0].upper() == "DROP":
            continue
        riga = testo.count("\n", 0, m.start()) + 1
        righe = testo.split("\n")
        trovati.append((riga, righe[riga - 1].strip()[:150]))
    return trovati


# Scopo: le violazioni di un changelog — blocchi `sql:` e `type:` nativi —
#        guardando SOLO `changes`, mai `rollback`.
def violazioni_di(percorso: Path) -> list[tuple[str, str]]:
    doc = carica_yaml(percorso.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        return []
    fuori: list[tuple[str, str]] = []
    for voce in doc.get("databaseChangeLog") or []:
        if not isinstance(voce, dict):
            continue
        cs = voce.get("changeSet")
        if not isinstance(cs, dict) or not cs.get("changes"):
            continue
        cambi = cs["changes"]
        for cambio in cambi if isinstance(cambi, list) else [cambi]:
            if not isinstance(cambio, dict):
                continue
            if "sql" in cambio:
                corpo = cambio["sql"]
                testo = corpo.get("sql") if isinstance(corpo, dict) else corpo
                if isinstance(testo, str):
                    for riga, estratto in timestamp_nudi(testo):
                        fuori.append((f"sql, riga ~{riga} del blocco", estratto))
            for nome in CHANGE_CON_COLONNE:
                if nome not in cambio or not isinstance(cambio[nome], dict):
                    continue
                for col in cambio[nome].get("columns") or []:
                    c = col.get("column") if isinstance(col, dict) else None
                    if not isinstance(c, dict):
                        continue
                    tipo = c.get("type")
                    if isinstance(tipo, str) and TIPO_NATIVO_RE.match(tipo):
                        fuori.append((f"{nome}", f"column {c.get('name')}: type {tipo}"))
                tipo = cambio[nome].get("newDataType")
                if isinstance(tipo, str) and TIPO_NATIVO_RE.match(tipo):
                    fuori.append((f"{nome}", f"newDataType {tipo}"))
    return fuori


# Scopo: i file da esaminare — quelli passati, oppure il perimetro
#        (data >= DATA_INIZIO), oppure tutta la storia con --tutto.
def file_da_esaminare(argomenti: list[str]) -> list[Path]:
    tutto = "--tutto" in argomenti
    espliciti = [a for a in argomenti if a != "--tutto"]
    if espliciti:
        return [Path(a).resolve() for a in espliciti]
    if not BASE.is_dir():
        return []
    fuori = []
    for p in sorted(BASE.rglob("*")):
        m = FILENAME_RE.match(p.name)
        if not p.is_file() or not m:
            continue
        if tutto or m.group(1) >= DATA_INIZIO:
            fuori.append(p)
    return fuori


# Scopo: orchestra la passata e stampa un rapporto che dica DOVE e COSA fare.
def main() -> int:
    percorsi = file_da_esaminare(sys.argv[1:])
    violazioni: list[tuple[str, str, str]] = []
    dichiarati: list[tuple[str, str, int]] = []
    esaminati = 0

    for percorso in percorsi:
        try:
            trovate = violazioni_di(percorso)
        except yaml.YAMLError as exc:
            print(f"❌ YAML illeggibile: {percorso}\n   {exc}", file=sys.stderr)
            return 1
        esaminati += 1
        if not trovate:
            continue
        rel = str(percorso.relative_to(ROOT)) if ROOT in percorso.parents else str(percorso)
        marcatore = MARCATORE_RE.search(percorso.read_text(encoding="utf-8"))
        if marcatore:
            dichiarati.append((rel, marcatore.group(1).strip(), len(trovate)))
            continue
        for dove, estratto in trovate:
            violazioni.append((rel, dove, estratto))

    for rel, motivo, quante in dichiarati:
        print(f"⚠️  timestamp senza fuso DICHIARATO ({quante}): {rel}\n    motivo: {motivo}")

    if not violazioni:
        print(f"✅ guardrail timestamp senza fuso: {esaminati} changelog esaminati "
              f"(perimetro >= {DATA_INIZIO}), nessun `timestamp` senza fuso non dichiarato")
        return 0

    print("❌ `timestamp` SENZA fuso in un changeSet\n", file=sys.stderr)
    for rel, dove, estratto in violazioni:
        print(f"  {rel}  [{dove}]", file=sys.stderr)
        print(f"      → {estratto}", file=sys.stderr)
    print(
        "\nIn PostgreSQL `TIMESTAMP` nudo e' `timestamp without time zone`: la\n"
        "colonna (o il parametro, o il RETURNS) memorizza l'orario LOCALE della\n"
        "sessione che scrive, e le sessioni di questo progetto sono due — il\n"
        "backend in UTC, psql/Liquibase in Europe/Rome. Lo stesso now() vale due\n"
        "istanti diversi, e la riga non ricorda quale.\n"
        "\n"
        "COSA FARE: scrivi `timestamptz` (o `timestamp with time zone`). Se il\n"
        "valore e' un giorno e non un istante, il tipo e' `date`. In un DECLARE o\n"
        "in una firma, ancora la variabile alla colonna con `%TYPE`.\n"
        "\n"
        "Se esiste un motivo vero, si DICHIARA in testa al file:\n"
        "    # timestamp-senza-fuso: ammesso — <perche', in chiaro>\n"
        "\n"
        "Storia: voce V-3 di valutazione-modello-di-dominio-db (2026-09-20) —\n"
        "34 colonne, due firme e un RETURNS nati cosi', sanati da 20260920-02..-07.\n"
        "Presidio vivo: db/pgtap/dbops/test-nessun-timestamp-senza-fuso-v1.sql.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
