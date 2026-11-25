# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del command `crea_primo_amministratore` (R-DB-K1, passo
#        3j di brief-db-porte-aperte-dalla-sola-guc §4.9.7): il verbo si chiama
#        con l'HASH della password, i due rifiuti che parlano escono come
#        messaggio e non come traceback, il riuso di una credenziale si
#        dichiara (domanda al terminale, o `--riusa-credenziale` senza).
# Note: Repository mockato (SimpleTestCase: nessun accesso al DB). Il binding
#       col DB vero lo prova
#       `anagrafiche/tests/db/test_crea_primo_amministratore_db`.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) test_chiama_il_verbo_con_l_hash
2) test_domicilio_fiscale_e_data_passano
3) test_gia_presente_e_un_messaggio
4) test_altro_rifiuto_esce_col_suo_codice
5) test_da_confermare_confermato_richiama_col_riuso
6) test_da_confermare_non_confermato_si_ferma
7) test_da_confermare_senza_terminale_dice_l_opzione
8) test_riuso_dichiarato_non_chiede
9) test_password_che_non_coincide_non_chiama_il_verbo
10) test_password_debole_non_chiama_il_verbo
11) test_residenza_non_json_non_chiama_il_verbo
12) test_noinput_senza_variabile_si_ferma
13) test_avviso_password_prima_della_domanda
"""
from __future__ import annotations

import contextlib
import io
import os
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError

_MODULO = "apps.anagrafiche.management.commands.crea_primo_amministratore"
_PASSWORD = "Una-Password-Lunga-42!"
_RESIDENZA = '{"indirizzo_libero": "Via Roma 1", "stato_id": 1, "comune_id": 5, "codice_postale_id": 9}'
_BASE = (
    "--cognome", "Rossi", "--nome", "Anna", "--codice-fiscale", "RSSNNA80A41H501X",
    "--sesso", "f", "--email", "anna@esempio.test", "--username", "anna",
    "--residenza", _RESIDENZA,
)
_ESITO = {"auth_user_id": 42, "username": "anna", "credenziale_riusata": False}
_CREDENZIALE = {
    "auth_user_id": 42, "username": "anna.vecchia",
    "vesti": [{"ruolo_applicativo": "OPERATORE", "attivo": False, "soggetto": "Rossi Anna"}],
}


# Scopo: Il rifiuto del verbo come arriva dalla traduzione: la frase e la
#        soluzione del catalogo (`hint`).
def _rifiuto(codice: str, messaggio: str = "rifiutato", hint: str | None = None) -> ServiceError:
    return ServiceError(code=codice, message=messaggio, hint=hint)


class CreaPrimoAmministratoreTests(SimpleTestCase):
    def setUp(self) -> None:
        self.repo = MagicMock()
        self.repo.crea_primo_amministratore.return_value = dict(_ESITO)
        self.repo.get_credenziale_per_email.return_value = dict(_CREDENZIALE)
        self.risposte: list[str] = []
        self.password: list[str] = [_PASSWORD, _PASSWORD]
        for nome, valore in (
            ("AmmSoftwareRepository", MagicMock(return_value=self.repo)),
            ("make_password", MagicMock(side_effect=lambda p: f"hash:{p}")),
            ("chiedi", MagicMock(side_effect=lambda _domanda: self.risposte.pop(0))),
            ("chiedi_password", MagicMock(side_effect=lambda _domanda: self.password.pop(0))),
        ):
            self.enterContext(patch(f"{_MODULO}.{nome}", valore))
        self.enterContext(patch(f"{_MODULO}.transaction.atomic", contextlib.nullcontext))

    # Scopo: Lancia il command e ne restituisce l'uscita.
    def _lancia(self, *argomenti: str) -> str:
        uscita = io.StringIO()
        call_command("crea_primo_amministratore", *_BASE, *argomenti, stdout=uscita)
        return uscita.getvalue()

    # Scopo: Gli argomenti di una chiamata al verbo.
    def _chiamata(self, n: int = 0) -> dict[str, Any]:
        return self.repo.crea_primo_amministratore.call_args_list[n].kwargs

    # 1) Il verbo riceve l'hash, mai la password; la residenza e' l'oggetto.
    def test_chiama_il_verbo_con_l_hash(self) -> None:
        uscita = self._lancia()
        chiamata = self._chiamata()
        self.assertEqual(chiamata["password_hash"], f"hash:{_PASSWORD}")
        self.assertNotIn(_PASSWORD, [v for k, v in chiamata.items() if k != "password_hash"])
        self.assertEqual(chiamata["indirizzo_residenza"]["indirizzo_libero"], "Via Roma 1")
        self.assertIsNone(chiamata["indirizzo_domicilio_fiscale"])
        self.assertIsNone(chiamata["riusa_auth_user_id"])
        self.assertEqual(chiamata["sesso"], "F")
        self.assertIn("Primo amministratore creato: anna (auth_user_id 42)", uscita)

    # 2) Il domicilio fiscale e la data di nascita, se dati, passano.
    def test_domicilio_fiscale_e_data_passano(self) -> None:
        self._lancia(
            "--domicilio-fiscale", '{"indirizzo_dettaglio_id": 7}', "--data-nascita", "1980-01-01",
        )
        chiamata = self._chiamata()
        self.assertEqual(chiamata["indirizzo_domicilio_fiscale"], {"indirizzo_dettaglio_id": 7})
        self.assertEqual(chiamata["data_nascita"], date(1980, 1, 1))

    # 3) Il primo impianto chiuso: un messaggio che dice dove andare. Frase e
    #    soluzione sono quelle del catalogo, non una copia nel comando.
    def test_gia_presente_e_un_messaggio(self) -> None:
        self.repo.crea_primo_amministratore.side_effect = _rifiuto(
            "E_PRIMO_AMMINISTRATORE_GIA_PRESENTE", "Frase del catalogo.", hint="Soluzione del catalogo.",
        )
        with self.assertRaises(CommandError) as ctx:
            self._lancia()
        self.assertEqual(
            str(ctx.exception),
            "Frase del catalogo. Soluzione del catalogo. (E_PRIMO_AMMINISTRATORE_GIA_PRESENTE)",
        )

    # 4) Ogni altro rifiuto esce col suo messaggio e il suo codice.
    def test_altro_rifiuto_esce_col_suo_codice(self) -> None:
        self.repo.crea_primo_amministratore.side_effect = _rifiuto(
            "E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO", "Manca il domicilio fiscale.",
        )
        with self.assertRaises(CommandError) as ctx:
            self._lancia()
        self.assertEqual(
            str(ctx.exception),
            "Manca il domicilio fiscale. (E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO)",
        )

    # 5) L'email e' gia' di una credenziale: la si mostra e, confermato, il
    #    verbo si richiama dichiarando QUELLA credenziale.
    def test_da_confermare_confermato_richiama_col_riuso(self) -> None:
        self.repo.crea_primo_amministratore.side_effect = [
            _rifiuto("E_CREDENZIALE_DA_CONFERMARE"),
            {"auth_user_id": 42, "username": "anna.vecchia", "credenziale_riusata": True},
        ]
        self.risposte = ["s"]
        uscita = self._lancia()
        self.assertEqual(self.repo.crea_primo_amministratore.call_count, 2)
        self.assertIsNone(self._chiamata(0)["riusa_auth_user_id"])
        self.assertEqual(self._chiamata(1)["riusa_auth_user_id"], 42)
        self.assertIn("credenziale 'anna.vecchia'", uscita)
        self.assertIn("OPERATORE spenta", uscita)
        self.assertIn("si entra col suo username e la sua password", uscita)

    # 6) Senza conferma non nasce niente: una chiamata sola.
    def test_da_confermare_non_confermato_si_ferma(self) -> None:
        self.repo.crea_primo_amministratore.side_effect = _rifiuto("E_CREDENZIALE_DA_CONFERMARE")
        self.risposte = ["n"]
        with self.assertRaises(CommandError) as ctx:
            self._lancia()
        self.assertIn("non e' stato confermato", str(ctx.exception))
        self.assertEqual(self.repo.crea_primo_amministratore.call_count, 1)

    # 7) Senza terminale non si chiede: si dice come dichiararlo.
    def test_da_confermare_senza_terminale_dice_l_opzione(self) -> None:
        self.repo.crea_primo_amministratore.side_effect = _rifiuto("E_CREDENZIALE_DA_CONFERMARE")
        with patch.dict(os.environ, {"ZEROERP_PRIMO_AMMINISTRATORE_PASSWORD": _PASSWORD}):
            with self.assertRaises(CommandError) as ctx:
                self._lancia("--noinput")
        self.assertIn("--riusa-credenziale 42", str(ctx.exception))
        self.assertEqual(self.repo.crea_primo_amministratore.call_count, 1)

    # 8) Il riuso dichiarato passa alla prima chiamata, senza domande; un
    #    secondo rifiuto di conferma (un'altra credenziale) e' un messaggio.
    def test_riuso_dichiarato_non_chiede(self) -> None:
        self._lancia("--riusa-credenziale", "42")
        self.assertEqual(self._chiamata()["riusa_auth_user_id"], 42)
        self.repo.crea_primo_amministratore.side_effect = _rifiuto("E_CREDENZIALE_DA_CONFERMARE", "Un'altra.")
        self.password = [_PASSWORD, _PASSWORD]
        with self.assertRaises(CommandError) as ctx:
            self._lancia("--riusa-credenziale", "41")
        self.assertEqual(str(ctx.exception), "Un'altra. (E_CREDENZIALE_DA_CONFERMARE)")

    # 13) Prima di chiedere la password si dice quando non si usa: col riuso
    #     l'account tiene la sua. La frase cambia se il riuso e' gia' dichiarato.
    def test_avviso_password_prima_della_domanda(self) -> None:
        self.assertIn("chiedera' se riusarlo", self._lancia())
        self.password = [_PASSWORD, _PASSWORD]
        self.assertIn("Con --riusa-credenziale l'account tiene la sua password", self._lancia("--riusa-credenziale", "42"))

    # 9) Password e conferma diverse: il verbo non si chiama.
    def test_password_che_non_coincide_non_chiama_il_verbo(self) -> None:
        self.password = [_PASSWORD, _PASSWORD + "x"]
        with self.assertRaises(CommandError) as ctx:
            self._lancia()
        self.assertIn("non coincidono", str(ctx.exception))
        self.repo.crea_primo_amministratore.assert_not_called()

    # 10) Una password che i validatori di Django rifiutano: niente verbo.
    def test_password_debole_non_chiama_il_verbo(self) -> None:
        self.password = ["anna", "anna"]
        with self.assertRaises(CommandError):
            self._lancia()
        self.repo.crea_primo_amministratore.assert_not_called()

    # 11) Una residenza che non e' JSON: niente password chiesta, niente verbo.
    def test_residenza_non_json_non_chiama_il_verbo(self) -> None:
        uscita = io.StringIO()
        argomenti = list(_BASE)
        argomenti[argomenti.index(_RESIDENZA)] = "via Roma 1"
        with self.assertRaises(CommandError) as ctx:
            call_command("crea_primo_amministratore", *argomenti, stdout=uscita)
        self.assertIn("--residenza", str(ctx.exception))
        self.repo.crea_primo_amministratore.assert_not_called()
        self.assertEqual(len(self.password), 2)

    # 12) `--noinput` senza la variabile: si ferma e dice quale.
    def test_noinput_senza_variabile_si_ferma(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ZEROERP_PRIMO_AMMINISTRATORE_PASSWORD", None)
            with self.assertRaises(CommandError) as ctx:
                self._lancia("--noinput")
        self.assertIn("ZEROERP_PRIMO_AMMINISTRATORE_PASSWORD", str(ctx.exception))
        self.repo.crea_primo_amministratore.assert_not_called()
