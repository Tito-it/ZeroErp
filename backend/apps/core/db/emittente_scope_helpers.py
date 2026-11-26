# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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

from apps.core.services.error_manager import ErrorManager

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
# ⛔ `auth_user_id=None` SOLLEVA `E_SCOPE_SENZA_UTENTE` (2026-11-24, verifica
#    critica di D-J). Fino a quel giorno i chiamanti lo leggevano come «nessun
#    limite», la risposta voluta per il superuser Django. Ritirato il bypass,
#    `None` vuol dire «nessun utente», e un perimetro senza utente non si
#    apre: si rifiuta. E' la sede del rifiuto per ogni strada del filtro
#    applicativo (`add_emittente_scope_condition` e chi risolve il perimetro
#    una volta per un giro) e per `PermissionResolver.get_emittenti_sr_ids` /
#    `get_emittenti_pk_ids`, che dal 2026-11-24 delegano qui tenendo la loro
#    cache (D-K5 a, brief-db-porte-aperte-dalla-sola-guc §4.7): prima
#    interrogavano le funzioni DB per conto loro, e con `user=None` davano un
#    `AttributeError`. E' l'unica sede che le interroga (presidio in
#    `core/tests/db/test_scope_senza_utente.py`, test 8).
#    Il `None` della funzione DB in uscita e' un'altra cosa: lo decide il DB
#    (admin globale) e resta «nessuna restrizione».
def fetch_emittenti_scope_ids(
    auth_user_id: int | None, *, convention: str = "pk",
) -> list[int] | None:
    ErrorManager.require(
        auth_user_id is not None,
        code="E_SCOPE_SENZA_UTENTE",
        message="Perimetro emittente richiesto senza un utente.",
        detail=(
            "Una lettura con perimetro emittente e' arrivata senza auth_user_id: "
            "il chiamante deve passare l'utente della richiesta "
            "(get_scope_user_id)."
        ),
        function_name="core.emittente_scope_helpers.fetch_emittenti_scope_ids",
    )
    fn = _SCOPE_FN_BY_CONVENTION[convention]
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {fn}(%s)", [auth_user_id])  # fn da whitelist
        row = cursor.fetchone()
    if row and row[0] is not None:
        return list(row[0])
    return None


# Scopo: Appende la condizione di scope a partire da un perimetro GIA' RISOLTO.
#        Semantica di `scope_ids`: `None` = nessuna restrizione, `[]` = nessun
#        accesso (fail-closed: `col = ANY('{}')` non matcha nulla), lista =
#        whitelist.
#
# ⭐ Esiste per i GIRI che ripetono la STESSA condizione su N righe: senza,
#    ogni riga ririsolverebbe con una query il perimetro dell'operatore — che
#    dentro una richiesta non cambia. Un verbo di massa da 200 righe faceva 200
#    risoluzioni inutili (corretto il 2026-09-04 sull'archiviazione delle code).
#
# ⛔ E' una funzione SUA e non un parametro opzionale di quella sotto, ed e' una
#    scelta di sicurezza: rendere `auth_user_id` facoltativo avrebbe fatto di
#    «me ne sono dimenticato» un `None`, cioe' NESSUNO SCOPE — un fail-OPEN
#    silenzioso al posto di un `TypeError` rumoroso. Due nomi espliciti, e chi
#    non passa niente non compila.
def add_emittente_scope_condition_risolta(
    conditions: list[str],
    params: list[Any],
    *,
    scope_ids: list[int] | None,
    column: str,
) -> None:
    if not _IDENT_RE.match(column):
        raise ValueError(f"colonna scope non valida: {column!r}")
    if scope_ids is None:
        return
    conditions.append(f"{column} = ANY(%s)")  # colonna da whitelist regex
    params.append(scope_ids)


# Scopo: Appende a conditions/params la condizione di scope emittente per la
#        colonna indicata, risolvendo il perimetro con una query. No-op se
#        la fn ritorna NULL (nessuna restrizione, deciso dal DB).
#        `auth_user_id=None` solleva, da `fetch_emittenti_scope_ids`.
# ⚠️ Dentro un giro su N righe usare `add_emittente_scope_condition_risolta`
#    con il perimetro risolto una volta sola: qui ogni chiamata e' una query.
def add_emittente_scope_condition(
    conditions: list[str],
    params: list[Any],
    *,
    auth_user_id: int | None,
    column: str,
    convention: str = "pk",
) -> None:
    add_emittente_scope_condition_risolta(
        conditions, params,
        scope_ids=fetch_emittenti_scope_ids(auth_user_id, convention=convention),
        column=column,
    )
