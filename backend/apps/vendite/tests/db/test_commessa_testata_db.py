# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il responsabile della commessa DAL DATABASE PROVVISTO: che la persona
#        sia attiva ed esista lo dice il DB, e il service traduce soltanto
#        (`aggiorna_commessa_testata`). Fino al 2026-11-07 il service lo
#        anticipava con una lettura sua, perche' il require sul figlio
#        rispondeva `E_ATTIVO_REQUIRE` (TECNICO, 500); dal giro 3 di
#        brief-db-revisione-dbops (D46) risponde `E_ATTIVO_PADRE_NON_ATTIVO`
#        (CONFLITTO_STATO) con la colonna nel campo, e la lettura si e'
#        ritirata (BE3). E' la giuntura Python<->PL/pgSQL che i mock non vedono.
# Note: ⚠️ Il require e' un constraint trigger DIFFERITO al commit: in una
#       transazione annullata non scatterebbe mai. Il test lo porta a fine
#       istruzione con `SET CONSTRAINTS ALL IMMEDIATE`, che e' quello che
#       succede in produzione, dove il backend va in autocommit
#       (`ATOMIC_REQUESTS` spento). Opt-in `ZEROERP_TEST_DB_E2E=1`.
#       ⚠️ Le REGOLE del guard le prova il pgTAP
#       `dbops/test-guard-attivo-grammatica-e-codici-v1`.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) CommessaTestataDbTests.test_responsabile_disattivato — E_ATTIVO_PADRE_NON_ATTIVO, 409, campo responsabile_risorsa_umana_id
2) CommessaTestataDbTests.test_responsabile_inesistente — la FK: E_VENDITE_FK col campo
3) CommessaTestataDbTests.test_responsabile_attivo_si_scrive — il caso buono, dal DB
"""
from __future__ import annotations

import unittest
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.services.commesse_service import aggiorna_commessa_testata


class CommessaTestataDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda sul codice che il test aspetta: un DB indietro rispetto al
        # giro 3 risponderebbe ancora `E_ATTIVO_REQUIRE`, e fallirebbe
        # sull'attesa invece che sul prerequisito.
        richiedi_db_provvisto("dbops.trgfn_child_requires_active_parent()")
        with connection.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM config.codici_errore WHERE codice = 'E_ATTIVO_PADRE_NON_ATTIVO'",
            )
            if cur.fetchone() is None:
                raise unittest.SkipTest("DB senza E_ATTIVO_PADRE_NON_ATTIVO (giro 3 dbops)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        # La persona prima della commessa: il builder dell'operatore non apre
        # il contesto, quello della commessa si' (sul suo operatore).
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('testata commessa')")
            persona = row_to_dict(cur)
            cur.execute("SELECT * FROM dbops.fn_pgtap_crea_commessa('testata commessa')")
            commessa = row_to_dict(cur)
        assert persona is not None and commessa is not None
        self.risorsa_umana_id = int(persona["risorsa_umana_id"])
        self.identita_id = int(persona["identita_id"])
        self.commessa_id = int(commessa["commessa_id"])

    def _immediati(self) -> None:
        with connection.cursor() as cur:
            cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

    # I figli prima del padre: l'identita' operatore della persona si spegne
    # prima della risorsa umana (`E_RISORSA_UMANA_IDENTITA_ATTIVA`).
    def _disattiva_persona(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = %s",
                [self.identita_id],
            )
            cur.execute(
                "UPDATE anagrafiche.risorse_umane SET attivo = false WHERE id = %s",
                [self.risorsa_umana_id],
            )

    def _responsabile(self) -> Any:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT responsabile_risorsa_umana_id FROM vendite.commesse WHERE id = %s",
                [self.commessa_id],
            )
            return cur.fetchone()[0]

    def _rifiuto(self, responsabile_id: int) -> ServiceError:
        self._immediati()
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            aggiorna_commessa_testata(
                self.commessa_id, {"responsabile_risorsa_umana_id": responsabile_id},
            )
        return cm.exception

    def test_responsabile_disattivato(self) -> None:
        self._disattiva_persona()
        errore = self._rifiuto(self.risorsa_umana_id)
        self.assertEqual(errore.code, "E_ATTIVO_PADRE_NON_ATTIVO")
        self.assertEqual(ErrorPolicyRegistry.resolve(errore.code).http_status, 409)
        self.assertIn("responsabile_risorsa_umana_id", errore.fields or ())
        self.assertIsNone(self._responsabile())

    def test_responsabile_inesistente(self) -> None:
        with connection.cursor() as cur:
            cur.execute("SELECT coalesce(max(id), 0) + 1000 FROM anagrafiche.risorse_umane")
            inesistente = int(cur.fetchone()[0])
        errore = self._rifiuto(inesistente)
        self.assertEqual(errore.code, "E_VENDITE_FK")
        self.assertEqual(errore.context.get("field"), "responsabile_risorsa_umana_id")

    def test_responsabile_attivo_si_scrive(self) -> None:
        self._immediati()
        aggiorna_commessa_testata(
            self.commessa_id, {"responsabile_risorsa_umana_id": self.risorsa_umana_id},
        )
        self.assertEqual(self._responsabile(), self.risorsa_umana_id)
