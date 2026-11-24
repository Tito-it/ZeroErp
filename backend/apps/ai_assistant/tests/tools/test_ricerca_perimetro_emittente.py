# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gli strumenti dell'assistente che cercano su una lista con perimetro
#        emittente passano al service l'utente della richiesta, come il loro
#        endpoint gemello.
#
# 🔴 PERCHE' ESISTE (2026-11-24, verifica critica di D-J). `CercaContrattiTool`
#    chiamava `list_contratti` senza `auth_user_id`: il default `None` spegneva
#    il filtro applicativo, e la ricerca dall'assistente restava con la sola
#    RLS, contro il contratto «stessi filtri dell'endpoint».
#
# Indice test:
#   1) contratti: il service riceve l'id dell'utente della richiesta
#   2) preventivi: idem
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from apps.ai_assistant.tools.vendite_tools import CercaContrattiTool, CercaPreventiviTool


def _richiesta(user_id: int) -> SimpleNamespace:
    return SimpleNamespace(user=SimpleNamespace(id=user_id, is_authenticated=True))


class RicercaPerimetroEmittenteTests(unittest.TestCase):
    """Lo strumento porta il perimetro dell'utente, non il default del service."""

    def test_contratti_passa_l_utente(self):
        with patch(
            "apps.vendite.services.contratti_service.ContrattiService.list_contratti",
            return_value=([], 0),
        ) as lista:
            CercaContrattiTool().execute({}, _richiesta(42))
        self.assertEqual(lista.call_args.kwargs["auth_user_id"], 42)

    def test_preventivi_passa_l_utente(self):
        with patch(
            "apps.vendite.services.preventivi_service.list_preventivi",
            return_value={"results": [], "count": 0},
        ) as lista:
            CercaPreventiviTool().execute({}, _richiesta(42))
        self.assertEqual(lista.call_args.kwargs["auth_user_id"], 42)
