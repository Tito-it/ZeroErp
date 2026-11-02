# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per PayloadValidator e map_integrity_error
#        (apps.core.services.payload_helpers). Nessun accesso DB: test puri
#        di validazione input, coercizione tipi e mapping IntegrityError.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_validate_allowed_keys_ok               — whitelist rispettata
 2) test_validate_allowed_keys_unknown          — chiave extra -> VALIDATION
 3) test_guard_positive_int_ok                  — int > 0 passa
 4) test_guard_positive_int_zero                — 0 rifiutato
 5) test_guard_positive_int_negative            — < 0 rifiutato
 6) test_guard_positive_int_bool                — True/False rifiutati (int trap)
 7) test_guard_positive_int_str                 — stringa rifiutata
 8) test_require_string_ok                      — stringa valida, trim applicato
 9) test_require_string_missing                 — chiave assente -> VALIDATION
10) test_require_string_empty                   — stringa vuota/whitespace
11) test_require_string_too_long                — oltre max_len -> VALIDATION
12) test_require_string_non_str                 — tipo errato rifiutato
13) test_require_positive_int_ok_int            — int positivo
14) test_require_positive_int_ok_str_numeric    — stringa numerica
15) test_require_positive_int_missing           — None o assente -> VALIDATION
16) test_require_positive_int_bool              — bool rifiutato
17) test_require_positive_int_zero              — 0 rifiutato
18) test_require_positive_int_negative_str      — "-5" rifiutato
19) test_require_positive_int_float             — float rifiutato
20) test_optional_positive_int_absent           — chiave assente -> None
21) test_optional_positive_int_none             — None esplicito -> None
22) test_optional_positive_int_ok               — valore valido
23) test_optional_smallint_default_range        — [0, 32767]
24) test_optional_smallint_fuori_range          — 40000 -> VALIDATION
25) test_optional_smallint_negativo_default     — negativo rifiutato default
26) test_optional_smallint_range_custom         — min/max custom
27) test_optional_smallint_bool                 — bool rifiutato
28) test_optional_smallint_none                 — None -> None
29) test_optional_bool_true                     — True passa
30) test_optional_bool_false                    — False passa
31) test_optional_bool_absent                   — assente -> None
32) test_optional_bool_none                     — None -> None
33) test_optional_bool_str                      — "true" rifiutato
34) test_optional_bool_int                      — 1 rifiutato
34b) test_require_bool_*                        — vero/falso passano; assente, None, "true" rifiutati col campo
35) test_optional_meta_absent                   — assente -> None
36) test_optional_meta_none                     — None esplicito -> {}
37) test_optional_meta_dict                     — dict passa
38) test_optional_meta_json_string              — JSON string parsato
39) test_optional_meta_json_invalid             — JSON malformato -> VALIDATION
40) test_optional_meta_non_object               — JSON array -> VALIDATION
41) test_map_integrity_error_unique_match       — UNIQUE constraint -> codice
42) test_map_integrity_error_fk_match           — FK constraint -> codice
43) test_map_integrity_error_fallback           — nessun match -> fallback
44) test_map_integrity_error_case_insensitive   — case insensitive match
45) test_instance_log_to_db_propagato           — V6-B2: log_to_db instance -> log_error_only
46) test_per_call_override_function_name        — V6-B2: override per-chiamata
47) test_per_call_override_log_to_db_disabilita — V6-B2: override disable logging
48) test_message_override_custom                — V6-B2: message kwarg
49) test_require_string_max_len_none_skipped    — V6-B2: max_len=None skip check
50) test_optional_smallint_doppio_segno_rifiut  — review: "--5" non deve passare come int
51) test_optional_smallint_stringa_numerica_neg — regression: "-5" con range custom ok
52) test_map_integrity_exact_match_non_prefix   — review: "fk_foo" non matcha "fk_foo_bar"
53) test_map_integrity_fk_preferita_su_specific — review: piu' constraint precisi -> il piu' specifico vince via word boundary
54) test_validate_order_by_ok                   — nuovo helper V6-B2 review
55) test_validate_order_by_invalid              — nuovo helper V6-B2 review
55b) test_validate_order_by_rifiuta_una_direzione_estranea — 2026-09-26: la direzione e' validata insieme alla colonna
56) test_reject_keys_empty_ok                   — nuovo helper V6-B2 review
57) test_reject_keys_presente                   — nuovo helper V6-B2 review
58) test_require_decimal_ok_int_float_str        — 2026-09-18: int, float e stringa passano da `str` (Decimal esatto)
59) test_require_decimal_missing                 — assente o None -> VALIDATION col campo
60) test_require_decimal_bool                    — True non e' un numero (sommerebbe come 1)
61) test_require_decimal_non_numerico            — "dieci" -> VALIDATION, valore nel detail
62) test_require_decimal_nan_infinity            — NaN/Infinity (stringa e float) rifiutati: non arrivano alla colonna numeric
63) test_require_decimal_min_value_inclusivo     — min_value e' `>=`: il limite passa, sotto no
64) test_optional_decimal_absent_none            — assente o None -> None
65) test_optional_decimal_present                — presente -> Decimal, stesso rigore
66) test_extract_optional_decimal_tre_stati      — assente -> MISSING; None nullable -> None; None non nullable -> VALIDATION
67) test_coerce_decimal_scalare                  — la forma per un parametro di firma; None e' obbligatorio
68) test_require_enum_normalizza                 — 2026-09-18 (regola del 2 su cinque siti): " percentuale " -> PERCENTUALE
69) test_require_enum_missing_o_vuoto            — assente, None o "" -> VALIDATION col campo («obbligatorio», non «uno tra»)
70) test_require_enum_non_stringa                — True / 3 -> VALIDATION col campo, non un AttributeError su .strip()
71) test_require_enum_fuori_vocabolario          — il detail elenca gli ammessi (+ la `nota` del dominio), il valore sta nel context e NON nel detail
72) test_optional_enum                           — assente o None -> None; presente -> stesso rigore
73) test_extract_optional_enum_tre_stati         — assente -> MISSING; None nullable -> None; None non nullable -> VALIDATION
74) test_coerce_enum_scalare                     — la forma per un parametro di firma; None e' obbligatorio
75) test_extract_optional_string_max_len         — 2026-09-21 (regola del 2): oltre `max_len` -> VALIDATION col campo; MISSING e None (nullable) non lo misurano
76) test_optional_smallint_porta_il_campo         — 2026-09-21 (presidio C2 §3-bis.4): i tre rifiuti nominano `field`, come le sorelle
77) test_optional_bool_porta_il_campo             — idem
78) test_optional_meta_porta_il_campo             — idem, sui due rifiuti (JSON rotto, non oggetto)
79) test_optional_upper                         — 2026-10-09 (regola del 2): strip + upper, vuoto -> None; non-stringa -> VALIDATION col campo
80) test_require_campi_da_aggiornare_*          — 2026-10-14 (regola del 2, ~45 copie): vuoto -> VALIDATION col codice del dominio; un None e' un reset e conta; un sotto-oggetto conta solo se ha chiavi
81) test_solo_chiavi_ammesse_*                 — 2026-10-20 (regola del 2, 11 copie): chiave ignota -> VALIDATION; ritorna il dict con vuoti a None; `colonne` tiene le sole colonne
"""

from decimal import Decimal
from unittest import TestCase

from django.db import IntegrityError

from apps.core.services.payload_helpers import (
    MISSING,
    PayloadValidator,
    map_integrity_error,
)
from apps.core.services.service_errors import ServiceError


_CODE = "E_TEST_VALIDATION"


class _Base(TestCase):
    """Bootstrap comune: un validator col codice di test."""

    def setUp(self) -> None:
        self.v = PayloadValidator(validation_code=_CODE)

    def assertRaisesValidation(self):
        return self.assertRaises(ServiceError)


class TestValidateAllowedKeys(_Base):
    def test_validate_allowed_keys_ok(self):
        self.v.validate_allowed_keys(
            {"a": 1, "b": 2}, allowed=frozenset({"a", "b", "c"})
        )

    def test_validate_allowed_keys_unknown(self):
        with self.assertRaisesValidation() as ctx:
            self.v.validate_allowed_keys({"a": 1, "x": 2}, allowed=frozenset({"a"}))
        self.assertEqual(ctx.exception.code, _CODE)
        self.assertIn("x", ctx.exception.context["unknown_keys"])


class TestSoloChiaviAmmesse(_Base):
    def test_solo_chiavi_ammesse_rifiuta_la_chiave_ignota(self):
        with self.assertRaisesValidation() as ctx:
            self.v.solo_chiavi_ammesse({"a": 1, "x": 2}, ammesse=frozenset({"a"}))
        self.assertEqual(ctx.exception.code, _CODE)
        self.assertEqual(ctx.exception.context["unknown_keys"], ["x"])

    def test_solo_chiavi_ammesse_ritorna_il_dict_normalizzato(self):
        self.assertEqual(
            self.v.solo_chiavi_ammesse({"a": "", "b": 2}, ammesse=frozenset({"a", "b", "c"})),
            {"a": None, "b": 2},
        )

    def test_solo_chiavi_ammesse_colonne_tiene_le_sole_colonne(self):
        dati = self.v.solo_chiavi_ammesse(
            {"a": 1, "mappa": {"7": "1.00"}},
            ammesse=frozenset({"a", "mappa"}), colonne=frozenset({"a"}),
        )
        self.assertEqual(dati, {"a": 1})


class TestGuardPositiveInt(_Base):
    def test_guard_positive_int_ok(self):
        self.v.guard_positive_int(5, field="id")

    def test_guard_positive_int_zero(self):
        with self.assertRaisesValidation():
            self.v.guard_positive_int(0, field="id")

    def test_guard_positive_int_negative(self):
        with self.assertRaisesValidation():
            self.v.guard_positive_int(-1, field="id")

    def test_guard_positive_int_bool(self):
        with self.assertRaisesValidation():
            self.v.guard_positive_int(True, field="id")
        with self.assertRaisesValidation():
            self.v.guard_positive_int(False, field="id")

    def test_guard_positive_int_str(self):
        with self.assertRaisesValidation():
            self.v.guard_positive_int("5", field="id")


class TestRequireString(_Base):
    def test_require_string_ok(self):
        value = self.v.require_string({"codice": "  ABC  "}, "codice", max_len=10)
        self.assertEqual(value, "ABC")

    def test_require_string_missing(self):
        with self.assertRaisesValidation():
            self.v.require_string({}, "codice", max_len=10)

    def test_require_string_empty(self):
        with self.assertRaisesValidation():
            self.v.require_string({"codice": ""}, "codice", max_len=10)
        with self.assertRaisesValidation():
            self.v.require_string({"codice": "   "}, "codice", max_len=10)

    def test_require_string_too_long(self):
        with self.assertRaisesValidation():
            self.v.require_string({"codice": "A" * 11}, "codice", max_len=10)

    def test_require_string_non_str(self):
        with self.assertRaisesValidation():
            self.v.require_string({"codice": 123}, "codice", max_len=10)


class TestExtractOptionalString(_Base):
    # 75. Il tetto e' quello di `require_string`, sullo stesso campo: prima il
    #     PATCH per delta lo riscriveva a mano dopo la chiamata.
    def test_extract_optional_string_max_len(self):
        self.assertIs(self.v.extract_optional_string({}, "descrizione", nullable=True, max_len=5), MISSING)
        self.assertIsNone(self.v.extract_optional_string({"descrizione": None}, "descrizione", nullable=True, max_len=5))
        self.assertEqual(self.v.extract_optional_string({"descrizione": " abc "}, "descrizione", max_len=5), "abc")
        with self.assertRaisesValidation() as ctx:
            self.v.extract_optional_string({"descrizione": "abcdef"}, "descrizione", nullable=True, max_len=5)
        self.assertEqual(ctx.exception.context.get("field"), "descrizione")


class TestOptionalUpper(_Base):
    # 79. La forma di un codice a vocabolario maiuscolo (il sesso): prima era
    #     scritta a mano in quattro punti, e `.strip()` su un non-stringa era
    #     un 500. Il valore ammesso non lo giudica l'helper.
    def test_optional_upper(self):
        for raw, atteso in ((" x ", "X"), ("f", "F"), ("  ", None), (None, None), ("", None)):
            with self.subTest(raw=raw):
                self.assertEqual(self.v.optional_upper({"sesso": raw}, "sesso"), atteso)
        self.assertIsNone(self.v.optional_upper({}, "sesso"))
        with self.assertRaisesValidation() as ctx:
            self.v.optional_upper({"sesso": 1}, "sesso")
        self.assertEqual(ctx.exception.context.get("field"), "sesso")


class TestRequirePositiveInt(_Base):
    def test_require_positive_int_ok_int(self):
        self.assertEqual(self.v.require_positive_int({"id": 42}, "id"), 42)

    def test_require_positive_int_ok_str_numeric(self):
        self.assertEqual(self.v.require_positive_int({"id": "42"}, "id"), 42)

    def test_require_positive_int_missing(self):
        with self.assertRaisesValidation():
            self.v.require_positive_int({}, "id")
        with self.assertRaisesValidation():
            self.v.require_positive_int({"id": None}, "id")

    def test_require_positive_int_bool(self):
        with self.assertRaisesValidation():
            self.v.require_positive_int({"id": True}, "id")

    def test_require_positive_int_zero(self):
        with self.assertRaisesValidation():
            self.v.require_positive_int({"id": 0}, "id")

    def test_require_positive_int_negative_str(self):
        # "-5" non passa isdigit(), quindi va nel ramo raise.
        with self.assertRaisesValidation():
            self.v.require_positive_int({"id": "-5"}, "id")

    def test_require_positive_int_float(self):
        with self.assertRaisesValidation():
            self.v.require_positive_int({"id": 1.5}, "id")


class TestOptionalPositiveInt(_Base):
    def test_optional_positive_int_absent(self):
        self.assertIsNone(self.v.optional_positive_int({}, "id"))

    def test_optional_positive_int_none(self):
        self.assertIsNone(self.v.optional_positive_int({"id": None}, "id"))

    def test_optional_positive_int_ok(self):
        self.assertEqual(self.v.optional_positive_int({"id": 7}, "id"), 7)


class TestOptionalSmallint(_Base):
    def test_optional_smallint_default_range(self):
        self.assertEqual(self.v.optional_smallint({"o": 0}, "o"), 0)
        self.assertEqual(self.v.optional_smallint({"o": 32767}, "o"), 32767)

    def test_optional_smallint_fuori_range(self):
        with self.assertRaisesValidation():
            self.v.optional_smallint({"o": 40000}, "o")

    def test_optional_smallint_negativo_default(self):
        # Default min=0: negativo rifiutato.
        with self.assertRaisesValidation():
            self.v.optional_smallint({"o": -1}, "o")

    def test_optional_smallint_range_custom(self):
        self.assertEqual(
            self.v.optional_smallint({"o": -5}, "o", min_val=-10, max_val=10),
            -5,
        )
        with self.assertRaisesValidation():
            self.v.optional_smallint({"o": 11}, "o", min_val=-10, max_val=10)

    def test_optional_smallint_bool(self):
        with self.assertRaisesValidation():
            self.v.optional_smallint({"o": True}, "o")

    def test_optional_smallint_none(self):
        self.assertIsNone(self.v.optional_smallint({}, "o"))
        self.assertIsNone(self.v.optional_smallint({"o": None}, "o"))

    # Scopo: il canale del campo (presidio C2, brief-be-presidio-ui-action-e-
    #        canale-campi §3-bis.4). Fino al 2026-09-21 i tre rifiuti scrivevano
    #        `context={key: value}` — il nome del campo come CHIAVE, che
    #        `_campi_da_correggere` non legge — e l'envelope usciva senza
    #        `fields` su un errore che sa esattamente quale input ha sbagliato.
    #        E' un metodo che estrae dal PAYLOAD, come `require_string`: il
    #        campo e' un input del form, e va nominato.
    def test_optional_smallint_porta_il_campo(self):
        for payload in ({"o": True}, {"o": "x"}, {"o": 40000}):
            with self.assertRaises(ServiceError) as ctx:
                self.v.optional_smallint(payload, "o")
            self.assertEqual(ctx.exception.context.get("field"), "o", payload)


class TestOptionalBool(_Base):
    def test_optional_bool_true(self):
        self.assertIs(self.v.optional_bool({"attivo": True}, "attivo"), True)

    def test_optional_bool_false(self):
        self.assertIs(self.v.optional_bool({"attivo": False}, "attivo"), False)

    def test_optional_bool_absent(self):
        self.assertIsNone(self.v.optional_bool({}, "attivo"))

    def test_optional_bool_none(self):
        self.assertIsNone(self.v.optional_bool({"attivo": None}, "attivo"))

    def test_optional_bool_str(self):
        with self.assertRaisesValidation():
            self.v.optional_bool({"attivo": "true"}, "attivo")

    # Scopo: come `test_optional_smallint_porta_il_campo`, sul booleano.
    def test_optional_bool_porta_il_campo(self):
        with self.assertRaises(ServiceError) as ctx:
            self.v.optional_bool({"attivo": "true"}, "attivo")
        self.assertEqual(ctx.exception.context.get("field"), "attivo")

    def test_optional_bool_int(self):
        with self.assertRaisesValidation():
            self.v.optional_bool({"attivo": 1}, "attivo")

    def test_require_bool_true_false(self):
        self.assertIs(self.v.require_bool({"attivo": True}, "attivo"), True)
        self.assertIs(self.v.require_bool({"attivo": False}, "attivo"), False)

    # Scopo: assente e None non sono «invariato»: il comando vuole il valore.
    def test_require_bool_assente_o_none_rifiutato(self):
        for corpo in ({}, {"attivo": None}):
            with self.assertRaises(ServiceError) as ctx:
                self.v.require_bool(corpo, "attivo")
            self.assertEqual(ctx.exception.context.get("field"), "attivo", corpo)

    def test_require_bool_str_rifiutato(self):
        with self.assertRaisesValidation():
            self.v.require_bool({"attivo": "true"}, "attivo")


class TestDecimal(_Base):
    """I tre metodi decimal (2026-09-18, regola del 2 su otto siti): il rigore
    e' quello piu' alto fra le copie che hanno sostituito, per tutti."""

    def test_require_decimal_ok_int_float_str(self):
        self.assertEqual(self.v.require_decimal({"q": 10}, "q"), Decimal("10"))
        # Da `str`, non dal float: 0.1 resta 0.1, non 0.1000000000000000055…
        self.assertEqual(self.v.require_decimal({"q": 0.1}, "q"), Decimal("0.1"))
        self.assertEqual(self.v.require_decimal({"q": " 12.50 "}, "q"), Decimal("12.50"))
        self.assertEqual(self.v.require_decimal({"q": "-5"}, "q"), Decimal("-5"))

    def test_require_decimal_missing(self):
        for payload in ({}, {"q": None}):
            with self.assertRaisesValidation() as ctx:
                self.v.require_decimal(payload, "q")
            self.assertEqual(ctx.exception.code, _CODE)
            self.assertEqual(ctx.exception.context["field"], "q")

    def test_require_decimal_bool(self):
        with self.assertRaisesValidation() as ctx:
            self.v.require_decimal({"q": True}, "q")
        self.assertEqual(ctx.exception.context["field"], "q")

    def test_require_decimal_non_numerico(self):
        with self.assertRaisesValidation() as ctx:
            self.v.require_decimal({"q": "dieci"}, "q")
        self.assertEqual(ctx.exception.context["field"], "q")
        self.assertIn("'dieci'", ctx.exception.detail or "")

    def test_require_decimal_nan_infinity(self):
        for raw in ("NaN", "Infinity", "-Infinity", float("nan"), float("inf")):
            with self.assertRaisesValidation() as ctx:
                self.v.require_decimal({"q": raw}, "q")
            self.assertEqual(ctx.exception.context["field"], "q")

    def test_require_decimal_min_value_inclusivo(self):
        self.assertEqual(
            self.v.require_decimal({"q": "0"}, "q", min_value=Decimal("0")), Decimal("0"),
        )
        with self.assertRaisesValidation() as ctx:
            self.v.require_decimal({"q": "-0.01"}, "q", min_value=Decimal("0"))
        self.assertEqual(ctx.exception.context["min_value"], "0")

    def test_optional_decimal_absent_none(self):
        self.assertIsNone(self.v.optional_decimal({}, "q"))
        self.assertIsNone(self.v.optional_decimal({"q": None}, "q"))

    def test_optional_decimal_present(self):
        self.assertEqual(self.v.optional_decimal({"q": "7"}, "q"), Decimal("7"))
        with self.assertRaisesValidation():
            self.v.optional_decimal({"q": "NaN"}, "q")

    def test_extract_optional_decimal_tre_stati(self):
        self.assertIs(self.v.extract_optional_decimal({}, "q"), MISSING)
        self.assertIsNone(self.v.extract_optional_decimal({"q": None}, "q", nullable=True))
        with self.assertRaisesValidation() as ctx:
            self.v.extract_optional_decimal({"q": None}, "q", nullable=False)
        self.assertEqual(ctx.exception.context["field"], "q")
        self.assertEqual(
            self.v.extract_optional_decimal({"q": "1.5"}, "q", min_value=Decimal("1")),
            Decimal("1.5"),
        )

    def test_coerce_decimal_scalare(self):
        self.assertEqual(self.v.coerce_decimal("3.25", field="importo"), Decimal("3.25"))
        with self.assertRaisesValidation() as ctx:
            self.v.coerce_decimal(None, field="importo")
        self.assertEqual(ctx.exception.context["field"], "importo")
        with self.assertRaisesValidation():
            self.v.coerce_decimal(False, field="importo")


_TIPI = frozenset({"PERCENTUALE", "VALORE_FISSO"})


class TestEnum(_Base):
    """I quattro metodi enum (2026-09-18, regola del 2 su cinque siti): la
    lettura e' una, il vocabolario resta del dominio."""

    def test_require_enum_normalizza(self):
        self.assertEqual(
            self.v.require_enum({"t": " percentuale "}, "t", allowed=_TIPI), "PERCENTUALE",
        )

    def test_require_enum_missing_o_vuoto(self):
        for payload in ({}, {"t": None}, {"t": ""}, {"t": "   "}):
            with self.assertRaisesValidation() as ctx:
                self.v.require_enum(payload, "t", allowed=_TIPI, message="M")
            self.assertEqual(ctx.exception.code, _CODE)
            self.assertEqual(ctx.exception.context["field"], "t")
            self.assertIn("obbligatorio", ctx.exception.detail or "")

    def test_require_enum_non_stringa(self):
        for raw in (True, 3, ["PERCENTUALE"]):
            with self.assertRaisesValidation() as ctx:
                self.v.require_enum({"t": raw}, "t", allowed=_TIPI)
            self.assertEqual(ctx.exception.context["field"], "t")

    def test_require_enum_fuori_vocabolario(self):
        with self.assertRaisesValidation() as ctx:
            self.v.require_enum(
                {"t": "prezzo_fisso"}, "t", allowed=_TIPI, message="M", nota="Per i prezzi fissi usa una riga.",
            )
        self.assertEqual(ctx.exception.context["field"], "t")
        self.assertEqual(ctx.exception.context["t"], "PREZZO_FISSO")
        detail = ctx.exception.detail or ""
        self.assertIn("PERCENTUALE, VALORE_FISSO", detail)
        self.assertIn("usa una riga", detail)
        # il valore scritto dall'operatore non torna indietro nel detail
        self.assertNotIn("PREZZO_FISSO", detail)

    def test_optional_enum(self):
        self.assertIsNone(self.v.optional_enum({}, "t", allowed=_TIPI))
        self.assertIsNone(self.v.optional_enum({"t": None}, "t", allowed=_TIPI))
        self.assertEqual(
            self.v.optional_enum({"t": "valore_fisso"}, "t", allowed=_TIPI), "VALORE_FISSO",
        )
        with self.assertRaisesValidation():
            self.v.optional_enum({"t": ""}, "t", allowed=_TIPI)

    def test_extract_optional_enum_tre_stati(self):
        self.assertIs(self.v.extract_optional_enum({}, "t", allowed=_TIPI), MISSING)
        self.assertIsNone(
            self.v.extract_optional_enum({"t": None}, "t", allowed=_TIPI, nullable=True),
        )
        with self.assertRaisesValidation() as ctx:
            self.v.extract_optional_enum({"t": None}, "t", allowed=_TIPI)
        self.assertEqual(ctx.exception.context["field"], "t")
        self.assertEqual(
            self.v.extract_optional_enum({"t": "percentuale"}, "t", allowed=_TIPI), "PERCENTUALE",
        )

    def test_coerce_enum_scalare(self):
        self.assertEqual(self.v.coerce_enum("commodity", field="ambito", allowed=("COMMODITY",)), "COMMODITY")
        with self.assertRaisesValidation() as ctx:
            self.v.coerce_enum(None, field="ambito", allowed=("COMMODITY",))
        self.assertEqual(ctx.exception.context["field"], "ambito")


