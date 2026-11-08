# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gli obblighi della credenziale e il secondo fattore sul DB VERO
#        (brief sicurezza §3.4-bis, T-0 e seguenti): il binding di
#        AuthRepository con le funzioni `script` del cambio password e del
#        TOTP. I mock non vedono un nome di colonna o un cast sbagliati, e qui
#        un errore e' un cancello che non apre a nessuno.
#
#        ⭐ CASI COSTRUITI: le credenziali il test se le fabbrica, tutto gira
#        in una transazione SEMPRE annullata.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) FattiObblighiDbTests.test_credenziale_nuova_nessun_obbligo — una riga anche a riga assente
2) FattiObblighiDbTests.test_cambio_password_pendente_dal_db — il cancello legge il flag vero
3) DeviceDbTests.test_ciclo_di_vita_del_device — registra, conferma, usa, disabilita
4) DeviceDbTests.test_anti_replay_sul_passo — lo stesso passo due volte, uno piu' vecchio
5) DeviceDbTests.test_codici_di_recupero_monouso — consuma, conta, rigenera
6) DeviceDbTests.test_obbligo_da_configurare_con_device_a_meta — DA_CONFERMARE non soddisfa
7) DeviceDbTests.test_uso_senza_device_attivo — prima della conferma niente login
8) ServizioDbTests.test_configura_rigenera_e_disattiva_da_se — col servizio, e la riga di traccia
9) ServizioDbTests.test_il_super_admin_impone_l_obbligo_e_disattiva_col_motivo — il SUPER_ADMIN lo crea il test
10) ServizioDbTests.test_chi_non_e_super_admin_non_impone_ne_disattiva — E_PERMESSO_NEGATO dai verbi
11) ServizioDbTests.test_senza_traccia_la_disattivazione_si_annulla — D-T3, il savepoint del servizio
12) ServizioDbTests.test_la_password_sbagliata_conta_e_frena_la_configurazione — D-T2 sul freno vero
13) ServizioDbTests.test_su_una_credenziale_di_sistema_l_obbligo_non_si_accende — le uscite restano aperte
14) ServizioDbTests.test_configura_confermato_dal_provisioning — gia' confermato, e un device attivo resta
"""

from __future__ import annotations

import unittest
import uuid
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import DatabaseError, connection, transaction
from django.test import override_settings

from apps.core.api.cancello_obblighi import (
    OBBLIGO_CAMBIO_PASSWORD,
    OBBLIGO_SECONDO_FATTORE,
    obblighi_pendenti,
)
from apps.core.db._helpers import jsonb_out
from apps.core.db.auth_repository import AuthRepository
from apps.core.db.secondo_fattore_repository import SecondoFattoreRepository
from apps.core.services import crypto_service, totp_service
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


# Scopo: Credenziale fabbricata, senza vesti e senza device.
_PASSWORD = "Giusta-Per-Il-Test-2026!"


def _nuova_credenziale() -> User:
    return User.objects.create_user(
        username=f"test_obblighi_{uuid.uuid4().hex[:12]}",
        email="",
        password=_PASSWORD,
    )


class _TransazioneAnnullata(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)

    # Scopo: Come `_codice_errore`, ma senza savepoint: per provare che il
    #        savepoint ce l'ha chi viene chiamato.
    @staticmethod
    def _codice_senza_savepoint(azione) -> str | None:
        try:
            azione()
        except DatabaseError as exc:
            return structured_db_error_code(exc)
        return None

    # Scopo: Esegue `azione` in un savepoint e ne ritorna il codice d'errore del DB.
    def _codice_errore(self, azione) -> str | None:
        try:
            with transaction.atomic():
                azione()
        except DatabaseError as exc:
            return structured_db_error_code(exc)
        return None


class FattiObblighiDbTests(_TransazioneAnnullata):
    repo = AuthRepository()

    # Scopo: Le tre funzioni rispondono con una riga anche per una
    # credenziale che non ha niente: niente obblighi, device ASSENTE.
    def test_credenziale_nuova_nessun_obbligo(self):
        fatti = self.repo.get_fatti_obblighi(_nuova_credenziale().id)
        self.assertEqual(
            fatti,
            {
                "deve_cambiare_password": False,
                "totp_obbligatorio": False,
                "totp_motivo": None,
                "totp_stato": "ASSENTE",
            },
        )
        self.assertEqual(obblighi_pendenti(fatti), ())

    # Scopo: Il flag scritto dal verbo del DB arriva al cancello.
    def test_cambio_password_pendente_dal_db(self):
        uid = _nuova_credenziale().id
        self.repo.set_deve_cambiare_password(uid, True)
        self.assertEqual(
            obblighi_pendenti(self.repo.get_fatti_obblighi(uid)),
            (OBBLIGO_CAMBIO_PASSWORD,),
        )


class DeviceDbTests(_TransazioneAnnullata):
    repo = SecondoFattoreRepository()

    # Scopo: Una credenziale fabbricata che agisce su di se': i verbi
    # «dell'utente stesso» leggono `app.current_user_id`, come col Bearer.
    def setUp(self) -> None:
        super().setUp()
        self.uid = _nuova_credenziale().id
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.current_user_id', %s, true)", [str(self.uid)])
        self.codici = totp_service.nuovi_codici_recupero()

    # Scopo: Registra un device col segreto cifrato e il mazzo del setUp.
    def _registra(self) -> None:
        self.repo.registra_device(
            self.uid,
            secret_encrypted=crypto_service.encrypt(totp_service.nuovo_segreto()),
            impronte_recupero=[totp_service.impronta_codice_recupero(c) for c in self.codici],
        )

    def test_ciclo_di_vita_del_device(self):
        self.assertEqual(self.repo.get_device(self.uid)["stato"], "ASSENTE")
        self._registra()
        device = self.repo.get_device(self.uid)
        self.assertEqual(device["stato"], "DA_CONFERMARE")
        self.assertEqual(device["recovery_rimasti"], len(self.codici))
        # Il segreto torna com'e' stato scritto: cifrato, e si apre.
        self.assertEqual(len(crypto_service.decrypt(device["secret_encrypted"])), 32)

        passo = totp_service.passo_corrente()
        self.repo.conferma_device(self.uid, passo=passo)
        self.assertEqual(self.repo.get_device(self.uid)["stato"], "ATTIVO")
        self.assertEqual(self.repo.get_device(self.uid)["ultimo_passo_usato"], passo)

        self.repo.registra_uso(self.uid, passo=passo + 1)
        self.assertEqual(self.repo.get_device(self.uid)["ultimo_passo_usato"], passo + 1)

        self.repo.disabilita_device(self.uid, motivo=None)
        self.assertEqual(self.repo.get_device(self.uid)["stato"], "ASSENTE")

    def test_anti_replay_sul_passo(self):
        self._registra()
        passo = totp_service.passo_corrente()
        self.repo.conferma_device(self.uid, passo=passo)
        self.assertEqual(
            self._codice_errore(lambda: self.repo.registra_uso(self.uid, passo=passo)),
            "E_TOTP_PASSO_GIA_USATO",
        )
        self.assertEqual(
            self._codice_errore(lambda: self.repo.registra_uso(self.uid, passo=passo - 1)),
            "E_TOTP_PASSO_GIA_USATO",
        )

    def test_codici_di_recupero_monouso(self):
        self._registra()
        self.repo.conferma_device(self.uid, passo=totp_service.passo_corrente())
        # Scritto come lo digita una persona: minuscolo, senza trattini.
        digitato = self.codici[0].lower().replace("-", "")
        impronta = totp_service.impronta_codice_recupero(digitato)
        self.assertEqual(self.repo.consuma_recovery(self.uid, impronta=impronta), len(self.codici) - 1)
        self.assertEqual(
            self._codice_errore(lambda: self.repo.consuma_recovery(self.uid, impronta=impronta)),
            "E_TOTP_RECOVERY_NON_VALIDO",
        )
        nuovi = totp_service.nuovi_codici_recupero()
        self.repo.rigenera_recovery(
            self.uid, impronte_recupero=[totp_service.impronta_codice_recupero(c) for c in nuovi],
        )
        self.assertEqual(self.repo.get_device(self.uid)["recovery_rimasti"], len(nuovi))
        # I vecchi non valgono piu'.
        vecchia = totp_service.impronta_codice_recupero(self.codici[1])
        self.assertEqual(
            self._codice_errore(lambda: self.repo.consuma_recovery(self.uid, impronta=vecchia)),
            "E_TOTP_RECOVERY_NON_VALIDO",
        )

    # Scopo: Il cancello sui fatti veri: una configurazione a meta' non
    # soddisfa l'obbligo, la conferma si'. L'obbligo lo accende il verbo del
    # SUPER_ADMIN, che qui non c'e': lo si scrive come fatto, sulla regola.
    def test_obbligo_da_configurare_con_device_a_meta(self):
        self._registra()
        fatti = AuthRepository().get_fatti_obblighi(self.uid)
        self.assertEqual(fatti["totp_stato"], "DA_CONFERMARE")
        self.assertEqual(
            obblighi_pendenti({**fatti, "totp_obbligatorio": True}), (OBBLIGO_SECONDO_FATTORE,),
        )
        self.repo.conferma_device(self.uid, passo=totp_service.passo_corrente())
        fatti = AuthRepository().get_fatti_obblighi(self.uid)
        self.assertEqual(obblighi_pendenti({**fatti, "totp_obbligatorio": True}), ())

    def test_uso_senza_device_attivo(self):
        passo = totp_service.passo_corrente()
        self.assertEqual(
            self._codice_errore(lambda: self.repo.registra_uso(self.uid, passo=passo)),
            "E_TOTP_DEVICE_ASSENTE",
        )
        self._registra()
        self.assertEqual(
            self._codice_errore(lambda: self.repo.registra_uso(self.uid, passo=passo)),
            "E_TOTP_DEVICE_ASSENTE",
        )


class ServizioDbTests(_TransazioneAnnullata):
    """Il servizio sui verbi veri: cio' che le view del self-service e del
    SUPER_ADMIN fanno, senza HTTP (la view e' provata coi mock)."""

    def setUp(self) -> None:
        super().setUp()
        from django.test import RequestFactory

        from apps.core.services.secondo_fattore_service import SecondoFattoreService

        self.servizio = SecondoFattoreService()
        self.user = _nuova_credenziale()
        # La provenienza da REMOTE_ADDR, qualunque sia la catena di proxy della
        # macchina: il freno la vuole, e il test non deve dipendere da env.sh.
        self.enterContext(override_settings(TRUSTED_PROXY_COUNT=0))
        self.request = RequestFactory().post("/", REMOTE_ADDR="198.51.100.60")

    # Scopo: Chi agisce, per i verbi che lo leggono (la GUC del Bearer).
    @staticmethod
    def _agisce(auth_user_id: int) -> None:
        with connection.cursor() as cur:
            cur.execute("SELECT set_config('app.current_user_id', %s, true)", [str(auth_user_id)])

    # Scopo: Il codice dell'app per il segreto mostrato, al passo dato.
    @staticmethod
    def _codice(segreto_mostrato: str, passo: int) -> str:
        import pyotp

        return pyotp.TOTP(segreto_mostrato.replace(" ", "")).generate_otp(passo)

    # Scopo: Le righe TOTP_DISABILITATO della credenziale.
    @staticmethod
    def _tracce(auth_user_id: int) -> list:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dettaglio FROM dbops.sessioni_utente "
                "WHERE auth_user_id = %s AND evento = 'TOTP_DISABILITATO'",
                [auth_user_id],
            )
            return [jsonb_out(r[0]) for r in cur.fetchall()]

    def test_configura_rigenera_e_disattiva_da_se(self):
        self._agisce(self.user.id)
        adesso = totp_service.passo_corrente()
        configurazione = self.servizio.avvia_configurazione(
            self.user, _PASSWORD, request=self.request,
        )
        self.assertEqual(self.servizio.stato(self.user.id)["stato"], "DA_CONFERMARE")

        # Conferma col codice del passo precedente: il successivo resta libero.
        segreto = configurazione["segreto"]
        with patch("apps.core.services.totp_service.passo_corrente", return_value=adesso - 1):
            self.servizio.conferma_configurazione(self.user, self._codice(segreto, adesso - 1))
        self.assertEqual(self.servizio.stato(self.user.id)["stato"], "ATTIVO")

        with patch("apps.core.services.totp_service.passo_corrente", return_value=adesso):
            nuovi = self.servizio.rigenera_codici_recupero(
                self.user, self._codice(segreto, adesso), provenienza="198.51.100.60",
            )["codici_recupero"]

        # Disattiva con un codice di recupero NUOVO: la traccia c'e', via APP.
        self.servizio.disattiva_propria(
            self.user, codice=None, codice_recupero=nuovi[0],
            provenienza="198.51.100.60", request=self.request,
        )
        self.assertEqual(self.servizio.stato(self.user.id)["stato"], "ASSENTE")
        self.assertEqual(
            self._tracce(self.user.id),
            [{"via": "APP", "chi_agisce": self.user.id, "motivo": None}],
        )

    # Scopo: Il provisioning di sviluppo configura il device GIA' confermato,
    #        sui verbi veri e come la credenziale stessa; il segreto restituito
    #        e' quello scritto; su un device attivo non tocca niente.
    def test_configura_confermato_dal_provisioning(self):
        self._agisce(self.user.id)
        configurazione = self.servizio.configura_confermato(self.user)
        assert configurazione is not None
        device = self.servizio.device(self.user.id)
        self.assertEqual(device["stato"], "ATTIVO")
        self.assertEqual(crypto_service.decrypt(device["secret_encrypted"]), configurazione["segreto"])
        # Il passo di adesso resta libero per il primo login.
        self.assertLess(device["ultimo_passo_usato"], totp_service.passo_corrente())
        self.assertEqual(device["recovery_rimasti"], len(configurazione["codici_recupero"]))
        self.assertIsNone(self.servizio.configura_confermato(self.user))
        self.assertEqual(
            crypto_service.decrypt(self.servizio.device(self.user.id)["secret_encrypted"]),
            configurazione["segreto"],
        )

    # Scopo: La password sbagliata all'avvio della configurazione conta sul
    #        freno VERO della credenziale: dopo `max_tentativi` dalla stessa
    #        provenienza si ferma anche chi la scrive giusta, e il device non
    #        nasce (brief secondo fattore e riautenticazione).
    def test_la_password_sbagliata_conta_e_frena_la_configurazione(self):
        self._agisce(self.user.id)
        with connection.cursor() as cur:
            cur.execute("SELECT max_tentativi FROM script.fn_login_parametri()")
            n = cur.fetchone()[0]
        from django.test import RequestFactory

        # Una provenienza sua: il freno e' sulla coppia credenziale + provenienza.
        richiesta = RequestFactory().post("/", REMOTE_ADDR="198.51.100.61")
        for _ in range(n - 1):
            with self.assertRaises(ServiceError) as rifiuto:
                self.servizio.avvia_configurazione(self.user, "Sbagliata-2026!", request=richiesta)
            self.assertEqual(rifiuto.exception.code, "E_TOTP_PASSWORD_NON_VALIDA")

        # Il tentativo che fa scattare il freno risponde col freno (la frase del
        # DB, coi minuti), non con «password sbagliata». ⛔ SENZA il savepoint
        # di `_codice_errore`: e' il BB a doverne avere uno suo, altrimenti il
        # rifiuto annullerebbe il tentativo appena registrato e la password
        # giusta, dopo, passerebbe.
        self.assertEqual(
            self._codice_senza_savepoint(
                lambda: self.servizio.avvia_configurazione(self.user, "Sbagliata-2026!", request=richiesta)
            ),
            "E_UTENTE_BLOCCATO",
        )
        self.assertEqual(
            self._codice_senza_savepoint(
                lambda: self.servizio.avvia_configurazione(self.user, _PASSWORD, request=richiesta)
            ),
            "E_UTENTE_BLOCCATO",
        )
        self.assertEqual(self.servizio.stato(self.user.id)["stato"], "ASSENTE")

    # Scopo: Un operatore costruito dal percorso di produzione, volendo
    #        SUPER_ADMIN. ⛔ Non uno preso dal DB: su un DB senza
    #        amministratori il test si sarebbe saltato, verde senza provare.
    @staticmethod
    def _operatore(etichetta: str, *, super_admin: bool) -> int:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT auth_user_id FROM dbops.fn_pgtap_crea_operatore_umano(%s, %s)",
                [etichetta, super_admin],
            )
            return cur.fetchone()[0]

    # Scopo: Un device attivo per la credenziale del test, scritto da lei.
    def _device_attivo(self) -> None:
        self._agisce(self.user.id)
        self.servizio.avvia_configurazione(self.user, _PASSWORD, request=self.request)
        SecondoFattoreRepository().conferma_device(self.user.id, passo=totp_service.passo_corrente())

    def test_il_super_admin_impone_l_obbligo_e_disattiva_col_motivo(self):
        admin_id = self._operatore("sf admin", super_admin=True)
        self._device_attivo()

        self._agisce(admin_id)
        stato = self.servizio.imposta_obbligo(self.user.id, True)
        self.assertEqual((stato["obbligatorio"], stato["motivo"]), (True, "CREDENZIALE"))
        self.assertTrue(stato["obbligo_sulla_credenziale"])

        # Senza motivo il DB rifiuta, e niente traccia.
        codice = self._codice_errore(lambda: self.servizio.disattiva_da_admin(
            self.user.id, motivo="  ", chi_agisce=admin_id, request=self.request,
        ))
        self.assertEqual(codice, "E_TOTP_MOTIVO_OBBLIGATORIO")
        self.assertEqual(self._tracce(self.user.id), [])

        self.servizio.disattiva_da_admin(
            self.user.id, motivo="telefono perso", chi_agisce=admin_id, request=self.request,
        )
        self.assertEqual(self.servizio.stato(self.user.id)["stato"], "ASSENTE")
        self.assertEqual(
            self._tracce(self.user.id),
            [{"via": "APP", "chi_agisce": admin_id, "motivo": "telefono perso"}],
        )

    # Scopo: Su una credenziale di sistema (l'utente tecnico di un processo)
    #        il SUPER_ADMIN non accende l'obbligo: una macchina non ha un
    #        telefono, e il processo si fermerebbe. Le uscite restano aperte:
    #        spegnere l'obbligo e togliere un device registrato per errore
    #        passano (brief-db-credenziale-verbi-amministratore, D-2).
    def test_su_una_credenziale_di_sistema_l_obbligo_non_si_accende(self):
        admin_id = self._operatore("sf sistema", super_admin=True)
        with connection.cursor() as cur:
            cur.execute("SELECT m.auth_user_id FROM dbops.fn_pgtap_crea_emittente_operatore() m")
            macchina = cur.fetchone()[0]
            cur.execute("SELECT script.fn_categoria_accesso(%s)", [macchina])
            self.assertEqual(cur.fetchone()[0], "SISTEMA", "la credenziale costruita dev'essere di sistema")

        self._agisce(admin_id)
        self.assertEqual(
            self._codice_errore(lambda: self.servizio.imposta_obbligo(macchina, True)),
            "E_CREDENZIALE_DI_SISTEMA",
        )
        self.assertFalse(self.servizio.stato(macchina)["obbligatorio"])
        self.assertFalse(self.servizio.imposta_obbligo(macchina, False)["obbligatorio"])

        # Il device di una macchina esiste solo per errore: lo registra lei,
        # il SUPER_ADMIN lo toglie.
        self._agisce(macchina)
        SecondoFattoreRepository().registra_device(
            macchina, secret_encrypted="segreto-macchina", impronte_recupero=["m1"],
        )
        self._agisce(admin_id)
        stato = self.servizio.disattiva_da_admin(
            macchina, motivo="registrato per errore", chi_agisce=admin_id, request=self.request,
        )
        self.assertEqual(stato["stato"], "ASSENTE")

    def test_chi_non_e_super_admin_non_impone_ne_disattiva(self):
        collega = self._operatore("sf collega", super_admin=False)
        self._device_attivo()

        self._agisce(collega)
        self.assertEqual(
            self._codice_errore(lambda: self.servizio.imposta_obbligo(self.user.id, True)),
            "E_PERMESSO_NEGATO",
        )
        self.assertEqual(
            self._codice_errore(lambda: self.servizio.disattiva_da_admin(
                self.user.id, motivo="telefono perso", chi_agisce=collega, request=self.request,
            )),
            "E_PERMESSO_NEGATO",
        )
        self.assertEqual(self.servizio.stato(self.user.id)["stato"], "ATTIVO")
        self.assertEqual(self._tracce(self.user.id), [])

    # Scopo: D-T3: una disattivazione senza traccia non resta. Se la scrittura
    #        della riga TOTP_DISABILITATO fallisce, il device e' ancora ATTIVO.
    #        ⭐ Sotto la transazione del test l'`atomic` del servizio e' un
    #        savepoint: il suo annullamento si osserva qui.
    def test_senza_traccia_la_disattivazione_si_annulla(self):
        admin_id = self._operatore("sf traccia", super_admin=True)
        self._device_attivo()

        self._agisce(admin_id)
        with patch(
            "apps.core.services.secondo_fattore_service.SessionAuditRepository.log_session_event",
            side_effect=DatabaseError("traccia non scritta"), autospec=True,
        ), self.assertRaises(DatabaseError):
            self.servizio.disattiva_da_admin(
                self.user.id, motivo="telefono perso", chi_agisce=admin_id, request=self.request,
            )
        self.assertEqual(self.servizio.stato(self.user.id)["stato"], "ATTIVO")
