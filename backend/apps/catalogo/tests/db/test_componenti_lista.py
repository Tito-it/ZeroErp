# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il SQL della distinta base letta da `CatalogoBomRepository` sulla
#        vista `catalogo.vw_articoli_componenti_dettaglio`
#        (brief-db-liste-righe-documento, lotto C, 2026-09-28): la pagina
#        della lista configurabile `catalogo.articolo_componenti`, la lettura
#        completa e la riga singola.
# Note: nessun DB — si sostituiscono `fetch_paged_with_total` e `connection`
#       e si legge cio' che ricevono: nel BB core `righe_lista_mixin` per la
#       pagina e la lettura completa (dal 2026-10-04, §9.16 del brief), nel
#       modulo del repository per la riga singola. Che la vista
#       abbia le colonne nominate lo presidiano il trigger
#       `a10_valida_campo_sorgente` al migrate e i pgTAP della parte DB.
# ------------------------------------------------------------
"""⛔ PERCHE' QUESTO FILE ESISTE.

Fino al 2026-09-28 il repository ricopiava in Python la proiezione della
vista, capability di chiusura compresa, e le due copie erano gia' divergite.
Ora le tre letture passano dalla vista, e la lista ha un filtro di validita'
e un ordinamento suoi: le cose che un errore renderebbe silenziose sono
l'ordine di partenza (la versione piu' recente in cima, non la prima
colonna), `valido_al` ordinato come «infinito» quando e' vuoto, il filtro
«in vigore al» che non perde le righe senza fine, e la ricerca legata alla
lista giusta.

Indice test:

 1) test_pagina_parte_dalla_versione_piu_recente
 2) test_pagina_filtra_il_prodotto_dalla_vista
 3) test_in_vigore_al_tiene_le_righe_senza_fine
 4) test_senza_data_nessun_filtro_di_validita
 5) test_valido_al_vuoto_ordina_come_infinito_e_parte_desc
 6) test_chiave_fuori_whitelist_e_rifiutata
 7) test_pagina_rispetta_il_tetto_e_l_export_lo_alza
 8) test_la_ricerca_nomina_la_lista_della_distinta
 9) test_lettura_completa_e_riga_singola_dalla_vista
10) test_nessuna_proiezione_python_residua
"""

import datetime as dt
import unittest
from unittest.mock import MagicMock, patch

from apps.catalogo.db import catalogo_bom_repository as modulo
from apps.catalogo.db.catalogo_bom_repository import CatalogoBomRepository
from apps.core.api.constants import MAX_LIMIT
from apps.core.db import righe_lista_mixin as bb

_VISTA = "catalogo.vw_articoli_componenti_dettaglio"
_ARTICOLO = "11111111-1111-1111-1111-111111111111"


# Scopo: chiama `list_righe_pagina` e ritorna (sql, params, kw) passati a
#        `fetch_paged_with_total`.
def _pagina(**kwargs):
    kwargs.setdefault("limit", 10)
    with patch.object(bb, "fetch_paged_with_total", return_value=([], 0)) as fn:
        CatalogoBomRepository().list_righe_pagina(_ARTICOLO, **kwargs)
    args, kw = fn.call_args
    return " ".join(args[0].split()), args[1], kw


# Scopo: esegue una lettura diretta e ritorna (sql, params). `dove` e' il
#        modulo che apre la connessione.
def _lettura(chiamata, dove=modulo):
    cursor = MagicMock()
    cursor.description = []
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = None
    with patch.object(dove, "connection") as conn:
        conn.cursor.return_value.__enter__.return_value = cursor
        chiamata()
    sql, params = cursor.execute.call_args.args
    return " ".join(sql.split()), params


