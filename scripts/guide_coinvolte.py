#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Dice quali guide e quali note di dominio descrivono gli oggetti che
#        un lavoro tocca, perche' l'analisi le legga PRIMA di decidere e la
#        verifica le confronti DOPO (AGENTS.md, «Lo sviluppo si confronta
#        con le guide del dominio»).
#
# ── COSA LEGGE ───────────────────────────────────────────────────────
#   Dai file del perimetro (changeSet, pgTAP, codice BE/FE, brief):
#   1. i nomi qualificati `schema.oggetto` degli schemi del database
#      (anche nella forma Django `schema"."oggetto` e nei link della doc
#      `/dbzero/<schema>/<tabelle|funzioni|views>/<oggetto>`);
#   2. i percorsi `/api/v1/<area>/<risorsa>/` scritti nel codice BE/FE.
#   Gli schemi sono le cartelle di `docs/it/dbzero/`: uno schema nuovo
#   entra da solo appena ha la sua doc.
#
# ── DOVE CERCA ───────────────────────────────────────────────────────
#   * le guide             `docs/it/guide/*.md`
#   * le note di dominio   `docs/it/dbzero/<schema>/_*.md`
#   * le pagine manual/    `docs/it/dbzero/*/manual`, `docs/it/backend/*/manual`
#   Una guida che linka una pagina `backend/.../manual/` trovata per
#   endpoint conta come coinvolta anche se non nomina l'oggetto DB.
#
# ── ⚠️ QUELLO CHE NON PUO' FARE ──────────────────────────────────────
#   Trova le guide che NOMINANO un oggetto. Una guida che descrive il
#   concetto senza citare la tabella o l'endpoint le sfugge: per questo
#   l'header «Vedi anche» di ogni guida elenca gli oggetti che descrive
#   (standard-guide.md). L'elenco e' il punto di partenza della lettura,
#   non il suo confine; e l'esito di ogni guida (coerente / guida indietro /
#   sviluppo che la contraddice) lo decide chi legge, non lo script.
#
# Uso:
#   scripts/guide_coinvolte.py                      # lavoro non committato
#   scripts/guide_coinvolte.py --base origin/main   # diff da un ref al working tree
#   scripts/guide_coinvolte.py <file>...            # file indicati
#   scripts/guide_coinvolte.py --oggetti magazzino.movimenti vendite.ddt
#   scripts/guide_coinvolte.py ... --tutte          # anche le pagine manual/
# ------------------------------------------------------------
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
DOCS = RADICE / "docs" / "it"
GUIDE = DOCS / "guide"
DBZERO = DOCS / "dbzero"
BACKEND_DOC = DOCS / "backend"

# Schemi che non descrivono un dominio: i loro nomi qualificati sono rumore.
SCHEMI_ESCLUSI = {"public", "tools", "topology", "maintenance"}

ESTENSIONI_LETTE = {".yaml", ".yml", ".sql", ".py", ".vue", ".ts", ".js", ".md", ".csv"}


def schemi() -> list[str]:
    return sorted(
        p.name for p in DBZERO.iterdir()
        if p.is_dir() and not p.name.startswith((".", "_")) and p.name not in SCHEMI_ESCLUSI
    )


def regex_oggetti(nomi_schema: list[str]) -> re.Pattern[str]:
    alt = "|".join(map(re.escape, nomi_schema))
    # schema.oggetto | schema"."oggetto | /dbzero/schema/<tipo>/oggetto
    return re.compile(
        rf'(?<![A-Za-z0-9_])(?:/dbzero/)?({alt})(?:\.|"\."|/(?:tabelle|funzioni|views)/)([a-z_][a-z0-9_]*)'
    )


RE_API = re.compile(r"/api/v1/([a-z0-9-]+)/([a-z0-9-]+)/")


def file_del_perimetro(base: str | None) -> list[Path]:
    def git(*args: str) -> list[str]:
        out = subprocess.run(["git", *args], cwd=RADICE, capture_output=True, text=True, check=True)
        return [r for r in out.stdout.splitlines() if r.strip()]

    nomi = set(git("diff", "--name-only", base or "HEAD"))
    nomi |= set(git("ls-files", "--others", "--exclude-standard"))
    return [RADICE / n for n in sorted(nomi)]


