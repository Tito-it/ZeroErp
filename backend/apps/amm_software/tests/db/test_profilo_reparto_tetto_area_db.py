# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `limitata_da_area` delle azioni del profilo di reparto sul DB vero
#        (2026-10-31, decisione Tid «sola regola DB»): la lettura del profilo
#        chiama `script.fn_area_consente_azione` sul livello che la SUA area ha
#        nello stesso profilo. I test dell'API mockano il repository e non
#        vedono ne' la funzione ne' il LEFT JOIN sull'area.
#
# ⚠️ CASI COSTRUITI in una transazione SEMPRE annullata: il reparto lo crea il
#    test, nel contesto operatore (RLS). ⭐ I casi NON dipendono dal minimo che
#    il catalogo assegna oggi all'azione: BLOCCATO non consente niente (il
#    CHECK vieta un minimo BLOCCATO), TUTTO consente tutto, NULL vale no.
#
# Indice test (opt-in `ZEROERP_TEST_DB_E2E=1`):
#   1. area BLOCCATA → limitata; area TUTTO → no; area assente dal profilo →
#      limitata (fail-closed); azione non abilitata → mai limitata
# ------------------------------------------------------------

from __future__ import annotations

from unittest import TestCase

from django.db import connection, transaction

from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.core.tests.db_e2e import Annulla, apri_contesto_operatore, richiedi_db_provvisto


class ProfiloRepartoTettoAreaDbTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def test_limitata_da_area_viene_dalla_regola_del_db(self):
        repo = AmmSoftwareRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                apri_contesto_operatore(cur)
                cur.execute(
                    "INSERT INTO config.unita_organizzative (codice, codice_interno, descrizione) "
                    "VALUES ('T3TETTO', 'T3TETTO', 'Reparto tetto d''area') RETURNING id"
                )
                uo_id = cur.fetchone()[0]
                cur.execute(
                    "SELECT id, area_id FROM config.azioni_processo "
                    "WHERE attivo ORDER BY id LIMIT 1"
                )
                azione_id, area_id = cur.fetchone()

                def limitata(aree, abilitata=True):
                    repo.put_profilo_reparto(
                        uo_id, aree, [{"azione_id": azione_id, "abilitata": abilitata}],
                    )
                    azioni = repo.get_profilo_reparto(uo_id)["azioni"]
                    return next(a for a in azioni if a["azione_id"] == azione_id)["limitata_da_area"]

                self.assertTrue(limitata([{"area_id": area_id, "livello": "BLOCCATO"}]))
                self.assertFalse(limitata([{"area_id": area_id, "livello": "TUTTO"}]))
                # L'area non c'e' nel profilo: NULL alla funzione, che dice «no».
                self.assertTrue(limitata([]))
                # Non abilitata: non c'e' niente da limitare.
                self.assertFalse(limitata([{"area_id": area_id, "livello": "BLOCCATO"}], abilitata=False))
                raise Annulla
        except Annulla:
            pass