class ComponentiListaTests(unittest.TestCase):

    def test_pagina_parte_dalla_versione_piu_recente(self):
        sql, _, _ = _pagina()
        self.assertIn("ORDER BY v.valido_dal DESC", sql)

    def test_pagina_filtra_il_prodotto_dalla_vista(self):
        sql, params, _ = _pagina()
        self.assertIn(f"FROM {_VISTA} v WHERE v.prodotto_id = %s", sql)
        self.assertEqual(params[0], _ARTICOLO)

    # ⭐ Una riga senza fine e' in vigore a qualunque data: un confronto secco
    #    `v.valido_al >= %s` la perderebbe (NULL non e' >= di niente).
    def test_in_vigore_al_tiene_le_righe_senza_fine(self):
        giorno = dt.date(2026, 9, 28)
        sql, params, kw = _pagina(valido_al=giorno)
        self.assertIn("(v.valido_al IS NULL OR v.valido_al >= %s)", sql)
        self.assertEqual(params[1], giorno)
        # Il conteggio di ripiego porta lo stesso filtro.
        self.assertIn("v.valido_al IS NULL OR v.valido_al >= %s", kw["fallback_count_sql"])
        self.assertEqual(kw["fallback_params"], [_ARTICOLO, giorno])

    def test_senza_data_nessun_filtro_di_validita(self):
        sql, params, _ = _pagina(valido_al=None)
        self.assertNotIn("valido_al >=", sql)
        self.assertEqual(params[:1], [_ARTICOLO])

    def test_valido_al_vuoto_ordina_come_infinito_e_parte_desc(self):
        sql, _, _ = _pagina(order_by="valido_al", order_dir=None)
        self.assertIn("ORDER BY COALESCE(v.valido_al, 'infinity'::date) DESC", sql)
        sql, _, _ = _pagina(order_by="valido_dal", order_dir=None)
        self.assertIn("ORDER BY v.valido_dal DESC", sql)

    # ⛔ Una chiave fuori whitelist e' un 400 (`order_by_invalid`), non
    #    l'ordine della distinta (dal 2026-10-20, brief-be-verifica-documentazione-api §A1).
    def test_chiave_fuori_whitelist_e_rifiutata(self):
        with self.assertRaisesRegex(ValueError, "order_by_invalid"):
            _pagina(order_by="prezzo; DROP", order_dir="asc")

    def test_pagina_rispetta_il_tetto_e_l_export_lo_alza(self):
        _, params, _ = _pagina(limit=5000, offset=-3)
        self.assertEqual(params[-2:], [MAX_LIMIT, 0])
        _, params, _ = _pagina(limit=10001, max_limit=10001)
        self.assertEqual(params[-2], 10001)

    def test_la_ricerca_nomina_la_lista_della_distinta(self):
        self.assertEqual(modulo._RICERCA_COMPONENTI.lista_codice, "catalogo.articolo_componenti")
        self.assertEqual(
            tuple(modulo._RICERCA_COMPONENTI.colonne),
            ("componente_codice", "componente_descrizione"),
        )

    def test_lettura_completa_e_riga_singola_dalla_vista(self):
        sql, params = _lettura(lambda: CatalogoBomRepository().list_righe(_ARTICOLO), dove=bb)
        self.assertIn(f"FROM {_VISTA} v WHERE v.prodotto_id = %s", sql)
        self.assertIn("ORDER BY v.valido_dal DESC, v.id", sql)
        self.assertEqual(params, [_ARTICOLO])
        sql, params = _lettura(lambda: CatalogoBomRepository().get_componente(_ARTICOLO, "c-1"))
        self.assertIn(f"FROM {_VISTA} v WHERE v.prodotto_id = %s AND v.id = %s", sql)
        self.assertEqual(params, [_ARTICOLO, "c-1"])

    # ⛔ La copia Python della vista (`COMPONENTE_DETAIL_COLUMNS`) e' ritirata:
    #    tornasse, sarebbe la seconda sede che la D-8.5 ha tolto.
    def test_nessuna_proiezione_python_residua(self):
        self.assertFalse(hasattr(modulo, "COMPONENTE_DETAIL_COLUMNS"))
        self.assertFalse(hasattr(CatalogoBomRepository, "_componente_projection"))
