# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block UNICO del ciclo di vita d'invito di una veste —
#        operatore, cliente e fornitore portale, cliente shop (L-3 del
#        piano-be-fe-accessi-credenziale-e-vesti, regola del 2, ok Tid
#        2026-09-25). La regola e' quella dell'analisi §4.2, uguale per ogni
#        veste:
#          - INVITO: la veste esiste SPENTA; il flusso si sceglie sulla
#            credenziale («ha una password vera?»): senza → la persona la
#            sceglie all'attivazione (token INVITO); con → attiva con un clic
#            (token CROSS). ⛔ Nessuna password esistente viene mai toccata;
#          - EMISSIONE (primo invito o reinvio, e' la stessa cosa): invalida
#            i token pendenti della veste NELLA STESSA transazione del token
#            nuovo — un link vivo per veste;
#          - ATTIVAZIONE: consuma il token e ACCENDE la veste nella stessa
#            transazione; la password si sceglie solo nel flusso INVITO.
#        ⭐ Quello che cambia fra le vesti e' solo la PORTA (`PortaInvito`):
#        tipi di token, template email, link del frontend, codici d'errore.
#        Chi decide COSA invitare (la veste da creare o da cercare, il check
#        d'invitabilita') resta al servizio della veste; da qui in giu' la
#        strada e' una.
#        ⭐ Anche lo SPEGNIMENTO ha la sua strada qui (`chiudi_veste_spenta`,
#        2026-10-03): cio' che resta aperto di una veste spenta si chiude
#        allo stesso modo per ogni porta.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

from apps.core.db.auth_repository import AuthRepository
from apps.core.services.auth_constants import (
    NOME_SISTEMA_EMAIL,
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_FORNITORE_PORTALE,
    RUOLO_APPLICATIVO_OPERATORE,
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
)
from apps.core.services.auth_helpers import (
    apply_new_password,
    extract_identita_id_from_token_meta,
    valida_nuova_password,
)
from apps.core.services.email_service import EmailDispatchService
from apps.core.services.error_manager import ErrorManager
from apps.core.services.permissions_cache import invalidate_user
from apps.core.services.revoca_token import blocca_token_sessioni
from apps.core.services.token_service import TokenService

logger = logging.getLogger("security")

# Scadenza dell'invito, uguale per ogni porta (oggi): se una porta ne vorra'
# un'altra, si scrive nella sua `PortaInvito`, non qui.
_SCADENZA_INVITO_ORE = 72


# Scopo: La porta d'ingresso di una o piu' vesti: tutto cio' che distingue un
# invito dall'altro. Due vesti con la stessa porta (cliente e fornitore
# portale) condividono token, template e pagina di attivazione.
@dataclass(frozen=True)
class PortaInvito:
    nome: str
    ruoli: tuple[str, ...]
    token_invito: str
    token_cross: str
    template: str
    # Il template del flusso con un clic (credenziale che ha gia' una
    # password): un testo diverso, non un ramo dentro lo stesso testo — il
    # motore dei template sostituisce `{{chiave}}` e basta (brief
    # blocco-login §15, B-16). Il testo resta dato, nel DB.
    template_cross: str
    link_path: str
    codice_invito: str
    codice_attivazione: str
    scadenza_ore: int = _SCADENZA_INVITO_ORE

    # Scopo: I due tipi di token della porta, nell'ordine in cui si cercano.
    @property
    def token_tipi(self) -> tuple[str, str]:
        return (self.token_invito, self.token_cross)


