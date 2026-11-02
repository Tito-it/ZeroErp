# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
12) test_create_conto_soggetto_conto_id_not_found — conto_bancario_id inesistente (404)
13) test_update_conto_soggetto_ok — aggiorna legame soggetto
14) test_update_conto_soggetto_not_found — legame inesistente
15) test_delete_conto_soggetto_ok — elimina legame soggetto
16) test_delete_conto_soggetto_not_found — legame inesistente (404)
17) test_list_conti_ruolo_ok — lista conti ruolo + ereditati
18) test_create_conto_ruolo_ok — crea legame ruolo
19) test_update_conto_ruolo_ok — aggiorna legame ruolo
20) test_delete_conto_ruolo_ok — elimina legame ruolo
21) test_extract_legame_bool_absent — booleani non inviati non sovrascrivono
22) test_list_conti_ruolo_cascata_istanza — cascata 3 livelli con istanza_utility_id
23) test_list_conti_ruolo_no_istanza — senza istanza = comportamento retrocompatibile
24) test_create_conto_ruolo_with_istanza — crea legame con istanza_utility_id
25) test_guard_predefinito_bloccato_create — crea con predefinito+bloccato rifiutato
26) test_guard_predefinito_bloccato_update — blocca un predefinito rifiutato
27) TestVincoliLegame (E-7, 2026-10-07) — ogni IntegrityError col SUO codice:
    a) uso fuori elenco → E_ANAG_VALIDAZIONE, campo `uso`
    b) date invertite → E_ANAG_VALIDAZIONE, campo `valido_al`
    c) FK istanza (ruolo) → E_ANAG_FK, campo `istanza_utility_id`
    d) secondo predefinito (indice parziale del ruolo) → E_ANAG_DUPLICATO, campo `predefinito`
    e) duplicato vero → E_ANAG_DUPLICATO, senza campo
    f) vincolo non mappato → E_ANAG_VALIDAZIONE generico, mai «duplicato»
28) TestPatchLegame (E-7) — PATCH `{}` → 400 E_ANAG_VALIDAZIONE (soggetto e
    ruolo, senza toccare il repository); chiave fuori elenco → 400
    uso minuscolo in PATCH → normalizzato come in create; uso ignoto → 400
    campo `uso`, senza toccare il repository
