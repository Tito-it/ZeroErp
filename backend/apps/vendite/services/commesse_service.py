# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Servizio applicativo commesse — entry-point per le API REST.
# ------------------------------------------------------------

"""
Funzioni esposte:
- pr_run_commesse_push      — lancia l'orchestratore push commesse batch (write)
- pr_run_commesse_push_one  — push singolo documento sorgente filtrato (write)
- fn_get_commesse_push_log  — dettaglio di un push log (read)
- fn_get_commessa_stato     — stato e contatori di una commessa (read)
- fn_list_commessa_attivita — lista paginata attività di una commessa (read)
- approva_commessa_attivita — approvazione righe di una commessa (write, A-1)
- approva_attivita_competenza — approvazione massiva per mese (write, A-2)
- aggiungi_onere_commessa   — porta oneri: riga di puro valore (write)
- annulla_attivita_manuale  — annullamento di una riga manuale di commessa (write)
- cambia_stato_commessa     — azione di stato utente; ANNULLATA dal verbo DB (write)
- get_legami                — legami per la finestra di conferma dell'annullo (read)
"""

from collections.abc import Callable
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db import DatabaseError, transaction

from apps.config.sorgenti import (
    SORGENTE_ATTIVITA_CONSUMI,
    SORGENTE_COMMESSA,
    SORGENTE_CONTRATTO,
    SORGENTE_DDT_VENDITA,
    SORGENTE_ORDINE_VENDITA,
    SORGENTE_PREVENTIVO,
)
from apps.core.api.constants import DEFAULT_LIMIT, DEFAULT_LIMIT_EVENTI
from apps.core.db._helpers import (
    colonne_identita,
    sql_order_direction_lista,
    sql_tiebreak_direction,
)
from apps.core.services.diagnostica_best_effort import diagnostica_best_effort
from apps.core.services.documento_modello import e_stato_di_annullo
from apps.core.services.error_manager import ErrorManager
from apps.core.services.list_helpers import validate_enum_param, validate_order_params
from apps.core.services.payload_helpers import (
    PayloadValidator,
    translate_db_errors,
)
from apps.core.services.testata_guard import testata_o_not_found
from apps.anagrafiche.services.billing_account_service import istanza_del_billing_account
from apps.vendite.db.commesse_repository import (
    TESTATA_COMMESSE,
    ATTIVITA_SORT_COLUMNS,
    TIPO_MOVIMENTO_RETTIFICA,
    STATI_APPROVAZIONE_ATTIVITA,
    STATI_EMISSIONE_ATTIVITA,
    TIPO_MOVIMENTO_VALUES,
    CommesseRepository,
)
from apps.vendite.services._annullo_con_legami import (
    legami_del_documento,
    legami_confermati as dichiarazione_legami,
)
from apps.vendite.services.commesse_push_orchestrator import (
    CommessaPushOrchestrator,
    PushReport,
)
from apps.vendite.services.commesse_source_handlers import (
    BaseSourceHandler,
    HandlerContratti,
    HandlerConsumi,
    HandlerDdt,
    HandlerOrdini,
    HandlerPreventivi,
)
from apps.vendite.services.prezzo_riga_commessa import (
    argomenti_resolver,
    provenienza_da_resolver,
    provenienza_manuale,
)
from apps.vendite.services.pricing_service import PricingService

# Registry: codice config.sorgenti → handler class.
# Permette costruzione dinamica basata sulle sorgenti attive in DB.
_HANDLER_REGISTRY: dict[str, type[BaseSourceHandler]] = {
    SORGENTE_PREVENTIVO: HandlerPreventivi,
    SORGENTE_ORDINE_VENDITA: HandlerOrdini,
    SORGENTE_CONTRATTO: HandlerContratti,
    SORGENTE_DDT_VENDITA: HandlerDdt,
    SORGENTE_ATTIVITA_CONSUMI: HandlerConsumi,
}

# Stati `PushReport.stato` che richiedono rollback all-or-nothing nel push
# singolo (`pr_run_commesse_push_one`):
# - PARZIALE: almeno una riga fallita, alcune OK -> scritture inconsistenti
# - ERRORE: nessun handler senza errori (lock acquisito ma fallimento totale)
# COMPLETATO e SKIPPED NON sono qui: il primo e' successo, il secondo non
# ha tentato scritture (lock concorrente).
_STATI_PUSH_FALLIMENTO = frozenset({"PARZIALE", "ERRORE"})

_STATO_PUSH_COMPLETATO = "COMPLETATO"

# Codice del guard DB (497) che blocca l'approvazione di righe emittibili senza
# tipo_doc_fiscale_id. fn_log_and_raise_error lo include nel messaggio RAISE → lo
# riconosciamo nella stringa dell'eccezione per classificare i fallimenti del ponte.
_ERR_TIPO_DOC_MANCANTE = "E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO"


def _commesse_ids_da_report(report: PushReport) -> list[int]:
    """Unione ordinata delle commesse toccate da tutti gli handler del run."""
    ids: set[int] = set()
    for h in report.handlers:
        ids.update(h.commesse_ids)
    return sorted(ids)


# Scopo: Unione degli id attivita` upsertati dal run, raggruppati per commessa.
#        Alimenta il ponte di approvazione «il push approva le PROPRIE righe».
def _attivita_ids_da_report(report: PushReport) -> dict[int, list[int]]:
    out: dict[int, list[int]] = {}
    for h in report.handlers:
        for commessa_id, ids in h.attivita_ids_per_commessa.items():
            out.setdefault(commessa_id, []).extend(ids)
    return {cid: sorted(set(ids)) for cid, ids in out.items()}


# Scopo: Ponte di emittibilita` post-push — righe dell'invio APPROVATA +
#        testata PRONTA_FATTURAZIONE per una commessa toccata da un push
#        riuscito. Lo fa il DB, in una madre (`vendite.fn_rendi_commessa_emittibile`,
#        D-10 / R-9 di brief-db-annullo-a-valle-riapre-a-monte): il verso in
#        avanti verso la commessa sta nello stesso posto del ritorno. Qui si
#        passano le sole cose che sa chi orchestra: la commessa e le righe
#        di QUESTO invio.
def _rendi_commessa_emittibile(
    repo: CommesseRepository,
    *,
    commessa_id: int,
    righe_ids: list[int] | None = None,
    user: str | None = None,
) -> None:
    """Regola di modello (V9, generalizzata dal handler pratica al push):
    le viste `fn_list_*_da_pushare` ammettono SOLO documenti sorgente gia`
    autorizzati (preventivo ACCETTATO, ordine CONFERMATO, contratto ATTIVO,
    DDT, consumi) — il push e` quindi esso stesso l'autorizzazione delle
    attivita` generate. Senza questo ponte la commessa resta BOZZA/BOZZA e
    il ramo commessa→fattura e` dormiente (fn_list_commesse_emittibili non
    la vede mai).

    ⭐ Fino al 2026-10-12 erano due passi Python (approvazione + cambio di
    stato con lo skip «gia` pronta»): ora e` una madre DB, con la stessa
    semantica. Idempotente sulle righe e sulla testata gia` pronta; CHIUSA o
    ANNULLATA non sono silenziate di proposito: la matrice rifiuta forte —
    non si pusha su una commessa chiusa/annullata.

    Granularita` singola deliberata: il batch deve poter isolare il fallimento
    di una commessa senza perdere il ponte sulle altre (best-effort), il push
    singolo itera e lascia propagare (all-or-nothing).

    `righe_ids` = le righe che QUESTO push ha upsertato sulla commessa: il push
    e` l'autorizzazione delle attivita` che genera, non di quelle altrui. Senza
    il filtro approverebbe tutte le BOZZA+NON_EMESSA della commessa, spazzando
    ad APPROVATA righe di terzi in attesa (brief-db-immutabilita-quantita-e-
    porta-oneri §4b, trappola T1). Lista vuota = nessuna riga nostra atterrata:
    niente approvazione, ma la testata va comunque portata PRONTA_FATTURAZIONE.
    `None` = nessun filtro.
    """
    repo.rendi_commessa_emittibile(
        commessa_id=commessa_id, righe_ids=righe_ids, user=user,
    )


def _build_handlers(repo: CommesseRepository) -> list[BaseSourceHandler]:
    """Costruisce handler solo per le sorgenti attive in config.sorgenti.

    Ordine determinato da config.sorgenti.id (registrazione).
    Sorgenti attive in DB ma senza handler Python vengono silenziosamente
    ignorate (validate_sorgente_map le rileva come warning).
    """
    active_codes = repo.list_active_push_sources()
    return [
        _HANDLER_REGISTRY[codice](repo)
        for codice in active_codes
        if codice in _HANDLER_REGISTRY
    ]


