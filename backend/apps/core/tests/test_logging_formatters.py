# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari di `FormatterUtcIso`: l'ora delle righe di log e' UTC,
#        ISO 8601 con `Z`, e non dipende dal fuso del processo. Brief
#        un-solo-fuso-aziendale B-8 (T-3).
# ------------------------------------------------------------
"""Indice test.

1. test_l_ora_e_utc_iso_con_z
2. test_il_fuso_del_processo_non_conta
3. test_il_formato_verbose_usa_il_formatter
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from apps.core.logging_formatters import FormatterUtcIso

_ISTANTE = datetime(2026, 9, 14, 23, 30, 5, 120000, tzinfo=UTC).timestamp()


# Scopo: un record di log creato all'istante `_ISTANTE`.
def _record() -> logging.LogRecord:
    record = logging.LogRecord("apps.x", logging.INFO, __file__, 1, "ciao", None, None)
    record.created = _ISTANTE
    return record


class FormatterUtcIsoTests(SimpleTestCase):
    """L'ora delle righe di log."""

    # 1. Millisecondi e `Z`: nessun offset da indovinare.
    def test_l_ora_e_utc_iso_con_z(self) -> None:
        riga = FormatterUtcIso("%(asctime)s %(message)s").format(_record())
        self.assertEqual(riga, "2026-09-14T23:30:05.120Z ciao")

    # 2. Il fuso del processo (`TIME_ZONE`, cioe' `TZ`) non cambia la riga.
    @override_settings(TIME_ZONE="Pacific/Kiritimati")
    def test_il_fuso_del_processo_non_conta(self) -> None:
        riga = FormatterUtcIso("%(asctime)s").format(_record())
        self.assertEqual(riga, "2026-09-14T23:30:05.120Z")

    # 3. Il formato `verbose` dei settings passa da qui (un formatter scritto
    #    e non agganciato non serve a niente).
    def test_il_formato_verbose_usa_il_formatter(self) -> None:
        self.assertEqual(
            settings.LOGGING["formatters"]["verbose"]["class"],
            "apps.core.logging_formatters.FormatterUtcIso",
        )
