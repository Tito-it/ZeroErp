# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio applicativo modulo pratiche.
#        Facade per operazioni su pratiche, flussi, prerequisiti,
#        giornale e handler dispatch.
#        Progettato come API interna cross-dominio: altre app Django
#        (vendite, anagrafiche, acquisti) importano e usano queste
#        funzioni per creare/gestire pratiche legate ai propri eventi.
# ------------------------------------------------------------

from typing import Any

from django.db import transaction

from apps.core.services.error_manager import ErrorManager
from apps.pratiche.db.pratiche_repository import PraticheRepository
from apps.pratiche.types import (
    CanalePraticaRow,
    GiornaleRow,
    PraticaRow,
    PrerequisitoCheckRow,
)

# -- PRATICHE --------------------------------------------------------


# Scopo: Crea una nuova pratica con stato iniziale BOZZA.
# Obiettivo: entry point per creazione pratica da qualsiasi dominio.
# Perimetro: risolve stato iniziale, delega INSERT al repository.
# Risultato: ID della pratica creata.
@transaction.atomic()
def crea_pratica(
    *,
    emittente_fiscale_id: int,
    tipo_prestazione_id: int,
    soggetto_id: str | None = None,
    priorita_id: int,
    risorsa_umana_id: int | None = None,
    unita_organizzativa_id: int | None = None,
    canale_origine_id: int | None = None,
    solo_interna: bool = False,
    descrizione: str | None = None,
    data_scadenza: str | None = None,
    meta: dict[str, Any] | None = None,
) -> int:
    ErrorManager.require(
        emittente_fiscale_id > 0,
        code="E_PRATICA_VALIDATION",
        message="emittente_fiscale_id obbligatorio e > 0",
    )
    assert emittente_fiscale_id > 0
    ErrorManager.require(
        tipo_prestazione_id > 0,
        code="E_PRATICA_VALIDATION",
        message="tipo_prestazione_id obbligatorio e > 0",
    )
    assert tipo_prestazione_id > 0
    ErrorManager.require(
        priorita_id > 0,
        code="E_PRATICA_VALIDATION",
        message="priorita_id obbligatorio e > 0",
    )
    assert priorita_id > 0

    # Risolve stato iniziale BOZZA.
    repo = PraticheRepository()
    stato_id = repo.resolve_stato_pratica("BOZZA")
    return repo.create_pratica({
        "emittente_fiscale_id": emittente_fiscale_id,
        "tipo_prestazione_id": tipo_prestazione_id,
        "soggetto_id": soggetto_id,
        "stato_id": stato_id,
        "priorita_id": priorita_id,
        "risorsa_umana_id": risorsa_umana_id,
        "unita_organizzativa_id": unita_organizzativa_id,
        "canale_origine_id": canale_origine_id,
        "solo_interna": solo_interna,
        "descrizione": descrizione,
        "data_scadenza": data_scadenza,
        "meta": meta or {},
    })


# Scopo: Aggiorna i campi modificabili di una pratica.
@transaction.atomic()
def aggiorna_pratica(pratica_id: int, data: dict[str, Any]) -> None:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    assert pratica_id > 0

    repo = PraticheRepository()
    # Verifica esistenza pratica.
    pratica = repo.get_pratica(pratica_id)
    ErrorManager.require(
        pratica is not None,
        code="E_PRATICA_NOT_FOUND",
        message=f"Pratica {pratica_id} non trovata",
    )
    assert pratica is not None

    repo.update_pratica(pratica_id, data)


# Scopo: Transizione di stato di una pratica tramite codice_interno.
@transaction.atomic()
def cambia_stato_pratica(pratica_id: int, nuovo_stato: str) -> None:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    assert pratica_id > 0
    ErrorManager.require(
        bool(nuovo_stato),
        code="E_PRATICA_VALIDATION",
        message="nuovo_stato obbligatorio",
    )

    repo = PraticheRepository()
    repo.update_stato_pratica(pratica_id, nuovo_stato)


# Scopo: Assegna una pratica a risorsa umana e/o unita' organizzativa.
def assegna_pratica(
    pratica_id: int,
    *,
    risorsa_umana_id: int | None = None,
    unita_organizzativa_id: int | None = None,
) -> None:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    assert pratica_id > 0

    repo = PraticheRepository()
    update_data: dict[str, Any] = {}
    if risorsa_umana_id is not None:
        update_data["risorsa_umana_id"] = risorsa_umana_id
    if unita_organizzativa_id is not None:
        update_data["unita_organizzativa_id"] = unita_organizzativa_id

    if update_data:
        repo.update_pratica(pratica_id, update_data)


# Scopo: Ricerca pratiche con filtri e paginazione.
def cerca_pratiche(
    *,
    emittente_fiscale_id: int,
    stato_codice_interno: str | None = None,
    tipo_prestazione_id: int | None = None,
    soggetto_id: str | None = None,
    solo_interna: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[PraticaRow], int]:
    repo = PraticheRepository()
    return repo.list_pratiche(
        emittente_fiscale_id=emittente_fiscale_id,
        stato_codice_interno=stato_codice_interno,
        tipo_prestazione_id=tipo_prestazione_id,
        soggetto_id=soggetto_id,
        solo_interna=solo_interna,
        limit=limit,
        offset=offset,
    )


