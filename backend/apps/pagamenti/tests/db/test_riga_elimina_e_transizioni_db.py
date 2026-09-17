# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidi sul DATABASE PROVVISTO per il seguito del collaudo del
#        2026-09-14 (D16/D17/D18): le colonne del blocco «elimina» esistono
#        davvero, la check che le alimenta esiste con la sua arita', l'INSERT
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
4) ColonneTests.test_la_check_esiste_con_arita_1
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
"""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from django.db import connection, transaction

from apps.core.services.error_manager import ServiceError
from apps.core.services.error_policies import ErrorPolicyRegistry
from apps.core.tests.db_e2e import apri_contesto_operatore, richiedi_db_provvisto
from apps.pagamenti.db import pagamenti_repository as repo_mod
from apps.pagamenti.db.pagamenti_repository import RIGHE_SORT_COLUMNS, PagamentiRepository
from apps.pagamenti.services import pagamenti_service

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
    "fattura_natura_doc_codice_interno",
    "fattura_natura_doc_descrizione",
    "scadenza_importo",
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
    #        una distinta).
    def test_la_riga_porta_le_quattro_colonne_del_blocco_elimina(self):
        colonne = self._colonne(f"{repo_mod._RIGA_SELECT} WHERE r.id = %s", [-1])
        for nome in _COLONNE_ELIMINA:
            self.assertIn(nome, colonne)

    # Scopo: ...e sulla coda, che condivide il frammento per costruzione.
    def test_anche_la_coda_le_porta(self):
        colonne = self._colonne(f"{repo_mod._RIGA_CODA_SELECT} WHERE r.id = %s", [-1])
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

    # Scopo: La check che alimenta la LATERAL esiste, con UN parametro. Se
    #        cambiasse firma, la lista delle righe risponderebbe 500.
    def test_la_check_esiste_con_arita_1(self):
        def _leggi(cur):
            cur.execute(
                """
                SELECT p.pronargs
                  FROM pg_proc p
                  JOIN pg_namespace n ON n.oid = p.pronamespace
                 WHERE n.nspname = 'script'
                   AND p.proname = 'fn_check_riga_contabile_eliminabile'
                """
            )
            return [r[0] for r in cur.fetchall()]
        arita = self._con_operatore(_leggi)
        self.assertEqual(arita, [1], "script.fn_check_riga_contabile_eliminabile(bigint) assente o con altra arita'")


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
    def test_il_difetto_del_collaudo_non_e_piu_offerto(self):
        _, riga = self._matrici()
        ammesse = pagamenti_service._transizioni_richiedibili(
            riga, pagamenti_service.STATI_RIGA_RICHIEDIBILI
        )
        self.assertNotIn("SCARTATA", ammesse.get("ABBINATA", []))
        self.assertIn("DA_ABBINARE", ammesse.get("ABBINATA", []))


# La fixture del secondo tempo, COSTRUITA (regola zero: non si pesca): la
# propria azienda col suo operatore, un cliente fatturabile, una fattura con
# UNA rata da 400, una distinta MANUALE in BOZZA e una riga ABBINATA a quella
# rata per 400 — cioe' la rata e' gia' piena. Stesse primitive dei pgTAP.
# ⚠️ Passi SEPARATI, non una CTE sola: il contesto operatore va aperto PRIMA
#    che nasca il cliente (il guard del billing account lo pretende), e in una
#    CTE l'ordine di valutazione dei rami non e' garantito.
_FIXTURE_PASSI: tuple[str, ...] = (
    """
    CREATE TEMP TABLE _mondo_bst AS
    SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m
    """,
    """
    SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo_bst))
    """,
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
          FROM _mondo_bst m, _cli_bst c
        RETURNING id
    )
    SELECT id AS fattura_id FROM ins
    """,
    """
    CREATE TEMP TABLE _rata_bst AS
    WITH ins AS (
        INSERT INTO vendite.fatture_scadenze (fattura_id, numero_rata, data_scadenza, importo)
        SELECT fattura_id, 1, current_date + 30, 400.00 FROM _fat_bst
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
               current_date, current_date,
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
    SELECT d.contabile_id, 'BE_SECONDO_TEMPO', current_date, 400.00,
           f.fattura_id, c.billing_account_id, r.scadenza_id,
           (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
             WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1)
      FROM _dist_bst d, _fat_bst f, _rata_bst r, _cli_bst c
    RETURNING id
    """,
)


class ModificaSecondoTempoTests(_DbTestCase):
    # Scopo: monta la fixture nel contesto dell'operatore che la possiede e
    #        consegna l'id della riga. ⚠️ Il contesto lo apre la funzione
    #        pgTAP dentro la CTE, non `apri_contesto_operatore`: l'operatore
    #        deve essere QUELLO dell'azienda costruita, o la RLS non gli
    #        farebbe vedere la fattura. Le TEMP TABLE muoiono col rollback.
    def _riga_piena(self, cur) -> int:
        for passo in _FIXTURE_PASSI:
            cur.execute(passo)
        row = cur.fetchone()
        assert row is not None
        return int(row[0])

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
