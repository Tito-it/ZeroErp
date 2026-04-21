# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio invito portale cliente/fornitore.
#        Pattern simmetrico a InvitoOperatoreService ma differenziato per:
#        - risolve entita sorgente (billing_account per cliente, fornitori
#          per fornitore) -> soggetto_ruolo_id
#        - crea, se mancante, auth_user + identita_digitali con
#          ruolo_applicativo = CLIENTE_PORTALE o FORNITORE_PORTALE
#        - usa template email dedicato INVITO_PORTALE
#        - riusa TokenService con tipo INVITO_PORTALE
# ------------------------------------------------------------

from __future__ import annotations

import logging
import secrets
from typing import Any

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import connection, transaction

from apps.core.db.auth_repository import AuthRepository
from apps.core.services.auth_constants import (
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_FORNITORE_PORTALE,
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


# Scopo: Risolve (senza consumare) un token di attivazione portale
# cercandolo in entrambi i tipi ammessi (§8.4.2). Il FE non deve sapere
# in anticipo il tipo del token: lo determina il BE guardando quale tipo
# matcha. I due tipi sono mutuamente esclusivi — lo stesso token_hash
# esiste una sola volta nel DB grazie all'unique su token_hash.
# Ritorna None se il token non matcha nessuno dei tipi o e' scaduto/usato.
def resolve_portale_token(
    token: str,
    token_service: TokenService | None = None,
) -> tuple[int, dict[str, Any], str] | None:
    svc = token_service or TokenService()
    for tipo in PORTALE_ATTIVAZIONE_TOKEN_TIPI:
        result = svc.validate(token, tipo)
        if result is not None:
            auth_user_id, meta = result
            return auth_user_id, meta, tipo
    return None


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
        info = self._repo.get_cliente_info(cliente_id)
        ErrorManager.require(
            info is not None,
            code=E_INVITO_PORTALE,
            message=f"Cliente {cliente_id} non trovato.",
        )
        assert info is not None
        self._invalidate_existing_token(
            int(info["soggetto_ruolo_id"]), RUOLO_APPLICATIVO_CLIENTE_PORTALE
        )
        return self.invia_invito_cliente(
            cliente_id=cliente_id,
            email=email,
            invitato_da_user_id=invitato_da_user_id,
        )

    # Scopo: Reinvia invito portale fornitore invalidando token precedenti.
    def reinvia_invito_fornitore(
        self,
        *,
        fornitore_id: int,
        email: str,
        invitato_da_user_id: int,
    ) -> dict[str, Any]:
        info = self._repo.get_fornitore_info(fornitore_id)
        ErrorManager.require(
            info is not None,
            code=E_INVITO_PORTALE,
            message=f"Fornitore {fornitore_id} non trovato.",
        )
        assert info is not None
        self._invalidate_existing_token(
            int(info["soggetto_ruolo_id"]), RUOLO_APPLICATIVO_FORNITORE_PORTALE
        )
        return self.invia_invito_fornitore(
            fornitore_id=fornitore_id,
            email=email,
            invitato_da_user_id=invitato_da_user_id,
        )

    # Scopo: Flusso comune invito (cliente+fornitore). Post modello 1:N
    # §8.4.1 branching esplicito email nuova vs esistente:
    #
    # - Email NUOVA (auth_user non esiste): flow "INVITO classico".
    #   Crea auth_user + identita `attivo=true`, setta password temporanea,
    #   flag deve_cambiare_password=true, token tipo INVITO_PORTALE.
    #   L'utente all'attivazione sceglie la password definitiva.
    #
    # - Email ESISTENTE (auth_user gia' presente come operatore o altra
    #   veste portale): flow "CROSS". Aggiunge una 2a identita con
    #   `attivo=false`, NON tocca la password (l'utente ha gia' la sua),
    #   NON setta deve_cambiare_password, token tipo
    #   ATTIVAZIONE_PORTALE_CROSS. L'attivazione (§8.4.2) attivera'
    #   l'identita senza chiedere nuova password.
    #
    # Orchestrazione in transazione atomica: upsert auth_user, upsert
    # identita, [solo flow INVITO] set password temp + flag, genera token.
    # Fuori dalla transazione: invio email + timestamp. Rationale: il
    # token deve restare valido anche se l'email fallisce (recupero manuale).
    def _invia_invito_common(
        self,
        *,
        soggetto_ruolo_id: int,
        ruolo_applicativo: str,
        email: str,
        nome_destinatario: str,
        entita_label: str,
        invitato_da_user_id: int,
    ) -> dict[str, Any]:
        ErrorManager.require(
            "@" in email,
            code=E_INVITO_PORTALE,
            message="Email destinatario non valida.",
        )

        with transaction.atomic():
            auth_user_id, was_created = self._ensure_auth_user(
                email=email, nome_destinatario=nome_destinatario
            )
            # Branching flow: `was_created=True` significa auth_user nuovo
            # → flow INVITO, identita attivo=true + password temp.
            # `was_created=False` → flow CROSS, identita attivo=false + no password.
            is_cross = not was_created
            identita_id = self._ensure_identita(
                auth_user_id=auth_user_id,
                soggetto_ruolo_id=soggetto_ruolo_id,
                ruolo_applicativo=ruolo_applicativo,
                attivo=not is_cross,
            )

            if not is_cross:
                # Flow INVITO: password temporanea + flag deve_cambiare_password.
                # L'utente dovra' scegliere la password definitiva in attivazione.
                temp_password = secrets.token_urlsafe(16)
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE django.auth_user SET password = %s WHERE id = %s",
                        [make_password(temp_password), auth_user_id],
                    )
                self._auth_repo.set_deve_cambiare_password(
                    auth_user_id, True, identita_id=identita_id
                )

            token_tipo = (
                ATTIVAZIONE_PORTALE_CROSS_TOKEN_TIPO
                if is_cross
                else INVITO_PORTALE_TOKEN_TIPO
            )
            token_plain = self._token_service.create(
                tipo=token_tipo,
                auth_user_id=auth_user_id,
                scadenza_ore=INVITO_PORTALE_SCADENZA_ORE,
                meta={
                    "invitato_da_user_id": invitato_da_user_id,
                    "ruolo_applicativo": ruolo_applicativo,
                    "entita": entita_label,
                    "identita_id": identita_id,
                },
            )

        # Link di attivazione portale: path dedicato per distinguere dal
        # flow operatore. Il FE gestisce la rotta /attivazione-portale/:token
        # e distinguera' UX (set-password vs attiva-veste) in base al
        # token_type restituito dal BE in §8.4.2.
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        link = f"{frontend_url}/attivazione-portale/{token_plain}"

        invitato_da_nome = self._get_display_name_of(invitato_da_user_id)

        try:
            self._email_service.send_email(
                codice_template=_TEMPLATE_INVITO_PORTALE,
                destinatario=email,
                variabili={
                    "nome": nome_destinatario,
                    "entita": entita_label,
                    "azienda": "ZeroErp",
                    "link": link,
                    "scadenza_ore": str(INVITO_PORTALE_SCADENZA_ORE),
                    "invitato_da": invitato_da_nome,
                    "ruolo_applicativo": ruolo_applicativo,
                    # Flag leggibile dal template per differenziare
                    # "attiva il tuo account" (nuovo) vs "attiva l'accesso
                    # portale" (cross su utente esistente).
                    "is_cross": "1" if is_cross else "0",
                },
                ambito="SISTEMA",
                auth_user_id=auth_user_id,
            )
        except Exception:
            logger.exception(
                "Errore invio email invito portale user_id=%s ruolo=%s "
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
            password_hash="!",  # placeholder, verra' sovrascritto nel flow
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
    # - Non esiste: la crea con `attivo=attivo` e
    #   `deve_cambiare_password=attivo` (flow INVITO ha entrambi true, flow
    #   CROSS ha entrambi false — la password resta quella dell'utente).
    # - Esiste gia' ATTIVA: ERRORE `E_INVITO_PORTALE_GIA_ATTIVO` — l'utente
    #   ha gia' accesso al portale con quella veste; un nuovo invito non
    #   ha senso (se serve reset credenziali, il self-service password
    #   reset copre il caso). Copre sia primo-invito mal richiesto sia
    #   reinvio su identita gia' attivata (§8.4.1 BUG1).
    # - Esiste collegata ad un auth_user DIVERSO: ERRORE (stato incoerente
    #   del modello — soggetto_ruolo con holder diverso dall'auth_user
    #   risolto via email). Richiede intervento manuale, NON risolviamo
    #   automaticamente (§8.4.1 FRAG4).
    # - Esiste disattivata con auth_user coerente: e' il caso legittimo
    #   del reinvio di invito scaduto/non attivato:
    #   * flow INVITO (`attivo=True`): riattiva la riga, il caller
    #     rigenerera' comunque token + password.
    #   * flow CROSS (`attivo=False`): NON riattiva — l'attivazione avviene
    #     al consumo del token CROSS (§8.4.2).
    def _ensure_identita(
        self,
        *,
        auth_user_id: int,
        soggetto_ruolo_id: int,
        ruolo_applicativo: str,
        attivo: bool,
    ) -> int:
        existing = self._repo.find_identita_portale(
            soggetto_ruolo_id, ruolo_applicativo
        )
        if existing is None:
            return self._repo.create_identita_portale(
                auth_user_id=auth_user_id,
                soggetto_ruolo_id=soggetto_ruolo_id,
                ruolo_applicativo=ruolo_applicativo,
                attivo=attivo,
                deve_cambiare_password=attivo,
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

        # Identita disattivata in attesa di attivazione (caso reinvio
        # legittimo). Solo flow INVITO riattiva on-the-fly — il CROSS
        # delega l'attivazione al consumo del token CROSS.
        if attivo:
            self._repo.riattiva_identita(identita_id)
        return identita_id

    # Scopo: Invalida token portale residui (entrambi i tipi INVITO e
    # CROSS) per l'auth_user collegato a un soggetto_ruolo+ruolo_applicativo.
    # Usato in reinvio per consumare lo stato precedente qualunque sia il
    # flow con cui era stato creato.
    def _invalidate_existing_token(
        self, soggetto_ruolo_id: int, ruolo_applicativo: str
    ) -> None:
        existing = self._repo.find_identita_portale(
            soggetto_ruolo_id, ruolo_applicativo
        )
        if existing and existing.get("auth_user_id"):
            auth_user_id = int(existing["auth_user_id"])
            self._token_service.invalidate_all(
                INVITO_PORTALE_TOKEN_TIPO, auth_user_id
            )
            self._token_service.invalidate_all(
                ATTIVAZIONE_PORTALE_CROSS_TOKEN_TIPO, auth_user_id
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
