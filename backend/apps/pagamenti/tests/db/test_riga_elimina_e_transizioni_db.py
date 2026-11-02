# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi sul DATABASE PROVVISTO per il seguito del collaudo del
#        2026-09-14 (D16/D17/D18): le colonne del blocco «elimina» esistono
#        davvero, la check che le alimenta esiste con la sua firma, l'INSERT
#        con la destinazione e l'UPDATE di eliminazione si pianificano, le
#        due matrici si leggono e ogni stato richiedibile e' raggiungibile.
#        ⭐ E il SECONDO TEMPO in modifica (Q-H, 2026-09-15), provato PER
#        INTERO contro il guard vero: il PATCH di un importo oltre la capienza
#        e' rifiutato «confermabile», e col `forzata` passa.
# Note: ⚠️ I mock non vedono l'SQL: un nome di colonna sbagliato in una
#       LATERAL o in un INSERT e' un 500 sul primo incasso digitato, non un
#       test rosso. Qui si parla col database vero, in transazione ANNULLATA
#       e col contesto operatore (senza, le tabelle sotto RLS rispondono zero
#       righe e sembrano un dato).
#       ⛔ Non si asserisce che `stato_info_key` sia NULL: sarebbe il test che
#       tiene fuori il dato il giorno in cui il seed (brief §4 P-8) arriva.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) ColonneTests.test_la_riga_porta_le_quattro_colonne_del_blocco_elimina
2) ColonneTests.test_anche_la_coda_le_porta
3) ColonneTests.test_la_testata_porta_stato_info_key
4) ColonneTests.test_la_check_esiste_con_la_firma_della_lateral
5) ScrittureTests.test_l_insert_con_la_destinazione_si_pianifica
6) ScrittureTests.test_l_update_di_eliminazione_si_pianifica
7) LettureTests.test_get_riga_e_list_righe_eseguono_con_la_lateral
8) LettureTests.test_ogni_ordinamento_della_coda_esegue_con_la_lateral
9) MatriciTests.test_le_due_matrici_si_leggono_e_hanno_la_forma_attesa
10) MatriciTests.test_ogni_richiedibile_e_raggiungibile_in_matrice
11) MatriciTests.test_il_difetto_del_collaudo_non_e_piu_offerto
12) ModificaSecondoTempoTests.test_il_patch_oltre_la_capienza_e_rifiutato_confermabile
13) ModificaSecondoTempoTests.test_col_secondo_tempo_il_patch_passa_e_resta_scritto
14) ColonneTests.test_la_riga_porta_la_destinazione_leggibile
15) ColonneTests.test_anche_la_coda_porta_la_destinazione_leggibile
16) ColonneTests.test_il_numero_documento_viene_dalla_sede_unica
17) ColonneTests.test_la_testata_porta_l_emittente_e_il_registro
18) ColonneTests.test_la_madre_accetta_l_emittente
19) NumerazioneSulRegistroTests.test_senza_emittente_la_distinta_e_della_sessione_e_numerata
20) NumerazioneSulRegistroTests.test_con_emittente_esplicito_arriva_com_e_e_riusa
21) SaldoPrimaDiSeTests.test_il_documento_esclude_la_riga_come_la_rata
22) SaldoPrimaDiSeTests.test_un_id_di_esclusione_non_positivo_e_un_guasto_dichiarato
23) LettureTests.test_ogni_ordinamento_delle_righe_della_distinta_esegue_con_la_lateral
24) LettureTests.test_la_lista_dice_lo_stesso_motivo_della_firma_per_id
25) LettureTests.test_la_check_della_coda_sta_sopra_la_window
"""

from __future__ import annotations

import re
import unittest
from datetime import date
from decimal import Decimal

from django.db import DatabaseError, connection, transaction

from apps.core.services.fuso_aziendale import oggi_aziendale
from apps.core.services.db_error_fields import structured_db_error_code
from apps.core.services.error_manager import ServiceError
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto
from apps.pagamenti.db import pagamenti_repository as repo_mod
from apps.pagamenti.db.pagamenti_repository import (
    DISTINTA_RIGHE_SORT_COLUMNS,
    RIGHE_SORT_COLUMNS,
    PagamentiRepository,
)
from apps.pagamenti.services import pagamenti_service, saldi_service

_COLONNE_ELIMINA = (
    "elimina_blocco_reason",
    "elimina_blocco_reason_key",
    "elimina_blocco_dettaglio",
    "can_eliminare",
)

# ⭐ La destinazione LEGGIBILE (D19-b, 2026-09-17): il documento e la rata con
#    cui una persona li riconosce, non il contatore. Un nome sbagliato qui e'
#    un 500 sul dettaglio della distinta, e i mock non lo vedono.
_COLONNE_DESTINAZIONE = (
    "fattura_numero_documento",
    "fattura_data",
    "fattura_totale_doc",
    "fattura_registro_codice",
    # ⚠️ Senza il prefisso `fattura_` (dal 2026-09-18): e' la gemella che il
    #    `formato = natura_doc` della lista 69 legge dalla riga.
    "natura_doc_codice_interno",
    "natura_doc_descrizione",
    "scadenza_importo",
)

# ⭐ Di chi e' la distinta (D3, 2026-09-17): le tre forme dell'emittente che
#    il frontend legge, la chiave del DB e i due assi del contatore.
_COLONNE_EMITTENTE_TESTATA = (
    "emittente_soggetto_ruolo_id",
    "emittente_fiscale_id",
    "emittente_fiscale_codice",
    "emittente_ragione_sociale",
    "registro_id",
    "anno",
)


class _DbTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    # Scopo: esegue `azione(cursor)` col contesto operatore, in una transazione
    #        che viene SEMPRE annullata.
    def _con_operatore(self, azione):
        with transaction.atomic():
            try:
                with connection.cursor() as cur:
                    apri_contesto_operatore(cur)
                    return azione(cur)
            finally:
                transaction.set_rollback(True)

    # Scopo: i nomi delle colonne che una SELECT proietta, a zero righe.
    # ⭐ Le colonne le dichiara il CURSORE, non le righe: vale anche su un
    #    database senza incassi, che e' il caso in cui serve di piu'.
    def _colonne(self, sql: str, params: list) -> set[str]:
        def _leggi(cur):
            cur.execute(sql, params)
            return {c[0] for c in cur.description}
        return self._con_operatore(_leggi)


class ColonneTests(_DbTestCase):
    # Scopo: BE-4 — la terna + il flag sulla riga «nuda» (dettaglio e righe di
    #        una distinta). Dal 2026-10-21 le aggiunge `_sql_con_elimina` SOPRA
    #        la lettura: si prova la composizione che le letture eseguono.
    def test_la_riga_porta_le_quattro_colonne_del_blocco_elimina(self):
        colonne = self._colonne(
            repo_mod._sql_con_elimina(f"{repo_mod._RIGA_SELECT} WHERE r.id = %s"), [-1]
        )
        for nome in _COLONNE_ELIMINA:
            self.assertIn(nome, colonne)

    # Scopo: ...e sulla coda, con lo stesso frammento.
    def test_anche_la_coda_le_porta(self):
        colonne = self._colonne(
            repo_mod._sql_con_elimina(f"{repo_mod._RIGA_CODA_SELECT} WHERE r.id = %s"), [-1]
        )
        for nome in _COLONNE_ELIMINA:
            self.assertIn(nome, colonne)

    # Scopo: D19-b — le sette colonne con cui la riga racconta il SUO documento
    #        e la SUA rata (numero parlante, data, totale, registro, natura,
    #        importo della rata), sulla riga «nuda».
    def test_la_riga_porta_la_destinazione_leggibile(self):
        colonne = self._colonne(f"{repo_mod._RIGA_SELECT} WHERE r.id = %s", [-1])
        for nome in _COLONNE_DESTINAZIONE:
            self.assertIn(nome, colonne)

    # Scopo: ...e sulla coda, che condivide il frammento: il seed
    #        `pagamenti.righe` puo' prenderle quando vorra'.
    def test_anche_la_coda_porta_la_destinazione_leggibile(self):
        colonne = self._colonne(f"{repo_mod._RIGA_CODA_SELECT} WHERE r.id = %s", [-1])
        for nome in _COLONNE_DESTINAZIONE:
            self.assertIn(nome, colonne)

    # Scopo: il numero parlante NON e' composto nel repository: e' la sede unica
    #        del database a produrlo. Si asserisce sul FRAMMENTO, perche' la
    #        regola e' «si legge, non si compone» e una composizione a mano
    #        (`numero::text || ' - ' || serie`) darebbe le stesse colonne e
    #        passerebbe i due test sopra — sbagliando in silenzio sulla serie
    #        NULL, dove il numero sparirebbe. ⚠️ E' un presidio sulla FORMA
    #        (la chiamata alla fn c'e'), non un cancello contro ogni
    #        composizione possibile: quello non si scrive con una stringa.
    def test_il_numero_documento_viene_dalla_sede_unica(self):
        self.assertIn(
            "vendite.fn_numero_documento_fattura(f.numero, f.serie) AS fattura_numero_documento",
            repo_mod._RIGA_COLONNE,
        )

    # Scopo: FE-9 — la chiave della riga di stato si legge dal `meta` dello
    #        stato. Si asserisce che la COLONNA c'e', non il suo valore.
    def test_la_testata_porta_stato_info_key(self):
        colonne = self._colonne(
            f"{repo_mod._DISTINTA_SELECT}{repo_mod._TOTALI_LATERAL} WHERE c.id = %s", [-1]
        )
        self.assertIn("stato_info_key", colonne)

    # Scopo: ⭐ La distinta SA DI CHI E' (D3, 2026-09-17): la testata porta
    #        l'emittente nelle tre forme che il frontend legge (PK, sigla,
    #        ragione sociale) piu' la chiave del DB e i due assi del contatore.
    #        Si pianifica contro il database vero: `emittente_soggetto_ruolo_id`,
    #        `registro_id` e `anno` sono colonne nate col cantiere, e un nome
    #        sbagliato in un JOIN e' un 500 sull'elenco, non un test rosso.
    def test_la_testata_porta_l_emittente_e_il_registro(self):
        colonne = self._colonne(
            f"{repo_mod._DISTINTA_SELECT}{repo_mod._TOTALI_LATERAL} WHERE c.id = %s", [-1]
        )
        for nome in _COLONNE_EMITTENTE_TESTATA:
            self.assertIn(nome, colonne, f"manca {nome} nella testata")

    # Scopo: La madre accetta `p_emittente_fiscale_id` (L6 del brief): la
    #        chiamata NOMINATA del repository si pianifica con la firma viva.
    #        ⚠️ EXPLAIN pianifica senza eseguire: nessuna distinta nasce.
    def test_la_madre_accetta_l_emittente(self):
        def _pianifica(cur):
            cur.execute(
                """
                EXPLAIN SELECT pagamenti.fn_get_or_create_vendite_contabile(
                    p_centro_riscossione_id := %s,
                    p_data_contabile        := %s,
                    p_ente_incasso_id       := %s,
                    p_emittente_fiscale_id  := %s,
                    p_codice_stato_interno  := %s,
                    p_meta                  := %s::jsonb,
                    p_origine               := %s)
                """,
                [
                    1, oggi_aziendale(), None, None,
                    pagamenti_service.STATO_DISTINTA_INIZIALE, "{}",
                    pagamenti_service.ORIGINE_MANUALE,
                ],
            )
            return cur.fetchall()
        self.assertTrue(self._con_operatore(_pianifica))

    # Scopo: La check che alimenta la LATERAL esiste, con la firma che la
    #        LATERAL chiama: dal 2026-10-21 la meta' sulla TESTATA. Se
    #        cambiasse firma, la lista delle righe risponderebbe 500.
    def test_la_check_esiste_con_la_firma_della_lateral(self):
        def _leggi(cur):
            cur.execute(
                """
                SELECT to_regprocedure(
                    'script.fn_check_riga_contabile_eliminabile_su_distinta(pagamenti.vendite_contabili)'
                ) IS NOT NULL
                """
            )
            return cur.fetchone()[0]
        self.assertTrue(
            self._con_operatore(_leggi),
            "script.fn_check_riga_contabile_eliminabile_su_distinta(pagamenti.vendite_contabili) assente",
        )


class ScrittureTests(_DbTestCase):
    # Scopo: L'INSERT coi cinque campi della destinazione si pianifica: ogni
    #        nome di colonna esiste. ⚠️ EXPLAIN pianifica senza eseguire.
    def test_l_insert_con_la_destinazione_si_pianifica(self):
        def _pianifica(cur):
            cur.execute(
                f"EXPLAIN {repo_mod._RIGA_INSERT}",
                [
                    -1, "400.00", "CRO 1",
                    date(2026, 9, 14), None, None,
                    None, "{}",
                    -1, -1, -1,
                    False, None,
                    "ABBINATA",
                ],
            )
            return cur.fetchall()
        self.assertTrue(self._con_operatore(_pianifica))

    def test_l_update_di_eliminazione_si_pianifica(self):
        def _pianifica(cur):
            cur.execute(f"EXPLAIN {repo_mod._RIGA_DISATTIVA}", [-1])
            return cur.fetchall()
        self.assertTrue(self._con_operatore(_pianifica))


class LettureTests(_DbTestCase):
    # Scopo: Le tre letture di riga ESEGUONO con la LATERAL sulla check: una
    #        query che non parte e' un 500 sul drawer.
    def test_get_riga_e_list_righe_eseguono_con_la_lateral(self):
        def _leggi(cur):
            repo = PagamentiRepository()
            repo.get_riga(-1)
            repo.list_righe(-1)
            return True
        self.assertTrue(self._con_operatore(_leggi))

    # Scopo: OGNI ordinamento dichiarato della coda, nei due versi, con la
    #        LATERAL a bordo — il difetto del 24/08 (500 su `distinta`) si
    #        ripresenterebbe qui, non in un mock.
    def test_ogni_ordinamento_della_coda_esegue_con_la_lateral(self):
        def _leggi(cur):
            repo = PagamentiRepository()
            for colonna in RIGHE_SORT_COLUMNS:
                for verso in ("asc", "desc"):
                    with self.subTest(colonna=colonna, verso=verso):
                        rows, total = repo.list_righe_coda(
                            stati=pagamenti_service.CODE_RIGHE["TUTTE"],
                            order_by=colonna, order_dir=verso, limit=1, offset=0,
                        )
                        self.assertIsInstance(total, int)
            return True
        self.assertTrue(self._con_operatore(_leggi))

    # Scopo: OGNI ordinamento dichiarato della lista `pagamenti.distinta_righe`
    #        (2026-09-18), nei due versi E senza — cioe' il ramo di default
    #        (`id DESC`) — con la LATERAL a bordo. La whitelist mappa
    #        `fattura_numero_documento` sulla COPPIA `(fattura_numero,
    #        fattura_serie)`: un alias che la proiezione non porta e' un 500 al
    #        primo click sull'intestazione, e un mock non lo vede.
    def test_ogni_ordinamento_delle_righe_della_distinta_esegue_con_la_lateral(self):
        def _leggi(cur):
            repo = PagamentiRepository()
            versi = (None, "asc", "desc")
            for colonna in (None, *DISTINTA_RIGHE_SORT_COLUMNS):
                for verso in versi:
                    with self.subTest(colonna=colonna, verso=verso):
                        rows, total = repo.list_righe_distinta(
                            -1, order_by=colonna, order_dir=verso, limit=1, offset=0,
                        )
                        self.assertEqual((rows, total), ([], 0))
            return True
        self.assertTrue(self._con_operatore(_leggi))

    # Scopo: ⭐ La meta' sulla testata e la firma per id (quella del guard)
    #        danno lo STESSO primo motivo nel percorso reale del frammento
    #        (`_sql_con_elimina`, lo stesso delle quattro letture), su OGNI ramo
    #        del predicato: una riga per ramo, sotto una distinta costruita in
    #        quello stato (`_monta_righe_per_ramo`). Il cestino spento e il 409
    #        non devono divergere: e' la promessa della check, e cambiare la
    #        firma chiamata non deve romperla in silenzio.
    # ⭐ Si asserisce anche il motivo ATTESO: due risposte uguali e sbagliate
    #    (per esempio entrambe NULL) non sono una prova.
    # ⛔ Fino al 2026-10-22 confrontava le righe attive che il DB conteneva, e
    #    su un database ricostruito da zero si saltava: provava solo i rami che
    #    i dati di quel giorno, per caso, avevano.
    def test_la_lista_dice_lo_stesso_motivo_della_firma_per_id(self):
        def _leggi(cur):
            righe = _monta_righe_per_ramo(cur)
            lista = repo_mod._sql_con_elimina(f"{repo_mod._RIGA_SELECT} WHERE r.id = ANY(%s)")
            cur.execute(
                f"""
                SELECT l.id, l.elimina_blocco_reason,
                       script.fn_check_riga_contabile_eliminabile(l.id) -> 0 ->> 'reason'
                  FROM ({lista}) l
                """,
                [list(righe.values())],
            )
            letti = {riga_id: (in_lista, per_id) for riga_id, in_lista, per_id in cur.fetchall()}
            return righe, letti

        righe, letti = self._con_operatore(_leggi)
        self.assertEqual(set(letti), set(righe.values()), "la lista non restituisce le righe del mondo")
        for (ramo, atteso), riga_id in righe.items():
            in_lista, per_id = letti[riga_id]
            with self.subTest(ramo=ramo):
                self.assertEqual(in_lista, per_id)
                self.assertEqual(in_lista, atteso)

    # Scopo: ⭐ La check gira sulle righe MOSTRATE: nel piano della coda la
    #        sua chiamata non sta sotto la `WindowAgg` della `COUNT(*) OVER ()`
    #        (cioe' non per riga filtrata). Si legge il piano, non i tempi:
    #        e' la forma che si presidia, e vale anche a DB quasi vuoto.
    def test_la_check_della_coda_sta_sopra_la_window(self):
        catturata: dict = {}

        def _cattura(data_sql, params, **_kw):
            catturata["sql"], catturata["params"] = data_sql, params
            return [], 0

        def _piano(cur):
            originale = repo_mod.fetch_paged_with_total
            repo_mod.fetch_paged_with_total = _cattura
            try:
                PagamentiRepository().list_righe_coda(
                    stati=pagamenti_service.CODE_RIGHE["TUTTE"],
                    order_by="data_pagamento", order_dir="desc", limit=25, offset=0,
                )
            finally:
                repo_mod.fetch_paged_with_total = originale
            cur.execute("EXPLAIN (FORMAT JSON, VERBOSE) " + catturata["sql"], catturata["params"])
            return cur.fetchone()[0]

        piano = self._con_operatore(_piano)

        def _sotto_window(nodo, dentro=False):
            dentro = dentro or nodo.get("Node Type") == "WindowAgg"
            trovati = []
            if dentro and "fn_check_riga_contabile_eliminabile" in str(
                {k: v for k, v in nodo.items() if k != "Plans"}
            ):
                trovati.append(nodo.get("Node Type"))
            for figlio in nodo.get("Plans", []):
                trovati += _sotto_window(figlio, dentro)
            return trovati

        radice = piano[0]["Plan"]
        self.assertIn("fn_check_riga_contabile_eliminabile_su_distinta", str(radice))
        self.assertEqual(_sotto_window(radice), [], "la check gira sotto la WindowAgg")


class MatriciTests(_DbTestCase):
    def _matrici(self):
        return self._con_operatore(lambda cur: PagamentiRepository().list_transizioni())

    # Scopo: BE-5 — le due matrici arrivano come coppie di codici, entrambe
    #        popolate (il seed 20260821-31 le pretende gia' con un guard suo).
    def test_le_due_matrici_si_leggono_e_hanno_la_forma_attesa(self):
        distinta, riga = self._matrici()
        self.assertTrue(distinta and riga)
        for coppia in (*distinta, *riga):
            self.assertEqual(len(coppia), 2)
            self.assertNotEqual(coppia[0], coppia[1])

    # Scopo: ⭐ Ogni stato che il backend dichiara richiedibile compare come
    #        ARRIVO in matrice: un richiedibile irraggiungibile e' un pulsante
    #        che il database rifiuta — il difetto del collaudo, all'inverso.
    def test_ogni_richiedibile_e_raggiungibile_in_matrice(self):
        distinta, riga = self._matrici()
        arrivi_distinta = {a for _, a in distinta}
        arrivi_riga = {a for _, a in riga}
        for stato in pagamenti_service.STATI_DISTINTA_RICHIEDIBILI:
            self.assertIn(stato, arrivi_distinta, f"{stato}: richiedibile ma senza una transizione che ci porti")
        for stato in pagamenti_service.STATI_RIGA_RICHIEDIBILI:
            self.assertIn(stato, arrivi_riga, f"{stato}: richiedibile ma senza una transizione che ci porti")

    # Scopo: Il caso del collaudo, contro la matrice VERA: da `ABBINATA` non si
    #        propone `SCARTATA` (D14-a: si scarta cio' che non e' nostro, e una
    #        riga abbinata ha gia' un nome).
    # ⭐ Dal 2026-09-19 (D20-e, strada b, P-6 applicato) da ABBINATA esce SOLO
    #    la sospensione: lo «sgancia» (`ABBINATA → DA_ABBINARE`) e' spento in
    #    matrice — su una riga abbinata si RI-ABBINA, il dialogo si apre gia'
    #    sulla destinazione. Fino a quel giorno questo test pretendeva
    #    `DA_ABBINARE` fra le uscite: era la matrice di allora.
    def test_il_difetto_del_collaudo_non_e_piu_offerto(self):
        _, riga = self._matrici()
        ammesse = pagamenti_service._transizioni_richiedibili(
            riga, pagamenti_service.STATI_RIGA_RICHIEDIBILI
        )
        self.assertNotIn("SCARTATA", ammesse.get("ABBINATA", []))
        self.assertNotIn("DA_ABBINARE", ammesse.get("ABBINATA", []))
        self.assertIn("SOSPESA", ammesse.get("ABBINATA", []))


# La fixture del secondo tempo, COSTRUITA (regola zero: non si pesca): la
# propria azienda col suo operatore, un cliente fatturabile, una fattura con
# UNA rata da 400, una distinta MANUALE in BOZZA e una riga ABBINATA a quella
# rata per 400 — cioe' la rata e' gia' piena. Stesse primitive dei pgTAP.
# ⚠️ Passi SEPARATI, non una CTE sola: il contesto operatore va aperto PRIMA
#    che nasca il cliente (il guard del billing account lo pretende), e in una
#    CTE l'ordine di valutazione dei rami non e' garantito.
# Il MONDO di ogni fixture: un'azienda col suo operatore, e il contesto aperto
# su di lui. E' il primo passo di tutte le fixture di questo file, e sta in una
# sede sola (regola del 2): la seconda fixture lo ricopiava con un altro nome
# di TEMP TABLE. ⚠️ Il contesto lo apre la funzione pgTAP, non
# `apri_contesto_operatore`: l'operatore deve essere QUELLO dell'azienda
# costruita, o la RLS non gli farebbe vedere cio' che nasce dopo.
_FIXTURE_MONDO: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    """
    SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo))
    """,
)

_FIXTURE_PASSI: tuple[str, ...] = _FIXTURE_MONDO + (
    """
    CREATE TEMP TABLE _cli_bst AS
    SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('secondo tempo') c
    """,
    """
    CREATE TEMP TABLE _fat_bst AS
    WITH ins AS (
        INSERT INTO vendite.fatture
            (registro_id, emittente_soggetto_ruolo_id, billing_account_id, meta)
        SELECT script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id), m.soggetto_ruolo_id,
               c.billing_account_id, '{"test_scope": "be_secondo_tempo"}'::jsonb
          FROM _mondo m, _cli_bst c
        RETURNING id
    )
    SELECT id AS fattura_id FROM ins
    """,
    """
    CREATE TEMP TABLE _rata_bst AS
    WITH ins AS (
        INSERT INTO vendite.fatture_scadenze (fattura_id, numero_rata, data_scadenza, importo)
        SELECT fattura_id, 1, script.fn_data_operativa() + 30, 400.00 FROM _fat_bst
        RETURNING id
    )
    SELECT id AS scadenza_id FROM ins
    """,
    """
    CREATE TEMP TABLE _dist_bst AS
    WITH ins AS (
        INSERT INTO pagamenti.vendite_contabili
            (centro_riscossione_id, data_contabile, data_registrazione, stato_id, origine, meta)
        SELECT (SELECT c.id FROM pagamenti.centri_riscossione c
                 WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1),
               script.fn_data_operativa(), script.fn_data_operativa(),
               (SELECT s.id FROM pagamenti.vendite_contabili_stati s
                 WHERE s.codice_interno = 'BOZZA' ORDER BY s.id LIMIT 1),
               'MANUALE', '{"test_scope": "be_secondo_tempo"}'::jsonb
        RETURNING id
    )
    SELECT id AS contabile_id FROM ins
    """,
    """
    INSERT INTO pagamenti.vendite_contabili_righe
        (contabile_id, riferimento_ente, data_pagamento, importo,
         fattura_id, billing_account_id, scadenza_id, stato_id)
    SELECT d.contabile_id, 'BE_SECONDO_TEMPO', script.fn_data_operativa(), 400.00,
           f.fattura_id, c.billing_account_id, r.scadenza_id,
           (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
             WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1)
      FROM _dist_bst d, _fat_bst f, _rata_bst r, _cli_bst c
    RETURNING id
    """,
)


# Scopo: monta la fixture (il mondo di `_FIXTURE_MONDO` piu' cliente, fattura,
#        rata da 400, distinta in BOZZA e UNA riga ABBINATA da 400) e consegna
#        i tre id `(fattura_id, scadenza_id, riga_id)`. Le TEMP TABLE muoiono
#        col rollback. ⭐ Una sede per le due classi che la usano: la seconda
#        l'aveva ricopiata per leggere gli altri due id.
def _monta_riga_piena(cur) -> tuple[int, int, int]:
    for passo in _FIXTURE_PASSI:
        cur.execute(passo)
    row = cur.fetchone()
    assert row is not None
    riga_id = int(row[0])
    cur.execute("SELECT fattura_id FROM _fat_bst")
    row = cur.fetchone()
    assert row is not None
    fattura_id = int(row[0])
    cur.execute("SELECT scadenza_id FROM _rata_bst")
    row = cur.fetchone()
    assert row is not None
    scadenza_id = int(row[0])
    return fattura_id, scadenza_id, riga_id


# I rami del predicato «elimina» (`script.fn_check_riga_contabile_eliminabile_su_distinta`):
# (nome, origine della distinta, stati per cui passa dopo la BOZZA, primo motivo atteso).
# ⭐ I motivi stanno tutti sulla TESTATA, quindi un ramo e' una distinta.
# ⚠️ La riga nasce SCARTATA: una riga gia' lavorata, perche' una distinta con
#    righe da guardare non si valida (e senza VALIDATA non si arriva a CHIUSA).
_RAMI_ELIMINA: tuple[tuple[str, str, tuple[str, ...], str | None], ...] = (
    ("manuale_in_bozza", "MANUALE", (), None),
    ("manuale_validata", "MANUALE", ("VALIDATA",), "DISTINTA_VALIDATA"),
    ("generata", "GENERATA", (), "DISTINTA_NON_MANUALE"),
    ("chiusa", "MANUALE", ("VALIDATA", "CHIUSA"), "DISTINTA_FINALE"),
    ("annullata", "MANUALE", ("ANNULLATA",), "DISTINTA_ANNULLATA"),
)

_DISTINTA_IN_BOZZA = """
    INSERT INTO pagamenti.vendite_contabili
        (centro_riscossione_id, data_contabile, data_registrazione, stato_id, origine, meta)
    SELECT (SELECT c.id FROM pagamenti.centri_riscossione c
             WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1),
           script.fn_data_operativa(), script.fn_data_operativa(),
           (SELECT s.id FROM pagamenti.vendite_contabili_stati s WHERE s.codice_interno = 'BOZZA'),
           %s, '{"test_scope": "be_rami_elimina"}'::jsonb
    RETURNING id
