# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test eliminazione di una singola fattura dal lotto (perimetro
#        pre-fiscale: lotto E fattura DRAFT o EMESSA). Le precondizioni sono
#        del DB (`script.fn_check_fattura_eliminabile_da_lotto`): qui si
#        verifica solo il guard sui parametri e il pass-through del risultato.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LottoResetFatturaServiceUnitTests.test_elimina_fattura_requires_ids
2) LottoResetFatturaServiceUnitTests.test_elimina_fattura_ok_quattro_contatori
"""

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services.lotto_reset_service import LottoResetService


class LottoResetFatturaServiceUnitTests(SimpleTestCase):
    # Scopo: Guard sui parametri — id assenti o <= 0 non arrivano al repository.
    def test_elimina_fattura_requires_ids(self):
        repo = MagicMock()
        service = LottoResetService(repository=repo)

        with self.assertRaises(ServiceError) as exc:
            service.elimina_fattura_da_lotto(lotto_id=0, fattura_id=0)

        self.assertEqual(exc.exception.code, "E_RESET_LOTTO_FATTURA_VALIDATION")
        repo.elimina_fattura_da_lotto.assert_not_called()

    # Scopo: Pass-through del risultato con TUTTI e quattro i contatori.
    #        Il mock deve avere la forma vera di `EliminaFatturaDaLottoResult`
    #        (DB 2026-08-04, slice 6-B): fino a ieri ne restituiva tre e
    #        `riemesse_attivita` — il contatore che l'operatore legge nel toast
    #        di esito — passava senza che nessuno lo guardasse. Un fixture che
    #        riproduce una forma impossibile in produzione non verifica il
    #        codice: conferma un comportamento che non esiste.
    def test_elimina_fattura_ok_quattro_contatori(self):
        repo = MagicMock()
        repo.elimina_fattura_da_lotto.return_value = {
            "updated_attivita": 1,
            "deleted_fatture": 1,
            "deleted_righe": 3,
            # Attivita' di commessa tornate NON_EMESSA: fatto distinto dalle
            # attivita' sbloccate, per questo i due contatori restano separati.
            "riemesse_attivita": 2,
        }
        service = LottoResetService(repository=repo)

        result = service.elimina_fattura_da_lotto(lotto_id=10, fattura_id=22)

        repo.elimina_fattura_da_lotto.assert_called_once_with(10, 22)
        # Valori distinti fra loro: con quattro `1` un pass-through che
        # scambiasse due chiavi passerebbe comunque.
        self.assertEqual(
            result,
            {
                "updated_attivita": 1,
                "deleted_fatture": 1,
                "deleted_righe": 3,
                "riemesse_attivita": 2,
            },
        )
