# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#   il fuso e' parte del formato (Tid, 2026-09-14)
#    24. un_istante_aware_si_scrive_in_ora_locale
#    25. un_istante_naive_non_si_tocca
#    26. il_giorno_di_un_datetime_e_quello_locale
#    27. l_export_scrive_l_ora_locale   ⭐ il percorso degli export
#    28. il_fuso_del_processo_non_conta ⭐ TIME_ZONE e fuso attivo a Tokyo
#   format_bool
#     8. format_bool_true_si
#     9. format_bool_false_no
#    10. format_bool_string_truthy
#    11. format_bool_none_empty
#   format_number
#    12. format_number_int_no_thousands
#    13. format_number_thousand_format
#    14. format_number_currency_eur
#    15. format_number_percent_2 (+ currency_eur_6)
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

from datetime import UTC, date, datetime
from decimal import Decimal

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from apps.core.services.fuso_aziendale import fuso_aziendale_forzato

from apps.core.services.locale_formatters import (
    format_bool,
    format_date,
    format_datetime,
    format_for_export,
    format_number,
    in_ora_locale,
)


class FormatDateTests(SimpleTestCase):
    def test_format_date_da_date(self) -> None:
        self.assertEqual(format_date(date(2026, 5, 10)), "10-05-2026")

    def test_format_date_da_datetime(self) -> None:
        # datetime e' anche date: prendi solo la parte data
        self.assertEqual(
            format_date(datetime(2026, 5, 10, 17, 30)),  # noqa: DTZ001 — naive apposta: un istante senza fuso non si converte
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
            format_datetime(datetime(2026, 5, 10, 17, 30, 45)),  # noqa: DTZ001 — naive apposta: un istante senza fuso non si converte
            "10-05-2026 17:30",
        )

    def test_format_datetime_with_seconds(self) -> None:
        self.assertEqual(
            format_datetime(datetime(2026, 5, 10, 17, 30, 45), with_seconds=True),  # noqa: DTZ001 — naive apposta: un istante senza fuso non si converte
            "10-05-2026 17:30:45",
        )

    @fuso_aziendale_forzato("Europe/Rome")
    def test_format_datetime_da_iso_con_tz(self) -> None:
        # ISO con offset esplicito: si scrive in ora LOCALE, senza TZ
        # visibile. A maggio Roma e' +02:00, quindi l'offset del valore e'
        # gia' quello locale e l'ora non cambia.
        self.assertEqual(
            format_datetime("2026-05-10T17:30:00+02:00"),
            "10-05-2026 17:30",
        )