"""

_RIGA_SCARTATA = """
    INSERT INTO pagamenti.vendite_contabili_righe
        (contabile_id, riferimento_ente, data_pagamento, importo, stato_id)
    SELECT %s, 'BE_RAMI_ELIMINA', script.fn_data_operativa(), 10.00,
           (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
             WHERE s.codice_interno = 'SCARTATA')
    RETURNING id
"""

_DISTINTA_IN_STATO = """
    UPDATE pagamenti.vendite_contabili
       SET stato_id = (SELECT s.id FROM pagamenti.vendite_contabili_stati s
                        WHERE s.codice_interno = %s)
     WHERE id = %s
"""


# Scopo: monta il mondo (`_FIXTURE_MONDO`) e, per ogni ramo di `_RAMI_ELIMINA`,
#        una distinta con UNA riga, portata nel suo stato passando dai guard
#        veri (transizioni, «ogni riga guardata»). Consegna
#        `{(ramo, motivo atteso): riga_id}`. Tutto muore col rollback.
def _monta_righe_per_ramo(cur) -> dict[tuple[str, str | None], int]:
    for passo in _FIXTURE_MONDO:
        cur.execute(passo)
    righe: dict[tuple[str, str | None], int] = {}
    for ramo, origine, percorso, atteso in _RAMI_ELIMINA:
        cur.execute(_DISTINTA_IN_BOZZA, [origine])
        contabile_id = int(cur.fetchone()[0])
        cur.execute(_RIGA_SCARTATA, [contabile_id])
        righe[(ramo, atteso)] = int(cur.fetchone()[0])
        for stato in percorso:
            cur.execute(_DISTINTA_IN_STATO, [stato, contabile_id])
    return righe


class ModificaSecondoTempoTests(_DbTestCase):
    # Scopo: l'id della riga piena, dalla fixture condivisa.
    def _riga_piena(self, cur) -> int:
        return _monta_riga_piena(cur)[2]

    # Scopo: 🔴 Il PATCH di un importo che non rientra e' rifiutato dal guard
    #        vero — col codice della capienza, che risale con
    #        `confirm_and_retry` — e la riga NON cambia. E' il primo tempo,
    #        provato contro il database e non contro un mock.
    def test_il_patch_oltre_la_capienza_e_rifiutato_confermabile(self):
        def _prova(cur):
            riga_id = self._riga_piena(cur)
            with self.assertRaises(ServiceError) as ctx, transaction.atomic():
                pagamenti_service.aggiorna_riga(riga_id, {"importo": "900.00"})
            self.assertEqual(ctx.exception.code, "E_RIGA_CONTABILE_CAPIENZA_SUPERATA")
            self.assertEqual(
                ErrorPolicyRegistry.resolve(ctx.exception.code).ui_action,
                "confirm_and_retry",
            )
            cur.execute(
                "SELECT importo, forzata FROM pagamenti.vendite_contabili_righe WHERE id = %s",
                [riga_id],
            )
            return cur.fetchone()
        importo, forzata = self._con_operatore(_prova)
        self.assertEqual(importo, Decimal("400.00"))
        self.assertIs(forzata, False)

    # Scopo: ⭐ Q-H — col secondo tempo lo stesso PATCH passa, e la forzatura
    #        col suo motivo RESTA SCRITTA sulla riga: e' cio' che l'elenco delle
    #        rate fuori capienza legge per esistere.
    def test_col_secondo_tempo_il_patch_passa_e_resta_scritto(self):
        def _prova(cur):
            riga_id = self._riga_piena(cur)
            esito = pagamenti_service.aggiorna_riga(
                riga_id,
                {"importo": "900.00", "forzata": True, "motivo_forzatura": "pagato doppio"},
            )
            riga = esito["riga"]
            return riga["importo"], riga["forzata"], riga["motivo_forzatura"]
        importo, forzata, motivo = self._con_operatore(_prova)
        self.assertEqual(importo, Decimal("900.00"))
        self.assertIs(forzata, True)
        self.assertEqual(motivo, "pagato doppio")


class NumerazioneSulRegistroTests(_DbTestCase):
    """⭐ La distinta prende il numero dal registro e sa di chi e' (brief
    distinta-numerata-sul-registro, BE-5), provato PER INTERO: service → madre
    → sede unica dell'emittente → trigger numeratore → `DistintaRow`.
    ⚠️ I pgTAP provano il database con un INSERT; qui si prova che il BACKEND
    ci arrivi — la chiamata nominata, il parametro nuovo, le colonne nuove —
    che e' il pezzo in mezzo che nessuno dei due lati vede da solo.
    """

    # Scopo: monta l'azienda con l'operatore, apre il contesto SUO e consegna
    #        (sigla, PK) dell'emittente. Qui la distinta la apre il SERVICE,
    #        com'e' in esercizio: il mondo basta, senza cliente ne' fattura.
    #        Le TEMP TABLE muoiono col rollback.
    def _mondo(self, cur) -> tuple[str, int]:
        for passo in _FIXTURE_MONDO:
            cur.execute(passo)
        cur.execute("SELECT emittente_codice, emittente_fiscale_id FROM _mondo")
        row = cur.fetchone()
        assert row is not None
        return str(row[0]), int(row[1])

    # Scopo: il centro CASSA (senza canale): e' il caso in cui l'emittente
    #        non si deriva dal conto e la sessione deve rispondere.
    @staticmethod
    def _centro_cassa(cur) -> int:
        cur.execute(
            """
            SELECT c.id FROM pagamenti.centri_riscossione c
             WHERE c.attivo IS TRUE AND c.codice_interno = 'CASSA'
             ORDER BY c.id LIMIT 1
            """
        )
        row = cur.fetchone()
        assert row is not None, "centro CASSA a catalogo"
        return int(row[0])

    # Scopo: ⭐ Senza canale e SENZA emittente nel payload la distinta nasce
    #        lo stesso — dell'operatore in sessione (livello 3) — col codice
    #        `DIS-<sigla>-<anno>-<7 cifre>` sul SUO registro, e la testata lo
    #        racconta nelle tre forme. E' il percorso dell'operatore normale.
    def test_senza_emittente_la_distinta_e_della_sessione_e_numerata(self):
        # ⚠️ Una data sola per tutto il test: `oggi_aziendale()` chiamata due volte
        #    a cavallo della mezzanotte darebbe due anni.
        oggi = oggi_aziendale()

        def _prova(cur):
            sigla, ef_id = self._mondo(cur)
            esito = pagamenti_service.crea_distinta({
                "centro_riscossione_id": self._centro_cassa(cur),
                "data_contabile": oggi.isoformat(),
                "meta": {"test_scope": "be_numerazione"},
            })
            return sigla, ef_id, esito["distinta"]
        sigla, ef_id, d = self._con_operatore(_prova)
        self.assertRegex(d["codice"], rf"^DIS-{re.escape(sigla)}-{oggi.year}-\d{{7}}$")
        self.assertEqual(d["emittente_fiscale_id"], ef_id)
        self.assertEqual(d["emittente_fiscale_codice"], sigla)
        self.assertTrue(d["emittente_ragione_sociale"])
        self.assertIsNotNone(d["registro_id"])
        self.assertEqual(d["anno"], oggi.year)

    # Scopo: Con l'emittente ESPLICITO nel payload (la PK, com'e' nel form)
    #        arriva com'e' — e con lo stesso operatore e' lo stesso documento:
    #        la chiave di riuso comprende l'emittente, quindi «ridà quella di
    #        prima» e non ne apre una seconda.
    def test_con_emittente_esplicito_arriva_com_e_e_riusa(self):
        def _prova(cur):
            sigla, ef_id = self._mondo(cur)
            base = {
                "centro_riscossione_id": self._centro_cassa(cur),
                "data_contabile": oggi_aziendale().isoformat(),
                "meta": {"test_scope": "be_numerazione"},
            }
            prima = pagamenti_service.crea_distinta({**base, "emittente_fiscale_id": ef_id})
            seconda = pagamenti_service.crea_distinta(dict(base))
            return ef_id, prima["distinta"], seconda["distinta"]
        ef_id, prima, seconda = self._con_operatore(_prova)
        self.assertEqual(prima["emittente_fiscale_id"], ef_id)
        self.assertEqual(prima["id"], seconda["id"])
        self.assertEqual(prima["codice"], seconda["codice"])


class SaldoPrimaDiSeTests(_DbTestCase):
    """⭐ P-6 (2026-09-18): il «prima di se'» sul DOCUMENTO, provato contro la
    funzione vera e non contro un mock — i mock non vedono il binding
    `fn_get_saldo_fattura(%s, %s)`: una firma sbagliata e' un 500 sul pannello
    «Destinazione» di ogni riga in modifica, non un test rosso."""

    # Scopo: 🔴 La riga in BOZZA e' «in lavorazione» per 400 sui DUE livelli;
    #        con `escludi_riga_id` sparisce dai due allo stesso modo. E' il
    #        contratto che il pannello legge: stesso nome, stessa domanda,
    #        stessa risposta su rata e documento — prima del 18/09 il documento
    #        non aveva il parametro e il pannello DICHIARAVA di non saperla
    #        escludere.
    def test_il_documento_esclude_la_riga_come_la_rata(self):
        def _prova(cur):
            fattura_id, scadenza_id, riga_id = _monta_riga_piena(cur)
            doc = saldi_service.saldo_documento(fattura_id)
            doc_prima = saldi_service.saldo_documento(fattura_id, escludi_riga_id=riga_id)
            rata = saldi_service.saldo_rata(scadenza_id)
            rata_prima = saldi_service.saldo_rata(scadenza_id, escludi_riga_id=riga_id)
            return doc, doc_prima, rata, rata_prima
        doc, doc_prima, rata, rata_prima = self._con_operatore(_prova)
        self.assertEqual(doc["in_lavorazione"], Decimal("400.00"))
        self.assertEqual(doc_prima["in_lavorazione"], Decimal("0"))
        self.assertEqual(rata["in_lavorazione"], Decimal("400.00"))
        self.assertEqual(rata_prima["in_lavorazione"], Decimal("0"))
        # ⭐ La forma non cambia con l'opzione: gli stessi campi, lo stesso livello.
        self.assertEqual(set(doc), set(doc_prima))
        self.assertEqual(doc_prima["livello"], "DOCUMENTO")

    # Scopo: ⛔ Un id di esclusione non positivo non esce da nessuna
    #        interfaccia: il database lo rifiuta come guasto del chiamante
    #        (`E_PAGAMENTI_CHIAMATA_NON_VALIDA`, TECNICO) e il backend lo passa
    #        cosi' com'e' — NON lo normalizza a «nessuna esclusione», che
    #        farebbe leggere un saldo con la riga dentro a chi ha chiesto di
    #        toglierla. ⚠️ La base dei saldi non traduce: il `DatabaseError`
    #        arriva nudo al middleware, che legge il codice dal campo
    #        strutturato — e' la strada di `E_FATTURA_NON_TROVATA`, la stessa.
    def test_un_id_di_esclusione_non_positivo_e_un_guasto_dichiarato(self):
        def _prova(cur):
            fattura_id, _scadenza_id, _riga_id = _monta_riga_piena(cur)
            with self.assertRaises(DatabaseError) as ctx, transaction.atomic():
                saldi_service.saldo_documento(fattura_id, escludi_riga_id=0)
            return structured_db_error_code(ctx.exception)
        self.assertEqual(self._con_operatore(_prova), "E_PAGAMENTI_CHIAMATA_NON_VALIDA")
