# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio applicativo modulo pratiche.
#        Facade per operazioni su pratiche, flussi, prerequisiti,
#        giornale e handler dispatch.
#        Progettato come API interna cross-dominio: altre app Django
#        (vendite, anagrafiche, acquisti) importano e usano queste
#        funzioni per creare/gestire pratiche legate ai propri eventi.
# ------------------------------------------------------------

from collections.abc import Callable
from datetime import date, datetime
from typing import Any, NoReturn

from django.db import DatabaseError, IntegrityError, transaction

from apps.core.api.constants import DEFAULT_LIMIT, DEFAULT_LIMIT_EVENTI
from apps.core.services.db_error_fields import diagnostica_db
from apps.core.services.error_manager import ErrorManager
from apps.core.services.payload_helpers import PayloadValidator, map_integrity_error
from apps.core.services.service_errors import ServiceError
from apps.anagrafiche.services.billing_account_service import istanza_del_billing_account
from apps.pratiche.db.pratiche_repository import (
    PRATICA_UPDATE_SET,
    PraticheRepository,
    coerce_jsonb_dict,
)

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
    # Chiusura pratica (manuale + auto): restano flussi ISTANZIATI in stato NON
    # terminale (DA_ESEGUIRE/IN_CORSO/SOSPESO/ERRORE). D1 hardening — invariante
    # condiviso guard manuale + auto-chiusura (brief-db-chiusura-pratica-nessun-
    # lavoro-pendente, errore catalogo 501).
    ("PRATICHE_CHIUSURA_FLUSSI_APERTI", "flussi ancora aperti"),
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
    # Guard classe esito (step DOMINIO vs verdetto, brief-db-step-dominio-e-
    # definizioni-versionate §1.3, catalogo id 504): al completamento uno step
    # DOMINIO esige un esito di ramo (is_verdetto=false) e uno step non-DOMINIO un
    # verdetto. Marker = substring stabile del messaggio "Esito %s non ammesso per
    # lo step %s: richiesto un esito di %s.", immune ai %s.
    ("FLUSSI_ESITO_NON_AMMESSO", "non ammesso per lo step"),
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
    # Workflow definizioni versionate (Fase 1, companion BE-2.2): risoluzione
    # definizione alla creazione pratica (DEFINIZIONE_NON_TROVATA, id 507) e guard
    # flusso↔definizione pinnata (FLUSSI_TEMPLATE_FUORI_DEFINIZIONE). Marker =
    # substring stabile dei messaggi catalogo, immune ai %s.
    ("DEFINIZIONE_NON_TROVATA", "Nessuna definizione workflow pubblicata"),
    ("FLUSSI_TEMPLATE_FUORI_DEFINIZIONE", "non appartiene alla definizione"),
    # Azioni ciclo di vita edizioni (Fase 2 Slice 1b: fork/nuova-versione/pubblica).
    # Marker = substring stabile dei messaggi catalogo (id 509/510/511), immune ai %s.
    ("DEFINIZIONE_NON_PUBBLICABILE", "non pubblicabile"),
    ("DEFINIZIONE_PUBBLICATA_IMMUTABILE", "non modificabile: stato"),
    ("DEFINIZIONE_TRANSIZIONE_NON_AMMESSA", "Transizione di stato definizione workflow"),
    # Invariante «≤1 BOZZA per scope» + derivazione nuova-versione da PUBBLICATA
    # (brief-db-guard-bozza-unica-nuova-versione, guard in fn_fork/fn_nuova_versione).
    # Marker = substring stabile dei messaggi catalogo, immune ai %s.
    ("DEFINIZIONE_BOZZA_ESISTENTE", "una bozza di edizione workflow"),
    ("DEFINIZIONE_NO_PUBBLICATA", "Nuova versione non ammessa"),
    # Editing strutturale BOZZA (Slice 2): guard immutabilità su edizione
    # per-emittente gia' emessa (514, brief-db-accesso-write-editing-strutturale-bozza)
    # + unique codice per definizione. Marker = substring stabile.
    ("TEMPLATE_DEFINIZIONE_CONGELATA", "edizione per-emittente"),
    ("E_TEMPLATE_CODICE_DUPLICATO", "uq_template_flussi_definizione_codice"),
)

# Perimetro dei codici che questo dominio si aspetta. Insieme, non elenco di
# stringhe esatte: vedi il confronto in `_raise_known_db_error`, che accetta
# anche la forma col prefisso `E_` dei codici in via di rinomina.
_CODICI_DICHIARATI: frozenset[str] = frozenset(c for c, _ in _KNOWN_DB_ERROR_MARKERS)

