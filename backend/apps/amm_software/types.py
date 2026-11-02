# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: TypedDict per le righe ritornate dal repository amministrazione.
# ------------------------------------------------------------

from __future__ import annotations

from typing import NotRequired, TypedDict


class OperatoreRow(TypedDict):
    """Riga lista operatori."""
    auth_user_id: int
    username: str
    email: str
    first_name: str
    last_name: str
    soggetto_cognome: str | None
    soggetto_nome: str | None
    # Solo nella lista (colonna del catalogo e della ricerca, 2026-09-24): il
    # dettaglio lo compone `script.fn_get_operatore_detail`, che non la porta.
    soggetto_ragione_sociale: NotRequired[str | None]
    # Solo nella lista (2026-10-02): le altre vesti ATTIVE della credenziale
    # (codici di `config.ruolo_applicativo`), `[]` se non ne ha.
    altre_vesti: NotRequired[list[str]]
    # Solo nella lista (2026-10-06): gli override dei permessi scritti, da
    # `script.vw_override_operatore_area` (brief riepilogo-permessi).
    override_count: NotRequired[int]
    # Solo nella lista (2026-10-18): la credenziale porta l'etichetta di prova
    # (`dbops.credenziali_di_prova`, la mette solo il provisioning di sviluppo).
    # Non cambia la categoria: un utente di prova resta un operatore.
    di_prova: NotRequired[bool]
    is_super_admin: bool
    ruolo_applicativo: str | None
    is_active: bool
    unita_organizzativa_id: int | None
    unita_organizzativa_nome: str | None
    risorsa_umana_id: int | None
    attivo: bool | None
    valido_dal: str | None
    valido_al: str | None


class OperatoreDetailRow(OperatoreRow):
    """Riga dettaglio operatore con conteggi override e dati soggetto.

    Capability fields (Fase 1 multi-face, popolati da
    `script.fn_get_operatore_detail`):

    ⭐ Ogni motivo e' una COPPIA (dal ``20260927-02``, §16 del brief
    blocco-login): ``<verbo>_reason`` e' il **codice macchina** del primo
    motivo (``VESTE_GIA_ATTIVA``, ``ULTIMO_SUPER_ADMIN``…), NULL se l'azione
    e' ammessa; ``<verbo>_reason_key`` e' la **chiave i18n** della frase. Il
    testo non viaggia (api.md §«Capability di riga»): lo compone il FE.

    - ``can_invite``/``invite_reason``/``invite_reason_key``: derivati da
      ``script.fn_check_operatore_invitabile`` (``reason``/``reason_key``).
    - ``can_disable``/``disable_reason``: preview del trigger DB
      ``trgfn_profili_accesso_bindings_guard_ultimo_super_admin``. **Non e'
      una garanzia**: in caso di race tra sessioni l'UPDATE puo' comunque
      fallire con ``E_PROFILO_ULTIMO_SUPER_ADMIN``. Il trigger resta
      l'autorita'; il FE usa la preview solo per nascondere il pulsante UX.
      Motivo: ``disable_reason``/``disable_reason_key``.
    - ``can_demote_super_admin``/``demote_reason``/``demote_reason_key``:
      simmetrico per la rimozione del binding SUPER_ADMIN. Stesso codice di
      disable (la condizione e' una), chiave diversa (dice QUALE azione).
    - ``can_set_valido_al``/``valido_al_reason``/``valido_al_reason_key``:
      mettere una data di fine al rapporto (``20261007-27``). Stessa
      condizione di disable (l'ultimo SUPER_ADMIN senza data di fine), chiave
      sua. Un amministratore che ha gia' una data di fine risponde ``true``.
    """
    soggetto_id: str | None
    ragione_sociale_completa: str | None
    codice_fiscale: str | None
    override_aree_count: int
    override_azioni_count: int
    emittenti_count: int
    # Capability data-driven (Fase 1 multi-face)
    can_invite: bool
    invite_reason: str | None
    can_disable: bool
    disable_reason: str | None
    # NULL quando l'azione "demote" non e' applicabile (operatore non e'
    # SUPER_ADMIN): il FE nasconde l'azione invece di mostrarla disabled.
    can_demote_super_admin: bool | None
    demote_reason: str | None
    # Lo stato della veste OPERATORE (R-9, `fn_get_operatore_detail`): la
    # attiva se c'e', altrimenti la spenta piu' recente; NULL senza veste.
    # ⚠️ Non e' `attivo` (risorsa umana) ne' `is_active` (credenziale, da
    # tutte le vesti): e' l'unico campo che dice se QUESTA porta e' aperta.
    veste_attiva: bool | None
    # Le chiavi i18n dei tre motivi (§16, `20260927-02`, in coda come nel
    # RETURNS TABLE): NULL quando l'azione e' ammessa.
    invite_reason_key: str | None
    disable_reason_key: str | None
    demote_reason_key: str | None
    # La terna della data di fine del rapporto (brief-db-veste-utilizzabile
    # §10, `20261007-27`, in coda al RETURNS TABLE).
    can_set_valido_al: bool
    valido_al_reason: str | None
    valido_al_reason_key: str | None


class VesteCredenzialeRow(TypedDict):
    """Una veste della credenziale, come la costruisce il DB."""
    ruolo_applicativo: str
    attivo: bool
    # La denominazione del soggetto della veste (ragione_sociale_completa).
    soggetto: str | None


class CredenzialePerEmailRow(TypedDict):
    """La credenziale che porta un'email (`script.fn_get_credenziale_per_email`).

    Serve al dialog di conferma del riuso (B-20 del brief
    brief-db-credenziale-per-email): l'admin vede username e vesti, e conferma
    dichiarando ``auth_user_id``. La stessa lettura la usa la madre per il
    rifiuto ``E_CREDENZIALE_DA_CONFERMARE``: dialog e rifiuto mostrano la
    stessa cosa.
    """
    auth_user_id: int
    username: str
    # In ordine di id; lista vuota se la credenziale non ha vesti.
    vesti: list[VesteCredenzialeRow]
