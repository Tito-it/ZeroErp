# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LE SCRITTURE DINAMICHE di offerte, contratti e promo sul DATABASE
#        VERO, dopo la migrazione ai BB core `execute_dynamic_insert`/
#        `execute_dynamic_update` (2026-09-26) — e il rifiuto delle chiavi
#        fuori lista.
#
# 🔴 PERCHE' SUL DB VERO. I test dei service mockano il repository: vedono che
#    il service CHIAMA `create_eccezione`, non che l'INSERT composto dal BB si
#    leghi davvero alle colonne (enum, uuid, `::jsonb`). E un caso l'ha gia'
#    dimostrato: `promo_articoli_repository` passava `meta` (un dict) come
#    `%s` nudo, e psycopg 3 un dict non lo sa adattare — la promo con `meta`
#    era un 500 che nessun mock vedeva. Il test 4 lo prova.
#
# ⭐ Il mondo si COSTRUISCE (regola zero): azienda, operatore, contesto e
#    cliente da `fn_pgtap_crea_mondo_cliente`, listino da
#    `fn_pgtap_crea_listino`, articoli da `fn_pgtap_crea_articolo`. Unica
#    lettura di configurazione: lo stato BOZZA dell'offerta (seed di sistema,
#    lo risolve il repository stesso). Tutto in transazione ANNULLATA.
#
# ⛔ IL RIFIUTO (classe senza DB). Una chiave fuori whitelist in una scrittura
#    e' `RuntimeError` PRIMA di toccare il database: fino al 2026-09-26 veniva
#    SCARTATA in silenzio. Il 400 educato lo danno i service.
# ------------------------------------------------------------
"""
Indice test eseguiti:
Rifiuto (senza DB):
1) RifiutoChiaviFuoriListaTests.test_ogni_scrittura_rifiuta_la_chiave_estranea
Opt-in `ZEROERP_TEST_DB_E2E=1`:
2) ScrittureDinamicheVenditeDbTests.test_offerta_testata_utility_eccezione
   meta STRINGA = testo JSON (oggetto, non scalare), dict = oggetto, enum e
   uuid come parametri, stringhe strippate, update vuoto -> False.
3) ScrittureDinamicheVenditeDbTests.test_contratto_testata_righe_utility
   padre dal repository, campi L3 del workflow ammessi sulla riga.
4) ScrittureDinamicheVenditeDbTests.test_promo_create_e_update_con_meta
   il `meta` dict arriva come oggetto jsonb (prima: 500 di adattamento).
"""
from __future__ import annotations

import json
import unittest
from datetime import timedelta
from decimal import Decimal

from django.db import connection, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto
from apps.vendite.db.contratti_repository import ContrattiRepository
from apps.vendite.db.offerte_repository import OfferteRepository
from apps.vendite.db.promo_articoli_repository import PromoArticoliRepository

_MONDO = (
    "CREATE TEMP TABLE _mondo AS "
    "SELECT m.* FROM dbops.fn_pgtap_crea_mondo_cliente('SCRDYNV') m"
)


# Scopo: una riga come dict, per le verifiche.
def _riga(cur, sql: str, params: list) -> dict:
    cur.execute(sql, params)
    colonne = [c[0] for c in cur.description]
    valori = cur.fetchone()
    assert valori is not None, f"nessuna riga: {sql}"
    return dict(zip(colonne, valori, strict=True))


# Scopo: jsonb letto dal driver (dict, o testo se il driver non decodifica).
def _json(valore):
    return json.loads(valore) if isinstance(valore, str) else valore


