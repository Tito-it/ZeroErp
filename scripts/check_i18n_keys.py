#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Zero ERP - guard chiavi i18n
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# ------------------------------------------------------------
# Scopo: rendere RUMOROSO un errore che per sua natura e' silenzioso.
# Una chiave i18n non risolta non produce un errore a runtime: produce
# testo mancante. E' cosi' che le reason del push ordini sono rimaste
# invisibili per un mese e mezzo (brief-db-i18n-namespace-reason-ordini).
#
# Controlla cinque cose:
#   0) VUOTE       - chiavi PRESENTI ma senza testo. Erano il buco: il guard
#                    registrava per presenza, quindi una stringa vuota passava
#                    ogni controllo mentre a video il testo spariva lo stesso.
#                    E' errore per le chiavi emesse dal DB (li' il database
#                    promette un messaggio), avviso altrove: una cella vuota
#                    puo' essere voluta, es. l'intestazione di una colonna
#                    azioni. Trovato dal team DB il 2026-08-10 misurando un
#                    rilievo BE (brief vie d'uscita §12.5-bis).
#   1) ROTTE       - chiavi citate nel codice ma assenti dai locales
#   2) PARITA'     - chiavi in it.json ma non in en.json (o viceversa).
#                    ⚠️ Le due direzioni NON sono simmetriche: il fallback e'
#                    l'italiano, quindi manca-in-en degrada a testo italiano
#                    leggibile, manca-in-it mostra la CHIAVE GREZZA. Il
#                    messaggio lo dice, perche' «parita' violata» suonava come
#                    una simmetria da sistemare con calma.
#   3) RADICI      - radici di dominio in cima, che violano la convenzione
#                    di docs/it/dev/frontend/frontend-standards.md (Multilingua)
#   4) EMISSIONI DB - chiavi emesse dalle funzioni (label_key/reason_key)
#                    e assenti dai locales: e' la classe di difetto che ha
#                    colpito offerte e ordini, invisibile dal solo frontend.
#                    Tre sorgenti, non una: il corpo delle funzioni nella doc
#                    auto-gen, il `meta` jsonb dei seed transizioni_stati_* E,
#                    dal 2026-09-19, la COLONNA `etichetta_key` dei CSV di
#                    seed (i vocabolari etichettati riga per riga:
#                    tipi_entita, eventi_dominio, registri_giornale).
#                    Il difetto offerte di maggio viveva per meta' nel CSV
#                    (addendum-db-stati-doc-offerte-transizioni-label-key):
#                    guardare solo le funzioni ne intercetterebbe una meta'.
#                    ⚠️ La terza sorgente era un buco fino al 19-09: le
#                    chiavi di `tipi_entita` ed `eventi_dominio` erano nei
#                    locales perche' scritte a mano, non perche' presidiate.
#   5) DUPLICATE   - chiavi definite DUE VOLTE nello stesso oggetto (2026-08-26).
#                    In JSON e' lecito e ogni parser tiene l'ULTIMA: la prima e'
#                    morta, senza errori e senza test rossi.
#                    ⛔ E questo cancello era CIECO al proprio difetto: faceva
#                    `json.load`, cioe' leggeva il dizionario gia' collassato —
#                    guardava il RISULTATO invece del difetto. Serve un
#                    `object_pairs_hook`, che vede le coppie prima che si
#                    schiaccino.
#                    Caso reale: `vendite.lotti.numera_esito` definita due volte
#                    con DUE consumatori dai contratti diversi — la numerazione
#                    di massa passava `{numerati}` e riceveva la frase del
#                    singolo lotto, perdendo il conteggio a video.
#
# In Python e non in JS di proposito: gira ovunque ci sia Python, quindi
# anche sul server DB dove non e' installato Node.
#
# Uso:  python3 scripts/check_i18n_keys.py [--strict-roots]
#       exit 0 = pulito, exit 1 = problemi (usabile in CI / pre-commit)
# ------------------------------------------------------------
"""Guard chiavi i18n: rotte, parita' it/en, radici, emissioni DB, duplicate."""

