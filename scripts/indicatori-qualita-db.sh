#!/usr/bin/env bash
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Scopo: stampare in un colpo gli indicatori di qualità dello strato database
#        descritti in docs/it/dev/qualita-db-indicatori.md, letti dal repo così
#        com'è adesso e, a richiesta, dal catalogo di un database.
#
# IL PROBLEMA CHE RISOLVE. La valutazione DB del 2026-09/10 rileggeva a ogni
# giro gli stessi registri (baseline pgTAP, soglie dei rubinetti, seed del
# debito) con comandi scritti a mano, e il documento li ricopiava: a metà
# ottobre metà dei suoi numeri erano vecchi di dieci giorni. Qui il comando È la
# definizione dell'indicatore; il documento dice che cosa significa e in che
# verso deve andare, non ricopia il valore.
#
# Due letture:
#   * il REPO (sempre): registri pgTAP, soglie, seed, changeSet, doc. Niente
#     database, niente rete. I guardrail e la suite hanno già il loro cancello
#     in CI: qui si leggono i registri che quei cancelli tengono, non si
#     rilanciano.
#   * il CATALOGO (--catalogo): le viste di presidio di dbops e pg_catalog, sul
#     database delle variabili PG* dell'ambiente, in una transazione di sola
#     lettura. ⚠️ Il catalogo è quello di UNA macchina: dbdev non è la CI.
#
# ⚠️ Sono letture di STRUTTURA (quali file, quali vincoli, quali registri), fatti
# datati: trovano gli errori, non decidono il progetto (regola zero, AGENTS.md).
#
# Uso:
#   scripts/indicatori-qualita-db.sh                 # repo, tabella leggibile
#   scripts/indicatori-qualita-db.sh --tsv           # area<TAB>indicatore<TAB>valore, per un diff
#   set -a; . db/internal.env; set +a
#   scripts/indicatori-qualita-db.sh --catalogo      # repo + catalogo di dbdev
#   scripts/indicatori-qualita-db.sh --catalogo --tsv
# ------------------------------------------------------------
set -euo pipefail

RADICE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RADICE"

FORMATO="tabella"
CATALOGO="no"
for arg in "$@"; do
  case "$arg" in
    --tsv) FORMATO="tsv" ;;
    --catalogo) CATALOGO="si" ;;
    *) echo "uso: $0 [--tsv] [--catalogo]" >&2; exit 2 ;;
  esac
done

# ⚠️ -I: lo script Python non deve importare niente dalla cartella corrente.
exec python3 -I - "$FORMATO" "$CATALOGO" <<'PY'
import collections
import csv
import os
import re
import subprocess
import sys

FORMATO, CATALOGO = sys.argv[1], sys.argv[2] == "si"
righe = []


# Scopo: registrare una misura sotto la sua area.
def misura(area, indicatore, valore):
    righe.append((area, indicatore, str(valore)))


# Scopo: i file tracciati da git che rispettano i pathspec dati.
def tracciati(*pathspec):
    out = subprocess.run(["git", "ls-files", "--", *pathspec],
                         capture_output=True, text=True, check=True).stdout
    return [r for r in out.splitlines() if r]


# Scopo: il testo di un file, senza fermarsi su un byte non UTF-8.
def testo(f):
    return open(f, encoding="utf-8", errors="replace").read()


# Scopo: i file, fra quelli dati, che contengono l'espressione regolare.
def con(files, regex):
    rx = re.compile(regex, re.MULTILINE)
    return [f for f in files if rx.search(testo(f))]


# Scopo: le righe di un registro TSV (file, classe), senza commenti.
def registro(f):
    return [r.rstrip("\n").split("\t") for r in open(f, encoding="utf-8")
            if r.strip() and not r.startswith("#")]


# Scopo: «totale (classe n, classe n…)» di un registro di rossi.
def per_classe(voci):
    c = collections.Counter(v[1] if len(v) > 1 else "?" for v in voci)
    dettaglio = ", ".join(f"{k} {n}" for k, n in sorted(c.items(), key=lambda x: -x[1]))
    return f"{len(voci)} ({dettaglio})" if voci else "0"


