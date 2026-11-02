# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Guard STATICO — il canale di sistema `BYPASSRLS` NON deve tornare.
#
# ⭐ Questo cancello e' stato GIRATO il 2026-09-05 (R-2), non cancellato.
#    Prima diceva «il gateway si usa solo in questi cinque moduli»: era la forma
#    giusta finche' un uso legittimo esisteva. Adesso non ne esiste piu' nessuno
#    — ogni processo ha la propria identita' e lavora dentro il proprio
#    perimetro — quindi la whitelist e' VUOTA e il presidio dice una cosa piu'
#    forte: **zero occorrenze**.
# ⛔ Perche' non si cancella il file: il pericolo che presidiava non e' sparito,
#    ha cambiato forma. Prima era «qualcuno lo usa dove non deve»; adesso e'
#    «qualcuno lo rimette». Un ruolo che scavalca le policy e' la scorciatoia
#    che verra' in mente al primo processo nuovo che «deve vedere tutte le
#    aziende», e la risposta e' che si crea un utente tecnico, non un
#    passepartout.
# ⚠️ Resta fuori `connection_role_bypasses_rls`, che ha il verso OPPOSTO: non
#    concede il bypass, verifica che la connessione della richiesta non ce
#    l'abbia. Quella si usa, e il middleware la usa.
# Indice test:
#   1) `system_process_context` non compare in nessun modulo applicativo
#   2) l'alias `system_fatturazione` non compare in nessun modulo applicativo
# ------------------------------------------------------------

from __future__ import annotations

from pathlib import Path
from unittest import TestCase

# Radice apps/ del backend (questo file è apps/core/tests/...).
_APPS_ROOT = Path(__file__).resolve().parents[2]

# ⛔ VUOTE, e sono la sostanza del presidio: dal 2026-09-05 non c'e' nessun
#    modulo autorizzato, perche' non c'e' nessun uso legittimo. Se un giorno
#    servisse davvero un'eccezione, si aggiunge QUI con la ragione scritta
#    accanto — non si aggira il test.
_GATEWAY_WHITELIST: set[str] = set()
_ALIAS_WHITELIST: set[str] = set()


def _offending_files(needle: str, whitelist: set[str]) -> list[str]:
    """Scopo: file .py (escludendo i test) che USANO `needle` in codice (non in
    commenti) e non sono nella whitelist. Ritorna i path relativi ad apps/ in
    violazione. Le righe-commento (`#`) sono ignorate: una semplice menzione del
    canale in un commento/docstring-riga non è un uso e non deve far fallire il
    guard (evita falsi positivi ricorrenti su commenti esplicativi)."""
    offenders: list[str] = []
    for path in _APPS_ROOT.rglob("*.py"):
        rel = path.relative_to(_APPS_ROOT).as_posix()
        if "/tests/" in f"/{rel}" or rel.startswith("tests/"):
            continue  # i test possono riferirsi liberamente al canale
        if rel in whitelist:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("#"):
                continue  # riga-commento → non è un uso
            if needle in line:
                offenders.append(rel)
                break
    return offenders


class SystemContextUsageWhitelistTests(TestCase):
    # Scopo: il gateway ritirato non deve ricomparire da nessuna parte.
    def test_system_process_context_non_esiste_piu(self):
        offenders = _offending_files("system_process_context", _GATEWAY_WHITELIST)
        self.assertEqual(
            offenders, [],
            f"Il canale di sistema BYPASSRLS è ricomparso in: {offenders}. "
            "È stato ritirato il 2026-09-05: un processo che deve lavorare più "
            "aziende NON scavalca le policy, ha un utente tecnico per azienda "
            "(script.fn_crea_utente_tecnico) e itera il proprio roster. Se "
            "esistesse davvero un'eccezione, va dichiarata in "
            "_GATEWAY_WHITELIST con la ragione scritta accanto.",
        )

    # Scopo: l'alias del canale non deve comparire fuori dai moduli whitelisted.
    def test_system_fatturazione_alias_only_in_whitelist(self):
        offenders = _offending_files("system_fatturazione", _ALIAS_WHITELIST)
        self.assertEqual(
            offenders, [],
            f"alias 'system_fatturazione' referenziato fuori whitelist: {offenders}.",
        )
