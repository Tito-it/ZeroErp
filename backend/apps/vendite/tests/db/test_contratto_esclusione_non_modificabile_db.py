# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: L'ESCLUSIONE E' SOLO «NON SI VENDE», vista dal backend sul DATABASE
#        VERO, sul contratto e sull'offerta (decisioni di Tid del 2026-10-04:
#        brief-db-contratto-esclusione-non-modificabile e
#        brief-db-righe-esclusione-solo-non-si-vende):
#          · «Escludi» crea l'esclusione VUOTA, e passa;
#          · un'esclusione con un dato di fatturazione la rifiuta il guard DB,
#            col campo (E_RIGA_ESCLUSIONE_CON_DATI);
#          · il PATCH di un'esclusione lo rifiuta il guard `_a05_`
#            (E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE), anche sul prezzo: fino
#            al 2026-10-04 lo rifiutava il service con un 400 suo, che invitava
#            a togliere il prezzo e riprovare.
#
# 🔴 PERCHE' SUL DB VERO. Le tre regole vivono nei trigger: il backend deve solo
#    lasciarle passare col loro codice e il loro campo, attraverso i mapper dei
#    due service. Un repository mockato non le vede.
#
# ⭐ Il mondo si COSTRUISCE (regola zero), con la fixture del test gemello
#    `test_righe_erogazione_obbligatoria_db` (importata, non ricopiata).
#    Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) test_contratto_escludi_crea_l_esclusione_vuota
2) test_contratto_esclusione_con_quantita_rifiutata_col_campo
2b) test_contratto_esclusione_con_prezzo_rifiutata_col_campo
3) test_contratto_patch_del_prezzo_dell_esclusione_rifiutato
4) test_offerta_escludi_crea_l_esclusione_vuota
5) test_offerta_esclusione_con_fonte_rifiutata_col_campo
6) test_offerta_patch_dell_esclusione_rifiutato
"""
from __future__ import annotations

import unittest
from collections.abc import Callable

from django.db import connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto
from apps.vendite.services.contratti_service import ContrattiService
from apps.vendite.services.offerte_service import OfferteService
# ⚠️ Il MODULO, non la classe: una classe di test importata qui verrebbe
#    scoperta e girata una seconda volta.
from apps.vendite.tests.db import test_righe_erogazione_obbligatoria_db as _gemello

_CODICE_NON_MODIFICABILE = "E_CONTRATTO_ESCLUSIONE_NON_MODIFICABILE"
_CODICE_CON_DATI = "E_RIGA_ESCLUSIONE_CON_DATI"

# I nove dati di fatturazione che un'esclusione non porta (CHECK
# `chk_*_esclusione_senza_dati`; `competenza_canone` ritirata dal `20261029-26`).
_DATI_FATTURAZIONE = (
    "prezzo_unitario", "quantita", "qta_operativa", "uom_operativa_id", "factor_to_base",
    "tipo_erogazione", "fonte_quantita_attesa", "periodicita", "generazione_canone",
)

_FIXTURE = _gemello._FIXTURE
_contratto = _gemello.RigheErogazioneObbligatoriaDbTests._contratto
_offerta = _gemello.RigheErogazioneObbligatoriaDbTests._offerta


# Scopo: il payload di «Escludi»: l'articolo e il tipo, nient'altro.
def _escludi(cur) -> dict:
    cur.execute("SELECT id FROM _a")
    return {"articolo_id": str(cur.fetchone()[0]), "tipo_eccezione": "ESCLUSIONE"}


class EsclusioneSoloNonSiVendeDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto("dbops.fn_pgtap_crea_mondo_cliente(text,character varying)")

    # Scopo: costruisce il mondo, lancia `azione(cur)` e ritorna cio' che
    #        rende. Il blocco viene annullato.
    def _nel_mondo(self, azione: Callable):
        esito = None
        try:
            with transaction.atomic(), connection.cursor() as cur:
                for sql in _FIXTURE:
                    cur.execute(sql)
                esito = azione(cur)
                raise Annulla
        except Annulla:
            pass
        return esito

    # Scopo: come `_nel_mondo`, ma `azione` deve sollevare: ritorna l'errore.
    def _errore(self, azione: Callable) -> ServiceError:
        def _attesa(cur):
            with self.assertRaises(ServiceError) as ctx:
                azione(cur)
            return ctx.exception
        return self._nel_mondo(_attesa)

    # Scopo: i dati di fatturazione della riga, tutti vuoti.
    def _assert_vuota(self, cur, tabella: str, riga_id: int) -> None:
        cur.execute(
            f"SELECT {', '.join(_DATI_FATTURAZIONE)} FROM vendite.{tabella} WHERE id = %s",
            [riga_id],
        )
        valori = dict(zip(_DATI_FATTURAZIONE, cur.fetchone(), strict=True))
        self.assertEqual({k: v for k, v in valori.items() if v is not None}, {})

    # ── contratto ──────────────────────────────────────────────

    # 1. «Escludi» passa, e nessun trigger riempie la riga.
    def test_contratto_escludi_crea_l_esclusione_vuota(self):
        def azione(cur):
            riga = ContrattiService().create_riga(_contratto(cur), _escludi(cur))
            self._assert_vuota(cur, "contratti_righe", riga["id"])
        self._nel_mondo(azione)

    # 2. Il vecchio «Escludi» (quantita' 1): rifiutato col campo.
    def test_contratto_esclusione_con_quantita_rifiutata_col_campo(self):
        def azione(cur):
            ContrattiService().create_riga(
                _contratto(cur), {**_escludi(cur), "qta_operativa": "1"},
            )
        errore = self._errore(azione)
        self.assertEqual(errore.code, _CODICE_CON_DATI)
        self.assertTrue(set(errore.fields or ()) & set(_DATI_FATTURAZIONE))

    # 2b. Il prezzo in create: parla il guard DB col campo, non un 400 del
    #     service (ritirato il 2026-10-04, R-BE-3: stessa regola, altro codice).
    def test_contratto_esclusione_con_prezzo_rifiutata_col_campo(self):
        def azione(cur):
            ContrattiService().create_riga(
                _contratto(cur), {**_escludi(cur), "prezzo_unitario": "10"},
            )
        errore = self._errore(azione)
        self.assertEqual(errore.code, _CODICE_CON_DATI)
        self.assertIn("prezzo_unitario", errore.fields or ())

    # 3. Un'esclusione non si modifica: sul prezzo parla il guard `_a05_`, prima
    #    del CHECK sul prezzo e senza il vecchio 400 del service.
    def test_contratto_patch_del_prezzo_dell_esclusione_rifiutato(self):
        def azione(cur):
            contratto_id = _contratto(cur)
            riga = ContrattiService().create_riga(contratto_id, _escludi(cur))
            ContrattiService().update_riga(contratto_id, riga["id"], {"prezzo_unitario": "10"})
        self.assertEqual(self._errore(azione).code, _CODICE_NON_MODIFICABILE)

    # ── offerta: le stesse tre regole ──────────────────────────

    # 4. «Escludi» sull'offerta passa vuoto: la fonte non si pretende piu'.
    def test_offerta_escludi_crea_l_esclusione_vuota(self):
        def azione(cur):
            riga = OfferteService().crea_eccezione(_offerta(cur), _escludi(cur))
            self._assert_vuota(cur, "offerte_commerciali_eccezioni", riga["id"])
        self._nel_mondo(azione)

    # 5. Il vecchio form dell'offerta (fonte sull'esclusione): rifiutato col campo.
    def test_offerta_esclusione_con_fonte_rifiutata_col_campo(self):
        def azione(cur):
            OfferteService().crea_eccezione(
                _offerta(cur), {**_escludi(cur), "fonte_quantita_attesa": "FISSA"},
            )
        errore = self._errore(azione)
        self.assertEqual(errore.code, _CODICE_CON_DATI)
        self.assertIn("fonte_quantita_attesa", errore.fields or ())

    # 6. Sull'offerta, come sul contratto, l'esclusione non si modifica.
    def test_offerta_patch_dell_esclusione_rifiutato(self):
        def azione(cur):
            offerta = _offerta(cur)
            riga = OfferteService().crea_eccezione(offerta, _escludi(cur))
            OfferteService().aggiorna_eccezione(offerta, riga["id"], {"ordine": 5})
        self.assertEqual(self._errore(azione).code, _CODICE_NON_MODIFICABILE)


if __name__ == "__main__":
    unittest.main()
