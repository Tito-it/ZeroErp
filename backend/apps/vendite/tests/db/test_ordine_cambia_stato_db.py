# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lo stato dell'ordine DAL VERBO sul DATABASE PROVVISTO
#        (brief-modello-documento-vendita §9.6, giro 7): `ordini_service`
#        arriva a `vendite.fn_cambia_stato_ordine` con lo stato di emissione
#        letto dal vocabolario (`DocumentoModelloRepository.stato_di_emissione`,
#        §8.11 B-1), il permesso lo dice la riga del passaggio
#        (`emetti_ordine`), le righe le conta il guard del DB, e lo stato di
#        emissione dal cambio stato generico e' un 400. E' la giuntura
#        Python↔PL/pgSQL che i test del service (mock) non vedono: la firma
#        del verbo, la porta, i lettori.
# Note: ⚠️ Le REGOLE del verbo (matrice, azione, porta, processo) le prova il
#       pgTAP `vendite/test-ordine-al-modello-v1`. L'ordine nasce in bozza dai
#       builder `dbops.fn_pgtap_crea_ordine*`, che aprono il contesto
#       sull'operatore del mondo; l'azione la concede
#       `dbops.fn_pgtap_concedi_azione`. Transazione SEMPRE annullata.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) OrdineCambiaStatoDbTests.test_conferma_dal_verbo — lo stato di emissione, dal verbo
2) OrdineCambiaStatoDbTests.test_conferma_senza_azione — E_PERMESSO_NEGATO dalla riga del passaggio
3) OrdineCambiaStatoDbTests.test_conferma_senza_righe — il rifiuto del guard, col suo codice (C-2)
4) OrdineCambiaStatoDbTests.test_lo_stato_di_emissione_e_un_400 — M-2 dal vocabolario
5) OrdineCambiaStatoDbTests.test_annullo_della_bozza — senza azione (M-4), dal verbo d'annullo
6) OrdineCambiaStatoDbTests.test_conferma_due_volte — rifiutata dal verbo, E_DOC_GIA_NELLO_STATO (§9.10)
7) OrdineCambiaStatoDbTests.test_conferma_ordine_inesistente — il 404 dal verbo
8) OrdineCambiaStatoDbTests.test_stato_inesistente — il rifiuto del verbo, col suo codice (§9.9)
"""
from __future__ import annotations

import unittest

from django.db import connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.services import ordini_service


class OrdineCambiaStatoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # Le sonde sugli oggetti del giro: un DB indietro fallisce sull'oggetto
        # mancante, non su un'attesa sbagliata.
        richiedi_db_provvisto("vendite.fn_cambia_stato_ordine(bigint,character varying)")
        richiedi_db_provvisto("script.fn_doc_stato_codice(regclass,bigint)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT ordine_id, auth_user_id FROM dbops.fn_pgtap_crea_ordine_con_righe("
                "'BE cambia stato ordine', 'DRAFT')",
            )
            ordine_id, auth_user_id = cur.fetchone()
        self.ordine_id = int(ordine_id)
        self.auth_user_id = int(auth_user_id)

    def _concedi_emetti_ordine(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_concedi_azione(%s, 'emetti_ordine')", [self.auth_user_id],
            )

    def _stato(self, ordine_id: int | None = None) -> str:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT s.codice_interno
                  FROM vendite.ordini o
                  JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
                 WHERE o.id = %s
                """,
                [ordine_id or self.ordine_id],
            )
            return str(cur.fetchone()[0])

    def test_conferma_dal_verbo(self) -> None:
        self._concedi_emetti_ordine()
        out = ordini_service.conferma(self.ordine_id)
        self.assertEqual(
            out, {"ordine_id": self.ordine_id, "stato_precedente": "DRAFT", "stato": "CONFERMATO"},
        )
        self.assertEqual(self._stato(), "CONFERMATO")

    def test_conferma_senza_azione(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            ordini_service.conferma(self.ordine_id)
        self.assertEqual(cm.exception.code, "E_PERMESSO_NEGATO")
        self.assertEqual(self._stato(), "DRAFT")

    # Fino al 2026-10-25 lo diceva il service (E_ORD_NESSUNA_RIGA, copia della
    # Regola 2 del guard): ora una regola, un livello.
    def test_conferma_senza_righe(self) -> None:
        with connection.cursor() as cur:
            cur.execute("SELECT ordine_id FROM dbops.fn_pgtap_crea_ordine('BE ordine senza righe')")
            vuoto = int(cur.fetchone()[0])
        self._concedi_emetti_ordine()
        with self.assertRaises(ServiceError) as cm:
            ordini_service.conferma(vuoto)
        self.assertEqual(cm.exception.code, "E_ORDINE_CONFERMA_SENZA_RIGHE")
        self.assertEqual(self._stato(vuoto), "DRAFT")

    def test_lo_stato_di_emissione_e_un_400(self) -> None:
        self._concedi_emetti_ordine()
        with self.assertRaises(ServiceError) as cm:
            ordini_service.cambia_stato(self.ordine_id, "CONFERMATO")
        self.assertEqual(cm.exception.code, "E_ORD_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "stato_codice")
        self.assertEqual(self._stato(), "DRAFT")

    def test_annullo_della_bozza(self) -> None:
        out = ordini_service.cambia_stato(self.ordine_id, "ANNULLATO")
        self.assertEqual(out["stato_precedente"], "DRAFT")
        self.assertEqual(self._stato(), "ANNULLATO")

    # La seconda conferma la rifiuta il verbo, dalla prima riga: il documento
    # e' gia' nello stato chiesto (brief-modello-documento-vendita §9.10).
    def test_conferma_due_volte(self) -> None:
        self._concedi_emetti_ordine()
        ordini_service.conferma(self.ordine_id)
        with self.assertRaises(ServiceError) as cm:
            ordini_service.conferma(self.ordine_id)
        self.assertEqual(cm.exception.code, "E_DOC_GIA_NELLO_STATO")
        self.assertEqual(self._stato(), "CONFERMATO")

    def test_conferma_ordine_inesistente(self) -> None:
        self._concedi_emetti_ordine()
        with self.assertRaises(ServiceError) as cm:
            ordini_service.conferma(2_000_000_000)
        self.assertEqual(cm.exception.code, "E_ORD_NOT_FOUND")

    # Lo stato che il vocabolario non ha: lo dice il verbo, il service non ne
    # ha una copia (brief-modello-documento-vendita §9.9).
    def test_stato_inesistente(self) -> None:
        # Il savepoint: il rifiuto del verbo interrompe la transazione, e la
        # rilettura dello stato qui sotto deve poter girare.
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            ordini_service.cambia_stato(self.ordine_id, "INESISTENTE")
        self.assertEqual(cm.exception.code, "E_STATO_WORKFLOW_NON_TROVATO")
        self.assertEqual(self._stato(), "DRAFT")
