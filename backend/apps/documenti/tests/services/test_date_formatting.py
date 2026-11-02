# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari degli helper di data dei context builder documentali
#        (`_date_formatting`): il giorno di un istante e' quello dell'AZIENDA,
#        anche quando l'istante arriva come stringa ISO con offset.
#        Brief un-solo-fuso-aziendale B-6.
# ------------------------------------------------------------
"""Indice test.

1. test_una_stringa_con_offset_e_un_istante_e_vale_il_giorno_dell_azienda
2. test_una_data_pura_non_si_sposta
3. test_un_istante_naive_non_si_converte
4. test_un_valore_illeggibile_resta_com_e
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from django.test import SimpleTestCase

from apps.core.services.fuso_aziendale import fuso_aziendale_forzato
from apps.documenti.services.context_builders._date_formatting import (
    format_date_iso,
    format_date_it,
)


class DateFormattingTests(SimpleTestCase):
    """La data di un documento."""

    # Scopo: fissa il fuso dell'azienda a Roma per ogni test della classe.
    def setUp(self) -> None:
        self.enterContext(fuso_aziendale_forzato("Europe/Rome"))

    # 1. Le 23:30 UTC del 14 sono il 15 a Roma: come `datetime`, come stringa
    #    con `+00:00` e come stringa con `Z`. Fino al 2026-10-09 la stringa si
    #    tagliava ai primi dieci caratteri, cioe' il giorno UTC.
    def test_una_stringa_con_offset_e_un_istante_e_vale_il_giorno_dell_azienda(self) -> None:
        for valore in (
            datetime(2026, 9, 14, 23, 30, tzinfo=UTC),
            "2026-09-14T23:30:00+00:00",
            "2026-09-14T23:30:00Z",
        ):
            with self.subTest(valore=valore):
                self.assertEqual(format_date_it(valore), "15-09-2026")
                self.assertEqual(format_date_iso(valore), "2026-09-15")

    # 2. Una data senza ora non ha un fuso e non si sposta.
    def test_una_data_pura_non_si_sposta(self) -> None:
        self.assertEqual(format_date_it("2026-09-14"), "14-09-2026")
        self.assertEqual(format_date_it(date(2026, 9, 14)), "14-09-2026")

    # 3. Un istante senza offset (`timestamp without time zone`) non porta un
    #    fuso: vale il suo giorno, non si converte.
    def test_un_istante_naive_non_si_converte(self) -> None:
        self.assertEqual(format_date_it("2026-09-14T23:30:00"), "14-09-2026")

    # 4. None resta None; cio' che non si legge torna com'e' (contratto del
    #    modulo), compresa una stringa con l'ora malformata.
    def test_un_valore_illeggibile_resta_com_e(self) -> None:
        self.assertIsNone(format_date_it(None))
        for valore in ("non una data", "2026-13-45", "2026-09-14T25:00:00Z"):
            with self.subTest(valore=valore):
                self.assertEqual(format_date_it(valore), valore)
