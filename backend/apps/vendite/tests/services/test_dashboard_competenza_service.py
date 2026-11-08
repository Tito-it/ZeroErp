# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari service Lente 1 Competenza (mock repository).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) DashCompetenzaMensileServiceTests.test_griglia_12_mesi_4_stadi_sempre_completa
2) DashCompetenzaMensileServiceTests.test_contratto_simmetrico_celle_vuote
3) DashCompetenzaMensileServiceTests.test_ordine_stadi_funnel
4) DashCompetenzaMensileServiceTests.test_pivot_fatturata_somma_e_breakdown
5) DashCompetenzaMensileServiceTests.test_stadio_non_fatturato_proiettato
6) DashCompetenzaMensileServiceTests.test_totali_mese_db6
7) DashCompetenzaMensileServiceTests.test_stadio_sconosciuto_accodato_fail_visible
8) DashCompetenzaMensileServiceTests.test_errori_per_mese
9) DashCompetenzaMensileServiceTests.test_anno_fuori_range_min
10) DashCompetenzaMensileServiceTests.test_anno_fuori_range_max
9) DashCompetenzaAttivitaServiceTests.test_attivita_ok_envelope_paginato
10) DashCompetenzaAttivitaServiceTests.test_attivita_stadio_invalido
11) DashCompetenzaAttivitaServiceTests.test_attivita_competenza_normalizzata_al_primo
12) DashCompetenzaAttivitaServiceTests.test_attivita_solo_ritardo_passthrough
13) DashCompetenzaAttivitaServiceTests.test_attivita_page_invalida
13a) DashCompetenzaAttivitaServiceTests.test_attivita_ordinamento_inoltrato
13b) DashCompetenzaAttivitaServiceTests.test_attivita_order_by_non_valido
13c) DashCompetenzaAttivitaServiceTests.test_attivita_order_dir_non_valido
13d) DashCompetenzaCommesseServiceTests.test_commesse_ok_envelope_e_passthrough (DEC-4)
13e) DashCompetenzaCommesseServiceTests.test_commesse_stadio_invalido
13f) DashCompetenzaCommesseServiceTests.test_commesse_order_by_non_valido
13g) DashCompetenzaCommesseServiceTests.test_commesse_order_dir_non_valido
13h) DashCompetenzaCommesseServiceTests.test_commesse_page_invalida
14) DashCompetenzaErroriServiceTests.test_errori_ok_envelope_paginato
15) DashCompetenzaErroriServiceTests.test_errori_competenza_opzionale_none
16) DashCompetenzaErroriServiceTests.test_errori_competenza_normalizzata_al_primo
16a) DashCompetenzaErroriServiceTests.test_errori_order_by_propagato
16b) DashCompetenzaErroriServiceTests.test_errori_order_by_fuori_whitelist
16c) DashCompetenzaErroriServiceTests.test_errori_order_dir_invalido
17) DashCompetenzaGruppiServiceTests.test_gruppi_envelope_con_riepilogo_e_facet
18) DashCompetenzaGruppiServiceTests.test_gruppi_filtro_tipo_inoltrato_alla_lista_e_ai_totali
19) DashCompetenzaGruppiServiceTests.test_gruppi_facet_ignora_il_filtro_tipo
20) DashCompetenzaGruppiServiceTests.test_gruppi_stadio_invalido
21) DashCompetenzaGruppiServiceTests.test_gruppi_order_by_non_valido
22) DashCompetenzaGruppiServiceTests.test_gruppi_competenza_normalizzata_al_primo
23) DashCompetenzaGruppiRepositoryTests.test_id_documento_dalla_vista_non_da_una_seconda_risoluzione
24) DashCompetenzaGruppiRepositoryTests.test_mapping_espone_documento_id_e_ne_preserva_il_null
24-bis) DashCompetenzaGruppiRepositoryTests.test_mapping_espone_emittibilita_testata_col_motivo
24-ter) DashCompetenzaGruppiRepositoryTests.test_mapping_espone_cliente_di_fatturazione_e_ne_preserva_il_null
24-quater) DashCompetenzaGruppiRepositoryTests.test_where_gruppi_filtro_cliente_e_ricerca
24-quater-bis) DashCompetenzaGruppiRepositoryTests.test_filtri_gruppi_colonne_della_ricerca
24-quinquies) DashCompetenzaGruppiRepositoryTests.test_mapping_espone_emittente_ragione_sociale
24-sexies) DashCompetenzaGruppiRepositoryTests.test_ogni_campo_sorgente_di_catalogo_e_una_chiave_della_riga
24-septies) DashCompetenzaGruppiRepositoryTests.test_larghezza_riga_finta_uguale_al_select
24-novies) DashCompetenzaGruppiRepositoryTests.test_mapping_espone_il_blocco_di_emissione_col_bersaglio
24-novies-bis) DashCompetenzaGruppiRepositoryTests.test_senza_blocco_di_emissione_i_quattro_campi_restano_none
24-decies) DashCompetenzaGruppiRepositoryTests.test_mapping_espone_l_esito_dell_ultimo_tentativo
24-undecies) DashCompetenzaGruppiRepositoryTests.test_esito_assente_resta_none
24-octies) DashCompetenzaGruppiRepositoryTests.test_mapping_espone_riferimento_non_nullo
25) DashCompetenzaFatturePerCellaTests.test_n_fatture_innestato_sulla_cella_di_quello_stadio
26) DashCompetenzaFatturePerCellaTests.test_stadio_non_calcolabile_e_non_applicabile
27) DashCompetenzaFatturePerCellaTests.test_calcolo_fallito_e_errore_non_silenzio
28) DashCompetenzaFatturePerCellaTests.test_cella_vuota_tace_senza_essere_errore
29) DashCompetenzaFatturePerCellaTests.test_zero_esplicito_non_diventa_none
30) DashCompetenzaFatturePerCellaTests.test_una_sola_lettura_per_la_griglia
31) DashCompetenzaFatturePerCellaTests.test_errore_solo_dove_ci_sono_attivita
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest import TestCase
from unittest.mock import ANY, patch

from apps.core.services.service_errors import ServiceError
from apps.core.tests.ricerca_catalogo_fakes import catalogo_ricerca_finto
from apps.vendite.db.vendite_repository import VenditeRepository

# Le cinque colonne che il seed accende sulla lista gruppi, per il catalogo
# finto del BB della ricerca libera (`catalogo_ricerca_finto`).
_GRUPPI_ACCESE = (
    "riferimento", "cliente_display", "commessa_codice", "ba_codice_fatturazione", "id_fiscale",
)
from apps.vendite.services import vendite_service
from apps.vendite.services.vendite_service import (
    fn_dash_competenza_attivita,
    fn_dash_competenza_commesse,
    fn_dash_competenza_errori,
    fn_dash_competenza_gruppi,
    fn_dash_competenza_mensile,
)

# ⭐ Il mese che si SPEZZA con la grana nuova (changeSet 20260820-07): lo stesso
# bucket FATTURATA/EMESSA arriva su DUE righe, una per tipo movimento. E' la
# forma misurata dal team DB su luglio 2026 — 25 attivita' NORMALE + 1 ONERE da
# 5.000 €. Il breakdown 3a deve restare UNA voce per stato.
# ⭐ Le DUE popolazioni dentro `EMESSA_NON_FATTURATA`, che la card deve saper
# distinguere: il RESIDUO chiede un'azione («Riporta da emettere»), le altre due
# situazioni no. ⚠️ Una riga per valore VIVO del vocabolario (tre: vedi il
# commento su `MOTIVO_NON_FATTURATA_RESIDUO` nel repository, che e' la sede).
# ⚠️ Il caso si COSTRUISCE qui: nei dati di sviluppo del 2026-08-27 il transito
# non c'era (5 righe su 5 residue), quindi un test che guardasse la popolazione
# reale sarebbe verde senza aver verificato niente.
_ROWS_DUE_POPOLAZIONI = [
    {
        "competenza_mese": "2026-07-01",
        "stadio": "EMESSA_NON_FATTURATA",
        "stato_fattura_codice_interno": None,
        "stato_fattura_codice": None,
        "tipo_movimento": "NORMALE",
        "n_attivita": 5,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "5019.00",
        "valore_fatturato": "0",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
        "motivo_non_fatturata": "RESIDUO",
    },
    {
        "competenza_mese": "2026-07-01",
        "stadio": "EMESSA_NON_FATTURATA",
        "stato_fattura_codice_interno": None,
        "stato_fattura_codice": None,
        "tipo_movimento": "NORMALE",
        "n_attivita": 3,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "150.00",
        "valore_fatturato": "0",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
        "motivo_non_fatturata": "GIRO_IN_CORSO",
    },
    # ⚠️ La quarta situazione, che nessun percorso scritto oggi produce — e non
    #    e' una ragione per non provarla: il modello l'ammette (una riga di
    #    commessa EMESSA senza riga in attivita_fatturabili).
    {
        "competenza_mese": "2026-07-01",
        "stadio": "EMESSA_NON_FATTURATA",
        "stato_fattura_codice_interno": None,
        "stato_fattura_codice": None,
        "tipo_movimento": "NORMALE",
        "n_attivita": 1,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "70.00",
        "valore_fatturato": "0",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
        "motivo_non_fatturata": "SENZA_ATTIVITA_FATTURABILE",
    },
]


_ROWS_BUCKET_SPEZZATO = [
    {
        "competenza_mese": "2026-07-01",
        "stadio": "FATTURATA",
        "stato_fattura_codice_interno": "EMESSA",
        "stato_fattura_codice": "EMESSA",
        "tipo_movimento": "NORMALE",
        "n_attivita": 25,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "924.00",
        "valore_fatturato": "924.00",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
    },
    {
        "competenza_mese": "2026-07-01",
        "stadio": "FATTURATA",
        "stato_fattura_codice_interno": "EMESSA",
        "stato_fattura_codice": "EMESSA",
        "tipo_movimento": "ONERE",
        "n_attivita": 1,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "5000.00",
        "valore_fatturato": "5000.00",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
    },
]

# ⭐ Il mese del rilievo in-app: una fattura da emettere e una NOTA DI CREDITO da
# emettere, di pari importo. Col residuo a somma unica si annullerebbero e la
# dashboard direbbe «niente da fare» con DUE documenti da produrre.
_ROWS_COMPENSAZIONE = [
    {
        "competenza_mese": "2026-08-01",
        "stadio": "FATTURATA",
        "stato_fattura_codice_interno": "EMESSA",
        "stato_fattura_codice": "EMESSA",
        "tipo_movimento": "NORMALE",
        "n_attivita": 10,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "1000.00",
        "valore_fatturato": "1000.00",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
    },
    {
        "competenza_mese": "2026-08-01",
        "stadio": "DA_EMETTERE",
        "stato_fattura_codice_interno": None,
        "stato_fattura_codice": None,
        "tipo_movimento": "NORMALE",
        "n_attivita": 1,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "29.50",
        "valore_fatturato": "0",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
    },
    {
        "competenza_mese": "2026-08-01",
        "stadio": "DA_EMETTERE",
        "stato_fattura_codice_interno": None,
        "stato_fattura_codice": None,
        "tipo_movimento": "RETTIFICA",
        "n_attivita": 2,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "-29.50",
        "valore_fatturato": "0",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
    },
]

# ⭐ Il mese CHIUSO: tutto fatturato, nota di credito COMPRESA (gia' emessa).
# Serve a provare la proprieta' di chiusura della misura assoluta — se il
# numeratore non fosse anch'esso in valore assoluto, un mese senza piu' niente
# da fare non arriverebbe MAI al 100%: la nota di credito emessa lo tirerebbe
# giu' come se fosse lavoro arretrato.
_ROWS_TUTTO_FATTURATO = [
    {
        "competenza_mese": "2026-09-01",
        "stadio": "FATTURATA",
        "stato_fattura_codice_interno": "EMESSA",
        "stato_fattura_codice": "EMESSA",
        "tipo_movimento": "NORMALE",
        "n_attivita": 10,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "1000.00",
        "valore_fatturato": "1000.00",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
    },
    {
        "competenza_mese": "2026-09-01",
        "stadio": "FATTURATA",
        "stato_fattura_codice_interno": "EMESSA",
        "stato_fattura_codice": "EMESSA",
        "tipo_movimento": "RETTIFICA",
        "n_attivita": 2,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "-29.50",
        "valore_fatturato": "-29.50",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
    },
]

