# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il cursore finto dei test di repository — una sede sola.
# ------------------------------------------------------------
"""⭐ Estratto il 2026-08-28 alla TERZA copia identica.

`test_commesse_repository`, `test_filtro_ultima_revisione` e
`test_commessa_registro` avevano lo stesso helper con la stessa firma, parola per
parola. Serve a provare il SQL che un repository genera senza un database: si
sostituisce `connection.cursor`, si legge `execute.call_args`.

⚠️ NON e' l'unico mock di cursore del progetto e non pretende di esserlo: nel
resto della suite ce ne sono altri undici con firme diverse (`_mock_cursor_ctx`,
`_mock_cursor_with_row`, `_mock_cursor_with_description`...). Sono mock **ad hoc**
per esigenze diverse, non copie della stessa cosa — accorparli tutti dietro una
firma unica produrrebbe un helper con sei parametri opzionali, cioe' piu'
difficile da leggere dei dodici che sostituisce.
⛔ Si estrae cio' che e' IDENTICO, non cio' che si somiglia.
"""

from unittest.mock import MagicMock


# Scopo: un cursore che si comporta da context manager e risponde a
#        fetchone/fetchall con quello che gli si dice.
def mock_cursor(fetchone=None, fetchall=None, description=None) -> MagicMock:
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone
    cursor.fetchall.return_value = fetchall or []
    cursor.description = description
    return cursor
