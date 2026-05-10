# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit dei formattatori locale (DEF-1, italiano default).
#
# Indice test (0..N):
#   format_date
#     0. format_date_da_date
#     1. format_date_da_datetime
#     2. format_date_da_iso_string
#     3. format_date_none_returns_empty
#     4. format_date_string_invalida_passthrough
#   format_datetime
#     5. format_datetime_default_no_seconds
#     6. format_datetime_with_seconds
#     7. format_datetime_da_iso_con_tz
#   format_bool
#     8. format_bool_true_si
#     9. format_bool_false_no
#    10. format_bool_string_truthy
#    11. format_bool_none_empty
#   format_number
#    12. format_number_int_no_thousands
#    13. format_number_thousand_format
#    14. format_number_currency_eur
#    15. format_number_percent_2
#    16. format_number_decimal_separator_italiano
#   format_for_export (dispatcher)
#    17. dispatcher_tipo_dato_date
#    18. dispatcher_tipo_dato_datetime
#    19. dispatcher_tipo_dato_boolean
#    20. dispatcher_tipo_dato_numeric_con_formato
#    21. dispatcher_string_passthrough
#    22. dispatcher_none_empty
#    23. dispatcher_fallback_isinstance_date
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.test import SimpleTestCase

from apps.core.services.locale_formatters import (
    format_bool,
    format_date,
    format_datetime,
    format_for_export,
    format_number,
)


class FormatDateTests(SimpleTestCase):
    def test_format_date_da_date(self) -> None:
        self.assertEqual(format_date(date(2026, 5, 10)), "10-05-2026")

    def test_format_date_da_datetime(self) -> None:
        # datetime e' anche date: prendi solo la parte data
        self.assertEqual(
            format_date(datetime(2026, 5, 10, 17, 30)),
            "10-05-2026",
        )

    def test_format_date_da_iso_string(self) -> None:
        self.assertEqual(format_date("2026-05-10"), "10-05-2026")

    def test_format_date_none_returns_empty(self) -> None:
        self.assertEqual(format_date(None), "")

    def test_format_date_string_invalida_passthrough(self) -> None:
        # "ieri" non e' parsabile -> ritorna stringa originale per non
        # perdere informazione.
        self.assertEqual(format_date("ieri"), "ieri")


class FormatDatetimeTests(SimpleTestCase):
    def test_format_datetime_default_no_seconds(self) -> None:
        self.assertEqual(
            format_datetime(datetime(2026, 5, 10, 17, 30, 45)),
            "10-05-2026 17:30",
        )

    def test_format_datetime_with_seconds(self) -> None:
        self.assertEqual(
            format_datetime(datetime(2026, 5, 10, 17, 30, 45), with_seconds=True),
            "10-05-2026 17:30:45",
        )

    def test_format_datetime_da_iso_con_tz(self) -> None:
        # ISO con offset esplicito: il parsing rispetta TZ ma il
        # formato output e' "naive" (senza TZ visibile).
        self.assertEqual(
            format_datetime("2026-05-10T17:30:00+02:00"),
            "10-05-2026 17:30",
        )


class FormatBoolTests(SimpleTestCase):
    def test_format_bool_true_si(self) -> None:
        self.assertEqual(format_bool(True), "Si")

    def test_format_bool_false_no(self) -> None:
        self.assertEqual(format_bool(False), "No")

    def test_format_bool_string_truthy(self) -> None:
        self.assertEqual(format_bool("true"), "Si")
        self.assertEqual(format_bool("False"), "No")
        self.assertEqual(format_bool("sì"), "Si")
        self.assertEqual(format_bool("0"), "No")

    def test_format_bool_none_empty(self) -> None:
        self.assertEqual(format_bool(None), "")


class FormatNumberTests(SimpleTestCase):
    def test_format_number_int_no_thousands(self) -> None:
        # Int senza formato: niente migliaia (preserva ID).
        self.assertEqual(format_number(1000), "1000")

    def test_format_number_thousand_format(self) -> None:
        self.assertEqual(format_number(1234567, formato="thousand"), "1.234.567")
        self.assertEqual(format_number(1234.56, formato="thousand"), "1.234,56")

    def test_format_number_currency_eur(self) -> None:
        self.assertEqual(
            format_number(Decimal("1234.5"), formato="currency_eur"),
            "1.234,50 €",
        )
        self.assertEqual(
            format_number(0, formato="currency_eur"),
            "0,00 €",
        )

    def test_format_number_percent_2(self) -> None:
        # 0.1234 e' la frazione 0..1 -> 12,34%
        self.assertEqual(
            format_number(Decimal("0.1234"), formato="percent_2"),
            "12,34%",
        )

    def test_format_number_decimal_separator_italiano(self) -> None:
        self.assertEqual(format_number(3.14), "3,14")


class FormatForExportDispatcherTests(SimpleTestCase):
    def test_dispatcher_tipo_dato_date(self) -> None:
        self.assertEqual(
            format_for_export(date(2026, 5, 10), tipo_dato="date"),
            "10-05-2026",
        )

    def test_dispatcher_tipo_dato_datetime(self) -> None:
        self.assertEqual(
            format_for_export(
                datetime(2026, 5, 10, 17, 30),
                tipo_dato="datetime",
            ),
            "10-05-2026 17:30",
        )

    def test_dispatcher_tipo_dato_boolean(self) -> None:
        self.assertEqual(format_for_export(True, tipo_dato="boolean"), "Si")
        self.assertEqual(format_for_export(False, tipo_dato="boolean"), "No")

    def test_dispatcher_tipo_dato_numeric_con_formato(self) -> None:
        self.assertEqual(
            format_for_export(
                Decimal("1234.5"),
                tipo_dato="numeric",
                formato="currency_eur",
            ),
            "1.234,50 €",
        )

    def test_dispatcher_string_passthrough(self) -> None:
        self.assertEqual(format_for_export("hello", tipo_dato="string"), "hello")

    def test_dispatcher_none_empty(self) -> None:
        self.assertEqual(format_for_export(None, tipo_dato="date"), "")

    def test_dispatcher_fallback_isinstance_date(self) -> None:
        # Senza tipo_dato esplicito: dispatch via isinstance.
        self.assertEqual(format_for_export(date(2026, 5, 10)), "10-05-2026")
