# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il SQL delle due liste «Revisioni» (preventivo e offerta), paginate
#        dal 2026-09-27 (brief-db-liste-datatable-grezze §4 righe 7 e 8).
# Note: nessun DB — si sostituisce `fetch_paged_with_total` nel modulo del
#       repository e si legge cio' che riceve. Che le query COMPILINO sul DB vero
#       e' stato provato con EXPLAIN il giorno della conversione (le viste sono
#       `security_invoker`: senza GUC le righe non si vedono, il piano si').
# ------------------------------------------------------------
"""⛔ PERCHE' QUESTO FILE ESISTE.

Fino al 2026-09-27 i due tab tornavano la catena INTERA, senza LIMIT, e
l'offerta la ricostruiva con una CTE ricorsiva a ogni apertura. Ora sono due
liste a catalogo (`vendite.preventivo_revisioni`, `vendite.offerta_revisioni`)
con colonne gemelle, e ognuna ha la SUA whitelist — separata da quella della
lista principale, che `rev`/`revisione_numero` non li ordina (§7.3).

Indice test:

 1) test_preventivo_default_rev_asc_con_spareggio
 2) test_preventivo_data_senza_direzione_parte_desc
 3) test_preventivo_chiave_della_lista_principale_e_rifiutata
 4) test_preventivo_paginazione_e_conteggio_di_ripiego
 5) test_preventivo_nessun_filtro_emittente
 6) test_offerta_legge_la_radice_per_uguaglianza_non_ricorsione
 7) test_offerta_default_revisione_numero_asc
 8) test_offerta_data_emissione_senza_direzione_parte_desc
 9) test_offerta_codice_ordina_e_chiave_principale_rifiutata
10) test_offerta_nessun_filtro_emittente
11) test_whitelist_separate_da_quelle_principali
"""

import unittest
from unittest.mock import patch

from apps.vendite.db import offerte_repository, preventivi_repository
from apps.vendite.db.offerte_repository import OfferteRepository
from apps.vendite.db.preventivi_repository import PreventiviRepository


# Scopo: chiama `list_revisioni` del repository e ritorna (sql, params, kw)
#        passati a `fetch_paged_with_total`.
def _cattura(modulo, repo_cls, documento_id=7, **kwargs):
    with patch.object(modulo, "fetch_paged_with_total", return_value=([], 0)) as fn:
        repo_cls().list_revisioni(documento_id, **kwargs)
    args, kw = fn.call_args
    return " ".join(args[0].split()), args[1], kw


class PreventivoRevisioniListaTests(unittest.TestCase):

    def _cattura(self, **kwargs):
        return _cattura(preventivi_repository, PreventiviRepository, **kwargs)

    # Scopo: la catena si legge dalla prima revisione.
    def test_preventivo_default_rev_asc_con_spareggio(self):
        sql, _, _ = self._cattura(order_by=None, order_dir=None)
        self.assertIn("ORDER BY v.rev ASC NULLS FIRST, v.id ASC", sql)
        self.assertIn(
            "v.numero = (SELECT numero FROM vendite.preventivi WHERE id = %s)", sql,
        )

    # Scopo: `data` e' una colonna DATA a catalogo: senza direzione, DESC.
    def test_preventivo_data_senza_direzione_parte_desc(self):
        sql, _, _ = self._cattura(order_by="data", order_dir=None)
        self.assertIn("ORDER BY v.data DESC NULLS LAST, v.id DESC", sql)

    # Scopo: una chiave della lista PRINCIPALE non appartiene a questa lista:
    #        e' un 400 (`order_by_invalid`), non il default (dal 2026-10-20).
    def test_preventivo_chiave_della_lista_principale_e_rifiutata(self):
        with self.assertRaisesRegex(ValueError, "order_by_invalid"):
            self._cattura(order_by="ragione_sociale_completa", order_dir="asc")

    # Scopo: LIMIT/OFFSET come parametri, e il conteggio di ripiego (pagina
    #        oltre l'ultima) con lo stesso FROM/WHERE della pagina.
    def test_preventivo_paginazione_e_conteggio_di_ripiego(self):
        sql, params, kw = self._cattura(limit=10, offset=20)
        self.assertIn("COUNT(*) OVER () AS total_count", sql)
        self.assertTrue(sql.endswith("LIMIT %s OFFSET %s"))
        self.assertEqual(params, [7, 10, 20])
        self.assertEqual(kw["fallback_params"], [7])
        self.assertEqual(kw["offset"], 20)
        self.assertIn("FROM vendite.vw_preventivi_lista v WHERE", kw["fallback_count_sql"])

    # Scopo: ⛔ l'emittente del tab lo legge solo il cancello di perimetro: nel
    #        WHERE non c'e' — un id sbagliato non deve diventare una lista vuota.
    def test_preventivo_nessun_filtro_emittente(self):
        sql, params, _ = self._cattura(limit=25, offset=0)
        self.assertNotIn("emittente", sql)
        self.assertEqual(params, [7, 25, 0])


