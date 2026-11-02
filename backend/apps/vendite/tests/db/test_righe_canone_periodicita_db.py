# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: UNA RIGA A CANONE DICE OGNI QUANTO SI ADDEBITA, vista dal backend sul
#        DATABASE VERO (brief-db-contratto-righe-periodiche-in-commessa §7.13.4,
#        passo 4; la (b) di Tid del 2026-10-29). Un'AGGIUNTA a canone senza
#        periodicita' e' un 400 col codice del guard DB e col campo da
#        accendere nel form.
#
# 🔴 PERCHE' SUL DB VERO. La regola ha una sede sola, il guard
#    `script.trgfn_righe_guard_periodicita_canone` (rete: i due CHECK). Il
#    service non la pre-valida. Cio' che il backend deve garantire e' il
#    TRASPORTO: codice e campo (canale `COLUMN`) arrivano al `ServiceError`
#    attraverso i mapper dei due service, contratto e offerta. Un repository
#    mockato non lo vede.
#
# ⭐ Il mondo si COSTRUISCE (regola zero), come nel pgTAP della parte DB
#    `vendite/test-righe-canone-periodicita-obbligatoria-v1`: un articolo di
#    quota fissa (CANONE/FISSA ammessa), contratto senza listino e offerta su un
#    listino vuoto, in BOZZA. L'AGGIUNTA non eredita la periodicita' dal
#    listino (F-9): la scrive l'operatore. Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) test_contratto_aggiunta_a_canone_senza_periodicita
2) test_offerta_aggiunta_a_canone_senza_periodicita
"""
from __future__ import annotations

import unittest
from collections.abc import Callable

from django.db import connection, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto
from apps.vendite.db.offerte_repository import OfferteRepository
from apps.vendite.services.contratti_service import ContrattiService
from apps.vendite.services.offerte_service import OfferteService

_CODICE = "E_RIGA_CANONE_SENZA_PERIODICITA"

_FIXTURE = (
    "CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('CANPER')",
    "CREATE TEMP TABLE _l AS SELECT * FROM dbops.fn_pgtap_crea_listino("
    " (SELECT utility_id FROM _m), 'CANPER')",
    "CREATE TEMP TABLE _a AS SELECT dbops.fn_pgtap_crea_articolo('CANPER-ART',"
    " p_listino_tipologia_id => (SELECT id FROM config.listini_tipologie"
    " WHERE codice = 'QUOTA_FISSA')) AS id",
)

_CONTRATTO = (
    "SELECT k.contratto_id FROM dbops.fn_pgtap_crea_contratto("
    " 'CANPER', 'DRAFT', (SELECT billing_account_id FROM _m), NULL,"
    " script.fn_data_operativa(), script.fn_data_operativa() + 365, NULL, NULL) k"
)


# Scopo: il payload di un'AGGIUNTA a canone senza periodicita'.
def _aggiunta_a_canone(cur) -> dict:
    cur.execute("SELECT id, uom_id FROM catalogo.articoli WHERE id = (SELECT id FROM _a)")
    articolo_id, uom_id = cur.fetchone()
    return {
        "articolo_id": str(articolo_id),
        "tipo_eccezione": "AGGIUNTA",
        "prezzo_unitario": "80.00",
        "tipo_erogazione": "CANONE",
        "fonte_quantita_attesa": "FISSA",
        "qta_operativa": "1",
        "uom_operativa_id": uom_id,
    }


class RigheCanonePeriodicitaDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("dbops.fn_pgtap_crea_mondo_cliente(text,character varying)")

    # Scopo: costruisce il mondo, lancia `azione(cur)` e ritorna l'errore che
    #        risponde. Il blocco viene annullato.
    def _errore(self, azione: Callable) -> ServiceError:
        try:
            with transaction.atomic(), connection.cursor() as cur:
                for sql in _FIXTURE:
                    cur.execute(sql)
                with self.assertRaises(ServiceError) as ctx:
                    azione(cur)
                raise Annulla
        except Annulla:
            pass
        return ctx.exception

    # Scopo: il codice del guard, col campo nel canale strutturato.
    def _assert_codice_e_campo(self, errore: ServiceError) -> None:
        self.assertEqual(errore.code, _CODICE, errore.detail)
        self.assertIn("periodicita", errore.fields or ())

    # Scopo: un'offerta in BOZZA nel mondo, dal repository; ritorna l'id.
    @staticmethod
    def _offerta(cur) -> int:
        cur.execute(
            "SELECT emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id"
            " FROM _m"
        )
        emittente, ba, istanza, utility = cur.fetchone()
        cur.execute("SELECT listino_id FROM _l")
        return OfferteRepository().create_offerta({
            "emittente_fiscale_id": emittente,
            "billing_account_id": ba,
            "istanza_utility_id": istanza,
            "utility_id": utility,
            "listino_id": cur.fetchone()[0],
            "validita_dal": oggi_aziendale(),
        })

    # 1. Contratto: l'AGGIUNTA a canone senza periodicita' e' rifiutata.
    def test_contratto_aggiunta_a_canone_senza_periodicita(self):
        def azione(cur):
            cur.execute(_CONTRATTO)
            ContrattiService().create_riga(cur.fetchone()[0], _aggiunta_a_canone(cur))
        self._assert_codice_e_campo(self._errore(azione))

    # 2. Offerta: la stessa regola (il push la ricopia nel contratto).
    def test_offerta_aggiunta_a_canone_senza_periodicita(self):
        def azione(cur):
            OfferteService().crea_eccezione(self._offerta(cur), _aggiunta_a_canone(cur))
        self._assert_codice_e_campo(self._errore(azione))


if __name__ == "__main__":
    unittest.main()
