# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: «GENERA ORDINE» E «ANNULLA» DA UN'OFFERTA ACCETTATA, visti dal backend
#        sul DATABASE VERO (brief-db-offerta-emissione-ed-erogazione §I.5.5,
#        decisioni I-D2 e H-R3 di Tid del 2026-10-21). L'ordine lo genera il
#        verbo DB `vendite.fn_genera_ordine_da_offerta`, che prende il posto
#        dell'orchestrazione Python; l'annullo da ACCETTATA lo ammette il DB, e
#        il service non ha piu' un «solo da BOZZA» suo.
#
# 🔴 PERCHE' SUL DB VERO. Le regole del verbo (stato, documenti vivi, righe,
#    testata, provenienza, righe espanse) le prova il pgTAP
#    `test-righe-ammesse-ai-passi-e-annullo-v1`. Qui si prova la GIUNTURA: che
#    la chiamata parta col nome e il tipo giusti (un mock la darebbe per buona
#    anche col nome di ieri) e che i rifiuti arrivino al `ServiceError` col
#    codice del verbo. E che l'annullo da ACCETTATA passi dal service fino al
#    guard, dove parla il DB.
#
# ⭐ Il mondo si COSTRUISCE (regola zero), come nel pgTAP: cliente, listino con
#    una versione in vigore da oggi, un articolo MERCE, un'offerta con una riga
#    AGGIUNTA nella combinazione di default dell'articolo, portata ad ACCETTATA
#    dalla fixture `dbops.fn_pgtap_porta_a_stato`, che passa dal verbo
#    dell'offerta e concede all'operatore l'azione dei passaggi
#    (`emetti_offerta`). ⛔ Fino al 2026-10-26 un UPDATE diretto dello stato:
#    ora la porta lo rifiuta (brief-modello-documento-vendita §13.6 punto 8).
#    Tutto in transazione ANNULLATA.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) test_genera_l_ordine_con_provenienza_e_righe
2) test_una_seconda_volta_e_rifiutata_col_codice_del_verbo — E_ORD_OFFERTA_GIA_CONVERTITA
3) test_da_un_offerta_in_bozza_e_rifiutata — E_ORD_ORIGINE_NON_CONVERTIBILE
4) test_un_offerta_che_non_c_e — E_OFFERTA_NON_TROVATA
5) test_annullo_da_accettata_con_l_ordine_vivo_rifiutato — E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI
6) test_annullo_da_accettata_senza_documenti_vivi — il service non lo ferma
7) test_il_dettaglio_porta_il_contratto_vivo — BE-T.5-b: `contratto_id` dalla provenienza
8) test_i_legami_dell_ordine_riportano_l_offerta — PROVENIENZA col codice della sorgente e il tipo da aprire
"""
from __future__ import annotations

import unittest
from collections.abc import Callable
from typing import Any

from django.db import connection, transaction

from apps.config.sorgenti import SORGENTE_OFFERTA_COMMERCIALE, SORGENTE_ORDINE_VENDITA
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import Annulla, richiedi_db_provvisto
from apps.vendite.services import ordini_service
from apps.vendite.services._annullo_con_legami import legami_del_documento
from apps.vendite.services.offerte_service import OfferteService

_FIXTURE: tuple[str, ...] = (
    "CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('GENORD')",
    "CREATE TEMP TABLE _l AS SELECT * FROM dbops.fn_pgtap_crea_listino("
    " (SELECT utility_id FROM _m), 'GENORD')",
    # Un bene: l'unica natura che un ordine contiene (la check delle righe
    # d'ordine). Senza tipologia: le erogazioni le dice la natura.
    "CREATE TEMP TABLE _a AS SELECT dbops.fn_pgtap_crea_articolo('GENORD-M',"
    " p_natura_vendita_id => (SELECT n.id FROM config.nature_vendita n"
    " WHERE n.codice_interno = 'MERCE')) AS id",
)

# Un'offerta in BOZZA sul listino, con un'AGGIUNTA nella combinazione di default
# dell'articolo (`vendite.fn_articolo_erogazioni`): la si legge dalla sede, non
# si ricopia.
_OFFERTA = (
    "INSERT INTO vendite.offerte_commerciali (emittente_fiscale_id, billing_account_id,"
    " istanza_utility_id, utility_id, listino_id, validita_dal, stato_doc_offerta_id)"
    " SELECT m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id, m.utility_id,"
    " (SELECT listino_id FROM _l), script.fn_data_operativa(),"
    " (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')"
    " FROM _m m RETURNING id"
)
_RIGA = (
    "INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id,"
    " tipo_eccezione, prezzo_unitario, qta_operativa, tipo_erogazione, fonte_quantita_attesa)"
    " SELECT %s, ar.id, 'AGGIUNTA', 10, CASE WHEN ae.fonte_quantita_attesa = 'FISSA' THEN 2 END,"
    " ae.tipo_erogazione, ae.fonte_quantita_attesa"
    " FROM catalogo.articoli ar"
    " JOIN vendite.fn_articolo_erogazioni(ar.id) ae ON ae.e_default"
    " WHERE ar.id = (SELECT id FROM _a)"
)
_PORTA_A = "SELECT dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali'::regclass, %s, %s)"


class GeneraOrdineDaOffertaDbTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("vendite.fn_genera_ordine_da_offerta(bigint)")

    # Scopo: costruisce il mondo, lancia `azione(cur)` e ne ritorna l'esito. Il
    #        blocco viene annullato.
    def _nel_mondo(self, azione: Callable[[Any], Any]) -> Any:
        esito = None
        try:
            with transaction.atomic(), connection.cursor() as cur:
                for sql in _FIXTURE:
                    cur.execute(sql)
                esito = azione(cur)
                raise Annulla
        except Annulla:
            pass
        return esito

    # Scopo: un'offerta con la sua riga, nello stato dato (BOZZA o ACCETTATA,
    #        per il percorso della matrice); ritorna l'id.
    @staticmethod
    def _offerta(cur, stato: str = "ACCETTATA") -> int:
        cur.execute(_OFFERTA)
        offerta_id = cur.fetchone()[0]
        cur.execute(_RIGA, [offerta_id])
        if stato == "ACCETTATA":
            cur.execute(_PORTA_A, [offerta_id, "ACCETTATA"])
        return offerta_id

    # Scopo: il codice del rifiuto, su un savepoint: la transazione del mondo
    #        resta usabile.
    def _rifiuto(self, chiamata: Callable[[], Any]) -> ServiceError:
        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            chiamata()
        return ctx.exception

    # 1.
    def test_genera_l_ordine_con_provenienza_e_righe(self):
        def azione(cur):
            offerta_id = self._offerta(cur)
            out = ordini_service.crea_ordine_da_offerta(offerta_id)
            cur.execute(
                "SELECT v.documento_origine_tipo, v.documento_origine_id, o.numero, s.codice_interno,"
                # La riga della MERCE dell'offerta. ⚠️ Dal giro 12 la versione
                # del listino ha anche la riga d'appoggio della fixture (un
                # articolo suo, brief-modello-documento-vendita §16.4), che
                # l'ordine espande accanto: come nel pgTAP delle offerte.
                " (SELECT count(*) FROM vendite.ordini_righe r"
                "   WHERE r.ordine_id = o.id AND r.articolo_id = (SELECT id FROM _a)),"
                " (SELECT max(r.prezzo_unitario) FROM vendite.ordini_righe r"
                "   WHERE r.ordine_id = o.id AND r.articolo_id = (SELECT id FROM _a))"
                " FROM vendite.ordini o JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id"
                # L'origine dagli alias stabili della vista, calcolati dalla
                # provenienza: le colonne parallele sono uscite col giro T.5.
                " JOIN vendite.vw_ordini_lista v ON v.id = o.id"
                " WHERE o.id = %s",
                [out["ordine_id"]],
            )
            return offerta_id, out, cur.fetchone()

        offerta_id, out, ordine = self._nel_mondo(azione)
        tipo, origine_id, numero, stato, righe, prezzo = ordine
        self.assertEqual((tipo, origine_id), (SORGENTE_OFFERTA_COMMERCIALE, offerta_id))
        self.assertEqual(out["numero"], numero)
        self.assertIsNotNone(numero)
        self.assertEqual(out["documento_origine"], {"tipo": SORGENTE_OFFERTA_COMMERCIALE, "id": offerta_id})
        self.assertEqual(stato, "DRAFT")
        # La riga espansa, al prezzo negoziato dell'offerta.
        self.assertEqual((righe, float(prezzo)), (1, 10.0))

    # 2.
    def test_una_seconda_volta_e_rifiutata_col_codice_del_verbo(self):
        def azione(cur):
            offerta_id = self._offerta(cur)
            ordini_service.crea_ordine_da_offerta(offerta_id)
            return self._rifiuto(lambda: ordini_service.crea_ordine_da_offerta(offerta_id))

        self.assertEqual(self._nel_mondo(azione).code, "E_ORD_OFFERTA_GIA_CONVERTITA")

    # 3.
    def test_da_un_offerta_in_bozza_e_rifiutata(self):
        def azione(cur):
            offerta_id = self._offerta(cur, stato="BOZZA")
            return self._rifiuto(lambda: ordini_service.crea_ordine_da_offerta(offerta_id))

        self.assertEqual(self._nel_mondo(azione).code, "E_ORD_ORIGINE_NON_CONVERTIBILE")

    # 4.
    def test_un_offerta_che_non_c_e(self):
        # Il massimo del bigint: nessuna sequenza ci arriva. `max(id) + N`
        # dipendeva dalle righe di oggi, e sotto RLS dalle sole visibili.
        assente = 9223372036854775807

        def azione(cur):
            return self._rifiuto(lambda: ordini_service.crea_ordine_da_offerta(assente))

        self.assertEqual(self._nel_mondo(azione).code, "E_OFFERTA_NON_TROVATA")

    # 5. L'annullo da ACCETTATA arriva al guard, che lo ferma col documento vivo.
    def test_annullo_da_accettata_con_l_ordine_vivo_rifiutato(self):
        def azione(cur):
            offerta_id = self._offerta(cur)
            ordini_service.crea_ordine_da_offerta(offerta_id)
            return self._rifiuto(
                lambda: OfferteService().annulla(offerta_id, motivazione="il cliente ci ripensa"),
            )

        self.assertEqual(self._nel_mondo(azione).code, "E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI")

    # 6. Senza documenti vivi l'offerta accettata si annulla: nessun «solo da
    #    BOZZA» nel service. ⚠️ L'annullo dell'accettata chiede `emetti_offerta`
    #    (O-1): l'operatore la ha dalla fixture, che gliel'ha concessa per
    #    emettere.
    def test_annullo_da_accettata_senza_documenti_vivi(self):
        def azione(cur):
            offerta_id = self._offerta(cur)
            return OfferteService().annulla(offerta_id, motivazione="il cliente ci ripensa")

        offerta = self._nel_mondo(azione)
        self.assertEqual(offerta["stato_codice_interno"], "ANNULLATA")

    # 7. BE-T.5-b: il dettaglio dell'offerta porta il contratto VIVO nato dal
    #    push, dalla sede unica `vendite.fn_offerta_documenti_vivi`. Fino al
    #    giro T.5 lo leggeva da `contratti.offerta_id`, che non esiste piu':
    #    il dettaglio intero si rompeva, e nessun test sul DB lo leggeva.
    def test_il_dettaglio_porta_il_contratto_vivo(self):
        def azione(cur):
            offerta_id = self._offerta(cur)
            prima = OfferteService().get_offerta(offerta_id)
            pushato = OfferteService().push_a_contratto(offerta_id)
            dopo = OfferteService().get_offerta(offerta_id)
            return prima, pushato, dopo

        prima, pushato, dopo = self._nel_mondo(azione)
        self.assertIsNone(prima["contratto_id"])
        self.assertIsNone(prima["contratto_numero"])
        self.assertEqual(dopo["contratto_id"], pushato["contratto_id"])
        self.assertEqual(dopo["contratto_numero"], pushato["contratto_codice"])

    # 8. I legami dell'ordine generato riportano l'offerta come PROVENIENZA:
    #    l'origine e' il codice della sorgente, ed e' anche il tipo da aprire.
    #    Stava in `test_origine_ordine_sorgente_db` su un id d'offerta inventato,
    #    che dal giro T.2 il guard unico della provenienza rifiuta.
    def test_i_legami_dell_ordine_riportano_l_offerta(self):
        def azione(cur):
            offerta_id = self._offerta(cur)
            out = ordini_service.crea_ordine_da_offerta(offerta_id)
            return offerta_id, legami_del_documento(SORGENTE_ORDINE_VENDITA, out["ordine_id"])

        offerta_id, legami = self._nel_mondo(azione)
        provenienze = [r for r in legami["righe"] if r["natura"] == "PROVENIENZA"]
        self.assertEqual(len(provenienze), 1, legami["righe"])
        riga = provenienze[0]
        self.assertEqual(riga["origine"], SORGENTE_OFFERTA_COMMERCIALE)
        self.assertEqual(riga["origine_id"], offerta_id)
        self.assertEqual(riga["origine_tipo_codice_interno"], SORGENTE_OFFERTA_COMMERCIALE)
