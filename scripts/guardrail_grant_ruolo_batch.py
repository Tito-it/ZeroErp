#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Guardrail CI — i privilegi dei ruoli batch stanno nel PROVISIONING,
#                mai in un changeSet
#   Regola: docs/it/linee-guida-sql.md §11.6
#
# COSA PRESIDIA, in una riga:
#   «nessun `GRANT … TO zeroerp_batch_*` dentro un changeSet Liquibase».
#
# IL MECCANISMO. I ruoli batch headless hanno `BYPASSRLS`, che richiede
# superuser: Liquibase gira come `zeroerp`, quindi NON puo' crearli. Li crea
# `scripts/sql/provision_db_role_batch_fatturazione.sql`, lanciato in CI come
# `postgres` — e il workflow lo lancia **DOPO** le migrazioni standard, perche'
# quello script concede sul perimetro e le tabelle del perimetro devono
# esistere. Quindi durante tutto il migrate quel ruolo NON ESISTE, e un GRANT
# che lo nomina uccide la pipeline:
#   ERROR: role "zeroerp_batch_fatturazione" does not exist
# Su un database di sviluppo il ruolo c'e' da settimane e il GRANT passa.
#
# ⭐ E il GRANT e' anche INUTILE. Il provisioning fa
# `GRANT SELECT ON ALL TABLES` + `GRANT EXECUTE ON ALL FUNCTIONS` sui 14 schemi
# applicativi, piu' `ALTER DEFAULT PRIVILEGES` per gli oggetti futuri: l'oggetto
# e' coperto su ogni ambiente anche se nasce dopo. Misurato il 2026-09-02: una
# funzione creata il 31 agosto, senza NESSUN grant esplicito, risponde gia'
# `EXECUTE = true` per il ruolo batch.
#
# PERCHE' SERVE UN CANCELLO E NON BASTAVA LA REGOLA. Perche' la regola era gia'
# scritta — parola per parola — nell'intestazione di
# `20260727-21-create-vw-indici-ridondanti-prefisso`, dopo lo stesso identico
# guasto del 2026-07-27: «i privilegi dei ruoli batch stanno nel provisioning,
# mai in un changeSet». Nei trentasei giorni successivi sono stati scritti
# **39 GRANT** in **20 changeSet** che la violano, bonificati il 2026-09-02.
# ⚠️ Una regola scritta in un commento la legge chi apre quel file. Un cancello
# la legge per tutti.
#
# ⚠️ E il difetto NON e' visibile scrivendo: chi aggiunge una funzione al
# perimetro batch copia il GRANT accanto a quello per `zeroerp_app`, che invece
# ci vuole. La riga giusta e la riga sbagliata sono adiacenti e identiche
# tranne il nome del ruolo.
#
# ⚠️ LIMITI DICHIARATI:
#   * guarda `migrations_v2`, non la vecchia storia in `changelog/migrations`,
#     che e' congelata e gia' applicata ovunque;
#   * riconosce i ruoli dal prefisso `zeroerp_batch_`. Un ruolo batch
#     battezzato altrimenti non e' guardato: il prefisso e' il perimetro.
#
# Uso (read-only, nessun database):
#   python scripts/guardrail_grant_ruolo_batch.py
# Exit 0 se pulito, 1 se trova violazioni.
# ------------------------------------------------------------

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "db" / "changelog" / "migrations_v2"

PREFISSO_RUOLO_BATCH = "zeroerp_batch_"

# `TO <ruolo>` di un GRANT: il nome del ruolo puo' stare su una riga sua,
# perche' la firma della funzione va spesso a capo.
TO_RUOLO_RE = re.compile(
    r"\bTO\s+([a-z_][a-z0-9_]*)\s*(?:,\s*[a-z_][a-z0-9_]*\s*)*;", re.IGNORECASE
)
RUOLO_RE = re.compile(r"\b(zeroerp_batch_[a-z0-9_]+)\b", re.IGNORECASE)

BLOCCO_COMMENTO_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


# Scopo: una riga che e' solo commento — YAML (`#`) o SQL (`--`) — non esegue.
def _e_commento(riga: str) -> bool:
    nuda = riga.lstrip()
    return nuda.startswith(("#", "--"))


# Scopo: elenca le violazioni (file, riga, ruolo, testo).
def trova_violazioni() -> list[tuple[str, int, str, str]]:
    fuori: list[tuple[str, int, str, str]] = []
    if not BASE.is_dir():
        return fuori
    for p in sorted(BASE.rglob("*.y*ml")):
        testo = p.read_text(encoding="utf-8")
        if PREFISSO_RUOLO_BATCH not in testo:
            continue
        # I commenti di blocco spariscono prima di guardare riga per riga.
        righe = BLOCCO_COMMENTO_RE.sub("", testo).splitlines()
        rel = p.relative_to(BASE).as_posix()
        for n, riga in enumerate(righe, start=1):
            if _e_commento(riga):
                continue
            nomi = RUOLO_RE.findall(riga)
            if not nomi:
                continue
            # Il nome del ruolo compare in una riga eseguibile: e' un GRANT solo
            # se quella riga chiude una clausola `TO … ;`.
            if not TO_RUOLO_RE.search(riga):
                continue
            for nome in nomi:
                fuori.append((rel, n, nome.lower(), " ".join(riga.split())[:110]))
    return fuori


# Scopo: eseguire il controllo e tradurre l'esito in exit code per la CI.
def main() -> int:
    violazioni = trova_violazioni()
    if not violazioni:
        print(
            "✅ guardrail GRANT/ruolo-batch: nessun changeSet concede privilegi a "
            f"un ruolo {PREFISSO_RUOLO_BATCH}*"
        )
        return 0

    print(
        f"❌ guardrail GRANT/ruolo-batch: {len(violazioni)} GRANT nominano un ruolo "
        "batch dentro un changeSet.\n"
        "   In CI quel ruolo non esiste ancora — lo provisiona `postgres` DOPO le\n"
        "   migrazioni — e il migrate muore con «role ... does not exist».\n",
        file=sys.stderr,
    )
    for rel, n, nome, riga in violazioni:
        print(f"  · {rel}:{n}", file=sys.stderr)
        print(f"      ruolo: {nome}", file=sys.stderr)
        print(f"      riga : {riga}", file=sys.stderr)
    print(
        "\n   Rimedio: TOGLIERE la riga. Dal 2026-10-15 i ruoli batch non esistono\n"
        "   piu' (ritirati: brief-db-ruoli-di-sistema, fase 4): un processo\n"
        "   automatico gira come zeroerp_app con un utente tecnico per azienda.\n"
        "   ⚠️ Il GRANT a `zeroerp_app` accanto invece RESTA: quello e' un ruolo che\n"
        "   esiste durante il migrate, ed e' la riga da cui questa e' stata copiata.\n"
        "   ⛔ Un ruolo BYPASSRLS nuovo non si crea: si usa un utente tecnico.\n"
        "   Regola: docs/it/linee-guida-sql.md §11.6",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
