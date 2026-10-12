# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `RigheDocumentoRepositoryMixin.scrivi_data_consegna` sul DATABASE
#        PROVVISTO (brief-db-date-consegna-righe-in-blocco §5, §8): la query
#        che un mock non vede, e i lock del DB che la giudicano riga per riga.
#          · la riga gia' spedita si SALTA e si conta (BF-1), l'altra si scrive;
#          · l'anteprima esegue l'UPDATE vero e lo annulla: conta come la
#            scrittura, il rifiuto del lock arriva gia' li', e niente resta;
#          · sulla riga singola la spedita NON si salta: 409 del guard di riga;
#          · un motivo di STATO non fa saltare: lo rifiuta il lock (BF-1);
#          · SOLO_VUOTE tocca le sole righe senza data, su ordine e preventivo.
# Note: ⚠️ Il mondo si COSTRUISCE (regola zero), come nel pgTAP
#       `test-data-consegna-confermata-riga-spedita-v1`: ordini che nascono
#       DRAFT e salgono con `dbops.fn_pgtap_porta_a_stato`, bolle da
#       `fn_genera_ddt_da_ordine` emesse nel verso vero; articolo NON gestito a
#       magazzino. Transazione SEMPRE annullata. Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) DateConsegnaRigheDbTests.test_ordine_la_riga_spedita_si_salta_e_si_conta
2) DateConsegnaRigheDbTests.test_ordine_riga_singola_spedita_e_409_del_guard
3) DateConsegnaRigheDbTests.test_ordine_evaso_lo_rifiuta_il_lock_non_si_salta
4) DateConsegnaRigheDbTests.test_ordine_in_bozza_solo_vuote_e_tutte
5) DateConsegnaRigheDbTests.test_ordine_confermato_la_data_richiesta_la_rifiuta_il_lock
6) DateConsegnaRigheDbTests.test_preventivo_in_bozza_solo_vuote
7) DateConsegnaRigheDbTests.test_anteprima_il_lock_rifiuta_gia_li_e_niente_resta
"""
from __future__ import annotations

import json
import unittest
from datetime import date
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.services.error_manager import ServiceError
from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.vendite.services.ordini_service import _db_errors

_CONFERMATA = "data_consegna_confermata"
_RICHIESTA = "data_consegna_richiesta_cliente"
_META = json.dumps({"test_scope": "be_date_consegna_righe_db"})


class DateConsegnaRigheDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # ── Fixture ────────────────────────────────────────────────────────

    def _mondo(self, cur: Any) -> dict[str, Any]:
        cur.execute("SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('date consegna righe db')")
        mondo = row_to_dict(cur)
        assert mondo is not None
        cur.execute("SELECT dbops.fn_pgtap_crea_articolo('BE-DC-RIGHE', false)")
        mondo["articolo_id"] = cur.fetchone()[0]
        cur.execute("SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1")
        mondo["iva_id"] = cur.fetchone()[0]
        return mondo

    # Un ordine con due righe (10 e 5) e le date date; nasce DRAFT, poi lo stato.
    def _ordine(
        self, cur: Any, mondo: dict[str, Any], stato: str,
        *, confermate: tuple[date | None, date | None] = (None, None),
        richieste: tuple[date | None, date | None] = (None, None),
    ) -> tuple[int, int, int]:
        cur.execute("""
            INSERT INTO vendite.ordini (billing_account_id, stato_doc_ordine_id,
                valuta_id, data, emittente_fiscale_id, storicizza, meta)
            VALUES (%s, (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'DRAFT'),
                    (SELECT id FROM config.valute ORDER BY id LIMIT 1),
                    DATE '2026-10-01', %s, false, %s::jsonb)
            RETURNING id
        """, [mondo["billing_account_id"], mondo["emittente_fiscale_id"], _META])
        ordine_id = cur.fetchone()[0]
        righe = []
        for nr, qta in ((1, 10), (2, 5)):
            cur.execute("""
                INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
                    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza,
                    data_consegna_confermata, data_consegna_richiesta_cliente, meta)
                VALUES (%s, %s, %s, %s, %s, %s, 20, %s, true, false, %s, %s, %s::jsonb)
                RETURNING id
            """, [ordine_id, nr, mondo["articolo_id"], f"Riga {nr} BE date consegna",
                  qta, qta, mondo["iva_id"], confermate[nr - 1], richieste[nr - 1], _META])
            righe.append(cur.fetchone()[0])
        if stato != "DRAFT":
            cur.execute("SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini', %s, %s)",
                        [ordine_id, stato])
        return ordine_id, righe[0], righe[1]

    # Una bolla dall'ordine per le quantita' date, emessa nel verso vero.
    def _spedisci(self, cur: Any, ordine_id: int, evasioni: list[tuple[int, int]]) -> None:
        cur.execute(
            "SELECT vendite.fn_genera_ddt_da_ordine(%s, %s::jsonb, DATE '2026-10-02')",
            [ordine_id, json.dumps([
                {"ordine_riga_id": riga_id, "qta_da_evadere": qta} for riga_id, qta in evasioni
            ])],
        )
        ddt_id = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
            VALUES (%s, (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'CON'),
                    '{"display":"CON"}'::jsonb)
            ON CONFLICT DO NOTHING
        """, [ddt_id])
        cur.execute("""
            UPDATE vendite.ddt SET causale_trasporto_id =
                (SELECT id FROM config.causali_trasporto WHERE codice = 'VENDITA' ORDER BY id LIMIT 1)
             WHERE id = %s
        """, [ddt_id])
        cur.execute("""
            UPDATE vendite.ddt SET stato_doc_ddt_id =
                (SELECT id FROM config.stati_doc_ddt WHERE codice_interno = 'EMESSO')
             WHERE id = %s
        """, [ddt_id])

    def _date(self, cur: Any, tabella: str, colonna: str, ids: tuple[int, ...]) -> list[Any]:
        cur.execute(
            f"SELECT {colonna} FROM {tabella} WHERE id = ANY(%s) ORDER BY id",
            [list(ids)],
        )
        return [r[0] for r in cur.fetchall()]

    # Il rifiuto del DB, tradotto come lo traduce il service (il codice al client).
    def _codice_rifiuto(self, scrittura: Any) -> str:
        with self.assertRaises(ServiceError) as cm, transaction.atomic(), _db_errors("test"):
            scrittura()
        return cm.exception.code

    # ── Test ───────────────────────────────────────────────────────────

    def test_ordine_la_riga_spedita_si_salta_e_si_conta(self) -> None:
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    mondo = self._mondo(cur)
                    d = date(2026, 11, 20)
                    ordine_id, r1, r2 = self._ordine(cur, mondo, "CONFERMATO", confermate=(d, d))
                    # P-1: spedita IN PARTE (4 di 10) basta a fermarla.
                    self._spedisci(cur, ordine_id, [(r1, 4)])
                    repo = OrdiniRepository()
                    nuova = date(2026, 12, 1)

                    anteprima = repo.scrivi_data_consegna(ordine_id, _CONFERMATA, nuova, anteprima=True)
                    self.assertEqual(anteprima, {"aggiornate": 1, "saltate": 1})
                    self.assertEqual(self._date(cur, "vendite.ordini_righe", _CONFERMATA, (r1, r2)), [d, d])

                    esito = repo.scrivi_data_consegna(ordine_id, _CONFERMATA, nuova)
                    self.assertEqual(esito, {"aggiornate": 1, "saltate": 1})
                    self.assertEqual(
                        self._date(cur, "vendite.ordini_righe", _CONFERMATA, (r1, r2)), [d, nuova],
                    )
            finally:
                transaction.set_rollback(True)

    def test_ordine_riga_singola_spedita_e_409_del_guard(self) -> None:
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    mondo = self._mondo(cur)
                    d = date(2026, 11, 20)
                    ordine_id, r1, _ = self._ordine(cur, mondo, "CONFERMATO", confermate=(d, d))
                    self._spedisci(cur, ordine_id, [(r1, 4)])
                    codice = self._codice_rifiuto(lambda: OrdiniRepository().scrivi_data_consegna(
                        ordine_id, _CONFERMATA, date(2026, 12, 1), riga_id=r1,
                    ))
                    self.assertEqual(codice, "E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA")
            finally:
                transaction.set_rollback(True)

    def test_ordine_evaso_lo_rifiuta_il_lock_non_si_salta(self) -> None:
        # BF-1: spedito per intero l'ordine e' EVASO, e il primo motivo e' lo
        # STATO. Saltare per «check <> []» darebbe «0 aggiornate, 2 spedite»:
        # invece la riga va all'UPDATE e il lock la rifiuta.
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    mondo = self._mondo(cur)
                    d = date(2026, 11, 20)
                    ordine_id, r1, r2 = self._ordine(cur, mondo, "CONFERMATO", confermate=(d, d))
                    self._spedisci(cur, ordine_id, [(r1, 10), (r2, 5)])
                    codice = self._codice_rifiuto(lambda: OrdiniRepository().scrivi_data_consegna(
                        ordine_id, _CONFERMATA, date(2026, 12, 1),
                    ))
                    self.assertEqual(codice, "E_RIGA_DOC_NON_BOZZA")
            finally:
                transaction.set_rollback(True)

    def test_ordine_in_bozza_solo_vuote_e_tutte(self) -> None:
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    mondo = self._mondo(cur)
                    scritta = date(2026, 11, 15)
                    ordine_id, r1, r2 = self._ordine(cur, mondo, "DRAFT", richieste=(None, scritta))
                    repo = OrdiniRepository()
                    nuova = date(2026, 11, 20)

                    esito = repo.scrivi_data_consegna(ordine_id, _RICHIESTA, nuova, solo_vuote=True)
                    self.assertEqual(esito, {"aggiornate": 1, "saltate": 0})
                    self.assertEqual(
                        self._date(cur, "vendite.ordini_righe", _RICHIESTA, (r1, r2)), [nuova, scritta],
                    )

                    # In bozza la check di riga non ha motivi: la confermata si
                    # scrive su tutte e due.
                    esito = repo.scrivi_data_consegna(ordine_id, _CONFERMATA, nuova)
                    self.assertEqual(esito, {"aggiornate": 2, "saltate": 0})
                    esito = repo.scrivi_data_consegna(ordine_id, _RICHIESTA, date(2026, 11, 22))
                    self.assertEqual(esito, {"aggiornate": 2, "saltate": 0})
            finally:
                transaction.set_rollback(True)

    def test_ordine_confermato_la_data_richiesta_la_rifiuta_il_lock(self) -> None:
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    mondo = self._mondo(cur)
                    ordine_id, _, _ = self._ordine(cur, mondo, "CONFERMATO")
                    codice = self._codice_rifiuto(lambda: OrdiniRepository().scrivi_data_consegna(
                        ordine_id, _RICHIESTA, date(2026, 12, 1),
                    ))
                    self.assertEqual(codice, "E_RIGA_DOC_NON_BOZZA")
            finally:
                transaction.set_rollback(True)

    def test_preventivo_in_bozza_solo_vuote(self) -> None:
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    mondo = self._mondo(cur)
                    cur.execute("SELECT * FROM dbops.fn_pgtap_crea_preventivo('date consegna righe db')")
                    prev = row_to_dict(cur)
                    assert prev is not None
                    scritta = date(2026, 11, 15)
                    righe = []
                    for nr, data_richiesta in ((1, None), (2, scritta)):
                        cur.execute("""
                            INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id,
                                descrizione, quantita, qta_operativa, prezzo_unitario, iva_id,
                                ordine, meta, data_consegna_richiesta_cliente)
                            VALUES (%s, %s, %s, 1, 1, 20, %s, %s, %s::jsonb, %s)
                            RETURNING id
                        """, [prev["preventivo_id"], mondo["articolo_id"], f"Riga {nr}",
                              mondo["iva_id"], nr, _META, data_richiesta])
                        righe.append(cur.fetchone()[0])
                    nuova = date(2026, 11, 20)
                    esito = PreventiviRepository().scrivi_data_consegna(
                        prev["preventivo_id"], _RICHIESTA, nuova, solo_vuote=True,
                    )
                    self.assertEqual(esito, {"aggiornate": 1, "saltate": 0})
                    self.assertEqual(
                        self._date(cur, "vendite.preventivi_righe", _RICHIESTA, tuple(righe)),
                        [nuova, scritta],
                    )
            finally:
                transaction.set_rollback(True)

    def test_anteprima_il_lock_rifiuta_gia_li_e_niente_resta(self) -> None:
        # L'anteprima e' lo stesso UPDATE in un savepoint annullato: in uno
        # stato che il lock non ammette il 409 arriva PRIMA della domanda di
        # conferma (fino al 2026-10-12 contava con una SELECT e diceva un
        # numero). Dopo il rifiuto la transazione esterna resta usabile.
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    mondo = self._mondo(cur)
                    d = date(2026, 11, 20)
                    ordine_id, r1, r2 = self._ordine(cur, mondo, "CONFERMATO", confermate=(d, d))
                    repo = OrdiniRepository()
                    nuova = date(2026, 12, 1)

                    codice = self._codice_rifiuto(lambda: repo.scrivi_data_consegna(
                        ordine_id, _RICHIESTA, nuova, anteprima=True,
                    ))
                    self.assertEqual(codice, "E_RIGA_DOC_NON_BOZZA")

                    # La confermata in CONFERMATO si scrive: l'anteprima conta
                    # le due righe, e nessuna data cambia.
                    anteprima = repo.scrivi_data_consegna(ordine_id, _CONFERMATA, nuova, anteprima=True)
                    self.assertEqual(anteprima, {"aggiornate": 2, "saltate": 0})
                    self.assertEqual(
                        self._date(cur, "vendite.ordini_righe", _CONFERMATA, (r1, r2)), [d, d],
                    )
            finally:
                transaction.set_rollback(True)
