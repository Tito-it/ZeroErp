#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Bootstrap UNA TANTUM del seed `config.codici_errore` — estrae la
#        classe di ogni codice errore dallo `http_status` gia' deciso in
#        `error_policies.py` e la unisce a `obsoleto_dal` del catalogo.
# Note: passo D-1 di docs/it/dev/work-done/piano-db-classe-codici-errore.md
#
#   🔴 NON GIRA PIU', E NON VA RIPARATO. Il 2026-08-07, poche ore dopo questa
#   estrazione, il backend ha eseguito il proprio passo B-3: `error_policies.py`
#   e' stato diviso in quattro moduli e **non contiene piu' nessun `http_status=`
#   per codice** — ci sono sette righe classe -> status. La sorgente che questo
#   script legge non esiste piu'.
#
#   Resta nel repo come REPERTO, non come strumento: documenta *come* le 659
#   decisioni del cantiere del terzo/quarto lato sono state portate nel catalogo,
#   e la mappa `CLASSE_DA_STATUS` e' la sola forma in cui quella corrispondenza
#   status->classe e' ancora scritta da questo lato.
#
#   ⚠️ Da qui in avanti la sorgente della classe e' il CSV di seed, e poi il DB:
#   il verso si inverte e sara' il backend a GENERARE il proprio modulo dal
#   catalogo (decisione D6-bis del brief). Chi deve correggere una classe tocca
#   il CSV, non questo file.
#
#   ⚠️ IL PARSER DELIMITA OGNI VOCE CON LA CHIAVE SUCCESSIVA, non con
#   l'indentazione. 32 voci di `error_policies.py` sono scritte su UNA RIGA
#   SOLA: un parser che cerca `http_status=` a inizio riga le perde, e in
#   questo cantiere quell'errore ha gia' prodotto due misure sbagliate — una
#   delle quali ribaltava una conclusione.
# ------------------------------------------------------------

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOGO = ROOT / "db/changelog/migrations_v2/80_data/sql/config/messaggi_errore.csv"
POLICIES = ROOT / "backend/apps/core/services/error_policies.py"
USCITA = ROOT / "db/changelog/migrations_v2/80_data/sql/config/codici_errore.csv"

# Mappa deterministica status -> classe. E' l'inverso di quella che vivra' nel
# backend dopo il cantiere: qui serve solo a leggere all'indietro le decisioni
# gia' prese. Vocabolario: brief §4.
CLASSE_DA_STATUS: dict[int, str] = {
    400: "DATO_ERRATO",
    409: "CONFLITTO_STATO",
    404: "NON_TROVATO",
    500: "TECNICO",
    403: "NON_PERMESSO",
    422: "NON_ESEGUIBILE",
    501: "NON_DISPONIBILE",
    # ⚠️ Le due classi seguenti sono una PROPOSTA aperta (vedi §4.3 del brief):
    #    il brief dichiarava 401 e 502 «fuori dal vocabolario di dominio», ma
    #    quei 5 codici sono righe del catalogo e con `classe NOT NULL` una
    #    classe la vogliono. E' lo stesso problema di `AVVISO`.
    401: "NON_AUTENTICATO",
    502: "ERRORE_ESTERNO",
}

# Codici che nel catalogo hanno un nome e in `error_policies.py` un altro.
# Non sono codici diversi: sono lo stesso codice scritto in due modi, e la
# verita' e' il nome a catalogo (§7.2 del brief).
ALIAS_POLICY = {
    "MESSAGGIO_NON_DEFINITO": "E_MESSAGGIO_NON_DEFINITO",
    "W_TXID_NOT_REGISTERED": "E_W_TXID_NOT_REGISTERED",
}

# La famiglia `W_` non e' un errore: e' un avviso, il DB lo scrive nel diario e
# non lo solleva mai. La sua policy dice 500 perche' nessuno l'aveva mai
# classificato — non va creduta (§4.2 del brief).
CLASSE_FORZATA = {
    "W_TXID_NOT_REGISTERED": "AVVISO",
}

TOKEN_NULL = "NULL"  # convenzione CSV del progetto: token letterale, non cella vuota  # noqa: S105 — segnaposto del parser, non un segreto


