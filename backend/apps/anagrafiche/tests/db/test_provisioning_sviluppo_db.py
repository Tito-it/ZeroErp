# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `manage.py provision_utenti_sviluppo` sul DATABASE VERO, e la lista
#        Operatori che nasconde gli utenti di prova (brief-be-utenti-di-sviluppo
#        T-1 e T-4). I mock non vedono il binding col verbo
#        `anagrafiche.fn_provisiona_dati_di_sviluppo` (colonne, jsonb degli
#        hash), la conferma del secondo fattore sotto `fn_guard_utente_stesso`
#        ne' il JOIN dell'etichetta nella lista.
# Note: ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Tutto in una
#       transazione ANNULLATA: il verbo crea (o riallinea, se il database li ha
#       gia') gli utenti e i dati di prova, e alla fine non resta niente.
#       ⚠️ Il ramo PRODUZIONE non si prova qui: l'ambiente e' immutabile e la
#       CI e' SVILUPPO. Lo provano il pgTAP del verbo (sui valori) e il test
#       unitario del command. Su un database non SVILUPPO il test si dichiara
#       saltato, non verde.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) ProvisioningSviluppoDbTests.test_il_command_da_password_e_secondo_fattore — le password
   stampate aprono le credenziali, il secondo fattore di dev.smoke e' attivo con la chiave stampata
2) ProvisioningSviluppoDbTests.test_la_lista_operatori_nasconde_gli_utenti_di_prova — e li
   mostra, col segno `di_prova`, solo a chi li chiede
"""
from __future__ import annotations

import io
import re
import unittest

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection

from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.anagrafiche.db.dati_di_sviluppo_repository import DatiDiSviluppoRepository
from apps.core.services import crypto_service
from apps.core.services.secondo_fattore_service import SecondoFattoreService
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto

_RIGA_ENV = re.compile(r"^export (\w+)='([^']*)'$", re.MULTILINE)


class ProvisioningSviluppoDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()
        if DatiDiSviluppoRepository().ambiente_dichiarato() != "SVILUPPO":
            raise unittest.SkipTest(
                "Installazione non dichiarata SVILUPPO: il verbo del provisioning "
                "non parte, e il ramo PRODUZIONE lo prova il pgTAP sui valori."
            )

    def setUp(self) -> None:
        apri_transazione_annullata(self)

    # Scopo: Lancia il command con password nuove per tutti e ne restituisce
    #        le righe `export` stampate per env.sh.
    def _provisiona(self) -> dict[str, str]:
        uscita = io.StringIO()
        call_command("provision_utenti_sviluppo", "--nuove-password", stdout=uscita)
        return dict(_RIGA_ENV.findall(uscita.getvalue()))

    # Scopo: Gli username delle credenziali etichettate di prova.
    @staticmethod
    def _credenziali_di_prova() -> set[str]:
        with connection.cursor() as cur:
            cur.execute("SELECT chiave FROM dbops.credenziali_di_prova")
            return {r[0] for r in cur.fetchall()}

    def test_il_command_da_password_e_secondo_fattore(self):
        env = self._provisiona()
        self.assertIn("dev.smoke", self._credenziali_di_prova())
        self.assertEqual(env["SMOKE_USER"], "dev.smoke")

        # Le password stampate sono quelle che il verbo ha scritto.
        smoke = User.objects.get(username="dev.smoke")
        self.assertTrue(smoke.check_password(env["SMOKE_PASSWORD"]))
        lettura = User.objects.get(username="dev.lettura")
        self.assertTrue(lettura.check_password(env["DEV_LETTURA_PASSWORD"]))

        # Il secondo fattore di dev.smoke e' attivo; se l'ha configurato questa
        # corsa, la chiave stampata e' quella scritta.
        device = SecondoFattoreService().device(smoke.id)
        self.assertEqual(device["stato"], "ATTIVO")
        if "SMOKE_TOTP_SECRET" in env:
            self.assertEqual(crypto_service.decrypt(device["secret_encrypted"]), env["SMOKE_TOTP_SECRET"])

    def test_la_lista_operatori_nasconde_gli_utenti_di_prova(self):
        self._provisiona()
        di_prova = self._credenziali_di_prova()
        repo = AmmSoftwareRepository()

        righe, totale = repo.list_operatori(search="dev.", limit=200)
        self.assertFalse({r["username"] for r in righe} & di_prova)
        self.assertEqual(totale, len(righe))

        righe, _ = repo.list_operatori(search="dev.", includi_di_prova=True, limit=200)
        per_nome = {r["username"]: r for r in righe}
        self.assertIn("dev.smoke", per_nome)
        self.assertTrue(per_nome["dev.smoke"]["di_prova"])
        self.assertTrue(all(r["di_prova"] == (r["username"] in di_prova) for r in righe))