def estrai(testo: str, re_ogg: re.Pattern[str]) -> tuple[set[str], set[str]]:
    oggetti = {f"{s}.{o}" for s, o in re_ogg.findall(testo)}
    api = {f"/api/v1/{a}/{b}/" for a, b in RE_API.findall(testo)}
    return oggetti, api


def leggi(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(RADICE))
    except ValueError:
        return str(p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", nargs="*", help="file del perimetro (vuoto = lavoro non committato)")
    ap.add_argument("--base", help="ref da cui prendere il diff (al working tree)")
    ap.add_argument("--oggetti", nargs="+", default=[], help="oggetti schema.nome da cercare")
    ap.add_argument("--tutte", action="store_true", help="elenca anche le pagine manual/")
    a = ap.parse_args()

    re_ogg = regex_oggetti(schemi())

    oggetti: set[str] = set(a.oggetti)
    api: set[str] = set()
    ingressi: list[Path] = []
    if a.file:
        ingressi = [Path(f).resolve() for f in a.file]
    elif not a.oggetti:
        ingressi = file_del_perimetro(a.base)

    for p in ingressi:
        if p.suffix in ESTENSIONI_LETTE and p.is_file():
            o, e = estrai(leggi(p), re_ogg)
            oggetti |= o
            api |= e

    if not oggetti and not api:
        print("Nessun oggetto DB né endpoint nel perimetro: niente da confrontare.")
        return 0

    ingressi_set = {p.resolve() for p in ingressi}
    guide = sorted(GUIDE.glob("*.md"))
    note = sorted(DBZERO.glob("*/_*.md"))
    manual = sorted(DBZERO.glob("*/manual/*.md")) + sorted(BACKEND_DOC.glob("*/manual/*.md"))

    # Pagine backend manual/ che documentano gli endpoint toccati: una guida
    # che le linka e' coinvolta anche senza nominare l'oggetto DB.
    pagine_api: dict[str, set[str]] = defaultdict(set)
    if api:
        for p in sorted(BACKEND_DOC.glob("*/manual/*.md")):
            t = leggi(p)
            for e in api:
                if e in t:
                    area = p.parent.parent.name
                    pagine_api[f"/backend/{area}/manual/{p.stem}"].add(e)

    def colpi(p: Path) -> set[str]:
        t = leggi(p)
        trovati = {f"{s}.{o}" for s, o in re_ogg.findall(t)} & oggetti
        trovati |= {e for e in api if e in t}
        for link, endpoint in pagine_api.items():
            if link in t:
                trovati |= endpoint
        return trovati

    def sezione(titolo: str, pagine: list[Path]) -> set[str]:
        righe = []
        coperti: set[str] = set()
        for p in pagine:
            if p.resolve() in ingressi_set:
                continue
            c = colpi(p)
            if c:
                righe.append((len(c), rel(p), sorted(c)))
                coperti |= c
        print(f"\n## {titolo} ({len(righe)})")
        if not righe:
            print("  nessuna")
        for n, nome, c in sorted(righe, key=lambda r: (-r[0], r[1])):
            mostra = ", ".join(c[:6]) + (f", … (+{len(c) - 6})" if len(c) > 6 else "")
            print(f"  {n:>3}  {nome}\n       {mostra}")
        return coperti

    print(f"Oggetti DB nel perimetro: {len(oggetti)} · endpoint: {len(api)}")
    coperti = sezione("Guide", guide)
    coperti |= sezione("Note di dominio (dbzero/<schema>/_*.md)", note)
    if a.tutte:
        sezione("Pagine manual/", manual)

    orfani = sorted((oggetti | api) - coperti)
    print(f"\n## Nomi che nessuna guida né nota di dominio cita ({len(orfani)})")
    print("  " + (", ".join(orfani) if orfani else "nessuno"))
    print(
        "\nPer ogni guida e nota trovata l'analisi scrive l'esito: coerente · guida indietro "
        "(si aggiorna nello stesso giro) · lo sviluppo la contraddice (cambio di modello: decide Tid)."
        "\nUn nome orfano che è un concetto del dominio, e non un dettaglio interno, segnala "
        "una guida che manca o un «Vedi anche» incompleto."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
