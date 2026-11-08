# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per AmmSoftwareService — validazione, orchestrazione,
#        cache invalidation. Mock repository, CI-compatible.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_create_operatore_ok — happy path, credenziale col segnaposto non utilizzabile
 2) test_create_operatore_missing_cognome — campo obbligatorio mancante
 3) test_create_operatore_rifiuta_password — la password la sceglie l'operatore (L-3)
 4) test_create_operatore_missing_qualifica — qualifica mancante
 5) test_create_operatore_credenziale_riusata — la risposta dice il riuso (D-6)
 5a) test_create_operatore_consenso_al_riuso — `riusa_auth_user_id` arriva al repo, assente = None
 6) test_get_operatore_ok — dettaglio operatore
 7) test_get_operatore_not_found — id inesistente
 7a) test_get_operatore_di_un_altra_categoria — una macchina o un cliente non e' un operatore (404)
 8) test_update_operatore_ok — aggiorna e invalida cache
 9) test_update_operatore_not_found — id inesistente
 9a) test_update_operatore_passa_flag_multiface_al_repo — Fase 7: is_super_admin com'e', attivo solo come transizione (D-3)
 9a-bis) test_update_operatore_non_riaccende_la_veste_spenta — D-3: attivo=true su veste spenta → E_AMM_VALIDAZIONE
 9b) test_update_operatore_rifiuta_ruolo_sistema_legacy — guard fail-fast su payload legacy
 9c) test_update_operatore_super_admin_guard_dbtrigger — race condition trigger 384
 9d) test_update_operatore_attivo_only — spegnere dall'interruttore e' «Disabilita», dopo i campi; chiude le sessioni della veste operatore
 9e) test_update_operatore_spento_legge_la_veste_prima — id della veste letto prima di spegnerla
 9f) test_update_operatore_senza_spegnere_non_chiude_sessioni — salvare non chiude sessioni
 9g) test_update_operatore_gia_spento_non_invalida_l_invito — salvare un operatore gia' spento non e' uno spegnimento (ne' richiude la risorsa umana)
10) test_disabilita_operatore_ok — disabilita, invalida cache, chiude le sessioni della sola veste operatore
10b) test_disabilita_operatore_revoca_fallita_propaga — revoca e disattivazione in una transazione
11) test_disabilita_operatore_not_found — id inesistente
11a) test_disabilita_operatore_ultimo_super_admin_preview — preview Python (fast-path)
11b) test_disabilita_operatore_ultimo_super_admin_dbtrigger — race condition trigger 384
12) test_create_operatore_rifiuta_ruolo_sistema_legacy — guard fail-fast su payload legacy
12a) test_create_operatore_is_super_admin_passato_al_repo — Fase 7: bool al repo (no enum)
12b) test_create_operatore_senza_sesso_non_lo_inventa — soggetto nuovo senza sesso: None al DB (lo giudica il guard), niente default «M»
12c) test_create_operatore_campo_non_stringa_400_col_campo — non-stringa → 400 col campo, non un 500
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
26-27) (usciti il 2026-09-26 col vocabolario degli stati email: ora in
    `core/tests/api/test_email_log_stati_lookup.py`)
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

from apps.core.services.invito_veste import PORTA_OPERATORE
from apps.core.services.service_errors import ServiceError

REPO = "apps.amm_software.services.amm_software_service.AmmSoftwareRepository"
INVALIDATE_USER = "apps.amm_software.services.amm_software_service.invalidate_user"
INVALIDATE_DEPT = "apps.amm_software.services.amm_software_service.invalidate_department"
TRANSACTION = "apps.amm_software.services.amm_software_service.transaction"
INVITO = "apps.amm_software.services.amm_software_service.InvitoVeste"


# Scopo: `django.db.transaction` finto, senza database: `atomic()` esegue i
#        callback di `on_commit` SOLO se il blocco esce senza eccezioni, come
#        il commit vero. Basta a provare l'ORDINE (cosa sta dentro la
#        transazione, cosa aspetta il commit), non il ROLLBACK, che e' del DB.
class _TransazioneFinta:
    def __init__(self) -> None:
        self._in_attesa: list = []

    def on_commit(self, callback) -> None:
        self._in_attesa.append(callback)

    def atomic(self):
        finta = self

        class _Blocco:
            def __enter__(self):
                return self

            def __exit__(self, tipo, _valore, _tb):
                callback, finta._in_attesa = finta._in_attesa, []
                if tipo is None:
                    for cb in callback:
                        cb()
                return False

        return _Blocco()