import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "frontend", "src")
LOCALES = os.path.join(SRC, "locales")
DBDOCS = os.path.join(ROOT, "docs", "it", "dbzero")
# Seed di stato: il `meta` jsonb porta le label_key dei pulsanti di cambio
# stato e la `nessuna_azione_key` degli stati, emesse verso l'utente esattamente
# come quelle scritte nel corpo delle capability. I CSV vivono nella
# sottocartella dello schema che possiede la tabella: quasi tutti sotto
# `config/`, ma quelli di tabelle non-config (es. `vendite.stati_commessa`)
# stanno sotto la cartella dello schema. Si scandisce quindi l'intero albero
# `80_data/sql`, non la sola `config/` (il caso commessa di luglio 2026).
#
# ⚠️ E si scandisce **ogni** CSV, senza filtrare per nome file. Il filtro
# precedente ammetteva i soli `transizioni_stati_*` e `stati_doc_*`, e per il
# secondo passaggio del caso commessa e' stato di nuovo cieco: la tabella degli
# stati della commessa e' `vendite.stati_commessa`, che non ha il segmento
# `doc`, quindi le sue due `nessuna_azione_key` non sono mai state guardate — un
# verde per sottrazione, la stessa forma di difetto gia' pagata due volte su
# questo stesso presidio. La convenzione di nome non e' una garanzia: il criterio
# e' il **contenuto**, cioe' `RE_SEED_KEY`, che e' gia' abbastanza specifico
# (nome della proprieta' + valore puntato). Scandire tutti i 206 CSV
# dell'albero costa qualche decina di ms su mezzo secondo di guard.
SEED = os.path.join(ROOT, "db", "changelog", "migrations_v2", "80_data", "sql")

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
# Nomi delle proprieta' che portano un indirizzo i18n dal DB al frontend.
# `nessuna_azione_key` (2026-08-04, brief-db-vie-uscita-operatore §4) e' la
# terza: vive nel `meta` degli STATI (non delle transizioni) e spiega perche' da
# quello stato non c'e' nessuna azione da azionare. Senza di lei qui, quelle
# quattro chiavi sarebbero rimaste invisibili al guard — la stessa classe di
# difetto che il guard esiste per intercettare.
_PROP_KEY = "label_key|reason_key|nessuna_azione_key"

# Chiavi emesse dal DB nelle doc auto-gen delle funzioni.
# Il valore DEVE contenere un punto e stare sulla stessa riga: senza questi due
# vincoli il match scavalca il fine riga e aggancia la chiave jsonb successiva
# (`'label_key', t.meta->>'label_key',` + a capo + `'severity',` -> "severity").
RE_DB_KEY = re.compile(
    rf"""['"](?:{_PROP_KEY})['"][^\S\n]*,[^\S\n]*'(\w+(?:\.\w+)+)'""")
RE_DB_ASSIGN = re.compile(
    r"""_(?:reason|label|azione)_key\s*:?=\s*'(\w+(?:\.\w+)+)'""")
# Seed CSV: JSON dentro CSV, quindi virgolette raddoppiate.
RE_SEED_KEY = re.compile(rf'""(?:{_PROP_KEY})""\s*:\s*""(\w+(?:\.\w+)+)""')


def flatten_valori(obj, prefisso="", out=None):
    """Appiattisce l'albero delle traduzioni in {chiave puntata: valore}.

    Tenere il VALORE, non la sola presenza, e' il punto: distingue «tradotta»
    da «presente e vuota». La versione storica (`flatten`) registrava per
    presenza in un set: una chiave con stringa vuota era indistinguibile da
    una tradotta, e passava ogni controllo — la parita' it/en la vedeva
    integra, le rotte non la vedevano affatto. E' la stessa classe di difetto
    che questo guard esiste per rendere rumorosa — testo che sparisce senza
    errore — su una strada che i controlli non attraversavano. Misurato dal
    team DB il 2026-08-10 (brief vie d'uscita §12.5-bis). I set di chiavi si
    derivano da qui (`set(flatten_valori(...))`), una sola discesa.
    """
    if out is None:
        out = {}
    for k, v in obj.items():
        key = f"{prefisso}.{k}" if prefisso else k
        if isinstance(v, dict):
            flatten_valori(v, key, out)
        else:
            out[key] = v
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
    """File sorgente FE, esclusi i locales stessi e i test."""
    for dirpath, dirnames, filenames in os.walk(SRC):
        dirnames[:] = [d for d in dirnames if d not in ("locales", "node_modules")]
        for f in filenames:
            # ⚠️ Gli spec non vanno nel bundle, e le loro chiavi sono FIXTURE:
            #    un test del ripiego fail-visible cita apposta una chiave che
            #    non esiste (`useDrawerActions.spec.js`). Leggerli qui farebbe
            #    del guard un cancello rosso su un comportamento voluto.
            if f.endswith((".spec.js", ".test.js")):
                continue
            if f.endswith((".vue", ".js")):
                yield os.path.join(dirpath, f)


