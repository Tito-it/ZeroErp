# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `PreventivoDocumentContextBuilder` (Tranche J motore
#        documentale). Mock-only su `PreventiviRepository`. Verifica:
#         - build_context happy path: shape dict stabile con sezioni
#           preventivo/cliente/indirizzi/righe/riepilogo_iva/_meta;
#         - guard id positivo: 0, negativo, bool, non-int -> VALIDATION;
#         - preventivo inesistente (repo ritorna None) -> NOT_FOUND;
#         - delega lettura ai metodi repo (chiamati 1 volta ciascuno);
#         - registrazione al boot Django: dopo import esplicito di
#           apps.vendite.services.preventivo_document_context_builder
#           il codice 'PREVENTIVO' e' in `registered_codes()`.
#
# Indice test (0..N):
#   0. build_context_happy_path_shape_completa
#   1. build_context_id_non_valido_raises_validation
#   2. build_context_preventivo_inesistente_raises_not_found
#   3. build_context_invoca_repo_una_volta_per_metodo
#   4. builder_code_costante_uguale_a_preventivo
#   5. registry_contiene_preventivo_dopo_import_modulo
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.preventivo_document_context_builder import (
    PreventivoDocumentContextBuilder,
)


def _testata_row() -> dict[str, Any]:
    return {
        "id": 1,
        "uid": "0190a000-0000-0000-0000-000000000001",
        "numero": "P-2026-0001",
        "rev": 0,
        "is_attiva": True,
        "has_next_revision": False,
        "data": "2026-05-04",
        "stato_doc_preventivo_id": 3,
        "stato_codice_interno": "BOZZA",
        "stato_codice": "BOZZA",
        "stato_descrizione": "Bozza",
        "billing_account_id": 100,
        "cliente_denominazione": "Acme Srl",
        "utility_id": 1,
        "utility_descrizione": "Gas",
        "istanza_utility_id": 5,
        "valuta_id": 1,
        "valuta_codice": "EUR",
        "termine_pagamento_id": 7,
        "termine_pagamento_descrizione": "30 gg fine mese",
        "validita_dal": "2026-05-04",
        "validita_al": "2026-06-04",
        "competenza_mese": "2026-05-01",
        "fatturazione_immediata": False,
        "totale_imponibile": "100.00",
        "totale_iva": "22.00",
        "totale_documento": "122.00",
        "storicizza": False,
        "meta": {"note": "abc"},
        "data_insert": "2026-05-04T10:00:00+00:00",
        "user_insert": "tid",
        "data_update": "2026-05-04T10:00:00+00:00",
        "user_update": None,
    }


