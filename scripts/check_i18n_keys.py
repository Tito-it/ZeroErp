#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Zero ERP - guard chiavi i18n
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# ------------------------------------------------------------
# Scopo: rendere RUMOROSO un errore che per sua natura e' silenzioso.
# Una chiave i18n non risolta non produce un errore a runtime: produce
# testo mancante. E' cosi' che le reason del push ordini sono rimaste
# invisibili per un mese e mezzo (brief-db-i18n-namespace-reason-ordini).
#
# Controlla quattro cose:
#   1) ROTTE       - chiavi citate nel codice ma assenti dai locales
#   2) PARITA'     - chiavi in it.json ma non in en.json (o viceversa)
#   3) RADICI      - radici di dominio in cima, che violano la convenzione
#                    di docs/it/dev/frontend/frontend-standards.md (Multilingua)
#   4) EMISSIONI DB - chiavi emesse dalle funzioni (label_key/reason_key)
#                    e assenti dai locales: e' la classe di difetto che ha
#                    colpito offerte e ordini, invisibile dal solo frontend.
#                    Due sorgenti, non una: il corpo delle funzioni nella doc
#                    auto-gen E il `meta` jsonb dei seed transizioni_stati_*.
#                    Il difetto offerte di maggio viveva per meta' nel CSV
#                    (addendum-db-stati-doc-offerte-transizioni-label-key):
#                    guardare solo le funzioni ne intercetterebbe una meta'.
#
# In Python e non in JS di proposito: gira ovunque ci sia Python, quindi
# anche sul server DB dove non e' installato Node.
#
# Uso:  python3 scripts/check_i18n_keys.py [--strict-roots]
#       exit 0 = pulito, exit 1 = problemi (usabile in CI / pre-commit)
# ------------------------------------------------------------
"""Guard delle chiavi i18n: chiavi rotte, parita' it/en, radici, emissioni DB."""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "frontend", "src")
LOCALES = os.path.join(SRC, "locales")
DBDOCS = os.path.join(ROOT, "docs", "it", "dbzero")
# Seed delle transizioni di stato: il `meta` jsonb porta le label_key dei
# pulsanti di cambio stato, che sono emesse verso l'utente esattamente come
# quelle scritte nel corpo delle capability.
SEED = os.path.join(ROOT, "db", "changelog", "migrations_v2", "80_data", "sql", "config")

STRICT_ROOTS = "--strict-roots" in sys.argv

# Aree di dominio: cartelle di frontend/src/ che possono fare da radice.
AREE = {"vendite", "anagrafiche", "catalogo", "acquisti", "magazzino",
        "contabilita", "pagamenti", "pratiche", "documenti", "config",
        "amministrazione", "portale", "shop", "ui"}

# Radici trasversali ammesse in cima (vocabolario di interfaccia, non dominio).
# Vedi brief-i18n-radici-uniformi §2c. `lista` e `profile` erano radici morte
# (0 consumatori) rimosse a fine migrazione: NON reinserirle qui — la loro
# assenza fa sì che un'eventuale reintroduzione (es. `lista.{codice}.col_*`,
# decisione aperta in liste_def) venga segnalata come radice di dominio da
# ricondurre a un'area, coerente con lo standard.
TRASVERSALI = {"common", "errors", "validation", "actions", "confirm", "nav",
               "nav_menu", "pagination", "placeholder", "search", "tabs",
               "context", "lista_config", "export_dialog", "dash_mesi", "home",
               "auth", "sessions", "geo", "note", "ai", "config_panel",
               "dati_societari", "soggetto_ruolo_lookup", "indirizzi",
               "resolver", "istanza_utility", "billing_account",
               "notifications"}

# Posizioni di chiave nel codice FE: t('x') / $t('x') / te('x') / tm('x')
RE_T = re.compile(r"""(?<![\w$])\$?t[em]?\(\s*(['"`])([\w.]+)\1""")
# ...e le proprieta' label_key / reason_key valorizzate a stringa literal
RE_KEYPROP = re.compile(
    r"""\b(?:label_key|reason_key|labelKey|reasonKey)\s*[:=]\s*(['"`])([\w.]+)\1""")
