# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il secondo fattore (TOTP) della credenziale, dal lato del backend:
#        la configurazione (registra, conferma), i codici di recupero, la
#        disattivazione propria e dell'amministratore, l'obbligo sulla
#        credenziale, e la VERIFICA DELLA PROVA (codice o codice di recupero)
#        che usano anche il secondo passo del login.
# Note: Brief sicurezza §3.4-bis, lotti T-2 e T-3. Lo stato e le regole sono
#       del DB (`SecondoFattoreRepository`, verbi `script.fn_totp_*`); il
#       segreto in chiaro e il calcolo del codice sono di `totp_service`.
#       ⭐ Regola del 2 (2026-10-01): la verifica della prova stava nella view
#       del secondo passo; con la disattivazione e la rigenerazione dei codici
#       i chiamanti sono tre, e la sede e' qui.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from django.contrib.auth.models import User
from django.db import DatabaseError, transaction

from apps.core.db.auth_repository import AuthRepository
from apps.core.db.secondo_fattore_repository import (
    STATO_DEVICE_ATTIVO,
    STATO_DEVICE_DA_CONFERMARE,
    SecondoFattoreRepository,
)
from apps.core.db.session_audit_repository import SessionAuditRepository
from apps.core.services import crypto_service, totp_service
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.nome_tentato import digest_nome_tentato, etichetta_log
from apps.core.services.password_con_freno import verifica_password_con_freno
from apps.core.services.request_context import get_client_ip, get_request_id, get_user_agent
from apps.core.services.service_errors import ServiceError

logger = logging.getLogger("security")

_T = TypeVar("_T")

E_TOTP_CODICE_NON_VALIDO = "E_TOTP_CODICE_NON_VALIDO"
E_TOTP_DEVICE_ASSENTE = "E_TOTP_DEVICE_ASSENTE"
E_TOTP_DEVICE_GIA_ATTIVO = "E_TOTP_DEVICE_GIA_ATTIVO"
# ⛔ Non E_AUTHENTICATION_FAILED: un 401 fa partire sul frontend il rinnovo
# della sessione e poi il logout.
E_TOTP_PASSWORD_NON_VALIDA = "E_TOTP_PASSWORD_NON_VALIDA"  # noqa: S105 — codice errore, non un segreto
E_PERMESSO_NEGATO = "E_PERMESSO_NEGATO"

# I rifiuti del DB che, come il codice sbagliato, sono un tentativo fallito:
# lo stesso codice ripresentato (o uno piu' vecchio) e un codice di recupero
# che non c'e'.
_RIFIUTI_CHE_CONTANO = frozenset({"E_TOTP_PASSO_GIA_USATO", "E_TOTP_RECOVERY_NON_VALIDO"})

# Con quale prova: va nella riga di `dbops.sessioni_utente`.
PROVA_CODICE = "TOTP"
PROVA_RECUPERO = "CODICE_RECUPERO"

# L'evento della disattivazione (`chk_sessioni_utente_evento`, `20260929-25`).
_EVENTO_DISATTIVATO = "TOTP_DISABILITATO"


# Scopo: L'esito di una prova accettata.
class ProvaAccettata:
    def __init__(self, tipo: str, recupero_rimasti: int | None) -> None:
        self.tipo = tipo
        self.recupero_rimasti = recupero_rimasti


