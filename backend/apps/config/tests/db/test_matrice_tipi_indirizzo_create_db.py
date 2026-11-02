# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `TipiRuoloTipiIndirizzoRepository.create_matrice` sul BB
#        `execute_dynamic_insert` (2026-09-26), sul DATABASE VERO:
#        `valido_dal` arriva dall'espressione letterale `CURRENT_DATE` e gli
#        opzionali None si omettono (DEFAULT della colonna), come prima.
# Note: ⚠️ Il mondo si COSTRUISCE: un tipo ruolo e un tipo indirizzo NUOVI,
#       cosi' la coppia e' libera per costruzione e non per fortuna. Tutto in
#       transazione ANNULLATA. Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) CreateMatriceDbTests.test_valido_dal_oggi_e_default_sugli_omessi
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.tests.db_e2e import Annulla, apri_contesto_operatore, richiedi_db_provvisto


class CreateMatriceDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto()

    def test_valido_dal_oggi_e_default_sugli_omessi(self):
        from apps.config.db.tipi_ruolo_tipi_indirizzo_repository import (
            TipiRuoloTipiIndirizzoRepository,
        )

        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute(
                    "INSERT INTO config.tipi_ruoli (codice, descrizione, codice_interno)"
                    " VALUES ('SCRMTR', 'Ruolo scrittura BB', 'SCRMTR') RETURNING id"
                )
                tipo_ruolo_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO config.tipi_indirizzi (codice, descrizione, codice_interno)"
                    " VALUES ('SCRMTI', 'Indirizzo scrittura BB', 'SCRMTI') RETURNING id"
                )
                tipo_indirizzo_id = cur.fetchone()[0]

                nuovo_id = TipiRuoloTipiIndirizzoRepository().create_matrice(
                    tipo_ruolo_id=tipo_ruolo_id, tipo_indirizzo_id=tipo_indirizzo_id,
                )
                cur.execute(
                    """
                    SELECT valido_dal = script.fn_data_operativa(), valido_al, obbligatorio, attivo,
                           fallback_tipo_indirizzo_id
                      FROM config.tipi_ruolo_tipi_indirizzo WHERE id = %s
                    """,
                    [nuovo_id],
                )
                # obbligatorio/attivo None -> omessi -> DEFAULT false/true.
                self.assertEqual(cur.fetchone(), (True, None, False, True, None))
                raise Annulla
        except Annulla:
            pass
