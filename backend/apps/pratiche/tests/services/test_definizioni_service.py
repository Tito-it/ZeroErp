# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test service edizioni workflow (Fase 2 Slice 1a): lista + drift
#        annidato. Mock repository, nessun DB reale.
# ------------------------------------------------------------
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.pratiche.services import definizioni_service

_SVC = "apps.pratiche.services.definizioni_service"


class DefinizioniServiceTests(SimpleTestCase):
    # Scopo: il service annida i campi drift in `drift` e li rimuove dal livello
    # superiore; passa i filtri al repository.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_list_definizioni_annida_drift(self, MockRepo):
        MockRepo.return_value.list_definizioni.return_value = [
            {
                "id": 7, "tipo_prestazione_id": 9004, "stato": "PUBBLICATA",
                "emittente_fiscale_id": None,
                "versioni_indietro": None, "preset_corrente_id": None,
                "versione_preset_corrente": None,
            },
        ]
        rows = definizioni_service.list_definizioni(tipo_prestazione_id=9004)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["drift"], {
            "versioni_indietro": None,
            "preset_corrente_id": None,
            "versione_preset_corrente": None,
        })
        # I campi drift non restano sparsi al livello superiore.
        self.assertNotIn("versioni_indietro", row)
        MockRepo.return_value.list_definizioni.assert_called_once_with(
            tipo_prestazione_id=9004, emittente_fiscale_id=None,
        )

    # Scopo: drift valorizzato (edizione forkata) → annidato correttamente.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_list_definizioni_drift_valorizzato(self, MockRepo):
        MockRepo.return_value.list_definizioni.return_value = [
            {
                "id": 12, "tipo_prestazione_id": 9004, "stato": "PUBBLICATA",
                "emittente_fiscale_id": 155,
                "versioni_indietro": 2, "preset_corrente_id": 7,
                "versione_preset_corrente": 3,
            },
        ]
        rows = definizioni_service.list_definizioni(
            tipo_prestazione_id=9004, emittente_fiscale_id=155,
        )
        self.assertEqual(rows[0]["drift"]["versioni_indietro"], 2)
        self.assertEqual(rows[0]["drift"]["preset_corrente_id"], 7)

    # --- Azioni ciclo di vita (Slice 1b) ---

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_fork_definizione_ok(self, MockRepo):
        MockRepo.return_value.fork_definizione.return_value = 12
        out = definizioni_service.fork_definizione(7, 155)
        self.assertEqual(out, {"definizione_id": 12})
        MockRepo.return_value.fork_definizione.assert_called_once_with(7, 155)

    def test_fork_definizione_emittente_invalido(self):
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.fork_definizione(7, 0)
        self.assertEqual(ctx.exception.code, "E_INVALID_ID")

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_pubblica_definizione_ok(self, MockRepo):
        MockRepo.return_value.pubblica_definizione.return_value = 7
        out = definizioni_service.pubblica_definizione(7)
        self.assertEqual(out, {"definizione_id": 7})

    # Scopo: marker DB (id 511) → ServiceError parlante su pubblica non ammessa.
    @patch(f"{_SVC}.DefinizioniRepository")
    def test_pubblica_definizione_non_pubblicabile(self, MockRepo):
        from django.db import DatabaseError

        MockRepo.return_value.pubblica_definizione.side_effect = DatabaseError(
            "Definizione workflow 9 non pubblicabile: la BOZZA non ha modifiche.",
        )
        with self.assertRaises(ServiceError) as ctx:
            definizioni_service.pubblica_definizione(9)
        self.assertEqual(ctx.exception.code, "DEFINIZIONE_NON_PUBBLICABILE")

    @patch(f"{_SVC}.DefinizioniRepository")
    def test_nuova_versione_ok(self, MockRepo):
        MockRepo.return_value.nuova_versione_definizione.return_value = 20
        out = definizioni_service.nuova_versione_definizione(7)
        self.assertEqual(out, {"definizione_id": 20})