# Il CAMPO del form per i codici che il DB solleva senza `COLUMN` — una UNIQUE
# violata (23505) non nomina la colonna, e `diag.fields` resta vuoto. Stessa
# forma del terzo elemento di `map_integrity_error`: si dichiara solo quando il
# nome e' una chiave del payload (presidio C2, brief-be-presidio-ui-action-e-
# canale-campi §3-ter).
_CAMPO_PER_CODICE_DB: dict[str, tuple[str, ...]] = {
    "E_TEMPLATE_CODICE_DUPLICATO": ("codice",),
}


# Scopo: il campo dichiarato per un codice DB, letto nella forma col prefisso
#        `E_` qualunque sia quella con cui il codice arriva. Stessa tolleranza
#        di `_raise_known_db_error` sui codici in via di rinomina: senza, il
#        lotto che aggiunge il prefisso a DB spegnerebbe il campo in silenzio.
def _campo_per_codice_db(code: str) -> tuple[str, ...] | None:
    return _CAMPO_PER_CODICE_DB.get("E_" + code.removeprefix("E_"))

# Mapping vincoli DB sospensioni -> codici errore applicativi.
# L'EXCLUDE ex_sospensioni_no_overlap (framework dbops.automazione_overlap)
# solleva un native 23P01 IntegrityError: lo mappiamo per nome constraint,
# pattern speculare a ex_contratti_no_overlap -> E_CONTRATTO_OVERLAP_ESISTENTE.
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

# Validazione esiti data-driven dal vocabolario DB `config.esiti_flussi_pratiche`
# (bonifica 2026-07-02: rimossi i mirror hardcoded ESITI_FLUSSO_AMMESSI e
# ESITI_FLUSSO_RAMO — una sola verita', la colonna `is_verdetto` DEFAULT false
# fail-closed consegnata dal team DB):
#   is_verdetto = true  → verdetto deciso dall'operatore (selezionabile a mano);
#   is_verdetto = false → esito di RAMO calcolato dal dominio (bivio SMISTAMENTO),
#                         ammesso solo dai BB di dominio (completa_step_pratica).
# La FK su flussi.esito resta il guard autoritativo; le letture qui sotto danno
# l'errore parlante PRIMA del round-trip di scrittura. Un nuovo esito seedato a
# DB e' automaticamente valido: nessuna costante da aggiornare.

# Esito implicito dell'auto-completamento per gli step con handler ma senza
# esito_default (retro-compatibilita' col vecchio POSITIVO cablato). Per gli step
# AUTOMATICO l'esito_default e' garantito NOT NULL dal guard DB (Inv1) → questo
# fallback li riguarda solo in assenza di configurazione.
_ESITO_AUTO_FALLBACK = "POSITIVO"


# Scopo: Guard fail-fast sull'esito di un flusso: deve esistere ATTIVO nel
# vocabolario DB (is_verdetto qualsiasi: vale per operatore e BB di dominio).
# `repo` iniettabile (simmetrico al guard operatore). NB: sul percorso API il
# guard operatore ha gia' letto la stessa voce — la seconda lettura qui e' una
# PK-lookup volutamente accettata: completa_flusso resta autosufficiente per i
# BB di dominio senza threading di stato fra i layer.
def _require_esito_valido(esito: str, repo: PraticheRepository | None = None) -> None:
    voce = (repo or PraticheRepository()).get_esito_flusso_vocabolario(esito)
    ErrorManager.require(
        voce is not None and voce[0],
        code="E_FLUSSO_VALIDATION",
        message=f"Esito non valido: {esito}",
        context={"field": "esito"},
    )


# Scopo: Guard sul percorso OPERATORE (API cambio stato flusso): l'esito scelto
# a mano deve essere un verdetto (`is_verdetto`); gli esiti di ramo restano
# riservati ai BB di dominio. Il lookup FE espone `selezionabile_operatore`
# (derivato da is_verdetto) e filtra il Select alla fonte; questo guard e' la
# difesa in profondita' sul contratto API. Codice inesistente → passa: ci pensa
# _require_esito_valido a valle con l'errore parlante giusto.
# `repo` iniettabile: la view riusa la propria istanza (gia' mockata nei test API).
def require_esito_selezionabile_operatore(
    esito: str, repo: PraticheRepository | None = None,
) -> None:
    voce = (repo or PraticheRepository()).get_esito_flusso_vocabolario(esito)
    ErrorManager.require(
        voce is None or voce[1],
        code="E_FLUSSO_VALIDATION",
        message=f"Esito calcolato dal dominio, non selezionabile manualmente: {esito}",
        context={"field": "esito"},
    )