# -- FLUSSI ----------------------------------------------------------


# Scopo: Crea un nuovo flusso per una pratica.
# Il trigger DB valida i prerequisiti automaticamente (guard).
# Se il trigger blocca l'INSERT, il DB solleva un errore gestito dal middleware.
@transaction.atomic()
def crea_flusso(
    *,
    pratica_id: int,
    template_flusso_id: int | None = None,
    risorsa_umana_id: int | None = None,
    unita_organizzativa_id: int | None = None,
    sequenza: int = 0,
    data_scadenza: str | None = None,
    meta: dict[str, Any] | None = None,
) -> int:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    assert pratica_id > 0

    # Risolve stato iniziale DA_ESEGUIRE.
    repo = PraticheRepository()
    stato_id = repo.resolve_stato_flusso("DA_ESEGUIRE")
    return repo.create_flusso({
        "pratica_id": pratica_id,
        "template_flusso_id": template_flusso_id,
        "stato_id": stato_id,
        "risorsa_umana_id": risorsa_umana_id,
        "unita_organizzativa_id": unita_organizzativa_id,
        "sequenza": sequenza,
        "data_scadenza": data_scadenza,
        "meta": meta or {},
    })


# Scopo: Transizione flusso DA_ESEGUIRE → IN_CORSO.
@transaction.atomic()
def avvia_flusso(flusso_id: int) -> None:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    assert flusso_id > 0

    repo = PraticheRepository()
    repo.update_stato_flusso(flusso_id, "IN_CORSO")


# Scopo: Completa un flusso con esito e note.
# Obiettivo: transizione → COMPLETATO. La generazione automatica
# cross-pratica e' gestita dal trigger DB (trgfn_flussi_generazione).
@transaction.atomic()
def completa_flusso(
    flusso_id: int,
    *,
    esito: str,
    note_esito: str | None = None,
) -> None:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    assert flusso_id > 0
    ErrorManager.require(
        esito in ("POSITIVO", "NEGATIVO", "PARZIALE", "NON_APPLICABILE"),
        code="E_FLUSSO_VALIDATION",
        message=f"Esito non valido: {esito}",
    )

    repo = PraticheRepository()
    repo.update_stato_flusso(flusso_id, "COMPLETATO", esito=esito, note_esito=note_esito)


# Scopo: Transizione generica di stato di un flusso tramite codice_interno.
# Obiettivo: gestisce transizioni diverse da IN_CORSO/COMPLETATO (es. SOSPESO, ANNULLATO).
@transaction.atomic()
def cambia_stato_flusso(
    flusso_id: int,
    nuovo_stato: str,
    *,
    esito: str | None = None,
    note_esito: str | None = None,
) -> None:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    assert flusso_id > 0
    ErrorManager.require(
        bool(nuovo_stato),
        code="E_FLUSSO_VALIDATION",
        message="nuovo_stato obbligatorio",
    )

    repo = PraticheRepository()
    repo.update_stato_flusso(flusso_id, nuovo_stato, esito=esito, note_esito=note_esito)


# Scopo: Verifica prerequisiti per un template flusso su una pratica (per UI/preview).
def verifica_prerequisiti(
    pratica_id: int, template_flusso_id: int,
) -> list[PrerequisitoCheckRow]:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    assert pratica_id > 0

    repo = PraticheRepository()
    return repo.check_prerequisiti(pratica_id, template_flusso_id)


# Scopo: Restituisce i canali abilitati per un template flusso.
def get_canali_disponibili(template_flusso_id: int) -> list[CanalePraticaRow]:
    repo = PraticheRepository()
    return repo.get_canali_flusso(template_flusso_id)


# Scopo: Invoca l'handler Django configurato per il flusso.
# Obiettivo: dispatch automatico se il template flusso ha un handler_key.
# Perimetro: lookup handler dal registry, invocazione execute().
def dispatch_handler(flusso_id: int) -> dict[str, Any] | None:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    assert flusso_id > 0

    repo = PraticheRepository()
    flusso = repo.get_flusso(flusso_id)
    ErrorManager.require(
        flusso is not None,
        code="E_FLUSSO_NOT_FOUND",
        message=f"Flusso {flusso_id} non trovato",
    )
    assert flusso is not None

    if flusso["template_flusso_id"] is None:
        return None

    # Lookup handler_key dal template flusso.
    handler_key = repo.get_handler_key(flusso["template_flusso_id"])
    if handler_key is None:
        return None

    from apps.pratiche.services.handler_registry import get_handler
    handler_class = get_handler(handler_key)
    if handler_class is None:
        return None

    handler = handler_class()
    return handler.execute(
        flusso_id=flusso_id,
        pratica_id=flusso["pratica_id"],
        meta=flusso["meta"],
    )


# Scopo: Restituisce il giornale di bordo di una pratica.
def get_giornale(
    pratica_id: int, *, limit: int = 100, offset: int = 0,
) -> tuple[list[GiornaleRow], int]:
    repo = PraticheRepository()
    return repo.get_giornale_pratica(pratica_id, limit=limit, offset=offset)


