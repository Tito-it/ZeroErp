# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Un parametro di `config.parameters` COSTRUITO per un test sul DB, con
#        la sua famiglia (`ammette_override`, brief-db-parametri-senza-override
#        BE-3). Da usare dentro una transazione che il test annulla.
# Note: ⭐ Estratto il 2026-10-26 (regola del 2, ok Tid) da
#       `test_parameter_overrides_db`, al secondo consumatore
#       (`test_accessi_db`). Fino al 2026-10-25 i due test prendevano il primo
#       parametro del seed per id, che vale per tutti: il guard ne rifiuta
#       l'override. Un parametro scelto per id decide il test con un dato di
#       oggi, e uno del seed puo' stare nel registro FK-surrogata, che ne valida
#       il valore. Quello costruito non e' in nessuno dei due casi.
#       ⚠️ `config.parameters.id` non ha default: il seed lo scrive dal CSV, e
#       qui si prende il successivo al massimo.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any


# Scopo: inserisce il parametro `codice` (default `'di prova'`) e ne
#        restituisce `(id, code)`. `ammette_override` dichiara la famiglia: a
#        False ogni override e' rifiutato con `E_PARAMETER_OVERRIDE_NON_AMMESSO`.
def crea_parametro_di_prova(
    cur: Any, *, codice: str, ammette_override: bool = True,
) -> tuple[int, str]:
    cur.execute(
        "INSERT INTO config.parameters "
        "(id, code, default_value, description, ammette_override) "
        "SELECT COALESCE(max(id), 0) + 1, %s, 'di prova', 'Parametro di prova di un test', %s "
        "FROM config.parameters RETURNING id, code",
        [codice, ammette_override],
    )
    riga = cur.fetchone()
    assert riga is not None
    return int(riga[0]), str(riga[1])