# Due righe FATTURATA di gennaio (una per stato fattura) + una DA_EMETTERE:
# esercitano insieme la somma per stadio e il breakdown 3a.
_ROWS_GENNAIO = [
    {
        "competenza_mese": "2026-01-01",
        "stadio": "DA_EMETTERE",
        "stato_fattura_codice_interno": None,
        "stato_fattura_codice": None,
        "tipo_movimento": "NORMALE",
        "n_attivita": 2,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "300.00",
        "valore_fatturato": "0",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
    },
    {
        "competenza_mese": "2026-01-01",
        "stadio": "FATTURATA",
        "stato_fattura_codice_interno": "DRAFT",
        "stato_fattura_codice": "DRAFT",
        "tipo_movimento": "NORMALE",
        "n_attivita": 3,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "1000.00",
        "valore_fatturato": "990.00",
        "n_in_ritardo": 1,
        "valore_in_ritardo": "100.00",
    },
    {
        "competenza_mese": "2026-01-01",
        "stadio": "FATTURATA",
        "stato_fattura_codice_interno": "DEFINITIVA",
        "stato_fattura_codice": "DEFINITIVA",
        "tipo_movimento": "NORMALE",
        "n_attivita": 4,
        "n_attivita_trattenute": 0,
        "valore_trattenuto": "0",
        "valore": "2000.00",
        "valore_fatturato": "2010.50",
        "n_in_ritardo": 0,
        "valore_in_ritardo": "0",
    },
]


class DashCompetenzaMensileServiceTests(TestCase):
    # Scopo: neutralizza la terza lettura della griglia (conteggio fatture per
    #        cella) su TUTTI i test della classe. Non un decoratore per metodo:
    #        e' una dipendenza DB che nessuno di questi test esercita, e in CI
    #        — dove il database non c'e' — una query vera li farebbe fallire
    #        tutti insieme per un motivo che non riguarda cio' che asseriscono.
    #        I test che la misurano davvero la mockano per proprio conto.
    def setUp(self):
        patcher = patch.object(
            vendite_service.VenditeRepository,
            "count_dash_competenza_fatture_mensile", autospec=True,
            return_value=({}, set()),
        )
        self._mock_fatture = patcher.start()
        self.addCleanup(patcher.stop)

    # Scopo: La griglia ha sempre 12 mesi x 4 stadi anche a repository vuoto.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", autospec=True, return_value=[])
    def test_griglia_12_mesi_4_stadi_sempre_completa(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        self.assertEqual(data["anno"], 2026)
        self.assertEqual(len(data["mesi"]), 12)
        self.assertEqual(data["mesi"][0]["competenza_mese"], "2026-01-01")
        self.assertEqual(data["mesi"][11]["competenza_mese"], "2026-12-01")
        for mese in data["mesi"]:
            self.assertEqual(len(mese["stadi"]), 4)
            self.assertEqual(mese["n_errori"], 0)

    # Scopo: Contratto simmetrico: ogni cella vuota ha tutti i campi a zero
    #        (inclusa la misura display) e stati_fattura lista vuota; i totali
    #        del mese vuoto sono zeri espliciti (concentrico DL-8).
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", autospec=True, return_value=[])
    def test_contratto_simmetrico_celle_vuote(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        for cella in data["mesi"][0]["stadi"]:
            self.assertEqual(cella["n_attivita"], 0)
            self.assertEqual(cella["valore"], "0")
            self.assertEqual(cella["valore_fatturato"], "0")
            self.assertEqual(cella["valore_display"], "0")
            self.assertEqual(cella["n_in_ritardo"], 0)
            self.assertEqual(cella["valore_in_ritardo"], "0")
            self.assertEqual(cella["stati_fattura"], [])
        totali = data["mesi"][0]["totali"]
        self.assertEqual(totali["valore_teorico"], "0")
        self.assertEqual(totali["valore_fatturato"], "0")
        self.assertEqual(totali["valore_da_fatturare"], "0")
        self.assertEqual(totali["n_in_ritardo"], 0)

    # Scopo: L'ordine degli stadi e' quello del funnel commessa → fattura.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", autospec=True, return_value=[])
    def test_ordine_stadi_funnel(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        ordine = [s["stadio"] for s in data["mesi"][0]["stadi"]]
        self.assertEqual(
            ordine,
            ["DA_APPROVARE", "DA_EMETTERE", "EMESSA_NON_FATTURATA", "FATTURATA"],
        )

    # Scopo: Le righe FATTURATA per stato si sommano nella cella stadio e
    #        alimentano il breakdown stati_fattura (blocco 3a, ordine repo).
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile", autospec=True,
        return_value=_ROWS_GENNAIO,
    )
    def test_pivot_fatturata_somma_e_breakdown(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        gennaio = {s["stadio"]: s for s in data["mesi"][0]["stadi"]}
        fatturata = gennaio["FATTURATA"]
        self.assertEqual(fatturata["n_attivita"], 7)
        self.assertEqual(fatturata["valore"], "3000.00")
        self.assertEqual(fatturata["valore_fatturato"], "3000.50")
        # DB-6: la misura display del fatturato e' l'imponibile riga.
        self.assertEqual(fatturata["valore_display"], "3000.50")
        self.assertEqual(fatturata["n_in_ritardo"], 1)
        self.assertEqual(fatturata["valore_in_ritardo"], "100.00")
        self.assertEqual(len(fatturata["stati_fattura"]), 2)
        self.assertEqual(
            fatturata["stati_fattura"][0]["stato_fattura_codice_interno"], "DRAFT"
        )
        self.assertEqual(fatturata["stati_fattura"][0]["valore_fatturato"], "990.00")
        self.assertEqual(
            fatturata["stati_fattura"][1]["stato_fattura_codice_interno"], "DEFINITIVA"
        )
        # Febbraio non eredita nulla.
        febbraio = {s["stadio"]: s for s in data["mesi"][1]["stadi"]}
        self.assertEqual(febbraio["FATTURATA"]["n_attivita"], 0)

    # Scopo: Uno stadio non fatturato finisce nella cella giusta senza
    #        popolare il breakdown stati_fattura.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile", autospec=True,
        return_value=_ROWS_GENNAIO,
    )
    def test_stadio_non_fatturato_proiettato(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        gennaio = {s["stadio"]: s for s in data["mesi"][0]["stadi"]}
        da_emettere = gennaio["DA_EMETTERE"]
        self.assertEqual(da_emettere["n_attivita"], 2)
        self.assertEqual(da_emettere["valore"], "300.00")
        # DB-6: fuori dal fatturato la misura display resta il teorico.
        self.assertEqual(da_emettere["valore_display"], "300.00")
        self.assertEqual(da_emettere["stati_fattura"], [])

    # Scopo: I totali del mese seguono DB-6: fatturato = imponibile riga,
    #        da fatturare = teorico degli stadi non fatturati.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile", autospec=True,
        return_value=_ROWS_GENNAIO,
    )
    def test_totali_mese_db6(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        totali = data["mesi"][0]["totali"]
        self.assertEqual(totali["valore_teorico"], "3300.00")
        self.assertEqual(totali["valore_fatturato"], "3000.50")
        self.assertEqual(totali["valore_da_fatturare"], "300.00")
        self.assertEqual(totali["n_in_ritardo"], 1)

    # Scopo: 🔴 Il breakdown 3a resta UNA voce per stato fattura anche quando la
    #        vista spezza il bucket per tipo movimento (changeSet 20260820-07).
    # ⚠️ Il difetto si vede SOLO su un mese come luglio, dove uno stesso stadio
    #        contiene movimenti di natura diversa: su agosto le rettifiche stanno
    #        in DA_EMETTERE e i normali in FATTURATA, la cardinalita' non cambia
    #        affatto e provare quel mese direbbe «non si e' rotto niente».
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile", autospec=True,
        return_value=_ROWS_BUCKET_SPEZZATO,
    )
    def test_breakdown_non_duplica_lo_stato_su_bucket_spezzato(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        luglio = data["mesi"][6]
        fatturata = next(s for s in luglio["stadi"] if s["stadio"] == "FATTURATA")

        # UNA voce, non due: il breakdown risponde a «in che stato sono le
        # fatture», e la natura del movimento non e' quella domanda.
        self.assertEqual(len(fatturata["stati_fattura"]), 1)
        voce = fatturata["stati_fattura"][0]
        self.assertEqual(voce["stato_fattura_codice_interno"], "EMESSA")
        # E i movimenti si SOMMANO dentro la voce, non si perdono.
        self.assertEqual(voce["n_attivita"], 26)
        self.assertEqual(voce["valore"], "5924.00")
        self.assertEqual(voce["valore_fatturato"], "5924.00")

    # Scopo: 🔴 La copertura conta una nota di credito da emettere come LAVORO,
    #        in valore ASSOLUTO. Due misure sbagliate prima di questa:
    #          · somma con segno   -> i due importi si annullano, residuo ZERO,
    #                                 «niente da fare» con due documenti aperti;
    #          · rettifiche escluse -> residuo 29,50 ma la nota di credito
    #                                 sparisce dal conto: «100% coperto» mentre
    #                                 aspetta di essere emessa.
    #        In assoluto il residuo e' 59,00 — i due documenti, contati due
    #        volte perche' sono due lavori. Correzione di Tid, 2026-08-20.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile", autospec=True,
        return_value=_ROWS_COMPENSAZIONE,
    )
    def test_copertura_non_compensa_le_rettifiche(self, _mock_rows, _mock_err):
        totali = fn_dash_competenza_mensile(anno=2026)["mesi"][7]["totali"]

        # Il NETTO resta quello di prima (altri consumatori lo leggono): la
        # fattura e la nota di credito si annullano, e infatti fa zero.
        self.assertEqual(totali["valore_da_fatturare"], "0.00")

        # La COPERTURA no: 29,50 di fattura + 29,50 di nota di credito, ognuno
        # per quello che vale. Due documenti da produrre, due volte contati.
        self.assertEqual(totali["copertura_da_fatturare"], "59.00")
        self.assertEqual(totali["copertura_fatturato"], "1000.00")
        # Le due voci simmetriche del residuo, e la loro somma E' il residuo:
        # nessuna delle due sta fuori dal denominatore del grafico.
        self.assertEqual(totali["copertura_da_addebitare"], "29.50")
        self.assertEqual(totali["copertura_da_accreditare"], "29.50")
        self.assertEqual(
            Decimal(totali["copertura_da_addebitare"])
            + Decimal(totali["copertura_da_accreditare"]),
            Decimal(totali["copertura_da_fatturare"]),
        )
        # E le rettifiche restano DICHIARATE, col loro segno vero: il grafico
        # dice quanto manca, questa voce dice che cosa manca.
        self.assertEqual(totali["rettifiche_valore"], "-29.50")
        self.assertEqual(totali["rettifiche_n"], 2)

        # E il rapporto del grafico non puo' superare il 100% NE' toccarlo:
        # finche' c'e' un documento aperto, «coperto» non si puo' dire.
        transitato = Decimal(totali["copertura_fatturato"])
        fermo = Decimal(totali["copertura_da_fatturare"])
        self.assertLess(transitato / (transitato + fermo), 1)

    # Scopo: 🔴 PROPRIETA' DI CHIUSURA — a mese tutto fatturato la copertura fa
    #        esattamente 100%, anche con una nota di credito gia' emessa dentro.
    # ⚠️ E' la contro-prova della misura assoluta, ed e' il punto in cui una
    #        formula mista (denominatore assoluto, numeratore con segno) si
    #        romperebbe: il numeratore varrebbe 970,50 su 1.029,50 = 94%, cioe'
    #        un mese senza NIENTE da fare che si dichiara incompleto per sempre.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile", autospec=True,
        return_value=_ROWS_TUTTO_FATTURATO,
    )
    def test_copertura_chiude_al_100_con_nota_di_credito_emessa(self, _mock_rows, _mock_err):
        totali = fn_dash_competenza_mensile(anno=2026)["mesi"][8]["totali"]

        # Numeratore in assoluto: la nota di credito emessa e' lavoro FATTO.
        self.assertEqual(totali["copertura_fatturato"], "1029.50")
        self.assertEqual(totali["copertura_da_fatturare"], "0")

        transitato = Decimal(totali["copertura_fatturato"])
        fermo = Decimal(totali["copertura_da_fatturare"])
        self.assertEqual(transitato / (transitato + fermo), 1)

        # ⚠️ Il netto NON fa 1029,50 ed e' giusto cosi': quello e' il ricavo
        # (970,50), questa e' la quantita' di lavoro. Due domande diverse.
        self.assertEqual(totali["valore_fatturato"], "970.50")

    # Scopo: Uno stadio emesso dalla vista ma fuori whitelist NON viene perso:
    #        accodato dopo i 4 noti (fail-visible) e conteggiato nei totali.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile", autospec=True,
        return_value=[
            {
                "competenza_mese": "2026-01-01",
                "stadio": "STORNATA",
                "stato_fattura_codice_interno": None,
                "stato_fattura_codice": None,
                "tipo_movimento": "NORMALE",
                "n_attivita": 1,
                "valore": "50.00",
                "valore_fatturato": "0",
                "n_in_ritardo": 0,
                "valore_in_ritardo": "0",
                "n_attivita_trattenute": 0,
                "valore_trattenuto": "0",
            }
        ],
    )
    def test_stadio_sconosciuto_accodato_fail_visible(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        gennaio = data["mesi"][0]
        stadi = [s["stadio"] for s in gennaio["stadi"]]
        self.assertEqual(
            stadi,
            ["DA_APPROVARE", "DA_EMETTERE", "EMESSA_NON_FATTURATA", "FATTURATA", "STORNATA"],
        )
        self.assertEqual(gennaio["stadi"][4]["n_attivita"], 1)
        self.assertEqual(gennaio["totali"]["valore_teorico"], "50.00")
        self.assertEqual(gennaio["totali"]["valore_da_fatturare"], "50.00")
        # Gli altri mesi restano a 4 stadi.
        self.assertEqual(len(data["mesi"][1]["stadi"]), 4)

    # Scopo: Il conteggio errori vivi arriva nel mese giusto (blocco 4).
    @patch.object(
        vendite_service.VenditeRepository,
        "count_dash_competenza_errori_mensile", autospec=True,
        return_value={"2026-03-01": 2},
    )
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", autospec=True, return_value=[])
    def test_errori_per_mese(self, _mock_rows, _mock_err):
        data = fn_dash_competenza_mensile(anno=2026)
        self.assertEqual(data["mesi"][2]["n_errori"], 2)
        self.assertEqual(data["mesi"][0]["n_errori"], 0)

    # Scopo: Anno sotto il minimo -> E_VENDITE_VALIDATION.
    def test_anno_fuori_range_min(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_mensile(anno=1999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Anno sopra il massimo -> E_VENDITE_VALIDATION.
    def test_anno_fuori_range_max(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_mensile(anno=2101)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")


class DashCompetenzaAttivitaServiceTests(TestCase):
    # Scopo: Envelope paginato standard con i risultati del repository.
    #        Nessun auth_user_id: lo scope e' interamente DB-side (GUC vista).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_attivita", autospec=True,
        return_value=([{"commessa_attivita_id": 1}], 1),
    )
    def test_attivita_ok_envelope_paginato(self, mock_repo):
        data = fn_dash_competenza_attivita(
            competenza_mese=date(2026, 5, 1), stadio="FATTURATA"
        )
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["total_pages"], 1)
        self.assertEqual(data["results"], [{"commessa_attivita_id": 1}])
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["stadio"], "FATTURATA")
        self.assertNotIn("auth_user_id", kwargs)

    # Scopo: Stadio fuori whitelist -> E_VENDITE_VALIDATION.
    def test_attivita_stadio_invalido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_attivita(
                competenza_mese=date(2026, 5, 1), stadio="TRANSITATA"
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: La competenza viene normalizzata al 1° del mese.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_attivita", autospec=True,
        return_value=([], 0),
    )
    def test_attivita_competenza_normalizzata_al_primo(self, mock_repo):
        fn_dash_competenza_attivita(competenza_mese=date(2026, 5, 17))
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 5, 1))
        # Senza filtro stadio il repository riceve None (tutti gli stadi).
        self.assertIsNone(kwargs["stadio"])
        self.assertFalse(kwargs["solo_ritardo"])

    # Scopo: Il filtro recuperi tardivi viene inoltrato al repository.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_attivita", autospec=True,
        return_value=([], 0),
    )
    def test_attivita_solo_ritardo_passthrough(self, mock_repo):
        fn_dash_competenza_attivita(
            competenza_mese=date(2026, 5, 1), solo_ritardo=True
        )
        kwargs = mock_repo.call_args.kwargs
        self.assertTrue(kwargs["solo_ritardo"])

    # Scopo: la finestra arriva al repository come `limit`/`offset` (dal
    #        2026-10-21 un dialetto solo: la valida `pagina_da_query`, nella view).
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_attivita", autospec=True, return_value=([], 0))
    def test_attivita_page_invalida(self, mock_repo):
        fn_dash_competenza_attivita(competenza_mese=date(2026, 5, 1), limit=10, offset=30)
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (10, 30))

    # Scopo: order_by/order_dir (whitelist) inoltrati al repository per
    #        l'ordinamento server-side su tutte le pagine.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_attivita", autospec=True,
        return_value=([], 0),
    )
    def test_attivita_ordinamento_inoltrato(self, mock_repo):
        fn_dash_competenza_attivita(
            competenza_mese=date(2026, 5, 1),
            order_by="data_attivita",
            order_dir="asc",
        )
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "data_attivita")
        self.assertEqual(kwargs["order_dir"], "asc")

    # Scopo: order_by fuori whitelist -> E_VENDITE_VALIDATION (fail-fast 400).
    def test_attivita_order_by_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_attivita(
                competenza_mese=date(2026, 5, 1), order_by="quantita; DROP"
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: order_dir diverso da asc/desc -> E_VENDITE_VALIDATION.
    def test_attivita_order_dir_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_attivita(
                competenza_mese=date(2026, 5, 1),
                order_by="valore",
                order_dir="up",
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")


class DashCompetenzaCommesseServiceTests(TestCase):
    # Scopo: Envelope paginato con conteggio = n commesse; competenza al 1°,
    #        stadio/solo_ritardo/ordinamento inoltrati al repository.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_commesse", autospec=True,
        return_value=([{"commessa_id": 7, "n_attivita": 4}], 1),
    )
    def test_commesse_ok_envelope_e_passthrough(self, mock_repo):
        data = fn_dash_competenza_commesse(
            competenza_mese=date(2026, 5, 17),
            stadio="DA_EMETTERE",
            solo_ritardo=True,
            order_by="valore_tot",
            order_dir="desc",
        )
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"], [{"commessa_id": 7, "n_attivita": 4}])
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 5, 1))
        self.assertEqual(kwargs["stadio"], "DA_EMETTERE")
        self.assertTrue(kwargs["solo_ritardo"])
        self.assertEqual(kwargs["order_by"], "valore_tot")
        self.assertEqual(kwargs["order_dir"], "desc")
        self.assertNotIn("auth_user_id", kwargs)

    # Scopo: Stadio fuori whitelist -> E_VENDITE_VALIDATION.
    def test_commesse_stadio_invalido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_commesse(
                competenza_mese=date(2026, 5, 1), stadio="TRANSITATA"
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: order_by fuori dalla whitelist AGGREGATA -> E_VENDITE_VALIDATION.
    #        (le colonne di riga come data_attivita non sono ammesse qui).
    def test_commesse_order_by_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_commesse(
                competenza_mese=date(2026, 5, 1), order_by="data_attivita"
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: order_dir diverso da asc/desc -> E_VENDITE_VALIDATION.
    def test_commesse_order_dir_non_valido(self):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_commesse(
                competenza_mese=date(2026, 5, 1),
                order_by="n_attivita",
                order_dir="up",
            )
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: la finestra arriva al repository come `limit`/`offset` (dal
    #        2026-10-21 un dialetto solo: la valida `pagina_da_query`, nella view).
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_commesse", autospec=True, return_value=([], 0))
    def test_commesse_page_invalida(self, mock_repo):
        fn_dash_competenza_commesse(competenza_mese=date(2026, 5, 1), limit=10, offset=30)
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual((kwargs["limit"], kwargs["offset"]), (10, 30))


class DashCompetenzaErroriServiceTests(TestCase):
    # Scopo: Envelope paginato standard con i risultati del repository.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_errori", autospec=True,
        return_value=([{"tipo_evento": "TASK_ERRORE"}], 1),
    )
    def test_errori_ok_envelope_paginato(self, mock_repo):
        data = fn_dash_competenza_errori(competenza_mese=date(2026, 5, 1))
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"], [{"tipo_evento": "TASK_ERRORE"}])
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 5, 1))

    # Scopo: Senza competenza il repository riceve None (tutti i mesi).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_errori", autospec=True,
        return_value=([], 0),
    )
    def test_errori_competenza_opzionale_none(self, mock_repo):
        fn_dash_competenza_errori()
        kwargs = mock_repo.call_args.kwargs
        self.assertIsNone(kwargs["competenza_mese"])

    # Scopo: La competenza (se presente) viene normalizzata al 1° del mese.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_errori", autospec=True,
        return_value=([], 0),
    )
    def test_errori_competenza_normalizzata_al_primo(self, mock_repo):
        fn_dash_competenza_errori(competenza_mese=date(2026, 5, 17))
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["competenza_mese"], date(2026, 5, 1))

    # Scopo: order_by in whitelist → propagato al repository (8° lotto liste).
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_errori", autospec=True,
        return_value=([], 0),
    )
    def test_errori_order_by_propagato(self, mock_repo):
        fn_dash_competenza_errori(order_by="data_evento", order_dir="asc")
        kwargs = mock_repo.call_args.kwargs
        self.assertEqual(kwargs["order_by"], "data_evento")
        self.assertEqual(kwargs["order_dir"], "asc")

    # Scopo: order_by fuori whitelist → ServiceError 400, repo mai chiamato.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_errori", autospec=True,
        return_value=([], 0),
    )
    def test_errori_order_by_fuori_whitelist(self, mock_repo):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_errori(order_by="messaggio")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        mock_repo.assert_not_called()

    # Scopo: order_dir non asc/desc → ServiceError 400, repo mai chiamato.
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_errori", autospec=True,
        return_value=([], 0),
    )
    def test_errori_order_dir_invalido(self, mock_repo):
        with self.assertRaises(ServiceError) as ctx:
            fn_dash_competenza_errori(order_by="data_evento", order_dir="banana")
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")
        mock_repo.assert_not_called()


