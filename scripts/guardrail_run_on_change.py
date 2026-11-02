#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Guardrail CI — `runOnChange` vietato in 00_schema e 20_code
#   Regola: docs/it/linee-guida-sql.md §11.1 (indice in .codex/AGENTS.md §Database e Liquibase)
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
# IL MECCANISMO che rende `runOnChange` pericoloso qui: un `runOnChange`
# ri-esegue al migrate SUCCESSIVO a un edit, cioe' FUORI dall'ordine di
# timeline, e riscrive il proprio corpo SOPRA le revisioni piu' recenti, che
# sono spente e non ri-eseguono. La CI lo rende visibile perche' invoca
# Liquibase DUE volte sullo stesso changelog (`--contexts="!provision"`, poi
# `--contexts=ci_apply`): un changeSet che nella seconda passata risulta
# «cambiato» riparte li', dopo tutto il resto.
#
# ⛔ SECONDA REGOLA (2026-09-17): dove `runOnChange` resta lecito, i change
# NON portano `dbms:`. In Liquibase 5.0.4 un `runOnChange` con
# `validCheckSums: ANY` e un change `dbms: postgresql` viene ri-eseguito UNA
# VOLTA senza che nessuno l'abbia toccato: con ANY la validazione non calcola
# il checksum, e il filtro che decide se ri-eseguire lo calcola SENZA il
# Database nello Scope (ChangeLogIterator lo mette solo attorno alla visit) —
# e senza Database un change `dbms:` viene ESCLUSO dal checksum
# (ChangeSet.generateCheckSum → DatabaseList.definitionMatches, shortName
# "null"). Il checksum salvato alla prima esecuzione non torna: RERAN, e da
# li' resta salvato «il checksum di niente», quindi un edit dell'SQL non
# ri-esegue MAI piu'. Il 2026-09-17 la CI e' morta cosi' (`20260831-03`,
# ripartito in ci_apply dopo il seed della sesta famiglia); su dbdev 175 righe
# RERAN portano l'MD5 della stringa vuota. In ZeroErp il database e' sempre
# PostgreSQL: `dbms:` non decide niente, e su un runOnChange costa questo.
#
# DOVE `runOnChange` RESTA LECITO (e vale la seconda regola): `80_data`
# (mirror CSV loadData/loadUpdateData, seed convergenti), `85_pgagent` (job),
# `90_end` (resync, grant). La' la ri-esecuzione e' il comportamento voluto —
# e proprio per questo il corpo deve reggere una ri-esecuzione DOPO changeSet
# piu' recenti: idempotente, precondizioni per NOME, mai «quante righe ci sono».
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

# ⭐ Il parser YAML in C dove c'e', quello in puro Python dove non c'e'.
#   Il 99% del costo di questo cancello e' il parsing (misurato il
#   2026-09-10): ~14x. Stesso risultato, provato su tutti i changelog del
#   repo — vedi scripts/_yaml_veloce.py.
#   ⚠️ `yaml` resta importato: serve per `yaml.YAMLError` nei rami di errore.
from _yaml_veloce import carica as carica_yaml

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "db" / "changelog" / "migrations_v2"
FASI_VIETATE = ("00_schema", "20_code")
# Fasi dove runOnChange e' lecito: li' vale la seconda regola (niente dbms:).
FASI_LECITE = ("70_dati_sistema", "80_data", "85_pgagent", "90_end")
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
                doc = carica_yaml(p.read_text(encoding="utf-8"))
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


# Scopo: i change con `dbms:` dentro un changeSet runOnChange delle fasi lecite
#   (file, id del changeSet, tipo del change).
def trova_dbms_su_run_on_change() -> list[tuple[str, str, str]]:
    fuori: list[tuple[str, str, str]] = []
    for fase in FASI_LECITE:
        radice = BASE / fase
        if not radice.is_dir():
            continue
        for p in sorted(radice.rglob("*")):
            if not p.is_file() or not FILENAME_RE.match(p.name):
                continue
            try:
                doc = carica_yaml(p.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                print(f"⚠️  YAML non parsabile, saltato: {p} ({exc})", file=sys.stderr)
                continue
            if not isinstance(doc, dict):
                continue
            for blocco in doc.get("databaseChangeLog", []) or []:
                if not isinstance(blocco, dict) or "changeSet" not in blocco:
                    continue
                cs = blocco["changeSet"] or {}
                if cs.get("runOnChange") is not True:
                    continue
                for change in cs.get("changes") or []:
                    if not isinstance(change, dict):
                        continue
                    for tipo, corpo in change.items():
                        if isinstance(corpo, dict) and corpo.get("dbms"):
                            rel = p.relative_to(ROOT).as_posix()
                            fuori.append((rel, str(cs.get("id", "<senza id>")), tipo))
    return fuori


# Scopo: eseguire il controllo e tradurre l'esito in exit code per la CI.
def main() -> int:
    violazioni = trova_violazioni()
    con_dbms = trova_dbms_su_run_on_change()
    if not violazioni and not con_dbms:
        print("✅ guardrail runOnChange: nessun changeSet con runOnChange:true "
              f"in {' / '.join(FASI_VIETATE)}; nessun change `dbms:` in un "
              f"runOnChange di {' / '.join(FASI_LECITE)}")
        return 0

    if con_dbms:
        print("❌ un changeSet runOnChange NON porta `dbms:` sui change\n", file=sys.stderr)
        for rel, cs_id, tipo in con_dbms:
            print(f"  {rel}\n      changeSet: {cs_id}  (change: {tipo})", file=sys.stderr)
        print(
            "\nIn Liquibase 5.0.4 un runOnChange con validCheckSums: ANY e un change\n"
            "`dbms:` viene ri-eseguito UNA volta senza che nessuno l'abbia toccato\n"
            "(il filtro calcola il checksum senza Database nello Scope e il change\n"
            "`dbms:` ne esce), in CI nella SECONDA invocazione (--contexts=ci_apply),\n"
            "fuori ordine; poi salva «il checksum di niente» e un edit dell'SQL non\n"
            "ri-esegue mai piu'. Il 2026-09-17 la CI e' morta cosi' (20260831-03).\n"
            "\n"
            "COSA FARE: togli la riga `dbms: postgresql` dai change (e dal rollback):\n"
            "il database di ZeroErp e' sempre PostgreSQL, quella riga non decide niente.\n"
            "Se invece il changeSet era una tantum (un backfill), spegnilo:\n"
            "runOnChange: false + validCheckSums: - ANY (il checksum salvato dalla\n"
            "ri-esecuzione spuria e' quello vuoto e tornerebbe vincolante).\n"
            "\n"
            "Regola: linee-guida-sql.md §11.1 (seconda regola).\n",
            file=sys.stderr,
        )
        if not violazioni:
            return 1

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
        "Regola: docs/it/linee-guida-sql.md §11.1 (indice in .codex/AGENTS.md §Database e Liquibase)\n"
        "Resta lecito in 80_data (mirror CSV), 85_pgagent, 90_end.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
