# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test delle letture dei campi opzionali del CORPO nella view
#        (`optional_int`, `optional_iso_date`, `optional_uuid`): una regola
#        sola, quella di `PayloadValidator`, col codice `E_VALIDATION_INPUT` e
#        il campo nell'errore (2026-11-24, brief-be-fe-BB-audit §2). Fino a quel
#        giorno la view aveva regole sue, e lo stesso valore aveva due esiti
#        secondo chi lo leggeva.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_valori_validi — int (anche negativo), stringa d'intero (anche con spazi), assente, zero_as_none
2) test_cifre_non_ascii_sono_rifiutate — «²» e «٣»: `\\d` e `int()` li leggerebbero
3) test_altre_forme_sono_rifiutate — `+3`, decimali, vuoto, bool, oltre bigint
4) test_rifiuto_col_campo — codice E_VALIDATION_INPUT e `context.field`
5) test_tabella_stessa_risposta_del_validator — per ogni input, la funzione della
   view risponde come il metodo di `PayloadValidator` (int, data, uuid)
6) test_service_non_importano_le_funzioni_della_view — presidio sorgente
"""

from pathlib import Path
from unittest import TestCase

from apps.core.api.payload_validators import optional_int, optional_iso_date, optional_uuid
from apps.core.services.payload_helpers import BIGINT_MAX, PayloadValidator
from apps.core.services.service_errors import E_VALIDATION_INPUT, ServiceError

_UUID = "3f2a6c1e-8b4d-4e2a-9c1f-0a1b2c3d4e5f"


def _esito(fn, *args, **kwargs):
    """Il valore restituito, o `("rifiuto", codice, campo)`."""
    try:
        return fn(*args, **kwargs)
    except ServiceError as exc:
        return ("rifiuto", exc.code, (exc.context or {}).get("field"))


class TestOptionalInt(TestCase):

    def test_valori_validi(self):
        self.assertEqual(optional_int({"x": 7}, "x"), 7)
        self.assertEqual(optional_int({"x": -3}, "x"), -3)
        self.assertEqual(optional_int({"x": "42"}, "x"), 42)
        self.assertEqual(optional_int({"x": " 42 "}, "x"), 42)
        self.assertEqual(optional_int({"x": "-3"}, "x"), -3)
        self.assertEqual(optional_int({"x": 0}, "x"), 0)
        self.assertIsNone(optional_int({}, "x"))
        self.assertIsNone(optional_int({"x": None}, "x"))
        self.assertIsNone(optional_int({"x": "0"}, "x", zero_as_none=True))
        self.assertIsNone(optional_int({"x": 0}, "x", zero_as_none=True))

    def test_cifre_non_ascii_sono_rifiutate(self):
        """⛔ «²» farebbe fallire `int()`; «٣» passerebbe come 3 un valore che
        nessun client scrive (`\\d` in Python e' ogni cifra Unicode)."""
        for grezzo in ("²", "7²", "٣"):
            with self.subTest(grezzo=grezzo), self.assertRaises(ServiceError):
                optional_int({"x": grezzo}, "x")

    def test_altre_forme_sono_rifiutate(self):
        for grezzo in ("+3", "3.0", 3.0, "", "abc", True, False, BIGINT_MAX + 1):
            with self.subTest(grezzo=grezzo), self.assertRaises(ServiceError):
                optional_int({"x": grezzo}, "x")
        # zero_as_none non trasforma un bool in «nessuno»: False == 0 in Python.
        with self.assertRaises(ServiceError):
            optional_int({"x": False}, "x", zero_as_none=True)

    def test_zero_as_none_giudica_il_valore_letto(self):
        """⚠️ Lo zero si riconosce sul valore letto, non sul grezzo: `" 0"` e
        `"-0"` sono lo stesso zero di `"0"`, e `0.0` e' un float rifiutato come
        `1.0`, non un «nessuno» (2026-11-24)."""
        for grezzo in (0, "0", " 0 ", "-0", "00"):
            with self.subTest(grezzo=grezzo):
                self.assertIsNone(optional_int({"x": grezzo}, "x", zero_as_none=True))
        with self.assertRaises(ServiceError):
            optional_int({"x": 0.0}, "x", zero_as_none=True)
        # L'intervallo vale per i valori diversi da zero, e lo zero non lo viola.
        v = PayloadValidator(validation_code=E_VALIDATION_INPUT)
        self.assertIsNone(v.optional_int({"x": "0"}, "x", zero_as_none=True, min_val=1))
        with self.assertRaises(ServiceError):
            v.optional_int({"x": "-1"}, "x", zero_as_none=True, min_val=1)

    def test_rifiuto_col_campo(self):
        for fn, valore in ((optional_int, "abc"), (optional_iso_date, "ieri"), (optional_uuid, "abc")):
            with self.subTest(fn=fn.__name__), self.assertRaises(ServiceError) as ctx:
                fn({"campo": valore}, "campo")
            self.assertEqual(ctx.exception.code, E_VALIDATION_INPUT)
            self.assertEqual(ctx.exception.context.get("field"), "campo")

    def test_tabella_stessa_risposta_del_validator(self):
        v = PayloadValidator(validation_code=E_VALIDATION_INPUT)
        casi = {
            (optional_int, v.optional_int): (
                None, 0, 7, -3, "42", " 42 ", "-3", "", "abc", "٣", True, 3.0, BIGINT_MAX + 1,
            ),
            (optional_iso_date, v.optional_date): (
                None, "2026-01-31", " 2026-01-31 ", "", "31/01/2026", "2026-02-30", 0, True,
            ),
            (optional_uuid, v.optional_uuid): (
                None, _UUID, _UUID.upper(), f" {_UUID} ", "", "0", 0, "abc", True,
            ),
        }
        for (vista, metodo), valori in casi.items():
            for valore in valori:
                payload = {"k": valore}
                with self.subTest(fn=vista.__name__, valore=valore):
                    self.assertEqual(_esito(vista, payload, "k"), _esito(metodo, payload, "k"))
        # La chiave assente e' None per tutte.
        for vista in (optional_int, optional_iso_date, optional_uuid):
            self.assertIsNone(vista({}, "k"))

    def test_service_non_importano_le_funzioni_della_view(self):
        """⛔ Un service legge col PROPRIO `PayloadValidator` (codice del dominio):
        le funzioni della view rispondono `E_VALIDATION_INPUT`, e nei service di
        anagrafiche ogni rifiuto usciva senza il codice del dominio."""
        apps_dir = Path(__file__).resolve().parents[3]
        vietate = ("optional_int", "optional_iso_date", "optional_uuid")
        trovati = []
        for sorgente in apps_dir.glob("*/services/**/*.py"):
            if "/tests/" in sorgente.as_posix():
                continue
            testo = sorgente.read_text(encoding="utf-8")
            for riga in testo.splitlines():
                if "from apps.core.api.payload_validators import" in riga and any(
                    nome in riga.split("import", 1)[1] for nome in vietate
                ):
                    trovati.append(sorgente.relative_to(apps_dir).as_posix())
        self.assertEqual(trovati, [], "service che leggono il corpo con le funzioni della view")