class DashCompetenzaGruppiServiceTests(TestCase):
    """Elenco GRUPPI FATTURABILI + filtro «tipo documento/sorgente».

    Il punto che questi test presidiano non e' l'envelope (banale) ma la
    DIFFERENZA di perimetro fra i tre blocchi della stessa risposta: le righe e
    i totali seguono il filtro, le voci del filtro no.
    """

    # Scopo: repository mockato con le DUE letture dell'endpoint — la lista e
    #        il suo contorno. Erano cinque fino al 2026-08-26: riepilogo e tre
    #        facet vivono ora in una query sola (vedi
    #        `get_dash_competenza_gruppi_accessori`).
    def _repo(self, mock_repo_cls):
        repo = mock_repo_cls.return_value
        repo.list_dash_competenza_gruppi.return_value = ([{"gruppo_key": "PREVENTIVO:a"}], 1)
        repo.get_dash_competenza_gruppi_accessori.return_value = {
            "riepilogo": {
                "n_gruppi": 1, "n_attivita": 3, "valore": "100.00",
                "n_gruppi_oneri": 0,
            },
            "tipi": [
                {"tipo_gruppo": "PREVENTIVO", "documento_apribile": True,
                 "n_gruppi": 1, "n_attivita": 3},
                {"tipo_gruppo": "ONERI_COMMESSA", "documento_apribile": None,
                 "n_gruppi": 2, "n_attivita": 2},
            ],
            "clienti": [],
            "registri": [],
            "n_gruppi_perimetro": 3,
        }
        return repo

    # 17) La risposta porta pagina + riepilogo + facet insieme: una seconda
    #     chiamata per i totali potrebbe raccontare un istante diverso.
    @patch.object(vendite_service, "VenditeRepository", autospec=True)
    def test_gruppi_envelope_con_riepilogo_e_facet(self, mock_repo_cls):
        self._repo(mock_repo_cls)
        out = fn_dash_competenza_gruppi(competenza_mese=date(2026, 6, 1))
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["riepilogo"]["n_attivita"], 3)
        self.assertEqual([t["tipo_gruppo"] for t in out["tipi"]],
                         ["PREVENTIVO", "ONERI_COMMESSA"])

    # 18) Il filtro tipo arriva SIA alla lista SIA ai totali: se arrivasse solo
    #     alla lista, la riga di totali descriverebbe un perimetro piu' largo
    #     delle righe che ha sopra — cioe' mentirebbe.
    @patch.object(vendite_service, "VenditeRepository", autospec=True)
    def test_gruppi_filtro_tipo_inoltrato_alla_lista_e_ai_totali(self, mock_repo_cls):
        repo = self._repo(mock_repo_cls)
        fn_dash_competenza_gruppi(
            competenza_mese=date(2026, 6, 1), tipo_gruppo="ONERI_COMMESSA",
        )
        self.assertEqual(
            repo.list_dash_competenza_gruppi.call_args.kwargs["tipo_gruppo"],
            "ONERI_COMMESSA",
        )
        self.assertEqual(
            repo.get_dash_competenza_gruppi_accessori.call_args.kwargs["tipo_gruppo"],
            "ONERI_COMMESSA",
        )

    # 19) ⚠️ QUESTO TEST HA CAMBIATO SEDE il 2026-08-26, e il perche' conta.
    #     Prima verificava che le facet NON ricevessero il filtro: era una
    #     proprieta' del SERVICE, che chiamava cinque metodi con argomenti
    #     diversi. Ora la chiamata e' una sola e riceve tutto — la distinzione
    #     fra i due perimetri e' scesa DENTRO la query (due CTE: `base` per le
    #     facet, `filtrato` per il riepilogo).
    #     Qui resta il pezzo che il service governa ancora: che il contorno
    #     riceva TUTTI i filtri, perche' senza il riepilogo non potrebbe
    #     riconciliare le righe. Il presidio della separazione vera sta in
    #     `test_due_perimetri_dentro_la_query`, sotto — dov'e' andata a stare
    #     la proprieta'.
    @patch.object(vendite_service, "VenditeRepository", autospec=True)
    def test_gruppi_contorno_riceve_tutti_i_filtri(self, mock_repo_cls):
        repo = self._repo(mock_repo_cls)
        fn_dash_competenza_gruppi(
            competenza_mese=date(2026, 6, 1), tipo_gruppo="PREVENTIVO",
            registro_id=4, search="ORD0005174",
        )
        kwargs = repo.get_dash_competenza_gruppi_accessori.call_args.kwargs
        self.assertEqual(kwargs["tipo_gruppo"], "PREVENTIVO")
        self.assertEqual(kwargs["registro_id"], 4)
        self.assertEqual(kwargs["search"], "ORD0005174")

    # 20) Stadio fuori vocabolario -> 400 (stessa whitelist delle altre liste).
    @patch.object(vendite_service, "VenditeRepository", autospec=True)
    def test_gruppi_stadio_invalido(self, mock_repo_cls):
        self._repo(mock_repo_cls)
        with self.assertRaises(ServiceError):
            fn_dash_competenza_gruppi(
                competenza_mese=date(2026, 6, 1), stadio="INVENTATO",
            )

    # 21) order_by fuori whitelist -> 400, mai un ordinamento silenziosamente
    #     ignorato (che renderebbe la paginazione non deterministica).
    @patch.object(vendite_service, "VenditeRepository", autospec=True)
    def test_gruppi_order_by_non_valido(self, mock_repo_cls):
        self._repo(mock_repo_cls)
        with self.assertRaises(ServiceError):
            fn_dash_competenza_gruppi(
                competenza_mese=date(2026, 6, 1), order_by="drop_table",
            )

    # 22) Competenza normalizzata al 1° del mese su ENTRAMBE le letture: una
    #     sola normalizzata e l'altra no darebbe una lista di un mese e un
    #     contorno di un altro.
    @patch.object(vendite_service, "VenditeRepository", autospec=True)
    def test_gruppi_competenza_normalizzata_al_primo(self, mock_repo_cls):
        repo = self._repo(mock_repo_cls)
        fn_dash_competenza_gruppi(competenza_mese=date(2026, 6, 23))
        atteso = date(2026, 6, 1)
        for chiamata in (
            repo.list_dash_competenza_gruppi,
            repo.get_dash_competenza_gruppi_accessori,
        ):
            self.assertEqual(chiamata.call_args.kwargs["competenza_mese"], atteso)

    # 22-bis) ⛔ IL PRESIDIO DEI DUE PERIMETRI, e ora vive QUI perche' e' qui
    #     che vive la proprieta': dentro il testo della query.
    #     · il RIEPILOGO legge `filtrato` — deve riconciliare le righe a video;
    #     · le TRE FACET e il conteggio di perimetro leggono `base` — devono
    #       mostrare tutte le voci anche quando una e' gia' scelta.
    #     Farle leggere tutte lo stesso insieme e' la scorciatoia ovvia e
    #     romperebbe le tendine IN SILENZIO: scelto «Preventivi», le altre voci
    #     sparirebbero e non si potrebbe piu' cambiare idea senza azzerare il
    #     filtro alla cieca. Nessun errore, nessun numero sbagliato: solo una
    #     tendina che smette di funzionare.
    @patch("apps.vendite.db.vendite_repository.connection")
    def test_due_perimetri_dentro_la_query(self, mock_conn):
        cursore = mock_conn.cursor.return_value.__enter__.return_value
        cursore.fetchone.return_value = ("{}", "[]", "[]", "[]", 0)
        VenditeRepository().get_dash_competenza_gruppi_accessori(
            competenza_mese=date(2026, 6, 1), stadio="DA_EMETTERE",
            tipo_gruppo="PREVENTIVO",
        )
        sql = cursore.execute.call_args[0][0]
        # Il perimetro filtrato si usa UNA volta sola, e in un punto solo.
        self.assertEqual(
            sql.count("FROM filtrato"), 1,
            "qualcuno oltre al riepilogo legge il perimetro filtrato: se sono "
            "le facet, le tendine smettono di far cambiare idea.",
        )
        testa, coda = sql.split("tipi AS (", 1)
        self.assertIn(
            "FROM filtrato", testa.split("riepilogo AS (", 1)[1],
            "il riepilogo non legge piu' il perimetro filtrato: i totali "
            "descriverebbero un perimetro diverso dalle righe che hanno sopra.",
        )
        self.assertNotIn(
            "filtrato", coda,
            "una facet (o il conteggio di perimetro) e' passata al perimetro "
            "filtrato.",
        )
        self.assertEqual(
            coda.count("FROM base"), 4,
            "le tre facet e il conteggio di perimetro devono leggere tutte e "
            "quattro il perimetro BASE.",
        )


