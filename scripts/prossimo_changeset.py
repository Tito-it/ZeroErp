#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Dice il prossimo `YYYYMMDD-NN` libero per un changeSet, leggendo
#        TUTTE le sedi in cui un numero puo' essere gia' occupato.
#
# ── LA REGOLA CHE APPLICA ────────────────────────────────────────────
#   Il progressivo `NN` e' UNICO PER DATA, condiviso fra tutti i livelli
#   (`00_schema`, `20_code`, `80_data`, `90_end`, ...): l'autogen mescola
#   `00_schema` e `20_code` ordinando per numero, non per fase.
#
#   Il primo numero libero e' `max(NN) + 1` dell'ULTIMA data usata, anche
#   se il giorno di calendario e' un altro. Niente buchi riempiti, niente
#   salti «di cortesia» per un'altra sessione. Oltre il `-99` si passa al
#   giorno dopo e si riparte da `-01`.
#
# ── DOVE GUARDA ──────────────────────────────────────────────────────
#   1. i file sotto `db/changelog/`, con `os.walk`: contano anche quelli
#      non committati e quelli a un livello solo (`90_end/`, `80_data/`);
#   2. i rami git, locali e remoti: un numero puo' essere su un ramo non
#      ancora unito;
#   3. il `databasechangelog` del database di sviluppo e dello scratch: un
#      changeSet applicato puo' non avere il file in questo albero.
#   Una sede che non si riesce a leggere viene DICHIARATA nell'esito, non
#   taciuta: il numero proposto vale solo per le sedi lette.
#
# ── ⚠️ QUELLO CHE NON PUO' FARE ──────────────────────────────────────
#   La risposta vale per il minuto in cui gira. Con un'altra sessione DB
#   attiva il numero si occupa mentre si scrive: si rilancia SUBITO PRIMA
#   di salvare ogni file, e un intervallo concordato si occupa per intero
#   appena deciso (un file per numero, anche uno scheletro).
#
# Uso:
#   scripts/prossimo_changeset.py          # il prossimo numero
#   scripts/prossimo_changeset.py 5        # i prossimi cinque, consecutivi
#   scripts/prossimo_changeset.py --doppi  # numeri usati da piu' di un file
# ------------------------------------------------------------

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
CHANGELOG = RADICE / "db" / "changelog"
# Un file per database: quello di sviluppo e lo scratch.
ENV_FILE = ("db/internal.env", "db/internal.ruoli.env")
# `20260429-19a-...` esiste: la lettera in coda non e' un numero nuovo.
NOME = re.compile(r"(?<![0-9])(20[0-9]{6})-([0-9]{1,3})[a-z]?-")


def _aggiungi(usati: dict[str, dict[int, set[str]]], testo: str, sede: str) -> None:
    nome = testo.rsplit("/", 1)[-1]
    m = NOME.match(nome)
    if m:
        usati[m.group(1)].setdefault(int(m.group(2)), set()).add(f"{sede}: {nome}")


def _da_file(usati) -> None:
    for _cartella, _sotto, files in os.walk(CHANGELOG):
        for f in files:
            if f.endswith((".yaml", ".yml")):
                _aggiungi(usati, f, "file")


def _da_rami(usati) -> str | None:
    try:
        rami = subprocess.run(
            ["git", "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes"],
            cwd=RADICE, capture_output=True, text=True, check=True, timeout=30,
        ).stdout.split()
        for ramo in rami:
            if ramo.endswith("/HEAD"):
                continue
            out = subprocess.run(
                ["git", "ls-tree", "-r", "--name-only", ramo, "--", "db/changelog"],
                cwd=RADICE, capture_output=True, text=True, check=True, timeout=60,
            ).stdout
            breve = ramo.replace("refs/heads/", "").replace("refs/remotes/", "")
            for riga in out.splitlines():
                _aggiungi(usati, riga, f"ramo {breve}")
    except (subprocess.SubprocessError, OSError) as e:
        return f"rami git: {e}"
    return None


def _leggi_env(percorso: Path) -> dict[str, str]:
    env = {}
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if riga and not riga.startswith("#") and "=" in riga:
            k, v = riga.split("=", 1)
            env[k.removeprefix("export ").strip()] = v.strip().strip("'\"")
    return env


def _da_database(usati) -> list[str]:
    non_letti = []
    for rel in ENV_FILE:
        p = RADICE / rel
        if not p.is_file():
            non_letti.append(f"{rel}: file assente")
            continue
        env = {**os.environ, **_leggi_env(p), "PGCONNECT_TIMEOUT": "5"}
        try:
            r = subprocess.run(
                ["psql", "--no-psqlrc", "-X", "-At", "-v", "ON_ERROR_STOP=1",
                 "-c", "SELECT filename FROM databasechangelog"],
                env=env, capture_output=True, text=True, timeout=30,
            )
        except (subprocess.SubprocessError, OSError) as e:
            non_letti.append(f"{rel}: {e}")
            continue
        if r.returncode != 0:
            non_letti.append(f"{rel}: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'psql rc ' + str(r.returncode)}")
            continue
        for riga in r.stdout.splitlines():
            _aggiungi(usati, riga, f"applicato su {env.get('PGDATABASE', rel)}")
    return non_letti


def _prossimi(usati, quanti: int) -> list[str]:
    data = max(usati)
    n = max(usati[data])
    out = []
    while len(out) < quanti:
        n += 1
        if n > 99:
            giorno = dt.date(int(data[:4]), int(data[4:6]), int(data[6:])) + dt.timedelta(days=1)
            data = giorno.strftime("%Y%m%d")
            n = max(usati.get(data, {0: None}))
            continue
        if n not in usati.get(data, {}):
            out.append(f"{data}-{n:02d}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Prossimo YYYYMMDD-NN libero per un changeSet.")
    ap.add_argument("quanti", nargs="?", type=int, default=1, help="quanti numeri consecutivi (default 1)")
    ap.add_argument("--doppi", action="store_true",
                    help="elenca i numeri dell'ultima data usati da piu' di un FILE dell'albero")
    a = ap.parse_args()

    usati: dict[str, dict[int, set[str]]] = defaultdict(dict)
    _da_file(usati)
    if not usati:
        print(f"Nessun changelog trovato sotto {CHANGELOG}", file=sys.stderr)
        return 2
    non_letti = []
    if (e := _da_rami(usati)):
        non_letti.append(e)
    non_letti += _da_database(usati)

    data = max(usati)
    numeri = sorted(usati[data])
    print(f"Ultima data usata: {data} — {len(numeri)} numeri, massimo -{numeri[-1]:02d}")
    solo_altrove = [n for n in numeri if not any(s.startswith("file: ") for s in usati[data][n])]
    for n in solo_altrove:
        print(f"  ⚠️  -{n:02d} non ha un file in questo albero: {'; '.join(sorted(usati[data][n]))}")

    if a.doppi:
        doppi = {n: sorted(s for s in sedi if s.startswith("file: "))
                 for n, sedi in usati[data].items()}
        doppi = {n: s for n, s in doppi.items() if len(s) > 1}
        if not doppi:
            print("Nessun numero doppio fra i file dell'ultima data.")
        for n in sorted(doppi):
            print(f"  ⛔ -{n:02d} usato da {len(doppi[n])} file:")
            for s in doppi[n]:
                print(f"       {s.removeprefix('file: ')}")
        return 1 if doppi else 0

    print("Prossimo libero: " + " ".join(_prossimi(usati, max(1, a.quanti))))
    for nl in non_letti:
        print(f"  ⚠️  sede NON letta — {nl}")
    print("Vale per questo minuto: si rilancia subito prima di salvare ogni file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
