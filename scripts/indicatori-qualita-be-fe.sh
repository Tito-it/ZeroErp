#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Scopo: stampare in un colpo gli indicatori di qualità di backend e frontend
#        descritti in docs/it/dev/qualita-be-fe-indicatori.md, letti dal repo
#        così com'è adesso.
#
# IL PROBLEMA CHE RISOLVE. Le valutazioni del 2026-09/10 rileggevano ogni volta
# gli stessi numeri con una decina di comandi scritti a mano, e ogni rilettura
# li riscriveva un po' diversi: un conteggio senza il suo comando non si
# confronta con quello del mese prima. Qui il comando È la definizione
# dell'indicatore; il documento dice che cosa significa e in che verso deve
# andare, non ricopia il valore.
#
# ⛔ Legge SOLO file del repo: niente database, niente rete, niente backend in
# esecuzione. ruff, mypy, i guard e la suite hanno già il loro cancello in CI;
# qui si leggono i registri che quei cancelli tengono, non si rilanciano.
#
# ⚠️ Sono letture di STRUTTURA (quali file esistono, cosa dichiarano), fatti
# datati: trovano gli errori, non decidono il progetto (regola zero, AGENTS.md).
#
# Uso:
#   scripts/indicatori-qualita-be-fe.sh          # tabella leggibile
#   scripts/indicatori-qualita-be-fe.sh --tsv    # area<TAB>indicatore<TAB>valore, per un diff
# ------------------------------------------------------------
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RADICE"

FORMATO="tabella"
case "${1:-}" in
  --tsv) FORMATO="tsv" ;;
  "") ;;
  *) echo "uso: $0 [--tsv]" >&2; exit 2 ;;
esac

# ⚠️ -I: lo script Python non deve importare niente dalla cartella corrente.
exec python3 -I - "$FORMATO" <<'PY'
import ast
import collections
import csv
import json
import re
import subprocess
import sys

FORMATO = sys.argv[1]
righe = []


# Scopo: registrare una misura sotto la sua area.
def misura(area, indicatore, valore):
    righe.append((area, indicatore, str(valore)))


# Scopo: i file tracciati da git che rispettano i pathspec dati.
def tracciati(*pathspec):
    out = subprocess.run(["git", "ls-files", "--", *pathspec],
                         capture_output=True, text=True, check=True).stdout
    return [r for r in out.splitlines() if r]


# Scopo: i file, fra quelli dati, che contengono l'espressione regolare.
def con(files, regex):
    rx = re.compile(regex, re.MULTILINE)
    return [f for f in files if rx.search(open(f, encoding="utf-8", errors="replace").read())]


# ── Frontend ───────────────────────────────────────────────────────────────
FE = "Frontend"
vue = tracciati("frontend/src/**/*.vue")
js = [f for f in tracciati("frontend/src/**/*.js") if not f.endswith(".spec.js")]
spec = tracciati("frontend/**/*.spec.js")
misura(FE, "file .spec.js / di cui col DOM (jsdom)", f"{len(spec)} / {len(con(spec, r'@vitest-environment jsdom'))}")

pkg = json.load(open("frontend/package.json", encoding="utf-8"))
misura(FE, "guard in CI (script guard:*)", sum(1 for k in pkg.get("scripts", {}) if k.startswith("guard:")))

dt = json.load(open("frontend/scripts/datatable.baseline.json", encoding="utf-8"))
misura(FE, "DataTable grezze / senza motivazione (registro)", f"{len(dt['grezze'])} / {len(dt['senza_motivazione'])}")

fl = json.load(open("frontend/scripts/filtri-lista.baseline.json", encoding="utf-8"))
voci_fl = {k: v for k, v in fl.items() if not k.startswith("_")}
misura(FE, "filtri di lista scritti a mano (registro)",
       sum(len(v) if isinstance(v, (list, dict)) else int(v or 0) for v in voci_fl.values()))

misura(FE, "file con <ListaConfigurabile> / <DrawerTabLista>",
       f"{len(con(vue, r'<ListaConfigurabile'))} / {len(con(vue, r'<DrawerTabLista'))}")
axios_fuori = [f for f in con(vue + js, r"from ['\"]axios['\"]") if f != "frontend/src/core/api.js"]
misura(FE, "import di axios fuori da core/api.js (atteso 0)", len(axios_fuori))
misura(FE, "v-html (atteso 0)", len(con(vue, r"\bv-html\b")))
misura(FE, "console.log nei sorgenti (atteso 0)", len(con(vue + js, r"\bconsole\.log\(")))


# Scopo: le chiavi foglia di un file di traduzione.
def chiavi(d, p=""):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from chiavi(v, f"{p}{k}.")
        else:
            yield p + k


