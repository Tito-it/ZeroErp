# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Test unit per `DocumentiRepository` lato asset documentali
#        (Tranche G - debito test H1). Mocka `connection.cursor`
#        per non richiedere DB reale (regola CI). Verifica:
#        - list_asset: count + data + filtri (attivo, asset_tipo_id,
#          emittente, ricerca libera dal catalogo della lista) + scope ANY(%s) + paginazione
#          deterministica (id ASC tiebreaker) + cap LIMIT 200;
#        - list_asset: order_by fuori whitelist -> E_DOCUMENTI_VALIDATION
#          senza toccare il DB (defense-in-depth);
#        - get_asset: WHERE su id (+ scope opzionale), ritorna None se
#          assente (il service traduce in 404 unificato);
#        - create_asset: INSERT con sole colonne whitelisted in
#          ASSET_CREATE_COLUMNS, RETURNING id;
#        - update_asset_metadati: UPDATE su sole colonne whitelisted in
#          ASSET_UPDATE_COLUMNS (chiavi file/anag: RuntimeError dal
#          2026-09-26, prima scartate in silenzio), True se rowcount > 0, False se
#          data vuoto senza eseguire SQL;
#        - get_tipo_asset: SELECT su tipi_asset_documento per id, dict
#          ritornato con id/codice_interno/attivo, None se inesistente.
#
# Indice test (0..N):
#   0. list_asset_basic_no_filters
#   1. list_asset_applies_filters_and_search_dal_catalogo
#   1-bis. list_asset_utilizzabili_usa_la_condizione_del_render
#   2. list_asset_applies_emittente_scope_anyarray
#   3. list_asset_paginazione_deterministica_id_tiebreaker
#   4. list_asset_invalid_order_by_raises_validation_no_db
#   4-bis. list_asset_order_dir_maiuscola_ammessa
#   4-ter. list_asset_order_dir_estranea_rifiutata_no_db
#   5. get_asset_returns_row_or_none
#   6. get_asset_with_scope_passes_anyarray
#   7. create_asset_inserts_only_whitelisted_columns_returns_id
#   7-bis. create_asset_chiave_fuori_whitelist_rifiutata
#   8. update_asset_metadati_returns_true_on_success
#   9. update_asset_metadati_returns_false_on_empty_data_no_sql
#  10. update_asset_metadati_filters_only_whitelisted_columns (ora: RuntimeError)
#  11. get_tipo_asset_returns_dict_or_none
# ------------------------------------------------------------

from __future__ import annotations

from typing import Any
from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.core.services.service_errors import ServiceError
from apps.core.tests.ricerca_catalogo_fakes import catalogo_ricerca_finto
from apps.documenti.db.documenti_repository import DocumentiRepository


# Scopo: Costruisce un cursor MagicMock con context manager + sequenza
#        programmata di execute/fetch. `description` viene aggiornata
#        per attributo a ogni execute (no PropertyMock che leakerebbe
#        cross-test alla classe MagicMock globale).
def _mk_cursor(
    *,
    fetchone_results: list[Any] | None = None,
    fetchall_results: list[list[tuple]] | None = None,
    descriptions: list[list[Any]] | None = None,
) -> MagicMock:
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    state = {"call": -1}

    def _on_execute(_sql, _params=None):
        state["call"] += 1
        if descriptions and state["call"] < len(descriptions):
            cursor.description = descriptions[state["call"]]
        else:
            cursor.description = []

    cursor.execute.side_effect = _on_execute
    cursor.fetchone.side_effect = lambda: (
        fetchone_results[state["call"]]
        if fetchone_results and state["call"] < len(fetchone_results)
        else None
    )
    cursor.fetchall.side_effect = lambda: (
        fetchall_results[state["call"]]
        if fetchall_results and state["call"] < len(fetchall_results)
        else []
    )
    return cursor


# Scopo: psycopg espone description come lista di Column con attributo `.name`.
def _columns(*names: str) -> list[Any]:
    cols = []
    for n in names:
        m = MagicMock()
        m.name = n
        cols.append(m)
    return cols


