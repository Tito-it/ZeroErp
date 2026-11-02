# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio delle CLASSI MORTE del frontend — i token statici di
#        `class="..."` nei template Vue che nessun foglio definisce.
# Note: ⭐ Nasce il 2026-09-17, dopo tre passate che hanno trovato 21 utility
#       PrimeFlex mai installate (`w-full` in 245 punti), due classi del
#       progetto MAI SCRITTE (`app-text-muted`, `form-field-wide`) e 26
#       identificatori orfani. Una classe che non sta in nessun foglio non fa
#       niente e non lo dice: il testo «sottotono» era testo normale in 135
#       siti, e nessuno l'ha visto perche' il difetto TOGLIE un colore, non ne
#       aggiunge uno. Il presidio tiene il conto a ZERO.
#       ⚠️ Guarda i soli attributi STATICI (`class="..."` preceduto da spazio):
#       `:class` e le prop `*-class` sono espressioni, e un nome dentro un
#       ternario non e' un token da contare. ⚠️ Una classe «definita» e' un
#       nome che compare come selettore `.nome` in QUALUNQUE foglio o
#       `<style>` — anche scoped in un altro componente (falso negativo
#       possibile: la rilettura del 17/09 ha trovato cosi' `font-bold`,
#       definita scoped in un file e usata in altri otto). Le classi di
#       PrimeVue (`p-*`) e PrimeIcons (`pi`, `pi-*`) arrivano da fuori e non
#       si contano.
#       Esce 1 se trova qualcosa: e' un cancello, non un report.
# ------------------------------------------------------------

from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "frontend" / "src"

_STYLE = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
_TEMPLATE = re.compile(r"<template>(.*)</template>", re.S)
_SELECTORE = re.compile(r"\.([A-Za-z_][\w-]*)")
_CLASS_STATICA = re.compile(r'(?<=\s)class="([^"]*)"')


# Scopo: ogni nome che compare come selettore `.nome` nei fogli e negli <style>.
def classi_definite() -> set[str]:
    css = "".join(Path(f).read_text() for f in glob.glob(f"{ROOT}/**/*.css", recursive=True))
    for f in glob.glob(f"{ROOT}/**/*.vue", recursive=True):
        css += "".join(m.group(1) for m in _STYLE.finditer(Path(f).read_text()))
    return set(_SELECTORE.findall(css))


# Scopo: `True` per le classi che arrivano da PrimeVue/PrimeIcons.
def esterna(nome: str) -> bool:
    return nome == "pi" or nome.startswith(("p-", "pi-"))


# Scopo: le classi statiche non definite, con i file che le usano.
def classi_morte() -> dict[str, set[str]]:
    definite = classi_definite()
    morte: dict[str, set[str]] = {}
    for f in sorted(glob.glob(f"{ROOT}/**/*.vue", recursive=True)):
        tpl = _TEMPLATE.search(Path(f).read_text())
        if not tpl:
            continue
        for m in _CLASS_STATICA.finditer(tpl.group(1)):
            for c in m.group(1).split():
                if not esterna(c) and c not in definite:
                    morte.setdefault(c, set()).add(str(Path(f).relative_to(ROOT.parent.parent)))
    return morte


# Scopo: stampa l'elenco ed esce 1 se non e' vuoto.
def main() -> int:
    morte = classi_morte()
    if not morte:
        print("[ok] nessuna classe statica non definita nei template")
        return 0
    print(f"[KO] {len(morte)} classi usate nei template e definite in nessun foglio:")
    for nome, files in sorted(morte.items(), key=lambda x: (-len(x[1]), x[0])):
        print(f"  {nome}  ({len(files)} file)  es. {sorted(files)[0]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
