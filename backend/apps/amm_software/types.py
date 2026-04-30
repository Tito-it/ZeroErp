# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: TypedDict per le righe ritornate dal repository amministrazione.
# ------------------------------------------------------------

from __future__ import annotations

from typing import TypedDict


class OperatoreRow(TypedDict):
    """Riga lista operatori."""
    auth_user_id: int
    username: str
    email: str
    first_name: str
    last_name: str
    soggetto_cognome: str | None
    soggetto_nome: str | None
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

    - ``can_invite``/``invite_reason``: derivati da
      ``script.fn_check_operatore_invitabile``. ``invite_reason`` e' una
      stringa libera it-IT (vedi nota team DB sul pattern attuale; eventuale
      futura migrazione a codici stabili va coordinata col FE che oggi
      mostra il testo cosi' com'e').
    - ``can_disable``/``disable_reason``: preview del trigger DB
      ``trgfn_profili_accesso_bindings_guard_ultimo_super_admin``. **Non e'
      una garanzia**: in caso di race tra sessioni l'UPDATE puo' comunque
      fallire con ``E_PROFILO_ULTIMO_SUPER_ADMIN``. Il trigger resta
      l'autorita'; il FE usa la preview solo per nascondere il pulsante UX.
    - ``can_demote_super_admin``/``demote_reason``: simmetrico per la
      rimozione del binding SUPER_ADMIN.
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
