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
5-bis. test_patch_vuota_e_400_in_tutti_e_cinque — 2026-10-14: prima ordini e
   DDT «aggiornato» senza scrivere, il preventivo 404, contratto e offerta 400
   ma dopo la scrittura
6. test_lo_schema_openapi_pubblica_il_contratto
7. test_le_cinque_patch_usano_lo_schema_unico
8. test_prezzo_scritto_passa_dal_gate_l1 — 2026-10-20: senza `prezzo_override_manuale`
   la PATCH di un prezzo e' un rifiuto, prima del repository (prima nessuno dei
   cinque lo chiedeva: lo faceva solo il pannello del frontend)
9. test_senza_prezzo_scritto_il_gate_non_scatta — `null` (si torna al suggerito)
   e `attivo` non chiedono il permesso, come alla nascita del componente
10. test_le_cinque_patch_passano_l_utente — ogni view porta l'utente al service
"""

from __future__ import annotations

import inspect
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.error_manager import ErrorManager
from apps.core.services.service_errors import ServiceError
from apps.vendite.services._componenti_service_helpers import (
    COMPONENTE_PATCH_OPERATORE,
    dati_patch_componente,
)
from apps.vendite.db._componenti_repo_mixin import COMPONENTE_UPDATE_ALLOWED


_GATE = "apps.vendite.services._componenti_service_helpers.check_permesso_override_prezzo"


class DatiPatchComponenteTests(TestCase):

    # Il gate L1 legge l'utente dal DB: qui e' materia dei test 8-9, negli
    # altri lo si lascia passare.
    def setUp(self) -> None:
        patcher = patch(_GATE)
        self.gate = patcher.start()
        self.addCleanup(patcher.stop)

    # 0.
    def test_prezzo_scritto_e_manuale(self) -> None:
        self.assertEqual(
            dati_patch_componente({"prezzo_unitario": "9.50"}, auth_user_id=1, function_name="t"),
            {"prezzo_unitario": "9.50", "origine_prezzo": "MANUALE"},
        )

    # 1. Solo i DDT lo ammettono a DB (prezzo e origine facoltativi insieme):
    #    sugli altri documenti il NOT NULL rifiuta, ed e' giusto che rifiuti.
    def test_prezzo_tolto_toglie_l_origine(self) -> None:
        self.assertEqual(
            dati_patch_componente({"prezzo_unitario": None}, auth_user_id=1, function_name="t"),
            {"prezzo_unitario": None, "origine_prezzo": None},
        )

    # 2.
    def test_senza_prezzo_l_origine_non_si_tocca(self) -> None:
        self.assertEqual(
            dati_patch_componente({"attivo": False}, auth_user_id=1, function_name="t"),
            {"attivo": False},
        )

    # 3.
    def test_stringa_vuota_diventa_none(self) -> None:
        self.assertEqual(
            dati_patch_componente({"prezzo_unitario": ""}, auth_user_id=1, function_name="t"),
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
                        {chiave: "x"}, auth_user_id=1, function_name="t", error_code="E_DDT_VALIDAZIONE",
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
                servizio.update_componente(1, 10, 50, {"prezzo_unitario": "3.00"}, auth_user_id=1)
                repo.update_componente.assert_called_once_with(
                    50, prezzo_unitario="3.00", origine_prezzo="MANUALE",
                )


    # 5-bis. ⛔ Una PATCH senza campi: 400 col codice del dominio, PRIMA del
    #    repository, uguale nei cinque documenti (lo dice il BB).
    def test_patch_vuota_e_400_in_tutti_e_cinque(self) -> None:
        for codice in ("E_ORD_VALIDAZIONE", "E_DDT_VALIDAZIONE", "E_PREV_VALIDAZIONE", "E_VENDITE_VALIDATION"):
            with self.subTest(codice=codice), self.assertRaises(ServiceError) as ctx:
                dati_patch_componente({}, auth_user_id=1, function_name="t", error_code=codice)
            self.assertEqual(ctx.exception.code, codice)
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
                with self.assertRaises(ServiceError):
                    servizio.update_componente(1, 10, 50, {}, auth_user_id=1)
                repo.update_componente.assert_not_called()


    # 8. ⛔ Un prezzo scritto e' un prezzo a mano: passa dal gate L1, con
    #    l'utente della richiesta, e un rifiuto ferma tutto prima del
    #    repository. Nei due service gemelli lo si prova col repository.
    def test_prezzo_scritto_passa_dal_gate_l1(self) -> None:
        dati_patch_componente({"prezzo_unitario": "9.50"}, auth_user_id=42, function_name="t")
        self.gate.assert_called_once_with(42, function_name="t")

        def _rifiuta(*_a, **_k):
            ErrorManager.raise_error(
                code="E_PRICING_OVERRIDE_NON_AUTORIZZATO", message="no",
            )
        self.gate.side_effect = _rifiuta
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
                with self.assertRaises(ServiceError) as ctx:
                    servizio.update_componente(1, 10, 50, {"prezzo_unitario": "3.00"}, auth_user_id=7)
                self.assertEqual(ctx.exception.code, "E_PRICING_OVERRIDE_NON_AUTORIZZATO")
                repo.update_componente.assert_not_called()

    # 9.
    def test_senza_prezzo_scritto_il_gate_non_scatta(self) -> None:
        for payload in ({"prezzo_unitario": None}, {"prezzo_unitario": ""}, {"attivo": False}):
            with self.subTest(payload=payload):
                dati_patch_componente(payload, auth_user_id=None, function_name="t")
        self.gate.assert_not_called()


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


class CablaggioUtentePatchComponenteTests(TestCase):

    # 10. ⛔ Il gate vale solo se l'utente arriva: fino al 2026-10-20 quattro
    #     view su cinque non lo passavano nemmeno. Ogni PATCH porta al service
    #     l'`auth_user_id` della richiesta.
    def test_le_cinque_patch_passano_l_utente(self) -> None:
        from apps.vendite.api import (
            preventivi_views,
            views_contratti,
            views_ddt,
            views_offerte,
            views_ordini,
        )

        casi = (
            (preventivi_views.ApiPreventivoRigaComponenteDetail,
             "apps.vendite.api.preventivi_views.preventivi_service.update_componente", None,
             {"preventivo_id": 1, "riga_id": 2, "componente_id": 3}),
            (views_contratti.ApiContrattoRigaComponenteDetail,
             "apps.vendite.api.views_contratti.ContrattiService", "update_componente_riga",
             {"contratto_id": 1, "riga_id": 2, "componente_id": 3}),
            (views_offerte.ApiOffertaEccezioneComponenteDetail,
             "apps.vendite.api.views_offerte.OfferteService", "update_componente_eccezione",
             {"offerta_id": 1, "eccezione_id": 2, "componente_id": 3}),
            (views_ordini.ApiOrdineRigaComponenteDetail,
             "apps.vendite.api.views_ordini.ordini_service.update_componente", None,
             {"ordine_id": 1, "riga_id": 2, "componente_id": 3}),
            (views_ddt.ApiDdtRigaComponenteDetail,
             "apps.vendite.api.views_ddt.ddt_service.update_componente", None,
             {"ddt_id": 1, "riga_id": 2, "componente_id": 3}),
        )
        # `metodo`: per i service di CLASSE la chiamata da guardare e' quella
        # del metodo sull'istanza, non quella del costruttore.
        for vista, bersaglio, metodo, kwargs in casi:
            with self.subTest(vista=vista.__name__), \
                    patch(bersaglio) as servizio, \
                    patch(f"{vista.__module__}.get_actor_user_id", return_value=42), \
                    patch(f"{vista.__module__}.corpo_oggetto", return_value={"prezzo_unitario": "1"}), \
                    patch(f"{vista.__module__}.success_response"):
                vista().patch(MagicMock(), **kwargs)
                chiamata = (
                    getattr(servizio.return_value, metodo).call_args if metodo
                    else servizio.call_args
                )
                self.assertEqual(chiamata.kwargs.get("auth_user_id"), 42)
