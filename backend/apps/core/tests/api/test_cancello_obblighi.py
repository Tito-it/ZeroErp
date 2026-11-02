# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cancello degli obblighi della credenziale (cambio password,
#        configurazione del secondo fattore) sul percorso VERO di una
#        richiesta col Bearer: client Django -> middleware -> DRF ->
#        JwtAuditAuthentication. Brief sicurezza §3.4-bis, lotto T-0 (A-8).
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_bearer_con_cambio_password_pendente_e_fermato — A-8: 403 E_CAMBIO_PASSWORD_RICHIESTO
 2) test_bearer_senza_obblighi_passa — 200
 3) test_bearer_con_secondo_fattore_da_configurare_e_fermato — 403 E_TOTP_CONFIGURAZIONE_RICHIESTA
 4) test_superuser_non_e_esentato — il vecchio middleware lo esentava
 5) test_db_che_non_risponde_non_apre — fail-closed: mai un 200
 6) test_obblighi_pendenti_nell_ordine — password prima del secondo fattore
 7) test_device_da_confermare_e_ancora_pendente — la configurazione a meta' non vale
 8) test_device_attivo_soddisfa_l_obbligo
 9) test_view_che_ammette_l_obbligo_passa
10) test_si_ferma_al_primo_pendente — pagina del secondo fattore chiusa finche' c'e' la password
11) test_view_senza_dichiarazione_non_ammette_niente
12) test_view_ammesse_dichiarate — logout e profilo tutti, cambio password il suo
13) test_obblighi_in_vigore_per_il_profilo — quelli che /core/me/ pubblica (T-4)
14) test_ogni_obbligo_in_vigore_ha_la_sua_strada — una view negli URL che lo ammette
"""

from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import Client, SimpleTestCase
from django.urls import URLPattern, URLResolver, get_resolver

from apps.core.api.cancello_obblighi import (
    OBBLIGO_CAMBIO_PASSWORD,
    OBBLIGO_SECONDO_FATTORE,
    OBBLIGHI_IN_VIGORE,
    TUTTI_GLI_OBBLIGHI,
    CambioPasswordRichiestoError,
    SecondoFattoreDaConfigurareError,
    obblighi_pendenti,
    verifica_obblighi,
)
from apps.core.tests._helpers.jwt_mock import JwtMockedApiTest

_PARENT_AUTH = "rest_framework_simplejwt.authentication.JWTAuthentication.authenticate"
_SET_GUCS = "apps.core.api.jwt_audit_authentication.JwtAuditAuthentication._set_gucs"
_FATTI = "apps.core.db.auth_repository.AuthRepository.get_fatti_obblighi"
# Una view qualunque, fuori dagli obblighi: il suo repository risponde vuoto,
# cosi' una richiesta che passa il cancello e' un 200 pulito.
_URL_QUALUNQUE = "/api/v1/core/lookup/tipi-ruolo/EF/utilities/"
_REPO_QUALUNQUE = "apps.core.api.views_lookup.LookupRepository"
# La permission viene DOPO il cancello e non e' materia di questi test.
_PERMISSION = "apps.core.api.permissions.ZeroERPPermission.has_permission"
# Il secondo fattore entra in vigore con T-3: i test del suo meccanismo lo
# accendono, cosi' il meccanismo resta provato fino ad allora.
_IN_VIGORE = "apps.core.api.cancello_obblighi.OBBLIGHI_IN_VIGORE"
_TUTTI_IN_VIGORE = patch(_IN_VIGORE, TUTTI_GLI_OBBLIGHI)


# Scopo: I fatti come li restituisce `AuthRepository.get_fatti_obblighi`.
def _fatti(
    *, password: bool = False, totp: bool = False, stato: str = "ASSENTE",
) -> dict[str, object]:
    return {
        "deve_cambiare_password": password,
        "totp_obbligatorio": totp,
        "totp_motivo": "CREDENZIALE" if totp else None,
        "totp_stato": stato,
    }


# Scopo: utente e token validato come li consegna SimpleJWT a una richiesta
#        col Bearer: il token porta i claim obbligatori (identita_id, sid),
#        cosi' l'autenticazione arriva fino in fondo.
def _utente_e_token(*, superuser: bool = False) -> tuple[MagicMock, MagicMock]:
    user = MagicMock()
    user.id = 42
    user.is_authenticated = True
    user.is_superuser = superuser
    user.__str__ = MagicMock(return_value="mctit")
    claims = {"identita_id": 7, "sid": "sid-di-prova"}
    token = MagicMock()
    token.get = MagicMock(side_effect=lambda k, d=None: claims.get(k, d))
    return user, token


class CancelloObblighiBearerTests(JwtMockedApiTest):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        gucs = patch(_SET_GUCS, return_value=True)
        gucs.start()
        self.addCleanup(gucs.stop)
        repo = patch(_REPO_QUALUNQUE)
        repo.start().return_value.list_utilities_per_ruolo.return_value = []
        self.addCleanup(repo.stop)
        permesso = patch(_PERMISSION, return_value=True)
        permesso.start()
        self.addCleanup(permesso.stop)

    # Scopo: Una GET col Bearer sulla view qualunque, con i fatti dati.
    def _get(self, fatti_o_errore, *, superuser: bool = False):
        mock_fatti = (
            patch(_FATTI, side_effect=fatti_o_errore)
            if isinstance(fatti_o_errore, Exception)
            else patch(_FATTI, return_value=fatti_o_errore)
        )
        with mock_fatti, patch(_PARENT_AUTH, return_value=_utente_e_token(superuser=superuser)):
            return self.client.get(_URL_QUALUNQUE, HTTP_AUTHORIZATION="Bearer finto")

    # Scopo: A-8. Una credenziale che deve cambiare la password, con un
    #        Bearer valido, NON raggiunge una view qualunque: 403 col codice
    #        dell'obbligo. Fino al 2026-09-30 il middleware guardava
    #        `request.user` in `process_view`, prima dell'autenticazione DRF:
    #        l'utente del Bearer era ancora anonimo e la richiesta passava
    #        (questo test, scritto prima della correzione, rispondeva 200).
    def test_bearer_con_cambio_password_pendente_e_fermato(self):
        resp = self._get(_fatti(password=True))
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_CAMBIO_PASSWORD_RICHIESTO")

    # Scopo: Senza obblighi il cancello non cambia niente.
    def test_bearer_senza_obblighi_passa(self):
        resp = self._get(_fatti())
        self.assertEqual(resp.status_code, 200, resp.content)

    # Scopo: Il secondo obbligo, con la stessa strada.
    @_TUTTI_IN_VIGORE
    def test_bearer_con_secondo_fattore_da_configurare_e_fermato(self):
        resp = self._get(_fatti(totp=True, stato="ASSENTE"))
        self.assertEqual(resp.status_code, 403, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_TOTP_CONFIGURAZIONE_RICHIESTA")

    # Scopo: Il superuser Django non e' esentato. Il vecchio middleware lo
    #        esentava: e' la persona per cui un secondo fattore conta di piu'.
    def test_superuser_non_e_esentato(self):
        resp = self._get(_fatti(password=True), superuser=True)
        self.assertEqual(resp.status_code, 403, resp.content)

    # Scopo: Fail-closed. Un DB che non risponde e' un errore della
    #        richiesta, mai un «nessun obbligo».
    def test_db_che_non_risponde_non_apre(self):
        resp = self._get(DatabaseError("giu'"))
        self.assertNotEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["error"]["code"], "E_DATABASE")

    # Scopo: T-4. Gli obblighi che `/core/me/` pubblica per il guard del
    #        frontend sono quelli che il cancello fa rispettare, nell'ordine;
    #        dal 2026-10-02 il secondo fattore e' fra questi.
    def test_obblighi_in_vigore_per_il_profilo(self):
        from apps.core.api.cancello_obblighi import obblighi_in_vigore

        with patch(_FATTI, return_value=_fatti(password=True, totp=True)):
            self.assertEqual(obblighi_in_vigore(42), (OBBLIGO_CAMBIO_PASSWORD, OBBLIGO_SECONDO_FATTORE))
        with patch(_FATTI, return_value=_fatti(totp=True, stato="ATTIVO")):
            self.assertEqual(obblighi_in_vigore(42), ())


class _View:
    """Una view con gli obblighi ammessi dati."""

    def __init__(self, ammessi: frozenset[str] | None = None) -> None:
        if ammessi is not None:
            self.obblighi_ammessi = ammessi


class RegolaObblighiTests(SimpleTestCase):
    # Scopo: L'ordine e' quello in cui si soddisfano.
    def test_obblighi_pendenti_nell_ordine(self):
        self.assertEqual(
            obblighi_pendenti(_fatti(password=True, totp=True)),
            (OBBLIGO_CAMBIO_PASSWORD, OBBLIGO_SECONDO_FATTORE),
        )
        self.assertEqual(obblighi_pendenti(_fatti()), ())

    # Scopo: Un device registrato ma non confermato e' una configurazione
    #        a meta': l'obbligo resta.
    def test_device_da_confermare_e_ancora_pendente(self):
        self.assertEqual(
            obblighi_pendenti(_fatti(totp=True, stato="DA_CONFERMARE")),
            (OBBLIGO_SECONDO_FATTORE,),
        )

    def test_device_attivo_soddisfa_l_obbligo(self):
        self.assertEqual(obblighi_pendenti(_fatti(totp=True, stato="ATTIVO")), ())

    @_TUTTI_IN_VIGORE
    @patch(_FATTI, return_value=_fatti(totp=True))
    def test_view_che_ammette_l_obbligo_passa(self, _f):
        verifica_obblighi(_View(frozenset({OBBLIGO_SECONDO_FATTORE})), 42)

    # Scopo: Con la password da cambiare, la pagina del secondo fattore
    #        resta chiusa: si risponde col PRIMO obbligo pendente.
    @_TUTTI_IN_VIGORE
    @patch(_FATTI, return_value=_fatti(password=True, totp=True))
    def test_si_ferma_al_primo_pendente(self, _f):
        with self.assertRaises(CambioPasswordRichiestoError):
            verifica_obblighi(_View(frozenset({OBBLIGO_SECONDO_FATTORE})), 42)
        verifica_obblighi(_View(frozenset({OBBLIGO_CAMBIO_PASSWORD})), 42)

    @_TUTTI_IN_VIGORE
    @patch(_FATTI, return_value=_fatti(totp=True))
    def test_view_senza_dichiarazione_non_ammette_niente(self, _f):
        with self.assertRaises(SecondoFattoreDaConfigurareError):
            verifica_obblighi(_View(), 42)
        with self.assertRaises(SecondoFattoreDaConfigurareError):
            verifica_obblighi(None, 42)

    # Scopo: Le strade che devono restare aperte con un obbligo pendente.
    def test_view_ammesse_dichiarate(self):
        from apps.core.api.change_password_view import ChangePasswordView
        from apps.core.api.logout_view import LogoutView
        from apps.core.api.me_view import UserProfileView

        self.assertEqual(LogoutView.obblighi_ammessi, TUTTI_GLI_OBBLIGHI)
        self.assertEqual(UserProfileView.obblighi_ammessi, TUTTI_GLI_OBBLIGHI)
        self.assertEqual(ChangePasswordView.obblighi_ammessi, frozenset({OBBLIGO_CAMBIO_PASSWORD}))

    # Scopo: La regola di `OBBLIGHI_IN_VIGORE`: ogni obbligo che il cancello
    #        fa rispettare ha, negli URL VERI, una view che lo ammette e non
    #        e' una delle universali (logout, profilo) — la strada che lo
    #        chiude. Quando T-3 accende il secondo fattore senza i suoi
    #        endpoint, questo test lo dice prima di un'utenza murata.
    def test_ogni_obbligo_in_vigore_ha_la_sua_strada(self):
        strade: set[str] = set()

        def visita(patterns) -> None:
            for p in patterns:
                if isinstance(p, URLResolver):
                    visita(p.url_patterns)
                elif isinstance(p, URLPattern):
                    ammessi = getattr(getattr(p.callback, "cls", None), "obblighi_ammessi", None)
                    if ammessi and ammessi != TUTTI_GLI_OBBLIGHI:
                        strade.update(ammessi)

        visita(get_resolver().url_patterns)
        self.assertLessEqual(OBBLIGHI_IN_VIGORE, strade)