PORTA_OPERATORE = PortaInvito(
    nome="OPERATORE",
    ruoli=(RUOLO_APPLICATIVO_OPERATORE,),
    token_invito="INVITO_OPERATORE",  # noqa: S106 — codice del tipo token, non un segreto
    token_cross="ATTIVAZIONE_OPERATORE_CROSS",  # noqa: S106 — codice del tipo token, non un segreto
    template="INVITO_OPERATORE",
    template_cross="INVITO_OPERATORE_CROSS",
    link_path="/attivazione",
    codice_invito="E_INVITO_OPERATORE",
    codice_attivazione="E_ATTIVAZIONE",
)
PORTA_PORTALE = PortaInvito(
    nome="PORTALE",
    ruoli=(RUOLO_APPLICATIVO_CLIENTE_PORTALE, RUOLO_APPLICATIVO_FORNITORE_PORTALE),
    token_invito="INVITO_PORTALE",  # noqa: S106 — codice del tipo token, non un segreto
    token_cross="ATTIVAZIONE_PORTALE_CROSS",  # noqa: S106 — codice del tipo token, non un segreto
    template="INVITO_PORTALE",
    template_cross="INVITO_PORTALE_CROSS",
    link_path="/attivazione-portale",
    codice_invito="E_INVITO_PORTALE",
    codice_attivazione="E_ATTIVAZIONE_PORTALE",
)
PORTA_SHOP = PortaInvito(
    nome="SHOP",
    ruoli=(RUOLO_APPLICATIVO_SHOP_CUSTOMER,),
    token_invito="INVITO_SHOP",  # noqa: S106 — codice del tipo token, non un segreto
    token_cross="ATTIVAZIONE_SHOP_CROSS",  # noqa: S106 — codice del tipo token, non un segreto
    template="INVITO_SHOP",
    template_cross="INVITO_SHOP_CROSS",
    link_path="/attivazione-shop",
    codice_invito="E_INVITO_PORTALE",
    codice_attivazione="E_ATTIVAZIONE_SHOP",
)

_PORTE: tuple[PortaInvito, ...] = (PORTA_OPERATORE, PORTA_PORTALE, PORTA_SHOP)


# Scopo: La porta di una veste. Una veste senza porta e' un errore di chi
# chiama (non un dato dell'operatore): esplode, non ripiega.
def porta_della_veste(ruolo_applicativo: str) -> PortaInvito:
    for porta in _PORTE:
        if ruolo_applicativo in porta.ruoli:
            return porta
    raise ValueError(f"Veste {ruolo_applicativo!r} senza porta d'invito")


# Scopo: L'esito dell'emissione: il token in chiaro (unica volta in cui
# esiste) e il flusso scelto sulla credenziale.
@dataclass(frozen=True)
class EmissioneInvito:
    token: str
    is_cross: bool


# Scopo: Maschera un'email per le risposte API (es. "m***@azienda.it").
def maschera_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"


# Scopo: Il nome da mostrare di una credenziale nelle email: la ragione
# sociale completa del suo soggetto (decisione di Tid, 2026-10-02: «Ciao
# Soggetto1773959838» veniva dal first_name copiato alla creazione), poi nome
# e cognome, poi lo username. Il saluto del reset e della conferma del cambio
# password, e la firma «invitato da» degli inviti.
def nome_visualizzato(auth_user_id: int, auth_repo: AuthRepository | None = None) -> str:
    nomi = (auth_repo or AuthRepository()).get_nomi_credenziale(auth_user_id)
    if nomi is None:
        return "Amministratore"
    nome = nomi.get("ragione_sociale_completa") or f"{nomi['first_name']} {nomi['last_name']}".strip()
    return nome or nomi["username"] or "Amministratore"


