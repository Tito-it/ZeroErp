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
 2) test_list_records_capability_non_gestita_emittente_attivo — can_attivare=true
 3) test_list_records_capability_non_gestita_emittente_disattivo — can_attivare=false
 4) test_list_records_capability_gestita_senza_parametri — can_update + can_remove, niente reset
 5) test_list_records_capability_gestita_personalizzata — can_reset
 5b) test_crea_record_senza_parametri — l'attivazione porta solo l'utility
 5c) test_crea_record_rifiuta_attivo — `attivo` nel payload e' un 400 che lo nomina
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
    """Capability di riga delle utility dell'azienda (brief-db-utility-gestite-
    dall-emittente §10 R-3): la riga presente e' l'utility gestita."""

    # Scopo: list_records sulle righe date, con l'emittente acceso o spento.
    def _righe(self, righe, *, attivo=True):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )
        with patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True) as repo, \
                patch(f"{SVC_MOD}.EmittentiFiscaliService") as parent:
            parent.return_value._resolve_soggetto_ruolo_id.return_value = 50
            parent.return_value._repo.get_emittente.return_value = {"id": 7, "attivo": attivo}
            repo.return_value.list_by_emittente.return_value = righe
            return EmittentiFiscaliUtilitiesService().list_records(7)

    def test_list_records_capability_non_gestita_emittente_attivo(self):
        row = self._righe([{"utility_id": 1, "record_id": None, "personalizzata": False}])[0]
        self.assertTrue(row["can_attivare"])
        self.assertFalse(row["can_update"])
        self.assertFalse(row["can_reset"])
        self.assertFalse(row["can_remove"])

    def test_list_records_capability_non_gestita_emittente_disattivo(self):
        # Sotto un emittente spento non nasce niente (child_requires_active_parent).
        row = self._righe(
            [{"utility_id": 1, "record_id": None, "personalizzata": False}], attivo=False,
        )[0]
        self.assertFalse(row["can_attivare"])

    def test_list_records_capability_gestita_senza_parametri(self):
        row = self._righe([{"utility_id": 1, "record_id": 99, "personalizzata": False}])[0]
        self.assertFalse(row["can_attivare"])
        self.assertTrue(row["can_update"])
        self.assertFalse(row["can_reset"])
        self.assertTrue(row["can_remove"])

    def test_list_records_capability_gestita_personalizzata(self):
        row = self._righe([{"utility_id": 1, "record_id": 99, "personalizzata": True}])[0]
        self.assertTrue(row["can_reset"])
        self.assertTrue(row["can_remove"])


class TestCreaRecordUtility(TestCase):
    """L'attivazione: `utility_id` obbligatorio, i parametri facoltativi,
    `attivo` rifiutato (D-U-1, D-U-11)."""

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_crea_record_senza_parametri(self, mock_parent_cls, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_repo_cls.return_value.create_record.return_value = 99
        esito = EmittentiFiscaliUtilitiesService().crea_record(7, {"utility_id": 3})
        self.assertEqual({"id": 99}, esito)
        mock_repo_cls.return_value.create_record.assert_called_once_with(
            emittente_soggetto_ruolo_id=50, utility_id=3, parametri={},
        )

    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_crea_record_rifiuta_attivo(self, _parent, mock_repo_cls):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )
        from apps.core.services.service_errors import ServiceError

        with self.assertRaises(ServiceError) as ctx:
            EmittentiFiscaliUtilitiesService().crea_record(7, {"utility_id": 3, "attivo": True})
        self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
        self.assertIn("attivo", ctx.exception.context["unknown_keys"])
        mock_repo_cls.return_value.create_record.assert_not_called()

    # 2026-11-28 (/verifica): i parametri facoltativi arrivavano grezzi al DB,
    # e un valore non numerico usciva col testo di PostgreSQL, senza il campo.
    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_crea_record_parametri_tipizzati(self, mock_parent_cls, mock_repo_cls):
        from decimal import Decimal

        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )
        from apps.core.services.service_errors import ServiceError

        mock_parent_cls.return_value._resolve_soggetto_ruolo_id.return_value = 50
        mock_repo_cls.return_value.create_record.return_value = 99
        svc = EmittentiFiscaliUtilitiesService()
        svc.crea_record(7, {
            "utility_id": 3, "arrotondamento_importi_dec": "2",
            "metodo_arrotondamento_importi": " HALF_UP ", "minimo_soglia_min": "",
            "minimo_soglia_max": "1.5",
        })
        mock_repo_cls.return_value.create_record.assert_called_once_with(
            emittente_soggetto_ruolo_id=50, utility_id=3, parametri={
                "arrotondamento_importi_dec": 2,
                "metodo_arrotondamento_importi": "HALF_UP",
                "minimo_soglia_min": None,
                "minimo_soglia_max": Decimal("1.5"),
            },
        )
        for campo in ("arrotondamento_importi_dec", "minimo_soglia_min"):
            with self.subTest(campo=campo), self.assertRaises(ServiceError) as ctx:
                svc.crea_record(7, {"utility_id": 3, campo: "abc"})
            self.assertEqual(ctx.exception.code, "E_ANAG_VALIDAZIONE")
            self.assertEqual(ctx.exception.context.get("field"), campo)

    @patch(f"{SVC_MOD}._verify_record_ownership")
    @patch(f"{SVC_MOD}.EmittentiFiscaliUtilitiesRepository", autospec=True)
    @patch(f"{SVC_MOD}.EmittentiFiscaliService")
    def test_aggiorna_record_parametri_tipizzati(self, _parent, mock_repo_cls, _own):
        from apps.anagrafiche.services.emittenti_fiscali_service import (
            EmittentiFiscaliUtilitiesService,
        )
        from apps.core.services.service_errors import ServiceError

        mock_repo_cls.return_value.update_record.return_value = True
        svc = EmittentiFiscaliUtilitiesService()
        with self.assertRaises(ServiceError) as ctx:
            svc.aggiorna_record(7, 5, {"arrotondamento_importi_dec": "due"})
        self.assertEqual(ctx.exception.context.get("field"), "arrotondamento_importi_dec")
        mock_repo_cls.return_value.update_record.assert_not_called()

        svc.aggiorna_record(7, 5, {"arrotondamento_importi_dec": None})
        mock_repo_cls.return_value.update_record.assert_called_once_with(
            5, {"arrotondamento_importi_dec": None},
        )


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