class TestOptionalMeta(_Base):
    def test_optional_meta_absent(self):
        self.assertIsNone(self.v.optional_meta({}))

    def test_optional_meta_none(self):
        self.assertEqual(self.v.optional_meta({"meta": None}), {})

    def test_optional_meta_dict(self):
        self.assertEqual(
            self.v.optional_meta({"meta": {"a": 1}}), {"a": 1}
        )

    def test_optional_meta_json_string(self):
        self.assertEqual(
            self.v.optional_meta({"meta": '{"a": 1}'}), {"a": 1}
        )

    def test_optional_meta_json_invalid(self):
        with self.assertRaisesValidation():
            self.v.optional_meta({"meta": "{not json"})

    def test_optional_meta_non_object(self):
        # array JSON -> valido come JSON ma non e' dict
        with self.assertRaisesValidation():
            self.v.optional_meta({"meta": "[1,2,3]"})

    # Scopo: come `test_optional_smallint_porta_il_campo`, sui due rifiuti del
    #        blob: il campo e' la chiave del payload (`meta`), non `meta_raw`.
    def test_optional_meta_porta_il_campo(self):
        for raw in ("{not json", "[1,2,3]"):
            with self.assertRaises(ServiceError) as ctx:
                self.v.optional_meta({"meta": raw})
            self.assertEqual(ctx.exception.context.get("field"), "meta", raw)