class DashCompetenzaGruppiRepositoryTests(TestCase):
    """Risoluzione del DOCUMENTO del gruppo (repository, query mockata).

    Il gruppo fatturabile E' un documento sorgente, ma la vista ne espone solo
    l'uid e il codice: senza l'id il kebab della lista non puo' aprirne il
    drawer, che si apre per id. Questi due test presidiano la coppia
    «la query lo chiede» + «il mapping lo consegna»: separati di proposito,
    perche' si rompono per cause diverse (SELECT modificata vs indice di
    colonna sfasato da un inserimento a meta' proiezione).
    """

    # Scopo: righe finte con le 20 colonne della proiezione (rev 2026-08-15:
    # + commessa_emittibile, commessa_stato_codice_interno, stato_descrizione;
    # rev 2026-08-17: + ba_codice_fatturazione, id_fiscale — cliente di
    # fatturazione, brief-db-dash-competenza-gruppi §D-4;
    # rev 2026-08-18: + emittente_ragione_sociale — P-4 sulla lista PILOTA,
    # brief-db-perimetro-emittente passo 6 / BE-2).
    # ⚠️ La fixture deve avere ESATTAMENTE la forma della proiezione reale: una
    # riga finta piu' corta non fa fallire il mapping in modo parlante, lo fa
    # esplodere su un indice — e una piu' lunga lo farebbe passare leggendo la
    # colonna sbagliata, che e' il modo silenzioso di sbagliare.
    # ⚠️ La tupla deve avere la STESSA LARGHEZZA del SELECT del repository: il
    #     mapping legge per indice, e una riga corta fa `IndexError` mentre una
    #     lunga fa scorrere i valori sulle chiavi sbagliate — in silenzio.
    #     `test_larghezza_riga_finta_uguale_al_select` qui sotto lo verifica
    #     contro il SELECT vero invece di fidarsi di questo commento.
    def _rows(self, documento_id, *, emittibile=True,
              stato="PRONTA_FATTURAZIONE", stato_descr="Pronta fatturazione",
              ba_codice="BA-0001", id_fiscale="12345678901",
              emittente="Tito Srl",
              registri_n=1, registro_codice="Front-office",
              data_prevista=date(2026, 8, 31),
              ultimo_esito=None, ultimo_errore_codice=None,
              ultimo_errore_messaggio=None, ultimo_errore_quando=None,
              ultimo_lotto_codice=None,
              blocco_reason=None, blocco_reason_key=None,
              blocco_lotto_id=None, blocco_lotto_codice=None,
              ultimo_lotto_id=None, ultimo_lotto_stato=None,
              ultimo_lotto_pre_fiscale=None):
        return [(
            "ORDINE_VENDITA:uid-1", "ORDINE_VENDITA", True, "ORD0005174",
            4277, "CMM-2026…", "Rossi SRL", "DA_EMETTERE", 3, Decimal("731.00"),
            False, date(2026, 8, 3), date(2026, 8, 3), documento_id,
            emittibile, stato, stato_descr, ba_codice, id_fiscale, emittente,
            registri_n, registro_codice, data_prevista,
            # ⭐ L'esito dell'ULTIMO tentativo (rev 2026-09-06, changeSet DB
            # `20260906-12` — brief-db-esito-gruppo-lotto R-3). I default sono
            # tutti `None` e NON e' pigrizia: e' la forma che il database
            # produce su ogni gruppo che nessun giro ha ancora lavorato, cioe'
            # il caso normale. Chi prova il ramo «e' fallito» lo chiede.
            ultimo_esito, ultimo_errore_codice, ultimo_errore_messaggio,
            ultimo_errore_quando, ultimo_lotto_codice,
            # ⭐ Il VERDETTO «trattenuto da un lotto vivo» (changeSet DB
            # `20260909-24`). Default `None` = la riga si puo' prendere, che e'
            # il caso normale.
            # ⛔ E' un verdetto, non materia da dedurre: `ultimo_esito` qui
            # sopra NON risponde alla stessa domanda — su un lotto ANNULLATO
            # vale `COMPLETED` e il documento e' LIBERO.
            blocco_reason, blocco_reason_key, blocco_lotto_id, blocco_lotto_codice,
            # ⭐ V-1 (`20260909-66`): il lotto del TENTATIVO esce col suo STATO,
            # non col solo codice — a video un tentativo dentro un lotto
            # ANNULLATO si leggeva come uno ancora in corso.
            # ⛔ `ultimo_lotto_id` NON e' `blocco_lotto_id` qui sopra: quello e'
            # il lotto che TRATTIENE adesso, questo e' l'ultimo che ci ha
            # provato — su un lotto annullato il secondo c'e' e il primo no.
            # I default `None` sono la forma che il database produce su un
            # gruppo che nessun giro ha ancora lavorato, cioe' il caso normale.
            ultimo_lotto_id, ultimo_lotto_stato, ultimo_lotto_pre_fiscale,
        )]

    # 24-novies) 🟢 IL VERDETTO «TRATTENUTO DA UN LOTTO VIVO» arriva dalla vista
    #     e il mapping lo consegna intero, bersaglio compreso
    #     (brief-db-documento-trattenuto-da-un-lotto-vivo, changeSet
    #     `20260909-24`).
    # ⛔ E si presidia che NON venga dedotto da `ultimo_esito`: qui la riga ha
    #     `ultimo_esito = COMPLETED` — che su un lotto annullato significa
    #     LIBERO — e insieme il verdetto di blocco. Sono due domande diverse, e
    #     un mapping che le confondesse passerebbe questo test solo per caso.
    # ⚠️ Il `lotto_id` viaggia perche' il frontend ci disegna un GESTO: senza,
    #     l'operatore ricopia un codice e poi lo cerca a mano.
    @patch.object(VenditeRepository, "_applica_bandiera_respinta", autospec=True)
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_mapping_espone_il_blocco_di_emissione_col_bersaglio(
        self, mock_query, _band,
    ):
        mock_query.return_value = (
            self._rows(
                99, ultimo_esito="COMPLETED",
                blocco_reason="TRATTENUTO_DA_LOTTO",
                blocco_reason_key="vendite.emissione.blocco_reason.trattenuto_da_lotto",
                blocco_lotto_id=11764, blocco_lotto_codice="LTF-0010331",
            ),
            1,
        )
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 9, 1), stadio="DA_EMETTERE", limit=10, offset=0,
        )
        self.assertEqual(righe[0]["emissione_blocco_reason"], "TRATTENUTO_DA_LOTTO")
        self.assertEqual(
            righe[0]["emissione_blocco_reason_key"],
            "vendite.emissione.blocco_reason.trattenuto_da_lotto",
        )
        self.assertEqual(righe[0]["emissione_blocco_lotto_id"], 11764)
        self.assertEqual(righe[0]["emissione_blocco_lotto_codice"], "LTF-0010331")

    # 24-novies-bis) ⚠️ E senza blocco resta `None` su tutti e quattro: la riga
    #     si puo' prendere. Uno zero o una stringa vuota direbbero un'altra cosa.
    @patch.object(VenditeRepository, "_applica_bandiera_respinta", autospec=True)
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_senza_blocco_di_emissione_i_quattro_campi_restano_none(
        self, mock_query, _band,
    ):
        mock_query.return_value = (self._rows(99), 1)
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 9, 1), stadio="DA_EMETTERE", limit=10, offset=0,
        )
        for campo in ("emissione_blocco_reason", "emissione_blocco_reason_key",
                      "emissione_blocco_lotto_id", "emissione_blocco_lotto_codice"):
            self.assertIsNone(righe[0][campo], campo)

    # 24-decies) 🟢 L'ESITO DELL'ULTIMO TENTATIVO arriva dalla VISTA e il
    #     mapping lo consegna (brief-db-esito-gruppo-lotto R-3, changeSet DB
    #     `20260906-12`). ⭐ Il caso vero e' il documento che il lotto ha preso
    #     in carico e NON e' riuscito a fatturare: restava fra quelli da
    #     emettere senza un segno, quindi sembrava fatturabile.
    #     ⛔ Il test verifica anche cio' che NON deve cambiare: `stadio` e
    #     `commessa_emittibile` restano quelli di prima (decisione di Tid). Il
    #     segno dice «ci ho provato», non «non si puo' fare» — e la riga deve
    #     restare fatturabile, o il rimedio (correggi e riprova) sarebbe
    #     impossibile proprio dove serve.
    @patch.object(VenditeRepository, "_applica_bandiera_respinta", autospec=True)
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_mapping_espone_l_esito_dell_ultimo_tentativo(self, mock_query, _band):
        mock_query.return_value = (self._rows(
            5387,
            ultimo_esito="ERRORE",
            ultimo_errore_codice="E_PULL_COMMESSA",
            ultimo_errore_messaggio="ROOT source mancante per commessa 34137",
            ultimo_errore_quando=datetime(2026, 9, 6, 17, 12, tzinfo=UTC),
            ultimo_lotto_codice="LTF-0009578",
        ), 1)
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 9, 1), stadio=None, limit=25, offset=0,
        )
        self.assertEqual(righe[0]["ultimo_esito"], "ERRORE")
        self.assertEqual(righe[0]["ultimo_errore_codice"], "E_PULL_COMMESSA")
        self.assertEqual(
            righe[0]["ultimo_errore_messaggio"],
            "ROOT source mancante per commessa 34137",
        )
        # ISO, come ogni altro timestamp del payload.
        self.assertTrue(righe[0]["ultimo_errore_quando"].startswith("2026-09-06T17:12"))
        self.assertEqual(righe[0]["ultimo_lotto_codice"], "LTF-0009578")
        # ⛔ Il segno NON spegne la riga.
        self.assertEqual(righe[0]["stadio"], "DA_EMETTERE")
        self.assertTrue(righe[0]["commessa_emittibile"])

    # 24-undecies) ⚠️ `None` NON diventa una stringa, e non e' un dettaglio: e' la
    #     verita' di ogni gruppo che nessun giro ha ancora lavorato — «nessuno
    #     l'ha detto», che il frontend deve poter distinguere da «e' andata
    #     bene». Un `"None"` a video sarebbe un esito inventato.
    @patch.object(VenditeRepository, "_applica_bandiera_respinta", autospec=True)
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_esito_assente_resta_none(self, mock_query, _band):
        mock_query.return_value = (self._rows(5387), 1)
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 9, 1), stadio=None, limit=25, offset=0,
        )
        for chiave in (
            "ultimo_esito", "ultimo_errore_codice", "ultimo_errore_messaggio",
            "ultimo_errore_quando", "ultimo_lotto_codice",
        ):
            self.assertIsNone(righe[0][chiave], chiave)

    # 24-septies) La riga finta e il SELECT vero devono avere la STESSA
    #     larghezza. E' il presidio del presidio: tutti i test di mapping di
    #     questa classe girano su `_rows`, quindi una tupla rimasta indietro non
    #     li fa fallire — li fa passare su una forma che il database non
    #     produce. Il conteggio si legge dal SELECT, non si scrive qui.
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_larghezza_riga_finta_uguale_al_select(self, mock_query):
        mock_query.return_value = (self._rows(5387), 1)
        VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        sql = mock_query.call_args.kwargs["select_sql"]
        proiezione = sql.split("FROM vendite.vw_dash_competenza_gruppi")[0]
        # Per RIGA e non per virgola: la prima colonna sta sulla stessa riga
        # di `SELECT` e uno split sulle virgole la perderebbe — facendo contare
        # 22 dove il SELECT ne ha 23, cioe' fallire il presidio nel momento in
        # cui e' corretto.
        colonne = [
            r for r in (x.strip() for x in proiezione.splitlines())
            if r.startswith("g.")
        ]
        self.assertEqual(
            len(colonne), len(self._rows(1)[0]),
            "la tupla di `_rows` non ha piu' la larghezza del SELECT: i test di "
            "mapping di questa classe stanno girando su una forma che il "
            "database non produce.",
        )

    # 23) 🟢 L'id del documento viene dalla VISTA, non piu' da una LATERAL
    #     scritta qui (DB `20260815-25`). Era una SECONDA risoluzione della
    #     stessa regola — il commento la dichiarava «drift noto e accettato» —
    #     e id e codice potevano descrivere documenti diversi. Il test ora
    #     presidia il verso opposto: che quella risoluzione NON torni.
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_id_documento_dalla_vista_non_da_una_seconda_risoluzione(self, mock_query):
        mock_query.return_value = (self._rows(5387), 1)
        VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio="DA_EMETTERE",
            limit=25, offset=0,
        )
        sql = mock_query.call_args.kwargs["select_sql"]
        self.assertIn("g.documento_id", sql)
        self.assertNotIn("vw_dash_fatturazione_documenti", sql)
        self.assertNotIn("LATERAL", sql)

    # 24) Il mapping consegna l'id al FE. Il caso NULL non e' un dettaglio: i
    #     gruppi SOURCELESS (oneri di commessa) non hanno documento, e il FE
    #     deve poter nascondere l'azione invece di aprire un drawer vuoto.
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_mapping_espone_documento_id_e_ne_preserva_il_null(self, mock_query):
        mock_query.return_value = (self._rows(5387), 1)
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        self.assertEqual(righe[0]["documento_id"], 5387)

        mock_query.return_value = (self._rows(None), 1)
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        self.assertIsNone(righe[0]["documento_id"])

    # 24-octies) `riferimento` arriva al FE, e arriva NON nullo. E' il gemello
    #     del test 24: quello presidia il NULL che deve SOPRAVVIVERE, questo il
    #     valore che non deve mai esserlo.
    #     ⚠️ Serve perche' il mapping legge per INDICE: un riordino del SELECT
    #     farebbe scorrere i valori sulle chiavi sbagliate senza rompere niente,
    #     e la larghezza (24-septies) resterebbe giusta.
    #     ⛔ Il campo e' dichiarato `str`, non `str | None`: il ripiego
    #     `COALESCE(numero documento, codice commessa, gruppo_key)` lo fa GIA' la
    #     vista, e l'ultimo ramo e' la chiave del gruppo — riscrivere quella
    #     catena nel repository o nel frontend sarebbe la stessa regola in due
    #     posti (brief-db-riferimento-gruppi-lateral-costosa §9).
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_mapping_espone_riferimento_non_nullo(self, mock_query):
        mock_query.return_value = (self._rows(5387), 1)
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        self.assertEqual(righe[0]["riferimento"], "ORD0005174")

    # 24-bis) L'emittibilita' della TESTATA arriva al FE (brief emittibilita' §3.1,
    #     rev 2026-08-15): e' il dato che la vista espone da giugno e che
    #     nessuno leggeva — l'operatore vedeva lavoro promesso e scopriva il
    #     blocco solo cliccando. Col PERCHE' accanto (stato commessa), non solo
    #     il CHE: «segnalare, non nascondere» pretende il motivo.
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_mapping_espone_emittibilita_testata_col_motivo(self, mock_query):
        mock_query.return_value = (
            self._rows(5387, emittibile=False, stato="BOZZA", stato_descr="Bozza"), 1,
        )
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        self.assertIs(righe[0]["commessa_emittibile"], False)
        self.assertEqual(righe[0]["commessa_stato_codice_interno"], "BOZZA")
        # A video va la DESCRIZIONE, e dal 2026-08-15 la porta la VISTA
        # (DB `20260815-24`/`-25`): il `LEFT JOIN vendite.stati_commessa` che
        # stava qui era una seconda copia della stessa decodifica.
        self.assertEqual(righe[0]["commessa_stato_descrizione"], "Bozza")
        sql = mock_query.call_args.kwargs["select_sql"]
        self.assertIn("g.commessa_emittibile", sql)
        self.assertIn("g.commessa_stato_codice_interno", sql)
        self.assertIn("g.commessa_stato_descrizione", sql)
        self.assertNotIn("stati_commessa", sql)

    # 24-ter) Il cliente di FATTURAZIONE arriva al FE (D-4). ⚠️ Il caso NULL non
    #     e' un dettaglio ne' un errore: e' il gruppo il cui BA padre sta fuori
    #     dallo scope dell'operatore, che resta in lista e finisce nella voce
    #     «cliente non determinabile» (D-5). Coercerlo a stringa vuota lo
    #     renderebbe indistinguibile da un codice mancante a monte.
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_mapping_espone_cliente_di_fatturazione_e_ne_preserva_il_null(self, mock_query):
        mock_query.return_value = (self._rows(5387), 1)
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        self.assertEqual(righe[0]["ba_codice_fatturazione"], "BA-0001")
        self.assertEqual(righe[0]["id_fiscale"], "12345678901")

        mock_query.return_value = (
            self._rows(5387, ba_codice=None, id_fiscale=None), 1,
        )
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        self.assertIsNone(righe[0]["ba_codice_fatturazione"])
        self.assertIsNone(righe[0]["id_fiscale"])

        sql = mock_query.call_args.kwargs["select_sql"]
        self.assertIn("g.ba_codice_fatturazione", sql)
        self.assertIn("g.id_fiscale", sql)

    # 24-quinquies) L'EMITTENTE della riga arriva al FE (P-4, brief
    #     perimetro-emittente passo 6). Questa e' la lista PILOTA del giro: il
    #     DB ha fatto la sua meta' il 2026-08-18 (vista + riga di catalogo), e
    #     senza questa colonna nel SELECT la colonna spuntata resterebbe VUOTA
    #     — cioe' SEMBREREBBE la garanzia che il flag `multi_emittente`
    #     pretende, senza esserlo.
    # ⚠️ Si asserisce la RAGIONE SOCIALE e si nega l'id: la vista espone anche
    #     `emittente_soggetto_ruolo_id`, e portarlo a video sposterebbe
    #     l'ambiguita' di un passo invece di toglierla (§11.4).
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_mapping_espone_emittente_ragione_sociale(self, mock_query):
        mock_query.return_value = (self._rows(5387), 1)
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        self.assertEqual(righe[0]["emittente_ragione_sociale"], "Tito Srl")

        mock_query.return_value = (self._rows(5387, emittente=None), 1)
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        self.assertIsNone(righe[0]["emittente_ragione_sociale"])

        sql = mock_query.call_args.kwargs["select_sql"]
        self.assertIn("g.emittente_ragione_sociale", sql)
        # ⚠️ La negazione va cercata nella sola PROIEZIONE, non in tutto lo
        # `select_sql`: quella stringa contiene anche la `WHERE`, e un filtro
        # legittimo per emittente (che un giorno potrebbe servire) renderebbe
        # rosso un test che parla di cosa arriva A VIDEO. Un presidio che
        # vieta piu' di quel che intende viene disattivato al primo falso
        # positivo.
        proiezione = sql.split("FROM vendite.vw_dash_competenza_gruppi")[0]
        self.assertNotIn("emittente_soggetto_ruolo_id", proiezione)

    # 24-sexies) OGNI `campo_sorgente` del catalogo deve essere una chiave della
    #     riga che il repository consegna. La lista ha `vista_sql = NULL`,
    #     quindi il catalogo non puo' pescare i campi da se': li compone questo
    #     repository, e se le due parti divergono la colonna si spunta e resta
    #     VUOTA — senza che nessun errore lo dica.
    #
    # ⚠️ Il `campo_sorgente` si LEGGE DAL CSV, non si scrive qui. Una prima
    #     versione di questo test asseriva la stringa `"emittente_ragione_sociale"`
    #     a mano: si chiamava «allineata al campo_sorgente di catalogo» e il
    #     catalogo non lo apriva nemmeno — sarebbe rimasta verde proprio nel
    #     caso che dichiarava di presidiare (il seed che cambia nome al campo).
    #
    # ⚠️ Vale per TUTTE le colonne, non per l'ultima arrivata: e' il contratto
    #     del building block `<ListaConfigurabile>` su questa lista. Le colonne
    #     `tipo_colonna = 'azione'` sono fuori perche' un campo sorgente non ce
    #     l'hanno (lo dichiara gia' `test_colonna_azione_mai_ordinabile` del
    #     presidio trasversale).
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_ogni_campo_sorgente_di_catalogo_e_una_chiave_della_riga(self, mock_query):
        # Import locale: lega questo test al presidio trasversale invece di
        # riscrivere la lettura del CSV (che li' e' gia' scritta, con la
        # ricerca della root del repo che non conta i livelli a mano).
        from apps.core.tests.test_liste_configurabili_seed import _colonne_attive

        attese = sorted(
            r["campo_sorgente"]
            for r in _colonne_attive("vendite.dash_competenza_gruppi")
            if r["tipo_colonna"] != "azione" and r["campo_sorgente"]
        )
        self.assertIn(
            "emittente_ragione_sociale", attese,
            "il catalogo non dichiara piu' la colonna emittente: se e' voluto "
            "va tolta anche dal SELECT del repository (P-4, passo 6).",
        )

        mock_query.return_value = (self._rows(5387), 1)
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        mancanti = [c for c in attese if c not in righe[0]]
        self.assertEqual(
            mancanti, [],
            "campi dichiarati a catalogo che il repository non consegna: la "
            "colonna si spunta e resta vuota a video.",
        )

    # 24-quater) Il filtro cliente e la ricerca vivono in `_where_gruppi`, cioe'
    #     nel predicato CONDIVISO da lista e riepilogo: e' cio' che impedisce ai
    #     totali di descrivere un perimetro diverso dalle righe sopra di se'.
    #     ⚠️ «non determinabile» e' un IS NULL, non un id sentinella, e VINCE
    #     sull'id: sono alternativi, non sommabili.
    def test_where_gruppi_filtro_cliente_e_ricerca(self) -> None:
        cond, params = VenditeRepository._where_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, ba_fatturazione_id=77,
        )
        self.assertIn("g.ba_fatturazione_id = %s", cond)
        self.assertIn(77, params)

        cond, params = VenditeRepository._where_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None,
            ba_fatturazione_id=77, ba_non_determinabile=True,
        )
        self.assertIn("g.ba_fatturazione_id IS NULL", cond)
        self.assertNotIn(77, params)

        # Sotto soglia: ignorata, non solleva e non svuota la lista — e le
        # colonne del catalogo non si leggono nemmeno (si legge solo la soglia).
        # ⭐ Dal 2026-09-24 la ricerca passa dal BB `add_ricerca_full_condition`:
        #    le colonne le decide il catalogo, qui mockato con le cinque accese.
        with catalogo_ricerca_finto(_GRUPPI_ACCESE) as (lettura, _):
            cond, _ = VenditeRepository._where_gruppi(
                competenza_mese=date(2026, 8, 1), stadio=None, search="OR",
            )
            self.assertTrue(all("ILIKE" not in c for c in cond))
            lettura.assert_not_called()

            cond, params = VenditeRepository._where_gruppi(
                competenza_mese=date(2026, 8, 1), stadio=None, search="ORD0005174",
            )
        ramo = [c for c in cond if "ILIKE" in c]
        self.assertEqual(len(ramo), 1)
        # ⚠️ Un solo gruppo parentesizzato: senza le parentesi l'OR si legherebbe
        # all'ultima AND e il filtro mese/stadio smetterebbe di valere per i rami
        # successivi — una ricerca che ALLARGA il perimetro invece di stringerlo.
        self.assertTrue(ramo[0].startswith("(") and ramo[0].endswith(")"))
        self.assertEqual(ramo[0].count("ILIKE"), 5)
        self.assertEqual(params.count("%ORD0005174%"), 5)

    # 24-quater-bis) Il contorno (riepilogo + facet) filtra un perimetro GIA'
    #     letto, quindi deve sapere quali colonne portarsi dietro: con la
    #     ricerca attiva quelle della dichiarazione, senza ricerca nessuna. E una
    #     colonna che il catalogo spegne esce dalla condizione (non dalla CTE).
    def test_filtri_gruppi_colonne_della_ricerca(self) -> None:
        with catalogo_ricerca_finto(_GRUPPI_ACCESE):
            _, _, colonne = VenditeRepository._where_gruppi_filtri(search="OR")
            self.assertEqual(colonne, [])
            _, _, colonne = VenditeRepository._where_gruppi_filtri(search="ORD0005174")
            self.assertEqual(set(colonne), {f"g.{c}" for c in _GRUPPI_ACCESE})
        with catalogo_ricerca_finto(["riferimento"]):
            cond, params, _ = VenditeRepository._where_gruppi_filtri(search="ORD0005174")
        self.assertEqual(cond, ["((g.riferimento)::text ILIKE %s)"])
        self.assertEqual(params, ["%ORD0005174%"])

    # ═══ IL SEZIONALE PREVISTO (brief-db-registro-e-data-prevista) ═══════════

    # 25) ⛔ Il filtro sezionale lavora sull'INSIEME dei sezionali del gruppo,
    #     non sul codice unico. E' la decisione portante: un gruppo che tocca
    #     due sezionali ha `registro_codice` NULL, quindi un filtro sul codice
    #     lo farebbe sparire da ENTRAMBE le voci — cioe' proprio dal gruppo che
    #     l'operatore sta cercando.
    def test_filtro_registro_usa_l_insieme_non_il_codice(self) -> None:
        cond, params = VenditeRepository._where_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, registro_id=4,
        )
        self.assertIn("%s = ANY(g.registri_ids)", cond)
        self.assertIn(4, params)
        self.assertTrue(
            all("registro_codice" not in c for c in cond),
            "il filtro si e' appoggiato al codice: i gruppi multi-sezionale "
            "sparirebbero da tutte le voci.",
        )

    # 26) «Non risolvibile» e' l'ASSENZA del valore e VINCE sull'id, come la
    #     coppia gemella del cliente: sono alternativi, non sommabili.
    #     ⚠️ E non si scrive `cardinality(...) = 0`: `array_agg(DISTINCT)`
    #     conserva i NULL, quindi un gruppo interamente non risolvibile ha
    #     `{NULL}` — cardinalita' 1 — e con quel predicato non lo troverebbe
    #     nessuno.
    def test_filtro_registro_non_risolvibile_vince_e_non_conta_la_cardinalita(self) -> None:
        cond, params = VenditeRepository._where_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None,
            registro_id=4, registro_non_risolvibile=True,
        )
        ramo = [c for c in cond if "registri_ids" in c]
        self.assertEqual(len(ramo), 1)
        self.assertIn("IS NOT NULL", ramo[0])
        self.assertNotIn(4, params)
        self.assertTrue(
            all("cardinality" not in c for c in cond),
            "predicato sulla cardinalita': un gruppo `{NULL}` la conta 1 e "
            "resterebbe invisibile alla voce che lo riguarda.",
        )

    # 27) La frase «piu' sezionali» si accende sul CONTEGGIO, non sul NULL del
    #     codice. Quel NULL ha due significati — piu' di uno, oppure nessuno
    #     risolvibile — e confonderli direbbe «sono piu' di uno» a un gruppo che
    #     di sezionali non ne ha nemmeno uno.
    def test_etichetta_multi_registro_distingue_i_due_null(self) -> None:
        from apps.vendite.services.vendite_service import _marca_gruppi_multi_registro

        righe = [
            {"registri_n": 2, "registro_codice": None},   # piu' sezionali
            {"registri_n": 1, "registro_codice": None},   # non risolvibile
            {"registri_n": 0, "registro_codice": None},   # nessuno
            {"registri_n": 1, "registro_codice": "VX1"},  # normale
        ]
        _marca_gruppi_multi_registro(righe)
        self.assertIn("2", str(righe[0]["registro_codice"]))
        self.assertIsNone(righe[1]["registro_codice"])
        self.assertIsNone(righe[2]["registro_codice"])
        self.assertEqual(righe[3]["registro_codice"], "VX1")

    # 28) Il mapping consegna le due colonne con le chiavi che il catalogo
    #     dichiara, e la data come stringa ISO (il FE la formatta, il BE non
    #     inventa un formato — memoria locale_formatters).
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_mapping_sezionale_e_data_prevista(self, mock_query):
        mock_query.return_value = (self._rows(5387), 1)
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        self.assertEqual(righe[0]["registro_codice"], "Front-office")
        self.assertEqual(righe[0]["data_documento_prevista"], "2026-08-31")
        self.assertEqual(righe[0]["registri_n"], 1)

        mock_query.return_value = (
            self._rows(5387, registro_codice=None, data_prevista=None), 1,
        )
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        self.assertIsNone(righe[0]["registro_codice"])
        self.assertIsNone(righe[0]["data_documento_prevista"])

    # 29-bis) ⭐ I due numeri restano DUE fino al payload. Il riepilogo segue i
    #     filtri (32), il totale della tendina no (39): se il service li
    #     collassasse — o ne sovrascrivesse uno con l'altro passando dal
    #     `payload.update` — la voce «Tutti i sezionali» direbbe 32 di
    #     un'opzione che, premuta, ne mostra 39.
    #     ⚠️ Che i due numeri NASCANO da perimetri diversi lo presidia
    #     `test_due_perimetri_dentro_la_query`, dove sta la query. Qui si
    #     verifica solo che il service non li confonda per strada.
    @patch.object(vendite_service, "VenditeRepository", autospec=True)
    def test_riepilogo_e_totale_perimetro_restano_due_numeri(self, mock_repo_cls):
        repo = mock_repo_cls.return_value
        repo.list_dash_competenza_gruppi.return_value = ([], 0)
        repo.get_dash_competenza_gruppi_accessori.return_value = {
            "riepilogo": {
                "n_gruppi": 32, "n_attivita": 0, "valore": "0", "n_gruppi_oneri": 0,
            },
            "tipi": [], "clienti": [], "registri": [],
            "n_gruppi_perimetro": 39,
        }
        payload = fn_dash_competenza_gruppi(
            competenza_mese=date(2026, 6, 1), stadio="DA_EMETTERE", registro_id=4,
        )
        self.assertEqual(payload["riepilogo"]["n_gruppi"], 32)
        self.assertEqual(payload["n_gruppi_perimetro"], 39)

    # 29) ⛔ La lista degli id NON esce nel payload: se un giorno ci rientrasse,
    #     andrebbe deciso cosa farne dei NULL che `array_agg(DISTINCT)`
    #     conserva — e due numeri che rispondono «quanti sezionali» in modo
    #     diverso sono peggio di uno solo.
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_registri_ids_non_esce_nel_payload(self, mock_query):
        mock_query.return_value = (self._rows(5387), 1)
        righe, _ = VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 8, 1), stadio=None, limit=25, offset=0,
        )
        self.assertNotIn("registri_ids", righe[0])


