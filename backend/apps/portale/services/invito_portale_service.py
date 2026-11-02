# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio invito "veste non-operatore" (CLIENTE_PORTALE,
#        FORNITORE_PORTALE, SHOP_CUSTOMER). Qui resta solo cio' che e' della
#        veste: risolvere l'entita' sorgente (clienti per CLIENTE_PORTALE e
#        SHOP_CUSTOMER, fornitori per FORNITORE_PORTALE) → soggetto_ruolo_id,
#        e creare se mancano credenziale e veste (spenta). Emissione del
#        token, reinvio, email e attivazione sono il building block unico
#        `apps.core.services.invito_veste` (L-3, regola del 2): la stessa
#        strada dell'operatore.
#
#        Il nome storico `InvitoPortaleService` resta (usage esterni), ma il
#        service gestisce anche SHOP_CUSTOMER.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from apps.core.db.auth_repository import AuthRepository
from apps.core.services.auth_constants import (
    RUOLO_APPLICATIVO_CLIENTE_PORTALE,
    RUOLO_APPLICATIVO_FORNITORE_PORTALE,
    RUOLO_APPLICATIVO_SHOP_CUSTOMER,
)
from apps.core.services.error_manager import ErrorManager
from apps.core.services.invito_veste import (
    PORTA_PORTALE,
    InvitoVeste,
    maschera_email,
    porta_della_veste,
)
from apps.portale.db.portale_repository import PortaleRepository

logger = logging.getLogger("security")

E_INVITO_PORTALE = PORTA_PORTALE.codice_invito


