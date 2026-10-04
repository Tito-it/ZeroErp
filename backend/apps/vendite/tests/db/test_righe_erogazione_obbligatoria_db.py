# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: UNA RIGA CHE SI FATTURA DICE COME SI EROGA, vista dal backend sul
#        DATABASE VERO (brief-db-erogazione-obbligatoria-righe-fatturate §6,
#        decisione di Tid del 2026-10-04): una riga OVERRIDE/AGGIUNTA di
#        contratto o di offerta senza `tipo_erogazione` risponde il codice del
#        guard DB, 400, col campo da evidenziare nel form.
#
# 🔴 PERCHE' SUL DB VERO. Il service non pre-valida l'erogazione, per scelta:
#    la regola ha una sede sola, il guard `script.trgfn_righe_guard_erogazione_obbligatoria`.
#    Cio' che il backend deve garantire e' il TRASPORTO: codice e campo
#    (canale `COLUMN`) arrivano al `ServiceError` attraverso i due mapper dei
#    service. Un repository mockato non lo vede.
#
# ⭐ Il mondo si COSTRUISCE (regola zero), come nel pgTAP della parte DB
#    `test-righe-erogazione-obbligatoria-v1`: cliente, listino con una versione
#    ATTIVA che copre oggi, un articolo del listino, contratto e offerta in
#    BOZZA. Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) test_contratto_create_senza_erogazione
2) test_contratto_patch_che_toglie_l_erogazione
3) test_offerta_create_senza_erogazione
4) test_offerta_patch_che_toglie_l_erogazione
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from datetime import date

from django.db import connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.offerte_repository import OfferteRepository
from apps.vendite.services.contratti_service import ContrattiService
from apps.vendite.services.offerte_service import OfferteService

_CODICE = "E_RIGA_EROGAZIONE_OBBLIGATORIA"

# Il mondo del pgTAP, ridotto a un articolo: la versione del builder finisce
# nel 2020, quindi quella che copre oggi nasce qui (BOZZA, righe, ATTIVA).
_FIXTURE = (
    "CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('EROGOBB')",
    "CREATE TEMP TABLE _l AS SELECT * FROM dbops.fn_pgtap_crea_listino("
    " (SELECT utility_id FROM _m), 'EROGOBB', '2020-01-01'::date, '2020-12-31'::date)",
    "CREATE TEMP TABLE _v AS WITH ins AS ("
    " INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, stato)"
    " SELECT listino_id, 'EROGOBB_V2', '2021-01-01'::date, 'BOZZA' FROM _l RETURNING id"
    ") SELECT id FROM ins",
    "CREATE TEMP TABLE _a AS SELECT dbops.fn_pgtap_crea_articolo('EROGOBB-ART') AS id",
    "UPDATE catalogo.articoli SET listino_tipologia_id = (SELECT tipologia_id FROM _l)"
    " WHERE id = (SELECT id FROM _a)",
    "INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)"
    " SELECT (SELECT id FROM _v), ar.id, ar.uom_id, 100.00"
    " FROM catalogo.articoli ar WHERE ar.id = (SELECT id FROM _a)",
    "UPDATE vendite.listini_versioni SET stato = 'ATTIVA' WHERE id = (SELECT id FROM _v)",
)

_CONTRATTO = (
    "INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,"
    " stato_doc_contratto_id, listino_id, valido_dal, valido_al)"
    " SELECT 'EROGOBB-' || substr(gen_random_uuid()::text, 1, 8),"
    " m.billing_account_id, m.istanza_utility_id, m.utility_id,"
    " (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'),"
    " (SELECT listino_id FROM _l), CURRENT_DATE, CURRENT_DATE + 365"
    " FROM _m m RETURNING id"
)

# Una riga OVERRIDE con l'erogazione, al prezzo del listino: il bersaglio del
# PATCH che la toglie.
_RIGA_CONTRATTO = (
    "INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione,"
    " prezzo_unitario, tipo_erogazione, fonte_quantita_attesa, quantita, qta_operativa,"
    " uom_operativa_id)"
    " SELECT %s, ar.id, 'OVERRIDE', 100.00, 'CANONE', 'FISSA', 1, 1, ar.uom_id"
    " FROM catalogo.articoli ar WHERE ar.id = (SELECT id FROM _a) RETURNING id"
)

