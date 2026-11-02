# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il segno «richiede il secondo fattore» del profilo di reparto sul DB
#        vero (brief sicurezza §3.4-bis, T-3; D-T1 del brief DB TOTP): la
#        colonna `config.profili_accesso.richiede_secondo_fattore` letta e
#        scritta dal percorso del profilo di reparto. I test dell'API mockano
#        il repository e non vedono ne' il nome della colonna ne' l'upsert.
#
# ⚠️ CASI COSTRUITI in una transazione SEMPRE annullata: il reparto lo crea il
#    test, nel contesto operatore (RLS).
#
# Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`):
#   1. un reparto senza profilo legge false; acceso, si legge acceso; un PUT
#      senza il segno lo lascia com'e'; spento, si legge spento
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase

from django.db import connection, transaction

from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.core.tests.db_e2e import Annulla, apri_contesto_operatore, richiedi_db_provvisto


class ProfiloRepartoSecondoFattoreDbTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def test_il_segno_si_scrive_si_legge_e_resta_se_non_detto(self):
        repo = AmmSoftwareRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute(
                    "INSERT INTO config.unita_organizzative (codice, codice_interno, descrizione) "
                    "VALUES ('T3SECFAT', 'T3SECFAT', 'Reparto secondo fattore') RETURNING id"
                )
                uo_id = cur.fetchone()[0]

                self.assertFalse(repo.get_profilo_reparto(uo_id)["richiede_secondo_fattore"])

                repo.put_profilo_reparto(uo_id, [], [], richiede_secondo_fattore=True)
                self.assertTrue(repo.get_profilo_reparto(uo_id)["richiede_secondo_fattore"])

                # Il PUT di oggi, che non sa del segno, non lo spegne.
                repo.put_profilo_reparto(uo_id, [], [])
                self.assertTrue(repo.get_profilo_reparto(uo_id)["richiede_secondo_fattore"])

                repo.put_profilo_reparto(uo_id, [], [], richiede_secondo_fattore=False)
                self.assertFalse(repo.get_profilo_reparto(uo_id)["richiede_secondo_fattore"])
                raise Annulla
        except Annulla:
            pass