class DashCompetenzaRespintaEErroriRepositoryTests(TestCase):
    """D3 · le commesse respinte arrivano fino alla riga.

    Due superfici, due presidi. Sulla lista GRUPPI la bandiera arriva da una
    LATERAL su `vw_dash_commesse_respinte`; sulla lista ERRORI arrivano
    l'elenco delle commesse respinte e il loro numero, in coda alle colonne
    esistenti.

    ⛔ Entrambe le liste mappano per INDICE. Il modo in cui si rompono non e'
    un'eccezione: e' una data nel campo del task e un messaggio in quello della
    data, senza nessun errore. Per questo i test guardano la LARGHEZZA oltre ai
    valori.
    """

    # Scopo: la bandiera si accende SOLO sulle commesse respinte, e le altre
    #        righe restano pulite. Il caso NULL e' la stragrande maggioranza:
    #        una bandiera che si accende ovunque non e' una bandiera.
    @patch("apps.vendite.db.vendite_repository.connection")
    def test_la_bandiera_si_accende_solo_su_chi_e_stato_respinto(self, mock_conn):
        cursor = mock_conn.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            (34137, datetime(2026, 9, 4, 17, 32, 38, tzinfo=UTC),
             "ROOT source mancante per commessa 34137"),
        ]
        righe = [
            {"commessa_id": 34136, "respinta_il": None, "respinta_motivo": None},
            {"commessa_id": 34137, "respinta_il": None, "respinta_motivo": None},
            {"commessa_id": None, "respinta_il": None, "respinta_motivo": None},
        ]
        VenditeRepository()._applica_bandiera_respinta(
            righe, competenza_mese=date(2026, 9, 1),
        )
        self.assertIsNone(righe[0]["respinta_il"])
        self.assertTrue(righe[1]["respinta_il"].startswith("2026-09-04"))
        self.assertEqual(
            righe[1]["respinta_motivo"], "ROOT source mancante per commessa 34137"
        )
        self.assertIsNone(righe[2]["respinta_il"])

    # Scopo: ⛔ IL PRESIDIO DI COSTO. La forma ovvia — una LATERAL nella
    #        proiezione — si valuta su TUTTO il perimetro del mese e non sulla
    #        pagina, perche' `query_paged_view` materializza la CTE per contare
    #        il totale. Misurato il 2026-09-04 su `2026-06` (48 gruppi): 27 ms
    #        senza, 1073 ms con. Questo test dice che la lettura resta UNA,
    #        fuori dal SELECT paginato e ristretta agli id della pagina.
    @patch.object(VenditeRepository, "_applica_bandiera_respinta", autospec=True)
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_la_bandiera_non_entra_nel_select_paginato(self, mock_query, _mock_band):
        mock_query.return_value = (DashCompetenzaGruppiRepositoryTests()._rows(1), 1)
        VenditeRepository().list_dash_competenza_gruppi(
            competenza_mese=date(2026, 9, 1), stadio=None, limit=25, offset=0,
        )
        sql = mock_query.call_args.kwargs["select_sql"]
        self.assertNotIn("vw_dash_commesse_respinte", sql)

    # Scopo: la lettura e' ristretta al MESE della riga e prende l'ULTIMO
    #        rifiuto. Senza il mese, un rifiuto di agosto accenderebbe la
    #        bandiera su una riga di settembre; senza il collasso, una commessa
    #        respinta due volte porterebbe due righe e vincerebbe quella
    #        arrivata per ultima nel dizionario — cioe' il caso.
    @patch("apps.vendite.db.vendite_repository.connection")
    def test_la_bandiera_e_legata_al_mese_e_prende_l_ultimo_rifiuto(self, mock_conn):
        cursor = mock_conn.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = []
        VenditeRepository()._applica_bandiera_respinta(
            [{"commessa_id": 34137, "respinta_il": None, "respinta_motivo": None}],
            competenza_mese=date(2026, 9, 1),
        )
        sql, params = cursor.execute.call_args.args
        self.assertIn("DISTINCT ON (commessa_id)", sql)
        self.assertIn("ORDER BY commessa_id, respinta_il DESC", sql)
        self.assertIn("competenza_mese = %s", sql)
        self.assertEqual(params[0], date(2026, 9, 1))
        self.assertEqual(params[1], [34137])

    # Scopo: nessuna commessa nella pagina = nessuna interrogazione. Un giro a
    #        vuoto su `= ANY('{}')` costerebbe una lettura per non trovare mai
    #        niente — e le liste dei cruscotti si pagano a query.
    @patch("apps.vendite.db.vendite_repository.connection")
    def test_la_bandiera_non_interroga_il_db_senza_commesse(self, mock_conn):
        VenditeRepository()._applica_bandiera_respinta(
            [{"commessa_id": None, "respinta_il": None, "respinta_motivo": None}],
            competenza_mese=date(2026, 9, 1),
        )
        mock_conn.cursor.assert_not_called()

    # Scopo: le due colonne nuove della lista errori arrivano in fondo e sono
    #        mappate. ⛔ IN FONDO e' il contratto: infilarle in mezzo
    #        sposterebbe di una casella tutto cio' che segue, in silenzio.
    # ⚠️ Riga finta UNICA per i due test qui sotto: la sua larghezza e' cio' che
    #    `test_larghezza_riga_errori_uguale_al_select` confronta col SELECT
    #    vero. Scriverla due volte, o scrivere il numero a mano, rimetterebbe in
    #    piedi proprio la doppia verita' che il presidio esiste per togliere.
    def _riga_errore(self):
        return (
            "TASK_ERRORE", date(2026, 9, 1), 10141, "LTF-0009181", "ERRORE",
            None, None, None, None, None,
            "pull_attivita_da_commessa", "E_PULL_COMMESSA",
            "Pull attivita' completato con 1 commesse su 3 in errore",
            datetime(2026, 9, 4, 17, 32, 38, tzinfo=UTC),
            "Gestore Test pgTAP",
            # 🔴 STRINGA, non lista: e' la forma che il driver consegna
            #    davvero (psycopg 3 in questa configurazione non decodifica il
            #    jsonb fuori dall'ORM). Un finto che passasse gia' una lista
            #    farebbe passare il test per una ragione diversa da quella per
            #    cui passa il sistema — ed e' esattamente cosi' che, il
            #    2026-09-04, la suite era verde mentre l'endpoint restituiva
            #    una stringa al posto dell'array.
            '[{"commessa_id": 34137, "commessa_codice": "CMM-…-004", '
            '"error_code": "E_PULL_COMMESSA", '
            '"messaggio": "Errore emissione commessa 34137", '
            '"dettaglio": "ROOT source mancante per commessa 34137"}]',
            1,
        )

    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_errori_mappano_le_commesse_respinte_in_coda(self, mock_query):
        mock_query.return_value = ([self._riga_errore()], 1)
        righe, _ = VenditeRepository().list_dash_competenza_errori(
            competenza_mese=date(2026, 9, 1), limit=25, offset=0,
        )
        self.assertEqual(righe[0]["n_commesse_fallite"], 1)
        # ⛔ Una LISTA, non la stringa che il driver ha consegnato: e' il campo
        #    su cui il frontend cicla. Senza decodifica non ci sarebbe nessun
        #    errore — solo una lista che non si puo' ciclare.
        self.assertIsInstance(righe[0]["commesse_fallite"], list)
        self.assertEqual(righe[0]["commesse_fallite"][0]["commessa_id"], 34137)
        self.assertEqual(
            righe[0]["commesse_fallite"][0]["dettaglio"],
            "ROOT source mancante per commessa 34137",
        )
        # I campi preesistenti non si sono spostati di una casella.
        self.assertEqual(righe[0]["task_code"], "pull_attivita_da_commessa")
        self.assertEqual(righe[0]["emittente_ragione_sociale"], "Gestore Test pgTAP")

    # Scopo: il presidio del presidio, come per i gruppi — la riga finta e il
    #        SELECT vero devono avere la stessa larghezza, o tutti i test di
    #        mapping qui sopra girano su una forma che il database non produce.
    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_larghezza_riga_errori_uguale_al_select(self, mock_query):
        mock_query.return_value = ([self._riga_errore()], 1)
        VenditeRepository().list_dash_competenza_errori(
            competenza_mese=date(2026, 9, 1), limit=25, offset=0,
        )
        sql = mock_query.call_args.kwargs["select_sql"]
        proiezione = sql.split("FROM vendite.vw_dash_competenza_errori")[0]
        # Le colonne della proiezione sono `e.<nome>` piu' la chiamata alla
        # sede unica del numero documento, che colonna della vista non e'.
        colonne = [
            r for r in (x.strip() for x in proiezione.splitlines())
            if r.startswith(("e.", "vendite.fn_numero_documento_fattura"))
        ]
        self.assertEqual(
            len(colonne), len(self._riga_errore()),
            "la riga finta non ha piu' la larghezza del SELECT: i test di "
            "mapping stanno girando su una forma che il database non produce.",
        )


