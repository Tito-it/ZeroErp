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

from django.db import DatabaseError, IntegrityError, transaction

from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import map_integrity_error
from apps.core.services.service_errors import ServiceError
from apps.pratiche.db.pratiche_repository import PraticheRepository, coerce_jsonb_dict

# Marker → codice per i guard DB workflow v2 (fn_log_and_raise_error solleva
# il solo testo localizzato, senza codice: substring-match sul messaggio,
# pattern speculare a lookup_service._KNOWN_DB_ERROR_MARKERS). I codici sono
# quelli del catalogo DB (messaggi_errore id 300/301/302/477/483/485/490/491/492).
# ⚠ ASSUNZIONE: i marker sono sul testo ITALIANO e reggono perche' il
# catalogo ha solo righe lingua='it' per questi codici (fn_get_messaggio fa
# fallback a it). Se si aggiungono traduzioni, i marker vanno estesi o il
# match fallisce silenziosamente (fallback E_DATABASE generico, mai falsi
# positivi).
_KNOWN_DB_ERROR_MARKERS: tuple[tuple[str, str], ...] = (
    ("PRATICHE_FLUSSO_NON_RIPETIBILE", "non e' ripetibile in questa pratica"),
    (
        "PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI",
        "flussi obbligatori non completati",
    ),
    # Guard prerequisiti (D: flusso non ancora eseguibile): step cliccato in
    # anticipo nel percorso → messaggio parlante invece di E_DATABASE generico.
    ("PRATICHE_PREREQUISITI_NON_SODDISFATTI", "Prerequisiti non soddisfatti per il template flusso"),
    # Guard pratica terminale (CHIUSA/ANNULLATA): blocco creazione/modifica flussi.
    ("PRATICHE_TERMINALE_NUOVO_FLUSSO_BLOCCATO", "Impossibile creare un flusso"),
    ("PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE", "Impossibile modificare il flusso"),
    # Chiusura workflow-driven: il flusso di chiusura non puo' completarsi finche'
    # restano altri obbligatori bloccanti.
    ("PRATICHE_CHIUSURA_FLUSSO_PREMATURO", "Impossibile completare il flusso di chiusura"),
    # Guard transizione di stato (matrice config.transizioni_*): transizione non
    # in matrice → 409 parlante invece di E_DATABASE 500. Guard di bordo: le
    # transizioni valide non li toccano.
    ("PRATICHE_TRANSIZIONE_NON_AMMESSA", "Transizione pratica non ammessa"),
    ("FLUSSI_TRANSIZIONE_NON_AMMESSA", "Transizione flusso non ammessa"),
    # Guard esito-aware: COMPLETATO richiede esito valorizzato (nessuna fase si
    # chiude senza verdetto).
    ("FLUSSI_ESITO_OBBLIGATORIO", "Esito obbligatorio per completare il flusso"),
    # Presa in carico flusso (eligibilita' reparto-first, fn_prendi_in_carico_flusso):
    # casi A/D = competenza mancante; caso B = operatore fuori dal reparto instradato.
    # I marker sono substring stabili dei messaggi catalogo (id 322 / 496), immuni
    # alla sostituzione dei %s. NB: per il 496 si usa "non consentita del flusso"
    # (NON il prefisso "Presa in carico non consentita"): quest'ultimo collide col
    # messaggio di FLUSSI_PRESA_CARICO_STATO_ERRATO (486, "...: presa in carico non
    # consentita.") differendo solo per maiuscola — marker fragile. "del flusso"
    # e' presente solo nel 496.
    ("FLUSSI_COMPETENZA_MANCANTE", "non abilitato per il flusso"),
    ("FLUSSI_PRESA_NON_ELIGIBILE", "non consentita del flusso"),
    # Guard data non futura sospensioni (trg a10 trgfn_sospensioni_guard_data_non_futura,
    # catalogo id 499): la sospensione registra un evento gia' avvenuto, non
    # pianificato. Marker sul testo IT del catalogo, immune al %s del valore.
    ("E_SOSPENSIONE_DATA_FUTURA", "non puo' essere nel futuro"),
)

