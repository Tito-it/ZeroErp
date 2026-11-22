# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio di `apps.core.api.openapi_params` — la frase di `order_by`
#        nello schema OpenAPI si LEGGE dalla whitelist del repository, quindi
#        non puo' elencare colonne che non ci sono ne' perderne una.
# Note: Nessun DB, nessuna view: e' una funzione pura. Il test che conta e'
#       il secondo — le view di pagamenti e magazzino passano le mappe vere,
#       e questo pinna che ogni chiave della mappa compaia nella frase.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) test_frase_elenca_le_chiavi_della_mappa_nell_ordine — la whitelist entra intera, in ordine
2) test_le_view_leggono_le_mappe_vere                  — pagamenti e magazzino: ogni chiave ordinabile sta nella descrizione
3) test_senza_nota_la_frase_finisce_col_punto          — `nota` opzionale, niente spazio pendente
4) ParametriOrdinamentoTests.test_order_by_dice_la_partenza_e_il_ripiego
5) ParametriOrdinamentoTests.test_colonne_come_testo_o_assenti
6) ParametriOrdinamentoTests.test_order_dir_dice_il_ripiego_e_la_partenza
7) ParametriOrdinamentoSchemaTests.test_ogni_lista_configurabile_lo_dichiara_col_bb
8) ParametriOrdinamentoSchemaTests.test_nessuna_view_fuori_catalogo_lo_dichiara
"""

from django.test import SimpleTestCase

from functools import lru_cache

from apps.core.api.openapi_params import (
    FRASE_ORDINAMENTO_DI_PARTENZA,
    descrizione_order_by,
    parametri_ordinamento,
)


class DescrizioneOrderByTests(SimpleTestCase):
    # Scopo: la frase porta TUTTE le chiavi, nell'ordine della mappa.
    def test_frase_elenca_le_chiavi_della_mappa_nell_ordine(self) -> None:
        frase = descrizione_order_by(
            {"data": "t.data", "codice": "t.codice"}, "Senza: data.",
        )
        self.assertEqual(
            frase, "Whitelist (nome FISICO della colonna): data | codice. Senza: data.",
        )

    # Scopo: le due aree che hanno adottato il BB passano le mappe del
    #        repository: se una colonna ordinabile nasce, la frase la dice da se'.
    def test_le_view_leggono_le_mappe_vere(self) -> None:
        from apps.magazzino.db.magazzino_repository import MOVIMENTI_SORT_COLUMNS
        from apps.pagamenti.db.pagamenti_repository import (
            DISTINTE_SORT_COLUMNS,
            RATE_SORT_COLUMNS,
        )

        for mappa in (DISTINTE_SORT_COLUMNS, RATE_SORT_COLUMNS, MOVIMENTI_SORT_COLUMNS):
            frase = descrizione_order_by(mappa, "nota")
            for chiave in mappa:
                self.assertIn(chiave, frase)

    # Scopo: senza nota la frase e' chiusa dal punto, senza spazio in coda.
    def test_senza_nota_la_frase_finisce_col_punto(self) -> None:
        self.assertEqual(
            descrizione_order_by(["a"]), "Whitelist (nome FISICO della colonna): a.",
        )


# Scopo: ⛔ Lo schema di un lookup dichiara `data.results`, come la risposta
#        vera (2026-10-21, §B10 del brief-be-verifica-documentazione-api):
#        dieci lookup di `views_lookup` dichiaravano `data` come lista nuda. Si
#        guarda lo schema GENERATO da drf-spectacular, non la chiamata
#        all'helper: e' quello che legge chi genera il client.
class RispostaLookupSchemaTests(SimpleTestCase):
    def test_i_lookup_dichiarano_data_results(self) -> None:
        from drf_spectacular.generators import SchemaGenerator

        componenti = SchemaGenerator().get_schema(request=None, public=True)["components"]["schemas"]
        for nome in (
            "TipiSoggettoDettaglioResponse", "FormeGiuridicheResponse",
            "TipiIndirizzoNaturaResponse", "TipiIndirizzoTipoRuoloResponse",
            "ContiContabiliLookupResponse",
        ):
            with self.subTest(componente=nome):
                self.assertIn(nome, componenti)
                data = componenti[nome]["properties"]["data"]
                if "$ref" in data:
                    data = componenti[data["$ref"].rsplit("/", 1)[1]]
                self.assertEqual(data["properties"]["results"]["type"], "array")


def _descrizioni(parametri) -> dict[str, str]:
    return {p.name: p.description for p in parametri}


# Scopo: il BB `parametri_ordinamento` (ok Tid 2026-11-22): le frasi di
#        `order_by`/`order_dir` di una lista configurabile, che dal giro 6 di
#        brief-db-revisione-ui parte dall'ordinamento del suo preset.
class ParametriOrdinamentoTests(SimpleTestCase):
    def test_order_by_dice_la_partenza_e_il_ripiego(self) -> None:
        d = _descrizioni(parametri_ordinamento(
            {"data": "t.data", "codice": "t.codice"}, senza="data DESC.", nota="Fuori -> 400.",
        ))
        self.assertEqual(
            d["order_by"],
            "Whitelist (nome FISICO della colonna): data | codice. "
            f"{FRASE_ORDINAMENTO_DI_PARTENZA} "
            "Se la lista non ne dichiara uno: data DESC. Fuori -> 400.",
        )

    def test_colonne_come_testo_o_assenti(self) -> None:
        testo = _descrizioni(parametri_ordinamento("Stessa whitelist della lista."))
        self.assertTrue(testo["order_by"].startswith("Stessa whitelist della lista. "))
        assenti = _descrizioni(parametri_ordinamento())
        self.assertTrue(assenti["order_by"].startswith("Il `campo_sorgente` "))
        self.assertIn(FRASE_ORDINAMENTO_DI_PARTENZA, assenti["order_by"])

    def test_order_dir_dice_il_ripiego_e_la_partenza(self) -> None:
        d = _descrizioni(parametri_ordinamento(verso="desc"))
        self.assertEqual(
            d["order_dir"],
            "asc | desc. Assente con `order_by`: desc. Senza `order_by`, se la "
            "lista ha un ordinamento di partenza, vale il verso di quello.",
        )
        self.assertNotIn("Assente con", _descrizioni(parametri_ordinamento())["order_dir"])


# Scopo: lo schema GENERATO, legato alla classe di ogni GET: (percorso, classe
#        della view, descrizione di `order_by`) per le operazioni che lo
#        dichiarano.
@lru_cache(maxsize=1)
def _order_by_dello_schema() -> tuple[tuple[str, type, str], ...]:
    from drf_spectacular.drainage import GENERATOR_STATS
    from drf_spectacular.settings import spectacular_settings

    from apps.core.tests.test_schema_openapi_registro import _pattern_con_rotte_condizionali

    GENERATOR_STATS.reset()
    try:
        with GENERATOR_STATS.silence():
            generatore = spectacular_settings.DEFAULT_GENERATOR_CLASS(
                patterns=_pattern_con_rotte_condizionali(),
            )
            percorsi = generatore.get_schema(request=None, public=True)["paths"]
            endpoint = generatore._get_paths_and_endpoints()
    finally:
        GENERATOR_STATS.reset()
    trovati = []
    for percorso, _regex, metodo, view in endpoint:
        operazione = percorsi.get(percorso, {}).get("get") if metodo == "GET" else None
        for parametro in (operazione or {}).get("parameters", []):
            if parametro.get("in") == "query" and parametro.get("name") == "order_by":
                trovati.append((percorso, type(view), parametro.get("description", "")))
    return tuple(trovati)


# Scopo: ⛔ il presidio del BB. Una view con `lista_codice` riceve dalla base
#        view l'ordinamento del preset quando la richiesta non porta
#        `order_by` (`ordinamento_di_partenza`): il suo schema lo deve dire, e
#        lo dice solo il BB. Le descrizioni scritte a mano dicevano «default X»
#        (una ottantina di view, 2026-11-22). E al contrario: la frase su una
#        view fuori catalogo direbbe un comportamento che non ha.
# ⚠️ Si guarda lo schema generato e la classe VERA della rotta: le fabbriche
#    (note, righe figlie, documenti interni) tolgono o mettono `lista_codice`
#    per sede, e un controllo sul sorgente non lo vedrebbe.
class ParametriOrdinamentoSchemaTests(SimpleTestCase):
    def test_ogni_lista_configurabile_lo_dichiara_col_bb(self) -> None:
        trovati = _order_by_dello_schema()
        con_lista = [t for t in trovati if getattr(t[1], "lista_codice", None)]
        self.assertGreater(len(con_lista), 50, "lo schema non e' stato letto")
        senza_bb = sorted(
            f"{percorso} ({cls.__name__})"
            for percorso, cls, descrizione in con_lista
            if FRASE_ORDINAMENTO_DI_PARTENZA not in descrizione
        )
        self.assertEqual(senza_bb, [], "usare `*parametri_ordinamento(...)`")

    def test_nessuna_view_fuori_catalogo_lo_dichiara(self) -> None:
        fuori = sorted(
            f"{percorso} ({cls.__name__})"
            for percorso, cls, descrizione in _order_by_dello_schema()
            if not getattr(cls, "lista_codice", None)
            and FRASE_ORDINAMENTO_DI_PARTENZA in descrizione
        )
        self.assertEqual(fuori, [], "fuori catalogo resta `descrizione_order_by`")
