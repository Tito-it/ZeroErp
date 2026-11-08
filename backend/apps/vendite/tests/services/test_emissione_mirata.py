# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit dell'EMISSIONE MIRATA per gruppo fatturabile
#        (brief-be-fe-emissione-fattura-mirata, garanzie B1-B7). Nessun DB:
#        repository e core mockati.
#
#        Il file presidia i punti in cui la slice puo' rompersi in SILENZIO —
#        cioe' senza errori a video ma senza fare il lavoro chiesto:
#        perimetro non persistito, perimetro allargato da un rerun, seconda
#        emissione assorbita dalla dedup della coda, corsia che esclude i
#        gruppi selezionati.
#
# Indice test:
#   1) parse_gruppi: normalizza, deduplica preservando l'ordine
#   2) parse_gruppi: None = nessun perimetro (giro di massa invariato)
#   3) parse_gruppi: lista vuota rifiutata (ambigua: «niente» o «tutto»?)
#   4) parse_gruppi: elemento non stringa / vuoto rifiutato
#   5) parse_gruppi: oltre il cap → errore parlante
#   6) insieme_digest: vuoto senza gruppi (chiave del giro di massa invariata)
#   7) insieme_digest: invariante all'ordine, diverso per insiemi diversi
#   8) runner: i gruppi sono persistiti alla CREAZIONE del lotto
#   9) runner: su lotto ESISTENTE (rerun) il perimetro NON viene riscritto
#  10) runner: senza gruppi non si tocca la tabella del perimetro
#  11) driver: corsia mirata → nessun filtro di corsia, fermata a EMESSA
#  12) driver: corsia mirata senza gruppi → ValueError (mai giro di massa)
#  13) driver: i gruppi arrivano a discovery E pipeline
#  14) driver: l'esito espone la LISTA dei lotti prodotti (non il primo)
#  15) handler: payload con gruppi → corsia mirata; senza → differita
#  16) handler: `lotti` sopravvive alla compattazione del result
#  ⚠️ I test 17-19 (`gruppi_non_coperti` misurato alla discovery) sono stati
#     RIMOSSI il 2026-08-15: quella misura era una PREVISIONE e il driver non
#     la fa piu'. Il «chi non e' stato servito» e' ora un CONSUNTIVO
#     (`fn_esito_gruppi_giro` sui lotti prodotti) e vive nell'handler —
#     presidiato in test_fatturazione_giro_handler. Togliere i test insieme
#     alla funzione, non lasciarli a fotografare un meccanismo che non c'e'.
# ------------------------------------------------------------

from __future__ import annotations

from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.core.services.service_errors import ServiceError
from apps.vendite.services._fatturazione_job_helpers import (
    MAX_GRUPPI_EMISSIONE_MIRATA,
    insieme_digest,
    parse_gruppi,
)
from apps.vendite.services.fatturazione_driver_service import (
    STATO_FERMATA_EMESSA,
    esegui_giro_fatturazione,
)
from apps.vendite.services.fatturazione_giro_handler import fatturazione_giro_handler
from apps.vendite.services.pipeline_runner import LottoPipelineParams, LottoPipelineRunner
# Fixture lane condiviso (regola del 2): una sede sola per la forma di
# list_emittibili_lane.
from apps.vendite.tests._helpers.lane_fixture import lane as _lane

_SVC = "apps.vendite.services.fatturazione_driver_service"
_GIRO = f"{_SVC}.esegui_giro_fatturazione"
_E = "E_TEST"
_REPO = "apps.vendite.db.commesse_repository.CommesseRepository"



