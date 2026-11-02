#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Guardrail CI — la prima generazione dei changelog (v1) non si tocca
#   Regola: docs/it/linee-guida-sql.md §11.11 (indice in .codex/AGENTS.md
#           §Database e Liquibase). Decisione di Tid del 2026-10-04.
#
# COSA PRESIDIA, in una riga:
#   «baseline/, migrations/ e changelog-master.yaml sono storia: nessun file
#    si aggiunge, si toglie o si modifica».
#
# PERCHE' SERVE. changelog-master-v2.yaml include changelog-master.yaml, che
# fa includeAll di baseline/ e migrations/: la prima generazione RIGIRA a
# ogni migrate da zero (in CI, a ogni installazione nuova). Centinaia di quei
# file sono `runOnChange: true`, e guardrail_run_on_change.py guarda solo
# migrations_v2/. Un edit a un file v1 lo fa ripartire al migrate successivo,
# FUORI dall'ordine di timeline e SOPRA le revisioni v2 piu' recenti: e' il
# difetto di linee-guida-sql §11.1, entrato dalla porta che quel cancello non
# vede. Su dbdev il file v1 e' gia' eseguito e non si nota niente.
#
# COME. Un manifesto committato (db/changelog/v1-congelato.json) porta lo
# sha256 di ogni file dell'albero v1. Il cancello ricalcola e confronta: un
# file in piu', in meno o diverso fa fallire la build. Non serve la storia git
# ne' un database, e il nome esatto di ogni file (anche quelli con lo spazio
# finale) e' nel manifesto.
#
# ⚠️ L'ECCEZIONE ESISTE, ma si vede. Se un file v1 va davvero cambiato (e' gia'
# successo per far girare la CI su un'installazione nuova: baseline, il
# 2026-09-02), si concorda con Tid e si rigenera il manifesto NELLO STESSO
# commit:
#   python scripts/guardrail_v1_congelato.py --rigenera
# Il diff del manifesto e' la firma del cambio: chi rivede la PR lo vede.
#
# Uso (read-only, nessun database):
#   python scripts/guardrail_v1_congelato.py
# Exit 0 se l'albero coincide col manifesto, 1 se diverge, 2 se il manifesto
# manca o non si legge.
# ------------------------------------------------------------

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "db" / "changelog"
MANIFESTO = CHANGELOG / "v1-congelato.json"
# Cio' che changelog-master.yaml include, e il master stesso.
RADICI = ("baseline", "migrations")
FILE_SINGOLI = ("changelog-master.yaml",)


# Scopo: sha256 di ogni file dell'albero v1, per percorso relativo a db/changelog.
def fotografa() -> dict[str, str]:
    impronte: dict[str, str] = {}
    percorsi = [CHANGELOG / f for f in FILE_SINGOLI]
    for radice in RADICI:
        percorsi.extend(p for p in (CHANGELOG / radice).rglob("*") if p.is_file())
    for p in sorted(percorsi):
        impronte[p.relative_to(CHANGELOG).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return impronte


# Scopo: scrive il manifesto dall'albero attuale (solo con --rigenera).
def rigenera() -> int:
    impronte = fotografa()
    MANIFESTO.write_text(
        json.dumps(impronte, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Manifesto rigenerato: {len(impronte)} file in {MANIFESTO.relative_to(ROOT)}")
    return 0


# Scopo: confronta l'albero col manifesto e stampa ogni divergenza.
def verifica() -> int:
    try:
        attese = json.loads(MANIFESTO.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"⛔ Manifesto v1 illeggibile ({MANIFESTO.relative_to(ROOT)}): {exc}")
        return 2
    attuali = fotografa()
    aggiunti = sorted(set(attuali) - set(attese))
    tolti = sorted(set(attese) - set(attuali))
    cambiati = sorted(k for k in set(attese) & set(attuali) if attese[k] != attuali[k])
    if not (aggiunti or tolti or cambiati):
        print(f"OK — albero v1 congelato: {len(attuali)} file coincidono col manifesto.")
        return 0
    print("⛔ La prima generazione dei changelog (v1) e' cambiata.")
    print("   baseline/, migrations/ e changelog-master.yaml rigirano a ogni migrate da zero:")
    print("   un file v1 modificato (runOnChange) riparte FUORI ordine, sopra le revisioni v2.")
    print("   Regola: docs/it/linee-guida-sql.md §11.11. Si scrive un changeSet nuovo in migrations_v2/.")
    for etichetta, elenco in (("aggiunto", aggiunti), ("tolto", tolti), ("modificato", cambiati)):
        for k in elenco:
            print(f"   - {etichetta}: db/changelog/{k!r}")
    print("   Eccezione concordata con Tid: python scripts/guardrail_v1_congelato.py --rigenera,")
    print("   nello stesso commit del cambio.")
    return 1


if __name__ == "__main__":
    sys.exit(rigenera() if "--rigenera" in sys.argv[1:] else verifica())
