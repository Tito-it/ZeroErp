# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Login e stato della credenziale sul DB VERO (P-1 del
#        brief-db-blocco-login-per-credenziale): il binding di AuthRepository
#        con le funzioni del DB e un login vero attraverso la view.
#
#        ⭐ PERCHE' SUL DB VERO. Le firme delle funzioni del login sono cambiate
#        (la provenienza, `fn_get/fn_imposta_deve_cambiare_password`) e le
#        colonne sono uscite da `identita_digitali`: i test col mock non vedono
#        nessuna delle due cose. Un parametro in piu' o un cast sbagliato qui
#        e' un login rotto per tutti.
#
#        ⭐ CASI COSTRUITI: credenziali e operatori il test se li fabbrica
#        (nessuna riga di sviluppo letta come dato), e tutto gira in una
#        transazione che viene SEMPRE annullata. I numeri (soglia, tetto) si
#        leggono da `script.fn_login_parametri()`, non si ricopiano.
#        Il login RIUSCITO vuole una veste attiva: la costruisce il ciclo vero
#        dell'operatore (madre del DB → invito → attivazione, L-3), che e'
#        esso stesso sotto prova. Per scrivere il soggetto serve il contesto
#        operatore (RLS): dove il DB non ha un superuser su cui aprirlo il
#        test salta col motivo (`apri_contesto_operatore`).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) RepositoryCredenzialeDbTests.test_freno_sulla_provenienza_e_non_sulle_altre
2) RepositoryCredenzialeDbTests.test_successo_toglie_il_freno_della_sola_coppia
3) RepositoryCredenzialeDbTests.test_azzeramento_del_reset_toglie_tutti_i_freni
4) RepositoryCredenzialeDbTests.test_deve_cambiare_password_della_credenziale
5) RepositoryCredenzialeDbTests.test_provenienza_mancante_e_un_errore_del_chiamante
6) LoginViewDbTests.test_password_sbagliata_401_poi_freno_403_solo_da_quella_provenienza
7) LoginViewDbTests.test_attesa_crescente_403_con_i_secondi_nel_messaggio
8) CicloOperatoreDbTests.test_operatore_nuovo_crea_invita_attiva_entra
9) CicloOperatoreDbTests.test_credenziale_riusata_un_clic_e_password_intatta
"""

from __future__ import annotations

import random
import string
import unittest
import uuid
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import DatabaseError, connection, transaction
from django.test import override_settings
from rest_framework.test import APIClient

from apps.core.api.throttling import LoginRateThrottle, PasswordResetRateThrottle
from apps.core.db.auth_repository import AuthRepository
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto

_PASSWORD = "Giusta-Per-Il-Test-2026!"
_URL_LOGIN = "/api/v1/admin/token/"


# Scopo: I parametri del login come li legge il DB (sede unica dei numeri).
def _parametri() -> dict[str, int]:
    with connection.cursor() as cur:
        cur.execute("SELECT * FROM script.fn_login_parametri()")
        cols = [c.name for c in cur.description]
        return dict(zip(cols, cur.fetchone()))


# Scopo: Credenziale fabbricata, senza nessuna veste: conta anch'essa (brief §3.1).
def _nuova_credenziale() -> User:
    return User.objects.create_user(
        username=f"test_login_{uuid.uuid4().hex[:12]}",
        email="",
        password=_PASSWORD,
    )


class _TransazioneAnnullata(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        self._atomic = transaction.atomic()
        self._atomic.__enter__()

    def tearDown(self) -> None:
        transaction.set_rollback(True)
        self._atomic.__exit__(None, None, None)

    # Scopo: Esegue `azione` in un savepoint e ne ritorna il codice d'errore del DB.
    def _codice_errore(self, azione) -> str | None:
        try:
            with transaction.atomic():
                azione()
        except DatabaseError as exc:
            return structured_db_error_code(exc)
        return None


class RepositoryCredenzialeDbTests(_TransazioneAnnullata):
    repo = AuthRepository()

    # Scopo: N fallimenti da P1 frenano P1 (E_UTENTE_BLOCCATO); da P2 si passa.
    def test_freno_sulla_provenienza_e_non_sulle_altre(self):
        uid = _nuova_credenziale().id
        n = _parametri()["max_tentativi"]
        for _ in range(n):
            esito = self.repo.registra_tentativo_login(
                uid, provenienza="198.51.100.1", successo=False,
            )
        self.assertTrue(esito["bloccato"])
        self.assertIn("attesa_secondi", esito)

        self.assertEqual(
            self._codice_errore(
                lambda: self.repo.check_blocco_login(uid, provenienza="198.51.100.1")
            ),
            "E_UTENTE_BLOCCATO",
        )
        self.assertIsNone(
            self._codice_errore(
                lambda: self.repo.check_blocco_login(uid, provenienza="198.51.100.2")
            )
        )

    # Scopo: Un accesso riuscito da P2 non toglie il freno su P1 (brief §11.2-3).
    def test_successo_toglie_il_freno_della_sola_coppia(self):
        uid = _nuova_credenziale().id
        n = _parametri()["max_tentativi"]
        for prov in ("198.51.100.1", "198.51.100.2"):
            for _ in range(n):
                self.repo.registra_tentativo_login(uid, provenienza=prov, successo=False)

        self.repo.registra_tentativo_login(uid, provenienza="198.51.100.2", successo=True)

        self.assertIsNone(
            self._codice_errore(
                lambda: self.repo.check_blocco_login(uid, provenienza="198.51.100.2")
            )
        )
        self.assertEqual(
            self._codice_errore(
                lambda: self.repo.check_blocco_login(uid, provenienza="198.51.100.1")
            ),
            "E_UTENTE_BLOCCATO",
        )

    # Scopo: Il reset (D-2) azzera su tutte le provenienze.
    def test_azzeramento_del_reset_toglie_tutti_i_freni(self):
        uid = _nuova_credenziale().id
        n = _parametri()["max_tentativi"]
        for _ in range(n):
            self.repo.registra_tentativo_login(uid, provenienza="198.51.100.1", successo=False)

        self.repo.azzera_tentativi_credenziale(uid)

        self.assertIsNone(
            self._codice_errore(
                lambda: self.repo.check_blocco_login(uid, provenienza="198.51.100.1")
            )
        )

    # Scopo: Il flag e' della credenziale: assente = False, poi si accende e si spegne.
    def test_deve_cambiare_password_della_credenziale(self):
        uid = _nuova_credenziale().id
        self.assertFalse(self.repo.get_deve_cambiare_password(uid))
        self.repo.set_deve_cambiare_password(uid, True)
        self.assertTrue(self.repo.get_deve_cambiare_password(uid))
        self.repo.set_deve_cambiare_password(uid, False)
        self.assertFalse(self.repo.get_deve_cambiare_password(uid))

    # Scopo: Il DB rifiuta la provenienza NULL: la view non deve mai mandarla.
    def test_provenienza_mancante_e_un_errore_del_chiamante(self):
        uid = _nuova_credenziale().id
        self.assertEqual(
            self._codice_errore(lambda: self.repo.check_blocco_login(uid, provenienza=None)),
            "E_AUTH_CHIAMATA_NON_VALIDA",
        )


# Nessun proxy: la provenienza e' REMOTE_ADDR, qualunque sia l'env della
# macchina. Il throttle per IP e' un'altra regola (5 richieste): qui si
# spegne, altrimenti coprirebbe il freno della credenziale. Base senza test:
# la usano il login e il ciclo dell'operatore.
class _ViewVere(_TransazioneAnnullata):

    def setUp(self) -> None:
        super().setUp()
        self.enterContext(override_settings(TRUSTED_PROXY_COUNT=0, REQUEST_LOG_ENABLED=False))
        self.enterContext(patch.object(LoginRateThrottle, "allow_request", return_value=True))

    # Scopo: POST a una view vera da una provenienza. Si conferma il savepoint
    # SOLO dove c'e' qualcosa da tenere: 401 (il fallimento registrato) e 200.
    # Ogni altro esito si annulla: un rifiuto sollevato dal DB (403) o un
    # guasto (500) lasciano la transazione interrotta, e confermarla farebbe
    # fallire le asserzioni successive con un errore che non e' il loro.
    def _post(self, url: str, dati: dict, ip: str = "198.51.100.99"):
        sid = transaction.savepoint()
        risposta = APIClient().post(url, dati, format="json", REMOTE_ADDR=ip)
        if risposta.status_code in (200, 401):
            transaction.savepoint_commit(sid)
        else:
            transaction.savepoint_rollback(sid)
        return risposta

    def _login(self, username: str, password: str, ip: str):
        return self._post(_URL_LOGIN, {"username": username, "password": password}, ip)


class LoginViewDbTests(_ViewVere):

    def test_password_sbagliata_401_poi_freno_403_solo_da_quella_provenienza(self):
        user = _nuova_credenziale()
        p = _parametri()
        n = p["max_tentativi"]
        # La prova dall'altra provenienza distingue il freno di COPPIA solo se
        # gli n fallimenti non hanno gia' portato la credenziale al tetto
        # dell'attesa: altrimenti il 403 sarebbe E_LOGIN_ATTESA, giusto ma
        # un'altra regola. Dipende dai parametri: si dichiara, non si assume.
        if p["tetto_credenziale"] <= n:
            self.skipTest(
                f"tetto_credenziale ({p['tetto_credenziale']}) <= max_tentativi ({n}): "
                "l'attesa sulla credenziale copre il freno di coppia"
            )
        for _ in range(n):
            r = self._login(user.username, "sbagliata", "198.51.100.10")
            self.assertEqual(r.status_code, 401)

        r = self._login(user.username, _PASSWORD, "198.51.100.10")
        self.assertEqual(r.status_code, 403)
        errore = r.json()["error"]
        self.assertEqual(errore["code"], "E_UTENTE_BLOCCATO")

        # Da un'altra macchina la credenziale non e' frenata: la password
        # giusta supera il check e la verifica, e si ferma alla veste (che
        # questa credenziale non ha). Un 403 con un ALTRO codice: e' la prova
        # che il freno non e' scattato.
        r = self._login(user.username, _PASSWORD, "198.51.100.11")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["error"]["code"], "E_VESTE_NON_ATTIVA")

    def test_attesa_crescente_403_con_i_secondi_nel_messaggio(self):
        user = _nuova_credenziale()
        p = _parametri()
        # Ogni provenienza sbaglia una volta sola: nessun freno di coppia,
        # ma la credenziale arriva al tetto.
        for i in range(p["tetto_credenziale"]):
            r = self._login(user.username, "sbagliata", f"203.0.113.{i + 1}")
            self.assertEqual(r.status_code, 401, f"tentativo {i + 1}")

        r = self._login(user.username, _PASSWORD, "192.0.2.200")
        self.assertEqual(r.status_code, 403)
        errore = r.json()["error"]
        self.assertEqual(errore["code"], "E_LOGIN_ATTESA")
        # Il frontend mostra `message`, la frase del DB coi secondi riempiti.
        # ⚠️ NON `detail`: li' arriva la causa del catalogo, senza numeri.
        self.assertRegex(errore["message"], r"\d+ secondi")


# Scopo: Un codice fiscale formalmente valido e sempre nuovo (le sei lettere
# sono casuali), per fabbricare il soggetto dell'operatore.
def _codice_fiscale() -> str:
    dispari = dict(zip("0123456789", (1, 0, 5, 7, 9, 13, 15, 17, 19, 21)))
    dispari.update(zip(string.ascii_uppercase, (
        1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23,
    )))
    pari = {**{str(i): i for i in range(10)}, **{c: i for i, c in enumerate(string.ascii_uppercase)}}
    base = "".join(random.choices(string.ascii_uppercase, k=6)) + "80A01H501"
    somma = sum(dispari[c] if i % 2 == 0 else pari[c] for i, c in enumerate(base))
    return base + string.ascii_uppercase[somma % 26]


# ⭐ Il ciclo di vita dell'operatore sulla regola unica (L-3), tutto vero:
# la madre del DB crea la veste SPENTA, l'invito emette il token, la view
# pubblica attiva, il login entra. Solo l'email e' finta (se ne legge il link).
class CicloOperatoreDbTests(_ViewVere):

    def setUp(self) -> None:
        super().setUp()
        self.enterContext(patch.object(PasswordResetRateThrottle, "allow_request", return_value=True))
        with connection.cursor() as cur:
            self.admin_id = apri_contesto_operatore(cur)
            cur.execute("SELECT id FROM config.qualifiche WHERE codice = 'DIPENDENTE'")
            self.qualifica_id = cur.fetchone()[0]
        email_finta = self.enterContext(patch("apps.core.services.invito_veste.EmailDispatchService"))
        self.email = email_finta.return_value

    # Scopo: Crea l'operatore dal service vero (madre P-2).
    def _crea(self, *, email: str, username: str) -> dict:
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        return AmmSoftwareService().create_operatore({
            "cognome": "Prova", "nome": "Ciclo", "codice_fiscale": _codice_fiscale(),
            "username": username, "email": email, "qualifica_id": self.qualifica_id,
        })

    # Scopo: Invita col service vero; ritorna il token letto dal link dell'email.
    def _invita(self, auth_user_id: int) -> str:
        from apps.anagrafiche.services.invito_operatore_service import InvitoOperatoreService

        InvitoOperatoreService().invia_invito(auth_user_id, invitato_da_user_id=self.admin_id)
        link = self.email.send_email.call_args.kwargs["variabili"]["link"]
        return link.rsplit("/", 1)[1]

    def _richiede_password(self, token: str) -> bool:
        dati = APIClient().get(f"/api/v1/auth/attivazione-validate/{token}/").json()["data"]
        self.assertTrue(dati["valid"])
        return dati["requires_password"]

    def test_operatore_nuovo_crea_invita_attiva_entra(self):
        nome = f"op_{uuid.uuid4().hex[:10]}"
        creato = self._crea(email=f"{nome}@example.invalid", username=nome)
        self.assertFalse(creato["credenziale_riusata"])
        uid = creato["auth_user_id"]

        # Prima dell'attivazione non si entra: la password non esiste ancora.
        self.assertEqual(self._login(nome, _PASSWORD, "198.51.100.30").status_code, 401)

        token = self._invita(uid)
        self.assertTrue(self._richiede_password(token))
        r = self._post("/api/v1/auth/attivazione/", {
            "token": token, "new_password": _PASSWORD, "new_password_confirm": _PASSWORD,
        })
        self.assertEqual(r.status_code, 200, r.content)

        r = self._login(nome, _PASSWORD, "198.51.100.30")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIsNotNone(User.objects.get(id=uid).last_login)  # D-8

    # ⏸️ Dichiarato, non a vuoto: su dbdev la madre e' gia' alla rev -51 (brief
    # §12.7, il riuso vuole il CONSENSO: `p_riusa_auth_user_id`, altrimenti
    # E_CREDENZIALE_DA_CONFERMARE), che in git non c'e' ancora. Il backend non
    # si scrive su un contratto che non e' in git: quando la -51 arriva, il
    # service passa il consenso e questo test lo esercita (piano §4.1).
    @unittest.skip("attende la rev -51 della madre in git (consenso al riuso, brief §12.7)")
    def test_credenziale_riusata_un_clic_e_password_intatta(self):
        # Una persona che ha gia' un accesso (qui senza vesti: basta la
        # credenziale con una password vera).
        persona = _nuova_credenziale()
        persona.email = f"{persona.username}@example.invalid"
        persona.save(update_fields=["email"])

        creato = self._crea(email=persona.email.upper(), username="ignorato_dalla_madre")
        self.assertTrue(creato["credenziale_riusata"])
        self.assertEqual(creato["auth_user_id"], persona.id)
        self.assertEqual(creato["username"], persona.username)

        # Veste spenta: la password e' giusta ma la porta e' chiusa.
        r = self._login(persona.username, _PASSWORD, "198.51.100.31")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["error"]["code"], "E_VESTE_NON_ATTIVA")

        token = self._invita(persona.id)
        self.assertFalse(self._richiede_password(token))
        r = self._post("/api/v1/auth/attivazione/", {"token": token})
        self.assertEqual(r.status_code, 200, r.content)

        # Entra con la SUA password: nessuno l'ha toccata (A-1).
        r = self._login(persona.username, _PASSWORD, "198.51.100.31")
        self.assertEqual(r.status_code, 200, r.content)
