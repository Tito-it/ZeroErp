# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Costruttore di `DatabaseError` finti FEDELI alla forma vera, per i test
#        che non possono usare un DB reale (vincolo CI di AGENTS.md).
# Note: Modulo di supporto ai test, non un modulo di test: il nome non comincia
#       per `test` apposta, cosi' il runner non lo raccoglie.
# ------------------------------------------------------------

"""Perche' esiste.

Un `DatabaseError("testo")` nudo non e' quello che Django consegna: manca la
catena `__cause__` verso l'errore psycopg, e con essa `sqlstate` e i campi
`diag`. Un test costruito cosi' esercita per forza il **ripiego testuale**, non
il percorso vero — che dal 2026-08-05 e' il campo strutturato `CONSTRAINT` su
`SQLSTATE = 'P0001'` (brief-db-codice-errore-strutturato).

Non e' un dettaglio di stile: un finto che sbaglia forma fa passare il test per
una ragione diversa da quella per cui passa il sistema, ed e' la famiglia di
trappole che quel cantiere insegue da giorni.

Estratto il 2026-08-05 alla 5a copia (regola del 2): `test_db_error_fields` piu'
i quattro moduli di test di `pratiche`.
"""

from __future__ import annotations

from typing import Any

from django.db import DatabaseError, IntegrityError

# SQLSTATE di `RAISE EXCEPTION` senza ERRCODE esplicito — l'unico su cui il
# backend si fida del campo `constraint_name` (vedi `db_error_fields`).
SQLSTATE_RAISE_EXCEPTION = "P0001"


class FakeDiag:
    """I campi `diag` di psycopg3 che il backend legge davvero.

    ⭐ I canali strutturati sono TRE, e vanno tutti riprodotti: `constraint_name`
    porta il codice (05/08), `column_name` il campo da correggere (08/08),
    `datatype_name` il bersaglio (23/08). ⚠️ Un finto che ne dimentica uno fa
    passare il test **per una ragione diversa** da quella per cui passa il
    sistema — che e' esattamente la famiglia di trappole per cui questo modulo
    esiste.
    """

    def __init__(self, **campi: Any) -> None:
        self.message_primary = campi.get("message_primary")
        self.message_detail = campi.get("message_detail")
        self.message_hint = campi.get("message_hint")
        self.constraint_name = campi.get("constraint_name")
        self.column_name = campi.get("column_name")
        self.datatype_name = campi.get("datatype_name")


class FakeCausaPg(Exception):
    """Sta al posto dell'errore psycopg: `sqlstate` + `diag`, come il vero."""

    def __init__(self, sqlstate: str, **diag: Any) -> None:
        super().__init__(diag.get("message_primary", ""))
        self.sqlstate = sqlstate
        self.diag = FakeDiag(**diag)


# Scopo: Costruisce un DatabaseError con la stessa catena `__cause__` che Django
#        produce avvolgendo un errore psycopg.
#        `codice` valorizza il campo strutturato (`CONSTRAINT`); passare None
#        simula i `RAISE EXCEPTION` diretti, che il campo non lo mettono.
def make_db_error(
    testo: str,
    *,
    codice: str | None = None,
    sqlstate: str = SQLSTATE_RAISE_EXCEPTION,
    detail: str | None = None,
    hint: str | None = None,
    campo: str | None = None,
    bersaglio: str | None = None,
) -> DatabaseError:
    exc = DatabaseError(testo)
    exc.__cause__ = FakeCausaPg(
        sqlstate,
        message_primary=testo,
        message_detail=detail,
        message_hint=hint,
        constraint_name=codice,
        column_name=campo,
        # ⚠️ Forma del canale: `TIPO:id[,TIPO:id]`, testo — non jsonb. Il ricco
        # resta nel `context` e finisce in `dbops.error_log`; qui viaggia la
        # versione minima che serve a disegnare un gesto.
        datatype_name=bersaglio,
    )
    return exc


# SQLSTATE delle violazioni d'integrita' che i test simulano.
SQLSTATE_UNICITA = "23505"
SQLSTATE_FK = "23503"
SQLSTATE_CHECK = "23514"
SQLSTATE_NOT_NULL = "23502"


# Scopo: Un `IntegrityError` con la catena `__cause__` del vero: SQLSTATE,
#        `constraint_name` e, per il NOT NULL, `column_name`. Il testo nomina il
#        vincolo come lo scrive PostgreSQL.
# ⚠️ Un `IntegrityError("unique")` nudo non ha SQLSTATE, e PostgreSQL non lo
#    solleva mai cosi': dal 2026-10-07 la traduzione dei service anagrafiche
#    decide sullo SQLSTATE (`_validators.rifiuto_integrita`), e un finto senza
#    SQLSTATE proverebbe il ripiego, non il percorso vero.
def make_integrity_error(
    sqlstate: str,
    *,
    vincolo: str | None = None,
    colonna: str | None = None,
) -> IntegrityError:
    testo = f'violates constraint "{vincolo}"' if vincolo else "integrity violation"
    exc = IntegrityError(testo)
    exc.__cause__ = FakeCausaPg(
        sqlstate,
        message_primary=testo,
        constraint_name=vincolo,
        column_name=colonna,
    )
    return exc
