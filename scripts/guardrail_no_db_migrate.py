#!/usr/bin/env python3
# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Guardrail per Zero ERP
# Copyright (C) 2026 Tid (Michele Carlo Titini)
#
# Rilasciato sotto GNU AGPLv3 o versione successiva.
# Vedi LICENSE.md per il testo completo della licenza.
# ------------------------------------------------------------
# Scopo: impedire che un agente AI applichi migrazioni al database senza
#        autorizzazione esplicita dell'utente, in quel momento e per quel
#        comando.
#
# Perche' esiste. La regola c'e' da sempre — .codex/AGENTS.md, sezione
# «Workflow Safety»: «Ask before running DB migrations locally» e «Non eseguire
# migrazioni DB senza conferma esplicita dell'utente». Il 2026-08-15 e' stata
# infranta lo stesso: l'agente ha letto «fai tutto il possibile lato DB» come
# un'autorizzazione, e ha eseguito `liquibase update` sul database di sviluppo.
# Una regola scritta in un documento e' una raccomandazione; questo file la
# rende un cancello. Il modello non puo' aggirarlo: gira nel harness, non nel
# contesto.
#
# Come funziona: e' un hook PreToolUse su Bash (.claude/settings.json). Riceve
# il JSON della chiamata su stdin, guarda il comando e:
#   exit 0  -> il comando non c'entra con le migrazioni, prosegue
#   exit 2  -> BLOCCA, e il messaggio su stderr torna al modello
#
# ⚠️ NIENTE DIPENDENZE. Gira in un ambiente non controllato: solo stdlib, e
#    `python3` di sistema. In particolare NON usa `jq`, che su questa macchina
#    non e' installato — un hook che fallisce per un comando mancante non
#    blocca niente, e nessuno se ne accorge.
#
# Cosa NON blocca, di proposito: `status`, `validate`, `history`, `diff`,
# `updateSQL` (che stampa l'SQL senza applicarlo) e i test pgTAP, che sono in
# transazione e chiudono in ROLLBACK. Un cancello che blocca anche la lettura
# viene disattivato dopo due giorni.
# ------------------------------------------------------------

import json
import re
import sys

# Verbi Liquibase che SCRIVONO sul database. `updateSQL` non c'e': genera lo
# script e non lo applica, ed e' anzi il modo giusto di preparare la richiesta
# di autorizzazione.
VERBI_SCRITTURA = (
    "update",
    "updateCount",
    "updateToTag",
    "rollback",
    "rollbackCount",
    "rollbackToDate",
    "changelogSync",
    "changelogSyncSQL",
    "dropAll",
    "futureRollbackSQL",
)

# Un token Liquibase e' presente se compare come parola isolata: `update` in
# «git update-index» non deve far scattare niente.
_RE_LIQUIBASE = re.compile(r"(?:^|[/\s;&|(])liquibase(?:5\.sh)?(?:\s|$)", re.IGNORECASE)
_RE_MAKE_DB = re.compile(
    r"(?:^|[\s;&|(])make\s+(?:[-\w=.\s]*\s)?db-(?:migrate|ci-apply|setup)\b",
    re.IGNORECASE,
)


# Scopo: dire se il comando applica migrazioni. Vero = va bloccato.
def applica_migrazioni(comando: str) -> str | None:
    if _RE_MAKE_DB.search(comando):
        return "make db-migrate / db-ci-apply / db-setup"

    if _RE_LIQUIBASE.search(comando):
        # Il verbo Liquibase e' il primo argomento non-opzione. Si cercano
        # tutti i token: una riga puo' contenere piu' comandi concatenati.
        for token in re.split(r"[\s;&|]+", comando):
            for verbo in VERBI_SCRITTURA:
                if token.lower() == verbo.lower():
                    return f"liquibase {verbo}"
        return None

    return None


# Scopo: leggere il payload dell'hook e decidere. Qualunque anomalia di parsing
#        lascia passare (exit 0): un guardrail che rompe le sessioni per un
#        JSON inatteso viene spento, e allora non presidia piu' niente.
def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") not in (None, "Bash"):
        return 0

    comando = (payload.get("tool_input") or {}).get("command") or ""
    if not isinstance(comando, str) or not comando.strip():
        return 0

    motivo = applica_migrazioni(comando)
    if motivo is None:
        return 0

    sys.stderr.write(
        "BLOCCATO dal guardrail migrazioni (scripts/guardrail_no_db_migrate.py).\n"
        f"Il comando applica migrazioni al database: {motivo}.\n"
        "\n"
        ".codex/AGENTS.md, «Workflow Safety»: le migrazioni NON si eseguono "
        "senza conferma esplicita dell'utente, chiesta per QUESTO comando.\n"
        "«Fai tutto il possibile», «procedi», «vai avanti» NON sono "
        "autorizzazioni a migrare: autorizzano il lavoro, non l'applicazione.\n"
        "\n"
        "Cosa fare invece:\n"
        "  1. preparare i changeSet e fermarsi;\n"
        "  2. verificare l'SQL in transazione (BEGIN … ROLLBACK) o con "
        "`liquibase updateSQL`, che NON applica;\n"
        "  3. dire all'utente che c'e' da migrare, e ASPETTARE che sia lui a "
        "farlo o ad autorizzarlo a parole.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