class ParseGruppiTests(TestCase):

    # 1) Normalizzazione + dedup con ordine preservato.
    def test_normalizza_e_deduplica(self):
        self.assertEqual(
            parse_gruppi(["  PREVENTIVO:a ", "PREVENTIVO:a", "MAN:42"], error_code=_E),
            ("PREVENTIVO:a", "MAN:42"),
        )

    # 2) None = nessun perimetro: e' il giro di massa di sempre, non un errore.
    def test_none_significa_nessun_perimetro(self):
        self.assertIsNone(parse_gruppi(None, error_code=_E))

    # 3) Lista vuota: ambigua fra «fattura niente» e «fattura tutto» → si
    #    rifiuta invece di indovinare (indovinare male = giro di massa).
    def test_lista_vuota_rifiutata(self):
        with self.assertRaises(ServiceError):
            parse_gruppi([], error_code=_E)

    # 4) Elementi non validi: mai una chiave spazzatura che filtra zero righe
    #    senza dirlo.
    def test_elementi_non_validi_rifiutati(self):
        for cattivo in ([123], [None], ["   "], [{"k": "v"}]):
            with self.subTest(cattivo=cattivo), self.assertRaises(ServiceError):
                parse_gruppi(cattivo, error_code=_E)

    def test_tipo_non_lista_rifiutato(self):
        with self.assertRaises(ServiceError):
            parse_gruppi("PREVENTIVO:a", error_code=_E)

    # 5) Cap esplicito: oltre, «mirata» non vuol piu' dire niente.
    def test_cap_massimo(self):
        troppi = [f"PREVENTIVO:{i}" for i in range(MAX_GRUPPI_EMISSIONE_MIRATA + 1)]
        with self.assertRaises(ServiceError):
            parse_gruppi(troppi, error_code=_E)


class GruppiDigestTests(TestCase):

    # 6) Senza gruppi il digest e' vuoto → la chiave di business del giro di
    #    massa resta IDENTICA a prima della slice (non-regressione dedup).
    def test_digest_vuoto_senza_gruppi(self):
        self.assertEqual(insieme_digest(None), "")
        self.assertEqual(insieme_digest(()), "")

    # 7) Stesso insieme = stesso lavoro (ordine irrilevante); insiemi diversi
    #    = job diversi, altrimenti la seconda emissione mirata del mese
    #    verrebbe assorbita dalla dedup dei job vivi.
    def test_digest_invariante_ordine_e_distinto_per_insieme(self):
        self.assertEqual(insieme_digest(("B", "A")), insieme_digest(("A", "B")))
        self.assertNotEqual(insieme_digest(("A",)), insieme_digest(("A", "B")))

    # 7-bis) ⭐ Generalizzato ai LOTTI (2026-08-26, regola del 2): la
    #     numerazione su selezione usa lo stesso digest con id NUMERICI.
    #     ⛔ E' il punto che rende la funzione condivisibile: due selezioni
    #     diverse sullo stesso mese devono restare due job, o la dedup assorbe
    #     la seconda e l'operatore legge «accodato» senza che succeda niente.
    def test_digest_su_id_numerici(self) -> None:
        self.assertEqual(insieme_digest((15, 12)), insieme_digest((12, 15)))
        self.assertNotEqual(insieme_digest((12,)), insieme_digest((12, 15)))
        self.assertEqual(insieme_digest([]), "")
        # ⚠️ Ordina come STRINGHE, non come numeri: indifferente al risultato
        #     (serve solo che sia deterministico) ma va saputo da chi legge.
        self.assertEqual(insieme_digest((2, 10)), insieme_digest((10, 2)))


class RunnerPersistenzaGruppiTests(SimpleTestCase):

    # Scopo: runner con repository mockato; ci interessa solo _resolve_lotto.
    def _runner(self):
        repo = MagicMock()
        repo.get_or_create_lotto.return_value = 77
        return LottoPipelineRunner(repository=repo), repo

    # 8) Il perimetro va scritto alla creazione del lotto: e' l'UNICO canale
    #    con cui raggiunge gli step (che ricevono solo lotto_id).
    def test_gruppi_persistiti_alla_creazione(self):
        runner, repo = self._runner()
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic"):
            lotto_id, esistente = runner._resolve_lotto(
                LottoPipelineParams(gruppi=("PREVENTIVO:a", "MAN:42")),
            )
        self.assertEqual(lotto_id, 77)
        self.assertFalse(esistente)
        repo.set_lotto_gruppi.assert_called_once_with(77, ("PREVENTIVO:a", "MAN:42"))

    # 9) Rerun / avanza step su lotto ESISTENTE: il criterio e' gia' a DB e va
    #    riprodotto, non riscritto. Riscriverlo da una chiamata senza gruppi
    #    allargherebbe in silenzio il perimetro di un lotto mirato.
    def test_lotto_esistente_non_riscrive_il_perimetro(self):
        runner, repo = self._runner()
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic"):
            _, esistente = runner._resolve_lotto(
                LottoPipelineParams(lotto_id=77, gruppi=("PREVENTIVO:a",)),
            )
        self.assertTrue(esistente)
        repo.set_lotto_gruppi.assert_not_called()

    # 10) Giro di massa: la tabella del perimetro non viene toccata affatto
    #     (assenza di righe = nessuna restrizione, convenzione DB).
    def test_senza_gruppi_nessuna_scrittura(self):
        runner, repo = self._runner()
        with patch("apps.vendite.services.pipeline_runner.transaction.atomic"):
            runner._resolve_lotto(LottoPipelineParams())
        repo.set_lotto_gruppi.assert_not_called()


