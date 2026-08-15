# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit dell'handler del job FATTURAZIONE_GIRO (C-3). Mock del core
#        `esegui_giro_fatturazione`: verifica corsia (differita), normalizzazione
#        competenza, fino_a_stato opzionale, compattazione del result (no lista
#        per-terna), guard payload con codice registrato, e registrazione.
#
# Indice test:
#   0. happy_path_differita_competenza_normalizzata_result_compatto
#   1. fino_a_stato_opzionale_propagato
#   2. competenza_mancante_raises_payload
#   3. competenza_invalida_raises_payload
#   4. handler_registrato_dopo_boot
#   5. mirata_senza_lotti_fallisce_con_motivo (E_FATTURAZIONE_GIRO_NESSUN_LOTTO)
#   6. mirata_senza_lotti_e_terminale (niente retry su fallimento deterministico)
#   7. mirata_con_lotti_non_diagnostica (la diagnosi non gira sul percorso felice)
#   7-bis. mirata_parziale_spiega_i_non_coperti_senza_fallire (rev 2026-08-15:
#      lotti prodotti + gruppi fuori → esito con `gruppi_non_serviti`, no raise)
#   8. giro_di_massa_a_vuoto_resta_successo (perimetro non nominale)
#   9. mirata_con_terne_fallite_riporta_errori_terna (no diagnosi di perimetro,
#      non terminale: un errore pipeline puo' essere transiente)
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.core.services.coda_lavori.drain_engine import CONTEXT_KEY_TERMINALE
from apps.core.services.service_errors import ServiceError
from apps.vendite.services.fatturazione_giro_handler import (
    HANDLER_CODE,
    fatturazione_giro_handler,
)

_GIRO = "apps.vendite.services.fatturazione_driver_service.esegui_giro_fatturazione"
_REPO = "apps.vendite.db.commesse_repository.CommesseRepository"

# Fotografia del caso reale del 2026-08-03 (job 141): righe pronte, testata in
# BOZZA. `n_pronte` valorizzato + `commessa_emittibile=False` e' cio' che
# distingue «il lavoro c'e' ma la commessa e' chiusa alla fatturazione» da
# «non c'era lavoro».
_DIAGNOSI_COMMESSA_BOZZA = [{
    "gruppo_key": "ORDINE_VENDITA:019eb2ac",
    "commessa_codice": "CMM-20260610175449872-e059eb",
    "stato_commessa": "BOZZA",
    "commessa_emittibile": False,
    "n_righe": 5, "n_emesse": 0, "n_non_approvate": 0,
    "n_senza_tipo_doc": 0, "n_fuori_competenza": 0, "n_pronte": 5,
}]