class TestInstanceDefaults(TestCase):
    """Test propagazione log_to_db e function_name (V6-B2 extension).

    Verifica che i parametri di istanza e i per-call override siano
    propagati correttamente a ErrorManager.raise_error/require.
    """

    def test_instance_log_to_db_propagato(self):
        v = PayloadValidator(
            validation_code=_CODE,
            log_to_db=True,
            function_name="vendite.listini.create",
        )
        # Patch ErrorManager.log_error_only (chiamato internamente quando log_to_db=True)
        # per evitare accesso DB nel test.
        from unittest.mock import patch

        with patch(
            "apps.core.services.error_manager.ErrorManager.log_error_only"
        ) as mock_log:
            with self.assertRaises(ServiceError):
                v.require_positive_int({}, "utility_id")
        mock_log.assert_called_once()
        called_kwargs = mock_log.call_args.kwargs
        self.assertEqual(called_kwargs.get("function_name"), "vendite.listini.create")

    def test_per_call_override_function_name(self):
        v = PayloadValidator(
            validation_code=_CODE,
            log_to_db=True,
            function_name="default_name",
        )
        from unittest.mock import patch

        with patch(
            "apps.core.services.error_manager.ErrorManager.log_error_only"
        ) as mock_log:
            with self.assertRaises(ServiceError):
                v.require_positive_int(
                    {}, "id", function_name="vendite.listini.update"
                )
        self.assertEqual(
            mock_log.call_args.kwargs.get("function_name"),
            "vendite.listini.update",
        )

    def test_per_call_override_log_to_db_disabilita(self):
        # Instance con log_to_db=True, override False su chiamata specifica.
        v = PayloadValidator(validation_code=_CODE, log_to_db=True)
        from unittest.mock import patch

        with patch(
            "apps.core.services.error_manager.ErrorManager.log_error_only"
        ) as mock_log:
            with self.assertRaises(ServiceError):
                v.require_positive_int({}, "id", log_to_db=False)
        mock_log.assert_not_called()

    def test_message_override_custom(self):
        v = PayloadValidator(validation_code=_CODE)
        with self.assertRaises(ServiceError) as ctx:
            v.require_positive_int(
                {}, "utility_id", message="Parametri listino non validi."
            )
        self.assertEqual(ctx.exception.message, "Parametri listino non validi.")

    def test_require_string_max_len_none_skipped(self):
        # max_len=None (default) disabilita il controllo di lunghezza.
        v = PayloadValidator(validation_code=_CODE)
        value = v.require_string({"codice": "A" * 500}, "codice")
        self.assertEqual(len(value), 500)