"""

from unittest import TestCase
from unittest.mock import patch

from django.db import IntegrityError

from apps.core.services.error_policies import ErrorPolicyRegistry
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
        # 404 e non 400: il codice e' a catalogo come NON_TROVATO (E-1).
        self.assertEqual(ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 404)

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_update_conto_soggetto_ok(self, mock_sog, mock_cb):
        """Aggiorna legame soggetto — happy path."""
        mock_sog.return_value.exists_soggetto.return_value = True
        repo = mock_cb.return_value
        repo.get_legame_flags_soggetto.return_value = {"predefinito": False, "bloccato": False}
        repo.update_conto_soggetto.return_value = True
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
        repo = mock_cb.return_value
        repo.get_legame_flags_soggetto.return_value = {"predefinito": False, "bloccato": False}
        repo.update_conto_soggetto.return_value = False
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
        # 404 e non 400: il codice e' a catalogo come NON_TROVATO (E-1).
        self.assertEqual(ErrorPolicyRegistry.resolve(ctx.exception.code).http_status, 404)


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
        repo = mock_cb.return_value
        repo.get_legame_flags_ruolo.return_value = {"predefinito": False, "bloccato": False}
        repo.update_conto_ruolo.return_value = True
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


class TestContiBancariRuoloCascataIstanza(TestCase):
    """Test cascata 3 livelli con istanza_utility_id."""

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_list_conti_ruolo_cascata_istanza(self, _sog, mock_cb):
        """Con istanza_utility_id: L1 istanza vince, L2 generico solo se uso non coperto,
        L3 soggetto solo se uso non coperto da L1+L2."""
        repo = mock_cb.return_value
        repo.list_conti_ruolo.return_value = [
            # L1: istanza 5 + INCASSO
            {"id": 1, "uso": "INCASSO", "istanza_utility_id": 5},
            # L2: generico + INCASSO (sara' nascosto da L1)
            {"id": 2, "uso": "INCASSO", "istanza_utility_id": None},
            # L2: generico + PAGAMENTO (non coperto, passa)
            {"id": 3, "uso": "PAGAMENTO", "istanza_utility_id": None},
        ]
        repo.list_conti_ereditati_ruolo.return_value = [
            # L3: soggetto + INCASSO (nascosto da L1)
            {"id": 10, "uso": "INCASSO"},
            # L3: soggetto + GENERICO (non coperto, passa)
            {"id": 11, "uso": "GENERICO"},
        ]
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().list_conti_ruolo(10, istanza_utility_id=5)
        editabili = result["conti_ruolo"]
        readonly = result["conti_ereditati"]
        # Editabili: id=1 (istanza INCASSO) + id=3 (generico PAGAMENTO)
        self.assertEqual(len(editabili), 2)
        self.assertEqual(editabili[0]["id"], 1)
        self.assertEqual(editabili[0]["fonte"], "istanza")
        self.assertEqual(editabili[1]["id"], 3)
        self.assertEqual(editabili[1]["fonte"], "ruolo")
        # Readonly: id=11 (soggetto GENERICO), id=10 nascosto
        self.assertEqual(len(readonly), 1)
        self.assertEqual(readonly[0]["id"], 11)
        self.assertEqual(readonly[0]["fonte"], "soggetto")

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_list_conti_ruolo_no_istanza(self, _sog, mock_cb):
        """Senza istanza_utility_id: tutti i ruolo mostrati + soggetto fallback."""
        repo = mock_cb.return_value
        repo.list_conti_ruolo.return_value = [
            {"id": 1, "uso": "INCASSO", "istanza_utility_id": None},
        ]
        repo.list_conti_ereditati_ruolo.return_value = [
            {"id": 10, "uso": "INCASSO"},
            {"id": 11, "uso": "GENERICO"},
        ]
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().list_conti_ruolo(10)
        editabili = result["conti_ruolo"]
        readonly = result["conti_ereditati"]
        # Ruolo copre INCASSO → soggetto INCASSO nascosto, GENERICO passa
        self.assertEqual(len(editabili), 1)
        self.assertEqual(editabili[0]["fonte"], "ruolo")
        self.assertEqual(len(readonly), 1)
        self.assertEqual(readonly[0]["uso"], "GENERICO")

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_create_conto_ruolo_with_istanza(self, _sog, mock_cb):
        """Crea legame ruolo con istanza_utility_id."""
        repo = mock_cb.return_value
        repo.get_or_create_conto_bancario.return_value = (1, True)
        repo.create_conto_ruolo.return_value = {
            "id": 30, "conto_bancario_id": 1, "uso": "INCASSO", "istanza_utility_id": 5,
        }
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        result = ContiBancariService().create_conto_ruolo(10, {
            "iban": _FAKE_IBAN, "bank_branch_id": 1,
            "uso": "INCASSO", "istanza_utility_id": 5,
        })
        self.assertEqual(result["istanza_utility_id"], 5)
        # Verifica che istanza_utility_id sia stato passato al repo
        call_kwargs = repo.create_conto_ruolo.call_args
        self.assertEqual(call_kwargs[1].get("istanza_utility_id"), 5)


class TestGuardPredefinitBloccato(TestCase):
    """Test regola: un conto predefinito non puo' essere bloccato."""

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_guard_predefinito_bloccato_create(self, mock_sog, mock_cb):
        """Crea con predefinito=true + bloccato=true → E_ANAG_VALIDAZIONE."""
        mock_sog.return_value.exists_soggetto.return_value = True
        mock_cb.return_value.get_or_create_conto_bancario.return_value = (1, True)
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().create_conto_soggetto(_FAKE_UUID, {
                "iban": _FAKE_IBAN, "bank_branch_id": 1,
                "predefinito": True, "bloccato": True,
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("predefinito", ctx.exception.message)

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_guard_predefinito_bloccato_update(self, mock_sog, mock_cb):
        """Blocca un conto gia' predefinito → E_ANAG_VALIDAZIONE."""
        mock_sog.return_value.exists_soggetto.return_value = True
        repo = mock_cb.return_value
        # Il record corrente e' predefinito
        repo.get_legame_flags_soggetto.return_value = {"predefinito": True, "bloccato": False}
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().update_conto_soggetto(
                _FAKE_UUID, 10, {"bloccato": True},
            )
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


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


# Scopo: un IntegrityError come lo solleva psycopg, col nome del vincolo nel testo.
def _violazione(nome: str) -> IntegrityError:
    return IntegrityError(f'new row violates constraint "{nome}"')


class TestVincoliLegame(TestCase):
    """E-7: ogni violazione di vincolo esce col suo codice, non come duplicato."""

    def _crea_soggetto(self, mock_sog, mock_cb, nome: str) -> ServiceError:
        mock_sog.return_value.exists_soggetto.return_value = True
        repo = mock_cb.return_value
        repo.get_conto_bancario.return_value = {"id": 1}
        repo.create_conto_soggetto.side_effect = _violazione(nome)
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().create_conto_soggetto(
                _FAKE_UUID, {"conto_bancario_id": 1, "uso": "INCASSO"},
            )
        return ctx.exception

    def _aggiorna_ruolo(self, mock_cb, nome: str) -> ServiceError:
        repo = mock_cb.return_value
        repo.get_legame_flags_ruolo.return_value = {"predefinito": False, "bloccato": False}
        repo.update_conto_ruolo.side_effect = _violazione(nome)
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().update_conto_ruolo(10, 20, {"predefinito": True})
        return ctx.exception

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_uso_fuori_elenco(self, mock_sog, mock_cb):
        err = self._crea_soggetto(mock_sog, mock_cb, "chk_soggetti_conti_bancari_uso")
        self.assertEqual(err.code, "E_ANAG_VALIDAZIONE")
        self.assertEqual(err.context.get("field"), "uso")

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_date_invertite(self, mock_sog, mock_cb):
        err = self._crea_soggetto(mock_sog, mock_cb, "chk_soggetti_conti_bancari_validita")
        self.assertEqual(err.code, "E_ANAG_VALIDAZIONE")
        self.assertEqual(err.context.get("field"), "valido_al")

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_fk_istanza_ruolo(self, _sog, mock_cb):
        err = self._aggiorna_ruolo(mock_cb, "fk_src_bancari_istanze_utilities")
        self.assertEqual(err.code, "E_ANAG_FK")
        self.assertEqual(err.context.get("field"), "istanza_utility_id")

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_secondo_predefinito_ruolo(self, _sog, mock_cb):
        err = self._aggiorna_ruolo(mock_cb, "uq_src_bancari_predefinito_no_istanza")
        self.assertEqual(err.code, "E_ANAG_DUPLICATO")
        self.assertEqual(err.context.get("field"), "predefinito")

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_duplicato_vero(self, mock_sog, mock_cb):
        err = self._crea_soggetto(
            mock_sog, mock_cb, "uq_soggetti_conti_bancari_soggetto_id_conto_id_uso",
        )
        self.assertEqual(err.code, "E_ANAG_DUPLICATO")
        self.assertNotIn("field", err.context)

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_vincolo_non_mappato_non_e_duplicato(self, mock_sog, mock_cb):
        err = self._crea_soggetto(mock_sog, mock_cb, "chk_inventato")
        self.assertEqual(err.code, "E_ANAG_VALIDAZIONE")


class TestPatchLegame(TestCase):
    """E-7: un PATCH senza campi e' 400, non 404."""

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_patch_vuoto_soggetto(self, mock_sog, mock_cb):
        mock_sog.return_value.exists_soggetto.return_value = True
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().update_conto_soggetto(_FAKE_UUID, 10, {})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_cb.return_value.update_conto_soggetto.assert_not_called()

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_patch_vuoto_ruolo(self, _sog, mock_cb):
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().update_conto_ruolo(10, 20, {})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_cb.return_value.update_conto_ruolo.assert_not_called()

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_chiave_fuori_elenco(self, _sog, mock_cb):
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().update_conto_soggetto(
                _FAKE_UUID, 10, {"istanza_utility_id": 3},
            )
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        mock_cb.return_value.update_conto_soggetto.assert_not_called()

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_patch_uso_normalizzato_come_in_create(self, _sog, mock_cb):
        repo = mock_cb.return_value
        repo.get_legame_flags_ruolo.return_value = {"predefinito": False, "bloccato": False}
        repo.update_conto_ruolo.return_value = True
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        payload = {"uso": " incasso "}
        ContiBancariService().update_conto_ruolo(10, 20, payload)
        repo.update_conto_ruolo.assert_called_once_with(20, 10, {"uso": "INCASSO"})
        self.assertEqual(payload, {"uso": " incasso "})  # l'input non si muta

    @patch(_CB_REPO)
    @patch(_SOG_REPO)
    def test_patch_uso_ignoto(self, mock_sog, mock_cb):
        mock_sog.return_value.exists_soggetto.return_value = True
        mock_cb.return_value.get_legame_flags_soggetto.return_value = None
        from apps.anagrafiche.services.conti_bancari_service import ContiBancariService
        with self.assertRaises(ServiceError) as ctx:
            ContiBancariService().update_conto_soggetto(_FAKE_UUID, 10, {"uso": "BOH"})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertEqual(ctx.exception.context.get("field"), "uso")
        mock_cb.return_value.update_conto_soggetto.assert_not_called()