# Scopo: carica un locale e SEGNALA le chiavi definite due volte nello stesso
#        oggetto JSON.
# ⛔ Perche' serve un hook e non basta `json.load`: in JSON un oggetto con la
#    stessa chiave due volte e' *lecito*, e ogni parser tiene l'ULTIMA — sia
#    `json.load` qui, sia `JSON.parse` nel browser. Quindi la prima definizione
#    e' morta e nessuno se ne accorge: niente errore, niente test rosso, solo una
#    frase che a video non e' quella che si legge nel file.
#    ⚠️ Fino al 2026-08-26 questo cancello era CIECO proprio perche' faceva
#    `json.load`: leggeva il dizionario gia' collassato, cioe' guardava il
#    risultato del difetto invece del difetto. Caso reale trovato quel giorno:
#    `vendite.lotti.numera_esito` definita due volte, con DUE consumatori dai
#    contratti diversi — la numerazione di massa passava `{numerati}` e riceveva
#    la frase del singolo lotto, perdendo il conteggio.
# ⚠️ E il difetto NON si vede da una ricerca testuale del nome: le due
#    definizioni possono stare a cinquanta righe di distanza, ed essere
#    entrambe legittime se gli oggetti che le contengono sono diversi. A
#    decidere e' l'annidamento, che solo il parser conosce.
def carica_locale(path):
    duplicati = []

    def hook(coppie):
        visti = set()
        for chiave, _ in coppie:
            if chiave in visti:
                duplicati.append(chiave)
            visti.add(chiave)
        return dict(coppie)

    with open(path, encoding="utf-8") as fh:
        return json.load(fh, object_pairs_hook=hook), duplicati


