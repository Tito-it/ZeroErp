# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: `manage.py ricifra_campi_cifrati` sul DATABASE VERO: la rotazione
#        delle chiavi e la migrazione dalla chiave derivata dalla SECRET_KEY
#        (brief-be-fe-sicurezza-header-token-mfa §3.5).
# Note: ⚠️ Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI). Il mondo si COSTRUISCE
#       (regola zero): l'account email lo crea il test, con un token della
#       chiave che il caso vuole; gli account gia' presenti si neutralizzano.
#       Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) RicifraCampiCifratiDbTests.test_rotazione_porta_il_token_sulla_chiave_nuova
2) RicifraCampiCifratiDbTests.test_migrazione_dalla_chiave_derivata_dalla_secret_key
3) RicifraCampiCifratiDbTests.test_token_illeggibile_annulla_tutto
4) RicifraCampiCifratiDbTests.test_dry_run_non_scrive
5) RicifraCampiCifratiDbTests.test_segreto_totp_ruota_attraverso_il_verbo — tabella chiusa all'app
6) RicifraCampiCifratiDbTests.test_segreto_totp_cambiato_nel_frattempo_resta
"""
from __future__ import annotations

import base64
import hashlib
import io
import unittest
import uuid

from cryptography.fernet import Fernet
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.test import override_settings

from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto

_NUOVA = Fernet.generate_key().decode()
_VECCHIA = Fernet.generate_key().decode()
_SECRET_KEY = "secret-key-di-prova-per-la-migrazione"


# Scopo: Inserisce un account email con il token dato, ritorna l'id.
def _account(cur, codice: str, token: str) -> int:
    cur.execute(
        """
        INSERT INTO config.email_account
            (codice, codice_interno, descrizione, smtp_host, smtp_port,
             smtp_use_tls, smtp_use_ssl, smtp_username, smtp_password_encrypted,
             email_from, attivo)
        VALUES (%s, %s, 'ricifra', 'smtp.invalid', 587, true, false, 'u', %s,
                'ricifra@esempio.test', true)
        RETURNING id
        """,
        [codice, codice, token],
    )
    return cur.fetchone()[0]


# Scopo: ⛔ Il comando percorre TUTTA la tabella: gli account che il DB
#        provvisto ha gia' (token di altre chiavi) farebbero fallire ogni caso.
#        Dentro la transazione annullata si riscrivono con un token della
#        chiave nuova, cosi' il test vede solo il mondo che costruisce.
def _neutralizza_esistenti(cur) -> None:
    cur.execute(
        "UPDATE config.email_account SET smtp_password_encrypted = %s",
        [Fernet(_NUOVA).encrypt(b"esistente").decode()],
    )
    # I device del secondo fattore: tabella chiusa all'app, si passa dal verbo,
    # che per sostituire vuole solo il token attuale (non serve saperlo aprire).
    cur.execute("SELECT auth_user_id, secret_encrypted FROM config.auth_totp_device")
    for auth_user_id, token in cur.fetchall():
        cur.execute(
            "SELECT script.fn_totp_ricifra_segreto(%s, %s, %s)",
            [auth_user_id, token, Fernet(_NUOVA).encrypt(b"esistente").decode()],
        )


# Scopo: Un device del secondo fattore col token dato, scritto dai verbi come
#        la credenziale stessa (la tabella e' chiusa all'app). Ritorna l'id.
def _device(cur, token: str) -> int:
    from django.contrib.auth.models import User

    from apps.core.db.secondo_fattore_repository import SecondoFattoreRepository

    uid = User.objects.create_user(username=f"ricifra_{uuid.uuid4().hex[:12]}", password=None).id
    cur.execute("SELECT set_config('app.current_user_id', %s, true)", [str(uid)])
    SecondoFattoreRepository().registra_device(uid, secret_encrypted=token, impronte_recupero=["a", "b"])
    cur.execute("SELECT set_config('app.current_user_id', '', true)")
    return uid


# Scopo: Il token salvato nel device.
def _token_device(cur, auth_user_id: int) -> str:
    cur.execute(
        "SELECT secret_encrypted FROM config.auth_totp_device WHERE auth_user_id = %s",
        [auth_user_id],
    )
    return cur.fetchone()[0]


# Scopo: Il token salvato per l'account.
def _token(cur, account_id: int) -> str:
    cur.execute(
        "SELECT smtp_password_encrypted FROM config.email_account WHERE id = %s",
        [account_id],
    )
    return cur.fetchone()[0]


class RicifraCampiCifratiDbTests(unittest.TestCase):
    def setUp(self):
        richiedi_db_provvisto()
        # `unittest.TestCase` (come gli altri test DB): il decoratore di classe
        # vale solo per SimpleTestCase, quindi l'override si apre a mano.
        chiavi = override_settings(FIELD_ENCRYPTION_KEYS=[_NUOVA, _VECCHIA], SECRET_KEY=_SECRET_KEY)
        chiavi.enable()
        self.addCleanup(chiavi.disable)

    # 1. Rotazione: un token della chiave vecchia, dopo il comando, si apre con
    #    la sola chiave nuova.
    def test_rotazione_porta_il_token_sulla_chiave_nuova(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _neutralizza_esistenti(cur)
                account_id = _account(cur, "RICIFRA1", Fernet(_VECCHIA).encrypt(b"pw").decode())
                call_command("ricifra_campi_cifrati", stdout=io.StringIO())
                self.assertEqual(Fernet(_NUOVA).decrypt(_token(cur, account_id).encode()), b"pw")
                raise Annulla
        except Annulla:
            pass

    # 2. ⭐ Migrazione: il token com'era prima del 2026-09-28 (chiave derivata
    #    dalla SECRET_KEY) si apre SOLO con l'opzione, e ne esce sulla chiave nuova.
    def test_migrazione_dalla_chiave_derivata_dalla_secret_key(self):
        derivata = base64.urlsafe_b64encode(hashlib.sha256(_SECRET_KEY.encode()).digest())
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _neutralizza_esistenti(cur)
                account_id = _account(cur, "RICIFRA2", Fernet(derivata).encrypt(b"legacy").decode())
                with self.assertRaises(CommandError):
                    call_command("ricifra_campi_cifrati", stdout=io.StringIO())
                call_command(
                    "ricifra_campi_cifrati", "--anche-chiave-da-secret-key", stdout=io.StringIO(),
                )
                self.assertEqual(
                    Fernet(_NUOVA).decrypt(_token(cur, account_id).encode()), b"legacy",
                )
                raise Annulla
        except Annulla:
            pass

    # 3. ⛔ Tutto o niente: un token illeggibile fa fallire il comando, e
    #    nemmeno l'account leggibile viene riscritto.
    def test_token_illeggibile_annulla_tutto(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _neutralizza_esistenti(cur)
                buono = Fernet(_VECCHIA).encrypt(b"buono").decode()
                id_buono = _account(cur, "RICIFRA3A", buono)
                id_rotto = _account(
                    cur, "RICIFRA3B", Fernet(Fernet.generate_key()).encrypt(b"x").decode(),
                )
                with self.assertRaises(CommandError) as ctx:
                    call_command("ricifra_campi_cifrati", stdout=io.StringIO())
                self.assertIn(f"id={id_rotto}", str(ctx.exception))
                self.assertEqual(_token(cur, id_buono), buono)
                raise Annulla
        except Annulla:
            pass

    # 4. Il dry-run apre i token ma non scrive.
    def test_dry_run_non_scrive(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _neutralizza_esistenti(cur)
                vecchio = Fernet(_VECCHIA).encrypt(b"pw").decode()
                account_id = _account(cur, "RICIFRA4", vecchio)
                call_command("ricifra_campi_cifrati", "--dry-run", stdout=io.StringIO())
                self.assertEqual(_token(cur, account_id), vecchio)
                raise Annulla
        except Annulla:
            pass

    # 5. Il segreto del secondo fattore ruota come gli altri, ma la tabella e'
    #    chiusa all'app: il comando la legge senza FOR UPDATE e la riscrive col
    #    verbo. Il device resta nel suo stato (qui DA_CONFERMARE).
    def test_segreto_totp_ruota_attraverso_il_verbo(self):
        try:
            with transaction.atomic(), connection.cursor() as cur:
                _neutralizza_esistenti(cur)
                uid = _device(cur, Fernet(_VECCHIA).encrypt(b"segreto").decode())
                out = io.StringIO()
                call_command("ricifra_campi_cifrati", stdout=out)
                self.assertEqual(Fernet(_NUOVA).decrypt(_token_device(cur, uid).encode()), b"segreto")
                cur.execute("SELECT stato FROM script.fn_get_totp_device(%s)", [uid])
                self.assertEqual(cur.fetchone()[0], "DA_CONFERMARE")
                self.assertIn("config.auth_totp_device.secret_encrypted", out.getvalue())
                raise Annulla
        except Annulla:
            pass

    # 6. Il segreto cambiato fra la lettura e la scrittura (device
    #    riconfigurato): il verbo non lo tocca e il comando lo conta, non e' un
    #    errore. Si prova sulla riscrittura, con un token atteso non piu' vero.
    def test_segreto_totp_cambiato_nel_frattempo_resta(self):
        from apps.core.management.commands.ricifra_campi_cifrati import _riscrivi
        from apps.core.services.crypto_service import CAMPI_CIFRATI

        campo = next(c for c in CAMPI_CIFRATI if c.tabella == "config.auth_totp_device")
        try:
            with transaction.atomic(), connection.cursor() as cur:
                attuale = Fernet(_NUOVA).encrypt(b"riconfigurato").decode()
                uid = _device(cur, attuale)
                letto_prima = Fernet(_VECCHIA).encrypt(b"vecchio").decode()
                self.assertFalse(
                    _riscrivi(campo, uid, letto_prima, Fernet(_NUOVA).encrypt(b"vecchio").decode())
                )
                self.assertEqual(_token_device(cur, uid), attuale)
                raise Annulla
        except Annulla:
            pass
