# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: I DUE CAMPI DEL CANONE sulla testata di contratto e offerta
#        (`generazione_canone`, `mese_partenza_canone`; F-2, F-7): come e da
#        che mese si addebitano i canoni. La lettura dal payload e la
#        traduzione dei loro CHECK sul campo, in una forma sola.
# Note: ⭐ Regola del 2 (2026-10-31, ok Tid; brief-db-contratto-righe-
#       periodiche-in-commessa §7.4, D-5). Nati sull'offerta, il contratto li
#       ha avuti con `20261031-28`, e le due copie erano gia' divergenti: il
#       contratto metteva il codice in maiuscolo e ometteva il `null`,
#       l'offerta passava i valori GREZZI («fine_periodo» → 400 del CHECK,
#       `null` → NULL su una colonna NOT NULL).
#       ⛔ Solo la FORMA: il dominio lo dicono i CHECK del DB.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any

from apps.core.services.payload_helpers import PayloadValidator

CAMPI_CANONE: tuple[str, ...] = ("generazione_canone", "mese_partenza_canone")


# Scopo: I due campi del canone presenti nel payload, nella forma che
#        raggiunge il DB: il codice in maiuscolo (`optional_upper`), il mese
#        intero (`optional_smallint`, un non intero → 400 col campo).
#        ⭐ Assente, `null` o vuoto → la chiave si OMETTE: le colonne sono NOT
#        NULL col default, e la madre del contratto filtra sulla PRESENZA della
#        chiave (§C4, come `fatturazione_immediata`).
def campi_canone(
    validator: PayloadValidator,
    payload: dict[str, Any],
    *,
    function_name: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    generazione = validator.optional_upper(
        payload, "generazione_canone", function_name=function_name,
    )
    if generazione is not None:
        out["generazione_canone"] = generazione
    mese = validator.optional_smallint(
        payload, "mese_partenza_canone", function_name=function_name,
    )
    if mese is not None:
        out["mese_partenza_canone"] = mese
    return out


# Scopo: Il payload con i due campi del canone letti da `campi_canone`, per il
#        service che passa la testata al repository com'e' (l'offerta).
#        Ritorna un payload NUOVO, quello in ingresso non si tocca.
def con_campi_canone(
    validator: PayloadValidator,
    payload: dict[str, Any],
    *,
    function_name: str | None = None,
) -> dict[str, Any]:
    out = {k: v for k, v in payload.items() if k not in CAMPI_CANONE}
    out.update(campi_canone(validator, payload, function_name=function_name))
    return out


# Scopo: Le voci della mappa CHECK dei due campi (`check_constraints` di
#        `map_integrity_error`), per la tabella di testata il cui vincolo si
#        chiama `chk_<tabella>_<campo>`. ⛔ I codici ammessi NON sono nel
#        messaggio: stanno nel CHECK (e nelle opzioni del Select), e una lista
#        ricopiata qui diverge in silenzio al primo cambio del vincolo.
def check_campi_canone(tabella: str, code: str) -> dict[str, tuple[str, str, str]]:
    return {
        f"chk_{tabella}_generazione_canone": (
            code, "Addebito dei canoni non ammesso.", "generazione_canone",
        ),
        f"chk_{tabella}_mese_partenza_canone": (
            code, "Mese di partenza dei canoni non valido: da 1 a 12.", "mese_partenza_canone",
        ),
    }
