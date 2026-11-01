# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `DdtDocumentContextBuilder` (stampa DDT accompagnatorio).
#        Mock-only su `DdtRepository`. Verifica shape context (ddt +
#        destinatario + trasporto + righe), formattazione date, guard id +
#        404, registrazione registry. Mirror di
#        test_ordine_document_context_builder (quinto dominio famiglia).
#
# Indice test (0..N):
#   0. build_context_shape_e_campi
#   1. build_context_righe_propagate
#   2. build_context_numero_null_in_draft
#   3. build_context_id_non_valido_raises_validation
#   4. build_context_ddt_inesistente_raises_not_found
#   5. registry_contiene_ddt_vendita_dopo_import_modulo
#   6. build_context_consegna_da_snapshot_con
#   7. build_context_consegna_none_senza_slot_con
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.ddt_document_context_builder import (
    DdtDocumentContextBuilder,
)


def _testata_row() -> dict[str, Any]:
    """Riga gemella di `vendite.vw_ddt_lista` (get_ddt)."""
    return {
        "id": 54,
        "uid": "019f4c7d-328d-7e87-947e-786ff90ea13d",
        "numero": "DDT0000030",
        "serie": None,
        "anno": 2026,
        "data": "2026-07-10",
        "stato_doc_ddt_id": 2,
        "stato_codice_interno": "EMESSO",
        "stato_descrizione": "Emesso",
        "destinatario_soggetto_ruolo_id": 50,
        "destinatario_soggetto_id": 40,
        "destinatario_denominazione": "Destinatario Merce Srl",
        "id_fiscale_univoco_cf_piva": "IT01234567890",
        "billing_account_id": 155,
        "ba_codice": "BA-155",
        "emittente_fiscale_id": 32,
        "emittente_fiscale_codice": "EF-32",
        "utility_id": 5,
        "utility_codice": "BASE",
        "utility_descrizione": "Base",
        "valuta_id": 1,
        "valuta_codice": "EUR",
        "mittente_soggetto_ruolo_id": 60,
        "mittente_denominazione": "Magazzino Centrale Srl",
        "vettore_soggetto_ruolo_id": 61,
        "vettore_denominazione": "Trasporti Veloci Snc",
        "causale_trasporto_id": 1,
        "causale_trasporto_codice": "VEND",
        "causale_trasporto_descrizione": "Vendita",
        "aspetto_bene_id": 2,
        "aspetto_bene_codice": "SCATOLE",
        "aspetto_bene_descrizione": "Scatole",
        "modalita_addebito_trasporto_codice": "FRANCO",
        "num_colli": 3,
        "peso_lordo": "12.500",
        "peso_netto": "11.000",
        "volume": "0.250",
        "targa": "AB123CD",
        "autista": "Mario Verdi",
        "tracking_code": "TRK-001",
        "data_ora_partenza": None,
        "data_ora_consegna_prev": None,
        "sorgente_codice_interno": "ORDINE_VENDITA",
        "ordine_origine_id": 174,
        "ordine_origine_numero": "ORD0000163",
        "meta": {"note": "ddt demo"},
    }


