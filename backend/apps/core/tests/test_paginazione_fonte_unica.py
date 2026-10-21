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
#       cerca le tre forme in cui il numero torna: il TETTO (`200` accanto a
#       limit / page_size) ovunque, il DEFAULT scritto nella query string di
#       una view, e il DEFAULT di una FIRMA (`limit: int = 50` in un service o
#       un repository: §9.6 punto 3 del brief-db-liste-righe-documento, Tid
#       2026-10-04 — una lista aveva il suo default nella view e un altro,
#       diverso, nella firma). Le eccezioni stanno in `_AMMESSI` e
#       `_FIRME_AMMESSE`, ciascuna col suo motivo.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_il_tetto_di_pagina_non_e_scritto_a_mano
2) test_il_default_delle_view_non_e_scritto_a_mano
3) test_le_eccezioni_esistono_ancora
4) test_il_default_delle_firme_non_e_scritto_a_mano
5) test_le_eccezioni_delle_firme_esistono_ancora
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from apps.core.api.constants import DEFAULT_LIMIT, DEFAULT_LIMIT_EVENTI, MAX_LIMIT

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
    # ⭐ Le liste di EVENTI (giornale pratica, registro commessa, task run del
    #    lotto) non sono piu' eccezioni dal 2026-10-04: il loro 100 e' la
    #    costante `DEFAULT_LIMIT_EVENTI`, letta da view e firme.
    # Lookup (autocomplete): un contratto suo, piu' corto di una pagina.
    ("core/api/views_lookup.py", '"limit", 30)'): "lookup: 30 righe, tetto 100",
    ("catalogo/api/views.py", '"limit", 20)'): "lookup articoli: 20 righe",
    # Il ripiego NON si usa: la riga gira solo se il client ha mandato `limit`.
    ("anagrafiche/api/views_billing_account.py", 'qp_int_strict(raw_limit, "limit", 0)'): "solo con limit esplicito",
    ("anagrafiche/api/views_istanze_utility.py", 'qp_int_strict(raw_limit, "limit", 0)'): "solo con limit esplicito",
    # Non e' una pagina: righe prese per giro dal drainer della coda lavori.
    ("core/services/coda_lavori/drainer_service.py", "_LIMIT_DEFAULT = 200"): "batch del drainer, non una pagina",
}


# Il default di una FIRMA di service o repository: un numero.
_DEFAULT_FIRMA = re.compile(r"\b(?:limit|page_size): int = \d+")

# (file relativo ad apps/, nome della funzione) → perche' il numero e' ammesso.
# ⚠️ Non sono pagine di lista: un lookup ha un tetto suo (le righe di una
#    tendina), un batch prende cio' che deve lavorare.
_FIRME_AMMESSE: dict[tuple[str, str], str] = {
    ("catalogo/services/catalogo_service.py", "fn_lookup_articoli"): "lookup articoli: 20 righe",
    ("catalogo/services/catalogo_service.py", "fn_lookup_articoli_ammessi"): "picker delle righe di documento: 20 righe, come il lookup",
    ("anagrafiche/db/conti_bancari_repository.py", "search_conti_bancari"): "autocomplete IBAN",
    ("anagrafiche/db/conti_bancari_repository.py", "search_bank_branches"): "autocomplete filiali",
    ("anagrafiche/services/conti_bancari_service.py", "search_conti_bancari"): "autocomplete IBAN",
    ("anagrafiche/services/conti_bancari_service.py", "search_bank_branches"): "autocomplete filiali",
    ("core/db/lookup_repository.py", "search_comuni"): "lookup comuni",
    ("core/db/lookup_repository.py", "search_stradario"): "lookup stradario",
    ("core/db/lookup_repository.py", "search_stradario_generale"): "lookup stradario",
    ("core/db/dbops_repository.py", "list_lookup_codici"): "lookup codici: la pagina delle tendine (PROJECT_CONTEXT, «Tendine del lookup generico»)",
    ("vendite/db/pipeline_repository.py", "list_attivita_da_fatturare"): "batch della pipeline",
    ("vendite/db/pipeline_repository.py", "list_fatture_by_lotto"): "batch della pipeline",
    ("vendite/db/pipeline_repository.py", "list_fatture_by_lotto_ordinate"): "batch della pipeline",
    ("vendite/db/commesse_repository.py", "list_commesse_emittibili"): "batch di emissione",
    ("vendite/db/commesse_repository.py", "list_emittibili_lane"): "batch di emissione",
    ("vendite/services/fatturazione_driver_service.py", "esegui_giro_fatturazione"): "batch del giro di fatturazione",
}


# Scopo: le firme con un default numerico di pagina: (file, funzione, riga).
#        La funzione e' l'ultimo `def` sopra la riga (la firma va a capo).
def _firme_con_numero():
    for p in sorted(_APPS.rglob("*.py")):
        rel = p.relative_to(_APPS).as_posix()
        if "/tests/" in f"/{rel}" or "/migrations/" in f"/{rel}":
            continue
        funzione = None
        for n, riga in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            m = re.search(r"\bdef (\w+)\(", riga)
            if m:
                funzione = m.group(1)
            if _DEFAULT_FIRMA.search(riga.split("#", 1)[0]):
                yield rel, funzione, n


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

    def test_il_default_delle_firme_non_e_scritto_a_mano(self) -> None:
        trovate = [
            f"{rel}:{n} ({funzione})"
            for rel, funzione, n in _firme_con_numero()
            if (rel, funzione) not in _FIRME_AMMESSE
        ]
        self.assertEqual(
            trovate, [],
            f"righe per pagina di default scritte come numero in una firma: usare "
            f"`DEFAULT_LIMIT` ({DEFAULT_LIMIT}) o, per una lista di eventi, "
            f"`DEFAULT_LIMIT_EVENTI` ({DEFAULT_LIMIT_EVENTI}); un lookup o un batch va "
            f"dichiarato in `_FIRME_AMMESSE` col suo motivo:\n" + "\n".join(trovate),
        )

    def test_le_eccezioni_delle_firme_esistono_ancora(self) -> None:
        presenti = {(rel, funzione) for rel, funzione, _n in _firme_con_numero()}
        orfane = [f"{f}: {fn}" for (f, fn) in _FIRME_AMMESSE if (f, fn) not in presenti]
        self.assertEqual(orfane, [], "eccezioni senza piu' la loro firma: toglierle")
