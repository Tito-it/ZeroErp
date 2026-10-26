# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cambio di stato del preventivo DAL VERBO sul DATABASE PROVVISTO
#        (brief-modello-documento-vendita §8.7, giro 6): `preventivi_service`
#        arriva a `vendite.fn_cambia_stato_preventivo` con la firma a due
#        argomenti, l'accettazione scrive la modalita' di fatturazione e passa
#        lo stato, un ACCETTATO si aggiorna senza passare dal verbo, e lo stato
#        di emissione dal cambio stato generico e' un 400 letto dal
#        vocabolario. E' la giuntura Python↔PL/pgSQL che i test del service
#        (mock) non vedono: la firma del verbo, la porta, i lettori.
# Note: ⚠️ Le REGOLE del verbo (matrice, azione, porta) le provano i pgTAP
#       `script/test-doc-lettori-stato-e-preventivo-al-modello-v1` e
#       `vendite/test-fn-cambia-stato-preventivo`. Il preventivo nasce EMESSO
#       con una riga da `dbops.fn_pgtap_crea_preventivo_con_righe`, che apre il
#       contesto sull'operatore del mondo. Transazione SEMPRE annullata.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) PreventivoCambiaStatoDbTests.test_accettazione_dal_verbo
2) PreventivoCambiaStatoDbTests.test_accettato_si_aggiorna_senza_il_verbo — §8.7 punto 5
3) PreventivoCambiaStatoDbTests.test_lo_stato_di_emissione_e_un_400 — M-2 dal vocabolario
4) PreventivoCambiaStatoDbTests.test_il_secondo_emetti_e_rifiutato — §9.10
"""
from __future__ import annotations

import unittest
from datetime import date

from django.db import DatabaseError, connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.services import preventivi_service


class PreventivoCambiaStatoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda sulla firma FINALE del verbo (due argomenti, giro 6).
        richiedi_db_provvisto("vendite.fn_cambia_stato_preventivo(bigint,character varying)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT preventivo_id FROM dbops.fn_pgtap_crea_preventivo_con_righe("
                "'BE cambia stato preventivo', 'EMESSO')",
            )
            self.preventivo_id = int(cur.fetchone()[0])

    def _stato(self) -> tuple[str, bool, date | None]:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT s.codice_interno, p.fatturazione_immediata, p.competenza_mese
                  FROM vendite.preventivi p
                  JOIN config.stati_doc_preventivi s ON s.id = p.stato_doc_preventivo_id
                 WHERE p.id = %s
                """,
                [self.preventivo_id],
            )
            codice, immediata, competenza = cur.fetchone()
        return codice, immediata, competenza

    def test_accettazione_dal_verbo(self) -> None:
        out = preventivi_service.cambia_stato(
            self.preventivo_id, "ACCETTATO",
            fatturazione_immediata=False, competenza_mese=date(2026, 11, 1),
        )
        self.assertEqual(out["stato_precedente"], "EMESSO")
        self.assertEqual(out["stato_nuovo"], "ACCETTATO")
        self.assertEqual(self._stato(), ("ACCETTATO", False, date(2026, 11, 1)))

    def test_accettato_si_aggiorna_senza_il_verbo(self) -> None:
        preventivi_service.cambia_stato(
            self.preventivo_id, "ACCETTATO",
            fatturazione_immediata=False, competenza_mese=date(2026, 11, 1),
        )
        # Fino al giro 6 la seconda richiesta chiamava il verbo con lo stesso
        # stato, e la matrice (senza ACCETTATO -> ACCETTATO) la rifiutava.
        out = preventivi_service.cambia_stato(
            self.preventivo_id, "ACCETTATO",
            fatturazione_immediata=False, competenza_mese=date(2026, 12, 1),
        )
        self.assertEqual(out["stato_precedente"], "ACCETTATO")
        self.assertEqual(out["stato_nuovo"], "ACCETTATO")
        self.assertEqual(self._stato(), ("ACCETTATO", False, date(2026, 12, 1)))

    def test_lo_stato_di_emissione_e_un_400(self) -> None:
        with self.assertRaises(ServiceError) as cm:
            preventivi_service.cambia_stato(self.preventivo_id, "EMESSO")
        self.assertEqual(cm.exception.code, "E_PREV_VALIDAZIONE")
        self.assertEqual(cm.exception.context.get("field"), "nuovo_stato")
        self.assertEqual(self._stato()[0], "EMESSO")

    # Il preventivo del mondo nasce EMESSO: un «Emetti» su di lui e' il secondo,
    # e lo rifiuta la prima riga del verbo (brief-modello-documento-vendita
    # §9.10). Il service non traduce: il codice viaggia nel campo dedicato
    # dell'eccezione, e il PDF non nasce perche' la view lo genera solo dopo
    # il verbo, nella stessa transazione.
    def test_il_secondo_emetti_e_rifiutato(self) -> None:
        with self.assertRaises(DatabaseError) as cm, transaction.atomic():
            preventivi_service.emetti(self.preventivo_id)
        diag = getattr(cm.exception.__cause__, "diag", None)
        self.assertEqual(getattr(diag, "constraint_name", None), "E_DOC_GIA_NELLO_STATO")
        self.assertEqual(self._stato()[0], "EMESSO")
