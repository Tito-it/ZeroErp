# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per SoggettiService — validazione, dedup, not found,
#        orchestrazione creazione PF. Mock repository, CI-compatible.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_soggetti_ok — happy path lista
 2) test_get_soggetto_ok — dettaglio con contatti, indirizzi, ruoli
 3) test_get_soggetto_not_found — id inesistente → E_ANAG_NOT_FOUND
 4) test_create_soggetto_pf_ok — creazione PF completa
 5) test_create_soggetto_missing_tipo — tipo mancante → E_ANAG_VALIDAZIONE
 6) test_create_soggetto_pf_missing_cognome — cognome vuoto → E_ANAG_VALIDAZIONE
 7) test_create_soggetto_pf_duplicate_cf — IntegrityError → E_ANAG_DUPLICATO
 8) test_create_soggetto_pg_ok — creazione PG completa (via _create_pg)
 9) test_update_soggetto_ok — aggiorna campi
10) test_update_soggetto_not_found — id inesistente → E_ANAG_NOT_FOUND
11) test_create_contatto_ok — crea contatto
12) test_create_contatto_missing_nominativo — nominativo vuoto → E_ANAG_VALIDAZIONE
13) test_update_contatto_not_found — contatto inesistente → E_ANAG_NOT_FOUND
14) test_create_indirizzo_soggetto_ok — crea indirizzo
15) test_create_indirizzo_missing_tipo — tipo mancante → E_ANAG_VALIDAZIONE
16) test_assign_ruolo_ok — assegna ruolo
17) test_assign_ruolo_missing_codice — codice vuoto → E_ANAG_VALIDAZIONE
18) test_auto_clone_tipi_obbligatori — clona primo indirizzo per obbligatori mancanti
19) test_no_auto_clone_if_flag_false — auto_clone=False, nessuna clonazione
20) test_auto_clone_riusa_dettaglio — clone riusa indirizzo_dettaglio_id del primo
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import IntegrityError

from apps.core.services.service_errors import ServiceError


SOGG_REPO = "apps.anagrafiche.services.soggetti_service.SoggettiRepository"
IND_REPO = "apps.anagrafiche.services.soggetti_service.IndirizziRepository"
LOOKUP_REPO = "apps.anagrafiche.services.soggetti_service.LookupRepository"

FAKE_UUID = "019bac81-3f96-7ce8-a086-7e0bd0a2fec1"


