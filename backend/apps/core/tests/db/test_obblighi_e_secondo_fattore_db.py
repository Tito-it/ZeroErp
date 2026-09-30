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
"""

from __future__ import annotations

import unittest
import uuid

from django.contrib.auth.models import User
from django.db import transaction

from apps.core.api.cancello_obblighi import OBBLIGO_CAMBIO_PASSWORD, obblighi_pendenti
from apps.core.db.auth_repository import AuthRepository
from apps.core.tests.db_e2e import richiedi_db_provvisto


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
        self._atomic = transaction.atomic()
        self._atomic.__enter__()

    def tearDown(self) -> None:
        transaction.set_rollback(True)
        self._atomic.__exit__(None, None, None)


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
