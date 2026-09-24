# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio invito "veste non-operatore" (CLIENTE_PORTALE,
#        FORNITORE_PORTALE, SHOP_CUSTOMER).
#        Pattern simmetrico a InvitoOperatoreService, differenziato per:
#        - risolve entita sorgente (clienti per CLIENTE_PORTALE e
#          SHOP_CUSTOMER, fornitori per FORNITORE_PORTALE) ->
#          soggetto_ruolo_id
#        - crea, se mancante, auth_user + identita_digitali con
#          ruolo_applicativo coerente con la veste
#        - usa template email + tipi token dedicati per veste
#          (_VESTE_CONFIG mappa ruolo -> tipi token, template, link FE)
#
#        Il nome storico `InvitoPortaleService` resta per retrocompat
#        (5 usage esterni), ma il service ora gestisce anche
#        SHOP_CUSTOMER via `invia_invito_shop_customer` e
#        `reinvia_invito_shop_customer`.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any, TypedDict

from django.conf import settings
from django.db import connection, transaction

from apps.core.db.auth_repository import AuthRepository
from apps.core.services.auth_constants import (
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_FORNITORE_PORTALE,
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
)
from apps.core.services.email_service import EmailDispatchService
from apps.core.services.error_manager import ErrorManager
from apps.core.services.token_service import TokenService
from apps.portale.db.portale_repository import PortaleRepository

logger = logging.getLogger("security")

E_INVITO_PORTALE = "E_INVITO_PORTALE"
# Token type per email NUOVA (auth_user appena creato): l'attivazione setta
# password definitiva + attiva identita.
INVITO_PORTALE_TOKEN_TIPO = "INVITO_PORTALE"
# Token type per email ESISTENTE (auth_user gia' presente, nuova veste
# portale aggiunta come 2a identita post modello 1:N §8.4.1):
# l'attivazione solo attiva l'identita, la password resta quella esistente.
ATTIVAZIONE_PORTALE_CROSS_TOKEN_TIPO = "ATTIVAZIONE_PORTALE_CROSS"
# Union dei token type che AttivazionePortaleView accetta (§8.4.2).
PORTALE_ATTIVAZIONE_TOKEN_TIPI = (
    INVITO_PORTALE_TOKEN_TIPO,
    ATTIVAZIONE_PORTALE_CROSS_TOKEN_TIPO,
)
INVITO_PORTALE_SCADENZA_ORE = 72
_TEMPLATE_INVITO_PORTALE = "INVITO_PORTALE"

# Token types per invito shop customer (B1 §13.7 admin-driven).
# Simmetria totale col portale: email nuova -> INVITO_SHOP (set password
# + attiva identita), email esistente -> ATTIVAZIONE_SHOP_CROSS (solo
# attiva identita, password invariata).
INVITO_SHOP_TOKEN_TIPO = "INVITO_SHOP"
ATTIVAZIONE_SHOP_CROSS_TOKEN_TIPO = "ATTIVAZIONE_SHOP_CROSS"
SHOP_ATTIVAZIONE_TOKEN_TIPI = (
    INVITO_SHOP_TOKEN_TIPO,
    ATTIVAZIONE_SHOP_CROSS_TOKEN_TIPO,
)
_TEMPLATE_INVITO_SHOP = "INVITO_SHOP"


# Type-safety per la mappa config veste: forza i 5 campi obbligatori e
# preserva tipi distinti (str vs int) — evita drift tra entries.
class _VesteConfig(TypedDict):
    token_invito: str
    token_cross: str
    template: str
    link_path: str
    scadenza_ore: int


