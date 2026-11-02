# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test del BB `_campi_canone` (apps/vendite/services/_campi_canone.py):
#        i due campi del canone della testata di contratto e offerta letti in
#        una forma sola, e i loro CHECK tradotti sul campo.
# ------------------------------------------------------------
"""
Indice test:

CampiCanoneTests (unit, senza DB)
 1) test_maiuscolo_e_intero         — « fine_periodo », "2" -> FINE_PERIODO, 2
 2) test_null_e_vuoto_si_omettono   — None e '' non arrivano al DB (NOT NULL col default)
 3) test_mese_non_intero_e_400      — "febbraio" -> E_VENDITE_VALIDATION col campo
 4) test_con_campi_canone           — le altre chiavi intatte, il payload d'ingresso pure
 5) test_check_dal_nome_tabella     — chk_<tabella>_<campo> -> (codice, messaggio, campo)
 6) test_contratto_e_offerta_stessi_check — le due mappe dei service vengono dal BB
"""

from __future__ import annotations

from django.test import SimpleTestCase

from apps.core.services.payload_helpers import PayloadValidator
from apps.core.services.service_errors import ServiceError
from apps.vendite.services._campi_canone import (
    CAMPI_CANONE,
    campi_canone,
    check_campi_canone,
    con_campi_canone,
)

_V = PayloadValidator(validation_code="E_VENDITE_VALIDATION", log_to_db=False)


class CampiCanoneTests(SimpleTestCase):
    # Scopo: 1) la forma del DB: codice del CHECK in maiuscolo, mese intero.
    def test_maiuscolo_e_intero(self):
        out = campi_canone(_V, {"generazione_canone": " fine_periodo ", "mese_partenza_canone": "2"})
        self.assertEqual(out, {"generazione_canone": "FINE_PERIODO", "mese_partenza_canone": 2})

    # Scopo: 2) null e vuoto non sono un valore: la chiave si omette.
    def test_null_e_vuoto_si_omettono(self):
        self.assertEqual(campi_canone(_V, {}), {})
        self.assertEqual(
            campi_canone(_V, {"generazione_canone": "", "mese_partenza_canone": None}), {},
        )

    # Scopo: 3) un mese che non e' un intero e' un 400 col campo. Il dominio
    #        (1..12) lo dice il CHECK.
    def test_mese_non_intero_e_400(self):
        with self.assertRaises(ServiceError) as cm:
            campi_canone(_V, {"mese_partenza_canone": "febbraio"})
        self.assertEqual(cm.exception.code, "E_VENDITE_VALIDATION")
        self.assertEqual(cm.exception.context.get("field"), "mese_partenza_canone")

    # Scopo: 4) `con_campi_canone` sostituisce solo i due campi; il payload in
    #        ingresso non si modifica.
    def test_con_campi_canone(self):
        ingresso = {"meta": {"x": 1}, "generazione_canone": "inizio_periodo", "mese_partenza_canone": None}
        out = con_campi_canone(_V, ingresso)
        self.assertEqual(out, {"meta": {"x": 1}, "generazione_canone": "INIZIO_PERIODO"})
        self.assertEqual(ingresso["generazione_canone"], "inizio_periodo")

    # Scopo: 5) il nome del vincolo dalla tabella, il campo per il form.
    def test_check_dal_nome_tabella(self):
        mappa = check_campi_canone("contratti", "E_X")
        self.assertEqual(
            sorted(mappa), ["chk_contratti_generazione_canone", "chk_contratti_mese_partenza_canone"],
        )
        self.assertEqual([v[2] for v in mappa.values()], list(CAMPI_CANONE))
        self.assertTrue(all(v[0] == "E_X" for v in mappa.values()))

    # Scopo: 6) il punto della regola del 2: le due mappe dei service sono il
    #        BB, con i nomi dei loro vincoli.
    def test_contratto_e_offerta_stessi_check(self):
        from apps.vendite.services import contratti_service, offerte_service

        self.assertEqual(
            contratti_service._CHECK_CONSTRAINTS,
            check_campi_canone("contratti", "E_VENDITE_VALIDATION"),
        )
        self.assertEqual(
            offerte_service._CHECK_CONSTRAINTS,
            check_campi_canone("offerte_commerciali", "E_VENDITE_VALIDATION"),
        )
