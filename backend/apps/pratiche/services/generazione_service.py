# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio applicativo per generazione cross-pratica.
#        Gestisce generazione manuale (regole auto=false),
#        lookup regole applicabili e pratiche generate.
# ------------------------------------------------------------

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.pratiche.db.generazione_repository import GenerazioneRepository
from apps.pratiche.db.pratiche_repository import PraticheRepository
from apps.pratiche.types import PraticaRow, RegolaGenerazioneRow


# Scopo: Generazione manuale di una pratica da un flusso con regola auto=false.
# Obiettivo: l'utente sceglie esplicitamente quando generare.
# Perimetro: validazione flusso/regola, delega a fn_genera_pratica_da_flusso.
# Risultato: ID della pratica generata.
@transaction.atomic()
def genera_pratica_manuale(flusso_id: int, regola_id: int) -> int:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    ErrorManager.require(
        regola_id > 0,
        code="E_INVALID_ID",
        message="regola_id deve essere > 0",
    )

    # Verifica che il flusso esista.
    pratiche_repo = PraticheRepository()
    flusso = pratiche_repo.get_flusso(flusso_id)
    ErrorManager.require(
        flusso is not None,
        code="E_FLUSSO_NOT_FOUND",
        message=f"Flusso {flusso_id} non trovato",
    )
    assert flusso is not None

    gen_repo = GenerazioneRepository()
    return gen_repo.genera_pratica_manuale(flusso_id, regola_id)


# Scopo: Restituisce le regole di generazione applicabili al flusso.
# Lookup basato sul template_flusso_id del flusso.
def get_regole_applicabili(flusso_id: int) -> list[RegolaGenerazioneRow]:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )

    pratiche_repo = PraticheRepository()
    flusso = pratiche_repo.get_flusso(flusso_id)
    ErrorManager.require(
        flusso is not None,
        code="E_FLUSSO_NOT_FOUND",
        message=f"Flusso {flusso_id} non trovato",
    )
    assert flusso is not None

    if flusso["template_flusso_id"] is None:
        return []

    gen_repo = GenerazioneRepository()
    return gen_repo.list_regole_generazione(flusso["template_flusso_id"])


# Scopo: Restituisce le pratiche generate da un flusso (via flusso_origine_id).
def get_pratiche_generate(flusso_id: int) -> list[PraticaRow]:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )

    gen_repo = GenerazioneRepository()
    return gen_repo.get_pratiche_generate_da_flusso(flusso_id)