# Scopo: il mondo (cliente fatturabile, listino della sua utility, un
#        articolo) sul cursore; ritorna i riferimenti che servono ai test.
def _apri_mondo(cur) -> dict:
    cur.execute(_MONDO)
    mondo = _riga(cur, "SELECT * FROM _mondo", [])
    cur.execute(
        "SELECT listino_id FROM dbops.fn_pgtap_crea_listino(%s, 'SCRDYNV')",
        [mondo["utility_id"]],
    )
    mondo["listino_id"] = cur.fetchone()[0]
    cur.execute("SELECT dbops.fn_pgtap_crea_articolo('SCRDYNV-ART', false)")
    mondo["articolo_id"] = cur.fetchone()[0]
    cur.execute("SELECT uom_id FROM catalogo.articoli WHERE id = %s", [mondo["articolo_id"]])
    mondo["uom_id"] = cur.fetchone()[0]
    return mondo


# Scopo: la riga di una eccezione/riga AGGIUNTA minima e coerente (fonte e
#        erogazione compatibili, prezzo presente come il CHECK pretende).
def _riga_aggiunta(mondo: dict) -> dict:
    return {
        "articolo_id": mondo["articolo_id"],
        "tipo_eccezione": "AGGIUNTA",
        "tipo_erogazione": "UNA_TANTUM",
        "fonte_quantita_attesa": "FISSA",
        "prezzo_unitario": Decimal("10.00"),
        "qta_operativa": Decimal("1"),
        "uom_operativa_id": mondo["uom_id"],
        "factor_to_base": Decimal("1"),
        "meta": {"origine": "test"},
    }


class RifiutoChiaviFuoriListaTests(unittest.TestCase):
    """⛔ Una chiave fuori whitelist e' `RuntimeError`, mai uno scarto."""

    # 1. Il BB verifica le colonne PRIMA di aprire il cursore: niente DB.
    def test_ogni_scrittura_rifiuta_la_chiave_estranea(self):
        off, con, promo = OfferteRepository(), ContrattiRepository(), PromoArticoliRepository()
        casi = (
            ("create_offerta", lambda: off.create_offerta({"validita_dal": "x", "codice": "Y"})),
            ("update_offerta", lambda: off.update_offerta(1, {"stato_doc_offerta_id": 2})),
            ("create_eccezione", lambda: off.create_eccezione(1, {"componenti_overrides": {}})),
            ("update_eccezione", lambda: off.update_eccezione(1, {"articolo_id": "a"})),
            ("create_utility off", lambda: off.create_utility(1, {"utility": {}})),
            ("update_utility off", lambda: off.update_utility(1, {"utility_id": 3})),
            ("update_contratto", lambda: con.update_contratto(1, {"numero": "X"})),
            ("create_riga", lambda: con.create_riga(1, {"richiesta_approvazione": True})),
            ("update_riga", lambda: con.update_riga(1, {"tipo_eccezione": "AGGIUNTA"})),
            ("create_utility con", lambda: con.create_utility(1, {"numero": "X"})),
            ("update_utility con", lambda: con.update_utility(1, {"istanza_utility_id": 2})),
            ("create_promo", lambda: promo.create_promo({"codice": "X", "validita": "[,)"})),
            ("update_promo", lambda: promo.update_promo(1, {"codice": "X"})),
        )
        for nome, chiama in casi:
            with self.subTest(nome), self.assertRaises(RuntimeError) as ctx:
                chiama()
            self.assertIn("colonne non ammesse", str(ctx.exception), nome)


class ScrittureDinamicheVenditeDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("dbops.fn_pgtap_crea_mondo_cliente(text,character varying)")

    # 2. Offerta: testata, utility 1:1 ed eccezione, INSERT e UPDATE dal BB.
    def test_offerta_testata_utility_eccezione(self):
        repo = OfferteRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                m = _apri_mondo(cur)
                offerta = repo.create_offerta({
                    "emittente_fiscale_id": m["emittente_fiscale_id"],
                    "billing_account_id": m["billing_account_id"],
                    "istanza_utility_id": m["istanza_utility_id"],
                    "utility_id": m["utility_id"],
                    "listino_id": m["listino_id"],
                    "validita_dal": oggi_aziendale(),
                    # ⭐ Regola Tid 2026-09-26: una STRINGA su una colonna jsonb
                    #    dichiarata e' TESTO JSON. Prima `to_write_param` la
                    #    serializzava di nuovo: uno scalare stringa jsonb.
                    "meta": '{"da": "testo"}',
                })
                riga = _riga(cur, """
                    SELECT codice, jsonb_typeof(meta) AS tipo_meta, meta
                    FROM vendite.offerte_commerciali WHERE id = %s
                """, [offerta])
                self.assertTrue(riga["codice"])  # dal trigger BEFORE INSERT
                self.assertEqual(riga["tipo_meta"], "object")
                self.assertEqual(_json(riga["meta"]), {"da": "testo"})

                self.assertTrue(repo.update_offerta(offerta, {
                    "validita_al": oggi_aziendale() + timedelta(days=30),
                    "meta": {"v": 2},
                }))
                self.assertEqual(_json(_riga(cur, (
                    "SELECT meta FROM vendite.offerte_commerciali WHERE id = %s"
                ), [offerta])["meta"]), {"v": 2})
                self.assertFalse(repo.update_offerta(offerta, {}))

                utility = repo.create_utility(offerta, {
                    "istanza_utility_id": m["istanza_utility_id"],
                    "utility_id": m["utility_id"],
                    "param_2_txt": "  valore  ",
                    "meta": {"k": 1},
                })
                riga = _riga(cur, """
                    SELECT offerta_id, param_2_txt, jsonb_typeof(meta) AS tipo_meta
                    FROM vendite.offerte_commerciali_utilities WHERE id = %s
                """, [utility])
                self.assertEqual(riga["offerta_id"], offerta)
                # ⚠️ Cambio di semantica dichiarato: il BB strippa.
                self.assertEqual(riga["param_2_txt"], "valore")
                self.assertEqual(riga["tipo_meta"], "object")
                self.assertTrue(repo.update_utility(utility, {"param_2_txt": None}))
                self.assertIsNone(_riga(cur, (
                    "SELECT param_2_txt FROM vendite.offerte_commerciali_utilities WHERE id = %s"
                ), [utility])["param_2_txt"])

                eccezione = repo.create_eccezione(offerta, _riga_aggiunta(m))
                riga = _riga(cur, """
                    SELECT offerta_id, articolo_id, tipo_eccezione::text AS tipo,
                           prezzo_unitario, jsonb_typeof(meta) AS tipo_meta
                    FROM vendite.offerte_commerciali_eccezioni WHERE id = %s
                """, [eccezione])
                self.assertEqual(riga["offerta_id"], offerta)
                self.assertEqual(riga["articolo_id"], m["articolo_id"])
                self.assertEqual(riga["tipo"], "AGGIUNTA")
                self.assertEqual(riga["prezzo_unitario"], Decimal("10.00"))
                self.assertEqual(riga["tipo_meta"], "object")
                self.assertTrue(repo.update_eccezione(eccezione, {
                    "prezzo_unitario": Decimal("12.50"), "meta": {"v": 3},
                }))
                self.assertEqual(_riga(cur, (
                    "SELECT prezzo_unitario FROM vendite.offerte_commerciali_eccezioni WHERE id = %s"
                ), [eccezione])["prezzo_unitario"], Decimal("12.50"))
                raise Annulla
        except Annulla:
            pass

    # 3. Contratto: testata (nata dalla madre), righe e utility dal BB.
    def test_contratto_testata_righe_utility(self):
        repo = ContrattiRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                m = _apri_mondo(cur)
                contratto = repo.create_contratto_atomico(testata={
                    "billing_account_id": m["billing_account_id"],
                    "istanza_utility_id": m["istanza_utility_id"],
                    "utility_id": m["utility_id"],
                    "emittente_fiscale_id": m["emittente_fiscale_id"],
                    "valido_dal": oggi_aziendale(),
                    "listino_id": m["listino_id"],
                }, utility=None)

                self.assertTrue(repo.update_contratto(contratto, {
                    "codice_commessa": "  COMM-1  ",
                    "meta": {"nota": "x"},
                }))
                riga = _riga(cur, """
                    SELECT codice_commessa, jsonb_typeof(meta) AS tipo_meta
                    FROM vendite.contratti WHERE id = %s
                """, [contratto])
                self.assertEqual(riga["codice_commessa"], "COMM-1")
                self.assertEqual(riga["tipo_meta"], "object")
                self.assertFalse(repo.update_contratto(contratto, {}))

                riga_id = repo.create_riga(contratto, _riga_aggiunta(m))
                riga = _riga(cur, """
                    SELECT contratto_id, tipo_eccezione::text AS tipo,
                           jsonb_typeof(meta) AS tipo_meta
                    FROM vendite.contratti_righe WHERE id = %s
                """, [riga_id])
                self.assertEqual(riga["contratto_id"], contratto)
                self.assertEqual(riga["tipo"], "AGGIUNTA")
                self.assertEqual(riga["tipo_meta"], "object")
                # `quantita` non e' scrivibile (dal 2026-10-21): la calcola il DB
                # da `qta_operativa` (`trgfn_qta_from_operativa`).
                self.assertTrue(repo.update_riga(riga_id, {
                    "qta_operativa": Decimal("3"), "meta": {"v": 2},
                }))
                self.assertEqual(_riga(cur, (
                    "SELECT quantita FROM vendite.contratti_righe WHERE id = %s"
                ), [riga_id])["quantita"], Decimal("3"))

                utility = repo.create_utility(contratto, {
                    "istanza_utility_id": m["istanza_utility_id"],
                    "utility_id": m["utility_id"],
                    "meta": {"k": 1},
                })
                self.assertTrue(repo.update_utility(utility, {"param_2_txt": "  p2  "}))
                self.assertEqual(_riga(cur, (
                    "SELECT param_2_txt FROM vendite.contratti_utilities WHERE id = %s"
                ), [utility])["param_2_txt"], "p2")
                raise Annulla
        except Annulla:
            pass

    # 4. Promo: il `meta` dict arriva come OGGETTO jsonb, in INSERT e UPDATE.
    #    ⛔ Prima della migrazione era un `%s` nudo: psycopg 3 non adatta un
    #    dict, e la promo col `meta` rispondeva 500.
    def test_promo_create_e_update_con_meta(self):
        repo = PromoArticoliRepository()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                m = _apri_mondo(cur)
                # Il guard data-driven vuole `valido_dal` strettamente futuro.
                domani = oggi_aziendale() + timedelta(days=1)
                promo = repo.create_promo({
                    "codice": "SCRDYNV-PROMO",
                    "descrizione": "Promo scritture",
                    "articolo_id": str(m["articolo_id"]),
                    "uom_id": m["uom_id"],
                    "tipo_variazione": "PERCENTUALE",
                    "valore_variazione": Decimal("10"),
                    "valido_dal": domani,
                    "valido_al": domani + timedelta(days=10),
                    "meta": {"campagna": "autunno"},
                })
                riga = _riga(cur, """
                    SELECT articolo_id, meta, jsonb_typeof(meta) AS tipo_meta
                    FROM vendite.promo_articoli WHERE id = %s
                """, [promo])
                self.assertEqual(riga["articolo_id"], m["articolo_id"])
                self.assertEqual(riga["tipo_meta"], "object")
                self.assertEqual(_json(riga["meta"]), {"campagna": "autunno"})

                self.assertTrue(repo.update_promo(promo, {"meta": {"v": 2}}))
                self.assertEqual(_json(_riga(cur, (
                    "SELECT meta FROM vendite.promo_articoli WHERE id = %s"
                ), [promo])["meta"]), {"v": 2})
                raise Annulla
        except Annulla:
            pass
