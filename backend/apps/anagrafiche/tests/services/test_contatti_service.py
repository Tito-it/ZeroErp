# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per classify_contatto_payload (Fase 5 refactor
#        anagrafiche). Verifica la regola unificata "contatto e' EMPTY,
#        PARTIAL o VALID" usata da clienti, fornitori e soggetti service.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_classify_none_returns_empty               — None payload → EMPTY
 2) test_classify_empty_dict_returns_empty         — dict vuoto → EMPTY
 3) test_classify_all_strings_blank_returns_empty  — solo stringhe vuote → EMPTY
 4) test_classify_only_email_returns_partial       — email senza nominativo+tipo → PARTIAL
 5) test_classify_only_telefono_returns_partial    — telefono solo → PARTIAL
 6) test_classify_only_nominativo_returns_partial  — nominativo senza tipo → PARTIAL
 7) test_classify_only_tipo_contatto_returns_partial — tipo senza nominativo → PARTIAL
 8) test_classify_required_present_returns_valid   — nominativo+tipo presenti → VALID
 9) test_classify_full_payload_returns_valid       — tutti i campi → VALID
10) test_classify_tipo_contatto_zero_returns_partial — tipo_contatto_id=0 considerato non valido
11) test_classify_nominativo_whitespace_returns_partial — nominativo solo spazi → non valido
12) test_missing_required_fields_partial_returns_only_missing — manca solo nominativo
13) test_missing_required_fields_empty_for_valid  — VALID → lista vuota
14) test_missing_required_fields_none_returns_all — None → tutti i required
15) test_missing_required_fields_empty_dict_returns_all — {} → tutti i required
16) test_crea_contatto_validato_duplicato_tipo — ogni unicita' per tipo → E_ANAG_DUPLICATO col campo tipo_contatto_id
17) test_crea_contatto_validato_incompleto — contatto non VALIDO → E_CONTATTO_INCOMPLETO, nessuna scrittura
"""

from unittest import TestCase

from apps.anagrafiche.services.contatti_service import (
    classify_contatto_payload,
    missing_required_fields,
)


class ClassifyContattoPayloadTests(TestCase):
    """Verifica regola classify EMPTY/PARTIAL/VALID."""

    def test_classify_none_returns_empty(self):
        self.assertEqual(classify_contatto_payload(None), "EMPTY")

    def test_classify_empty_dict_returns_empty(self):
        self.assertEqual(classify_contatto_payload({}), "EMPTY")

    def test_classify_all_strings_blank_returns_empty(self):
        payload = {"nominativo": "", "email": "", "telefono": "  ", "pec": ""}
        self.assertEqual(classify_contatto_payload(payload), "EMPTY")

    def test_classify_only_email_returns_partial(self):
        """Bug originale fornitore: email senza nominativo veniva scartata silenziosamente.
        Ora deve sollevare PARTIAL → caller raise E_CONTATTO_INCOMPLETO."""
        payload = {"email": "mario@example.it"}
        self.assertEqual(classify_contatto_payload(payload), "PARTIAL")

    def test_classify_only_telefono_returns_partial(self):
        payload = {"telefono": "+39 123 456 7890"}
        self.assertEqual(classify_contatto_payload(payload), "PARTIAL")

    def test_classify_only_nominativo_returns_partial(self):
        """Nominativo senza tipo_contatto → PARTIAL (DB ha NOT NULL su tipo_contatto_id)."""
        payload = {"nominativo": "Mario Rossi"}
        self.assertEqual(classify_contatto_payload(payload), "PARTIAL")

    def test_classify_only_tipo_contatto_returns_partial(self):
        payload = {"tipo_contatto_id": 5}
        self.assertEqual(classify_contatto_payload(payload), "PARTIAL")

    def test_classify_required_present_returns_valid(self):
        """Caso minimo VALID: solo nominativo + tipo_contatto_id."""
        payload = {"nominativo": "Mario Rossi", "tipo_contatto_id": 5}
        self.assertEqual(classify_contatto_payload(payload), "VALID")

    def test_classify_full_payload_returns_valid(self):
        payload = {
            "nominativo": "Mario Rossi", "tipo_contatto_id": 5,
            "email": "x@y.it", "telefono": "123", "cellulare": "456", "pec": "p@p.it",
        }
        self.assertEqual(classify_contatto_payload(payload), "VALID")

    def test_classify_tipo_contatto_zero_returns_partial(self):
        """tipo_contatto_id=0 non e' un id valido (FK > 0) → considerato non valorizzato."""
        payload = {"nominativo": "Mario", "tipo_contatto_id": 0}
        self.assertEqual(classify_contatto_payload(payload), "PARTIAL")

    def test_classify_nominativo_whitespace_returns_partial(self):
        """Nominativo composto solo da spazi non conta come valorizzato."""
        payload = {"nominativo": "   ", "tipo_contatto_id": 5}
        # whitespace su nominativo → considerato non valorizzato → PARTIAL
        # (tipo_contatto_id e' valorizzato → any_filled True)
        self.assertEqual(classify_contatto_payload(payload), "PARTIAL")