class TestCreateOperatore(TestCase):
    """Test AmmSoftwareService.create_operatore() — regola unica dell'invito
    (L-3): niente password dall'admin, veste spenta, credenziale riusata."""

    _PAYLOAD = {
        "cognome": "Rossi", "nome": "Mario", "codice_fiscale": "RSSMRA80A01H501Z",
        "sesso": "M", "username": "mrossi", "email": "m@test.it", "qualifica_id": 1,
    }

    def _repo(self, mock_repo_cls, *, riusata=False):
        mock_repo = mock_repo_cls.return_value
        mock_repo.crea_operatore.return_value = {
            "auth_user_id": 1, "username": "mrossi", "credenziale_riusata": riusata,
        }
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1, "username": "mrossi"}
        return mock_repo

    # Scopo: Happy path: la credenziale nuova nasce col segnaposto NON
    # utilizzabile (la password la sceglie la persona attivando l'invito).
    @patch(REPO, autospec=True)
    def test_create_operatore_ok(self, mock_repo_cls):
        from django.contrib.auth.hashers import is_password_usable

        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        mock_repo = self._repo(mock_repo_cls)
        result = AmmSoftwareService().create_operatore(dict(self._PAYLOAD))
        self.assertEqual(result["auth_user_id"], 1)
        self.assertFalse(result["credenziale_riusata"])
        kwargs = mock_repo.crea_operatore.call_args.kwargs
        self.assertFalse(is_password_usable(kwargs["password_hash"]))
        self.assertNotIn("attivo", kwargs)

    # Scopo: Soggetto nuovo senza sesso: None al DB, nessun default e nessun
    # controllo qui. Il flusso A crea un privato (REQUIRED) e il rifiuto arriva
    # dal guard `trgfn_soggetti_guard_sesso_policy`, prima del consenso al
    # riuso (brief-db-sesso-senza-default §6). `X` passa: e' un valore.
    @patch(REPO, autospec=True)
    def test_create_operatore_senza_sesso_non_lo_inventa(self, mock_repo_cls):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        mock_repo = self._repo(mock_repo_cls)
        for sesso, atteso in ((None, None), ("", None), ("x", "X")):
            with self.subTest(sesso=sesso):
                AmmSoftwareService().create_operatore({**self._PAYLOAD, "sesso": sesso})
                self.assertEqual(mock_repo.crea_operatore.call_args.kwargs["sesso"], atteso)

    # Scopo: un campo persona che non e' una stringa e' un 400 sul campo, non
    # un 500: prima `(payload.get(k) or "").strip()` era un AttributeError.
    @patch(REPO, autospec=True)
    def test_create_operatore_campo_non_stringa_400_col_campo(self, mock_repo_cls):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        mock_repo = self._repo(mock_repo_cls)
        for campo in ("cognome", "sesso", "username", "soggetto_id"):
            with self.subTest(campo=campo):
                with self.assertRaises(ServiceError) as ctx:
                    AmmSoftwareService().create_operatore({**self._PAYLOAD, campo: 1})
                self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
                self.assertEqual(ctx.exception.context.get("field"), campo)
        mock_repo.crea_operatore.assert_not_called()

    # Scopo: Email di una credenziale esistente (D-6): la risposta lo dice,
    # perche' il pannello avvisi l'admin.
    @patch(REPO, autospec=True)
    def test_create_operatore_credenziale_riusata(self, mock_repo_cls):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        self._repo(mock_repo_cls, riusata=True)
        result = AmmSoftwareService().create_operatore(dict(self._PAYLOAD))
        self.assertTrue(result["credenziale_riusata"])

    # Scopo: Il consenso al riuso (`20260925-51`) e' una dichiarazione del
    # client: il service la trasporta com'e' e, assente, non la inventa (la
    # prima chiamata DEVE andare senza, perche' la madre chieda conferma).
    @patch(REPO, autospec=True)
    def test_create_operatore_consenso_al_riuso(self, mock_repo_cls):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        mock_repo = self._repo(mock_repo_cls, riusata=True)
        AmmSoftwareService().create_operatore(dict(self._PAYLOAD))
        self.assertIsNone(mock_repo.crea_operatore.call_args.kwargs["riusa_auth_user_id"])
        AmmSoftwareService().create_operatore({**self._PAYLOAD, "riusa_auth_user_id": "42"})
        self.assertEqual(mock_repo.crea_operatore.call_args.kwargs["riusa_auth_user_id"], 42)

    # Scopo: `password` nel payload e' rifiutata: un client che la manda
    # crederebbe che valga.
    @patch(REPO, autospec=True)
    def test_create_operatore_rifiuta_password(self, mock_repo_cls):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().create_operatore({**self._PAYLOAD, "password": "pw"})
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        self.assertIn("password", ctx.exception.message)
        mock_repo_cls.return_value.crea_operatore.assert_not_called()

    @patch(REPO, autospec=True)
    def test_create_operatore_missing_cognome(self, mock_repo_cls):
        """Cognome vuoto -> ServiceError."""
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().create_operatore({**self._PAYLOAD, "cognome": ""})
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        self.assertIn("Cognome", ctx.exception.message)

    @patch(REPO, autospec=True)
    def test_create_operatore_missing_qualifica(self, mock_repo_cls):
        """Qualifica None -> ServiceError."""
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().create_operatore({**self._PAYLOAD, "qualifica_id": None})
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        self.assertIn("Qualifica", ctx.exception.message)

    # Scopo: Fase 1 multi-face — il payload con `ruolo_sistema` legacy e'
    # rifiutato (E_AMM_VALIDAZIONE) prima di toccare il repo.
    @patch(REPO, autospec=True)
    def test_create_operatore_rifiuta_ruolo_sistema_legacy(self, mock_repo_cls):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().create_operatore({**self._PAYLOAD, "ruolo_sistema": "ADMIN"})
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        mock_repo_cls.return_value.crea_operatore.assert_not_called()

    # Scopo: `is_super_admin` passa al repo come bool (default False).
    @patch(REPO, autospec=True)
    def test_create_operatore_is_super_admin_passato_al_repo(self, mock_repo_cls):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        mock_repo = self._repo(mock_repo_cls)
        AmmSoftwareService().create_operatore({**self._PAYLOAD, "is_super_admin": True})
        kwargs = mock_repo.crea_operatore.call_args.kwargs
        self.assertTrue(kwargs["is_super_admin"])
        self.assertNotIn("ruolo_sistema", kwargs)

        mock_repo.crea_operatore.reset_mock()
        AmmSoftwareService().create_operatore(dict(self._PAYLOAD))
        self.assertFalse(mock_repo.crea_operatore.call_args.kwargs["is_super_admin"])