class DriverCorsiaMirataTests(TestCase):

    # 11) Corsia mirata: NESSUN filtro di corsia (il perimetro lo fanno i
    #     gruppi) e fermata a EMESSA. Se filtrasse per corsia, un gruppo di
    #     commessa a fatturazione immediata — selezionabile a video — non
    #     produrrebbe alcun lotto, senza dirlo.
    def test_mirata_non_filtra_la_corsia_e_ferma_a_emessa(self):
        with patch(f"{_SVC}.CommesseRepository", autospec=True) as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane()]
            mock_run.return_value = {"lotto_id": 5, "motivo_stop": "FERMATO_A_STATO"}
            summary = esegui_giro_fatturazione(
                modalita="mirata", competenza=date(2026, 6, 1),
                gruppi=("PREVENTIVO:a",),
            )
        discovery = RepoCls.return_value.list_emittibili_lane.call_args.kwargs
        self.assertIsNone(discovery["fatturazione_immediata"])
        self.assertEqual(mock_run.call_args.kwargs["fino_a_stato"], STATO_FERMATA_EMESSA)
        self.assertIsNone(summary["fatturazione_immediata"])

    # 12) Corsia mirata senza gruppi = giro di massa su ENTRAMBE le corsie:
    #     fail-fast, mai un default silenzioso.
    def test_mirata_senza_gruppi_e_errore(self):
        with self.assertRaises(ValueError):
            esegui_giro_fatturazione(modalita="mirata", competenza=date(2026, 6, 1))

    # 13) I gruppi devono arrivare sia alla discovery (altrimenti nasce un
    #     lotto vuoto per ogni altra terna) sia alla pipeline (che li persiste).
    def test_gruppi_propagati_a_discovery_e_pipeline(self):
        with patch(f"{_SVC}.CommesseRepository", autospec=True) as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            RepoCls.return_value.list_emittibili_lane.return_value = [_lane()]
            mock_run.return_value = {"lotto_id": 5, "motivo_stop": "OK"}
            esegui_giro_fatturazione(
                modalita="mirata", competenza=date(2026, 6, 1),
                gruppi=["MAN:42"],
            )
        self.assertEqual(
            RepoCls.return_value.list_emittibili_lane.call_args.kwargs["gruppi"],
            ("MAN:42",),
        )
        self.assertEqual(mock_run.call_args.kwargs["gruppi"], ("MAN:42",))

    # 14) Un gruppo con righe di tipo doc fiscale diverso finisce in terne
    #     diverse → lotti diversi. L'esito deve portarli TUTTI: e' il dato del
    #     «vai al lotto», e mostrarne uno solo nasconderebbe una fattura.
    def test_esito_espone_tutti_i_lotti_prodotti(self):
        with patch(f"{_SVC}.CommesseRepository", autospec=True) as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            RepoCls.return_value.list_emittibili_lane.return_value = [
                _lane(1, tipo_doc=1), _lane(1, tipo_doc=2),
            ]
            mock_run.side_effect = [
                {"lotto_id": 11, "motivo_stop": "OK"},
                {"lotto_id": 12, "motivo_stop": "OK"},
            ]
            summary = esegui_giro_fatturazione(
                modalita="mirata", competenza=date(2026, 6, 1), gruppi=("PREVENTIVO:a",),
            )
        self.assertEqual([l["lotto_id"] for l in summary["lotti"]], [11, 12])
        self.assertEqual(summary["gruppi"], ["PREVENTIVO:a"])

    # Le terne fallite non finiscono fra i lotti: non c'e' nulla da aprire.
    def test_terna_fallita_non_entra_nei_lotti(self):
        with patch(f"{_SVC}.CommesseRepository", autospec=True) as RepoCls, \
             patch(f"{_SVC}.run_lotto_pipeline_until_done") as mock_run:
            RepoCls.return_value.list_emittibili_lane.return_value = [
                _lane(1, tipo_doc=1), _lane(1, tipo_doc=2),
            ]
            mock_run.side_effect = [
                ServiceError(code="E_X", message="boom"),
                {"lotto_id": 12, "motivo_stop": "OK"},
            ]
            summary = esegui_giro_fatturazione(
                modalita="mirata", competenza=date(2026, 6, 1), gruppi=("PREVENTIVO:a",),
            )
        self.assertEqual(summary["falliti"], 1)
        self.assertEqual([l["lotto_id"] for l in summary["lotti"]], [12])