class FatturazioneGiroHandlerTests(SimpleTestCase):

    # 0. Corsia differita, competenza normalizzata al 1°, result senza `esiti`.
    @patch(_GIRO)
    def test_happy_path_differita_competenza_normalizzata_result_compatto(
        self, mock_giro,
    ) -> None:
        mock_giro.return_value = {
            "lane": 3, "per_motivo": {"COMPLETATO": 3}, "falliti": 0,
            "esiti": [{"x": 1}],  # lista per-terna: va compattata via
        }

        result = fatturazione_giro_handler(
            {"competenza_mese": "2026-06-15"},
            scope={"auth_user_id": 9, "emittente_ids": [3]},
        )

        kwargs = mock_giro.call_args.kwargs
        self.assertEqual(kwargs["modalita"], "differita")
        self.assertEqual(kwargs["competenza"], date(2026, 6, 1))  # 1° del mese
        self.assertNotIn("fino_a_stato", kwargs)  # non passato → default corsia
        self.assertNotIn("esiti", result)  # compattato
        self.assertEqual(result["lane"], 3)

    # 1. fino_a_stato opzionale propagato al core quando presente.
    @patch(_GIRO)
    def test_fino_a_stato_opzionale_propagato(self, mock_giro) -> None:
        mock_giro.return_value = {"lane": 0}
        fatturazione_giro_handler(
            {"competenza_mese": "2026-06-01", "fino_a_stato": "DEFINITIVA"},
            scope=None,
        )
        self.assertEqual(mock_giro.call_args.kwargs["fino_a_stato"], "DEFINITIVA")

    # 2. competenza mancante → codice registrato (non eccezione generica).
    @patch(_GIRO)
    def test_competenza_mancante_raises_payload(self, mock_giro) -> None:
        with self.assertRaises(ServiceError) as ctx:
            fatturazione_giro_handler({}, scope=None)
        self.assertEqual(ctx.exception.code, "E_FATTURAZIONE_GIRO_PAYLOAD")
        mock_giro.assert_not_called()

    # 3. competenza malformata → stesso codice registrato.
    @patch(_GIRO)
    def test_competenza_invalida_raises_payload(self, mock_giro) -> None:
        with self.assertRaises(ServiceError) as ctx:
            fatturazione_giro_handler({"competenza_mese": "non-una-data"}, scope=None)
        self.assertEqual(ctx.exception.code, "E_FATTURAZIONE_GIRO_PAYLOAD")
        mock_giro.assert_not_called()

    # 4. L'handler è registrato nel registry dopo il boot (VenditeConfig.ready()).
    def test_handler_registrato_dopo_boot(self) -> None:
        from apps.core.services.coda_lavori.handler_registry import (
            get_handler,
            registered_handlers,
        )
        self.assertIn(HANDLER_CODE, registered_handlers())
        self.assertIs(get_handler(HANDLER_CODE), fatturazione_giro_handler)

    # 5. Emissione mirata che non produce lotti: fallisce, e il messaggio dice
    #    PERCHE' (il difetto misurato era un «fatto» muto con lotti: []).
    @patch(_REPO)
    @patch(_GIRO)
    def test_mirata_senza_lotti_fallisce_con_motivo(self, mock_giro, mock_repo) -> None:
        mock_giro.return_value = {"lane": 0, "lotti": [], "falliti": 0, "esiti": []}
        mock_repo.return_value.diagnostica_gruppi.return_value = _DIAGNOSI_COMMESSA_BOZZA

        with self.assertRaises(ServiceError) as ctx:
            fatturazione_giro_handler(
                {"competenza_mese": "2026-06-01",
                 "gruppi": ["ORDINE_VENDITA:019eb2ac"]},
                scope=None,
            )

        self.assertEqual(ctx.exception.code, "E_FATTURAZIONE_GIRO_NESSUN_LOTTO")
        # Il messaggio nomina la commessa e lo stato che blocca: e' quello che
        # l'operatore legge nel toast (FE: `ultimo_errore.message`).
        self.assertIn("CMM-20260610175449872-e059eb", ctx.exception.message)
        self.assertIn("BOZZA", ctx.exception.message)
        motivi = ctx.exception.context["gruppi_non_serviti"]
        self.assertEqual(motivi[0]["motivo"], "COMMESSA_NON_EMITTIBILE")
        # La diagnosi usa lo STESSO bound di competenza del giro.
        self.assertEqual(
            mock_repo.return_value.diagnostica_gruppi.call_args.kwargs["competenza_mese"],
            date(2026, 6, 1),
        )

    # 6. Il fallimento e' deterministico → terminale: la coda non lo ritenta 5 volte.
    @patch(_REPO)
    @patch(_GIRO)
    def test_mirata_senza_lotti_e_terminale(self, mock_giro, mock_repo) -> None:
        mock_giro.return_value = {"lane": 0, "lotti": [], "falliti": 0}
        mock_repo.return_value.diagnostica_gruppi.return_value = _DIAGNOSI_COMMESSA_BOZZA

        with self.assertRaises(ServiceError) as ctx:
            fatturazione_giro_handler(
                {"competenza_mese": "2026-06-01", "gruppi": ["g1"]}, scope=None,
            )
        self.assertTrue(ctx.exception.context.get(CONTEXT_KEY_TERMINALE))

    # 7. Percorso felice: nessuna diagnosi (dopo l'emissione le righe sono EMESSA
    #    e la fotografia racconterebbe l'arrivo, non l'ostacolo).
    @patch(_REPO)
    @patch(_GIRO)
    def test_mirata_con_lotti_non_diagnostica(self, mock_giro, mock_repo) -> None:
        mock_giro.return_value = {
            "lane": 1, "lotti": [{"lotto_id": 1279}], "falliti": 0, "esiti": [{"x": 1}],
            "gruppi_non_coperti": [],
        }
        result = fatturazione_giro_handler(
            {"competenza_mese": "2026-06-01", "gruppi": ["g1"]}, scope=None,
        )
        mock_repo.return_value.diagnostica_gruppi.assert_not_called()
        self.assertEqual(result["lotti"], [{"lotto_id": 1279}])
        self.assertNotIn("gruppi_non_serviti", result)

    # 7-bis. Emissione mirata PARZIALE (rev 2026-08-15): lotti prodotti MA
    #    gruppi rimasti fuori dalla discovery. NON solleva — i lotti sono
    #    lavoro vero — ma l'esito porta la diagnosi per-gruppo, e la diagnosi
    #    gira SOLO sui non coperti (non su chi e' stato servito). Era il caso
    #    peggiore dei tre perche' l'unico silenzioso: «2 su 3» sembrava un
    #    successo pieno e il terzo restava fermo senza che nessuno lo cercasse.
    @patch(_REPO)
    @patch(_GIRO)
    def test_mirata_parziale_spiega_i_non_coperti_senza_fallire(
        self, mock_giro, mock_repo,
    ) -> None:
        mock_giro.return_value = {
            "lane": 2, "lotti": [{"lotto_id": 1279}, {"lotto_id": 1280}],
            "falliti": 0, "esiti": [{"x": 1}],
            "gruppi_non_coperti": ["ORDINE_VENDITA:019eb2ac"],
        }
        mock_repo.return_value.diagnostica_gruppi.return_value = _DIAGNOSI_COMMESSA_BOZZA

        result = fatturazione_giro_handler(
            {"competenza_mese": "2026-06-15",
             "gruppi": ["PREVENTIVO:aa", "MAN:42", "ORDINE_VENDITA:019eb2ac"]},
            scope=None,
        )

        # Diagnosi SOLO sui non coperti, con lo stesso bound di competenza.
        diag_kwargs = mock_repo.return_value.diagnostica_gruppi.call_args.kwargs
        self.assertEqual(list(diag_kwargs["gruppi"]), ["ORDINE_VENDITA:019eb2ac"])
        self.assertEqual(diag_kwargs["competenza_mese"], date(2026, 6, 1))
        # L'esito porta lotti E spiegazioni, classificate come il giro a vuoto.
        self.assertEqual(len(result["lotti"]), 2)
        self.assertEqual(
            result["gruppi_non_serviti"][0]["motivo"], "COMMESSA_NON_EMITTIBILE",
        )
        self.assertNotIn("esiti", result)  # la compattazione resta

    # 8. Giro di MASSA a vuoto: resta un successo. Il perimetro non e' nominale —
    #    «questo mese non c'era nulla da fatturare» e' un esito legittimo, e il
    #    cron lo produce di routine.
    @patch(_REPO)
    @patch(_GIRO)
    def test_giro_di_massa_a_vuoto_resta_successo(self, mock_giro, mock_repo) -> None:
        mock_giro.return_value = {"lane": 0, "lotti": [], "falliti": 0}
        result = fatturazione_giro_handler({"competenza_mese": "2026-06-01"}, scope=None)
        mock_repo.return_value.diagnostica_gruppi.assert_not_called()
        self.assertEqual(result["lotti"], [])

    # 9. Terne trovate ma pipeline fallita: la causa vera e' negli esiti per
    #    terna — la diagnosi di perimetro racconterebbe la cosa sbagliata
    #    (NON_DETERMINATO su un perimetro perfettamente valido). E NON e'
    #    terminale: un errore pipeline puo' essere transiente, i retry della
    #    coda sono il rimedio giusto.
    @patch(_REPO)
    @patch(_GIRO)
    def test_mirata_con_terne_fallite_riporta_errori_terna(
        self, mock_giro, mock_repo,
    ) -> None:
        mock_giro.return_value = {
            "lane": 1, "lotti": [], "falliti": 1,
            "esiti": [{"ok": False, "errore_code": "E_LOCK_LOTTO",
                       "errore_detail": "lotto in lavorazione"}],
        }

        with self.assertRaises(ServiceError) as ctx:
            fatturazione_giro_handler(
                {"competenza_mese": "2026-06-01", "gruppi": ["g1"]}, scope=None,
            )

        self.assertEqual(ctx.exception.code, "E_FATTURAZIONE_GIRO_NESSUN_LOTTO")
        self.assertIn("E_LOCK_LOTTO", ctx.exception.message)
        self.assertFalse(ctx.exception.context.get(CONTEXT_KEY_TERMINALE))
        mock_repo.return_value.diagnostica_gruppi.assert_not_called()
