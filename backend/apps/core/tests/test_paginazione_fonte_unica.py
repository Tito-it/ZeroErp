# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio della FONTE UNICA della paginazione delle liste
#        (`apps.core.api.constants`: `MAX_LIMIT`, `DEFAULT_LIMIT`; decisione di
#        Tid del 2026-09-28). Fino a quel giorno il tetto di pagina aveva tre
#        costanti e ~45 `200` scritti a mano, e il default due valori (50 e
#        25): una lista rispondeva 50 righe e la vicina 25, senza che nessuno
#        l'avesse deciso.
# Note: statico, nessun DB. Legge il sorgente di `apps/` (test esclusi) e
#       cerca le due forme in cui il numero torna: il TETTO (`200` accanto a
#       limit / page_size) ovunque, e il DEFAULT scritto nella query string di
#       una view. Le eccezioni stanno in `_AMMESSI`, ciascuna col suo motivo.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_il_tetto_di_pagina_non_e_scritto_a_mano
2) test_il_default_delle_view_non_e_scritto_a_mano
3) test_le_eccezioni_esistono_ancora
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from apps.core.api.constants import DEFAULT_LIMIT, MAX_LIMIT

_APPS = Path(__file__).resolve().parents[2]

# Il tetto: il suo numero accanto a un limite di pagina, fuori da un commento.
_TETTO = re.compile(
    rf"(limit|page_size|max_rows|safe_)[^#\n]*(?<![\w.]){MAX_LIMIT}(?![\w.])", re.IGNORECASE,
)
# Il default di una view: un numero come ripiego della query string.
_DEFAULT_VIEW = re.compile(
    r"""(?:get\(\s*["'](?:page_size|limit)["']\s*,\s*["']\d+["']\s*\)"""
    r"""|["'](?:page_size|limit)["']\)?\s*,\s*\d+\s*\)"""
    r"""|["'](?:page_size|limit)["']\)\s*or\s*\d+)""",
)

# (file relativo ad apps/, frammento della riga) → perche' e' ammesso.
_AMMESSI: dict[tuple[str, str], str] = {
    ("core/api/constants.py", f"MAX_LIMIT = {MAX_LIMIT}"): "la fonte",
    # Liste di EVENTI (giornale, registro, segnalazioni): partono da 100
    # dichiarato nella loro doc OpenAPI — un registro si legge a blocchi piu'
    # lunghi di una lista anagrafica. Il tetto resta `MAX_LIMIT`.
    ("pratiche/api/views.py", 'qp.get("limit", "100")'): "giornale pratica, default 100 dichiarato",
    ("vendite/api/views.py", 'q.get("limit") or "100"'): "task run del lotto (`ApiLottoTaskRuns`), contratto del client storico (FE-2)",
    ("vendite/api/views.py", 'qp.get("limit", "100")'): "registro commessa, default 100 dichiarato",
    # Lookup (autocomplete): un contratto suo, piu' corto di una pagina.
    ("core/api/views_lookup.py", 'qp.get("limit"), 30)'): "lookup: 30 righe, tetto 100",
    ("catalogo/api/views.py", '"limit", 20)'): "lookup articoli: 20 righe",
    # Il ripiego NON si usa: la riga gira solo se il client ha mandato `limit`.
    ("anagrafiche/api/views_billing_account.py", 'qp_int_strict(raw_limit, "limit", 0)'): "solo con limit esplicito",
    ("anagrafiche/api/views_istanze_utility.py", 'qp_int_strict(raw_limit, "limit", 0)'): "solo con limit esplicito",
    # Non e' una pagina: righe prese per giro dal drainer della coda lavori.
    ("core/services/coda_lavori/drainer_service.py", "_LIMIT_DEFAULT = 200"): "batch del drainer, non una pagina",
}


# Scopo: le righe di codice di `apps/` (test e migration esclusi), commenti tolti.
def _righe():
    for p in sorted(_APPS.rglob("*.py")):
        rel = p.relative_to(_APPS).as_posix()
        if "/tests/" in f"/{rel}" or "/migrations/" in f"/{rel}":
            continue
        for n, riga in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            codice = riga.split("#", 1)[0]
            if codice.strip():
                yield rel, n, codice


def _ammessa(rel: str, codice: str) -> bool:
    return any(rel == f and frammento in codice for (f, frammento) in _AMMESSI)


class PaginazioneFonteUnicaTests(unittest.TestCase):

    def test_il_tetto_di_pagina_non_e_scritto_a_mano(self) -> None:
        trovate = [
            f"{rel}:{n}: {codice.strip()}"
            for rel, n, codice in _righe()
            if _TETTO.search(codice) and not _ammessa(rel, codice)
        ]
        self.assertEqual(
            trovate, [],
            "il tetto di pagina scritto come numero: usare `MAX_LIMIT` "
            "(apps.core.api.constants) o `limiti_pagina`:\n" + "\n".join(trovate),
        )

    def test_il_default_delle_view_non_e_scritto_a_mano(self) -> None:
        trovate = [
            f"{rel}:{n}: {codice.strip()}"
            for rel, n, codice in _righe()
            if "/api/" in f"/{rel}" and _DEFAULT_VIEW.search(codice)
            and not _ammessa(rel, codice)
        ]
        self.assertEqual(
            trovate, [],
            f"righe per pagina di default scritte come numero in una view: usare "
            f"`DEFAULT_LIMIT` ({DEFAULT_LIMIT}), o dichiarare l'eccezione in "
            f"`_AMMESSI` col suo motivo:\n" + "\n".join(trovate),
        )

    # ⛔ Un'eccezione che non trova piu' la sua riga e' una porta rimasta aperta:
    #    la prossima riga che le somiglia passerebbe senza motivo.
    def test_le_eccezioni_esistono_ancora(self) -> None:
        righe = [(rel, codice) for rel, _n, codice in _righe()]
        orfane = [
            f"{f}: {frammento}" for (f, frammento) in _AMMESSI
            if not any(rel == f and frammento in codice for rel, codice in righe)
        ]
        self.assertEqual(orfane, [], "eccezioni senza piu' la loro riga: toglierle")
