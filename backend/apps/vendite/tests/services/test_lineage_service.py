# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari del service lineage/genealogia documenti
#        (get_documento_passaggi, mock repository).
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) LineagePassaggiServiceTests.test_tipo_fuori_whitelist
2) LineagePassaggiServiceTests.test_documento_id_non_valido
3) LineagePassaggiServiceTests.test_sorgente_non_configurata
4) LineagePassaggiServiceTests.test_documento_uid_non_risolto
5) LineagePassaggiServiceTests.test_nodo_non_trovato
6) LineagePassaggiServiceTests.test_shape_risposta_e_direzioni
7) LineagePassaggiServiceTests.test_key_selector_id_niente_query_uid
8) LineagePassaggiServiceTests.test_key_selector_uid_risolto_da_target_table
9) LineagePassaggiServiceTests.test_pratica_none_se_non_collegata
10) LineagePassaggiServiceTests.test_frontiera_none_se_non_transitato
11) LineagePassaggiServiceTests.test_frontiera_none_se_self
12) LineagePassaggiServiceTests.test_frontiera_valorizzata
13) LineagePassaggiServiceTests.test_frontiera_nota_di_credito_porta_la_natura
13) LineagePassaggiServiceTests.test_is_ramo_inverso_passthrough
14) LineagePassaggiServiceTests.test_is_legame_ritirato_tre_stati
"""

from unittest import TestCase
from unittest.mock import patch

from apps.core.services.service_errors import ServiceError
from apps.vendite.services import vendite_service
from apps.vendite.services.vendite_service import get_documento_passaggi

_SORGENTE_ORDINE = {
    "id": 6,
    "codice": "ORDINE_VENDITA",
    "key_selector": "id",
    "target_table": "vendite.ordini",
}

_SORGENTE_PREVENTIVO = {
    "id": 2,
    "codice": "PREVENTIVO",
    "key_selector": "uid",
    "target_table": "vendite.preventivi",
}


# Scopo: Riga summary di base (nodo transitato, con pratica e frontiera).
def _nodo(**overrides):
    base = {
        "tipo_id": 6,
        "tipo_codice_interno": "ORDINE_VENDITA",
        "uid": "163",
        "codice": "ORD0000163",
        "stato_codice_interno": "CONFERMATO",
        "stato_codice": "CONF",
        "stato_descrizione": "Confermato",
        "fase": "IN_CORSO",
        "is_abortito": False,
        "pratica_id": 818,
        "pratica_numero": "PRA-0000818",
        "n_pratiche": 1,
        "frontiera_tipo_id": 8,
        "frontiera_tipo_codice_interno": "DDT_VENDITA",
        "frontiera_uid": "31",
        "frontiera_codice": "DDT0000031",
        "frontiera_stato_codice_interno": "SPEDITO",
        "frontiera_fase": "IN_CORSO",
        "n_discendenti_diretti": 1,
        "n_discendenti_attivi": 1,
        "is_transitato": True,
        "n_sorgenti": 1,
        "root_codice": "PRV0000185",
        # NULL su un ordine: la natura esiste solo sui documenti fiscali.
        "natura_doc_codice_interno": None,
        # Frontiera DDT: nemmeno lei ha natura. Il caso valorizzato (frontiera
        # = nota di credito) ha il suo test dedicato.
        "frontiera_natura_doc_codice_interno": None,
    }
    base.update(overrides)
    return base


def _passaggio(**overrides):
    base = {
        "livello": 1,
        "ordine": 1,
        "arco": "H",
        "ruolo": None,
        "from_tipo_id": 6,
        "from_tipo_codice_interno": "ORDINE_VENDITA",
        "from_uid": "163",
        "from_codice": "ORD0000163",
        "from_stato_codice_interno": "CONFERMATO",
        "from_fase": "IN_CORSO",
        "from_doc_id": 163,
        "to_tipo_id": 8,
        "to_tipo_codice_interno": "DDT_VENDITA",
        "to_uid": "31",
        "to_codice": "DDT0000031",
        "to_stato_codice_interno": "SPEDITO",
        "to_fase": "IN_CORSO",
        "to_is_abortito": False,
        "to_doc_id": 31,
        "is_ramo_inverso": False,
        "from_natura_doc_codice_interno": None,
        "to_natura_doc_codice_interno": None,
        "is_legame_ritirato": False,
    }
    base.update(overrides)
    return base


class LineagePassaggiServiceTests(TestCase):
    # Scopo: Tipo documento fuori whitelist -> E_VENDITE_VALIDATION.
    # ⚠️ L'esempio era "FATTURA" e il 2026-08-21 e' entrata in whitelist: il
    # test restava verde per la ragione sbagliata (arrivava fino al repository e
    # falliva con NOT_FOUND). Ora usa un codice che non esiste in
    # `config.sorgenti` e non puo' entrarci per distrazione.
    def test_tipo_fuori_whitelist(self):
        with self.assertRaises(ServiceError) as ctx:
            get_documento_passaggi("TIPO_INESISTENTE", 1)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: documento_id nullo/negativo/non-int -> E_VENDITE_VALIDATION.
    def test_documento_id_non_valido(self):
        for bad in (0, -3, "42"):
            with self.assertRaises(ServiceError) as ctx:
                get_documento_passaggi("ORDINE_VENDITA", bad)  # type: ignore[arg-type]
            self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: Sorgente assente in config.sorgenti (seed incoerente) ->
    #        E_VENDITE_VALIDATION.
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=None)
    def test_sorgente_non_configurata(self, _mock):
        with self.assertRaises(ServiceError) as ctx:
            get_documento_passaggi("ORDINE_VENDITA", 163)
        self.assertEqual(ctx.exception.code, "E_VENDITE_VALIDATION")

    # Scopo: uid non risolto (doc inesistente o fuori scope RLS) ->
    #        E_VENDITE_NOT_FOUND.
    @patch.object(vendite_service.VenditeRepository, "resolve_lineage_node_uid", autospec=True, return_value=None)
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=_SORGENTE_PREVENTIVO)
    def test_documento_uid_non_risolto(self, _mock_sorg, _mock_uid):
        with self.assertRaises(ServiceError) as ctx:
            get_documento_passaggi("PREVENTIVO", 999999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    # Scopo: Nodo assente dalla summary -> E_VENDITE_NOT_FOUND.
    @patch.object(vendite_service.VenditeRepository, "get_lineage_nodo", autospec=True, return_value=None)
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=_SORGENTE_ORDINE)
    def test_nodo_non_trovato(self, _mock_sorg, _mock_nodo):
        with self.assertRaises(ServiceError) as ctx:
            get_documento_passaggi("ORDINE_VENDITA", 999999)
        self.assertEqual(ctx.exception.code, "E_VENDITE_NOT_FOUND")

    # Scopo: Shape della risposta (nodo/pratica/frontiera/avanti/indietro) e
    #        traversal invocato in ENTRAMBE le direzioni con la chiave nodo.
    @patch.object(vendite_service.VenditeRepository, "list_lineage_passaggi", autospec=True)
    @patch.object(vendite_service.VenditeRepository, "get_lineage_nodo", autospec=True, return_value=_nodo())
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=_SORGENTE_ORDINE)
    def test_shape_risposta_e_direzioni(self, _mock_sorg, _mock_nodo, mock_passaggi):
        mock_passaggi.return_value = [_passaggio()]
        data = get_documento_passaggi("ORDINE_VENDITA", 163)
        self.assertEqual(data["nodo"]["tipo_codice_interno"], "ORDINE_VENDITA")
        self.assertEqual(data["nodo"]["codice"], "ORD0000163")
        self.assertEqual(data["pratica"]["pratica_numero"], "PRA-0000818")
        self.assertEqual(data["frontiera"]["codice"], "DDT0000031")
        self.assertEqual(len(data["avanti"]), 1)
        self.assertEqual(len(data["indietro"]), 1)
        direzioni = [c.kwargs["direzione"] for c in mock_passaggi.call_args_list]
        self.assertEqual(direzioni, ["avanti", "indietro"])
        for c in mock_passaggi.call_args_list:
            self.assertEqual(c.kwargs["tipo_id"], 6)
            self.assertEqual(c.kwargs["node_uid"], "163")

    # Scopo: key_selector='id' -> chiave nodo = str(doc_id) senza query uid.
    @patch.object(vendite_service.VenditeRepository, "list_lineage_passaggi", autospec=True, return_value=[])
    @patch.object(vendite_service.VenditeRepository, "get_lineage_nodo", autospec=True, return_value=_nodo())
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=_SORGENTE_ORDINE)
    def test_key_selector_id_niente_query_uid(self, _mock_sorg, mock_nodo, _mock_p):
        get_documento_passaggi("ORDINE_VENDITA", 163)
        self.assertEqual(mock_nodo.call_args.kwargs["node_uid"], "163")

    # Scopo: key_selector='uid' -> chiave nodo risolta dalla tabella target
    #        (convenzione chiave sorgente polimorfa).
    @patch.object(vendite_service.VenditeRepository, "list_lineage_passaggi", autospec=True, return_value=[])
    @patch.object(
        vendite_service.VenditeRepository,
        "get_lineage_nodo", autospec=True,
        return_value=_nodo(tipo_id=2, tipo_codice_interno="PREVENTIVO", uid="abc-uuid"),
    )
    @patch.object(vendite_service.VenditeRepository, "resolve_lineage_node_uid", autospec=True, return_value="abc-uuid")
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=_SORGENTE_PREVENTIVO)
    def test_key_selector_uid_risolto_da_target_table(
        self, _mock_sorg, mock_uid, mock_nodo, _mock_p
    ):
        get_documento_passaggi("PREVENTIVO", 185)
        self.assertEqual(mock_uid.call_args.kwargs["target_table"], "vendite.preventivi")
        self.assertEqual(mock_uid.call_args.kwargs["key_selector"], "uid")
        self.assertEqual(mock_uid.call_args.kwargs["doc_id"], 185)
        self.assertEqual(mock_nodo.call_args.kwargs["node_uid"], "abc-uuid")

    # Scopo: Documento senza pratica -> pratica=None (non oggetto vuoto).
    @patch.object(vendite_service.VenditeRepository, "list_lineage_passaggi", autospec=True, return_value=[])
    @patch.object(
        vendite_service.VenditeRepository,
        "get_lineage_nodo", autospec=True,
        return_value=_nodo(pratica_id=None, pratica_numero=None, n_pratiche=0),
    )
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=_SORGENTE_ORDINE)
    def test_pratica_none_se_non_collegata(self, _mock_sorg, _mock_nodo, _mock_p):
        data = get_documento_passaggi("ORDINE_VENDITA", 163)
        self.assertIsNone(data["pratica"])

    # Scopo: Documento non transitato -> frontiera=None.
    @patch.object(vendite_service.VenditeRepository, "list_lineage_passaggi", autospec=True, return_value=[])
    @patch.object(
        vendite_service.VenditeRepository,
        "get_lineage_nodo", autospec=True,
        return_value=_nodo(
            is_transitato=False,
            n_discendenti_diretti=0,
            n_discendenti_attivi=0,
        ),
    )
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=_SORGENTE_ORDINE)
    def test_frontiera_none_se_non_transitato(self, _mock_sorg, _mock_nodo, _mock_p):
        data = get_documento_passaggi("ORDINE_VENDITA", 163)
        self.assertIsNone(data["frontiera"])

    # Scopo: La summary per un nodo senza discendenti attivi puo' indicare il
    #        nodo stesso come frontiera -> normalizzata a None.
    @patch.object(vendite_service.VenditeRepository, "list_lineage_passaggi", autospec=True, return_value=[])
    @patch.object(
        vendite_service.VenditeRepository,
        "get_lineage_nodo", autospec=True,
        return_value=_nodo(
            frontiera_tipo_id=6,
            frontiera_tipo_codice_interno="ORDINE_VENDITA",
            frontiera_uid="163",
            frontiera_codice="ORD0000163",
        ),
    )
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=_SORGENTE_ORDINE)
    def test_frontiera_none_se_self(self, _mock_sorg, _mock_nodo, _mock_p):
        data = get_documento_passaggi("ORDINE_VENDITA", 163)
        self.assertIsNone(data["frontiera"])

    # Scopo: Frontiera valorizzata con i campi FE-critici (chip transito).
    @patch.object(vendite_service.VenditeRepository, "list_lineage_passaggi", autospec=True, return_value=[])
    @patch.object(vendite_service.VenditeRepository, "get_lineage_nodo", autospec=True, return_value=_nodo())
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=_SORGENTE_ORDINE)
    def test_frontiera_valorizzata(self, _mock_sorg, _mock_nodo, _mock_p):
        data = get_documento_passaggi("ORDINE_VENDITA", 163)
        self.assertEqual(
            data["frontiera"],
            {
                "tipo_codice_interno": "DDT_VENDITA",
                "natura_doc_codice_interno": None,
                "codice": "DDT0000031",
                "stato_codice_interno": "SPEDITO",
                "fase": "IN_CORSO",
                "n_discendenti_attivi": 1,
            },
        )

    # Scopo: 🔴 LA FRONTIERA PUO' ESSERE UNA NOTA DI CREDITO, e la natura deve
    #        arrivare al FE. Non e' un caso di scuola: l'arco G dalla commessa
    #        NON e' un ramo di ritorno, e al 2026-08-21 la NC 15353 e' gia' la
    #        frontiera dell'ordine 240 e della commessa 322 (misurato). Senza
    #        la natura il pannello etichetta «Fattura» il documento sbagliato —
    #        ed e' l'invariante falsa («una NC non e' mai frontiera») che il
    #        pgTAP del DB ha corretto (§44.5 del brief).
    #        `codice=None` nel fixture e' fedele: la NC frontiera non e' ancora
    #        numerata, ed e' il caso che ha scoperto anche la fallback
    #        «non ancora numerato» su frontiera e chip lista.
    @patch.object(vendite_service.VenditeRepository, "list_lineage_passaggi", autospec=True, return_value=[])
    @patch.object(
        vendite_service.VenditeRepository,
        "get_lineage_nodo", autospec=True,
        return_value=_nodo(
            frontiera_tipo_id=10,
            frontiera_tipo_codice_interno="FATTURA",
            frontiera_uid="15353",
            frontiera_codice=None,
            frontiera_stato_codice_interno="EMESSA",
            frontiera_natura_doc_codice_interno="NOTA_CREDITO",
        ),
    )
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=_SORGENTE_ORDINE)
    def test_frontiera_nota_di_credito_porta_la_natura(self, _mock_sorg, _mock_nodo, _mock_p):
        data = get_documento_passaggi("ORDINE_VENDITA", 240)
        self.assertEqual(data["frontiera"]["tipo_codice_interno"], "FATTURA")
        self.assertEqual(data["frontiera"]["natura_doc_codice_interno"], "NOTA_CREDITO")
        self.assertIsNone(data["frontiera"]["codice"])

    # Scopo: gli OTTO tipi con endpoint /passaggi/. La lista si scrive per
    #        intero e non per appartenenza: un tipo aggiunto senza la sua rotta
    #        (o una rotta senza il tipo) e' un 404 che nessun test vedrebbe.
    #
    #        ⚠️ FATTURA c'e' dal 2026-08-21 e prima questo test ne presidiava
    #        l'ASSENZA («capolinea senza superficie propria», Q4). Le due meta'
    #        di quella frase sono cadute in momenti diversi: il drawer di
    #        consultazione esiste dal 2026-07-29, e l'arco N (fattura
    #        rettificata -> nota di credito) le ha dato un discendente.
    def test_whitelist_passaggi_otto_tipi(self):
        from apps.vendite.services.vendite_service import LINEAGE_TIPI_DOCUMENTO
        self.assertEqual(
            sorted(LINEAGE_TIPI_DOCUMENTO),
            [
                "COMMESSA",
                "CONTRATTO",
                "DDT_VENDITA",
                "FATTURA",
                "OFFERTA_COMMERCIALE",
                "ORDINE_VENDITA",
                "PREVENTIVO",
                "RESO_VENDITA",
            ],
        )

    # Scopo: L'arco R (DDT->Reso) arriva al FE con is_ramo_inverso=true.
    @patch.object(vendite_service.VenditeRepository, "list_lineage_passaggi", autospec=True)
    @patch.object(vendite_service.VenditeRepository, "get_lineage_nodo", autospec=True, return_value=_nodo())
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=_SORGENTE_ORDINE)
    def test_is_ramo_inverso_passthrough(self, _mock_sorg, _mock_nodo, mock_passaggi):
        mock_passaggi.return_value = [
            _passaggio(),
            _passaggio(
                ordine=2,
                arco="R",
                to_tipo_codice_interno="RESO_VENDITA",
                to_codice="RES0000004",
                is_ramo_inverso=True,
            ),
        ]
        data = get_documento_passaggi("ORDINE_VENDITA", 163)
        self.assertFalse(data["avanti"][0]["is_ramo_inverso"])
        self.assertTrue(data["avanti"][1]["is_ramo_inverso"])

    # Scopo: il legame dell'arco (brief-db-annullo-a-valle-riapre-a-monte §11)
    #        arriva al FE nei TRE stati del DB. ⛔ None resta None: e' «arco non
    #        censito», e un `False` al suo posto direbbe «legame vivo».
    @patch.object(vendite_service.VenditeRepository, "list_lineage_passaggi", autospec=True)
    @patch.object(vendite_service.VenditeRepository, "get_lineage_nodo", autospec=True, return_value=_nodo())
    @patch.object(vendite_service.SorgentiRepository, "get_sorgente_attiva", autospec=True, return_value=_SORGENTE_ORDINE)
    def test_is_legame_ritirato_tre_stati(self, _mock_sorg, _mock_nodo, mock_passaggi):
        mock_passaggi.return_value = [
            _passaggio(is_legame_ritirato=True),
            _passaggio(ordine=2, is_legame_ritirato=False),
            _passaggio(ordine=3, is_legame_ritirato=None),
        ]
        data = get_documento_passaggi("ORDINE_VENDITA", 163)
        self.assertEqual(
            [p["is_legame_ritirato"] for p in data["avanti"]],
            [True, False, None],
        )