class BuildContextHappyPathTests(SimpleTestCase):
    """build_context shape completa + valori dal repo."""

    # 0. happy path: dict atteso con tutte le sezioni.
    def test_build_context_happy_path_shape_completa(self) -> None:
        repo = MagicMock()
        repo.get_preventivo.return_value = _testata_row()
        repo.list_righe.return_value = [
            {"id": 1, "ordine": 1, "descrizione": "Riga 1", "importo_riga": "50.00"},
            {"id": 2, "ordine": 2, "descrizione": "Riga 2", "importo_riga": "50.00"},
        ]
        repo.list_riepilogo_iva.return_value = [
            {"iva_id": 1, "iva_aliquota": "22.00", "imponibile": "100.00", "imposta": "22.00"},
        ]
        repo.list_indirizzi.return_value = [
            {
                "tipo_indirizzo_id": 10,
                "tipo_indirizzo_codice_interno": "CON",
                "snapshot": {
                    "intestazione": "Acme Srl", "via": "VIA X 1", "cap": "00100",
                    "citta": "ROMA", "prov": "RM", "stato": "IT",
                },
            },
        ]

        builder = PreventivoDocumentContextBuilder(repo=repo)
        ctx = builder.build_context(1, auth_user_id=5, locale="it-IT")

        # Sezioni top-level previste.
        self.assertEqual(
            set(ctx.keys()),
            {"preventivo", "cliente", "indirizzi", "righe", "riepilogo_iva", "_meta"},
        )

        # Preventivo: chiavi principali + sotto-dict totali/stato.
        prev = ctx["preventivo"]
        self.assertEqual(prev["id"], 1)
        self.assertEqual(prev["numero"], "P-2026-0001")
        self.assertEqual(prev["data"], "04-05-2026")
        self.assertEqual(prev["data_iso"], "2026-05-04")
        self.assertEqual(prev["validita_dal"], "04-05-2026")
        self.assertEqual(prev["validita_dal_iso"], "2026-05-04")
        self.assertEqual(prev["fatturazione_immediata"], False)
        self.assertEqual(prev["stato"]["codice"], "BOZZA")
        # Numeri formattati per la stampa (2026-08-04): il context non porta
        # piu' la scala della colonna DB ma il formato italiano.
        self.assertEqual(prev["totali"]["imponibile"], "100,00")
        self.assertEqual(prev["totali"]["valuta_codice"], "EUR")
        self.assertEqual(prev["meta"], {"note": "abc"})

        # Cliente: solo billing_account + denominazione (v1).
        self.assertEqual(
            ctx["cliente"],
            {"billing_account_id": 100, "denominazione": "Acme Srl"},
        )

        # Righe + riepilogo IVA dal repo, coi soli campi numerici formattati.
        self.assertEqual(len(ctx["righe"]), 2)
        self.assertEqual(ctx["righe"][0]["descrizione"], "Riga 1")
        self.assertEqual(len(ctx["riepilogo_iva"]), 1)
        self.assertEqual(ctx["riepilogo_iva"][0]["iva_aliquota"], "22,00")
        self.assertEqual(ctx["riepilogo_iva"][0]["imponibile"], "100,00")

        # Indirizzi: forma unica cross-dominio (context v2, 2026-08-16). Non
        # piu' la lista pass-through della v1 ma slot con nome, TUTTI presenti
        # anche quando il documento non li ha — e' cio' che permette al
        # template l'accesso diretto `indirizzi.consegna.via` sotto
        # StrictUndefined invece del `.get()` difensivo che rese silenzioso il
        # difetto del Preventivo (brief-db-template-preventivo-indirizzi §2).
        indirizzi = ctx["indirizzi"]
        self.assertEqual(
            set(indirizzi.keys()),
            {"consegna", "fatturazione", "fornitura", "residenza"},
        )
        self.assertEqual(indirizzi["consegna"]["via"], "VIA X 1")
        self.assertEqual(indirizzi["consegna"]["prov"], "RM")
        # Chiavi opzionali comunque presenti (valore None), mai assenti.
        self.assertIsNone(indirizzi["consegna"]["display"])
        self.assertEqual(
            indirizzi["consegna"]["display_compatto"],
            "Acme Srl — VIA X 1, 00100 ROMA, RM",
        )
        # Slot ammessi dall'ambito ma non valorizzati sul documento: None.
        self.assertIsNone(indirizzi["fatturazione"])
        self.assertIsNone(indirizzi["fornitura"])
        self.assertIsNone(indirizzi["residenza"])

        # _meta: locale + auth_user_id + context_code + version.
        # NIENTE timestamp/random: context_hash deve essere deterministico
        # per consentire dedup logico in Tranche I.
        self.assertEqual(ctx["_meta"]["locale"], "it-IT")
        self.assertEqual(ctx["_meta"]["auth_user_id"], 5)
        self.assertEqual(ctx["_meta"]["context_code"], "PREVENTIVO")
        self.assertEqual(ctx["_meta"]["context_version"], 2)
        self.assertNotIn("built_at", ctx["_meta"])
        # Doppia chiamata a parita' di input -> dict identici (deterministico).
        ctx2 = PreventivoDocumentContextBuilder(repo=repo).build_context(
            1, auth_user_id=5, locale="it-IT",
        )
        self.assertEqual(ctx, ctx2)

    # 3. delega ai metodi repo (chiamati 1 volta ciascuno).
    def test_build_context_invoca_repo_una_volta_per_metodo(self) -> None:
        repo = MagicMock()
        repo.get_preventivo.return_value = _testata_row()
        repo.list_righe.return_value = []
        repo.list_riepilogo_iva.return_value = []
        repo.list_indirizzi.return_value = []

        PreventivoDocumentContextBuilder(repo=repo).build_context(1)

        repo.get_preventivo.assert_called_once_with(1)
        repo.list_righe.assert_called_once_with(1)
        repo.list_riepilogo_iva.assert_called_once_with(1)
        repo.list_indirizzi.assert_called_once_with(1)


class BuildContextGuardTests(SimpleTestCase):
    """Guard input + 404."""

    # 1. id non valido (0, negativo, bool, non-int) -> VALIDATION, no DB.
    def test_build_context_id_non_valido_raises_validation(self) -> None:
        repo = MagicMock()
        builder = PreventivoDocumentContextBuilder(repo=repo)
        for bad in (0, -1, True, "stringa"):
            with self.subTest(value=bad):
                with self.assertRaises(ServiceError) as ctx:
                    builder.build_context(bad)  # type: ignore[arg-type]
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.get_preventivo.assert_not_called()

    # 2. preventivo inesistente -> E_DOCUMENTI_NOT_FOUND, no chiamate aggiuntive.
    def test_build_context_preventivo_inesistente_raises_not_found(
        self,
    ) -> None:
        repo = MagicMock()
        repo.get_preventivo.return_value = None
        builder = PreventivoDocumentContextBuilder(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            builder.build_context(999)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        # list_* NON chiamati: 404 prima.
        repo.list_righe.assert_not_called()
        repo.list_riepilogo_iva.assert_not_called()
        repo.list_indirizzi.assert_not_called()


class BuilderCodeAndRegistryTests(SimpleTestCase):
    """Costante CODE + registrazione al boot Django."""

    # 4. CODE = "PREVENTIVO" — chiave whitelisted del registry.
    def test_builder_code_costante_uguale_a_preventivo(self) -> None:
        self.assertEqual(PreventivoDocumentContextBuilder.CODE, "PREVENTIVO")

    # 5. Dopo l'import del modulo (eseguito per side-effect dal
    #    VenditeConfig.ready() al boot), il registry contiene 'PREVENTIVO'.
    #    Qui forziamo l'import esplicito per garantire indipendenza dal
    #    boot order del runner di test.
    def test_registry_contiene_preventivo_dopo_import_modulo(self) -> None:
        # Import esplicito che esegue la `register_builder(...)` finale.
        import apps.vendite.services.preventivo_document_context_builder  # noqa: F401
        from apps.documenti.services.context_builders.registry import (
            registered_codes,
            get_builder,
        )

        codes = registered_codes()
        self.assertIn("PREVENTIVO", codes)
        builder = get_builder("PREVENTIVO")
        self.assertIsInstance(builder, PreventivoDocumentContextBuilder)
