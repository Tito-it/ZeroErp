# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per ContiBancariService.
#        Mock del repository, nessun accesso DB reale (compatibilita CI).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_search_conti_bancari_ok — ricerca IBAN con risultati
 2) test_search_conti_bancari_short — ricerca < 2 char restituisce lista vuota
 3) test_search_bank_branches_ok — ricerca filiali con risultati
 4) test_list_conti_soggetto_ok — lista conti di un soggetto
 5) test_list_conti_soggetto_not_found — soggetto inesistente
 6) test_create_conto_soggetto_new_iban — crea con IBAN nuovo (get_or_create)
 7) test_create_conto_soggetto_existing_iban — crea con IBAN esistente nel registro
 8) test_create_conto_soggetto_missing_iban — IBAN mancante
 9) test_create_conto_soggetto_missing_branch — filiale mancante
10) test_create_conto_soggetto_invalid_uso — uso non valido
11) test_create_conto_soggetto_by_conto_id — crea usando conto_bancario_id diretto
12) test_create_conto_soggetto_conto_id_not_found — conto_bancario_id inesistente
13) test_update_conto_soggetto_ok — aggiorna legame soggetto
14) test_update_conto_soggetto_not_found — legame inesistente
15) test_delete_conto_soggetto_ok — elimina legame soggetto
16) test_delete_conto_soggetto_not_found — legame inesistente
17) test_list_conti_ruolo_ok — lista conti ruolo + ereditati
18) test_create_conto_ruolo_ok — crea legame ruolo
19) test_update_conto_ruolo_ok — aggiorna legame ruolo
20) test_delete_conto_ruolo_ok — elimina legame ruolo
21) test_extract_legame_bool_absent — booleani non inviati non sovrascrivono
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError

_CB_REPO = "apps.anagrafiche.services.conti_bancari_service.ContiBancariRepository"
_SOG_REPO = "apps.anagrafiche.services.conti_bancari_service.SoggettiRepository"

_FAKE_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_FAKE_IBAN = "IT60X0542811101000000123456"
_FAKE_BIC = "BPPIITRRXXX"


class TestContiBancariSearch(TestCase):
    """Test ricerca registro IBAN e filiali."""

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_search_conti_bancari_ok(self, _sog, mock_cb):
        """Ricerca IBAN con risultati."""
        repo = mock_cb.return_value
        repo.search_conti_bancari.return_value = [
            {"id": 1, "iban": _FAKE_IBAN, "bic_swift": _FAKE_BIC},
        ]
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().search_conti_bancari("IT60", 10)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["iban"], _FAKE_IBAN)

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_search_conti_bancari_short(self, _sog, _cb):
        """Ricerca < 2 char restituisce lista vuota senza chiamare il repo."""
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().search_conti_bancari("I", 10)
        self.assertEqual(result, [])

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_search_bank_branches_ok(self, _sog, mock_cb):
        """Ricerca filiali con risultati."""
        repo = mock_cb.return_value
        repo.search_bank_branches.return_value = [
            {"id": 1, "filiale_nome": "Filiale Milano"},
        ]
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().search_bank_branches("Milano", 10)
        self.assertEqual(len(result), 1)


