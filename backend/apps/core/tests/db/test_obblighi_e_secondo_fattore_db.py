# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
"""

from __future__ import annotations

import unittest
import uuid

from django.contrib.auth.models import User
from django.db import DatabaseError, connection, transaction

from apps.core.api.cancello_obblighi import (
    OBBLIGO_CAMBIO_PASSWORD,
    OBBLIGO_SECONDO_FATTORE,
    obblighi_pendenti,
)
from apps.core.db.auth_repository import AuthRepository
from apps.core.db.secondo_fattore_repository import SecondoFattoreRepository
from apps.core.services import crypto_service, totp_service
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto


# Scopo: Credenziale fabbricata, senza vesti e senza device.
def _nuova_credenziale() -> User:
    return User.objects.create_user(
        username=f"test_obblighi_{uuid.uuid4().hex[:12]}",
        email="",
        password="Giusta-Per-Il-Test-2026!",
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
