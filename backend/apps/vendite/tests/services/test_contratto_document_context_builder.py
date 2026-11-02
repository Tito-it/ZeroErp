# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `ContrattoDocumentContextBuilder`. Mock-only su
#        `ContrattiRepository`. Verifica shape context e selezione righe
#        documentali: preview listino per modalita' A/B, righe native per
#        modalita' C.
#
# Indice test (0..N):
#   0. build_context_con_listino_usa_righe_preview
#   1. build_context_modalita_c_usa_righe_contratto
#   2. build_context_id_non_valido_raises_validation
#   3. build_context_contratto_inesistente_raises_not_found
#   4. registry_contiene_contratto_dopo_import_modulo
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.contratto_document_context_builder import (
    ContrattoDocumentContextBuilder,
)


def _testata_row(*, listino_id: int | None = 100) -> dict[str, Any]:
    return {
        "id": 7,
        "uid": "0190b000-0000-0000-0000-000000000007",
        "numero": "CNT0000007",
        "billing_account_id": 10,
        "ba_codice": "BA-10",
        "ba_ragione_sociale": "Cliente Contratto Srl",
        "istanza_utility_id": 20,
        "utility_id": 3,
        "utility_codice": "GAS",
        "utility_descrizione": "Gas",
        "ambito": "COMMODITY",
        "data": "2026-05-06",
        "valido_dal": "2026-05-01",
        "valido_al": None,
        "parent_contratto_id": None,
        "stato_doc_contratto_id": 1,
        # codice = display (mutabile), codice_interno = logica (immutabile): valori
        # DISTINTI per provare che il builder li mappa dalla colonna giusta.
        "stato_codice": "ATT",
        "stato_codice_interno": "ATTIVO",
        "stato_descrizione": "Attivo",
        "listino_id": listino_id,
        "listino_codice": "LIS-2026" if listino_id else None,
        "listino_descrizione": "Listino 2026" if listino_id else None,
        "tipo_variazione_globale": "PERCENTUALE" if listino_id else None,
        "valore_variazione_globale": "10.00" if listino_id else None,
        "categoria_cliente_id_snapshot": 1,
        "categoria_cliente_snapshot_codice": "STANDARD",
        "categoria_cliente_snapshot_descrizione": "Standard",
        "meta": {"note": "contratto demo"},
    }