# Scopo: Guard simmetrico sul percorso OPERATORE (companion BE-1.3): vieta di
# COMPLETARE manualmente uno step il cui esito e' calcolato dal dominio
# (modalita_esito = DOMINIO, es. SMISTAMENTO). `require_esito_selezionabile_
# operatore` blocca l'esito di ramo scelto a mano, non il verdetto su uno step
# DOMINIO: questo copre il caso opposto e chiude il buco dell'incidente
# PRA-0000243 (POSITIVO su SMISTAMENTO) con errore parlante prima del DB.
# ⚠️ Vive SOLO sul percorso operatore (view), NON dentro completa_flusso/
# avvia_e_completa_flusso: il percorso di dominio (completa_step_pratica ←
# vendite.completa_smistamento) passa da li' e deve continuare a funzionare.
# La difesa autoritativa resta il guard DB di classe (id 504). Config assente →
# passa (MANUALE): ci pensa _require_esito_valido a valle.
def require_completamento_operatore_ammesso(
    flusso_id: int, repo: PraticheRepository | None = None,
) -> None:
    config = (repo or PraticheRepository()).get_flusso_esito_config(flusso_id)
    modalita = config[0] if config else "MANUALE"
    ErrorManager.require(
        modalita != "DOMINIO",
        code="E_FLUSSO_VALIDATION",
        message="Esito calcolato dal dominio: completare lo step con l'azione di dominio dedicata.",
    )


