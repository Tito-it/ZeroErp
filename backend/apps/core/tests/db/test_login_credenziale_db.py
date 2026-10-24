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
5b) RepositoryCredenzialeDbTests.test_nome_inesistente_frenato_sulla_sua_impronta
5c) RepositoryCredenzialeDbTests.test_successo_senza_credenziale_e_un_errore_del_chiamante
6) LoginViewDbTests.test_password_sbagliata_401_poi_freno_403_solo_da_quella_provenienza
6b) LoginViewDbTests.test_nome_inesistente_stesse_risposte_di_una_credenziale
6c) LoginViewDbTests.test_nome_con_spazi_non_aggira_il_freno
7) LoginViewDbTests.test_attesa_crescente_403_con_i_secondi_nel_messaggio
7b) LoginViewDbTests.test_portale_e_shop_cercano_la_credenziale_per_email (L-4)
7c) LoginViewDbTests.test_email_inesistente_frenata_a_prescindere_dalle_maiuscole (L-4)
8) CicloOperatoreDbTests.test_operatore_nuovo_crea_invita_attiva_entra
9) CicloOperatoreDbTests.test_credenziale_riusata_un_clic_e_password_intatta
   (con la lettura del dialog, B-20: la conferma dichiara l'id letto dall'endpoint)
10) CicloOperatoreDbTests.test_login_a_due_passi_col_secondo_fattore_attivo
   (T-2 del brief sicurezza §3.4-bis: password -> sfida -> codice -> sessione -> Bearer;
    il codice ripresentato e' rifiutato dall'anti-replay del DB)
11) CicloOperatoreDbTests.test_disabilitato_si_riattiva_col_reinvio_e_rientra
   (D-3: interruttore 400, rotta ritirata 404, reinvio che riapre il rapporto
    e non la porta, attivazione con un clic, rientro; valido_dal intatto)
12) CicloOperatoreDbTests.test_operatore_disabilitato_entra_ancora_come_cliente_shop
   (M-5 sul login: porta admin 403 E_VESTE_NON_ATTIVA, porta shop 200 con l'email, L-4)
13) CicloOperatoreDbTests.test_operatore_disabilitato_entra_ancora_come_cliente_portale
   (lo stesso giro con la veste CLIENTE_PORTALE: porta portale 200)
14) CicloOperatoreDbTests.test_veste_scaduta_non_entra_e_chiude_la_sessione_aperta
   (L-6, brief-db-veste-utilizzabile §6: la richiesta dopo e' 401, il refresh e'
    rifiutato — dopo uno riuscito, a veste valida —, il login 403
    E_VESTE_NON_ATTIVA; la porta del cliente resta aperta)
15) CicloOperatoreDbTests.test_scaduta_e_valida_sulla_stessa_porta_entra_la_valida
16) CicloOperatoreDbTests.test_rapporto_chiuso_dal_drawer_non_entra (D-2)
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

from apps.core.api.refresh_cookie import ANTI_CSRF_HEADER, ANTI_CSRF_VALORE, REFRESH_COOKIE_NAME
from apps.core.api.throttling import ConfermaTokenRateThrottle, LoginRateThrottle, PasswordResetRateThrottle
from apps.core.db.auth_repository import AuthRepository
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.nome_tentato import digest_nome_tentato
from apps.core.tests.db_e2e import apri_contesto_operatore, apri_transazione_annullata, richiedi_db_provvisto

_PASSWORD = "Giusta-Per-Il-Test-2026!"
_URL_LOGIN = "/api/v1/admin/token/"
_URL_LOGIN_SHOP = "/api/v1/shop/token/"
_URL_LOGIN_PORTALE = "/api/v1/portale/token/"
_URL_REFRESH = "/api/v1/admin/token/refresh/"
_URL_ME = "/api/v1/core/me/"
# Con la credenziale il DB non legge l'impronta, ma la pretende (brief §13.6):
# un check che la volesse solo per i nomi inesistenti darebbe al backend un
# ramo in piu' da tenere uguale.
_IMPRONTA = digest_nome_tentato("impronta-non-letta-con-la-credenziale")