class TestRegressionReview(_Base):
    """Regression test dai findings della review critica."""

    def test_optional_smallint_doppio_segno_rifiut(self):
        # Prima: lstrip("-") rimuoveva TUTTI i '-' leading, accettando "--5".
        with self.assertRaisesValidation():
            self.v.optional_smallint({"o": "--5"}, "o", min_val=-10, max_val=10)
        with self.assertRaisesValidation():
            self.v.optional_smallint({"o": "---0"}, "o", min_val=-10, max_val=10)
        with self.assertRaisesValidation():
            self.v.optional_smallint({"o": "+5"}, "o", min_val=-10, max_val=10)

    def test_optional_smallint_stringa_numerica_neg(self):
        # "-5" con range custom che ammette negativi deve passare.
        self.assertEqual(
            self.v.optional_smallint({"o": "-5"}, "o", min_val=-10, max_val=10),
            -5,
        )


class TestValidateOrderBy(_Base):
    _ALLOWED = frozenset({"codice", "descrizione", "data_insert"})

    def test_validate_order_by_ok(self):
        # La direzione ASSENTE e' ammessa (prende il default del repository),
        # e maiuscole/spazi valgono come nel BB SQL.
        for order_dir in (None, "", "asc", "desc", " DESC "):
            with self.subTest(order_dir=order_dir):
                self.v.validate_order_by("codice", allowed=self._ALLOWED, order_dir=order_dir)

    def test_validate_order_by_invalid(self):
        with self.assertRaisesValidation() as ctx:
            self.v.validate_order_by("random_col", allowed=self._ALLOWED, order_dir="asc")
        self.assertEqual(ctx.exception.code, _CODE)

    # ⛔ 2026-09-26: prima il metodo guardava la sola colonna, e `?order_dir=giu`
    #    arrivava al repository che lo trasformava in ASC. Ora e' il 400 di
    #    dominio, con il campo nel context.
    def test_validate_order_by_rifiuta_una_direzione_estranea(self):
        for order_dir in ("giu", "desc;", "ASC NULLS LAST"):
            with self.subTest(order_dir=order_dir):
                with self.assertRaisesValidation() as ctx:
                    self.v.validate_order_by("codice", allowed=self._ALLOWED, order_dir=order_dir)
                self.assertEqual(ctx.exception.code, _CODE)
                self.assertEqual(ctx.exception.context, {"order_dir": order_dir})


