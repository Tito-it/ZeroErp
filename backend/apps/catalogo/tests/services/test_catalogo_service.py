# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unitari funzioni catalogo_service per Fasi 1-2 articoli/UoM.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) CatalogoServiceTests.test_fn_list_articoli_ok
2) CatalogoServiceTests.test_fn_list_articoli_invalid_order
4) CatalogoServiceTests.test_fn_get_articolo_ok
5) CatalogoServiceTests.test_fn_get_articolo_not_found
5b) CatalogoServiceTests.test_fn_list_componenti_pagina_legge_prima_l_articolo
6) CatalogoServiceTests.test_fn_lookup_articoli_ok
7) CatalogoServiceTests.test_fn_lookup_articoli_invalid_limit
10) CatalogoServiceTests.test_fn_create_articolo_ok
11) CatalogoServiceTests.test_fn_create_articolo_missing_codice
11b) CatalogoServiceTests.test_fn_create_articolo_missing_uom_id
12) CatalogoServiceTests.test_fn_create_articolo_duplicate_codice
13) CatalogoServiceTests.test_fn_update_articolo_ok
14) CatalogoServiceTests.test_fn_update_articolo_codice_immutabile
14b) CatalogoServiceTests.test_fn_update_articolo_uom_id_immutabile
15) CatalogoServiceTests.test_fn_disattiva_articolo_ok
16) CatalogoServiceTests.test_fn_disattiva_articolo_already_inactive
17) CatalogoServiceTests.test_fn_create_articolo_unknown_key
18) CatalogoServiceTests.test_fn_update_articolo_float_fk_invalid
19) CatalogoServiceTests.test_fn_create_uom_operativa_ok
20) CatalogoServiceTests.test_fn_update_uom_operativa_not_found
21) CatalogoServiceTests.test_fn_create_componente_ok
22) CatalogoServiceTests.test_fn_update_componente_immutabile
23) CatalogoServiceTests.test_fn_create_nota_articolo_ok
24) CatalogoServiceTests.test_fn_create_nota_articolo_default_documento_header
25) CatalogoServiceTests.test_fn_create_nota_componente_default_riga_after
26) CatalogoServiceTests.test_fn_create_nota_articolo_anchor_riga_inconsistency
27) CatalogoServiceTests.test_fn_update_nota_not_found
28) CatalogoServiceTests.test_fn_create_componente_self_reference
26) CatalogoServiceTests.test_fn_create_articolo_listino_tipologia_id_ok
27) CatalogoServiceTests.test_fn_update_articolo_listino_tipologia_id_invalid
27b) CatalogoServiceTests.test_fn_create_articolo_natura_vendita_id_ok
27c) CatalogoServiceTests.test_fn_update_articolo_natura_vendita_id_null_invalid
28) CatalogoServiceTests.test_fn_create_componente_esposizione_in_fattura_ok
28b) CatalogoServiceTests.test_fn_create_componente_booleano_ritirato_rifiutato
28c) CatalogoServiceTests.test_fn_create_componente_esposizione_null_rifiutata
31) CatalogoServiceTests.test_fn_create_componente_valido_dal_fallback_today
40) CatalogoServiceTests.test_fn_create_uom_operativa_valido_dal_fallback_today
41) CatalogoServiceTests.test_fn_create_conversione_valido_dal_fallback_today
42) CatalogoServiceTests.test_fn_get_articolo_includes_non_editable_fields
43) CatalogoServiceTests.test_fn_list_uom_operative_envelope_non_editable_fields
44) CatalogoServiceTests.test_fn_get_conversione_includes_non_editable_fields
45) CatalogoServiceTests.test_fn_list_articoli_proietta_capability_bom
46) CatalogoServiceTests.test_fn_list_uom_operative_proietta_capability_eliminabile
47) CatalogoServiceTests.test_fn_riattiva_articolo_ok
48) CatalogoServiceTests.test_fn_riattiva_articolo_already_active
49) CatalogoServiceTests.test_fn_riattiva_articolo_not_found
50) CatalogoServiceTests.test_fn_update_articolo_rifiuta_attivo
51) CatalogoServiceTests.test_fn_get_articolo_form_defaults_ok
52) CatalogoServiceTests.test_fn_get_articolo_form_defaults_missing_param
53) CatalogoServiceTests.test_fn_get_articolo_form_defaults_malformed_param
54) CatalogoServiceTests.test_fn_update_articolo_approvvigionamento_propagato (Blocco B)
55) CatalogoServiceTests.test_fn_update_articolo_modo_approvvigionamento_null_invalid
56) CatalogoServiceTests.test_fn_update_articolo_lead_time_negativo_invalid
57) CatalogoServiceTests.test_chiave_fuori_contratto_e_un_400_prima_del_repository
58) CatalogoServiceTests.test_nota_meta_null_diventa_oggetto_vuoto
59) CatalogoServiceTests.test_fn_create_articolo_composito_e_solo_componente
60) CatalogoServiceTests.test_fn_create_componente_periodo_sovrapposto
61) CatalogoServiceTests.test_fn_create_uom_operativa_doppia
62) CatalogoServiceTests.test_uom_operativa_campi_ritirati_sono_fuori_contratto
63) CatalogoServiceTests.test_fn_update_uom_operativa_riga_base_fissa
64) CatalogoServiceTests.test_fn_create_conversione_coppia_sovrapposta
65) CatalogoServiceTests.test_fn_create_conversione_rifiuto_col_codice_passa_intatto
    (2026-09-26: il repository e' a whitelist RIGIDA, quindi il 400 del
    service e' l'unica risposta educata — per OGNI scrittura del dominio)