# Scopo: Legge il catalogo e torna {codice: obsoleto_dal}, preferendo la riga 'it'.
#        L'universo dei codici e' il CATALOGO, non le policy: un codice esiste
#        se il DB puo' nominarlo.
def leggi_catalogo() -> dict[str, str]:
    catalogo: dict[str, str] = {}
    with CATALOGO.open(encoding="utf-8") as fh:
        for riga in csv.DictReader(fh):
            codice = riga["codice"]
            # La riga 'it' vince: `obsoleto_dal` e' per-lingua solo per il difetto
            # che questo cantiere sta togliendo, e le 50 ritirate sono tutte 'it'.
            if codice not in catalogo or riga["lingua"] == "it":
                catalogo[codice] = riga["obsoleto_dal"]
    return catalogo


# Scopo: Legge `error_policies.py` e torna {codice: http_status}.
#        Delimita ogni voce con la chiave successiva — vedi l'avvertenza in testata.
def leggi_policy() -> dict[str, int]:
    sorgente = POLICIES.read_text(encoding="utf-8")
    chiave = re.compile(r'^\s{8}"([A-Za-z_][A-Za-z0-9_]*)": ErrorPolicy\(', re.M)
    trovate = list(chiave.finditer(sorgente))
    policy: dict[str, int] = {}
    for i, m in enumerate(trovate):
        fine = trovate[i + 1].start() if i + 1 < len(trovate) else len(sorgente)
        corpo = sorgente[m.end() : fine]
        status = re.search(r"http_status=(\d+)", corpo)
        if status is None:
            raise SystemExit(f"voce senza http_status: {m.group(1)} — parser da rivedere")
        policy[m.group(1)] = int(status.group(1))
    return policy


# Scopo: Decide la classe di un codice, nell'ordine: forzatura di dominio,
#        policy diretta, policy del gemello con prefisso. Torna None se il
#        codice non ha policy da nessuna parte (sono le decisioni residue del D-2).
def classe_di(codice: str, policy: dict[str, int]) -> str | None:
    if codice in CLASSE_FORZATA:
        return CLASSE_FORZATA[codice]
    status = policy.get(codice)
    if status is None:
        status = policy.get(ALIAS_POLICY.get(codice, ""))
    if status is None:
        return None
    classe = CLASSE_DA_STATUS.get(status)
    if classe is None:
        raise SystemExit(f"status {status} non mappato ({codice}) — vocabolario da estendere")
    return classe


# Scopo: Orchestrazione del bootstrap — legge le due sorgenti, incrocia,
#        scrive il CSV di seed e stampa il riepilogo che va riportato nel piano.
#        I codici senza classe escono col token NULL: sono il lavoro del D-2, e
#        il seed non parte finche' non sono zero (`classe NOT NULL`).
def main() -> int:
    catalogo = leggi_catalogo()
    policy = leggi_policy()

    righe: list[dict[str, str]] = []
    senza_classe: list[str] = []
    for codice in sorted(catalogo):
        classe = classe_di(codice, policy)
        if classe is None:
            senza_classe.append(codice)
        righe.append(
            {
                "codice": codice,
                "classe": classe or TOKEN_NULL,
                "obsoleto_dal": catalogo[codice] or TOKEN_NULL,
                "note": TOKEN_NULL,
            }
        )

    with USCITA.open("w", encoding="utf-8", newline="") as fh:
        scrittore = csv.DictWriter(fh, fieldnames=["codice", "classe", "obsoleto_dal", "note"])
        scrittore.writeheader()
        scrittore.writerows(righe)

    distribuzione = Counter(r["classe"] for r in righe)
    print(f"scritto {USCITA.relative_to(ROOT)} — {len(righe)} righe")
    print(f"  policy lette: {len(policy)} | codici a catalogo: {len(catalogo)}")
    print(f"  ritirati (obsoleto_dal valorizzato): "
          f"{sum(1 for r in righe if r['obsoleto_dal'] != TOKEN_NULL)}")
    print("  distribuzione classi:")
    for classe, quanti in distribuzione.most_common():
        print(f"    {classe:<18} {quanti:>4}")
    if senza_classe:
        print(f"\n  ⚠️ {len(senza_classe)} codici SENZA classe — sono il passo D-2:")
        for codice in senza_classe:
            print(f"    {codice}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
