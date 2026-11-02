# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `OrdineDocumentContextBuilder` (stampa conferma d'ordine).
#        Mock-only su `OrdiniRepository`. Verifica shape context (ordine +
#        cliente + righe), formattazione date, guard id + 404, registrazione
#        registry.
#
# Indice test (0..N):
#   0. build_context_shape_e_campi
#   1. build_context_righe_propagate
#   2. build_context_riepilogo_iva_propagate
#   3. build_context_id_non_valido_raises_validation
#   4. build_context_ordine_inesistente_raises_not_found
#   5. registry_contiene_ordine_vendita_dopo_import_modulo
#   6. build_context_senza_origine_chiavi_presenti
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.ordine_document_context_builder import (
    OrdineDocumentContextBuilder,
)


def _testata_row() -> dict[str, Any]:
    """Riga gemella di `vendite.vw_ordini_lista` (get_ordine)."""
    return {
        "id": 7,
        "uid": "0190b000-0000-0000-0000-000000000007",
        "numero": "ORD0000007",
        "serie": "A",
        "anno": 2026,
        "data": "2026-06-04",
        "data_insert": "2026-06-04 09:00:00",
        "stato_doc_ordine_id": 1,
        "stato_codice_interno": "DRAFT",
        "stato_descrizione": "Bozza",
        "soggetto_ruolo_id": 50,
        "soggetto_id": 40,
        "ragione_sociale_completa": "Cliente Ordine Srl",
        "id_fiscale_univoco_cf_piva": "IT01234567890",
        "billing_account_id": 10,
        "ba_codice": "BA-10",
        "emittente_fiscale_id": 3,
        "emittente_fiscale_codice": "EF-3",
        "utility_id": 5,
        "utility_codice": "GAS",
        "utility_descrizione": "Gas",
        "imponibile_tot": "100.00",
        "sconto_tot": "0.00",
        "iva_tot": "22.00",
        "totale_doc": "122.00",
        "modalita_pagamento_codice": "BB",
        "termine_pagamento_codice": "30GG",
        "valuta_codice": "EUR",
        "tasso_cambio": "1",
        "fatturazione_trigger": "CONFERMATO",
        "canale_origine": "ADMIN",
        "agente_denominazione": "Mario Rossi",
        "documento_origine_tipo": "PREVENTIVO",
        "documento_origine_codice": "P-2026/123",
        "documento_origine_etichetta": "Preventivo",
        "meta": {"note": "ordine demo"},
    }