"""

from unittest import TestCase
from unittest.mock import patch

from django.db import IntegrityError

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.service_errors import ServiceError

# Dal 2026-11-09 i lock li legge il BB `compute_non_editable_fields`: si
# sostituisce il repository dove lo importa il BB, non piu' in catalogo.
_LOCK_REPO = "apps.core.services.non_editable_fields_helper.LockColumnsRepository"


class CatalogoServiceTests(TestCase):
    # Scopo: Lista articoli valida -> envelope paginato coerente.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_list_articoli_ok(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_list_articoli

        mock_repo_cls.return_value.list_articoli.return_value = (
            [{"id": 1, "codice": "ART-001", "descrizione": "Articolo demo"}],
            1,
        )

        results, total = fn_list_articoli(search="art", limit=25, offset=0, order_by="codice")

        self.assertEqual(total, 1)
        self.assertEqual(results[0]["codice"], "ART-001")

    # Scopo: order_by fuori whitelist -> ServiceError validazione.
    def test_fn_list_articoli_invalid_order(self):
        from apps.catalogo.services.catalogo_service import fn_list_articoli

        with self.assertRaises(ServiceError) as ctx:
            fn_list_articoli(order_by="nome")
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: Dettaglio articolo trovato -> dict ritornato senza trasformazioni.
    # ⚠️ Anche `LockColumnsRepository` e' mockato (2026-11-09): senza, il test
    #    andava al DB vero con un id intero su una PK uuid, e passava solo
    #    perche' il repository ricade sui lock statici e logga un warning.
    @patch(_LOCK_REPO, autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_get_articolo_ok(
        self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls, mock_lock_cls,
    ):
        from apps.catalogo.services.catalogo_service import fn_get_articolo

        mock_lock_cls.list_non_editable_for_record.return_value = ()

        mock_repo_cls.return_value.get_articolo.return_value = {
            "id": 7,
            "codice": "ART-007",
            "is_composito": True,
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = [{"id": 1, "uom_codice": "PZ"}]
        mock_bom_repo_cls.return_value.list_righe.return_value = [{"id": "comp-1"}]
        # Shape allineata al pattern partizionato vendite (2026-05-22):
        # le note ritornano `id`/`testo_md` senza prefisso `nota_`.
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = [{"id": 9}]

        result = fn_get_articolo(7)

        self.assertEqual(result["id"], 7)
        self.assertEqual(result["codice"], "ART-007")
        self.assertEqual(result["uom_operative"][0]["uom_codice"], "PZ")
        self.assertEqual(result["componenti"][0]["id"], "comp-1")
        self.assertEqual(result["note"][0]["id"], 9)

    # Scopo: Dettaglio articolo assente -> not found uniforme.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_get_articolo_not_found(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_get_articolo

        mock_repo_cls.return_value.get_articolo.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            fn_get_articolo(999)
        self.assertEqual(ctx.exception.code, "E_CATALOGO_ARTICOLO_NOT_FOUND")

    # Scopo: «Leggi prima la testata» sulla PAGINA della distinta (§9.6 del
    #        brief-db-liste-righe-documento, 2026-10-04): un articolo che non
    #        c'e' e' un 404, e le righe non si leggono.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_list_componenti_pagina_legge_prima_l_articolo(self, mock_repo_cls, mock_bom_cls):
        from apps.catalogo.services.catalogo_service import fn_list_componenti_pagina

        mock_repo_cls.return_value.get_articolo.return_value = None
        with self.assertRaises(ServiceError) as ctx:
            fn_list_componenti_pagina("a-1", limit=10, valido_al=None)
        self.assertEqual(ctx.exception.code, "E_CATALOGO_ARTICOLO_NOT_FOUND")
        mock_bom_cls.return_value.list_righe_pagina.assert_not_called()

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "a-1"}
        mock_bom_cls.return_value.list_righe_pagina.return_value = ([], 0)
        self.assertEqual(fn_list_componenti_pagina("a-1", limit=10, valido_al=None), ([], 0))
        mock_bom_cls.return_value.list_righe_pagina.assert_called_once_with(
            "a-1", limit=10, valido_al=None,
        )

    # Scopo: Lookup articoli valido -> count e results coerenti.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_lookup_articoli_ok(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_lookup_articoli

        # ⚠️ Il repository consegna una COPPIA `(righe, troncato)`: e' lui a
        #    conoscere `safe_limit`, quindi e' lui a sapere se ha tagliato.
        mock_repo_cls.return_value.lookup_articoli.return_value = (
            [{"id": 1, "codice": "ART-001"}], False,
        )

        result = fn_lookup_articoli(search="art")

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["results"][0]["id"], 1)
        self.assertFalse(result["troncato"])

    # Scopo: la riga di un documento passa il suo contesto al repository della
    # sede unica, e il `motivo` torna intero (brief-db-articoli-ammessi-per-
    # documento §9.6, Lotto 4).
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_lookup_articoli_ammessi_passa_il_contesto(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_lookup_articoli_ammessi

        repo = mock_repo_cls.return_value
        repo.tipo_eccezione_valido.return_value = True
        motivo = {"codice": "E_X", "reason": "X", "reason_key": "k.x", "valori": ["A"]}
        repo.lookup_articoli_ammessi.return_value = (
            [{"id": 1, "motivo": None}, {"id": 2, "motivo": motivo}], False,
        )

        result = fn_lookup_articoli_ammessi(
            documento="CONTRATTO", documento_id=7, search="art", tipo_eccezione="AGGIUNTA",
        )

        kwargs = repo.lookup_articoli_ammessi.call_args.kwargs
        self.assertEqual(kwargs["documento"], "CONTRATTO")
        self.assertEqual(kwargs["documento_id"], 7)
        self.assertEqual(kwargs["tipo_eccezione"], "AGGIUNTA")
        self.assertIsNone(kwargs["articolo_padre_id"])
        self.assertEqual(result["results"][1]["motivo"], motivo)
        self.assertFalse(result["troncato"])

    # Scopo: un tipo d'eccezione fuori enum e' un 400 PRIMA del cast, che
    # sarebbe un 500 (22P02): il picker non viene nemmeno chiamato.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_lookup_articoli_ammessi_tipo_eccezione_estraneo(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_lookup_articoli_ammessi

        repo = mock_repo_cls.return_value
        repo.tipo_eccezione_valido.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            fn_lookup_articoli_ammessi(documento="CONTRATTO", documento_id=7, tipo_eccezione="BANANA")
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        repo.lookup_articoli_ammessi.assert_not_called()

    # Scopo: la correzione di struttura nel PATCH (R-BE-1): prima il verbo, poi
    # l'UPDATE; `correzione_struttura` arriva al verbo com'e' (forma, permesso e
    # colonne li giudica lui); da sola non chiede altri campi; assente, il verbo
    # non parte. L'atomicita' e' provata su DB vero
    # (tests/db/test_articoli_ammessi_db.py).
    @patch("apps.catalogo.services.catalogo_service.fn_get_articolo")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_update_articolo_con_correzione_di_struttura(self, mock_repo_cls, mock_get):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        articolo_id = "00000000-0000-0000-0000-000000000001"
        repo = mock_repo_cls.return_value
        repo.update_articolo.return_value = True
        mock_get.return_value = {"id": articolo_id}

        fn_update_articolo(articolo_id, {"descrizione": "Nuova", "correzione_struttura": {"requires_lotto": True}})
        chiamate = [c[0] for c in repo.method_calls]
        self.assertEqual(chiamate, ["correggi_struttura_articolo", "update_articolo"])
        repo.correggi_struttura_articolo.assert_called_once_with(articolo_id, {"requires_lotto": True})
        repo.update_articolo.assert_called_once_with(articolo_id, {"descrizione": "Nuova"})

        repo.reset_mock()
        for correzione in ({}, None):
            with self.subTest(correzione=correzione):
                fn_update_articolo(articolo_id, {"correzione_struttura": correzione})
                repo.correggi_struttura_articolo.assert_called_with(articolo_id, correzione)
        repo.update_articolo.assert_not_called()

        repo.reset_mock()
        fn_update_articolo(articolo_id, {"descrizione": "Nuova"})
        repo.correggi_struttura_articolo.assert_not_called()

    # Scopo: 🔴 IL CASO PER CUI D6 ESISTE — un lookup TAGLIATO lo dichiara.
    #        Prima di oggi la risposta era `{"count": 20, "results": [20 righe]}`
    #        anche quando i risultati erano cento: il conteggio CONFERMAVA il
    #        troncamento invece di rivelarlo, e chi legge non aveva modo di
    #        sapere che l'elenco era parziale.
    #        ⚠️ Il conteggio resta quello delle righe consegnate: cio' che cambia
    #        e' che accanto c'e' la sola informazione che lo rende leggibile.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_lookup_articoli_dichiara_il_troncamento(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_lookup_articoli

        mock_repo_cls.return_value.lookup_articoli.return_value = (
            [{"id": i} for i in range(20)], True,
        )

        result = fn_lookup_articoli(search="a", limit=20)

        self.assertEqual(result["count"], 20)
        self.assertTrue(result["troncato"], "il taglio non arriva a chi legge")

    # Scopo: ⭐ E la collezione INTERA non porta `troncato`, perche' non puo'
    #        essere tagliata: due nature, due envelope. Tenerle sullo stesso
    #        helper era il difetto — la forma sbagliata era indistinguibile da
    #        quella giusta perche' era la stessa riga di codice.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_una_collezione_intera_non_dichiara_troncamento(self, _mock_repo, mock_bom):
        from apps.catalogo.services.catalogo_service import fn_list_componenti

        mock_bom.return_value.list_righe.return_value = [{"id": 1}, {"id": 2}]

        result = fn_list_componenti("00000000-0000-0000-0000-000000000001")

        self.assertEqual(result["count"], 2)
        self.assertNotIn("troncato", result)

    # Scopo: limit lookup articoli fuori range -> ServiceError.
    def test_fn_lookup_articoli_invalid_limit(self):
        from apps.catalogo.services.catalogo_service import fn_lookup_articoli

        with self.assertRaises(ServiceError) as ctx:
            fn_lookup_articoli(limit=0)
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: Create articolo valido -> insert + dettaglio finale.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_articolo_ok(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        repo = mock_repo_cls.return_value
        repo.create_articolo.return_value = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            "codice": "ART-001",
            "descrizione": "Articolo demo",
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_righe.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        result = fn_create_articolo(
            {"codice": "ART-001", "descrizione": "Articolo demo", "uom_id": 1}
        )

        self.assertEqual(result["codice"], "ART-001")
        repo.create_articolo.assert_called_once_with(
            {"codice": "ART-001", "descrizione": "Articolo demo", "uom_id": 1}
        )

    # Scopo: codice mancante in create -> ServiceError validazione.
    def test_fn_create_articolo_missing_codice(self):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_create_articolo({"descrizione": "Articolo demo", "uom_id": 1})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: uom_id mancante in create -> ServiceError validazione (NOT NULL DDL).
    def test_fn_create_articolo_missing_uom_id(self):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_create_articolo({"codice": "ART-001", "descrizione": "Articolo demo"})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("uom_id", ctx.exception.detail or "")

    # Scopo: duplicate codice -> traduzione IntegrityError in validazione catalogo.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_articolo_duplicate_codice(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        mock_repo_cls.return_value.create_articolo.side_effect = IntegrityError("uq_articoli_codice")

        with self.assertRaises(ServiceError) as ctx:
            fn_create_articolo(
                {"codice": "ART-001", "descrizione": "Articolo demo", "uom_id": 1}
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertEqual(ctx.exception.message, "Codice articolo gia' esistente.")
        self.assertEqual(ctx.exception.context.get("field"), "codice")

    # Scopo: composito e solo componente insieme -> il CHECK del DB
    #        (`chk_articoli_composito_non_solo_componente`, BE10 di
    #        brief-db-revisione-catalogo) diventa un 400 parlante, senza campo.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_articolo_composito_e_solo_componente(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        mock_repo_cls.return_value.create_articolo.side_effect = IntegrityError(
            "new row violates check constraint \"chk_articoli_composito_non_solo_componente\""
        )

        with self.assertRaises(ServiceError) as ctx:
            fn_create_articolo(
                {"codice": "ART-001", "descrizione": "Articolo demo", "uom_id": 1}
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("solo componente", ctx.exception.message)
        self.assertNotIn("field", ctx.exception.context)

    # Scopo: update articolo valido -> update delta e dettaglio riletto.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_update_articolo_ok(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        repo = mock_repo_cls.return_value
        repo.update_articolo.return_value = True
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            "codice": "ART-001",
            "descrizione": "Aggiornato",
            "descrizione_breve": None,
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_righe.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        result = fn_update_articolo(
            "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            {"descrizione": "Aggiornato", "descrizione_breve": ""},
        )

        self.assertEqual(result["descrizione"], "Aggiornato")
        repo.update_articolo.assert_called_once_with(
            "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            {"descrizione": "Aggiornato", "descrizione_breve": None},
        )

    # Scopo: tentativo di update codice -> errore per immutabilita'.
    def test_fn_update_articolo_codice_immutabile(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d", {"codice": "NEW"})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: tentativo di update uom_id -> errore per immutabilita' (lock_columns DDL).
    def test_fn_update_articolo_uom_id_immutabile(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d", {"uom_id": 99})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("uom_id", ctx.exception.detail or "")

    # Scopo: disattiva articolo -> update attivo=false e dettaglio finale.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_disattiva_articolo_ok(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_disattiva_articolo

        repo = mock_repo_cls.return_value
        repo.deactivate_articolo.return_value = True
        repo.get_articolo.side_effect = [
            {
                "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                "codice": "ART-001",
                "attivo": True,
            },
            {
                "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                "codice": "ART-001",
                "attivo": False,
            },
        ]
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_righe.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        result = fn_disattiva_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d")

        self.assertFalse(result["attivo"])
        repo.deactivate_articolo.assert_called_once_with("019bbee2-5f6a-704f-bbd0-34ed84db252d")

    # Scopo: articolo gia' inattivo -> risposta idempotente senza secondo update.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_disattiva_articolo_already_inactive(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_disattiva_articolo

        repo = mock_repo_cls.return_value
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            "codice": "ART-001",
            "attivo": False,
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_righe.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        result = fn_disattiva_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d")

        self.assertFalse(result["attivo"])
        repo.deactivate_articolo.assert_not_called()

    # Scopo: riattiva articolo inattivo -> chiama fn DB e restituisce dettaglio attivo.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_riattiva_articolo_ok(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_riattiva_articolo

        repo = mock_repo_cls.return_value
        repo.get_articolo.side_effect = [
            {"id": "019bbee2-5f6a-704f-bbd0-34ed84db252d", "codice": "ART-001", "attivo": False},
            {"id": "019bbee2-5f6a-704f-bbd0-34ed84db252d", "codice": "ART-001", "attivo": True},
        ]
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_righe.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        result = fn_riattiva_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d")

        self.assertTrue(result["attivo"])
        repo.reactivate_articolo.assert_called_once_with("019bbee2-5f6a-704f-bbd0-34ed84db252d")

    # Scopo: articolo gia' attivo -> idempotente, fn DB non chiamata.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_riattiva_articolo_already_active(self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_riattiva_articolo

        repo = mock_repo_cls.return_value
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            "codice": "ART-001",
            "attivo": True,
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_righe.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        result = fn_riattiva_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d")

        self.assertTrue(result["attivo"])
        repo.reactivate_articolo.assert_not_called()

    # Scopo: riattiva articolo inesistente -> NOT_FOUND uniforme dal pre-flight.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_riattiva_articolo_not_found(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_riattiva_articolo

        mock_repo_cls.return_value.get_articolo.return_value = None

        with self.assertRaises(ServiceError) as ctx:
            fn_riattiva_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d")
        self.assertEqual(ctx.exception.code, "E_CATALOGO_ARTICOLO_NOT_FOUND")
        mock_repo_cls.return_value.reactivate_articolo.assert_not_called()

    # Scopo: PATCH articolo con `attivo` -> rifiutato (Fase 7: solo endpoint dedicati).
    def test_fn_update_articolo_rifiuta_attivo(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo(
                "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                {"attivo": False},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("attivo", ctx.exception.detail or "")

    # Scopo: form-defaults articolo legge DEFAULT_IVA (chiave naturale) e ne
    # RISOLVE l'id sul lookup di `config.iva`.
    @patch("apps.catalogo.services.catalogo_service.resolve_config_id_by_codice_interno")
    @patch("apps.catalogo.services.catalogo_service.ParameterService")
    def test_fn_get_articolo_form_defaults_ok(self, mock_ps_cls, mock_resolve):
        from apps.catalogo.services.catalogo_service import fn_get_articolo_form_defaults

        mock_ps_cls.return_value.get_defaults.return_value = {"DEFAULT_IVA": "22"}
        mock_resolve.return_value = 42

        result = fn_get_articolo_form_defaults()

        self.assertEqual(result, {"default_iva_id": 42})
        mock_ps_cls.return_value.get_defaults.assert_called_once_with(
            ["DEFAULT_IVA"],
            django_user_id=None,
            group_ids=None,
            emittente_fiscale_id=None,
        )

    # Scopo: ⛔ IL CASO CHE DISCRIMINA, e senza di lui il rename sembrerebbe
    # gia' a posto. Il `codice_interno` e' `22`, cioe' un NUMERO: un lettore
    # rimasto indietro che facesse `int()` non fallirebbe — otterrebbe l'ID 22,
    # che oggi in `config.iva` non esiste ma che il modello ammette eccome, e il
    # giorno che esistesse sarebbe un'aliquota sbagliata proposta in silenzio su
    # un dato che finisce sui documenti fiscali. Qui il lookup dice 7, e a
    # vincere deve essere il lookup — mai il numero scritto nel parametro.
    @patch("apps.catalogo.services.catalogo_service.resolve_config_id_by_codice_interno")
    @patch("apps.catalogo.services.catalogo_service.ParameterService")
    def test_fn_get_articolo_form_defaults_non_casta_il_codice(
        self, mock_ps_cls, mock_resolve
    ):
        from apps.catalogo.services.catalogo_service import fn_get_articolo_form_defaults

        mock_ps_cls.return_value.get_defaults.return_value = {"DEFAULT_IVA": "22"}
        mock_resolve.return_value = 7

        result = fn_get_articolo_form_defaults()

        self.assertEqual(result, {"default_iva_id": 7})
        mock_resolve.assert_called_once()
        self.assertEqual(mock_resolve.call_args.args[0], "config.iva")
        self.assertEqual(mock_resolve.call_args.args[1], "22")

    # Scopo: parametro mancante -> default_iva_id a None (best-effort, no raise).
    # ⚠️ E il lookup NON deve nemmeno partire: interrogare il database per un
    # parametro che non c'e' e' un round-trip che non puo' rispondere.
    @patch("apps.catalogo.services.catalogo_service.resolve_config_id_by_codice_interno")
    @patch("apps.catalogo.services.catalogo_service.ParameterService")
    def test_fn_get_articolo_form_defaults_missing_param(self, mock_ps_cls, mock_resolve):
        from apps.catalogo.services.catalogo_service import fn_get_articolo_form_defaults

        mock_ps_cls.return_value.get_defaults.return_value = {}

        result = fn_get_articolo_form_defaults()

        self.assertEqual(result, {"default_iva_id": None})
        mock_resolve.assert_not_called()

    # Scopo: il codice non esiste (o l'aliquota e' disattivata) -> None, e il
    # form si apre lo stesso. ⚠️ E' il contratto best-effort di questa funzione:
    # far fallire il form-defaults spegnerebbe la creazione articolo per un
    # default mancante.
    @patch("apps.catalogo.services.catalogo_service.resolve_config_id_by_codice_interno")
    @patch("apps.catalogo.services.catalogo_service.ParameterService")
    def test_fn_get_articolo_form_defaults_codice_non_risolvibile(
        self, mock_ps_cls, mock_resolve
    ):
        from apps.catalogo.services.catalogo_service import fn_get_articolo_form_defaults

        mock_ps_cls.return_value.get_defaults.return_value = {"DEFAULT_IVA": "999"}
        mock_resolve.side_effect = ServiceError(
            code="E_CONFIG_MANCANTE", message="non trovato"
        )

        result = fn_get_articolo_form_defaults()

        self.assertEqual(result, {"default_iva_id": None})

    # Scopo: stringa vuota = assenza, non un codice da cercare.
    @patch("apps.catalogo.services.catalogo_service.resolve_config_id_by_codice_interno")
    @patch("apps.catalogo.services.catalogo_service.ParameterService")
    def test_fn_get_articolo_form_defaults_stringa_vuota(self, mock_ps_cls, mock_resolve):
        from apps.catalogo.services.catalogo_service import fn_get_articolo_form_defaults

        mock_ps_cls.return_value.get_defaults.return_value = {"DEFAULT_IVA": "  "}

        result = fn_get_articolo_form_defaults()

        self.assertEqual(result, {"default_iva_id": None})
        mock_resolve.assert_not_called()

    # Scopo: campi sconosciuti nel payload -> errore esplicito, non ignorati.
    def test_fn_create_articolo_unknown_key(self):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_create_articolo(
                {"codice": "ART-001", "descrizione": "Articolo demo", "descrizionee": "typo"}
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: FK float in PATCH -> errore, niente cast implicito a int.
    def test_fn_update_articolo_float_fk_invalid(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo("019bbee2-5f6a-704f-bbd0-34ed84db252d", {"uom_id": 1.2})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: create UoM operativa -> insert e rilettura riga arricchita.
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_uom_operativa_ok(self, mock_repo_cls, mock_uom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_uom_operativa

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        uom_repo = mock_uom_repo_cls.return_value
        uom_repo.create_uom_operativa.return_value = 11
        uom_repo.get_uom_operativa.return_value = {"id": 11, "uom_id": 3, "uom_codice": "PZ"}

        result = fn_create_uom_operativa("art-1", {"uom_id": 3, "factor_to_base": "1"})

        self.assertEqual(result["id"], 11)
        uom_repo.create_uom_operativa.assert_called_once()

    # Scopo: update UoM su riga assente -> 404 dominio catalogo.
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_update_uom_operativa_not_found(self, mock_repo_cls, mock_uom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_update_uom_operativa

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        mock_uom_repo_cls.return_value.update_uom_operativa.return_value = False

        with self.assertRaises(ServiceError) as ctx:
            fn_update_uom_operativa("art-1", 77, {"factor_to_base": "2"})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_UOM_NOT_FOUND")

    # Scopo: create componente -> insert e rilettura riga arricchita.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_componente_ok(self, mock_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_componente

        comp_id = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.create_componente.return_value = comp_id
        bom_repo.get_componente.return_value = {"id": comp_id, "coeff_qta": 1}

        result = fn_create_componente(
            "art-1",
            {"componente_id": comp_id, "coeff_qta": "1", "valido_dal": "2026-01-01"},
        )

        self.assertEqual(result["id"], comp_id)

    # Scopo: il legame che si sovrappone a uno in vigore (EXCLUDE
    #        `uq_articoli_componenti_no_overlap`) -> 400 parlante, senza campo
    #        (contano componente E periodo), e la violazione va nel diario.
    @patch("apps.core.services.error_manager.ErrorManager.log_error_only")
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_componente_periodo_sovrapposto(self, mock_repo_cls, mock_bom_repo_cls, mock_log):
        from apps.catalogo.services.catalogo_service import fn_create_componente

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        mock_bom_repo_cls.return_value.create_componente.side_effect = IntegrityError(
            'conflicting key value violates exclusion constraint "uq_articoli_componenti_no_overlap"'
        )

        with self.assertRaises(ServiceError) as ctx:
            fn_create_componente(
                "art-1",
                {"componente_id": "019bbee2-5f6a-704f-bbd0-34ed84db252d", "coeff_qta": "1",
                 "valido_dal": "2026-01-01"},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("periodo che si sovrappone", ctx.exception.message)
        self.assertNotIn("field", ctx.exception.context)
        self.assertEqual(
            mock_log.call_args.kwargs["function_name"], "catalogo.catalogo_service.fn_create_componente",
        )

    # Scopo: la stessa UoM in un periodo che si sovrappone a una mappatura
    #        gia' scritta (`uq_articoli_uom_operativa_no_overlap`, 23P01: la
    #        mappatura si versiona dal 2026-11-09) -> 400 parlante, senza campo:
    #        contano unita' E periodo.
    @patch("apps.core.services.error_manager.ErrorManager.log_error_only")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_uom_operativa_doppia(self, mock_repo_cls, mock_uom_repo_cls, _mock_log):
        from apps.catalogo.services.catalogo_service import fn_create_uom_operativa

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        mock_uom_repo_cls.return_value.create_uom_operativa.side_effect = IntegrityError(
            'conflicting key value violates exclusion constraint "uq_articoli_uom_operativa_no_overlap"'
        )

        with self.assertRaises(ServiceError) as ctx:
            fn_create_uom_operativa("art-1", {"uom_id": 3, "factor_to_base": "1"})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("periodo che si sovrappone", ctx.exception.message)
        self.assertNotIn("field", ctx.exception.context)

    # Scopo: `is_base` (la base nasce con l'articolo, D12), `rounding_mode` e
    #        `require_lot` (ritirate, Q4) sono fuori contratto: 400 prima del
    #        repository, in creazione e in modifica.
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_uom_operativa_campi_ritirati_sono_fuori_contratto(self, mock_repo_cls, mock_uom_repo_cls):
        from apps.catalogo.services.catalogo_service import (
            fn_create_uom_operativa,
            fn_update_uom_operativa,
        )

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        for campo, valore in (("is_base", True), ("rounding_mode", "HALF_UP"), ("require_lot", False)):
            with self.subTest(campo=campo, verso="create"), self.assertRaises(ServiceError) as ctx:
                fn_create_uom_operativa("art-1", {"uom_id": 3, "factor_to_base": "2", campo: valore})
            self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
            with self.subTest(campo=campo, verso="update"), self.assertRaises(ServiceError) as ctx:
                fn_update_uom_operativa("art-1", 10, {campo: valore})
            self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        mock_uom_repo_cls.return_value.create_uom_operativa.assert_not_called()
        mock_uom_repo_cls.return_value.update_uom_operativa.assert_not_called()

    # Scopo: la riga base con un fattore diverso da 1 (o con date) la rifiuta il
    #        CHECK `chk_articoli_uom_operativa_base_fissa` -> la frase del
    #        dominio, senza campo (BE1: la copia parziale del service e' uscita).
    @patch("apps.core.services.error_manager.ErrorManager.log_error_only")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_update_uom_operativa_riga_base_fissa(self, mock_repo_cls, mock_uom_repo_cls, _mock_log):
        from apps.catalogo.services.catalogo_service import fn_update_uom_operativa

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        mock_uom_repo_cls.return_value.update_uom_operativa.side_effect = IntegrityError(
            'new row for relation "articoli_uom_operativa" violates check constraint '
            '"chk_articoli_uom_operativa_base_fissa"'
        )

        with self.assertRaises(ServiceError) as ctx:
            fn_update_uom_operativa("art-1", 10, {"factor_to_base": "2"})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("unita' base", ctx.exception.message)
        self.assertNotIn("field", ctx.exception.context)

    # Scopo: una conversione fra le stesse due unita', anche nel verso opposto,
    #        in un periodo che si sovrappone (`ex_unita_misura_conversioni_coppia_no_overlap`,
    #        23P01) -> la frase del dominio, riconosciuta per NOME e non dal testo.
    @patch("apps.core.services.error_manager.ErrorManager.log_error_only")
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_conversione_coppia_sovrapposta(self, mock_repo_cls, _mock_log):
        from apps.catalogo.services.catalogo_service import fn_create_conversione

        mock_repo_cls.return_value.create_conversione.side_effect = IntegrityError(
            'conflicting key value violates exclusion constraint "ex_unita_misura_conversioni_coppia_no_overlap"'
        )
        with self.assertRaises(ServiceError) as ctx:
            fn_create_conversione({"uom_from_id": 1, "uom_to_id": 2, "fattore": "1000"})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("in uno dei due versi", ctx.exception.message)
        self.assertNotIn("field", ctx.exception.context)

    # Scopo: un rifiuto del DB col suo codice (il guard delle tipologie,
    #        `E_UOM_CONVERSIONE_TIPO_DIVERSO`) passa intatto al middleware: il
    #        service non lo riveste col ripiego.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_conversione_rifiuto_col_codice_passa_intatto(self, mock_repo_cls):
        from django.db import DatabaseError

        from apps.catalogo.services.catalogo_service import fn_create_conversione

        errore = DatabaseError("E_UOM_CONVERSIONE_TIPO_DIVERSO: le due unita' hanno tipologie diverse")
        mock_repo_cls.return_value.create_conversione.side_effect = errore
        with self.assertRaises(DatabaseError) as ctx:
            fn_create_conversione({"uom_from_id": 1, "uom_to_id": 2, "fattore": "1000"})
        self.assertIs(ctx.exception, errore)

    # Scopo: tentativo di update componente_id -> errore per immutabilita'.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_update_componente_immutabile(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_update_componente

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        with self.assertRaises(ServiceError) as ctx:
            fn_update_componente(
                "art-1",
                "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                {"componente_id": "00000000-0000-0000-0000-000000000000"},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: create nota articolo -> insert e rilettura nota arricchita.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_nota_articolo_ok(self, mock_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_nota_articolo

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        bom_repo = mock_bom_repo_cls.return_value
        # Il servizio scrive con `create_nota` (target ARTICOLO): il vecchio
        # `create_nota_articolo` non esiste, e il 5 non arrivava mai.
        bom_repo.create_nota.return_value = 5
        # Shape allineata al pattern partizionato vendite (2026-05-22):
        # alias senza prefisso `nota_` (id/testo invece di nota_id/nota_testo).
        bom_repo.get_nota_articolo.return_value = {"id": 5, "testo": "Demo"}

        result = fn_create_nota_articolo("art-1", {"id_stile": 1, "testo": "Demo"})

        self.assertEqual(result["id"], 5)
        bom_repo.get_nota_articolo.assert_called_once_with("art-1", 5)

    # Scopo: create nota articolo senza target_riga_id -> anchor_tipo/posizione
    # default DOCUMENTO/HEADER applicati dal service (allineamento col pattern
    # vendite PartitionedNoteService). Verifica che il payload passato al repo
    # contenga i default — senza questi i NOT NULL DB su anchor_tipo/posizione
    # rifiuterebbero l'INSERT (regression check per il bug E_CATALOGO_VALIDATION
    # rilevato durante lo smoke Fase 2.B del refactor UI drawer).
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_nota_articolo_default_documento_header(self, mock_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_nota_articolo

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.create_nota.return_value = 5
        bom_repo.get_nota_articolo.return_value = {"id": 5}

        fn_create_nota_articolo("art-1", {"id_stile": 1, "testo_md": "Demo"})

        # Verifica argomento `data` passato al repo: deve contenere i default.
        bom_repo.create_nota.assert_called_once()
        _, _, data_arg = bom_repo.create_nota.call_args.args
        self.assertEqual(data_arg["anchor_tipo"], "DOCUMENTO")
        self.assertEqual(data_arg["posizione"], "HEADER")

    # Scopo: create nota componente con target_riga_id -> anchor_tipo/posizione
    # default RIGA/AFTER applicati dal service.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    def test_fn_create_nota_componente_default_riga_after(self, mock_bom_repo_cls, _mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_nota_componente

        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.create_nota.return_value = 7
        bom_repo.get_nota_componente.return_value = {"id": 7}

        riga_uuid = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        fn_create_nota_componente(
            "art-1", "comp-1",
            {"id_stile": 1, "testo_md": "Demo", "target_riga_id": riga_uuid},
        )

        bom_repo.create_nota.assert_called_once()
        _, _, data_arg = bom_repo.create_nota.call_args.args
        self.assertEqual(data_arg["anchor_tipo"], "RIGA")
        self.assertEqual(data_arg["posizione"], "AFTER")
        self.assertEqual(str(data_arg["target_riga_id"]), riga_uuid)

    # Scopo: ⛔ un componente che non e' dell'articolo dell'URL e' un 404, e le
    #        note non si leggono ne' si scrivono (2026-10-21, §B8 del
    #        brief-be-verifica-documentazione-api): prima `articolo_id` del path
    #        era ignorato.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    def test_note_componente_di_un_altro_articolo_404(self, mock_bom_repo_cls, _mock_repo_cls):
        from apps.catalogo.services.catalogo_service import (
            fn_create_nota_componente,
            fn_list_note_componente,
        )

        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.get_componente.return_value = None
        for chiamata in (
            lambda: fn_list_note_componente("art-1", "comp-di-altro"),
            lambda: fn_create_nota_componente("art-1", "comp-di-altro", {"id_stile": 1, "testo_md": "x"}),
        ):
            with self.subTest(), self.assertRaises(ServiceError) as ctx:
                chiamata()
            self.assertEqual(ctx.exception.code, "E_CATALOGO_COMPONENTE_NOT_FOUND")
        bom_repo.get_componente.assert_called_with("art-1", "comp-di-altro")
        bom_repo.list_note_componente.assert_not_called()
        bom_repo.create_nota.assert_not_called()

    # Scopo: create nota con coppia incoerente anchor_tipo='DOCUMENTO' +
    # target_riga_id valorizzato -> errore E_CATALOGO_VALIDATION (guard
    # defense-in-depth simmetrica a vendite).
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_nota_articolo_anchor_riga_inconsistency(self, mock_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_nota_articolo

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        del mock_bom_repo_cls  # repo non viene mai chiamato

        riga_uuid = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        with self.assertRaises(ServiceError) as ctx:
            fn_create_nota_articolo(
                "art-1",
                {
                    "id_stile": 1,
                    "testo_md": "Demo",
                    "anchor_tipo": "DOCUMENTO",
                    "target_riga_id": riga_uuid,
                },
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: update nota inesistente -> 404 dominio catalogo.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    def test_fn_update_nota_not_found(self, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_update_nota

        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.resolve_nota.return_value = []

        with self.assertRaises(ServiceError) as ctx:
            fn_update_nota(999, {"testo": "Aggiornata"})
        self.assertEqual(ctx.exception.code, "E_CATALOGO_NOTA_NOT_FOUND")

    # Scopo: create componente self-reference -> errore anticipato senza delega al DB.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_componente_self_reference(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_componente

        article_id = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        mock_repo_cls.return_value.get_articolo.return_value = {
            "id": article_id,
            "codice": "ART-001",
        }

        with self.assertRaises(ServiceError) as ctx:
            fn_create_componente(
                article_id,
                {"componente_id": article_id, "coeff_qta": "1", "valido_dal": "2026-01-01"},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")

    # Scopo: create articolo con listino_tipologia_id -> campo propagato al repo (pricing v5).
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_articolo_listino_tipologia_id_ok(
        self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls
    ):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        repo = mock_repo_cls.return_value
        repo.create_articolo.return_value = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            "codice": "ART-001",
            "descrizione": "Articolo demo",
            "listino_tipologia_id": 3,
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_righe.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        fn_create_articolo(
            {
                "codice": "ART-001",
                "descrizione": "Articolo demo",
                "uom_id": 1,
                "listino_tipologia_id": 3,
            }
        )

        repo.create_articolo.assert_called_once_with(
            {
                "codice": "ART-001",
                "descrizione": "Articolo demo",
                "uom_id": 1,
                "listino_tipologia_id": 3,
            }
        )

    # Scopo: update articolo con listino_tipologia_id non intero -> validazione.
    def test_fn_update_articolo_listino_tipologia_id_invalid(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo(
                "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                {"listino_tipologia_id": 1.5},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("listino_tipologia_id", ctx.exception.detail or "")

    # Scopo: create articolo con natura_vendita_id -> campo propagato al repo
    # (modello split per natura: instradamento ordine/commessa/contratto).
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_articolo_natura_vendita_id_ok(
        self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls
    ):
        from apps.catalogo.services.catalogo_service import fn_create_articolo

        repo = mock_repo_cls.return_value
        repo.create_articolo.return_value = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            "codice": "SERV-001",
            "descrizione": "Servizio una tantum demo",
            "natura_vendita_id": 2,
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_righe.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        fn_create_articolo(
            {
                "codice": "SERV-001",
                "descrizione": "Servizio una tantum demo",
                "uom_id": 1,
                "natura_vendita_id": 2,
            }
        )

        repo.create_articolo.assert_called_once_with(
            {
                "codice": "SERV-001",
                "descrizione": "Servizio una tantum demo",
                "uom_id": 1,
                "natura_vendita_id": 2,
            }
        )

    # Scopo: update articolo con natura_vendita_id null -> validazione (colonna
    # NOT NULL: la natura si puo' cambiare ma mai azzerare).
    def test_fn_update_articolo_natura_vendita_id_null_invalid(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo(
                "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                {"natura_vendita_id": None},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertIn("natura_vendita_id", ctx.exception.detail or "")

    # Scopo: Blocco B di brief-db-modifiche-certe-ciclo-vendita-e-articolo —
    #        i tre campi «da dove arriva l'articolo» arrivano al repository con
    #        il loro tipo: il modo come id, il flag come bool, il lead time come
    #        int (0 e' un valore, non «non si applica»; NULL si').
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_update_articolo_approvvigionamento_propagato(
        self, mock_repo_cls, mock_uom_repo_cls, mock_bom_repo_cls
    ):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        repo = mock_repo_cls.return_value
        repo.update_articolo.return_value = True
        repo.get_articolo.return_value = {
            "id": "019bbee2-5f6a-704f-bbd0-34ed84db252d", "codice": "ART-001",
        }
        mock_uom_repo_cls.return_value.list_uom_operative.return_value = []
        mock_bom_repo_cls.return_value.list_righe.return_value = []
        mock_bom_repo_cls.return_value.list_note_articolo.return_value = []

        fn_update_articolo(
            "019bbee2-5f6a-704f-bbd0-34ed84db252d",
            {"modo_approvvigionamento_id": 2, "gestito_a_magazzino": True,
             "lead_time_giorni": 0, "requires_lotto": True},
        )
        _, data = repo.update_articolo.call_args.args
        self.assertEqual(data["modo_approvvigionamento_id"], 2)
        self.assertIs(data["gestito_a_magazzino"], True)
        self.assertEqual(data["lead_time_giorni"], 0)
        # Lotto 2 di magazzino (brief §4.9): `requires_lotto` e' un flag come
        # `gestito_a_magazzino` — passa, e fuori dal lock BoM.
        self.assertIs(data["requires_lotto"], True)

        # E il NULL del lead time e' un'informazione («non si applica»): passa.
        repo.update_articolo.reset_mock()
        fn_update_articolo(
            "019bbee2-5f6a-704f-bbd0-34ed84db252d", {"lead_time_giorni": None},
        )
        _, data = repo.update_articolo.call_args.args
        self.assertIsNone(data["lead_time_giorni"])

    # Scopo: `modo_approvvigionamento_id` e' NOT NULL a DB (DEFAULT ACQUISTO):
    #        si puo' cambiare, mai azzerare — stessa regola di natura_vendita_id.
    def test_fn_update_articolo_modo_approvvigionamento_null_invalid(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo(
                "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                {"modo_approvvigionamento_id": None},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "modo_approvvigionamento_id")

    # Scopo: il CHECK `>= 0` sul lead time e' anticipato con un 400 che nomina
    #        il campo, invece del «violazione vincoli articolo» generico.
    def test_fn_update_articolo_lead_time_negativo_invalid(self):
        from apps.catalogo.services.catalogo_service import fn_update_articolo

        with self.assertRaises(ServiceError) as ctx:
            fn_update_articolo(
                "019bbee2-5f6a-704f-bbd0-34ed84db252d",
                {"lead_time_giorni": -1},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "lead_time_giorni")

    # Scopo: create componente con esposizione_in_fattura -> codice propagato
    # al repo com'e' (dal 2026-10-01 un codice, non un booleano; i valori li
    # giudica la FK su config.esposizioni_componente).
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_componente_esposizione_in_fattura_ok(self, mock_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_componente

        comp_id = "019bbee2-5f6a-704f-bbd0-34ed84db252e"
        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.create_componente.return_value = comp_id
        bom_repo.get_componente.return_value = {"id": comp_id, "esposizione_in_fattura": "VALORIZZATO"}

        fn_create_componente(
            "art-1",
            {
                "componente_id": comp_id,
                "coeff_qta": "1",
                "valido_dal": "2026-01-01",
                "esposizione_in_fattura": "VALORIZZATO",
            },
        )

        args, _ = bom_repo.create_componente.call_args
        self.assertEqual(args[1]["esposizione_in_fattura"], "VALORIZZATO")

    # Scopo: il booleano ritirato non e' piu' una chiave ammessa: chi lo manda
    # ancora riceve un 400 che lo nomina, non un salvataggio che lo ignora.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_componente_booleano_ritirato_rifiutato(self, mock_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_componente

        comp_id = "019bbee2-5f6a-704f-bbd0-34ed84db252e"
        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}

        with self.assertRaises(ServiceError) as ctx:
            fn_create_componente(
                "art-1",
                {"componente_id": comp_id, "coeff_qta": "1", "esposto_in_fattura": True},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        mock_bom_repo_cls.return_value.create_componente.assert_not_called()

    # Scopo: l'esposizione e' NOT NULL a DB: un `null` esplicito si ferma nel
    # service con il campo nominato.
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_componente_esposizione_null_rifiutata(self, mock_repo_cls, mock_bom_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_create_componente

        comp_id = "019bbee2-5f6a-704f-bbd0-34ed84db252e"
        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}

        with self.assertRaises(ServiceError) as ctx:
            fn_create_componente(
                "art-1",
                {"componente_id": comp_id, "coeff_qta": "1", "esposizione_in_fattura": None},
            )
        self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION")
        self.assertEqual(ctx.exception.context.get("field"), "esposizione_in_fattura")

    # =================================================================
    # Fase 4 — fallback valido_dal=today lato service (DB declined)
    # =================================================================

    # Scopo: payload create componente senza valido_dal -> service applica
    # oggi_aziendale() prima del repository call. Il DDL DB non ha
    # DEFAULT CURRENT_DATE, il fallback vive nel service (Fase 4 BE-only).
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_componente_valido_dal_fallback_today(self, mock_repo_cls, mock_bom_repo_cls):

        from apps.catalogo.services.catalogo_service import fn_create_componente

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1"}
        bom_repo = mock_bom_repo_cls.return_value
        bom_repo.create_componente.return_value = "comp-1"
        bom_repo.get_componente.return_value = {"id": "comp-1"}

        # Payload SENZA valido_dal: il service deve applicare today.
        fn_create_componente(
            "art-1",
            {"componente_id": "019bbee2-5f6a-704f-bbd0-34ed84db252f", "coeff_qta": "1"},
        )

        args = bom_repo.create_componente.call_args.args
        self.assertEqual(args[1]["valido_dal"], oggi_aziendale())

    # Scopo: payload create UoM operativa senza valido_dal -> service applica today.
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_uom_operativa_valido_dal_fallback_today(self, mock_repo_cls, mock_uom_repo_cls):

        from apps.catalogo.services.catalogo_service import fn_create_uom_operativa

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1"}
        uom_repo = mock_uom_repo_cls.return_value
        uom_repo.create_uom_operativa.return_value = 99
        uom_repo.get_uom_operativa.return_value = {"id": 99}

        # Payload SENZA valido_dal.
        fn_create_uom_operativa("art-1", {"uom_id": 1, "factor_to_base": "1"})

        args = uom_repo.create_uom_operativa.call_args.args
        self.assertEqual(args[1]["valido_dal"], oggi_aziendale())

    # Scopo: payload create conversione UoM senza valido_dal -> service applica today.
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_create_conversione_valido_dal_fallback_today(self, mock_repo_cls):

        from apps.catalogo.services.catalogo_service import fn_create_conversione

        repo = mock_repo_cls.return_value
        repo.create_conversione.return_value = 42
        repo.get_conversione.return_value = {"id": 42}

        # Payload SENZA valido_dal.
        fn_create_conversione({"uom_from_id": 1, "uom_to_id": 2, "fattore": "10"})

        args = repo.create_conversione.call_args.args
        self.assertEqual(args[0]["valido_dal"], oggi_aziendale())

    # =================================================================
    # Fase 5 — non_editable_fields nei detail (cross-vista DB + gap Python)
    # =================================================================

    # Scopo: detail articolo include non_editable_fields, e `codice` arriva
    # dal DB, non da un gap Python (BE2 di brief-db-revisione-dbops: dal giro
    # 10a la vista legge il lock vivo, e il gap che lo ripeteva e' uscito).
    # Il dettaglio legge il ramo PER RECORD (lock statici + condizionali).
    # Che la vista lo dichiari davvero lo prova `test_lock_columns_vivo_db`.
    @patch(_LOCK_REPO, autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_get_articolo_includes_non_editable_fields(
        self, mock_repo_cls, mock_uom_cls, mock_bom_cls, mock_lock_cls,
    ):
        from apps.catalogo.services.catalogo_service import fn_get_articolo

        mock_repo_cls.return_value.get_articolo.return_value = {"id": 1, "is_composito": False}
        mock_uom_cls.return_value.list_uom_operative.return_value = []
        mock_bom_cls.return_value.list_note_articolo.return_value = []

        for db_locked, attesi in (
            (("codice", "uom_id"), ["codice", "uom_id"]),
            # ⛔ Senza il lock del DB `codice` NON compare: nessun gap Python
            #    lo ripete piu'. Se torna, e' rinata la seconda sede.
            ((), []),
        ):
            with self.subTest(db_locked=db_locked):
                mock_lock_cls.list_non_editable_for_record.return_value = db_locked
                result = fn_get_articolo(1)
                self.assertEqual(result["non_editable_fields"], attesi)

    # Scopo: lista UoM operative espone non_editable_fields envelope-level.
    @patch(_LOCK_REPO, autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_list_uom_operative_envelope_non_editable_fields(
        self, mock_repo_cls, mock_uom_cls, mock_lock_cls,
    ):
        from apps.catalogo.services.catalogo_service import fn_list_uom_operative

        mock_repo_cls.return_value.get_articolo.return_value = {"id": 1}
        mock_uom_cls.return_value.list_uom_operative.return_value = []
        mock_lock_cls.list_non_editable.return_value = ()

        result = fn_list_uom_operative(1)

        self.assertEqual(result["non_editable_fields"], ["uom_id"])

    # Scopo: detail conversione UoM include non_editable_fields (uom_from_id, uom_to_id).
    @patch(_LOCK_REPO, autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_get_conversione_includes_non_editable_fields(self, mock_repo_cls, mock_lock_cls):
        from apps.catalogo.services.catalogo_service import fn_get_conversione

        mock_repo_cls.return_value.get_conversione.return_value = {"id": 7}
        mock_lock_cls.list_non_editable.return_value = ()

        result = fn_get_conversione(7)

        self.assertEqual(result["non_editable_fields"], ["uom_from_id", "uom_to_id"])

    # Scopo: lista articoli propaga capability BoM dalla vista DB (Fase 6).
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_list_articoli_proietta_capability_bom(self, mock_repo_cls):
        from apps.catalogo.services.catalogo_service import fn_list_articoli

        mock_repo_cls.return_value.list_articoli.return_value = (
            [
                {
                    "id": 1,
                    "codice": "ART-COMP",
                    "is_composito": True,
                    "is_solo_componente": False,
                    "puo_gestire_bom": True,
                    "motivo_non_gestibile_bom": None,
                },
                {
                    "id": 2,
                    "codice": "ART-FOGLIA",
                    "is_composito": False,
                    "is_solo_componente": False,
                    "puo_gestire_bom": False,
                    "motivo_non_gestibile_bom": "ARTICOLO_NON_COMPOSITO",
                },
            ],
            2,
        )

        results, total = fn_list_articoli(limit=25, offset=0)

        self.assertEqual(total, 2)
        self.assertTrue(results[0]["puo_gestire_bom"])
        self.assertIsNone(results[0]["motivo_non_gestibile_bom"])
        self.assertFalse(results[1]["puo_gestire_bom"])
        self.assertEqual(results[1]["motivo_non_gestibile_bom"], "ARTICOLO_NON_COMPOSITO")

    # Scopo: lista UoM operative propaga capability eliminazione dalla vista DB (Fase 6).
    @patch(_LOCK_REPO, autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_fn_list_uom_operative_proietta_capability_eliminabile(
        self, mock_repo_cls, mock_uom_cls, mock_lock_cls,
    ):
        from apps.catalogo.services.catalogo_service import fn_list_uom_operative

        mock_repo_cls.return_value.get_articolo.return_value = {"id": 1}
        mock_uom_cls.return_value.list_uom_operative.return_value = [
            {
                "id": 10,
                "uom_codice": "PZ",
                "is_base": True,
                "puo_eliminarsi": False,
                "motivo_non_eliminabile": "UOM_BASE_NON_ELIMINABILE",
            },
            {
                "id": 11,
                "uom_codice": "CT",
                "is_base": False,
                "puo_eliminarsi": True,
                "motivo_non_eliminabile": None,
            },
        ]
        mock_lock_cls.list_non_editable.return_value = ()

        result = fn_list_uom_operative(1)

        rows = result["results"]
        self.assertFalse(rows[0]["puo_eliminarsi"])
        self.assertEqual(rows[0]["motivo_non_eliminabile"], "UOM_BASE_NON_ELIMINABILE")
        self.assertTrue(rows[1]["puo_eliminarsi"])
        self.assertIsNone(rows[1]["motivo_non_eliminabile"])

    # Scopo: 57. ⛔ Dal 2026-09-26 i repository del catalogo scrivono col BB
    #    `execute_dynamic_insert`/`execute_dynamic_update`/`sql_set_clause`, a
    #    whitelist RIGIDA: una chiave fuori lista e' un `RuntimeError` (500),
    #    non piu' uno scarto silenzioso. Il 400 educato lo deve dare il service,
    #    PRIMA del repository — per ogni scrittura, comprese le chiavi che il
    #    repository scrive da se' (padre dal path, partizione della nota).
    @patch("apps.catalogo.services.catalogo_service._resolve_single_nota")
    @patch("apps.catalogo.services.catalogo_service.CatalogoUomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoBomRepository", autospec=True)
    @patch("apps.catalogo.services.catalogo_service.CatalogoRepository", autospec=True)
    def test_chiave_fuori_contratto_e_un_400_prima_del_repository(
        self, mock_repo_cls, mock_bom_cls, mock_uom_cls, mock_resolve,
    ):
        from apps.catalogo.services import catalogo_service as svc

        mock_repo_cls.return_value.get_articolo.return_value = {"id": "art-1", "codice": "ART-001"}
        mock_resolve.return_value = {"nota_target_tipo": "ARTICOLO", "nota_target_id": "art-1"}
        comp = "019bbee2-5f6a-704f-bbd0-34ed84db252d"
        casi = (
            ("update_articolo", lambda: svc.fn_update_articolo("art-1", {"descrizione": "x", "estranea": 1})),
            ("create_uom_operativa", lambda: svc.fn_create_uom_operativa("art-1", {"uom_id": 3, "articolo_id": "altro"})),
            ("update_uom_operativa", lambda: svc.fn_update_uom_operativa("art-1", 7, {"qty_step": "1", "estranea": 1})),
            ("create_componente", lambda: svc.fn_create_componente(
                "art-1", {"componente_id": comp, "coeff_qta": "1", "prodotto_id": "altro"},
            )),
            ("update_componente", lambda: svc.fn_update_componente("art-1", comp, {"coeff_qta": "2", "estranea": 1})),
            ("create_nota", lambda: svc.fn_create_nota_articolo(
                "art-1", {"testo": "t", "id_stile": 1, "target_tipo": "ARTICOLO_COMPONENTE"},
            )),
            ("update_nota", lambda: svc.fn_update_nota(5, {"testo": "t", "target_id": "altro"})),
            ("update_uom_tipo", lambda: svc.fn_update_uom_tipo(1, {"descrizione": "x", "codice": "Y"})),
            ("update_unita_misura", lambda: svc.fn_update_unita_misura(1, {"descrizione": "x", "codice": "Y"})),
            ("update_conversione", lambda: svc.fn_update_conversione(1, {"fattore": "2", "uom_from_id": 3})),
        )
        for nome, chiama in casi:
            with self.subTest(nome), self.assertRaises(ServiceError) as ctx:
                chiama()
            self.assertEqual(ctx.exception.code, "E_CATALOGO_VALIDATION", nome)

        # Nessuna scrittura e' arrivata al repository.
        for repo in (mock_repo_cls, mock_bom_cls, mock_uom_cls):
            scritture = [
                c for c in repo.return_value.method_calls
                if c[0].startswith(("create_", "update_"))
            ]
            self.assertEqual(scritture, [], "una chiave fuori contratto ha raggiunto il repository")

    # 58. ⛔ `catalogo.note.meta` e' NOT NULL DEFAULT '{}': `meta: null` dal
    #     client e' «nessun metadato», cioe' `{}`. Prima arrivava NULL al DB e
    #     la scrittura falliva sul vincolo.
    def test_nota_meta_null_diventa_oggetto_vuoto(self):
        from apps.catalogo.services.catalogo_service import _extract_nota_payload

        for for_update in (False, True):
            with self.subTest(for_update=for_update):
                data = _extract_nota_payload(
                    {"testo": "x", "id_stile": 1, "meta": None},
                    for_update=for_update, function_name="t",
                )
                self.assertEqual(data["meta"], {})
