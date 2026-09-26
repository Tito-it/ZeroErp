# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio del BB `dati_patch_componente`, il contratto dell'operatore
#        sulla PATCH di un componente BoM, uguale per preventivi, contratti,
#        offerte, ordini e DDT (2026-09-26). Due difetti che chiude, entrambi
#        senza errore:
#         - l'auto-approvazione: il client poteva scrivere
#           `stato_approvazione_prezzo` perche' si validava contro la
#           whitelist del repository;
#         - l'origine manuale mai scritta in ordini e DDT, dove un filtro
#           locale la scartava in silenzio.
#        Il cablaggio nei cinque service lo prova il test sul service di
#        ciascuno (ordini e DDT qui sotto, preventivi, contratti e offerte nei
#        loro moduli). Qui anche lo schema OpenAPI unico delle cinque PATCH.
# ------------------------------------------------------------
"""Indice test (0..N):

0. test_prezzo_scritto_e_manuale
1. test_prezzo_tolto_toglie_l_origine
2. test_senza_prezzo_l_origine_non_si_tocca
3. test_stringa_vuota_diventa_none
4. test_campi_del_workflow_e_origine_dal_client_rifiutati
5. test_ordini_e_ddt_scrivono_l_origine_manuale
6. test_lo_schema_openapi_pubblica_il_contratto
7. test_le_cinque_patch_usano_lo_schema_unico
"""

from __future__ import annotations

import inspect
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services._componenti_service_helpers import (
    COMPONENTE_PATCH_OPERATORE,
    dati_patch_componente,
)
from apps.vendite.db._componenti_repo_mixin import COMPONENTE_UPDATE_ALLOWED


class DatiPatchComponenteTests(TestCase):

    # 0.
    def test_prezzo_scritto_e_manuale(self) -> None:
        self.assertEqual(
            dati_patch_componente({"prezzo_unitario": "9.50"}, function_name="t"),
            {"prezzo_unitario": "9.50", "origine_prezzo": "MANUALE"},
        )

    # 1. Solo i DDT lo ammettono a DB (prezzo e origine facoltativi insieme):
    #    sugli altri documenti il NOT NULL rifiuta, ed e' giusto che rifiuti.
    def test_prezzo_tolto_toglie_l_origine(self) -> None:
        self.assertEqual(
            dati_patch_componente({"prezzo_unitario": None}, function_name="t"),
            {"prezzo_unitario": None, "origine_prezzo": None},
        )

    # 2.
    def test_senza_prezzo_l_origine_non_si_tocca(self) -> None:
        self.assertEqual(
            dati_patch_componente({"attivo": False}, function_name="t"),
            {"attivo": False},
        )

    # 3.
    def test_stringa_vuota_diventa_none(self) -> None:
        self.assertEqual(
            dati_patch_componente({"prezzo_unitario": ""}, function_name="t"),
            {"prezzo_unitario": None, "origine_prezzo": None},
        )

    # 4. Tutto cio' che il repository sa scrivere ma l'operatore non deve
    #    mandare: 400 col codice del dominio, per ciascuna chiave.
    def test_campi_del_workflow_e_origine_dal_client_rifiutati(self) -> None:
        riservati = COMPONENTE_UPDATE_ALLOWED - COMPONENTE_PATCH_OPERATORE
        self.assertIn("stato_approvazione_prezzo", riservati)
        self.assertIn("origine_prezzo", riservati)
        for chiave in sorted(riservati):
            with self.subTest(chiave=chiave):
                with self.assertRaises(ServiceError) as ctx:
                    dati_patch_componente(
                        {chiave: "x"}, function_name="t", error_code="E_DDT_VALIDAZIONE",
                    )
                self.assertEqual(ctx.exception.code, "E_DDT_VALIDAZIONE")

    # 5. ⛔ Fino al 2026-09-26 ordini e DDT scartavano in silenzio l'origine
    #    mandata dal pannello: il repository deve riceverla.
    def test_ordini_e_ddt_scrivono_l_origine_manuale(self) -> None:
        casi = (
            ("apps.vendite.services.ordini_service", "OrdiniRepository",
             {"ordine_id": 1, "riga_ordine_id": 10}),
            ("apps.vendite.services.ddt_service", "DdtRepository",
             {"ddt_id": 1, "riga_ddt_id": 10}),
        )
        for modulo, repo_cls, scope in casi:
            with self.subTest(modulo=modulo), \
                    patch(f"{modulo}.{repo_cls}") as MockRepo, \
                    patch(f"{modulo}.richiedi_righe_in_bozza"):
                repo = MagicMock()
                repo.load_componente_with_scope.return_value = scope
                MockRepo.return_value = repo
                servizio = __import__(modulo, fromlist=["update_componente"])
                servizio.update_componente(1, 10, 50, {"prezzo_unitario": "3.00"})
                repo.update_componente.assert_called_once_with(
                    50, prezzo_unitario="3.00", origine_prezzo="MANUALE",
                )


class SchemaPatchComponenteTests(TestCase):

    # 6. ⛔ Lo schema pubblica ESATTAMENTE il contratto: fino al 2026-09-26 le
    #    view pubblicavano ancora `iva_id`, `stato_approvazione_prezzo`, ...,
    #    campi che il service rifiuta con un 400.
    def test_lo_schema_openapi_pubblica_il_contratto(self) -> None:
        from apps.vendite.api._componenti_schema import COMPONENTE_PATCH_REQUEST

        self.assertEqual(set(COMPONENTE_PATCH_REQUEST.fields), set(COMPONENTE_PATCH_OPERATORE))

    # 7. Le cinque PATCH dichiarano lo schema unico, non uno loro.
    def test_le_cinque_patch_usano_lo_schema_unico(self) -> None:
        from apps.vendite.api import (
            preventivi_views,
            views_contratti,
            views_ddt,
            views_offerte,
            views_ordini,
        )
        from apps.vendite.api._componenti_schema import COMPONENTE_PATCH_REQUEST

        viste = (
            preventivi_views.ApiPreventivoRigaComponenteDetail,
            views_contratti.ApiContrattoRigaComponenteDetail,
            views_offerte.ApiOffertaEccezioneComponenteDetail,
            views_ordini.ApiOrdineRigaComponenteDetail,
            views_ddt.ApiDdtRigaComponenteDetail,
        )
        for vista in viste:
            with self.subTest(vista=vista.__name__):
                # `extend_schema` tiene il `request` nella chiusura del suo
                # `get_request_serializer`: e' li' che lo si legge.
                schema = vista.patch.kwargs["schema"]
                dichiarato = inspect.getclosurevars(
                    schema.get_request_serializer,
                ).nonlocals["request"]
                self.assertIs(dichiarato, COMPONENTE_PATCH_REQUEST)