class InvitoVeste:
    """Emissione, reinvio e spedizione dell'invito di una veste (una porta)."""

    def __init__(
        self,
        *,
        auth_repo: AuthRepository | None = None,
        token_service: TokenService | None = None,
        email_service: EmailDispatchService | None = None,
    ) -> None:
        self._auth_repo = auth_repo or AuthRepository()
        self._token_service = token_service or TokenService()
        self._email_service = email_service or EmailDispatchService()

    # Scopo: Invalida i token pendenti di UNA veste (reinvio, disattivazione).
    def invalida(self, porta: PortaInvito, *, auth_user_id: int, identita_id: int) -> int:
        return self._token_service.invalidate_for_identita(
            porta.token_tipi, auth_user_id, identita_id
        )

    # Scopo: Chiude cio' che resta aperto di una veste SPENTA: gli inviti
    #        pendenti (un link in volo la riaccenderebbe), le sue sessioni
    #        (`blocca_token_sessioni` per `identita_id`: quelle delle altre
    #        vesti della credenziale restano) e, a commit avvenuto, la cache
    #        dei permessi della credenziale.
    # ⭐ Regola del 2 (ok Tid, 2026-10-03): la scrivevano due servizi,
    #    `AmmSoftwareService._spegni_veste_operatore` e
    #    `InvitoPortaleService._disattiva_veste_common` (A-5, D-5). Una
    #    conseguenza nuova dello spegnimento si aggiunge qui, per ogni porta.
    # ⛔ Va chiamata DENTRO la transazione che spegne la veste: una chiusura
    #    fallita deve annullare anche lo spegnimento, e `on_commit` senza
    #    transazione aperta scatterebbe subito, prima che la veste sia spenta
    #    per gli altri. Non spegne la veste: lo fa il chiamante.
    def chiudi_veste_spenta(
        self, porta: PortaInvito, *, auth_user_id: int, identita_id: int,
    ) -> None:
        self.invalida(porta, auth_user_id=auth_user_id, identita_id=identita_id)
        blocca_token_sessioni(auth_user_id, identita_id=identita_id)
        transaction.on_commit(lambda: invalidate_user(auth_user_id))

    # Scopo: Emette il token d'invito di una veste SPENTA. Il flusso si decide
    # sulla credenziale; i token pendenti della veste si invalidano SEMPRE,
    # nella STESSA transazione del token nuovo (o tutti e due, o nessuno: la
    # persona non resta mai senza un link valido, e non ne ha mai due). ⭐ Non
    # c'e' un «primo invito» da distinguere dal reinvio: una veste spenta con
    # un token pendente E' un reinvio, comunque lo si chiami. Si spengono solo
    # i token di QUESTA veste: quelli di un'altra veste della stessa porta
    # (cliente e fornitore portale) restano validi.
    # ⛔ Non tocca password ne' veste: la veste la accende solo l'attivazione.
    # `meta` aggiunge chiavi al meta del token (es. l'entita' del portale).
    def emetti(
        self,
        porta: PortaInvito,
        *,
        auth_user_id: int,
        identita_id: int,
        ruolo_applicativo: str,
        invitato_da_user_id: int,
        meta: dict[str, Any] | None = None,
    ) -> EmissioneInvito:
        if ruolo_applicativo not in porta.ruoli:
            raise ValueError(f"Veste {ruolo_applicativo!r} fuori dalla porta {porta.nome}")
        with transaction.atomic():
            self.invalida(porta, auth_user_id=auth_user_id, identita_id=identita_id)
            is_cross = self._auth_repo.auth_user_ha_password(auth_user_id)
            token = self._token_service.create(
                tipo=porta.token_cross if is_cross else porta.token_invito,
                auth_user_id=auth_user_id,
                scadenza_ore=porta.scadenza_ore,
                meta={
                    **(meta or {}),
                    "invitato_da_user_id": invitato_da_user_id,
                    "ruolo_applicativo": ruolo_applicativo,
                    "identita_id": identita_id,
                },
            )
        return EmissioneInvito(token=token, is_cross=is_cross)

    # Scopo: Spedisce l'email d'invito e segna l'invito sulla veste. FUORI
    # dalla transazione dell'emissione: l'email e' un effetto esterno, e se
    # fallisce il token resta valido (l'admin rimanda). Le variabili comuni
    # (link, scadenza, firma, sistema, flusso) le aggiunge il BB; quelle
    # della veste (nome, entita', ...) le passa il chiamante.
    # ⭐ Ritorna se l'email E' PARTITA, e il chiamante lo riporta al client
    #    (`inviato`). Un fallimento non solleva — il token c'e' e vale — ma
    #    non si tace: si logga, e `invito_inviato_at` («l'ultimo invito
    #    inviato») resta dov'era.
    # ⛔ Fino al 2026-09-28 l'esito di `send_email` si scartava: un SMTP
    #    fallito o un canale non configurato tornano `False` SENZA eccezione,
    #    quindi l'invito risultava inviato e il log taceva (analisi difetti doc
    #    API core, F-3). L'eccezione copre l'altra meta': template o account
    #    che mancano.
    # ⚠️ In console mode (`DEBUG`) `send_email` torna `True`: la mail e' stata
    #    stampata, e il giornale la segna `SIMULATA`. Per lo sviluppo e' il
    #    comportamento voluto, e qui vale come partita.
    def spedisci(
        self,
        porta: PortaInvito,
        emissione: EmissioneInvito,
        *,
        auth_user_id: int,
        identita_id: int,
        destinatario: str,
        invitato_da_user_id: int,
        variabili: dict[str, str],
        unita_organizzativa_id: int | None = None,
    ) -> bool:
        link = f"{settings.FRONTEND_URL}{porta.link_path}/{emissione.token}"
        try:
            log_id, spedita = self._email_service.send_email(
                # Il flusso sceglie il TESTO: «scegli la password» (nuovo) o
                # «entra con le credenziali che usi gia'» (un clic).
                codice_template=porta.template_cross if emissione.is_cross else porta.template,
                destinatario=destinatario,
                variabili={
                    **variabili,
                    "azienda": NOME_SISTEMA_EMAIL,
                    "link": link,
                    "scadenza_ore": str(porta.scadenza_ore),
                    "invitato_da": nome_visualizzato(invitato_da_user_id, self._auth_repo),
                },
                unita_organizzativa_id=unita_organizzativa_id,
                ambito="SISTEMA",
                auth_user_id=auth_user_id,
            )
        except Exception:
            logger.exception(
                "Errore invio email invito porta=%s user_id=%s is_cross=%s "
                "— token valido, invito recuperabile",
                porta.nome, auth_user_id, emissione.is_cross,
            )
            return False

        if not spedita:
            # Il motivo sta gia' nel giornale email (`FAILED` con `errore`).
            logger.error(
                "Email invito NON partita porta=%s user_id=%s is_cross=%s log_id=%s "
                "— token valido, invito recuperabile",
                porta.nome, auth_user_id, emissione.is_cross, log_id,
            )
            return False

        if not self._auth_repo.set_invito_inviato_at(auth_user_id, identita_id=identita_id):
            # Non fatale (il token c'e'), ma la veste non e' piu' dove
            # l'emissione l'aveva trovata: utile in diagnosi.
            logger.warning(
                "Timestamp invito non aggiornato porta=%s user_id=%s identita_id=%s "
                "— riga non trovata o credenziale divergente",
                porta.nome, auth_user_id, identita_id,
            )
        return True