class InvitoPortaleService:
    """Gestione invito portale: verifica, crea identita, invia email."""

    def __init__(self) -> None:
        self._repo = PortaleRepository()
        self._auth_repo = AuthRepository()
        self._invito = InvitoVeste(auth_repo=self._auth_repo)

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
        info = self._cliente_info(cliente_id)
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
        info = self._fornitore_info(fornitore_id)
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
        # Fix analisi-fix-transazioni #17: l'invalidazione dei token della
        # veste sta DENTRO l'atomic dell'emissione (BB `InvitoVeste.emetti`,
        # sempre, non solo sul reinvio): l'utente non resta mai senza un
        # link valido se l'emissione fallisce.
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
        # Stessa strada dell'invito: vedi reinvia_invito_cliente.
        return self.invia_invito_fornitore(
            fornitore_id=fornitore_id,
            email=email,
            invitato_da_user_id=invitato_da_user_id,
        )

    # ── Stato + disattivazione veste (§6.2.4 + §6.2.6) ────────────────

    # Scopo: Stato aggregato delle vesti non-operatore di un cliente
    # (CLIENTE_PORTALE + SHOP_CUSTOMER). Un admin lo usa dal drawer per
    # decidere se "invita" (stato NESSUNO), "reinvia" (PENDING), "disattiva"
    # (ATTIVO) o "reinvia per riattivare" (DISATTIVO).
    def get_stato_accessi_cliente(self, cliente_id: int) -> dict[str, Any]:
        info = self._cliente_info(cliente_id)
        soggetto_ruolo_id = int(info["soggetto_ruolo_id"])
        return {
            "portale": self._repo.get_stato_identita(
                soggetto_ruolo_id,
                RUOLO_APPLICATIVO_CLIENTE_PORTALE,
            ),
            "shop": self._repo.get_stato_identita(
                soggetto_ruolo_id,
                RUOLO_APPLICATIVO_SHOP_CUSTOMER,
            ),
        }

    # Scopo: Stato aggregato delle vesti non-operatore di un fornitore
    # (solo FORNITORE_PORTALE; i fornitori non accedono allo shop B2C).
    def get_stato_accessi_fornitore(self, fornitore_id: int) -> dict[str, Any]:
        info = self._fornitore_info(fornitore_id)
        return {
            "portale": self._repo.get_stato_identita(
                int(info["soggetto_ruolo_id"]),
                RUOLO_APPLICATIVO_FORNITORE_PORTALE,
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
        info = self._cliente_info(cliente_id)
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
        info = self._fornitore_info(fornitore_id)
        return self._disattiva_veste_common(
            soggetto_ruolo_id=int(info["soggetto_ruolo_id"]),
            ruolo_applicativo=RUOLO_APPLICATIVO_FORNITORE_PORTALE,
            disattivato_da_user_id=disattivato_da_user_id,
        )

    # Scopo: core comune della disattivazione — risolve l'identita, la
    # disattiva se attiva, invalida i token pendenti, chiude le sessioni della
    # veste e la cache dei permessi. Tutto in una transazione: una chiusura
    # fallita annulla anche lo spegnimento.
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

        # Invalida i token pendenti della veste in ogni caso (anche su una
        # veste gia' spenta: un invito in volo smette di funzionare).
        # ⛔ E chiude le sessioni di QUESTA veste, con la cache dei permessi a
        #    commit avvenuto (A-5, D-5, 2026-10-02; BB
        #    `InvitoVeste.chiudi_veste_spenta`): gli stessi effetti dello
        #    spegnimento di una veste operatore. Fino a quel giorno portale e
        #    shop non chiudevano ne' sessioni ne' cache. Le sessioni delle altre
        #    vesti della credenziale restano: si filtra per `identita_id`.
        #    Anche su una veste gia' spenta: idempotente, e chiude le sessioni
        #    rimaste vive da prima di questa regola.
        porta = porta_della_veste(ruolo_applicativo)
        with transaction.atomic():
            if was_active:
                self._repo.disattiva_identita(identita_id)
            if auth_user_id is not None:
                self._invito.chiudi_veste_spenta(
                    porta, auth_user_id=auth_user_id, identita_id=identita_id,
                )

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
    # CROSS), porta risolta dal BB (`porta_della_veste`).
    def invia_invito_shop_customer(
        self,
        *,
        cliente_id: int,
        email: str,
        invitato_da_user_id: int,
    ) -> dict[str, Any]:
        email_clean = self._clean_email(email)
        info = self._cliente_info(cliente_id)
        return self._invia_invito_common(
            soggetto_ruolo_id=int(info["soggetto_ruolo_id"]),
            ruolo_applicativo=RUOLO_APPLICATIVO_SHOP_CUSTOMER,
            email=email_clean,
            nome_destinatario=self._build_display_name(info),
            entita_label=f"Shop customer {info.get('ba_codice') or cliente_id}",
            invitato_da_user_id=invitato_da_user_id,
        )

    # Scopo: Reinvia invito shop customer invalidando token precedenti.
    def reinvia_invito_shop_customer(
        self,
        *,
        cliente_id: int,
        email: str,
        invitato_da_user_id: int,
    ) -> dict[str, Any]:
        # Stessa strada dell'invito: vedi reinvia_invito_cliente.
        return self.invia_invito_shop_customer(
            cliente_id=cliente_id,
            email=email,
            invitato_da_user_id=invitato_da_user_id,
        )

    # Scopo: Flusso comune invito (cliente+fornitore+shop). Qui la parte
    # della veste: credenziale (riusata per email o creata col segnaposto
    # non utilizzabile) e veste SPENTA, in transazione. Il resto e' il BB
    # `InvitoVeste` (regola unica, analisi §4.2): flusso scelto sulla
    # credenziale (password vera → attivazione con un clic, altrimenti la
    # persona la sceglie), token pendenti della VESTE invalidati nella
    # stessa transazione del nuovo, email fuori transazione (se fallisce il token
    # resta valido). ⛔ La veste la accende solo il consumo del token (M-3).
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

        porta = porta_della_veste(ruolo_applicativo)

        with transaction.atomic():
            auth_user_id, was_created = self._ensure_auth_user(
                email=email, nome_destinatario=nome_destinatario
            )
            identita_id = self._ensure_identita(
                auth_user_id=auth_user_id,
                soggetto_ruolo_id=soggetto_ruolo_id,
                ruolo_applicativo=ruolo_applicativo,
            )
            # Flusso sulla credenziale, token pendenti della veste invalidati
            # nella stessa transazione: BB.
            emissione = self._invito.emetti(
                porta,
                auth_user_id=auth_user_id,
                identita_id=identita_id,
                ruolo_applicativo=ruolo_applicativo,
                invitato_da_user_id=invitato_da_user_id,
                meta={"entita": entita_label},
            )

        # ⭐ `inviato` e' l'esito della MAIL, non della chiamata (F-3): il
        #    token c'e' comunque, e il client con `false` dice di reinviare.
        inviato = self._invito.spedisci(
            porta,
            emissione,
            auth_user_id=auth_user_id,
            identita_id=identita_id,
            destinatario=email,
            invitato_da_user_id=invitato_da_user_id,
            variabili={
                "nome": nome_destinatario,
                "entita": entita_label,
                "ruolo_applicativo": ruolo_applicativo,
            },
        )

        logger.info(
            "security.invito_portale_inviato user_id=%s ruolo=%s da=%s "
            "created_user=%s is_cross=%s identita_id=%s inviato=%s",
            auth_user_id,
            ruolo_applicativo,
            invitato_da_user_id,
            was_created,
            emissione.is_cross,
            identita_id,
            inviato,
        )

        return {
            "inviato": inviato,
            "email": maschera_email(email),
            "auth_user_id": auth_user_id,
            "identita_id": identita_id,
            "nuovo_utente": was_created,
            "is_cross": emissione.is_cross,
        }

    # Scopo: Restituisce l'auth_user_id se esiste per quell'email, altrimenti
    # ne crea uno nuovo. Il second flag (bool) indica se e' stato creato.
    def _ensure_auth_user(
        self, *, email: str, nome_destinatario: str
    ) -> tuple[int, bool]:
        existing = self._auth_repo.find_auth_user_id_per_email(email)
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
            password_hash="!",  # noqa: S106 — "!" = password inutilizzabile (convenzione Django), non un segreto
            first_name=first,
            last_name=last,
        )
        return new_id, True

    # Scopo: Garantisce che esista un'identita digitale portale per la
    # coppia (soggetto_ruolo_id, ruolo_applicativo). Ritorna l'`identita_id`
    # (nuova o esistente) per consentire al caller di puntare la riga
    # giusta negli UPDATE successivi (pattern richiesto dal modello 1:N
    # §8.4.1, vedi `set_invito_inviato_at`).
    #
    # Comportamento per stato identita:
    # - Non esiste: la crea `attivo=false`, in entrambi i flussi. Si attiva
    #   al consumo del token.
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

    # Scopo: L'entita' di partenza dell'invito, o 404. Cliente e fornitore
    # indicati dall'URL che non esistono sono un «non trovato» (E-4 di
    # analisi-be-difetti-emersi-verifica-doc-api-core): fino al 2026-10-08
    # uscivano `E_INVITO_PORTALE` (DATO_ERRATO), cioe' 400, da sette punti
    # scritti uguali. `cliente_id` e `fornitore_id` sono le PK di
    # anagrafiche.clienti / anagrafiche.fornitori: le stesse che nominano
    # `E_CLIENTE_NON_TROVATO` (fn_update_cliente) ed `E_FORNITORE_NON_TROVATO`
    # (fn_guard_fornitore_attivo).
    def _cliente_info(self, cliente_id: int) -> dict[str, Any]:
        info = self._repo.get_cliente_info(cliente_id)
        ErrorManager.require(
            info is not None,
            code="E_CLIENTE_NON_TROVATO",
            message=f"Cliente {cliente_id} non trovato.",
            context={"cliente_id": cliente_id},
        )
        assert info is not None
        return info

    def _fornitore_info(self, fornitore_id: int) -> dict[str, Any]:
        info = self._repo.get_fornitore_info(fornitore_id)
        ErrorManager.require(
            info is not None,
            code="E_FORNITORE_NON_TROVATO",
            message=f"Fornitore {fornitore_id} non trovato.",
            context={"fornitore_id": fornitore_id},
        )
        assert info is not None
        return info

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