class TestGetOperatore(TestCase):
    """Test AmmSoftwareService.get_operatore()."""

    @patch(REPO, autospec=True)
    def test_get_operatore_ok(self, mock_repo_cls):
        mock_repo_cls.return_value.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo_cls.return_value.get_operatore_detail.return_value = {"auth_user_id": 1}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        result = AmmSoftwareService().get_operatore(1)
        self.assertEqual(result["auth_user_id"], 1)

    @patch(REPO, autospec=True)
    def test_get_operatore_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo_cls.return_value.get_operatore_detail.return_value = None
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().get_operatore(999)
        self.assertEqual(ctx.exception.code, "E_AMM_OPERATORE_NOT_FOUND")

    # Scopo: Una credenziale di categoria SISTEMA o ALTRO risponde come un id
    #        inesistente, e il dettaglio non si legge: i comandi dell'operatore
    #        spegnerebbero la veste OPERATORE di un utente tecnico (R-DB-A1).
    @patch(REPO, autospec=True)
    def test_get_operatore_di_un_altra_categoria(self, mock_repo_cls):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        for categoria in ("SISTEMA", "ALTRO", None):
            with self.subTest(categoria=categoria):
                mock_repo_cls.return_value.get_categoria_accesso.return_value = categoria
                mock_repo_cls.return_value.get_operatore_detail.return_value = {"auth_user_id": 9}
                with self.assertRaises(ServiceError) as ctx:
                    AmmSoftwareService().get_operatore(9)
                self.assertEqual(ctx.exception.code, "E_AMM_OPERATORE_NOT_FOUND")
        mock_repo_cls.return_value.get_operatore_detail.assert_not_called()