class TestRejectKeys(_Base):
    _FORBIDDEN = frozenset({"categoria_cliente_id", "utility_id"})

    def test_reject_keys_empty_ok(self):
        self.v.reject_keys({"attivo": True}, forbidden=self._FORBIDDEN, reason="X")

    def test_reject_keys_presente(self):
        with self.assertRaisesValidation() as ctx:
            self.v.reject_keys(
                {"utility_id": 5, "attivo": True},
                forbidden=self._FORBIDDEN,
                reason="Dimensioni immutabili.",
            )
        self.assertIn("utility_id", ctx.exception.context["forbidden_keys"])


class TestRequireUuid(_Base):
    """D1 review 2026-04-15: helper UUID estratto in PayloadValidator."""

    _VALID = "019bac81-3f96-7ce8-a086-7e0bd0a2fec1"

    def test_require_uuid_str_ok(self):
        from uuid import UUID

        result = self.v.require_uuid({"id": self._VALID}, "id")
        self.assertEqual(UUID(result), UUID(self._VALID))

    def test_require_uuid_obj_ok(self):
        from uuid import UUID

        result = self.v.require_uuid({"id": UUID(self._VALID)}, "id")
        self.assertEqual(UUID(result), UUID(self._VALID))

    def test_require_uuid_missing(self):
        with self.assertRaisesValidation():
            self.v.require_uuid({}, "id")
        with self.assertRaisesValidation():
            self.v.require_uuid({"id": None}, "id")

    def test_require_uuid_invalido(self):
        with self.assertRaisesValidation():
            self.v.require_uuid({"id": "not-uuid"}, "id")
        with self.assertRaisesValidation():
            self.v.require_uuid({"id": 123}, "id")

    def test_optional_uuid_absent(self):
        self.assertIsNone(self.v.optional_uuid({}, "id"))
        self.assertIsNone(self.v.optional_uuid({"id": None}, "id"))

    def test_optional_uuid_ok(self):
        result = self.v.optional_uuid({"id": self._VALID}, "id")
        self.assertIsNotNone(result)