class TestSoggettiListDetail(TestCase):
    """Test lista e dettaglio soggetti."""

    @patch(SOGG_REPO)
    def test_list_soggetti_ok(self, mock_repo):
        """Happy path: lista soggetti."""
        mock_repo.return_value.list_soggetti.return_value = (
            [{"id": FAKE_UUID, "ragione_sociale_completa": "Rossi Mario"}], 1
        )
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        results, total = SoggettiService().list_soggetti()
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["ragione_sociale_completa"], "Rossi Mario")

    @patch(SOGG_REPO)
    def test_get_soggetto_ok(self, mock_repo):
        """Dettaglio soggetto con contatti, indirizzi, ruoli."""
        repo = mock_repo.return_value
        repo.get_soggetto.return_value = {"id": FAKE_UUID, "cognome": "Rossi"}
        repo.get_soggetto_contatti.return_value = [{"id": 1, "nominativo": "Mario Rossi"}]
        repo.get_soggetto_indirizzi.return_value = []
        repo.get_soggetto_ruoli.return_value = []
        repo.get_dati_societari.return_value = None
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().get_soggetto(FAKE_UUID)
        self.assertEqual(result["cognome"], "Rossi")
        self.assertEqual(len(result["contatti"]), 1)

    @patch(SOGG_REPO)
    def test_get_soggetto_not_found(self, mock_repo):
        """Soggetto inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.get_soggetto.return_value = None
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().get_soggetto(FAKE_UUID)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")


class TestSoggettiCreate(TestCase):
    """Test creazione soggetti."""

    @patch(SOGG_REPO)
    def test_create_soggetto_pf_ok(self, mock_repo):
        """Happy path: crea soggetto PF."""
        repo = mock_repo.return_value
        repo.get_natura_by_tipo_id.return_value = "PF"
        repo.crea_soggetto_pf.return_value = FAKE_UUID
        repo.get_soggetto_contatti.return_value = [{"id": 1}]
        repo.update_contatto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().create_soggetto({
            "tipo_soggetto_dettaglio_id": 1,
            "cognome": "Rossi",
            "nome": "Mario",
            "codice_fiscale": "RSSMRA80A01H501Z",
            "contatto": {"nominativo": "Mario Rossi", "email": "m@r.it"},
        })
        self.assertEqual(result["id"], FAKE_UUID)
        repo.crea_soggetto_pf.assert_called_once()

    @patch(SOGG_REPO)
    def test_create_soggetto_missing_tipo(self, mock_repo):
        """Tipo mancante → E_ANAG_VALIDAZIONE."""
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().create_soggetto({"cognome": "Rossi"})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(SOGG_REPO)
    def test_create_soggetto_pf_missing_cognome(self, mock_repo):
        """Cognome vuoto → E_ANAG_VALIDAZIONE."""
        mock_repo.return_value.get_natura_by_tipo_id.return_value = "PF"
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().create_soggetto({
                "tipo_soggetto_dettaglio_id": 1,
                "cognome": "",
                "nome": "Mario",
                "codice_fiscale": "RSSMRA80A01H501Z",
                "contatto": {"nominativo": "Mario Rossi"},
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(SOGG_REPO)
    def test_create_soggetto_pf_duplicate_cf(self, mock_repo):
        """CF duplicato → E_ANAG_DUPLICATO."""
        repo = mock_repo.return_value
        repo.get_natura_by_tipo_id.return_value = "PF"
        repo.crea_soggetto_pf.side_effect = IntegrityError("unique cf")
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().create_soggetto({
                "tipo_soggetto_dettaglio_id": 1,
                "cognome": "Rossi",
                "nome": "Mario",
                "codice_fiscale": "RSSMRA80A01H501Z",
                "contatto": {"nominativo": "Mario Rossi"},
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")

    @patch(SOGG_REPO)
    def test_create_soggetto_pg_ok(self, mock_repo):
        """Happy path: crea soggetto PG."""
        repo = mock_repo.return_value
        repo.get_natura_by_tipo_id.return_value = "PG"
        repo.crea_soggetto_pg.return_value = FAKE_UUID
        repo.get_soggetto_contatti.return_value = [{"id": 1}]
        repo.update_contatto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().create_soggetto({
            "tipo_soggetto_dettaglio_id": 3,
            "ragione_sociale": "Test SRL",
            "codice_fiscale": "12345678901",
            "contatto": {"nominativo": "Admin", "email": "admin@test.it"},
            "dati_societari": {
                "forma_giuridica_id": 4,
                "id_prov_iscri_rea": 1,
                "iscrizione_rea": "MI-123456",
                "capitale_sociale": 10000.00,
            },
        })
        self.assertEqual(result["id"], FAKE_UUID)
        repo.crea_soggetto_pg.assert_called_once()


class TestSoggettiUpdate(TestCase):
    """Test aggiornamento soggetti."""

    @patch(SOGG_REPO)
    def test_update_soggetto_ok(self, mock_repo):
        """Aggiorna campi soggetto."""
        mock_repo.return_value.update_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().update_soggetto(FAKE_UUID, {"cognome": "Bianchi"})
        self.assertTrue(result["updated"])

    @patch(SOGG_REPO)
    def test_update_soggetto_not_found(self, mock_repo):
        """Soggetto inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.update_soggetto.return_value = False
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().update_soggetto(FAKE_UUID, {"cognome": "X"})
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")


