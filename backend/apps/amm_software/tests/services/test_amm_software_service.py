# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per AmmSoftwareService — validazione, orchestrazione,
#        cache invalidation. Mock repository, CI-compatible.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_create_operatore_ok — happy path
 2) test_create_operatore_missing_cognome — campo obbligatorio mancante
 3) test_create_operatore_missing_password — password vuota
 4) test_create_operatore_missing_qualifica — qualifica mancante
 5) test_create_operatore_password_hashed — password non in chiaro
 6) test_get_operatore_ok — dettaglio operatore
 7) test_get_operatore_not_found — id inesistente
 8) test_update_operatore_ok — aggiorna e invalida cache
 9) test_update_operatore_not_found — id inesistente
 9a) test_update_operatore_passa_flag_multiface_al_repo — Fase 7: contract is_super_admin/attivo
 9b) test_update_operatore_rifiuta_ruolo_sistema_legacy — guard fail-fast su payload legacy
 9c) test_update_operatore_super_admin_guard_dbtrigger — race condition trigger 384
 9d) test_update_operatore_attivo_only — solo attivo passa al repo
10) test_disabilita_operatore_ok — disabilita e invalida cache + blacklist
11) test_disabilita_operatore_not_found — id inesistente
11a) test_disabilita_operatore_ultimo_super_admin_preview — preview Python (fast-path)
11b) test_disabilita_operatore_ultimo_super_admin_dbtrigger — race condition trigger 384
12) test_create_operatore_rifiuta_ruolo_sistema_legacy — guard fail-fast su payload legacy
12a) test_create_operatore_is_super_admin_passato_al_repo — Fase 7: bool al repo (no enum)
12) test_put_override_aree_invalidates_cache — invalida cache dopo save
13) test_put_override_azioni_invalidates_cache — invalida cache dopo save
14) test_put_emittenti_scope_invalidates_cache — invalida cache dopo save
15) test_put_profilo_reparto_invalidates_department — invalida cache reparto
16) test_cast_param_bool_truthy_false_default — cast 'true'/'false'/'' helper
17) test_cast_param_decimal_empty_to_none — '' -> None convenzione DB
18) test_cast_param_decimal_invalid_returns_none — best-effort, no raise
19) test_get_emittente_form_defaults_ok — happy path con seed atteso
20) test_get_emittente_form_defaults_missing_params — chiavi assenti -> defaults sicuri
21) test_get_emittente_form_defaults_rounding_invalid — rounding fuori enum -> None
22) test_get_emittente_form_defaults_rounding_half_even_rejected — HALF_EVEN -> None (no listini UoM)
23) test_list_emittente_rounding_modes_ok — 4 codici nell'ordine canonico
24) test_list_emittente_rounding_modes_coverage — descrizioni coprono enum (no HALF_EVEN)
25) test_list_audit_sources_delegates_to_repo — service ritorna 8 sorgenti
26) test_list_email_log_stati_ok — l'atteso si deriva da _EMAIL_LOG_STATI_DESCRIZIONI,
    default-first SENT (5 codici dal 2026-09-11, con SIMULATA)
