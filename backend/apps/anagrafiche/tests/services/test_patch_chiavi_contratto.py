# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il contratto delle PATCH di anagrafiche: una chiave fuori contratto
#        e' un 400 `E_ANAG_VALIDAZIONE` che la NOMINA, deciso nel SERVICE prima
#        di toccare il repository.
# Note: ⛔ Il perche' (2026-09-26): le scritture dinamiche sono passate ai BB di
#       `sql_write_helpers`, la cui whitelist e' RIGIDA — una colonna fuori
#       lista e' `RuntimeError`, cioe' un 500. Fino a quel giorno il repository
#       la SCARTAVA in silenzio: un salvataggio che «riusciva» senza aver
#       scritto il campo. Il service e' il posto dove l'errore diventa quello
#       giusto per l'operatore; il repository non deve mai vederlo arrivare.
#       Mock repository, CI-compatible.
# ------------------------------------------------------------
"""
Indice test eseguiti:
 1) SoggettiPatchChiaviTests.test_update_soggetto_chiave_ignota
 2) SoggettiPatchChiaviTests.test_update_soggetto_alias_comune_nascita_ammesso
 3) SoggettiPatchChiaviTests.test_update_contatto_chiave_ignota
 4) SoggettiPatchChiaviTests.test_update_contatto_ruolo_chiave_ignota
 5) SoggettiPatchChiaviTests.test_update_contatto_ruolo_ok_passa_ownership_ruolo
 6) SoggettiPatchChiaviTests.test_update_indirizzo_ruolo_chiave_ignota
 7) ContiBancariPatchChiaviTests.test_legame_soggetto_rifiuta_istanza_utility
 8) ContiBancariPatchChiaviTests.test_legame_ruolo_ammette_istanza_utility
 9) EmittentiPatchChiaviTests.test_update_emittente_rifiuta_codice
10) EmittentiPatchChiaviTests.test_aggiorna_record_utility_chiave_ignota
11) FornitoriPatchChiaviTests.test_update_fornitore_chiave_ignota
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError


_SOGG_REPO = "apps.anagrafiche.services.soggetti_service.SoggettiRepository"
_CB_REPO = "apps.anagrafiche.services.conti_bancari_service.ContiBancariRepository"
_CB_SOGG_REPO = "apps.anagrafiche.services.conti_bancari_service.SoggettiRepository"
_EF_REPO = "apps.anagrafiche.services.emittenti_fiscali_service.EmittentiFiscaliRepository"
_EFU_REPO = (
    "apps.anagrafiche.services.emittenti_fiscali_service.EmittentiFiscaliUtilitiesRepository"
)
_FO_REPO = "apps.anagrafiche.services.fornitori_service.FornitoriRepository"

_FAKE_UUID = "019bac81-3f96-7ce8-a086-7e0bd0a2fec1"


class _Asserzioni(TestCase):

    # Scopo: 400 di dominio che nomina la chiave estranea.
    def assert_chiave_rifiutata(self, ctx, chiave: str) -> None:
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn(chiave, ctx.exception.context["unknown_keys"])


class SoggettiPatchChiaviTests(_Asserzioni):

    @patch(_SOGG_REPO, autospec=True)
    def test_update_soggetto_chiave_ignota(self, mock_repo):
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().update_soggetto(_FAKE_UUID, {"cognome": "X", "codice": "S1"})
        self.assert_chiave_rifiutata(ctx, "codice")
        mock_repo.return_value.update_soggetto.assert_not_called()

    # L'alias del frontend fa parte del contratto: il repository lo mappa.
    @patch(_SOGG_REPO, autospec=True)
    def test_update_soggetto_alias_comune_nascita_ammesso(self, mock_repo):
        mock_repo.return_value.update_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        SoggettiService().update_soggetto(_FAKE_UUID, {"comune_nascita_id": 7})
        mock_repo.return_value.update_soggetto.assert_called_once()

    @patch(_SOGG_REPO, autospec=True)
    def test_update_contatto_chiave_ignota(self, mock_repo):
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().update_contatto(1, {"nominativo": "X", "fonte": "soggetto"})
        self.assert_chiave_rifiutata(ctx, "fonte")
        mock_repo.return_value.update_contatto.assert_not_called()

    # ⚠️ Prima del 2026-09-26 la view del RUOLO scriveva `request.data` nel
    #    repository senza passare da un service: nessuno validava le chiavi.
    @patch(_SOGG_REPO, autospec=True)
    def test_update_contatto_ruolo_chiave_ignota(self, mock_repo):
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().update_contatto_ruolo(10, 1, {"soggetto_id": _FAKE_UUID})
        self.assert_chiave_rifiutata(ctx, "soggetto_id")
        mock_repo.return_value.update_contatto.assert_not_called()

    @patch(_SOGG_REPO, autospec=True)
    def test_update_contatto_ruolo_ok_passa_ownership_ruolo(self, mock_repo):
        mock_repo.return_value.update_contatto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        risultato = SoggettiService().update_contatto_ruolo(10, 1, {"email": "a@b.it"})
        self.assertEqual({"updated": True}, risultato)
        mock_repo.return_value.update_contatto.assert_called_once_with(
            1, {"email": "a@b.it"}, soggetto_ruolo_id=10,
        )

    @patch(_SOGG_REPO, autospec=True)
    def test_update_indirizzo_ruolo_chiave_ignota(self, mock_repo):
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().update_indirizzo_ruolo(10, 50, {"soggetto_ruolo_id": 99})
        self.assert_chiave_rifiutata(ctx, "soggetto_ruolo_id")
        mock_repo.return_value.update_indirizzo_ruolo.assert_not_called()


class ContiBancariPatchChiaviTests(_Asserzioni):

    # ⛔ Il legame SOGGETTO non ha la colonna `istanza_utility_id`: prima la
    #    PATCH arrivava a PostgreSQL e usciva come 500.
    @patch(_CB_SOGG_REPO, autospec=True)
    @patch(_CB_REPO, autospec=True)
    def test_legame_soggetto_rifiuta_istanza_utility(self, mock_cb, _sogg):
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().update_conto_soggetto(
                _FAKE_UUID, 1, {"istanza_utility_id": 5},
            )
        self.assert_chiave_rifiutata(ctx, "istanza_utility_id")
        mock_cb.return_value.update_conto_soggetto.assert_not_called()

    @patch(_CB_SOGG_REPO, autospec=True)
    @patch(_CB_REPO, autospec=True)
    def test_legame_ruolo_ammette_istanza_utility(self, mock_cb, _sogg):
        repo = mock_cb.return_value
        repo.get_legame_flags_ruolo.return_value = {"predefinito": False, "bloccato": False}
        repo.update_conto_ruolo.return_value = True
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        ContiBancariService().update_conto_ruolo(10, 1, {"istanza_utility_id": 5})
        repo.update_conto_ruolo.assert_called_once()


class EmittentiPatchChiaviTests(_Asserzioni):

    # ⚠️ Fino al 2026-09-26 `codice` in PATCH era accettato e ignorato: ora e'
    #    un 400 che lo nomina (e' immutabile, trigger `lock_columns`).
    @patch(_EF_REPO, autospec=True)
    def test_update_emittente_rifiuta_codice(self, mock_repo):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliService,
        )
        with self.assertRaises(ServiceError) as ctx:
            EmittentiFiscaliService().update_emittente(1, {"codice": "CMM-X", "attivo": True})
        self.assert_chiave_rifiutata(ctx, "codice")
        mock_repo.return_value.update_emittente.assert_not_called()

    @patch(_EF_REPO, autospec=True)
    @patch(_EFU_REPO)
    def test_aggiorna_record_utility_chiave_ignota(self, mock_repo, _parent):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )
        with self.assertRaises(ServiceError) as ctx:
            EmittentiFiscaliUtilitiesService().aggiorna_record(1, 2, {"utility_id": 3})
        self.assert_chiave_rifiutata(ctx, "utility_id")
        mock_repo.return_value.update_record.assert_not_called()


class FornitoriPatchChiaviTests(_Asserzioni):

    @patch(_FO_REPO, autospec=True)
    def test_update_fornitore_chiave_ignota(self, mock_repo):
        from apps.anagrafiche.services.fornitori_service import FornitoriService
        with self.assertRaises(ServiceError) as ctx:
            FornitoriService().update_fornitore(1, {"note": "x", "codice": "F1"})
        self.assert_chiave_rifiutata(ctx, "codice")
        mock_repo.return_value.update_fornitore.assert_not_called()
