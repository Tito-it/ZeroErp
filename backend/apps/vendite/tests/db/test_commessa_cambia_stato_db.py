# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lo stato della commessa DAL SUO VERBO sul DATABASE PROVVISTO
#        (brief-modello-documento-vendita §14.6, giro 10): il service arriva a
#        `vendite.fn_cambia_stato_commessa(id, stato)` nella firma senza
#        l'utente (C-4), l'azione della riga e' quella che la catena chiede
#        (`DocumentoModelloRepository.azione_del_passaggio`), e i rifiuti
#        arrivano al client col codice che il DB ha scelto, senza la «difesa
#        applicativa» di prima. E' la giuntura Python↔PL/pgSQL che i test del
#        service (mock) non vedono.
# Note: ⚠️ Le REGOLE del verbo (matrice, azione, porta, condizioni) le prova il
#       pgTAP `vendite/test-commessa-al-modello-v1`. La commessa si COSTRUISCE
#       (`dbops.fn_pgtap_crea_commessa`, nello stato chiesto), in transazione
#       ANNULLATA; ogni rifiuto atteso in un SAVEPOINT. Opt-in
#       `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) CommessaCambiaStatoDbTests.test_l_azione_della_riga — «riapri» e annullo fuori bozza: `cambia_stato_commessa`; annullo della bozza: nessuna (C-1)
2) CommessaCambiaStatoDbTests.test_riapri_senza_azione — E_PERMESSO_NEGATO dalla riga del passaggio
3) CommessaCambiaStatoDbTests.test_riapri_porta_ad_aperta — C-3, dal verbo nella firma nuova
4) CommessaCambiaStatoDbTests.test_lo_stato_che_ha_gia — E_DOC_GIA_NELLO_STATO
5) CommessaCambiaStatoDbTests.test_in_esecuzione_ritirato — E_STATO_WORKFLOW_NON_TROVATO (C-3)
6) CommessaCambiaStatoDbTests.test_annullo_della_bozza_senza_azione — C-1, M-4
"""
from __future__ import annotations

import unittest
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.db.documento_modello_repository import DocumentoModelloRepository
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.commesse_repository import TESTATA_COMMESSE
from apps.vendite.services.commesse_service import cambia_stato_commessa


class CommessaCambiaStatoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda sulla firma FINALE del verbo (giro 10, C-4): un DB indietro
        # fallisce sull'oggetto mancante, non su un'attesa sbagliata.
        richiedi_db_provvisto("vendite.fn_cambia_stato_commessa(bigint,character varying)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)

    # Scopo: una commessa del mondo nello stato chiesto; il builder apre il
    #        contesto sull'operatore che costruisce.
    def _commessa(self, stato: str | None = None) -> int:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM dbops.fn_pgtap_crea_commessa('cambia stato commessa', %s)", [stato],
            )
            commessa = row_to_dict(cur)
        assert commessa is not None
        self.auth_user_id = int(commessa["auth_user_id"])
        return int(commessa["commessa_id"])

    def _concedi_cambia_stato(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_concedi_azione(%s, 'cambia_stato_commessa')", [self.auth_user_id],
            )

    # ⚠️ L'operatore del builder ha gia' `cambia_stato_commessa` dal suo
    #    profilo (letto il 2026-10-27): il diniego lo scrive il test, con un
    #    override utente spento, che nella catena viene prima del profilo.
    #    `dbops` non ha un builder del diniego: prima occorrenza, resta qui.
    def _nega_cambia_stato(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO config.user_override_azioni"
                " (auth_user_id, azione_id, abilitata, motivo, valido_dal, valido_al)"
                " SELECT %s, ap.id, false, 'Fixture test Django', script.fn_data_operativa(), NULL"
                " FROM config.azioni_processo ap WHERE ap.permission_codename = 'cambia_stato_commessa'"
                " ON CONFLICT ON CONSTRAINT uq_user_override_azioni_user_azione"
                " DO UPDATE SET abilitata = false",
                [self.auth_user_id],
            )

    def _stato(self, commessa_id: int) -> str:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT s.codice_interno FROM vendite.commesse c"
                " JOIN vendite.stati_commessa s ON s.id = c.stato_commessa_id WHERE c.id = %s",
                [commessa_id],
            )
            return str(cur.fetchone()[0])

    def _rifiuto(self, chiamata: Any) -> ServiceError:
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            chiamata()
        return cm.exception

    # Il permesso che la view chiede prima della transazione e' quello della
    # riga del seed di oggi (`transizioni_stati_commessa.csv`): se Tid sposta
    # l'azione su un'altra riga cambia l'atteso, non il codice.
    def test_l_azione_della_riga(self) -> None:
        repo = DocumentoModelloRepository()
        pronta = self._commessa("PRONTA_FATTURAZIONE")
        bozza = self._commessa()
        self.assertEqual(repo.azione_del_passaggio(TESTATA_COMMESSE, pronta, "APERTA"), "cambia_stato_commessa")
        self.assertEqual(repo.azione_del_passaggio(TESTATA_COMMESSE, pronta, "ANNULLATA"), "cambia_stato_commessa")
        self.assertIsNone(repo.azione_del_passaggio(TESTATA_COMMESSE, bozza, "ANNULLATA"))

    def test_riapri_senza_azione(self) -> None:
        commessa_id = self._commessa("PRONTA_FATTURAZIONE")
        self._nega_cambia_stato()
        errore = self._rifiuto(lambda: cambia_stato_commessa(commessa_id=commessa_id, nuovo_stato="APERTA"))
        self.assertEqual(errore.code, "E_PERMESSO_NEGATO")
        self.assertEqual(self._stato(commessa_id), "PRONTA_FATTURAZIONE")

    def test_riapri_porta_ad_aperta(self) -> None:
        commessa_id = self._commessa("PRONTA_FATTURAZIONE")
        self._concedi_cambia_stato()
        out = cambia_stato_commessa(commessa_id=commessa_id, nuovo_stato="APERTA")
        self.assertEqual(out, {"commessa_id": commessa_id, "stato_da": "PRONTA_FATTURAZIONE", "stato_a": "APERTA"})
        self.assertEqual(self._stato(commessa_id), "APERTA")

    def test_lo_stato_che_ha_gia(self) -> None:
        commessa_id = self._commessa("PRONTA_FATTURAZIONE")
        self._concedi_cambia_stato()
        errore = self._rifiuto(
            lambda: cambia_stato_commessa(commessa_id=commessa_id, nuovo_stato="PRONTA_FATTURAZIONE"),
        )
        self.assertEqual(errore.code, "E_DOC_GIA_NELLO_STATO")

    # C-3: IN_ESECUZIONE e' spento nel vocabolario. Prima lo rifiutava la
    # «difesa applicativa» con un codice del backend; ora il verbo, col suo.
    def test_in_esecuzione_ritirato(self) -> None:
        commessa_id = self._commessa("PRONTA_FATTURAZIONE")
        self._concedi_cambia_stato()
        errore = self._rifiuto(
            lambda: cambia_stato_commessa(commessa_id=commessa_id, nuovo_stato="IN_ESECUZIONE"),
        )
        self.assertEqual(errore.code, "E_STATO_WORKFLOW_NON_TROVATO")
        self.assertEqual(self._stato(commessa_id), "PRONTA_FATTURAZIONE")

    # C-1: l'annullo della bozza non chiede l'azione (M-4); passa dal verbo
    # dell'annullo, senza legami da confermare.
    def test_annullo_della_bozza_senza_azione(self) -> None:
        commessa_id = self._commessa()
        self._nega_cambia_stato()
        self.assertEqual(self._stato(commessa_id), "BOZZA")
        out = cambia_stato_commessa(commessa_id=commessa_id, nuovo_stato="ANNULLATA")
        self.assertEqual(out["stato_a"], "ANNULLATA")
        self.assertEqual(self._stato(commessa_id), "ANNULLATA")