class GiroHandlerMirataTests(SimpleTestCase):

    # 15) La presenza dei gruppi nel payload sceglie la corsia: un solo job
    #     type, due perimetri (invariante I-1: un solo core).
    #     `lotti` valorizzato di proposito: dal 2026-08-04 una mirata che non
    #     produce lotti fallisce con la diagnosi del perimetro
    #     (E_FATTURAZIONE_GIRO_NESSUN_LOTTO, test in
    #     test_fatturazione_giro_handler) — qui si verifica solo l'instradamento.
    # `_REPO` mockato: con `lotti` valorizzati l'handler chiede al DB il
    # CONSUNTIVO per gruppo (fn_esito_gruppi_giro) — qui si verifica solo
    # l'instradamento della corsia, non il consuntivo.
    @patch(_REPO, autospec=True)
    @patch(_GIRO)
    def test_payload_con_gruppi_usa_corsia_mirata(self, mock_giro, mock_repo):
        mock_giro.return_value = {
            "lane": 1, "esiti": [], "lotti": [{"lotto_id": 7}],
        }
        mock_repo.return_value.esito_gruppi_giro.return_value = []
        fatturazione_giro_handler(
            {"competenza_mese": "2026-06-15", "gruppi": ["PREVENTIVO:a"]},
        )
        kwargs = mock_giro.call_args.kwargs
        self.assertEqual(kwargs["modalita"], "mirata")
        self.assertEqual(kwargs["gruppi"], ("PREVENTIVO:a",))
        self.assertEqual(kwargs["competenza"], date(2026, 6, 1))

    @patch(_GIRO)
    def test_payload_senza_gruppi_resta_differita(self, mock_giro):
        mock_giro.return_value = {"lane": 1, "esiti": [], "lotti": []}
        fatturazione_giro_handler({"competenza_mese": "2026-06-01"})
        kwargs = mock_giro.call_args.kwargs
        self.assertEqual(kwargs["modalita"], "differita")
        self.assertNotIn("gruppi", kwargs)

    # 16) La compattazione del result toglie `esiti` (gonfierebbe il jsonb) ma
    #     NON `lotti`: senza, il FE non saprebbe dove mandare l'operatore.
    @patch(_REPO, autospec=True)
    @patch(_GIRO)
    def test_result_compatto_conserva_i_lotti(self, mock_giro, mock_repo):
        mock_repo.return_value.esito_gruppi_giro.return_value = []
        mock_giro.return_value = {
            "lane": 1,
            "esiti": [{"lotto_id": 11, "ok": True}],
            "lotti": [{"lotto_id": 11, "tipo_doc_fiscale_id": 1,
                       "competenza_mese": "2026-06-01"}],
        }
        result = fatturazione_giro_handler(
            {"competenza_mese": "2026-06-01", "gruppi": ["MAN:42"]},
        )
        self.assertNotIn("esiti", result)
        self.assertEqual(result["lotti"][0]["lotto_id"], 11)

    # Payload gruppi malformato: fallimento di dominio parlante nel job, non
    # eccezione generica da leggere nei log.
    @patch(_GIRO)
    def test_payload_gruppi_malformato(self, mock_giro):
        with self.assertRaises(ServiceError):
            fatturazione_giro_handler(
                {"competenza_mese": "2026-06-01", "gruppi": [""]},
            )
        mock_giro.assert_not_called()