# Chiave costruita dinamicamente: punto cieco, si segnala e non si valuta
RE_DINAMICA = re.compile(r"""(?<![\w$])\$?t[em]?\(\s*(?:(['"])[\w.]*\1\s*\+|`[^`]*\$\{)""")
# Chiavi emesse dal DB nelle doc auto-gen delle funzioni.
# Il valore DEVE contenere un punto e stare sulla stessa riga: senza questi due
# vincoli il match scavalca il fine riga e aggancia la chiave jsonb successiva
# (`'label_key', t.meta->>'label_key',` + a capo + `'severity',` -> "severity").
RE_DB_KEY = re.compile(
    r"""['"](?:label_key|reason_key)['"][^\S\n]*,[^\S\n]*'(\w+(?:\.\w+)+)'""")
RE_DB_ASSIGN = re.compile(r"""_(?:reason|label)_key\s*:?=\s*'(\w+(?:\.\w+)+)'""")
# Seed CSV: JSON dentro CSV, quindi virgolette raddoppiate.
RE_SEED_KEY = re.compile(r'""(?:label_key|reason_key)""\s*:\s*""(\w+(?:\.\w+)+)""')


def flatten(obj, prefisso="", out=None):
    """Appiattisce l'albero delle traduzioni in chiavi puntate."""
    if out is None:
        out = set()
    for k, v in obj.items():
        key = f"{prefisso}.{k}" if prefisso else k
        if isinstance(v, dict):
            flatten(v, key, out)
        else:
            out.add(key)
    return out


def spoglia_commenti(testo):
    """Neutralizza le righe di solo commento, conservando gli offset.

    I blocchi «Uso:» in testa ai componenti mostrano esempi di chiamata
    (`t('dominio.col_azioni')`, `t('...')`): sono didascalie, non chiavi, e
    segnalarle produce falsi positivi che a lungo andare fanno ignorare il
    guard. Si azzerano SOLO le righe interamente di commento: dentro una riga
    di codice un `//` puo' stare in una stringa (URL), e toglierlo li'
    nasconderebbe chiavi vere.
    Le righe sono sostituite da spazi di pari lunghezza cosi' i numeri di riga
    calcolati sugli offset restano corretti.
    """
    fuori = []
    for riga in testo.split("\n"):
        nuda = riga.lstrip()
        if nuda.startswith(("//", "*", "<!--", "#")):
            fuori.append(" " * len(riga))
        else:
            fuori.append(riga)
    return "\n".join(fuori)


def walk_src():
    """File sorgente FE, esclusi i locales stessi."""
    for dirpath, dirnames, filenames in os.walk(SRC):
        dirnames[:] = [d for d in dirnames if d not in ("locales", "node_modules")]
        for f in filenames:
            if f.endswith((".vue", ".js")):
                yield os.path.join(dirpath, f)