it = set(chiavi(json.load(open("frontend/src/locales/it.json", encoding="utf-8"))))
en = set(chiavi(json.load(open("frontend/src/locales/en.json", encoding="utf-8"))))
misura(FE, "chiavi i18n (it) / in una sola lingua (atteso 0)", f"{len(it)} / {len(it ^ en)}")
misura(FE, ".vue / di cui con useI18n", f"{len(vue)} / {len(con(vue, r'useI18n'))}")

# ── Backend ────────────────────────────────────────────────────────────────
BE = "Backend"
py = [f for f in tracciati("backend/apps/**/*.py")
      if "/tests/" not in f and "/migrations/" not in f]
test = [f for f in tracciati("backend/apps/**/test*.py") if "/tests/" in f]

mb = json.load(open("backend/mypy.baseline.json", encoding="utf-8"))
misura(BE, "rilievi mypy nel registro (atteso 0)", mb.get("totale"))

pol = {}
exec(compile(open("backend/apps/core/services/error_policies_generated.py", encoding="utf-8").read(),
             "error_policies_generated.py", "exec"), pol)
cat, rit = set(pol["CLASSE_PER_CODICE"]), set(pol["CODICI_RITIRATI"])
misura(BE, "codici errore a catalogo / ritirati / vivi", f"{len(cat)} / {len(rit)} / {len(cat - rit)}")

seed = "db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv"
lingue = collections.Counter(r["lingua"] for r in csv.DictReader(open(seed, encoding="utf-8")))
misura(BE, "messaggi d'errore a catalogo it / en", f"{lingue.get('it', 0)} / {lingue.get('en', 0)}")

# Le base view: si contano le dichiarazioni, non l'ereditarietà transitiva.
basi = collections.Counter()
for f in py:
    try:
        albero = ast.parse(open(f, encoding="utf-8").read())
    except SyntaxError:
        continue
    for n in ast.walk(albero):
        if isinstance(n, ast.ClassDef):
            for b in n.bases:
                nome = b.attr if isinstance(b, ast.Attribute) else getattr(b, "id", None)
                if nome:
                    basi[nome] += 1
misura(BE, "view su DomainAPIView / AdminAPIView / APIView nudo",
       f"{basi['DomainAPIView']} / {basi['AdminAPIView']} / {basi['APIView'] - 1}")
misura(BE, "sottoclassi di PortaleAPIView / ShopAPIView", f"{basi['PortaleAPIView']} / {basi['ShopAPIView']}")
misura(BE, "righe skip_area_check = True", len([1 for f in py for r in open(f, encoding="utf-8")
                                                if re.search(r"skip_area_check\s*=\s*True", r)]))

# api.md: «# Scopo:» prima di ogni def. Si conta per def, risalendo i commenti e
# i decoratori che la precedono: contare i commenti nel file conterebbe anche
# quelli sulle classi, e darebbe più commenti che funzioni.
defs = scopo = 0
for f in py:
    linee = open(f, encoding="utf-8").read().split("\n")
    for i, linea in enumerate(linee):
        if not re.match(r"\s*(?:async\s+)?def\s", linea):
            continue
        defs += 1
        j = i - 1
        while j >= 0 and linee[j].lstrip().startswith(("#", "@")):
            if "Scopo:" in linee[j]:
                scopo += 1
                break
            j -= 1
misura(BE, "def con # Scopo: sopra / def (sorgenti non-test)", f"{scopo} / {defs}")

misura(BE, "file di test / con mock / sul DB vero (richiedi_db_provvisto)",
       f"{len(test)} / {len(con(test, r'unittest\.mock|from unittest import mock'))} / "
       f"{len(con(test, r'richiedi_db_provvisto'))}")

smoke_py = tracciati("backend/scripts/tests/smoke-*.py")
smoke_sh = tracciati("backend/scripts/tests/smoke-test-*.sh")
noti = [r for r in open("backend/scripts/tests/baseline-smoke.tsv", encoding="utf-8")
        if r.strip() and not r.startswith("#")]
misura(BE, "smoke non-verdi noti / smoke (py + bash)",
       f"{len(noti)} / {len(smoke_py) + len(smoke_sh)} ({len(smoke_py)} + {len(smoke_sh)})")

# ── Uscita ─────────────────────────────────────────────────────────────────
if FORMATO == "tsv":
    for r in righe:
        print("\t".join(r))
else:
    larg = max(len(r[1]) for r in righe)
    area = None
    for a, ind, val in righe:
        if a != area:
            print(f"\n{a}")
            area = a
        print(f"  {ind.ljust(larg)}  {val}")
    print()
PY