class TestContiBancariSoggetto(TestCase):
    """Test CRUD legame soggetto ↔ conto."""

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_list_conti_soggetto_ok(self, mock_sog, mock_cb):
        """Lista conti di un soggetto."""
        mock_sog.return_value.exists_soggetto.return_value = True
        mock_cb.return_value.list_conti_soggetto.return_value = [
            {"id": 1, "iban": _FAKE_IBAN, "uso": "INCASSO"},
        ]
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().list_conti_soggetto(_FAKE_UUID)
        self.assertEqual(len(result), 1)

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_list_conti_soggetto_not_found(self, mock_sog, _cb):
        """Soggetto inesistente → E_ANAG_NOT_FOUND."""
        mock_sog.return_value.exists_soggetto.return_value = False
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().list_conti_soggetto(_FAKE_UUID)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_create_conto_soggetto_new_iban(self, mock_sog, mock_cb):
        """Crea con IBAN nuovo — get_or_create crea il registro."""
        mock_sog.return_value.exists_soggetto.return_value = True
        repo = mock_cb.return_value
        repo.get_or_create_conto_bancario.return_value = (1, True)
        repo.create_conto_soggetto.return_value = {
            "id": 10, "conto_bancario_id": 1, "uso": "INCASSO",
        }
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().create_conto_soggetto(_FAKE_UUID, {
            "iban": _FAKE_IBAN, "bic_swift": _FAKE_BIC,
            "bank_branch_id": 1, "uso": "INCASSO", "predefinito": True,
        })
        self.assertEqual(result["id"], 10)
        repo.get_or_create_conto_bancario.assert_called_once()
        repo.create_conto_soggetto.assert_called_once()

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_create_conto_soggetto_existing_iban(self, mock_sog, mock_cb):
        """Crea con IBAN esistente — get_or_create riusa il registro."""
        mock_sog.return_value.exists_soggetto.return_value = True
        repo = mock_cb.return_value
        repo.get_or_create_conto_bancario.return_value = (5, False)
        repo.create_conto_soggetto.return_value = {
            "id": 11, "conto_bancario_id": 5, "uso": "GENERICO",
        }
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().create_conto_soggetto(_FAKE_UUID, {
            "iban": _FAKE_IBAN, "bank_branch_id": 1,
        })
        self.assertEqual(result["conto_bancario_id"], 5)

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_create_conto_soggetto_missing_iban(self, mock_sog, _cb):
        """IBAN mancante → E_ANAG_VALIDAZIONE."""
        mock_sog.return_value.exists_soggetto.return_value = True
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().create_conto_soggetto(_FAKE_UUID, {
                "bank_branch_id": 1,
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_create_conto_soggetto_missing_branch(self, mock_sog, _cb):
        """Filiale mancante → E_ANAG_VALIDAZIONE."""
        mock_sog.return_value.exists_soggetto.return_value = True
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().create_conto_soggetto(_FAKE_UUID, {
                "iban": _FAKE_IBAN,
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_create_conto_soggetto_invalid_uso(self, mock_sog, mock_cb):
        """Uso non valido → E_ANAG_VALIDAZIONE."""
        mock_sog.return_value.exists_soggetto.return_value = True
        mock_cb.return_value.get_or_create_conto_bancario.return_value = (1, False)
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().create_conto_soggetto(_FAKE_UUID, {
                "iban": _FAKE_IBAN, "bank_branch_id": 1, "uso": "INVALIDO",
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_create_conto_soggetto_by_conto_id(self, mock_sog, mock_cb):
        """Crea usando conto_bancario_id diretto (bypass get_or_create)."""
        mock_sog.return_value.exists_soggetto.return_value = True
        repo = mock_cb.return_value
        repo.get_conto_bancario.return_value = {"id": 5, "iban": _FAKE_IBAN}
        repo.create_conto_soggetto.return_value = {
            "id": 12, "conto_bancario_id": 5, "uso": "PAGAMENTO",
        }
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().create_conto_soggetto(_FAKE_UUID, {
            "conto_bancario_id": 5, "uso": "PAGAMENTO",
        })
        self.assertEqual(result["conto_bancario_id"], 5)
        repo.get_or_create_conto_bancario.assert_not_called()

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_create_conto_soggetto_conto_id_not_found(self, mock_sog, mock_cb):
        """conto_bancario_id inesistente → E_ANAG_CONTO_NOT_FOUND."""
        mock_sog.return_value.exists_soggetto.return_value = True
        mock_cb.return_value.get_conto_bancario.return_value = None
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().create_conto_soggetto(_FAKE_UUID, {
                "conto_bancario_id": 999,
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_CONTO_NOT_FOUND")

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_update_conto_soggetto_ok(self, mock_sog, mock_cb):
        """Aggiorna legame soggetto — happy path."""
        mock_sog.return_value.exists_soggetto.return_value = True
        mock_cb.return_value.update_conto_soggetto.return_value = True
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().update_conto_soggetto(
            _FAKE_UUID, 10, {"uso": "PAGAMENTO"},
        )
        self.assertTrue(result["updated"])

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_update_conto_soggetto_not_found(self, mock_sog, mock_cb):
        """Legame inesistente → E_ANAG_NOT_FOUND."""
        mock_sog.return_value.exists_soggetto.return_value = True
        mock_cb.return_value.update_conto_soggetto.return_value = False
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().update_conto_soggetto(
                _FAKE_UUID, 999, {"uso": "INCASSO"},
            )
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_delete_conto_soggetto_ok(self, mock_sog, mock_cb):
        """Elimina legame soggetto — happy path."""
        mock_sog.return_value.exists_soggetto.return_value = True
        mock_cb.return_value.delete_conto_soggetto.return_value = True
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().delete_conto_soggetto(_FAKE_UUID, 10)
        self.assertTrue(result["deleted"])

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_delete_conto_soggetto_not_found(self, mock_sog, mock_cb):
        """Legame inesistente → E_ANAG_CONTO_SOGGETTO_NOT_FOUND."""
        mock_sog.return_value.exists_soggetto.return_value = True
        mock_cb.return_value.delete_conto_soggetto.return_value = False
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().delete_conto_soggetto(_FAKE_UUID, 999)
        self.assertEqual(ctx.exception.code, "E_ANAG_CONTO_SOGGETTO_NOT_FOUND")


class TestContiBancariRuolo(TestCase):
    """Test CRUD legame ruolo ↔ conto."""

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_list_conti_ruolo_ok(self, _sog, mock_cb):
        """Lista conti ruolo + ereditati."""
        repo = mock_cb.return_value
        repo.list_conti_ruolo.return_value = [
            {"id": 1, "uso": "INCASSO"},
        ]
        repo.list_conti_ereditati_ruolo.return_value = [
            {"id": 2, "uso": "GENERICO"},
        ]
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().list_conti_ruolo(10)
        self.assertEqual(len(result["conti_ruolo"]), 1)
        self.assertEqual(len(result["conti_ereditati"]), 1)

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_create_conto_ruolo_ok(self, _sog, mock_cb):
        """Crea legame ruolo — happy path."""
        repo = mock_cb.return_value
        repo.get_or_create_conto_bancario.return_value = (1, True)
        repo.create_conto_ruolo.return_value = {
            "id": 20, "conto_bancario_id": 1, "uso": "PAGAMENTO",
        }
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().create_conto_ruolo(10, {
            "iban": _FAKE_IBAN, "bank_branch_id": 1, "uso": "PAGAMENTO",
        })
        self.assertEqual(result["id"], 20)

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_update_conto_ruolo_ok(self, _sog, mock_cb):
        """Aggiorna legame ruolo — happy path."""
        mock_cb.return_value.update_conto_ruolo.return_value = True
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().update_conto_ruolo(10, 20, {"predefinito": True})
        self.assertTrue(result["updated"])

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_delete_conto_ruolo_ok(self, _sog, mock_cb):
        """Elimina legame ruolo — happy path."""
        mock_cb.return_value.delete_conto_ruolo.return_value = True
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().delete_conto_ruolo(10, 20)
        self.assertTrue(result["deleted"])


class TestExtractLegamePayload(TestCase):
    """Test estrazione payload legame — focus su bug booleani."""

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_extract_legame_bool_absent(self, _sog, _cb):
        """Booleani non inviati non devono comparire nel payload estratto."""
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        svc = ContiBancariService()
        # Payload senza predefinito, verificato, bloccato
        result = svc._extract_legame_payload({"uso": "INCASSO"})
        self.assertEqual(result, {"uso": "INCASSO"})
        self.assertNotIn("predefinito", result)
        self.assertNotIn("verificato", result)
        self.assertNotIn("bloccato", result)