class DashCompetenzaGruppiExportParitaTests(TestCase):
    """L'export deve portare gli STESSI filtri della lista (D-7).

    Un export che non corrisponde a cio' che si vede a video e' peggio di nessun
    export: chi lo apre crede di avere quel perimetro e non ha modo di
    accorgersi che non e' cosi'. E il modo in cui si rompe non e' un errore —
    e' un filtro aggiunto alla lista e dimenticato nell'export, che continua a
    funzionare esportando piu' righe.

    Il test legge la sorgente invece di eseguire la view: la view richiede
    request/auth/scope, e cio' che va presidiato e' un fatto statico — quali
    chiavi il chiamante passa a `fn_dash_competenza_gruppi`.
    """

    # Parametri del service che NON sono filtri di perimetro: l'export li governa
    # per conto suo (niente paginazione, cap righe dal BB di export).
    _NON_FILTRI = {"limit", "offset", "max_rows"}

    # Scopo: le classi delle due view che chiamano `_filtri_gruppi_da_query`.
    def _classi_che_usano_il_lettore(self) -> set[str]:
        import ast
        import inspect

        from apps.vendite.api import views_dashboard_competenza as mod

        albero = ast.parse(inspect.getsource(mod))
        trovate: set[str] = set()
        for nodo in ast.walk(albero):
            if not isinstance(nodo, ast.ClassDef):
                continue
            for chiamata in ast.walk(nodo):
                if (
                    isinstance(chiamata, ast.Call)
                    and isinstance(chiamata.func, ast.Name)
                    and chiamata.func.id == "_filtri_gruppi_da_query"
                ):
                    trovate.add(nodo.name)
        return trovate

    # ⚠️ QUESTO TEST E' CAMBIATO IL 2026-08-26, e il motivo va letto.
    #     Prima leggeva le chiavi LETTERALI del dict `filtri={...}` dell'export
    #     e le confrontava con la firma del service. Misurava la cosa giusta
    #     finche' i due punti di lettura erano DUE — ma la duplicazione era il
    #     difetto, non il presidio: aggiungendo il filtro sezionale e' finito
    #     nella lista e non nell'export, e questo test e' rimasto VERDE perche'
    #     nel dict la chiave c'era (l'avevo scritta a mano in tutti e due).
    #     Ora la lettura e' UNA (`_filtri_gruppi_da_query`) e la proprieta' da
    #     provare e' diventata piu' forte: che quel lettore sia completo, e che
    #     lo usino entrambe le view. Un filtro dimenticato non e' piu'
    #     possibile — nasce in tutti e due i posti o in nessuno.
    def test_lettore_filtri_copre_tutti_i_filtri_del_service(self) -> None:
        import inspect

        from apps.vendite.api.views_dashboard_competenza import _filtri_gruppi_da_query

        parametri = set(inspect.signature(fn_dash_competenza_gruppi).parameters)
        attesi = parametri - self._NON_FILTRI
        # `competenza_mese` lo passano le view separatamente: e' obbligatorio e
        # ha una sua validazione parlante, non e' un filtro opzionale.
        letti = set(_filtri_gruppi_da_query({})) | {"competenza_mese"}
        dimenticati = attesi - letti
        self.assertEqual(
            dimenticati, set(),
            f"filtri del service che nessuno legge dalla query string: "
            f"{dimenticati}. Lista ed export mostrerebbero un perimetro piu' "
            "largo di quello chiesto, senza nessun errore.",
        )

    def test_lista_ed_export_usano_lo_stesso_lettore(self) -> None:
        self.assertEqual(
            self._classi_che_usano_il_lettore(),
            {"ApiDashboardCompetenzaGruppi", "ApiDashboardCompetenzaGruppiExport"},
            "una delle due view si e' riscritta la lettura dei filtri in "
            "proprio: e' esattamente il modo in cui l'export ha gia' esportato "
            "un perimetro diverso da quello a video.",
        )


