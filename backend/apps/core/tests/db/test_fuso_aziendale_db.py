# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il BB `fuso_aziendale` sul database vero — la giuntura fra le due
#        meta' della stessa regola: Python converte col fuso che legge da
#        `script.fn_fuso_operativo()`, il DB con `fn_giorno_operativo` /
#        `fn_data_operativa`. Devono dare lo stesso giorno per lo stesso istante.
# Note: ⛔ Gli istanti si COSTRUISCONO a cavallo della mezzanotte, d'estate e
#        d'inverno, nei due versi: un confronto sull'ora di adesso sarebbe
#        verde quasi sempre senza provare niente. Il fuso e' quello vero del
#        parametro, qualunque sia: il test non lo suppone.
# ------------------------------------------------------------
"""Indice test previsti (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_il_fuso_del_db_e_noto_a_python
     il nome restituito da fn_fuso_operativo e' un ZoneInfo valido, ed e' quello del BB.
2. test_python_e_db_danno_lo_stesso_giorno_allo_stesso_istante
     istanti costruiti a cavallo della mezzanotte: in_ora_locale(...).date() == fn_giorno_operativo(...).
3. test_oggi_aziendale_e_fn_data_operativa_coincidono
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest import TestCase
from zoneinfo import ZoneInfo

from django.db import connection

from apps.core.db.core_repository import CoreRepository
from apps.core.services.fuso_aziendale import fuso_aziendale, oggi_aziendale
from apps.core.services.locale_formatters import in_ora_locale
from apps.core.tests.db_e2e import richiedi_db_provvisto


class FusoAziendaleDbTests(TestCase):
    """Python e DB, stesso fuso, stesso giorno."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # 1. Il nome del DB e' noto all'archivio dei fusi di Python, ed e' quello
    #    che il BB tiene in cache.
    def test_il_fuso_del_db_e_noto_a_python(self) -> None:
        nome = CoreRepository().get_fuso_operativo()
        self.assertEqual(ZoneInfo(nome).key, fuso_aziendale().key)

    # 2. ⭐ Per ogni istante a ±30 minuti dalla mezzanotte AZIENDALE, d'estate
    #    e d'inverno, Python e DB dicono lo stesso giorno. La mezzanotte si
    #    calcola nel fuso vero, cosi' il caso di confine esiste in ogni fuso.
    def test_python_e_db_danno_lo_stesso_giorno_allo_stesso_istante(self) -> None:
        fuso = fuso_aziendale()
        istanti = []
        for giorno in (date(2026, 7, 15), date(2026, 1, 15)):
            mezzanotte = datetime(giorno.year, giorno.month, giorno.day, tzinfo=fuso).astimezone(UTC)
            istanti += [mezzanotte - timedelta(minutes=30), mezzanotte + timedelta(minutes=30)]
        with connection.cursor() as cur:
            for istante in istanti:
                cur.execute("SELECT script.fn_giorno_operativo(%s)", [istante])
                row = cur.fetchone()
                assert row is not None
                self.assertEqual(in_ora_locale(istante).date(), row[0], istante.isoformat())

    # 3. L'«oggi» di Python e quello del DB sono lo stesso giorno. Si legge
    #    prima e dopo: a cavallo della mezzanotte il DB puo' stare in mezzo.
    def test_oggi_aziendale_e_fn_data_operativa_coincidono(self) -> None:
        prima = oggi_aziendale()
        with connection.cursor() as cur:
            cur.execute("SELECT script.fn_data_operativa()")
            row = cur.fetchone()
        dopo = oggi_aziendale()
        assert row is not None
        self.assertIn(row[0], {prima, dopo})