# Mapping vincoli DB sospensioni -> codici errore applicativi.
# L'EXCLUDE ex_sospensioni_no_overlap (framework dbops.automazione_overlap)
# solleva un native 23P01 IntegrityError: lo mappiamo per nome constraint,
# pattern speculare a ex_contratti_no_overlap -> E_VENDITE_CONTRATTO_OVERLAP.
_SOSPENSIONE_OVERLAP_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "ex_sospensioni_no_overlap": (
        "E_SOSPENSIONE_OVERLAP",
        "Esiste gia' una sospensione che copre questo periodo per la stessa "
        "pratica o lo stesso flusso. Correggi le date oppure chiudi prima la "
        "sospensione esistente.",
    ),
}

# CHECK chk_sospensioni_data_fine (data_fine > data_inizio): con la data
# manuale di riattivazione l'operatore puo' indicare una data_fine anteriore
# all'inizio della sospensione -> IntegrityError (23514). Mappato a errore
# parlante invece del 500 generico.
_SOSPENSIONE_CHECK_CONSTRAINTS: dict[str, tuple[str, str]] = {
    "chk_sospensioni_data_fine": (
        "E_SOSPENSIONE_DATA_FINE",
        "La data di riattivazione deve essere successiva all'inizio della "
        "sospensione.",
    ),
}

# Esiti ammessi per un flusso: mirror applicativo del CHECK DB chk_flussi_esito.
# Single source per la validazione fail-fast (completa/avvia_e_completa).
ESITI_FLUSSO_AMMESSI = ("POSITIVO", "NEGATIVO", "PARZIALE", "NON_APPLICABILE")

# Esito implicito dell'auto-completamento per gli step con handler ma senza
# esito_default (retro-compatibilita' col vecchio POSITIVO cablato). Per gli step
# AUTOMATICO l'esito_default e' garantito NOT NULL dal guard DB (Inv1) → questo
# fallback li riguarda solo in assenza di configurazione.
_ESITO_AUTO_FALLBACK = "POSITIVO"


# Scopo: Guard fail-fast sull'esito di un flusso (dominio chk_flussi_esito).
def _require_esito_valido(esito: str) -> None:
    ErrorManager.require(
        esito in ESITI_FLUSSO_AMMESSI,
        code="E_FLUSSO_VALIDATION",
        message=f"Esito non valido: {esito}",
    )


# Scopo: Traduce i DatabaseError dei guard workflow v2 in ServiceError parlante
# (codice del catalogo DB + policy registrata). Errori non riconosciuti
# ripropagano al middleware (mapping E_DATABASE generico).
def _raise_known_db_error(exc: DatabaseError, *, function_name: str) -> None:
    msg = str(exc)
    for code, marker in _KNOWN_DB_ERROR_MARKERS:
        if marker in msg:
            diag = getattr(getattr(exc, "__cause__", None), "diag", None)
            ErrorManager.raise_error(
                code=code,
                # message_primary = solo il RAISE, senza stack PL/pgSQL.
                message=getattr(diag, "message_primary", None) or msg,
                detail=getattr(diag, "message_detail", None),
                hint=getattr(diag, "message_hint", None),
                cause=exc,
                function_name=function_name,
            )
    raise exc

# -- PRATICHE --------------------------------------------------------


