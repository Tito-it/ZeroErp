# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `OffertaDocumentContextBuilder`. Mock-only su
#        `OfferteRepository`. Verifica shape context (testata + cliente +
#        utility + eccezioni), formattazione date/decimali e modalita'
#        pricing A/B/C.
#
# Indice test (0..N):
#   0. build_context_shape_e_modalita_a
#   1. build_context_modalita_c_senza_listino
#   2. build_context_formatta_decimali_eccezioni_e_componenti
#   2b. build_context_componenti_stringa_jsonb_deserializzati
#   2c. build_context_componenti_invalidi_lista_vuota
#   3. build_context_id_non_valido_raises_validation
#   4. build_context_offerta_inesistente_raises_not_found
#   5. registry_contiene_offerta_commerciale_dopo_import_modulo
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.offerta_document_context_builder import (
    OffertaDocumentContextBuilder,
)


def _testata_row(*, listino_id: int | None = 100) -> dict[str, Any]:
    return {
        "id": 7,
        "uid": "0190b000-0000-0000-0000-000000000007",
        "codice": "OFC0000007",
        "emittente_fiscale_id": 3,
        "emittente_fiscale_codice": "EF-3",
        "emittente_ragione_sociale": "Azienda Emittente Spa",
        "billing_account_id": 10,
        "ba_codice": "BA-10",
        "billing_account_display": "Cliente Offerta Srl",
        "id_fiscale": "IT01234567890",
        "istanza_utility_id": 20,
        "utility_id": 3,
        "utility_codice": "GAS",
        "utility_display": "Gas",
        "listino_id": listino_id,
        "listino_codice": "LIS-2026" if listino_id else None,
        "listino_descrizione": "Listino 2026" if listino_id else None,
        "listino_versione_id": 55 if listino_id else None,
        "listino_versione_codice": "V1" if listino_id else None,
        "tipo_variazione_globale": "PERCENTUALE" if listino_id else None,
        "valore_variazione_globale": "10.00" if listino_id else None,
        "stato_doc_offerta_id": 2,
        "stato_codice_interno": "EMESSA",
        "stato_descrizione": "Emessa",
        "revisione_numero": 1,
        "revisione_padre_id": None,
        "data_emissione": "2026-05-27",
        "data_accettazione": None,
        "data_rifiuto": None,
        "data_annullamento": None,
        "motivazione_rifiuto": None,
        "validita_dal": "2026-05-01",
        "validita_al": "2026-06-30",
        "contratto_id": None,
        "contratto_numero": None,
        "meta": {"note": "offerta demo"},
    }


