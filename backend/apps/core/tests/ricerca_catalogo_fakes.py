# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il catalogo della ricerca libera, finto, per i test unitari che
#        passano dal BB `add_ricerca_full_condition` con la connessione mockata.
# Note: ⭐ Il BB legge il catalogo in DUE punti — le colonne accese
#       (`colonne_ricerca_accese`) e la soglia della lista (`soglia_ricerca`,
#       dal 2026-09-26, brief-db-be-fe-ricerca-soglia-per-lista) — e un test che
#       ne sostituisce uno solo manda l'altro al database, o a un cursore mockato
#       che risponde con la riga sbagliata. Si sostituiscono qui, insieme: un
#       terzo punto di lettura domani si aggiunge in questo file, non in ogni
#       test. Prima di questa sede la coppia era scritta a mano in cinque file,
#       con tre nomi diversi per lo stesso percorso (regola del 2, ok Tid
#       2026-09-26).
# ------------------------------------------------------------
from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from apps.core.db._helpers import RICERCA_MIN_CARATTERI

_COLONNE = "apps.core.db._helpers.colonne_ricerca_accese"
_SOGLIA = "apps.core.db._helpers.soglia_ricerca"


# Scopo: sostituisce le letture del catalogo della ricerca per la durata del
#        blocco: `accese` sono le colonne che il catalogo accende, `soglia` la
#        `ricerca_min_caratteri` della lista (di norma quella di progetto).
#        Rende i due mock `(colonne, soglia)`, per chi guarda COSA si e' letto.
@contextmanager
def catalogo_ricerca_finto(
    accese: Iterable[str], *, soglia: int = RICERCA_MIN_CARATTERI,
) -> Iterator[tuple[MagicMock, MagicMock]]:
    with patch(_COLONNE, return_value=list(accese)) as colonne, \
            patch(_SOGLIA, return_value=soglia) as lettura_soglia:
        yield colonne, lettura_soglia
