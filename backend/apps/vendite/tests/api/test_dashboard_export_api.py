# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit del building block di export delle liste dei CRUSCOTTI
#        (`build_dash_export_response`). Nessun DB: la fn di lista del service
#        e il renderer generico sono mockati.
#
#        Perche' esiste: il primo download reale ha fallito con
#        «page_size deve essere compreso tra 1 e 200». L'export chiedeva
#        `page_size=EXPORT_MAX_ROWS + 1` — cioe' violava il guard di
#        paginazione condiviso invece di saltarlo. Il difetto e' passato
#        perche' NESSUN test esercitava il percorso export: la suite copriva
#        le liste paginate, che quel parametro non lo usano. Questi test
#        presidiano il contratto verso il service, che e' esattamente il
#        punto in cui si e' rotto.
#
# Indice test:
#   1) chiede max_rows (non page_size) e non passa page/page_size
#   2) il +1 su EXPORT_MAX_ROWS c'e': serve a far scattare il guard di limite
#   3) i filtri di dominio arrivano alla fn di lista intatti
#   4) results/count sono sfilati dall'envelope e passati al renderer
#   5) formato invalido: si solleva PRIMA di interrogare il service
#   6) i filtri data finiscono nel file JSON-serializzabili (mai un date grezzo)
#   7) i filtri NON impostati non sono elencati fra quelli applicati
#   8) i filtri passati a `fetch` restano OGGETTI (la normalizzazione e' solo
#      per il file: al service la data serve come date, non come stringa)
# ------------------------------------------------------------

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from apps.core.services.service_errors import ServiceError
from apps.ui.services.lista_export_service import EXPORT_MAX_ROWS
from apps.vendite.api.dash_export_helpers import build_dash_export_response

_BUILD = "apps.vendite.api.dash_export_helpers.build_export_response"


def _envelope(results=None, count=0):
    return {
        "results": results if results is not None else [],
        "count": count,
        "page": 1,
        "page_size": 50,
        "total_pages": 1,
    }


class BuildDashExportResponseTests(SimpleTestCase):

    # `parse_export_format` legge `request.query_params`, che esiste solo
    # sulla Request DRF: la factory da' una WSGIRequest e va avvolta.
    def _request(self, formato="csv"):
        return Request(APIRequestFactory().get("/x/", {"formato": formato}))

    # 1) Il contratto verso il service: modalita' EXPORT via `max_rows`.
    #    `page`/`page_size` NON devono comparire — passarli con un valore
    #    fuori scala e' esattamente il difetto che ha rotto il download.
    @patch(_BUILD)
    def test_chiede_max_rows_e_non_page_size(self, mock_build) -> None:
        fetch = MagicMock(return_value=_envelope())
        build_dash_export_response(
            self._request(),
            lista_codice="vendite.dash_backlog_documenti",
            fetch=fetch,
            filtri={"classe": "RECUPERABILE"},
        )
        kwargs = fetch.call_args.kwargs
        self.assertIn("max_rows", kwargs)
        self.assertNotIn("page_size", kwargs)
        self.assertNotIn("page", kwargs)

    # 2) Il +1: senza, un perimetro esattamente al cap non farebbe scattare il
    #    guard di limite e il file uscirebbe troncato in silenzio.
    @patch(_BUILD)
    def test_max_rows_e_cap_piu_uno(self, mock_build) -> None:
        fetch = MagicMock(return_value=_envelope())
        build_dash_export_response(
            self._request(),
            lista_codice="vendite.dash_backlog_documenti",
            fetch=fetch,
            filtri={},
        )
        self.assertEqual(fetch.call_args.kwargs["max_rows"], EXPORT_MAX_ROWS + 1)

    # 3) I filtri di dominio arrivano intatti: l'export deve copiare la lista
    #    a video, non interrogare un perimetro diverso.
    @patch(_BUILD)
    def test_filtri_inoltrati_intatti(self, mock_build) -> None:
        fetch = MagicMock(return_value=_envelope())
        filtri = {
            "classe": "ANOMALIA", "area": "ORDINE_VENDITA",
            "ritardo_giorni": 30, "order_by": "anzianita_giorni", "order_dir": "desc",
        }
        build_dash_export_response(
            self._request(),
            lista_codice="vendite.dash_backlog_documenti",
            fetch=fetch,
            filtri=filtri,
        )
        for k, v in filtri.items():
            self.assertEqual(fetch.call_args.kwargs[k], v)

    # 4) L'envelope dei cruscotti (results/count) viene sfilato e consegnato al
    #    renderer generico: e' l'adattamento per cui questo BB esiste.
    @patch(_BUILD)
    def test_sfila_results_e_count_dall_envelope(self, mock_build) -> None:
        righe = [{"a": 1}, {"a": 2}]
        fetch = MagicMock(return_value=_envelope(results=righe, count=2))
        build_dash_export_response(
            self._request("xlsx"),
            lista_codice="vendite.dash_competenza_gruppi",
            fetch=fetch,
            filtri={},
        )
        kwargs = mock_build.call_args.kwargs
        self.assertEqual(kwargs["results"], righe)
        self.assertEqual(kwargs["total"], 2)
        self.assertEqual(kwargs["fmt"], "xlsx")
        self.assertEqual(kwargs["lista_codice"], "vendite.dash_competenza_gruppi")

    # 5) Formato invalido: si solleva PRIMA di interrogare il service (non si
    #    paga una query da 10.000 righe per poi scartarla).
    @patch(_BUILD)
    def test_formato_invalido_non_interroga_il_service(self, mock_build) -> None:
        fetch = MagicMock(return_value=_envelope())
        with self.assertRaises(ServiceError):
            build_dash_export_response(
                self._request("pdf"),
                lista_codice="vendite.dash_backlog_documenti",
                fetch=fetch,
                filtri={},
            )
        fetch.assert_not_called()
        mock_build.assert_not_called()