# Scopo: Traduce i DatabaseError dei guard workflow v2 in ServiceError parlante
# (codice del catalogo DB + policy registrata). Errori non riconosciuti
# ripropagano al middleware (mapping E_DATABASE generico).
def _raise_known_db_error(exc: DatabaseError, *, function_name: str) -> NoReturn:
    msg = str(exc)
    # ⭐ UNA lettura sola (BB `diagnostica_db`). ⚠️ E questo e' il QUINTO punto in
    #    cui un errore del database diventa un errore dell'applicazione: i primi
    #    quattro sono stati sanati il 2026-08-24, questo era rimasto indietro —
    #    e non e' un dettaglio, perche' ci passa il TERZO SCAGLIONE del roll-out
    #    del bersaglio (`E_FLUSSI_*`, `E_DEFINIZIONE_BOZZA_ESISTENTE`, applicati
    #    il 2026-08-24). Senza, quei bersagli si fermavano qui e il pulsante non
    #    sarebbe comparso mai — proprio sul caso che il brief chiama «il piu'
    #    netto dell'intero roll-out», dove la frase la bozza che blocca non la
    #    nomina affatto.
    diag = diagnostica_db(exc, text=msg)

    # 1) Campo strutturato (dal 2026-08-05): il codice arriva dal DB, non si
    #    deduce dal testo. Qui vale piu' che altrove — i codici di questo
    #    dominio non hanno prefisso `E_`, quindi la regex generale non li ha
    #    mai visti e l'unico appiglio erano i frammenti di messaggio ITALIANO
    #    di `_KNOWN_DB_ERROR_MARKERS`: bastava riformulare una frase nel seed,
    #    o tradurla, e il match cadeva in silenzio (fallback E_DATABASE).
    #    Filtro sui soli codici dichiarati: la lista e' anche il perimetro di
    #    cio' che questo dominio si aspetta e ha registrato in error_policies.
    #
    #    ⚠️ Si accetta anche la forma col prefisso `E_`. Il DB sta rinominando i
    #    codici di questo dominio anteponendolo, un lotto per volta
    #    (brief-db-codice-errore-strutturato §15), e la rinomina tocca il CODICE
    #    non il MESSAGGIO: senza questa clausola, dopo un lotto il campo
    #    strutturato verrebbe scartato, vincerebbe il marker testuale — che
    #    corrisponde ancora — e l'API restituirebbe il nome vecchio, ormai
    #    ritirato a catalogo. Non fallirebbe niente: e' proprio per questo che
    #    non se ne accorgerebbe nessuno.
    #    Una condizione invece di 21 voci gemelle da aggiungere e poi ripulire:
    #    copre ogni lotto futuro senza altre modifiche, e quando i codici vecchi
    #    usciranno dalla lista resta corretta com'e'.
    structured = diag.codice_strutturato
    if structured is not None and (
        structured in _CODICI_DICHIARATI
        or structured.removeprefix("E_") in _CODICI_DICHIARATI
    ):
        ErrorManager.raise_error(
            code=structured,
            # message_primary = solo il RAISE, senza stack PL/pgSQL.
            message=diag.messaggio or msg,
            detail=diag.detail,
            hint=diag.hint,
            fields=diag.fields or _campo_per_codice_db(structured),
            targets=diag.bersagli or None,
            cause=exc,
            function_name=function_name,
        )

    # 2) Ripiego sui marker testuali: serve ancora per i RAISE diretti che non
    #    passano da `script.fn_log_and_raise_error` (il campo esce vuoto).
    for code, marker in _KNOWN_DB_ERROR_MARKERS:
        if marker in msg:
            ErrorManager.raise_error(
                code=code,
                message=diag.messaggio or msg,
                detail=diag.detail,
                hint=diag.hint,
                fields=diag.fields or _campo_per_codice_db(code),
                targets=diag.bersagli or None,
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
    billing_account_id: int | None = None,
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
        context={"field": "emittente_fiscale_id"},
    )
    ErrorManager.require(
        tipo_prestazione_id > 0,
        code="E_PRATICA_VALIDATION",
        message="tipo_prestazione_id obbligatorio e > 0",
        context={"field": "tipo_prestazione_id"},
    )
    # Priorita' opzionale: se assente si applica il default NORMALE risolto
    # per codice_interno (mai id hardcodato — feedback_no_hardcoded_ids).
    if priorita_id is not None:
        ErrorManager.require(
            priorita_id > 0,
            code="E_PRATICA_VALIDATION",
            message="priorita_id deve essere > 0",
            context={"field": "priorita_id"},
        )

    # Il cliente di cui parla la pratica, a grana fine (D-9 di
    # brief-db-istanza-nasce-col-ba, 2026-10-08): il BA porta la sua istanza.
    # Se il chiamante passa il solo BA l'istanza e' la sua; se le passa
    # entrambe devono coincidere (la FK composta
    # fk_pratiche_billing_account_istanza lo direbbe con un 23503 nudo): BB
    # `istanza_del_billing_account`. Che il BA sia del ruolo della pratica lo
    # dice il trigger (regola 5, E_PRATICHE_BA_NON_COERENTE).
    if billing_account_id is not None:
        istanza_utility_id = istanza_del_billing_account(
            billing_account_id,
            istanza_utility_id,
            code="E_PRATICA_VALIDATION",
            function_name="pratiche_service.crea_pratica",
        )

    # Validazione coerenza contesto anagrafico (stesse regole del trigger DB,
    # qui per dare errori user-friendly via ServiceError). L'istanza e il ruolo
    # richiedono entrambi il soggetto. ⚠️ Il «prospect puro» (istanza senza
    # ruolo) non esiste piu': l'istanza nasce col BA e il ruolo CLIENTE con lei
    # (brief-db-istanza-nasce-col-ba, D-3). Il trigger non pretende il ruolo
    # accanto all'istanza, e qui non lo si aggiunge: e' una regola del DB.
    if istanza_utility_id is not None:
        ErrorManager.require(
            soggetto_id is not None,
            code="E_PRATICA_VALIDATION",
            message="istanza_utility_id richiede soggetto_id",
            context={"field": "soggetto_id"},
        )
    if soggetto_ruolo_id is not None:
        ErrorManager.require(
            soggetto_id is not None,
            code="E_PRATICA_VALIDATION",
            message="soggetto_ruolo_id richiede soggetto_id",
            context={"field": "soggetto_id"},
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
                context={"field": "tipo_prestazione_id"},
            )
        if not tipo_att["post_attivazione"] and ha_ba:
            raise ServiceError(
                code="E_PRATICA_VALIDATION",
                message="Tipo prestazione ammesso solo prima dell'attivazione cliente (pre-attivazione).",
                context={"field": "tipo_prestazione_id"},
            )

    # Risolve stato iniziale APERTA + default priorita' NORMALE se assente.
    stato_id = repo.resolve_stato_pratica("APERTA")
    if priorita_id is None:
        priorita_id = repo.resolve_priorita_pratica("NORMALE")
    try:
        return repo.create_pratica({
            "emittente_fiscale_id": emittente_fiscale_id,
            "tipo_prestazione_id": tipo_prestazione_id,
            "soggetto_id": soggetto_id,
            "soggetto_ruolo_id": soggetto_ruolo_id,
            "istanza_utility_id": istanza_utility_id,
            "billing_account_id": billing_account_id,
            "stato_id": stato_id,
            "priorita_id": priorita_id,
            "risorsa_umana_id": risorsa_umana_id,
            "unita_organizzativa_id": unita_organizzativa_id,
            "canale_origine_id": canale_origine_id,
            "descrizione": descrizione,
            "data_scadenza": data_scadenza,
            "meta": meta or {},
        })
    except DatabaseError as exc:
        # Pin definizione alla creazione (Fase 1, trgfn_pratiche_default_definizione
        # → fn_risolvi_definizione): un tipo senza definizione pubblicata risolvibile
        # solleva DEFINIZIONE_NON_TROVATA → ServiceError parlante invece di E_DATABASE
        # generico (rende effettivo il marker, altrimenti morto su questo percorso).
        _raise_known_db_error(exc, function_name="pratiche_service.crea_pratica")


