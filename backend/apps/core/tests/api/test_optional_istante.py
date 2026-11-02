# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari di `payload_validators.optional_istante`: un istante in
#        ingresso porta il suo offset, o si rifiuta. Brief un-solo-fuso-aziendale B-7.
# ------------------------------------------------------------
"""Indice test.

1. test_assente_o_vuoto_e_none
2. test_con_offset_e_un_istante
3. test_senza_offset_si_rifiuta
4. test_illeggibile_o_non_testo_si_rifiuta
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from unittest import TestCase

from apps.core.api.payload_validators import optional_istante


class OptionalIstanteTests(TestCase):
    """Il validatore di un istante in ingresso."""

    # 1. Campo assente, null o vuoto: nessun istante (decide il chiamante).
    def test_assente_o_vuoto_e_none(self) -> None:
        for payload in ({}, {"t": None}, {"t": ""}):
            with self.subTest(payload=payload):
                self.assertIsNone(optional_istante(payload, "t"))

    # 2. `Z` e offset espliciti danno lo stesso istante.
    def test_con_offset_e_un_istante(self) -> None:
        atteso = datetime(2026, 6, 20, 9, 30, tzinfo=UTC)
        for raw in ("2026-06-20T09:30:00Z", "2026-06-20T09:30:00+00:00", "2026-06-20T11:30:00+02:00"):
            with self.subTest(raw=raw):
                self.assertEqual(optional_istante({"t": raw}, "t"), atteso)
        roma = optional_istante({"t": "2026-06-20T11:30:00+02:00"}, "t")
        assert roma is not None
        self.assertEqual(roma.utcoffset(), timezone(timedelta(hours=2)).utcoffset(None))

    # 3. ⛔ Senza offset (o solo la data) l'ora sarebbe del fuso della sessione.
    def test_senza_offset_si_rifiuta(self) -> None:
        for raw in ("2026-06-20T09:30:00", "2026-06-20"):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "t_senza_offset"):
                optional_istante({"t": raw}, "t")

    # 4. Cio' che non e' un istante ISO e' un errore di input, non un 500.
    def test_illeggibile_o_non_testo_si_rifiuta(self) -> None:
        for valore in ("ieri", "2026-13-01T00:00:00Z", 42):
            with self.subTest(valore=valore), self.assertRaisesRegex(ValueError, "t_invalid"):
                optional_istante({"t": valore}, "t")
