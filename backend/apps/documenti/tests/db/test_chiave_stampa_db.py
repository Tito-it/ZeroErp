# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La CHIAVE con cui una stampa cita il suo documento, sul DB vero:
#        `DocumentiRepository.chiave_sorgente` (wrapper di
#        `script.fn_sorgente_chiave`) dà la colonna del `key_selector` del
#        tipo, e progressivo e lista contano su quella colonna.
# Note: ⭐ Giro D.1 di brief-db-sorgente-documento-e-riga (2026-11-07): la
#        stampa di un tipo a chiave id (ordine, DDT, contratto, fattura) sta in
#        `sorgente_id`, quella di un tipo a chiave uid (preventivo, offerta) in
#        `sorgente_uid`, mai tutte e due. Gli altri test sul DB stampano solo
#        preventivi: il ramo a chiave id qui si COSTRUISCE, con un ordine vero.
#        ⛔ I mock vedono l'SQL scritto, non se la colonna esiste e se il
#        cast regge: lo sa solo PostgreSQL.
# ------------------------------------------------------------
"""Indice test (su DB provvisto, `ZEROERP_TEST_DB_E2E=1`).

1. test_tipo_a_chiave_id
     ordine: dall'id e dall'uid la stessa coppia (id, NULL); progressivo e
     lista eseguono sulla colonna dell'id.
2. test_tipo_a_chiave_uid
     preventivo: dall'id la coppia (NULL, uid); progressivo e lista eseguono
     sulla colonna dell'uid.
"""

from __future__ import annotations

from unittest import TestCase

from django.db import connection

from apps.config.sorgenti import SORGENTE_ORDINE_VENDITA, SORGENTE_PREVENTIVO
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.documenti.db.documenti_repository import DocumentiRepository


class ChiaveStampaDbTests(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        richiedi_db_provvisto("script.fn_sorgente_chiave(bigint,text)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.repo = DocumentiRepository()

    def _tipo(self, codice: str) -> int:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT id FROM config.sorgenti WHERE codice_interno = %s", [codice],
            )
            riga = cur.fetchone()
        self.assertIsNotNone(riga, f"tipo {codice} assente dal catalogo")
        return int(riga[0])

    # Scopo: progressivo e lista sulla coppia data, eseguiti davvero. Non si
    #        guarda quante righe: si guarda che l'SQL composto regga.
    def _letture_eseguono(self, tipo: int, chiave: tuple[int | None, str | None]) -> None:
        sorgente_id, sorgente_uid = chiave
        self.assertEqual(
            self.repo.next_progressivo_sorgente(
                sorgente_tipo_id=tipo, sorgente_id=sorgente_id,
                sorgente_uid=sorgente_uid, sorgente_riga=None,
            ),
            1,
        )
        righe, totale = self.repo.list_documenti_per_sorgente(
            sorgente_tipo_id=tipo, sorgente_id=sorgente_id, sorgente_uid=sorgente_uid,
            sorgente_riga=None, emittente_ids_scope=None, limit=5, offset=0,
        )
        self.assertEqual((righe, totale), ([], 0))

    # 1. Un tipo a chiave id: l'ordine.
    def test_tipo_a_chiave_id(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT ordine_id, ordine_uid::text"
                "  FROM dbops.fn_pgtap_crea_ordine('chiave stampa ordine')"
            )
            ordine_id, ordine_uid = cur.fetchone()
        tipo = self._tipo(SORGENTE_ORDINE_VENDITA)

        dall_id = self.repo.chiave_sorgente(sorgente_tipo_id=tipo, chiave=str(ordine_id))
        self.assertEqual(dall_id, (int(ordine_id), None))
        # Una chiave dell'altra specie si traduce: la stessa coppia.
        self.assertEqual(
            self.repo.chiave_sorgente(sorgente_tipo_id=tipo, chiave=ordine_uid), dall_id,
        )
        self._letture_eseguono(tipo, dall_id)

    # 2. Un tipo a chiave uid: il preventivo.
    def test_tipo_a_chiave_uid(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT preventivo_id, preventivo_uid::text"
                "  FROM dbops.fn_pgtap_crea_preventivo('chiave stampa preventivo')"
            )
            preventivo_id, preventivo_uid = cur.fetchone()
        tipo = self._tipo(SORGENTE_PREVENTIVO)

        chiave = self.repo.chiave_sorgente(sorgente_tipo_id=tipo, chiave=str(preventivo_id))
        self.assertEqual(chiave, (None, preventivo_uid))
        self._letture_eseguono(tipo, chiave)