# Scopo: I parametri del login come li legge il DB (sede unica dei numeri).
def _parametri() -> dict[str, int]:
    with connection.cursor() as cur:
        cur.execute("SELECT * FROM script.fn_login_parametri()")
        cols = [c.name for c in cur.description]
        return dict(zip(cols, cur.fetchone(), strict=True))


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
        apri_transazione_annullata(self)

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
                uid, nome_digest=_IMPRONTA, provenienza="198.51.100.1", successo=False,
            )
        self.assertTrue(esito["bloccato"])
        self.assertIn("attesa_secondi", esito)

        self.assertEqual(
            self._codice_errore(
                lambda: self.repo.check_blocco_login(uid, nome_digest=_IMPRONTA, provenienza="198.51.100.1")
            ),
            "E_UTENTE_BLOCCATO",
        )
        self.assertIsNone(
            self._codice_errore(
                lambda: self.repo.check_blocco_login(uid, nome_digest=_IMPRONTA, provenienza="198.51.100.2")
            )
        )

    # Scopo: Un accesso riuscito da P2 non toglie il freno su P1 (brief §11.2-3).
    def test_successo_toglie_il_freno_della_sola_coppia(self):
        uid = _nuova_credenziale().id
        n = _parametri()["max_tentativi"]
        for prov in ("198.51.100.1", "198.51.100.2"):
            for _ in range(n):
                self.repo.registra_tentativo_login(uid, nome_digest=_IMPRONTA, provenienza=prov, successo=False)

        self.repo.registra_tentativo_login(uid, nome_digest=_IMPRONTA, provenienza="198.51.100.2", successo=True)

        self.assertIsNone(
            self._codice_errore(
                lambda: self.repo.check_blocco_login(uid, nome_digest=_IMPRONTA, provenienza="198.51.100.2")
            )
        )
        self.assertEqual(
            self._codice_errore(
                lambda: self.repo.check_blocco_login(uid, nome_digest=_IMPRONTA, provenienza="198.51.100.1")
            ),
            "E_UTENTE_BLOCCATO",
        )

    # Scopo: Il reset (D-2) azzera su tutte le provenienze.
    def test_azzeramento_del_reset_toglie_tutti_i_freni(self):
        uid = _nuova_credenziale().id
        n = _parametri()["max_tentativi"]
        for _ in range(n):
            self.repo.registra_tentativo_login(uid, nome_digest=_IMPRONTA, provenienza="198.51.100.1", successo=False)

        self.repo.azzera_tentativi_credenziale(uid)

        self.assertIsNone(
            self._codice_errore(
                lambda: self.repo.check_blocco_login(uid, nome_digest=_IMPRONTA, provenienza="198.51.100.1")
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
            self._codice_errore(lambda: self.repo.check_blocco_login(uid, nome_digest=_IMPRONTA, provenienza=None)),
            "E_AUTH_CHIAMATA_NON_VALIDA",
        )

    # Scopo: R-7 — un nome che non trova una credenziale conta sulla sua
    # impronta: alla soglia la provenienza e' frenata, un'altra no.
    def test_nome_inesistente_frenato_sulla_sua_impronta(self):
        impronta = digest_nome_tentato(f"nessuno_{uuid.uuid4().hex}")
        n = _parametri()["max_tentativi"]
        for _ in range(n):
            esito = self.repo.registra_tentativo_login(
                None, nome_digest=impronta, provenienza="198.51.100.3", successo=False,
            )
        self.assertTrue(esito["bloccato"])
        self.assertEqual(
            self._codice_errore(
                lambda: self.repo.check_blocco_login(
                    None, nome_digest=impronta, provenienza="198.51.100.3",
                )
            ),
            "E_UTENTE_BLOCCATO",
        )
        self.assertIsNone(
            self._codice_errore(
                lambda: self.repo.check_blocco_login(
                    None, nome_digest=impronta, provenienza="198.51.100.4",
                )
            )
        )

    # Scopo: Un nome inesistente non entra mai: un successo senza credenziale
    # e' una chiamata rotta, e il DB la rifiuta.
    def test_successo_senza_credenziale_e_un_errore_del_chiamante(self):
        self.assertEqual(
            self._codice_errore(
                lambda: self.repo.registra_tentativo_login(
                    None, nome_digest=_IMPRONTA, provenienza="198.51.100.5", successo=True,
                )
            ),
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
    # `client`: per chi deve portare un cookie (il refresh); di norma uno nuovo.
    def _post(self, url: str, dati: dict, ip: str = "198.51.100.99", client: APIClient | None = None):
        sid = transaction.savepoint_create()
        risposta = (client or APIClient()).post(url, dati, format="json", REMOTE_ADDR=ip)
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
        # I minuti del freno arrivano nel `message` (dal `20260925-52`): il
        # login del frontend lo mostra com'e' (MESSAGGIO_DB_CON_DATO). Un `%s`
        # rimasto letterale, o il ripiego senza numero, sarebbero rossi qui.
        self.assertRegex(errore["message"], r"riprovare fra \d+ minuti")

        # Da un'altra macchina la credenziale non e' frenata: la password
        # giusta supera il check e la verifica, e si ferma alla veste (che
        # questa credenziale non ha). Un 403 con un ALTRO codice: e' la prova
        # che il freno non e' scattato.
        r = self._login(user.username, _PASSWORD, "198.51.100.11")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["error"]["code"], "E_VESTE_NON_ATTIVA")

    # ⭐ R-7, la parita': la stessa sequenza su un nome che non esiste da' le
    # stesse risposte che su una credenziale vera — n volte 401, poi 403
    # E_UTENTE_BLOCCATO. Prima il nome inesistente rispondeva 401 per sempre.
    def test_nome_inesistente_stesse_risposte_di_una_credenziale(self):
        nome = f"nessuno_{uuid.uuid4().hex[:12]}"
        n = _parametri()["max_tentativi"]
        for i in range(n):
            r = self._login(nome, "sbagliata", "198.51.100.12")
            self.assertEqual(r.status_code, 401, f"tentativo {i + 1}")

        r = self._login(nome, "sbagliata", "198.51.100.12")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["error"]["code"], "E_UTENTE_BLOCCATO")

    # Scopo: Il nome passa dalla normalizzazione del serializer (spazi tolti),
    # come in `authenticate`: con uno spazio davanti la credenziale frenata
    # resta frenata. Fino al 2026-09-25 il lookup usava il valore grezzo, non
    # trovava la credenziale e non la controllava, e la password giusta
    # arrivava fino alla veste (E_VESTE_NON_ATTIVA).
    def test_nome_con_spazi_non_aggira_il_freno(self):
        user = _nuova_credenziale()
        p = _parametri()
        n = p["max_tentativi"]
        if p["tetto_credenziale"] <= n:
            self.skipTest(
                f"tetto_credenziale ({p['tetto_credenziale']}) <= max_tentativi ({n}): "
                "l'attesa sulla credenziale copre il freno di coppia"
            )
        for _ in range(n):
            self.assertEqual(
                self._login(user.username, "sbagliata", "198.51.100.13").status_code, 401,
            )

        r = self._login(f"  {user.username} ", _PASSWORD, "198.51.100.13")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["error"]["code"], "E_UTENTE_BLOCCATO")

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

    # Scopo: L-4, D-9. Le porte del cliente cercano la credenziale per EMAIL
    # (backend `CredenzialePerEmailBackend` sul DB vero): la password giusta
    # passa la verifica e si ferma alla veste, che questa credenziale non ha.
    # Il nome utente della stessa credenziale non apre niente: 400, non un 401
    # (non e' un tentativo, la password non si guarda).
    def test_portale_e_shop_cercano_la_credenziale_per_email(self):
        nome = f"test_login_{uuid.uuid4().hex[:12]}"
        User.objects.create_user(username=nome, email=f"{nome}@example.invalid", password=_PASSWORD)
        for i, url in enumerate((_URL_LOGIN_PORTALE, _URL_LOGIN_SHOP)):
            with self.subTest(porta=url):
                ip = f"198.51.100.{40 + i}"
                r = self._post(url, {"email": f" {nome.upper()}@EXAMPLE.invalid", "password": _PASSWORD}, ip)
                self.assertEqual(r.status_code, 403, r.content)
                self.assertEqual(r.json()["error"]["code"], "E_VESTE_NON_ATTIVA")
                r = self._post(url, {"email": f"{nome}@example.invalid", "password": "sbagliata"}, ip)
                self.assertEqual(r.status_code, 401, r.content)
                r = self._post(url, {"username": nome, "password": _PASSWORD}, ip)
                self.assertEqual(r.status_code, 400, r.content)

    # Scopo: R-7 con l'email: un'email inesistente scritta con maiuscole
    # diverse e' lo STESSO nome tentato (lookup e impronta seguono la stessa
    # normalizzazione), quindi n fallimenti misti la frenano come una
    # credenziale vera. Con due normalizzazioni la variante di maiuscole
    # ripartirebbe da zero solo per chi non esiste: l'oracolo del nome.
    def test_email_inesistente_frenata_a_prescindere_dalle_maiuscole(self):
        email = f"nessuno_{uuid.uuid4().hex[:12]}@example.invalid"
        n = _parametri()["max_tentativi"]
        for i in range(n):
            variante = email.upper() if i % 2 else email
            r = self._post(_URL_LOGIN_PORTALE, {"email": variante, "password": "sbagliata"}, "198.51.100.42")
            self.assertEqual(r.status_code, 401, f"tentativo {i + 1}")

        r = self._post(_URL_LOGIN_PORTALE, {"email": email.title(), "password": "sbagliata"}, "198.51.100.42")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["error"]["code"], "E_UTENTE_BLOCCATO")