# Mappa config veste: ruolo_applicativo -> config (token invito, token
# cross, template email, path FE di attivazione, scadenza ore). Unica
# fonte di verita' per parametrizzare `_invia_invito_common` e
# `_invalidate_existing_token`. Aggiungere una nuova veste = aggiungere
# una nuova entry qui (no altre modifiche al service).
_VESTE_CONFIG: dict[str, _VesteConfig] = {
    RUOLO_APPLICATIVO_CLIENTE_PORTALE: {
        "token_invito": INVITO_PORTALE_TOKEN_TIPO,
        "token_cross": ATTIVAZIONE_PORTALE_CROSS_TOKEN_TIPO,
        "template": _TEMPLATE_INVITO_PORTALE,
        "link_path": "/attivazione-portale",
        "scadenza_ore": INVITO_PORTALE_SCADENZA_ORE,
    },
    RUOLO_APPLICATIVO_FORNITORE_PORTALE: {
        "token_invito": INVITO_PORTALE_TOKEN_TIPO,
        "token_cross": ATTIVAZIONE_PORTALE_CROSS_TOKEN_TIPO,
        "template": _TEMPLATE_INVITO_PORTALE,
        "link_path": "/attivazione-portale",
        "scadenza_ore": INVITO_PORTALE_SCADENZA_ORE,
    },
    RUOLO_APPLICATIVO_SHOP_CUSTOMER: {
        "token_invito": INVITO_SHOP_TOKEN_TIPO,
        "token_cross": ATTIVAZIONE_SHOP_CROSS_TOKEN_TIPO,
        "template": _TEMPLATE_INVITO_SHOP,
        "link_path": "/attivazione-shop",
        "scadenza_ore": INVITO_PORTALE_SCADENZA_ORE,
    },
}


# Scopo: Risolve (senza consumare) un token di attivazione cercandolo
# nell'insieme di tipi ammessi passato. Il FE non deve sapere in
# anticipo il tipo del token: lo determina il BE guardando quale tipo
# matcha. I tipi dello stesso insieme sono mutuamente esclusivi — lo
# stesso token_hash esiste una sola volta nel DB (unique su token_hash).
# Ritorna None se il token non matcha nessuno dei tipi o e' scaduto/usato.
def _resolve_token_in(
    token: str,
    tipi: tuple[str, ...],
    token_service: TokenService | None = None,
) -> tuple[int, dict[str, Any], str] | None:
    svc = token_service or TokenService()
    for tipo in tipi:
        result = svc.validate(token, tipo)
        if result is not None:
            auth_user_id, meta = result
            return auth_user_id, meta, tipo
    return None


# Scopo: Wrapper legacy per AttivazionePortaleView (§8.4.2). Mantiene la
# firma originale per retrocompat; delega a `_resolve_token_in` con i
# tipi portale.
def resolve_portale_token(
    token: str,
    token_service: TokenService | None = None,
) -> tuple[int, dict[str, Any], str] | None:
    return _resolve_token_in(token, PORTALE_ATTIVAZIONE_TOKEN_TIPI, token_service)


# Scopo: Risolve token shop (INVITO_SHOP o ATTIVAZIONE_SHOP_CROSS).
# Usato da AttivazioneShopValidateView + AttivazioneShopView (§13.7 B1).
def resolve_shop_token(
    token: str,
    token_service: TokenService | None = None,
) -> tuple[int, dict[str, Any], str] | None:
    return _resolve_token_in(token, SHOP_ATTIVAZIONE_TOKEN_TIPI, token_service)


