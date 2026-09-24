# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Ogni tool dell'assistente ha il suo endpoint gemello, e il gemello
#        e' vero (brief-db-area-funzionale-assistente-ai §5.4 punto 2).
#
# ⭐ PERCHE' ESISTE (2026-09-24). Il permesso di un tool non si dichiara piu':
#    si DERIVA dall'endpoint della UI che fa la stessa cosa, con la regola di
#    `ZeroERPPermission` (`valuta_accesso_endpoint`). Da quel giorno il gemello
#    e' l'unica cosa scritta a mano che decide chi usa il tool — e un gemello
#    sbagliato non da' errore: nega a tutti (metodo che la view non ha,
#    permission class che la regola non sa valutare) o concede la cosa
#    sbagliata. Qui si prova che ogni dichiarazione regge, per ogni tool
#    REGISTRATO: l'elenco viene dal registro, non da una lista scritta qui.
#
# Indice test:
#   1) il registro non e' vuoto (un ciclo su zero tool sarebbe verde per sottrazione)
#   2) il gemello e' una APIView e implementa il metodo dichiarato
#   3) il metodo e' uno che la regola sa tradurre in un tipo di accesso
#   4) ogni permission class del gemello ha `valuta` (altrimenti nega sempre)
#   5) conferma dichiarata ⇔ gemello di scrittura
#   6) le eccezioni senza gemello sono elencate per nome (oggi nessuna)
# ------------------------------------------------------------

from __future__ import annotations

import unittest

from rest_framework.views import APIView

from apps.ai_assistant.services import tool_registry
from apps.ai_assistant.tools.base import EndpointGemello
from apps.core.api.permissions import ZeroERPPermission

# ⚠️ I tool che non hanno un endpoint gemello, ciascuno col motivo. Oggi
#    nessuno: `AITool` pretende un `endpoint`. Un tool che non ne ha uno e'
#    una decisione da prendere (quale regola lo governa?) e si scrive qui, per
#    nome — non si aggira dichiarando un gemello che «somiglia».
_SENZA_GEMELLO: dict[str, str] = {}


class TestToolEndpointGemello(unittest.TestCase):

    def setUp(self) -> None:
        tool_registry.clear_registry()
        tool_registry.populate_registry()
        self.addCleanup(tool_registry.clear_registry)
        self.tools = tool_registry.get_all_tools()

    # 1) Un ciclo su un registro vuoto non prova niente.
    def test_il_registro_non_e_vuoto(self) -> None:
        self.assertGreater(len(self.tools), 0)

    # 2) La view esiste ed espone davvero il metodo: un gemello `POST` su una
    #    view che ha solo `get` descriverebbe una chiamata impossibile.
    def test_il_gemello_implementa_il_metodo(self) -> None:
        for tool in self.tools:
            with self.subTest(tool=tool.name):
                self.assertIsInstance(tool.endpoint, EndpointGemello)
                view = tool.endpoint.view
                self.assertTrue(
                    isinstance(view, type) and issubclass(view, APIView),
                    f"{tool.name}: il gemello {view!r} non e' una APIView",
                )
                self.assertTrue(
                    callable(getattr(view, tool.endpoint.metodo.lower(), None)),
                    f"{tool.name}: {view.__name__} non implementa "
                    f"{tool.endpoint.metodo}",
                )

    # 3) Un metodo che la regola non traduce e' negato per tutti
    #    (`azione_sconosciuta`), senza errore.
    def test_il_metodo_e_uno_che_la_regola_traduce(self) -> None:
        for tool in self.tools:
            with self.subTest(tool=tool.name):
                self.assertIn(tool.endpoint.metodo, ZeroERPPermission.METHOD_REQUIRES)

    # 4) Una permission class senza `valuta` fa negare il tool a chiunque:
    #    `valuta_accesso_endpoint` e' fail-closed.
    def test_ogni_permission_class_del_gemello_e_valutabile(self) -> None:
        for tool in self.tools:
            with self.subTest(tool=tool.name):
                classi = tool.endpoint.view.permission_classes
                self.assertTrue(classi)
                for classe in classi:
                    self.assertTrue(
                        callable(getattr(classe, "valuta", None)),
                        f"{tool.name}: {classe.__name__} non ha `valuta`",
                    )

    # 5) La conferma resta dichiarata sul tool (§5.2, «restano com'erano»):
    #    qui si prova che non contraddice il gemello. Un tool che scrive senza
    #    conferma, o una lettura che chiede conferma, e' un gemello sbagliato
    #    o una conferma sbagliata — in entrambi i casi, uno dei due mente.
    def test_conferma_dichiarata_solo_sui_gemelli_di_scrittura(self) -> None:
        for tool in self.tools:
            with self.subTest(tool=tool.name):
                scrive = tool.endpoint.metodo not in ("GET", "HEAD", "OPTIONS")
                self.assertEqual(tool.requires_confirmation, scrive)

    # 6) L'elenco delle eccezioni nomina tool che esistono.
    def test_le_eccezioni_nominano_tool_registrati(self) -> None:
        nomi = {t.name for t in self.tools}
        for nome, motivo in _SENZA_GEMELLO.items():
            with self.subTest(tool=nome):
                self.assertIn(nome, nomi)
                self.assertTrue(motivo.strip())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
