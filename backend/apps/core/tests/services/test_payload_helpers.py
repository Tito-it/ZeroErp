# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
56) test_reject_keys_empty_ok                   — nuovo helper V6-B2 review
57) test_reject_keys_presente                   — nuovo helper V6-B2 review
"""

from unittest import TestCase

from django.db import IntegrityError

from apps.core.services.payload_helpers import (
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

    def test_optional_bool_int(self):
        with self.assertRaisesValidation():
            self.v.optional_bool({"attivo": 1}, "attivo")


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
        self.v.validate_order_by("codice", allowed=self._ALLOWED)

    def test_validate_order_by_invalid(self):
        with self.assertRaisesValidation() as ctx:
            self.v.validate_order_by("random_col", allowed=self._ALLOWED)
        self.assertEqual(ctx.exception.code, _CODE)


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