_V_PRATICA = PayloadValidator(validation_code="E_PRATICA_VALIDATION")
# ⛔ I VALORI passano dal BB, non solo le chiavi: una data o un uuid
#    illeggibili erano un 500 del cast, `""` non diventava NULL e
#    `meta: "x"` scriveva una stringa jsonb. Il campo assente resta assente.
_LETTURE_PATCH_PRATICA: dict[str, Callable[[dict[str, Any], str], Any]] = {
    "descrizione": _V_PRATICA.optional_string,
    "data_scadenza": _V_PRATICA.optional_date,
    "soggetto_id": _V_PRATICA.optional_uuid,
    "risorsa_umana_id": _V_PRATICA.optional_positive_int,
    "unita_organizzativa_id": _V_PRATICA.optional_positive_int,
    "meta": _V_PRATICA.optional_meta,
}


# Scopo: Aggiorna i campi modificabili di una pratica.
@transaction.atomic()
def aggiorna_pratica(pratica_id: int, data: dict[str, Any]) -> None:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )

    repo = PraticheRepository()
    # Verifica esistenza pratica.
    pratica = repo.get_pratica(pratica_id)
    ErrorManager.require(
        pratica is not None,
        code="E_PRATICA_NOT_FOUND",
        message=f"Pratica {pratica_id} non trovata",
    )
    assert pratica is not None

    # ⛔ Una chiave fuori contratto e' un 400, e un PATCH senza campi pure (Tid,
    #    2026-10-20, brief-be-verifica-documentazione-api §A2/§B2): fino a quel
    #    giorno le chiavi ignote si scartavano e il PATCH vuoto rispondeva 200
    #    senza scrivere.
    _V_PRATICA.validate_allowed_keys(
        data, allowed=frozenset(PRATICA_UPDATE_SET), message="Campi della pratica non modificabili.",
    )
    _V_PRATICA.require_campi_da_aggiornare(data)
    dati = {k: leggi(data, k) for k, leggi in _LETTURE_PATCH_PRATICA.items() if k in data}
    try:
        repo.update_pratica(pratica_id, dati)
    except IntegrityError as exc:
        map_integrity_error(
            exc,
            fk_constraints={
                "fk_pratiche_soggetto": ("E_PRATICA_VALIDATION", "Soggetto inesistente.", "soggetto_id"),
                "fk_pratiche_risorsa_umana": (
                    "E_PRATICA_VALIDATION", "Risorsa umana inesistente.", "risorsa_umana_id",
                ),
                "fk_pratiche_unita_organizzativa": (
                    "E_PRATICA_VALIDATION", "Unita' organizzativa inesistente.", "unita_organizzativa_id",
                ),
            },
            fallback_code="E_PRATICA_VALIDATION",
        )


