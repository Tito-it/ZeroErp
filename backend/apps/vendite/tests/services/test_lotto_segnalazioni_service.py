# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari valutazione segnalazioni lotto per blocco avanzamento step pipeline.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LottoSegnalazioniServiceUnitTests.test_evaluate_lotto_status_blocks_when_critical_exists
2) LottoSegnalazioniServiceUnitTests.test_evaluate_lotto_status_allows_when_only_warning_and_info
3) LottoSegnalazioniServiceUnitTests.test_evaluate_lotto_status_blocks_when_fatture_stato_esecuzione_errore
4) LottoSegnalazioniServiceUnitTests.test_evaluate_lotto_status_blocks_when_esiti_stato_esecuzione_errore (D2)
5) LottoSegnalazioniServiceUnitTests.test_evaluate_lotto_status_allows_when_everything_is_zero
"""

from django.test import SimpleTestCase

from apps.vendite.services.lotto_segnalazioni_service import LottoSegnalazioniService


# Scopo: il riepilogo a DIECI chiavi, tutto a zero, con gli override del caso.
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


class LottoSegnalazioniServiceUnitTests(SimpleTestCase):
    # Scopo: Verifica il caso `test_evaluate_lotto_status_blocks_when_critical_exists`.
    def test_evaluate_lotto_status_blocks_when_critical_exists(self):
        service = LottoSegnalazioniService(_Repo(_summary(
            fatture_critical_count=1, fatture_warning_count=2,
            lotto_warning_count=3, lotto_info_count=4,
        )))
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.critical_count, 1)
        self.assertEqual(status.warning_count, 5)
        self.assertEqual(status.attention_count, 4)
        self.assertTrue(status.is_error)
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

    # Scopo: Verifica che la presenza di fatture con stato_esecuzione=ERRORE blocchi il lotto
    # anche in assenza di segnalazioni critical nei log (guard unificata PRE-1).
    def test_evaluate_lotto_status_blocks_when_fatture_stato_esecuzione_errore(self):
        service = LottoSegnalazioniService(_Repo(_summary(
            fatture_stato_esecuzione_errore_count=2,
        )))
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.critical_count, 0)
        self.assertEqual(status.fatture_stato_esecuzione_errore_count, 2)
        self.assertTrue(status.is_error)
        self.assertTrue(status.blocks_next_step)

    # Scopo: ⭐ D2 (2026-09-12) — un documento preso in carico il cui ULTIMO
    #        esito e' ERRORE blocca il lotto ANCHE con zero critiche vive e
    #        zero fatture in errore. E' il caso che prima chiudeva COMPLETATO:
    #        il runner ritira le proprie bandiere all'avvio del rerun, il giro
    #        non rivede il documento, nessuno le rialza — e l'esito, l'unica
    #        traccia durevole, non contava. Un lotto non e' a posto per
    #        sottrazione.
    # ⚠️ Il caso e' costruito con TUTTI gli altri addendi a zero, di proposito:
    #        con una critica viva accanto il test sarebbe verde anche senza
    #        il terzo addendo, cioe' non deciderebbe niente.
    def test_evaluate_lotto_status_blocks_when_esiti_stato_esecuzione_errore(self):
        service = LottoSegnalazioniService(_Repo(_summary(
            documenti_presi_in_carico_count=2,
            esiti_stato_esecuzione_errore_count=1,
        )))
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.critical_count, 0)
        self.assertEqual(status.fatture_stato_esecuzione_errore_count, 0)
        self.assertEqual(status.esiti_stato_esecuzione_errore_count, 1)
        self.assertTrue(status.is_error)
        self.assertTrue(status.blocks_next_step)
        # Il riepilogo viaggia intero: e' cio' che l'API consegna al client.
        self.assertEqual(status.summary["esiti_stato_esecuzione_errore_count"], 1)

    # Scopo: il contrario del precedente — a tutto zero il lotto e' a posto.
    #        Presidia che il terzo addendo non renda `is_error` vero per
    #        costruzione (un `>= 0` al posto di `> 0` passerebbe i test sopra).
    def test_evaluate_lotto_status_allows_when_everything_is_zero(self):
        service = LottoSegnalazioniService(_Repo(_summary(
            documenti_presi_in_carico_count=3,
        )))
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.esiti_stato_esecuzione_errore_count, 0)
        self.assertFalse(status.is_error)
        self.assertFalse(status.blocks_next_step)
