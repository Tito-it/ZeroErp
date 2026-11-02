# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari per MultiVesteTokenSerializer e VesteNonAttivaError.
# Copertura: contract della class-exception (status 403, code
# E_VESTE_NON_ATTIVA) e default serializer (allowed_ruoli_applicativi
# vuoto = nessuna veste ammessa per la superclasse astratta).
# Il flusso validate() completo richiede un user Django reale + SimpleJWT
# internals — viene coperto dallo smoke test bash di §8.3.3.
# ------------------------------------------------------------

"""
Indice test eseguiti:
 1) test_exception_status_code_403 — VesteNonAttivaError mappato a HTTP 403
 2) test_exception_default_code — codice errore = E_VESTE_NON_ATTIVA
 3) test_exception_default_detail — messaggio business-safe no-enumeration
 4) test_serializer_default_allowed_vuoto — la superclasse non ammette alcun ruolo
 5) test_error_policy_registrata — E_VESTE_NON_ATTIVA in error_policies (403/banner)
 6) test_validate_happy_path_injects_claims — claim custom iniettati nel refresh
 7) test_validate_veste_non_attiva — repo None -> VesteNonAttivaError
 8) test_admin_serializer_allowed_ruoli — solo OPERATORE
 9) test_portale_serializer_allowed_ruoli — solo clienti/fornitori portale
10) test_shop_serializer_allowed_ruoli — solo SHOP_CUSTOMER
11) test_password_non_ripulita_su_ogni_porta — la password arriva ad authenticate com'e' digitata (S-5)
12) ChiaveIngressoPerPortaTests — nome utente per admin, email per portale e shop (L-4, D-9):
    campo, normalizzazione, ricerca della credenziale, chiave passata ad `authenticate`
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from rest_framework import status
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.core.api.multi_veste_token_serializer import (
    AdminTokenSerializer,
    E_VESTE_NON_ATTIVA,
    MultiVesteTokenSerializer,
    PortaleTokenSerializer,
    ShopTokenSerializer,
    VesteNonAttivaError,
)
from apps.core.api.token_serializers import SidTokenObtainPairSerializer
from apps.core.services.auth_constants import (
    JWT_CLAIM_IDENTITA_ID,
    JWT_CLAIM_RUOLO_APPLICATIVO,
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_FORNITORE_PORTALE,
    RUOLO_APPLICATIVO_OPERATORE,
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
)


class _AdminSerializerUnderTest(MultiVesteTokenSerializer):
    """Sottoclasse di test che simula la view admin (§8.3.3)."""

    allowed_ruoli_applicativi = (RUOLO_APPLICATIVO_OPERATORE,)


class VesteNonAttivaErrorTests(TestCase):
    """Contract della class-exception usata dal serializer multi-veste."""

    def test_exception_status_code_403(self):
        """VesteNonAttivaError deve essere 403 (non 401): distingue da
        credenziali errate e non deve triggerare il blocco tentativi."""
        self.assertEqual(VesteNonAttivaError.status_code, status.HTTP_403_FORBIDDEN)

    def test_exception_default_code(self):
        self.assertEqual(VesteNonAttivaError.default_code, E_VESTE_NON_ATTIVA)
        self.assertEqual(E_VESTE_NON_ATTIVA, "E_VESTE_NON_ATTIVA")

    def test_exception_default_detail(self):
        """Messaggio generico richiesto dal piano (§8.5.7 no enumeration)."""
        self.assertIn("canale", str(VesteNonAttivaError.default_detail).lower())


class MultiVesteTokenSerializerTests(TestCase):
    """Contract di configurazione del serializer base."""

    def test_serializer_default_allowed_vuoto(self):
        """La superclasse non ammette nessun ruolo: le sottoclassi
        (§8.3.3) sono obbligate a settare allowed_ruoli_applicativi."""
        self.assertEqual(tuple(MultiVesteTokenSerializer.allowed_ruoli_applicativi), ())


class ErrorPolicyRegistrationTests(TestCase):
    """E_VESTE_NON_ATTIVA deve essere registrato in error_policies:
    senza policy il codice non ha HTTP status / ui_action / user_message
    coerenti e cade nel fallback generico."""

    def test_error_policy_registrata(self):
        from apps.core.services.error_policies import ErrorPolicyRegistry

        policy = ErrorPolicyRegistry.resolve(E_VESTE_NON_ATTIVA)
        self.assertIsNotNone(policy)
        self.assertEqual(policy.http_status, 403)
        self.assertEqual(policy.ui_action, "show_error_banner")
        self.assertTrue(policy.user_message)


class MultiVesteTokenSerializerValidateTests(TestCase):
    """Test sul flusso validate() con super().validate e get_token mockati.

    L'end-to-end con user Django reale + SimpleJWT completo e' coperto
    dallo smoke test bash di §8.3.3; qui verifichiamo il contratto del
    serializer: risoluzione identita, injection claim, errore veste.
    """

    def setUp(self):
        self.mock_user = MagicMock(id=42)

    def _fake_super_validate(self, ser_self, attrs):
        """Side_effect per super().validate: popola self.user come farebbe
        l'autenticazione SimpleJWT, e ritorna il dict base con i token
        "vecchi" che il nostro validate poi sovrascrive."""
        ser_self.user = self.mock_user
        return {"refresh": "r_old", "access": "a_old"}

    @patch.object(
        TokenObtainPairSerializer,
        "validate",
        autospec=True,
    )
    # Mock su SidTokenObtainPairSerializer (parent diretto di MultiVeste):
    # cosi' evitiamo che Sid.get_token esegua OutstandingToken.update (query
    # DB reale non disponibile nei test unit).
    @patch.object(
        SidTokenObtainPairSerializer,
        "get_token",
    )
    @patch.object(MultiVesteTokenSerializer, "_auth_repo")
    def test_validate_happy_path_injects_claims(
        self, mock_repo, mock_get_token, mock_super_validate
    ):
        """Happy path: l'identita esiste -> il refresh riceve i 2 claim
        custom e data viene rigenerato con i nuovi token."""
        mock_super_validate.side_effect = self._fake_super_validate
        mock_repo.find_veste_utilizzabile_per_ruoli.return_value = {
            "id": 99,
            "soggetto_ruolo_id": 7,
            "ruolo_applicativo": RUOLO_APPLICATIVO_OPERATORE,
        }
        fake_refresh = MagicMock()
        mock_get_token.return_value = fake_refresh

        ser = _AdminSerializerUnderTest()
        data = ser.validate({"username": "tid", "password": "x"})

        # Claim custom iniettati usando le costanti condivise
        fake_refresh.__setitem__.assert_any_call(JWT_CLAIM_IDENTITA_ID, 99)
        fake_refresh.__setitem__.assert_any_call(
            JWT_CLAIM_RUOLO_APPLICATIVO, RUOLO_APPLICATIVO_OPERATORE
        )
        # Repo chiamato con i ruoli del namespace
        mock_repo.find_veste_utilizzabile_per_ruoli.assert_called_once_with(
            auth_user_id=42,
            ruoli_applicativi=(RUOLO_APPLICATIVO_OPERATORE,),
        )
        # Tokens sovrascritti (valore stringa: str(MagicMock) != "r_old"/"a_old")
        self.assertNotEqual(data["refresh"], "r_old")
        self.assertNotEqual(data["access"], "a_old")

    @patch.object(
        TokenObtainPairSerializer,
        "validate",
        autospec=True,
    )
    @patch.object(MultiVesteTokenSerializer, "_auth_repo")
    def test_validate_veste_non_attiva(self, mock_repo, mock_super_validate):
        """Identita assente per il namespace -> VesteNonAttivaError (403)."""
        mock_super_validate.side_effect = self._fake_super_validate
        mock_repo.find_veste_utilizzabile_per_ruoli.return_value = None

        ser = _AdminSerializerUnderTest()
        with self.assertRaises(VesteNonAttivaError) as ctx:
            ser.validate({"username": "tid", "password": "x"})
        self.assertEqual(ctx.exception.status_code, 403)


class NamespaceSerializerConcreteTests(TestCase):
    """Verifica che le 3 sottoclassi concrete espongano esattamente il
    set atteso di ruoli applicativi. Invariante: nessuna sottoclasse
    deve mai includere ruoli non propri del suo namespace (rischio
    escalation inter-veste)."""

    def test_admin_serializer_allowed_ruoli(self):
        self.assertEqual(
            tuple(AdminTokenSerializer.allowed_ruoli_applicativi),
            (RUOLO_APPLICATIVO_OPERATORE,),
        )

    def test_portale_serializer_allowed_ruoli(self):
        ruoli = set(PortaleTokenSerializer.allowed_ruoli_applicativi)
        self.assertEqual(
            ruoli,
            {RUOLO_APPLICATIVO_CLIENTE_PORTALE, RUOLO_APPLICATIVO_FORNITORE_PORTALE},
        )
        # Guard anti-escalation: portale NON puo' loggare operatori ne' shop.
        self.assertNotIn(RUOLO_APPLICATIVO_OPERATORE, ruoli)
        self.assertNotIn(RUOLO_APPLICATIVO_SHOP_CUSTOMER, ruoli)

    def test_shop_serializer_allowed_ruoli(self):
        self.assertEqual(
            tuple(ShopTokenSerializer.allowed_ruoli_applicativi),
            (RUOLO_APPLICATIVO_SHOP_CUSTOMER,),
        )


class PasswordComeDigitataTests(TestCase):
    """S-5: la password non si ripulisce dagli spazi, su nessuna porta."""

    # Scopo: Il campo di SimpleJWT e' un `CharField` e toglieva gli spazi ai
    # bordi: una password salvata con lo spazio non sarebbe piu' entrata.
    # Lo username resta ripulito (lo legge `_nome_tentato`, brief §13.3).
    def test_password_non_ripulita_su_ogni_porta(self):
        for cls in (AdminTokenSerializer, PortaleTokenSerializer, ShopTokenSerializer):
            with self.subTest(serializer=cls.__name__):
                ser = cls()
                self.assertEqual(ser.fields["password"].run_validation(" segreta "), " segreta ")
                self.assertEqual(ser.fields[ser.username_field].run_validation(" tid "), "tid")


class ChiaveIngressoPerPortaTests(TestCase):
    """L-4, D-9: la chiave d'ingresso e' della porta — il nome utente per
    admin, l'email per portale e shop. Il campo normalizza, e la ricerca della
    credenziale segue lo stesso valore (lookup, `authenticate` e impronta del
    freno leggono il campo)."""

    def test_admin_entra_col_nome_utente_esatto(self):
        ser = AdminTokenSerializer()
        self.assertEqual(ser.username_field, "username")
        # Il nome utente non si abbassa: `get_by_natural_key` e' esatto.
        self.assertEqual(ser.fields["username"].run_validation(" Tid "), "Tid")
        self.assertNotIn("email", ser.fields)

    def test_portale_e_shop_entrano_con_l_email_normalizzata(self):
        for cls in (PortaleTokenSerializer, ShopTokenSerializer):
            with self.subTest(serializer=cls.__name__):
                ser = cls()
                self.assertEqual(ser.username_field, "email")
                self.assertNotIn("username", ser.fields)
                self.assertEqual(ser.fields["email"].run_validation("  Ada@Example.IT "), "ada@example.it")

    @patch("apps.core.api.multi_veste_token_serializer.credenziale_per_nome_utente")
    def test_admin_trova_la_credenziale_per_nome_utente(self, mock_per_nome):
        AdminTokenSerializer.trova_credenziale("tid")
        mock_per_nome.assert_called_once_with("tid")

    @patch("apps.core.api.multi_veste_token_serializer.credenziale_per_email")
    def test_portale_e_shop_trovano_la_credenziale_per_email(self, mock_per_email):
        for cls in (PortaleTokenSerializer, ShopTokenSerializer):
            mock_per_email.reset_mock()
            cls.trova_credenziale("ada@example.it")
            mock_per_email.assert_called_once_with("ada@example.it")

    def test_authenticate_riceve_la_chiave_della_porta(self):
        """Il validate di SimpleJWT passa ad `authenticate` il campo della porta:
        `email=` arriva a `CredenzialePerEmailBackend`."""
        user = MagicMock(id=5, is_active=True)
        with patch("rest_framework_simplejwt.serializers.authenticate", return_value=user) as mock_auth, \
                patch.object(PortaleTokenSerializer, "_auth_repo") as repo, \
                patch.object(PortaleTokenSerializer, "get_token", return_value=MagicMock()), \
                patch("apps.core.api.multi_veste_token_serializer.emetti_refresh_veste") as emetti:
            repo.find_veste_utilizzabile_per_ruoli.return_value = {"id": 1, "ruolo_applicativo": RUOLO_APPLICATIVO_CLIENTE_PORTALE}
            emetti.return_value = MagicMock(access_token="a")
            ser = PortaleTokenSerializer(data={"email": " Ada@X.it ", "password": "p"})
            self.assertTrue(ser.is_valid(), ser.errors)
        self.assertEqual(mock_auth.call_args.kwargs["email"], "ada@x.it")
        self.assertNotIn("username", mock_auth.call_args.kwargs)