# Scopo: Transizione di stato di una pratica tramite codice_interno.
@transaction.atomic()
def cambia_stato_pratica(pratica_id: int, nuovo_stato: str) -> None:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    ErrorManager.require(
        bool(nuovo_stato),
        code="E_PRATICA_VALIDATION",
        message="nuovo_stato obbligatorio",
        context={"field": "nuovo_stato"},
    )

    repo = PraticheRepository()
    try:
        # Lo stato l'ha scelto il client: uno che non esiste e' un 400 sul
        # campo, non il 500 di un seed mancante (2026-10-20).
        repo.update_stato_pratica(
            pratica_id, nuovo_stato, codice_errore="E_PRATICA_VALIDATION", campo="nuovo_stato",
        )
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
    data_da: date | None = None,
    data_a: date | None = None,
    limit: int = DEFAULT_LIMIT,
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
        code="E_PRATICHE_LISTA_CONTESTO_PARAMETRI_ESCLUSIVI",
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
    ErrorManager.require(
        template_flusso_id is not None and template_flusso_id > 0,
        code="E_FLUSSO_VALIDATION",
        message="template_flusso_id obbligatorio e > 0: un flusso nasce sempre da un template del percorso.",
        context={"field": "template_flusso_id"},
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
        # Esclusione DOMINIO (brief-db-step-dominio §1.3 / companion BE-1.2): uno
        # step a esito calcolato dal dominio ha esito_default NULL (guard DB Inv3)
        # → auto_esito ricadrebbe sul fallback verdetto POSITIVO, che il guard di
        # classe (id 504) rifiuterebbe a runtime. Fail-safe prima del DB: uno step
        # DOMINIO su avvio resta IN_CORSO (come MANUALE) e si completa SOLO dal BB
        # di dominio (completa_step_pratica ← es. vendite.completa_smistamento).
        if modalita != "DOMINIO" and (result is not None or modalita == "AUTOMATICO"):
            repo.update_stato_flusso(flusso_id, "COMPLETATO", esito=auto_esito)
            # Azioni di dominio legate al COMPLETATO (template_flussi_handler_eventi).
            dispatch_handler_eventi(flusso_id, evento="COMPLETATO", esito=auto_esito, user=user)
        return result
    except DatabaseError as exc:
        # Guard pratica terminale (CHIUSA/ANNULLATA) → PRATICHE_TERMINALE_FLUSSO_
        # NON_MODIFICABILE parlante; altri errori (handler, ecc.) al middleware.
        _raise_known_db_error(exc, function_name="pratiche_service.avvia_flusso")


# Scopo: corpo del completamento (transizione COMPLETATO + azioni di dominio),
# SENZA validazione esito: i chiamanti pubblici (completa_flusso,
# avvia_e_completa_flusso) validano UNA volta e delegano qui — niente doppia
# lettura del vocabolario sul percorso CONTESTUALE.
def _completa_flusso_validato(
    flusso_id: int,
    *,
    esito: str,
    note_esito: str | None,
    user: str | None,
    meta: dict[str, Any] | None,
) -> None:
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
    # `meta` = contesto d'azione fornito dall'operatore (es. modalita/competenza
    # di fatturazione all'accettazione): passa all'handler, non viene persistito sul flusso.
    dispatch_handler_eventi(
        flusso_id, evento="COMPLETATO", esito=esito, user=user, extra_meta=meta,
    )


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
    meta: dict[str, Any] | None = None,
) -> None:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    _require_esito_valido(esito)
    _completa_flusso_validato(
        flusso_id, esito=esito, note_esito=note_esito, user=user, meta=meta,
    )


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
    meta: dict[str, Any] | None = None,
) -> None:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    # Valida l'esito PRIMA di qualsiasi scrittura: niente avvio "orfano" (flusso
    # lasciato IN_CORSO) se l'esito e' fuori dominio.
    _require_esito_valido(esito)

    repo = PraticheRepository()
    try:
        repo.update_stato_flusso(flusso_id, "IN_CORSO")
    except DatabaseError as exc:
        _raise_known_db_error(exc, function_name="pratiche_service.avvia_e_completa_flusso")
    # Riusa il corpo del completamento canonico (gia' validato sopra: niente
    # seconda lettura del vocabolario): COMPLETATO + esito + azioni di dominio
    # (template_flussi_handler_eventi), nella stessa transazione → atomico.
    # NB: CONTESTUALE NON esegue l'handler di AVVIO (dispatch_handler): e' la
    # modalita "esito deciso dall'operatore"; l'automazione d'avvio appartiene ad
    # AUTOMATICO/handler. Le reazioni di dominio all'esito viaggiano comunque su
    # dispatch_handler_eventi.
    _completa_flusso_validato(
        flusso_id, esito=esito, note_esito=note_esito, user=user, meta=meta,
    )


# Stati terminali di un flusso: mirror applicativo della derivazione data-driven
# DB (fn_pratica_flussi_aperti / trgfn_flussi_guard_pratica_terminale: stato senza
# transizione di stato in uscita attiva). Usato per l'idempotenza degli
# auto-completamenti di step (ri-azione dal programma base = no-op). La FK/guard DB
# resta autoritativa; questo mirror evita un round-trip sull'idempotenza.
_STATI_FLUSSO_TERMINALI = ("COMPLETATO", "ANNULLATO")