class FusoLocaleTests(SimpleTestCase):
    """Il fuso e' parte del formato (decisione di Tid, 2026-09-14).

    ⛔ Fino a quel giorno i formattatori scrivevano l'ora nel fuso che il
    valore PORTAVA, e con `USE_TZ` la connessione consegna UTC: ogni export
    stampava ore UTC mentre le liste a video le mostravano giuste. Emerso sul
    digest dei presidi (testata locale, corse UTC).

    Il fuso e' un'ipotesi del test, dichiarata col BB (dal 2026-10-09 non e'
    piu' `TIME_ZONE`, che vale 'UTC' ed e' neutro).
    """

    # Scopo: Fissa il fuso dell'azienda a Roma per ogni test della classe.
    def setUp(self) -> None:
        self.enterContext(fuso_aziendale_forzato("Europe/Rome"))

    # 24. Un istante aware — com'e' ogni timestamptz letto dal DB — si scrive
    #     nell'ora dell'azienda, non in quella che porta. A settembre Roma
    #     e' +02:00: le 09:47 UTC sono le 11:47.
    def test_un_istante_aware_si_scrive_in_ora_locale(self) -> None:
        istante = datetime(2026, 9, 14, 9, 47, 32, tzinfo=UTC)
        self.assertEqual(format_datetime(istante), "14-09-2026 11:47")
        self.assertEqual(
            format_datetime(istante, with_seconds=True), "14-09-2026 11:47:32",
        )
        # Anche da stringa ISO, che e' la forma in cui i repository consegnano
        # `isoformat()` di un timestamptz.
        self.assertEqual(
            format_datetime("2026-09-14T09:47:32+00:00", with_seconds=True),
            "14-09-2026 11:47:32",
        )

    # 25. Un naive non porta un fuso: non c'e' niente da convertire, e
    #     `localtime` su un naive solleverebbe. Resta com'e'.
    def test_un_istante_naive_non_si_tocca(self) -> None:
        naive = datetime(2026, 9, 14, 9, 47, 32)  # noqa: DTZ001 — naive apposta: un istante senza fuso non si converte
        self.assertIs(in_ora_locale(naive), naive)
        self.assertEqual(format_datetime(naive), "14-09-2026 09:47")
        self.assertEqual(format_datetime("2026-09-14T09:47:32"), "14-09-2026 09:47")

    # 26. Da un datetime si prende il GIORNO locale: le 23:30 UTC del 14 sono
    #     gia' il 15 a Roma. Vale per `format_date` e per il dispatcher.
    def test_il_giorno_di_un_datetime_e_quello_locale(self) -> None:
        a_cavallo = datetime(2026, 9, 14, 23, 30, tzinfo=UTC)
        self.assertEqual(format_date(a_cavallo), "15-09-2026")
        self.assertEqual(format_date("2026-09-14T23:30:00+00:00"), "15-09-2026")
        self.assertEqual(format_for_export(a_cavallo, tipo_dato="date"), "15-09-2026")
        # Una `date` pura non ha un'ora e non si sposta.
        self.assertEqual(format_date(date(2026, 9, 14)), "14-09-2026")

    # 27. ⭐ Il percorso degli EXPORT: `format_for_export` con il `tipo_dato`
    #     dichiarato a catalogo e, senza, per isinstance. E' la riga che
    #     finisce nel CSV/XLSX.
    def test_l_export_scrive_l_ora_locale(self) -> None:
        istante = datetime(2026, 9, 14, 9, 47, 32, tzinfo=UTC)
        self.assertEqual(
            format_for_export(istante, tipo_dato="datetime"), "14-09-2026 11:47",
        )
        self.assertEqual(format_for_export(istante), "14-09-2026 11:47")
        self.assertNotIn("09:47", format_for_export(istante))

    # 28. ⭐ Il fuso del PROCESSO non conta: con `TIME_ZONE` (e il fuso attivo)
    #     a Tokyo l'ora resta quella dell'azienda. Fino al 2026-10-09 la
    #     conversione seguiva `TIME_ZONE`, una seconda copia del parametro.
    @override_settings(TIME_ZONE="Asia/Tokyo")
    def test_il_fuso_del_processo_non_conta(self) -> None:
        istante = datetime(2026, 9, 14, 9, 47, 32, tzinfo=UTC)
        with timezone.override("Asia/Tokyo"):
            self.assertEqual(format_datetime(istante), "14-09-2026 11:47")
            self.assertEqual(format_date(datetime(2026, 9, 14, 23, 30, tzinfo=UTC)), "15-09-2026")


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
        # Il valore e' GIA' in percentuale (come `sconto_percentuale`), e il
        # testo e' quello a video (`CellaConfigurabile`): 12,34 -> «12,34 %».
        # ⛔ Fino al 2026-09-28 era una frazione, e 10 usciva «1000,00%».
        self.assertEqual(
            format_number(Decimal("12.34"), formato="percent_2"),
            "12,34 %",
        )
        self.assertEqual(format_number(Decimal("10"), formato="percent_2"), "10,00 %")

    def test_format_number_currency_eur_6(self) -> None:
        # Il prezzo UNITARIO a 6 decimali dei listini (non l'importo).
        self.assertEqual(
            format_number(Decimal("1234.5"), formato="currency_eur_6"),
            "1.234,500000 €",
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
                datetime(2026, 5, 10, 17, 30),  # noqa: DTZ001 — naive apposta: un istante senza fuso non si converte
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
