# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per capability di riga + non_editable_fields
#        nel servizio emittenti_fiscali (Fase 4 — A7/A9).
#        Mock repo, no DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_get_emittente_include_non_editable_fields — testata arricchita
 2) test_list_records_capability_slot_vuoto_emittente_attivo — can_configure=true
 3) test_list_records_capability_slot_vuoto_emittente_disattivo — can_configure=false
 4) test_list_records_capability_record_configurato — can_update + can_remove
 5) test_list_records_capability_utility_disattiva_blocca_configure — can_configure=false
 6) test_list_mapping_can_remove — BA mapping arricchito con can_remove=True
"""

from unittest import TestCase
from unittest.mock import patch


SVC_MOD = "apps.anagrafiche.services.emittenti_fiscali_service"


class TestGetEmittenteNonEditable(TestCase):
    """Detail testata emittente arricchito con non_editable_fields."""

    @patch(f"{SVC_MOD}.EmittentiFiscaliRepository")
    @patch("apps.core.services.non_editable_fields_helper.LockColumnsRepository.list_non_editable")
    def test_get_emittente_include_non_editable_fields(self, mock_list_locks, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliService,
        )

        mock_list_locks.return_value = ()
        mock_repo_cls.return_value.get_emittente.return_value = {
            "id": 7, "codice": "EF001", "soggetto_id": "uuid-x",
        }

        result = EmittentiFiscaliService().get_emittente(7)

        self.assertEqual(result["id"], 7)
        self.assertIn("non_editable_fields", result)
        self.assertEqual(set(result["non_editable_fields"]), {"codice", "soggetto_id"})


class TestUtilitiesCapability(TestCase):
    """Capability di riga matrice utility (slot/override pattern)."""

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository")
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_records_capability_slot_vuoto_emittente_attivo(
        self, mock_parent_cls, mock_repo_cls,
    ):
        # Slot vuoto (record_id=None) + emittente attivo + utility attiva
        # -> can_configure=True, can_update/remove=False.
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_parent_cls.return_value._repo.get_emittente.return_value = {
            "id": 7, "attivo": True,
        }
        mock_repo_cls.return_value.list_by_emittente.return_value = [
            {"utility_id": 1, "utility_codice": "GAS", "record_id": None, "utility_attiva": True},
        ]

        rows = EmittentiFiscaliUtilitiesService().list_records(7)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row["can_configure"])
        self.assertFalse(row["can_update"])
        self.assertFalse(row["can_remove"])

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository")
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_records_capability_slot_vuoto_emittente_disattivo(
        self, mock_parent_cls, mock_repo_cls,
    ):
        # Slot vuoto + emittente disattivo -> can_configure=False (trigger DB
        # bloccherebbe child_requires_active_parent).
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_parent_cls.return_value._repo.get_emittente.return_value = {
            "id": 7, "attivo": False,
        }
        mock_repo_cls.return_value.list_by_emittente.return_value = [
            {"utility_id": 1, "utility_codice": "GAS", "record_id": None, "utility_attiva": True},
        ]

        rows = EmittentiFiscaliUtilitiesService().list_records(7)

        self.assertFalse(rows[0]["can_configure"])

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository")
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_records_capability_record_configurato(
        self, mock_parent_cls, mock_repo_cls,
    ):
        # Record configurato (record_id valorizzato) -> can_update + can_remove,
        # can_configure=False (lo slot non e' piu' vuoto).
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_parent_cls.return_value._repo.get_emittente.return_value = {
            "id": 7, "attivo": True,
        }
        mock_repo_cls.return_value.list_by_emittente.return_value = [
            {"utility_id": 1, "utility_codice": "GAS", "record_id": 99, "utility_attiva": True},
        ]

        rows = EmittentiFiscaliUtilitiesService().list_records(7)

        row = rows[0]
        self.assertFalse(row["can_configure"])
        self.assertTrue(row["can_update"])
        self.assertTrue(row["can_remove"])

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository")
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_records_capability_utility_disattiva_blocca_configure(
        self, mock_parent_cls, mock_repo_cls,
    ):
        # Slot vuoto + emittente attivo ma utility globalmente disattivata
        # -> can_configure=False.
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_parent_cls.return_value._repo.get_emittente.return_value = {
            "id": 7, "attivo": True,
        }
        mock_repo_cls.return_value.list_by_emittente.return_value = [
            {"utility_id": 1, "utility_codice": "GAS", "record_id": None, "utility_attiva": False},
        ]

        rows = EmittentiFiscaliUtilitiesService().list_records(7)

        self.assertFalse(rows[0]["can_configure"])


class TestBillingAccountMappingCapability(TestCase):
    """BA mapping arricchito con can_remove=True."""

    @patch(f"{SVC_MOD}.EmittentiFiscaliBillingAccountRepository")
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_list_mapping_can_remove(self, mock_parent_cls, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliBillingAccountService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_repo_cls.return_value.list_by_emittente.return_value = (
            [
                {"id": 1, "billing_account_id": 100, "is_default": False},
                {"id": 2, "billing_account_id": None, "is_default": True},
            ],
            2,
        )

        rows, total = EmittentiFiscaliBillingAccountService().list_mapping(7)

        self.assertEqual(total, 2)
        self.assertTrue(rows[0]["can_remove"])
        self.assertTrue(rows[1]["can_remove"])
