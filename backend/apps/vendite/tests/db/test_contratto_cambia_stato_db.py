# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lo stato del contratto DAI SUOI VERBI sul DATABASE PROVVISTO
#        (brief-modello-documento-vendita §11.6, giro 8): «Emetti» arriva a
#        `vendite.fn_cambia_stato_contratto`, la cessazione a
#        `vendite.fn_cessa_contratto` con la sua data, e i rifiuti arrivano al
#        client col codice che il DB ha scelto. E' la giuntura Python↔PL/pgSQL
#        che i test del service (mock) non vedono: firme, ritorno di
#        `programmata`, la porta che rifiuta l'UPDATE diretto.
# Note: ⚠️ Le REGOLE dei verbi (matrice, azione, porta, date) le prova il pgTAP
#       `vendite/test-contratto-al-modello-v1`. Il mondo si COSTRUISCE
#       (emittente e operatore, un cliente, un listino della sua utility), in
#       transazione ANNULLATA; ogni rifiuto atteso in un SAVEPOINT. Opt-in
#       `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ContrattoCambiaStatoDbTests.test_emetti_dal_verbo
2) ContrattoCambiaStatoDbTests.test_emetti_senza_azione — E_PERMESSO_NEGATO dalla riga del passaggio
3) ContrattoCambiaStatoDbTests.test_il_secondo_emetti_e_rifiutato — E_DOC_GIA_NELLO_STATO
4) ContrattoCambiaStatoDbTests.test_cessazione_di_oggi_e_immediata
5) ContrattoCambiaStatoDbTests.test_cessazione_futura_e_programmata
6) ContrattoCambiaStatoDbTests.test_i_rifiuti_della_cessazione_hanno_il_codice_del_db
7) ContrattoCambiaStatoDbTests.test_annullo_della_bozza_senza_azione — M-4
"""
from __future__ import annotations

import unittest
from datetime import date, timedelta
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.services.contratti_service import ContrattiService


class ContrattoCambiaStatoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda sulla firma FINALE del verbo della cessazione (giro 8): il
        # verbo di stato nasce nello stesso giro.
        richiedi_db_provvisto("vendite.fn_cessa_contratto(bigint,date)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore()")
            mondo = row_to_dict(cur)
            assert mondo is not None
            cur.execute("SELECT script.fn_pgtap_set_contesto_operatore(%s)", [mondo["auth_user_id"]])
            cur.execute("SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('cambia stato contratto')")
            cliente = row_to_dict(cur)
            assert cliente is not None
            cur.execute(
                "SELECT listino_id FROM dbops.fn_pgtap_crea_listino(%s, 'cambia stato contratto')",
                [cliente["utility_id"]],
            )
            listino_id = cur.fetchone()[0]
            # Il «giorno» dei verbi e' la data operativa del DB, non l'orologio
            # del test.
            cur.execute("SELECT script.fn_data_operativa()")
            self.oggi: date = cur.fetchone()[0]
        self.auth_user_id = mondo["auth_user_id"]
        self.servizio = ContrattiService()
        c = cliente
        self.contratto_id = int(self.servizio.create_contratto({
            "billing_account_id": c["billing_account_id"],
            "istanza_utility_id": c["istanza_utility_id"],
            "utility_id": c["utility_id"],
            "emittente_fiscale_id": mondo["emittente_fiscale_id"],
            "listino_id": listino_id,
            "valido_dal": (self.oggi - timedelta(days=30)).isoformat(),
        })["id"])

    def _concedi_emetti_contratto(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_concedi_azione(%s, 'emetti_contratto')", [self.auth_user_id],
            )

    def _stato(self) -> tuple[str, date | None]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT s.codice_interno, c.valido_al FROM vendite.contratti c"
                " JOIN config.stati_doc_contratti s ON s.id = c.stato_doc_contratto_id"
                " WHERE c.id = %s",
                [self.contratto_id],
            )
            codice, valido_al = cur.fetchone()
        return str(codice), valido_al

    def _rifiuto(self, chiamata: Any) -> ServiceError:
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            chiamata()
        return cm.exception

    def test_emetti_dal_verbo(self) -> None:
        self._concedi_emetti_contratto()
        out = self.servizio.emetti(self.contratto_id)
        self.assertEqual(out["stato_codice_interno"], "ATTIVO")
        self.assertEqual(self._stato()[0], "ATTIVO")

    def test_emetti_senza_azione(self) -> None:
        errore = self._rifiuto(lambda: self.servizio.emetti(self.contratto_id))
        self.assertEqual(errore.code, "E_PERMESSO_NEGATO")
        self.assertEqual(self._stato()[0], "DRAFT")

    def test_il_secondo_emetti_e_rifiutato(self) -> None:
        self._concedi_emetti_contratto()
        self.servizio.emetti(self.contratto_id)
        errore = self._rifiuto(lambda: self.servizio.emetti(self.contratto_id))
        self.assertEqual(errore.code, "E_DOC_GIA_NELLO_STATO")
        self.assertEqual(self._stato()[0], "ATTIVO")

    def test_cessazione_di_oggi_e_immediata(self) -> None:
        self._concedi_emetti_contratto()
        self.servizio.emetti(self.contratto_id)
        out = self.servizio.cambia_stato(
            self.contratto_id, codice_interno="CESSATO", valido_al=self.oggi,
        )
        self.assertIs(out["programmata"], False)
        self.assertEqual(self._stato(), ("CESSATO", self.oggi))

    def test_cessazione_futura_e_programmata(self) -> None:
        self._concedi_emetti_contratto()
        self.servizio.emetti(self.contratto_id)
        fine = self.oggi + timedelta(days=10)
        out = self.servizio.cambia_stato(
            self.contratto_id, codice_interno="CESSATO", valido_al=fine,
        )
        self.assertIs(out["programmata"], True)
        self.assertEqual(self._stato(), ("ATTIVO", fine))

    def test_i_rifiuti_della_cessazione_hanno_il_codice_del_db(self) -> None:
        self._concedi_emetti_contratto()
        self.servizio.emetti(self.contratto_id)

        def cessa(valido_al: date | None) -> ServiceError:
            return self._rifiuto(lambda: self.servizio.cambia_stato(
                self.contratto_id, codice_interno="CESSATO", valido_al=valido_al,
            ))

        senza = cessa(None)
        self.assertEqual(senza.code, "E_CONTRATTO_CESSAZIONE_SENZA_DATA")
        self.assertEqual(cessa(self.oggi - timedelta(days=1)).code, "E_CONTRATTO_VALIDO_AL_RETROATTIVO")
        self.assertEqual(self._stato(), ("ATTIVO", None))

    def test_annullo_della_bozza_senza_azione(self) -> None:
        out = self.servizio.cambia_stato(self.contratto_id, codice_interno="ANNULLATO")
        self.assertEqual(out["stato_codice_interno"], "ANNULLATO")
        self.assertEqual(self._stato()[0], "ANNULLATO")
