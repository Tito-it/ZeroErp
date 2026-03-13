# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: TypedDict per le righe ritornate dal repository amministrazione.
# ------------------------------------------------------------

from __future__ import annotations

from typing import TypedDict


class UtenteRow(TypedDict):
    """Riga lista utenti."""
    auth_user_id: int
    username: str
    email: str
    first_name: str
    last_name: str
    ruolo_sistema: str | None
    is_active: bool
    unita_organizzativa_id: int | None
    unita_organizzativa_nome: str | None
    risorsa_umana_id: int | None
    attivo: bool | None
    valido_al: str | None
    data_insert: str | None


class UtenteDetailRow(UtenteRow):
    """Riga dettaglio utente con conteggi override."""
    override_aree_count: int
    override_azioni_count: int
    emittenti_count: int