# Scopo: Un token della porta risolto senza consumarlo: credenziale, meta e
# tipo (cioe' il flusso). None se non vale per nessuno dei due tipi. I due
# tipi sono esclusivi: lo stesso hash esiste una volta sola.
def risolvi_token(
    porta: PortaInvito,
    token: str,
    token_service: TokenService | None = None,
) -> tuple[int, dict[str, Any], str] | None:
    svc = token_service or TokenService()
    for tipo in porta.token_tipi:
        risolto = svc.validate(token, tipo)
        if risolto is not None:
            auth_user_id, meta = risolto
            return auth_user_id, meta, tipo
    return None


# Scopo: Dice se l'attivazione chiede la password. La decide la CREDENZIALE
# ADESSO, non il tipo del token soltanto: fra l'invito e l'attivazione la
# persona puo' aver attivato un'altra veste e avere ora una password vera, e un
# token INVITO la sovrascriverebbe per tutte le sue vesti. ⭐ La stessa
# domanda la fanno la validazione (che guida la pagina) e l'attivazione.
def richiede_password(
    porta: PortaInvito,
    token_type: str,
    auth_user_id: int,
    auth_repo: AuthRepository | None = None,
) -> bool:
    if token_type != porta.token_invito:
        return False
    return not (auth_repo or AuthRepository()).auth_user_ha_password(auth_user_id)