class SecondoFattoreService:
    """Configurazione, prova e disattivazione del secondo fattore."""

    def __init__(self) -> None:
        self._auth_repo = AuthRepository()
        self._repo = SecondoFattoreRepository()

    # =================================================================
    # La prova (login e self-service)
    # =================================================================

    # Scopo: Verifica la PROVA del secondo fattore di `user` — il codice
    #        dell'app oppure un codice di recupero — col freno della
    #        credenziale: blocco controllato prima, e un codice sbagliato,
    #        ripresentato o di recupero non valido conta come una password
    #        sbagliata (D-T2). Il device dev'essere ATTIVO (lo controlla il
    #        chiamante, che sa cosa rispondere se non lo e').
    #        Accettata: il passo e' registrato (anti-replay) o il codice di
    #        recupero consumato. Una richiesta senza prova non e' un tentativo.
    def verifica_prova(
        self,
        user: User,
        device: dict[str, Any],
        *,
        codice: object,
        codice_recupero: object,
        provenienza: str,
    ) -> ProvaAccettata:
        digest = digest_nome_tentato(user.get_username())
        chi = etichetta_log(user.id, digest)
        self._auth_repo.check_blocco_login(user.id, nome_digest=digest, provenienza=provenienza)

        if isinstance(codice, str) and codice:
            passo = totp_service.verifica_codice(self.segreto(device, user.id), codice)
            if passo is None:
                self._tentativo_fallito(user.id, digest, provenienza, chi)
                raise _codice_non_valido()
            self._prova_al_db(
                lambda: self._repo.registra_uso(user.id, passo=passo),
                user.id, digest, provenienza, chi,
            )
            return ProvaAccettata(PROVA_CODICE, None)
        if isinstance(codice_recupero, str) and codice_recupero:
            rimasti = self._prova_al_db(
                lambda: self._repo.consuma_recovery(
                    user.id, impronta=totp_service.impronta_codice_recupero(codice_recupero),
                ),
                user.id, digest, provenienza, chi,
            )
            logger.warning("security.codice_recupero_usato %s rimasti=%s", chi, rimasti)
            return ProvaAccettata(PROVA_RECUPERO, rimasti)
        raise _codice_non_valido(detail="ne' codice ne' codice di recupero")

    # Scopo: Il segreto in chiaro. ⛔ Un segreto che nessuna chiave apre non
    #        e' un codice sbagliato: e' una chiave tolta senza la rotazione
    #        (`ricifra_campi_cifrati`). Errore tecnico, non un tentativo.
    @staticmethod
    def segreto(device: dict[str, Any], auth_user_id: int) -> str:
        try:
            return crypto_service.decrypt(device["secret_encrypted"])
        except ValueError:
            logger.error("security.totp_segreto_illeggibile user_id=%s", auth_user_id)
            raise RuntimeError(
                "segreto del secondo fattore illeggibile con le chiavi configurate"
            ) from None

    # Scopo: Presenta la prova al DB. Se il DB la rifiuta per un codice
    #        ripresentato o non valido, e' un tentativo fallito (D-T2).
    #        ⛔ In un SAVEPOINT: il rifiuto interrompe la transazione in cui
    #        cade, e la registrazione del tentativo che lo segue non passerebbe
    #        — sotto una transazione esterna il tentativo non verrebbe contato e
    #        il codice d'errore diventerebbe E_DATABASE (trovato col login a due
    #        passi sul DB vero, 2026-10-01).
    def _prova_al_db(
        self, verbo: Callable[[], _T], auth_user_id: int, digest: bytes, provenienza: str, chi: str,
    ) -> _T:
        try:
            with transaction.atomic():
                return verbo()
        except DatabaseError as exc:
            if structured_db_error_code(exc) in _RIFIUTI_CHE_CONTANO:
                self._tentativo_fallito(auth_user_id, digest, provenienza, chi)
            raise

    # Scopo: D-T2. Un codice sbagliato conta come una password sbagliata:
    #        stesso freno sulla provenienza, stessa attesa crescente.
    def _tentativo_fallito(self, auth_user_id: int, digest: bytes, provenienza: str, chi: str) -> None:
        esito = self._auth_repo.registra_tentativo_login(
            auth_user_id, nome_digest=digest, provenienza=provenienza, successo=False,
        )
        logger.warning(
            "security.secondo_fattore_fallito %s provenienza=%s bloccato=%s",
            chi, provenienza, esito.get("bloccato"),
        )

    # =================================================================
    # Self-service (la credenziale su se stessa)
    # =================================================================

    # Scopo: Il device come lo legge il DB (stato, segreto cifrato, ultimo
    #        passo, codici rimasti), per chi decide cosa fare prima della prova.
    def device(self, auth_user_id: int) -> dict[str, Any]:
        return self._repo.get_device(auth_user_id)

    # Scopo: Lo stato da mostrare: il device, l'obbligo e il suo motivo
    #        (CREDENZIALE / PROFILO / None), quanti codici di recupero restano.
    def stato(self, auth_user_id: int) -> dict[str, Any]:
        device = self._repo.get_device(auth_user_id)
        obbligo = self._repo.get_obbligo(auth_user_id)
        return {
            "stato": device["stato"],
            "obbligatorio": bool(obbligo["obbligatorio"]),
            "motivo": obbligo["motivo"],
            "codici_recupero_rimasti": device["recovery_rimasti"],
        }

    # Scopo: Avvia (o ricomincia) la configurazione: segreto e codici di
    #        recupero nuovi, device NON confermato. Il segreto, il QR e i codici
    #        escono UNA volta sola, in questa risposta: al DB vanno il segreto
    #        cifrato e le impronte. Su un device ATTIVO il DB rifiuta
    #        (E_TOTP_DEVICE_GIA_ATTIVO): va prima disattivato.
    #        ⛔ Dietro la password della credenziale, sempre (anche al primo
    #        accesso con l'obbligo): con la sola sessione, chi la tiene rubata
    #        legherebbe il proprio telefono all'accesso di un altro (brief
    #        secondo fattore e riautenticazione, decisione di Tid 2026-10-02).
    def avvia_configurazione(self, user: User, password: object, *, request: Any) -> dict[str, Any]:
        verifica_password_con_freno(
            user, password, request=request, auth_repo=self._auth_repo,
            codice=E_TOTP_PASSWORD_NON_VALIDA, messaggio="Password non corretta.",
        )
        segreto, codici = self._registra_device_nuovo(user)
        return {
            "qr_data_uri": totp_service.qr_data_uri(totp_service.uri_configurazione(segreto, user.get_username())),
            # Per chi non puo' inquadrare il QR: lo stesso segreto, a gruppi.
            "segreto": " ".join(segreto[i:i + 4] for i in range(0, len(segreto), 4)),
            "codici_recupero": codici,
        }

    # Scopo: Chiude la configurazione col primo codice dell'app: il device
    #        diventa ATTIVO e il passo del codice e' il primo registrato. Un
    #        codice sbagliato qui non conta sul freno: il segreto la persona
    #        l'ha appena ricevuto, non c'e' niente da indovinare.
    def conferma_configurazione(self, user: User, codice: object) -> dict[str, Any]:
        device = self._repo.get_device(user.id)
        if device["stato"] == STATO_DEVICE_ATTIVO:
            # Il secondo clic su «Conferma»: il device e' gia' attivo, e dirlo
            # «non attivo» sarebbe falso.
            raise ServiceError(
                code=E_TOTP_DEVICE_GIA_ATTIVO,
                message="Il secondo fattore e' gia' attivo per questo accesso.",
                detail="conferma con device ATTIVO",
            )
        if device["stato"] != STATO_DEVICE_DA_CONFERMARE:
            raise _device_non_attivo(device["stato"])
        passo = (
            totp_service.verifica_codice(self.segreto(device, user.id), codice)
            if isinstance(codice, str) else None
        )
        if passo is None:
            raise _codice_non_valido()
        self._repo.conferma_device(user.id, passo=passo)
        logger.info("security.secondo_fattore_attivato user_id=%s", user.id)
        return self.stato(user.id)

    # Scopo: Il secondo fattore di una credenziale DI PROVA, configurato e gia'
    #        confermato, per il provisioning di sviluppo (T-1 di
    #        brief-be-utenti-di-sviluppo): segreto e codici nuovi come
    #        `avvia_configurazione`, poi la conferma sul passo di adesso.
    #        Restituisce segreto e codici (escono una volta sola), o None se il
    #        device e' gia' ATTIVO: la chiave buona e' quella gia' consegnata.
    #        ⛔ Niente password ne' codice: non c'e' una sessione da proteggere,
    #        e il segreto lo genera questo stesso processo. Per questo la chiama
    #        solo il command del provisioning, sulle credenziali che il verbo
    #        del DB restituisce come sue, e dentro il contesto della credenziale
    #        (il DB vuole che agisca lei: `fn_guard_utente_stesso`).
    def configura_confermato(self, user: User) -> dict[str, Any] | None:
        if self._repo.get_device(user.id)["stato"] == STATO_DEVICE_ATTIVO:
            return None
        segreto, codici = self._registra_device_nuovo(user)
        # Il passo PRECEDENTE: nessun codice e' stato usato davvero, e il DB
        # accetta solo passi successivi all'ultimo registrato — cosi' il primo
        # login (gli smoke, subito dopo) non trova il passo di adesso gia' preso.
        self._repo.conferma_device(user.id, passo=totp_service.passo_corrente() - 1)
        logger.info("security.secondo_fattore_attivato_dal_provisioning user_id=%s", user.id)
        return {"segreto": segreto, "codici_recupero": codici}

    # Scopo: Codici di recupero nuovi (i vecchi non valgono piu'), dietro un
    #        codice dell'app corrente: con la sola sessione non si ottengono.
    def rigenera_codici_recupero(self, user: User, codice: object, *, provenienza: str) -> dict[str, Any]:
        device = self._device_attivo(user.id)
        self.verifica_prova(user, device, codice=codice, codice_recupero=None, provenienza=provenienza)
        codici = totp_service.nuovi_codici_recupero()
        self._repo.rigenera_recovery(
            user.id, impronte_recupero=[totp_service.impronta_codice_recupero(c) for c in codici],
        )
        logger.info("security.codici_recupero_rigenerati user_id=%s", user.id)
        return {"codici_recupero": codici}

    # Scopo: La persona disattiva il proprio secondo fattore (per esempio per
    #        cambiare telefono), presentando un codice dell'app O un codice di
    #        recupero: una sessione rubata da sola non lo spegne (decisione 7,
    #        Tid 2026-09-30). Con l'obbligo, il cancello la riporta alla
    #        configurazione.
    def disattiva_propria(
        self, user: User, *, codice: object, codice_recupero: object, provenienza: str, request: Any,
    ) -> dict[str, Any]:
        device = self._device_attivo(user.id)
        self.verifica_prova(
            user, device, codice=codice, codice_recupero=codice_recupero, provenienza=provenienza,
        )
        self._disattiva_con_traccia(user.id, chi_agisce=user.id, motivo=None, request=request)
        return self.stato(user.id)

    # =================================================================
    # Amministratore (SUPER_ADMIN: lo ricontrollano i verbi del DB)
    # =================================================================

    # Scopo: Accende o spegne l'obbligo sulla CREDENZIALE. Non tocca quello
    #        che viene da un profilo, ne' il device.
    def imposta_obbligo(self, auth_user_id: int, valore: bool) -> dict[str, Any]:
        self._repo.imposta_obbligo(auth_user_id, valore=valore)
        logger.info("security.obbligo_secondo_fattore user_id=%s valore=%s", auth_user_id, valore)
        return self.stato_per_admin(auth_user_id)

    # Scopo: Lo stato per il drawer dell'operatore: oltre allo stato, se
    #        l'obbligo viene dalla credenziale (l'interruttore che
    #        l'amministratore accende) o da un profilo (che si cambia altrove).
    def stato_per_admin(self, auth_user_id: int) -> dict[str, Any]:
        stato = self.stato(auth_user_id)
        stato["obbligo_sulla_credenziale"] = stato["motivo"] == "CREDENZIALE"
        return stato

    # Scopo: Il SUPER_ADMIN disattiva il device di un altro (telefono perso),
    #        con motivo obbligatorio (E_TOTP_MOTIVO_OBBLIGATORIO). Le sessioni
    #        aperte restano (decisione 8): le ha aperte il titolare col secondo
    #        fattore. La traccia (D-T3) la scrive il backend.
    #        ⛔ Mai su se stesso: per il verbo del DB «la credenziale stessa»
    #        disattiva senza motivo e senza prova (la prova la chiede il
    #        backend, `disattiva_propria`). Da qui, con la sola sessione, un
    #        SUPER_ADMIN derubato perderebbe il device e chi tiene la sessione
    #        registrerebbe il proprio telefono: la decisione 7 aggirata.
    def disattiva_da_admin(
        self, auth_user_id: int, *, motivo: object, chi_agisce: int, request: Any,
    ) -> dict[str, Any]:
        if auth_user_id == chi_agisce:
            raise ServiceError(
                code=E_PERMESSO_NEGATO,
                message=(
                    "Il proprio secondo fattore si disattiva dalla pagina Sicurezza, "
                    "con un codice dell'app o un codice di recupero."
                ),
                detail="disattivazione da amministratore sulla propria credenziale",
            )
        self._disattiva_con_traccia(
            auth_user_id,
            chi_agisce=chi_agisce,
            motivo=(motivo.strip() or None) if isinstance(motivo, str) else None,
            request=request,
        )
        return self.stato_per_admin(auth_user_id)

    # =================================================================
    # Interni
    # =================================================================

    # Scopo: Segreto e codici di recupero nuovi, registrati sul device NON
    #        confermato (al DB il segreto cifrato e le impronte). Restituisce
    #        il segreto in chiaro e i codici: escono una volta sola.
    def _registra_device_nuovo(self, user: User) -> tuple[str, list[str]]:
        segreto = totp_service.nuovo_segreto()
        codici = totp_service.nuovi_codici_recupero()
        self._repo.registra_device(
            user.id,
            secret_encrypted=crypto_service.encrypt(segreto),
            impronte_recupero=[totp_service.impronta_codice_recupero(c) for c in codici],
        )
        logger.info("security.secondo_fattore_configurazione_avviata user_id=%s", user.id)
        return segreto, codici

    # Scopo: Il device ATTIVO, o E_TOTP_DEVICE_ASSENTE.
    def _device_attivo(self, auth_user_id: int) -> dict[str, Any]:
        device = self._repo.get_device(auth_user_id)
        if device["stato"] != STATO_DEVICE_ATTIVO:
            raise _device_non_attivo(device["stato"])
        return device

    # Scopo: Disattiva e lascia la traccia `TOTP_DISABILITATO` in
    #        `dbops.sessioni_utente` NELLA STESSA transazione (D-T3, via APP;
    #        dal server la scrive il verbo, D-T5). ⛔ Non con
    #        `session_audit_service`, che e' fail-open: una disattivazione del
    #        secondo fattore senza traccia e' proprio cio' che D-T3 esclude.
    #        Se la traccia non si scrive, la disattivazione si annulla.
    def _disattiva_con_traccia(
        self, auth_user_id: int, *, chi_agisce: int, motivo: str | None, request: Any,
    ) -> None:
        with transaction.atomic():
            self._repo.disabilita_device(auth_user_id, motivo=motivo)
            SessionAuditRepository().log_session_event(
                auth_user_id=auth_user_id,
                evento=_EVENTO_DISATTIVATO,
                jti=None,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                request_id=get_request_id(),
                dettaglio={"via": "APP", "chi_agisce": chi_agisce, "motivo": motivo},
            )
        logger.warning(
            "security.secondo_fattore_disattivato user_id=%s chi_agisce=%s",
            auth_user_id, chi_agisce,
        )


# Scopo: Il device non e' nello stato che l'azione richiede: una frase sola
#        per la configurazione e per le azioni su un device attivo.
def _device_non_attivo(stato: str) -> ServiceError:
    return ServiceError(
        code=E_TOTP_DEVICE_ASSENTE,
        message="Il secondo fattore non e' attivo per questo accesso.",
        detail=f"device {stato}",
    )


# Scopo: L'errore del codice sbagliato, una frase per tutti i casi.
def _codice_non_valido(*, detail: str | None = None) -> ServiceError:
    return ServiceError(
        code=E_TOTP_CODICE_NON_VALIDO,
        message="Codice non valido.",
        detail=detail,
        fields=("codice",),
    )
