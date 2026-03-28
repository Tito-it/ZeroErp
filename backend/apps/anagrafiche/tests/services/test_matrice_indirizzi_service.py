# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per MatriceIndirizziService.
#        Mock repository, CI-compatible (no DB reale).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_list_ok — happy path lista paginata
 2) test_get_ok — dettaglio regola
 3) test_get_not_found — regola inesistente
 4) test_crea_ok — creazione regola
 5) test_crea_missing_tipo_ruolo — tipo_ruolo_id mancante
 6) test_crea_missing_tipo_indirizzo — tipo_indirizzo_id mancante
 7) test_crea_fallback_self — fallback uguale a tipo_indirizzo
 8) test_crea_duplicato — duplicato UNIQUE
 9) test_update_ok — aggiorna obbligatorio
10) test_update_attivo_false — disattiva regola
11) test_update_not_found — regola inesistente
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError


REPO = "apps.anagrafiche.services.matrice_indirizzi_service.MatriceIndirizziRepository"


def _regola_detail():
    return {
        "id": 1, "tipo_ruolo_id": 2, "tipo_ruolo_descrizione": "Fornitore",
        "tipo_ruolo_codice": "FO", "tipo_indirizzo_id": 8,
        "tipo_indirizzo_descrizione": "Fatturazione", "tipo_indirizzo_codice": "FATT",
        "obbligatorio": True, "fallback_tipo_indirizzo_id": 3,
        "fallback_descrizione": "Sede Legale", "fallback_codice": "SEDELEG",
        "attivo": True, "valido_dal": "2026-01-01", "valido_al": None,
        "data_insert": "2026-01-01", "data_update": "2026-01-01",
    }


class TestMatriceIndirizziList(TestCase):

    @patch(REPO)
    def test_list_ok(self, mock_repo):
        """Happy path: lista paginata."""
        mock_repo.return_value.list_matrice.return_value = ([_regola_detail()], 1)
        from apps.anagrafiche.services.matrice_indirizzi_service import MatriceIndirizziService
        results, total = MatriceIndirizziService().list_regole()
        self.assertEqual(total, 1)

    @patch(REPO)
    def test_get_ok(self, mock_repo):
        """Happy path: dettaglio regola."""
        mock_repo.return_value.get_regola.return_value = _regola_detail()
        from apps.anagrafiche.services.matrice_indirizzi_service import MatriceIndirizziService
        result = MatriceIndirizziService().get_regola(1)
        self.assertEqual(result["tipo_ruolo_codice"], "FO")

    @patch(REPO)
    def test_get_not_found(self, mock_repo):
        """Regola inesistente."""
        mock_repo.return_value.get_regola.return_value = None
        from apps.anagrafiche.services.matrice_indirizzi_service import MatriceIndirizziService
        with self.assertRaises(ServiceError) as ctx:
            MatriceIndirizziService().get_regola(999)
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")


class TestMatriceIndirizziCrea(TestCase):

    @patch(REPO)
    def test_crea_ok(self, mock_repo):
        """Happy path: crea regola."""
        mock_repo.return_value.create_regola.return_value = 10
        from apps.anagrafiche.services.matrice_indirizzi_service import MatriceIndirizziService
        result = MatriceIndirizziService().crea_regola({
            "tipo_ruolo_id": 2, "tipo_indirizzo_id": 8,
            "obbligatorio": True, "fallback_tipo_indirizzo_id": 3,
        })
        self.assertEqual(result["id"], 10)

    @patch(REPO)
    def test_crea_missing_tipo_ruolo(self, mock_repo):
        """tipo_ruolo_id mancante."""
        from apps.anagrafiche.services.matrice_indirizzi_service import MatriceIndirizziService
        with self.assertRaises(ServiceError) as ctx:
            MatriceIndirizziService().crea_regola({"tipo_indirizzo_id": 8})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(REPO)
    def test_crea_missing_tipo_indirizzo(self, mock_repo):
        """tipo_indirizzo_id mancante."""
        from apps.anagrafiche.services.matrice_indirizzi_service import MatriceIndirizziService
        with self.assertRaises(ServiceError) as ctx:
            MatriceIndirizziService().crea_regola({"tipo_ruolo_id": 2})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(REPO)
    def test_crea_fallback_self(self, mock_repo):
        """Fallback uguale a tipo_indirizzo."""
        from apps.anagrafiche.services.matrice_indirizzi_service import MatriceIndirizziService
        with self.assertRaises(ServiceError) as ctx:
            MatriceIndirizziService().crea_regola({
                "tipo_ruolo_id": 2, "tipo_indirizzo_id": 8,
                "fallback_tipo_indirizzo_id": 8,
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")

    @patch(REPO)
    def test_crea_duplicato(self, mock_repo):
        """Duplicato UNIQUE."""
        from django.db import IntegrityError
        mock_repo.return_value.create_regola.side_effect = IntegrityError("uq_tipi_ruolo_tipi_indirizzo")
        from apps.anagrafiche.services.matrice_indirizzi_service import MatriceIndirizziService
        with self.assertRaises(ServiceError) as ctx:
            MatriceIndirizziService().crea_regola({
                "tipo_ruolo_id": 2, "tipo_indirizzo_id": 8,
            })
        self.assertEqual(ctx.exception.code, "E_ANAG_DUPLICATO")


class TestMatriceIndirizziUpdate(TestCase):

    @patch(REPO)
    def test_update_ok(self, mock_repo):
        """Happy path: aggiorna obbligatorio."""
        mock_repo.return_value.get_regola.return_value = _regola_detail()
        mock_repo.return_value.update_regola.return_value = True
        from apps.anagrafiche.services.matrice_indirizzi_service import MatriceIndirizziService
        result = MatriceIndirizziService().update_regola(1, {"obbligatorio": False})
        self.assertTrue(result["updated"])

    @patch(REPO)
    def test_update_attivo_false(self, mock_repo):
        """Disattiva regola (attivo=false → valido_al gestito dal repo)."""
        mock_repo.return_value.get_regola.return_value = _regola_detail()
        mock_repo.return_value.update_regola.return_value = True
        from apps.anagrafiche.services.matrice_indirizzi_service import MatriceIndirizziService
        result = MatriceIndirizziService().update_regola(1, {"attivo": False})
        self.assertTrue(result["updated"])

    @patch(REPO)
    def test_update_not_found(self, mock_repo):
        """Regola inesistente."""
        mock_repo.return_value.get_regola.return_value = None
        from apps.anagrafiche.services.matrice_indirizzi_service import MatriceIndirizziService
        with self.assertRaises(ServiceError) as ctx:
            MatriceIndirizziService().update_regola(999, {"obbligatorio": False})
        self.assertEqual(ctx.exception.code, "E_ANAG_NOT_FOUND")