class TestUpdateOperatore(TestCase):
    """Test AmmSoftwareService.update_operatore()."""

    # ⛔ Spegnere l'operatore invalida gli inviti pendenti (A-5): senza questo
    #    mock l'UPDATE andrebbe su `config.token_monouso` del DB di sviluppo.
    def setUp(self):
        patcher = patch(INVITO)
        self.mock_invito = patcher.start()
        self.addCleanup(patcher.stop)

    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_update_operatore_ok(self, mock_repo_cls, mock_invalidate):
        """Aggiorna e invalida cache."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().update_operatore(1, {"email": "new@test.it"})
        mock_repo.update_operatore.assert_called_once()
        mock_invalidate.assert_called_once_with(1)

    @patch(REPO, autospec=True)
    def test_update_operatore_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo_cls.return_value.get_operatore_detail.return_value = None
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError):
            AmmSoftwareService().update_operatore(999, {"email": "x"})

    # Scopo: Fase 7 multi-face — `is_super_admin` arriva al repository com'e';
    # `attivo` solo come TRANSIZIONE (D-3, 2026-10-04): `true` su una veste
    # accesa non cambia niente, `false` la spegne con la scrittura di
    # «Disabilita» (2026-10-04). I due flag restano ortogonali.
    @patch(TRANSACTION, new_callable=_TransazioneFinta)
    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_update_operatore_passa_flag_multiface_al_repo(
        self, mock_repo_cls, _mock_invalidate, _tx,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1, "veste_attiva": True}
        mock_repo.get_veste_operatore_id.return_value = 7
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        # Caso 1: super=true, attivo=true su veste accesa (nessun cambio d'accesso)
        AmmSoftwareService().update_operatore(
            1, {"is_super_admin": True, "attivo": True}
        )
        kwargs = mock_repo.update_operatore.call_args.kwargs
        self.assertTrue(kwargs["is_super_admin"])
        self.assertNotIn("attivo", kwargs)
        self.assertNotIn("ruolo_sistema", kwargs)
        mock_repo.disabilita_operatore.assert_not_called()

        # Caso 2: super=false, attivo=true
        AmmSoftwareService().update_operatore(
            1, {"is_super_admin": False, "attivo": True}
        )
        kwargs = mock_repo.update_operatore.call_args.kwargs
        self.assertFalse(kwargs["is_super_admin"])
        mock_repo.disabilita_operatore.assert_not_called()

        # Caso 3: super=true, attivo=false (disabilita un super)
        AmmSoftwareService().update_operatore(
            1, {"is_super_admin": True, "attivo": False}
        )
        kwargs = mock_repo.update_operatore.call_args.kwargs
        self.assertTrue(kwargs["is_super_admin"])
        mock_repo.disabilita_operatore.assert_called_once_with(1)
        mock_repo.disabilita_operatore.reset_mock()

        # Caso 4: solo is_super_admin (NO-OP su attivo).
        AmmSoftwareService().update_operatore(1, {"is_super_admin": True})
        kwargs = mock_repo.update_operatore.call_args.kwargs
        self.assertTrue(kwargs["is_super_admin"])
        mock_repo.disabilita_operatore.assert_not_called()

    # Scopo: `valido_al` (fine del rapporto) ha tre stati, brief-db-veste-
    # utilizzabile §10: assente -> MISSING (non si tocca), una data -> date,
    # `null` -> None (si toglie). Un formato sbagliato non arriva al repository.
    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_update_operatore_valido_al_tre_stati(self, mock_repo_cls, _mock_invalidate):
        from datetime import date

        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        from apps.core.services.payload_helpers import MISSING

        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1, "veste_attiva": True}

        AmmSoftwareService().update_operatore(1, {"first_name": "A"})
        self.assertIs(mock_repo.update_operatore.call_args.kwargs["valido_al"], MISSING)

        AmmSoftwareService().update_operatore(1, {"valido_al": "2026-12-31"})
        self.assertEqual(mock_repo.update_operatore.call_args.kwargs["valido_al"], date(2026, 12, 31))

        AmmSoftwareService().update_operatore(1, {"valido_al": None})
        self.assertIsNone(mock_repo.update_operatore.call_args.kwargs["valido_al"])

        mock_repo.update_operatore.reset_mock()
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().update_operatore(1, {"valido_al": "31/12/2026"})
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        mock_repo.update_operatore.assert_not_called()

    # Scopo: D-3 — l'interruttore non riaccende una veste spenta: 400
    # E_AMM_VALIDAZIONE sul campo `attivo`, e niente arriva al repository.
    # Si riattiva col reinvio dell'invito.
    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_update_operatore_non_riaccende_la_veste_spenta(
        self, mock_repo_cls, mock_invalidate,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1, "veste_attiva": False}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().update_operatore(1, {"attivo": True, "first_name": "A"})
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        self.assertEqual(ctx.exception.context.get("field"), "attivo")
        mock_repo.update_operatore.assert_not_called()
        mock_invalidate.assert_not_called()

    # Scopo: Fase 1 multi-face — il contract pubblico non ammette piu'
    # `ruolo_sistema`. Il payload con la chiave legacy viene rifiutato
    # con E_AMM_VALIDAZIONE per forzare i client al nuovo contract
    # (is_super_admin + attivo).
    @patch(REPO, autospec=True)
    def test_update_operatore_rifiuta_ruolo_sistema_legacy(self, mock_repo_cls):
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().update_operatore(1, {"ruolo_sistema": "ADMIN"})
        self.assertEqual(ctx.exception.code, "E_AMM_VALIDAZIONE")
        # Il repo non viene neanche chiamato: validazione fallisce prima.
        mock_repo_cls.return_value.update_operatore.assert_not_called()

    # Scopo: Payload con solo `attivo:false` su una veste accesa: i campi
    # arrivano al repo (is_super_admin=None, NO-OP) e POI lo spegnimento e'
    # quello di «Disabilita» (2026-10-04: veste, rapporto con `valido_al =
    # oggi`, sync), nella stessa strada che chiude sessioni e inviti.
    @patch(TRANSACTION, new_callable=_TransazioneFinta)
    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_update_operatore_attivo_only(
        self, mock_repo_cls, mock_invalidate, _tx,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1, "veste_attiva": True}
        mock_repo.get_veste_operatore_id.return_value = 7
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().update_operatore(1, {"attivo": False})
        kwargs = mock_repo.update_operatore.call_args.kwargs
        self.assertIsNone(kwargs["is_super_admin"])
        self.assertNotIn("attivo", kwargs)
        self.assertNotIn("ruolo_sistema", kwargs)
        chiamate = [c[0] for c in mock_repo.method_calls]
        self.assertLess(chiamate.index("update_operatore"), chiamate.index("disabilita_operatore"))
        mock_repo.disabilita_operatore.assert_called_once_with(1)
        # A-5: l'interruttore spento chiude le sessioni come «Disabilita»,
        # e solo quelle della veste operatore (D-5).
        self.mock_invito.return_value.chiudi_veste_spenta.assert_called_once_with(
            PORTA_OPERATORE, auth_user_id=1, identita_id=7,
        )

    # Scopo: L'id della veste si legge PRIMA di spegnerla: dopo, la veste di
    #        riferimento potrebbe essere un'altra (l'accesa vince sulla spenta).
    @patch(TRANSACTION, new_callable=_TransazioneFinta)
    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_update_operatore_spento_legge_la_veste_prima(
        self, mock_repo_cls, _mock_invalidate, _tx,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1, "veste_attiva": True}
        mock_repo.get_veste_operatore_id.return_value = 7
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().update_operatore(1, {"attivo": False})
        chiamate = [c[0] for c in mock_repo.method_calls]
        self.assertLess(
            chiamate.index("get_veste_operatore_id"), chiamate.index("disabilita_operatore"),
        )

    # Scopo: Salvare un operatore GIA' spento (il drawer manda `attivo: false`
    #        a ogni salvataggio) non e' uno spegnimento: l'invito spedito per
    #        riaccenderlo (D-3) resta valido, e nessuna sessione si tocca.
    @patch(TRANSACTION, new_callable=_TransazioneFinta)
    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_update_operatore_gia_spento_non_invalida_l_invito(
        self, mock_repo_cls, mock_invalidate, _tx,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1, "veste_attiva": False}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().update_operatore(1, {"attivo": False, "email": "nuova@example.com"})
        # Niente transizione: la veste non si riscrive e la risorsa umana
        # (riaperta dall'invito, D-3) non si richiude.
        mock_repo.disabilita_operatore.assert_not_called()
        self.mock_invito.assert_not_called()
        mock_repo.get_veste_operatore_id.assert_not_called()
        mock_invalidate.assert_called_once_with(1)

    # Scopo: Salvare senza spegnere (anche con `attivo: true` su una veste
    #        accesa) non chiude sessioni.
    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_update_operatore_senza_spegnere_non_chiude_sessioni(
        self, mock_repo_cls, mock_invalidate,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1, "veste_attiva": True}
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().update_operatore(1, {"attivo": True, "first_name": "A"})
        AmmSoftwareService().update_operatore(1, {"first_name": "B"})
        mock_repo.get_veste_operatore_id.assert_not_called()
        self.mock_invito.assert_not_called()
        self.assertEqual(mock_invalidate.call_count, 2)

    # Scopo: Race condition trigger 384 — quando il preview `can_disable`
    # passa ma il trigger DB rifiuta (concorrenza tra sessioni), il service
    # traduce DatabaseError in E_PROFILO_ULTIMO_SUPER_ADMIN preservando
    # il code per l'envelope errore.
    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_update_operatore_super_admin_guard_dbtrigger(
        self, mock_repo_cls, _mock_invalidate
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1, "veste_attiva": True}
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

    # ⛔ Spegnere l'operatore invalida gli inviti pendenti (A-5): senza questo
    #    mock l'UPDATE andrebbe su `config.token_monouso` del DB di sviluppo.
    def setUp(self):
        patcher = patch(INVITO)
        self.mock_invito = patcher.start()
        self.addCleanup(patcher.stop)

    @patch(TRANSACTION, new_callable=_TransazioneFinta)
    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_disabilita_operatore_ok(self, mock_repo_cls, mock_invalidate, _tx):
        """Disabilita, invalida cache, chiude le sessioni della veste operatore."""
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_veste_operatore_id.return_value = 7
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().disabilita_operatore(1)
        mock_repo.disabilita_operatore.assert_called_once_with(1)
        # D-5, A-5: inviti, sessioni e cache della SOLA veste operatore, dal BB.
        self.mock_invito.return_value.chiudi_veste_spenta.assert_called_once_with(
            PORTA_OPERATORE, auth_user_id=1, identita_id=7,
        )

    # Scopo: la revoca delle sessioni FALLISCE → l'errore propaga e la cache
    #        NON si invalida: la disattivazione e la revoca stanno nella stessa
    #        transazione, e senza commit non c'e' niente da invalidare. Prima
    #        la disattivazione committava da sola e l'operatore restava
    #        disattivato con le sessioni vive.
    @patch(TRANSACTION, new_callable=_TransazioneFinta)
    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_disabilita_operatore_revoca_fallita_propaga(
        self, mock_repo_cls, mock_invalidate, _tx,
    ):
        mock_repo_cls.return_value.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo_cls.return_value.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo_cls.return_value.get_veste_operatore_id.return_value = 7
        self.mock_invito.return_value.chiudi_veste_spenta.side_effect = DatabaseError(
            "scrittura blacklist fallita"
        )
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(DatabaseError):
            AmmSoftwareService().disabilita_operatore(1)
        mock_invalidate.assert_not_called()

    @patch(REPO, autospec=True)
    def test_disabilita_operatore_not_found(self, mock_repo_cls):
        mock_repo_cls.return_value.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo_cls.return_value.get_operatore_detail.return_value = None
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError):
            AmmSoftwareService().disabilita_operatore(999)

    # Scopo: Preview `can_disable=false` -> short-circuit Python con
    # E_PROFILO_ULTIMO_SUPER_ADMIN, niente round-trip DB. Il `disable_reason`
    # e' un codice macchina (§16): NON finisce nel `detail`, sta nel contesto.
    @patch(REPO, autospec=True)
    def test_disabilita_operatore_ultimo_super_admin_preview(self, mock_repo_cls):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {
            "auth_user_id": 1,
            "is_super_admin": True,
            "can_disable": False,
            "disable_reason": "ULTIMO_SUPER_ADMIN",
            "disable_reason_key": "amministrazione.operatori.disabilita_reason.ultimo_super_admin",
        }
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().disabilita_operatore(1)
        self.assertEqual(ctx.exception.code, "E_PROFILO_ULTIMO_SUPER_ADMIN")
        self.assertNotIn("ULTIMO_SUPER_ADMIN", ctx.exception.detail or "")
        self.assertEqual(ctx.exception.context["reason"], "ULTIMO_SUPER_ADMIN")
        # disabilita_operatore del repo NON deve essere chiamato (short-circuit)
        mock_repo.disabilita_operatore.assert_not_called()

    # Scopo: Preview UX passa (can_disable=true) ma il trigger DB rifiuta
    # comunque per race tra sessioni. Il service traduce DatabaseError in
    # ServiceError E_PROFILO_ULTIMO_SUPER_ADMIN.
    @patch(TRANSACTION, new_callable=_TransazioneFinta)
    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_disabilita_operatore_ultimo_super_admin_dbtrigger(
        self, mock_repo_cls, _mock_invalidate, _tx,
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
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
    @patch(REPO, autospec=True)
    def test_put_override_aree_invalidates_cache(self, mock_repo_cls, mock_invalidate):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_override_aree.return_value = []
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().put_override_aree(1, [])
        mock_invalidate.assert_called_once_with(1)

    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_put_override_azioni_invalidates_cache(self, mock_repo_cls, mock_invalidate):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
        mock_repo.get_operatore_detail.return_value = {"auth_user_id": 1}
        mock_repo.get_override_azioni.return_value = []
        from apps.amm_software.services.amm_software_service import AmmSoftwareService
        AmmSoftwareService().put_override_azioni(1, [])
        mock_invalidate.assert_called_once_with(1)

    @patch(INVALIDATE_USER)
    @patch(REPO, autospec=True)
    def test_put_emittenti_scope_invalidates_cache(self, mock_repo_cls, mock_invalidate):
        # Fase 2: signature cambiata da `(auth_user_id, list)` a
        # `(auth_user_id, payload)` con scope_mode + emittenti_ids.
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_categoria_accesso.return_value = "OPERATORE"
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
    @patch(REPO, autospec=True)
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

    @patch(REPO, autospec=True)
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


class TestGetAuditSummary(TestCase):
    """Validazioni get_audit_summary + traduzione errori (Fase 5)."""

    @patch(REPO, autospec=True)
    def test_get_audit_summary_param_invalido_code_assente(self, mock_repo_cls):
        del mock_repo_cls
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().get_audit_summary(None, 5)
        self.assertEqual(ctx.exception.code, "E_AUDIT_SUMMARY_PARAM_NON_VALIDO")

    @patch(REPO, autospec=True)
    def test_get_audit_summary_param_invalido_storico_id_zero(self, mock_repo_cls):
        del mock_repo_cls
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        with self.assertRaises(ServiceError) as ctx:
            AmmSoftwareService().get_audit_summary("user_override_aree", 0)
        self.assertEqual(ctx.exception.code, "E_AUDIT_SUMMARY_PARAM_NON_VALIDO")

    @patch(REPO, autospec=True)
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

    @patch(REPO, autospec=True)
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

    @patch(REPO, autospec=True)
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