class BuildContextDdtTests(SimpleTestCase):
    """Shape context + formattazione."""

    # 0. Shape stabile + campi denormalizzati + date formattate IT/ISO.
    def test_build_context_shape_e_campi(self) -> None:
        repo = MagicMock()
        repo.get_ddt.return_value = _testata_row()
        repo.list_righe.return_value = []
        repo.list_indirizzi.return_value = []

        ctx = DdtDocumentContextBuilder(repo=repo).build_context(
            54, auth_user_id=9,
        )

        self.assertEqual(
            set(ctx.keys()),
            {"ddt", "destinatario", "indirizzi", "trasporto", "righe", "_meta"},
        )
        ddt = ctx["ddt"]
        self.assertEqual(ddt["numero"], "DDT0000030")
        self.assertEqual(ddt["data"], "10-07-2026")
        self.assertEqual(ddt["data_iso"], "2026-07-10")
        self.assertEqual(ddt["stato"]["codice_interno"], "EMESSO")
        self.assertEqual(ddt["utility"]["codice"], "BASE")
        self.assertEqual(ddt["emittente"]["codice"], "EF-32")
        self.assertEqual(ddt["valuta_codice"], "EUR")
        self.assertEqual(ddt["origine"]["ordine_numero"], "ORD0000163")
        self.assertEqual(
            ddt["origine"]["sorgente_codice_interno"], "ORDINE_VENDITA",
        )

        destinatario = ctx["destinatario"]
        self.assertEqual(destinatario["denominazione"], "Destinatario Merce Srl")
        self.assertEqual(destinatario["id_fiscale"], "IT01234567890")
        self.assertEqual(destinatario["ba_codice"], "BA-155")
        self.assertEqual(destinatario["soggetto_ruolo_id"], 50)

        trasporto = ctx["trasporto"]
        self.assertEqual(trasporto["causale"]["codice"], "VEND")
        self.assertEqual(trasporto["aspetto_beni"]["descrizione"], "Scatole")
        self.assertEqual(trasporto["porto_codice"], "FRANCO")
        self.assertEqual(
            trasporto["mittente_denominazione"], "Magazzino Centrale Srl",
        )
        self.assertEqual(
            trasporto["vettore_denominazione"], "Trasporti Veloci Snc",
        )
        self.assertEqual(trasporto["num_colli"], 3)
        self.assertEqual(trasporto["peso_lordo"], "12,50")
        self.assertEqual(trasporto["targa"], "AB123CD")
        self.assertEqual(trasporto["tracking_code"], "TRK-001")

        self.assertEqual(ctx["_meta"]["context_code"], "DDT_VENDITA")
        self.assertEqual(ctx["_meta"]["context_version"], 2)
        self.assertEqual(ctx["_meta"]["auth_user_id"], 9)
        self.assertEqual(ctx["_meta"]["locale"], "it-IT")

    # 1. Le righe del repo passano intatte nel context.
    def test_build_context_righe_propagate(self) -> None:
        repo = MagicMock()
        repo.get_ddt.return_value = _testata_row()
        repo.list_indirizzi.return_value = []
        repo.list_righe.return_value = [
            {"id": 1, "articolo_descrizione": "Art A", "qta_operativa": "2"},
            {"id": 2, "articolo_descrizione": "Art B", "qta_operativa": "1"},
        ]

        ctx = DdtDocumentContextBuilder(repo=repo).build_context(54)

        self.assertEqual(len(ctx["righe"]), 2)
        self.assertEqual(ctx["righe"][0]["articolo_descrizione"], "Art A")
        repo.list_righe.assert_called_once_with(54)

    # 2. In DRAFT `numero` e' NULL (assegnato a EMESSO dal trigger): il
    #    context lo propaga None, il fallback e' del template (anteprima bozza).
    def test_build_context_numero_null_in_draft(self) -> None:
        repo = MagicMock()
        testata = _testata_row()
        testata.update({
            "numero": None,
            "stato_codice_interno": "DRAFT",
            "stato_descrizione": "Bozza",
        })
        repo.get_ddt.return_value = testata
        repo.list_righe.return_value = []
        repo.list_indirizzi.return_value = []

        ctx = DdtDocumentContextBuilder(repo=repo).build_context(54)

        self.assertIsNone(ctx["ddt"]["numero"])
        self.assertEqual(ctx["ddt"]["stato"]["codice_interno"], "DRAFT")

    # 6. Slot CON presente -> `indirizzi.consegna` = snapshot congelato +
    #    display_compatto pre-composto (mirror FE formatSnapshotDisplay).
    def test_build_context_consegna_da_snapshot_con(self) -> None:
        repo = MagicMock()
        repo.get_ddt.return_value = _testata_row()
        repo.list_righe.return_value = []
        repo.list_indirizzi.return_value = [
            {
                "id": 7,
                "tipo_indirizzo_codice_interno": "CON",
                "tipo_indirizzo_descrizione": "Consegna",
                "snapshot": {
                    "via": "Via Roma 1",
                    "cap": "20100",
                    "citta": "Milano",
                    "prov": "MI",
                },
                "origine_indirizzo_id": 33,
            },
        ]

        ctx = DdtDocumentContextBuilder(repo=repo).build_context(54)

        consegna = ctx["indirizzi"]["consegna"]
        self.assertIsNotNone(consegna)
        self.assertEqual(consegna["via"], "Via Roma 1")
        self.assertEqual(
            consegna["display_compatto"], "Via Roma 1, 20100 Milano, MI",
        )
        repo.list_indirizzi.assert_called_once_with(54)

    # 7. Nessuno slot CON (anteprima in DRAFT) -> consegna None: il template
    #    omette il blocco indirizzo, nessun errore.
    def test_build_context_consegna_none_senza_slot_con(self) -> None:
        repo = MagicMock()
        repo.get_ddt.return_value = _testata_row()
        repo.list_righe.return_value = []
        repo.list_indirizzi.return_value = []

        ctx = DdtDocumentContextBuilder(repo=repo).build_context(54)

        self.assertIsNone(ctx["indirizzi"]["consegna"])


class BuildContextDdtGuardTests(SimpleTestCase):
    """Guard input + 404."""

    # 3. id non valido -> VALIDATION, no DB.
    def test_build_context_id_non_valido_raises_validation(self) -> None:
        repo = MagicMock()
        builder = DdtDocumentContextBuilder(repo=repo)
        for bad in (0, -1, True, "stringa"):
            with self.subTest(value=bad):
                with self.assertRaises(ServiceError) as ctx:
                    builder.build_context(bad)  # type: ignore[arg-type]
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.get_ddt.assert_not_called()

    # 4. DDT inesistente -> NOT_FOUND, niente list_righe.
    def test_build_context_ddt_inesistente_raises_not_found(self) -> None:
        repo = MagicMock()
        repo.get_ddt.return_value = None
        builder = DdtDocumentContextBuilder(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            builder.build_context(999)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        repo.list_righe.assert_not_called()


class BuilderCodeAndRegistryTests(SimpleTestCase):
    """Costante CODE + registrazione al boot Django."""

    # 5. Dopo l'import del modulo, il registry contiene 'DDT_VENDITA'.
    def test_registry_contiene_ddt_vendita_dopo_import_modulo(self) -> None:
        import apps.vendite.services.ddt_document_context_builder  # noqa: F401
        from apps.documenti.services.context_builders.registry import (
            get_builder,
            registered_codes,
        )

        self.assertIn("DDT_VENDITA", registered_codes())
        builder = get_builder("DDT_VENDITA")
        self.assertIsInstance(builder, DdtDocumentContextBuilder)