class DocumentiRepositoryListAssetTests(TestCase):
    """Test list_asset: count + data + filtri + scope + paginazione."""

    # Scopo: Set di argomenti di default per list_asset, override-friendly.
    def _list_default_args(self, **overrides: Any) -> dict[str, Any]:
        defaults: dict[str, Any] = {
            "attivo": True,
            "asset_tipo_id": None,
            "emittente_fiscale_id": None,
            "search": None,
            "emittente_ids_scope": None,
            "order_by": "codice",
            "order_dir": "asc",
            "limit": 50,
            "offset": 0,
        }
        defaults.update(overrides)
        return defaults

    # 0. baseline: solo `attivo=True` come WHERE; SQL count+data eseguiti
    #    e ORDER BY usa il tiebreaker `a.id ASC`.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_asset_basic_no_filters(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(2,), None],
            descriptions=[[], _columns("id", "codice")],
            fetchall_results=[[], [(1, "L1"), (2, "L2")]],
        )
        mocked_factory.return_value = cursor

        rows, total = DocumentiRepository().list_asset(**self._list_default_args())

        self.assertEqual(total, 2)
        self.assertEqual(rows, [{"id": 1, "codice": "L1"}, {"id": 2, "codice": "L2"}])
        self.assertEqual(cursor.execute.call_count, 2)
        data_sql = cursor.execute.call_args_list[1].args[0]
        self.assertIn("ORDER BY a.codice ASC NULLS FIRST, a.id ASC", data_sql)
        self.assertIn("s_ef.ragione_sociale_completa", data_sql)
        self.assertIn("AS emittente_ragione_sociale", data_sql)
        self.assertIn("LEFT JOIN anagrafiche.soggetti_ruoli sr_ef", data_sql)

    # 1. filtri valorizzati e ricerca libera entrano nei params nell'ordine
    #    corretto. Le colonne della ricerca le accende il catalogo della lista
    #    (BB `add_ricerca_full_condition`, lettura mockata qui): codice,
    #    descrizione e nome file. ⛔ Il `codice_interno` non si cerca (Tid,
    #    2026-09-23): fino al 2026-09-24 la ricerca scritta a mano lo cercava.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_asset_applies_filters_and_search_dal_catalogo(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(0,), None],
            descriptions=[[], _columns("id")],
            fetchall_results=[[], []],
        )
        mocked_factory.return_value = cursor

        # Catalogo finto: le colonne che la lista accende.
        with catalogo_ricerca_finto(["codice", "descrizione", "file_name"]):
            DocumentiRepository().list_asset(
                **self._list_default_args(
                    attivo=False,
                    asset_tipo_id=4,
                    emittente_fiscale_id=11,
                    search="logo",
                )
            )

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("a.attivo = %s", sql)
        self.assertIn("a.asset_tipo_id = %s", sql)
        self.assertIn("a.emittente_fiscale_id = %s", sql)
        # Ricerca sulle 3 colonne accese a catalogo, mai sul codice interno.
        self.assertEqual(sql.count("ILIKE %s"), 3)
        self.assertIn("(a.file_name)::text ILIKE %s", sql)
        self.assertNotIn("codice_interno", sql.split("WHERE", 1)[1])
        self.assertEqual(
            params,
            [False, 4, 11, "%logo%", "%logo%", "%logo%"],
        )

    # 1-bis. Il filtro `utilizzabili` usa la STESSA condizione con cui il
    #        render risolve `asset:` (la prova che le due letture concordano
    #        sul DB vero e' in tests/db/test_asset_per_render_db); assente =
    #        nessun filtro.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_asset_utilizzabili_usa_la_condizione_del_render(self, mocked_factory) -> None:
        from apps.documenti.db.documenti_repository import _ASSET_UTILIZZABILE_OGGI

        for valore, atteso in (
            (True, f"AND {_ASSET_UTILIZZABILE_OGGI}"),
            (False, f"NOT {_ASSET_UTILIZZABILE_OGGI}"),
            (None, None),
        ):
            with self.subTest(utilizzabili=valore):
                cursor = _mk_cursor(
                    fetchone_results=[(0,), None],
                    descriptions=[[], _columns("id")],
                    fetchall_results=[[], []],
                )
                mocked_factory.return_value = cursor
                with catalogo_ricerca_finto(["codice"]):
                    DocumentiRepository().list_asset(
                        **self._list_default_args(utilizzabili=valore),
                    )
                sql, _ = cursor.execute.call_args_list[0].args
                if atteso is None:
                    self.assertNotIn("validita", sql)
                else:
                    self.assertIn(atteso, sql)

    # 2. scope emittente passa lista ANY(%s) con i soli id whitelisted.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_asset_applies_emittente_scope_anyarray(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(0,), None],
            descriptions=[[], _columns("id")],
            fetchall_results=[[], []],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().list_asset(
            **self._list_default_args(emittente_ids_scope=[11, 22])
        )

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("a.emittente_fiscale_id = ANY(%s)", sql)
        self.assertEqual(params, [True, [11, 22]])

    # 3. paginazione: LIMIT cappato a 200 + offset preservato + tiebreaker id.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_asset_paginazione_deterministica_id_tiebreaker(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(0,), None],
            descriptions=[[], _columns("id")],
            fetchall_results=[[], []],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().list_asset(
            **self._list_default_args(limit=999, offset=10)
        )

        data_sql, data_params = cursor.execute.call_args_list[1].args
        self.assertEqual(data_params[-2:], [200, 10])
        self.assertIn("ORDER BY a.codice ASC NULLS FIRST, a.id ASC", data_sql)

    # 4. order_by fuori whitelist -> E_DOCUMENTI_VALIDATION (no DB call).
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_asset_invalid_order_by_raises_validation_no_db(
        self, mocked_factory
    ) -> None:
        with self.assertRaises(ServiceError) as ctx:
            DocumentiRepository().list_asset(
                **self._list_default_args(order_by="totalmente_inventato")
            )
        self.assertEqual(ctx.exception.code, "E_DOCUMENTI_VALIDATION")
        # Defense-in-depth: nessuna query eseguita.
        mocked_factory.assert_not_called()

    # 4-bis. Direzione dal BB `sql_order_clause` (2026-09-26): `DESC`
    #        maiuscolo e' ammesso e allinea il tiebreak.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_asset_order_dir_maiuscola_ammessa(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(0,), None],
            descriptions=[[], _columns("id")],
            fetchall_results=[[], []],
        )
        mocked_factory.return_value = cursor
        DocumentiRepository().list_asset(**self._list_default_args(order_dir="DESC"))
        data_sql = cursor.execute.call_args_list[1].args[0]
        self.assertIn("ORDER BY a.codice DESC NULLS LAST, a.id DESC", data_sql)

    # 4-ter. Una direzione estranea e' `ValueError` (400 `E_VALIDATION_INPUT`
    #        sull'API), non ASC in silenzio come faceva la copia a mano.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_list_asset_order_dir_estranea_rifiutata_no_db(self, mocked_factory) -> None:
        with self.assertRaisesRegex(ValueError, "order_dir_invalid"):
            DocumentiRepository().list_asset(**self._list_default_args(order_dir="giu"))
        mocked_factory.assert_not_called()


