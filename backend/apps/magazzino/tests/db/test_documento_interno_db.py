# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LA CATENA INTERA del documento interno sul DATABASE PROVVISTO —
#        l'unico livello che vede la giuntura Python↔PL/pgSQL (api.md §Test,
#        secondo livello): bozza → riga → CONFIRM → piano → registra → POSTED,
#        il rifiuto del piano `NON_POSTABILE` che ferma TUTTO, la rettifica
#        alla media, il 404 no-leak dell'altro emittente, i lookup di riga.
#        E' il copione di collaudo del piano (§8) provato PRIMA del video.
# Note: ⚠️ Il mondo si COSTRUISCE, non si cerca (guida pgtap §79): azienda e
#       operatore da `fn_pgtap_crea_emittente_operatore`, poi il CONTESTO
#       (`fn_pgtap_set_contesto_operatore` — senza, ogni tabella RLS risponde
#       ZERO righe e un test che cerca materiale «passa» per sottrazione), poi
#       due magazzini (uno a ubicazioni) e tre articoli (gestito, non gestito,
#       per lotti) dai BB `dbops.fn_pgtap_crea_magazzino` / `_crea_articolo`
#       (P-9 del brief). Tutto in transazione ANNULLATA.
#       ⚠️ Ogni rifiuto atteso gira in un SAVEPOINT (`transaction.atomic()`
#       annidato): un `RAISE` del database lascia la transazione esterna
#       «interrotta», e il passo successivo fallirebbe per quello e non per
#       il suo motivo.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) DocumentoInternoDbTests.test_il_primo_carico_dall_inventario
2) DocumentoInternoDbTests.test_la_riga_non_postabile_ferma_tutto_il_posting
3) DocumentoInternoDbTests.test_la_riga_incoerente_passa_e_il_form_la_vede
4) DocumentoInternoDbTests.test_la_rettifica_negativa_va_alla_media
5) DocumentoInternoDbTests.test_posted_non_si_elimina_ne_si_modifica_e_confirm_riapre
6) DocumentoInternoDbTests.test_un_altro_emittente_non_vede_il_documento
7) DocumentoInternoDbTests.test_i_lookup_di_riga_filtrano_per_padre
8) DocumentoInternoDbTests.test_ogni_ordinamento_della_whitelist_esegue
9) DocumentoInternoDbTests.test_il_conteggio_della_lista_non_e_un_eco
10) DocumentoInternoDbTests.test_la_capability_segue_la_matrice_del_guard — R-1, 2026-09-23
11) DocumentoInternoDbTests.test_registra_spento_col_motivo_nei_tre_casi — R-1, 2026-09-23
12) DocumentoInternoDbTests.test_il_duplicato_di_posizione_ha_il_suo_codice — R-2, 2026-09-23
13) DocumentoInternoDbTests.test_la_ricerca_trova_ogni_colonna_accesa — 2026-09-23
"""
from __future__ import annotations

import unittest
from decimal import Decimal

from django.db import connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import (
    richiedi_db_provvisto,
    richiedi_ruolo_soggetto_a_rls,
    verifica_ricerca_colonna_per_colonna,
)
from apps.magazzino.db.magazzino_repository import (
    DOCUMENTI_SORT_COLUMNS,
    MOVIMENTI_SORT_COLUMNS,
    INVENTARIO_RIGHE_SORT_COLUMNS,
    PIANO_SORT_COLUMNS,
)
from apps.magazzino.services import consultazione_service, magazzino_service

# Il mondo: azienda con operatore (PRIMA del contesto), il contesto, due
# magazzini (senza e con ubicazioni) e tre articoli.
_FIXTURE: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))",
    # I verbi di registrazione chiedono l'azione nella prima riga
    # (`script.fn_guard_azione`): l'operatore del mondo non ce l'ha, gliela
    # si concede (brief-db-magazzino-verbi-con-permesso §6).
    "SELECT dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _mondo), 'registra_magazzino')",
    """
    CREATE TEMP TABLE _mag AS
    SELECT dbops.fn_pgtap_crea_magazzino('BE-MAG-A', false) AS mag_a,
           dbops.fn_pgtap_crea_magazzino('BE-MAG-U', true)  AS mag_u
    """,
    """
    CREATE TEMP TABLE _art AS
    SELECT dbops.fn_pgtap_crea_articolo('BE-ART-1')                 AS art,
           dbops.fn_pgtap_crea_articolo('BE-ART-NG', false)         AS art_ng,
           dbops.fn_pgtap_crea_articolo('BE-ART-L', true, true)     AS art_l
    """,
    # Un'ubicazione nel magazzino a ubicazioni, per il lookup.
    """
    INSERT INTO magazzino.ubicazioni (magazzino_id, codice, tipo_id)
    SELECT mag_u, 'UX', (SELECT id FROM config.tipi_ubicazione WHERE codice_interno = 'TIPO_UBI_STORAGE')
      FROM _mag
    """,
    # Un lotto dell'articolo per lotti, per il lookup.
    """
    INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo)
    SELECT art_l, 'L-2026-01', script.fn_data_operativa() FROM _art
    """,
)


class _Mondo:
    """Gli id del mondo costruito."""

    def __init__(self, cur) -> None:
        for passo in _FIXTURE:
            cur.execute(passo)
        cur.execute("SELECT mag_a, mag_u FROM _mag")
        self.mag_a, self.mag_u = (int(x) for x in cur.fetchone())
        cur.execute("SELECT art, art_ng, art_l FROM _art")
        self.art, self.art_ng, self.art_l = (str(x) for x in cur.fetchone())
        cur.execute("SELECT auth_user_id FROM _mondo")
        self.uid = int(cur.fetchone()[0])


class DocumentoInternoDbTests(unittest.TestCase):
    """Il documento interno, per intero, sul mondo costruito."""

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()
        # ⛔ Il 404 no-leak (f) si prova solo con un ruolo che la RLS vede: come
        #    owner (in CI `DB_USER: zeroerp` fino al 2026-09-19) passerebbe
        #    tutto e il rosso accuserebbe la RLS invece del ruolo.
        richiedi_ruolo_soggetto_a_rls("magazzino.inventari")

    # Scopo: esegue `azione(cur, mondo)` nel mondo costruito, in una
    #        transazione SEMPRE annullata.
    def _nel_mondo(self, azione):
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    return azione(cur, _Mondo(cur))
            finally:
                transaction.set_rollback(True)

    # Scopo: esegue un'azione che DEVE essere rifiutata, in un savepoint, e
    #        torna il `ServiceError`.
    @staticmethod
    def _rifiuto(fn) -> ServiceError:
        try:
            with transaction.atomic():
                fn()
        except ServiceError as e:
            return e
        raise AssertionError("atteso un rifiuto, e' passato")

    # Scopo: una bozza con una riga di 10 pezzi a 7 €, confermata.
    @staticmethod
    def _inventario_confermato(m: _Mondo) -> dict:
        d = magazzino_service.crea_documento(
            "inventari", {"magazzino_id": m.mag_a, "descrizione": "primo carico"},
        )
        magazzino_service.crea_riga(
            "inventari", d["id"], {"articolo_id": m.art, "qta_contata": "10", "costo_unitario": 7},
        )
        return magazzino_service.cambia_stato_documento("inventari", d["id"], {"stato": "CONFIRM"})

    # Scopo: (a) del copione — il primo carico in assoluto si fa DALL'INVENTARIO:
    #        piano `INV_INIZIALE` gia' in bozza (anteprima), un movimento
    #        registrato, `POSTED`, `qta_sistema = 0`, disponibilita' a 10.
    def test_il_primo_carico_dall_inventario(self):
        def _prova(cur, m):
            d = magazzino_service.crea_documento(
                "inventari", {"magazzino_id": m.mag_a, "descrizione": "primo carico"},
            )
            self.assertEqual(d["stato"], "DRAFT")
            self.assertFalse(d["magazzino_usa_ubicazioni"])
            self.assertEqual(d["piano_riepilogo"]["n_righe"], 0)
            r = magazzino_service.crea_riga(
                "inventari", d["id"], {"articolo_id": m.art, "qta_contata": "10", "costo_unitario": 7},
            )
            self.assertEqual(r["articolo_codice"], "BE-ART-1")
            self.assertEqual(r["qta_contata"], Decimal("10"))
            self.assertIsNone(r["qta_sistema"])
            # Il piano si legge anche in DRAFT: e' un'anteprima.
            piano = magazzino_service.list_piano("inventari", d["id"], limit=10)
            self.assertEqual([p["esito"] for p in piano["results"]], ["INV_INIZIALE"])
            self.assertEqual(piano["results"][0]["delta"], Decimal("10"))
            d = magazzino_service.cambia_stato_documento("inventari", d["id"], {"stato": "CONFIRM"})
            self.assertEqual(d["stato"], "CONFIRM")
            self.assertEqual(d["piano_riepilogo"]["n_con_delta"], 1)
            # In CONFIRM le righe sono congelate: lo dice il guard, non il BE.
            e = self._rifiuto(lambda: magazzino_service.crea_riga(
                "inventari", d["id"], {"articolo_id": m.art, "qta_contata": 1},
            ))
            self.assertEqual(e.code, "E_MAG_DOCUMENTO_RIGHE_CONGELATE")

            esito = magazzino_service.registra_documento("inventari", d["id"])
            self.assertEqual(esito["n_movimenti"], 1)
            self.assertEqual(esito["movimenti"][0]["qta"], Decimal("10"))
            self.assertEqual(esito["documento"]["stato"], "POSTED")
            righe = magazzino_service.list_righe("inventari", d["id"], limit=10)["results"]
            self.assertEqual(righe[0]["qta_sistema"], Decimal("0"))

            mov = consultazione_service.list_movimenti(auth_user_id=m.uid, inventario_id=d["id"], limit=10)
            self.assertEqual(mov["count"], 1)
            self.assertEqual(mov["results"][0]["causale_codice"], "INV_INIZIALE")
            self.assertEqual(mov["results"][0]["sorgente_codice_interno"], "INVENTARIO_RIGA")
            self.assertEqual(mov["results"][0]["costo_unitario"], Decimal("7"))
            disp = consultazione_service.list_disponibilita(auth_user_id=m.uid, magazzino_id=m.mag_a, limit=10)
            self.assertEqual([(x["articolo_codice"], x["disponibile"]) for x in disp["results"]],
                             [("BE-ART-1", Decimal("10"))])
            per_art = consultazione_service.list_disponibilita_articoli(articolo_id=m.art, limit=10)
            self.assertEqual(per_art["results"][0]["n_magazzini"], 1)
        self._nel_mondo(_prova)

    # Scopo: (c) — la riga su un articolo NON gestito entra in bozza (Q-3), il
    #        piano la dichiara `NON_POSTABILE` col motivo della check, e
    #        `registra/` rifiuta TUTTO: lo stato resta `CONFIRM`.
    def test_la_riga_non_postabile_ferma_tutto_il_posting(self):
        def _prova(cur, m):
            d = magazzino_service.crea_documento("inventari", {"magazzino_id": m.mag_a})
            magazzino_service.crea_riga("inventari", d["id"], {"articolo_id": m.art, "qta_contata": 4})
            magazzino_service.crea_riga("inventari", d["id"], {"articolo_id": m.art_ng, "qta_contata": 3})
            magazzino_service.cambia_stato_documento("inventari", d["id"], {"stato": "CONFIRM"})
            piano = magazzino_service.list_piano("inventari", d["id"], limit=10, order_by="esito")
            esiti = {p["esito"]: p for p in piano["results"]}
            self.assertEqual(set(esiti), {"INV_INIZIALE", "NON_POSTABILE"})
            self.assertEqual(
                esiti["NON_POSTABILE"]["posting_blocco_reason_key"],
                "magazzino.riga.blocco.articolo_non_gestito",
            )
            self.assertEqual(magazzino_service.get_documento("inventari", d["id"])["piano_riepilogo"]["n_non_postabili"], 1)
            e = self._rifiuto(lambda: magazzino_service.registra_documento("inventari", d["id"]))
            self.assertEqual(e.code, "E_MAG_ARTICOLO_NON_GESTITO")
            self.assertEqual(magazzino_service.get_documento("inventari", d["id"])["stato"], "CONFIRM")
            # Niente e' stato scritto sul registro: neanche la riga buona.
            self.assertEqual(
                consultazione_service.list_movimenti(auth_user_id=m.uid, inventario_id=d["id"], limit=10)["count"], 0,
            )
        self._nel_mondo(_prova)

    # Scopo: (d) — una riga senza lotto su un articolo `requires_lotto` PASSA
    #        (Q-3) e `righe/motivi/` la dichiara: la stessa funzione del piano.
    def test_la_riga_incoerente_passa_e_il_form_la_vede(self):
        def _prova(cur, m):
            d = magazzino_service.crea_documento("inventari", {"magazzino_id": m.mag_a})
            r = magazzino_service.crea_riga("inventari", d["id"], {"articolo_id": m.art_l, "qta_contata": 2})
            self.assertTrue(r["articolo_requires_lotto"])
            motivi = magazzino_service.motivi_riga(
                magazzino_id=m.mag_a, articolo_id=m.art_l, lotto_id=None, asset_id=None, ubicazione_id=None,
            )["motivi"]
            self.assertEqual([x["reason_key"] for x in motivi], ["magazzino.riga.blocco.lotto_obbligatorio"])
            self.assertEqual(motivi[0]["dettaglio"]["campo"], "lotto_id")
            # Col lotto giusto, nessun motivo: e' cio' che il posting scrivera'.
            cur.execute("SELECT id FROM magazzino.lotti WHERE codice = 'L-2026-01'")
            lotto_id = int(cur.fetchone()[0])
            self.assertEqual(magazzino_service.motivi_riga(
                magazzino_id=m.mag_a, articolo_id=m.art_l, lotto_id=lotto_id, asset_id=None, ubicazione_id=None,
            )["motivi"], [])
            # Sul magazzino a ubicazioni, senza ubicazione: un motivo suo.
            self.assertEqual([x["reason_key"] for x in magazzino_service.motivi_riga(
                magazzino_id=m.mag_u, articolo_id=m.art, lotto_id=None, asset_id=None, ubicazione_id=None,
            )["motivi"]], ["magazzino.riga.blocco.ubicazione_obbligatoria"])
        self._nel_mondo(_prova)

    # Scopo: (e) — la rettifica −5 dopo il carico: un movimento `RETT_NEG` al
    #        costo medio (7), disponibilita' a 5. La famiglia e' la stessa
    #        implementazione: qui si prova la SECONDA configurazione.
    def test_la_rettifica_negativa_va_alla_media(self):
        def _prova(cur, m):
            d = self._inventario_confermato(m)
            magazzino_service.registra_documento("inventari", d["id"])
            rt = magazzino_service.crea_documento("rettifiche", {"magazzino_id": m.mag_a})
            self.assertIsNone(rt["descrizione"])
            self.assertNotIn("piano_riepilogo", rt)
            rr = magazzino_service.crea_riga(
                "rettifiche", rt["id"], {"articolo_id": m.art, "qta_delta": -5, "motivo": "ROTTURA"},
            )
            self.assertEqual(rr["qta_delta"], Decimal("-5"))
            self.assertEqual(rr["motivo"], "ROTTURA")
            e = self._rifiuto(lambda: magazzino_service.crea_riga(
                "rettifiche", rt["id"], {"articolo_id": m.art, "qta_delta": 0},
            ))
            self.assertEqual(e.code, "E_MAGAZZINO_VALIDATION")
            self.assertEqual(e.context.get("field"), "qta_delta")
            e = self._rifiuto(lambda: magazzino_service.list_piano("rettifiche", rt["id"], limit=10))
            self.assertEqual(e.code, "E_MAGAZZINO_VALIDATION")
            magazzino_service.cambia_stato_documento("rettifiche", rt["id"], {"stato": "CONFIRM"})
            esito = magazzino_service.registra_documento("rettifiche", rt["id"])
            self.assertEqual(esito["n_movimenti"], 1)
            self.assertEqual(esito["movimenti"][0]["qta"], Decimal("-5"))
            mov = consultazione_service.list_movimenti(auth_user_id=m.uid, rettifica_id=rt["id"], limit=10)["results"]
            self.assertEqual((mov[0]["causale_codice"], mov[0]["costo_unitario"]), ("RETT_NEG", Decimal("7")))
            disp = consultazione_service.list_disponibilita(
                auth_user_id=m.uid, magazzino_id=m.mag_a, articolo_id=m.art, limit=10,
            )["results"]
            self.assertEqual(disp[0]["disponibile"], Decimal("5"))
            # `descrizione` non esiste sulla rettifica: il PATCH la rifiuta.
            e = self._rifiuto(lambda: magazzino_service.aggiorna_documento("rettifiche", rt["id"], {"descrizione": "x"}))
            self.assertEqual(e.code, "E_MAGAZZINO_VALIDATION")
        self._nel_mondo(_prova)

    # Scopo: (g) — `POSTED` non si elimina, non si modifica (righe) e non torna
    #        in bozza; `CONFIRM → DRAFT` riapre le righe; `POSTED` non si CHIEDE.
    def test_posted_non_si_elimina_ne_si_modifica_e_confirm_riapre(self):
        def _prova(cur, m):
            d = self._inventario_confermato(m)
            riga = magazzino_service.list_righe("inventari", d["id"], limit=10)["results"][0]
            # Da CONFIRM si riapre, e in bozza la riga si corregge.
            self.assertEqual(magazzino_service.cambia_stato_documento("inventari", d["id"], {"stato": "DRAFT"})["stato"], "DRAFT")
            r = magazzino_service.aggiorna_riga("inventari", d["id"], riga["id"], {"qta_contata": 12})
            self.assertEqual(r["qta_contata"], Decimal("12"))
            magazzino_service.cambia_stato_documento("inventari", d["id"], {"stato": "CONFIRM"})
            magazzino_service.registra_documento("inventari", d["id"])
            for fn, atteso in (
                (lambda: magazzino_service.elimina_documento("inventari", d["id"]), "E_MAG_DOCUMENTO_NON_ELIMINABILE"),
                (lambda: magazzino_service.aggiorna_riga("inventari", d["id"], riga["id"], {"qta_contata": 3}), "E_MAG_DOCUMENTO_RIGHE_CONGELATE"),
                (lambda: magazzino_service.elimina_riga("inventari", d["id"], riga["id"]), "E_MAG_DOCUMENTO_RIGHE_CONGELATE"),
                (lambda: magazzino_service.cambia_stato_documento("inventari", d["id"], {"stato": "DRAFT"}), "E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA"),
                # ⛔ `POSTED` non e' richiedibile: il vocabolario lo ferma PRIMA
                #    del guard, che risponderebbe un TECNICO.
                (lambda: magazzino_service.cambia_stato_documento("inventari", d["id"], {"stato": "POSTED"}), "E_MAGAZZINO_VALIDATION"),
            ):
                self.assertEqual(self._rifiuto(fn).code, atteso)
            # Q-2: la testata resta libera anche su POSTED — nessun guard nel BE.
            self.assertEqual(
                magazzino_service.aggiorna_documento("inventari", d["id"], {"descrizione": "conteggio di settembre"})["descrizione"],
                "conteggio di settembre",
            )
            # E una bozza si elimina, righe comprese.
            d2 = magazzino_service.crea_documento("inventari", {"magazzino_id": m.mag_a})
            magazzino_service.crea_riga("inventari", d2["id"], {"articolo_id": m.art, "qta_contata": 1})
            self.assertTrue(magazzino_service.elimina_documento("inventari", d2["id"])["eliminato"])
            self.assertEqual(self._rifiuto(lambda: magazzino_service.get_documento("inventari", d2["id"])).code,
                             "E_MAG_DOCUMENTO_NON_TROVATO")
        self._nel_mondo(_prova)

    # Scopo: (f) — l'operatore di un ALTRO emittente non vede il documento
    #        (404 no-leak, la RLS via magazzino) e la sua lista e' vuota; e il
    #        magazzino dell'altro non si sceglie alla nascita (400 col campo).
    def test_un_altro_emittente_non_vede_il_documento(self):
        def _prova(cur, m):
            d = self._inventario_confermato(m)
            cur.execute("CREATE TEMP TABLE _mondo2 AS SELECT x.* FROM dbops.fn_pgtap_crea_emittente_operatore('B2') x")
            cur.execute("SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo2))")
            cur.execute("SELECT auth_user_id FROM _mondo2")
            uid2 = int(cur.fetchone()[0])
            self.assertEqual(self._rifiuto(lambda: magazzino_service.get_documento("inventari", d["id"])).code,
                             "E_MAG_DOCUMENTO_NON_TROVATO")
            self.assertEqual(magazzino_service.list_documenti("inventari", auth_user_id=uid2, limit=10)["count"], 0)
            e = self._rifiuto(lambda: magazzino_service.crea_documento("inventari", {"magazzino_id": m.mag_a}))
            self.assertEqual((e.code, e.context.get("field")), ("E_MAGAZZINO_VALIDATION", "magazzino_id"))
            self.assertEqual(consultazione_service.list_movimenti(auth_user_id=uid2, limit=10, magazzino_id=m.mag_a)["count"], 0)
        self._nel_mondo(_prova)

    # Scopo: i tre lookup di riga rispondono SOLO per il padre: le ubicazioni
    #        del magazzino, i lotti dell'articolo, i seriali dell'emittente.
    def test_i_lookup_di_riga_filtrano_per_padre(self):
        def _prova(cur, m):
            self.assertEqual([u["codice"] for u in magazzino_service.lookup_ubicazioni(m.mag_u)["results"]], ["UX"])
            self.assertEqual(magazzino_service.lookup_ubicazioni(m.mag_a)["results"], [])
            self.assertEqual([x["codice"] for x in magazzino_service.lookup_lotti(articolo_id=m.art_l, search=None)["results"]], ["L-2026-01"])
            self.assertEqual(magazzino_service.lookup_lotti(articolo_id=m.art_l, search="ZZZ")["results"], [])
            self.assertEqual(magazzino_service.lookup_lotti(articolo_id=m.art, search=None)["results"], [])
            self.assertEqual(magazzino_service.lookup_assets(articolo_id=m.art, magazzino_id=m.mag_a)["results"], [])
        self._nel_mondo(_prova)

    # Scopo: ogni colonna delle whitelist, in ENTRAMBI i versi, produce SQL che
    #        parte — il verso che un mock non sa rifiutare (500, non 400).
    def test_ogni_ordinamento_della_whitelist_esegue(self):
        def _prova(cur, m):
            d = self._inventario_confermato(m)
            for col in DOCUMENTI_SORT_COLUMNS:
                for verso in ("asc", "desc"):
                    for fam in ("inventari", "rettifiche"):
                        magazzino_service.list_documenti(fam, auth_user_id=m.uid, limit=5, order_by=col, order_dir=verso)
            for col in INVENTARIO_RIGHE_SORT_COLUMNS:
                for verso in ("asc", "desc"):
                    magazzino_service.list_righe("inventari", d["id"], limit=5, order_by=col, order_dir=verso)
            for col in PIANO_SORT_COLUMNS:
                for verso in ("asc", "desc"):
                    magazzino_service.list_piano("inventari", d["id"], limit=5, order_by=col, order_dir=verso)
            for col in MOVIMENTI_SORT_COLUMNS:
                for verso in ("asc", "desc"):
                    consultazione_service.list_movimenti(auth_user_id=m.uid, limit=5, order_by=col, order_dir=verso)
        self._nel_mondo(_prova)

    # Scopo: il `count` viene da `COUNT(*) OVER ()`, non da `len(results)`:
    #        con `limit=1` su due documenti il totale dice 2 e la pagina 1.
    def test_il_conteggio_della_lista_non_e_un_eco(self):
        def _prova(cur, m):
            magazzino_service.crea_documento("inventari", {"magazzino_id": m.mag_a, "descrizione": "uno"})
            magazzino_service.crea_documento("inventari", {"magazzino_id": m.mag_u, "descrizione": "due"})
            esito = magazzino_service.list_documenti("inventari", auth_user_id=m.uid, limit=1)
            self.assertEqual((esito["count"], len(esito["results"])), (2, 1))
            # Il filtro per magazzino e la ricerca libera restringono davvero.
            self.assertEqual(magazzino_service.list_documenti("inventari", auth_user_id=m.uid, limit=10, magazzino_id=m.mag_u)["count"], 1)
            self.assertEqual(magazzino_service.list_documenti("inventari", auth_user_id=m.uid, limit=10, search="uno")["count"], 1)
            self.assertEqual(magazzino_service.list_documenti("inventari", auth_user_id=m.uid, limit=10, search="MAG-U")["count"], 1)
        self._nel_mondo(_prova)

    # ══════════════════════════════════════════════════════════════
    #  R-1 / R-2 — la capability e il duplicato (2026-09-23)
    # ══════════════════════════════════════════════════════════════

    # Scopo: le azioni proposte sono ESATTAMENTE quelle che il guard ammette,
    #        perche' vengono dalla stessa matrice. Si prova COSTRUENDO le
    #        transizioni, non leggendo i dati di oggi: per ogni stato si
    #        confronta cio' che la capability propone con cio' che il guard
    #        accetta davvero (AGENTS.md §corollario sui test).
    # ⛔ `POSTED` non e' mai fra le azioni: quella porta la apre solo
    #    `registra/`, e fra le proposte sarebbe un 500 promesso a un pulsante.
    def test_la_capability_segue_la_matrice_del_guard(self):
        def _prova(cur, m):
            d = magazzino_service.crea_documento("inventari", {"magazzino_id": m.mag_a})
            doc_id = d["id"]

            # DRAFT: si conferma o si annulla; si scrive tutto.
            caps = magazzino_service.get_documento("inventari", doc_id)["capabilities"]
            # ⭐ I NOMI del blob, per intero: sono il contratto che il drawer
            #    legge campo per campo (`capabilities.can_registra_reason_key`
            #    e compagni). Un campo rinominato a DB non farebbe fallire
            #    niente — il pulsante resterebbe spento per sempre, e a video
            #    sembrerebbe una regola (api.md §Capability: «un campo
            #    dichiarato e mai letto sembra presidiato e non presidia»).
            self.assertEqual(set(caps), {
                "stato_codice", "available_actions", "can_change_state",
                "can_edit_testata", "can_edit_righe", "can_delete",
                "can_registra", "can_registra_reason", "can_registra_reason_key",
                "stato_info_key",
            })
            self.assertEqual(set(caps["available_actions"][0]), {
                "key", "target_state", "label_key",
                "requires_confirm", "enabled", "reason", "reason_key", "manuale",
            })
            self.assertEqual(caps["stato_codice"], "DRAFT")
            self.assertEqual({a["target_state"] for a in caps["available_actions"]}, {"CONFIRM", "CANCEL"})
            self.assertEqual({a["key"] for a in caps["available_actions"]}, {"conferma", "annulla"})
            self.assertTrue(caps["can_edit_testata"] and caps["can_edit_righe"] and caps["can_delete"])
            self.assertIsNone(caps["stato_info_key"])
            # ⚠️ L'annullamento e' l'unica che chiede conferma: e' terminale.
            per_key = {a["key"]: a for a in caps["available_actions"]}
            self.assertTrue(per_key["annulla"]["requires_confirm"])
            self.assertFalse(per_key["conferma"]["requires_confirm"])

            # CONFIRM: si registra, si riapre, si annulla. Niente scrittura.
            magazzino_service.crea_riga(
                "inventari", doc_id, {"articolo_id": m.art, "qta_contata": "10", "costo_unitario": 7},
            )
            magazzino_service.cambia_stato_documento("inventari", doc_id, {"stato": "CONFIRM"})
            caps = magazzino_service.get_documento("inventari", doc_id)["capabilities"]
            self.assertEqual({a["target_state"] for a in caps["available_actions"]}, {"DRAFT", "CANCEL"})
            self.assertFalse(caps["can_edit_righe"] or caps["can_delete"])
            self.assertTrue(caps["can_registra"])
            self.assertIsNone(caps["can_registra_reason"])

            # POSTED: nessuna azione, e la nota che dice qual e' la strada.
            magazzino_service.registra_documento("inventari", doc_id)
            caps = magazzino_service.get_documento("inventari", doc_id)["capabilities"]
            self.assertEqual(caps["available_actions"], [])
            self.assertFalse(caps["can_change_state"])
            self.assertFalse(caps["can_registra"])
            self.assertEqual(caps["stato_info_key"], "magazzino.documenti_interni.stato_info.posted")

            # E cio' che la capability NON propone, il guard lo rifiuta: le due
            # facce della stessa matrice.
            e = self._rifiuto(lambda: magazzino_service.cambia_stato_documento(
                "inventari", doc_id, {"stato": "DRAFT"},
            ))
            self.assertEqual(e.code, "E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA")

            # CANCEL: terminale, con la sua nota.
            altro = magazzino_service.crea_documento("inventari", {"magazzino_id": m.mag_a})
            magazzino_service.cambia_stato_documento("inventari", altro["id"], {"stato": "CANCEL"})
            caps = magazzino_service.get_documento("inventari", altro["id"])["capabilities"]
            self.assertEqual(caps["available_actions"], [])
            self.assertEqual(caps["stato_info_key"], "magazzino.documenti_interni.stato_info.cancel")
        self._nel_mondo(_prova)

    # Scopo: «Registra» e' spento col motivo GIUSTO nei tre casi con cui le
    #        madri del posting rifiutano, e nell'ordine di precedenza
    #        dichiarato (stato > righe > postabilita'). ⭐ E' la prova che il
    #        pulsante non promette cio' che il database rifiutera': la sede e'
    #        una sola (`fn_check_documento_interno_registrabile`).
    def test_registra_spento_col_motivo_nei_tre_casi(self):
        def _prova(cur, m):
            # (1) non confermato — in DRAFT non si registra.
            d = magazzino_service.crea_documento("inventari", {"magazzino_id": m.mag_a})
            caps = magazzino_service.get_documento("inventari", d["id"])["capabilities"]
            self.assertFalse(caps["can_registra"])
            self.assertEqual(caps["can_registra_reason"], "DOCUMENTO_NON_CONFERMATO")
            self.assertEqual(
                caps["can_registra_reason_key"],
                "magazzino.documenti_interni.registra_reason.non_confermato",
            )

            # (2) senza righe — confermato ma vuoto.
            magazzino_service.cambia_stato_documento("inventari", d["id"], {"stato": "CONFIRM"})
            caps = magazzino_service.get_documento("inventari", d["id"])["capabilities"]
            self.assertEqual(caps["can_registra_reason"], "DOCUMENTO_SENZA_RIGHE")
            self.assertEqual(
                caps["can_registra_reason_key"],
                "magazzino.documenti_interni.registra_reason.senza_righe",
            )
            # ⭐ E il motivo e' lo STESSO codice con cui la madre rifiuta.
            e = self._rifiuto(lambda: magazzino_service.registra_documento("inventari", d["id"]))
            self.assertEqual(e.code, "E_MAG_DOCUMENTO_SENZA_RIGHE")

            # (3) righe non postabili — l'articolo non e' gestito a magazzino.
            d2 = magazzino_service.crea_documento("inventari", {"magazzino_id": m.mag_a})
            magazzino_service.crea_riga("inventari", d2["id"], {"articolo_id": m.art_ng, "qta_contata": 3})
            magazzino_service.cambia_stato_documento("inventari", d2["id"], {"stato": "CONFIRM"})
            caps = magazzino_service.get_documento("inventari", d2["id"])["capabilities"]
            self.assertFalse(caps["can_registra"])
            self.assertEqual(caps["can_registra_reason"], "RIGHE_NON_POSTABILI")
            self.assertEqual(
                caps["can_registra_reason_key"],
                "magazzino.documenti_interni.registra_reason.righe_non_postabili",
            )
            e = self._rifiuto(lambda: magazzino_service.registra_documento("inventari", d2["id"]))
            self.assertEqual(e.code, "E_MAG_ARTICOLO_NON_GESTITO")
        self._nel_mondo(_prova)

    # Scopo: R-2 — due letture della stessa posizione sono la stessa riga
    #        scritta due volte: il `23505` di `uq_mag_inventari_righe_posizione`
    #        esce come CODICE registrato, col campo da accendere.
    # ⛔ La rettifica NON lo prende: due delta sulla stessa posizione sono due
    #    correzioni (C14), e a DB il vincolo non c'e'.
    def test_il_duplicato_di_posizione_ha_il_suo_codice(self):
        def _prova(cur, m):
            d = magazzino_service.crea_documento("inventari", {"magazzino_id": m.mag_a})
            magazzino_service.crea_riga("inventari", d["id"], {"articolo_id": m.art, "qta_contata": 4})
            e = self._rifiuto(lambda: magazzino_service.crea_riga(
                "inventari", d["id"], {"articolo_id": m.art, "qta_contata": 6},
            ))
            self.assertEqual(e.code, "E_MAG_INVENTARIO_RIGA_POSIZIONE_DUPLICATA")
            self.assertEqual(e.context.get("field"), "articolo_id")

            # La rettifica ammette due righe sulla stessa posizione.
            r = magazzino_service.crea_documento("rettifiche", {"magazzino_id": m.mag_a})
            magazzino_service.crea_riga(
                "rettifiche", r["id"], {"articolo_id": m.art, "qta_delta": 2, "motivo": "ROTTURA"},
            )
            magazzino_service.crea_riga(
                "rettifiche", r["id"], {"articolo_id": m.art, "qta_delta": -1, "motivo": "ROTTURA"},
            )
            self.assertEqual(
                magazzino_service.get_documento("rettifiche", r["id"])["righe_count"], 2,
            )
        self._nel_mondo(_prova)

    # 13. La ricerca libera delle testate e della disponibilita' (BB
    #     `add_ricerca_full_condition`): per ogni colonna che il CATALOGO
    #     accende, il valore di una riga costruita la trova
    #     (`verifica_ricerca_colonna_per_colonna`). Testate, righe, piano,
    #     registro e disponibilita' — otto liste — non hanno
    #     `vista_sql`: questo e' il loro esercizio sul DB vero
    #     (`test_ricerca_full_db` lo nomina).
    def test_la_ricerca_trova_ogni_colonna_accesa(self):
        def _prova(cur, m):
            inv = self._inventario_confermato(m)
            magazzino_service.registra_documento("inventari", inv["id"])
            cur.execute("UPDATE magazzino.inventari SET descrizione = 'Conta ricdescinv' WHERE id = %s", [inv["id"]])
            rett = magazzino_service.crea_documento("rettifiche", {"magazzino_id": m.mag_u})
            cur.execute("SELECT id, codice, descrizione FROM magazzino.magazzini WHERE id IN (%s, %s)", [m.mag_a, m.mag_u])
            mag = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
            cur.execute("SELECT codice, descrizione FROM catalogo.articoli WHERE id = %s::uuid", [m.art])
            art_codice, art_descrizione = cur.fetchone()

            verifica_ricerca_colonna_per_colonna(
                self, cur, "magazzino.inventari", inv["id"],
                {"magazzino_codice": mag[m.mag_a][0], "magazzino_descrizione": mag[m.mag_a][1],
                 "descrizione": "ricdescinv"},
                lambda t: magazzino_service.list_documenti(
                    "inventari", auth_user_id=m.uid, search=t, limit=100)["results"],
            )
            verifica_ricerca_colonna_per_colonna(
                self, cur, "magazzino.rettifiche", rett["id"],
                {"magazzino_codice": mag[m.mag_u][0], "magazzino_descrizione": mag[m.mag_u][1]},
                lambda t: magazzino_service.list_documenti(
                    "rettifiche", auth_user_id=m.uid, search=t, limit=100)["results"],
            )
            verifica_ricerca_colonna_per_colonna(
                self, cur, "magazzino.disponibilita", f"{m.art}|{m.mag_a}",
                {"articolo_codice": art_codice, "articolo_descrizione": art_descrizione,
                 "magazzino_codice": mag[m.mag_a][0]},
                lambda t: consultazione_service.list_disponibilita(
                    auth_user_id=m.uid, search=t, limit=100)["results"],
                chiave="chiave_riga",
            )
            articolo = {"articolo_codice": art_codice, "articolo_descrizione": art_descrizione}
            riga_inv = magazzino_service.list_righe("inventari", inv["id"], limit=10)["results"][0]
            verifica_ricerca_colonna_per_colonna(
                self, cur, "magazzino.inventario_righe", riga_inv["id"], articolo,
                lambda t: magazzino_service.list_righe("inventari", inv["id"], search=t, limit=100)["results"],
            )
            riga_rett = magazzino_service.crea_riga(
                "rettifiche", rett["id"], {"articolo_id": m.art, "qta_delta": -1, "motivo": "Caduta ricmotivo"},
            )
            verifica_ricerca_colonna_per_colonna(
                self, cur, "magazzino.rettifica_righe", riga_rett["id"], {**articolo, "motivo": "ricmotivo"},
                lambda t: magazzino_service.list_righe("rettifiche", rett["id"], search=t, limit=100)["results"],
            )
            # Il piano si legge anche in bozza: un secondo inventario, non registrato.
            bozza = magazzino_service.crea_documento("inventari", {"magazzino_id": m.mag_a})
            magazzino_service.crea_riga("inventari", bozza["id"], {"articolo_id": m.art, "qta_contata": 3})
            verifica_ricerca_colonna_per_colonna(
                self, cur, "magazzino.inventario_piano", f"{m.art}|||", articolo,
                lambda t: magazzino_service.list_piano("inventari", bozza["id"], search=t, limit=100)["results"],
                chiave="chiave_riga",
            )
            movimento = consultazione_service.list_movimenti(
                auth_user_id=m.uid, inventario_id=inv["id"], limit=10)["results"][0]
            verifica_ricerca_colonna_per_colonna(
                self, cur, "magazzino.movimenti", movimento["id"], articolo,
                lambda t: consultazione_service.list_movimenti(
                    auth_user_id=m.uid, inventario_id=inv["id"], search=t, limit=100)["results"],
            )
            verifica_ricerca_colonna_per_colonna(
                self, cur, "magazzino.disponibilita_articoli", m.art,
                {"articolo_codice": art_codice, "articolo_descrizione": art_descrizione},
                lambda t: consultazione_service.list_disponibilita_articoli(search=t, limit=100)["results"],
                chiave="chiave_riga",
            )
        self._nel_mondo(_prova)
