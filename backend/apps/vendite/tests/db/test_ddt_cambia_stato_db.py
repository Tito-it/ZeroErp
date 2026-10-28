# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Il cambio di stato della bolla DAL VERBO sul DATABASE PROVVISTO
#        (Lotto 3 R-1, piano-be-fe-magazzino-lotto-3 A1): `ddt_service.emetti`
#        arriva a `vendite.fn_cambia_stato_ddt`, una bolla che muove merce si
#        emette e scarica il magazzino nella stessa chiamata, una bolla senza
#        merce si emette senza movimenti, e il rifiuto della merce arriva al
#        client col codice che il DB ha scelto. E' la giuntura Python↔PL/pgSQL
#        che i test del service (mock) non vedono: firma, codice dello stato al
#        posto dell'id, righe ritornate.
# Note: ⚠️ Le REGOLE del verbo (porta del registro, kit, lotti, storno) le prova
#       il pgTAP `magazzino/test-ddt-scarico-v1`, da cui viene il mondo: azienda
#       e operatore, cliente, azioni concesse, magazzino, articoli costruiti
#       (gestito e non), giacenza da un inventario postato. Transazione SEMPRE
#       annullata; ogni rifiuto atteso in un SAVEPOINT.
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) DdtCambiaStatoDbTests.test_la_bolla_con_merce_si_emette_e_scarica
2) DdtCambiaStatoDbTests.test_la_bolla_senza_merce_si_emette_senza_movimenti
3) DdtCambiaStatoDbTests.test_oltre_la_giacenza_il_rifiuto_ha_il_codice_del_db
4) DdtCambiaStatoDbTests.test_il_magazzino_si_legge_e_si_cambia_in_bozza — A2
5) DdtCambiaStatoDbTests.test_il_prelievo_dal_lotto_e_lo_scarico_di_quel_lotto — B1
6) DdtCambiaStatoDbTests.test_i_rifiuti_dei_prelievi_hanno_il_loro_codice — B1
7) DdtCambiaStatoDbTests.test_il_reso_fa_rientrare_dal_prelievo_scelto — B2
8) DdtCambiaStatoDbTests.test_il_secondo_emetti_e_rifiutato_e_non_riscarica — §9.10
9) DdtCambiaStatoDbTests.test_lo_stato_che_non_c_e_lo_dice_il_verbo — §9.10
"""
from __future__ import annotations

import unittest
from typing import Any

from django.db import connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.services import ddt_service, resi_service

# Il mondo di `magazzino/test-ddt-scarico-v1`, ridotto a un articolo gestito
# (10 pezzi a giacenza) e uno non gestito.
_FIXTURE: tuple[str, ...] = (
    "CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore()",
    "SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az))",
    "CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('BE-L3-VERBO')",
    # Il verbo chiede `emetti_ddt` nella prima riga; il carico di giacenza
    # (inventario postato) chiede `registra_magazzino`.
    "SELECT dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'emetti_ddt')",
    "SELECT dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'registra_magazzino')",
    # La conferma del reso (3-bis D-3b-f) chiede la sua azione.
    "SELECT dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _m), 'conferma_reso')",
    """
    CREATE TEMP TABLE _fix AS
    SELECT dbops.fn_pgtap_crea_magazzino('BE-L3V-MAG', false)                     AS mag,
           dbops.fn_pgtap_crea_articolo('BE-L3V-GESTITO', true, false, false)      AS art_g,
           dbops.fn_pgtap_crea_articolo('BE-L3V-NON-GESTITO', false, false, false) AS art_n,
           (SELECT i.id FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1)    AS iva
    """,
    """
    CREATE TEMP TABLE _lotti AS
    WITH art AS (SELECT dbops.fn_pgtap_crea_articolo('BE-L3V-A-LOTTI', true, true, false) AS art_l),
         la AS (INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo)
                SELECT art_l, 'BE-L3V-LA', script.fn_data_operativa() - 10 FROM art RETURNING id, articolo_id),
         lb AS (INSERT INTO magazzino.lotti (articolo_id, codice, data_arrivo)
                SELECT art_l, 'BE-L3V-LB', script.fn_data_operativa() - 5 FROM art RETURNING id)
    SELECT la.articolo_id AS art_l, la.id AS lotto_a, lb.id AS lotto_b FROM la, lb
    """,
    """
    CREATE TEMP TABLE _inv AS
    WITH ins AS (INSERT INTO magazzino.inventari (magazzino_id) SELECT mag FROM _fix RETURNING id)
    SELECT id FROM ins
    """,
    """
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata, costo_unitario)
    SELECT (SELECT id FROM _inv), art_g, 10, 5 FROM _fix
    """,
    # L'articolo a lotti: 6 pezzi per lotto.
    """
    INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, lotto_id, qta_contata, costo_unitario)
    SELECT (SELECT id FROM _inv), art_l, lotto_a, 6, 3 FROM _lotti
    UNION ALL
    SELECT (SELECT id FROM _inv), art_l, lotto_b, 6, 3 FROM _lotti
    """,
    "UPDATE magazzino.inventari SET stato_mag_inventario = 'CONFIRM' WHERE id = (SELECT id FROM _inv)",
    "SELECT magazzino.fn_posta_inventario((SELECT id FROM _inv))",
)


class DdtCambiaStatoDbTests(unittest.TestCase):
    """Il cambio di stato della bolla passa dal verbo, sul mondo costruito."""

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto()

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            for passo in _FIXTURE:
                cur.execute(passo)
            cur.execute("SELECT mag, art_g::text, art_n::text, iva FROM _fix")
            self.mag, self.art_g, self.art_n, self.iva = cur.fetchone()
            cur.execute("SELECT art_l::text, lotto_a, lotto_b FROM _lotti")
            self.art_l, self.lotto_a, self.lotto_b = cur.fetchone()

    # Una bolla di vendita in bozza, dal magazzino del mondo, con una riga.
    def _bolla(self, articolo_id: str, qta: int) -> int:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_ddt("
                " (SELECT billing_account_id FROM _m), (SELECT cliente_soggetto_ruolo_id FROM _m),"
                " 'VENDITA', %s)",
                [self.mag],
            )
            ddt_id = int(cur.fetchone()[0])
            cur.execute(
                "INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,"
                " qta_operativa, quantita, prezzo_unitario, iva_id)"
                " VALUES (%s, 1, %s, 'riga', %s, %s, 10, %s)",
                [ddt_id, articolo_id, qta, qta, self.iva],
            )
        return ddt_id

    def _stato(self, ddt_id: int) -> str:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT s.codice_interno FROM vendite.ddt d"
                " JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id WHERE d.id = %s",
                [ddt_id],
            )
            return str(cur.fetchone()[0])

    def _giacenza(self) -> Any:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(sum(g.qta), 0) FROM magazzino.vw_giacenza g"
                " WHERE g.magazzino_id = %s AND g.articolo_id = %s::uuid",
                [self.mag, self.art_g],
            )
            return cur.fetchone()[0]

    def test_la_bolla_con_merce_si_emette_e_scarica(self) -> None:
        ddt_id = self._bolla(self.art_g, 4)

        out = ddt_service.emetti(ddt_id)

        self.assertEqual((out["stato_precedente"], out["stato"]), ("DRAFT", "EMESSO"))
        # Un articolo semplice: il verbo crea da se' l'unico prelievo e scrive
        # l'unica uscita, nella stessa chiamata dell'emissione.
        self.assertEqual(out["movimenti_scritti"], 1)
        self.assertEqual(self._stato(ddt_id), "EMESSO")
        self.assertEqual(self._giacenza(), 6)

    def test_la_bolla_senza_merce_si_emette_senza_movimenti(self) -> None:
        ddt_id = self._bolla(self.art_n, 2)

        out = ddt_service.emetti(ddt_id)

        self.assertEqual(out["stato"], "EMESSO")
        self.assertEqual(out["movimenti_scritti"], 0)
        self.assertEqual(self._giacenza(), 10)

    # Un secondo «Emetti» lo rifiuta la prima riga del verbo, prima dei
    # controlli della merce: il codice e' quello del documento gia' nello
    # stato, non un motivo di giacenza, e il magazzino non si muove di nuovo
    # (brief-modello-documento-vendita §9.10). Il PDF non nasce perche' la
    # view genera il documento solo dopo il verbo, nella stessa transazione
    # (test_ddt_api `test_emetti_rifiutato_non_genera_il_documento`).
    def test_il_secondo_emetti_e_rifiutato_e_non_riscarica(self) -> None:
        ddt_id = self._bolla(self.art_g, 4)
        ddt_service.emetti(ddt_id)

        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            ddt_service.emetti(ddt_id)

        self.assertEqual(cm.exception.code, "E_DOC_GIA_NELLO_STATO")
        self.assertEqual(self._stato(ddt_id), "EMESSO")
        self.assertEqual(self._giacenza(), 6)

    # Lo stato che il vocabolario della bolla non ha: il verbo risponde come i
    # gemelli, non piu' con la chiamata malformata (un 500), e il service non
    # ne ha una copia (§9.10).
    def test_lo_stato_che_non_c_e_lo_dice_il_verbo(self) -> None:
        ddt_id = self._bolla(self.art_g, 1)

        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            ddt_service.cambia_stato(ddt_id, "INESISTENTE")

        self.assertEqual(cm.exception.code, "E_STATO_WORKFLOW_NON_TROVATO")
        self.assertEqual(self._stato(ddt_id), "DRAFT")

    def test_oltre_la_giacenza_il_rifiuto_ha_il_codice_del_db(self) -> None:
        ddt_id = self._bolla(self.art_g, 100)
        # Il codice atteso lo dice il DB (la stessa check che alimenta la
        # capability), non il test: e' il primo motivo della merce.
        with connection.cursor() as cur:
            cur.execute(
                "SELECT script.fn_check_ddt_merce(d) -> 0 ->> 'codice' FROM vendite.ddt d WHERE d.id = %s",
                [ddt_id],
            )
            atteso = cur.fetchone()[0]
        self.assertIsNotNone(atteso, "il caso non si e' formato: nessun motivo della merce")

        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            ddt_service.emetti(ddt_id)

        self.assertEqual(cm.exception.code, atteso)
        self.assertEqual(self._stato(ddt_id), "DRAFT")
        self.assertEqual(self._giacenza(), 10)

    # A2 (Lotto 3 R-2a): il magazzino di partenza viaggia nel dettaglio con le
    # etichette, e in bozza si cambia dal service (whitelist di service e
    # repository: una chiave mancante in una delle due e' un errore che si vede).
    def test_il_magazzino_si_legge_e_si_cambia_in_bozza(self) -> None:
        ddt_id = self._bolla(self.art_g, 1)
        with connection.cursor() as cur:
            cur.execute("SELECT dbops.fn_pgtap_crea_magazzino('BE-L3V-MAG2', false)")
            mag2 = int(cur.fetchone()[0])

        prima = ddt_service.get_ddt(ddt_id)
        self.assertEqual(prima["magazzino_id"], self.mag)
        self.assertIsNone(prima["magazzino_arrivo_id"])

        ddt_service.aggiorna_ddt(ddt_id, {"magazzino_id": mag2})

        dopo = ddt_service.get_ddt(ddt_id)
        self.assertEqual(dopo["magazzino_id"], mag2)
        self.assertEqual(dopo["magazzino_codice"], "BE-L3V-MAG2")

    # B1 (Lotto 3 R-2b): una riga a lotti non e' automatica; il prelievo scelto
    # dall'operatore e' quello che l'emissione scarica.
    def test_il_prelievo_dal_lotto_e_lo_scarico_di_quel_lotto(self) -> None:
        ddt_id = self._bolla(self.art_l, 4)
        situazione = ddt_service.get_prelievi(ddt_id)
        self.assertTrue(situazione["muove_merce"])
        self.assertEqual(len(situazione["voci"]), 1)
        voce = situazione["voci"][0]
        self.assertFalse(voce["automatico"])
        self.assertTrue(voce["requires_lotto"])
        self.assertEqual((voce["qta"], voce["prelevata"], voce["prelievi"]), (4, 0, []))

        out = ddt_service.crea_prelievo(
            ddt_id, voce["ddt_riga_id"], {"qta": "4", "lotto_id": self.lotto_b},
        )
        dopo = ddt_service.get_prelievi(ddt_id)["voci"][0]
        self.assertEqual(dopo["prelevata"], 4)
        self.assertEqual(
            [(p["id"], p["lotto_codice"]) for p in dopo["prelievi"]],
            [(out["prelievo_id"], "BE-L3V-LB")],
        )

        self.assertEqual(ddt_service.emetti(ddt_id)["movimenti_scritti"], 1)
        with connection.cursor() as cur:
            # La giacenza per lotto dal registro (nessuna vista per lotto): 6 - 4.
            cur.execute(
                "SELECT COALESCE(sum(m.qta), 0) FROM magazzino.movimenti m"
                " WHERE m.magazzino_id = %s AND m.lotto_id = %s",
                [self.mag, self.lotto_b],
            )
            self.assertEqual(cur.fetchone()[0], 2)

    # B1: i rifiuti arrivano col codice giusto — la posizione ripetuta (UNIQUE,
    # tradotta dal service), la quantita' mancante (validazione), il prelievo di
    # una riga di un'altra bolla (404), e dopo l'emissione il lock del DB.
    def test_i_rifiuti_dei_prelievi_hanno_il_loro_codice(self) -> None:
        ddt_id = self._bolla(self.art_l, 4)
        riga_id = ddt_service.get_prelievi(ddt_id)["voci"][0]["ddt_riga_id"]
        altra = self._bolla(self.art_l, 1)

        def codice(chiamata: Any) -> str:
            with self.assertRaises(ServiceError) as cm, transaction.atomic():
                chiamata()
            return cm.exception.code

        ddt_service.crea_prelievo(ddt_id, riga_id, {"qta": "2", "lotto_id": self.lotto_a})
        self.assertEqual(
            codice(lambda: ddt_service.crea_prelievo(ddt_id, riga_id, {"qta": "1", "lotto_id": self.lotto_a})),
            "E_VENDITE_DUPLICATO",
        )
        self.assertEqual(
            codice(lambda: ddt_service.crea_prelievo(ddt_id, riga_id, {"lotto_id": self.lotto_b})),
            "E_DDT_VALIDAZIONE",
        )
        self.assertEqual(
            codice(lambda: ddt_service.crea_prelievo(altra, riga_id, {"qta": "1", "lotto_id": self.lotto_b})),
            "E_DDT_NOT_FOUND",
        )

        ddt_service.crea_prelievo(ddt_id, riga_id, {"qta": "2", "lotto_id": self.lotto_b})
        ddt_service.emetti(ddt_id)
        self.assertEqual(
            codice(lambda: ddt_service.crea_prelievo(ddt_id, riga_id, {"qta": "1", "lotto_id": self.lotto_b})),
            "E_RIGA_DOC_NON_BOZZA",
        )

    # B2 (3-bis R-1b): il reso di una bolla a lotti fa rientrare la merce dal
    # PRELIEVO d'origine che l'operatore sceglie, nel magazzino del reso (lo
    # propone il DB dalla bolla), e la conferma ricarica proprio quel lotto.
    def test_il_reso_fa_rientrare_dal_prelievo_scelto(self) -> None:
        ddt_id = self._bolla(self.art_l, 4)
        riga_ddt = ddt_service.get_prelievi(ddt_id)["voci"][0]["ddt_riga_id"]
        prelievo = ddt_service.crea_prelievo(ddt_id, riga_ddt, {"qta": "4", "lotto_id": self.lotto_b})
        ddt_service.emetti(ddt_id)
        for stato in ("SPEDITO", "CONSEGNATO"):
            ddt_service.cambia_stato(ddt_id, stato)
        with connection.cursor() as cur:
            cur.execute("SELECT id FROM config.tipi_reso WHERE codice_interno = 'RESO_A_CREDITO'")
            tipo_reso_id = int(cur.fetchone()[0])
        reso = resi_service.crea_reso({
            "ddt_id": ddt_id,
            "righe": [{"ddt_riga_id": riga_ddt, "tipo_reso_id": tipo_reso_id, "qta_operativa": "2"}],
        })
        reso_id, riga_reso = int(reso["id"]), reso["righe_ids"][0]

        situazione = resi_service.get_rientri(reso_id)
        self.assertTrue(situazione["muove_merce"])
        self.assertEqual(situazione["magazzino_id"], self.mag)
        voce = situazione["voci"][0]
        self.assertEqual((voce["qta"], voce["rientrata"]), (2, 0))
        self.assertEqual([p["id"] for p in voce["prelievi_origine"]], [prelievo["prelievo_id"]])
        self.assertEqual(voce["prelievi_origine"][0]["lotto_codice"], "BE-L3V-LB")

        resi_service.crea_rientro(
            reso_id, riga_reso, {"ddt_riga_prelievo_id": prelievo["prelievo_id"], "qta": "2"},
        )
        dopo = resi_service.get_rientri(reso_id)["voci"][0]
        self.assertEqual(dopo["rientrata"], 2)
        self.assertEqual([r["lotto_codice"] for r in dopo["rientri"]], ["BE-L3V-LB"])

        resi_service.conferma_reso(reso_id)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(sum(m.qta), 0) FROM magazzino.movimenti m"
                " WHERE m.magazzino_id = %s AND m.lotto_id = %s",
                [self.mag, self.lotto_b],
            )
            # 6 caricati, 4 usciti con la bolla, 2 rientrati col reso.
            self.assertEqual(cur.fetchone()[0], 4)
