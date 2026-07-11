# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Helper condiviso per il filtro applicativo "scope emittente" delle
#        query lista (defense-in-depth sopra la RLS). Estrazione regola-del-2:
#        il pattern SQL inline `(fn(%s) IS NULL OR col = ANY(fn(%s)))` era
#        replicato in 5 repository (ordini/ddt/preventivi/contratti pk_ids +
#        vendite_repository sr_ids) e valutava la fn plpgsql STABLE ~2 volte
#        per riga sia nella count query sia nella data query. Qui l'array
#        viene risolto UNA SOLA VOLTA in Python (pattern sanzionato in api.md
#        §"Scope emittente", variante 2) e bindato come parametro.
# ------------------------------------------------------------

from __future__ import annotations

import re
from typing import Any

from django.db import connection

# Convenzione colonna -> funzione DB (guida soggetti-e-ruoli §5b, memoria
# feedback_emittente_pk_vs_soggetto_ruolo):
#  - "pk": colonne emittente_fiscale_id (PK reale emittenti_fiscali.id)
#  - "sr": colonne <ruolo>_soggetto_ruolo_id (soggetto_ruolo dell'emittente)
_SCOPE_FN_BY_CONVENTION = {
    "pk": "script.fn_get_emittenti_scope_pk_ids",
    "sr": "script.fn_get_emittenti_scope_sr_ids",
}

# Guard difensivo sull'identificatore colonna (arriva sempre da letterali dei
# call-site, mai da input utente: il check congela l'invariante).
_IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)?$")


# Scopo: Risolve UNA volta l'array degli emittenti autorizzati per l'utente
#        (bigint[] della fn DB). Semantica invariata rispetto alla fn SQL:
#        None = nessuna restrizione (super admin / bypass), [] = nessun
#        accesso (fail-closed), lista = whitelist.
def fetch_emittenti_scope_ids(
    auth_user_id: int, *, convention: str = "pk",
) -> list[int] | None:
    fn = _SCOPE_FN_BY_CONVENTION[convention]
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {fn}(%s)", [auth_user_id])  # noqa: S608 — fn da whitelist
        row = cursor.fetchone()
    if row and row[0] is not None:
        return list(row[0])
    return None


# Scopo: Appende a conditions/params la condizione di scope emittente per la
#        colonna indicata, con l'array risolto una volta in Python. No-op se
#        auth_user_id e' None (superuser a livello API) o se la fn ritorna
#        NULL (nessuna restrizione). Un array vuoto viene bindato comunque:
#        `col = ANY('{}')` non matcha nulla -> fail-closed preservato.
def add_emittente_scope_condition(
    conditions: list[str],
    params: list[Any],
    *,
    auth_user_id: int | None,
    column: str,
    convention: str = "pk",
) -> None:
    if auth_user_id is None:
        return
    if not _IDENT_RE.match(column):
        raise ValueError(f"colonna scope non valida: {column!r}")
    scope_ids = fetch_emittenti_scope_ids(auth_user_id, convention=convention)
    if scope_ids is None:
        return
    conditions.append(f"{column} = ANY(%s)")  # noqa: S608 — colonna da whitelist regex
    params.append(scope_ids)
