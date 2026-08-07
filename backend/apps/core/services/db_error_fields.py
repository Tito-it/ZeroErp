# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lettura unica del codice errore di dominio da un'eccezione DB.
# Note: Modulo volutamente senza dipendenze interne (lo importano
#       error_translator, error_manager e payload_helpers: qualsiasi import
#       verso quei moduli creerebbe un ciclo).
# ------------------------------------------------------------

"""Da dove arriva il codice errore di dominio, e in che ordine.

Dal 2026-08-05 `script.fn_log_and_raise_error` fa viaggiare il codice in un
campo STRUTTURATO dell'eccezione (`RAISE ... USING CONSTRAINT = p_error_code`),
non piu' solo nel testo. Il contratto e':

    SQLSTATE = 'P0001' + `constraint_name` valorizzato  =  errore di dominio

Prima esisteva solo il ripiego a regex, ed e' importante capire perche'
funzionava quasi sempre pur non essendo una difesa: il driver allega al testo
dell'eccezione anche lo *statement chiamante*, dove il codice compare scritto a
mano (`PERFORM script.fn_log_and_raise_error(..., 'E_XXX', ...)`). Il backend
leggeva il SORGENTE della chiamata, non il dato — e falliva sulle guard che il
codice lo passano da una variabile (`v_motivi -> 0 ->> 'codice'`: le transizioni
di stato di ordini, commesse, preventivi, lotti, resi) e sui codici a catalogo
senza prefisso `E_`.

⚠️ **Il ripiego a regex resta, e non e' un residuo da togliere**: nel DB vivo ci
sono ~135 `RAISE EXCEPTION` diretti in ~46 funzioni che non passano dall'helper.
Per quelli il campo esce vuoto e il testo e' l'unica strada. Si potra' togliere
il giorno in cui quei RAISE saranno zero — cantiere a se'.

Riferimento: `docs/it/dev/work-in-progress/brief-db-codice-errore-strutturato.md`.
"""

from __future__ import annotations

import re
from typing import Any

# Convenzione codici applicativi: `E_<DOMINIO>_<DETTAGLIO>`.
# ⚠️ Non vede i codici a catalogo senza prefisso (`PRATICHE_*`, `PREV_*`,
# `ERRORE_PARAMETRI`, ...): e' un limite del RIPIEGO, non del campo strutturato,
# ed e' una delle ragioni per cui il campo esiste.
# Il gruppo di cattura e' ridondante con `group(0)` ma tiene compatibile chi
# usava `DB_ERROR_CODE_RE.search(...).group(1)` (alias in payload_helpers).
APP_ERROR_CODE_RE = re.compile(r"\b(E_[A-Z][A-Z0-9_]+)\b")

# SQLSTATE di `RAISE EXCEPTION` senza ERRCODE esplicito: l'unico su cui il campo
# `constraint_name` puo' essere un codice applicativo.
SQLSTATE_RAISE_EXCEPTION = "P0001"


# Scopo: Estrae il codice di dominio dal campo strutturato dell'eccezione DB.
#        Ritorna None se l'eccezione non viene dall'helper DB (o se il campo e'
#        vuoto), lasciando decidere al chiamante se ripiegare sul testo.
def structured_db_error_code(exc: BaseException) -> str | None:
    cause = getattr(exc, "__cause__", None)
    sqlstate = getattr(cause, "sqlstate", None) or getattr(cause, "pgcode", None)
    # ⚠️ Il guard sullo SQLSTATE non e' prudenza, e' necessario: su una
    # violazione di vincolo vera (classe 23xxx) `constraint_name` contiene il
    # nome del vincolo DB (`uq_...`, `fk_...`). Prenderlo per un codice
    # applicativo scavalcherebbe `map_integrity_error` — che quei vincoli li
    # traduce in codici di dominio — e produrrebbe un codice inesistente,
    # quindi un 500 al posto di un 409 parlante.
    if sqlstate != SQLSTATE_RAISE_EXCEPTION:
        return None
    diag = getattr(cause, "diag", None)
    # ⚠️ `or None`: quando il codice viene da un'espressione che vale NULL il
    # campo arriva come STRINGA VUOTA, non come None. Senza questo si
    # propagherebbe un codice vuoto invece di ripiegare sul testo.
    return getattr(diag, "constraint_name", None) or None


# Scopo: Cerca un codice applicativo `E_*` nel testo dell'eccezione (ripiego
#        storico, valido per i RAISE diretti che non passano dall'helper).
def app_error_code_from_text(message: str) -> str | None:
    match = APP_ERROR_CODE_RE.search(message)
    return match.group(0) if match else None


# Scopo: Il codice di dominio di un'eccezione DB, campo strutturato per primo e
#        testo come ripiego. `text` esplicito per i chiamanti che hanno gia' il
#        testo in mano e non vogliono ricalcolare `str(exc)`.
def db_error_code(exc: BaseException, *, text: str | None = None) -> str | None:
    code = structured_db_error_code(exc)
    if code is not None:
        return code
    return app_error_code_from_text(text if text is not None else str(exc))


# Scopo: Diagnostica psycopg dell'eccezione DB (o None se non e' un errore DB
#        con causa psycopg). Centralizza il doppio `getattr` che i chiamanti
#        ripetevano per leggere message_primary/detail/hint.
def db_diag(exc: BaseException) -> Any | None:
    return getattr(getattr(exc, "__cause__", None), "diag", None)
