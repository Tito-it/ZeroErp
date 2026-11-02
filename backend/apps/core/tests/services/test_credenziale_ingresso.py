# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del BB della chiave d'ingresso (L-4, D-9): ricerca per
#        nome utente; per email normalizzazione, ricerca della credenziale,
#        backend di autenticazione.
#        Mock del repository: il binding con `fn_get_auth_user_id_for_email`
#        lo prova il login vero in `test_login_credenziale_db`.
# ------------------------------------------------------------

"""
Indice test eseguiti:
0) CredenzialePerNomeUtenteTests.test_vuoto_non_interroga_il_db
0b) CredenzialePerNomeUtenteTests.test_uguaglianza_esatta_come_model_backend
1) NormalizzaEmailTests.test_spazi_e_maiuscole
2) CredenzialePerEmailTests.test_vuota_non_interroga_il_db (anche di soli spazi)
3) CredenzialePerEmailTests.test_sconosciuta_none
4) CredenzialePerEmailTests.test_trovata_cerca_per_id_con_l_email_normalizzata
5) BackendTests.test_password_giusta_entra
6) BackendTests.test_password_sbagliata_o_credenziale_spenta_no
7) BackendTests.test_email_sconosciuta_calcola_comunque_un_hash
8) BackendTests.test_login_per_nome_utente_non_attraversa_il_backend
9) BackendTests.test_backend_registrato_dopo_quello_del_nome_utente
"""

import inspect
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.conf import settings

from apps.core.services.credenziale_ingresso import (
    CredenzialePerEmailBackend,
    credenziale_per_email,
    credenziale_per_nome_utente,
    normalizza_email,
)

_REPO = "apps.core.services.credenziale_ingresso._auth_repo"
_USER = "apps.core.services.credenziale_ingresso.User"
_PER_EMAIL = "apps.core.services.credenziale_ingresso.credenziale_per_email"


class CredenzialePerNomeUtenteTests(TestCase):
    @patch(_USER)
    def test_vuoto_non_interroga_il_db(self, MockUser):
        self.assertIsNone(credenziale_per_nome_utente(""))
        MockUser.objects.filter.assert_not_called()

    # Scopo: Il nome non si abbassa ne' si ripulisce: `get_by_natural_key` e'
    # esatto, e una ricerca diversa troverebbe un'altra credenziale.
    @patch(_USER)
    def test_uguaglianza_esatta_come_model_backend(self, MockUser):
        utente = MagicMock()
        MockUser.objects.filter.return_value.first.return_value = utente
        self.assertIs(credenziale_per_nome_utente("Tid"), utente)
        MockUser.objects.filter.assert_called_once_with(username="Tid")


class NormalizzaEmailTests(TestCase):
    def test_spazi_e_maiuscole(self):
        self.assertEqual(normalizza_email("  Ada@Example.IT\t"), "ada@example.it")


class CredenzialePerEmailTests(TestCase):
    @patch(_REPO)
    def test_vuota_non_interroga_il_db(self, repo):
        for vuota in ("", "   \t"):
            self.assertIsNone(credenziale_per_email(vuota))
        repo.find_auth_user_id_per_email.assert_not_called()

    @patch(_USER)
    @patch(_REPO)
    def test_sconosciuta_none(self, repo, MockUser):
        repo.find_auth_user_id_per_email.return_value = None
        self.assertIsNone(credenziale_per_email("nessuno@x.it"))
        MockUser.objects.filter.assert_not_called()

    @patch(_USER)
    @patch(_REPO)
    def test_trovata_cerca_per_id_con_l_email_normalizzata(self, repo, MockUser):
        repo.find_auth_user_id_per_email.return_value = 42
        utente = MagicMock()
        MockUser.objects.filter.return_value.first.return_value = utente
        self.assertIs(credenziale_per_email(" Ada@X.it "), utente)
        repo.find_auth_user_id_per_email.assert_called_once_with("ada@x.it")
        MockUser.objects.filter.assert_called_once_with(pk=42)


class BackendTests(TestCase):
    def setUp(self) -> None:
        self.backend = CredenzialePerEmailBackend()

    @patch(_PER_EMAIL)
    def test_password_giusta_entra(self, mock_per_email):
        utente = MagicMock(is_active=True)
        utente.check_password.return_value = True
        mock_per_email.return_value = utente
        self.assertIs(self.backend.authenticate(None, email="ada@x.it", password="p"), utente)

    @patch(_PER_EMAIL)
    def test_password_sbagliata_o_credenziale_spenta_no(self, mock_per_email):
        for password_giusta, attiva in ((False, True), (True, False)):
            with self.subTest(password_giusta=password_giusta, attiva=attiva):
                utente = MagicMock(is_active=attiva)
                utente.check_password.return_value = password_giusta
                mock_per_email.return_value = utente
                self.assertIsNone(self.backend.authenticate(None, email="ada@x.it", password="p"))

    # Scopo: Come `ModelBackend` per un nome sconosciuto: un hash si calcola
    # lo stesso, perche' il tempo di risposta non dica se l'email esiste.
    @patch(_USER)
    @patch(_PER_EMAIL, return_value=None)
    def test_email_sconosciuta_calcola_comunque_un_hash(self, _per_email, MockUser):
        self.assertIsNone(self.backend.authenticate(None, email="nessuno@x.it", password="p"))
        MockUser.return_value.set_password.assert_called_once_with("p")

    # Scopo: Django prova solo i backend la cui firma accetta le credenziali
    # passate (`inspect.signature(...).bind`). Con `username=` questo non deve
    # legarsi, o la porta admin entrerebbe anche per email.
    def test_login_per_nome_utente_non_attraversa_il_backend(self):
        firma = inspect.signature(self.backend.authenticate)
        with self.assertRaises(TypeError):
            firma.bind(None, username="tid", password="p")
        firma.bind(None, email="ada@x.it", password="p")

    def test_backend_registrato_dopo_quello_del_nome_utente(self):
        self.assertEqual(
            settings.AUTHENTICATION_BACKENDS,
            [
                "django.contrib.auth.backends.ModelBackend",
                "apps.core.services.credenziale_ingresso.CredenzialePerEmailBackend",
            ],
        )
