#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Guardrail CI — il COMMENT ON nei changeSet nuovi descrive l'oggetto, non la storia
#
# COSA PRESIDIA, in una riga:
#   «un `COMMENT ON … IS '…'` scritto in un changeSet nuovo non porta il nome
#    di un brief, un marcatore di revisione, l'id di un changeSet o l'hash di
#    un commit» (linee-guida-sql §5d).
#
# PERCHE' ESISTE. Il COMMENT e' il primo paragrafo della scheda auto-generata:
#   chi la apre lo legge come la definizione dell'oggetto. Una cronaca
#   («rev …», «Brief: …», «20261021-67») dentro il COMMENT invecchia il giorno
#   dopo e manda chi legge a cercare documenti di lavoro. Il debito che c'e'
#   gia' si riscrive per famiglia, quando un lavoro riapre gli oggetti; questo
#   cancello ferma quello NUOVO in tutto il database, senza un registro del
#   pregresso. Per dbops e maintenance il database vivo lo guarda il pgTAP
#   db/pgtap/dbops/test-comment-al-presente-v1, con le stesse quattro marche.
#
# COME FUNZIONA. Cammina i changelog di migrations_v2 dal changeSet
#   20261111-18 in poi (PERIMETRO: quelli prima sono mergiati e non si
#   toccano). Per ogni changeSet guarda SOLO `changes` (un `rollback` che
#   rimette il testo vecchio e' legittimo); nei blocchi `sql:` trova ogni
#   `COMMENT ON … IS` seguito da un letterale (quote singole, E'…', o
#   dollar-quote) e cerca le quattro marche:
#   · brief       — la parola «brief», in qualunque forma;
#   · revisione   — la parola «rev» isolata («rev 2026-…», «⭐ rev»);
#   · changeSet   — un id AAAAMMGG-NN;
#   · hash        — 7-12 cifre esadecimali con almeno una lettera e una cifra.
#   Date, sigle di decisione e misure NON entrano: stanno anche in frasi
#   lecite, e un cancello che sbaglia insegna a ignorarlo.
#
# ESCLUSIONI: si DICHIARANO. Un file che ha un motivo vero lo scrive in testa:
#     # comment-al-presente: ammesso — <perche', in chiaro>
#   e il cancello lo stampa come debito dichiarato invece di fermarsi.
#
# ⚠️ COSA NON PRESIDIA: un COMMENT composto a runtime (EXECUTE format(...)
#   dentro una funzione, con il testo in una variabile) non e' un letterale
#   dopo IS; lo vede solo il pgTAP sul database vivo, e solo per il suo
#   perimetro. Ne' i commenti `--` dentro i corpi delle funzioni: non sono
#   COMMENT ON.
#
# Uso (read-only, nessun database):
#   python scripts/guardrail_comment_al_presente.py            # perimetro (>= 20261111-18)
#   python scripts/guardrail_comment_al_presente.py <path>...  # solo questi file
#   python scripts/guardrail_comment_al_presente.py --tutto    # storia intera, per misurare
# Exit 0 se pulito, 1 se trova una marca non dichiarata.
# ------------------------------------------------------------

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

from _yaml_veloce import carica as carica_yaml

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "db" / "changelog" / "migrations_v2"
FILENAME_RE = re.compile(r"^(\d{8})-(\d{2,3})\D.*\.(ya?ml)$", re.IGNORECASE)
# ⭐ Il perimetro: dal primo changeSet scritto con la regola in vigore e il
#   presidio acceso (giro 14 di brief-db-revisione-dbops).
INIZIO = (20261111, 18)
MARCATORE_RE = re.compile(r"^#\s*comment-al-presente:\s*ammesso\s*[—-]\s*(\S.*)$", re.MULTILINE)
COMMENT_IS_RE = re.compile(r"\bCOMMENT\s+ON\b.*?\bIS\s+", re.IGNORECASE | re.DOTALL)
DOLLAR_RE = re.compile(r"\$[A-Za-z_][A-Za-z_0-9]*\$|\$\$")
MARCHE = (
    ("brief", re.compile(r"brief", re.IGNORECASE)),
    ("revisione", re.compile(r"\brev\b", re.IGNORECASE)),
    ("changeSet", re.compile(r"\b20\d{6}-\d{2,3}\b")),
    ("hash", re.compile(r"\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*[0-9])[0-9a-f]{7,12}\b")),
)


# Scopo: il letterale che comincia in `sql[i]`, come (testo, fine), oppure
#        None se dopo IS non c'e' un letterale (NULL, un'espressione).
def letterale(sql: str, i: int) -> tuple[str, int] | None:
    n = len(sql)
    if sql.startswith(("E'", "e'"), i):
        i += 1
    if i < n and sql[i] == "'":
        j, pezzi = i + 1, []
        while j < n:
            if sql[j] == "'":
                if j + 1 < n and sql[j + 1] == "'":
                    pezzi.append("'")
                    j += 2
                    continue
                return "".join(pezzi), j + 1
            pezzi.append(sql[j])
            j += 1
        return "".join(pezzi), n
    m = DOLLAR_RE.match(sql, i)
    if m:
        tag = m.group(0)
        chiusura = sql.find(tag, m.end())
        fine = n if chiusura < 0 else chiusura
        return sql[m.end():fine], fine + len(tag)
    return None


# Scopo: le marche trovate nei COMMENT di un blocco SQL, come (riga, marca, estratto).
def marche_nei_comment(sql: str) -> list[tuple[int, str, str]]:
    trovate: list[tuple[int, str, str]] = []
    pos = 0
    while True:
        m = COMMENT_IS_RE.search(sql, pos)
        if not m:
            break
        lett = letterale(sql, m.end())
        if lett is None:
            pos = m.end()
            continue
        testo, fine = lett
        riga = sql.count("\n", 0, m.start()) + 1
        for nome, rx in MARCHE:
            hit = rx.search(testo)
            if hit:
                a = max(0, hit.start() - 40)
                trovate.append((riga, nome, testo[a:hit.end() + 40].replace("\n", " ")))
        pos = fine
    return trovate


# Scopo: le violazioni di un changelog, guardando SOLO `changes`, mai `rollback`.
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
            if not isinstance(cambio, dict) or "sql" not in cambio:
                continue
            corpo = cambio["sql"]
            testo = corpo.get("sql") if isinstance(corpo, dict) else corpo
            if isinstance(testo, str):
                for riga, marca, estratto in marche_nei_comment(testo):
                    fuori.append((f"COMMENT a riga ~{riga} del blocco, marca «{marca}»", estratto))
    return fuori


# Scopo: i file da esaminare — quelli passati, oppure il perimetro, oppure
#        tutta la storia con --tutto.
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
        if tutto or (int(m.group(1)), int(m.group(2))) >= INIZIO:
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
        print(f"⚠️  debito dichiarato: {rel} ({quante} marche) — {motivo}")

    if violazioni:
        print(f"❌ {len(violazioni)} marche nei COMMENT dei changeSet nuovi (linee-guida-sql §5d):")
        for rel, dove, estratto in violazioni:
            print(f"   {rel}\n      {dove}: …{estratto}…")
        print("\nIl COMMENT descrive l'oggetto al presente: niente brief, «rev», id di changeSet o hash.\n"
              "La storia va nella testata del changeSet. Un'eccezione vera si dichiara in testa al file:\n"
              "   # comment-al-presente: ammesso — <perche'>")
        return 1

    print(f"COMMENT al presente: {esaminati} changelog esaminati, nessuna marca.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
