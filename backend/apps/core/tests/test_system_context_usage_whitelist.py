# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Guard STATICO anti-misuse del canale di sistema headless (RLS Path A,
#        D8). Il gateway `system_process_context` ripunta la connessione DEFAULT a
#        un ruolo BYPASSRLS: usarlo dentro un percorso di richiesta web
#        renderebbe quella connessione BYPASSRLS (leak cross-tenant). Questo test
#        fallisce se il gateway (o l'alias `system_fatturazione`) compare fuori dai
#        moduli whitelisted — pendant statico del guard runtime nel middleware.
# Indice test:
#   1) system_process_context usato solo nei moduli whitelisted
#   2) alias 'system_fatturazione' referenziato solo nei moduli whitelisted
# ------------------------------------------------------------

from __future__ import annotations

from pathlib import Path
from unittest import TestCase

# Radice apps/ del backend (questo file è apps/core/tests/...).
_APPS_ROOT = Path(__file__).resolve().parents[2]

# Moduli autorizzati a toccare il canale di sistema (path relativi ad apps/).
# - il gateway stesso (definizione/uso interno);
# - il management command headless che lo consuma;
# - il middleware web (importa l'helper di guardia connection_role_bypasses_rls).
_GATEWAY_WHITELIST = {
    "core/services/system_context.py",
    "vendite/management/commands/run_fatturazione_batch.py",
    "core/middleware/jwt_audit_middleware.py",
}
# L'alias DB compare anche dove il canale è cablato (command) e nel gateway.
_ALIAS_WHITELIST = {
    "core/services/system_context.py",
    "vendite/management/commands/run_fatturazione_batch.py",
}


def _offending_files(needle: str, whitelist: set[str]) -> list[str]:
    """Scopo: file .py (escludendo i test) che contengono `needle` ma non sono
    nella whitelist. Ritorna i path relativi ad apps/ in violazione."""
    offenders: list[str] = []
    for path in _APPS_ROOT.rglob("*.py"):
        rel = path.relative_to(_APPS_ROOT).as_posix()
        if "/tests/" in f"/{rel}" or rel.startswith("tests/"):
            continue  # i test possono riferirsi liberamente al canale
        if rel in whitelist:
            continue
        if needle in path.read_text(encoding="utf-8"):
            offenders.append(rel)
    return offenders


class SystemContextUsageWhitelistTests(TestCase):
    # Scopo: il gateway non deve essere usato fuori dai moduli headless whitelisted.
    def test_system_process_context_only_in_whitelist(self):
        offenders = _offending_files("system_process_context", _GATEWAY_WHITELIST)
        self.assertEqual(
            offenders, [],
            f"system_process_context usato fuori whitelist (rischio BYPASSRLS in "
            f"contesto richiesta): {offenders}. Se è un nuovo processo headless "
            f"legittimo, aggiungerlo a _GATEWAY_WHITELIST.",
        )

    # Scopo: l'alias del canale non deve comparire fuori dai moduli whitelisted.
    def test_system_fatturazione_alias_only_in_whitelist(self):
        offenders = _offending_files("system_fatturazione", _ALIAS_WHITELIST)
        self.assertEqual(
            offenders, [],
            f"alias 'system_fatturazione' referenziato fuori whitelist: {offenders}.",
        )