# Scopo: Lancia l'orchestratore push commesse e restituisce il report serializzato.
def pr_run_commesse_push(
    *,
    source_types: list[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """Entrypoint servizio Python: esegue il push commesse da sorgenti esterne."""
    repo = CommesseRepository()
    handlers = _build_handlers(repo)

    if source_types is not None:
        valid_codes = {h.sorgente_codice for h in handlers}
        unknown = [s for s in source_types if s not in valid_codes]
        if unknown:
            ErrorManager.raise_error(
                code="E_COMMESSA_VALIDATION",
                message="Codici sorgente non validi.",
                detail=f"source_types non riconosciuti: {unknown}. Sorgenti attive: {sorted(valid_codes)}",
                context={"source_types": source_types, "unknown": unknown},
                function_name="vendite.commesse_service.pr_run_commesse_push",
            )

    orch = CommessaPushOrchestrator(repo, handlers)
    report = orch.run(source_types=source_types, dry_run=dry_run)

    # Ponte emittibilita` batch: best-effort per-commessa, coerente con la
    # semantica per-riga del batch (1 commessa rotta non blocca le altre).
    # Gli errori finiscono nel report, non sollevano.
    commesse_ids = _commesse_ids_da_report(report)
    attivita_per_commessa = _attivita_ids_da_report(report)
    emittibilita_errors: list[str] = []
    tipo_doc_mancante: list[int] = []
    if not dry_run:
        for commessa_id in commesse_ids:
            try:
                with transaction.atomic():
                    _rendi_commessa_emittibile(
                        repo,
                        commessa_id=commessa_id,
                        righe_ids=attivita_per_commessa.get(commessa_id, []),
                    )
            except Exception as exc:  # best-effort, report-driven
                # Una sola composizione del messaggio: finisce sia nel report
                # (con le coordinate davanti) sia nel payload dell'evento. Due
                # `f"{type(exc).__name__}: {exc}"` scritti a mano avrebbero
                # potuto divergere alla prima modifica.
                errore = f"{type(exc).__name__}: {exc}"
                emittibilita_errors.append(f"commessa_id={commessa_id}: {errore}")
                # Categoria a sé: il guard tipo_doc (497) segnala righe approvabili
                # con tipo_doc_fiscale_id mancante → altrimenti fatturato perso in
                # silenzio. Lo isoliamo per renderlo osservabile (dashboard/alert).
                tipo_doc_mancante_qui = _ERR_TIPO_DOC_MANCANTE in str(exc)
                if tipo_doc_mancante_qui:
                    tipo_doc_mancante.append(commessa_id)

                # ⭐ UNA RIGA DI GIORNALE PER COMMESSA FALLITA (consegna BE-4,
                #    D-3). Prima era UN evento aggregato a fine ciclo, con
                #    dentro la lista degli id: appeso a `TASK_RUN`, cioe' a un
                #    giro — che non e' un'entita' e non ha un emittente da cui
                #    derivare il perimetro. Il giornale oggi lo rifiuterebbe.
                #
                #    ⭐ E l'aggregato era sbagliato prima ancora del perimetro:
                #    chi apre la commessa 812 vuole vedere che il suo push e'
                #    fallito, non pescare il proprio id da una lista dentro il
                #    payload di un evento che sta da un'altra parte. La riga si
                #    lega alla cosa di cui parla.
                #
                # 🔴 `severity` VALE "WARN", NON "WARNING" (BE-1). Il CHECK
                #    `chk_event_log_severity` ammette INFO | WARN | ERROR: con
                #    "WARNING" questa scrittura sollevava 23514 e — non essendo
                #    in un try — faceva saltare `pr_run_commesse_push` PROPRIO
                #    nel ramo in cui qualcosa era gia' andato storto. In
                #    tabella: zero righe, per mesi. E' sopravvissuto perche' il
                #    test lo asseriva su un mock, che il CHECK non ce l'ha.
                #
                # ⚠️ Nel telaio best-effort (BE-7 / D-15): siamo gia' dentro un
                #    fallimento, e un difetto del diario non deve prendere il
                #    posto dell'errore che sta descrivendo. Fuori
                #    dall'`atomic` per costruzione — quello e' gia' rollbackato.
                # ⛔ `entity_type` ed `event_code` restano ARGOMENTI ESPLICITI,
                #    e non e' una preferenza: il cancello di CI che li confronta
                #    coi cataloghi (`test_event_codes_declared_guardrail`) legge
                #    l'AST dei punti di chiamata. Raccoglierli in un dict e
                #    passarlo con `**` — che sembra piu' pulito — rende il
                #    cancello CIECO su questa riga, in silenzio. Provato: dopo
                #    quella "semplificazione" il gate vedeva un `entity_type`
                #    invece di due.
                #
                # ⭐ Le variabili del ciclo si LEGANO come argomenti di default
                #    (ruff B023, dal 2026-09-28). Il telaio oggi invoca la
                #    funzione subito, ma una funzione che legge la variabile del
                #    ciclo e' giusta solo finche' nessuno la rimanda: legata,
                #    lo e' per costruzione, qualunque cosa faccia il telaio.
                def _diario(
                    commessa_id: int = commessa_id,
                    tipo_doc_mancante_qui: bool = tipo_doc_mancante_qui,
                    errore: str = errore,
                ) -> None:
                    repo.log_event(
                        entity_type="COMMESSA",
                        entity_id=commessa_id,
                        event_code="EMITTIBILITA_FALLITA",
                        severity="WARN",
                        payload={
                            "push_log_id": report.push_log_id,
                            "tipo_doc_mancante": tipo_doc_mancante_qui,
                            "errore": errore,
                        },
                    )

                diagnostica_best_effort(
                    _diario,
                    contesto={"commessa_id": commessa_id},
                    function_name="vendite.commesse_service.pr_run_commesse_push",
                )
    return {
        "stato": report.stato,
        "dry_run": report.dry_run,
        "push_log_id": report.push_log_id,
        "durata_ms": report.durata_ms,
        "handlers": [r.as_dict() | {"handler_name": r.handler_name} for r in report.handlers],
        "commesse_ids": commesse_ids,
        "emittibilita_errors": emittibilita_errors,
        "emittibilita_tipo_doc_mancante": tipo_doc_mancante,
    }


# Scopo: Variante puntuale del push commesse — esegue UN solo handler con
# filtro sulla riga sorgente identificata da `sorgente_id`. Riusa
# orchestrator (lock + log su commesse_push_log): differisce
# dal batch sia per perimetro (1 documento invece di N) sia per
# semantica transazionale: all-or-nothing. Un documento sorgente
# (preventivo/ordine/contratto/DDT/consumi) e' un'unita' transazionale
# singola — inviare un sottoinsieme delle sue righe lascerebbe commessa
# orfana e testata sorgente semi-evasa. Se anche solo una riga fallisce,
# rollback dell'intera scrittura (commesse + attivita + link sorgente +
# push_log) e raise E_COMMESSA_PUSH_PARZIALE_VIETATO.
# Il batch globale `pr_run_commesse_push` mantiene best-effort per-riga
# (cron giornaliero su N documenti: 1 riga rotta non blocca le altre).
# Usato dal pulsante UI "Push commessa" del drawer preventivo (e in futuro
# dai pulsanti analoghi su ordini/DDT). Validazione stretta sul codice
# sorgente per evitare run vuoti silenziosi su typo durante refactor.
def pr_run_commesse_push_one(
    *,
    sorgente_codice: str,
    sorgente_id: int,
    righe_ids: list[int] | None = None,
    dry_run: bool = False,
    user: str | None = None,
) -> dict:
    """Entrypoint servizio Python: push commesse di un singolo documento sorgente.

    `righe_ids` (opzionale): sottoinsieme righe del documento da pushare
    (smistamento selettivo dal Pannello Smistamento,
    brief-db-smistamento-preventivi.md C). None = tutte le eleggibili.
    Supportato oggi dalla sola sorgente PREVENTIVO (guard nel repository).
    """
    repo = CommesseRepository()
    handlers = _build_handlers(repo)

    valid_codes = {h.sorgente_codice for h in handlers}
    ErrorManager.require(
        sorgente_codice in valid_codes,
        code="E_COMMESSA_VALIDATION",
        message="Codice sorgente non valido per push singolo.",
        detail=f"sorgente_codice={sorgente_codice} non in {sorted(valid_codes)}",
        context={"sorgente_codice": sorgente_codice, "valid_codes": sorted(valid_codes)},
        function_name="vendite.commesse_service.pr_run_commesse_push_one",
    )
    ErrorManager.require(
        bool(sorgente_id and sorgente_id > 0),
        code="E_COMMESSA_VALIDATION",
        message="Identificativo sorgente non valido.",
        detail=f"sorgente_id={sorgente_id} deve essere intero positivo",
        context={"sorgente_id": sorgente_id},
        function_name="vendite.commesse_service.pr_run_commesse_push_one",
    )

    orch = CommessaPushOrchestrator(repo, handlers)

    # Atomic esterna: il raise sotto rolla TUTTE le scritture del run
    # (commesse, attivita, link sorgente, push_log).
    # L'advisory lock dell'orchestrator e' session-level e viene rilasciato
    # dal finally interno indipendentemente dal rollback della transazione.
    # Dry-run e' esente: in simulazione l'utente vuole il report diagnostico
    # (es. "3 OK + 1 fallirebbe"), non un errore generico — niente scritture
    # da proteggere, niente raise.
    with transaction.atomic():
        report = orch.run(
            source_types=[sorgente_codice],
            dry_run=dry_run,
            sorgente_id=sorgente_id,
            righe_ids=righe_ids,
        )
        if not dry_run and report.stato in _STATI_PUSH_FALLIMENTO:
            # Estrai il primo errore tra tutti gli handler per dare contesto
            # operativo. La user_message resta generica (policy); il detail
            # propaga il messaggio tecnico utile al fix dati/configurazione.
            first_error = next(
                (e for h in report.handlers for e in h.errors),
                "errore sconosciuto",
            )
            ErrorManager.raise_error(
                code="E_COMMESSA_PUSH_PARZIALE_VIETATO",
                message="Push fallito: nessuna riga inviata.",
                detail=first_error,
                hint="Risolvi la causa indicata e ri-prova il push.",
                context={
                    "sorgente_codice": sorgente_codice,
                    "sorgente_id": sorgente_id,
                    "stato_report": report.stato,
                    "errors_count": sum(len(h.errors) for h in report.handlers),
                },
                function_name="vendite.commesse_service.pr_run_commesse_push_one",
            )

        # Ponte emittibilita`: stessa transazione del push (all-or-nothing —
        # se la commessa non puo` diventare emittibile il push intero rolla,
        # coerente con la semantica del push singolo). COMPLETATO only:
        # SKIPPED non ha scritto nulla, dry-run non deve scrivere.
        commesse_ids = _commesse_ids_da_report(report)
        attivita_per_commessa = _attivita_ids_da_report(report)
        if not dry_run and report.stato == _STATO_PUSH_COMPLETATO:
            for commessa_id in commesse_ids:
                _rendi_commessa_emittibile(
                    repo,
                    commessa_id=commessa_id,
                    righe_ids=attivita_per_commessa.get(commessa_id, []),
                    user=user,
                )
    return {
        "stato": report.stato,
        "dry_run": report.dry_run,
        "push_log_id": report.push_log_id,
        "durata_ms": report.durata_ms,
        "handlers": [r.as_dict() | {"handler_name": r.handler_name} for r in report.handlers],
        "commesse_ids": commesse_ids,
    }


# Scopo: Restituisce il dettaglio di un push log per consultazione operativa.
def fn_get_commesse_push_log(*, push_log_id: int) -> dict:
    """Entrypoint servizio Python: dettaglio push log commesse."""
    ErrorManager.require(
        bool(push_log_id and push_log_id > 0),
        code="E_COMMESSA_VALIDATION",
        message="Parametri non validi.",
        detail="push_log_id obbligatorio e > 0",
        context={"push_log_id": push_log_id},
        function_name="vendite.commesse_service.fn_get_commesse_push_log",
        log_to_db=True,
    )
    repo = CommesseRepository()
    row = repo.get_push_log(push_log_id)
    if row is None:
        ErrorManager.raise_error(
            code="E_COMMESSA_PUSH_LOG_NOT_FOUND",
            message="Push log non trovato.",
            detail=f"Nessun push log con id={push_log_id}",
            context={"push_log_id": push_log_id},
            function_name="vendite.commesse_service.fn_get_commesse_push_log",
            log_to_db=True,
        )
    assert row is not None  # raise_error è NoReturn — aiuta il type checker
    return dict(row)


# Scopo: guard standard su commessa_id (intero positivo) condiviso dagli entrypoint
#        del service. Estratto (regola del 2): 3 occorrenze identiche tranne function_name.
# Scopo: La testata della commessa da `getter`, o il 404 del dominio (BB core
#        `testata_o_not_found`: qui solo codice e messaggio). Inesistente e
#        fuori perimetro sono lo stesso 404: i lettori girano sotto la RLS.
#        ⛔ Solo dove il DB non lo dice gia': davanti a un verbo che prende la
#        testata nel perimetro sarebbe la stessa regola in due sedi.
def _commessa_o_not_found(getter: Callable[[int], Any], commessa_id: int, *, function_name: str) -> Any:
    return testata_o_not_found(
        getter, commessa_id,
        code="E_COMMESSA_NOT_FOUND", message="Commessa non trovata.",
        id_name="commessa_id", function_name=function_name,
    )


def _guard_commessa_id(commessa_id: int, *, function_name: str) -> None:
    ErrorManager.require(
        bool(commessa_id and commessa_id > 0),
        code="E_COMMESSA_VALIDATION",
        message="Parametri non validi.",
        detail="commessa_id obbligatorio e > 0",
        context={"commessa_id": commessa_id},
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Restituisce stato e contatori di una commessa per consultazione operativa.
def fn_get_commessa_stato(*, commessa_id: int) -> dict:
    """Entrypoint servizio Python: stato commessa con contatori."""
    _guard_commessa_id(commessa_id, function_name="vendite.commesse_service.fn_get_commessa_stato")
    repo = CommesseRepository()
    stato = _commessa_o_not_found(
        repo.get_commessa_stato, commessa_id,
        function_name="vendite.commesse_service.fn_get_commessa_stato",
    )
    # Capability data-driven (azioni di stato utente + flag edit) per la UI: blob
    # da `script.fn_available_actions_commessa`, stesso pattern di ordini/preventivi/
    # offerte/contratti. Espone anche `stato_codice` (= sc.codice_interno).
    capabilities = repo.get_capabilities(commessa_id)
    # La TESTATA LEGGIBILE (Blocco C del brief modifiche certe): descrizione,
    # data di apertura, responsabile. `fn_get_commessa_stato` non le espone,
    # e il drawer le legge dallo STESSO payload — un secondo endpoint sarebbe
    # una seconda chiamata per tre colonne della stessa riga.
    # ⚠️ Puo' essere None solo se la commessa e' sparita fra le due letture:
    #    `get_commessa_stato` ha gia' risposto, quindi il 404 e' gia' passato.
    testata = repo.get_commessa_testata(commessa_id)
    return {
        "commessa_id": commessa_id,
        # `stato_codice_interno` (contratto smoke/FE: esito ponte emittibilità senza
        # seconda chiamata) derivato dal blob capability (de-dup 2026-06-16: evita il
        # round-trip dedicato `get_commessa_stato_codice`, gemello di `stato_codice`).
        "stato_codice_interno": capabilities.get("stato_codice"),
        **dict(stato),
        "descrizione": testata["descrizione"] if testata else None,
        # ISO, mai None a testata letta: `data_apertura` e' NOT NULL a DB.
        "data_apertura": testata["data_apertura"].isoformat() if testata else None,
        "responsabile_risorsa_umana_id": (
            testata["responsabile_risorsa_umana_id"] if testata else None
        ),
        "responsabile_display": testata["responsabile_display"] if testata else None,
        "capabilities": capabilities,
    }


# I campi di testata che l'operatore puo' scrivere. ⛔ `data_apertura` NON c'e':
# la scrive il default `script.fn_data_operativa()` alla nascita ed e' in sola
# lettura a video (brief modifiche certe §5.5, voce 4).
_TESTATA_KEYS: frozenset[str] = frozenset({
    "descrizione", "responsabile_risorsa_umana_id",
})
_DESCRIZIONE_MAX = 255  # varchar(255) a DB: anticipato col tetto del BB (400 col campo).
_V_TESTATA = PayloadValidator(validation_code="E_COMMESSA_VALIDATION", log_to_db=True)
# Il vincolo DB che nomina il responsabile: tradotto col campo, cosi' l'input
# si accende (`campiErrati`) invece di un «FK violata» anonimo.
_TESTATA_FK_CONSTRAINTS: dict[str, tuple] = {
    "fk_commesse_risorse_umane": (
        "E_VENDITE_FK",
        "Responsabile non valido.",
        "responsabile_risorsa_umana_id",
    ),
}


# Scopo: Aggiorna la testata leggibile della commessa — `descrizione` e
#        `responsabile_risorsa_umana_id` (Blocco C, brief modifiche certe).
#        PATCH parziale: si scrive solo cio' che il payload porta; `null`
#        esplicito AZZERA (togliere il responsabile e' un gesto legittimo).
#        Nessun guard di STATO: il DB non ne mette, di proposito — la
#        descrizione di una commessa chiusa si puo' correggere.
# ⭐ Il responsabile deve essere una persona ATTIVA, e lo dice il DB: il
#        require sul figlio (`trg_commesse_a10_risorse_umane_require_attivo_ins_upd`)
#        risponde `E_ATTIVO_PADRE_NON_ATTIVO` (CONFLITTO_STATO, 409) con la
#        colonna nel campo, e una persona inesistente e' la FK qui sotto.
#        Fino al 2026-11-07 il require diceva `E_ATTIVO_REQUIRE` (TECNICO, 500)
#        e il service lo anticipava con una lettura sua: ritirata con
#        brief-db-revisione-dbops BE3 (D46), la regola ha una sede sola.
def aggiorna_commessa_testata(commessa_id: int, payload: dict[str, Any]) -> dict:
    function_name = "vendite.commesse_service.aggiorna_commessa_testata"
    _guard_commessa_id(commessa_id, function_name=function_name)
    # Il payload per presenza (BB): chiave fuori contratto e PATCH senza campi
    # sono un 400; `null` sul responsabile lo toglie.
    dati = _V_TESTATA.campi_per_presenza(
        payload, ammesse=_TESTATA_KEYS,
        testi={"descrizione": (True, _DESCRIZIONE_MAX)},
        interi={"responsabile_risorsa_umana_id": True},
        message="Payload commessa non valido.",
        message_vuoto="Nessun campo aggiornabile nel payload commessa.",
        context_vuoto={"commessa_id": commessa_id, "allowed_keys": sorted(_TESTATA_KEYS)},
        function_name=function_name,
    )

    repo = CommesseRepository()
    with translate_db_errors(
        context={"op": "aggiorna_commessa_testata", "commessa_id": commessa_id},
        fallback_code="E_COMMESSA_VALIDATION",
        fallback_message="Testata commessa non aggiornata: dati non validi.",
        fk_constraints=_TESTATA_FK_CONSTRAINTS,
    ):
        toccata = repo.update_commessa_testata(commessa_id, dati)
    # Zero righe = commessa inesistente O fuori scope (RLS): stesso 404, come
    # ogni dettaglio by-id (api.md §Enforcement RLS).
    ErrorManager.require(
        toccata,
        code="E_COMMESSA_NOT_FOUND",
        message="Commessa non trovata.",
        detail=f"Nessuna commessa con id={commessa_id}",
        context={"commessa_id": commessa_id},
        function_name=function_name,
        log_to_db=True,
    )
    return fn_get_commessa_stato(commessa_id=commessa_id)


# Scopo: Azione di stato utente sulla testata commessa (rendi pronta, riapri,
#        chiudi, annulla) dal verbo `vendite.fn_cambia_stato_commessa`, sul
#        modello del documento (brief-modello-documento-vendita §14). Il
#        permesso lo legge la view dalla riga del passaggio
#        (`PassaggioDocumento`); il resto lo dice il DB: il passaggio di
#        processo chiesto a mano e lo stato che ha gia' il verbo, matrice e
#        condizioni il guard, uno stato ritirato il vocabolario.
#        ⛔ Ritirata la «difesa applicativa» (lo stato ammesso solo se era una
#        `available_action` abilitata, §14.6 punto 3): ripeteva quelle regole,
#        e nasceva perche' il verbo di prima non rifiutava i passaggi di
#        processo.
#        ⭐ ANNULLATA passa SEMPRE dal verbo `vendite.fn_annulla_commessa`
#        (brief-db-annullo-a-valle-riapre-a-monte D-2): con righe NON_EMESSA
#        il DB rifiuta (E_DOC_ANNULLO_CON_LEGAMI, `confirm_and_retry`) finche'
#        la richiesta non dichiara `legami_confermati`, il numero letto da
#        `get_legami`; il verbo ritira i legami (riapre a monte) e cambia lo
#        stato. Stessa forma di bolla, ordine, preventivo e contratto.
def cambia_stato_commessa(
    *, commessa_id: int, nuovo_stato: Any, legami_confermati: Any = None,
) -> dict:
    function_name = "vendite.commesse_service.cambia_stato_commessa"
    _guard_commessa_id(commessa_id, function_name=function_name)
    # Lo stato come lo legge `PassaggioDocumento`: un non-testo (null, numero)
    # e' assente, mai la sua stringa («None») mandata al verbo.
    nuovo_stato = nuovo_stato.strip() if isinstance(nuovo_stato, str) else ""
    ErrorManager.require(
        bool(nuovo_stato),
        code="E_COMMESSA_VALIDATION",
        message="Stato di destinazione obbligatorio.",
        detail="nuovo_stato mancante",
        context={"commessa_id": commessa_id},
        function_name=function_name,
        log_to_db=True,
    )

    repo = CommesseRepository()
    # ⛔ Nessun controllo «la commessa c'e'» qui (regola del 1, Tid
    #    2026-10-27): i due verbi prendono la testata nel perimetro e rifiutano
    #    da se' (E_COMMESSA_NON_TROVATA, 404). Fino al 2026-10-27 un lettore
    #    lo ridiceva col suo codice: la stessa regola in due sedi.
    # L'annullo (lo stato d'annullo del vocabolario, ANNULLATA) dal suo verbo.
    if e_stato_di_annullo(TESTATA_COMMESSE, nuovo_stato):
        confermati = dichiarazione_legami(
            legami_confermati, validation_code="E_COMMESSA_VALIDATION",
            function_name=function_name,
        )
        # Lo stato di partenza per la risposta: il verbo d'annullo rende i
        # soli legami. Un None (commessa che non c'e') non arriva al client:
        # il verbo rifiuta prima.
        stato_da = repo.get_commessa_stato_codice(commessa_id)
        with translate_db_errors(
            context={"op": "annulla_commessa", "commessa_id": commessa_id},
            fallback_code="E_COMMESSA_VALIDATION",
            fallback_message="Commessa non annullata.",
        ):
            repo.annulla(commessa_id, confermati)
        # Stessa forma della risposta del cambio di stato: chi chiama non sa
        # (e non deve sapere) che l'annullo e' passato da un verbo.
        return {
            "commessa_id": commessa_id,
            "stato_da": stato_da,
            "stato_a": nuovo_stato,
        }

    with translate_db_errors(
        context={"op": "cambia_stato_commessa", "commessa_id": commessa_id},
        fallback_code="E_COMMESSA_VALIDATION",
        fallback_message="Stato della commessa non cambiato.",
    ):
        return repo.cambia_stato_commessa(commessa_id=commessa_id, nuovo_stato=nuovo_stato)


# Scopo: I legami della commessa per la finestra di conferma dell'annullo (BB
#        `legami_del_documento`): le righe NON_EMESSA, ciascuna col documento
#        (o il consumo, il reso) da cui viene, o l'onere che si annulla. Prima
#        la testata: il lettore del DB e' SECURITY DEFINER e non applica il
#        perimetro (fuori perimetro = 404, come ogni dettaglio by-id).
def get_legami(commessa_id: int) -> dict[str, Any]:
    function_name = "vendite.commesse_service.get_legami"
    _guard_commessa_id(commessa_id, function_name=function_name)
    repo = CommesseRepository()
    _commessa_o_not_found(repo.get_commessa_stato_codice, commessa_id, function_name=function_name)
    return legami_del_documento(SORGENTE_COMMESSA, commessa_id)


# Scopo: Helper — valida una lista opzionale di id dal payload (righe_ids,
#        commessa_ids): None = nessun filtro (semantica del chiamante); se presente
#        deve essere lista non vuota di interi positivi. Lista vuota = 400
#        (ambiguo: per "tutti" omettere il campo).
def _parse_ids_list(raw: object, *, field: str, function_name: str) -> list[int] | None:
    if raw is None:
        return None
    valid = isinstance(raw, list) and len(raw) > 0 and all(
        isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in raw
    )
    ErrorManager.require(
        valid,
        code="E_COMMESSA_VALIDATION",
        message=f"{field} non valido.",
        detail=f"{field}: lista non vuota di interi positivi, oppure omesso",
        context={field: raw},
        function_name=function_name,
        log_to_db=True,
    )
    assert isinstance(raw, list)
    return [int(v) for v in raw]


# Scopo: Azione APPROVA sulle attivita' di una commessa (cockpit Fase A, A-1):
#        porta le righe BOZZA+NON_EMESSA ad APPROVATA via
#        vendite.fn_approva_commessa_attivita (idempotente: gia' APPROVATA = 0).
#        righe_ids None = tutte le righe NON_EMESSA della commessa; altrimenti solo
#        le righe indicate. Il gate di permesso (`approva_attivita_commessa`) e'
#        applicato dalla view; qui il guard dell'input, l'esistenza la dice la fn.
def approva_commessa_attivita(
    *, commessa_id: int, righe_ids: list[int] | None = None, user: str | None = None,
) -> dict:
    _fn = "vendite.commesse_service.approva_commessa_attivita"
    _guard_commessa_id(commessa_id, function_name=_fn)
    righe_ids = _parse_ids_list(righe_ids, field="righe_ids", function_name=_fn)

    repo = CommesseRepository()
    # ⛔ Nessun controllo «la commessa c'e'» qui (regola del 1, Tid
    #    2026-10-27): `fn_approva_commessa_attivita` e' INVOKER su
    #    `vendite.commesse`, che ha la RLS, e rifiuta da se' la commessa che
    #    non c'e' o non si vede (E_COMMESSA_NON_TROVATA, 404).
    with translate_db_errors(
        context={"op": "approva_commessa_attivita", "commessa_id": commessa_id},
        fallback_code="E_COMMESSA_VALIDATION",
        fallback_message="Attivita' della commessa non approvate.",
    ):
        approvate = repo.approva_commessa_attivita(
            commessa_id=commessa_id, righe_ids=righe_ids, user=user,
        )
    return {"commessa_id": commessa_id, "approvate": approvate}


# Scopo: Azione APPROVA massiva per mese di competenza (cockpit Fase A, A-2):
#        approva TUTTE le attivita' in stadio DA_APPROVARE del mese M — esattamente
#        la popolazione che la card della Dashboard Competenza mostra (stessa vista
#        del drill-down, scope emittente in-vista). All-or-nothing: il loop per
#        commessa gira in UNA transazione (guardrail «una azione = una unita'
#        atomica»); la fn DB e' idempotente, quindi il retry post-errore e' innocuo.
#        commessa_ids opzionale restringe il perimetro (subset del mese).
def approva_attivita_competenza(
    *,
    competenza_mese: date,
    commessa_ids: list[int] | None = None,
    user: str | None = None,
) -> dict:
    _fn = "vendite.commesse_service.approva_attivita_competenza"
    ErrorManager.require(
        competenza_mese is not None,
        code="E_COMMESSA_VALIDATION",
        message="Mese di competenza obbligatorio.",
        detail="competenza_mese mancante (ISO YYYY-MM-DD)",
        function_name=_fn,
        log_to_db=True,
    )
    assert competenza_mese is not None
    commessa_ids = _parse_ids_list(commessa_ids, field="commessa_ids", function_name=_fn)
    competenza = competenza_mese.replace(day=1)

    repo = CommesseRepository()
    totale = 0
    # Snapshot + scritture nella STESSA transazione: la popolazione approvata e'
    # quella letta (niente finestra fra SELECT e loop). Piu' scritture (una fn
    # per commessa) = una sola unita' atomica.
    with transaction.atomic():
        gruppi = repo.list_da_approvare_per_competenza(
            competenza_mese=competenza, commessa_ids=commessa_ids,
        )
        for cid, attivita_ids in gruppi:
            totale += repo.approva_commessa_attivita(
                commessa_id=cid, righe_ids=attivita_ids, user=user,
            )
    # Nessuna attivita' da approvare nel perimetro: esito onesto a zero, non errore.
    if not gruppi:
        return {"competenza_mese": competenza.isoformat(), "commesse": 0, "approvate": 0}
    return {
        "competenza_mese": competenza.isoformat(),
        "commesse": len(gruppi),
        "approvate": totale,
    }


# --- Porta oneri (brief-db-immutabilita-quantita-e-porta-oneri §4c) ---

# Marker P0001 → codice applicativo per gli errori della madre DB. Substring
# stretti sul MESSAGE (pattern `PricingService._KNOWN_DB_ERROR_MARKERS`): i
# codici sono emessi da `script.fn_log_and_raise_error` e non sono localizzati.
_ONERE_DB_ERROR_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("E_ONERE_IMPORTO_NON_VALIDO", ("E_ONERE_IMPORTO_NON_VALIDO",)),
    ("E_ONERE_ARTICOLO_MANCANTE", ("E_ONERE_ARTICOLO_MANCANTE",)),
    # ⛔ `E_ONERE_CAUSALE_NON_VALIDA` NON e' piu' qui (2026-09-21): nessuna funzione
    #    viva lo solleva (pg_proc a zero occorrenze) e un marker per un codice
    #    che nessuno manda e' una promessa vuota. Ritiro a catalogo chiesto al
    #    team DB (brief-be-presidio-ui-action-e-canale-campi §3-bis.2, dec. 7).
    ("E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO", (_ERR_TIPO_DOC_MANCANTE,)),
    # Guard race progressivo segment_key (DB 557, brief-db-race-segment-key-
    # onere): senza questo marker il codice cadrebbe sul fallback
    # E_COMMESSA_VALIDATION (400), scavalcando la policy 409 registrata in
    # error_policies. La coppia policy+marker va tenuta insieme.
    ("E_ONERE_SEGMENT_DUPLICATO", ("E_ONERE_SEGMENT_DUPLICATO",)),
)


# Scopo: Helper — parsing importo onere (numerico, > 0). Distinto da
#        `_parse_prezzo` (che parla di `prezzo` ed e` legato agli endpoint N5/N7):
#        qui il campo si chiama `importo` e il messaggio deve nominarlo.
#        La coercizione (bool e NaN rifiutati) e' del BB; qui resta il `> 0`.
def _parse_importo(raw: object, *, function_name: str) -> Decimal:
    importo = _V_TESTATA.coerce_decimal(raw, field="importo", function_name=function_name)
    # Guard applicativo anticipato: il DB rifiuta comunque (`E_ONERE_IMPORTO_NON
    # _VALIDO`, 552), ma un 400 parlante evita il round-trip sul caso banale.
    ErrorManager.require(
        importo > 0,
        code="E_COMMESSA_VALIDATION",
        message="Importo non valido.",
        detail="L`importo dell`onere deve essere maggiore di zero.",
        context={"importo": str(importo)},
        function_name=function_name,
        log_to_db=True,
    )
    return importo


# Scopo: Porta oneri — aggiunge alla commessa una riga di PURO VALORE (qta=1,
#        `tipo_movimento='ONERE'`, sourceless) gia' APPROVATA, derivando causale,
#        unita' di misura e IVA dall'ARTICOLO-ONERE passato.
#        Perimetro: un solo onere per chiamata, delegato interamente alla madre
#        DB `vendite.fn_aggiungi_onere_commessa` (una SELECT = unita' atomica,
#        riga + audit `commesse_attivita_log` insieme). Qui vivono solo: guard di
#        input, esistenza commessa (404 parlante) e derivazione dell'istanza
#        utility dal billing account della commessa quando il chiamante non la
#        specifica. Risultato: id della riga creata.
#        Il presidio di autorizzazione (`carica_voce_manuale`) e' sulla view: la
#        madre resta usabile anche da un processo autorizzato.
def aggiungi_onere_commessa(
    *,
    commessa_id: int,
    articolo_onere_id: object,
    importo: object,
    tipo_doc_fiscale_id: int | None,
    istanza_utility_id: int | None = None,
    motivo: str | None = None,
    data_attivita: date | None = None,
) -> dict:
    _fn = "vendite.commesse_service.aggiungi_onere_commessa"
    _guard_commessa_id(commessa_id, function_name=_fn)

    # Articolo-onere: qui solo la forma (UUID). Che sia davvero un onere —
    # attivo, con `causale_onere_id` valorizzato — lo stabilisce il DB
    # (E_ONERE_ARTICOLO_MANCANTE): unica fonte di verita', non duplicata.
    try:
        if articolo_onere_id is None:
            raise ValueError("articolo_onere_id assente")
        articolo_uuid = str(UUID(str(articolo_onere_id)))
    except (TypeError, ValueError):
        ErrorManager.raise_error(
            code="E_COMMESSA_VALIDATION",
            message="Articolo onere non valido.",
            detail=(
                "articolo_onere_id obbligatorio (UUID di un articolo-onere), "
                f"ricevuto: {articolo_onere_id!r}."
            ),
            context={"field": "articolo_onere_id"},
            function_name=_fn,
            log_to_db=True,
        )

    importo_dec = _parse_importo(importo, function_name=_fn)

    # tipo_doc obbligatorio: la riga nasce APPROVATA+NON_EMESSA = emittibile, e
    # il guard DB `tipo_doc_emittibile` lo esige (§4c.8 del brief).
    ErrorManager.require(
        bool(tipo_doc_fiscale_id and tipo_doc_fiscale_id > 0),
        code="E_COMMESSA_VALIDATION",
        message="Tipo documento fiscale obbligatorio.",
        detail="tipo_doc_fiscale_id obbligatorio e > 0: la riga onere nasce emittibile.",
        context={"field": "tipo_doc_fiscale_id"},
        function_name=_fn,
        log_to_db=True,
    )
    assert tipo_doc_fiscale_id is not None

    # Type-check esplicito PRIMA dello strip: un `motivo` non-stringa dal
    # payload (es. numero) farebbe AttributeError → 500 E_INTERNAL invece di
    # un 400 parlante (review 2026-07-23).
    ErrorManager.require(
        motivo is None or isinstance(motivo, str),
        code="E_COMMESSA_VALIDATION",
        message="Motivo non valido.",
        detail=f"Il campo 'motivo' deve essere una stringa, ricevuto: {motivo!r}.",
        context={"field": "motivo"},
        function_name=_fn,
        log_to_db=False,
    )
    motivo_norm = (motivo or "").strip() or None
    if motivo_norm is not None:
        ErrorManager.require(
            len(motivo_norm) <= _MOTIVO_MAX_LENGTH,
            code="E_COMMESSA_VALIDATION",
            message="Motivo troppo lungo.",
            detail=f"Massimo {_MOTIVO_MAX_LENGTH} caratteri.",
            context={"field": "motivo", "length": len(motivo_norm)},
            function_name=_fn,
            log_to_db=False,
        )

    repo = CommesseRepository()
    # ⚠️ `get_commessa_stato` ritorna un `CommessaStatoResult`, che e' un
    # **TypedDict**: a runtime e' un dict normale e si legge con `stato["x"]`.
    # L'accesso ad attributo (`stato.x`) compila, passa i test se lo stato e'
    # mockato con un MagicMock — che accetta qualunque attributo — e poi
    # esplode in produzione con AttributeError (difetto del 2026-07-28,
    # rilevato solo alla prova in-app della porta oneri).
    stato = _commessa_o_not_found(repo.get_commessa_stato, commessa_id, function_name=_fn)

    # Istanza utility: un billing account ha UNA sola istanza (FK NOT NULL,
    # immutabile: E_BA_ISTANZA_IMMUTABILE) — un'istanza invece ne ha uno per
    # utility (brief-db-istanza-nasce-col-ba; fino al 2026-10-09 qui si diceva
    # «modello 1:1») — quindi la derivazione dal BA della
    # commessa e' ESATTA e l'istanza esplicita del chiamante DEVE coincidere
    # con quella derivata: senza il confronto si potrebbe agganciare l'onere
    # all'istanza di un ALTRO cliente (la FK verifica solo l'esistenza —
    # review 2026-07-23, ok Tid). La regola e' il BB
    # `istanza_del_billing_account` (lo stesso di pratica e preventivo); qui
    # l'errore cade sull'ISTANZA, perche' il BA e' della commessa e l'operatore
    # non lo sceglie.
    # La FK sul BA della commessa e' nullable (ON DELETE SET NULL): senza BA
    # l'onere non ha un'istanza a cui agganciarsi, ne' derivata ne' verificabile.
    billing_account_id = stato["billing_account_id"]
    ErrorManager.require(
        billing_account_id is not None,
        code="E_COMMESSA_VALIDATION",
        message="Istanza utility non risolvibile: la commessa non ha un billing account.",
        detail=f"commessa_id={commessa_id} senza billing_account_id.",
        context={"field": "istanza_utility_id", "commessa_id": commessa_id},
        function_name=_fn,
        log_to_db=True,
    )
    assert billing_account_id is not None
    istanza_utility_id = istanza_del_billing_account(
        billing_account_id,
        istanza_utility_id,
        code="E_COMMESSA_VALIDATION",
        function_name=_fn,
        campo="istanza_utility_id",
    )

    try:
        attivita_id = repo.aggiungi_onere(
            commessa_id=commessa_id,
            istanza_utility_id=istanza_utility_id,
            articolo_onere_id=articolo_uuid,
            importo=importo_dec,
            tipo_doc_fiscale_id=tipo_doc_fiscale_id,
            motivo=motivo_norm,
            data_attivita=data_attivita,
        )
    except DatabaseError as exc:
        # I guard della madre (importo, articolo-onere, causale, tipo_doc) sono
        # errori d'uso: vanno all'operatore col loro codice, non come E_DATABASE.
        ErrorManager.raise_from_database_error(
            exc,
            known_markers=_ONERE_DB_ERROR_MARKERS,
            fallback_code="E_COMMESSA_VALIDATION",
            message="Onere non caricato: dati non validi.",
            context={"commessa_id": commessa_id, "articolo_onere_id": articolo_uuid},
            function_name=_fn,
        )

    return {
        "commessa_id": commessa_id,
        "attivita_id": attivita_id,
        "importo": str(importo_dec),
    }


# Scopo: il verso dell'elenco attivita' (`asc`/`desc`) da passare alla fn DB,
#        che senza direzione parte crescente (`COALESCE(p_order_dir,'asc')`).
# ⛔ Lo decide il BB delle liste (`sql_order_direction_lista`), non un default
#    scritto qui: una colonna data senza direzione parte DESC come in ogni altra
#    lista. Fino al 2026-10-20 il service passava `order_dir or "asc"`, e la
#    regola non arrivava mai alla query (brief-be-verifica-documentazione-api §6.1).
def _verso_attivita(order_by: str | None, order_dir: str | None) -> str:
    direzione = sql_order_direction_lista(
        order_by, order_dir, colonne=colonne_identita(*ATTIVITA_SORT_COLUMNS),
    )
    return sql_tiebreak_direction(direzione).lower()


# Scopo: Restituisce la lista paginata delle attività di una commessa.
def fn_list_commessa_attivita(
    *,
    commessa_id: int,
    stato_emissione: str | None = None,
    stato_approvazione: str | None = None,
    competenza_mese: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    order_by: str | None = None,
    order_dir: str | None = None,
    tipo_movimento: str | None = None,
    max_rows: int | None = None,
) -> dict:
    """Entrypoint servizio Python: lista attività commessa (paginata).

    `max_rows` valorizzato = percorso EXPORT: salta la paginazione (e quindi il
    tetto di pagina qui sotto), fino al tetto della fn DB.
    """
    _guard_commessa_id(commessa_id, function_name="vendite.commesse_service.fn_list_commessa_attivita")
    # ⛔ La finestra (`limit` fra 1 e il tetto, `offset` non negativo) la
    #    valida la view con `pagina_da_query`, che dal 2026-10-21 risponde 400
    #    sul fuori limite (Tid): qui era una seconda copia, irraggiungibile.
    # Ordinamento validato PRIMA di toccare il DB (un parametro sbagliato non
    # deve costare un round-trip): whitelist ATTIVITA_SORT_COLUMNS, specchio
    # della mappa chiusa dentro la fn. None = ordine storico ca.id.
    # ⚠️ Si valida SEMPRE, non solo con la colonna (2026-09-26): la direzione
    #    va giudicata anche sul ramo «ordine storico», che la ignora — prima
    #    `?order_dir=giu` senza `order_by` arrivava muto alla fn. `nullable`
    #    ammette l'assenza di entrambi, come prima il ramo saltato.
    order_by, order_dir = validate_order_params(
        order_by,
        order_dir,
        allowed_columns=ATTIVITA_SORT_COLUMNS,
        error_code="E_COMMESSA_VALIDATION",
        function_name="vendite.commesse_service.fn_list_commessa_attivita",
        nullable=True,
    )
    # I due stati della riga nel loro vocabolario (specchi dei CHECK), o un 400
    # sul campo: prima un valore sbagliato rispondeva lista vuota (2026-10-20).
    for nome, valore, ammessi in (
        ("stato_emissione", stato_emissione, STATI_EMISSIONE_ATTIVITA),
        ("stato_approvazione", stato_approvazione, STATI_APPROVAZIONE_ATTIVITA),
    ):
        validate_enum_param(
            valore, allowed=ammessi, param_name=nome,
            error_code="E_COMMESSA_VALIDATION",
            function_name="vendite.commesse_service.fn_list_commessa_attivita",
        )
    # Filtro movimento: vocabolario chiuso, validato PRIMA del round-trip come
    # l'ordinamento. ⚠️ Vuoto e None sono la STESSA cosa — «tutti i movimenti» —
    # e non un valore da validare: un filtro azzerato dal frontend arriva come
    # stringa vuota, e rifiutarlo direbbe «valore non valido» a chi ha appena
    # tolto il filtro.
    if tipo_movimento is not None:
        tipo_movimento = tipo_movimento.strip().upper() or None
    if tipo_movimento is not None:
        ErrorManager.require(
            tipo_movimento in TIPO_MOVIMENTO_VALUES,
            code="E_COMMESSA_VALIDATION",
            message="Parametri non validi.",
            detail=f"tipo_movimento non ammesso: {tipo_movimento}",
            context={"commessa_id": commessa_id, "tipo_movimento": tipo_movimento},
            function_name="vendite.commesse_service.fn_list_commessa_attivita",
            log_to_db=True,
        )

    from apps.core.api.payload_validators import optional_iso_date as _parse_date

    competenza_mese_date = _parse_date({"competenza_mese": competenza_mese}, "competenza_mese") if competenza_mese else None

    repo = CommesseRepository()
    data = repo.list_commessa_attivita(
        commessa_id,
        stato_emissione=stato_emissione,
        stato_approvazione=stato_approvazione,
        competenza_mese=competenza_mese_date,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=_verso_attivita(order_by, order_dir),
        tipo_movimento=tipo_movimento,
        max_rows=max_rows,
    )
    return {"commessa_id": commessa_id, **data}


# --- N5, N7, N7-sblocco: Pricing operations su commessa ---

_MOTIVO_MAX_LENGTH = 500


E_VENDITE_VALIDATION = "E_VENDITE_VALIDATION"

# Validator modulo-level per l'estrazione del campo meta (JSONB). log_to_db=True
# per telemetria pipeline vendite; function_name override per-chiamata. Delega a
# PayloadValidator.optional_meta del core (review X1: la versione locale
# permissiva bubble-ava ValueError -> 500 e scartava silenziosamente l'audit).
_V = PayloadValidator(validation_code=E_VENDITE_VALIDATION, log_to_db=True)


# Scopo: Helper — carica attivita` con dati pricing e applica guard standard.
def _get_attivita_pricing_or_raise(
    commessa_id: int,
    attivita_id: int,
    *,
    function_name: str,
) -> dict[str, Any]:
    repo = CommesseRepository()
    att = repo.get_attivita_pricing(commessa_id, attivita_id)
    ErrorManager.require(
        att is not None,
        code="E_COMMESSA_ATTIVITA_NOT_FOUND",
        message="Attivita` commessa non trovata.",
        detail=f"Nessuna attivita` id={attivita_id} per commessa id={commessa_id}.",
        context={"commessa_id": commessa_id, "attivita_id": attivita_id},
        function_name=function_name,
        log_to_db=False,
    )
    assert att is not None
    return att


# Scopo: Helper — guard stato commessa modificabile. Data-driven sul flag
#        `stati_commessa.modificabile` (abilita upsert su commesse_attivita),
#        non su un set di codici hardcoded: lo stato lifecycle vive nella FK
#        stato_commessa_id e il flag e` la fonte di verita` per "si puo` ancora
#        toccare il prezzo". get_attivita_pricing espone `commessa_modificabile`.
def _assert_commessa_modificabile(
    att: dict[str, Any],
    *,
    function_name: str,
) -> None:
    stato = str(att["commessa_stato"])
    ErrorManager.require(
        bool(att.get("commessa_modificabile")),
        code="E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA",
        message="Operazione non consentita sullo stato corrente della commessa.",
        detail=f"Commessa in stato {stato}: non modificabile (stati_commessa.modificabile=false).",
        context={"commessa_stato": stato},
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Helper — guard riga non ancora fatturata.
# Scopo: il prezzo di una RETTIFICA non si tocca — non e' suo. E' copiato dalla
#        riga di fattura che rettifica, e cambiarlo farebbe accreditare un
#        importo diverso da quello fatturato: una nota di credito che non
#        corrisponde piu' al documento che dichiara di correggere.
# ⚠️ Questo e' un PRESIDIO, non il blocco. Il blocco vero e'
#        `vendite.trgfn_commesse_attivita_guard_prezzo_rettifica` sulla tabella,
#        e deve restare li': il prezzo si scrive con una UPDATE diretta
#        (`update_attivita_prezzo`), quindi un controllo solo qui sarebbe una
#        convenzione che chiunque scriva quella colonna per un'altra strada
#        aggirerebbe senza accorgersene.
# ⭐ Serve a dire la stessa cosa PRIMA e MEGLIO: un 400 parlante dal posto
#        giusto invece del 409 che risalirebbe dal trigger a UPDATE gia' tentata.
def _assert_prezzo_modificabile(
    att: dict[str, Any],
    *,
    function_name: str,
) -> None:
    tipo_movimento = str(att.get("tipo_movimento") or "")
    ErrorManager.require(
        tipo_movimento != TIPO_MOVIMENTO_RETTIFICA,
        code="E_COMMESSA_ATTIVITA_PREZZO_RETTIFICA_IMMUTABILE",
        message="Il prezzo di una rettifica di nota di credito non si modifica.",
        detail=(
            "La riga e` una RETTIFICA: il prezzo e` copiato dalla riga di fattura "
            "che rettifica e deve restare uguale a quella. Per disfare "
            "l`accredito: «Annulla l`accredito» sulla riga del reso."
        ),
        context={"attivita_id": att.get("id"), "tipo_movimento": tipo_movimento},
        function_name=function_name,
        log_to_db=True,
    )


def _assert_non_fatturata(
    att: dict[str, Any],
    *,
    function_name: str,
) -> None:
    ErrorManager.require(
        att.get("fattura_riga_id") is None,
        code="E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA",
        message="Operazione bloccata: riga gia` fatturata.",
        detail="La riga ha un fattura_riga_id valorizzato. Non e` possibile modificare il prezzo.",
        context={"fattura_riga_id": att.get("fattura_riga_id")},
        function_name=function_name,
        log_to_db=True,
    )


# Scopo: Helper — parsing prezzo dal payload: la coercizione e' del BB, il
#        `> 0` e' di dominio e resta qui con la sua frase.
def _parse_prezzo(payload: dict[str, Any], *, function_name: str) -> Decimal:
    prezzo = _V_TESTATA.require_decimal(payload, "prezzo", function_name=function_name)
    ErrorManager.require(
        prezzo > 0,
        code="E_COMMESSA_VALIDATION",
        message="Prezzo non valido.",
        detail="Il prezzo deve essere maggiore di zero.",
        context={"prezzo": str(prezzo)},
        function_name=function_name,
        log_to_db=True,
    )
    return prezzo


# Scopo: Helper — parsing motivo obbligatorio dal payload. `code` parametrico
#        perche' l'annullamento riga manuale ha un codice DEDICATO
#        (`E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO`, 567) simmetrico a quello della
#        madre DB: il messaggio deve essere lo stesso da qualunque lato arrivi.
def _parse_motivo(
    payload: dict[str, Any],
    *,
    function_name: str,
    code: str = "E_COMMESSA_VALIDATION",
) -> str:
    motivo = payload.get("motivo")
    ErrorManager.require(
        motivo and isinstance(motivo, str) and motivo.strip(),
        code=code,
        message="Motivo obbligatorio.",
        detail="Il campo motivo e` obbligatorio per questa operazione.",
        context={"field": "motivo"},
        function_name=function_name,
        log_to_db=True,
    )
    assert isinstance(motivo, str)
    motivo = motivo.strip()
    ErrorManager.require(
        len(motivo) <= _MOTIVO_MAX_LENGTH,
        code=code,
        message="Motivo troppo lungo.",
        detail=f"Massimo {_MOTIVO_MAX_LENGTH} caratteri.",
        context={"field": "motivo", "length": len(motivo)},
        function_name=function_name,
        log_to_db=False,
    )
    return motivo


# Scopo: Helper — il prezzo di una riga dal listino, OGGI: `prezzo_finale` del
#        resolver e la provenienza da scrivere accanto (building block
#        `prezzo_riga_commessa`, lo stesso del push). Lo usano riallinea e
#        sblocca.
#        ⛔ Passa dal `PricingService` (`resolve_prezzo`, quello che SOLLEVA):
#        qui un prezzo che il listino non sa dare e' un errore da mostrare,
#        non un'assenza da salvare. Fino al 2026-10-08 i due percorsi
#        chiamavano `ListiniRepository.test_resolver`, tolto il 2026-04-15:
#        un 500 su entrambi, che il test mockato fabbricava da se'.
def _prezzo_dal_listino(
    att: dict[str, Any],
    *,
    function_name: str,
) -> tuple[str, dict[str, Any]]:
    argomenti = argomenti_resolver(
        articolo_id=att.get("articolo_id"),
        uom_id=att.get("uom_id"),
        data_attivita=att.get("data_attivita"),
        competenza_mese=att.get("competenza_mese"),
        billing_account_id=att.get("billing_account_id"),
        utility_id=att.get("utility_id"),
        emittente_soggetto_ruolo_id=att.get("emittente_soggetto_ruolo_id"),
        meta=_V.optional_meta(att, "meta", function_name=function_name),
    )
    ErrorManager.require(
        argomenti is not None,
        code="E_COMMESSA_VALIDATION",
        message="Prezzo non ricalcolabile dal listino per questa riga.",
        detail=(
            "Alla riga o alla sua commessa manca un dato che il listino chiede "
            "(articolo, unita' di misura, data, cliente, utility o emittente)."
        ),
        context={"attivita_id": att.get("id")},
        function_name=function_name,
        log_to_db=True,
    )
    assert argomenti is not None
    risultato = PricingService().resolve_prezzo(**argomenti)
    return str(risultato["prezzo_finale"]), provenienza_da_resolver(risultato)


# --- N5: Riallineamento prezzo ---

# Scopo: Ricalcola il prezzo da listino per un'attivita` non ancora fatturata
#        e non bloccata manualmente. Se la versione listino e` cambiata rispetto
#        allo snapshot originale, richiede conferma esplicita.
def fn_riallinea_prezzo(
    commessa_id: int,
    attivita_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    function_name = "vendite.commesse_service.fn_riallinea_prezzo"

    att = _get_attivita_pricing_or_raise(commessa_id, attivita_id, function_name=function_name)
    _assert_commessa_modificabile(att, function_name=function_name)
    _assert_non_fatturata(att, function_name=function_name)
    _assert_prezzo_modificabile(att, function_name=function_name)

    ErrorManager.require(
        not att.get("prezzo_bloccato"),
        code="E_COMMESSA_VALIDATION",
        message="Riallineamento non ammesso su prezzo bloccato.",
        detail="Il prezzo e` bloccato (override manuale). Per riallinearlo prima sbloccarlo.",
        context={"prezzo_bloccato": att.get("prezzo_bloccato")},
        function_name=function_name,
        log_to_db=True,
    )

    # Risolve il prezzo attuale dal listino
    nuovo_prezzo, provenienza = _prezzo_dal_listino(att, function_name=function_name)

    # Guard: versione cambiata. ⚠️ Vive perche' la versione si SCRIVE: il push
    # la registra dal 2026-10-08, e il riallineamento qui sotto la aggiorna —
    # senza, il secondo riallineamento richiederebbe conferma per sempre.
    versione_originale = att.get("listino_versione_id")
    versione_attuale = provenienza["listino_versione_id"]
    versione_cambiata = versione_originale is not None and versione_attuale != versione_originale

    # ⛔ Dal BB: col test di verita' la stringa "false" valeva una conferma.
    #    Col codice del dominio e senza log a DB, come le altre validazioni qui.
    conferma = _V_TESTATA.optional_bool(
        payload, "conferma_versione_diversa", log_to_db=False,
    ) is True
    if versione_cambiata and not conferma:
        return {
            "versione_cambiata": True,
            "versione_originale_id": versione_originale,
            "versione_attuale_id": versione_attuale,
            "prezzo_attuale": str(att["prezzo_snapshot"]),
            "prezzo_ricalcolato": nuovo_prezzo,
            "richiede_conferma": True,
        }

    repo = CommesseRepository()

    meta = _V.optional_meta(att, "meta", function_name="commesse_service.fn_riallinea_prezzo") or {}
    riallineamenti = list(meta.get("riallineamenti", []))
    riallineamenti.append({
        "data": datetime.now(timezone.utc).isoformat(),
        "prezzo_precedente": str(att["prezzo_snapshot"]),
        "prezzo_nuovo": nuovo_prezzo,
        "listino_versione_id_precedente": versione_originale,
        "listino_versione_id_nuovo": versione_attuale,
        # La riga di listino del prezzo vecchio: dopo il riallineamento non la
        # cita piu' nessuno e torna modificabile (D-1 del brief-db-riga-listino-
        # propagata-dalla-commessa); la storia del prezzo resta leggibile qui.
        "listino_riga_id_precedente": att.get("listino_riga_id"),
        "listino_riga_id_nuovo": provenienza["listino_riga_id"],
    })
    meta["riallineamenti"] = riallineamenti

    with transaction.atomic():
        repo.lock_attivita_for_update(attivita_id)
        repo.update_attivita_prezzo(
            attivita_id=attivita_id,
            prezzo=nuovo_prezzo,
            prezzo_bloccato=False,
            meta=meta,
            provenienza=provenienza,
        )

    return {
        "attivita_id": attivita_id,
        "prezzo_precedente": str(att["prezzo_snapshot"]),
        "prezzo_nuovo": nuovo_prezzo,
        "versione_cambiata": versione_cambiata,
    }


# --- N7: Variazione prezzo eccezionale ---

# Scopo: Override manuale del prezzo su un'attivita` di commessa LIBERA o CONFERMATA.
#        Imposta prezzo_bloccato=TRUE. Motivo obbligatorio.
#        DEC-3 (brief processi-fatturazione §E): vietata su prezzo gia` bloccato —
#        il percorso e` sblocca (con motivo, ricalcola dal listino) e poi varia.
#        Evita il ri-override silenzioso di un blocco esistente.
def fn_variazione_prezzo_eccezionale(
    commessa_id: int,
    attivita_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    function_name = "vendite.commesse_service.fn_variazione_prezzo_eccezionale"

    att = _get_attivita_pricing_or_raise(commessa_id, attivita_id, function_name=function_name)
    _assert_commessa_modificabile(att, function_name=function_name)
    _assert_non_fatturata(att, function_name=function_name)
    _assert_prezzo_modificabile(att, function_name=function_name)

    ErrorManager.require(
        not att.get("prezzo_bloccato"),
        code="E_VENDITE_VARIAZIONE_PREZZO_NON_AMMESSA",
        message="Variazione non ammessa su prezzo bloccato.",
        detail="Il prezzo e` gia` bloccato: sbloccarlo prima di applicare una nuova variazione.",
        context={"prezzo_bloccato": att.get("prezzo_bloccato")},
        function_name=function_name,
        log_to_db=True,
    )

    nuovo_prezzo = _parse_prezzo(payload, function_name=function_name)
    motivo = _parse_motivo(payload, function_name=function_name)

    repo = CommesseRepository()

    meta = _V.optional_meta(att, "meta", function_name="commesse_service.fn_variazione_prezzo_eccezionale") or {}
    variazioni = list(meta.get("variazioni_eccezionali", []))
    variazioni.append({
        "data": datetime.now(timezone.utc).isoformat(),
        "prezzo_precedente": str(att["prezzo_snapshot"]),
        "prezzo_nuovo": str(nuovo_prezzo),
        "motivo": motivo,
        "stato_commessa": str(att["commessa_stato"]),
        "listino_versione_id_riferimento": att.get("listino_versione_id"),
        "listino_riga_id_riferimento": att.get("listino_riga_id"),
    })
    meta["variazioni_eccezionali"] = variazioni

    with transaction.atomic():
        repo.lock_attivita_for_update(attivita_id)
        repo.update_attivita_prezzo(
            attivita_id=attivita_id,
            prezzo=str(nuovo_prezzo),
            prezzo_bloccato=True,
            meta=meta,
            # Un prezzo scritto a mano dice di esserlo: origine MANUALE e
            # niente provenienza da listino (decisione di Tid 2026-10-08).
            # Versione e riga di riferimento restano nel diario qui sopra: la riga
            # di listino, non piu' citata, torna modificabile (D-1).
            provenienza=provenienza_manuale(),
        )

    return {
        "attivita_id": attivita_id,
        "prezzo_precedente": str(att["prezzo_snapshot"]),
        "prezzo_nuovo": str(nuovo_prezzo),
        "prezzo_bloccato": True,
        "motivo": motivo,
    }


# --- N7 sblocco: Sblocca prezzo_bloccato ---

# Scopo: Sblocca un prezzo bloccato manualmente e ricalcola dal resolver.
def fn_sblocca_prezzo(
    commessa_id: int,
    attivita_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    function_name = "vendite.commesse_service.fn_sblocca_prezzo"

    att = _get_attivita_pricing_or_raise(commessa_id, attivita_id, function_name=function_name)
    _assert_commessa_modificabile(att, function_name=function_name)
    _assert_non_fatturata(att, function_name=function_name)
    _assert_prezzo_modificabile(att, function_name=function_name)

    ErrorManager.require(
        att.get("prezzo_bloccato") is True,
        code="E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO",
        message="Sblocco non ammesso: il prezzo non e` bloccato.",
        detail="prezzo_bloccato e` FALSE. Nulla da sbloccare.",
        context={"prezzo_bloccato": att.get("prezzo_bloccato")},
        function_name=function_name,
        log_to_db=True,
    )

    motivo = _parse_motivo(payload, function_name=function_name)

    # Ricalcola dal resolver
    nuovo_prezzo, provenienza = _prezzo_dal_listino(att, function_name=function_name)
    repo = CommesseRepository()

    meta = _V.optional_meta(att, "meta", function_name="commesse_service.fn_sblocca_prezzo") or {}
    sblocchi = list(meta.get("sblocchi_prezzo", []))
    sblocchi.append({
        "data": datetime.now(timezone.utc).isoformat(),
        "prezzo_bloccato_precedente": str(att["prezzo_snapshot"]),
        "prezzo_ricalcolato": nuovo_prezzo,
        "motivo": motivo,
    })
    meta["sblocchi_prezzo"] = sblocchi

    with transaction.atomic():
        repo.lock_attivita_for_update(attivita_id)
        repo.update_attivita_prezzo(
            attivita_id=attivita_id,
            prezzo=nuovo_prezzo,
            prezzo_bloccato=False,
            meta=meta,
            provenienza=provenienza,
        )

    return {
        "attivita_id": attivita_id,
        "prezzo_bloccato_precedente": str(att["prezzo_snapshot"]),
        "prezzo_ricalcolato": nuovo_prezzo,
        "prezzo_bloccato": False,
        "motivo": motivo,
    }


# --- Annullamento riga MANUALE di commessa ---
# (brief-annullamento-righe-manuali-commessa §5)
#
# La riga non si cancella: passa a `stato_emissione='ANNULLATA'`, valore che
# TUTTE le porte verso la fattura e verso il cockpit gia' filtrano
# (fn_emit_attivita_fatturabili_da_commessa, fn_list_commesse_emittibili,
# fn_list_emittibili_lane, vw_dash_competenza_attivita/_gruppi,
# vw_dash_fatturazione_commesse). E' il libro giornale: annullare senza
# cancellare, con il motivo tracciato nell'evento di log.

_STATO_EMISSIONE_ANNULLATA = "ANNULLATA"
_STATO_EMISSIONE_NON_EMESSA = "NON_EMESSA"

# Marker P0001 → codice applicativo per gli errori della madre DB (564-567).
# I guard applicativi sotto arrivano prima nel caso normale, ma la madre resta
# l'ultima parola: sotto `FOR UPDATE` intercetta le corse (due annullamenti
# simultanei, un'emissione concorrente) che la rilettura applicativa non vede.
_ANNULLA_DB_ERROR_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("E_RIGA_COMMESSA_GIA_ANNULLATA", ("E_RIGA_COMMESSA_GIA_ANNULLATA",)),
    ("E_RIGA_COMMESSA_NON_MANUALE", ("E_RIGA_COMMESSA_NON_MANUALE",)),
    # Guard di NATURA della madre (changeSet 20260820-10): la riga e' sourceless
    # ma e' una RETTIFICA, quindi `_assert_annullabile` qui sopra la lascia
    # passare — sourceless per lui vuol dire manuale — e a rifiutarla e' il DB.
    # ⚠️ Questa whitelist e' CHIUSA: un codice che non c'e' non fallisce, ricade
    # su `E_COMMESSA_VALIDATION` (classe DATO_ERRATO, 400). Senza questa riga
    # l'operatore vedrebbe un errore di VALIDAZIONE al posto di un conflitto di
    # stato (409) — messaggio giusto, reazione sbagliata, e in silenzio.
    ("E_RIGA_COMMESSA_MOVIMENTO_NON_ANNULLABILE", ("E_RIGA_COMMESSA_MOVIMENTO_NON_ANNULLABILE",)),
    ("E_RIGA_COMMESSA_GIA_EMESSA", ("E_RIGA_COMMESSA_GIA_EMESSA",)),
    ("E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO", ("E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO",)),
)


# Scopo: Helper — i tre guard di ammissibilita' dell'annullamento, nello STESSO
#        ordine della madre DB (§4b del brief). L'ordine non e' indifferente:
#        «non manuale» viene PRIMA di «gia' emessa» perche' e' l'IDENTITA' della
#        riga, non una sua condizione — dire «gia' emessa» a una riga da push
#        suggerisce che, se non lo fosse, si potrebbe annullare (falso: il
#        rimedio e' a monte, sul documento). «Gia' annullata» resta in testa
#        perche' una riga ANNULLATA e' per costruzione manuale e non toglie il
#        posto a una diagnosi migliore.
def _assert_annullabile(
    att: dict[str, Any],
    *,
    function_name: str,
) -> None:
    stato_emissione = str(att.get("stato_emissione") or "")
    ErrorManager.require(
        stato_emissione != _STATO_EMISSIONE_ANNULLATA,
        code="E_RIGA_COMMESSA_GIA_ANNULLATA",
        message="La riga e` gia` annullata.",
        detail="L`operazione era gia` stata fatta: nessun secondo annullamento.",
        context={"attivita_id": att.get("id"), "stato_emissione": stato_emissione},
        function_name=function_name,
        log_to_db=False,
    )
    # Sourceless = non nata da un documento = manuale (fn_build_gruppo_
    # fatturabile_key definisce cosi' il gruppo `MAN:<commessa_id>`). Il CHECK
    # chk_commesse_attivita_sorgente_pair garantisce la coerenza della coppia.
    ErrorManager.require(
        att.get("sorgente_tipo_id") is None,
        code="E_RIGA_COMMESSA_NON_MANUALE",
        message="La riga nasce da un documento: il rimedio e` a monte.",
        detail=(
            "Solo le righe manuali (sourceless) si annullano qui. Questa riga ha "
            f"sorgente_tipo_id={att.get('sorgente_tipo_id')}: intervenire sul "
            "documento sorgente."
        ),
        context={
            "attivita_id": att.get("id"),
            "sorgente_tipo_id": att.get("sorgente_tipo_id"),
        },
        function_name=function_name,
        log_to_db=False,
    )
    # `<> NON_EMESSA` e non `= EMESSA`: se domani il CHECK ammettesse un quarto
    # stato, il default resta il rifiuto (fail-closed, come la madre).
    ErrorManager.require(
        stato_emissione == _STATO_EMISSIONE_NON_EMESSA,
        code="E_RIGA_COMMESSA_GIA_EMESSA",
        message="Riga gia` entrata nella catena di fatturazione.",
        detail=(
            f"stato_emissione={stato_emissione}: la riga ha gia` generato "
            "un`attivita` fatturabile. Annullarla qui lascerebbe un`AF orfana; "
            "la correzione di un documento gia` emesso e` la nota di credito."
        ),
        context={"attivita_id": att.get("id"), "stato_emissione": stato_emissione},
        function_name=function_name,
        log_to_db=True,
    )




# Scopo: Il REGISTRO di una commessa — gli eventi scritti dal database sulle sue
#        righe. Risponde a «perche' questa riga e' cosi'».
# Perimetro: sola lettura; lo scope e' DB-side (il repository legge il log
#        passando dal JOIN su `commesse_attivita`, che ha la RLS).
# Risultato: dict con commessa_id, count, rows.
#
# ⭐ ESISTE PERCHE' IL REGISTRO SI SCRIVEVA E NON SI LEGGEVA. Fino al 2026-08-28
#    `vendite.commesse_attivita_log` non aveva un solo `SELECT` in tutto il
#    backend: sei tipi di evento — oneri aggiunti, righe annullate a mano,
#    ritirate alla chiusura del documento, riportate da emettere, accrediti —
#    scritti fedelmente e **irraggiungibili** da qualunque schermata. La guida
#    prometteva il contrario, e la promessa e' rimasta falsa per due giorni:
#    «il lavoro e' sparito» restava indistinguibile da un difetto.
def fn_commessa_registro(
    *,
    commessa_id: int,
    commessa_attivita_id: int | None = None,
    limit: int = DEFAULT_LIMIT_EVENTI,
    offset: int = 0,
) -> dict[str, Any]:
    # ⛔ La finestra (`limit` fra 1 e il tetto, `offset` non negativo) la
    #    valida la view con `pagina_da_query`, che dal 2026-10-21 risponde 400
    #    sul fuori limite (Tid): qui era una seconda copia, irraggiungibile.
    rows, total = CommesseRepository().list_registro_attivita(
        commessa_id,
        commessa_attivita_id=commessa_attivita_id,
        limit=int(limit),
        offset=int(offset),
    )
    return {"commessa_id": commessa_id, "count": total, "rows": rows}


# Scopo: Annulla una riga MANUALE di commessa caricata per errore (causale
#        sbagliata, importo sbagliato, doppio click): la riga resta, con importo
#        e storia, ma esce dal giro — `stato_emissione='ANNULLATA'` e' gia'
#        filtrato da tutte le porte verso fattura e cockpit.
#        Perimetro: righe manuali (sourceless) NON ancora emesse, su commessa
#        ancora modificabile. Delegato alla madre DB `fn_annulla_commessa_
#        attivita` (UPDATE + evento di log in una SELECT atomica); qui vivono lo
#        scoping riga<->commessa, il guard di stato commessa e i guard di
#        ammissibilita' anticipati, per rispondere 4xx parlanti al posto di una
#        traduzione di RAISE. Risultato: {commessa_id, attivita_id, stato_emissione, motivo}.
#        Il presidio di autorizzazione (`carica_voce_manuale`) e' sulla view.
def annulla_attivita_manuale(
    commessa_id: int,
    attivita_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    function_name = "vendite.commesse_service.annulla_attivita_manuale"

    # Scoping riga<->commessa: la `WHERE` di get_attivita_pricing filtra su
    # ENTRAMBI gli id. Senza, il `commessa_id` dell'URL sarebbe decorativo e si
    # annullerebbe la riga di un altro cliente indovinando un intero.
    # La RLS non copre il buco — e NON perche' sia dormiente: la policy
    # `rls_commesse_attivita_ef_whitelist` si applica eccome (l'app `zeroerp_app`
    # non e' owner della tabella e non ha BYPASSRLS; `NO FORCE` esenta il solo
    # owner). Risponde pero' a una domanda DIVERSA — «l'operatore e' nella
    # whitelist dell'emittente di questa commessa?» — non «questa riga e' di
    # QUESTA commessa?»: un operatore in scope sull'emittente puo' ancora
    # colpire la riga di un'altra commessa dello stesso emittente.
    att = _get_attivita_pricing_or_raise(commessa_id, attivita_id, function_name=function_name)
    # Annullare una riga *e'* modificare la commessa: stesso guard data-driven
    # (`stati_commessa.modificabile`) delle tre azioni prezzo sorelle. Resta nel
    # BE e non scende nella madre: il gemello `fn_aggiungi_onere_commessa` non
    # fa quel lookup e qui non si apre una dipendenza che la porta non ha.
    _assert_commessa_modificabile(att, function_name=function_name)
    _assert_annullabile(att, function_name=function_name)

    motivo = _parse_motivo(
        payload,
        function_name=function_name,
        code="E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO",
    )

    repo = CommesseRepository()
    try:
        repo.annulla_attivita(attivita_id=attivita_id, motivo=motivo)
    except DatabaseError as exc:
        # I guard della madre sono errori d'uso (o corse perse): vanno
        # all'operatore col loro codice, non come E_DATABASE generico.
        ErrorManager.raise_from_database_error(
            exc,
            known_markers=_ANNULLA_DB_ERROR_MARKERS,
            fallback_code="E_COMMESSA_VALIDATION",
            message="Riga non annullata: operazione non ammessa.",
            context={"commessa_id": commessa_id, "attivita_id": attivita_id},
            function_name=function_name,
        )

    return {
        "commessa_id": commessa_id,
        "attivita_id": attivita_id,
        "stato_emissione": _STATO_EMISSIONE_ANNULLATA,
        "motivo": motivo,
    }