# Scopo: Un codice fiscale formalmente valido e sempre nuovo (le sei lettere
# sono casuali), per fabbricare il soggetto dell'operatore.
def _codice_fiscale() -> str:
    dispari = dict(zip("0123456789", (1, 0, 5, 7, 9, 13, 15, 17, 19, 21), strict=True))
    dispari.update(zip(string.ascii_uppercase, (
        1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23,
    ), strict=True))
    pari = {**{str(i): i for i in range(10)}, **{c: i for i, c in enumerate(string.ascii_uppercase)}}
    base = "".join(random.choices(string.ascii_uppercase, k=6)) + "80A01H501"
    somma = sum(dispari[c] if i % 2 == 0 else pari[c] for i, c in enumerate(base))
    return base + string.ascii_uppercase[somma % 26]


# ⭐ Il ciclo di vita dell'operatore sulla regola unica (L-3), tutto vero:
# la madre del DB crea la veste SPENTA, l'invito emette il token, la view
# pubblica attiva, il login entra. Solo l'email e' finta (se ne legge il link).
class CicloOperatoreDbTests(_ViewVere):

    # I test che vogliono il ruolo cliente (CL) di un'azienda, preparato
    # prima del contesto operatore.
    _CON_RUOLO_CLIENTE = frozenset({
        "test_operatore_disabilitato_entra_ancora_come_cliente_shop",
        "test_operatore_disabilitato_entra_ancora_come_cliente_portale",
        "test_veste_scaduta_non_entra_e_chiude_la_sessione_aperta",
        "test_scaduta_e_valida_sulla_stessa_porta_entra_la_valida",
        "test_rapporto_chiuso_dal_drawer_non_entra",
    })
    # Quelli che vogliono anche il ruolo fornitore (FO), per la seconda veste
    # della porta portale.
    _CON_RUOLO_FORNITORE = frozenset({
        "test_scaduta_e_valida_sulla_stessa_porta_entra_la_valida",
    })

    def setUp(self) -> None:
        super().setUp()
        self.enterContext(patch.object(PasswordResetRateThrottle, "allow_request", return_value=True))
        self.enterContext(patch.object(ConfermaTokenRateThrottle, "allow_request", return_value=True))
        with connection.cursor() as cur:
            # ⚠️ I builder dei soggetti PRIMA del contesto operatore (scrivono
            #    una saga, e dentro il contesto il controllo dell'indirizzo
            #    obbligatorio la ferma): il ruolo cliente lo prepara qui chi
            #    lo dichiara.
            self.ruolo_cliente = None
            if self._testMethodName in self._CON_RUOLO_CLIENTE:
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente shop di un operatore')")
                cliente = cur.fetchone()[0]
                cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s, 'CL')", [cliente])
                self.ruolo_cliente = cur.fetchone()[0]
                if self._testMethodName in self._CON_RUOLO_FORNITORE:
                    cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_pg('Fornitore portale')")
                    fornitore = cur.fetchone()[0]
                    cur.execute("SELECT dbops.fn_pgtap_crea_soggetto_ruolo(%s, 'FO')", [fornitore])
                    self.ruolo_fornitore = cur.fetchone()[0]
                # ⚠️ Il builder chiude la sua saga con i controlli IMMEDIATE, e
                #    il modo vale per il resto della transazione: la madre che
                #    crea l'operatore verrebbe controllata a meta' della sua
                #    («Indirizzo obbligatorio mancante»). Si torna allo stato di
                #    una transazione nuova, coi guard di completezza rimandati.
                cur.execute("SET CONSTRAINTS ALL DEFERRED")
            self.admin_id = apri_contesto_operatore(cur)
            cur.execute("SELECT id FROM config.qualifiche WHERE codice = 'DIPENDENTE'")
            self.qualifica_id = cur.fetchone()[0]
        email_finta = self.enterContext(patch("apps.core.services.invito_veste.EmailDispatchService"))
        self.email = email_finta.return_value
        # La forma vera della risposta, `(log_id, spedita)`: un MagicMock
        # nudo non si spacchetta, e `spedisci` lo registrava come email
        # fallita (traceback nel log a ogni invito, test verde lo stesso).
        self.email.send_email.return_value = (1, True)

    # Scopo: Crea l'operatore dal service vero (madre P-2).
    def _crea(self, *, email: str, username: str, codice_fiscale: str | None = None,
              riusa_auth_user_id: int | None = None) -> dict:
        from apps.amm_software.services.amm_software_service import AmmSoftwareService

        payload = {
            # Il sesso si SCEGLIE (brief-db-sesso-senza-default, 2026-10-09):
            # Per un soggetto nuovo (privato) lo pretende il guard del DB.
            "cognome": "Prova", "nome": "Ciclo", "sesso": "M",
            "codice_fiscale": codice_fiscale or _codice_fiscale(),
            "username": username, "email": email, "qualifica_id": self.qualifica_id,
        }
        if riusa_auth_user_id is not None:
            payload["riusa_auth_user_id"] = riusa_auth_user_id
        return AmmSoftwareService().create_operatore(payload)

    # Scopo: Invita col service vero; ritorna il token letto dal link dell'email.
    def _invita(self, auth_user_id: int) -> str:
        from apps.anagrafiche.services.invito_operatore_service import InvitoOperatoreService

        InvitoOperatoreService().invia_invito(auth_user_id, invitato_da_user_id=self.admin_id)
        link = self.email.send_email.call_args.kwargs["variabili"]["link"]
        return link.rsplit("/", 1)[1]

    # Scopo: `veste_attiva` dal repository vero (colonna di fn_get_operatore_detail, R-9).
    def _veste_attiva(self, auth_user_id: int) -> bool | None:
        from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository

        dettaglio = AmmSoftwareRepository().get_operatore_detail(auth_user_id)
        assert dettaglio is not None
        return dettaglio["veste_attiva"]

    # Scopo: La lettura del dialog (B-20) attraverso la view vera, da SUPER_ADMIN.
    def _credenziale_per_email(self, email: str) -> dict | None:
        client = APIClient()
        client.force_authenticate(User.objects.get(id=self.admin_id))
        r = client.get("/api/v1/amm-software/operatori/credenziale-per-email/", {"email": email})
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()["data"]["credenziale"]

    def _richiede_password(self, token: str) -> bool:
        dati = APIClient().get(f"/api/v1/auth/attivazione-validate/{token}/").json()["data"]
        self.assertTrue(dati["valid"])
        return dati["requires_password"]

    def test_operatore_nuovo_crea_invita_attiva_entra(self):
        nome = f"op_{uuid.uuid4().hex[:10]}"
        creato = self._crea(email=f"{nome}@example.invalid", username=nome)
        self.assertFalse(creato["credenziale_riusata"])
        uid = creato["auth_user_id"]
        # R-9: il dettaglio dice lo stato della VESTE, che nasce spenta.
        self.assertIs(self._veste_attiva(uid), False)

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
        self.assertIs(self._veste_attiva(uid), True)

    # Scopo: Una chiamata dell'amministratore attraverso la view vera.
    def _admin(self, metodo: str, url: str, dati: dict | None = None):
        # La key come dal frontend: ogni POST che scrive la porta (§A5 del
        # brief-be-verifica-documentazione-api, 2026-10-21).
        client = APIClient(HTTP_IDEMPOTENCY_KEY=f"test-{uuid.uuid4()}")
        client.force_authenticate(User.objects.get(id=self.admin_id))
        sid = transaction.savepoint_create()
        risposta = getattr(client, metodo)(url, dati or {}, format="json")
        if risposta.status_code == 200:
            transaction.savepoint_commit(sid)
        else:
            transaction.savepoint_rollback(sid)
        return risposta

    # Scopo: Il rapporto della veste operatore: (attivo, valido_dal, valido_al).
    def _rapporto(self, auth_user_id: int) -> tuple:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT ru.attivo, ru.valido_dal, ru.valido_al "
                "  FROM anagrafiche.risorse_umane ru "
                "  JOIN anagrafiche.identita_digitali id ON id.soggetto_ruolo_id = ru.soggetto_ruolo_id "
                " WHERE id.id = script.fn_veste_di_riferimento(%s, 'OPERATORE')",
                [auth_user_id],
            )
            return cur.fetchone()

    # Scopo: ⭐ D-3 (2026-10-04), il giro intero sulle view vere: un operatore
    # che e' entrato viene disabilitato; non si riaccende dall'interruttore
    # (400) ne' dalla rotta ritirata (404); il reinvio riapre il rapporto ma
    # non la porta (il login resta rifiutato); la persona attiva con un clic
    # (ha gia' la sua password) e rientra. `valido_dal` resta l'inizio del
    # rapporto. Solo l'email e' finta (se ne legge il link).
    def test_disabilitato_si_riattiva_col_reinvio_e_rientra(self):
        nome = f"op_{uuid.uuid4().hex[:10]}"
        uid = self._crea(email=f"{nome}@example.invalid", username=nome)["auth_user_id"]
        token = self._invita(uid)
        r = self._post("/api/v1/auth/attivazione/", {
            "token": token, "new_password": _PASSWORD, "new_password_confirm": _PASSWORD,
        })
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._login(nome, _PASSWORD, "198.51.100.32").status_code, 200)
        _, valido_dal, _ = self._rapporto(uid)

        base = f"/api/v1/amm-software/operatori/{uid}/"
        r = self._admin("post", base + "disabilita/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIs(self._veste_attiva(uid), False)
        self.assertIs(self._rapporto(uid)[0], False)
        self.assertEqual(self._login(nome, _PASSWORD, "198.51.100.32").status_code, 401)

        # L'interruttore non riaccende, e la vecchia rotta non c'e' piu'.
        r = self._admin("patch", base, {"attivo": True})
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(r.json()["error"]["code"], "E_AMM_VALIDAZIONE")
        self.assertEqual(self._admin("post", base + "riattiva/").status_code, 404)
        self.assertIs(self._veste_attiva(uid), False)

        # Il reinvio: rapporto riaperto, porta ancora chiusa.
        self.email.send_email.reset_mock()
        r = self._admin("post", base + "reinvia-invito/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._rapporto(uid), (True, valido_dal, None))
        self.assertIs(self._veste_attiva(uid), False)
        self.assertEqual(self._login(nome, _PASSWORD, "198.51.100.32").status_code, 401)

        # La persona ha gia' la password: un clic, poi rientra con la sua.
        token = self.email.send_email.call_args.kwargs["variabili"]["link"].rsplit("/", 1)[1]
        self.assertFalse(self._richiede_password(token))
        r = self._post("/api/v1/auth/attivazione/", {"token": token})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIs(self._veste_attiva(uid), True)
        self.assertEqual(self._login(nome, _PASSWORD, "198.51.100.32").status_code, 200)

    # Scopo: Un operatore attivato (madre + invito), che e' anche cliente:
    # la veste `ruolo_applicativo` sulla stessa credenziale (D-6), sul ruolo
    # cliente (CL) di un'azienda preparato dal setUp. La veste del cliente
    # tiene accesa la credenziale, cosi' un rifiuto alla porta admin e'
    # quello della VESTE operatore, non della password. Ritorna (nome, uid).
    def _operatore_anche_cliente(self, ruolo_applicativo: str, ip: str) -> tuple[str, int]:
        nome = f"op_{uuid.uuid4().hex[:10]}"
        uid = self._crea(email=f"{nome}@example.invalid", username=nome)["auth_user_id"]
        r = self._post("/api/v1/auth/attivazione/", {
            "token": self._invita(uid), "new_password": _PASSWORD, "new_password_confirm": _PASSWORD,
        }, ip)
        self.assertEqual(r.status_code, 200, r.content)
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO anagrafiche.identita_digitali "
                "(soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo) "
                "VALUES (%s, %s, %s, true)",
                [self.ruolo_cliente, uid, ruolo_applicativo],
            )
        return nome, uid

    # Scopo: Porta admin chiusa (403 E_VESTE_NON_ATTIVA: la credenziale e'
    # valida, la veste no) e porta del cliente aperta con la stessa password.
    # Spenta e fuori date hanno lo stesso esito (D-4). `email`: come la
    # scrive chi entra; di norma quella dell'operatore.
    def _porta_admin_chiusa_porta_cliente_aperta(
        self, nome: str, url_porta: str, ip: str, *, email: str | None = None,
    ) -> None:
        r = self._login(nome, _PASSWORD, ip)
        self.assertEqual(r.status_code, 403, r.content)
        self.assertEqual(r.json()["error"]["code"], "E_VESTE_NON_ATTIVA")
        email = email or f"{nome}@example.invalid"
        r = self._post(url_porta, {"email": email, "password": _PASSWORD}, ip)
        self.assertEqual(r.status_code, 200, r.content)

    # Scopo: ⭐ M-5 visto da chi entra (2026-10-04). Un operatore che e' anche
    # cliente (dello shop o del portale), con UNA credenziale (D-6):
    # disabilitato come operatore, dalla porta admin non entra piu', dalla
    # porta del cliente SI'. Il DB lo dice gia' (la veste del cliente resta
    # accesa, `is_active` e' l'OR delle vesti); qui lo si prova sul login,
    # che e' l'esito che conta per la persona. Prima di M-5 disabilitare
    # l'operatore toglieva l'accesso anche come cliente.
    def _disabilitato_entra_ancora_come_cliente(self, ruolo_applicativo: str, url_porta: str) -> None:
        ip = "198.51.100.33"
        nome, uid = self._operatore_anche_cliente(ruolo_applicativo, ip)
        self.assertEqual(self._login(nome, _PASSWORD, ip).status_code, 200)
        # La porta del cliente si apre con l'EMAIL (L-4), senza badare alle
        # maiuscole; il nome utente non e' il suo contratto (400, non un tentativo).
        email = f"{nome.upper()}@Example.INVALID"
        r = self._post(url_porta, {"email": email, "password": _PASSWORD}, ip)
        self.assertEqual(r.status_code, 200, r.content)
        r = self._post(url_porta, {"username": nome, "password": _PASSWORD}, ip)
        self.assertEqual(r.status_code, 400, r.content)

        r = self._admin("post", f"/api/v1/amm-software/operatori/{uid}/disabilita/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIs(self._veste_attiva(uid), False)
        # `is_active` resta acceso: c'e' ancora una veste utilizzabile.
        self.assertIs(User.objects.get(id=uid).is_active, True)

        self._porta_admin_chiusa_porta_cliente_aperta(nome, url_porta, ip, email=email)

    def test_operatore_disabilitato_entra_ancora_come_cliente_shop(self):
        self._disabilitato_entra_ancora_come_cliente("SHOP_CUSTOMER", _URL_LOGIN_SHOP)

    def test_operatore_disabilitato_entra_ancora_come_cliente_portale(self):
        self._disabilitato_entra_ancora_come_cliente("CLIENTE_PORTALE", _URL_LOGIN_PORTALE)

    # Scopo: ⭐ L-6 (brief-db-veste-utilizzabile §6). Una veste ACCESA ma uscita
    # dalle sue date non vale: la sessione aperta si chiude alla richiesta
    # successiva (401 E_IDENTITA_NON_ATTIVA, `set_jwt_gucs`), il refresh e'
    # rifiutato, il login nuovo e' 403. Prima del 2026-10-07 il BE guardava
    # solo `attivo`, e una veste scaduta entrava.
    def test_veste_scaduta_non_entra_e_chiude_la_sessione_aperta(self):
        ip = "198.51.100.50"
        nome, uid = self._operatore_anche_cliente("SHOP_CUSTOMER", ip)
        r = self._login(nome, _PASSWORD, ip)
        self.assertEqual(r.status_code, 200, r.content)
        access = r.json()["access"]
        bearer = APIClient(REMOTE_ADDR=ip)
        bearer.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(bearer.get(_URL_ME).status_code, 200)

        # ⚠️ Controllo positivo: con la veste ancora valida il refresh RINNOVA.
        #    Senza, il 401 di sotto passerebbe anche con un cookie che non
        #    arriva (refresh assente = 401): verde per sottrazione. Si tiene
        #    il refresh ruotato, il solo ancora buono.
        client_refresh = APIClient(headers={ANTI_CSRF_HEADER: ANTI_CSRF_VALORE})
        client_refresh.cookies[REFRESH_COOKIE_NAME] = r.cookies[REFRESH_COOKIE_NAME].value
        r = self._post(_URL_REFRESH, {}, ip, client=client_refresh)
        self.assertEqual(r.status_code, 200, r.content)
        client_refresh.cookies[REFRESH_COOKIE_NAME] = r.cookies[REFRESH_COOKIE_NAME].value

        # La veste resta ACCESA: esce solo dalla sua finestra (scaduta ieri).
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE anagrafiche.identita_digitali "
                "   SET valido_dal = script.fn_data_operativa() - 10, valido_al = script.fn_data_operativa() - 1 "
                " WHERE id = script.fn_veste_di_riferimento(%s, 'OPERATORE')",
                [uid],
            )
        self.assertIs(self._veste_attiva(uid), True)

        r = bearer.get(_URL_ME)
        self.assertEqual(r.status_code, 401, r.content)
        self.assertEqual(r.json()["error"]["code"], "E_IDENTITA_NON_ATTIVA")

        r = self._post(_URL_REFRESH, {}, ip, client=client_refresh)
        self.assertEqual(r.status_code, 401, r.content)

        self._porta_admin_chiusa_porta_cliente_aperta(nome, _URL_LOGIN_SHOP, ip)

    # Scopo: Due vesti della STESSA porta (portale), la piu' vecchia scaduta e
    # l'altra valida: entra la valida. Il login prende la prima UTILIZZABILE,
    # non la prima accesa.
    def test_scaduta_e_valida_sulla_stessa_porta_entra_la_valida(self):
        from rest_framework_simplejwt.tokens import AccessToken

        email = f"portale_{uuid.uuid4().hex[:10]}@example.invalid"
        persona = User.objects.create_user(username=email, email=email, password=_PASSWORD)
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO anagrafiche.identita_digitali "
                "(soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo, valido_dal, valido_al) "
                "VALUES (%s, %s, 'CLIENTE_PORTALE', true, script.fn_data_operativa() - 10, script.fn_data_operativa() - 1)",
                [self.ruolo_cliente, persona.id],
            )
            cur.execute(
                "INSERT INTO anagrafiche.identita_digitali "
                "(soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo) "
                "VALUES (%s, %s, 'FORNITORE_PORTALE', true) RETURNING id",
                [self.ruolo_fornitore, persona.id],
            )
            valida = cur.fetchone()[0]

        r = self._post(_URL_LOGIN_PORTALE, {"email": email, "password": _PASSWORD}, "198.51.100.51")
        self.assertEqual(r.status_code, 200, r.content)
        claims = AccessToken(r.json()["access"])
        self.assertEqual(claims["identita_id"], valida)
        self.assertEqual(claims["ruolo_applicativo"], "FORNITORE_PORTALE")

    # Scopo: ⭐ D-2 (strada (a)): per l'operatore conta anche il RAPPORTO. La
    # data «Valido al» del drawer scrive la fine del rapporto, non della veste,
    # e con la regola unica chiude l'accesso: la veste resta accesa, la porta
    # admin no.
    def test_rapporto_chiuso_dal_drawer_non_entra(self):
        ip = "198.51.100.52"
        nome, uid = self._operatore_anche_cliente("SHOP_CUSTOMER", ip)
        self.assertEqual(self._login(nome, _PASSWORD, ip).status_code, 200)

        # Il rapporto comincia prima, cosi' la sua fine puo' essere ieri.
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE anagrafiche.risorse_umane ru SET valido_dal = script.fn_data_operativa() - 10 "
                "  FROM anagrafiche.identita_digitali id "
                " WHERE id.soggetto_ruolo_id = ru.soggetto_ruolo_id "
                "   AND id.id = script.fn_veste_di_riferimento(%s, 'OPERATORE')",
                [uid],
            )
            cur.execute("SELECT (script.fn_data_operativa() - 1)::text")
            ieri = cur.fetchone()[0]
        r = self._admin("patch", f"/api/v1/amm-software/operatori/{uid}/", {"valido_al": ieri})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(str(self._rapporto(uid)[2]), ieri)
        self.assertIs(self._veste_attiva(uid), True)

        self._porta_admin_chiusa_porta_cliente_aperta(nome, _URL_LOGIN_SHOP, ip)

    # Scopo: T-2. Il login a due passi per intero, sulle view e sul DB veri.
    def test_login_a_due_passi_col_secondo_fattore_attivo(self):
        import pyotp

        from apps.core.db.secondo_fattore_repository import SecondoFattoreRepository
        from apps.core.services import crypto_service, totp_service

        nome = f"op_{uuid.uuid4().hex[:10]}"
        uid = self._crea(email=f"{nome}@example.invalid", username=nome)["auth_user_id"]
        r = self._post("/api/v1/auth/attivazione/", {
            "token": self._invita(uid), "new_password": _PASSWORD, "new_password_confirm": _PASSWORD,
        })
        self.assertEqual(r.status_code, 200, r.content)

        # Il device, scritto dai verbi come la credenziale stessa. La conferma
        # registra un passo di due periodi fa: il codice di adesso e' successivo.
        segreto = totp_service.nuovo_segreto()
        repo = SecondoFattoreRepository()
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.current_user_id', %s, true)", [str(uid)])
        repo.registra_device(
            uid,
            secret_encrypted=crypto_service.encrypt(segreto),
            impronte_recupero=[totp_service.impronta_codice_recupero(c) for c in totp_service.nuovi_codici_recupero()],
        )
        repo.conferma_device(uid, passo=totp_service.passo_corrente() - 2)
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.current_user_id', %s, true)", [str(self.admin_id)])

        ip = "198.51.100.40"
        url_secondo = "/api/v1/admin/token/secondo-fattore/"
        # Primo passo: la password non basta.
        r = self._login(nome, _PASSWORD, ip)
        self.assertEqual(r.status_code, 200, r.content)
        primo = r.json()
        self.assertTrue(primo["two_factor_required"])
        self.assertNotIn("access", primo)
        self.assertNotIn(REFRESH_COOKIE_NAME, r.cookies)

        # Secondo passo: il codice di adesso apre la sessione.
        codice = pyotp.TOTP(segreto).now()
        r = self._post(url_secondo, {"sfida": primo["sfida"], "codice": codice}, ip)
        self.assertEqual(r.status_code, 200, r.content)
        access = r.json()["data"]["access"]
        self.assertIn(REFRESH_COOKIE_NAME, r.cookies)
        self.assertIsNotNone(User.objects.get(id=uid).last_login)

        # La sessione vale: una richiesta col Bearer passa autenticazione e cancello.
        client = APIClient(REMOTE_ADDR=ip)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        self.assertEqual(client.get(_URL_ME).status_code, 200)

        # Lo stesso codice, con una sfida nuova: l'anti-replay sul passo lo rifiuta.
        sfida = self._login(nome, _PASSWORD, ip).json()["sfida"]
        r = self._post(url_secondo, {"sfida": sfida, "codice": codice}, ip)
        self.assertEqual(r.json()["error"]["code"], "E_TOTP_PASSO_GIA_USATO", r.content)

    # ⭐ Il riuso vuole il CONSENSO (`20260925-51`, brief §12.7): la prima
    # creazione si ferma con E_CREDENZIALE_DA_CONFERMARE, e passa solo
    # dichiarando la credenziale trovata (`riusa_auth_user_id`).
    def test_credenziale_riusata_un_clic_e_password_intatta(self):
        # Una persona che ha gia' un accesso (qui senza vesti: basta la
        # credenziale con una password vera).
        persona = _nuova_credenziale()
        persona.email = f"{persona.username}@example.invalid"
        persona.save(update_fields=["email"])
        cf = _codice_fiscale()

        # Primo tempo: senza consenso si ferma. Il service non traduce: il
        # DatabaseError arriva al middleware (punto 1 di api.md), che legge il
        # codice dal canale strutturato, come qui. Il messaggio nomina lo
        # username trovato: e' cio' che il dialog mostra all'admin.
        # ⚠️ Ogni rifiuto in un savepoint: senza, la transazione del test
        # resterebbe abortita per le chiamate dopo.
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            self._crea(email=persona.email.upper(), username="ignorato_dalla_madre",
                       codice_fiscale=cf)
        # ⚠️ Il canale strutturato, non `db_error_code`: quello ripiega sul
        #    testo, e renderebbe verde il test anche senza il codice nel canale.
        self.assertEqual(structured_db_error_code(ctx.exception), "E_CREDENZIALE_DA_CONFERMARE")
        self.assertIn(persona.username, str(ctx.exception))

        # Il dialog (B-20): legge la credenziale dall'endpoint vero, con la
        # stessa email della creazione. Mostra username e vesti, e l'id letto
        # e' quello che si dichiara confermando.
        letta = self._credenziale_per_email(persona.email.upper())
        self.assertEqual(letta, {"auth_user_id": persona.id, "username": persona.username, "vesti": []})
        self.assertIsNone(self._credenziale_per_email(f"nessuno_{uuid.uuid4().hex[:8]}@example.invalid"))

        # La dichiarazione di un'ALTRA credenziale non passa: una che esiste
        # davvero, non un id inventato (proverebbe solo «id inesistente»).
        altra = _nuova_credenziale()
        with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
            self._crea(email=persona.email.upper(), username="ignorato_dalla_madre",
                       codice_fiscale=cf, riusa_auth_user_id=altra.id)
        self.assertEqual(structured_db_error_code(ctx.exception), "E_CREDENZIALE_DA_CONFERMARE")

        # Secondo tempo: confermata la credenziale letta dal dialog, si crea.
        creato = self._crea(email=persona.email.upper(), username="ignorato_dalla_madre",
                            codice_fiscale=cf, riusa_auth_user_id=letta["auth_user_id"])
        self.assertTrue(creato["credenziale_riusata"])
        self.assertEqual(creato["auth_user_id"], persona.id)
        self.assertEqual(creato["username"], persona.username)
        # Ora la credenziale ha la veste OPERATORE, spenta: il dialog la vede.
        vesti = self._credenziale_per_email(persona.email)["vesti"]
        self.assertEqual([(v["ruolo_applicativo"], v["attivo"]) for v in vesti], [("OPERATORE", False)])

        # Prima dell'attivazione non si entra. Qui la credenziale non ha
        # nessun'altra veste attiva, quindi `is_active` (l'OR delle vesti,
        # guida multi-face §9) e' spento e l'autenticazione rifiuta prima di
        # guardare la porta: 401, come per l'operatore nuovo. Con un'altra
        # veste attiva (un cliente del portale) sarebbe il 403
        # E_VESTE_NON_ATTIVA della porta chiusa.
        self.assertIs(User.objects.get(id=persona.id).is_active, False)
        r = self._login(persona.username, _PASSWORD, "198.51.100.31")
        self.assertEqual(r.status_code, 401)

        token = self._invita(persona.id)
        self.assertFalse(self._richiede_password(token))
        r = self._post("/api/v1/auth/attivazione/", {"token": token})
        self.assertEqual(r.status_code, 200, r.content)

        # Entra con la SUA password: nessuno l'ha toccata (A-1).
        r = self._login(persona.username, _PASSWORD, "198.51.100.31")
        self.assertEqual(r.status_code, 200, r.content)