class OffertaRevisioniListaTests(unittest.TestCase):

    def _cattura(self, **kwargs):
        return _cattura(offerte_repository, OfferteRepository, **kwargs)

    # Scopo: ⛔ la CTE ricorsiva e' ritirata: la catena e' la colonna
    #        `revisione_radice_id`, letta per uguaglianza sulla vista di lista.
    def test_offerta_legge_la_radice_per_uguaglianza_non_ricorsione(self):
        sql, _, _ = self._cattura()
        self.assertNotIn("RECURSIVE", sql.upper())
        self.assertIn("FROM vendite.vw_offerte_commerciali_lista v", sql)
        self.assertIn(
            "v.revisione_radice_id = (SELECT revisione_radice_id "
            "FROM vendite.offerte_commerciali WHERE id = %s)",
            sql,
        )

    # Scopo: la catena si legge dalla rev.1.
    def test_offerta_default_revisione_numero_asc(self):
        sql, _, _ = self._cattura(order_by=None, order_dir=None)
        self.assertIn("ORDER BY v.revisione_numero ASC NULLS FIRST, v.id ASC", sql)

    # Scopo: `data_emissione` e' DATA: senza direzione DESC, le bozze (NULL)
    #        in coda.
    def test_offerta_data_emissione_senza_direzione_parte_desc(self):
        sql, _, _ = self._cattura(order_by="data_emissione", order_dir=None)
        self.assertIn("ORDER BY v.data_emissione DESC NULLS LAST, v.id DESC", sql)

    # Scopo: `codice` (la colonna «Numero») ordina dal 2026-09-28 (§9.1 del
    #        brief, colonna del nucleo resa `ordinabile = t`, gemella di
    #        `numero` sui preventivi); una chiave della lista principale che
    #        qui non c'e' e' un 400 (dal 2026-10-20).
    # ⛔ Fino a quel giorno questo test fissava il ripiego di `codice`: era il
    #    contratto di allora (`ordinabile = f`), non una regola.
    def test_offerta_codice_ordina_e_chiave_principale_rifiutata(self):
        sql, _, _ = self._cattura(order_by="codice", order_dir="desc")
        self.assertIn("ORDER BY v.codice DESC NULLS LAST, v.id DESC", sql)
        with self.assertRaisesRegex(ValueError, "order_by_invalid"):
            self._cattura(order_by="ragione_sociale_completa", order_dir="desc")

    # Scopo: come per il preventivo, nessun filtro emittente nella query.
    def test_offerta_nessun_filtro_emittente(self):
        sql, params, _ = self._cattura(limit=25, offset=0)
        self.assertNotIn("emittente", sql)
        self.assertEqual(params, [7, 25, 0])


class WhitelistSeparateTests(unittest.TestCase):

    # Scopo: ⛔ `revisione_numero` NON entra nella whitelist della lista
    #        offerte, ne' `rev` in quella dei preventivi (§7.3): le whitelist dei
    #        tab sono costanti a parte.
    def test_whitelist_separate_da_quelle_principali(self):
        self.assertNotIn("revisione_numero", offerte_repository._ORDER_COLS_OFFERTE)
        self.assertNotIn("rev", preventivi_repository._ORDER_COLS_PREVENTIVI)
        self.assertIsNot(
            offerte_repository.OFFERTA_REVISIONI_ORDER_COLUMNS,
            offerte_repository._ORDER_COLS_OFFERTE,
        )


if __name__ == "__main__":
    unittest.main()