def main():
    it, dupli_it = carica_locale(os.path.join(LOCALES, "it.json"))
    en, dupli_en = carica_locale(os.path.join(LOCALES, "en.json"))
    valori_it, valori_en = flatten_valori(it), flatten_valori(en)
    chiavi_it, chiavi_en = set(valori_it), set(valori_en)
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

    # Seconda sorgente: i seed. Le label_key delle TRANSIZIONI vivono nel `meta`
    # jsonb e finiscono all'utente come etichette dei pulsanti di cambio stato;
    # la `nessuna_azione_key` degli STATI e' il testo che spiega in che stato si
    # trova il documento. Entrambe valgono quanto quelle scritte nelle funzioni,
    # e per un giorno solo le prime erano guardate: guardare i soli
    # `transizioni_stati_*` lasciava fuori proprio il caso «nessuna azione»,
    # dove il testo mancante non lascia nemmeno un pulsante muto a segnalare che
    # qualcosa c'era. Il filtro per nome file e' caduto del tutto (vedi SEED):
    # decide `RE_SEED_KEY`, cioe' il contenuto.
    if os.path.isdir(SEED):
        for dirpath, _dirs, files in os.walk(SEED):
            for f in sorted(files):
                if not f.endswith(".csv"):
                    continue
                path = os.path.join(dirpath, f)
                with open(path, encoding="utf-8") as fh:
                    testo = fh.read()
                rel = os.path.relpath(path, ROOT)
                for m in RE_SEED_KEY.finditer(testo):
                    db_keys.setdefault(m.group(1), set()).add(rel)

    # ⭐ Quarta sorgente (2026-09-19): la colonna `etichetta_key` dei CSV di
    # seed — i vocabolari che il DB etichetta riga per riga (`config.tipi_entita`,
    # `config.eventi_dominio`, `config.registri_giornale`) e che il frontend
    # rende con `labelOrCode`. ⛔ Non e' JSON dentro una cella, quindi
    # `RE_SEED_KEY` non la vedeva: le chiavi delle prime due sono nei locales
    # perche' qualcuno le ha scritte a mano, e la prossima riga di catalogo
    # sarebbe rimasta senza testo in silenzio — il codice macchina a video, con
    # il guard verde (brief-db-registri-giornale-catalogo §4.2/§8.4). Stessa
    # classe di buco delle intestazioni di colonna (`etichetta_i18n_key`).
    # ⚠️ TUTTE le righe, ritirate comprese (`obsoleto_dal`): una riga vecchia
    # del diario porta ancora la sua chiave, e va letta.
    # ⚠️ Solo la colonna che si chiama ESATTAMENTE `etichetta_key`: quella del
    # catalogo liste (`etichetta_i18n_key`) ha la sua sorgente qui sotto, con
    # la sua regola (`attivo`).
    if os.path.isdir(SEED):
        for dirpath, _dirs, files in os.walk(SEED):
            for f in sorted(files):
                if not f.endswith(".csv"):
                    continue
                path = os.path.join(dirpath, f)
                with open(path, newline="", encoding="utf-8") as fh:
                    lettore = csv.DictReader(fh)
                    if "etichetta_key" not in (lettore.fieldnames or ()):
                        continue
                    rel = os.path.relpath(path, ROOT)
                    for riga in lettore:
                        chiave = (riga.get("etichetta_key") or "").strip()
                        if chiave and chiave.upper() != "NULL":
                            db_keys.setdefault(chiave, set()).add(rel)

    # ⭐ Terza sorgente: le INTESTAZIONI DI COLONNA del catalogo liste
    # (`ui.lista_colonna.etichetta_i18n_key`). Non sono scritte nel frontend
    # (nessun `t('...')` da grepare) e non sono JSON dentro un `meta`, quindi
    # non le vedeva NESSUNO dei due controlli sopra: erano il punto cieco piu'
    # grande del guard — 506 chiavi su 47 liste.
    # ⚠️ Perche' contano: quando la chiave manca, l'intestazione ripiega
    # sull'`etichetta` italiana del seed E NON DICE NIENTE (il frontend usa
    # `te()` prima di tradurre). Il difetto si vede solo cambiando lingua e
    # rileggendo le intestazioni — che e' esattamente come e' stato trovato,
    # a occhio, il 2026-08-22.
    colonne_keys = {}
    _catalogo_csv = os.path.join(SEED, "ui", "lista_colonna.csv")
    if os.path.isfile(_catalogo_csv):
        rel = os.path.relpath(_catalogo_csv, ROOT)
        with open(_catalogo_csv, newline="", encoding="utf-8") as fh:
            for riga in csv.DictReader(fh):
                if riga.get("attivo") != "t":
                    continue
                chiave = (riga.get("etichetta_i18n_key") or "").strip()
                # `null` in ogni grafia e' NULL per il caricatore Liquibase (il
                # `nullValue:` dei caricatori non esiste, brief-db-token-null-dei-seed
                # §1): e' l'assenza della chiave, non una chiave.
                if chiave and chiave.lower() != "null":
                    colonne_keys.setdefault(chiave, set()).add(rel)

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

    # ⛔ Le chiavi definite DUE VOLTE nello stesso oggetto. Vince l'ultima, la
    #    prima e' morta, e il file mostra una frase che a video non compare.
    if dupli_it or dupli_en:
        problemi += len(dupli_it) + len(dupli_en)
        print(f"\n[X] {len(dupli_it) + len(dupli_en)} CHIAVI DEFINITE DUE VOLTE nello stesso oggetto")
        print("    In JSON vince l'ultima: la prima e' morta e non da' nessun errore.")
        print("    Se i consumatori sono due con contratti diversi, uno riceve la")
        print("    frase dell'altro — e un segnaposto che non compare non si vede.")
        for lang, dupli in (("it.json", dupli_it), ("en.json", dupli_en)):
            for k in sorted(set(dupli)):
                print(f"    {lang}: {k}")
    else:
        print("[ok] nessuna chiave definita due volte")

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

    colonne_rotte = sorted((k, v) for k, v in colonne_keys.items() if k not in presenti)
    if colonne_rotte:
        problemi += len(colonne_rotte)
        print(f"\n[X] {len(colonne_rotte)} INTESTAZIONI DI COLONNA senza traduzione")
        print("    Il catalogo liste dichiara la chiave, i locales non ce l'hanno:")
        print("    la colonna ripiega sull'etichetta italiana del seed, in silenzio.")
        for k, dove in colonne_rotte[:20]:
            print(f"    {k}")
            for d in sorted(dove)[:2]:
                print(f"       {d}")
        if len(colonne_rotte) > 20:
            print(f"    ... e altre {len(colonne_rotte) - 20}")
    else:
        print(f"[ok] tutte le {len(colonne_keys)} intestazioni di colonna sono tradotte")

    if solo_it or solo_en:
        problemi += len(solo_it) + len(solo_en)
        print(f"\n[X] PARITA' it/en violata: {len(solo_it)} solo in it, "
              f"{len(solo_en)} solo in en")
        # ⚠️ Le due colonne sono simmetriche, le CONSEGUENZE no: il
        # `fallbackLocale` e' l'italiano (DEFAULT_LOCALE = 'it'), quindi una
        # chiave che manca dall'inglese degrada a testo italiano — leggibile —
        # mentre una che manca dall'italiano non ha rete e mostra la CHIAVE
        # GREZZA all'operatore. Scriverlo qui perche' «parita' violata» si legge
        # come una simmetria da sistemare con calma, e per meta' dei casi non lo
        # e' (rilievo BE + misura team DB, 2026-08-10).
        if solo_en:
            print(f"\n    → {len(solo_en)} MANCANO DALL'ITALIANO ({len(solo_en)} "
                  "solo in en): l'operatore vede la CHIAVE GREZZA.")
            print("      Il fallback e' l'italiano stesso: qui non c'e' rete.")
            for k in solo_en[:15]:
                print(f"      {k}")
        if solo_it:
            print(f"\n    → {len(solo_it)} mancano dall'inglese ({len(solo_it)} "
                  "solo in it): degradano al testo italiano, leggibile.")
            for k in solo_it[:15]:
                print(f"      {k}")
    else:
        print("[ok] parita' it/en integra")

    # VUOTE - una chiave c'e' ma non dice niente. Vedi `flatten_valori`.
    # Il criterio NON e' «vuoto = errore» ovunque: `anagrafiche.soggetti.col_azioni`
    # e' vuota in entrambi i locales e con ogni probabilita' di proposito
    # (intestazione di una colonna di azioni). E' errore dove il DATABASE
    # promette un messaggio — le chiavi emesse dalle funzioni e dai seed: li'
    # una stringa vuota e' una promessa non mantenuta, e l'operatore resta
    # davanti al nulla esattamente come con la chiave mancante. Altrove e' un
    # avviso, perche' il vuoto puo' essere una scelta.
    def _vuota(valori, k):
        return k in valori and isinstance(valori[k], str) and not valori[k].strip()

    db_vuote = sorted(
        k for k in db_keys
        if _vuota(valori_it, k) or _vuota(valori_en, k)
    )
    altre_vuote = sorted(
        k for k in presenti
        if k not in db_keys and (_vuota(valori_it, k) and _vuota(valori_en, k))
    )
    if db_vuote:
        problemi += len(db_vuote)
        print(f"\n[X] {len(db_vuote)} CHIAVI EMESSE DAL DB con testo VUOTO")
        print("    La chiave c'e', quindi nessun altro controllo la vede: ma il")
        print("    database promette un messaggio e l'operatore non legge nulla.")
        for k in db_vuote[:15]:
            locali = [n for n, v in (("it", valori_it), ("en", valori_en)) if _vuota(v, k)]
            print(f"    {k}  (vuota in: {'+'.join(locali)})")
    else:
        print("[ok] nessuna chiave emessa dal DB e' vuota")

    if altre_vuote:
        print(f"\n[!] {len(altre_vuote)} chiavi vuote in ENTRAMBI i locales "
              "(non emesse dal DB): non bloccano.")
        print("    Possono essere volute (es. intestazione di una colonna azioni).")
        for k in altre_vuote[:10]:
            print(f"    {k}")

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
