# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cancello sui `campo_sorgente` delle quattro liste configurabili di
#        `pagamenti`: ogni colonna dichiarata a catalogo deve esistere fra
#        quelle che la lista PROIETTA davvero.
#
#        PERCHE' ESISTE, ed e' una responsabilita' ricevuta. Le quattro liste
#        sono seminate con `vista_sql = NULL` (le alimenta un endpoint di
#        dominio, non una vista), e con quel campo nullo **il guard DB sui
#        `campo_sorgente` non gira**: il team DB lo ha scritto a chiare lettere
#        consegnando il lotto 9 — «l'unico presidio resta quello del backend».
#        Questo file e' quel presidio.
#
#        ⚠️ IL DIFETTO CHE PRESIDIA E' SILENZIOSO. Un `campo_sorgente` che non
#        combacia non solleva niente: `<ListaConfigurabile>` chiede una chiave
#        che nella riga non c'e' e disegna una **colonna vuota** — cioe' la cosa
#        che somiglia di piu' a «quel dato non c'e' ancora». Su elenchi che
#        esistono per non far sparire del denaro e' la risposta peggiore.
#
#        ⭐ LE COLONNE LE DICHIARA IL CURSORE, non le righe. Si legge
#        `cursor.description`, quindi la prova vale anche su una lista che oggi
#        e' **vuota** — che e' il caso in cui serve di piu': una lista senza
#        righe non puo' smentire niente, e un confronto fatto sui dati sarebbe
#        verde per sottrazione. Per la stessa ragione il contesto operatore qui
#        non serve: la RLS toglie le RIGHE, non le colonne.
#
#        ⚠️ LA SEDE E' IL CSV, non la tabella. `80_data` si cambia dal CSV (il
#        mirror e' `runOnChange` e riallinea il database), quindi il confronto
#        si fa contro cio' che sta in git: se i due divergono, a valere e' il
#        CSV, ed e' li' che il difetto va visto.
#
#        ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI):
#        senza database non si sa quali colonne proietti una query. NON SCRIVE
#        NULLA — esegue le sole SELECT di lista, in transazione annullata.
# ------------------------------------------------------------

"""Indice test previsti (opt-in `ZEROERP_TEST_DB_E2E=1`).

- test_ogni_campo_sorgente_a_catalogo_ha_la_sua_colonna: per tutte e quattro le
  liste, ogni `campo_sorgente` del CSV esiste fra le colonne proiettate.
- test_il_csv_dichiara_tutte_e_quattro_le_liste: se una lista sparisce dal seed
  il test sopra diventerebbe verde a vuoto — questo lo impedisce.
"""

from __future__ import annotations

import csv
import unittest
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.db import connection, transaction

from apps.core.tests.db_e2e import richiedi_db_provvisto
from apps.pagamenti.db import pagamenti_repository as repo_mod
from apps.pagamenti.db.pagamenti_repository import PagamentiRepository

# Il seed delle colonne, in git. `BASE_DIR` e' `backend/`, la radice del repo e'
# il suo padre.
CSV_COLONNE = (
    Path(settings.BASE_DIR).parent
    / "db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv"
)

# Le quattro liste del cantiere incassi: id di `ui.lista_definizione` -> come si
# chiama a catalogo. ⚠️ Gli id sono quelli del seed (50-53): un rinumero li fa
# fallire, ed e' il verso giusto — meglio rosso che silenzioso.
LISTE = {
    "50": "pagamenti.distinte",
    "51": "pagamenti.righe",
    "52": "pagamenti.rate_fuori_capienza",
    "53": "pagamenti.eccedenze",
}


# Scopo: legge dal CSV i `campo_sorgente` dichiarati per ciascuna delle quattro
#        liste. Ritorna {lista_id: {campo_sorgente, ...}}.
def _campi_dichiarati() -> dict[str, set[str]]:
    per_lista: dict[str, set[str]] = {lid: set() for lid in LISTE}
    with CSV_COLONNE.open(encoding="utf-8") as fh:
        for riga in csv.DictReader(fh):
            if riga["lista_id"] in per_lista:
                per_lista[riga["lista_id"]].add(riga["campo_sorgente"])
    return per_lista


class ListaCampoSorgenteGuardrailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        richiedi_db_provvisto()
        # ⚠️ Schema presente ma seed assente NON e' una condizione d'ambiente:
        # e' un difetto, e qui si fallisce invece di saltare.
        if not CSV_COLONNE.exists():
            raise AssertionError(f"seed delle colonne non trovato: {CSV_COLONNE}")

    # Scopo: raccoglie le colonne che una lista proietta, eseguendone la query
    #        di pagina e leggendo `cursor.description`. La paginazione passa da
    #        `fetch_paged_with_total`, quindi e' li' che si intercetta.
    # Note: ⚠️ La prima stesura di questa misura spiava `rows_to_list` e
    #        rispondeva «0 colonne esposte» su tutte e quattro — un rosso che
    #        non veniva dal codice ma dalla misura. Anche una prova e' un
    #        programma, e puo' avere il suo difetto.
    def _colonne_proiettate(self, chiamata) -> set[str]:
        viste: set[str] = set()

        def _spia(data_sql, params, **_kw):
            with connection.cursor() as cur:
                cur.execute(data_sql, params)
                viste.update(c[0] for c in (cur.description or []))
                cur.fetchall()
            return [], 0

        with patch.object(repo_mod, "fetch_paged_with_total", _spia):
            chiamata()
        return viste

    def test_ogni_campo_sorgente_a_catalogo_ha_la_sua_colonna(self):
        repo = PagamentiRepository()
        chiamate = {
            "50": lambda: repo.list_distinte(
                order_by="data_contabile", order_dir="DESC", limit=1, offset=0
            ),
            "51": lambda: repo.list_righe_coda(
                stati=("DA_ABBINARE",),
                order_by="data_pagamento",
                order_dir="DESC",
                limit=1,
                offset=0,
            ),
            "52": lambda: repo.list_rate_fuori_capienza(
                order_by="data_scadenza", order_dir="DESC", limit=1, offset=0
            ),
            "53": lambda: repo.list_eccedenze(
                order_by="eccedenza_cliente", order_dir="DESC", limit=1, offset=0
            ),
        }
        dichiarati = _campi_dichiarati()
        mancanti: dict[str, list[str]] = {}
        with transaction.atomic():
            for lista_id, codice in LISTE.items():
                proiettate = self._colonne_proiettate(chiamate[lista_id])
                assenti = sorted(dichiarati[lista_id] - proiettate)
                if assenti:
                    mancanti[codice] = assenti
            transaction.set_rollback(True)
        self.assertEqual(
            mancanti,
            {},
            "campo_sorgente a catalogo senza colonna nella lista: a video "
            "sarebbe una colonna VUOTA, non un errore",
        )

    # Scopo: il test sopra confronta contro cio' che il CSV dichiara. Se una
    #        lista uscisse dal seed, l'insieme diventerebbe vuoto e il confronto
    #        passerebbe **senza verificare niente** — la forma classica del
    #        verde per sottrazione.
    def test_il_csv_dichiara_tutte_e_quattro_le_liste(self):
        dichiarati = _campi_dichiarati()
        vuote = sorted(LISTE[lid] for lid, campi in dichiarati.items() if not campi)
        self.assertEqual(vuote, [], "liste senza colonne a catalogo")

    # Scopo: OGNI ordinamento dichiarato produce SQL valido — provato per
    #        intero, non a campione.
    # Note: ⭐ E' la meta' che `test_liste_configurabili_seed` non copre: quello
    #        confronta due ELENCHI (seed e whitelist) e vale senza database;
    #        qui si guarda se la query PARTE. Sono difetti diversi: la' un nome
    #        che il frontend manda e il backend non riconosce (400), qui una
    #        colonna che il backend riconosce e l'SQL non ha (**500**).
    #        ⚠️ Il secondo e' gia' successo su questo dominio il 2026-08-24: la
    #        coda dichiarava di saper ordinare per `distinta`, ma quella colonna
    #        non era nel `SELECT` — e i test ne provavano UNO.
    #        ⛔ Un ordinamento si prova solo CHIEDENDOLO: non c'e' modo di
    #        dedurlo leggendo il codice.
    def test_ogni_ordinamento_dichiarato_produce_sql_valido(self):
        repo = PagamentiRepository()
        casi = {
            "pagamenti.distinte": (
                repo_mod.DISTINTE_SORT_COLUMNS,
                lambda c, d: repo.list_distinte(order_by=c, order_dir=d, limit=1, offset=0),
            ),
            "pagamenti.righe": (
                repo_mod.RIGHE_SORT_COLUMNS,
                lambda c, d: repo.list_righe_coda(
                    stati=("DA_ABBINARE",), order_by=c, order_dir=d, limit=1, offset=0
                ),
            ),
            "pagamenti.rate_fuori_capienza": (
                repo_mod.RATE_FUORI_CAPIENZA_SORT_COLUMNS,
                lambda c, d: repo.list_rate_fuori_capienza(
                    order_by=c, order_dir=d, limit=1, offset=0
                ),
            ),
            "pagamenti.eccedenze": (
                repo_mod.ECCEDENZE_SORT_COLUMNS,
                lambda c, d: repo.list_eccedenze(order_by=c, order_dir=d, limit=1, offset=0),
            ),
        }
        provate = 0
        with transaction.atomic():
            for lista, (whitelist, chiamata) in casi.items():
                # ⚠️ ENTRAMBI i versi: la direzione finisce nella stessa clausola
                #    SQL della colonna, e `sql_order_direction` ci attacca anche
                #    la posizione dei NULL — un ripiego malformato si vedrebbe su
                #    un verso solo.
                for colonna in whitelist:
                    for verso in ("ASC", "DESC"):
                        with self.subTest(lista=lista, colonna=colonna, verso=verso):
                            self._colonne_proiettate(lambda: chiamata(colonna, verso))
                            provate += 1
            transaction.set_rollback(True)
        # Se una whitelist si svuotasse, il ciclo non proverebbe niente e il
        # test sarebbe verde a vuoto.
        self.assertGreaterEqual(provate, 2 * sum(len(w) for w, _ in casi.values()))
