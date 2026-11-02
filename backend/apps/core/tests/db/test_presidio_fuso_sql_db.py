# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: PRESIDIO — nel codice del backend nessuna colonna ISTANTE
#        (`timestamptz`) passa al calendario nel fuso della SESSIONE:
#          - `col::date`                       (il giorno della sessione);
#          - `col >= %s::date` / `%s::timestamptz` (la mezzanotte della sessione);
#          - `date_trunc('month', col)`        (il mese della sessione).
#        Le strade giuste sono il BB `predicato_giorno_operativo` (filtri per
#        giorno) e `script.fn_giorno_operativo(col)` (giorno/mese di un istante).
#        Brief un-solo-fuso-aziendale B-9.
# Note: ⭐ QUALI colonne sono istanti lo dice il CATALOGO del DB vero
#        (`information_schema.columns`), non un elenco: e' struttura, non
#        popolazione. Un nome che e' `date` in una tabella e `timestamptz` in
#        un'altra non si decide dal nome, ed e' escluso — calcolato, e il test
#        dice quanti sono.
#        ⚠️ Scansione testuale: trova le forme che conosce. La controprova
#        prova che le vede.
# ------------------------------------------------------------
"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_nessuna_colonna_istante_passa_al_calendario_della_sessione
2. test_la_scansione_vede_le_forme_vietate (controprova)
"""

from __future__ import annotations

import re
from unittest import TestCase

from django.db import connection

from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.core.tests.test_presidio_fuso_sql import righe_di_codice

_SCHEMI_DI_SISTEMA = ("pg_catalog", "information_schema")


# Scopo: i nomi di colonna che sono `timestamptz` in qualche tabella e MAI
#        `date` altrove, e quanti nomi sono stati esclusi perche' ambigui.
def _nomi_istante() -> tuple[set[str], int]:
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
              FROM information_schema.columns
             WHERE data_type IN ('timestamp with time zone', 'date')
               AND table_schema <> ALL(%s)
            """,
            [list(_SCHEMI_DI_SISTEMA)],
        )
        righe = cur.fetchall()
    istanti = {c for c, t in righe if t == "timestamp with time zone"}
    date = {c for c, t in righe if t == "date"}
    return istanti - date, len(istanti & date)


# Scopo: le tre forme vietate per un insieme di nomi di colonna istante.
def _forme_vietate(nomi: set[str]) -> list[re.Pattern[str]]:
    alt = "|".join(sorted(map(re.escape, nomi), key=len, reverse=True))
    col = rf"\b(?:\w+\.)?(?:{alt})\b"
    return [
        re.compile(rf"{col}\s*::\s*date\b"),
        re.compile(rf"{col}\s*(?:>=|<=|<|>|=)\s*\(?\s*%s::(?:date|timestamptz)"),
        re.compile(rf"date_trunc\(\s*'\w+'\s*,\s*{col}\s*\)"),
    ]


class ColonneIstanteNonAlCalendarioDellaSessioneTests(TestCase):
    """Nessun istante diventa un giorno nel fuso della sessione."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()
        cls.nomi, cls.ambigui = _nomi_istante()

    # 1. Zero righe di codice con una delle tre forme.
    def test_nessuna_colonna_istante_passa_al_calendario_della_sessione(self) -> None:
        self.assertTrue(self.nomi, "il catalogo non ha colonne timestamptz: la scansione sarebbe vuota")
        forme = _forme_vietate(self.nomi)
        trovate = [
            f"{p}:{n}: {r.strip()}"
            for p, n, r in righe_di_codice()
            if any(f.search(r) for f in forme)
        ]
        self.assertEqual(
            trovate, [],
            "usa predicato_giorno_operativo (filtri) o script.fn_giorno_operativo(col) "
            f"(nomi ambigui esclusi: {self.ambigui})",
        )

    # 2. Controprova sulle forme ritirate dal brief (§4.2 a), con colonne che
    #    il catalogo dichiara istanti; e la forma giusta passa.
    def test_la_scansione_vede_le_forme_vietate(self) -> None:
        self.assertIn("data_insert", self.nomi)
        forme = _forme_vietate(self.nomi)
        for vietata in (
            "a.data_insert::date >= %s",
            "AND el.data_insert >= %s::date",
            "AND executed_at <= %s::timestamptz + interval '1 day'",
            "p.data_insert < (%s::date + INTERVAL '1 day')",
            "to_char(date_trunc('month', started_at), 'YYYY-MM-DD')",
        ):
            with self.subTest(vietata=vietata):
                self.assertTrue(any(f.search(vietata) for f in forme))
        giusta = "a.data_insert >= script.fn_inizio_giorno_operativo(%s::date)"
        self.assertFalse(any(f.search(giusta) for f in forme))