class TestRequireDate(_Base):
    """D2 review 2026-04-15: helper date estratto in PayloadValidator."""

    def test_require_date_iso_string(self):
        from datetime import date

        result = self.v.require_date({"d": "2026-06-01"}, "d")
        self.assertEqual(result, date(2026, 6, 1))

    def test_require_date_date_obj(self):
        from datetime import date

        expected = date(2026, 6, 1)
        result = self.v.require_date({"d": expected}, "d")
        self.assertIs(result, expected)

    def test_require_date_missing(self):
        with self.assertRaisesValidation():
            self.v.require_date({}, "d")
        with self.assertRaisesValidation():
            self.v.require_date({"d": None}, "d")

    def test_require_date_invalid_format(self):
        with self.assertRaisesValidation():
            self.v.require_date({"d": "2026/06/01"}, "d")
        with self.assertRaisesValidation():
            self.v.require_date({"d": "not-a-date"}, "d")

    def test_require_date_wrong_type(self):
        with self.assertRaisesValidation():
            self.v.require_date({"d": 12345}, "d")

    def test_optional_date_absent(self):
        self.assertIsNone(self.v.optional_date({}, "d"))
        self.assertIsNone(self.v.optional_date({"d": None}, "d"))

    def test_optional_date_ok(self):
        from datetime import date

        self.assertEqual(
            self.v.optional_date({"d": "2026-06-01"}, "d"),
            date(2026, 6, 1),
        )


