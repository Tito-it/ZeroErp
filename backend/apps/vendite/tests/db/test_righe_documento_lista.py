# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: il SQL delle righe dei quattro documenti di vendita (preventivo,
#        ordine, DDT, reso), letto dal BB `RigheDocumentoRepositoryMixin`
#        (brief-db-liste-righe-documento, lotto A, 2026-09-28): la pagina
#        della lista configurabile, la lettura completa e la riga singola.
# Note: nessun DB — si sostituiscono `fetch_paged_with_total` e `connection`
#       nel modulo del BB e si legge cio' che ricevono. Che le viste
#       esistano con le colonne nominate lo presidiano i pgTAP della parte DB
#       e `test_lista_proiezione_campo_sorgente` (su DB vero, in CI).
# ------------------------------------------------------------
"""⛔ PERCHE' QUESTO FILE ESISTE.

Fino al 2026-09-28 ogni documento aveva la sua query delle righe, tre su
quattro proiettate a mano in Python, e la riga singola non filtrava
`attivo` (le righe si eliminano con un DELETE fisico: il filtro allinea la
riga singola alle altre letture sul caso `attivo = false`, che il modello
ammette). Ora le quattro letture passano da un BB, e le cose che contano
sono quelle che un errore renderebbe silenziose: l'ordine del DOCUMENTO come
partenza (non una colonna qualunque), le date che partono DESC, una chiave
fuori whitelist che ripiega invece di ordinare, il filtro `attivo` su tutte e
tre le letture.

Indice test:

 1) test_pagina_parte_dall_ordine_del_documento
 2) test_pagina_filtra_documento_e_righe_attive
 3) test_data_senza_direzione_parte_desc
 4) test_chiave_fuori_whitelist_e_rifiutata
 5) test_pagina_rispetta_il_tetto_e_l_export_lo_alza
 6) test_lettura_completa_dalla_vista_attive_in_ordine
 7) test_riga_singola_dalla_vista_solo_attiva
 8) test_whitelist_gemelle_uguali_sulle_righe_commerciali
 9) test_la_ricerca_nomina_la_lista_del_documento
10) test_conteggio_sulla_tabella_solo_righe_attive
"""

import unittest
from unittest.mock import MagicMock, patch

from apps.core.api.constants import MAX_LIMIT
from apps.core.db import righe_lista_mixin as bb
from apps.vendite.db import _righe_repo_mixin
from apps.vendite.db._righe_repo_mixin import COLONNE_RIGHE_COMMERCIALI
from apps.vendite.db.ddt_repository import DdtRepository
from apps.vendite.db.ordini_repository import OrdiniRepository
from apps.vendite.db.preventivi_repository import PreventiviRepository
from apps.vendite.db.resi_repository import ResiRepository

# La tabella delle righe, per il conteggio (`count_righe` conta sulla tabella).
_TABELLE = {
    PreventiviRepository: "vendite.preventivi_righe",
    OrdiniRepository: "vendite.ordini_righe",
    DdtRepository: "vendite.ddt_righe",
    ResiRepository: "vendite.resi_righe",
}

# (repository, vista, FK, colonne d'ordine del documento, lista, data DESC o None)
# ⭐ Ordine e bolla partono dalla SEZIONE della vista (1 articoli, 2 oneri;
#    20261103-51/-52): gli oneri dopo gli articoli, poi la posizione della riga.
_DOCUMENTI = (
    (PreventiviRepository, "vendite.vw_preventivi_righe_dettaglio", "preventivo_id", ("ordine",),
     "vendite.preventivo_righe", "data_consegna_richiesta_cliente"),
    (OrdiniRepository, "vendite.vw_ordini_righe_dettaglio", "ordine_id", ("sezione_documento", "riga_nr"),
     "vendite.ordine_righe", "data_consegna_confermata"),
    (DdtRepository, "vendite.vw_ddt_righe_dettaglio", "ddt_id", ("sezione_documento", "riga_nr"),
     "vendite.ddt_righe", None),
    (ResiRepository, "vendite.vw_resi_righe_dettaglio", "reso_id", ("riga_nr",),
     "vendite.reso_righe", None),
)