class BuildContextOffertaTests(SimpleTestCase):
    """Shape context + modalita' pricing + formattazione."""

    # 0. Offerta con listino + variazione globale -> modalita' A; shape stabile.
    def test_build_context_shape_e_modalita_a(self) -> None:
        repo = MagicMock()
        repo.get_offerta.return_value = _testata_row(listino_id=100)
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = {"id": 5, "classe_utenza_codice": "DOM"}

        ctx = OffertaDocumentContextBuilder(repo=repo).build_context(
            7, auth_user_id=9,
        )

        self.assertEqual(
            set(ctx.keys()),
            {"offerta", "cliente", "indirizzi", "utility", "eccezioni", "_meta"},
        )
        # Slot indirizzi SEMPRE presenti anche senza righe: garantisce al
        # template l'accesso diretto sotto StrictUndefined.
        self.assertEqual(
            ctx["indirizzi"],
            {"consegna": None, "fatturazione": None, "fornitura": None,
             "residenza": None},
        )
        self.assertEqual(ctx["offerta"]["codice"], "OFC0000007")
        self.assertEqual(ctx["offerta"]["data_emissione"], "27-05-2026")
        self.assertEqual(ctx["offerta"]["data_emissione_iso"], "2026-05-27")
        self.assertEqual(ctx["offerta"]["validita_dal"], "01-05-2026")
        self.assertEqual(ctx["offerta"]["validita_al"], "30-06-2026")
        self.assertEqual(ctx["offerta"]["pricing"]["modalita"], "A")
        self.assertEqual(
            ctx["offerta"]["pricing"]["valore_variazione_globale"], "10,00",
        )
        self.assertEqual(ctx["offerta"]["stato"]["codice"], "EMESSA")
        self.assertEqual(ctx["offerta"]["emittente_fiscale"]["codice"], "EF-3")
        self.assertEqual(ctx["cliente"]["denominazione"], "Cliente Offerta Srl")
        self.assertEqual(ctx["cliente"]["id_fiscale"], "IT01234567890")
        self.assertEqual(ctx["_meta"]["context_code"], "OFFERTA_COMMERCIALE")
        # La forma dei dati (`CONTEXT_VERSION`): v2 dal 2026-08-05, il blocco
        # `indirizzi`. Cambiarla vuole una versione di template che la legga.
        self.assertEqual(ctx["_meta"]["context_version"], 2)
        self.assertEqual(ctx["_meta"]["righe_source"], "OFFERTE_ECCEZIONI")
        self.assertEqual(ctx["_meta"]["auth_user_id"], 9)

    # 1. Senza listino -> modalita' C.
    def test_build_context_modalita_c_senza_listino(self) -> None:
        repo = MagicMock()
        repo.get_offerta.return_value = _testata_row(listino_id=None)
        repo.list_eccezioni.return_value = []
        repo.get_utility.return_value = None

        ctx = OffertaDocumentContextBuilder(repo=repo).build_context(7)

        self.assertEqual(ctx["offerta"]["pricing"]["modalita"], "C")
        self.assertIsNone(ctx["offerta"]["listino"]["id"])
        self.assertEqual(ctx["eccezioni"], [])

    # 2. Decimali eccezioni + componenti BoM annidati formattati a 6 cifre.
    def test_build_context_formatta_decimali_eccezioni_e_componenti(self) -> None:
        repo = MagicMock()
        repo.get_offerta.return_value = _testata_row(listino_id=100)
        repo.list_eccezioni.return_value = [
            {
                "id": 1,
                "articolo_descrizione": "Articolo composito",
                "tipo_eccezione": "OVERRIDE",
                "prezzo_unitario": "12.5",
                "quantita": "2",
                "qta_operativa": "2",
                "componenti": [
                    {
                        "id": 11,
                        "componente_descrizione": "Componente A",
                        "prezzo_unitario": "5.25",
                        "quantita": "1",
                        "coeff_qta_snapshot": "1",
                    },
                ],
            },
        ]
        repo.get_utility.return_value = None

        ctx = OffertaDocumentContextBuilder(repo=repo).build_context(7)

        riga = ctx["eccezioni"][0]
        self.assertEqual(riga["prezzo_unitario"], "12,50")
        self.assertEqual(riga["quantita"], "2,00")
        comp = riga["componenti"][0]
        self.assertEqual(comp["prezzo_unitario"], "5,25")
        self.assertEqual(comp["coeff_qta_snapshot"], "1,00")

    # 2b. componenti come stringa JSON (psycopg/jsonb_agg) -> deserializzati
    #     in lista di dict, prezzi formattati. Senza questa coercion il
    #     template Jinja itererebbe sui caratteri ('str object has no
    #     attribute "get"' a runtime). Pattern speculare al FE
    #     `coerceJsonbToArray`.
    def test_build_context_componenti_stringa_jsonb_deserializzati(self) -> None:
        repo = MagicMock()
        repo.get_offerta.return_value = _testata_row(listino_id=100)
        repo.list_eccezioni.return_value = [
            {
                "id": 1,
                "articolo_descrizione": "Articolo composito",
                "tipo_eccezione": "OVERRIDE",
                "prezzo_unitario": "10",
                "componenti": (
                    '[{"componente_descrizione": "C1", '
                    '"prezzo_unitario": "1.5", "quantita": "2"}]'
                ),
            },
        ]
        repo.get_utility.return_value = None

        ctx = OffertaDocumentContextBuilder(repo=repo).build_context(7)

        riga = ctx["eccezioni"][0]
        self.assertIsInstance(riga["componenti"], list)
        self.assertEqual(len(riga["componenti"]), 1)
        comp = riga["componenti"][0]
        self.assertEqual(comp["componente_descrizione"], "C1")
        self.assertEqual(comp["prezzo_unitario"], "1,50")
        self.assertEqual(comp["quantita"], "2,00")

    # 2c. componenti nullo / stringa vuota / JSON invalido -> lista vuota
    #     (no crash). Garantisce che il template non rompa con eccezioni
    #     non-composite o blob inattesi.
    def test_build_context_componenti_invalidi_lista_vuota(self) -> None:
        repo = MagicMock()
        repo.get_offerta.return_value = _testata_row(listino_id=100)
        repo.list_eccezioni.return_value = [
            {"id": 1, "tipo_eccezione": "OVERRIDE", "componenti": None},
            {"id": 2, "tipo_eccezione": "OVERRIDE", "componenti": ""},
            {"id": 3, "tipo_eccezione": "OVERRIDE", "componenti": "non-json-{"},
            {"id": 4, "tipo_eccezione": "OVERRIDE"},  # campo assente
        ]
        repo.get_utility.return_value = None

        ctx = OffertaDocumentContextBuilder(repo=repo).build_context(7)
        for riga in ctx["eccezioni"]:
            self.assertEqual(riga["componenti"], [])


class BuildContextOffertaGuardTests(SimpleTestCase):
    """Guard input + 404."""

    # 3. id non valido -> VALIDATION, no DB.
    def test_build_context_id_non_valido_raises_validation(self) -> None:
        repo = MagicMock()
        builder = OffertaDocumentContextBuilder(repo=repo)
        for bad in (0, -1, True, "stringa"):
            with self.subTest(value=bad):
                with self.assertRaises(ServiceError) as ctx:
                    builder.build_context(bad)  # type: ignore[arg-type]
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.get_offerta.assert_not_called()

    # 4. offerta inesistente -> NOT_FOUND, no chiamate aggiuntive.
    def test_build_context_offerta_inesistente_raises_not_found(self) -> None:
        repo = MagicMock()
        repo.get_offerta.return_value = None
        builder = OffertaDocumentContextBuilder(repo=repo)
        with self.assertRaises(ServiceError) as ctx:
            builder.build_context(999)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        repo.list_eccezioni.assert_not_called()
        repo.get_utility.assert_not_called()


class BuilderCodeAndRegistryTests(SimpleTestCase):
    """Costante CODE + registrazione al boot Django."""

    # 5. Dopo l'import del modulo, il registry contiene 'OFFERTA_COMMERCIALE'.
    def test_registry_contiene_offerta_commerciale_dopo_import_modulo(self) -> None:
        import apps.vendite.services.offerta_document_context_builder  # noqa: F401
        from apps.documenti.services.context_builders.registry import (
            get_builder,
            registered_codes,
        )

        self.assertIn("OFFERTA_COMMERCIALE", registered_codes())
        builder = get_builder("OFFERTA_COMMERCIALE")
        self.assertIsInstance(builder, OffertaDocumentContextBuilder)
