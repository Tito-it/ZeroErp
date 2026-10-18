# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command del PROVISIONING DI SVILUPPO: crea, o rimette a
#        posto, gli utenti `dev.*` e i loro dati di prova chiamando il verbo
#        del DB, da' la password a chi non l'ha, configura il secondo fattore
#        di chi lo deve avere e stampa le righe da mettere in `backend/env.sh`.
# Note: Brief brief-be-utenti-di-sviluppo T-1; lato DB
#       brief-db-processi-accensione-per-ambiente §5-ter.3.
#
#       ⭐ CHI DECIDE CHE COSA. L'elenco di utenti e soggetti, le etichette e il
#       rifiuto in PRODUZIONE sono del verbo `anagrafiche.fn_provisiona_dati_di_sviluppo`:
#       il command lo chiama e basta. Qui stanno solo le cose che il DB non sa
#       fare: l'hash Django delle password e il secondo fattore (il DB non
#       verifica codici).
#
#       ⭐ L'AMBIENTE si legge a ogni corsa, senza cache. Non dichiarato o
#       PRODUZIONE: il command si ferma e dice perche'. Il rifiuto vero resta
#       del verbo; qui lo si anticipa per un messaggio chiaro.
#
#       ⭐ LE PASSWORD. Il verbo riceve gli hash per username; chi non ne riceve
#       uno tiene la sua (alla nascita: nessuna password utilizzabile). Il
#       command la genera per le credenziali appena CREATE, e per tutte con
#       `--nuove-password`. L'elenco delle credenziali lo sa solo il verbo, quindi
#       lo si chiama due volte nella stessa transazione: la prima crea o
#       riallinea, la seconda porta le password nuove. Il verbo e' idempotente.
#
#       ⭐ IL SECONDO FATTORE lo configura `SecondoFattoreService`, gia'
#       confermato, dentro il contesto della credenziale (il DB vuole che agisca
#       lei). Un device gia' attivo non si tocca: la chiave buona e' quella in
#       `env.sh`. Tutto in una transazione: o il giro intero, o niente.
# ------------------------------------------------------------

from __future__ import annotations

import secrets
from typing import Any

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import CommandError, CommandParser
from django.db import transaction

from apps.anagrafiche.db.dati_di_sviluppo_repository import DatiDiSviluppoRepository, RadiceDiProva
from apps.core.db.auth_repository import AuthRepository
from apps.core.management.comando_aziendale import ComandoAziendale
from apps.core.services.coda_lavori.context import operator_identity_context
from apps.core.services.secondo_fattore_service import SecondoFattoreService

# I valori di `dbops.installazione.ambiente` e dell'uscita del verbo.
AMBIENTE_SVILUPPO = "SVILUPPO"
TIPO_CREDENZIALE = "CREDENZIALE"
ESITO_CREATA = "creata"

# L'utente degli smoke (brief-be-utenti-di-sviluppo T-2): le sue tre variabili
# sono quelle che `_smoke_auth.sh` legge.
UTENTE_SMOKE = "dev.smoke"
PREFISSO_SVILUPPO = "dev."

# Il secondo fattore lo configura chi agisce sulla propria veste OPERATORE.
VESTE_OPERATORE = "OPERATORE"


# Scopo: Una password nuova, casuale: caratteri sicuri dentro gli apici
#        singoli della shell (`token_urlsafe`: lettere, cifre, `-` e `_`).
def genera_password() -> str:
    return secrets.token_urlsafe(18)


# Scopo: Il nome della variabile di `env.sh` che porta un segreto di un
#        utente di sviluppo (`PASSWORD` o `TOTP_SECRET`): `dev.lettura` →
#        `DEV_LETTURA_PASSWORD`. Quelle dell'utente degli smoke sono
#        `SMOKE_PASSWORD` e `SMOKE_TOTP_SECRET`, che legge `_smoke_auth.sh`.
def variabile_env(username: str, cosa: str) -> str:
    if username == UTENTE_SMOKE:
        return f"SMOKE_{cosa}"
    nome = username.removeprefix(PREFISSO_SVILUPPO).upper().replace(".", "_")
    return f"DEV_{nome}_{cosa}"


