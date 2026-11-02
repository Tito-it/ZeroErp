# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Building block — una transazione di SOLA LETTURA garantita dal DB.
#        Dentro il blocco, una scrittura fallisce con `25006`
#        (`read_only_sql_transaction`), chiunque la tenti: anche una funzione
#        `SECURITY DEFINER`, perche' e' una regola della TRANSAZIONE, non del
#        ruolo.
# Note: ⭐ Nasce per due consumatori, e la regola del 2 vuole che sia UNO
#       (ok Tid 2026-09-25):
#       - i tool di lettura dell'assistente AI e le anteprime dei tool di
#         scrittura (brief-db-area-funzionale-assistente-ai §5.3 punto 3);
#       - il montaggio su ogni `GET`/`HEAD` delle API
#         (brief-be-letture-in-transazione-sola-lettura §2.3):
#         `SolaLetturaMiddleware`.
#       ⭐ Il `25006` si traduce QUI, alla sorgente, in `E_SCRITTURA_IN_LETTURA`
#       (TECNICO), con chi stava leggendo nel log (§5 del brief). Un
#       `ServiceError` non e' un `DatabaseError`: nessuno dei punti che
#       traducono gli errori DB (api.md, «I cinque punti di traduzione») lo
#       puo' riscrivere col suo ripiego.
#       ⛔ Per TRANSAZIONE, mai per sessione: con `CONN_MAX_AGE` le connessioni
#       si riusano, e un `SET SESSION CHARACTERISTICS` passerebbe alla
#       richiesta dopo — magari una POST che deve scrivere.
#       ⚠️ Le GUC non sono scritture: `set_config` funziona anche qui dentro.
#       E il `tx_id` arriva via dblink, cioe' da un'altra connessione.
# ------------------------------------------------------------

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections, transaction

from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.services.service_errors import ServiceError

logger = logging.getLogger(__name__)

E_SCRITTURA_IN_LETTURA = "E_SCRITTURA_IN_LETTURA"
_SQLSTATE_SOLA_LETTURA = "25006"  # read_only_sql_transaction


# Scopo: L'`execute_wrapper` del blocco: lascia passare tutto, e una scrittura
#        fermata da PostgreSQL (`25006`) la trasforma in `E_SCRITTURA_IN_LETTURA`.
#        Il nome di chi legge (una view, un tool) va nel LOG, non nel messaggio:
#        serve a chi sviluppa, e il catalogo tiene la frase chiusa.
# ⛔ La transazione e' gia' interrotta da PostgreSQL: la si marca da annullare,
#    altrimenti un chiamante che converte l'errore in risposta farebbe uscire
#    il blocco «normalmente», cioe' con un COMMIT.
def _ferma_la_scrittura(connessione: Any, chi: str) -> Callable[..., Any]:
    def wrapper(execute: Callable[..., Any], sql: str, params: Any, many: bool, context: Any) -> Any:
        try:
            return execute(sql, params, many, context)
        except DatabaseError as exc:
            if getattr(exc.__cause__, "sqlstate", None) != _SQLSTATE_SOLA_LETTURA:
                raise
            logger.error(
                "sola_lettura.scrittura_in_lettura chi=%s sql=%.200s", chi, sql,
            )
            connessione.needs_rollback = True
            raise ServiceError(
                code=E_SCRITTURA_IN_LETTURA,
                message=ErrorPolicyRegistry.resolve(E_SCRITTURA_IN_LETTURA).user_message,
                detail=f"Scrittura tentata in sola lettura da {chi}.",
                context={"chi": chi},
            ) from exc
    return wrapper


# Scopo: Apre una transazione, la dichiara di sola lettura come PRIMA
#        istruzione, esegue il blocco e la chiude. All'uscita normale fa
#        COMMIT, su eccezione ROLLBACK.
#        ⛔ COMMIT e non ROLLBACK anche se non c'e' niente da confermare: le GUC
#        impostate dentro il blocco (`set_config(..., false)`, l'identita' e
#        l'emittente della richiesta) con un ROLLBACK tornerebbero indietro, e
#        `RequestLogMiddleware` le legge DOPO la view.
# ⛔ Rifiuta di partire dentro una transazione gia' aperta: PostgreSQL accetta
#    `SET TRANSACTION READ ONLY` solo prima di qualunque query della
#    transazione, e un blocco atomico annidato e' un savepoint, cioe' una
#    query gia' fatta. Ripiegare in silenzio su «niente sola lettura»
#    vorrebbe dire promettere una garanzia e non darla: e' un errore di chi
#    chiama, e lo si dice.
# Parametri: using — alias della connessione Django (default: `default`).
#            chi — chi sta leggendo (view, tool): finisce nel log se scrive.
@contextmanager
def transazione_sola_lettura(
    using: str = DEFAULT_DB_ALIAS, *, chi: str = "(non dichiarato)",
) -> Iterator[None]:
    connessione = connections[using]
    if connessione.in_atomic_block:
        raise RuntimeError(
            "transazione_sola_lettura: c'e' gia' una transazione aperta sulla "
            f"connessione {using!r}, e la sola lettura si imposta solo come "
            "prima istruzione di una transazione nuova."
        )
    with transaction.atomic(using=using):
        with connessione.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
        with connessione.execute_wrapper(_ferma_la_scrittura(connessione, chi)):
            yield
