# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
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
#       ⚠️ Dal 2026-10-31 `tipo_valore` e' NOT NULL senza default
#       (brief-db-liste-datatable-grezze-secondo-giro §7.6, D-5): il parametro
#       dichiara la forma del suo valore, e i guard a07 la applicano al
#       default e a ogni override. `'TESTO'` accetta qualunque valore.
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any


# Scopo: inserisce il parametro `codice` e ne restituisce `(id, code)`.
#        `ammette_override` dichiara la famiglia: a False ogni override e'
#        rifiutato con `E_PARAMETER_OVERRIDE_NON_AMMESSO`. `tipo_valore` e
#        `default_value` vanno dichiarati insieme: il default deve avere la
#        forma del tipo (guard a07 su `config.parameters`).
def crea_parametro_di_prova(
    cur: Any, *, codice: str, ammette_override: bool = True,
    tipo_valore: str = "TESTO", default_value: str = "di prova",
) -> tuple[int, str]:
    cur.execute(
        "INSERT INTO config.parameters "
        "(id, code, default_value, description, ammette_override, tipo_valore) "
        "SELECT COALESCE(max(id), 0) + 1, %s, %s, 'Parametro di prova di un test', %s, %s "
        "FROM config.parameters RETURNING id, code",
        [codice, default_value, ammette_override, tipo_valore],
    )
    riga = cur.fetchone()
    assert riga is not None
    return int(riga[0]), str(riga[1])