class DocumentiRepositoryGetAssetTests(TestCase):
    """Test get_asset: row -> dict, missing -> None, scope ANY(%s)."""

    # 5. row esistente -> dict; row assente -> None.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_asset_returns_row(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id", "codice")],
            fetchall_results=[[(7, "LOGO-A")]],
        )
        mocked_factory.return_value = cursor

        result = DocumentiRepository().get_asset(7, emittente_ids_scope=None)
        self.assertEqual(result, {"id": 7, "codice": "LOGO-A"})

    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_asset_returns_none(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id")],
            fetchall_results=[[]],
        )
        mocked_factory.return_value = cursor

        self.assertIsNone(
            DocumentiRepository().get_asset(7, emittente_ids_scope=[1])
        )

    # 6. scope emittente: WHERE include `a.emittente_fiscale_id = ANY(%s)`.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_asset_with_scope_passes_anyarray(self, mocked_factory) -> None:
        cursor = _mk_cursor(
            fetchone_results=[None],
            descriptions=[_columns("id")],
            fetchall_results=[[]],
        )
        mocked_factory.return_value = cursor

        DocumentiRepository().get_asset(7, emittente_ids_scope=[33])

        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("a.id = %s", sql)
        self.assertIn("a.emittente_fiscale_id = ANY(%s)", sql)
        self.assertEqual(params, [7, [33]])