class FiltriApplicatiNelFileTests(SimpleTestCase):
    """Il blocco «Filtri applicati» del file passa da `json.dumps`.

    Il primo download del cruscotto competenza e' fallito con «Object of type
    date is not JSON serializable»: `competenza_mese` e' un `datetime.date` e
    finiva grezzo nei metadati. Backlog e Situazione aperta non se ne erano
    accorti solo perche' non hanno filtri data.
    """

    def _request(self, formato="csv"):
        return Request(APIRequestFactory().get("/x/", {"formato": formato}))

    # 6) Il caso che ha rotto: una data nei filtri deve uscire serializzabile.
    @patch(_BUILD)
    def test_filtro_data_e_json_serializzabile(self, mock_build) -> None:
        build_dash_export_response(
            self._request(),
            lista_codice="vendite.dash_competenza_gruppi",
            fetch=MagicMock(return_value=_envelope()),
            filtri={"competenza_mese": date(2026, 6, 1), "stadio": "DA_EMETTERE"},
        )
        applicati = mock_build.call_args.kwargs["filtri_applicati"]
        # L'asserzione vera: quello che il renderer fara' non deve sollevare.
        json.dumps(applicati, ensure_ascii=False, sort_keys=True)
        self.assertNotIsInstance(applicati["competenza_mese"], date)
        self.assertEqual(applicati["stadio"], "DA_EMETTERE")

    # 7) Un filtro non impostato non e' un filtro applicato: elencarlo
    #    descriverebbe male il perimetro del file.
    @patch(_BUILD)
    def test_filtri_non_impostati_non_elencati(self, mock_build) -> None:
        build_dash_export_response(
            self._request(),
            lista_codice="vendite.dash_competenza_commesse",
            fetch=MagicMock(return_value=_envelope()),
            filtri={
                "competenza_mese": date(2026, 6, 1),
                "stadio": None,
                "order_dir": "",
                "solo_ritardo": False,
            },
        )
        applicati = mock_build.call_args.kwargs["filtri_applicati"]
        self.assertEqual(list(applicati), ["competenza_mese"])

    # 8) La normalizzazione e' SOLO per il file: al service la data deve
    #    arrivare come `date`, altrimenti la query filtrerebbe su una stringa.
    @patch(_BUILD)
    def test_al_service_la_data_resta_un_oggetto_date(self, mock_build) -> None:
        fetch = MagicMock(return_value=_envelope())
        build_dash_export_response(
            self._request(),
            lista_codice="vendite.dash_competenza_gruppi",
            fetch=fetch,
            filtri={"competenza_mese": date(2026, 6, 1)},
        )
        self.assertEqual(fetch.call_args.kwargs["competenza_mese"], date(2026, 6, 1))
        self.assertIsInstance(fetch.call_args.kwargs["competenza_mese"], date)

    # 9) ⛔ Le etichette risolte SOSTITUISCONO il valore di singole chiavi, non
    #    l'intero dizionario dei filtri applicati. Col rimpiazzo, una view che
    #    volesse tradurre UNA chiave dovrebbe ricopiarsi tutte le altre — e la
    #    prossima che nasce sparirebbe dal file in silenzio, proprio dalla riga
    #    che promette di dire quale perimetro si sta guardando.
    @patch(_BUILD)
    def test_etichette_sostituiscono_una_chiave_e_non_il_dizionario(self, mock_build) -> None:
        fetch = MagicMock(return_value=_envelope())
        build_dash_export_response(
            self._request(),
            lista_codice="vendite.dash_competenza_gruppi",
            fetch=fetch,
            filtri={
                "competenza_mese": date(2026, 6, 1),
                "stadio": "DA_EMETTERE",
                "registro_id": 4,
            },
            etichette_filtri={"registro_id": "Back-office"},
        )
        applicati = mock_build.call_args.kwargs["filtri_applicati"]
        self.assertEqual(applicati["registro_id"], "Back-office")
        self.assertEqual(applicati["stadio"], "DA_EMETTERE")
        self.assertIn("competenza_mese", applicati)

    # 10) Un'etichetta non RESUSCITA un filtro che non e' stato applicato: la
    #     riga «Filtri applicati» descriverebbe un perimetro piu' stretto di
    #     quello del file.
    @patch(_BUILD)
    def test_etichetta_non_resuscita_un_filtro_assente(self, mock_build) -> None:
        fetch = MagicMock(return_value=_envelope())
        build_dash_export_response(
            self._request(),
            lista_codice="vendite.dash_competenza_gruppi",
            fetch=fetch,
            filtri={"competenza_mese": date(2026, 6, 1), "registro_id": None},
            etichette_filtri={"registro_id": "Back-office"},
        )
        applicati = mock_build.call_args.kwargs["filtri_applicati"]
        self.assertNotIn("registro_id", applicati)