27) test_list_email_log_stati_coverage — descrizioni coprono _EMAIL_LOG_STATI_VALIDI
28) test_get_audit_summary_param_invalido_code_assente — E_AUDIT_SUMMARY_PARAM_NON_VALIDO
29) test_get_audit_summary_param_invalido_storico_id_zero — E_AUDIT_SUMMARY_PARAM_NON_VALIDO
30) test_get_audit_summary_source_non_trovato — E_AUDIT_SOURCE_NON_TROVATO
31) test_get_audit_summary_snapshot_non_trovato — E_AUDIT_SNAPSHOT_NON_TROVATO
32) test_get_audit_summary_ok — happy path con jsonb diff/summary
33) test_run_or_raise_super_admin_guard_traduce_E_OPERATORE_SCOPE_PARAM_NON_VALIDO — refactor Fase 5
"""

from unittest import TestCase
from unittest.mock import patch

from django.db import DatabaseError

from apps.core.services.service_errors import ServiceError

REPO = "apps.amm_software.services.amm_software_service.AmmSoftwareRepository"
INVALIDATE_USER = "apps.amm_software.services.amm_software_service.invalidate_user"
INVALIDATE_DEPT = "apps.amm_software.services.amm_software_service.invalidate_department"
BLACKLIST = "apps.amm_software.services.amm_software_service._blacklist_user_tokens"
MAKE_PW = "apps.amm_software.services.amm_software_service.make_password"


class TestCreateOperatore(TestCase):
    """Test AmmSoftwareService.create_operatore()."""

    @patch(MAKE_PW, return_value="hashed_pw")
    @patch(REPO)
    def test_create_operatore_ok(self, mock_repo_cls, mock_pw):
        """Happy path: crea operatore, password hashata."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.crea_operatore.return_value = 1
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1, "username": "test"}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        result = AmmSoftwareService().create_operatore({
            "cognome": "Rossi", "nome": "Mario", "codice_fiscale": "RSSMRA80A01H501Z",
            "username": "mrossi", "email": "m@test.it", "password": "secret123",
            "qualifica_id": 1,
        })
        self.assertEqual(result["auth_user_id"], 1)
        mock_repo.crea_operatore.assert_called_once()
        # Verifica password hashata
        self.assertEqual(mock_repo.crea_operatore.call_args.kwargs["password_hash"], "hashed_pw")

    @patch(REPO)
    def test_create_operatore_missing_cognome(self, mock_repo_cls):
        """Cognome vuoto -> ServiceError."""
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().create_operatore({
                "cognome": "", "nome": "Mario", "codice_fiscale": "CF",
                "username": "u", "email": "e@t.it", "password": "pw", "qualifica_id": 1,
            })
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")

    @patch(REPO)
    def test_create_operatore_missing_password(self, mock_repo_cls):
        """Password vuota -> ServiceError."""
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().create_operatore({
                "cognome": "R", "nome": "M", "codice_fiscale": "CF",
                "username": "u", "email": "e@t.it", "password": "", "qualifica_id": 1,
            })
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")

    @patch(REPO)
    def test_create_operatore_missing_qualifica(self, mock_repo_cls):
        """Qualifica None -> ServiceError."""
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().create_operatore({
                "cognome": "R", "nome": "M", "codice_fiscale": "CF",
                "username": "u", "email": "e@t.it", "password": "pw", "qualifica_id": None,
            })
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")

    @patch(MAKE_PW, return_value="hashed")
    @patch(REPO)
    def test_create_operatore_password_hashed(self, mock_repo_cls, mock_pw):
        """Verifica che make_password venga chiamato con la password raw."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.crea_operatore.return_value = 1
        mock_repo.get_operatore_detail.return_value = {}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().create_operatore({
            "cognome": "R", "nome": "M", "codice_fiscale": "CF",
            "username": "u", "email": "e@t.it", "password": "mypassword", "qualifica_id": 1,
        })
        mock_pw.assert_called_once_with("mypassword")

    # Scopo: Fase 1 multi-face — il payload con `ruolo_sistema` legacy e'
    # rifiutato (E_AMM_VALIDAZIONE) prima di toccare il repo.
    @patch(REPO)
    def test_create_operatore_rifiuta_ruolo_sistema_legacy(self, mock_repo_cls):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().create_operatore({
                "cognome": "R", "nome": "M", "codice_fiscale": "CF",
                "username": "u", "email": "e@t.it", "password": "pw",
                "qualifica_id": 1, "ruolo_sistema": "ADMIN",
            })
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        mock_repo_cls.return_value.crea_operatore.assert_not_called()

    # Scopo: Fase 7 — il contract pubblico passa `is_super_admin` come bool
    # al repo, niente piu' `ruolo_sistema` legacy esposto. La traduzione
    # verso l'enum legacy della fn DB e' un dettaglio di
    # `AmmSoftwareRepository._legacy_ruolo_from_contract` (privato).
    @patch(MAKE_PW, return_value="hashed")
    @patch(REPO)
    def test_create_operatore_is_super_admin_passato_al_repo(
        self, mock_repo_cls, _mock_pw
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.crea_operatore.return_value = 1
        mock_repo.get_operatore_detail.return_value = {}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().create_operatore({
            "cognome": "R", "nome": "M", "codice_fiscale": "CF",
            "username": "u", "email": "e@t.it", "password": "pw",
            "qualifica_id": 1, "is_super_admin": True,
        })
        kwargs = mock_repo.crea_operatore.call_args.kwargs
        self.assertTrue(kwargs["is_super_admin"])
        self.assertTrue(kwargs["attivo"])
        self.assertNotIn("ruolo_sistema", kwargs)

        # Caso default: nessun flag -> is_super_admin=False, attivo=True.
        mock_repo.crea_operatore.reset_mock()
        AmmSoftwareService().create_operatore({
            "cognome": "R", "nome": "M", "codice_fiscale": "CF",
            "username": "u", "email": "e@t.it", "password": "pw",
            "qualifica_id": 1,
        })
        kwargs = mock_repo.crea_operatore.call_args.kwargs
        self.assertFalse(kwargs["is_super_admin"])
        self.assertTrue(kwargs["attivo"])


class TestGetOperatore(TestCase):
    """Test AmmSoftwareService.get_operatore()."""

    @patch(REPO)
    def test_get_operatore_ok(self, mock_repo_cls):
        mock_repo_cls.return_value.get_operatore_detail.return_value = {"auth_user_id": 1}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        result = AmmSoftwareService().get_operatore(1)
        self.assertEqual(result["auth_user_id"], 1)

    @patch(REPO)
    def test_get_operatore_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.get_operatore_detail.return_value = None
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().get_operatore(999)
        self.assertEqual(ctx.exception.code, "E_AMM_OPERATORE_NOT_FOUND")


class TestUpdateOperatore(TestCase):
    """Test AmmSoftwareService.update_operatore()."""

    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_update_operatore_ok(self, mock_repo_cls, mock_invalidate):
        """Aggiorna e invalida cache."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().update_operatore(1, {"email": "new@test.it"})
        mock_repo.update_operatore.assert_called_once()
        mock_invalidate.assert_called_once_with(1)

    @patch(REPO)
    def test_update_operatore_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.get_operatore_detail.return_value = None
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError):
            AmmSoftwareService().update_operatore(999, {"email": "x"})

    # Scopo: Fase 7 multi-face — il payload {is_super_admin, attivo} viene
    # passato as-is al repository (no traduzione legacy nel service). Le 4
    # combinazioni della matrice sono trasparenti: ogni flag e' ortogonale
    # e indipendente nel repo.
    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_update_operatore_passa_flag_multiface_al_repo(
        self, mock_repo_cls, _mock_invalidate
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        # Caso 1: super=true, attivo=true
        AmmSoftwareService().update_operatore(
            1, {"is_super_admin": True, "attivo": True}
        )
        kwargs = mock_repo.update_operatore.call_args.kwargs
        self.assertTrue(kwargs["is_super_admin"])
        self.assertTrue(kwargs["attivo"])
        self.assertNotIn("ruolo_sistema", kwargs)

        # Caso 2: super=false, attivo=true
        AmmSoftwareService().update_operatore(
            1, {"is_super_admin": False, "attivo": True}
        )
        kwargs = mock_repo.update_operatore.call_args.kwargs
        self.assertFalse(kwargs["is_super_admin"])
        self.assertTrue(kwargs["attivo"])

        # Caso 3: super=true, attivo=false (disabilita un super)
        AmmSoftwareService().update_operatore(
            1, {"is_super_admin": True, "attivo": False}
        )
        kwargs = mock_repo.update_operatore.call_args.kwargs
        self.assertTrue(kwargs["is_super_admin"])
        self.assertFalse(kwargs["attivo"])

        # Caso 4: solo is_super_admin (NO-OP su attivo).
        AmmSoftwareService().update_operatore(1, {"is_super_admin": True})
        kwargs = mock_repo.update_operatore.call_args.kwargs
        self.assertTrue(kwargs["is_super_admin"])
        self.assertIsNone(kwargs["attivo"])

    # Scopo: Fase 1 multi-face — il contract pubblico non ammette piu'
    # `ruolo_sistema`. Il payload con la chiave legacy viene rifiutato
    # con E_AMM_VALIDAZIONE per forzare i client al nuovo contract
    # (is_super_admin + attivo).
    @patch(REPO)
    def test_update_operatore_rifiuta_ruolo_sistema_legacy(self, mock_repo_cls):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().update_operatore(1, {"ruolo_sistema": "ADMIN"})
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        # Il repo non viene neanche chiamato: validazione fallisce prima.
        mock_repo_cls.return_value.update_operatore.assert_not_called()

    # Scopo: Fase 7 — payload con solo `attivo:false` arriva al repo come
    # is_super_admin=None (NO-OP) + attivo=False. La traduzione legacy
    # verso DISABILITATO e' interna al repo (`_legacy_ruolo_from_contract`),
    # invisibile dal service.
    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_update_operatore_attivo_only(
        self, mock_repo_cls, _mock_invalidate
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().update_operatore(1, {"attivo": False})
        kwargs = mock_repo.update_operatore.call_args.kwargs
        self.assertIsNone(kwargs["is_super_admin"])
        self.assertFalse(kwargs["attivo"])
        self.assertNotIn("ruolo_sistema", kwargs)

    # Scopo: Race condition trigger 384 — quando il preview `can_disable`
    # passa ma il trigger DB rifiuta (concorrenza tra sessioni), il service
    # traduce DatabaseError in E_PROFILO_ULTIMO_SUPER_ADMIN preservando
    # il code per l'envelope errore.
    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_update_operatore_super_admin_guard_dbtrigger(
        self, mock_repo_cls, _mock_invalidate
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.update_operatore.side_effect = DatabaseError(
            "ERROR: Codice: E_PROFILO_ULTIMO_SUPER_ADMIN — ultimo super admin attivo"
        )
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().update_operatore(
                1, {"is_super_admin": False, "attivo": True}
            )
        self.assertEqual(ctx.exception.code, "E_PROFILO_ULTIMO_SUPER_ADMIN")


class TestDisabilitaOperatore(TestCase):
    """Test AmmSoftwareService.disabilita_operatore()."""

    @patch(BLACKLIST)
    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_disabilita_operatore_ok(self, mock_repo_cls, mock_invalidate, mock_blacklist):
        """Disabilita, invalida cache, blacklist token."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().disabilita_operatore(1)
        mock_repo.disabilita_operatore.assert_called_once_with(1)
        mock_invalidate.assert_called_once_with(1)
        mock_blacklist.assert_called_once_with(1)

    @patch(REPO)
    def test_disabilita_operatore_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.get_operatore_detail.return_value = None
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError):
            AmmSoftwareService().disabilita_operatore(999)

    # Scopo: Preview `can_disable=false` -> short-circuit Python con
    # E_PROFILO_ULTIMO_SUPER_ADMIN, niente round-trip DB. Il `disable_reason`
    # del detail (it-IT free-form da DB) propaga nel `detail` dell'errore.
    @patch(REPO)
    def test_disabilita_operatore_ultimo_super_admin_preview(self, mock_repo_cls):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_operatore_detail.return_value = {
            "auth_user_id": 1,
            "is_super_admin": True,
            "can_disable": False,
            "disable_reason": "E' l'ultimo super admin attivo.",
        }
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().disabilita_operatore(1)
        self.assertEqual(ctx.exception.code, "E_PROFILO_ULTIMO_SUPER_ADMIN")
        # disabilita_operatore del repo NON deve essere chiamato (short-circuit)
        mock_repo.disabilita_operatore.assert_not_called()

    # Scopo: Preview UX passa (can_disable=true) ma il trigger DB rifiuta
    # comunque per race tra sessioni. Il service traduce DatabaseError in
    # ServiceError E_PROFILO_ULTIMO_SUPER_ADMIN.
    @patch(BLACKLIST)
    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_disabilita_operatore_ultimo_super_admin_dbtrigger(
        self, mock_repo_cls, _mock_invalidate, _mock_blacklist
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_operatore_detail.return_value = {
            "auth_user_id": 1,
            "is_super_admin": True,
            "can_disable": True,
            "disable_reason": None,
        }
        mock_repo.disabilita_operatore.side_effect = DatabaseError(
            "ERROR: E_PROFILO_ULTIMO_SUPER_ADMIN: ..."
        )
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().disabilita_operatore(1)
        self.assertEqual(ctx.exception.code, "E_PROFILO_ULTIMO_SUPER_ADMIN")


class TestOverrideCache(TestCase):
    """Test cache invalidation su override e profili."""

    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_put_override_aree_invalidates_cache(self, mock_repo_cls, mock_invalidate):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_override_aree.return_value = []
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().put_override_aree(1, [])
        mock_invalidate.assert_called_once_with(1)

    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_put_override_azioni_invalidates_cache(self, mock_repo_cls, mock_invalidate):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_override_azioni.return_value = []
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().put_override_azioni(1, [])
        mock_invalidate.assert_called_once_with(1)

    @patch(INVALIDATE_USER)
    @patch(REPO)
    def test_put_emittenti_scope_invalidates_cache(self, mock_repo_cls, mock_invalidate):
        # Fase 2: signature cambiata da `(auth_user_id, list)` a
        # `(auth_user_id, payload)` con scope_mode + emittenti_ids.
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_user_emittenti_scope.return_value = {
            "auth_user_id": 1, "scope_mode": "GLOBAL",
            "emittente_id": None, "emittente_descrizione": None,
            "allowed_scope_modes": ["GLOBAL", "SINGLE"],
            "can_change_scope": True, "change_scope_reason": None,
        }
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().put_emittenti_scope(1, {"scope_mode": "GLOBAL"})
        mock_invalidate.assert_called_once_with(1)

    @patch(INVALIDATE_DEPT)
    @patch(REPO)
    def test_put_profilo_reparto_invalidates_department(self, mock_repo_cls, mock_invalidate):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_profilo_reparto.return_value = {}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().put_profilo_reparto(5, [], [])
        mock_invalidate.assert_called_once_with(5)


# =================================================================
# Fase 3 — Form-defaults emittente fiscale
# =================================================================


PARAM_SVC = "apps.amm_software.services.amm_software_service.ParameterService"


class TestCastParamHelpers(TestCase):
    """Helpers cast best-effort per parameters (text NOT NULL)."""

    def test_cast_param_bool_truthy_false_default(self):
        from apps.amm_software.services.amm_software_service import _cast_param_bool

        self.assertTrue(_cast_param_bool("true"))
        self.assertTrue(_cast_param_bool("TRUE"))
        self.assertTrue(_cast_param_bool(" True "))
        self.assertFalse(_cast_param_bool("false"))
        self.assertFalse(_cast_param_bool(""))
        self.assertFalse(_cast_param_bool(None))
        # non-stringa -> default false (default-safe per bollo_auto)
        self.assertFalse(_cast_param_bool(1))
        self.assertFalse(_cast_param_bool(True))  # bool e' int sottoclasse, no isinstance(str)

    def test_cast_param_decimal_empty_to_none(self):
        # Convenzione DB: stringa vuota = nessuna soglia bollo -> None.
        from apps.amm_software.services.amm_software_service import _cast_param_decimal

        self.assertIsNone(_cast_param_decimal(""))
        self.assertIsNone(_cast_param_decimal("  "))
        self.assertIsNone(_cast_param_decimal(None))

    def test_cast_param_decimal_invalid_returns_none(self):
        # Best-effort: stringhe non parsabili -> None, no raise.
        from decimal import Decimal

        from apps.amm_software.services.amm_software_service import _cast_param_decimal

        self.assertEqual(_cast_param_decimal("100.00"), Decimal("100.00"))
        self.assertEqual(_cast_param_decimal("77.47"), Decimal("77.47"))
        self.assertIsNone(_cast_param_decimal("non-numerico"))
        self.assertIsNone(_cast_param_decimal("12,34"))  # virgola: BE seeda con `.`


class TestGetEmittenteFormDefaults(TestCase):
    """Test AmmSoftwareService.get_emittente_form_defaults()."""

    @patch(PARAM_SVC)
    def test_get_emittente_form_defaults_ok(self, mock_ps_cls):
        # Happy path con i 3 valori seedati (brief DB 2026-04-29).
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        mock_ps_cls.return_value.get_defaults.return_value = {
            "EMITTENTE_DEFAULT_BOLLO_AUTO": "false",
            "EMITTENTE_DEFAULT_BOLLO_SOGLIA": "",
            "EMITTENTE_DEFAULT_ROUNDING_POLICY": "HALF_UP",
        }

        result = AmmSoftwareService().get_emittente_form_defaults(
            django_user_id=42, group_ids=[1, 2], emittente_fiscale_id=None,
        )

        self.assertEqual(result["defaults"], {
            "bollo_auto": False,
            "bollo_soglia": None,
            "rounding_policy": "HALF_UP",
        })
        self.assertEqual(result["non_editable_fields"], ["codice", "soggetto_id"])
        # Verifica chiamata ParameterService col contesto utente.
        mock_ps_cls.return_value.get_defaults.assert_called_once_with(
            ["EMITTENTE_DEFAULT_BOLLO_AUTO", "EMITTENTE_DEFAULT_BOLLO_SOGLIA", "EMITTENTE_DEFAULT_ROUNDING_POLICY"],
            django_user_id=42,
            group_ids=[1, 2],
            emittente_fiscale_id=None,
        )

    @patch(PARAM_SVC)
    def test_get_emittente_form_defaults_missing_params(self, mock_ps_cls):
        # Chiavi assenti: cast helpers tornano default sicuri (False / None / None).
        # Non deve sollevare: il form parte comunque, l'utente compila a mano.
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        mock_ps_cls.return_value.get_defaults.return_value = {}

        result = AmmSoftwareService().get_emittente_form_defaults()

        self.assertEqual(result["defaults"], {
            "bollo_auto": False,
            "bollo_soglia": None,
            "rounding_policy": None,
        })

    @patch(PARAM_SVC)
    def test_get_emittente_form_defaults_rounding_invalid(self, mock_ps_cls):
        # Rounding policy fuori enum -> None (best-effort, no raise).
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        mock_ps_cls.return_value.get_defaults.return_value = {
            "EMITTENTE_DEFAULT_ROUNDING_POLICY": "BANKER_2024",
        }

        result = AmmSoftwareService().get_emittente_form_defaults()

        self.assertIsNone(result["defaults"]["rounding_policy"])

    @patch(PARAM_SVC)
    def test_get_emittente_form_defaults_rounding_half_even_rejected(self, mock_ps_cls):
        # HALF_EVEN e' valido per UoM operativa (catalogo) ma NON per emittente
        # fiscale (CHECK chk_emittenti_fiscali_rounding_policy ammette solo 4
        # valori). Defense-in-depth: il service non lo accetta nemmeno se per
        # errore qualcuno lo seedasse.
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        mock_ps_cls.return_value.get_defaults.return_value = {
            "EMITTENTE_DEFAULT_ROUNDING_POLICY": "HALF_EVEN",
        }

        result = AmmSoftwareService().get_emittente_form_defaults()

        self.assertIsNone(result["defaults"]["rounding_policy"])


class TestListEmittenteRoundingModes(TestCase):
    """Lookup statico modi di arrotondamento emittente fiscale (Fase 3 — A6)."""

    def test_list_emittente_rounding_modes_ok(self):
        # 4 codici nell'ordine canonico "default-first" (HALF_UP primo,
        # corrisponde a EMITTENTE_DEFAULT_ROUNDING_POLICY).
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        result = AmmSoftwareService().list_emittente_rounding_modes()

        self.assertEqual(len(result), 4)
        codici = [r["codice"] for r in result]
        self.assertEqual(codici, ["HALF_UP", "HALF_DOWN", "UP", "DOWN"])
        for row in result:
            self.assertTrue(row["descrizione"])
            self.assertIsInstance(row["ordering"], int)

    def test_list_emittente_rounding_modes_coverage(self):
        # Difesa coerenza enum/descrizioni + assenza HALF_EVEN
        # (allineato al CHECK chk_emittenti_fiscali_rounding_policy).
        from apps.amm_software.services import amm_software_service as svc

        descritti = {codice for codice, _desc, _ord in svc._ROUNDING_MODE_DESCRIZIONI_EMITTENTE}
        self.assertEqual(descritti, svc._ROUNDING_MODE_VALIDI_EMITTENTE)
        self.assertNotIn("HALF_EVEN", descritti)
        self.assertEqual(descritti, {"UP", "DOWN", "HALF_UP", "HALF_DOWN"})


# =================================================================
# Fase 5 — audit hardening + email log lookup
# =================================================================


class TestListAuditSources(TestCase):
    """Lookup audit sources delega al repo (Fase 5 — A13)."""

    @patch(REPO)
    def test_list_audit_sources_delegates_to_repo(self, mock_repo_cls):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        sample_sources = [
            {"code": "user_override_aree", "label_key": "amm.audit_tabella_override_aree", "area_funzionale": "PERMESSI"},
            {"code": "identita_digitali", "label_key": "amm.audit_tabella_identita", "area_funzionale": "AUTH"},
        ]
        mock_repo_cls.return_value.list_audit_sources.return_value = sample_sources

        result = AmmSoftwareService().list_audit_sources()

        self.assertEqual(result, sample_sources)
        mock_repo_cls.return_value.list_audit_sources.assert_called_once_with()


class TestListEmailLogStati(TestCase):
    """Lookup statico stati email log (Fase 5)."""

    def test_list_email_log_stati_ok(self):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        result = AmmSoftwareService().list_email_log_stati()

        codici = [r["codice"] for r in result]
        # ⭐ L'atteso si DERIVA dall'ordine dichiarato, non si ricopia: fino al
        #    2026-09-11 qui c'era la lista dei quattro codici scritta a mano —
        #    una SEDE IN PIU' dello stesso vocabolario, che il quinto valore
        #    (`SIMULATA`) ha fatto emergere facendo rosso in due punti.
        # ⚠️ E non e' tautologico: pretende che l'ordine di USCITA coincida con
        #    il campo `ordering`, che nessun codice si perda per strada e che
        #    «default-first» sopravviva.
        # ⛔ Attenzione a come e' scritto il service: NON ordina: restituisce la
        #    tupla nell'ordine in cui e' DICHIARATA. Quindi questo confronto e'
        #    proprio il presidio di quella coincidenza — una riga aggiunta in
        #    fondo con `ordering` basso fa rosso qui, che e' cio' che si vuole.
        from apps.amm_software.services import amm_software_service as _svc
        atteso = [c for c, _d, _o in sorted(
            _svc._EMAIL_LOG_STATI_DESCRIZIONI, key=lambda r: r[2],
        )]
        self.assertEqual(codici, atteso)
        self.assertEqual(codici[0], "SENT", "l'ordinamento resta default-first")
        for row in result:
            self.assertTrue(row["descrizione"])
            self.assertIsInstance(row["ordering"], int)

    def test_list_email_log_stati_coverage(self):
        # Difesa coerenza enum/descrizioni: aggiungere un codice in
        # _EMAIL_LOG_STATI_DESCRIZIONI senza aggiornare _VALIDI fa fallire qui.
        from apps.amm_software.services import amm_software_service as svc

        descritti = {codice for codice, _desc, _ord in svc._EMAIL_LOG_STATI_DESCRIZIONI}
        self.assertEqual(descritti, svc._EMAIL_LOG_STATI_VALIDI)


class TestGetAuditSummary(TestCase):
    """Validazioni get_audit_summary + traduzione errori (Fase 5)."""

    @patch(REPO)
    def test_get_audit_summary_param_invalido_code_assente(self, mock_repo_cls):
        del mock_repo_cls
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().get_audit_summary(None, 5)
        self.assertEqual(ctx.exception.code, "E_AUDIT_SUMMARY_PARAM_NON_VALIDO")

    @patch(REPO)
    def test_get_audit_summary_param_invalido_storico_id_zero(self, mock_repo_cls):
        del mock_repo_cls
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().get_audit_summary("user_override_aree", 0)
        self.assertEqual(ctx.exception.code, "E_AUDIT_SUMMARY_PARAM_NON_VALIDO")

    @patch(REPO)
    def test_get_audit_summary_source_non_trovato(self, mock_repo_cls):
        # Whitelist `vw_audit_sources` non contiene il code: errore esplicito
        # prima di toccare la funzione DB (defense-in-depth).
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        mock_repo_cls.return_value.list_audit_sources.return_value = [
            {"code": "user_override_aree", "label_key": "amm.x", "area_funzionale": "PERMESSI"},
        ]

        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().get_audit_summary("source_inesistente", 5)
        self.assertEqual(ctx.exception.code, "E_AUDIT_SOURCE_NON_TROVATO")

    @patch(REPO)
    def test_get_audit_summary_snapshot_non_trovato(self, mock_repo_cls):
        # Repo ritorna None (DB ha sollevato E_AUDIT_SNAPSHOT_NON_TROVATO,
        # tradotto a None dal repo) -> service mappa a ServiceError 404.
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        mock_repo_cls.return_value.list_audit_sources.return_value = [
            {"code": "user_override_aree", "label_key": "amm.x", "area_funzionale": "PERMESSI"},
        ]
        mock_repo_cls.return_value.get_audit_summary.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().get_audit_summary("user_override_aree", 9999)
        self.assertEqual(ctx.exception.code, "E_AUDIT_SNAPSHOT_NON_TROVATO")

    @patch(REPO)
    def test_get_audit_summary_ok(self, mock_repo_cls):
        # Happy path: shape jsonb {summary, diff} preservato.
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        mock_repo_cls.return_value.list_audit_sources.return_value = [
            {"code": "user_override_aree", "label_key": "amm.x", "area_funzionale": "PERMESSI"},
        ]
        mock_repo_cls.return_value.get_audit_summary.return_value = {
            "summary": "2 modifiche",
            "diff": [{"field": "livello", "old": "TUTTO", "new": "LETTURA"}],
        }

        result = AmmSoftwareService().get_audit_summary("user_override_aree", 7)

        self.assertEqual(result["summary"], "2 modifiche")
        self.assertEqual(len(result["diff"]), 1)


class TestSuperAdminGuardScopeParam(TestCase):
    """Refactor Fase 5: il guard distingue E_OPERATORE_SCOPE_PARAM_NON_VALIDO."""

    def test_run_or_raise_super_admin_guard_traduce_E_OPERATORE_SCOPE_PARAM_NON_VALIDO(self):
        # Il refactor DB di Fase 2 ha sostituito RAISE 22023 generico con
        # codice stabile. Il guard wrapper deve riconoscerlo e mapparlo.
        from apps.amm_software.services.amm_software_service import (
            _run_or_raise_super_admin_guard,
        )

        def repo_call():
            raise DatabaseError("E_OPERATORE_SCOPE_PARAM_NON_VALIDO: scope_mode invalido")

        with self.assertRaises(ServiceError) as ctx:
            _run_or_raise_super_admin_guard(repo_call)
        self.assertEqual(ctx.exception.code, "E_OPERATORE_SCOPE_PARAM_NON_VALIDO")