class TestSoggettiContatti(TestCase):
    """Test contatti soggetto."""

    @patch(SOGG_REPO)
    def test_create_contatto_ok(self, mock_repo):
        """Crea contatto."""
        repo = mock_repo.return_value
        repo.exists_soggetto.return_value = True
        repo.crea_contatto.return_value = {"id": 10, "nominativo": "Luigi Verdi"}
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().create_contatto(FAKE_UUID, {"nominativo": "Luigi Verdi"})
        self.assertEqual(result["nominativo"], "Luigi Verdi")

    @patch(SOGG_REPO)
    def test_create_contatto_missing_nominativo(self, mock_repo):
        """Nominativo vuoto → E_ANAG_VALIDAZIONE."""
        mock_repo.return_value.exists_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().create_contatto(FAKE_UUID, {"nominativo": ""})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(SOGG_REPO)
    def test_update_contatto_not_found(self, mock_repo):
        """Contatto inesistente → E_ANAG_NOT_FOUND."""
        mock_repo.return_value.update_contatto.return_value = False
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().update_contatto(999, {"nominativo": "X"})
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")


class TestSoggettiIndirizzi(TestCase):
    """Test indirizzi soggetto."""

    @patch(SOGG_REPO)
    def test_create_indirizzo_soggetto_ok(self, mock_repo):
        """Crea indirizzo soggetto."""
        repo = mock_repo.return_value
        repo.exists_soggetto.return_value = True
        repo.crea_indirizzo_soggetto.return_value = 42
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().create_indirizzo_soggetto(FAKE_UUID, {
            "tipo_indirizzo_codice": "RES",
            "indirizzo_dettaglio_id": 100,
        })
        self.assertEqual(result["id"], 42)

    @patch(SOGG_REPO)
    def test_create_indirizzo_missing_tipo(self, mock_repo):
        """Tipo mancante → E_ANAG_VALIDAZIONE."""
        mock_repo.return_value.exists_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().create_indirizzo_soggetto(FAKE_UUID, {
                "indirizzo_dettaglio_id": 100,
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


class TestSoggettiRuoli(TestCase):
    """Test ruoli soggetto."""

    @patch(SOGG_REPO)
    def test_assign_ruolo_ok(self, mock_repo):
        """Assegna ruolo."""
        repo = mock_repo.return_value
        repo.exists_soggetto.return_value = True
        repo.assign_ruolo.return_value = 5
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        result = SoggettiService().assign_ruolo(FAKE_UUID, {"codice_ruolo": "CLIENTE"})
        self.assertEqual(result["id"], 5)

    @patch(SOGG_REPO)
    def test_assign_ruolo_missing_codice(self, mock_repo):
        """Codice vuoto → E_ANAG_VALIDAZIONE."""
        mock_repo.return_value.exists_soggetto.return_value = True
        from apps.anagrafiche.services.soggetti_service import SoggettiService
        with self.assertRaises(ServiceError) as ctx:
            SoggettiService().assign_ruolo(FAKE_UUID, {"codice_ruolo": ""})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")


class TestAutoCloneIndirizzi(TestCase):
    """Test auto-clone indirizzi obbligatori nel backend."""

    @patch(LOOKUP_REPO)
    @patch(IND_REPO)
    @patch(SOGG_REPO)
    def test_auto_clone_tipi_obbligatori(self, mock_sogg, mock_ind, mock_lookup):
        """Verifica che i tipi obbligatori mancanti vengano clonati dal primo."""
        repo = mock_sogg.return_value
        repo.get_natura_by_tipo_id.return_value = "PF"
        repo.crea_soggetto_pf.return_value = FAKE_UUID
        repo.get_soggetto_contatti.return_value = [{"id": 1}]
        repo.update_contatto.return_value = True
        repo.crea_indirizzo_soggetto.return_value = 10

        mock_ind.return_value.create_indirizzo_dettaglio.return_value = 50

        # Matrice: RESID obbligatorio, DOMFISC obbligatorio, FATT facoltativo
        mock_lookup.return_value.list_matrice_indirizzi.return_value = [
            {"codice": "RESID", "obbligatorio": True},
            {"codice": "DOMFISC", "obbligatorio": True},
            {"codice": "FATT", "obbligatorio": False},
        ]

        from apps.anagrafiche.services.soggetti_service import SoggettiService
        SoggettiService().create_soggetto({
            "tipo_soggetto_dettaglio_id": 1,
            "cognome": "Rossi", "nome": "Mario",
            "codice_fiscale": "RSSMRA80A01H501Z",
            "contatto": {"nominativo": "Mario Rossi"},
            # Solo 1 indirizzo RESID — DOMFISC deve essere auto-clonato
            "indirizzi": [
                {"tipo_indirizzo_codice": "RESID", "stradario_id": 100, "civico": 1},
            ],
            "auto_clone": True,
        })

        # crea_indirizzo_soggetto deve essere chiamato 2 volte (RESID + DOMFISC clone)
        self.assertEqual(repo.crea_indirizzo_soggetto.call_count, 2)
        calls = repo.crea_indirizzo_soggetto.call_args_list
        self.assertEqual(calls[0].kwargs["tipo_indirizzo_codice"], "RESID")
        self.assertEqual(calls[1].kwargs["tipo_indirizzo_codice"], "DOMFISC")

    @patch(LOOKUP_REPO)
    @patch(IND_REPO)
    @patch(SOGG_REPO)
    def test_no_auto_clone_if_flag_false(self, mock_sogg, mock_ind, mock_lookup):
        """Se auto_clone=False, nessuna clonazione — solo indirizzi forniti."""
        repo = mock_sogg.return_value
        repo.get_natura_by_tipo_id.return_value = "PF"
        repo.crea_soggetto_pf.return_value = FAKE_UUID
        repo.get_soggetto_contatti.return_value = [{"id": 1}]
        repo.update_contatto.return_value = True
        repo.crea_indirizzo_soggetto.return_value = 10

        mock_ind.return_value.create_indirizzo_dettaglio.return_value = 50

        from apps.anagrafiche.services.soggetti_service import SoggettiService
        SoggettiService().create_soggetto({
            "tipo_soggetto_dettaglio_id": 1,
            "cognome": "Rossi", "nome": "Mario",
            "codice_fiscale": "RSSMRA80A01H501Z",
            "contatto": {"nominativo": "Mario Rossi"},
            "indirizzi": [
                {"tipo_indirizzo_codice": "RESID", "stradario_id": 100, "civico": 1},
            ],
            "auto_clone": False,
        })

        # Solo 1 indirizzo creato (nessun clone)
        self.assertEqual(repo.crea_indirizzo_soggetto.call_count, 1)
        mock_lookup.return_value.list_matrice_indirizzi.assert_not_called()

    @patch(LOOKUP_REPO)
    @patch(IND_REPO)
    @patch(SOGG_REPO)
    def test_auto_clone_riusa_dettaglio(self, mock_sogg, mock_ind, mock_lookup):
        """Auto-clone: il secondo indirizzo riusa indirizzo_dettaglio_id del primo."""
        repo = mock_sogg.return_value
        repo.get_natura_by_tipo_id.return_value = "PF"
        repo.crea_soggetto_pf.return_value = FAKE_UUID
        repo.get_soggetto_contatti.return_value = [{"id": 1}]
        repo.update_contatto.return_value = True
        repo.crea_indirizzo_soggetto.return_value = 10

        mock_ind.return_value.create_indirizzo_dettaglio.return_value = 50

        mock_lookup.return_value.list_matrice_indirizzi.return_value = [
            {"codice": "RESID", "obbligatorio": True},
            {"codice": "DOMFISC", "obbligatorio": True},
        ]

        from apps.anagrafiche.services.soggetti_service import SoggettiService
        SoggettiService().create_soggetto({
            "tipo_soggetto_dettaglio_id": 1,
            "cognome": "Rossi", "nome": "Mario",
            "codice_fiscale": "RSSMRA80A01H501Z",
            "contatto": {"nominativo": "Mario Rossi"},
            "indirizzi": [
                {"tipo_indirizzo_codice": "RESID", "stradario_id": 100, "civico": 1},
            ],
            "auto_clone": True,
        })

        # create_indirizzo_dettaglio chiamato UNA sola volta (il clone riusa l'ID)
        self.assertEqual(mock_ind.return_value.create_indirizzo_dettaglio.call_count, 1)
        # Ma crea_indirizzo_soggetto chiamato 2 volte
        self.assertEqual(repo.crea_indirizzo_soggetto.call_count, 2)
        # Il secondo chiama con indirizzo_dettaglio_id=50 (riuso)
        second_call = repo.crea_indirizzo_soggetto.call_args_list[1]
        self.assertEqual(second_call.kwargs["indirizzo_dettaglio_id"], 50)