class TestMapIntegrityError(TestCase):
    def test_map_integrity_error_unique_match(self):
        exc = IntegrityError(
            'duplicate key value violates unique constraint "uq_categorie_clienti_codice"'
        )
        with self.assertRaises(ServiceError) as ctx:
            map_integrity_error(
                exc,
                unique_constraints={
                    "uq_categorie_clienti_codice": (
                        "E_ANAG_DUPLICATO",
                        "Codice duplicato.",
                    ),
                },
                fallback_code="E_ANAG_VALIDAZIONE",
                context={"codice": "X"},
            )
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")
        self.assertEqual(ctx.exception.message, "Codice duplicato.")
        self.assertEqual(ctx.exception.context, {"codice": "X"})

    # Scopo: ⭐ Il terzo elemento della tupla — il CAMPO da accendere nel form.
    #        Sul duplicato e' il caso in cui serve di piu': il form e' compilato
    #        bene, la validazione client non ha niente da dire, e senza il campo
    #        l'operatore legge «esiste gia'» e deve indovinare quale.
    def test_map_integrity_error_porta_il_campo_del_vincolo(self):
        exc = IntegrityError(
            'duplicate key value violates unique constraint "uq_categorie_clienti_codice"'
        )
        with self.assertRaises(ServiceError) as ctx:
            map_integrity_error(
                exc,
                unique_constraints={
                    "uq_categorie_clienti_codice": (
                        "E_ANAG_DUPLICATO",
                        "Codice duplicato.",
                        "codice",
                    ),
                },
                fallback_code="E_ANAG_VALIDAZIONE",
                context={"codice": "X"},
            )
        self.assertEqual(ctx.exception.context, {"codice": "X", "field": "codice"})

    # Scopo: ⚠️ IL CAMPO E' DELLA VOCE, NON DEL CONTESTO CONDIVISO, ed e' la
    #        differenza che decide se il client accende l'input giusto. Una
    #        mappa con due vincoli su campi diversi deve dare il campo di
    #        QUELLO che ha fatto match: un `field` nel contesto comune si
    #        applicherebbe a entrambi, e mandare l'operatore a correggere un
    #        campo giusto e' peggio che non indicargliene nessuno.
    def test_map_integrity_error_campo_del_vincolo_che_ha_fatto_match(self):
        mappa = {
            "uq_tab_codice": ("E_DUP", "Codice duplicato.", "codice"),
            "uq_tab_email": ("E_DUP", "Email duplicata.", "email"),
        }
        for vincolo, campo_atteso in (("uq_tab_codice", "codice"), ("uq_tab_email", "email")):
            with self.subTest(vincolo=vincolo):
                exc = IntegrityError(f'duplicate key violates unique constraint "{vincolo}"')
                with self.assertRaises(ServiceError) as ctx:
                    map_integrity_error(
                        exc, unique_constraints=mappa, fallback_code="E_FALLBACK"
                    )
                self.assertEqual(ctx.exception.context.get("field"), campo_atteso)

    # Scopo: la tupla a due elementi resta valida e NON inventa un campo. E' la
    #        forma giusta per i vincoli composti su piu' colonne che l'operatore
    #        sceglie davvero: li' un campo solo direbbe il falso.
    def test_map_integrity_error_senza_campo_non_lo_inventa(self):
        exc = IntegrityError('duplicate key violates unique constraint "uq_coppia"')
        with self.assertRaises(ServiceError) as ctx:
            map_integrity_error(
                exc,
                unique_constraints={"uq_coppia": ("E_DUP", "Coppia duplicata.")},
                fallback_code="E_FALLBACK",
                context={"a": 1},
            )
        self.assertNotIn("field", ctx.exception.context)

    def test_map_integrity_error_fk_match(self):
        exc = IntegrityError('insert violates foreign key constraint "fk_figlio_padre"')
        with self.assertRaises(ServiceError) as ctx:
            map_integrity_error(
                exc,
                fk_constraints={
                    "fk_figlio_padre": (
                        "E_ANAG_FK",
                        "Padre inesistente.",
                    ),
                },
                fallback_code="E_ANAG_VALIDAZIONE",
            )
        self.assertEqual(ctx.exception.code, "E_ANAG_FK")

    def test_map_integrity_error_check_match(self):
        exc = IntegrityError(
            'new row violates check constraint "chk_template_documenti_versioni_valido_dal_pubblicata"'
        )
        with self.assertRaises(ServiceError) as ctx:
            map_integrity_error(
                exc,
                check_constraints={
                    "chk_template_documenti_versioni_valido_dal_pubblicata": (
                        "E_DOCUMENTI_VALIDATION",
                        "Una versione PUBBLICATA deve avere valido_dal valorizzato.",
                    ),
                },
                fallback_code="E_FALLBACK",
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        self.assertEqual(
            ctx.exception.message,
            "Una versione PUBBLICATA deve avere valido_dal valorizzato.",
        )

    def test_map_integrity_error_fallback(self):
        exc = IntegrityError("some generic db error")
        with self.assertRaises(ServiceError) as ctx:
            map_integrity_error(
                exc,
                fallback_code="E_TEST_VALIDATION",
                fallback_message="Errore generico.",
            )
        self.assertEqual(ctx.exception.code, "E_TEST_VALIDATION")
        self.assertEqual(ctx.exception.message, "Errore generico.")

    def test_map_integrity_error_case_insensitive(self):
        # constraint name in maiuscolo nel messaggio, mappa in minuscolo
        exc = IntegrityError('violates unique constraint "UQ_FOO_BAR"')
        with self.assertRaises(ServiceError) as ctx:
            map_integrity_error(
                exc,
                unique_constraints={
                    "uq_foo_bar": ("E_DUP", "Duplicato."),
                },
                fallback_code="E_FALLBACK",
            )
        self.assertEqual(ctx.exception.code, "E_DUP")

    def test_map_integrity_exact_match_non_prefix(self):
        # Review: "fk_foo" non deve matchare "fk_foo_bar" (prefix trap).
        # Il messaggio DB cita "fk_foo_bar"; se mappiamo SOLO "fk_foo",
        # non ci deve essere match -> fallback.
        exc = IntegrityError('violates foreign key constraint "fk_foo_bar"')
        with self.assertRaises(ServiceError) as ctx:
            map_integrity_error(
                exc,
                fk_constraints={
                    "fk_foo": ("E_FK_FOO", "Foo."),
                },
                fallback_code="E_FALLBACK",
            )
        self.assertEqual(ctx.exception.code, "E_FALLBACK")

    def test_map_integrity_fk_preferita_su_specific(self):
        # Se la mappa contiene il constraint SPECIFICO, va preso quello
        # (il prefix puo' essere nella mappa ma non deve prevalere).
        exc = IntegrityError('violates foreign key constraint "fk_foo_bar_baz"')
        with self.assertRaises(ServiceError) as ctx:
            map_integrity_error(
                exc,
                fk_constraints={
                    "fk_foo": ("E_FK_FOO", "Foo."),
                    "fk_foo_bar_baz": ("E_FK_SPECIFIC", "Specifico."),
                },
                fallback_code="E_FALLBACK",
            )
        # Il constraint esatto vince (word boundary esclude fk_foo).
        self.assertEqual(ctx.exception.code, "E_FK_SPECIFIC")


from apps.core.services.payload_helpers import make_db_errors_translator
from apps.core.tests.db_error_fakes import make_db_error


class TestTranslateDbErrorsHint(TestCase):
    """L'AZIONE SUGGERITA del catalogo arriva strutturata fino al chiamante."""

    # Scopo: 🔴 il campo che si perdeva. Per ogni codice il team DB scrive a
    # catalogo una `soluzione` — «se il documento non e' ancora numerato, la
    # strada e' il reset del lotto…» — che PostgreSQL consegna come HINT. Fino
    # al 2026-08-18 il traduttore la lasciava annegata nel testo di `detail`, e
    # un dominio che volesse mostrarla all'operatore doveva RISCRIVERLA in
    # Python: cioe' duplicare il catalogo, che e' la cosa che questo progetto
    # non fa. Ora viaggia in `hint`, dove l'envelope API la espone.
    def test_hint_del_db_arriva_nel_service_error(self) -> None:
        traduttore = make_db_errors_translator(
            fn_prefix="test.dominio",
            fallback_code="E_TEST_FALLBACK",
            fallback_message="fallback",
        )
        with self.assertRaises(ServiceError) as cm:
            with traduttore("op"):
                raise make_db_error(
                    "Riga di reso 24: rettifiche gia' emesse.",
                    codice="E_ACCREDITO_ANNULLO_NON_AMMESSO",
                    hint="Se il documento non e' ancora numerato, resetta il lotto.",
                )
        self.assertEqual(cm.exception.code, "E_ACCREDITO_ANNULLO_NON_AMMESSO")
        self.assertEqual(
            cm.exception.hint,
            "Se il documento non e' ancora numerato, resetta il lotto.",
        )

    # Scopo: un errore DB senza HINT non deve inventarne uno.
    def test_senza_hint_il_campo_resta_vuoto(self) -> None:
        traduttore = make_db_errors_translator(
            fn_prefix="test.dominio",
            fallback_code="E_TEST_FALLBACK",
            fallback_message="fallback",
        )
        with self.assertRaises(ServiceError) as cm:
            with traduttore("op"):
                raise make_db_error("errore secco", codice="E_TEST_SECCO")
        self.assertIsNone(cm.exception.hint)


class TestRequireCampiDaAggiornare(TestCase):
    """Un PATCH deve portare almeno un campo: mai un «salvato» a vuoto."""

    def setUp(self) -> None:
        self.v = PayloadValidator(validation_code=_CODE)

    # Scopo: niente campi -> 400 col codice del dominio e il messaggio di default.
    def test_require_campi_da_aggiornare_vuoto(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.v.require_campi_da_aggiornare({})
        self.assertEqual(ctx.exception.code, _CODE)
        self.assertEqual(ctx.exception.message, "Nessun campo aggiornabile presente nel payload.")

    # Scopo: una chiave col valore None e' un reset, cioe' una modifica.
    def test_require_campi_da_aggiornare_none_e_un_reset(self) -> None:
        self.v.require_campi_da_aggiornare({"descrizione": None})

    # Scopo: ⛔ il caso che passava (2026-10-14): `{"utility": {}}` da solo non
    #        e' una modifica, ne' un sotto-oggetto None o non-dict.
    def test_require_campi_da_aggiornare_sotto_oggetto_vuoto(self) -> None:
        for satellite in ({}, None, []):
            with self.subTest(satellite=satellite), self.assertRaises(ServiceError):
                self.v.require_campi_da_aggiornare({}, sotto_oggetti={"utility": satellite})

    # Scopo: un sotto-oggetto con almeno una chiave basta, anche senza testata.
    def test_require_campi_da_aggiornare_sotto_oggetto_pieno(self) -> None:
        self.v.require_campi_da_aggiornare({}, sotto_oggetti={"utility": {"classe_utenza_id": None}})

    # Scopo: messaggio e context del chiamante arrivano nell'errore.
    def test_require_campi_da_aggiornare_override(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.v.require_campi_da_aggiornare(
                {}, message="Payload riga non valido.", context={"op": "x"},
            )
        self.assertEqual(ctx.exception.message, "Payload riga non valido.")
        self.assertEqual(ctx.exception.context.get("op"), "x")