class Command(ComandoAziendale):
    help = (
        "Provisioning di sviluppo: crea o rimette a posto gli utenti dev.* e i loro dati di "
        "prova (verbo del DB, solo su un'installazione SVILUPPO) e stampa le righe per env.sh."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--nuove-password", action="store_true",
            help="Password nuove per TUTTI gli utenti di sviluppo (di default solo per quelli appena creati).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        repo = DatiDiSviluppoRepository()
        self._richiedi_sviluppo(repo.ambiente_dichiarato())

        with transaction.atomic():
            radici = repo.provisiona({})
            credenziali = [r for r in radici if r["tipo"] == TIPO_CREDENZIALE]
            password = {
                r["chiave"]: genera_password()
                for r in credenziali
                if options["nuove_password"] or r["esito"] == ESITO_CREATA
            }
            if password:
                repo.provisiona({u: make_password(p) for u, p in password.items()})
            secondi_fattori = {
                r["chiave"]: self._configura_secondo_fattore(int(r["radice_id"]))
                for r in credenziali
                if r["secondo_fattore"]
            }

        self._stampa(radici, password, secondi_fattori)

    # Scopo: Si ferma, dicendo perche', se l'installazione non e' dichiarata
    #        SVILUPPO.
    def _richiedi_sviluppo(self, ambiente: str | None) -> None:
        if ambiente is None:
            raise CommandError(
                "L'ambiente di questa installazione non e' dichiarato: lo scrive la fase post di "
                "scripts/sql/provision_zeroerp.sql con -v ambiente=SVILUPPO (installazione.md)."
            )
        if ambiente != AMBIENTE_SVILUPPO:
            raise CommandError(
                f"Questa e' un'installazione {ambiente}: gli utenti e i dati di sviluppo non si "
                "creano qui (E_DATI_DI_SVILUPPO_IN_PRODUZIONE)."
            )

    # Scopo: Il secondo fattore della credenziale, gia' confermato, dentro il
    #        contesto della sua veste OPERATORE. None se era gia' attivo.
    def _configura_secondo_fattore(self, auth_user_id: int) -> dict[str, Any] | None:
        user = User.objects.get(pk=auth_user_id)
        vesti = [
            v for v in AuthRepository().find_identita_per_ruolo(auth_user_id, VESTE_OPERATORE)
            if v["attivo"]
        ]
        if not vesti:
            raise CommandError(
                f"{user.username}: deve avere il secondo fattore ma non ha una veste OPERATORE attiva."
            )
        with operator_identity_context(auth_user_id, username=user.username, identita_id=vesti[0]["id"]):
            return SecondoFattoreService().configura_confermato(user)

    # Scopo: Il resoconto della corsa e, in fondo, le righe per `env.sh`: solo
    #        quelle nuove, cioe' le password e la chiave date in questa corsa.
    def _stampa(
        self,
        radici: list[RadiceDiProva],
        password: dict[str, str],
        secondi_fattori: dict[str, dict[str, Any] | None],
    ) -> None:
        email = dict(
            User.objects.filter(
                pk__in=[int(r["radice_id"]) for r in radici if r["tipo"] == TIPO_CREDENZIALE],
            ).values_list("username", "email")
        )
        self.stdout.write(f"Provisioning di sviluppo: {len(radici)} radici.")
        for r in radici:
            riga = f"  {r['tipo']:<12} {r['chiave']:<18} {r['esito']:<12}"
            if r["tipo"] == TIPO_CREDENZIALE:
                riga += f" {email.get(r['chiave'], '')}"
                if r["chiave"] in password:
                    riga += "  password nuova"
                if r["secondo_fattore"]:
                    riga += "  secondo fattore " + (
                        "configurato" if secondi_fattori.get(r["chiave"]) else "gia' attivo"
                    )
            self.stdout.write(riga)

        righe_env: list[str] = []
        if UTENTE_SMOKE in password or secondi_fattori.get(UTENTE_SMOKE):
            righe_env.append(f"export SMOKE_USER='{UTENTE_SMOKE}'")
        for username, pwd in password.items():
            righe_env.append(f"export {variabile_env(username, 'PASSWORD')}='{pwd}'")
        for username, fattore in secondi_fattori.items():
            if fattore is None:
                continue
            righe_env.append(f"export {variabile_env(username, 'TOTP_SECRET')}='{fattore['segreto']}'")
            righe_env.append(f"# codici di recupero di {username}: " + " ".join(fattore["codici_recupero"]))

        self.stdout.write("")
        if not righe_env:
            self.stdout.write("Nessuna password ne' chiave nuova: backend/env.sh resta com'e'.")
            return
        self.stdout.write("# --- Da mettere in backend/env.sh (sostituiscono le righe con lo stesso nome) ---")
        for riga in righe_env:
            self.stdout.write(riga)
