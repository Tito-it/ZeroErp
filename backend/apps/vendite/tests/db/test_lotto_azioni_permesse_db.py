# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `azioni_permesse` della riga di lotto (`VenditeRepository.get_lotto` e
#        `list_lotti`, proiezione `_LOTTO_SELECT_COLS`) sul DATABASE PROVVISTO:
#        i passaggi manuali che l'operatore della sessione puo' fare dallo stato
#        del lotto, letti da `script.fn_doc_azioni_permesse`
#        (brief-modello-documento-vendita §15.14). E' la giuntura che il test
#        del mapper (riga finta) non vede: il nome della testata, il binding
#        dello stato, l'array del driver.
# Note: ⚠️ Gli attesi sono quelli della matrice di oggi
#       (`transizioni_stati_doc_fiscale`, e il pgTAP
#       `test-doc-azioni-permesse-v1.sql` che li dichiara): se Tid sposta
#       un'azione, cambia l'atteso, non il codice. Transazione annullata.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_emessa_senza_concessione — EMESSA, operatore senza numera_fatture_lotti: nessuna
2) test_emessa_con_concessione — EMESSA con numera_fatture_lotti: numera, riporta_a_draft
3) test_draft_senza_concessioni — DRAFT: annulla (riga senza azione, decide il livello)
4) test_lista_porta_lo_stesso — la riga di `list_lotti` dice quanto il dettaglio
5) test_ristampabile_solo_da_definitiva — `ristampabile`: vero sul lotto DEFINITIVA, falso altrove
"""
from __future__ import annotations

import unittest

from django.db import connection

from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.vendite_repository import STATO_DEFINITIVA, VenditeRepository


class LottoAzioniPermesseDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # Un DB indietro fallisce sull'oggetto mancante, non su un'attesa.
        richiedi_db_provvisto("script.fn_doc_azioni_permesse(regclass,bigint)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.repo = VenditeRepository()
        with connection.cursor() as cur:
            # Lo stesso contesto del pgTAP: un operatore NON superuser, senza
            # concessioni di processo. Con un superuser il permesso non si vede.
            cur.execute("SELECT script.fn_pgtap_set_contesto_operatore()")
            cur.execute("SELECT current_setting('app.current_user_id')::integer")
            self.user_id = cur.fetchone()[0]
            cur.execute("SELECT lotto_id FROM dbops.fn_pgtap_crea_lotto('azioni permesse be bozza')")
            self.draft_id = cur.fetchone()[0]
            cur.execute(
                "SELECT lotto_id FROM dbops.fn_pgtap_crea_lotto('azioni permesse be emesso', 'EMESSA')",
            )
            self.emesso_id = cur.fetchone()[0]

    def _azioni(self, lotto_id: int) -> list[str]:
        riga = self.repo.get_lotto(lotto_id=lotto_id)
        # Il caso si e' formato davvero: una riga assente (RLS, contesto) non
        # deve passare per «nessuna azione».
        self.assertIsNotNone(riga)
        assert riga is not None
        return riga["azioni_permesse"]

    def _concedi(self, codename: str) -> None:
        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_concedi_azione(%s, %s)", [self.user_id, codename])

    def test_emessa_senza_concessione(self) -> None:
        self.assertEqual(self._azioni(self.emesso_id), [])

    def test_emessa_con_concessione(self) -> None:
        self._concedi("numera_fatture_lotti")
        self.assertEqual(self._azioni(self.emesso_id), ["numera", "riporta_a_draft"])

    def test_draft_senza_concessioni(self) -> None:
        self.assertEqual(self._azioni(self.draft_id), ["annulla"])

    def test_lista_porta_lo_stesso(self) -> None:
        self._concedi("numera_fatture_lotti")
        righe, _ = self.repo.list_lotti(
            competenza_mese=None, utility_id=None, stato_lotto=None,
            area_geografica_id=None, tipo_doc_fiscale_id=None,
            emittente_soggetto_ruolo_id=None, limit=500, offset=0,
            includi_annullati=True,
        )
        per_id = {r["id"]: r["azioni_permesse"] for r in righe}
        self.assertEqual(per_id.get(self.emesso_id), ["numera", "riporta_a_draft"])
        self.assertEqual(per_id.get(self.draft_id), ["annulla"])

    # `ristampabile` (la ristampa non e' un passaggio, quindi non sta in
    # `azioni_permesse`): lo stesso stato del gate di `ristampa_lotto`.
    def test_ristampabile_solo_da_definitiva(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT lotto_id FROM dbops.fn_pgtap_crea_lotto('azioni permesse be definitivo', %s)",
                [STATO_DEFINITIVA],
            )
            definitivo_id = cur.fetchone()[0]
        for lotto_id, atteso in (
            (definitivo_id, True), (self.emesso_id, False), (self.draft_id, False),
        ):
            with self.subTest(lotto_id=lotto_id):
                riga = self.repo.get_lotto(lotto_id=lotto_id)
                assert riga is not None
                self.assertIs(riga["ristampabile"], atteso)