class DashCompetenzaGruppiOrdinamentoTests(TestCase):
    """Ordinare per una colonna nuova non deve rompere la paginazione.

    La vista mette lo STESSO gruppo su piu' righe (una per stadio), quindi senza
    il tiebreaker `(gruppo_key, stadio)` l'ordine fra quelle righe e' indefinito:
    a offset alti PostgreSQL puo' restituire righe gia' viste. Il difetto non da'
    errore — da' pagine con doppioni e righe che non compaiono mai.
    """

    @patch.object(VenditeRepository, "_query_paged_view", autospec=True)
    def test_colonne_nuove_ordinano_col_tiebreaker(self, mock_query) -> None:
        mock_query.return_value = ([], 0)
        for colonna in ("ba_codice_fatturazione", "id_fiscale"):
            with self.subTest(colonna=colonna):
                VenditeRepository().list_dash_competenza_gruppi(
                    competenza_mese=date(2026, 8, 1), stadio=None,
                    order_by=colonna, order_dir="asc", limit=25, offset=0,
                )
                order = mock_query.call_args.kwargs["order_by"]
                self.assertIn(colonna, order)
                self.assertIn("gruppo_key ASC", order)
                self.assertIn("stadio", order)


class DashCompetenzaFatturePerCellaTests(TestCase):
    """La seconda misura delle card: quante FATTURE, non quante attivita'.

    Il difetto che questi test bloccano non e' un numero sbagliato ma un
    numero INVENTATO — e, dal rilievo del 2026-08-03, un SILENZIO ambiguo:
    «non si calcola per progetto» e «doveva calcolarsi e si e' rotto»
    finivano entrambi su un campo assente, quindi a video erano la stessa
    cosa. Un guasto che prende l'aspetto del comportamento normale e' il
    modo peggiore di sbagliare, ed e' proprio cio' che questo cantiere sta
    togliendo dal cruscotto.
    """

    _RIGHE = [
        {
            "competenza_mese": "2026-01-01", "stadio": "FATTURATA",
            "stato_fattura_codice_interno": "EMESSA", "stato_fattura_codice": "EM",
 "tipo_movimento": "NORMALE",
            "n_attivita": 9, "valore": "900.00", "valore_fatturato": "900.00",
            "n_in_ritardo": 0, "valore_in_ritardo": "0",
            "n_attivita_trattenute": 0,
            "valore_trattenuto": "0",
        },
        {
            "competenza_mese": "2026-01-01", "stadio": "DA_EMETTERE",
            "stato_fattura_codice_interno": None, "stato_fattura_codice": None,
 "tipo_movimento": "NORMALE",
            "n_attivita": 3, "valore": "300.00", "valore_fatturato": "0",
            "n_in_ritardo": 0, "valore_in_ritardo": "0",
            "n_attivita_trattenute": 0,
            "valore_trattenuto": "0",
        },
        {
            "competenza_mese": "2026-01-01", "stadio": "EMESSA_NON_FATTURATA",
            "stato_fattura_codice_interno": None, "stato_fattura_codice": None,
 "tipo_movimento": "NORMALE",
            "n_attivita": 5, "valore": "500.00", "valore_fatturato": "0",
            "n_in_ritardo": 0, "valore_in_ritardo": "0",
            "n_attivita_trattenute": 0,
            "valore_trattenuto": "0",
        },
    ]

    # Scopo: cella di uno stadio del primo mese della griglia.
    def _cella(self, data, stadio):
        return next(c for c in data["mesi"][0]["stadi"] if c["stadio"] == stadio)

    # 25) Il conteggio arriva alla cella GIUSTA. Con piu' stadi popolati nello
    #     stesso mese, un innesto per chiave sbagliata (solo mese, ignorando lo
    #     stadio) spalmerebbe le 2 fatture di FATTURATA anche sugli altri — e
    #     sarebbe invisibile in un test a stadio singolo.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", autospec=True)
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_fatture_mensile", autospec=True)
    def test_n_fatture_innestato_sulla_cella_di_quello_stadio(
        self, mock_fatture, mock_rows, _mock_err,
    ):
        mock_rows.return_value = self._RIGHE
        mock_fatture.return_value = ({("2026-01-01", "FATTURATA"): 2}, set())
        data = fn_dash_competenza_mensile(anno=2026)
        fatturata = self._cella(data, "FATTURATA")
        self.assertEqual(fatturata["n_fatture"], 2)
        self.assertEqual(fatturata["n_fatture_stato"], "OK")

    # 26) Stadio NON calcolabile per progetto (DA_EMETTERE): nessun numero e
    #     stato NON_APPLICABILE -> la card tace, ed e' corretto che taccia.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", autospec=True)
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_fatture_mensile", autospec=True)
    def test_stadio_non_calcolabile_e_non_applicabile(
        self, mock_fatture, mock_rows, _mock_err,
    ):
        mock_rows.return_value = self._RIGHE
        mock_fatture.return_value = ({("2026-01-01", "FATTURATA"): 2}, set())
        cella = self._cella(fn_dash_competenza_mensile(anno=2026), "DA_EMETTERE")
        self.assertIsNone(cella["n_fatture"])
        self.assertEqual(cella["n_fatture_stato"], "NON_APPLICABILE")

    # 27) 🔴 Il cuore del rilievo: calcolo FALLITO -> stato ERRORE, non
    #     NON_APPLICABILE. Se questi due collassassero, un guasto sarebbe
    #     indistinguibile a video dal comportamento normale — e nessuno
    #     verrebbe mai a saperlo, perche' il warning vive nei log del server.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", autospec=True)
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_fatture_mensile", autospec=True)
    def test_calcolo_fallito_e_errore_non_silenzio(
        self, mock_fatture, mock_rows, _mock_err,
    ):
        mock_rows.return_value = self._RIGHE
        mock_fatture.return_value = ({}, {"EMESSA_NON_FATTURATA"})
        data = fn_dash_competenza_mensile(anno=2026)
        rotta = self._cella(data, "EMESSA_NON_FATTURATA")
        self.assertIsNone(rotta["n_fatture"])
        self.assertEqual(rotta["n_fatture_stato"], "ERRORE")
        # ...e il guasto di UNO stadio non contagia gli altri.
        self.assertEqual(
            self._cella(data, "DA_EMETTERE")["n_fatture_stato"], "NON_APPLICABILE",
        )

    # 28) Cella VUOTA: nessuna attivita' -> nessun conteggio da mostrare
    #     («0 fatture» sotto «0 attivita'» e' rumore), ma NON e' un errore.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", autospec=True, return_value=[])
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_fatture_mensile", autospec=True, return_value=({}, set()))
    def test_cella_vuota_tace_senza_essere_errore(
        self, _mock_fatture, _mock_rows, _mock_err,
    ):
        data = fn_dash_competenza_mensile(anno=2026)
        for mese in data["mesi"]:
            for cella in mese["stadi"]:
                self.assertIsNone(cella["n_fatture"])
                self.assertEqual(cella["n_fatture_stato"], "NON_APPLICABILE")

    # 29) Zero VERO: attivita' presenti, stadio calcolabile, nessuna fattura
    #     ancora -> 0 con stato OK. E' il caso che un `or None` scritto per
    #     comodita' trasformerebbe in un silenzio.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", autospec=True)
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_fatture_mensile", autospec=True)
    def test_zero_esplicito_non_diventa_none(self, mock_fatture, mock_rows, _mock_err):
        mock_rows.return_value = self._RIGHE
        mock_fatture.return_value = ({("2026-01-01", "EMESSA_NON_FATTURATA"): 0}, set())
        cella = self._cella(fn_dash_competenza_mensile(anno=2026), "EMESSA_NON_FATTURATA")
        self.assertEqual(cella["n_fatture"], 0)
        self.assertEqual(cella["n_fatture_stato"], "OK")

    # 30) UNA sola lettura per l'intera griglia, non una per cella (48 query
    #     per un cruscotto sarebbero un difetto di per se').
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", autospec=True, return_value=[])
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_fatture_mensile", autospec=True, return_value=({}, set()))
    def test_una_sola_lettura_per_la_griglia(self, mock_fatture, _mock_rows, _mock_err):
        fn_dash_competenza_mensile(anno=2026)
        # `ANY` e' `self`: il mock `autospec` di un metodo registra l'istanza.
        mock_fatture.assert_called_once_with(ANY, anno=2026)

    # 31) L'avvertimento NON si spande sui mesi vuoti. Il calcolo fallisce per
    #     l'intero anno: senza questo presidio, un guasto accenderebbe fino a
    #     12 avvertimenti, quasi tutti su mesi in cui non c'era niente da
    #     contare — e il caso vero annegherebbe fra i propri falsi positivi.
    #     Presidia l'ORDINE dei rami di `_stato_fatture_cella`, che una prova
    #     di mutazione ha mostrato essere l'unica parte non coperta (e da
    #     correggere: il codice valutava prima il guasto).
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(vendite_service.VenditeRepository, "list_dash_competenza_mensile", autospec=True)
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_fatture_mensile", autospec=True)
    def test_errore_solo_dove_ci_sono_attivita(self, mock_fatture, mock_rows, _mock_err):
        mock_rows.return_value = self._RIGHE            # solo GENNAIO e' popolato
        mock_fatture.return_value = ({}, {"EMESSA_NON_FATTURATA"})
        data = fn_dash_competenza_mensile(anno=2026)

        # Gennaio ha 5 attivita' in quello stadio: li' il numero serviva.
        self.assertEqual(
            self._cella(data, "EMESSA_NON_FATTURATA")["n_fatture_stato"], "ERRORE",
        )
        # Gli altri 11 mesi sono vuoti: tacciono, nonostante lo stesso guasto.
        for mese in data["mesi"][1:]:
            cella = next(
                c for c in mese["stadi"] if c["stadio"] == "EMESSA_NON_FATTURATA"
            )
            self.assertEqual(cella["n_fatture_stato"], "NON_APPLICABILE")