# Scopo: L'esito di un'attivazione, per la risposta e il log.
@dataclass(frozen=True)
class EsitoAttivazione:
    auth_user_id: int
    identita_id: int
    token_type: str
    is_cross: bool


# Scopo: Attiva la veste di un invito: consuma il token e ACCENDE la veste
# nella stessa transazione; nel flusso INVITO la persona sceglie anche la
# password (validata PRIMA di consumare: una password rifiutata non brucia il
# link). Senza password da scegliere (`richiede_password`) una password nel
# payload si IGNORA: non si sovrascrive quella che la persona usa gia'.
# ⛔ `identita_id` nel meta e' obbligatorio: un token senza non appartiene a
# nessuna veste, e accendere «qualcosa» della credenziale non e' un'opzione.
def attiva_veste(
    porta: PortaInvito,
    *,
    token: str,
    new_password: str,
    new_password_confirm: str,
    ip: str | None,
    auth_repo: AuthRepository | None = None,
    token_service: TokenService | None = None,
) -> EsitoAttivazione:
    repo = auth_repo or AuthRepository()
    svc = token_service or TokenService()
    codice = porta.codice_attivazione

    ErrorManager.require(bool(token), code=codice, message="Token obbligatorio.")
    # Un messaggio solo per token scaduto, usato o inesistente: niente
    # enumerazione del perche'.
    risolto = risolvi_token(porta, token, svc)
    ErrorManager.require(
        risolto is not None,
        code=codice,
        message="Token non valido, scaduto o gia' utilizzato.",
    )
    assert risolto is not None
    auth_user_id, meta, token_type = risolto

    user = User.objects.filter(id=auth_user_id).first()
    ErrorManager.require(user is not None, code=codice, message="Utente non trovato.")
    assert user is not None

    identita_id = extract_identita_id_from_token_meta(meta)
    ErrorManager.require(
        identita_id is not None,
        code=codice,
        message=(
            "Token privo di riferimento identita. "
            "Richiedere un nuovo invito dall'amministratore."
        ),
    )
    assert identita_id is not None

    is_cross = not richiede_password(porta, token_type, auth_user_id, repo)
    if not is_cross:
        valida_nuova_password(new_password, new_password_confirm, user=user, code=codice)

    with transaction.atomic():
        svc.consume(token, token_type, ip=ip)
        if not is_cross:
            # Primo accesso: nessuna sessione da chiudere.
            apply_new_password(user, new_password, blacklist_tokens=False, auth_repo=repo)
        # Rowcount 0 = veste rimossa fra invito e consumo, o token che non le
        # appartiene: sollevare annulla consumo e password insieme.
        if not repo.attiva_identita(
            identita_id, auth_user_id=auth_user_id, ruoli_applicativi=porta.ruoli
        ):
            logger.warning(
                "security.attivazione_veste_fallita porta=%s user_id=%s identita_id=%s "
                "— veste non trovata per la credenziale e la porta, rollback",
                porta.nome, auth_user_id, identita_id,
            )
            ErrorManager.require(
                False,
                code=codice,
                message=(
                    "Accesso non piu' disponibile. "
                    "Contattare l'amministratore per un nuovo invito."
                ),
            )

    logger.info(
        "security.veste_attivata porta=%s user_id=%s identita_id=%s token_type=%s",
        porta.nome, auth_user_id, identita_id, token_type,
    )
    return EsitoAttivazione(
        auth_user_id=auth_user_id,
        identita_id=identita_id,
        token_type=token_type,
        is_cross=is_cross,
    )
