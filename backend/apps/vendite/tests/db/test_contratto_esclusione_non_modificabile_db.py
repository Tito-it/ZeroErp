# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: UN'ESCLUSIONE DEL CONTRATTO NON SI MODIFICA, vista dal backend sul
#        DATABASE VERO (brief-db-contratto-esclusione-non-modificabile §5,
#        decisione di Tid del 2026-10-04): il PATCH di una riga ESCLUSIONE
#        arriva al guard DB `_a05_` e risponde il suo codice, 409.
#
# 🔴 PERCHE' SUL DB VERO. Fino al 2026-10-04 il service pre-validava il prezzo
#    di un'esclusione con un 400 suo; quel ramo e' stato tolto perche' la regola
#    ora e' una sola, a DB. Un test con il repository mockato non vede niente:
#    il rifiuto nasce nel trigger, e la sola cosa che il backend deve fare e'
#    lasciarlo passare col suo codice, senza coprirlo col ripiego del service.
#
# ⭐ Il mondo si COSTRUISCE (regola zero), come nel pgTAP della parte DB
#    `test-contratto-esclusione-non-modificabile-v1`: cliente, listino con una
#    versione ATTIVA che copre oggi, un articolo, contratto in BOZZA e la riga
#    ESCLUSIONE. Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) test_patch_della_quantita_risponde_il_codice_del_guard
2) test_patch_del_prezzo_parla_il_guard_non_il_check_sul_prezzo
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.services.contratti_service import ContrattiService

_CODICE_GUARD = "E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE"

# Il mondo del pgTAP, ridotto a un articolo: la versione del builder finisce
# nel 2020, quindi quella che copre oggi nasce qui (BOZZA, righe, ATTIVA).
_FIXTURE = (
    "CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('ESCLNM')",
    "CREATE TEMP TABLE _l AS SELECT * FROM dbops.fn_pgtap_crea_listino("
    " (SELECT utility_id FROM _m), 'ESCLNM', '2020-01-01'::date, '2020-12-31'::date)",
    "CREATE TEMP TABLE _v AS WITH ins AS ("
    " INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, stato)"
    " SELECT listino_id, 'ESCLNM_V2', '2021-01-01'::date, 'BOZZA' FROM _l RETURNING id"
    ") SELECT id FROM ins",
    "CREATE TEMP TABLE _a AS SELECT dbops.fn_pgtap_crea_articolo('ESCLNM-ART') AS id",
    "UPDATE catalogo.articoli SET listino_tipologia_id = (SELECT tipologia_id FROM _l)"
    " WHERE id = (SELECT id FROM _a)",
    "INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)"
    " SELECT (SELECT id FROM _v), ar.id, ar.uom_id, 100.00"
    " FROM catalogo.articoli ar WHERE ar.id = (SELECT id FROM _a)",
    "UPDATE vendite.listini_versioni SET stato = 'ATTIVA' WHERE id = (SELECT id FROM _v)",
    "CREATE TEMP TABLE _c AS WITH ins AS ("
    " INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,"
    "  stato_doc_contratto_id, listino_id, valido_dal, valido_al)"
    " SELECT 'ESCLNM-' || substr(gen_random_uuid()::text, 1, 8),"
    "  m.billing_account_id, m.istanza_utility_id, m.utility_id,"
    "  (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),"
    "  (SELECT listino_id FROM _l), CURRENT_DATE, CURRENT_DATE + 365"
    " FROM _m m RETURNING id"
    ") SELECT id FROM ins",
)

# La riga ESCLUSIONE come nel pgTAP: senza prezzo (CHECK), con quantita' e UdM
# operativa che i trigger della tabella pretendono.
_ESCLUSIONE = (
    "INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione,"
    " tipo_erogazione, fonte_quantita_attesa, quantita, qta_operativa, uom_operativa_id)"
    " SELECT (SELECT id FROM _c), ar.id, 'ESCLUSIONE', 'CANONE', 'FISSA', 1, 1, ar.uom_id"
    " FROM catalogo.articoli ar WHERE ar.id = (SELECT id FROM _a)"
    " RETURNING id"
)


class _Annulla(Exception):
    """Esce dal blocco atomico annullandolo."""


class EsclusioneNonModificabileDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("dbops.fn_pgtap_crea_mondo_cliente(text,character varying)")

    # Scopo: costruisce il mondo e la riga ESCLUSIONE, poi lancia il PATCH del
    #        service e ritorna l'errore che risponde. Il blocco viene annullato.
    def _patch_esclusione(self, payload: dict) -> ServiceError:
        try:
            with transaction.atomic(), connection.cursor() as cur:
                for sql in _FIXTURE:
                    cur.execute(sql)
                cur.execute(_ESCLUSIONE)
                riga_id = cur.fetchone()[0]
                with self.assertRaises(ServiceError) as ctx:
                    ContrattiService().update_riga(riga_id, payload)
                raise _Annulla
        except _Annulla:
            pass
        return ctx.exception

    # 1. Una colonna di contenuto qualunque: risponde il guard, col suo codice.
    def test_patch_della_quantita_risponde_il_codice_del_guard(self):
        errore = self._patch_esclusione({"quantita": "3"})
        self.assertEqual(errore.code, _CODICE_GUARD)

    # 2. ⭐ Il prezzo: fino al 2026-10-04 lo rifiutava il service con un 400
    #    («prezzo_unitario deve essere NULL»), che invitava a togliere il prezzo
    #    e riprovare. Ora parla il guard `_a05_`, prima del CHECK sul prezzo.
    def test_patch_del_prezzo_parla_il_guard_non_il_check_sul_prezzo(self):
        errore = self._patch_esclusione({"prezzo_unitario": "10"})
        self.assertEqual(errore.code, _CODICE_GUARD)


if __name__ == "__main__":
    unittest.main()