# Scopo: Crea una nuova pratica gia' in stato APERTA.
# Obiettivo: entry point per creazione pratica da qualsiasi dominio.
# Perimetro: risolve stato iniziale, delega INSERT al repository.
# Risultato: ID della pratica creata.
# Nota modello: la pratica nasce APERTA (niente passaggio per BOZZA) — lo stato
#   BOZZA resta nel modello per un eventuale "salva bozza" esplicito futuro. Il
#   trigger DB valorizza data_apertura anche alla creazione diretta in APERTA.
@transaction.atomic()
def crea_pratica(
    *,
    emittente_fiscale_id: int,
    tipo_prestazione_id: int,
    soggetto_id: str | None = None,
    soggetto_ruolo_id: int | None = None,
    istanza_utility_id: int | None = None,
    priorita_id: int | None = None,
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
    # Priorita' opzionale: se assente si applica il default NORMALE risolto
    # per codice_interno (mai id hardcodato — feedback_no_hardcoded_ids).
    if priorita_id is not None:
        ErrorManager.require(
            priorita_id > 0,
            code="E_PRATICA_VALIDATION",
            message="priorita_id deve essere > 0",
        )
        assert priorita_id > 0

    # Validazione coerenza contesto anagrafico (stesse regole del trigger DB,
    # qui per dare errori user-friendly via ServiceError). Modello a due rami
    # dal soggetto (brief-db-pratiche-guard-contesto-istanza, consegna
    # 20260611-01): l'istanza NON richiede il ruolo — il prospect puro ha
    # solo istanze, il ruolo CL nasce col BA. Entrambi i rami richiedono il
    # soggetto.
    if istanza_utility_id is not None:
        ErrorManager.require(
            soggetto_id is not None,
            code="E_PRATICA_VALIDATION",
            message="istanza_utility_id richiede soggetto_id",
        )
    if soggetto_ruolo_id is not None:
        ErrorManager.require(
            soggetto_id is not None,
            code="E_PRATICA_VALIDATION",
            message="soggetto_ruolo_id richiede soggetto_id",
        )

    # Guard pre/post-attivazione: verifica ammissibilita' tipo prestazione
    # in base allo stato del billing_account del soggetto. Semantica flag
    # (analisi-pratiche-domini-anello3 §11.1.3): pre/post UGUALI (true/true
    # ma anche false/false, es. tipi PREVENTIVI_*) = ammessa
    # indipendentemente dallo stato BA -> guard saltato. Il check scatta
    # solo quando UNO dei due flag e' false (tipo vincolato a una fase).
    repo = PraticheRepository()
    tipo_att = repo.get_tipo_prestazione_attivazione(tipo_prestazione_id)
    if soggetto_id is not None and tipo_att["pre_attivazione"] != tipo_att["post_attivazione"]:
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

    # Risolve stato iniziale APERTA + default priorita' NORMALE se assente.
    stato_id = repo.resolve_stato_pratica("APERTA")
    if priorita_id is None:
        priorita_id = repo.resolve_priorita_pratica("NORMALE")
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
    try:
        repo.update_stato_pratica(pratica_id, nuovo_stato)
    except DatabaseError as exc:
        # Guard chiusura (D4, trg_pratiche_a10_guard_chiusura_flussi_upd) →
        # PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI parlante.
        _raise_known_db_error(
            exc, function_name="pratiche_service.cambia_stato_pratica",
        )


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
    soggetto_ruolo_id: int | None = None,
    istanza_utility_id: int | None = None,
    solo_interne: bool = False,
    priorita_id: int | None = None,
    risorsa_umana_id: int | None = None,
    search: str | None = None,
    data_da: str | None = None,
    data_a: str | None = None,
    limit: int = 50,
    offset: int = 0,
    order_by: str = "data_insert",
    order_dir: str = "desc",
) -> tuple[list[dict[str, Any]], int]:
    # Lente di contesto canonica (D1): al massimo UNA tra ruolo / istanza /
    # interne. Fail-fast qui con lo stesso codice del guard DB (484) — la fn
    # fn_lista_pratiche_per_contesto resta la difesa in profondita'.
    lenti_attive = sum(
        1 for attiva in (
            soggetto_ruolo_id is not None,
            istanza_utility_id is not None,
            solo_interne,
        ) if attiva
    )
    ErrorManager.require(
        lenti_attive <= 1,
        code="PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI",
        message=(
            "Parametri di contesto non ammessi: indicare al massimo una lente "
            "tra ruolo soggetto, istanza utility e solo interne."
        ),
    )

    repo = PraticheRepository()
    return repo.list_pratiche(
        emittente_fiscale_id=emittente_fiscale_id,
        stato_codice_interno=stato_codice_interno,
        tipo_prestazione_id=tipo_prestazione_id,
        soggetto_id=soggetto_id,
        soggetto_ruolo_id=soggetto_ruolo_id,
        istanza_utility_id=istanza_utility_id,
        solo_interne=solo_interne,
        priorita_id=priorita_id,
        risorsa_umana_id=risorsa_umana_id,
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
# Nota modello (workflow v2): ogni flusso e' template-driven — nasce sempre da un
# template del percorso (FE PraticaPercorso) o dall'auto-generazione cross-pratica
# (fn_genera_pratica_da_flusso, sempre con template_dest). Il vecchio "flusso
# generico" senza template e' stato rimosso: template_flusso_id e' OBBLIGATORIO,
# chiudiamo qui il path morto. I read-path (verifica_prerequisiti, canali) restano
# tolleranti ai flussi legacy con template NULL eventualmente presenti a DB.
@transaction.atomic()
def crea_flusso(
    *,
    pratica_id: int,
    template_flusso_id: int,
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
    ErrorManager.require(
        template_flusso_id is not None and template_flusso_id > 0,
        code="E_FLUSSO_VALIDATION",
        message="template_flusso_id obbligatorio e > 0: un flusso nasce sempre da un template del percorso.",
    )
    assert template_flusso_id is not None and template_flusso_id > 0

    # Risolve stato iniziale DA_ESEGUIRE.
    repo = PraticheRepository()
    stato_id = repo.resolve_stato_flusso("DA_ESEGUIRE")
    try:
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
    except DatabaseError as exc:
        # Guard ripetibilita' (D3, trg_flussi_a10_guard_ripetibilita_ins) →
        # PRATICHE_FLUSSO_NON_RIPETIBILE parlante; altri errori al middleware.
        _raise_known_db_error(exc, function_name="pratiche_service.crea_flusso")
        raise  # irraggiungibile, per il type checker


# Scopo: Assegna un flusso esistente a un operatore e/o a un reparto.
# Simmetrico ad assegna_pratica ma sul singolo step. I flag set_* distinguono
# "chiave assente" (non toccare) da "valore None esplicito" (de-assegna): la view
# li deriva da `"<key>" in payload`. Il trigger DB
# trg_flussi_z90_giornale_assegnazione_upd registra l'evento nel giornale; la
# validazione FK (operatore/reparto esistenti) e' lasciata al DB.
def assegna_flusso(
    flusso_id: int,
    *,
    risorsa_umana_id: int | None = None,
    unita_organizzativa_id: int | None = None,
    set_risorsa: bool = False,
    set_unita: bool = False,
) -> None:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    assert flusso_id > 0

    update_data: dict[str, Any] = {}
    if set_risorsa:
        update_data["risorsa_umana_id"] = risorsa_umana_id
    if set_unita:
        update_data["unita_organizzativa_id"] = unita_organizzativa_id

    if not update_data:
        return

    repo = PraticheRepository()
    repo.update_flusso(flusso_id, update_data)


# Scopo: Transizione flusso DA_ESEGUIRE → IN_CORSO; se il template ha un handler
# o modalita_esito=AUTOMATICO lo completa, tutto in UNA transazione (§8.2 del
# brief BE: IN_CORSO + execute + COMPLETATO non possono divergere). Su eccezione
# dell'handler l'intera transizione rolla (flusso torna DA_ESEGUIRE, ri-eseguibile)
# e l'errore parlante propaga all'operatore.
@transaction.atomic()
def avvia_flusso(flusso_id: int, *, user: str | None = None) -> dict[str, Any] | None:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    assert flusso_id > 0

    repo = PraticheRepository()
    # Config esito del template (20260617-01): modalita_esito + esito_default.
    # auto_esito unifica handler-completion e modalita AUTOMATICO su un unico esito
    # dichiarativo (fallback POSITIVO per gli step con handler ma senza esito_default,
    # retro-compatibile col vecchio POSITIVO cablato). Query leggera dedicata:
    # dispatch_handler/eventi rifanno la proiezione completa solo se serve.
    config = repo.get_flusso_esito_config(flusso_id)
    ErrorManager.require(
        config is not None,
        code="E_FLUSSO_NOT_FOUND",
        message=f"Flusso {flusso_id} non trovato",
    )
    assert config is not None
    modalita, esito_default = config
    auto_esito = esito_default or _ESITO_AUTO_FALLBACK
    try:
        repo.update_stato_flusso(flusso_id, "IN_CORSO")

        # Dispatch handler (None se il flusso non ha handler → resta IN_CORSO,
        # completamento manuale/contestuale dall'operatore).
        # NB sui prerequisiti: il guard esito-aware e' un trigger BEFORE INSERT sui
        # flussi → scatta alla CREAZIONE del flusso, non qui. Un flusso CONFERMA
        # esiste solo se APPROVAZIONE_CLIENTE era COMPLETATO+POSITIVO. La difesa a
        # runtime, all'avvio, e' il check "preventivo ACCETTATO" dentro l'handler.
        # Concorrenza: l'UPDATE di stato sopra prende il lock di riga del flusso →
        # due avvii concorrenti sullo stesso flusso si serializzano (no doppio push).
        result = dispatch_handler(flusso_id, user=user)
        # Auto-completamento: l'handler ha prodotto un risultato OPPURE lo step e'
        # configurato AUTOMATICO (avvia+chiudi senza scelta umana, ammesso solo su
        # direzione INTERNA per l'Inv2 garantita dal guard a config-time).
        if result is not None or modalita == "AUTOMATICO":
            repo.update_stato_flusso(flusso_id, "COMPLETATO", esito=auto_esito)
            # Azioni di dominio legate al COMPLETATO (template_flussi_handler_eventi).
            dispatch_handler_eventi(flusso_id, evento="COMPLETATO", esito=auto_esito, user=user)
        return result
    except DatabaseError as exc:
        # Guard pratica terminale (CHIUSA/ANNULLATA) → PRATICHE_TERMINALE_FLUSSO_
        # NON_MODIFICABILE parlante; altri errori (handler, ecc.) al middleware.
        _raise_known_db_error(exc, function_name="pratiche_service.avvia_flusso")
        raise  # irraggiungibile, per il type checker


# Scopo: Completa un flusso con esito e note.
# Obiettivo: transizione → COMPLETATO. La generazione automatica
# cross-pratica e' gestita dal trigger DB (trgfn_flussi_generazione).
@transaction.atomic()
def completa_flusso(
    flusso_id: int,
    *,
    esito: str,
    note_esito: str | None = None,
    user: str | None = None,
) -> None:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    assert flusso_id > 0
    _require_esito_valido(esito)

    repo = PraticheRepository()
    try:
        repo.update_stato_flusso(flusso_id, "COMPLETATO", esito=esito, note_esito=note_esito)
    except DatabaseError as exc:
        # Guard pratica terminale → PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE.
        _raise_known_db_error(exc, function_name="pratiche_service.completa_flusso")
    # Azioni di dominio legate al completamento (template_flussi_handler_eventi):
    # es. accetta il preventivo collegato quando APPROVAZIONE_CLIENTE chiude
    # POSITIVO. Stessa transazione → completamento + azione dominio atomici (sostituisce
    # il routing M2 hardcoded lato FE). I flussi senza binding: no-op.
    dispatch_handler_eventi(flusso_id, evento="COMPLETATO", esito=esito, user=user)


# Scopo: Avvia E completa un flusso in un'unica azione (modalita CONTESTUALE).
# Obiettivo: collassa i due momenti (avvio + registrazione esito) per gli step in
# cui l'operatore registra l'esito contestualmente all'avvio. DA_ESEGUIRE →
# IN_CORSO → COMPLETATO nella STESSA transazione (la matrice transizioni non ha la
# 1→3 diretta: si passa sempre da IN_CORSO, come avvia_flusso per gli handler).
# L'esito e' quello scelto/confermato dall'operatore (non fabbricato): valido su
# qualsiasi direzione (Inv2 vincola solo AUTOMATICO).
@transaction.atomic()
def avvia_e_completa_flusso(
    flusso_id: int,
    *,
    esito: str,
    note_esito: str | None = None,
    user: str | None = None,
) -> None:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    assert flusso_id > 0
    # Valida l'esito PRIMA di qualsiasi scrittura: niente avvio "orfano" (flusso
    # lasciato IN_CORSO) se l'esito e' fuori dominio.
    _require_esito_valido(esito)

    repo = PraticheRepository()
    try:
        repo.update_stato_flusso(flusso_id, "IN_CORSO")
    except DatabaseError as exc:
        _raise_known_db_error(exc, function_name="pratiche_service.avvia_e_completa_flusso")
    # Riusa il completamento canonico: COMPLETATO + esito + azioni di dominio
    # (template_flussi_handler_eventi), nella stessa transazione → atomico.
    # NB: CONTESTUALE NON esegue l'handler di AVVIO (dispatch_handler): e' la
    # modalita "esito deciso dall'operatore"; l'automazione d'avvio appartiene ad
    # AUTOMATICO/handler. Le reazioni di dominio all'esito viaggiano comunque su
    # dispatch_handler_eventi dentro completa_flusso.
    completa_flusso(flusso_id, esito=esito, note_esito=note_esito, user=user)


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
    try:
        repo.update_stato_flusso(flusso_id, nuovo_stato, esito=esito, note_esito=note_esito)
    except DatabaseError as exc:
        # Guard pratica terminale → PRATICHE_TERMINALE_FLUSSO_NON_MODIFICABILE.
        _raise_known_db_error(exc, function_name="pratiche_service.cambia_stato_flusso")


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


# Scopo: Percorso suggerito della pratica (template_flussi del tipo + stato
# istanziazione di ciascuno). Alimenta la roadmap FE.
def get_percorso(pratica_id: int) -> list[dict[str, Any]]:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    assert pratica_id > 0
    return PraticheRepository().get_percorso_pratica(pratica_id)


# Scopo: Carica il flusso per il dispatch handler, con guard di esistenza.
# Ritorna il flusso, o None se non ha template (handler e binding eventi vivono
# sul template → niente da dispatchare). Preambolo condiviso da dispatch_handler
# e dispatch_handler_eventi.
def _flusso_per_dispatch(flusso_id: int) -> dict[str, Any] | None:
    flusso = PraticheRepository().get_flusso(flusso_id)
    ErrorManager.require(
        flusso is not None,
        code="E_FLUSSO_NOT_FOUND",
        message=f"Flusso {flusso_id} non trovato",
    )
    assert flusso is not None
    return flusso if flusso["template_flusso_id"] is not None else None


# Scopo: Invoca l'handler Django configurato per il flusso.
# Obiettivo: dispatch automatico se il template flusso ha un handler_key.
# Perimetro: lookup handler dal registry, invocazione execute().
def dispatch_handler(flusso_id: int, *, user: str | None = None) -> dict[str, Any] | None:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    assert flusso_id > 0

    flusso = _flusso_per_dispatch(flusso_id)
    if flusso is None:
        return None

    # Lookup handler_key e handler_params dal template flusso.
    handler_info = PraticheRepository().get_handler_info(flusso["template_flusso_id"])
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
        # Coerce difensivo: jsonb puo' arrivare come str da psycopg; l'handler
        # fa meta.get(...) e si aspetta SEMPRE un dict (stesso fix di
        # handler_params in get_handler_info).
        meta=coerce_jsonb_dict(flusso["meta"]),
        handler_params=handler_params,
        user=user,
    )


# Scopo: Dispatch degli handler legati a un EVENTO di flusso
# (pratiche.template_flussi_handler_eventi). Generalizza il dispatch oltre
# l'avvio: su `COMPLETATO` esegue le azioni di dominio il cui `esito_richiesto`
# combacia con l'esito effettivo (NULL = qualsiasi esito), in ordine di sequenza.
# Perimetro: chiamato dentro la transazione del cambio stato del flusso, così
# completamento + azione di dominio sono atomici (rimpiazza il routing M2
# hardcoded lato FE). Eccezioni dell'handler propagano e rollano la transizione.
def dispatch_handler_eventi(
    flusso_id: int, *, evento: str, esito: str | None = None, user: str | None = None,
) -> None:
    flusso = _flusso_per_dispatch(flusso_id)
    if flusso is None:
        return

    bindings = PraticheRepository().get_handler_eventi(flusso["template_flusso_id"], evento, esito)
    if not bindings:
        return

    from apps.pratiche.services.handler_registry import get_handler
    meta = coerce_jsonb_dict(flusso["meta"])
    for handler_key, handler_params in bindings:
        handler_class = get_handler(handler_key)
        # Binding seedato a DB ma senza implementazione registrata = misconfig di
        # deploy: fail-fast (non eseguire un completamento "monco" che salta
        # silenziosamente l'azione di dominio promessa dal binding).
        ErrorManager.require(
            handler_class is not None,
            code="E_HANDLER_NON_REGISTRATO",
            message=f"Handler '{handler_key}' non registrato in HANDLER_MAP",
        )
        assert handler_class is not None
        handler_class().execute(
            flusso_id=flusso_id,
            pratica_id=flusso["pratica_id"],
            meta=meta,
            handler_params=handler_params,
            user=user,
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
    data_inizio: str | None = None,
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
    # data_inizio manuale (opz.) e' difesa a DB: l'EXCLUDE rifiuta i periodi
    # sovrapposti (23P01 -> 409), il guard a10 le date future (-> 422). L'intera
    # transazione (incluso il cambio stato sopra) rolla back su errore.
    try:
        return repo.create_sospensione(
            pratica_id,
            motivo,
            data_riattivazione_prevista=data_riattivazione_prevista,
            data_inizio=data_inizio,
        )
    except IntegrityError as exc:
        map_integrity_error(
            exc,
            unique_constraints=_SOSPENSIONE_OVERLAP_CONSTRAINTS,
            fallback_code="E_PRATICA_VALIDATION",
            fallback_message="Violazione vincolo DB su sospensione.",
            context={"pratica_id": pratica_id},
        )
    except DatabaseError as exc:
        # Guard data futura (trg a10) -> E_SOSPENSIONE_DATA_FUTURA parlante.
        _raise_known_db_error(exc, function_name="pratiche_service.sospendi_pratica")
        raise  # irraggiungibile, per il type checker


# Scopo: Riattiva una pratica sospesa.
# Obiettivo: chiude la sospensione attiva impostando data_fine = NOW().
# Perimetro: valida esistenza sospensione attiva, delega chiusura al repository.
#   Il trigger DB ripristina gli stati dei flussi, cambia stato pratica ad APERTA
#   e registra nel giornale.
@transaction.atomic()
def riattiva_pratica(pratica_id: int, *, data_fine: str | None = None) -> None:
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
    # data_fine manuale (opz.) e' difesa a DB: CHECK data_fine > data_inizio
    # (23514 -> E_SOSPENSIONE_DATA_FINE), guard a10 rifiuta le date future (P0001
    # -> E_SOSPENSIONE_DATA_FUTURA). IntegrityError e' sottoclasse di DatabaseError:
    # va intercettato PRIMA, altrimenti il CHECK finisce nel ramo generico (500).
    try:
        repo.chiudi_sospensione(sosp_attiva["id"], data_fine=data_fine)
    except IntegrityError as exc:
        map_integrity_error(
            exc,
            check_constraints=_SOSPENSIONE_CHECK_CONSTRAINTS,
            fallback_code="E_PRATICA_VALIDATION",
            fallback_message="Violazione vincolo DB su sospensione.",
            context={"pratica_id": pratica_id},
        )
    except DatabaseError as exc:
        _raise_known_db_error(exc, function_name="pratiche_service.riattiva_pratica")
        raise  # irraggiungibile, per il type checker


# Scopo: Verifica che il flusso esista e appartenga alla pratica indicata.
# Funzione pubblica: usata sia internamente dal service sia dalle views API.
def verifica_flusso_pratica(
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
    verifica_flusso_pratica(repo, pratica_id, flusso_id)

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
    verifica_flusso_pratica(repo, pratica_id, flusso_id)

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
    try:
        return repo.prendi_in_carico_flusso(flusso_id, risorsa_umana_id)
    except DatabaseError as exc:
        # Eligibilita' reparto-first (fn_prendi_in_carico_flusso): competenza
        # mancante (A/D) o operatore fuori reparto (B) → ServiceError parlante
        # invece di E_DATABASE generico. Altri errori al middleware.
        _raise_known_db_error(exc, function_name="pratiche_service.prendi_in_carico")
        raise  # irraggiungibile, per il type checker


# Scopo: Lista operatori (risorse umane attive) di un reparto, per il picker di
# assegnazione flusso. Coerente con la policy "operatore di quel reparto".
def list_operatori_reparto(unita_organizzativa_id: int) -> list[dict[str, Any]]:
    ErrorManager.require(
        unita_organizzativa_id > 0,
        code="E_INVALID_ID",
        message="unita_organizzativa_id deve essere > 0",
    )
    assert unita_organizzativa_id > 0

    repo = PraticheRepository()
    return repo.list_operatori_reparto(unita_organizzativa_id)


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


