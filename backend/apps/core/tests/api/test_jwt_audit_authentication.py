# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari JwtAuditAuthentication — propagazione GUC
#        sulla connessione PG dopo authenticate() del parent JWT.
#        Post §8.3.4: l'autenticazione valida il claim `identita_id`
#        e popola 3 GUC di identita in singola query CTE.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_authenticate_returns_none_passthrough — auth fallita → None, niente GUC
 2) test_authenticate_success_sets_gucs — auth ok → 1 execute + flag su request
 3) test_set_gucs_uses_session_scope_not_local — set_config con is_local=false
 4) test_set_gucs_passes_identita_user_and_username — params nel giusto ordine
 5) test_set_gucs_database_error_swallowed — DB down → no raise, no flag
 6) test_user_without_id_skipped — difensivo: nessun .id → no GUC
 7) test_jwt_senza_identita_claim_raise_401 — token senza claim → E_JWT_SENZA_IDENTITA
 8) test_identita_non_attiva_raise_401 — CTE count 0 → E_IDENTITA_NON_ATTIVA
 9) test_claim_emittente_attivo_propagato — claim → GUC + rivalidazione «attivo»
10) test_token_senza_claim_emittente_non_solleva — token pre-cantiere restano validi
11) test_jwt_senza_sid_claim_raise_401 — token senza `sid` → E_JWT_SENZA_SID
12) test_jwt_sid_vuoto_raise_401 — `sid` stringa vuota = assente
13) test_contesto_cache_permessi_da_emittente_effettivo — M-1: chiave L2 dalla GUC
14) test_cancello_obblighi_riceve_view_e_utente — T-0: la view dal parser_context
15) test_cancello_obblighi_non_parte_su_identita_spenta — prima il 401, poi l'obbligo
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.db import DatabaseError

from apps.core.api.jwt_audit_authentication import (
    IdentitaNonAttivaError,
    JwtAuditAuthentication,
    JwtSenzaIdentitaError,
    JwtSenzaSidError,
)

_PARENT_AUTH = (
    "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
)
_CONN = "apps.core.api.jwt_audit_authentication.connection"


def _mock_user(user_id: int = 42, username: str = "mctit") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.__str__ = MagicMock(return_value=username)
    return user


def _mock_token_with_identita(
    identita_id: int | None = 7,
    emittente_attivo_id: int | None = None,
    sid: str | None = "sid-di-prova",
) -> MagicMock:
    """Token validato SimpleJWT: espone `.get(claim)`. Se identita_id
    e' None simula un token pre-§8.3.2 (senza claim).
    `emittente_attivo_id` None = modalita' «Tutti gli emittenti» (claim
    assente), che e' anche la forma dei token emessi prima
    dell'impersonazione di scope.
    ⭐ `sid` valorizzato di default dal 2026-09-04: e' il terzo claim
    obbligatorio del JWT interno e l'autenticazione lo verifica. Passare
    `sid=None` simula il token che lo perde (es. `RefreshToken.for_user`
    usato fuori dal serializer di login)."""
    token = MagicMock()
    def _get(key, default=None):
        if key == "identita_id":
            return identita_id
        if key == "emittente_attivo_id":
            return emittente_attivo_id
        if key == "sid":
            return sid
        return default
    token.get = MagicMock(side_effect=_get)
    return token


def _mock_request() -> MagicMock:
    return MagicMock(spec=[])