# Scopo: Completa (idempotente) il flusso ISTANZIATO di `template_codice` nel
# percorso della pratica. Building block di orchestrazione dominio→motore: i
# domini (vendite) risolvono la pratica dal proprio documento (preventivo/ordine)
# e delegano QUI il completamento dello step-per-codice, senza duplicare la logica
# percorso + idempotenza + scelta avvia-e-completa/completa (regola del 2:
# preventivi.completa_smistamento + ordini._completa_flusso_ordine_pratica).
# Ritorna {"flusso_id": id|None, "stato_precedente": str|None, "completato": bool}:
#   - flusso_id None → step non istanziato nel percorso (il caller decide se e' un
#     no-op legittimo o un errore);
#   - completato False con flusso_id valorizzato → step gia' terminale (no-op
#     idempotente su ri-azione);
#   - completato True → transizione effettuata (avvia+completa se DA_ESEGUIRE,
#     altrimenti completa).
def completa_step_pratica(
    pratica_id: int, *, template_codice: str, esito: str, user: str | None = None,
) -> dict[str, Any]:
    repo = PraticheRepository()
    step = next(
        (s for s in repo.get_percorso_pratica(pratica_id)
         if s.get("template_flusso_codice") == template_codice),
        None,
    )
    if step is None or step.get("flusso_id") is None:
        return {"flusso_id": None, "stato_precedente": None, "completato": False}
    stato = step.get("stato_codice_interno")
    flusso_id = int(step["flusso_id"])
    if stato in _STATI_FLUSSO_TERMINALI:
        return {"flusso_id": flusso_id, "stato_precedente": stato, "completato": False}
    if stato == "DA_ESEGUIRE":
        avvia_e_completa_flusso(flusso_id, esito=esito, user=user)
    else:
        completa_flusso(flusso_id, esito=esito, user=user)
    return {"flusso_id": flusso_id, "stato_precedente": stato, "completato": True}


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
    ErrorManager.require(
        bool(nuovo_stato),
        code="E_FLUSSO_VALIDATION",
        message="nuovo_stato obbligatorio",
        context={"field": "nuovo_stato"},
    )

    repo = PraticheRepository()
    try:
        # Lo stato l'ha scelto il client: vedi `cambia_stato_pratica`.
        repo.update_stato_flusso(
            flusso_id, nuovo_stato, esito=esito, note_esito=note_esito,
            codice_errore="E_FLUSSO_VALIDATION", campo="nuovo_stato",
        )
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
    extra_meta: dict[str, Any] | None = None,
) -> None:
    flusso = _flusso_per_dispatch(flusso_id)
    if flusso is None:
        return

    bindings = PraticheRepository().get_handler_eventi(flusso["template_flusso_id"], evento, esito)
    if not bindings:
        return

    from apps.pratiche.services.handler_registry import get_handler
    # meta = stato persistito del flusso + contesto transiente fornito
    # dall'operatore al completamento (es. modalita/competenza all'accettazione):
    # l'extra prevale sul persistito ma NON viene scritto su flusso.meta (input
    # d'azione, non stato). Le scelte durevoli le persiste l'handler sul dominio.
    meta = {**coerce_jsonb_dict(flusso["meta"]), **(extra_meta or {})}
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
    pratica_id: int, *, limit: int = DEFAULT_LIMIT_EVENTI, offset: int = 0,
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
        context={"field": "tipo_nota_codice"},
    )
    ErrorManager.require(
        bool(contenuto and contenuto.strip()),
        code="E_PRATICA_VALIDATION", message="contenuto nota obbligatorio",
        context={"field": "contenuto"},
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
        context={"field": "contenuto"},
    )
    repo = PraticheRepository()
    updated = repo.update_nota_pratica(nota_id, pratica_id, contenuto.strip())
    ErrorManager.require(updated, code="E_NOTA_NOT_FOUND", message=f"Nota {nota_id} non trovata per pratica {pratica_id}")


