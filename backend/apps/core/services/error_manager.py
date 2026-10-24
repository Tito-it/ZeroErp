# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gestione errori e validazioni centralizzate.
# ------------------------------------------------------------


from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
import json
from typing import Any, NoReturn

from django.conf import settings
from django.db import connection

from apps.core.services.db_error_fields import Bersaglio, diagnostica_db
from apps.core.services.service_errors import ServiceError

# Helper unico errori: validazione, raise strutturato e logging opzionale su DB.

# Le righe di diario in attesa della fine della transazione dell'operazione
# (`ErrorManager.diario_dopo_la_transazione`). None = nessuna attesa: si scrive
# subito, come sempre. Una lista per richiesta: il ContextVar non si vede fra
# thread ne' fra richieste.
_diario_in_attesa: ContextVar[list[tuple[str, str, str, str]] | None] = ContextVar(
    "diario_in_attesa", default=None,
)


class ErrorManager:
    """Utility centralizzata per evitare logica errori duplicata nei servizi."""

    # Scopo: Costruisce e solleva un ServiceError uniforme, con logging DB opzionale.
    @staticmethod
    def raise_error(
        *,
        code: str,
        message: str,
        detail: str | None = None,
        hint: str | None = None,
        retryable: bool = False,
        context: dict[str, Any] | None = None,
        fields: tuple[str, ...] | None = None,
        targets: tuple[Bersaglio, ...] | None = None,
        area: str = "backend",
        function_name: str = "django_service",
        log_to_db: bool = False,
        cause: Exception | None = None,
    ) -> NoReturn:
        # ⭐ `NoReturn` (dal 2026-09-28): solleva SEMPRE, su ogni ramo. Dopo una
        #    chiamata non serve una riga «irraggiungibile»: il type checker e
        #    l'editor lo sanno, e `test_error_manager` lo prova.
        if log_to_db:
            ErrorManager.log_error_only(
                code=code,
                context=context or {},
                area=area,
                function_name=function_name,
            )

        service_error = ServiceError(
            code=code,
            message=message,
            detail=detail,
            hint=hint,
            retryable=retryable,
            context=context,
            # I due canali strutturati del database. Chi traduce un errore DB li
            # legge da `diagnostica_db` e li passa qui: senza, si fermano al log.
            fields=fields,
            targets=targets,
        )
        if cause is not None:
            raise service_error from cause
        raise service_error

    # Scopo: Valida una condizione e in caso negativo genera ServiceError coerente con policy core.
    @staticmethod
    def require(
        # `object` e non `bool`: la condizione si valuta per VERITA' (`if
        # condition:`), e i chiamanti passano anche valori, non solo booleani.
        condition: object,
        *,
        code: str,
        message: str,
        detail: str | None = None,
        hint: str | None = None,
        context: dict[str, Any] | None = None,
        area: str = "backend",
        function_name: str = "django_service",
        log_to_db: bool = False,
    ) -> None:
        if condition:
            return
        ErrorManager.raise_error(
            code=code,
            message=message,
            detail=detail,
            hint=hint,
            context=context,
            area=area,
            function_name=function_name,
            log_to_db=log_to_db,
        )

    # Scopo: Traduce una DatabaseError (tipicamente RAISE P0001 dal DB) in
    #        ServiceError preservando il codice originale.
    #        ⭐ CODICE DEL CATALOGO (campo strutturato, cioe' sollevato da
    #        `script.fn_log_and_raise_error`): vince SEMPRE, anche se il
    #        chiamante non lo ha in `known_markers`, e con la SUA frase — quella
    #        del catalogo, coi valori (Tid, 2026-09-23, brief-db-guard-date-validita
    #        §13). Fino ad allora un codice non in lista cadeva sul
    #        `fallback_code`, e uno in lista usciva col `message` del chiamante:
    #        un guard comune come quello delle date (25 tabelle) diventava
    #        «Violazione vincolo contrattuale.» o un codice generico a seconda
    #        di chi lo attraversava. `message`/`fallback_message` del chiamante
    #        restano il ripiego solo se il DB non ha mandato una frase.
    #        RIPIEGO SUL TESTO (i `RAISE` diretti, senza campo strutturato): il
    #        messaggio dell'eccezione viene confrontato con `known_markers`: la PRIMA
    #        voce i cui marker compaiono TUTTI nel messaggio vince; nessun
    #        match -> `fallback_code`. I marker restano dati di dominio del
    #        chiamante (ogni service dichiara i propri); qui vive solo il
    #        meccanismo di match+raise, prima duplicato in pricing_service,
    #        ui_service e dashboard_service.
    #        Nota fragilita' (review B4/F1 2026-04-15): il match su substring
    #        regge finche' il codice/template sopravvive nel MESSAGE_TEXT del
    #        RAISE; la soluzione strutturale (codice in DETAIL/HINT lato DB)
    #        e' rimandata — proteggersi con test di regressione sui marker.
    #
    #        Varianti per il caso NESSUN match:
    #        - `fallback_code=None` -> ri-solleva l'eccezione originale
    #          (la policy generica la mappa il middleware, es. E_DATABASE);
    #        - `fallback_message` -> messaggio utente alternativo quando si
    #          usa il fallback (default: stesso `message` del caso match).
    @staticmethod
    def raise_from_database_error(
        exc: Exception,
        *,
        known_markers: tuple[tuple[str, tuple[str, ...]], ...],
        fallback_code: str | None,
        message: str,
        fallback_message: str | None = None,
        context: dict[str, Any] | None = None,
        function_name: str = "django_service",
        log_to_db: bool = True,
    ) -> NoReturn:
        msg = str(exc)
        # ⭐ UNA lettura sola della diagnostica (BB `diagnostica_db`, 2026-08-24).
        #    Prima di allora questo metodo leggeva il solo codice e buttava via
        #    il resto: `hint`, il campo da correggere e il bersaglio non
        #    arrivavano mai all'envelope da questa strada.
        diag = diagnostica_db(exc, text=msg)
        matched_code: str | None = None
        # ⭐ Il codice del catalogo vince sempre, con la sua frase (vedi Scopo).
        # ⚠️ Prima era accettato solo se in `known_markers`, per non dare a un
        #    errore inatteso il `message` del caso riconosciuto: con la frase
        #    del DB quel rischio non c'e' piu', e la lista ne scartava di veri.
        structured = diag.codice_strutturato
        frase_del_db = diag.messaggio if structured is not None else None
        if structured is not None:
            matched_code = structured
        # ⛔ NON DUPLICARE IL DIARIO — decisione DB+BE del 2026-08-19.
        # Il campo strutturato e' valorizzato SOLO da `script.fn_log_and_raise_error`,
        # che prima di sollevare ha gia' scritto la sua riga in `dbops.error_log`
        # (via `fn_log_error_only`, dblink: sopravvive al rollback del RAISE).
        # Ri-loggare qui significa DUE righe per UN fallimento, con la seconda
        # marcata `area='backend'` come se l'errore fosse nato nel backend.
        # ⚠️ E il ripiego non e' simmetrico, percio' non si spegne tutto: i ~135
        # `RAISE EXCEPTION` diretti (46 funzioni, vedi `db_error_fields`) e gli
        # errori PG veri — violazioni di vincolo, timeout — nel diario NON ci
        # sono. Se il backend smettesse di scriverli si perderebbero del tutto:
        # li' la riga la scriviamo noi, e non e' un doppione.
        gia_scritto_dal_database = diag.gia_scritto_dal_database
        for code_candidate, markers in known_markers:
            if matched_code is not None:
                break
            if all(marker in msg for marker in markers):
                matched_code = code_candidate
                break
        if matched_code is None and fallback_code is None:
            raise exc
        codice = matched_code or fallback_code
        # Garantito dal guard qui sopra (un codice del catalogo non e' mai vuoto).
        assert codice is not None
        ErrorManager.raise_error(
            code=codice,
            message=frase_del_db or (
                message
                if matched_code is not None or fallback_message is None
                else fallback_message
            ),
            detail=msg,
            # ⚠️ `hint` e' la SOLUZIONE che il team DB scrive a catalogo per ogni
            #    codice, `message` la frase dell'errore (del catalogo, o del
            #    chiamante sul ripiego): sono due cose diverse e non si
            #    scavalcano. Fino al 2026-08-24 da questa strada la soluzione
            #    non usciva affatto.
            hint=diag.hint,
            context=context,
            fields=diag.fields,
            targets=diag.bersagli or None,
            cause=exc,
            log_to_db=log_to_db and not gia_scritto_dal_database,
            function_name=function_name,
        )

    # Scopo: Registra un errore tecnico su DB in best-effort senza interrompere il flusso chiamante.
    #
    #        ⚠️ RECINTO FRA TEST E PRODUZIONE. `settings.ERROR_LOG_DB_ENABLED` e'
    #        spento dal runner dei test (`zeroerp_backend/test_runner.py`): la
    #        suite gira contro il database vero e un test che esercita un service
    #        con `log_to_db=True` sostituisce il repository con un mock, non
    #        questo logger — la riga finirebbe nel diario indistinguibile da un
    #        errore vero. E' costato una diagnosi sbagliata al team DB il
    #        2026-08-19 (brief-be-pricing-codice-errore-fantasma.md §10).
    #        Il controllo sta QUI e non nei chiamanti: e' l'unico punto Python che
    #        chiama `script.fn_log_error_only`, quindi il recinto e' completo per
    #        costruzione — un service nuovo lo eredita senza saperlo.
    @staticmethod
    def log_error_only(
        *,
        code: str,
        context: dict[str, Any] | None = None,
        area: str = "backend",
        function_name: str = "django_service",
    ) -> None:
        if not getattr(settings, "ERROR_LOG_DB_ENABLED", True):
            return
        ErrorManager._registra_diario((area, function_name, code, json.dumps(context or {})))

    # Scopo: Una riga di diario va in attesa se un blocco
    #        `diario_dopo_la_transazione` e' aperto, altrimenti si scrive subito.
    @staticmethod
    def _registra_diario(riga: tuple[str, str, str, str]) -> None:
        in_attesa = _diario_in_attesa.get()
        if in_attesa is not None:
            in_attesa.append(riga)
            return
        ErrorManager._scrivi_diario(riga)

    # Scopo: Rimanda le righe di diario a DOPO la transazione dell'operazione,
    #        commit o rollback che sia: si scrivono all'uscita dal blocco.
    # ⛔ Perche' esiste (BE-2 di brief-be-verifica-documentazione-api,
    #    2026-10-24). `fn_log_error_only` scrive via dblink e sopravvive al
    #    rollback, ma la SELECT che la chiama gira sulla connessione di Django:
    #    dentro un `transaction.atomic()`, dopo un errore DB catturato senza
    #    savepoint, la transazione e' abortita, la SELECT fallisce e il
    #    best-effort qui sopra la inghiotte. La riga spariva senza un errore.
    # ⚠️ Si usa FUORI dall'`atomic`, che deve chiudersi prima:
    #    `with ErrorManager.diario_dopo_la_transazione(), transaction.atomic():`.
    #    Lo apre `handle_post_json` per le operazioni ATOMICA.
    # ⚠️ Annidato, il blocco interno consegna le sue righe a quello esterno:
    #    scriverle alla sua uscita vorrebbe dire scriverle dentro la transazione
    #    che l'esterno sta ancora aspettando.
    @staticmethod
    @contextmanager
    def diario_dopo_la_transazione() -> Iterator[None]:
        righe: list[tuple[str, str, str, str]] = []
        token = _diario_in_attesa.set(righe)
        try:
            yield
        finally:
            _diario_in_attesa.reset(token)
            for riga in righe:
                ErrorManager._registra_diario(riga)

    # Scopo: La scrittura vera di una riga di diario. Best-effort: non deve
    #        rompere il flusso applicativo.
    @staticmethod
    def _scrivi_diario(riga: tuple[str, str, str, str]) -> None:
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT script.fn_log_error_only(
                        %s, %s, %s, %s::jsonb, NULL::uuid, VARIADIC ARRAY[]::text[]
                    )
                    """,
                    list(riga),
                )
        except Exception:
            return
