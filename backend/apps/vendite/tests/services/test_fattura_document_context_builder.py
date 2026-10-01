# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit `FatturaDocumentContextBuilder` (stampa/ristampa fattura).
#        Mock-only su `VenditeRepository` (testata, riepilogo, scadenze) e
#        `FattureRepository` (righe). Verifica shape context (fattura +
#        cliente + righe + riepilogo IVA), formattazione date, guard id + 404,
#        registrazione registry.
#        ⭐ Forma 2 dal 2026-09-30: righe di primo livello dalla lista
#        (`list_righe`), i componenti esposti di un kit DENTRO la riga.
#
# Indice test (0..N):
#   0. build_context_shape_e_campi
#   1. build_context_righe_propagate
#   1-bis. build_context_righe_chiavi_di_contratto
#   1-ter. build_context_kit_porta_i_componenti_dentro (2026-09-30)
#   2. build_context_riepilogo_iva_propagate
#   3. build_context_id_non_valido_raises_validation
#   4. build_context_fattura_inesistente_raises_not_found
#   5. registry_contiene_fattura_dopo_import_modulo
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.fattura_document_context_builder import (
    FatturaDocumentContextBuilder,
)


def _testata_row() -> dict[str, Any]:
    """Riga gemella di `VenditeRepository.get_fattura_testata`."""
    return {
        "id": 42,
        "uid": "0190b000-0000-0000-0000-000000000042",
        "anno": 2026,
        "serie": "A",
        "numero": 137,
        "data": "2026-06-30",
        "data_contabilizzazione": "2026-06-30",
        "tipo_doc_fiscale_id": 1,
        "tipo_doc_fiscale_codice": "TD01",
        "tipo_doc_fiscale_descrizione": "Fattura",
        "stato_doc_fiscale_id": 3,
        "stato_codice_interno": "EMESSA",
        "stato_descrizione": "Emessa",
        "emittente_soggetto_ruolo_id": 88,
        "emittente_fiscale_id": 11,
        "emittente_fiscale_codice": "EF-11",
        "emittente_denominazione": "Emittente Demo SpA",
        "emittente_piva": "IT09876543210",
        "emittente_cf": "MTTMHL80A01H501X",
        "emittente_sede": "Via Roma 1, 20100 Milano MI",
        "utility_codice": "BASE",
        "utility_descrizione": "Servizio Base",
        "cliente_indirizzo": "Corso Test 12, 00100 Roma RM",
        "billing_account_id": 10,
        "ba_codice": "BA-10",
        "cliente_soggetto_ruolo_id": 50,
        "soggetto_id": 40,
        "ragione_sociale_completa": "Cliente Fattura Srl",
        "id_fiscale_univoco_cf_piva": "IT01234567890",
        "valuta_id": 1,
        "valuta_codice": "EUR",
        "tasso_cambio": "1",
        "imponibile_tot": "100.00",
        "imposta_tot": "22.00",
        "bollo_applicato": False,
        "bollo_importo": None,
        "arrotondamento_attuale": "0.00",
        "totale_doc": "122.00",
        "totale_a_pagare": "122.00",
        "meta": {"note": "fattura demo"},
    }


# Scopo: il builder coi due repository finti; `righe` = cio' che la lettura
#        completa della lista restituisce. Torna (builder, repo, righe_repo).
def _builder(righe: list[dict[str, Any]] | None = None):
    repo = MagicMock()
    repo.get_fattura_testata.return_value = _testata_row()
    repo.list_fattura_riepilogo_iva.return_value = []
    repo.list_fattura_scadenze.return_value = []
    righe_repo = MagicMock()
    righe_repo.list_righe.return_value = righe or []
    return FatturaDocumentContextBuilder(repo=repo, righe_repo=righe_repo), repo, righe_repo