# ── Suite pgTAP ────────────────────────────────────────────────────────────
PG = "Suite pgTAP"
pgtap = tracciati("db/pgtap/**/*.sql")
misura(PG, "file pgTAP", len(pgtap))
misura(PG, "file con pgtap-runner: owner (non girano come app)",
       len(con(pgtap, r"^\s*--\s*pgtap-runner:\s*owner")))
misura(PG, "file con uno skip() (su un DB vuoto contano verdi)", len(con(pgtap, r"\bskip\(")))
misura(PG, "file con SET LOCAL app.current_user_id = '1' (atteso 0)",
       len(con(pgtap, r"^\s*SET LOCAL app\.current_user_id\s*=\s*'1'")))
misura(PG, "rossi noti in sviluppo (baseline-rossi.tsv)", per_classe(registro("db/pgtap/baseline-rossi.tsv")))
misura(PG, "rossi noti in CI (baseline-rossi-ci.tsv)", per_classe(registro("db/pgtap/baseline-rossi-ci.tsv")))
misura(PG, "rossi noti sullo scratch (baseline-rossi-scratch.tsv)",
       per_classe(registro("db/pgtap/baseline-rossi-scratch.tsv")))
ultima_ci = subprocess.run(["git", "log", "-1", "--format=%ad", "--date=short", "--",
                            "db/pgtap/baseline-rossi-ci.tsv"],
                           capture_output=True, text=True, check=True).stdout.strip()
misura(PG, "ultimo commit del registro della CI", ultima_ci or "—")

m = re.search(r"^SOGLIA_THROWS_SENZA_DISCRIMINANTE\s*=\s*(\d+)",
              testo("scripts/guardrail_pgtap_preambolo.py"), re.MULTILINE)
misura(PG, "soglia throws_ok senza discriminante", m.group(1) if m else "?")

# Gli schemi documentati (cartelle di docs/it/dbzero con tabelle/) e i loro file di test:
# le cartelle di servizio di 00_schema (bootstrap, internal) non sono schemi.
schemi = sorted({p.split("/")[3] for p in tracciati("docs/it/dbzero/*/tabelle/*.md")})
per_schema = collections.Counter(p.split("/")[2] for p in pgtap if p.count("/") >= 3)
senza = [s for s in schemi if per_schema.get(s, 0) == 0]
misura(PG, "schemi senza nessun file pgTAP", ", ".join(senza) or "nessuno")

# ── Registri del debito e rubinetti ────────────────────────────────────────
RD = "Registri e rubinetti"
seed_rls = "db/changelog/migrations_v2/80_data/sql/dbops/rls_perimetro_debito.csv"
misura(RD, "rls_perimetro_debito (righe nel seed)", sum(1 for _ in csv.DictReader(open(seed_rls, encoding="utf-8"))))

sp = testo("db/pgtap/dbops/test-security-definer-search-path-v1.sql")
soglie = re.findall(r"'<=',\s*(\d+)::bigint,\s*'(\d)\.", sp)
soglia = {n: v for v, n in soglie}
misura(RD, "DEFINER senza pg_temp / con public prima di pg_catalog (soglie D6-bis)",
       f"{soglia.get('4', '?')} / {soglia.get('5', '?')}")


# ── Codici errore ──────────────────────────────────────────────────────────
CE = "Codici errore"
codici = list(csv.DictReader(open("db/changelog/migrations_v2/80_data/sql/config/codici_errore.csv",
                                  encoding="utf-8")))
messaggi = list(csv.DictReader(open("db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv",
                                    encoding="utf-8")))
con_it = {r["codice"] for r in messaggi if r["lingua"] == "it"}
misura(CE, "codici a catalogo / con obsoleto_dal", f"{len(codici)} / "
       f"{sum(1 for r in codici if r['obsoleto_dal'] not in ('', 'NULL'))}")
senza_msg = sorted(r["codice"] for r in codici if r["codice"] not in con_it)
misura(CE, "codici senza messaggio it (atteso 0)", len(senza_msg))

# ── Liquibase e guardrail ──────────────────────────────────────────────────
LQ = "Liquibase e guardrail"
yaml_v2 = [f for f in tracciati("db/changelog/migrations_v2/**/*.yaml")
           if not f.endswith("changelog-autogen.yaml")]
misura(LQ, "changeSet in migrations_v2", sum(len(re.findall(r"^\s*-\s*changeSet:", testo(f), re.MULTILINE))
                                            for f in yaml_v2))
