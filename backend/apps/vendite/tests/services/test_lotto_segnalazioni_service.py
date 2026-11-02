# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari valutazione segnalazioni lotto per blocco avanzamento step pipeline.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LottoSegnalazioniServiceUnitTests.test_evaluate_lotto_status_blocca_quando_il_db_dice_fermo
2) LottoSegnalazioniServiceUnitTests.test_evaluate_lotto_status_non_ricalcola_il_verdetto_dagli_addendi
3) LottoSegnalazioniServiceUnitTests.test_evaluate_lotto_status_somma_i_conteggi_per_la_frase
4) LottoSegnalazioniServiceUnitTests.test_evaluate_lotto_status_allows_when_only_warning_and_info
5) LottoSegnalazioniServiceUnitTests.test_evaluate_lotto_status_allows_when_everything_is_zero
6) LottoSegnalazioniServiceUnitTests.test_evaluate_lotto_status_trasporta_il_riepilogo_intero
"""

from django.test import SimpleTestCase

from apps.vendite.services.lotto_segnalazioni_service import LottoSegnalazioniService


# Scopo: il riepilogo a UNDICI chiavi — dieci conteggi a zero e il verdetto
#        `fermo` a `False` — con gli override del caso.
# ⚠️ Le chiavi sono quelle che `get_lotto_segnalazioni_summary` promette: una
#    fixture piu' corta passerebbe finche' il service non legge la chiave che
#    manca, e poi fallirebbe con un KeyError invece che sul verdetto.
def _summary(**override):
    base = {
        "fatture_critical_count": 0,
        "fatture_warning_count": 0,
        "lotto_critical_count": 0,
        "lotto_warning_count": 0,
        "lotto_info_count": 0,
        "fatture_stato_esecuzione_errore_count": 0,
        "documenti_bloccanti_count": 0,
        "documenti_presi_in_carico_count": 0,
        "critiche_giro_count": 0,
        "esiti_stato_esecuzione_errore_count": 0,
        "fermo": False,
    }
    sconosciute = set(override) - set(base)
    assert not sconosciute, f"chiavi non del riepilogo: {sconosciute}"
    return {**base, **override}


class _Repo:
    # Scopo: repository finto che risponde il riepilogo dato.
    def __init__(self, summary):
        self._summary = summary

    # Scopo: Restituisce riepilogo segnalazioni lotto per severita`.
    def get_lotto_segnalazioni_summary(self, lotto_id):
        return self._summary


# ⭐ Dal 2026-09-19 (D-V1 di Tid: «la regola va a DB») il verdetto NON si
#    calcola qui: `is_error` e `blocks_next_step` sono `summary["fermo"]`,
#    letto da `vendite.vw_lotti_segnalazioni_summary`. I tre addendi
#    (critiche vive, fatture in ERRORE sul ponte, esiti ERRORE) li prova il
#    pgTAP `vendite/test-lotti-fermi-verdetto-a-db-v1.sql`, caso per caso e
#    costruendoli. Qui si presidia il TRASPORTO: che il service legga il
#    verdetto e non lo ricostruisca dai conteggi.
class LottoSegnalazioniServiceUnitTests(SimpleTestCase):
    # Scopo: `fermo = true` con TUTTI i conteggi a zero blocca. E' il caso che
    #        distingue «leggo il verdetto» da «lo ricalcolo»: una copia in
    #        Python dei tre addendi qui direbbe «a posto».
    def test_evaluate_lotto_status_blocca_quando_il_db_dice_fermo(self):
        service = LottoSegnalazioniService(_Repo(_summary(fermo=True)))
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.critical_count, 0)
        self.assertEqual(status.fatture_stato_esecuzione_errore_count, 0)
        self.assertEqual(status.esiti_stato_esecuzione_errore_count, 0)
        self.assertTrue(status.is_error)
        self.assertTrue(status.blocks_next_step)

    # Scopo: il contrario — i tre addendi tutti > 0 e `fermo = false` NON
    #        blocca. Sul modello e' un caso che la vista non produce (il
    #        verdetto e' derivato da quei numeri); serve a dire che, se un
    #        giorno la vista cambiasse formula, il backend la seguirebbe
    #        invece di contraddirla con una somma sua.
    def test_evaluate_lotto_status_non_ricalcola_il_verdetto_dagli_addendi(self):
        service = LottoSegnalazioniService(_Repo(_summary(
            fatture_critical_count=1,
            lotto_critical_count=1,
            fatture_stato_esecuzione_errore_count=2,
            esiti_stato_esecuzione_errore_count=1,
            fermo=False,
        )))
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.critical_count, 2)
        self.assertFalse(status.is_error)
        self.assertFalse(status.blocks_next_step)

    # Scopo: i conteggi per la FRASE del banner si sommano come prima:
    #        critiche e avvisi per i due canali, info dal solo canale lotto.
    def test_evaluate_lotto_status_somma_i_conteggi_per_la_frase(self):
        service = LottoSegnalazioniService(_Repo(_summary(
            fatture_critical_count=1, fatture_warning_count=2,
            lotto_warning_count=3, lotto_info_count=4,
            fermo=True,
        )))
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.critical_count, 1)
        self.assertEqual(status.warning_count, 5)
        self.assertEqual(status.attention_count, 4)
        self.assertTrue(status.blocks_next_step)

    # Scopo: Verifica il caso `test_evaluate_lotto_status_allows_when_only_warning_and_info`.
    def test_evaluate_lotto_status_allows_when_only_warning_and_info(self):
        service = LottoSegnalazioniService(_Repo(_summary(
            fatture_warning_count=2, lotto_warning_count=1, lotto_info_count=6,
        )))
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.critical_count, 0)
        self.assertEqual(status.warning_count, 3)
        self.assertEqual(status.attention_count, 6)
        self.assertFalse(status.is_error)
        self.assertFalse(status.blocks_next_step)

    # Scopo: a tutto zero e `fermo = false` il lotto e' a posto.
    def test_evaluate_lotto_status_allows_when_everything_is_zero(self):
        service = LottoSegnalazioniService(_Repo(_summary(
            documenti_presi_in_carico_count=3,
        )))
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.esiti_stato_esecuzione_errore_count, 0)
        self.assertFalse(status.is_error)
        self.assertFalse(status.blocks_next_step)

    # Scopo: il riepilogo viaggia INTERO, verdetto compreso: e' cio' che l'API
    #        consegna al client (`summary` di `/lotti/<id>/segnalazioni/`).
    def test_evaluate_lotto_status_trasporta_il_riepilogo_intero(self):
        service = LottoSegnalazioniService(_Repo(_summary(
            documenti_presi_in_carico_count=2,
            esiti_stato_esecuzione_errore_count=1,
            fermo=True,
        )))
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.esiti_stato_esecuzione_errore_count, 1)
        self.assertEqual(status.summary["esiti_stato_esecuzione_errore_count"], 1)
        self.assertIs(status.summary["fermo"], True)