class BuildContextOrdineTests(SimpleTestCase):
    """Shape context + formattazione."""

    # 0. Shape stabile + campi denormalizzati + date formattate IT/ISO.
    def test_build_context_shape_e_campi(self) -> None:
        repo = MagicMock()
        repo.get_ordine.return_value = _testata_row()
        repo.list_righe.return_value = []
        repo.list_riepilogo_iva.return_value = []

        ctx = OrdineDocumentContextBuilder(repo=repo).build_context(
            7, auth_user_id=9,
        )

        self.assertEqual(
            set(ctx.keys()),
            {"ordine", "cliente", "indirizzi", "righe", "riepilogo_iva", "_meta"},
        )
        # Slot indirizzi SEMPRE presenti anche senza righe (qui il repo mock non
        # ne restituisce): è ciò che permette al template l'accesso diretto
        # `indirizzi.consegna.via` sotto StrictUndefined invece del `.get()`
        # difensivo che rese silenzioso il difetto del Preventivo.
        self.assertEqual(ctx["indirizzi"], {"consegna": None, "fatturazione": None})
        ordine = ctx["ordine"]
        self.assertEqual(ordine["numero"], "ORD0000007")
        self.assertEqual(ordine["data"], "04-06-2026")
        self.assertEqual(ordine["data_iso"], "2026-06-04")
        self.assertEqual(ordine["fatturazione_trigger"], "CONFERMATO")
        self.assertEqual(ordine["canale_origine"], "ADMIN")
        self.assertEqual(ordine["stato"]["codice_interno"], "DRAFT")
        self.assertEqual(ordine["utility"]["codice"], "GAS")
        self.assertEqual(ordine["emittente"]["codice"], "EF-3")
        self.assertEqual(ordine["pagamento"]["modalita_codice"], "BB")
        self.assertEqual(ordine["origine"]["tipo"], "PREVENTIVO")
        self.assertEqual(ordine["origine"]["codice"], "P-2026/123")
        self.assertEqual(ordine["origine"]["etichetta"], "Preventivo")
        self.assertEqual(ordine["agente_denominazione"], "Mario Rossi")
        self.assertEqual(ordine["totali"]["imponibile"], "100,00")
        self.assertEqual(ordine["totali"]["documento"], "122,00")
        self.assertEqual(ordine["totali"]["valuta_codice"], "EUR")

        cliente = ctx["cliente"]
        self.assertEqual(cliente["denominazione"], "Cliente Ordine Srl")
        self.assertEqual(cliente["id_fiscale"], "IT01234567890")
        self.assertEqual(cliente["ba_codice"], "BA-10")
        self.assertEqual(cliente["soggetto_ruolo_id"], 50)

        self.assertEqual(ctx["_meta"]["context_code"], "ORDINE_VENDITA")
        # v3 dal 2026-10-20: `ordine.origine.etichetta`.
        self.assertEqual(ctx["_meta"]["context_version"], 3)
        self.assertEqual(ctx["_meta"]["auth_user_id"], 9)
        self.assertEqual(ctx["_meta"]["locale"], "it-IT")

    # 1. Le righe del repo passano intatte nel context.
    def test_build_context_righe_propagate(self) -> None:
        repo = MagicMock()
        repo.get_ordine.return_value = _testata_row()
        repo.list_righe.return_value = [
            {"id": 1, "articolo_descrizione": "Art A", "quantita": "2"},
            {"id": 2, "articolo_descrizione": "Art B", "quantita": "1"},
        ]
        repo.list_riepilogo_iva.return_value = []

        ctx = OrdineDocumentContextBuilder(repo=repo).build_context(7)

        self.assertEqual(len(ctx["righe"]), 2)
        self.assertEqual(ctx["righe"][0]["articolo_descrizione"], "Art A")
        repo.list_righe.assert_called_once_with(7)

    # 2. Il riepilogo IVA (vista derivata) passa intatto nel context.
    def test_build_context_riepilogo_iva_propagate(self) -> None:
        repo = MagicMock()
        repo.get_ordine.return_value = _testata_row()
        repo.list_righe.return_value = []
        repo.list_riepilogo_iva.return_value = [
            {
                "ordine_id": 7, "iva_id": 1, "iva_codice": "22",
                "iva_aliquota": "22.00", "imponibile": "100.00",
                "imposta": "22.00", "totale_riga": "122.00",
            },
        ]

        ctx = OrdineDocumentContextBuilder(repo=repo).build_context(7)

        self.assertEqual(len(ctx["riepilogo_iva"]), 1)
        self.assertEqual(ctx["riepilogo_iva"][0]["iva_aliquota"], "22,00")
        self.assertEqual(ctx["riepilogo_iva"][0]["imposta"], "22,00")
        repo.list_riepilogo_iva.assert_called_once_with(7)

    # 6. Ordine senza origine (CREATE diretta): le tre chiavi di `origine` ci
    #    sono comunque, a None. Il template le legge sotto StrictUndefined
    #    (`{% if ordine.origine.etichetta or ordine.origine.codice %}`): una
    #    chiave assente sarebbe un render fallito, non un blocco vuoto.
    def test_build_context_senza_origine_chiavi_presenti(self) -> None:
        repo = MagicMock()
        repo.get_ordine.return_value = {
            **_testata_row(),
            "documento_origine_tipo": None,
            "documento_origine_codice": None,
            "documento_origine_etichetta": None,
        }
        repo.list_righe.return_value = []
        repo.list_riepilogo_iva.return_value = []

        ctx = OrdineDocumentContextBuilder(repo=repo).build_context(7)

        self.assertEqual(
            ctx["ordine"]["origine"],
            {"tipo": None, "codice": None, "etichetta": None},
        )


class BuildContextOrdineGuardTests(SimpleTestCase):
    """Guard input + 404."""

    # 3. id non valido -> VALIDATION, no DB.
    def test_build_context_id_non_valido_raises_validation(self) -> None:
        repo = MagicMock()
        builder = OrdineDocumentContextBuilder(repo=repo)
        for bad in (0, -1, True, "stringa"):
            with self.subTest(value=bad):
                with self.assertRaises(ServiceError) as ctx:
                    builder.build_context(bad)  # type: ignore[arg-type]
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.get_ordine.assert_not_called()

    # 4. ordine inesistente -> NOT_FOUND, niente list_righe/riepilogo.
    def test_build_context_ordine_inesistente_raises_not_found(self) -> None:
        repo = MagicMock()
        repo.get_ordine.return_value = None
        builder = OrdineDocumentContextBuilder(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            builder.build_context(999)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        repo.list_righe.assert_not_called()
        repo.list_riepilogo_iva.assert_not_called()


class BuilderCodeAndRegistryTests(SimpleTestCase):
    """Costante CODE + registrazione al boot Django."""

    # 5. Dopo l'import del modulo, il registry contiene 'ORDINE_VENDITA'.
    def test_registry_contiene_ordine_vendita_dopo_import_modulo(self) -> None:
        import apps.vendite.services.ordine_document_context_builder  # noqa: F401
        from apps.documenti.services.context_builders.registry import (
            get_builder,
            registered_codes,
        )

        self.assertIn("ORDINE_VENDITA", registered_codes())
        builder = get_builder("ORDINE_VENDITA")
        self.assertIsInstance(builder, OrdineDocumentContextBuilder)