class BuildContextFatturaTests(SimpleTestCase):
    """Shape context + formattazione."""

    # 0. Shape stabile + campi denormalizzati + date formattate IT/ISO.
    def test_build_context_shape_e_campi(self) -> None:
        builder, _, _ = _builder()
        ctx = builder.build_context(42, auth_user_id=9)

        self.assertEqual(
            set(ctx.keys()),
            {"fattura", "cliente", "righe", "riepilogo_iva", "scadenze", "_meta"},
        )
        fattura = ctx["fattura"]
        self.assertEqual(fattura["numero"], 137)
        self.assertEqual(fattura["serie"], "A")
        self.assertEqual(fattura["anno"], 2026)
        self.assertEqual(fattura["data"], "30-06-2026")
        self.assertEqual(fattura["data_iso"], "2026-06-30")
        self.assertEqual(fattura["tipo_doc"]["codice_interno"], "TD01")
        self.assertEqual(fattura["stato"]["codice_interno"], "EMESSA")
        # Emittente arricchito (intestazione fattura, C-9): denominazione + P.IVA + CF.
        self.assertEqual(fattura["emittente"]["id"], 11)
        self.assertEqual(fattura["emittente"]["codice"], "EF-11")
        self.assertEqual(fattura["emittente"]["denominazione"], "Emittente Demo SpA")
        self.assertEqual(fattura["emittente"]["piva"], "IT09876543210")
        self.assertEqual(fattura["emittente"]["cf"], "MTTMHL80A01H501X")
        self.assertEqual(fattura["emittente"]["sede"], "Via Roma 1, 20100 Milano MI")
        self.assertEqual(fattura["utility"]["codice"], "BASE")
        self.assertEqual(fattura["utility"]["descrizione"], "Servizio Base")
        self.assertEqual(fattura["bollo_applicato"], False)
        self.assertEqual(fattura["totali"]["imponibile"], "100,00")
        self.assertEqual(fattura["totali"]["imposta"], "22,00")
        self.assertEqual(fattura["totali"]["iva"], "22,00")  # alias template
        self.assertEqual(fattura["totali"]["documento"], "122,00")
        self.assertEqual(fattura["totali"]["a_pagare"], "122,00")
        self.assertEqual(fattura["totali"]["valuta_codice"], "EUR")
        # Chiavi «ricche» sempre presenti (StrictUndefined), None se non sorgentate.
        for k in ("origine", "pagamento", "utility"):
            self.assertIn(k, fattura)

        cliente = ctx["cliente"]
        self.assertEqual(cliente["denominazione"], "Cliente Fattura Srl")
        self.assertEqual(cliente["id_fiscale"], "IT01234567890")
        self.assertEqual(cliente["ba_codice"], "BA-10")
        self.assertEqual(cliente["soggetto_ruolo_id"], 50)
        self.assertEqual(cliente["indirizzo"], "Corso Test 12, 00100 Roma RM")

        self.assertEqual(ctx["_meta"]["context_code"], "FATTURA")
        # Forma 2 dal 2026-09-30: righe di primo livello, kit coi componenti
        # dentro. Pubblicare/stampare vuole una versione di template che la legga.
        self.assertEqual(ctx["_meta"]["context_version"], 2)
        self.assertEqual(ctx["_meta"]["auth_user_id"], 9)
        self.assertEqual(ctx["_meta"]["locale"], "it-IT")

    # 1. Le righe del repo passano intatte nel context, con i nomi di CONTRATTO
    #    condivisi con ordini/DDT/preventivi (`quantita`, `importo_riga`).
    #    Fino al 2026-07-28 il repo esponeva `qta`/`imponibile_riga` mentre il
    #    template leggeva `quantita`/`importo_riga`: `.get()` disinnesca
    #    StrictUndefined, quindi il PDF stampava `-` senza alcun errore.
    def test_build_context_righe_propagate(self) -> None:
        builder, _, righe_repo = _builder([
            {
                "riga_key": "R:1", "articolo_descrizione": "Art A",
                "quantita": "2", "prezzo_unitario": "10.00",
                "sconto_percentuale": "0.00", "importo_riga": "20.00",
                "componenti": None,
            },
            {
                "riga_key": "R:2", "articolo_descrizione": "Art B",
                "quantita": "1", "prezzo_unitario": "5.00",
                "sconto_percentuale": "0.00", "importo_riga": "5.00",
                "componenti": None,
            },
        ])

        ctx = builder.build_context(42)

        self.assertEqual(len(ctx["righe"]), 2)
        self.assertEqual(ctx["righe"][0]["articolo_descrizione"], "Art A")
        self.assertEqual(ctx["righe"][0]["importo_riga"], "20,00")
        # Fuori da un kit la lista c'e' ed e' vuota: il template la scorre
        # senza chiedersi se esiste.
        self.assertEqual(ctx["righe"][0]["componenti"], [])
        righe_repo.list_righe.assert_called_once_with(42)

    # 1-bis. Il template legge queste chiavi con `.get()`: se cambiano nome non
    #        c'e' errore, c'e' un trattino. Il contratto va asserito qui.
    def test_build_context_righe_chiavi_di_contratto(self) -> None:
        builder, _, _ = _builder([
            {
                "riga_key": "R:1", "riga_nr": 1, "descrizione": "Riga",
                "uom_codice": "PZ", "iva_codice": "22",
                "quantita": "2", "prezzo_unitario": "10.00",
                "sconto_percentuale": "0.00", "importo_riga": "20.00",
                "componenti": None,
            },
        ])

        riga = builder.build_context(42)["righe"][0]

        for chiave in ("quantita", "prezzo_unitario", "sconto_percentuale", "importo_riga"):
            self.assertIn(chiave, riga, f"chiave di contratto mancante: {chiave}")
        # Rimosse dal modello il 2026-07-28 (D1-ter): l'imposta di riga non e'
        # un concetto italiano e l'IVA e' governata per aggregato.
        for chiave in ("imposta_riga", "totale_riga"):
            self.assertNotIn(chiave, riga)

    # 1-ter. Forma 2: il kit e' UNA riga col totale, e i suoi componenti
    #        esposti stanno DENTRO (`componenti`, lista di dict con la
    #        quantita' formattata). Il repository li consegna gia' decodificati
    #        (`_righe_jsonb`, provato in test_righe_fattura_lista). Nessuna riga
    #        KIT_COMPONENTE di primo livello.
    def test_build_context_kit_porta_i_componenti_dentro(self) -> None:
        builder, _, _ = _builder([
            {
                "riga_key": "K:42:abc", "tipo_riga": "KIT_PADRE", "riga_nr": 3,
                "descrizione": "Kit", "quantita": "1.000000",
                "importo_riga": "150.000000", "componenti_numero": 2,
                "componenti": [
                    {"riga_nr": 4, "descrizione": "Pezzo A", "quantita": 2.000000,
                     "uom_codice": "PZ", "articolo_codice": "A"},
                    {"riga_nr": 5, "descrizione": "Pezzo B", "quantita": 1.5,
                     "uom_codice": "KG", "articolo_codice": "B"},
                ],
            },
        ])

        righe = builder.build_context(42)["righe"]

        self.assertEqual(len(righe), 1)
        kit = righe[0]
        self.assertEqual(kit["importo_riga"], "150,00")
        self.assertEqual([c["descrizione"] for c in kit["componenti"]], ["Pezzo A", "Pezzo B"])
        self.assertEqual([c["quantita"] for c in kit["componenti"]], ["2,00", "1,50"])
        self.assertNotIn("KIT_COMPONENTE", [r.get("tipo_riga") for r in righe])

    # 2. Il riepilogo IVA (tabella reale) passa intatto nel context.
    def test_build_context_riepilogo_iva_propagate(self) -> None:
        builder, repo, _ = _builder()
        repo.list_fattura_riepilogo_iva.return_value = [
            {
                "fattura_id": 42, "iva_id": 1, "iva_codice": "22",
                "iva_aliquota": "22.00", "natura_id": None,
                "imponibile": "100.00", "imposta": "22.00",
                "arrotondamento": "0.00",
            },
        ]

        ctx = builder.build_context(42)

        self.assertEqual(len(ctx["riepilogo_iva"]), 1)
        self.assertEqual(ctx["riepilogo_iva"][0]["iva_aliquota"], "22,00")
        self.assertEqual(ctx["riepilogo_iva"][0]["imposta"], "22,00")
        repo.list_fattura_riepilogo_iva.assert_called_once_with(42)

    # 3. Le scadenze (piano pagamenti) sono shaped con chiavi stabili per il
    #    template (nr/data/importo/modalita_codice); modalita dal meta.
    def test_build_context_scadenze_shape(self) -> None:
        builder, repo, _ = _builder()
        repo.list_fattura_scadenze.return_value = [
            {
                "id": 1, "numero_rata": 1, "data_scadenza": "2026-07-31",
                "importo": "61.00", "meta": {"modalita_codice": "BONIFICO"},
            },
            {
                "id": 2, "numero_rata": 2, "data_scadenza": "2026-08-31",
                "importo": "61.00", "meta": None,
            },
        ]

        ctx = builder.build_context(42)

        self.assertEqual(len(ctx["scadenze"]), 2)
        s0 = ctx["scadenze"][0]
        self.assertEqual(s0["nr"], 1)
        self.assertEqual(s0["data"], "31-07-2026")  # formattazione IT
        self.assertEqual(s0["importo"], "61,00")
        self.assertEqual(s0["modalita_codice"], "BONIFICO")
        # meta None → modalita_codice None (nessun errore)
        self.assertIsNone(ctx["scadenze"][1]["modalita_codice"])
        repo.list_fattura_scadenze.assert_called_once_with(42)