class BuildContextContrattoTests(SimpleTestCase):
    """Shape context + scelta righe documento."""

    # 0. Contratto con listino: righe stampabili dalla preview listino.
    def test_build_context_con_listino_usa_righe_preview(self) -> None:
        repo = MagicMock()
        repo.get_contratto.return_value = _testata_row(listino_id=100)
        repo.list_righe.return_value = [
            {"id": 1, "articolo_descrizione": "Override contratto"},
        ]
        repo.get_utility.return_value = {"id": 5, "classe_utenza_codice": "DOM"}
        repo.list_righe_preview.return_value = [
            {"articolo_descrizione": "Canone da listino", "prezzo_finale": "90.00"},
        ]

        ctx = ContrattoDocumentContextBuilder(repo=repo).build_context(
            7, auth_user_id=9,
        )

        self.assertEqual(
            set(ctx.keys()),
            {
                "contratto",
                "cliente",
                "indirizzi",
                "utility",
                "righe",
                "righe_contratto",
                "righe_preview",
                "_meta",
            },
        )
        # Slot indirizzi SEMPRE presenti anche senza righe: garantisce al
        # template l'accesso diretto sotto StrictUndefined.
        self.assertEqual(
            ctx["indirizzi"],
            {"consegna": None, "fatturazione": None, "fornitura": None},
        )
        self.assertEqual(ctx["contratto"]["numero"], "CNT0000007")
        self.assertEqual(ctx["contratto"]["data"], "06-05-2026")
        self.assertEqual(ctx["contratto"]["data_iso"], "2026-05-06")
        self.assertEqual(ctx["contratto"]["valido_dal"], "01-05-2026")
        # Stato: codice = display ('ATT'), codice_interno = logica ('ATTIVO').
        self.assertEqual(ctx["contratto"]["stato"]["codice"], "ATT")
        self.assertEqual(ctx["contratto"]["stato"]["codice_interno"], "ATTIVO")
        self.assertEqual(ctx["contratto"]["pricing"]["modalita"], "A")
        self.assertEqual(ctx["cliente"]["denominazione"], "Cliente Contratto Srl")
        self.assertEqual(ctx["righe"], ctx["righe_preview"])
        self.assertEqual(ctx["righe"][0]["prezzo_finale"], "90,00")
        self.assertEqual(ctx["_meta"]["righe_source"], "PREVIEW_LISTINO")
        self.assertEqual(ctx["_meta"]["context_code"], "CONTRATTO")
        # La forma dei dati (`CONTEXT_VERSION`): v2 dal 2026-08-05, il blocco
        # `indirizzi`. Cambiarla vuole una versione di template che la legga.
        self.assertEqual(ctx["_meta"]["context_version"], 2)
        self.assertEqual(ctx["_meta"]["auth_user_id"], 9)
        repo.list_righe_preview.assert_called_once_with(7)

    # 1. Modalita' C: nessun listino, righe stampabili dalle righe contratto.
    def test_build_context_modalita_c_usa_righe_contratto(self) -> None:
        repo = MagicMock()
        repo.get_contratto.return_value = _testata_row(listino_id=None)
        repo.list_righe.return_value = [
            {"id": 1, "articolo_descrizione": "Riga negoziata", "prezzo_unitario": "50.00"},
        ]
        repo.get_utility.return_value = None

        ctx = ContrattoDocumentContextBuilder(repo=repo).build_context(7)

        self.assertEqual(ctx["contratto"]["pricing"]["modalita"], "C")
        self.assertEqual(ctx["righe"], ctx["righe_contratto"])
        self.assertEqual(ctx["righe"][0]["prezzo_unitario"], "50,00")
        self.assertEqual(ctx["righe_preview"], [])
        self.assertEqual(ctx["_meta"]["righe_source"], "CONTRATTI_RIGHE")
        repo.list_righe_preview.assert_not_called()


class BuildContextContrattoGuardTests(SimpleTestCase):
    """Guard input + 404."""

    # 2. id non valido -> VALIDATION, no DB.
    def test_build_context_id_non_valido_raises_validation(self) -> None:
        repo = MagicMock()
        builder = ContrattoDocumentContextBuilder(repo=repo)
        for bad in (0, -1, True, "stringa"):
            with self.subTest(value=bad):
                with self.assertRaises(ServiceError) as ctx:
                    builder.build_context(bad)  # type: ignore[arg-type]
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.get_contratto.assert_not_called()

    # 3. contratto inesistente -> NOT_FOUND, no chiamate aggiuntive.
    def test_build_context_contratto_inesistente_raises_not_found(self) -> None:
        repo = MagicMock()
        repo.get_contratto.return_value = None
        builder = ContrattoDocumentContextBuilder(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            builder.build_context(999)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        repo.list_righe.assert_not_called()
        repo.get_utility.assert_not_called()
        repo.list_righe_preview.assert_not_called()


class BuilderCodeAndRegistryTests(SimpleTestCase):
    """Costante CODE + registrazione al boot Django."""

    # 4. Dopo l'import del modulo, il registry contiene 'CONTRATTO'.
    def test_registry_contiene_contratto_dopo_import_modulo(self) -> None:
        import apps.vendite.services.contratto_document_context_builder  # noqa: F401
        from apps.documenti.services.context_builders.registry import (
            get_builder,
            registered_codes,
        )

        self.assertIn("CONTRATTO", registered_codes())
        builder = get_builder("CONTRATTO")
        self.assertIsInstance(builder, ContrattoDocumentContextBuilder)
