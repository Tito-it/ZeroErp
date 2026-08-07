#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Guardrail CI — `runOnChange` vietato in 00_schema e 20_code
#   Regola: .codex/AGENTS.md §Liquibase v2 Workflow
#           docs/it/linee-guida-sql.md §11.1
#
# COSA PRESIDIA, in una riga:
#   «un changeSet di schema o di codice si applica UNA volta, in ordine di
#    timeline; se il corpo deve cambiare si scrive un file nuovo».
#
# PERCHE' SERVE UN CANCELLO E NON BASTAVA LA REGOLA. Perche' la regola non
# c'era: prima del 2026-08-06 la documentazione dava `runOnChange: true` per
# normale sulle funzioni, e in un punto affermava che «i changeSet successivi
# lo superano» — che e' falso. Due bonifiche a mano dopo, il divieto e' scritto
# e questo lo tiene.
#
# IL MECCANISMO che rende `runOnChange` pericoloso qui: la CI invoca Liquibase
# DUE volte sullo stesso changelog (`--contexts="!provision"`, poi
# `--contexts=ci_apply`). Nella seconda passata un `runOnChange` ri-esegue
# FUORI dall'ordine di timeline e riscrive il proprio corpo SOPRA le revisioni
# piu' recenti, che sono spente e non ri-eseguono. Su un DB di sviluppo
# l'invocazione e' una sola: il difetto e' invisibile fino alla CI.
#
# DOVE RESTA LECITO e percio' non e' controllato: `80_data` (mirror CSV
# loadData/loadUpdateData), `85_pgagent` (job), `90_end` (resync, grant). La'
# la ri-esecuzione e' il comportamento voluto.
#
# Uso (read-only, nessun database):
#   python scripts/guardrail_run_on_change.py
# Exit 0 se pulito, 1 se trova violazioni.
# ------------------------------------------------------------

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "db" / "changelog" / "migrations_v2"
FASI_VIETATE = ("00_schema", "20_code")
FILENAME_RE = re.compile(r"^\d{8}-\d{2}.*\.(ya?ml)$", re.IGNORECASE)


# Scopo: elenca le violazioni (file, id del changeSet) nelle fasi presidiate.
def trova_violazioni() -> list[tuple[str, str]]:
    fuori: list[tuple[str, str]] = []
    for fase in FASI_VIETATE:
        radice = BASE / fase
        if not radice.is_dir():
            continue
        for p in sorted(radice.rglob("*")):
            if not p.is_file() or not FILENAME_RE.match(p.name):
                continue
            try:
                doc = yaml.safe_load(p.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                print(f"⚠️  YAML non parsabile, saltato: {p} ({exc})", file=sys.stderr)
                continue
            if not isinstance(doc, dict):
                continue
            for blocco in doc.get("databaseChangeLog", []) or []:
                if not isinstance(blocco, dict) or "changeSet" not in blocco:
                    continue
                cs = blocco["changeSet"] or {}
                if cs.get("runOnChange") is True:
                    rel = p.relative_to(ROOT).as_posix()
                    fuori.append((rel, str(cs.get("id", "<senza id>"))))
    return fuori


# Scopo: eseguire il controllo e tradurre l'esito in exit code per la CI.
def main() -> int:
    violazioni = trova_violazioni()
    if not violazioni:
        print("✅ guardrail runOnChange: nessun changeSet con runOnChange:true "
              f"in {' / '.join(FASI_VIETATE)}")
        return 0

    print("❌ runOnChange: true VIETATO in 00_schema e 20_code\n", file=sys.stderr)
    for rel, cs_id in violazioni:
        print(f"  {rel}\n      changeSet: {cs_id}", file=sys.stderr)
    print(
        "\nUn changeSet di schema o di codice si applica UNA volta, in ordine di\n"
        "timeline. Con runOnChange:true ri-esegue anche nella SECONDA invocazione\n"
        "di Liquibase della CI (--contexts=ci_apply), fuori ordine, e riscrive il\n"
        "proprio corpo SOPRA le revisioni piu' recenti — che sono spente e non\n"
        "ri-eseguono. Su un DB di sviluppo non si vede: l'invocazione e' una sola.\n"
        "\n"
        "COSA FARE: metti runOnChange: false. Se devi cambiare il corpo, NON\n"
        "riaccendere questo changeSet: crea un file nuovo con numerazione\n"
        "successiva, copiando la definizione corrente dalla doc auto-gen\n"
        "(docs/it/dbzero/<schema>/funzioni/<nome>.md), non da un vecchio YAML.\n"
        "\n"
        "⚠️  Spegnendolo controlla anche la chiave del checksum: `validCheckSum`\n"
        "    SINGOLARE e' una chiave che Liquibase ignora, quindi quell'ANY non\n"
        "    vale niente. Con runOnChange:false il checksum torna vincolante e il\n"
        "    migrate fallisce. Deve essere `validCheckSums:` con `- ANY`.\n"
        "\n"
        "Regola: .codex/AGENTS.md §Liquibase v2 Workflow · linee-guida-sql.md §11.1\n"
        "Resta lecito in 80_data (mirror CSV), 85_pgagent, 90_end.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