misura(LQ, "file changeSet senza logicalFilePath (⚠️ nessun presidio)",
       len([f for f in con(yaml_v2, r"^\s*-\s*changeSet:") if "logicalFilePath" not in testo(f)]))
ci = testo(".github/workflows/ci-validate.yaml")
gr = sorted(os.path.basename(f) for f in tracciati("scripts/guardrail_*.py"))
misura(LQ, "guardrail scritti / chiamati in ci-validate",
       f"{len(gr)} / {sum(1 for g in gr if g in ci)}")

# ── Documentazione ─────────────────────────────────────────────────────────
DO = "Documentazione"
auto = tracciati("docs/it/dbzero/*/tabelle/*.md", "docs/it/dbzero/*/views/*.md", "docs/it/dbzero/*/funzioni/*.md")
manual = tracciati("docs/it/dbzero/*/manual/*.md")
misura(DO, "pagine manual/ / pagine auto-generate", f"{len(manual)} / {len(auto)}")

# ── Catalogo (a richiesta) ─────────────────────────────────────────────────
QUERY = [
    # ⛔ Misura, NON debito: conta ogni codice che il DB può nominare e cresce col dominio.
    #    Il debito è codici_errore_senza_policy (a zero, presidiato dal test Django). Correzione 2026-10-27.
    ("Catalogo", "codici nominabili dal DB — misura, non debito (vw_codici_errore_da_dichiarare)",
     "SELECT count(*) FROM dbops.vw_codici_errore_da_dichiarare"),
    ("Catalogo", "codici senza policy — il debito (codici_errore_senza_policy, atteso 0)",
     "SELECT count(*) FROM dbops.codici_errore_senza_policy"),
    ("Catalogo", "FK senza indice fuori policy (vw_fk_con_indice_missing_policy)",
     "SELECT count(*) FROM dbops.vw_fk_con_indice_missing_policy"),
    ("Catalogo", "indici ridondanti per prefisso (vw_indici_ridondanti_prefisso)",
     "SELECT count(*) FROM dbops.vw_indici_ridondanti_prefisso"),
    ("Catalogo", "processi che bypassano la RLS (atteso 0)",
     "SELECT count(*) FROM dbops.vw_processi_che_bypassano"),
    ("Catalogo", "tabelle con RLS / con FORCE (invariante Q-3: 0)",
     "SELECT count(*) FILTER (WHERE relrowsecurity) || ' / ' || count(*) FILTER (WHERE relforcerowsecurity)"
     " FROM pg_class WHERE relkind IN ('r','p')"),
    ("Catalogo", "trigger / con la fase nel nome / dai due guard per-figlia",
     "SELECT count(*) || ' / ' || count(*) FILTER (WHERE t.tgname ~ '_[az][0-9]{2}_') || ' / ' ||"
     " count(*) FILTER (WHERE p.proname IN ('trgfn_prevent_deactivate_if_children',"
     "'trgfn_child_requires_active_parent'))"
     " FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid WHERE NOT t.tgisinternal"),
    ("Catalogo", "trigger su catalogo.articoli",
     "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgrelid = 'catalogo.articoli'::regclass"),
]
if CATALOGO:
    sql = "\n".join(f"SELECT {i}, ({q});" for i, (_, _, q) in enumerate(QUERY))
    env = dict(os.environ, PGOPTIONS="-c default_transaction_read_only=on")
    r = subprocess.run(["psql", "-X", "-At", "-F", "\t", "-v", "ON_ERROR_STOP=1", "-c", sql],
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        # ⛔ Una misura che non si è potuta prendere si dice, non si tace.
        misura("Catalogo", "lettura del catalogo", "NON RIUSCITA: " + r.stderr.strip().splitlines()[-1])
    else:
        db = subprocess.run(["psql", "-X", "-At", "-c", "SELECT current_database()"],
                            capture_output=True, text=True, env=env).stdout.strip()
        misura("Catalogo", "database letto", db)
        valori = dict(l.split("\t", 1) for l in r.stdout.splitlines() if "\t" in l)
        for i, (area, ind, _) in enumerate(QUERY):
            misura(area, ind, valori.get(str(i), "?"))
else:
    misura("Catalogo", "non letto", "lanciare con --catalogo e le variabili PG* (es. db/internal.env)")

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
