# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il BB `utente_per_id` e il suo presidio di sede unica.
# Note: mock sul modello utente, nessun DB.
#
# Indice test:
#   1) test_id_none_nessuna_query
#   2) test_utente_trovato
#   3) test_utente_inesistente_none
#   4) test_nessuna_seconda_sede (fuori dal BB, nel codice di produzione,
#      nessuno legge l'utente con `.objects.get(` su un modello utente)
#   5) test_la_regex_riconosce_la_lettura (autocontrollo del presidio)
# ------------------------------------------------------------

from __future__ import annotations

from pathlib import Path
import re
import unittest
from unittest.mock import MagicMock, patch

from apps.core.services import utente_per_id as modulo
from apps.core.services.utente_per_id import utente_per_id

_MODELLO = "apps.core.services.utente_per_id.get_user_model"


def _modello() -> MagicMock:
    modello = MagicMock()
    modello.DoesNotExist = type("DoesNotExist", (Exception,), {})
    return modello


class UtentePerIdTests(unittest.TestCase):
    # 1) `None` non arriva a Django come `pk=None` (`IS NULL`): nessuna query.
    def test_id_none_nessuna_query(self) -> None:
        modello = _modello()
        with patch(_MODELLO, return_value=modello):
            self.assertIsNone(utente_per_id(None))
        modello.objects.get.assert_not_called()

    # 2) L'utente che c'e'.
    def test_utente_trovato(self) -> None:
        modello = _modello()
        utente = MagicMock(id=7)
        modello.objects.get.return_value = utente
        with patch(_MODELLO, return_value=modello):
            self.assertIs(utente_per_id(7), utente)
        modello.objects.get.assert_called_once_with(pk=7)

    # 3) L'utente che non c'e': `None`, il rifiuto lo decide il chiamante.
    def test_utente_inesistente_none(self) -> None:
        modello = _modello()
        modello.objects.get.side_effect = modello.DoesNotExist()
        with patch(_MODELLO, return_value=modello):
            self.assertIsNone(utente_per_id(9999))


# La lettura dell'utente per id fuori dal BB. Le fixture dei test sul DB ne
# restano fuori (lì un utente mancante deve rompere il test), e anche le
# migrazioni.
_LETTURA = re.compile(r"\b(?:get_user_model\(\)|\w*[uU]ser\w*)\.objects\.get\(")


class NessunaSecondaSedeTests(unittest.TestCase):
    # 4) Regola del 2 (2026-11-24): erano sette sedi.
    def test_nessuna_seconda_sede(self) -> None:
        sede = Path(modulo.__file__).resolve()
        radice = sede.parents[2]
        fuori: list[str] = []
        for path in radice.rglob("*.py"):
            rel = path.relative_to(radice).as_posix()
            if "/tests/" in rel or "/migrations/" in rel or path.resolve() == sede:
                continue
            for n, riga in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if _LETTURA.search(riga) and not riga.lstrip().startswith("#"):
                    fuori.append(f"{rel}:{n}")
        self.assertEqual(
            fuori, [],
            "letture dell'utente per id fuori dal BB: usa "
            "`apps.core.services.utente_per_id.utente_per_id`",
        )

    # 5) Senza, un presidio con la regex sbagliata e' verde per sempre.
    def test_la_regex_riconosce_la_lettura(self) -> None:
        self.assertTrue(_LETTURA.search("user = user_model.objects.get(pk=uid)"))
        self.assertTrue(_LETTURA.search("user = User.objects.get(pk=uid)"))
        self.assertTrue(_LETTURA.search("get_user_model().objects.get(pk=uid)"))
        self.assertFalse(_LETTURA.search("User.objects.filter(pk=uid)"))
        self.assertFalse(_LETTURA.search("get_user_model().objects.create_user(u)"))
