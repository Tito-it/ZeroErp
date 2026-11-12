#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: i pezzi che i cancelli statici dei changelog hanno in comune, in un
#        posto solo: quali file esaminare, come si cammina un changelog, come si
#        legge un'eccezione dichiarata, e le primitive lessicali del SQL.
#
# ⭐ PERCHE' ESISTE. Ogni cancello ricopiava l'elenco dei changelog, il giro dei
#   blocchi `sql:` e, peggio, il modo di saltare commenti, letterali e
#   dollar-quote. Tre copie dello stesso lessico prima o poi rispondono in tre
#   modi diversi allo stesso SQL (regola del 2, .codex/AGENTS.md). Qui stanno le
#   primitive; ogni cancello ci costruisce sopra la sua lettura.
#
# ⚠️ COSA NON FA. Non e' un parser SQL: riconosce commenti (`--`, `/* */`
#   annidati come in PostgreSQL), letterali a quote singole (con l'apostrofo
#   raddoppiato) e dollar-quote. Basta per dire «questo pezzo e' codice, questo
#   e' testo»; la verita' sull'SQL la dice solo il migrate.
# ------------------------------------------------------------

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterator

from _yaml_veloce import carica as carica_yaml

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "db" / "changelog" / "migrations_v2"

# `AAAAMMGG-NN[N]-…`: la data e il numero, che insieme danno il perimetro.
FILENAME_RE = re.compile(r"^(\d{8})-(\d{2,3})(?!\d).*\.(ya?ml)$", re.IGNORECASE)
DOLLAR_RE = re.compile(r"\$[A-Za-z_][A-Za-z_0-9]*\$|\$\$")


# ── Quali file ──────────────────────────────────────────────────────────


# Scopo: i changelog da esaminare. I percorsi passati vincono; senza percorsi,
#        il perimetro (data, numero) >= `inizio`, oppure tutta la storia con
#        `--tutto` o con `inizio` None.
def file_changelog(argomenti: list[str], inizio: tuple[int, int] | None) -> list[Path]:
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
        if tutto or inizio is None or (int(m.group(1)), int(m.group(2))) >= inizio:
            fuori.append(p)
    return fuori


# Scopo: il percorso da stampare, relativo alla radice del repo quando ci sta.
def rel(percorso: Path) -> str:
    return str(percorso.relative_to(ROOT)) if ROOT in percorso.parents else str(percorso)


# ── Come si cammina un changelog ────────────────────────────────────────


