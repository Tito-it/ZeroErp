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
from apps.core.services.service_errors import ServiceError
from apps.pratiche.db.pratiche_repository import PraticheRepository

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
    soggetto_ruolo_id: int | None = None,
    istanza_utility_id: int | None = None,
    priorita_id: int,
    risorsa_umana_id: int | None = None,
    unita_organizzativa_id: int | None = None,
    canale_origine_id: int | None = None,
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

    # Validazione coerenza contesto anagrafico (stesse regole del trigger DB,
    # qui per dare errori user-friendly via ServiceError).
    if istanza_utility_id is not None:
        ErrorManager.require(
            soggetto_ruolo_id is not None,
            code="E_PRATICA_VALIDATION",
            message="istanza_utility_id richiede soggetto_ruolo_id",
        )
    if soggetto_ruolo_id is not None:
        ErrorManager.require(
            soggetto_id is not None,
            code="E_PRATICA_VALIDATION",
            message="soggetto_ruolo_id richiede soggetto_id",
        )

    # Guard pre/post-attivazione: verifica ammissibilita' tipo prestazione
    # in base allo stato del billing_account del soggetto.
    repo = PraticheRepository()
    tipo_att = repo.get_tipo_prestazione_attivazione(tipo_prestazione_id)
    if soggetto_id is not None and not (tipo_att["pre_attivazione"] and tipo_att["post_attivazione"]):
        ha_ba = repo.ha_ba_attivo(soggetto_id, emittente_fiscale_id)
        if not tipo_att["pre_attivazione"] and not ha_ba:
            raise ServiceError(
                code="E_PRATICA_VALIDATION",
                message="Tipo prestazione ammesso solo per clienti attivati (post-attivazione).",
            )
        if not tipo_att["post_attivazione"] and ha_ba:
            raise ServiceError(
                code="E_PRATICA_VALIDATION",
                message="Tipo prestazione ammesso solo prima dell'attivazione cliente (pre-attivazione).",
            )

    # Risolve stato iniziale BOZZA.
    stato_id = repo.resolve_stato_pratica("BOZZA")
    return repo.create_pratica({
        "emittente_fiscale_id": emittente_fiscale_id,
        "tipo_prestazione_id": tipo_prestazione_id,
        "soggetto_id": soggetto_id,
        "soggetto_ruolo_id": soggetto_ruolo_id,
        "istanza_utility_id": istanza_utility_id,
        "stato_id": stato_id,
        "priorita_id": priorita_id,
        "risorsa_umana_id": risorsa_umana_id,
        "unita_organizzativa_id": unita_organizzativa_id,
        "canale_origine_id": canale_origine_id,
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
    search: str | None = None,
    data_da: str | None = None,
    data_a: str | None = None,
    limit: int = 50,
    offset: int = 0,
    order_by: str = "data_insert",
    order_dir: str = "desc",
) -> tuple[list[dict[str, Any]], int]:
    repo = PraticheRepository()
    return repo.list_pratiche(
        emittente_fiscale_id=emittente_fiscale_id,
        stato_codice_interno=stato_codice_interno,
        tipo_prestazione_id=tipo_prestazione_id,
        soggetto_id=soggetto_id,
        search=search,
        data_da=data_da,
        data_a=data_a,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
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
) -> list[dict[str, Any]]:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    assert pratica_id > 0

    repo = PraticheRepository()
    return repo.check_prerequisiti(pratica_id, template_flusso_id)


# Scopo: Restituisce i canali abilitati per un template flusso.
def get_canali_disponibili(template_flusso_id: int) -> list[dict[str, Any]]:
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

    # Lookup handler_key e handler_params dal template flusso.
    handler_info = repo.get_handler_info(flusso["template_flusso_id"])
    if handler_info is None:
        return None

    handler_key, handler_params = handler_info

    from apps.pratiche.services.handler_registry import get_handler
    handler_class = get_handler(handler_key)
    if handler_class is None:
        return None

    handler = handler_class()
    return handler.execute(
        flusso_id=flusso_id,
        pratica_id=flusso["pratica_id"],
        meta=flusso["meta"],
        handler_params=handler_params,
    )


# Scopo: Restituisce il giornale di bordo di una pratica.
def get_giornale(
    pratica_id: int, *, limit: int = 100, offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    repo = PraticheRepository()
    return repo.get_giornale_pratica(pratica_id, limit=limit, offset=offset)


# -- NOTE PRATICHE --------------------------------------------------------


# Scopo: Restituisce le note di una pratica.
def get_note_pratica(pratica_id: int) -> list[dict[str, Any]]:
    ErrorManager.require(pratica_id > 0, code="E_INVALID_ID", message="pratica_id deve essere > 0")
    repo = PraticheRepository()
    return repo.list_note_pratica(pratica_id)


# Scopo: Crea una nota per la pratica.
@transaction.atomic()
def crea_nota_pratica(pratica_id: int, tipo_nota_codice: str, contenuto: str) -> int:
    ErrorManager.require(pratica_id > 0, code="E_INVALID_ID", message="pratica_id deve essere > 0")
    ErrorManager.require(
        bool(tipo_nota_codice and tipo_nota_codice.strip()),
        code="E_PRATICA_VALIDATION", message="tipo_nota_codice obbligatorio",
    )
    ErrorManager.require(
        bool(contenuto and contenuto.strip()),
        code="E_PRATICA_VALIDATION", message="contenuto nota obbligatorio",
    )
    repo = PraticheRepository()
    return repo.create_nota_pratica(pratica_id, tipo_nota_codice.strip(), contenuto.strip())


# Scopo: Aggiorna il contenuto di una nota.
@transaction.atomic()
def aggiorna_nota_pratica(nota_id: int, pratica_id: int, contenuto: str) -> None:
    ErrorManager.require(pratica_id > 0, code="E_INVALID_ID", message="pratica_id deve essere > 0")
    ErrorManager.require(nota_id > 0, code="E_INVALID_ID", message="nota_id deve essere > 0")
    ErrorManager.require(
        bool(contenuto and contenuto.strip()),
        code="E_PRATICA_VALIDATION", message="contenuto nota obbligatorio",
    )
    repo = PraticheRepository()
    updated = repo.update_nota_pratica(nota_id, pratica_id, contenuto.strip())
    ErrorManager.require(updated, code="E_NOT_FOUND", message=f"Nota {nota_id} non trovata per pratica {pratica_id}")


# Scopo: Elimina una nota.
@transaction.atomic()
def elimina_nota_pratica(nota_id: int, pratica_id: int) -> None:
    ErrorManager.require(pratica_id > 0, code="E_INVALID_ID", message="pratica_id deve essere > 0")
    ErrorManager.require(nota_id > 0, code="E_INVALID_ID", message="nota_id deve essere > 0")
    repo = PraticheRepository()
    deleted = repo.delete_nota_pratica(nota_id, pratica_id)
    ErrorManager.require(deleted, code="E_NOT_FOUND", message=f"Nota {nota_id} non trovata per pratica {pratica_id}")


# -- ALLEGATI PRATICHE ---------------------------------------------------


# Scopo: Restituisce gli allegati di una pratica.
def get_allegati_pratica(pratica_id: int) -> list[dict[str, Any]]:
    ErrorManager.require(pratica_id > 0, code="E_INVALID_ID", message="pratica_id deve essere > 0")
    repo = PraticheRepository()
    return repo.list_allegati_pratica(pratica_id)


# Scopo: Crea un record allegato per la pratica (metadati, senza upload file).
@transaction.atomic()
def crea_allegato_pratica(
    pratica_id: int, tipo_allegato_codice: str, nome_file: str,
    *, percorso: str | None = None, mime_type: str | None = None,
    dimensione: int | None = None,
) -> int:
    ErrorManager.require(pratica_id > 0, code="E_INVALID_ID", message="pratica_id deve essere > 0")
    ErrorManager.require(
        bool(tipo_allegato_codice and tipo_allegato_codice.strip()),
        code="E_PRATICA_VALIDATION", message="tipo_allegato_codice obbligatorio",
    )
    ErrorManager.require(
        bool(nome_file and nome_file.strip()),
        code="E_PRATICA_VALIDATION", message="nome_file obbligatorio",
    )
    repo = PraticheRepository()
    return repo.create_allegato_pratica(
        pratica_id, tipo_allegato_codice.strip(), nome_file.strip(),
        percorso=percorso, mime_type=mime_type, dimensione=dimensione,
    )


# Scopo: Elimina un allegato.
@transaction.atomic()
def elimina_allegato_pratica(allegato_id: int, pratica_id: int) -> None:
    ErrorManager.require(pratica_id > 0, code="E_INVALID_ID", message="pratica_id deve essere > 0")
    ErrorManager.require(allegato_id > 0, code="E_INVALID_ID", message="allegato_id deve essere > 0")
    repo = PraticheRepository()
    deleted = repo.delete_allegato_pratica(allegato_id, pratica_id)
    ErrorManager.require(deleted, code="E_NOT_FOUND", message=f"Allegato {allegato_id} non trovato per pratica {pratica_id}")


# -- SOSPENSIONI --------------------------------------------------------


# Scopo: Sospende un'intera pratica.
# Obiettivo: crea una riga in pratiche.sospensioni con flusso_id NULL.
# Perimetro: valida input, cambia stato pratica a SOSPESA, INSERT sospensione.
#   I trigger DB propagano la sospensione ai flussi attivi e registrano nel giornale.
# Risultato: ID della sospensione creata.
@transaction.atomic()
def sospendi_pratica(
    pratica_id: int,
    motivo: str,
    *,
    data_riattivazione_prevista: str | None = None,
) -> int:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    assert pratica_id > 0
    ErrorManager.require(
        bool(motivo and motivo.strip()),
        code="E_PRATICA_VALIDATION",
        message="motivo sospensione obbligatorio",
    )

    repo = PraticheRepository()

    # Verifica che non ci sia gia' una sospensione attiva sulla pratica.
    sosp_attiva = repo.get_sospensione_attiva_pratica(pratica_id)
    ErrorManager.require(
        sosp_attiva is None,
        code="E_PRATICA_VALIDATION",
        message=f"Pratica {pratica_id} ha gia' una sospensione attiva",
    )

    # Cambia stato pratica a SOSPESA (il trigger DB valida la transizione).
    repo.update_stato_pratica(pratica_id, "SOSPESA")

    # INSERT sospensione: il trigger DB propaga ai flussi e registra nel giornale.
    return repo.create_sospensione(
        pratica_id,
        motivo,
        data_riattivazione_prevista=data_riattivazione_prevista,
    )


# Scopo: Riattiva una pratica sospesa.
# Obiettivo: chiude la sospensione attiva impostando data_fine = NOW().
# Perimetro: valida esistenza sospensione attiva, delega chiusura al repository.
#   Il trigger DB ripristina gli stati dei flussi, cambia stato pratica ad APERTA
#   e registra nel giornale.
@transaction.atomic()
def riattiva_pratica(pratica_id: int) -> None:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    assert pratica_id > 0

    repo = PraticheRepository()

    # Cerca la sospensione attiva (flusso_id IS NULL).
    sosp_attiva = repo.get_sospensione_attiva_pratica(pratica_id)
    ErrorManager.require(
        sosp_attiva is not None,
        code="E_PRATICA_VALIDATION",
        message=f"Pratica {pratica_id} non ha sospensione attiva",
    )
    assert sosp_attiva is not None

    # Cambia stato pratica ad APERTA (il trigger DB valida la transizione).
    repo.update_stato_pratica(pratica_id, "APERTA")

    # Chiude la sospensione: il trigger DB riattiva i flussi e registra nel giornale.
    repo.chiudi_sospensione(sosp_attiva["id"])


# Scopo: Verifica che il flusso esista e appartenga alla pratica indicata.
def _verifica_flusso_pratica(
    repo: PraticheRepository, pratica_id: int, flusso_id: int,
) -> dict[str, Any]:
    flusso = repo.get_flusso(flusso_id)
    ErrorManager.require(
        flusso is not None,
        code="E_FLUSSO_NOT_FOUND",
        message=f"Flusso {flusso_id} non trovato",
    )
    assert flusso is not None
    ErrorManager.require(
        flusso["pratica_id"] == pratica_id,
        code="E_FLUSSO_OWNERSHIP",
        message=f"Flusso {flusso_id} non appartiene alla pratica {pratica_id}",
    )
    return flusso


# Scopo: Sospende un singolo flusso all'interno di una pratica.
# Obiettivo: crea una sospensione con flusso_id specifico.
# Perimetro: valida input, verifica ownership flusso/pratica, INSERT sospensione.
#   Il trigger DB cambia stato del flusso a SOSPESO e registra nel giornale.
# Risultato: ID della sospensione creata.
@transaction.atomic()
def sospendi_flusso(
    pratica_id: int,
    flusso_id: int,
    motivo: str,
    *,
    data_riattivazione_prevista: str | None = None,
) -> int:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    assert pratica_id > 0
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    assert flusso_id > 0
    ErrorManager.require(
        bool(motivo and motivo.strip()),
        code="E_FLUSSO_VALIDATION",
        message="motivo sospensione obbligatorio",
    )

    repo = PraticheRepository()
    _verifica_flusso_pratica(repo, pratica_id, flusso_id)

    # Verifica che non ci sia gia' una sospensione attiva sul flusso.
    sosp_attiva = repo.get_sospensione_attiva_flusso(pratica_id, flusso_id)
    ErrorManager.require(
        sosp_attiva is None,
        code="E_FLUSSO_VALIDATION",
        message=f"Flusso {flusso_id} ha gia' una sospensione attiva",
    )

    # Cambia stato flusso a SOSPESO (il trigger DB valida la transizione).
    repo.update_stato_flusso(flusso_id, "SOSPESO")

    # INSERT sospensione con flusso_id: il trigger DB registra nel giornale.
    return repo.create_sospensione(
        pratica_id,
        motivo,
        flusso_id=flusso_id,
        data_riattivazione_prevista=data_riattivazione_prevista,
    )


# Scopo: Riattiva un singolo flusso sospeso.
# Obiettivo: chiude la sospensione attiva del flusso.
# Perimetro: valida esistenza sospensione attiva, delega chiusura al repository.
#   Il trigger DB ripristina lo stato del flusso e registra nel giornale.
@transaction.atomic()
def riattiva_flusso(pratica_id: int, flusso_id: int) -> None:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    assert pratica_id > 0
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    assert flusso_id > 0

    repo = PraticheRepository()
    _verifica_flusso_pratica(repo, pratica_id, flusso_id)

    # Cerca la sospensione attiva per il flusso specifico.
    sosp_attiva = repo.get_sospensione_attiva_flusso(pratica_id, flusso_id)
    ErrorManager.require(
        sosp_attiva is not None,
        code="E_FLUSSO_VALIDATION",
        message=f"Flusso {flusso_id} non ha sospensione attiva",
    )
    assert sosp_attiva is not None

    # Cambia stato flusso a IN_CORSO (ripresa manuale — il trigger DB valida la transizione).
    repo.update_stato_flusso(flusso_id, "IN_CORSO")

    # Chiude la sospensione: il trigger DB registra nel giornale.
    repo.chiudi_sospensione(sosp_attiva["id"])


# -- SOSPENSIONI LETTURA ------------------------------------------------


# Scopo: Restituisce le sospensioni di una pratica.
def get_sospensioni(pratica_id: int) -> list[dict[str, Any]]:
    repo = PraticheRepository()
    return repo.list_sospensioni(pratica_id)


# -- CALCOLI TEMPO LETTURA ----------------------------------------------


# Scopo: Restituisce i calcoli tempo di una pratica con stato_tempo live.
def get_calcoli_tempo(pratica_id: int) -> list[dict[str, Any]]:
    repo = PraticheRepository()
    return repo.list_calcoli_tempo(pratica_id)


# -- FORMULE TEMPO LETTURA -------------------------------------------------


# Scopo: Restituisce le formule tempo attive per un tipo prestazione.
def get_formule_tempo(tipo_prestazione_id: int) -> list[dict[str, Any]]:
    ErrorManager.require(
        tipo_prestazione_id > 0,
        code="E_INVALID_ID",
        message="tipo_prestazione_id deve essere > 0",
    )
    assert tipo_prestazione_id > 0

    repo = PraticheRepository()
    return repo.list_formule_tempo(tipo_prestazione_id)


# -- CODA LAVORO OPERATORE ------------------------------------------------


# Scopo: Restituisce la coda di lavoro dell'operatore su tre livelli.
# Obiettivo: alimenta la sidebar della dashboard pratiche.
# Perimetro: delega alla funzione DB fn_coda_lavoro_operatore.
def get_coda_lavoro(
    risorsa_umana_id: int,
    emittente_fiscale_id: int,
) -> list[dict[str, Any]]:
    ErrorManager.require(
        risorsa_umana_id > 0,
        code="E_INVALID_ID",
        message="risorsa_umana_id deve essere > 0",
    )
    assert risorsa_umana_id > 0
    ErrorManager.require(
        emittente_fiscale_id > 0,
        code="E_INVALID_ID",
        message="emittente_fiscale_id deve essere > 0",
    )
    assert emittente_fiscale_id > 0

    repo = PraticheRepository()
    return repo.list_coda_lavoro(risorsa_umana_id, emittente_fiscale_id)


# Scopo: Prende in carico un flusso assegnandolo all'operatore corrente.
# Obiettivo: azione "prendi in carico" dalla coda di lavoro.
# Perimetro: delega alla funzione DB fn_prendi_in_carico_flusso
#   che gestisce lock, validazione stato e verifica competenza.
# Risultato: True se assegnato, False se gia' assegnato allo stesso operatore.
@transaction.atomic()
def prendi_in_carico(flusso_id: int, risorsa_umana_id: int) -> bool:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    assert flusso_id > 0
    ErrorManager.require(
        risorsa_umana_id > 0,
        code="E_INVALID_ID",
        message="risorsa_umana_id deve essere > 0",
    )
    assert risorsa_umana_id > 0

    repo = PraticheRepository()
    return repo.prendi_in_carico_flusso(flusso_id, risorsa_umana_id)


# -- COMPETENZE FLUSSI ----------------------------------------------------


# Scopo: Restituisce la matrice competenze con display fields.
def get_competenze_flussi() -> list[dict[str, Any]]:
    repo = PraticheRepository()
    return repo.list_competenze_flussi()


# Scopo: Crea una nuova competenza flusso (operazione admin).
@transaction.atomic()
def crea_competenza_flusso(
    *,
    template_flusso_id: int,
    unita_organizzativa_id: int,
    risorsa_umana_id: int,
    attivo: bool = True,
) -> int:
    ErrorManager.require(
        template_flusso_id > 0,
        code="E_INVALID_ID",
        message="template_flusso_id deve essere > 0",
    )
    assert template_flusso_id > 0
    ErrorManager.require(
        unita_organizzativa_id > 0,
        code="E_INVALID_ID",
        message="unita_organizzativa_id deve essere > 0",
    )
    assert unita_organizzativa_id > 0
    ErrorManager.require(
        risorsa_umana_id > 0,
        code="E_INVALID_ID",
        message="risorsa_umana_id deve essere > 0",
    )
    assert risorsa_umana_id > 0

    repo = PraticheRepository()
    return repo.create_competenza_flusso({
        "template_flusso_id": template_flusso_id,
        "unita_organizzativa_id": unita_organizzativa_id,
        "risorsa_umana_id": risorsa_umana_id,
        "attivo": attivo,
    })


# Scopo: Elimina una competenza flusso (operazione admin).
@transaction.atomic()
def elimina_competenza_flusso(competenza_id: int) -> None:
    ErrorManager.require(
        competenza_id > 0,
        code="E_INVALID_ID",
        message="competenza_id deve essere > 0",
    )
    assert competenza_id > 0

    repo = PraticheRepository()
    deleted = repo.delete_competenza_flusso(competenza_id)
    ErrorManager.require(
        deleted,
        code="E_NOT_FOUND",
        message=f"Competenza {competenza_id} non trovata",
    )


