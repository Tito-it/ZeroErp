# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test service layer matrice config.utilities_tipi_ruolo. Mock del
#        repository (nessun accesso DB), verifica validazioni payload e
#        mapping IntegrityError -> codici errore parlanti.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_matrice_default — list passa parametri default al repo
 2) test_list_matrice_invalid_order_by — order_by non whitelisted -> ServiceError
 3) test_get_matrice_ok — get delega al repo e ritorna dict
 4) test_get_matrice_not_found — repo None -> ServiceError NOT_FOUND
 5) test_create_matrice_ok — payload valido -> repo.create + repo.get
 6) test_create_matrice_missing_utility_id — payload incompleto -> VALIDATION
 7) test_create_matrice_unknown_key — chiave extra -> VALIDATION
 8) test_create_matrice_duplicate_unique — IntegrityError UNIQUE -> DUPLICATA
 9) test_create_matrice_fk_violation — IntegrityError FK -> FK
10) test_update_matrice_attivo_ok — update solo attivo OK
11) test_update_matrice_fk_forbidden — payload con utility_id -> VALIDATION
12) test_update_matrice_no_attivo — payload vuoto -> VALIDATION
13) test_update_matrice_not_found — repo update returns False -> NOT_FOUND
14) test_list_usage_ok — usage delega al repo dopo verifica esistenza
"""

from unittest.mock import patch
from unittest import TestCase

from django.db import IntegrityError

from apps.config.services.utilities_tipi_ruolo_service import (
    UtilitiesTipiRuoloService,
)
from apps.core.services.service_errors import ServiceError


_REPO_PATH = (
    "apps.config.services.utilities_tipi_ruolo_service.UtilitiesTipiRuoloRepository"
)


class TestListMatrice(TestCase):
    """Test metodo list_matrice."""

    @patch(_REPO_PATH)
    def test_list_matrice_default(self, mock_repo_cls):
        """list_matrice delega al repo con parametri default."""
        mock_repo_cls.return_value.list_matrice.return_value = ([], 0)
        svc = UtilitiesTipiRuoloService()
        results, total = svc.list_matrice()
        self.assertEqual(results, [])
        self.assertEqual(total, 0)
        mock_repo_cls.return_value.list_matrice.assert_called_once()

    @patch(_REPO_PATH)
    def test_list_matrice_invalid_order_by(self, mock_repo_cls):
        """order_by non valido -> ServiceError E_CONFIG_VALIDATION."""
        del mock_repo_cls
        svc = UtilitiesTipiRuoloService()
        with self.assertRaises(ServiceError) as ctx:
            svc.list_matrice(order_by="not_a_column")
        self.assertEqual(ctx.exception.code, "E_CONFIG_VALIDATION")


class TestGetMatrice(TestCase):
    """Test metodo get_matrice."""

    @patch(_REPO_PATH)
    def test_get_matrice_ok(self, mock_repo_cls):
        """get_matrice ritorna dict dal repo."""
        mock_repo_cls.return_value.get_matrice.return_value = {
            "id": 1, "utility_id": 10, "tipo_ruolo_id": 5, "attivo": True,
        }
        svc = UtilitiesTipiRuoloService()
        result = svc.get_matrice(1)
        self.assertEqual(result["id"], 1)

    @patch(_REPO_PATH)
    def test_get_matrice_not_found(self, mock_repo_cls):
        """repo None -> ServiceError E_CONFIG_MATRICE_NOT_FOUND."""
        mock_repo_cls.return_value.get_matrice.return_value = None
        svc = UtilitiesTipiRuoloService()
        with self.assertRaises(ServiceError) as ctx:
            svc.get_matrice(999)
        self.assertEqual(ctx.exception.code, "E_CONFIG_MATRICE_NOT_FOUND")


class TestCreateMatrice(TestCase):
    """Test metodo create_matrice."""

    @patch(_REPO_PATH)
    def test_create_matrice_ok(self, mock_repo_cls):
        """Payload valido -> repo.create + repo.get_matrice."""
        mock_repo_cls.return_value.create_matrice.return_value = 42
        mock_repo_cls.return_value.get_matrice.return_value = {
            "id": 42, "utility_id": 10, "tipo_ruolo_id": 5, "attivo": True,
        }
        svc = UtilitiesTipiRuoloService()
        result = svc.create_matrice({"utility_id": 10, "tipo_ruolo_id": 5})
        self.assertEqual(result["id"], 42)
        mock_repo_cls.return_value.create_matrice.assert_called_once_with(
            utility_id=10, tipo_ruolo_id=5, attivo=None,
        )

    @patch(_REPO_PATH)
    def test_create_matrice_missing_utility_id(self, mock_repo_cls):
        """Payload senza utility_id -> ServiceError VALIDATION."""
        del mock_repo_cls
        svc = UtilitiesTipiRuoloService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice({"tipo_ruolo_id": 5})
        self.assertEqual(ctx.exception.code, "E_CONFIG_VALIDATION")

    @patch(_REPO_PATH)
    def test_create_matrice_unknown_key(self, mock_repo_cls):
        """Chiave non in whitelist -> ServiceError VALIDATION."""
        del mock_repo_cls
        svc = UtilitiesTipiRuoloService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice({
                "utility_id": 10, "tipo_ruolo_id": 5, "valido_dal": "2026-01-01",
            })
        self.assertEqual(ctx.exception.code, "E_CONFIG_VALIDATION")

    @patch(_REPO_PATH)
    def test_create_matrice_duplicate_unique(self, mock_repo_cls):
        """IntegrityError UNIQUE -> ServiceError DUPLICATA."""
        mock_repo_cls.return_value.create_matrice.side_effect = IntegrityError(
            "duplicate key value violates unique constraint "
            "\"uq_utilities_tipi_ruolo_utility_tipo_ruolo\""
        )
        svc = UtilitiesTipiRuoloService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice({"utility_id": 10, "tipo_ruolo_id": 5})
        self.assertEqual(ctx.exception.code, "E_CONFIG_MATRICE_DUPLICATA")

    @patch(_REPO_PATH)
    def test_create_matrice_fk_violation(self, mock_repo_cls):
        """IntegrityError FK -> ServiceError FK."""
        mock_repo_cls.return_value.create_matrice.side_effect = IntegrityError(
            "insert or update on table \"utilities_tipi_ruolo\" violates "
            "foreign key constraint \"fk_utilities_tipi_ruolo_utility\""
        )
        svc = UtilitiesTipiRuoloService()
        with self.assertRaises(ServiceError) as ctx:
            svc.create_matrice({"utility_id": 99999, "tipo_ruolo_id": 5})
        self.assertEqual(ctx.exception.code, "E_CONFIG_MATRICE_FK")


class TestUpdateMatrice(TestCase):
    """Test metodo update_matrice."""

    @patch(_REPO_PATH)
    def test_update_matrice_attivo_ok(self, mock_repo_cls):
        """update con solo attivo -> repo.update_matrice_attivo."""
        mock_repo_cls.return_value.update_matrice_attivo.return_value = True
        mock_repo_cls.return_value.get_matrice.return_value = {
            "id": 1, "utility_id": 10, "tipo_ruolo_id": 5, "attivo": False,
        }
        svc = UtilitiesTipiRuoloService()
        result = svc.update_matrice(1, {"attivo": False})
        self.assertFalse(result["attivo"])
        mock_repo_cls.return_value.update_matrice_attivo.assert_called_once_with(1, False)

    @patch(_REPO_PATH)
    def test_update_matrice_fk_forbidden(self, mock_repo_cls):
        """Tentativo modifica utility_id -> ServiceError VALIDATION."""
        del mock_repo_cls
        svc = UtilitiesTipiRuoloService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_matrice(1, {"utility_id": 99})
        self.assertEqual(ctx.exception.code, "E_CONFIG_VALIDATION")

    @patch(_REPO_PATH)
    def test_update_matrice_no_attivo(self, mock_repo_cls):
        """Payload senza attivo -> ServiceError VALIDATION."""
        del mock_repo_cls
        svc = UtilitiesTipiRuoloService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_matrice(1, {})
        self.assertEqual(ctx.exception.code, "E_CONFIG_VALIDATION")

    @patch(_REPO_PATH)
    def test_update_matrice_not_found(self, mock_repo_cls):
        """repo update_matrice_attivo False -> ServiceError NOT_FOUND."""
        mock_repo_cls.return_value.update_matrice_attivo.return_value = False
        svc = UtilitiesTipiRuoloService()
        with self.assertRaises(ServiceError) as ctx:
            svc.update_matrice(999, {"attivo": True})
        self.assertEqual(ctx.exception.code, "E_CONFIG_MATRICE_NOT_FOUND")


class TestListUsage(TestCase):
    """Test metodo list_usage."""

    @patch(_REPO_PATH)
    def test_list_usage_ok(self, mock_repo_cls):
        """list_usage verifica esistenza riga e delega al repo."""
        mock_repo_cls.return_value.get_matrice.return_value = {
            "id": 1, "utility_id": 10, "tipo_ruolo_id": 5, "attivo": True,
        }
        mock_repo_cls.return_value.list_emittenti_usage.return_value = (
            [{"emittente_id": 1, "emittente_codice": "EF-001"}], 1,
        )
        svc = UtilitiesTipiRuoloService()
        results, total = svc.list_usage(1)
        self.assertEqual(total, 1)
        self.assertEqual(results[0]["emittente_codice"], "EF-001")
        mock_repo_cls.return_value.list_emittenti_usage.assert_called_once_with(
            1, search=None, order_by=None, order_dir=None, limit=25, offset=0,
        )