class DocumentiRepositoryCreateAssetTests(TestCase):
    """Test create_asset: INSERT solo colonne whitelisted + RETURNING id."""

    # 7. create_asset usa solo colonne whitelisted; ritorna id RETURNING.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_create_asset_inserts_only_whitelisted_columns_returns_id(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor(
            fetchone_results=[(99,)], descriptions=[_columns("id")],
        )
        mocked_factory.return_value = cursor

        data = {
            "codice": "LOGO-PRINCIPALE",
            "codice_interno": "LOGO_PRINC",
            "descrizione": "Logo aziendale principale",
            "asset_tipo_id": 1,
            "mime_type": "image/png",
            "file_name": "logo.png",
            "file_size_bytes": 12345,
            "storage_key": "assets/11/abcdef.png",
            "sha256": "abcdef" * 10 + "1234",
            "emittente_fiscale_id": 11,
            "attivo": True,
            "meta": {"k": "v"},
        }
        new_id = DocumentiRepository().create_asset(data)

        self.assertEqual(new_id, 99)
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("INSERT INTO documenti.template_asset", sql)
        self.assertIn("RETURNING id", sql)
        # 12 chiavi presenti nel data tutte whitelisted (valido_dal/valido_al
        # assenti) -> 12 placeholder; `meta` serializzato `::jsonb` (fino al
        # 2026-09-26 il dict arrivava nudo al cursor: 500 su psycopg).
        self.assertEqual(len(params), 12)
        self.assertIn("%s::jsonb", sql)
        self.assertIn('{"k": "v"}', params)

    # 7-bis. ⛔ Una chiave fuori whitelist e' RuntimeError (2026-09-26), non
    #        uno scarto silenzioso: nessuna SQL parte.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_create_asset_chiave_fuori_whitelist_rifiutata(
        self, mocked_factory
    ) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            DocumentiRepository().create_asset({"codice": "X", "chiave_extra": "x"})
        self.assertIn("chiave_extra", str(ctx.exception))
        mocked_factory.assert_not_called()


class DocumentiRepositoryUpdateAssetMetadatiTests(TestCase):
    """Test update_asset_metadati: UPDATE whitelisted, immutabili escluse."""

    # 8. update_asset_metadati ritorna True se rowcount > 0.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_update_asset_metadati_returns_true_on_success(
        self, mocked_factory
    ) -> None:
        cursor = _mk_cursor()
        cursor.rowcount = 1
        mocked_factory.return_value = cursor

        result = DocumentiRepository().update_asset_metadati(
            42, {"descrizione": "Nuova descr"}
        )

        self.assertTrue(result)
        sql, params = cursor.execute.call_args_list[0].args
        self.assertIn("UPDATE documenti.template_asset", sql)
        self.assertIn("descrizione = %s", sql)
        self.assertIn("WHERE id = %s", sql)
        self.assertEqual(params, ["Nuova descr", 42])

    # 9. update_asset_metadati con data vuoto: nessuna SQL eseguita, False.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_update_asset_metadati_returns_false_on_empty_data_no_sql(
        self, mocked_factory
    ) -> None:
        result = DocumentiRepository().update_asset_metadati(42, {})
        self.assertFalse(result)
        mocked_factory.assert_not_called()

    # 10. ⛔ update_asset_metadati: le colonne file/anagrafiche fuori whitelist
    #     sono RuntimeError (2026-09-26), non piu' scartate in silenzio. Il
    #     service le rifiuta prima con un 400 (`_UPDATE_KEYS`); il trigger DB
    #     A4 resta la difesa finale.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_update_asset_metadati_filters_only_whitelisted_columns(
        self, mocked_factory
    ) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            DocumentiRepository().update_asset_metadati(
                7,
                {
                    "descrizione": "X",
                    "storage_key": "tampered",
                    "sha256": "tampered",
                    "file_name": "tampered.png",
                    "codice": "TAMPER",
                    "asset_tipo_id": 999,
                },
            )
        for forbidden in ("storage_key", "sha256", "file_name", "codice", "asset_tipo_id"):
            self.assertIn(forbidden, str(ctx.exception))
        mocked_factory.assert_not_called()


class DocumentiRepositoryGetTipoAssetTests(TestCase):
    """Test get_tipo_asset: lookup tipo asset per validazione MIME service-side."""

    # 11. row esistente -> dict normalizzato; row assente -> None.
    @patch("apps.documenti.db.documenti_repository.connection.cursor")
    def test_get_tipo_asset_returns_dict_or_none(self, mocked_factory) -> None:
        # Caso row presente.
        cursor_ok = _mk_cursor(fetchone_results=[(3, "LOGO", True)])
        mocked_factory.return_value = cursor_ok

        row = DocumentiRepository().get_tipo_asset(3)
        self.assertEqual(row, {"id": 3, "codice_interno": "LOGO", "attivo": True})
        sql, params = cursor_ok.execute.call_args_list[0].args
        self.assertIn("FROM documenti.tipi_asset_documento", sql)
        self.assertIn("WHERE id = %s", sql)
        self.assertEqual(params, [3])

        # Caso row assente.
        cursor_none = _mk_cursor(fetchone_results=[None])
        mocked_factory.return_value = cursor_none
        self.assertIsNone(DocumentiRepository().get_tipo_asset(999))
