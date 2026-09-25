# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
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
#         (brief-be-letture-in-transazione-sola-lettura §2.3) — non ancora
#         fatto: quel brief aspetta anche il codice `E_SCRITTURA_IN_LETTURA`.
#       ⛔ Per TRANSAZIONE, mai per sessione: con `CONN_MAX_AGE` le connessioni
#       si riusano, e un `SET SESSION CHARACTERISTICS` passerebbe alla
#       richiesta dopo — magari una POST che deve scrivere.
#       ⚠️ Le GUC non sono scritture: `set_config` funziona anche qui dentro.
#       E il `tx_id` arriva via dblink, cioe' da un'altra connessione.
# ------------------------------------------------------------

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from django.db import DEFAULT_DB_ALIAS, connections, transaction


# Scopo: Apre una transazione, la dichiara di sola lettura come PRIMA
#        istruzione, esegue il blocco e la chiude. All'uscita normale fa
#        COMMIT (non c'e' niente da confermare), su eccezione ROLLBACK.
# ⛔ Rifiuta di partire dentro una transazione gia' aperta: PostgreSQL accetta
#    `SET TRANSACTION READ ONLY` solo prima di qualunque query della
#    transazione, e un blocco atomico annidato e' un savepoint, cioe' una
#    query gia' fatta. Ripiegare in silenzio su «niente sola lettura»
#    vorrebbe dire promettere una garanzia e non darla: e' un errore di chi
#    chiama, e lo si dice.
# Parametri: using — alias della connessione Django (default: `default`).
@contextmanager
def transazione_sola_lettura(using: str = DEFAULT_DB_ALIAS) -> Iterator[None]:
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
        yield