_ECCEZIONE_OFFERTA = (
    "INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id,"
    " tipo_eccezione, prezzo_unitario, tipo_erogazione, fonte_quantita_attesa, quantita,"
    " qta_operativa, uom_operativa_id)"
    " SELECT %s, ar.id, 'OVERRIDE', 100.00, 'CANONE', 'FISSA', 1, 1, ar.uom_id"
    " FROM catalogo.articoli ar WHERE ar.id = (SELECT id FROM _a) RETURNING id"
)


class _Annulla(Exception):
    """Esce dal blocco atomico annullandolo."""


# Scopo: il payload di una riga OVERRIDE completa tranne l'erogazione.
def _override_senza_erogazione(cur) -> dict:
    cur.execute("SELECT id, uom_id FROM catalogo.articoli WHERE id = (SELECT id FROM _a)")
    articolo_id, uom_id = cur.fetchone()
    return {
        "articolo_id": str(articolo_id),
        "tipo_eccezione": "OVERRIDE",
        "fonte_quantita_attesa": "FISSA",
        "prezzo_unitario": "100.00",
        "qta_operativa": "1",
        "uom_operativa_id": uom_id,
    }


class RigheErogazioneObbligatoriaDbTests(unittest.TestCase):
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
                raise _Annulla
        except _Annulla:
            pass
        return ctx.exception

    # Scopo: il codice del guard, col campo nel canale strutturato.
    def _assert_codice_e_campo(self, errore: ServiceError) -> None:
        self.assertEqual(errore.code, _CODICE)
        self.assertIn("tipo_erogazione", errore.fields or ())

    # Scopo: un contratto in BOZZA nel mondo; ritorna l'id.
    @staticmethod
    def _contratto(cur) -> int:
        cur.execute(_CONTRATTO)
        return cur.fetchone()[0]

    # Scopo: un'offerta in BOZZA nel mondo, dal repository; ritorna l'id.
    @staticmethod
    def _offerta(cur) -> int:
        repo = OfferteRepository()
        cur.execute(
            "SELECT emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id"
            " FROM _m"
        )
        emittente, ba, istanza, utility = cur.fetchone()
        cur.execute("SELECT listino_id FROM _l")
        return repo.create_offerta({
            "emittente_fiscale_id": emittente,
            "billing_account_id": ba,
            "istanza_utility_id": istanza,
            "utility_id": utility,
            "listino_id": cur.fetchone()[0],
            "validita_dal": date.today(),
            "stato_doc_offerta_id": repo.get_stato_id_by_codice("BOZZA"),
        })

    # 1. Contratto, create: l'OVERRIDE senza erogazione non nasce.
    def test_contratto_create_senza_erogazione(self):
        def azione(cur):
            ContrattiService().create_riga(self._contratto(cur), _override_senza_erogazione(cur))
        self._assert_codice_e_campo(self._errore(azione))

    # 2. Contratto, PATCH: togliere l'erogazione a un OVERRIDE e' rifiutato.
    def test_contratto_patch_che_toglie_l_erogazione(self):
        def azione(cur):
            cur.execute(_RIGA_CONTRATTO, [self._contratto(cur)])
            ContrattiService().update_riga(cur.fetchone()[0], {"tipo_erogazione": None})
        self._assert_codice_e_campo(self._errore(azione))

    # 3. Offerta, create: la stessa regola (il push la ricopia nel contratto).
    def test_offerta_create_senza_erogazione(self):
        def azione(cur):
            OfferteService().crea_eccezione(self._offerta(cur), _override_senza_erogazione(cur))
        self._assert_codice_e_campo(self._errore(azione))

    # 4. Offerta, PATCH: togliere l'erogazione a un OVERRIDE e' rifiutato.
    def test_offerta_patch_che_toglie_l_erogazione(self):
        def azione(cur):
            offerta = self._offerta(cur)
            cur.execute(_ECCEZIONE_OFFERTA, [offerta])
            OfferteService().aggiorna_eccezione(
                offerta, cur.fetchone()[0], {"tipo_erogazione": None},
            )
        self._assert_codice_e_campo(self._errore(azione))


if __name__ == "__main__":
    unittest.main()
