# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Management command del PRIMO IMPIANTO: crea il primo SUPER_ADMIN di
#        un'installazione nuova, che entra subito, chiamando il verbo DB
#        `anagrafiche.fn_crea_primo_amministratore`. Si lancia una volta, dopo
#        l'installazione, e lo lancia la persona che diventera'
#        amministratore: la password la sceglie lei. Prende il posto di
#        `createsuperuser`, che crea un utente Django senza veste e senza
#        legame, cioe' un account che nel modello non e' nessuno.
# Note: R-DB-K1 (D-K7 b), passo 3j di brief-db-porte-aperte-dalla-sola-guc
#       §4.9.7.
#
#       ⭐ CHI DECIDE CHE COSA. Se il primo impianto e' ancora aperto, la
#       qualifica, il soggetto, gli indirizzi obbligatori, il riuso di una
#       credenziale e la veste accesa sono del verbo: il command lo chiama e
#       basta. Qui stanno solo le cose che il DB non sa fare: chiedere la
#       password, validarla coi validatori di Django (BB
#       `valida_nuova_password`) e calcolarne l'hash.
#
#       ⭐ I DUE RIFIUTI CHE PARLANO, come messaggio e mai come traceback:
#       - `E_PRIMO_AMMINISTRATORE_GIA_PRESENTE`: il primo impianto e' chiuso;
#       - `E_CREDENZIALE_DA_CONFERMARE`: l'email e' gia' di una credenziale
#         (chi ha seguito il playbook vecchio l'ha creata con
#         `createsuperuser`). Si mostra quale, e il riuso lo si DICHIARA:
#         confermato, il verbo si richiama con `p_riusa_auth_user_id`; senza
#         terminale (`--noinput`) lo si dichiara con `--riusa-credenziale`.
#       Ogni altro rifiuto del verbo esce col suo messaggio e il suo codice.
#
#       ⚠️ Gli indirizzi obbligatori li giudicano guard DIFFERITI: il rifiuto
#       arriva al COMMIT. Per questo la traduzione degli errori avvolge la
#       transazione intera, non solo la chiamata.
# ------------------------------------------------------------

from __future__ import annotations

import getpass
import json
import os
from datetime import date
from typing import Any

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import CommandError, CommandParser
from django.db import transaction

from apps.amm_software.db.amm_software_repository import AmmSoftwareRepository
from apps.anagrafiche.services.soggetti_service import indirizzo_per_madre
from apps.core.management.comando_aziendale import ComandoAziendale
from apps.core.services.auth_helpers import valida_nuova_password
from apps.core.services.payload_helpers import translate_db_errors
from apps.core.services.service_errors import E_VALIDATION_INPUT, ServiceError

E_DA_CONFERMARE = "E_CREDENZIALE_DA_CONFERMARE"

# La password senza terminale (`--noinput`): da una variabile d'ambiente, mai
# da un argomento, che resterebbe nella cronologia della shell e in `ps`.
ENV_PASSWORD = "ZEROERP_PRIMO_AMMINISTRATORE_PASSWORD"  # noqa: S105 — il NOME della variabile, non una password

# Le due domande al terminale, a livello di modulo perche' i test le
# sostituiscano senza toccare `builtins`.
chiedi = input
chiedi_password = getpass.getpass


# Scopo: Un indirizzo dall'argomento JSON: un oggetto nella forma di
#        `fn_crea_indirizzo_soggetto`, senza il tipo. La forma la ripulisce il
#        BB delle madri (`indirizzo_per_madre`: vuoti tolti, via richiesta se
#        non e' libero ne' un dettaglio); il resto lo giudica il DB.
def indirizzo_da_argomento(testo: str, *, opzione: str) -> dict[str, Any]:
    try:
        valore = json.loads(testo)
    except json.JSONDecodeError as exc:
        raise CommandError(f"{opzione}: non e' un JSON valido ({exc.msg}).") from exc
    try:
        return indirizzo_per_madre(valore)
    except ServiceError as exc:
        raise CommandError(f"{opzione}: {exc.message}") from exc