class MissingRequiredFieldsTests(TestCase):
    """Helper per dare contesto strutturato al frontend (highlight campo mancante)."""

    def test_missing_required_fields_partial_returns_only_missing(self):
        """Payload PARTIAL con solo email → mancano entrambi gli obbligatori."""
        self.assertEqual(
            missing_required_fields({"email": "x@y.it"}),
            ["nominativo", "tipo_contatto_id"],
        )

    def test_missing_required_fields_one_missing(self):
        """Solo nominativo presente → manca tipo_contatto_id."""
        self.assertEqual(
            missing_required_fields({"nominativo": "Mario", "email": "x"}),
            ["tipo_contatto_id"],
        )

    def test_missing_required_fields_empty_for_valid(self):
        self.assertEqual(
            missing_required_fields({"nominativo": "Mario", "tipo_contatto_id": 5}),
            [],
        )

    def test_missing_required_fields_none_returns_all(self):
        """None → tutti gli obbligatori mancano (semantica coerente per caller
        soggetto, dove EMPTY equivale a 'contatto non fornito')."""
        self.assertEqual(
            missing_required_fields(None),
            ["nominativo", "tipo_contatto_id"],
        )

    def test_missing_required_fields_empty_dict_returns_all(self):
        """{} → tutti gli obbligatori mancano (consistenza con None)."""
        self.assertEqual(
            missing_required_fields({}),
            ["nominativo", "tipo_contatto_id"],
        )


class TestCreaContattoValidato(TestCase):
    """BB `crea_contatto_validato` (regola del 2, 2026-10-09)."""

    _VALIDO = {"nominativo": "Mario Rossi", "tipo_contatto_id": 3}

    # 16. Le tre unicita' (soggetto, ruolo, ruolo per istanza) si traducono
    #     sul campo che l'operatore sceglie, non in un `E_DATABASE`.
    def test_crea_contatto_validato_duplicato_tipo(self):
        from unittest.mock import MagicMock

        from apps.anagrafiche.services.contatti_service import crea_contatto_validato
        from apps.core.services.service_errors import ServiceError
        from apps.core.tests.db_error_fakes import SQLSTATE_UNICITA, make_integrity_error

        for vincolo in (
            "uq_contatti_soggetto_tipo",
            "uq_contatti_ruolo_tipo_no_istanza",
            "uq_contatti_ruolo_istanza_tipo",
        ):
            with self.subTest(vincolo=vincolo):
                repo = MagicMock()
                repo.crea_contatto.side_effect = make_integrity_error(SQLSTATE_UNICITA, vincolo=vincolo)
                with self.assertRaises(ServiceError) as ctx:
                    crea_contatto_validato(repo, "s", dict(self._VALIDO))
                self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")
                # Il canale del campo singolo (il traduttore lo porta in `error.fields`).
                self.assertEqual(ctx.exception.context.get("field"), "tipo_contatto_id")

    # 17. Il contatto si pretende VALIDO: niente scrittura altrimenti.
    def test_crea_contatto_validato_incompleto(self):
        from unittest.mock import MagicMock

        from apps.anagrafiche.services.contatti_service import crea_contatto_validato
        from apps.core.services.service_errors import ServiceError

        repo = MagicMock()
        with self.assertRaises(ServiceError) as ctx:
            crea_contatto_validato(repo, "s", {"nominativo": "Mario Rossi"})
        self.assertEqual(ctx.exception.code, "E_CONTATTO_INCOMPLETO")
        self.assertEqual(ctx.exception.fields, ("tipo_contatto_id",))
        repo.crea_contatto.assert_not_called()