class BuildContextFatturaGuardTests(SimpleTestCase):
    """Guard input + 404."""

    # 3. id non valido -> VALIDATION, no DB.
    def test_build_context_id_non_valido_raises_validation(self) -> None:
        builder, repo, _ = _builder()
        for bad in (0, -1, True, "stringa"):
            with self.subTest(value=bad):
                with self.assertRaises(ServiceError) as ctx:
                    builder.build_context(bad)  # type: ignore[arg-type]
                self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        repo.get_fattura_testata.assert_not_called()

    # 4. fattura inesistente -> NOT_FOUND, niente righe/riepilogo.
    def test_build_context_fattura_inesistente_raises_not_found(self) -> None:
        builder, repo, righe_repo = _builder()
        repo.get_fattura_testata.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            builder.build_context(999)
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_NOT_FOUND")
        righe_repo.list_righe.assert_not_called()
        repo.list_fattura_riepilogo_iva.assert_not_called()


class BuilderCodeAndRegistryTests(SimpleTestCase):
    """Costante CODE + registrazione al boot Django."""

    # 5. Dopo l'import del modulo, il registry contiene 'FATTURA'.
    def test_registry_contiene_fattura_dopo_import_modulo(self) -> None:
        import apps.vendite.services.fattura_document_context_builder  # noqa: F401
        from apps.documenti.services.context_builders.registry import (
            get_builder,
            registered_codes,
        )

        self.assertIn("FATTURA", registered_codes())
        builder = get_builder("FATTURA")
        self.assertIsInstance(builder, FatturaDocumentContextBuilder)
