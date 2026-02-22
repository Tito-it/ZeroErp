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
"""

from django.test import SimpleTestCase

from apps.vendite.services.lotto_segnalazioni_service import LottoSegnalazioniService


class LottoSegnalazioniServiceUnitTests(SimpleTestCase):
    class _RepoMock:
        # Scopo: Restituisce riepilogo segnalazioni lotto per severita`.
        def get_lotto_segnalazioni_summary(self, lotto_id):
            return {
                "fatture_critical_count": 0,
                "fatture_warning_count": 0,
                "lotto_critical_count": 0,
                "lotto_warning_count": 0,
                "lotto_info_count": 0,
            }

        # Scopo: Conta le fatture del lotto con stato_esecuzione='ERRORE' nella tabella ponte.
        def count_fatture_stato_esecuzione_errore(self, lotto_id):
            return 0

    # Scopo: Verifica il caso `test_evaluate_lotto_status_blocks_when_critical_exists`.
    def test_evaluate_lotto_status_blocks_when_critical_exists(self):
        class _CriticalRepo(self._RepoMock):
            # Scopo: Restituisce riepilogo segnalazioni lotto per severita`.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                return {
                    "fatture_critical_count": 1,
                    "fatture_warning_count": 2,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 3,
                    "lotto_info_count": 4,
                }

        service = LottoSegnalazioniService(_CriticalRepo())
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.critical_count, 1)
        self.assertEqual(status.warning_count, 5)
        self.assertEqual(status.attention_count, 4)
        self.assertTrue(status.is_error)
        self.assertTrue(status.blocks_next_step)

    # Scopo: Verifica il caso `test_evaluate_lotto_status_allows_when_only_warning_and_info`.
    def test_evaluate_lotto_status_allows_when_only_warning_and_info(self):
        class _NoCriticalRepo(self._RepoMock):
            # Scopo: Restituisce riepilogo segnalazioni lotto per severita`.
            def get_lotto_segnalazioni_summary(self, lotto_id):
                return {
                    "fatture_critical_count": 0,
                    "fatture_warning_count": 2,
                    "lotto_critical_count": 0,
                    "lotto_warning_count": 1,
                    "lotto_info_count": 6,
                }

        service = LottoSegnalazioniService(_NoCriticalRepo())
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.critical_count, 0)
        self.assertEqual(status.warning_count, 3)
        self.assertEqual(status.attention_count, 6)
        self.assertFalse(status.is_error)
        self.assertFalse(status.blocks_next_step)

    # Scopo: Verifica che la presenza di fatture con stato_esecuzione=ERRORE blocchi il lotto
    # anche in assenza di segnalazioni critical nei log (guard unificata PRE-1).
    def test_evaluate_lotto_status_blocks_when_fatture_stato_esecuzione_errore(self):
        class _StatoEsecuzioneErroreRepo(self._RepoMock):
            # Scopo: Conta le fatture con stato_esecuzione='ERRORE' nella tabella ponte.
            def count_fatture_stato_esecuzione_errore(self, lotto_id):
                return 2

        service = LottoSegnalazioniService(_StatoEsecuzioneErroreRepo())
        status = service.evaluate_lotto_status(10)

        self.assertEqual(status.critical_count, 0)
        self.assertEqual(status.fatture_stato_esecuzione_errore_count, 2)
        self.assertTrue(status.is_error)
        self.assertTrue(status.blocks_next_step)