def _mock_cursor_row(
    mock_conn, *, identita_count: int = 1, emittente_guc: str = ""
) -> MagicMock:
    """Configura connection.cursor() come context manager e
    fa ritornare 7 colonne da fetchone(), layout della query CTE di
    `set_jwt_gucs`:
      idx 0..5 → risultati set_config (stringhe settate: jwt_user,
                  current_user_id, current_identita_id, ruolo_applicativo,
                  soggetto_ruolo_id, current_emittente_id). Il codice legge
                  la 5 (l'emittente EFFETTIVO, per il contesto della cache
                  permessi); le altre valgono '' perche' nessuno le legge.
      idx 6   → COUNT(*) da id_row, usato dal codice per decidere
                  `identita_trovata`.
    Se modifichi la query CTE (aggiungi/rimuovi GUC), aggiorna qui di
    conseguenza oppure il test diventa silenziosamente permissivo.
    ⚠️ Fino al 2026-09-24 le colonne simulate erano 6: il conteggio cadeva
    sulla colonna dell'emittente, e non se ne accorgeva nessuno perche'
    nessuno la leggeva."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (
        "", "", "", "", "", emittente_guc, identita_count,
    )
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_cursor


class JwtAuditAuthenticationTests(TestCase):
    """Test per JwtAuditAuthentication."""

    def setUp(self) -> None:
        self.auth = JwtAuditAuthentication()
        # Il cancello degli obblighi legge il DB: qui si prova l'autenticazione,
        # il cancello ha i suoi test (test_cancello_obblighi). ⛔ Senza questo
        # mock un `unittest.TestCase` parlerebbe col DB di sviluppo.
        cancello = patch.object(JwtAuditAuthentication, "_verifica_obblighi", return_value=None)
        self.mock_cancello = cancello.start()
        self.addCleanup(cancello.stop)

    # Scopo: Auth fallita (super ritorna None) → ritorna None senza
    # toccare le GUC.
    @patch(_CONN)
    @patch(_PARENT_AUTH, return_value=None)
    def test_authenticate_returns_none_passthrough(self, _parent, mock_conn):
        request = _mock_request()
        result = self.auth.authenticate(request)
        self.assertIsNone(result)
        mock_conn.cursor.assert_not_called()
        self.assertFalse(getattr(request, "_zeroerp_jwt_guc_set", False))

    # Scopo: Auth ok + claim identita_id presente + CTE trova identita
    # attiva → 1 execute + flag su request.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_authenticate_success_sets_gucs(self, mock_parent, mock_conn):
        user = _mock_user(user_id=42, username="mctit")
        token = _mock_token_with_identita(identita_id=7)
        mock_parent.return_value = (user, token)
        mock_cursor = _mock_cursor_row(mock_conn, identita_count=1)

        request = _mock_request()
        result = self.auth.authenticate(request)

        self.assertEqual(result, (user, token))
        self.assertEqual(mock_cursor.execute.call_count, 1)
        self.assertTrue(request._zeroerp_jwt_guc_set)

    # Scopo: La query usa set_config con is_local=false (session-scoped).
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_set_gucs_uses_session_scope_not_local(self, mock_parent, mock_conn):
        mock_parent.return_value = (_mock_user(), _mock_token_with_identita())
        mock_cursor = _mock_cursor_row(mock_conn)

        self.auth.authenticate(_mock_request())

        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("set_config", sql)
        self.assertIn("app.jwt_user", sql)
        self.assertIn("app.current_user_id", sql)
        self.assertIn("app.current_identita_id", sql)
        self.assertIn("false", sql)
        self.assertNotIn("SET LOCAL", sql)

    # Scopo: Params nell'ordine del set_jwt_gucs con identita_id + emittente
    # attivo: [identita_id, user_id (CTE), emittente x2 (CTE ef_row),
    # username, user_id (GUC)]. Senza claim emittente i due slot sono None
    # → la CTE non seleziona nulla e la GUC resta vuota.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_set_gucs_passes_identita_user_and_username(self, mock_parent, mock_conn):
        mock_parent.return_value = (
            _mock_user(user_id=99, username="alice"),
            _mock_token_with_identita(identita_id=501),
        )
        mock_cursor = _mock_cursor_row(mock_conn)

        self.auth.authenticate(_mock_request())

        params = mock_cursor.execute.call_args[0][1]
        self.assertEqual(params, ["501", "99", None, None, "alice", "99"])

    # 9) Claim emittente attivo presente → arriva alla CTE come intero, due
    #    volte (guard NOT NULL + confronto sulla PK).
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_claim_emittente_attivo_propagato(self, mock_parent, mock_conn):
        mock_parent.return_value = (
            _mock_user(user_id=99, username="alice"),
            _mock_token_with_identita(identita_id=501, emittente_attivo_id=32),
        )
        mock_cursor = _mock_cursor_row(mock_conn)

        self.auth.authenticate(_mock_request())

        params = mock_cursor.execute.call_args[0][1]
        self.assertEqual(params, ["501", "99", 32, 32, "alice", "99"])
        sql = mock_cursor.execute.call_args[0][0]
        self.assertIn("app.current_emittente_id", sql)
        # La rivalidazione «emittente ancora attivo» vive nella CTE, non nel
        # Python: e' cio' che chiude il caso del token con emittente spento.
        self.assertIn("ef.attivo = true", sql)

    # 13) M-1 — il contesto della cache permessi e' (identita', emittente
    #     EFFETTIVO): conta cio' che la GUC porta, non il claim. Un claim su un
    #     emittente disattivato lascia la GUC vuota, e i permessi calcolati li'
    #     sono quelli di «tutti»: devono stare in una voce diversa.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_contesto_cache_permessi_da_emittente_effettivo(self, mock_parent, mock_conn):
        mock_parent.return_value = (
            _mock_user(), _mock_token_with_identita(identita_id=7, emittente_attivo_id=32),
        )
        _mock_cursor_row(mock_conn, emittente_guc="32")
        attivo = _mock_request()
        self.auth.authenticate(attivo)
        self.assertEqual(attivo._zeroerp_perms_contesto, "i7:e32")

        _mock_cursor_row(mock_conn, emittente_guc="")
        spento = _mock_request()
        self.auth.authenticate(spento)
        self.assertEqual(spento._zeroerp_perms_contesto, "i7:e-")

    # 10) Token PRE-impersonazione (nessun claim emittente): nessun errore,
    #     modalita' globale. I token gia' emessi restano validi a scadenza.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_token_senza_claim_emittente_non_solleva(self, mock_parent, mock_conn):
        mock_parent.return_value = (
            _mock_user(), _mock_token_with_identita(identita_id=7),
        )
        _mock_cursor_row(mock_conn)
        self.assertIsNotNone(self.auth.authenticate(_mock_request()))

    # Scopo: DatabaseError dal cursor.execute non deve propagare —
    # cleanup best-effort + log warning. Ma set_jwt_gucs ritorna False
    # → authenticate solleva IdentitaNonAttivaError.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_set_gucs_database_error_swallowed(self, mock_parent, mock_conn):
        user = _mock_user()
        token = _mock_token_with_identita()
        mock_parent.return_value = (user, token)
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = DatabaseError("DB down")
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        request = _mock_request()
        # DB down → CTE fallisce → identita non trovata → 401.
        with self.assertRaises(IdentitaNonAttivaError):
            self.auth.authenticate(request)
        self.assertFalse(getattr(request, "_zeroerp_jwt_guc_set", False))

    # Scopo: User senza .id (caso difensivo) → no GUC, no flag,
    # ritorna comunque il risultato del parent.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_user_without_id_skipped(self, mock_parent, mock_conn):
        user = MagicMock(spec=["__str__"])
        # MagicMock(spec=[...]) non ha .id
        mock_parent.return_value = (user, _mock_token_with_identita())

        request = _mock_request()
        result = self.auth.authenticate(request)

        self.assertEqual(result, mock_parent.return_value)
        mock_conn.cursor.assert_not_called()
        self.assertFalse(getattr(request, "_zeroerp_jwt_guc_set", False))

    # Scopo: Token senza claim identita_id (vecchio stile pre-§8.3.2)
    # → JwtSenzaIdentitaError (401 E_JWT_SENZA_IDENTITA).
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_jwt_senza_identita_claim_raise_401(self, mock_parent, mock_conn):
        mock_parent.return_value = (
            _mock_user(),
            _mock_token_with_identita(identita_id=None),
        )
        with self.assertRaises(JwtSenzaIdentitaError) as ctx:
            self.auth.authenticate(_mock_request())
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.default_code, "E_JWT_SENZA_IDENTITA")
        # La CTE non deve essere stata eseguita (fail prima).
        mock_conn.cursor.assert_not_called()

    # Scopo: Token con `identita_id` ma SENZA `sid` → JwtSenzaSidError (401).
    # ⭐ E' il caso reale di `RefreshToken.for_user`, che non passa dal
    #    serializer di login e non mette il claim: prima del 2026-09-04 quel
    #    token arrivava alle view delle sessioni, dove il sid vuoto scavalcava
    #    sia il «non puoi revocare la sessione corrente» sia l'esclusione della
    #    propria sessione dalla revoca di massa.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_jwt_senza_sid_claim_raise_401(self, mock_parent, mock_conn):
        mock_parent.return_value = (
            _mock_user(),
            _mock_token_with_identita(sid=None),
        )
        with self.assertRaises(JwtSenzaSidError) as ctx:
            self.auth.authenticate(_mock_request())
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.default_code, "E_JWT_SENZA_SID")
        # Fail PRIMA della CTE: un token incompleto non popola nessuna GUC.
        mock_conn.cursor.assert_not_called()

    # Scopo: `sid` stringa vuota vale come ASSENTE.
    # ⚠️ Non e' pedanteria: le view leggono `str(auth.get("sid", ""))`, quindi
    #    un claim vuoto e uno mancante producono a valle lo stesso identico
    #    danno — e un guard che accettasse `""` lascerebbe passare proprio la
    #    forma che il codice a valle non distingue.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_jwt_sid_vuoto_raise_401(self, mock_parent, mock_conn):
        mock_parent.return_value = (
            _mock_user(),
            _mock_token_with_identita(sid=""),
        )
        with self.assertRaises(JwtSenzaSidError):
            self.auth.authenticate(_mock_request())
        mock_conn.cursor.assert_not_called()

    # Scopo: Claim presente ma la coppia (user, identita) non e' attiva
    # (CTE count = 0) → IdentitaNonAttivaError (401).
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_identita_non_attiva_raise_401(self, mock_parent, mock_conn):
        mock_parent.return_value = (
            _mock_user(),
            _mock_token_with_identita(identita_id=999),
        )
        _mock_cursor_row(mock_conn, identita_count=0)

        with self.assertRaises(IdentitaNonAttivaError) as ctx:
            self.auth.authenticate(_mock_request())
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.default_code, "E_IDENTITA_NON_ATTIVA")

    # Scopo: T-0 (brief sicurezza §3.4-bis). Il cancello degli obblighi riceve
    # la view che DRF mette nel `parser_context` e l'utente del token: e' cosi'
    # che una view dichiara quali obblighi ammette.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_cancello_obblighi_riceve_view_e_utente(self, mock_parent, mock_conn):
        mock_parent.return_value = (_mock_user(user_id=42), _mock_token_with_identita())
        _mock_cursor_row(mock_conn, identita_count=1)
        view = object()
        request = MagicMock(spec=["parser_context"])
        request.parser_context = {"view": view}

        self.auth.authenticate(request)

        self.mock_cancello.assert_called_once_with(view, 42)

    # Scopo: Un token di una veste spenta e' un 401 prima di essere un
    # obbligo: il cancello non parte, e il client riparte dal login.
    @patch(_CONN)
    @patch(_PARENT_AUTH)
    def test_cancello_obblighi_non_parte_su_identita_spenta(self, mock_parent, mock_conn):
        mock_parent.return_value = (_mock_user(), _mock_token_with_identita())
        _mock_cursor_row(mock_conn, identita_count=0)

        with self.assertRaises(IdentitaNonAttivaError):
            self.auth.authenticate(_mock_request())
        self.mock_cancello.assert_not_called()
