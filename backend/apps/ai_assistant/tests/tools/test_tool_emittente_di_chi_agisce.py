# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Gli strumenti dell'assistente leggono e scrivono sull'emittente di chi
#        agisce, come gli endpoint, e si fermano dove si ferma la loro
#        schermata (E1-2 di brief-be-fe-BB-audit, 2026-11-25).
#
# 🔴 PERCHE' ESISTE. Fino al 2026-11-25 l'emittente dei tool pratiche veniva
#    dal profilo, che a chi non ha una riga di permesso (il super admin)
#    risponde il gestore globale: in «tutti gli emittenti» `crea_pratica`
#    creava una pratica attribuita a un'azienda che nessuno aveva scelto. E il
#    tool ereditava dal gemello il permesso ma non il cancello della lista.
#
# Indice test:
#   1) il cancello del gemello: chiesto con la lista del gemello
#   2) il cancello del gemello: porta esente (AdminAPIView), niente cancello
#   3) il cancello del gemello: in «tutti» un tool di lista si ferma (422)
#   4) crea_pratica: scrive sull'emittente scelto
#   5) crea_pratica: in «tutti» 400 E_EMITTENTE_NON_RISOLTO, niente creato
#   6) cerca_pratiche: cerca sull'emittente di chi agisce
#   7) cerca_pratiche: operatore senza emittente, rifiuto parlante
#   8) cerca_flussi_pratica: in «tutti» passa, con l'emittente della pratica
#      (come il tab Flussi, che lo fissa col `lista_emittente_param`)
#   9) un emittente fissato dal tool non vale dove la view non lo dichiara
#  10) la query della richiesta di chat non fissa niente
# ------------------------------------------------------------

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from apps.ai_assistant.tools.config_tools import CercaOperatoriTool
from apps.ai_assistant.tools.pratiche_tools import (
    CercaFlussiPraticaTool,
    CercaPraticheTool,
    CreaPraticaTool,
)
from apps.core.services.service_errors import ServiceError

_EMITTENTE = "apps.core.services.permissions_resolver.PermissionResolver.get_emittente_for_user"
_GUARD = "apps.core.services.perimetro_emittente.guard_lista_per_codice"


def _richiesta(user_id: int = 5) -> SimpleNamespace:
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id, is_authenticated=True),
        query_params={},
    )


_CREA = {"tipo_prestazione_id": 3, "priorita_id": 2}


class CancelloDelGemelloTests(unittest.TestCase):

    def test_chiesto_con_la_lista_del_gemello(self):
        with patch(_GUARD) as guard:
            CercaPraticheTool().cancello_del_gemello(_richiesta(), {})
        self.assertEqual(guard.call_args.kwargs["lista_codice"], "pratiche.pratiche")

    # `OperatoriListView` dichiara `anagrafiche.operatori` ma e' una
    # `AdminAPIView`: la sua porta e' esente dal cancello, e il tool con lei.
    def test_porta_esente_nessun_cancello(self):
        with patch(_GUARD) as guard:
            CercaOperatoriTool().cancello_del_gemello(_richiesta(), {})
        guard.assert_not_called()

    # Il percorso intero del BB, con lo scope «tutti» e la lista senza
    # certificazione multi-emittente: il rifiuto della schermata.
    def test_in_tutti_gli_emittenti_si_ferma(self):
        flag = SimpleNamespace(multi_emittente=False, perimetro_emittente=True)
        with patch(
            "apps.core.services.permissions_resolver.PermissionResolver.get_emittenti_pk_ids",
            return_value=None,
        ), patch(
            "apps.core.services.perimetro_emittente.fetch_flag_perimetro", return_value=flag,
        ), self.assertRaises(ServiceError) as ctx:
            CreaPraticaTool().cancello_del_gemello(_richiesta(), {})
        self.assertEqual(ctx.exception.code, "E_UI_LISTA_EMITTENTE_DA_SCEGLIERE")