class CardResiduiTests(TestCase):
    """⭐ La card «Emesse non fatturate» conta DUE cose con rimedi opposti."""

    # ⚠️ Come la classe sorella: la terza lettura della griglia (conteggio
    #    fatture per cella) e' una dipendenza DB che questi test non esercitano,
    #    e in CI — dove il database non c'e' — una query vera li farebbe fallire
    #    tutti insieme per un motivo che non riguarda cio' che asseriscono.
    #    In locale il DB c'e' e il difetto sarebbe rimasto invisibile fino alla
    #    pipeline.
    def setUp(self):
        patcher = patch.object(
            vendite_service.VenditeRepository,
            "count_dash_competenza_fatture_mensile", autospec=True,
            return_value=({}, set()),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    # Scopo: 🔴 Dentro `EMESSA_NON_FATTURATA` solo il RESIDUO chiede un'azione:
    #        il totale resta il totale, ma `n_residui` isola la quota su cui vive
    #        il verbo «Riporta da emettere».
    # ⛔ Se questo test cade, la card torna a sommare il lavoro fermo per un
    #        difetto con quello in transito legittimo — e il verbo verrebbe
    #        proposto su emissioni corrette, disfacendole.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile", autospec=True,
        return_value=_ROWS_DUE_POPOLAZIONI,
    )
    def test_card_separa_residui_da_transito(self, _mock_rows, _mock_err):
        luglio = vendite_service.fn_dash_competenza_mensile(anno=2026)["mesi"][6]
        card = next(s for s in luglio["stadi"] if s["stadio"] == "EMESSA_NON_FATTURATA")

        # Il totale li contiene tutti: 5 + 3 + 1.
        self.assertEqual(card["n_attivita"], 9)
        # La quota che chiede un'azione e' SOLO il residuo.
        self.assertEqual(card["n_residui"], 5)
        self.assertEqual(card["valore_residui"], "5019.00")
        # ⚠️ E le altre due NON entrano: sommarle direbbe «9 da recuperare»,
        #    cioe' proporrebbe il verbo su 4 righe che lo rifiuterebbero.
        self.assertEqual(card["n_attivita"] - card["n_residui"], 4)

    # Scopo: Su uno stadio dove il motivo non si applica il campo c'e' e vale 0
    #        (contratto simmetrico DL-8: il frontend rende, non deduce).
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile", autospec=True,
        return_value=_ROWS_BUCKET_SPEZZATO,
    )
    def test_campo_presente_e_zero_dove_non_si_applica(self, _mock_rows, _mock_err):
        luglio = vendite_service.fn_dash_competenza_mensile(anno=2026)["mesi"][6]
        for card in luglio["stadi"]:
            with self.subTest(stadio=card["stadio"]):
                self.assertIn("n_residui", card)
                self.assertEqual(card["n_residui"], 0)

    # Scopo: 🔴 `valore_residui` e' NETTO, non assoluto. Un residuo di RETTIFICA
    #        vale meno di zero, e il verbo lo tocca eccome (Q-8: nessuna
    #        whitelist su `tipo_movimento`).
    # ⛔ Con l'assoluto la card direbbe «di cui 1 · 500,00 €» sotto un totale di
    #        -500,00 €, e sopra una lista che mostra -500,00: due meta' che non
    #        si sommano al tutto, senza che niente fallisca.
    @patch.object(vendite_service.VenditeRepository, "count_dash_competenza_errori_mensile", autospec=True, return_value={})
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile", autospec=True,
        return_value=[
            {
                "competenza_mese": "2026-07-01",
                "stadio": "EMESSA_NON_FATTURATA",
                "stato_fattura_codice_interno": None,
                "stato_fattura_codice": None,
                "tipo_movimento": "RETTIFICA",
                "n_attivita": 1,
                "valore": "-500.00",
                "valore_fatturato": "0",
                "n_in_ritardo": 0,
                "valore_in_ritardo": "0",
                "motivo_non_fatturata": "RESIDUO",
                "n_attivita_trattenute": 0,
                "valore_trattenuto": "0",
            },
        ],
    )
    def test_residuo_di_rettifica_resta_negativo(self, _mock_rows, _mock_err):
        luglio = vendite_service.fn_dash_competenza_mensile(anno=2026)["mesi"][6]
        card = next(s for s in luglio["stadi"] if s["stadio"] == "EMESSA_NON_FATTURATA")
        self.assertEqual(card["n_residui"], 1)
        # Lo stesso segno del `valore` accanto a cui viene reso.
        self.assertEqual(card["valore_residui"], "-500.00")
        self.assertEqual(card["valore_residui"], card["valore"])

    # Scopo: LA QUOTA TRATTENUTA DA UN GIRO IN CORSO arriva alla card, e ci
    #        arriva DICHIARATA — non sottratta una seconda volta.
    # ⛔ Il presidio serve perche' senza di lui questo file e' verde per
    #    SOTTRAZIONE: dal 2026-09-09 il servizio aggrega `n_attivita_trattenute`
    #    e `valore_trattenuto`, ma ogni fixture qui dentro li porta a ZERO —
    #    quindi le due righe girano e non provano niente. Uno scambio fra le due
    #    (`n_trattenute += valore_trattenuto`) passerebbe tutto il resto.
    # ⭐ E l'asserzione che conta davvero e' la terza: `n_attivita` NON si
    #    riduce. Il `FILTER` sta nella VISTA, quindi la quota arriva gia'
    #    esclusa dal totale; se qui si sottraesse ancora, il totale mostrerebbe
    #    meno righe di quante ne esistono — e a video sarebbe un numero
    #    plausibile, cioe' un difetto che nessuno nota.
    @patch.object(
        vendite_service.VenditeRepository,
        "count_dash_competenza_errori_mensile", autospec=True, return_value={},
    )
    @patch.object(
        vendite_service.VenditeRepository,
        "list_dash_competenza_mensile", autospec=True,
        return_value=[
            {
                "competenza_mese": "2026-07-01",
                "stadio": "DA_EMETTERE",
                "stato_fattura_codice_interno": None,
                "stato_fattura_codice": None,
                "tipo_movimento": "NORMALE",
                "n_attivita": 5,
                "valore": "500.00",
                "valore_fatturato": "0",
                "n_in_ritardo": 0,
                "valore_in_ritardo": "0",
                "n_attivita_trattenute": 2,
                "valore_trattenuto": "200.00",
            },
        ],
    )
    def test_la_quota_trattenuta_arriva_alla_card_e_non_si_sottrae(
        self, _mock_rows, _mock_err,
    ):
        luglio = vendite_service.fn_dash_competenza_mensile(anno=2026)["mesi"][6]
        card = next(s for s in luglio["stadi"] if s["stadio"] == "DA_EMETTERE")
        self.assertEqual(card["n_trattenute"], 2)
        self.assertEqual(card["valore_trattenuto"], "200.00")
        # ⛔ Il totale resta quello della vista: la quota e' gia' esclusa la'.
        self.assertEqual(card["n_attivita"], 5)
        self.assertEqual(card["valore"], "500.00")