# Scopo: i changeSet di un changelog (YAMLError risale al chiamante).
def changeset(percorso: Path) -> list[dict]:
    doc = carica_yaml(percorso.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        return []
    fuori = []
    for voce in doc.get("databaseChangeLog") or []:
        if isinstance(voce, dict) and isinstance(voce.get("changeSet"), dict):
            fuori.append(voce["changeSet"])
    return fuori


# Scopo: i change di una sezione (`changes` o `rollback`) di un changeSet.
def cambi(cs: dict, sezione: str = "changes") -> list[dict]:
    valore = cs.get(sezione)
    if not valore:
        return []
    return [c for c in (valore if isinstance(valore, list) else [valore]) if isinstance(c, dict)]


# Scopo: il testo dei blocchi `sql:` delle sezioni chieste, come (sezione, testo).
def blocchi_sql(cs: dict, sezioni: tuple[str, ...] = ("changes",)) -> list[tuple[str, str]]:
    fuori = []
    for sezione in sezioni:
        for cambio in cambi(cs, sezione):
            if "sql" not in cambio:
                continue
            corpo = cambio["sql"]
            testo = corpo.get("sql") if isinstance(corpo, dict) else corpo
            if isinstance(testo, str):
                fuori.append((sezione, testo))
    return fuori


# Scopo: il motivo di un'eccezione dichiarata in testa al file, nella forma
#          # <nome>: ammesso — <perche'>
#        oppure None.
def marcatore(testo: str, nome: str) -> str | None:
    m = re.search(r"^#\s*" + re.escape(nome) + r":\s*ammesso\s*[—-]\s*(\S.*)$",
                  testo, re.MULTILINE)
    return m.group(1).strip() if m else None


# ── Primitive lessicali ─────────────────────────────────────────────────


@dataclass
class Fine:
    pos: int        # la posizione subito dopo il pezzo
    chiuso: bool    # False se il testo finisce prima della chiusura


# Scopo: la fine di un commento `/* … */` che comincia in `i`. In PostgreSQL i
#        commenti a blocco SI ANNIDANO: si conta la profondita'.
def fine_commento_blocco(sql: str, i: int) -> Fine:
    n = len(sql)
    profondita, j = 1, i + 2
    while j < n and profondita > 0:
        if sql.startswith("/*", j):
            profondita += 1
            j += 2
            continue
        if sql.startswith("*/", j):
            profondita -= 1
            j += 2
            continue
        j += 1
    return Fine(j, profondita == 0)


# Scopo: la fine di un letterale a quote singole che comincia in `i` (sul primo
#        apostrofo). Un apostrofo raddoppiato resta dentro il letterale.
def fine_letterale(sql: str, i: int) -> Fine:
    n = len(sql)
    j = i + 1
    while j < n:
        if sql[j] == "'":
            if j + 1 < n and sql[j + 1] == "'":
                j += 2
                continue
            return Fine(j + 1, True)
        j += 1
    return Fine(n, False)


# Scopo: il contenuto di un letterale che comincia in `i`, con gli apostrofi
#        raddoppiati resi singoli.
def contenuto_letterale(sql: str, i: int) -> tuple[str, Fine]:
    f = fine_letterale(sql, i)
    fine_testo = f.pos - 1 if f.chiuso else f.pos
    return sql[i + 1:fine_testo].replace("''", "'"), f


# Scopo: il dollar-quote che apre in `i`, come (tag, fine), oppure None se in
#        `i` non ne comincia uno.
def dollar_quote(sql: str, i: int) -> tuple[str, Fine] | None:
    m = DOLLAR_RE.match(sql, i)
    if not m:
        return None
    tag = m.group(0)
    chiusura = sql.find(tag, m.end())
    if chiusura < 0:
        return tag, Fine(len(sql), False)
    return tag, Fine(chiusura + len(tag), True)


@dataclass
class Dollar:
    tag: str
    apertura: int   # posizione del tag di apertura
    corpo: int      # inizio del contenuto
    chiusura: int   # posizione del tag di chiusura
    fine: int       # subito dopo il tag di chiusura


# Scopo: i dollar-quote di PRIMO livello di un blocco SQL, saltando commenti e
#        letterali. Un dollar-quote non chiuso finisce col testo.
def dollar_di_primo_livello(sql: str) -> Iterator[Dollar]:
    i, n = 0, len(sql)
    while i < n:
        if sql.startswith("--", i):
            fine = sql.find("\n", i)
            i = n if fine < 0 else fine
            continue
        if sql.startswith("/*", i):
            i = fine_commento_blocco(sql, i).pos
            continue
        if sql[i] == "'":
            i = fine_letterale(sql, i).pos
            continue
        if sql[i] == "$":
            dq = dollar_quote(sql, i)
            if dq:
                tag, f = dq
                chiusura = f.pos - len(tag) if f.chiuso else n
                yield Dollar(tag, i, i + len(tag), chiusura, f.pos)
                i = f.pos
                continue
        i += 1


IS_PRIMA_RE = re.compile(r"\bIS$", re.IGNORECASE)
SPECIALE_RE = re.compile(r"--|/\*|[$']")


# Scopo: il blocco SQL con commenti e letterali tolti, ma lasciando le righe al
#        loro posto (i numeri di riga restano veri). I dollar-quote sono
#        TRASPARENTI: il corpo di una funzione si esamina, perche' e' li' che
#        vivono DECLARE, RETURNS e le chiamate. ⚠️ Con `prosa_dopo_is` un
#        dollar-quote che segue `IS` (COMMENT ON … IS $c$ … $c$) e' prosa e si
#        toglie come un letterale. Memorizzata: piu' regole chiedono lo stesso
#        blocco.
@lru_cache(maxsize=4096)
def spoglia(sql: str, prosa_dopo_is: bool = True) -> str:
    fuori: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        if sql.startswith("--", i):
            fine = sql.find("\n", i)
            i = n if fine < 0 else fine
            continue
        if sql.startswith("/*", i):
            f = fine_commento_blocco(sql, i)
            fuori.append("\n" * sql.count("\n", i, f.pos))
            i = f.pos
            continue
        if sql[i] == "$":
            m = DOLLAR_RE.match(sql, i)
            if m:
                if prosa_dopo_is and IS_PRIMA_RE.search("".join(fuori).rstrip()):
                    dq = dollar_quote(sql, i)
                    assert dq is not None
                    fine = dq[1].pos
                    fuori.append("\n" * sql.count("\n", i, fine))
                    i = fine
                    continue
                i = m.end()
                continue
        if sql[i] == "'":
            f = fine_letterale(sql, i)
            # Il letterale non chiuso arriva fino al fondo: le righe restano.
            fuori.append("\n" * sql.count("\n", i, f.pos if f.chiuso else n))
            i = f.pos
            continue
        # Fino al prossimo carattere che puo' aprire qualcosa, in un colpo solo.
        m = SPECIALE_RE.search(sql, i + 1)
        fine = n if m is None else m.start()
        fuori.append(sql[i:fine])
        i = fine
    return "".join(fuori)