class CreaPraticaEmittenteTests(unittest.TestCase):

    def test_scrive_sull_emittente_scelto(self):
        with patch(_EMITTENTE, return_value=32), patch(
            "apps.pratiche.services.pratiche_service.crea_pratica", return_value=1,
        ) as crea:
            CreaPraticaTool().execute(dict(_CREA), _richiesta())
        self.assertEqual(crea.call_args.kwargs["emittente_fiscale_id"], 32)

    def test_in_tutti_gli_emittenti_rifiutata(self):
        with patch(_EMITTENTE, return_value=None), patch(
            "apps.pratiche.services.pratiche_service.crea_pratica",
        ) as crea, self.assertRaises(ServiceError) as ctx:
            CreaPraticaTool().execute(dict(_CREA), _richiesta())
        self.assertEqual(ctx.exception.code, "E_EMITTENTE_NON_RISOLTO")
        crea.assert_not_called()


class CercaPraticheEmittenteTests(unittest.TestCase):

    def test_cerca_sull_emittente_di_chi_agisce(self):
        with patch(_EMITTENTE, return_value=32), patch(
            "apps.pratiche.services.pratiche_service.cerca_pratiche", return_value=([], 0),
        ) as cerca:
            CercaPraticheTool().execute({}, _richiesta())
        self.assertEqual(cerca.call_args.kwargs["emittente_fiscale_id"], 32)

    def test_operatore_senza_emittente_rifiuto_parlante(self):
        with patch(_EMITTENTE, return_value=None), patch(
            "apps.pratiche.services.pratiche_service.cerca_pratiche",
        ) as cerca, self.assertRaises(ServiceError) as ctx:
            CercaPraticheTool().execute({}, _richiesta())
        self.assertEqual(ctx.exception.code, "E_PRATICA_VALIDATION")
        cerca.assert_not_called()


class EmittenteFissatoTests(unittest.TestCase):

    def test_flussi_in_tutti_con_l_emittente_della_pratica(self):
        flag = SimpleNamespace(multi_emittente=False, perimetro_emittente=True)
        with patch(
            "apps.core.services.permissions_resolver.PermissionResolver.get_emittenti_pk_ids",
            return_value=None,
        ), patch(
            "apps.core.services.perimetro_emittente.fetch_flag_perimetro", return_value=flag,
        ), patch(
            "apps.pratiche.db.pratiche_repository.PraticheRepository.get_pratica",
            autospec=True,
            return_value={"id": 7, "emittente_fiscale_id": 32},
        ):
            CercaFlussiPraticaTool().cancello_del_gemello(_richiesta(), {"pratica_id": 7})

    def test_flussi_pratica_non_visibile_nessun_emittente(self):
        with patch(
            "apps.pratiche.db.pratiche_repository.PraticheRepository.get_pratica",
            autospec=True,
            return_value=None,
        ):
            self.assertIsNone(CercaFlussiPraticaTool().emittente_fissato({"pratica_id": 7}))

    # `ApiPraticheList` non dichiara `lista_emittente_param`: la schermata non
    # puo' fissare un emittente, e nemmeno il tool.
    def test_fissato_ignorato_dove_la_view_non_lo_dichiara(self):
        tool = CercaPraticheTool()
        with patch.object(tool, "emittente_fissato", return_value=32), patch(_GUARD) as guard:
            tool.cancello_del_gemello(_richiesta(), {})
        self.assertIsNone(guard.call_args.kwargs["emittente_esplicito"])

    def test_la_query_della_chat_non_fissa_niente(self):
        richiesta = _richiesta()
        richiesta.query_params = {"emittente_fiscale_id": "32"}
        with patch(
            "apps.pratiche.db.pratiche_repository.PraticheRepository.get_pratica",
            autospec=True,
            return_value=None,
        ), patch(_GUARD) as guard:
            CercaFlussiPraticaTool().cancello_del_gemello(richiesta, {"pratica_id": 7})
        self.assertIsNone(guard.call_args.kwargs["emittente_esplicito"])


if __name__ == "__main__":
    unittest.main()