class Command(ComandoAziendale):
    help = (
        "Primo impianto: crea il primo SUPER_ADMIN di un'installazione nuova, con la veste "
        "accesa (verbo del DB anagrafiche.fn_crea_primo_amministratore). Si apre solo finche' "
        "nessun accesso ha mai avuto il profilo SUPER_ADMIN."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--cognome", required=True)
        parser.add_argument("--nome", required=True)
        parser.add_argument("--codice-fiscale", required=True)
        parser.add_argument("--sesso", required=True, help="M, F o X.")
        parser.add_argument("--email", required=True)
        parser.add_argument("--username", required=True)
        parser.add_argument(
            "--residenza", required=True,
            help=(
                "La residenza, un oggetto JSON nella forma di anagrafiche.fn_crea_indirizzo_soggetto "
                "senza il tipo: libero ({\"indirizzo_libero\": …, \"stato_id\": …, \"comune_id\": …, "
                "\"codice_postale_id\": …}) o una via da risolvere."
            ),
        )
        parser.add_argument(
            "--domicilio-fiscale",
            help="Il domicilio fiscale, nella stessa forma. Se manca e' la residenza.",
        )
        parser.add_argument("--data-nascita", help="AAAA-MM-GG.")
        parser.add_argument("--comune-nascita-id", type=int)
        parser.add_argument(
            "--riusa-credenziale", type=int, metavar="AUTH_USER_ID",
            help=(
                "Riusa la credenziale che ha gia' questa email (quella che il comando mostra): "
                "username e password restano i suoi."
            ),
        )
        parser.add_argument(
            "--noinput", action="store_true",
            help=f"Nessuna domanda al terminale: la password da {ENV_PASSWORD}.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        residenza = indirizzo_da_argomento(options["residenza"], opzione="--residenza")
        domicilio = (
            indirizzo_da_argomento(options["domicilio_fiscale"], opzione="--domicilio-fiscale")
            if options.get("domicilio_fiscale") else None
        )
        data_nascita = self._data(options.get("data_nascita"))
        password = self._password(options)

        campi: dict[str, Any] = {
            "cognome": options["cognome"],
            "nome": options["nome"],
            "codice_fiscale": options["codice_fiscale"],
            "sesso": options["sesso"].strip().upper(),
            "email": options["email"],
            "username": options["username"],
            "password_hash": make_password(password),
            "indirizzo_residenza": residenza,
            "indirizzo_domicilio_fiscale": domicilio,
            "data_nascita": data_nascita,
            "comune_nascita_id": options.get("comune_nascita_id"),
        }
        riusa = options.get("riusa_credenziale")
        try:
            esito = self._crea(campi, riusa)
        except ServiceError as exc:
            if exc.code != E_DA_CONFERMARE or riusa is not None:
                raise self._rifiuto(exc) from exc
            riusa = self._conferma_riuso(options["email"], noinput=options["noinput"])
            try:
                esito = self._crea(campi, riusa)
            except ServiceError as exc2:
                raise self._rifiuto(exc2) from exc2

        self.stdout.write(self.style.SUCCESS(
            f"Primo amministratore creato: {esito['username']} (auth_user_id {esito['auth_user_id']})."
        ))
        if esito["credenziale_riusata"]:
            self.stdout.write(
                "La credenziale era gia' esistente: si entra col suo username e la sua password."
            )

    # Scopo: Una chiamata al verbo, in una transazione sua: i guard differiti
    #        parlano al COMMIT, e la traduzione li prende anche li'.
    def _crea(self, campi: dict[str, Any], riusa: int | None) -> dict[str, Any]:
        with translate_db_errors(
            context={"op": "crea_primo_amministratore"},
            fallback_code=E_VALIDATION_INPUT,
            fallback_message="Creazione del primo amministratore non riuscita.",
        ):
            with transaction.atomic():
                return AmmSoftwareRepository().crea_primo_amministratore(
                    **campi, riusa_auth_user_id=riusa,
                )

    # Scopo: Il rifiuto del verbo come messaggio: la frase e la soluzione del
    #        catalogo (`hint`, la colonna `soluzione` di `messaggi_errore`), poi
    #        il codice. Il primo impianto chiuso dice cosi' anche dove andare
    #        («li crea un SUPER_ADMIN, con l'invito»).
    # ⛔ Nessuna frase scritta qui per un codice: la sede del testo e' il
    #    catalogo, e una copia nel comando diverge alla prima correzione.
    @staticmethod
    def _rifiuto(exc: ServiceError) -> CommandError:
        parti = [exc.message, exc.hint, f"({exc.code})"]
        return CommandError(" ".join(p for p in parti if p))

    # Scopo: L'email e' gia' di una credenziale: la mostra (la lettura e' la
    #        stessa del rifiuto, `script.fn_get_credenziale_per_email`) e chiede
    #        se riusarla. Ritorna l'id dichiarato; senza conferma si ferma.
    def _conferma_riuso(self, email: str, *, noinput: bool) -> int:
        credenziale = AmmSoftwareRepository().get_credenziale_per_email(email)
        if credenziale is None:
            raise CommandError(
                f"Il database chiede di confermare una credenziale con l'email {email}, ma non la "
                f"trova piu'. ({E_DA_CONFERMARE})"
            )
        vesti = ", ".join(
            f"{v['ruolo_applicativo']} {'accesa' if v['attivo'] else 'spenta'}"
            for v in credenziale["vesti"]
        ) or "nessuna"
        descrizione = (
            f"L'email {email} e' gia' della credenziale '{credenziale['username']}' "
            f"(auth_user_id {credenziale['auth_user_id']}, vesti: {vesti})."
        )
        if noinput:
            raise CommandError(
                f"{descrizione} Per riusarla, rilancia con --riusa-credenziale "
                f"{credenziale['auth_user_id']}: username e password restano i suoi. ({E_DA_CONFERMARE})"
            )
        self.stdout.write(descrizione)
        risposta = chiedi("Riusarla per il primo amministratore? Username e password restano i suoi. [s/N] ")
        if risposta.strip().lower() not in ("s", "si", "sì"):
            raise CommandError("Nessun amministratore creato: il riuso non e' stato confermato.")
        return int(credenziale["auth_user_id"])

    # Scopo: La password, digitata due volte o da `ENV_PASSWORD` con
    #        `--noinput`, validata coi validatori di Django contro i dati della
    #        persona (un `User` non salvato: il confronto di somiglianza vuole
    #        username, nome ed email).
    def _password(self, options: dict[str, Any]) -> str:
        if options["noinput"]:
            password = os.environ.get(ENV_PASSWORD, "")
            conferma = password
            if not password:
                raise CommandError(f"Con --noinput la password si passa in {ENV_PASSWORD}.")
        else:
            # Prima della domanda si dice quando la password NON si usa: col
            # riuso di una credenziale l'account tiene la sua (Tid, 2026-11-25).
            self.stdout.write(
                "Con --riusa-credenziale l'account tiene la sua password: questa non verra' usata."
                if options.get("riusa_credenziale") is not None else
                "Se l'email e' gia' di un account, il comando chiedera' se riusarlo: in quel caso "
                "l'account tiene la sua password, e questa non verra' usata."
            )
            password = chiedi_password("Password: ")
            conferma = chiedi_password("Password (di nuovo): ")
        persona = User(
            username=options["username"], email=options["email"],
            first_name=options["nome"], last_name=options["cognome"],
        )
        try:
            valida_nuova_password(password, conferma, user=persona, code=E_VALIDATION_INPUT)
        except ServiceError as exc:
            raise CommandError(exc.message) from exc
        return password

    # Scopo: La data di nascita facoltativa, AAAA-MM-GG.
    @staticmethod
    def _data(testo: str | None) -> date | None:
        if not testo:
            return None
        try:
            return date.fromisoformat(testo)
        except ValueError as exc:
            raise CommandError(f"--data-nascita: attesa una data AAAA-MM-GG, non {testo!r}.") from exc
