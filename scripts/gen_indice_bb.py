#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Indice dei building block per Zero ERP
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Rilasciato sotto GNU AGPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------
# Scopo: generare, dai due cataloghi dei building block, un INDICE che si
#        legge per intero.
#
# Perche' esiste. I cataloghi (backend e frontend) sono la prima difesa contro
# le duplicazioni — regola del 2, .codex/AGENTS.md — ma una loro riga racconta
# anche la storia del building block, e i due file insieme non entrano in una
# sessione di lavoro. Chi non puo' leggerli li interroga per parola, e trova
# solo cio' di cui indovina il nome. L'indice porta, per ogni riga del catalogo,
# i nomi e l'inizio della descrizione: abbastanza per riconoscere «esiste gia'»,
# col numero di riga per aprire la voce intera.
#
# L'indice e' un DERIVATO: non si modifica a mano. Si corregge il catalogo e si
# rigenera. `--check` esce 1 se un indice non corrisponde al suo catalogo.
#
# Uso:
#   python3 scripts/gen_indice_bb.py           # rigenera i due indici
#   python3 scripts/gen_indice_bb.py --check   # verifica, senza scrivere
#
# Solo stdlib.
# ------------------------------------------------------------
from __future__ import annotations

import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent

# (catalogo, indice) — l'indice sta accanto al suo catalogo.
COPPIE = (
    (
        "docs/it/dev/backend/catalogo-building-block-backend.md",
        "docs/it/dev/backend/indice-building-block-backend.md",
    ),
    (
        "docs/it/dev/frontend/catalogo-building-block-frontend.md",
        "docs/it/dev/frontend/indice-building-block-frontend.md",
    ),
)

# Lunghezza a cui si taglia l'inizio della descrizione.
TAGLIO_DESCRIZIONE = 90

_SEPARATORE_CELLE = re.compile(r"(?<!\\)\|")
_RIGA_DI_TRATTINI = re.compile(r"^\|[\s:|-]+\|?\s*$")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_DATA_FRA_PARENTESI = re.compile(r"^\(\s*\d{4}-\d{2}-\d{2}[^)]*\)\s*")
_SPAZI = re.compile(r"\s+")


def _celle(riga: str) -> list[str]:
    corpo = riga.strip()
    if corpo.startswith("|"):
        corpo = corpo[1:]
    if corpo.endswith("|") and not corpo.endswith("\\|"):
        corpo = corpo[:-1]
    return [c.strip() for c in _SEPARATORE_CELLE.split(corpo)]


def _testo_piano(testo: str) -> str:
    """Toglie la veste markdown che nell'indice e' solo rumore."""
    testo = _LINK.sub(r"\1", testo)
    for segno in ("**", "⭐", "⛔", "⚠️"):
        testo = testo.replace(segno, "")
    return _SPAZI.sub(" ", testo).strip()


def _inizio_descrizione(testo: str) -> str:
    testo = _testo_piano(testo)
    # Una descrizione che apre con la data dell'estrazione direbbe solo quella.
    testo = _DATA_FRA_PARENTESI.sub("", testo)
    if len(testo) <= TAGLIO_DESCRIZIONE:
        return testo
    taglio = testo.rfind(" ", 0, TAGLIO_DESCRIZIONE)
    if taglio <= 0:
        taglio = TAGLIO_DESCRIZIONE
    return testo[:taglio].rstrip(" ,;:(") + "…"


def costruisci_indice(catalogo: Path) -> str:
    righe = catalogo.read_text(encoding="utf-8").splitlines()
    titolo = next((r[2:].strip() for r in righe if r.startswith("# ")), catalogo.name)
    uscita = [
        f"# Indice — {titolo}",
        "",
        "> ⛔ **File generato: non si modifica a mano.** Si corregge",
        f"> [{catalogo.name}]({catalogo.name}) e si rigenera con",
        "> `python3 scripts/gen_indice_bb.py`.",
        ">",
        "> Una riga per ogni riga del catalogo: `L<riga>` è il numero di riga nel",
        "> catalogo, dove stanno firma, regole d'uso e storia. **Questo file si legge",
        "> per intero** prima di scrivere logica nuova; del catalogo si apre solo la",
        "> riga che serve (`sed -n '<riga>p'`).",
        "",
    ]
    voci = 0
    in_tabella = False
    in_recinto = False
    for numero, riga in enumerate(righe, start=1):
        # Un blocco di codice recintato non e' catalogo: un commento `# ...`
        # d'esempio non e' un titolo, una riga `| a | b |` non e' una voce.
        if riga.lstrip().startswith("```"):
            in_recinto = not in_recinto
            in_tabella = False
            continue
        if in_recinto:
            continue
        if riga.startswith("#"):
            in_tabella = False
            if riga.startswith("##"):
                livello = len(riga) - len(riga.lstrip("#"))
                uscita += ["", f"{'#' * livello} {_testo_piano(riga.lstrip('#'))}", ""]
            continue
        if not riga.lstrip().startswith("|"):
            in_tabella = False
            continue
        if not in_tabella:
            # La prima riga di una tabella e' l'intestazione.
            in_tabella = True
            continue
        if _RIGA_DI_TRATTINI.match(riga.strip()):
            continue
        celle = _celle(riga)
        if len(celle) < 2 or not celle[0]:
            continue
        nome = _SPAZI.sub(" ", _LINK.sub(r"\1", celle[0]).replace("**", "")).strip()
        uscita.append(f"- L{numero} {nome} — {_inizio_descrizione(celle[-1])}")
        voci += 1
    # Righe vuote doppie: una sola.
    pulito: list[str] = []
    for riga in uscita:
        if riga == "" and pulito and pulito[-1] == "":
            continue
        pulito.append(riga)
    pulito += ["", f"<!-- voci: {voci} -->", ""]
    return "\n".join(pulito)


def main(argv: list[str]) -> int:
    verifica = "--check" in argv[1:]
    sconosciuti = [a for a in argv[1:] if a != "--check"]
    if sconosciuti:
        print(f"Argomento non riconosciuto: {sconosciuti[0]}", file=sys.stderr)
        return 2
    stantii = []
    for catalogo_rel, indice_rel in COPPIE:
        catalogo = RADICE / catalogo_rel
        indice = RADICE / indice_rel
        atteso = costruisci_indice(catalogo)
        attuale = indice.read_text(encoding="utf-8") if indice.exists() else None
        if attuale == atteso:
            continue
        if verifica:
            stantii.append(indice_rel)
        else:
            indice.write_text(atteso, encoding="utf-8")
            print(f"scritto {indice_rel}")
    if stantii:
        print(
            "Indice dei building block non allineato al catalogo:\n  "
            + "\n  ".join(stantii)
            + "\nRigenerare con: python3 scripts/gen_indice_bb.py",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
