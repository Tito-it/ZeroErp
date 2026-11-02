# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari della ripartizione per stato dei lotti — i pulsanti-filtro
#        del registro. Presidiano il perimetro del conteggio, che e' la sola
#        cosa che puo' rompersi in silenzio. Mock repository, nessun DB.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LottiWhereConteggioTests.test_stato_escluso_dal_perimetro_dei_conteggi
2) LottiWhereConteggioTests.test_gli_altri_filtri_restano_nel_perimetro
3) LottiWhereConteggioTests.test_recuperi_mese_resta_nel_perimetro
4) LottiStatiEnvelopeTests.test_envelope_porta_gli_stati_ordinati
5) LottiStatiEnvelopeTests.test_conteggio_chiesto_senza_filtro_stato
6) LottiStatiEnvelopeTests.test_contesto_inoltrato_al_conteggio
7) LottiExportRecuperiTests.test_export_inoltra_il_perimetro_recuperi
8) LottiExportRecuperiTests.test_export_recuperi_senza_mese_rifiutato
"""

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.db.vendite_repository import VenditeRepository
from apps.vendite.services import vendite_service
from apps.vendite.services.vendite_service import fn_export_lotti, fn_list_lotti


class LottiWhereConteggioTests(TestCase):
    """Il costruttore di `WHERE` condiviso da lista e conteggio."""

    def _where(self, **kwargs):
        base = {
            "competenza_mese": date(2026, 8, 1),
            "utility_id": None,
            "stato_lotto": None,
            "area_geografica_id": None,
            "tipo_doc_fiscale_id": None,
            "emittente_soggetto_ruolo_id": None,
            "auth_user_id": None,
            "solo_recuperi_mese": False,
        }
        base.update(kwargs)
        return VenditeRepository()._lotti_where(**base)

    # ⛔ L'invariante che tiene in piedi i pulsanti: il conteggio NON filtra per
    #    stato. Contandolo, scelto «BOZZA» gli altri stati andrebbero a zero, i
    #    loro pulsanti sparirebbero (si rendono solo sopra zero) e non ci
    #    sarebbe piu' modo di tornare indietro con un click.
    def test_stato_escluso_dal_perimetro_dei_conteggi(self):
        with_stato, params_con = self._where(stato_lotto="DRAFT")
        senza_stato, params_senza = self._where(
            stato_lotto="DRAFT", includi_stato=False,
        )
        self.assertIn("fl.stato_lotto = %s", with_stato)
        self.assertIn("DRAFT", params_con)
        self.assertNotIn("fl.stato_lotto", senza_stato)
        self.assertNotIn("DRAFT", params_senza)

    # ⚠️ Escluso lo stato e basta: mese, utility, area, tipo documento ed
    #    emittente sono il CONTESTO, non l'asse dei pulsanti. Perderli
    #    significherebbe contare lotti che la lista non mostra.
    def test_gli_altri_filtri_restano_nel_perimetro(self):
        clause, params = self._where(
            stato_lotto="DRAFT",
            utility_id=7,
            area_geografica_id=3,
            tipo_doc_fiscale_id=9,
            emittente_soggetto_ruolo_id=11,
            includi_stato=False,
        )
        self.assertIn("fl.competenza_mese = %s", clause)
        self.assertIn("fl.utility_id = %s", clause)
        self.assertIn("fl.area_geografica_id = %s", clause)
        self.assertIn("fl.tipo_doc_fiscale_id = %s", clause)
        self.assertIn("fl.emittente_soggetto_ruolo_id = %s", clause)
        for atteso in (date(2026, 8, 1), 7, 3, 9, 11):
            self.assertIn(atteso, params)

    # ⭐ La seconda scheda e' un perimetro suo: i pulsanti devono contare i
    #    RECUPERI quando si guardano i recuperi, non i lotti del mese.
    def test_recuperi_mese_resta_nel_perimetro(self):
        clause, _ = self._where(solo_recuperi_mese=True, includi_stato=False)
        self.assertIn("fl.competenza_mese < %s", clause)
        self.assertIn("fatturazione_lotti_fatture", clause)


class LottiStatiEnvelopeTests(TestCase):
    """`stati` viaggia nella stessa risposta della lista."""

    def _patch(self, conteggi):
        return (
            patch.object(
                vendite_service.VenditeRepository, "list_lotti",
                return_value=([], 0),
            ),
            patch.object(
                vendite_service.VenditeRepository, "count_lotti_per_stato",
                return_value=conteggi,
            ),
        )

    # Ordine stabile: due chiamate identiche non devono riordinare i pulsanti
    # sotto le mani di chi sta per cliccarne uno.
    def test_envelope_porta_gli_stati_ordinati(self):
        p_list, p_count = self._patch({"ERRORE": 2, "DRAFT": 5})
        with p_list, p_count:
            out = fn_list_lotti(competenza_mese=date(2026, 8, 1))
        self.assertEqual(
            out["stati"],
            [
                {"stato_lotto": "DRAFT", "n_lotti": 5},
                {"stato_lotto": "ERRORE", "n_lotti": 2},
            ],
        )

    # ⛔ Il presidio del difetto silenzioso: se un giorno qualcuno inoltrasse
    #    `stato_lotto` anche al conteggio, nulla fallirebbe — i pulsanti
    #    smetterebbero solo di far tornare indietro.
    def test_conteggio_chiesto_senza_filtro_stato(self):
        p_list, p_count = self._patch({})
        with p_list, p_count as mock_count:
            # Un valore DEL vocabolario (`chk_fatturazione_lotti_stato_job`):
            # fino al 2026-10-20 qui c'era «DRAFT», che e' lo stato FISCALE e
            # che il filtro accettava senza dire niente.
            fn_list_lotti(competenza_mese=date(2026, 8, 1), stato_lotto="ERRORE")
        self.assertNotIn("stato_lotto", mock_count.call_args.kwargs)

    # Il resto del contesto invece passa: conteggi e lista guardano lo stesso
    # insieme di lotti.
    def test_contesto_inoltrato_al_conteggio(self):
        p_list, p_count = self._patch({})
        with p_list, p_count as mock_count:
            fn_list_lotti(
                competenza_mese=date(2026, 8, 1),
                utility_id=7,
                auth_user_id=42,
                solo_recuperi_mese=True,
            )
        kwargs = mock_count.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 8, 1))
        self.assertEqual(kwargs["utility_id"], 7)
        self.assertEqual(kwargs["auth_user_id"], 42)
        self.assertTrue(kwargs["solo_recuperi_mese"])


class LottiExportRecuperiTests(TestCase):
    """L'export della scheda «Recuperi del mese» esporta i RECUPERI."""

    # 🔴 Il difetto che presidia (corretto il 2026-09-03): il frontend mandava
    #    `recuperi_mese: true` e nessuno lo leggeva — `_parse_lotti_query` non
    #    lo estraeva e `fn_export_lotti` non aveva il parametro. Dalla seconda
    #    scheda usciva l'elenco ORDINARIO del mese: un insieme DISGIUNTO da
    #    quello a video, senza che niente fallisse.
    @patch.object(
        vendite_service.VenditeRepository, "list_lotti", return_value=([], 0),
    )
    def test_export_inoltra_il_perimetro_recuperi(self, mock_list):
        fn_export_lotti(
            competenza_mese=date(2026, 8, 1), max_rows=10, solo_recuperi_mese=True,
        )
        self.assertTrue(mock_list.call_args.kwargs["solo_recuperi_mese"])

    # ⛔ Senza mese il predicato diventa `competenza_mese < NULL`, cioe' ZERO
    #    righe: un file vuoto consegnato come se fosse la risposta. Si rifiuta.
    @patch.object(
        vendite_service.VenditeRepository, "list_lotti", return_value=([], 0),
    )
    def test_export_recuperi_senza_mese_rifiutato(self, mock_list):
        with self.assertRaises(ServiceError):
            fn_export_lotti(competenza_mese=None, max_rows=10, solo_recuperi_mese=True)
        mock_list.assert_not_called()
