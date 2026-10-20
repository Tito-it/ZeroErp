# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: UNA RIGA CHE SI FATTURA DICE COME SI EROGA, vista dal backend sul
#        DATABASE VERO (brief-db-erogazione-obbligatoria-righe-fatturate §6,
#        decisione di Tid del 2026-10-04). Dal 2026-10-07
#        (brief-db-offerta-emissione-ed-erogazione B-R2) una riga OVERRIDE/
#        AGGIUNTA che NASCE senza `tipo_erogazione` la EREDITA dall'articolo;
#        il guard d'obbligo resta, e morde il PATCH che la svuota: codice del
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
1) test_contratto_create_senza_erogazione_la_eredita
2) test_contratto_patch_che_toglie_l_erogazione
3) test_offerta_create_senza_erogazione_la_eredita
4) test_offerta_patch_che_toglie_l_erogazione
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
    "CREATE TEMP TABLE _a AS SELECT dbops.fn_pgtap_crea_articolo('EROGOBB-ART',"
    " p_listino_tipologia_id => (SELECT tipologia_id FROM _l)) AS id",
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
    " (SELECT listino_id FROM _l), script.fn_data_operativa(), script.fn_data_operativa() + 365"
    " FROM _m m RETURNING id"
)

# Una riga OVERRIDE con l'erogazione, al prezzo del listino: il bersaglio del
# PATCH che la toglie. ⭐ La combinazione e' quella di default che il DB dichiara
# per l'articolo (`vendite.fn_articolo_erogazioni`): una scritta a mano
# (CANONE/FISSA) il perimetro la rifiuterebbe, se la tipologia non la ammette.
_RIGA_DEFAULT = (
    " SELECT %s, ar.id, 'OVERRIDE', 100.00, ae.tipo_erogazione, ae.fonte_quantita_attesa,"
    " CASE WHEN ae.fonte_quantita_attesa = 'FISSA' THEN 1 END,"
    " CASE WHEN ae.fonte_quantita_attesa = 'FISSA' THEN 1 END, ar.uom_id"
    " FROM catalogo.articoli ar"
    " JOIN vendite.fn_articolo_erogazioni(ar.id) ae ON ae.e_default"
    " WHERE ar.id = (SELECT id FROM _a) RETURNING id"
)

_RIGA_CONTRATTO = (
    "INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione,"
    " prezzo_unitario, tipo_erogazione, fonte_quantita_attesa, quantita, qta_operativa,"
    " uom_operativa_id)" + _RIGA_DEFAULT
)

_ECCEZIONE_OFFERTA = (
    "INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id,"
    " tipo_eccezione, prezzo_unitario, tipo_erogazione, fonte_quantita_attesa, quantita,"
    " qta_operativa, uom_operativa_id)" + _RIGA_DEFAULT
)

# La combinazione con cui e' nata una riga, accanto a quella di default che il
# DB dichiara per il suo articolo: l'eredita' si legge dalla sede, non si ricopia.
_EREDITATA = (
    "SELECT r.tipo_erogazione, r.fonte_quantita_attesa, ae.tipo_erogazione,"
    " ae.fonte_quantita_attesa"
    " FROM {tabella} r"
    " JOIN vendite.fn_articolo_erogazioni(r.articolo_id) ae ON ae.e_default"
    " WHERE r.id = %s"
)


# Scopo: il payload di una riga OVERRIDE senza erogazione e senza fonte: le
#        eredita dall'articolo (B-R2).
def _override_senza_erogazione(cur) -> dict:
    cur.execute("SELECT id, uom_id FROM catalogo.articoli WHERE id = (SELECT id FROM _a)")
    articolo_id, uom_id = cur.fetchone()
    return {
        "articolo_id": str(articolo_id),
        "tipo_eccezione": "OVERRIDE",
        "prezzo_unitario": "100.00",
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
                raise Annulla
        except Annulla:
            pass
        return ctx.exception

    # Scopo: costruisce il mondo, lancia `azione(cur)` (che ritorna l'id della
    #        riga creata) e ritorna (ereditata, default dell'articolo). Il blocco
    #        viene annullato.
    def _ereditata(self, azione: Callable, tabella: str) -> tuple:
        try:
            with transaction.atomic(), connection.cursor() as cur:
                for sql in _FIXTURE:
                    cur.execute(sql)
                riga_id = azione(cur)
                cur.execute(_EREDITATA.format(tabella=tabella), [riga_id])
                esito = cur.fetchone()
                raise Annulla
        except Annulla:
            pass
        return esito

    # Scopo: la riga e' nata con la combinazione di default del suo articolo.
    def _assert_ereditata(self, esito: tuple) -> None:
        self.assertIsNotNone(esito)
        tipo, fonte, tipo_default, fonte_default = esito
        self.assertIsNotNone(tipo)
        self.assertEqual((tipo, fonte), (tipo_default, fonte_default))

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
            "validita_dal": oggi_aziendale(),
            "stato_doc_offerta_id": repo.get_stato_id_by_codice("BOZZA"),
        })

    # 1. Contratto, create: l'OVERRIDE senza erogazione la eredita dall'articolo.
    def test_contratto_create_senza_erogazione_la_eredita(self):
        def azione(cur):
            riga = ContrattiService().create_riga(
                self._contratto(cur), _override_senza_erogazione(cur),
            )
            return riga["id"]
        self._assert_ereditata(self._ereditata(azione, "vendite.contratti_righe"))

    # 2. Contratto, PATCH: togliere l'erogazione a un OVERRIDE e' rifiutato.
    def test_contratto_patch_che_toglie_l_erogazione(self):
        def azione(cur):
            contratto_id = self._contratto(cur)
            cur.execute(_RIGA_CONTRATTO, [contratto_id])
            ContrattiService().update_riga(
                contratto_id, cur.fetchone()[0], {"tipo_erogazione": None},
            )
        self._assert_codice_e_campo(self._errore(azione))

    # 3. Offerta, create: la stessa regola (il push la ricopia nel contratto).
    def test_offerta_create_senza_erogazione_la_eredita(self):
        def azione(cur):
            riga = OfferteService().crea_eccezione(
                self._offerta(cur), _override_senza_erogazione(cur),
            )
            return riga["id"]
        self._assert_ereditata(
            self._ereditata(azione, "vendite.offerte_commerciali_eccezioni"),
        )

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
