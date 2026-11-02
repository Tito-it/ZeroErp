# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del command `provision_utenti_sviluppo`
#        (brief-be-utenti-di-sviluppo T-1): l'ambiente che lo ferma, quali
#        password genera e quante volte chiama il verbo, il secondo fattore
#        solo per chi lo deve avere, le righe per env.sh.
# Note: Repository, servizio e utenti mockati (SimpleTestCase: nessun accesso
#       al DB). Il binding col DB vero lo prova
#       `anagrafiche/tests/db/test_provisioning_sviluppo_db`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_ambiente_non_dichiarato_ferma_prima_del_verbo
2) test_produzione_ferma_prima_del_verbo
3) test_tutto_riallineato_una_chiamata_e_nessuna_password
4) test_password_solo_per_le_credenziali_create
5) test_nuove_password_per_tutte
6) test_secondo_fattore_solo_per_chi_lo_deve_avere
7) test_secondo_fattore_gia_attivo_non_stampa_la_chiave
8) test_nomi_delle_variabili
"""
from __future__ import annotations

import contextlib
import io
from typing import Any
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.anagrafiche.management.commands import provision_utenti_sviluppo as cmd

_MODULO = "apps.anagrafiche.management.commands.provision_utenti_sviluppo"


# Scopo: Una riga del verbo.
def _radice(tipo: str, chiave: str, radice_id: str, esito: str, secondo_fattore: bool | None) -> dict[str, Any]:
    return {
        "tipo": tipo, "chiave": chiave, "radice_id": radice_id,
        "esito": esito, "secondo_fattore": secondo_fattore,
    }


class ProvisionUtentiSviluppoTests(SimpleTestCase):
    def setUp(self) -> None:
        self.repo = MagicMock()
        self.repo.ambiente_dichiarato.return_value = "SVILUPPO"
        self.servizio = MagicMock()
        self.servizio.configura_confermato.return_value = {
            "segreto": "SEGRETO", "codici_recupero": ["AAAA-BBBB-CCCC-DDDD"],
        }
        utenti = MagicMock()
        utenti.objects.filter.return_value.values_list.return_value = [
            ("dev.smoke", "dev.smoke@sviluppo.invalid"),
        ]
        auth_repo = MagicMock()
        auth_repo.find_identita_per_ruolo.return_value = [{"id": 7, "attivo": True}]
        for nome, valore in (
            ("DatiDiSviluppoRepository", MagicMock(return_value=self.repo)),
            ("SecondoFattoreService", MagicMock(return_value=self.servizio)),
            ("User", utenti),
            ("AuthRepository", MagicMock(return_value=auth_repo)),
            ("operator_identity_context", MagicMock(return_value=contextlib.nullcontext())),
            ("make_password", MagicMock(side_effect=lambda p: f"hash:{p}")),
        ):
            self.enterContext(patch(f"{_MODULO}.{nome}", valore))
        self.enterContext(patch(f"{_MODULO}.transaction.atomic", contextlib.nullcontext))

    # Scopo: Lancia il command e ne restituisce l'uscita.
    def _lancia(self, *argomenti: str) -> str:
        uscita = io.StringIO()
        call_command("provision_utenti_sviluppo", *argomenti, stdout=uscita)
        return uscita.getvalue()

    def test_ambiente_non_dichiarato_ferma_prima_del_verbo(self):
        self.repo.ambiente_dichiarato.return_value = None
        with self.assertRaisesRegex(CommandError, "non e' dichiarato"):
            self._lancia()
        self.repo.provisiona.assert_not_called()

    def test_produzione_ferma_prima_del_verbo(self):
        self.repo.ambiente_dichiarato.return_value = "PRODUZIONE"
        with self.assertRaisesRegex(CommandError, "PRODUZIONE"):
            self._lancia()
        self.repo.provisiona.assert_not_called()

    def test_tutto_riallineato_una_chiamata_e_nessuna_password(self):
        self.repo.provisiona.return_value = [
            _radice("SOGGETTO", "DEV-EMITTENTE-A", "u-1", "riallineata", None),
            _radice("CREDENZIALE", "dev.lettura", "12", "riallineata", False),
        ]
        uscita = self._lancia()
        self.repo.provisiona.assert_called_once_with({})
        self.assertIn("backend/env.sh resta com'e'", uscita)

    def test_password_solo_per_le_credenziali_create(self):
        self.repo.provisiona.return_value = [
            _radice("CREDENZIALE", "dev.lettura", "12", "creata", False),
            _radice("CREDENZIALE", "dev.emittente", "13", "riallineata", False),
        ]
        uscita = self._lancia()
        self.assertEqual(self.repo.provisiona.call_count, 2)
        hash_dati = self.repo.provisiona.call_args_list[1].args[0]
        self.assertEqual(set(hash_dati), {"dev.lettura"})
        self.assertIn("export DEV_LETTURA_PASSWORD=", uscita)
        self.assertNotIn("DEV_EMITTENTE_PASSWORD", uscita)

    def test_nuove_password_per_tutte(self):
        self.repo.provisiona.return_value = [
            _radice("CREDENZIALE", "dev.lettura", "12", "riallineata", False),
            _radice("CREDENZIALE", "dev.emittente", "13", "riallineata", False),
        ]
        self._lancia("--nuove-password")
        hash_dati = self.repo.provisiona.call_args_list[1].args[0]
        self.assertEqual(set(hash_dati), {"dev.lettura", "dev.emittente"})
        self.assertTrue(all(h.startswith("hash:") for h in hash_dati.values()))

    def test_secondo_fattore_solo_per_chi_lo_deve_avere(self):
        self.repo.provisiona.return_value = [
            _radice("CREDENZIALE", "dev.smoke", "11", "creata", True),
            _radice("CREDENZIALE", "dev.lettura", "12", "creata", False),
        ]
        uscita = self._lancia()
        self.assertEqual(self.servizio.configura_confermato.call_count, 1)
        self.assertIn("export SMOKE_USER='dev.smoke'", uscita)
        self.assertIn("export SMOKE_PASSWORD=", uscita)
        self.assertIn("export SMOKE_TOTP_SECRET='SEGRETO'", uscita)
        self.assertIn("AAAA-BBBB-CCCC-DDDD", uscita)

    def test_secondo_fattore_gia_attivo_non_stampa_la_chiave(self):
        self.servizio.configura_confermato.return_value = None
        self.repo.provisiona.return_value = [
            _radice("CREDENZIALE", "dev.smoke", "11", "riallineata", True),
        ]
        uscita = self._lancia()
        self.assertIn("gia' attivo", uscita)
        self.assertNotIn("SMOKE_TOTP_SECRET", uscita)

    def test_nomi_delle_variabili(self):
        self.assertEqual(cmd.variabile_env("dev.smoke", "PASSWORD"), "SMOKE_PASSWORD")
        self.assertEqual(cmd.variabile_env("dev.smoke", "TOTP_SECRET"), "SMOKE_TOTP_SECRET")
        self.assertEqual(cmd.variabile_env("dev.portale1", "PASSWORD"), "DEV_PORTALE1_PASSWORD")