# Scopo: chiama `list_righe_pagina` e ritorna (sql, params, kw) passati a
#        `fetch_paged_with_total`.
def _pagina(repo_cls, documento_id=7, **kwargs):
    kwargs.setdefault("limit", 15)
    with patch.object(bb, "fetch_paged_with_total", return_value=([], 0)) as fn:
        repo_cls().list_righe_pagina(documento_id, **kwargs)
    args, kw = fn.call_args
    return " ".join(args[0].split()), args[1], kw


# Scopo: esegue una lettura diretta (completa o riga) e ritorna (sql, params).
def _lettura(chiamata):
    cursor = MagicMock()
    cursor.description = []
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = None
    # La lettura completa e' del BB core, la riga singola del mixin di vendita:
    # la stessa connessione finta per tutte e due.
    with patch.object(bb, "connection") as conn, patch.object(_righe_repo_mixin, "connection", conn):
        conn.cursor.return_value.__enter__.return_value = cursor
        chiamata()
    sql, params = cursor.execute.call_args.args
    return " ".join(sql.split()), params


class RigheDocumentoListaTests(unittest.TestCase):

    # Scopo: senza richiesta, l'ordine del documento — non la prima colonna.
    def test_pagina_parte_dall_ordine_del_documento(self):
        for repo, _, _, ordine, _, _ in _DOCUMENTI:
            with self.subTest(repo=repo.__name__):
                sql, _, _ = _pagina(repo, order_by="", order_dir=None)
                self.assertIn(f"ORDER BY v.{ordine[0]} ASC", sql)
                # Le colonne che seguono la prima entrano nello spareggio,
                # crescenti, prima della chiave.
                self.assertIn(", ".join([*(f"v.{c}" for c in ordine[1:]), "v.id ASC"]), sql)

    # Scopo: la pagina e' del documento indicato, e solo delle righe attive.
    def test_pagina_filtra_documento_e_righe_attive(self):
        for repo, vista, fk, _, _, _ in _DOCUMENTI:
            with self.subTest(repo=repo.__name__):
                sql, params, _ = _pagina(repo, documento_id=42)
                self.assertIn(f"FROM {vista} v WHERE v.{fk} = %s AND v.attivo IS TRUE", sql)
                self.assertEqual(params[0], 42)

    # Scopo: una data si legge dalla piu' recente (regola di Tid del 2026-09-02).
    def test_data_senza_direzione_parte_desc(self):
        # ⚠️ Tutte le colonne DESC dichiarate, non una per documento: l'ordine
        #    ne ha due (confermata e richiesta dal cliente).
        for repo, _, _, _, _, data in _DOCUMENTI:
            if data is not None:
                self.assertIn(data, repo._righe_colonne_desc)
            for colonna in repo._righe_colonne_desc:
                with self.subTest(repo=repo.__name__, colonna=colonna):
                    sql, _, _ = _pagina(repo, order_by=colonna, order_dir=None)
                    self.assertIn(f"ORDER BY {repo._righe_ordinamento[colonna]} DESC", sql)

    # Scopo: una chiave che la lista non ordina e' un 400 (`order_by_invalid`):
    #        non finisce nel SQL e non diventa l'ordine del documento in
    #        silenzio (dal 2026-10-20, brief-be-verifica-documentazione-api §A1).
    def test_chiave_fuori_whitelist_e_rifiutata(self):
        for repo, _, _, _ordine, _, _ in _DOCUMENTI:
            with self.subTest(repo=repo.__name__), self.assertRaisesRegex(ValueError, "order_by_invalid"):
                _pagina(repo, order_by="ragione_sociale_completa; DROP", order_dir="desc")

    # Scopo: la lista resta al cap standard per pagina; l'export alza il tetto
    #        col suo `max_limit` per accorgersi di un file troncato.
    def test_pagina_rispetta_il_tetto_e_l_export_lo_alza(self):
        # L'offset del ripiego e' l'ultimo parametro (BB `fetch_paged_with_total`).
        _, params, _ = _pagina(OrdiniRepository, limit=5000, offset=-3)
        self.assertEqual(params[-2:], [MAX_LIMIT, 0])
        _, params, _ = _pagina(OrdiniRepository, limit=10001, max_limit=10001)
        self.assertEqual(params[-2], 10001)

    # Scopo: la lettura COMPLETA (dialog, stampe) legge la vista, solo le
    #        righe attive, nell'ordine del documento.
    def test_lettura_completa_dalla_vista_attive_in_ordine(self):
        for repo, vista, fk, ordine, _, _ in _DOCUMENTI:
            with self.subTest(repo=repo.__name__):
                sql, params = _lettura(lambda r=repo: r().list_righe(9))
                self.assertIn(f"FROM {vista} v WHERE v.{fk} = %s AND v.attivo IS TRUE", sql)
                self.assertIn("ORDER BY " + ", ".join([*(f"v.{c}" for c in ordine), "v.id"]), sql)
                self.assertEqual(params, [9])

    # Scopo: la riga singola ha la stessa proiezione della lista, e una riga
    #        con `attivo = false` non si trova, come nelle altre due letture.
    def test_riga_singola_dalla_vista_solo_attiva(self):
        for repo, vista, _, _, _, _ in _DOCUMENTI:
            with self.subTest(repo=repo.__name__):
                sql, params = _lettura(lambda r=repo: r().get_riga(3))
                self.assertIn(f"FROM {vista} v WHERE v.id = %s AND v.attivo IS TRUE", sql)
                self.assertEqual(params, [3])

    # Scopo: le colonne gemelle (liste 97-99) sono le stesse sui tre
    #        documenti commerciali: ognuno ne aggiunge, nessuno ne toglie.
    def test_whitelist_gemelle_uguali_sulle_righe_commerciali(self):
        for repo in (PreventiviRepository, OrdiniRepository, DdtRepository):
            with self.subTest(repo=repo.__name__):
                self.assertLessEqual(
                    set(COLONNE_RIGHE_COMMERCIALI), set(repo.righe_colonne_ordinabili()),
                )

    # Scopo: la ricerca di ogni documento nomina la SUA lista: un codice
    #        sbagliato leggerebbe le colonne accese di un'altra lista.
    def test_la_ricerca_nomina_la_lista_del_documento(self):
        for repo, _, _, _, lista, _ in _DOCUMENTI:
            with self.subTest(repo=repo.__name__):
                self.assertEqual(repo._righe_ricerca.lista_codice, lista)

    # Scopo: il conteggio (righe_count del dettaglio, guard «senza righe» di
    #        elimina e conferma) conta le sole righe ATTIVE del documento,
    #        sulla tabella e non sulla vista.
    # ⛔ E' qui che vive la regola «le righe disattivate non contano» del
    #    guard di conferma dell'ordine (Regola 2 rev 2026-07-16): prima il
    #    service rifiltrava in Python la lista intera.
    def test_conteggio_sulla_tabella_solo_righe_attive(self):
        for repo, _, fk, _, _, _ in _DOCUMENTI:
            with self.subTest(repo=repo.__name__):
                cursor = MagicMock()
                cursor.fetchone.return_value = (3,)
                with patch.object(_righe_repo_mixin, "connection") as conn:
                    conn.cursor.return_value.__enter__.return_value = cursor
                    self.assertEqual(repo().count_righe(9), 3)
                sql, params = cursor.execute.call_args.args
                sql = " ".join(sql.split())
                self.assertIn(
                    f"FROM {_TABELLE[repo]} WHERE {fk} = %s AND attivo IS TRUE", sql,
                )
                self.assertEqual(params, [9])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