# Scopo: Elimina una nota.
@transaction.atomic()
def elimina_nota_pratica(nota_id: int, pratica_id: int) -> None:
    ErrorManager.require(pratica_id > 0, code="E_INVALID_ID", message="pratica_id deve essere > 0")
    ErrorManager.require(nota_id > 0, code="E_INVALID_ID", message="nota_id deve essere > 0")
    repo = PraticheRepository()
    deleted = repo.delete_nota_pratica(nota_id, pratica_id)
    ErrorManager.require(deleted, code="E_NOTA_NOT_FOUND", message=f"Nota {nota_id} non trovata per pratica {pratica_id}")


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
        context={"field": "tipo_allegato_codice"},
    )
    ErrorManager.require(
        bool(nome_file and nome_file.strip()),
        code="E_PRATICA_VALIDATION", message="nome_file obbligatorio",
        context={"field": "nome_file"},
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
    ErrorManager.require(deleted, code="E_ALLEGATO_NOT_FOUND", message=f"Allegato {allegato_id} non trovato per pratica {pratica_id}")


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
    data_inizio: datetime | None = None,
) -> int:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )
    ErrorManager.require(
        bool(motivo and motivo.strip()),
        code="E_PRATICA_VALIDATION",
        message="motivo sospensione obbligatorio",
        context={"field": "motivo"},
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


# Scopo: Riattiva una pratica sospesa.
# Obiettivo: chiude la sospensione attiva impostando data_fine = NOW().
# Perimetro: valida esistenza sospensione attiva, delega chiusura al repository.
#   Il trigger DB ripristina gli stati dei flussi, cambia stato pratica ad APERTA
#   e registra nel giornale.
@transaction.atomic()
def riattiva_pratica(pratica_id: int, *, data_fine: datetime | None = None) -> None:
    ErrorManager.require(
        pratica_id > 0,
        code="E_INVALID_ID",
        message="pratica_id deve essere > 0",
    )

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


# Scopo: ⭐ LA PRATICA A CUI UN FLUSSO APPARTIENE, dal solo id del flusso.
#
#        PERCHE' ESISTE. Tutte le rotte dei flussi sono annidate sotto la
#        pratica (`<pratica_id>/flussi/<flusso_id>/...`), e va benissimo finche'
#        si arriva DALLA pratica. Ma un flusso puo' essere nominato da fuori —
#        il BERSAGLIO di un errore ne e' il primo caso reale (`E_FLUSSI_*`,
#        roll-out del 2026-08-24) — e chi lo nomina ha in mano il solo id.
#        Senza questo, la dashboard non ha modo di aprirlo: il suo deep-link
#        vuole `pratica_id` e senza quello non fa niente.
#
#        ⚠️ NON e' un secondo modo di LEGGERE un flusso, ed e' la ragione per cui
#        risponde un id e non il flusso intero: il dettaglio resta uno solo
#        (`verifica_flusso_pratica`), con la sua verifica di appartenenza. Qui si
#        risponde a una domanda sola — «dove vive questa cosa?» — e chi la fa
#        prosegue dalla porta principale.
#
#        ⛔ LA VISIBILITA' LA DECIDE LA PRATICA, non il flusso — misurato:
#        `pratiche.flussi` non ha RLS, `pratiche.pratiche` si'. La lettura e'
#        agganciata alla pratica apposta (vedi `get_pratica_di_flusso`), cosi'
#        un flusso fuori perimetro e' indistinguibile da uno che non esiste.
#        Per chi opera e' la stessa cosa; per chi non deve vederlo, anche.
def pratica_di_flusso(flusso_id: int) -> int:
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    pratica_id = PraticheRepository().get_pratica_di_flusso(flusso_id)
    ErrorManager.require(
        pratica_id is not None,
        code="E_FLUSSO_NOT_FOUND",
        message=f"Flusso {flusso_id} non trovato",
    )
    assert pratica_id is not None
    return pratica_id


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
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )
    ErrorManager.require(
        bool(motivo and motivo.strip()),
        code="E_FLUSSO_VALIDATION",
        message="motivo sospensione obbligatorio",
        context={"field": "motivo"},
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
    ErrorManager.require(
        flusso_id > 0,
        code="E_INVALID_ID",
        message="flusso_id deve essere > 0",
    )

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
    ErrorManager.require(
        emittente_fiscale_id > 0,
        code="E_INVALID_ID",
        message="emittente_fiscale_id deve essere > 0",
    )

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
    ErrorManager.require(
        risorsa_umana_id > 0,
        code="E_INVALID_ID",
        message="risorsa_umana_id deve essere > 0",
    )

    repo = PraticheRepository()
    try:
        return repo.prendi_in_carico_flusso(flusso_id, risorsa_umana_id)
    except DatabaseError as exc:
        # Eligibilita' reparto-first (fn_prendi_in_carico_flusso): competenza
        # mancante (A/D) o operatore fuori reparto (B) → ServiceError parlante
        # invece di E_DATABASE generico. Altri errori al middleware.
        _raise_known_db_error(exc, function_name="pratiche_service.prendi_in_carico")


# Scopo: Lista operatori (risorse umane attive) di un reparto, per il picker di
# assegnazione flusso. Coerente con la policy "operatore di quel reparto".
def list_operatori_reparto(unita_organizzativa_id: int) -> list[dict[str, Any]]:
    ErrorManager.require(
        unita_organizzativa_id > 0,
        code="E_INVALID_ID",
        message="unita_organizzativa_id deve essere > 0",
    )

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
    ErrorManager.require(
        unita_organizzativa_id > 0,
        code="E_INVALID_ID",
        message="unita_organizzativa_id deve essere > 0",
    )
    ErrorManager.require(
        risorsa_umana_id > 0,
        code="E_INVALID_ID",
        message="risorsa_umana_id deve essere > 0",
    )

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

    repo = PraticheRepository()
    deleted = repo.delete_competenza_flusso(competenza_id)
    ErrorManager.require(
        deleted,
        code="E_FLUSSO_COMPETENZA_NOT_FOUND",
        message=f"Competenza {competenza_id} non trovata",
    )


