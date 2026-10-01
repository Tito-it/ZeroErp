# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del regime fiscale nel service emittenti (R-1/R-2 di
#        brief-db-esigibilita-iva-per-cassa-emittente): dichiarare il regime
#        e' confermarlo, il vuoto e' un 400 sul campo, chi non lo manda non
#        conferma niente. Mock repo, no DB (il binding reale e' in
#        `tests/db/test_regime_fiscale_conferma_db.py`).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) UpdateRegimeTests.test_regime_presente_conferma
2) UpdateRegimeTests.test_regime_assente_non_conferma
3) UpdateRegimeTests.test_regime_vuoto_o_null_400_sul_campo
4) UpdateRegimeTests.test_fk_ignota_non_diventa_errore_di_regime
5) CreaRegimeTests.test_regime_presente_conferma
6) CreaRegimeTests.test_regime_assente_non_conferma
7) CreaRegimeTests.test_regime_vuoto_400_prima_di_scrivere
8) ConfermaNonScrivibileTests.test_create_rifiuta_la_conferma_come_valore
9) ConfermaNonScrivibileTests.test_update_rifiuta_la_conferma_come_valore
"""

from unittest.mock import patch

from django.db import IntegrityError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError

SVC_MOD = "apps.anagrafiche.services.emittenti_fiscali_service"
_SOGGETTO = "00000000-0000-0000-0000-000000000001"


@patch(f"{SVC_MOD}.EmittentiFiscaliRepository")
class UpdateRegimeTests(SimpleTestCase):

    def _svc(self, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliService,
        )
        repo = mock_repo_cls.return_value
        repo.get_emittente.return_value = {"id": 1}
        repo.update_emittente.return_value = True
        svc = EmittentiFiscaliService()
        svc.get_non_editable_fields = list  # type: ignore[method-assign]
        return svc, repo

    def test_regime_presente_conferma(self, mock_repo_cls):
        svc, repo = self._svc(mock_repo_cls)
        svc.update_emittente(1, {"regime_fiscale_rf": "RF17"})
        repo.update_emittente.assert_called_once_with(
            1, {"regime_fiscale_rf": "RF17"}, conferma_regime=True,
        )

    def test_regime_assente_non_conferma(self, mock_repo_cls):
        svc, repo = self._svc(mock_repo_cls)
        svc.update_emittente(1, {"bollo_auto": True})
        repo.update_emittente.assert_called_once_with(
            1, {"bollo_auto": True}, conferma_regime=False,
        )

    def test_regime_vuoto_o_null_400_sul_campo(self, mock_repo_cls):
        svc, repo = self._svc(mock_repo_cls)
        for valore in ("", "  ", None):
            with self.subTest(valore=valore), self.assertRaises(ServiceError) as ctx:
                svc.update_emittente(1, {"regime_fiscale_rf": valore})
            self.assertEqual("E_ANAG_VALIDAZIONE", ctx.exception.code)
            self.assertEqual("regime_fiscale_rf", ctx.exception.context.get("field"))
        repo.update_emittente.assert_not_called()

    # Solo la FK del regime si traduce: un'altra violazione resta com'e'.
    def test_fk_ignota_non_diventa_errore_di_regime(self, mock_repo_cls):
        svc, repo = self._svc(mock_repo_cls)
        repo.update_emittente.side_effect = IntegrityError(
            'violates foreign key constraint "fk_emittenti_fiscali_valute"'
        )
        with self.assertRaises(IntegrityError):
            svc.update_emittente(1, {"regime_fiscale_rf": "RF01", "valuta_id": 999})


@patch(f"{SVC_MOD}.transaction")
@patch(f"{SVC_MOD}.EmittentiFiscaliRepository")
class CreaRegimeTests(SimpleTestCase):

    def _svc(self, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliService,
        )
        repo = mock_repo_cls.return_value
        repo.get_soggetto_partita_iva.return_value = "01234567890"
        repo.get_or_create_ruolo_emittente.return_value = 11
        repo.create_emittente.return_value = 5
        return EmittentiFiscaliService(), repo

    def test_regime_presente_conferma(self, mock_repo_cls, _tx):
        svc, repo = self._svc(mock_repo_cls)
        svc.crea_emittente({"soggetto_id": _SOGGETTO, "codice": "AB", "regime_fiscale_rf": "RF17"})
        kwargs = repo.create_emittente.call_args.kwargs
        self.assertTrue(kwargs["conferma_regime"])
        self.assertEqual("RF17", kwargs["regime_fiscale_rf"])

    def test_regime_assente_non_conferma(self, mock_repo_cls, _tx):
        svc, repo = self._svc(mock_repo_cls)
        svc.crea_emittente({"soggetto_id": _SOGGETTO, "codice": "AB"})
        kwargs = repo.create_emittente.call_args.kwargs
        self.assertFalse(kwargs["conferma_regime"])
        self.assertNotIn("regime_fiscale_rf", kwargs)

    # ⛔ Prima del 2026-10-01 il vuoto veniva omesso in silenzio: l'emittente
    #    nasceva RF01 come se nessuno avesse scritto niente.
    def test_regime_vuoto_400_prima_di_scrivere(self, mock_repo_cls, _tx):
        svc, repo = self._svc(mock_repo_cls)
        with self.assertRaises(ServiceError) as ctx:
            svc.crea_emittente({"soggetto_id": _SOGGETTO, "codice": "AB", "regime_fiscale_rf": ""})
        self.assertEqual("regime_fiscale_rf", ctx.exception.context.get("field"))
        repo.create_emittente.assert_not_called()


# Le colonne della conferma si scrivono SOLO come espressioni del repository:
# un valore passato da fuori direbbe una conferma che nessuno ha dato. Lo
# rifiuta il BB di scrittura PRIMA di aprire un cursore (SimpleTestCase: se
# arrivasse al DB, il test fallirebbe con DatabaseOperationForbidden).
class ConfermaNonScrivibileTests(SimpleTestCase):

    def _repo(self):
        from apps.anagrafiche.db.emittenti_fiscali_repository import (
            EmittentiFiscaliRepository,
        )
        return EmittentiFiscaliRepository()

    def test_create_rifiuta_la_conferma_come_valore(self):
        for conferma in (False, True):
            with self.subTest(conferma_regime=conferma), self.assertRaises(RuntimeError):
                self._repo().create_emittente(
                    soggetto_ruolo_id=1, codice="AB", conferma_regime=conferma,
                    regime_fiscale_confermato_da="qualcuno",
                )

    def test_update_rifiuta_la_conferma_come_valore(self):
        with self.assertRaises(RuntimeError):
            self._repo().update_emittente(1, {"regime_fiscale_confermato_il": "2026-01-01"})
