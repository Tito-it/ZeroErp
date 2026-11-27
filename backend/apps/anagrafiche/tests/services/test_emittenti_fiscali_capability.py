# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
 6) test_imposta_predefinita_rifiuta_il_billing_account — un BA nel payload e' un 400 che lo nomina
 7) test_imposta_predefinita_vuoto — il payload vuoto sposta la predefinita sull'emittente
 8) test_imposta_predefinita_senza_riga — la predefinita assente e' E_EMITTENTE_DEFAULT_MISSING, non si ricrea
(I 6-6d di prima, `can_remove` e motivo per riga dei collegamenti, ritirati il
 2026-11-27: la scheda e' in consultazione e nessun collegamento si toglie.)
"""

from unittest import TestCase
from unittest.mock import patch


SVC_MOD = "apps.anagrafiche.services.emittenti_fiscali_service"


class TestGetEmittenteNonEditable(TestCase):
    """Detail testata emittente arricchito con non_editable_fields."""

    @patch(f"{SVC_MOD}.EmittentiFiscaliRepository", autospec=True)
    @patch("apps.core.services.non_editable_fields_helper.LockColumnsRepository.list_non_editable", autospec=True)
    def test_get_emittente_include_non_editable_fields(self, mock_list_locks, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliService,
        )

        mock_repo_cls.return_value.get_emittente.return_value = {
            "id": 7, "codice": "EF001", "soggetto_id": "uuid-x",
        }

        # `codice` e `soggetto_ruolo_id` li dichiara il DB (trigger di lock
        # dell'emittente, letto vivo: BE2; il secondo dal 2026-11-21). Nessun
        # gap Python: la lista e' quella della vista, ordinata.
        # Che la vista lo dichiari davvero lo prova `test_lock_columns_vivo_db`.
        for db_locked, attesi in (
            (("soggetto_ruolo_id", "codice"), ["codice", "soggetto_ruolo_id"]),
            # ⛔ Senza lock del DB la lista e' vuota: non c'e' piu' un gap.
            ((), []),
        ):
            with self.subTest(db_locked=db_locked):
                mock_list_locks.return_value = db_locked
                result = EmittentiFiscaliService().get_emittente(7)
                self.assertEqual(result["id"], 7)
                self.assertEqual(result["non_editable_fields"], attesi)


class TestUtilitiesCapability(TestCase):
    """Capability di riga matrice utility (slot/override pattern)."""

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
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

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
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

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
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

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
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


class TestImpostaPredefinita(TestCase):
    """Dal 2026-11-27 (D-T4-3, giro 6 di brief-db-revisione-anagrafiche §26.2)
    il POST del collegamento rende l'emittente l'azienda predefinita: un BA ha
    gia' il suo collegamento, e da qui non se ne crea uno."""

    # Scopo: un `billing_account_id` nel payload e' un 400 che lo nomina, prima
    #        di toccare il repository.
    @patch(f"{SVC_MOD}.EmittentiFiscaliBillingAccountRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_imposta_predefinita_rifiuta_il_billing_account(self, _parent, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliBillingAccountService,
        )
        from apps.core.services.service_errors import ServiceError

        with self.assertRaises(ServiceError) as ctx:
            EmittentiFiscaliBillingAccountService().imposta_predefinita(7, {"billing_account_id": 5})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("billing_account_id", ctx.exception.context["unknown_keys"])
        mock_repo_cls.return_value.imposta_predefinita.assert_not_called()

    # Scopo: il payload vuoto sposta la predefinita sull'emittente.
    @patch(f"{SVC_MOD}.EmittentiFiscaliBillingAccountRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_imposta_predefinita_vuoto(self, mock_parent_cls, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliBillingAccountService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_repo_cls.return_value.imposta_predefinita.return_value = 11
        esito = EmittentiFiscaliBillingAccountService().imposta_predefinita(7, {})
        self.assertEqual(
            {"id": 11, "emittente_id": 7, "billing_account_id": None, "is_default": True}, esito,
        )
        mock_repo_cls.return_value.imposta_predefinita.assert_called_once_with(50)

    # Scopo: senza la riga della predefinita il service lo DICE
    #        (`E_EMITTENTE_DEFAULT_MISSING`) e non la ricrea: e' uno stato che il
    #        modello esclude, e un ripiego lo nasconderebbe.
    @patch(f"{SVC_MOD}.EmittentiFiscaliBillingAccountRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_imposta_predefinita_senza_riga(self, mock_parent_cls, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliBillingAccountService,
        )
        from apps.core.services.service_errors import ServiceError

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_repo_cls.return_value.imposta_predefinita.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            EmittentiFiscaliBillingAccountService().imposta_predefinita(7, {})
        self.assertEqual(ctx.exception.code, "E_EMITTENTE_DEFAULT_MISSING")
