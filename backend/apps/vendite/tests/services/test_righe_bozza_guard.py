# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB `richiedi_righe_in_bozza` (apps/vendite/services/
#        _righe_bozza_guard.py): il pre-check Python di «le righe si toccano
#        solo in bozza» parla col codice, la frase e il context del trigger
#        `vendite.trgfn_doc_righe_lock_fuori_bozza`.
# ------------------------------------------------------------
"""
Indice test:

RigheBozzaGuardTests (unit, senza DB)
 1) test_bozza_passa                       — DRAFT: nessun errore
 2) test_fuori_bozza_frase_con_numero      — codice E_RIGA_DOC_NON_BOZZA, frase
                                             a catalogo coi tre valori
 3) test_fuori_bozza_ripiego_su_id         — `numero` NULL -> «DDT #7»
 4) test_context_come_il_trigger           — documento maiuscolo, testata_id,
                                             stato, operazione = TG_OP (non il verbo)
 5) test_operazione_per_ogni_verbo         — i tre verbi -> INSERT/UPDATE/DELETE
 6) test_verbo_fuori_catalogo              — ValueError, non un 409 storto
 7) test_testata_senza_stato               — KeyError: lettore rotto, non un
                                             409 con «(stato )»

RigheBozzaGuardCatalogoE2ETests (OPT-IN `ZEROERP_TEST_DB_E2E=1`)
 8) test_frase_uguale_al_catalogo          — FRASE_CATALOGO == config.messaggi_errore
"""

from __future__ import annotations

# `unittest.TestCase` per la classe e2e, di proposito: `django.test.TestCase`
# dichiarerebbe un database e farebbe creare al runner un DB usa-e-getta per
# TUTTA la suite (AGENTS.md §Regole test Django); `SimpleTestCase` vieta il
# DB, che qui e' proprio cio' che serve.
from unittest import TestCase

from django.test import SimpleTestCase

from apps.core.services.error_manager import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.services._righe_bozza_guard import (
    CODICE,
    FRASE_CATALOGO,
    OPERAZIONE_PER_VERBO,
    richiedi_righe_in_bozza,
)

_FN = "test.righe_bozza_guard"


class RigheBozzaGuardTests(SimpleTestCase):
    """Il guard, da solo: codice, frase, context."""

    # Scopo: Verifica il caso `test_bozza_passa`.
    def test_bozza_passa(self) -> None:
        richiedi_righe_in_bozza(
            {"stato_codice_interno": "DRAFT", "numero": None},
            documento="DDT", documento_id=7, verbo="aggiungere", function_name=_FN,
        )

    # Scopo: Verifica il caso `test_fuori_bozza_frase_con_numero`.
    def test_fuori_bozza_frase_con_numero(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            richiedi_righe_in_bozza(
                {"stato_codice_interno": "EMESSO", "numero": "2026/00012"},
                documento="DDT", documento_id=7, verbo="modificare", function_name=_FN,
            )
        self.assertEqual(cm.exception.code, CODICE)
        self.assertEqual(
            cm.exception.message,
            "DDT 2026/00012 non e' piu' in bozza (stato EMESSO): le sue righe si "
            "possono modificare solo finche' e' in bozza.",
        )
        self.assertEqual(cm.exception.detail, "stato=EMESSO")

    # Scopo: Verifica il caso `test_fuori_bozza_ripiego_su_id`.
    def test_fuori_bozza_ripiego_su_id(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            richiedi_righe_in_bozza(
                {"stato_codice_interno": "SPEDITO"},
                documento="DDT", documento_id=7, verbo="togliere", function_name=_FN,
            )
        self.assertTrue(cm.exception.message.startswith("DDT #7 non e' piu' in bozza"))

    # Scopo: Verifica il caso `test_context_come_il_trigger`: le chiavi E i
    #        valori sono quelli che scrive `trgfn_doc_righe_lock_fuori_bozza`
    #        (`operazione` = TG_OP), cosi' il diario legge una lingua sola;
    #        niente `field`, su un conflitto di stato non c'e' un input.
    def test_context_come_il_trigger(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            richiedi_righe_in_bozza(
                {"stato_codice_interno": "CONFERMATO", "numero": "2026/00003"},
                documento="Ordine", documento_id=31, verbo="togliere", function_name=_FN,
            )
        self.assertEqual(
            cm.exception.context,
            {"documento": "ORDINE", "testata_id": 31, "stato": "CONFERMATO",
             "operazione": "DELETE"},
        )

    # Scopo: Verifica il caso `test_operazione_per_ogni_verbo`: la tabella
    #        e' quella del trigger letta al contrario, e copre i tre verbi.
    def test_operazione_per_ogni_verbo(self) -> None:
        self.assertEqual(
            OPERAZIONE_PER_VERBO,
            {"aggiungere": "INSERT", "modificare": "UPDATE", "togliere": "DELETE"},
        )
        for verbo, operazione in OPERAZIONE_PER_VERBO.items():
            with self.assertRaises(ServiceError) as cm:
                richiedi_righe_in_bozza(
                    {"stato_codice_interno": "EMESSO"},
                    documento="Preventivo", documento_id=1, verbo=verbo,  # type: ignore[arg-type]
                    function_name=_FN,
                )
            self.assertEqual(cm.exception.context["operazione"], operazione)
            self.assertIn(f" {verbo} ", cm.exception.message)

    # Scopo: Verifica il caso `test_verbo_fuori_catalogo`: e' un errore del
    #        chiamante e non deve diventare un 409 con un verbo inventato.
    def test_verbo_fuori_catalogo(self) -> None:
        with self.assertRaises(ValueError):
            richiedi_righe_in_bozza(
                {"stato_codice_interno": "EMESSO"},
                documento="DDT", documento_id=7, verbo="cancellare",  # type: ignore[arg-type]
                function_name=_FN,
            )

    # Scopo: Verifica il caso `test_testata_senza_stato`: una lettura che non
    #        porta lo stato e' un lettore rotto (500), non un documento fuori
    #        bozza con «(stato )» nella frase.
    def test_testata_senza_stato(self) -> None:
        with self.assertRaises(KeyError):
            richiedi_righe_in_bozza(
                {"numero": "2026/00012"},
                documento="DDT", documento_id=7, verbo="aggiungere", function_name=_FN,
            )


class RigheBozzaGuardCatalogoE2ETests(TestCase):
    """La copia della frase e' voluta (niente round-trip a DB per un 409), e
    una copia senza presidio diverge in silenzio: qui si confronta col
    catalogo vivo. Opt-in `ZEROERP_TEST_DB_E2E=1` (in CI e' acceso), stesso
    prerequisito di `test_db_error_fields`."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto()

    # Scopo: Verifica il caso `test_frase_uguale_al_catalogo`.
    def test_frase_uguale_al_catalogo(self) -> None:
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute(
                "SELECT messaggio FROM config.messaggi_errore "
                "WHERE codice = %s AND lingua = 'it'",
                [CODICE],
            )
            row = cur.fetchone()
        self.assertIsNotNone(row, f"{CODICE} non e' a catalogo in lingua it")
        assert row is not None
        self.assertEqual(row[0], FRASE_CATALOGO)