def main():
    with open(os.path.join(LOCALES, "it.json"), encoding="utf-8") as fh:
        it = json.load(fh)
    with open(os.path.join(LOCALES, "en.json"), encoding="utf-8") as fh:
        en = json.load(fh)
    chiavi_it, chiavi_en = flatten(it), flatten(en)
    presenti = chiavi_it | chiavi_en

    citate, dinamiche = {}, []
    for path in walk_src():
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8") as fh:
            testo = spoglia_commenti(fh.read())
        for regex in (RE_T, RE_KEYPROP):
            for m in regex.finditer(testo):
                chiave = m.group(2)
                if "." not in chiave:
                    continue          # non e' un path i18n
                riga = testo.count("\n", 0, m.start()) + 1
                citate.setdefault(chiave, []).append(f"{rel}:{riga}")
        for m in RE_DINAMICA.finditer(testo):
            riga = testo.count("\n", 0, m.start()) + 1
            dinamiche.append(f"{rel}:{riga}")

    # Chiavi emesse dal DB: si leggono dalla doc auto-gen, che riflette il vivo.
    db_keys = {}
    for dirpath, _dirs, files in os.walk(DBDOCS):
        if os.sep + "manual" in dirpath:
            continue                  # doc concettuale, non definizioni
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(dirpath, f)
            with open(path, encoding="utf-8") as fh:
                testo = fh.read()
            rel = os.path.relpath(path, ROOT)
            for m in RE_DB_KEY.finditer(testo):
                db_keys.setdefault(m.group(1), set()).add(rel)
            for m in RE_DB_ASSIGN.finditer(testo):
                db_keys.setdefault(m.group(1), set()).add(rel)

    # Seconda sorgente: i seed delle transizioni di stato. Le label_key vivono
    # nel `meta` jsonb e finiscono all'utente come etichette dei pulsanti di
    # cambio stato, quindi valgono quanto quelle scritte nelle funzioni.
    if os.path.isdir(SEED):
        for f in sorted(os.listdir(SEED)):
            if not (f.startswith("transizioni_stati_") and f.endswith(".csv")):
                continue
            path = os.path.join(SEED, f)
            with open(path, encoding="utf-8") as fh:
                testo = fh.read()
            rel = os.path.relpath(path, ROOT)
            for m in RE_SEED_KEY.finditer(testo):
                db_keys.setdefault(m.group(1), set()).add(rel)

    rotte = sorted((k, v) for k, v in citate.items() if k not in presenti)
    db_rotte = sorted((k, v) for k, v in db_keys.items() if k not in presenti)
    solo_it = sorted(chiavi_it - chiavi_en)
    solo_en = sorted(chiavi_en - chiavi_it)
    radici_sospette = sorted(r for r in it if r not in AREE and r not in TRASVERSALI)

    problemi = 0
    print(f"\ni18n guard - {len(citate)} chiavi citate nel FE, "
          f"{len(db_keys)} emesse dal DB, {len(chiavi_it)} in it.json, "
          f"{len(chiavi_en)} in en.json")

    if rotte:
        problemi += len(rotte)
        print(f"\n[X] {len(rotte)} CHIAVI ROTTE nel frontend (citate, assenti dai locales)")
        print("    Non danno errore a runtime: danno testo mancante.")
        for k, dove in rotte:
            print(f"    {k}")
            for d in dove[:3]:
                print(f"       {d}")
            if len(dove) > 3:
                print(f"       ... e altri {len(dove) - 3}")
    else:
        print("[ok] nessuna chiave rotta nel frontend")

    if db_rotte:
        problemi += len(db_rotte)
        print(f"\n[X] {len(db_rotte)} CHIAVI EMESSE DAL DB e assenti dai locales")
        print("    E' la classe di difetto di offerte e ordini: il DB manda un")
        print("    indirizzo che il frontend non sa risolvere, e il testo sparisce.")
        for k, dove in db_rotte:
            print(f"    {k}")
            for d in sorted(dove)[:2]:
                print(f"       {d}")
    else:
        print("[ok] nessuna chiave emessa dal DB risulta irrisolvibile")

    if solo_it or solo_en:
        problemi += len(solo_it) + len(solo_en)
        print(f"\n[X] PARITA' it/en violata: {len(solo_it)} solo in it, "
              f"{len(solo_en)} solo in en")
        for k in solo_it[:15]:
            print(f"    solo it: {k}")
        for k in solo_en[:15]:
            print(f"    solo en: {k}")
    else:
        print("[ok] parita' it/en integra")

    if radici_sospette:
        marc = "[X]" if STRICT_ROOTS else "[!]"
        print(f"\n{marc} {len(radici_sospette)} RADICI DI DOMINIO IN CIMA")
        print("    Convenzione: frontend-standards.md §Multilingua (dettaglio: i18n-namespace-radici.md)")
        print("    Attese sotto la loro area, es. preventivi.* -> vendite.preventivi.*")
        print(f"    {', '.join(radici_sospette)}")
        if STRICT_ROOTS:
            problemi += len(radici_sospette)
        else:
            print("    (avviso; usa --strict-roots per farlo fallire, a migrazione conclusa)")
    else:
        print("[ok] nessuna radice di dominio in cima")

    if dinamiche:
        print(f"\n[i] {len(dinamiche)} chiavi costruite dinamicamente - punto cieco:")
        for d in dinamiche[:10]:
            print(f"    {d}")
        if len(dinamiche) > 10:
            print(f"    ... e altre {len(dinamiche) - 10}")

    print(f"\n{'[X] ' + str(problemi) + ' problemi' if problemi else '[ok] tutto pulito'}\n")
    return 1 if problemi else 0


if __name__ == "__main__":
    sys.exit(main())
