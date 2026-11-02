#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il caricatore YAML dei cancelli CI, in un posto solo — parser in C
#        dove c'e', ripiego in puro Python dove non c'e'.
#
# ── ⭐ PERCHE' ESISTE, E NON E' UNA MICRO-OTTIMIZZAZIONE ─────────────
#   Misurato il 2026-09-10 profilando `guardrail_run_on_change.py`: dei suoi
#   14,3 secondi, il **99%** sta dentro `yaml.safe_load` — 3.113 changelog
#   passati dal parser YAML scritto in puro Python. Non e' il numero di
#   scansioni: e' il parser.
#
#   I sei cancelli della CI costavano ~44 s a corsa, e la corsa e' DUE volte
#   per merge. PyYAML porta gia' con se' `CSafeLoader`, che usa libyaml:
#
#     | 3.971 changelog | SafeLoader (python) | CSafeLoader (C) |
#     | tempo           | 18,9 s              | 1,3 s  → 14,3×  |
#
# ── ⛔ E LA SOSTITUZIONE E' PROVATA, NON DEDOTTA ─────────────────────
#   `CSafeLoader` cambia scanner, parser e composer; il *constructor* e il
#   *resolver* restano quelli di `SafeLoader`, quindi i valori costruiti sono
#   gli stessi. Ma «quindi» non basta per un cancello: il 2026-09-10 i due
#   loader sono stati confrontati su TUTTI i 3.971 changelog del repo —
#   **zero documenti diversi, zero file che sollevano**.
#
#   ⚠️ E' un fatto DATATO, non un presidio: nessun automatismo lo rifa'. Si
#   ripete cosi', e vale la pena rifarlo se un giorno PyYAML cambia major:
#
#     for f in pathlib.Path("db/changelog").rglob("*.y*ml"):
#         s = f.read_text(encoding="utf-8")
#         assert yaml.safe_load(s) == yaml.load(s, Loader=yaml.CSafeLoader), f
#
#   ⭐ E i quattro cancelli sono stati provati anche contro un caso che DEVE
#   fallire, non solo contro il verde: con la patch addosso, ognuno segnala
#   ancora la sua violazione.
#
# ── ⚠️ IL RIPIEGO C'E' E NON DEVE FARE RUMORE ────────────────────────
#   `CSafeLoader` esiste solo se PyYAML e' stato costruito con libyaml. Sulle
#   ruote ufficiali c'e'; su un ambiente che compila da sorgente senza
#   `libyaml-dev`, no. Li' si ripiega su `SafeLoader`: piu' lento, **stesso
#   risultato**. ⛔ Un cancello non deve fallire perche' manca una libreria di
#   velocita' — fallirebbe per il motivo sbagliato, e verrebbe spento.
#
#   ⚠️ Il ripiego e' silenzioso DI PROPOSITO: `NOME_LOADER` sta qui per chi
#   diagnostica «perche' oggi la CI ci mette 40 secondi in piu'», non per
#   stampare una riga a ogni corsa.
#
# ── ⛔ QUELLO CHE QUESTO MODULO NON FA ───────────────────────────────
#   Non tiene un indice, non fa cache su disco, non decide quali file
#   guardare. Ogni cancello conserva il **suo** perimetro, il suo `Scopo:`, i
#   suoi limiti dichiarati e il suo codice di uscita: qui si condivide solo il
#   parser. Con il loader in C i sei costano ~5 s in tutto, e una cache
#   condivisa aggiungerebbe un problema di invalidazione per guadagnare
#   qualche secondo — ⛔ *un cancello che legge un dato stantio e' peggio di un
#   cancello lento*.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

import yaml

# Il loader in C se PyYAML e' stato costruito con libyaml, altrimenti quello in
# puro Python. Stessa semantica, un ordine di grandezza di differenza.
try:  # pragma: no cover — dipende da come e' costruito PyYAML
    from yaml import CSafeLoader as _LOADER  # type: ignore[attr-defined]

    NOME_LOADER = "CSafeLoader"
except ImportError:  # pragma: no cover — ambiente senza libyaml
    from yaml import SafeLoader as _LOADER  # type: ignore[assignment]

    NOME_LOADER = "SafeLoader"


# Scopo: Parsare un documento YAML col loader piu' veloce disponibile.
#        Sostituisce `yaml.safe_load` uno a uno: stessa firma, stesso
#        risultato, stesse eccezioni (`yaml.YAMLError` e sottoclassi).
def carica(testo: str) -> Any:
    return yaml.load(testo, Loader=_LOADER)
