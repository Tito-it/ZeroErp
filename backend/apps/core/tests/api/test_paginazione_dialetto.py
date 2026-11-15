# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Una lista che pagina con `limit`/`offset` rifiuta `page`/`page_size`
#        con un 400, invece di ignorarli (decisione Tid 2026-10-20,
#        brief-be-verifica-documentazione-api §A3).
#        Fino a quel giorno chi li mandava riceveva sempre la prima pagina, di
#        25 righe, senza errore: la tab competenze delle definizioni workflow
#        chiedeva `page_size: 200` alla lista operatori e ne vedeva 25.
#        Il BB e' `richiedi_limit_offset`: lo chiama `parse_list_params` e ogni
#        lista che legge `limit`/`offset` a mano. Il 400 lo da'
#        `ApiExceptionMiddleware` sul `ValueError`.
# ------------------------------------------------------------
"""Indice test:
1. test_page_e_page_size_sono_rifiutati
2. test_limit_offset_e_assenza_passano
3. test_parse_list_params_li_rifiuta
4. test_pagina_da_query_rifiuta_illeggibile_e_fuori_limite
4b. test_nessuna_lista_legge_limit_offset_a_mano
4c. test_nessuna_view_legge_page_page_size (2026-10-21, un dialetto solo)
5. FlagQueryStringTests.test_vocabolario_unico (§A6)
6. FlagQueryStringTests.test_le_copie_sono_ritirate
"""

from __future__ import annotations

from unittest import TestCase

from django.http import QueryDict

from apps.core.api.payload_validators import pagina_da_query, parse_list_params, richiedi_limit_offset
from apps.core.tests._repo import repo_root