class InvitoPortaleService:
    """Gestione invito portale: verifica, crea identita, invia email."""

    def __init__(self) -> None:
        self._repo = PortaleRepository()
        self._auth_repo = AuthRepository()
        self._token_service = TokenService()
        self._email_service = EmailDispatchService()

    # Scopo: Invia invito portale cliente. Se l'identita CLIENTE_PORTALE
    # non esiste ancora per il soggetto_ruolo del cliente, la crea
    # (auth_user nuovo o riusato per email). Riattiva invece un'identita
    # esistente disattivata generando nuovo token e rinviando email.
    # cliente_id = PK di anagrafiche.clienti (coerente con ClientiDetailView).
    def invia_invito_cliente(
        self,
        *,
        cliente_id: int,
        email: str,
        invitato_da_user_id: int,
        invalidate_existing: bool = False,
    ) -> dict[str, Any]:
        email_clean = self._clean_email(email)
        info = self._repo.get_cliente_info(cliente_id)
        ErrorManager.require(
            info is not None,
            code=E_INVITO_PORTALE,
            message=f"Cliente {cliente_id} non trovato.",
        )
        assert info is not None
        return self._invia_invito_common(
            soggetto_ruolo_id=int(info["soggetto_ruolo_id"]),
            ruolo_applicativo=RUOLO_APPLICATIVO_CLIENTE_PORTALE,
            email=email_clean,
            nome_destinatario=self._build_display_name(info),
            entita_label=f"Cliente {info.get('ba_codice') or cliente_id}",
            invitato_da_user_id=invitato_da_user_id,
            invalidate_existing=invalidate_existing,
        )

    # Scopo: Invia invito portale fornitore. Simmetrico a invia_invito_cliente
    # con ruolo_applicativo FORNITORE_PORTALE ed entita di partenza
    # anagrafiche.fornitori.
    def invia_invito_fornitore(
        self,
        *,
        fornitore_id: int,
        email: str,
        invitato_da_user_id: int,
        invalidate_existing: bool = False,
    ) -> dict[str, Any]:
        email_clean = self._clean_email(email)
        info = self._repo.get_fornitore_info(fornitore_id)
        ErrorManager.require(
            info is not None,
            code=E_INVITO_PORTALE,
            message=f"Fornitore {fornitore_id} non trovato.",
        )
        assert info is not None
        return self._invia_invito_common(
            soggetto_ruolo_id=int(info["soggetto_ruolo_id"]),
            ruolo_applicativo=RUOLO_APPLICATIVO_FORNITORE_PORTALE,
            email=email_clean,
            nome_destinatario=self._build_display_name(info),
            entita_label=f"Fornitore {fornitore_id}",
            invitato_da_user_id=invitato_da_user_id,
            invalidate_existing=invalidate_existing,
        )

    # Scopo: Reinvia invito portale invalidando token precedenti per
    # quell'auth_user. Usato dall'admin quando il token scade o l'utente
    # non riceve l'email.
    def reinvia_invito_cliente(
        self,
        *,
        cliente_id: int,
        email: str,
        invitato_da_user_id: int,
    ) -> dict[str, Any]:
        # Fix analisi-fix-transazioni #17: l'invalidazione dei token precedenti
        # avviene ora DENTRO l'atomic di ri-emissione (invalidate_existing=True),
        # non piu' come scrittura separata prima: invalidate + re-emit sono atomici,
        # l'utente non resta mai senza token validi se la ri-emissione fallisce.
        return self.invia_invito_cliente(
            cliente_id=cliente_id,
            email=email,
            invitato_da_user_id=invitato_da_user_id,
            invalidate_existing=True,
        )

    # Scopo: Reinvia invito portale fornitore invalidando token precedenti.
    def reinvia_invito_fornitore(
        self,
        *,
        fornitore_id: int,
        email: str,
        invitato_da_user_id: int,
    ) -> dict[str, Any]:
        # Fix analisi-fix-transazioni #17: invalidate token precedenti + re-emit
        # nella stessa transazione (invalidate_existing=True), vedi reinvia_invito_cliente.
        return self.invia_invito_fornitore(
            fornitore_id=fornitore_id,
            email=email,
            invitato_da_user_id=invitato_da_user_id,
            invalidate_existing=True,
        )

    # ── Stato + disattivazione veste (§6.2.4 + §6.2.6) ────────────────

    # Scopo: Stato aggregato delle vesti non-operatore di un cliente
    # (CLIENTE_PORTALE + SHOP_CUSTOMER). Un admin lo usa dal drawer per
    # decidere se "invita" (stato NESSUNO), "reinvia" (PENDING), "disattiva"
    # (ATTIVO) o "reinvia per riattivare" (DISATTIVO).
    def get_stato_accessi_cliente(self, cliente_id: int) -> dict[str, Any]:
        info = self._repo.get_cliente_info(cliente_id)
        ErrorManager.require(
            info is not None,
            code=E_INVITO_PORTALE,
            message=f"Cliente {cliente_id} non trovato.",
        )
        assert info is not None
        soggetto_ruolo_id = int(info["soggetto_ruolo_id"])
        return {
            "portale": self._repo.get_stato_identita(
                soggetto_ruolo_id,
                RUOLO_APPLICATIVO_CLIENTE_PORTALE,
                PORTALE_ATTIVAZIONE_TOKEN_TIPI,
            ),
            "shop": self._repo.get_stato_identita(
                soggetto_ruolo_id,
                RUOLO_APPLICATIVO_SHOP_CUSTOMER,
                SHOP_ATTIVAZIONE_TOKEN_TIPI,
            ),
        }

    # Scopo: Stato aggregato delle vesti non-operatore di un fornitore
    # (solo FORNITORE_PORTALE; i fornitori non accedono allo shop B2C).
    def get_stato_accessi_fornitore(self, fornitore_id: int) -> dict[str, Any]:
        info = self._repo.get_fornitore_info(fornitore_id)
        ErrorManager.require(
            info is not None,
            code=E_INVITO_PORTALE,
            message=f"Fornitore {fornitore_id} non trovato.",
        )
        assert info is not None
        return {
            "portale": self._repo.get_stato_identita(
                int(info["soggetto_ruolo_id"]),
                RUOLO_APPLICATIVO_FORNITORE_PORTALE,
                PORTALE_ATTIVAZIONE_TOKEN_TIPI,
            ),
        }

    # Scopo: Disattiva (soft-revoke) una veste di un cliente/fornitore.
    # Invalida anche i token ancora pendenti per quella veste: se un invito
    # era in volo e l'admin disattiva, il link email smette di funzionare.
    # Idempotente: se l'identita e' gia' DISATTIVO o NESSUNO ritorna
    # `{disattivato: False, stato: ...}` senza errore.
    def disattiva_veste_cliente(
        self,
        *,
        cliente_id: int,
        ruolo_applicativo: str,
        disattivato_da_user_id: int,
    ) -> dict[str, Any]:
        info = self._repo.get_cliente_info(cliente_id)
        ErrorManager.require(
            info is not None,
            code=E_INVITO_PORTALE,
            message=f"Cliente {cliente_id} non trovato.",
        )
        assert info is not None
        return self._disattiva_veste_common(
            soggetto_ruolo_id=int(info["soggetto_ruolo_id"]),
            ruolo_applicativo=ruolo_applicativo,
            disattivato_da_user_id=disattivato_da_user_id,
        )

    def disattiva_veste_fornitore(
        self,
        *,
        fornitore_id: int,
        disattivato_da_user_id: int,
    ) -> dict[str, Any]:
        info = self._repo.get_fornitore_info(fornitore_id)
        ErrorManager.require(
            info is not None,
            code=E_INVITO_PORTALE,
            message=f"Fornitore {fornitore_id} non trovato.",
        )
        assert info is not None
        return self._disattiva_veste_common(
            soggetto_ruolo_id=int(info["soggetto_ruolo_id"]),
            ruolo_applicativo=RUOLO_APPLICATIVO_FORNITORE_PORTALE,
            disattivato_da_user_id=disattivato_da_user_id,
        )

    # Scopo: core comune della disattivazione — risolve l'identita, la
    # disattiva se attiva, invalida i token pendenti. Transazionale quando
    # c'e' un UPDATE fisico; altrimenti salta il wrapper `atomic` per non
    # aprire transazioni vuote.
    def _disattiva_veste_common(
        self,
        *,
        soggetto_ruolo_id: int,
        ruolo_applicativo: str,
        disattivato_da_user_id: int,
    ) -> dict[str, Any]:
        existing = self._repo.find_identita_portale(
            soggetto_ruolo_id, ruolo_applicativo
        )
        if existing is None:
            return {"disattivato": False, "stato": "NESSUNO"}

        identita_id = int(existing["identita_id"])
        auth_user_id = (
            int(existing["auth_user_id"])
            if existing.get("auth_user_id") is not None
            else None
        )
        was_active = bool(existing.get("attivo"))

        # Invalida token pendenti in ogni caso (best-effort cleanup anche
        # su identita gia' disattiva). La `_invalidate_tokens_for_veste`
        # fail-fast se la veste non e' in _VESTE_CONFIG.
        if was_active:
            with transaction.atomic():
                self._repo.disattiva_identita(identita_id)
                if auth_user_id is not None:
                    self._invalidate_tokens_for_veste(auth_user_id, ruolo_applicativo)
        elif auth_user_id is not None:
            # Gia' disattiva ma puliamo i token residui (no UPDATE -> no atomic).
            self._invalidate_tokens_for_veste(auth_user_id, ruolo_applicativo)

        logger.info(
            "security.veste_disattivata identita_id=%s ruolo=%s auth_user=%s da=%s was_active=%s",
            identita_id, ruolo_applicativo, auth_user_id,
            disattivato_da_user_id, was_active,
        )
        return {
            "disattivato": was_active,
            "stato": "DISATTIVO",
            "identita_id": identita_id,
        }

    # Scopo: Invita uno shop customer a partire da un cliente anagrafico
    # esistente (B1 §13.7 admin-driven). Lo SHOP_CUSTOMER vive sullo stesso
    # soggetto_ruolo (ruolo CL) del cliente: stesso pattern del
    # CLIENTE_PORTALE ma con veste SHOP_CUSTOMER e template/link dedicati.
    # Branching email nuova vs esistente identico al portale (INVITO vs
    # CROSS), config veste risolta via _VESTE_CONFIG.
    def invia_invito_shop_customer(
        self,
        *,
        cliente_id: int,
        email: str,
        invitato_da_user_id: int,
        invalidate_existing: bool = False,
    ) -> dict[str, Any]:
        email_clean = self._clean_email(email)
        info = self._repo.get_cliente_info(cliente_id)
        ErrorManager.require(
            info is not None,
            code=E_INVITO_PORTALE,
            message=f"Cliente {cliente_id} non trovato.",
        )
        assert info is not None
        return self._invia_invito_common(
            soggetto_ruolo_id=int(info["soggetto_ruolo_id"]),
            ruolo_applicativo=RUOLO_APPLICATIVO_SHOP_CUSTOMER,
            email=email_clean,
            nome_destinatario=self._build_display_name(info),
            entita_label=f"Shop customer {info.get('ba_codice') or cliente_id}",
            invitato_da_user_id=invitato_da_user_id,
            invalidate_existing=invalidate_existing,
        )

    # Scopo: Reinvia invito shop customer invalidando token precedenti.
    def reinvia_invito_shop_customer(
        self,
        *,
        cliente_id: int,
        email: str,
        invitato_da_user_id: int,
    ) -> dict[str, Any]:
        # Fix analisi-fix-transazioni #17 (simmetria con cliente/fornitore):
        # invalidate token precedenti + re-emit nella STESSA transazione
        # (invalidate_existing=True), non piu' invalidate autocommit separato prima.
        return self.invia_invito_shop_customer(
            cliente_id=cliente_id,
            email=email,
            invitato_da_user_id=invitato_da_user_id,
            invalidate_existing=True,
        )

    # Scopo: Flusso comune invito (cliente+fornitore+shop). Due flussi, e
    # il discriminante e' «l'utente ha gia' una password VERA?»
    # (`PortaleRepository.auth_user_ha_password`):
    #
    # - NO (email nuova, oppure utente creato da un invito e mai attivato):
    #   flow "INVITO". Crea, se manca, l'auth_user col segnaposto `!` (password
    #   non utilizzabile), token tipo INVITO_*. All'attivazione l'utente
    #   sceglie la password e l'identita si attiva.
    #
    # - SI' (operatore, o altra veste gia' attivata): flow "CROSS". NON tocca
    #   la password, token tipo ATTIVAZIONE_*_CROSS. L'attivazione (§8.4.2)
    #   attiva l'identita senza chiedere una password.
    #
    # ⛔ In ENTRAMBI i flussi l'identita nasce `attivo=false` e si attiva solo
    #    al consumo del token: una veste che nessuno ha ancora accettato non e'
    #    un accesso. Fino al 2026-09-24 il flow INVITO la creava gia' attiva,
    #    con una password temporanea, e sceglieva il flusso da «l'auth_user e'
    #    stato appena creato»: al reinvio l'utente esisteva gia', il flusso
    #    diventava CROSS e il rifiuto «ha gia' accesso» rendeva il reinvio
    #    impossibile — mentre lo stato accessi diceva ATTIVO a chi non aveva
    #    mai attivato (M-3 dell'analisi difetti).
    #
    # Orchestrazione in transazione atomica: upsert auth_user, upsert
    # identita, genera token. Fuori dalla transazione: invio email +
    # timestamp. Rationale: il token deve restare valido anche se l'email
    # fallisce (recupero manuale).
    def _invia_invito_common(
        self,
        *,
        soggetto_ruolo_id: int,
        ruolo_applicativo: str,
        email: str,
        nome_destinatario: str,
        entita_label: str,
        invitato_da_user_id: int,
        invalidate_existing: bool = False,
    ) -> dict[str, Any]:
        ErrorManager.require(
            "@" in email,
            code=E_INVITO_PORTALE,
            message="Email destinatario non valida.",
        )

        # Config della veste: token tipi, template email, link_path FE.
        # Single source of truth per supportare CLIENTE_PORTALE /
        # FORNITORE_PORTALE / SHOP_CUSTOMER senza duplicare il flow.
        cfg = _VESTE_CONFIG.get(ruolo_applicativo)
        ErrorManager.require(
            cfg is not None,
            code=E_INVITO_PORTALE,
            message=f"Veste {ruolo_applicativo} non supportata da invito.",
        )
        assert cfg is not None

        with transaction.atomic():
            # Fix analisi-fix-transazioni #17 (Classe C — saga): sul reinvio,
            # l'invalidazione dei token precedenti e la ri-emissione identita/token
            # vivono nella STESSA transazione. Prima l'invalidate era una scrittura
            # autocommit separata PRIMA di questo blocco: se la ri-emissione falliva,
            # l'utente restava senza token validi. Ora o entrambe o rollback totale
            # (l'utente conserva i token vecchi). L'invio email resta FUORI dall'atomic,
            # best-effort (side-effect esterno non contenibile in una tx DB).
            if invalidate_existing:
                self._invalidate_existing_token(soggetto_ruolo_id, ruolo_applicativo)
            auth_user_id, was_created = self._ensure_auth_user(
                email=email, nome_destinatario=nome_destinatario
            )
            # Branching flow sulla credenziale, non sulla creazione (vedi sopra).
            is_cross = self._repo.auth_user_ha_password(auth_user_id)
            identita_id = self._ensure_identita(
                auth_user_id=auth_user_id,
                soggetto_ruolo_id=soggetto_ruolo_id,
                ruolo_applicativo=ruolo_applicativo,
            )

            token_tipo = cfg["token_cross"] if is_cross else cfg["token_invito"]
            token_plain = self._token_service.create(
                tipo=token_tipo,
                auth_user_id=auth_user_id,
                scadenza_ore=cfg["scadenza_ore"],
                meta={
                    "invitato_da_user_id": invitato_da_user_id,
                    "ruolo_applicativo": ruolo_applicativo,
                    "entita": entita_label,
                    "identita_id": identita_id,
                },
            )

        # Link FE di attivazione: path dedicato per veste
        # (/attivazione-portale o /attivazione-shop). Il FE distingue l'UX
        # (set-password vs attiva-veste) in base al token_type restituito
        # dall'endpoint validate (§8.4.2 portale, §13.7 shop).
        frontend_url = settings.FRONTEND_URL
        link = f"{frontend_url}{cfg['link_path']}/{token_plain}"

        invitato_da_nome = self._get_display_name_of(invitato_da_user_id)

        try:
            self._email_service.send_email(
                codice_template=cfg["template"],
                destinatario=email,
                variabili={
                    "nome": nome_destinatario,
                    "entita": entita_label,
                    "azienda": "ZeroErp",
                    "link": link,
                    "scadenza_ore": str(cfg["scadenza_ore"]),
                    "invitato_da": invitato_da_nome,
                    "ruolo_applicativo": ruolo_applicativo,
                    # Flag leggibile dal template per differenziare
                    # "attiva il tuo account" (nuovo) vs "attiva l'accesso
                    # (portale|shop)" (cross su utente esistente).
                    "is_cross": "1" if is_cross else "0",
                },
                ambito="SISTEMA",
                auth_user_id=auth_user_id,
            )
        except Exception:
            logger.exception(
                "Errore invio email invito veste user_id=%s ruolo=%s "
                "is_cross=%s — token valido, invito recuperabile",
                auth_user_id,
                ruolo_applicativo,
                is_cross,
            )

        # Timestamp invito sulla riga identita specifica del flusso
        # (con modello 1:N serve puntare alla veste corretta — la stessa
        # auth_user puo' avere gia' un'altra identita con timestamp diverso).
        invito_updated = self._auth_repo.set_invito_inviato_at(
            auth_user_id, identita_id=identita_id
        )
        if not invito_updated:
            # Non fatale (il token e' gia' emesso, l'invito e' recuperabile)
            # ma segnale di stato incoerente: puntava a una riga non piu'
            # esistente o con auth_user_id divergente (guard anti-tampering
            # del repo). Utile in diagnosi.
            logger.warning(
                "Timestamp invito portale non aggiornato user_id=%s "
                "identita_id=%s — riga non trovata o auth_user divergente",
                auth_user_id, identita_id,
            )

        logger.info(
            "security.invito_portale_inviato user_id=%s ruolo=%s da=%s "
            "created_user=%s is_cross=%s identita_id=%s",
            auth_user_id,
            ruolo_applicativo,
            invitato_da_user_id,
            was_created,
            is_cross,
            identita_id,
        )

        return {
            "inviato": True,
            "email": self._mask_email(email),
            "auth_user_id": auth_user_id,
            "identita_id": identita_id,
            "nuovo_utente": was_created,
            "is_cross": is_cross,
        }

    # Scopo: Restituisce l'auth_user_id se esiste per quell'email, altrimenti
    # ne crea uno nuovo. Il second flag (bool) indica se e' stato creato.
    def _ensure_auth_user(
        self, *, email: str, nome_destinatario: str
    ) -> tuple[int, bool]:
        existing = self._repo.find_auth_user_by_email(email)
        if existing is not None:
            return existing, False
        # Split nome in first/last best-effort: usa l'unico campo
        # nome_destinatario come first_name se non contiene spazi, altrimenti
        # split al primo spazio. Il valore anagrafico vero vive sul soggetto.
        first, last = self._split_name(nome_destinatario)
        new_id = self._repo.create_auth_user_portale(
            email=email,
            # Password NON utilizzabile finche' l'invito non si attiva: e' cio'
            # che al reinvio tiene l'utente nel flow INVITO.
            password_hash="!",
            first_name=first,
            last_name=last,
        )
        return new_id, True

    # Scopo: Garantisce che esista un'identita digitale portale per la
    # coppia (soggetto_ruolo_id, ruolo_applicativo). Ritorna l'`identita_id`
    # (nuova o esistente) per consentire al caller di puntare la riga
    # giusta negli UPDATE successivi (pattern richiesto dal modello 1:N
    # §8.4.1, vedi `AuthRepository.set_deve_cambiare_password/...`).
    #
    # Comportamento per stato identita:
    # - Non esiste: la crea `attivo=false`, `deve_cambiare_password=false`,
    #   in entrambi i flussi. Si attiva al consumo del token.
    # - Esiste gia' ATTIVA: ERRORE — l'utente ha gia' accesso al portale con
    #   quella veste; un nuovo invito non ha senso (se serve reset
    #   credenziali, il self-service password reset copre il caso).
    # - Esiste collegata ad un auth_user DIVERSO: ERRORE (stato incoerente
    #   del modello — soggetto_ruolo con holder diverso dall'auth_user
    #   risolto via email). Richiede intervento manuale, NON risolviamo
    #   automaticamente (§8.4.1 FRAG4).
    # - Esiste disattivata con auth_user coerente: e' il caso legittimo del
    #   reinvio (invito scaduto, mai attivato, o veste revocata): la si
    #   lascia disattivata, la attivera' il consumo del token nuovo.
    def _ensure_identita(
        self,
        *,
        auth_user_id: int,
        soggetto_ruolo_id: int,
        ruolo_applicativo: str,
    ) -> int:
        existing = self._repo.find_identita_portale(
            soggetto_ruolo_id, ruolo_applicativo
        )
        if existing is None:
            return self._repo.create_identita_portale(
                auth_user_id=auth_user_id,
                soggetto_ruolo_id=soggetto_ruolo_id,
                ruolo_applicativo=ruolo_applicativo,
                attivo=False,
                deve_cambiare_password=False,
            )

        identita_id = int(existing["identita_id"])
        existing_auth_user_raw = existing.get("auth_user_id")

        # Guard coerenza: l'identita trovata deve appartenere allo stesso
        # auth_user risolto via email. Divergenza = stato manipolato
        # (soggetto_ruolo riassegnato, migrazione manuale incoerente).
        if existing_auth_user_raw is not None and int(
            existing_auth_user_raw
        ) != auth_user_id:
            ErrorManager.require(
                False,
                code=E_INVITO_PORTALE,
                message=(
                    "Identita portale gia' collegata a un altro utente. "
                    "Richiede intervento manuale."
                ),
            )

        # Guard logico: identita gia' attiva = utente gia' ha accesso al
        # portale con quella veste. Nuovo invito non ha senso: se serve
        # reset credenziali l'utente usa "ho dimenticato la password".
        if existing.get("attivo"):
            ErrorManager.require(
                False,
                code=E_INVITO_PORTALE,
                message=(
                    "L'utente ha gia' accesso a questa veste del portale. "
                    "Per problemi di credenziali usare il reset password."
                ),
            )

        # Identita disattivata (reinvio): resta com'e', la attiva il token.
        return identita_id

    # Scopo: Invalida la coppia di token (INVITO + CROSS) della veste per
    # un auth_user. Helper DRY usato sia da reinvio (`_invalidate_existing_token`)
    # sia da disattivazione (`_disattiva_veste_common`). Fail-fast se la
    # veste non e' in _VESTE_CONFIG — evita silent no-op che lascerebbero
    # token vecchi attivi.
    def _invalidate_tokens_for_veste(
        self, auth_user_id: int, ruolo_applicativo: str
    ) -> None:
        cfg = _VESTE_CONFIG.get(ruolo_applicativo)
        ErrorManager.require(
            cfg is not None,
            code=E_INVITO_PORTALE,
            message=f"Veste {ruolo_applicativo} non supportata.",
        )
        assert cfg is not None
        self._token_service.invalidate_all(cfg["token_invito"], auth_user_id)
        self._token_service.invalidate_all(cfg["token_cross"], auth_user_id)

    # Scopo: Invalida token invito/cross residui per l'auth_user collegato
    # a un soggetto_ruolo+ruolo_applicativo. Usato in reinvio per consumare
    # lo stato precedente qualunque sia il flow con cui era stato creato.
    def _invalidate_existing_token(
        self, soggetto_ruolo_id: int, ruolo_applicativo: str
    ) -> None:
        existing = self._repo.find_identita_portale(
            soggetto_ruolo_id, ruolo_applicativo
        )
        if existing and existing.get("auth_user_id"):
            self._invalidate_tokens_for_veste(
                int(existing["auth_user_id"]), ruolo_applicativo,
            )

    # Scopo: Costruisce il nome da mostrare nell'email a partire dal record
    # soggetto. Preferisce ragione_sociale_completa (PG/ENTE) con fallback
    # su cognome+nome (PF).
    @staticmethod
    def _build_display_name(info: dict[str, Any]) -> str:
        rs = (info.get("ragione_sociale") or "").strip()
        if rs:
            return rs
        cognome = (info.get("cognome") or "").strip()
        nome = (info.get("nome") or "").strip()
        combined = f"{nome} {cognome}".strip()
        return combined or "cliente/fornitore"

    # Scopo: Recupera il nome visualizzabile dell'utente che ha invitato.
    # Usato come variabile email "invitato_da".
    def _get_display_name_of(self, auth_user_id: int) -> str:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT first_name, last_name, username "
                "FROM django.auth_user WHERE id = %s",
                [auth_user_id],
            )
            row = cursor.fetchone()
            if row:
                name = f"{row[0] or ''} {row[1] or ''}".strip()
                return name or row[2] or "Amministratore"
        return "Amministratore"

    @staticmethod
    def _clean_email(email: str | None) -> str:
        cleaned = (email or "").strip()
        ErrorManager.require(
            bool(cleaned),
            code=E_INVITO_PORTALE,
            message="Email destinatario obbligatoria.",
        )
        return cleaned

    @staticmethod
    def _split_name(full: str) -> tuple[str, str]:
        full = (full or "").strip()
        if not full:
            return "", ""
        if " " in full:
            first, last = full.split(" ", 1)
            return first.strip(), last.strip()
        return full, ""

    @staticmethod
    def _mask_email(email: str) -> str:
        if not email or "@" not in email:
            return "***"
        local, domain = email.split("@", 1)
        if len(local) <= 1:
            return f"*@{domain}"
        return f"{local[0]}***@{domain}"
