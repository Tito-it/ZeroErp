# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del regime fiscale nel service emittenti (R-1/R-2 e §10 di
#        brief-db-esigibilita-iva-per-cassa-emittente): dichiarare il regime
#        e' confermarlo, il vuoto e' un 400 sul campo, chi non lo manda non
#        conferma niente. Dal §10 (2026-10-02) data e autore della conferma li
#        deriva il database da ogni UPDATE che nomina il regime: il service
#        deve solo nominarlo, anche in creazione (la INSERT non conferma mai).
#        Mock repo, no DB (il binding reale e' in
#        `tests/db/test_regime_fiscale_conferma_db.py`).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) UpdateRegimeTests.test_regime_presente_nominato_nella_update
2) UpdateRegimeTests.test_regime_assente_non_nominato
3) UpdateRegimeTests.test_regime_vuoto_o_null_400_sul_campo
4) UpdateRegimeTests.test_fk_ignota_non_diventa_errore_di_regime
5) CreaRegimeTests.test_regime_presente_insert_poi_update_del_regime
6) CreaRegimeTests.test_regime_assente_nessuna_update
7) CreaRegimeTests.test_regime_vuoto_400_prima_di_scrivere
7-bis) CreaRegimeTests.test_update_del_regime_a_vuoto_non_passa_in_silenzio
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

    # Il regime arriva alla UPDATE cosi' com'e': e' la colonna nominata a
    # far scrivere la conferma al trigger, niente altro.
    def test_regime_presente_nominato_nella_update(self, mock_repo_cls):
        svc, repo = self._svc(mock_repo_cls)
        svc.update_emittente(1, {"regime_fiscale_rf": "RF17"})
        repo.update_emittente.assert_called_once_with(1, {"regime_fiscale_rf": "RF17"})

    def test_regime_assente_non_nominato(self, mock_repo_cls):
        svc, repo = self._svc(mock_repo_cls)
        svc.update_emittente(1, {"bollo_auto": True})
        repo.update_emittente.assert_called_once_with(1, {"bollo_auto": True})

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
        repo.update_emittente.return_value = True
        return EmittentiFiscaliService(), repo

    # La INSERT porta il regime (la FK lo controlla li'), ma la dichiarazione
    # e' la UPDATE che segue, sull'id appena nato.
    def test_regime_presente_insert_poi_update_del_regime(self, mock_repo_cls, _tx):
        svc, repo = self._svc(mock_repo_cls)
        svc.crea_emittente({"soggetto_id": _SOGGETTO, "codice": "AB", "regime_fiscale_rf": "RF17"})
        self.assertEqual("RF17", repo.create_emittente.call_args.kwargs["regime_fiscale_rf"])
        repo.update_emittente.assert_called_once_with(5, {"regime_fiscale_rf": "RF17"})

    # Senza regime vale il default del DB, e nessuno lo dichiara.
    def test_regime_assente_nessuna_update(self, mock_repo_cls, _tx):
        svc, repo = self._svc(mock_repo_cls)
        svc.crea_emittente({"soggetto_id": _SOGGETTO, "codice": "AB"})
        self.assertNotIn("regime_fiscale_rf", repo.create_emittente.call_args.kwargs)
        repo.update_emittente.assert_not_called()

    # ⛔ Prima del 2026-10-01 il vuoto veniva omesso in silenzio: l'emittente
    #    nasceva RF01 come se nessuno avesse scritto niente.
    def test_regime_vuoto_400_prima_di_scrivere(self, mock_repo_cls, _tx):
        svc, repo = self._svc(mock_repo_cls)
        with self.assertRaises(ServiceError) as ctx:
            svc.crea_emittente({"soggetto_id": _SOGGETTO, "codice": "AB", "regime_fiscale_rf": ""})
        self.assertEqual("regime_fiscale_rf", ctx.exception.context.get("field"))
        repo.create_emittente.assert_not_called()

    # 7-bis. Una UPDATE del regime che non tocca righe lascerebbe l'emittente
    #        creato e NON confermato senza errore: e' un errore, non un esito.
    def test_update_del_regime_a_vuoto_non_passa_in_silenzio(self, mock_repo_cls, _tx):
        svc, repo = self._svc(mock_repo_cls)
        repo.update_emittente.return_value = False
        with self.assertRaises(ServiceError) as ctx:
            svc.crea_emittente({"soggetto_id": _SOGGETTO, "codice": "AB", "regime_fiscale_rf": "RF17"})
        self.assertEqual("E_ANAG_NOT_FOUND", ctx.exception.code)


# Le colonne della conferma non si scrivono da Python: le deriva il trigger, e
# il guard DB rifiuta chi le scrive. Il BB di scrittura le ferma PRIMA di aprire
# un cursore (SimpleTestCase: se arrivasse al DB, il test fallirebbe con
# DatabaseOperationForbidden), perche' non sono nelle whitelist del repository.
class ConfermaNonScrivibileTests(SimpleTestCase):

    def _repo(self):
        from apps.anagrafiche.db.emittenti_fiscali_repository import (
            EmittentiFiscaliRepository,
        )
        return EmittentiFiscaliRepository()

    def test_create_rifiuta_la_conferma_come_valore(self):
        with self.assertRaises(RuntimeError):
            self._repo().create_emittente(
                soggetto_ruolo_id=1, codice="AB", regime_fiscale_confermato_da="qualcuno",
            )

    def test_update_rifiuta_la_conferma_come_valore(self):
        with self.assertRaises(RuntimeError):
            self._repo().update_emittente(1, {"regime_fiscale_confermato_il": "2026-01-01"})