class PaginazioneDialettoTests(TestCase):
    def test_page_e_page_size_sono_rifiutati(self) -> None:
        for qs in ("page=2", "page_size=200", "page=1&page_size=10", "limit=10&page=2"):
            with self.subTest(qs=qs), self.assertRaisesRegex(ValueError, "_non_ammesso_usare_limit_offset"):
                richiedi_limit_offset(QueryDict(qs))

    def test_limit_offset_e_assenza_passano(self) -> None:
        for qs in ("", "limit=10&offset=20", "search=x"):
            with self.subTest(qs=qs):
                richiedi_limit_offset(QueryDict(qs))

    def test_parse_list_params_li_rifiuta(self) -> None:
        with self.assertRaisesRegex(ValueError, "page_size_non_ammesso_usare_limit_offset"):
            parse_list_params(QueryDict("page_size=200"))
        self.assertEqual(parse_list_params(QueryDict("limit=10&offset=20"))["offset"], 20)

    # ⛔ `limit`/`offset` si leggono in UN punto (`pagina_da_query`, regola
    #    del 2, ok Tid 2026-10-21): illeggibile e' un 400, e cosi' il fuori
    #    limite. Prima `?limit=abc` ripiegava in silenzio e `limit=500` diventava 200.
    def test_pagina_da_query_rifiuta_illeggibile_e_fuori_limite(self) -> None:
        for qs in ("limit=abc", "offset=xyz", "limit=1.5"):
            with self.subTest(qs=qs), self.assertRaisesRegex(ValueError, "_invalid"):
                pagina_da_query(QueryDict(qs))
        self.assertEqual(pagina_da_query(QueryDict("")), (25, 0))
        self.assertEqual(pagina_da_query(QueryDict("limit=200&offset=400")), (200, 400))
        # ⛔ Il fuori limite e' un 400, non una riduzione muta (Tid 2026-10-21).
        for qs, errore in (
            ("limit=0", "limit_fuori_limiti_1_200"),
            ("limit=-1", "limit_fuori_limiti_1_200"),
            ("limit=201", "limit_fuori_limiti_1_200"),
            ("offset=-5", "offset_negativo"),
        ):
            with self.subTest(qs=qs), self.assertRaisesRegex(ValueError, errore):
                pagina_da_query(QueryDict(qs))
        with self.assertRaisesRegex(ValueError, "limit_fuori_limiti_1_100"):
            pagina_da_query(QueryDict("limit=101"), max_limit=100)
        with self.assertRaisesRegex(ValueError, "page_non_ammesso"):
            pagina_da_query(QueryDict("page=2"))

    # ⚠️ Il presidio legge il CODICE: una lista che rilegge `limit`/`offset`
    #    a mano fuori dal BB e' la copia che la regola del 2 ha ritirato. Un
    #    controllo che si dimentica non da' errore — lo da' questo test.
    def test_nessuna_lista_legge_limit_offset_a_mano(self) -> None:
        import re

        apps = repo_root() / "backend/apps"
        lettura = re.compile(r"""(?:qp|q|query_params)\.get\(["'](?:limit|offset)["']""")
        # Le sole letture ammesse: il BB, e i lookup che leggono il solo
        # `limit` (quanti suggerimenti, un altro significato: non paginano).
        ammessi = {
            "core/api/payload_validators.py", "core/api/views_lookup.py", "catalogo/api/views.py",
            "anagrafiche/api/views_istanze_utility.py", "anagrafiche/api/views_soggetti.py",
            "anagrafiche/api/views_billing_account.py",
        }
        trovate = [
            f"{f.relative_to(apps)}:{n}"
            for f in apps.rglob("*.py")
            if "tests" not in f.parts and str(f.relative_to(apps)) not in ammessi
            for n, riga in enumerate(f.read_text(errors="ignore").splitlines(), 1)
            if lettura.search(riga)
        ]
        self.assertEqual(trovate, [])

    # ⛔ Un dialetto solo (2026-10-21): nessuna view legge piu' `page`/`page_size`
    #    dalla query string. Fino a quel giorno una ventina di liste (dashboard,
    #    pagamenti, lotti, tracciamento, note, ricerca) li leggevano e
    #    ritraducevano in offset; il frontend li calcolava da `limit`/`offset`
    #    per parlare con loro. Una lista nuova scritta col vecchio dialetto fa
    #    rosso qui. (I tool dell'assistente AI hanno un loro `page_size`: e' un
    #    parametro del tool verso il modello, non della query string.)
    def test_nessuna_view_legge_page_page_size(self) -> None:
        import re

        apps = repo_root() / "backend/apps"
        lettura = re.compile(r"""(?:qp|q|query_params)\.get\(["']page(?:_size)?["']""")
        trovate = [
            f"{f.relative_to(apps)}:{n}"
            for f in apps.rglob("*.py")
            if "tests" not in f.parts
            for n, riga in enumerate(f.read_text(errors="ignore").splitlines(), 1)
            if lettura.search(riga)
        ]
        self.assertEqual(trovate, [])


# Scopo: ⛔ Il flag della query string ha UN vocabolario: `true`/`false`
#        (maiuscole e spazi ammessi), assente o vuoto = default, il resto un
#        400 (decisione Tid 2026-10-20, brief-be-verifica-documentazione-api
#        §A6). Fino a quel giorno quattro helper davano a `1`, `yes`, `banana`
#        quattro letture diverse, sempre in silenzio.
class FlagQueryStringTests(TestCase):
    def test_vocabolario_unico(self) -> None:
        from apps.core.api.payload_validators import qp_bool_optional

        for raw, atteso in (("true", True), (" TRUE ", True), ("false", False), ("False", False)):
            with self.subTest(raw=raw):
                self.assertIs(qp_bool_optional(raw, "x"), atteso)
        for raw in (None, "", "  "):
            with self.subTest(assente=raw):
                self.assertIsNone(qp_bool_optional(raw, "x"))
                self.assertIs(qp_bool_optional(raw, "x", default=True), True)
        for raw in ("1", "0", "yes", "no", "on", "si", "banana"):
            with self.subTest(estraneo=raw), self.assertRaisesRegex(ValueError, "x_invalid"):
                qp_bool_optional(raw, "x")

    def test_le_copie_sono_ritirate(self) -> None:
        from apps.core.api import payload_validators
        from apps.core.services import value_normalizer

        from apps.amm_software.api import views as amm_views

        self.assertFalse(hasattr(payload_validators, "qp_bool"))
        self.assertFalse(hasattr(value_normalizer, "as_bool"))
        self.assertFalse(hasattr(amm_views, "_parse_optional_bool"))
