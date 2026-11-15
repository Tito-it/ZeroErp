# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La versione di listino AL MODELLO sul DATABASE PROVVISTO, dal lato
#        del backend (brief-modello-documento-vendita §16, giro 12): la riga
#        della versione porta lo stato dal vocabolario, i passaggi permessi e
#        il motivo di «Attiva», «Elimina» e «Chiudi»; attivazione, anteprima,
#        eliminazione, chiusura e clone sono i verbi e il lettore del DB
#        (§16.13, §16.16); i rifiuti arrivano col codice del DB.
#        E' la giuntura Python↔PL/pgSQL che i test del service (mock) non vedono.
# Note: ⚠️ Le REGOLE (matrice, porta, motivi, chiusura delle precedenti) le
#       prova il pgTAP `vendite/test-listino-versione-al-modello-v1`. Il mondo
#       si COSTRUISCE: `fn_pgtap_crea_listino` da' una versione ATTIVA aperta
#       da oggi (attivata dal verbo, con l'azione `attiva_listino` concessa
#       all'operatore del contesto); la seconda versione la crea il test, in
#       BOZZA, con decorrenza fra 30 giorni. Transazione ANNULLATA, ogni
#       rifiuto atteso in un SAVEPOINT. Opt-in `ZEROERP_TEST_DB_E2E=1`.
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) VersioneListinoModelloDbTests.test_la_riga_porta_stato_passaggi_e_motivo
2) VersioneListinoModelloDbTests.test_l_azione_della_riga
3) VersioneListinoModelloDbTests.test_attivazione_dal_verbo_chiude_le_precedenti
4) VersioneListinoModelloDbTests.test_senza_prezzi_non_si_attiva
4bis) VersioneListinoModelloDbTests.test_l_anteprima_non_scrive
5) VersioneListinoModelloDbTests.test_le_regole_per_stato_sono_del_db
6) VersioneListinoModelloDbTests.test_le_scadenze_leggono_il_vocabolario
7) VersioneListinoModelloDbTests.test_la_riga_porta_i_motivi_di_elimina_e_chiudi
8) VersioneListinoModelloDbTests.test_elimina_dal_verbo
9) VersioneListinoModelloDbTests.test_chiudi_dal_verbo
10) VersioneListinoModelloDbTests.test_clona_dal_verbo
10bis) VersioneListinoModelloDbTests.test_clona_salta_l_articolo_ritirato
"""
from __future__ import annotations

import unittest
from datetime import timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.db.documento_modello_repository import DocumentoModelloRepository
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.listini_repository import TESTATA_LISTINI_VERSIONI, ListiniRepository
from apps.vendite.services.listini_service import (
    fn_change_versione_state,
    fn_clone_versione,
    fn_delete_versione,
    fn_list_versioni,
    fn_programma_chiusura_versione,
    fn_update_versione,
)


class VersioneListinoModelloDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda sul verbo del giro: un DB indietro fallisce sull'oggetto
        # mancante, non su un'attesa sbagliata.
        for sonda in (
            "vendite.fn_attiva_versione_listino(bigint)",
            "vendite.fn_elimina_versione_listino(bigint)",
            "vendite.fn_programma_chiusura_versione_listino(bigint, date)",
            "vendite.fn_clona_versione_listino(bigint, varchar, date, date)",
        ):
            richiedi_db_provvisto(sonda)

    # Scopo: il listino con la versione ATTIVA (V1) e una BOZZA senza prezzi
    #        (V2) che decorre fra 30 giorni.
    def setUp(self) -> None:
        apri_transazione_annullata(self)
        self.repo = ListiniRepository()
        sfx = uuid4().hex[:8].upper()
        with connection.cursor() as cur:
            cur.execute(
                "CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente(%s)",
                [f"versione listino modello {sfx}"],
            )
            cur.execute(
                "SELECT l.listino_id, l.listino_versione_id, l.tipologia_id, script.fn_data_operativa() AS oggi"
                "  FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _mondo), %s) l",
                [f"versione listino modello {sfx}"],
            )
            mondo = row_to_dict(cur)
            assert mondo is not None
            # L'articolo nasce della tipologia del listino (una chiamata sola:
            # in una WHERE il builder girerebbe per ogni articolo letto).
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_articolo(%s, false, p_listino_tipologia_id => %s::smallint)",
                [f"LSMOD-{sfx}", mondo["tipologia_id"]],
            )
            articolo = cur.fetchone()[0]
            cur.execute("SELECT id::text, uom_id FROM catalogo.articoli WHERE id = %s", [articolo])
            self.articolo_id, self.uom_id = cur.fetchone()
        self.listino_id = int(mondo["listino_id"])
        self.v1 = int(mondo["listino_versione_id"])
        self.oggi = mondo["oggi"]
        self.v2_dal = self.oggi + timedelta(days=30)
        self.v2 = self.repo.create_versione(
            self.listino_id, {"codice_versione": f"V2-{sfx}", "valido_dal": self.v2_dal},
        )

    def _riga(self, versione_id: int) -> dict[str, Any]:
        righe = {r["id"]: r for r in fn_list_versioni(self.listino_id)[0]}
        return righe[versione_id]

    def _con_un_prezzo(self, versione_id: int) -> None:
        self.repo.create_riga(versione_id, {
            "articolo_id": self.articolo_id, "uom_id": self.uom_id, "prezzo": Decimal("10"),
        })

    def _rifiuto(self, chiamata: Any) -> ServiceError:
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            chiamata()
        return cm.exception

    # 1. Lo stato e' il codice del vocabolario; i passaggi sono quelli che
    #    l'operatore puo' fare da quello stato; il motivo di «Attiva» spento e'
    #    il primo della `fn_check`, con la sua chiave.
    def test_la_riga_porta_stato_passaggi_e_motivo(self) -> None:
        v1, v2 = self._riga(self.v1), self._riga(self.v2)
        self.assertEqual(v1["stato"], "ATTIVA")
        self.assertEqual(v1["azioni_permesse"], [])  # ATTIVA -> CHIUSA e' di processo
        self.assertIs(v1["chiusura_programmata"], False)  # aperta
        self.assertEqual(v2["stato"], "BOZZA")
        self.assertEqual(v2["azioni_permesse"], ["attiva"])
        self.assertEqual(v2["attivazione_blocco_reason"], "VERSIONE_SENZA_RIGHE")
        self.assertEqual(
            v2["attivazione_blocco_reason_key"], "vendite.listini.azione_reason.versione_senza_righe",
        )
        self._con_un_prezzo(self.v2)
        self.assertIsNone(self._riga(self.v2)["attivazione_blocco_reason"])

    # 2. Il permesso che la view chiede prima della transazione e' quello della
    #    riga del seed (`transizioni_stati_listino_versioni.csv`).
    def test_l_azione_della_riga(self) -> None:
        repo = DocumentoModelloRepository()
        self.assertEqual(
            repo.azione_del_passaggio(TESTATA_LISTINI_VERSIONI, self.v2, "ATTIVA"), "attiva_listino",
        )

    # 3. L'anteprima e l'attivazione dicono la stessa cosa (lo stesso lettore):
    #    V1 prende la fine al giorno prima della decorrenza di V2, V2 e' ATTIVA,
    #    e V1 mostra la chiusura programmata.
    def test_attivazione_dal_verbo_chiude_le_precedenti(self) -> None:
        self._con_un_prezzo(self.v2)
        anteprima = fn_change_versione_state(
            self.listino_id, self.v2, {"stato": "ATTIVA", "dry_run": True},
        )
        fine = self.v2_dal - timedelta(days=1)
        self.assertEqual(
            [(c["id"], c["valido_al_dopo"]) for c in anteprima["auto_close"]], [(self.v1, fine)],
        )
        self.assertEqual(self._riga(self.v2)["stato"], "BOZZA")  # l'anteprima non scrive

        out = fn_change_versione_state(self.listino_id, self.v2, {"stato": "ATTIVA"})

        self.assertEqual(out["stato"], "ATTIVA")
        v1 = self._riga(self.v1)
        self.assertEqual(v1["valido_al"], fine)
        self.assertIs(v1["chiusura_programmata"], True)

    # 4. Il primo motivo della `fn_check` arriva dal verbo col suo codice, e
    #    l'anteprima rifiuta allo stesso modo (il verbo in un savepoint).
    def test_senza_prezzi_non_si_attiva(self) -> None:
        errore = self._rifiuto(
            lambda: fn_change_versione_state(self.listino_id, self.v2, {"stato": "ATTIVA"}),
        )
        self.assertEqual(errore.code, "E_LISTINO_VERSIONE_SENZA_RIGHE")
        self.assertEqual(self._riga(self.v2)["stato"], "BOZZA")
        errore = self._rifiuto(
            lambda: fn_change_versione_state(
                self.listino_id, self.v2, {"stato": "ATTIVA", "dry_run": True},
            ),
        )
        self.assertEqual(errore.code, "E_LISTINO_VERSIONE_SENZA_RIGHE")

    # 4bis. Con i prezzi l'anteprima passa dal verbo ma non lascia niente:
    #       V2 resta BOZZA e V1 resta aperta.
    def test_l_anteprima_non_scrive(self) -> None:
        self._con_un_prezzo(self.v2)
        fn_change_versione_state(self.listino_id, self.v2, {"stato": "ATTIVA", "dry_run": True})
        self.assertEqual(self._riga(self.v2)["stato"], "BOZZA")
        self.assertIsNone(self._riga(self.v1)["valido_al"])

    # 5. Le regole per stato (L-5) sono del guard della versione: di una
    #    ATTIVA si cambia solo la fine, solo da «Chiudi» (C-4 = a), e non si
    #    elimina.
    def test_le_regole_per_stato_sono_del_db(self) -> None:
        errore = self._rifiuto(
            lambda: fn_update_versione(self.listino_id, self.v1, {"codice_versione": "ALTRO"}),
        )
        self.assertEqual(errore.code, "E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE")
        errore = self._rifiuto(lambda: fn_delete_versione(self.listino_id, self.v1))
        self.assertEqual(errore.code, "E_LISTINO_VERSIONE_NON_ELIMINABILE")
        fine = self.oggi + timedelta(days=10)
        errore = self._rifiuto(
            lambda: fn_update_versione(self.listino_id, self.v1, {"valido_al": fine.isoformat()}),
        )
        self.assertEqual(errore.code, "E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO")
        self.assertIsNone(self._riga(self.v1)["valido_al"])

    # Scopo: le versioni del listino che la regola del DB dice in scadenza
    #        (`giorni_alla_scadenza` della lista versioni, dal 2026-10-31).
    def _in_scadenza(self) -> set[int]:
        versioni, _ = self.repo.list_versioni_pagina(self.listino_id)
        return {v["id"] for v in versioni if v["giorni_alla_scadenza"] is not None}

    # 6. Le scadenze: V1 in vigore oggi che scade fra 10 giorni compare; con
    #    una BOZZA che le subentra (lo stato letto dal vocabolario) no. Fra 10
    #    giorni: dentro il preavviso del seed (15).
    def test_le_scadenze_leggono_il_vocabolario(self) -> None:
        fn_programma_chiusura_versione(
            self.listino_id, self.v1, {"valido_al": (self.oggi + timedelta(days=10)).isoformat()},
        )
        fn_delete_versione(self.listino_id, self.v2)
        self.assertIn(self.v1, self._in_scadenza())
        self.repo.create_versione(
            self.listino_id,
            {"codice_versione": "SUCC", "valido_dal": self.oggi + timedelta(days=11)},
        )
        self.assertNotIn(self.v1, self._in_scadenza())

    # 7. «Elimina» e «Chiudi» si spengono dalla superficie del DB col primo
    #    motivo della loro `fn_check` (§16.13 BE-E3, §16.16 BE-C3).
    def test_la_riga_porta_i_motivi_di_elimina_e_chiudi(self) -> None:
        v1, v2 = self._riga(self.v1), self._riga(self.v2)
        self.assertEqual(v1["eliminazione_blocco_reason"], "VERSIONE_NON_IN_BOZZA")
        self.assertEqual(
            v1["eliminazione_blocco_reason_key"], "vendite.listini.azione_reason.versione_non_in_bozza",
        )
        self.assertIsNone(v1["chiusura_blocco_reason"])
        self.assertIsNone(v2["eliminazione_blocco_reason"])
        self.assertEqual(v2["chiusura_blocco_reason"], "VERSIONE_NON_ATTIVA")
        self.assertEqual(
            v2["chiusura_blocco_reason_key"], "vendite.listini.azione_reason.versione_non_attiva",
        )

    # 8. L'eliminazione e' il verbo: una BOZZA con un prezzo se ne va intera,
    #    con i conteggi; una versione che non c'e' piu' e' un 404 del verbo.
    def test_elimina_dal_verbo(self) -> None:
        self._con_un_prezzo(self.v2)
        out = fn_delete_versione(self.listino_id, self.v2)
        self.assertEqual((out["deleted"], out["righe_eliminate"], out["componenti_eliminati"]), (True, 1, 0))
        self.assertNotIn(self.v2, {r["id"] for r in fn_list_versioni(self.listino_id)[0]})
        errore = self._rifiuto(lambda: fn_delete_versione(self.listino_id, self.v2))
        self.assertEqual(errore.code, "E_VENDITE_LISTINO_VERSIONE_NOT_FOUND")

    # 9. «Chiudi» e' il verbo: la fine nel passato e' rifiutata sul campo
    #    `valido_al`; una futura si scrive (lo stato resta ATTIVA, la chiusura
    #    e' programmata) e null la toglie. Su una BOZZA: non chiudibile.
    def test_chiudi_dal_verbo(self) -> None:
        ieri = self.oggi - timedelta(days=1)
        errore = self._rifiuto(
            lambda: fn_programma_chiusura_versione(self.listino_id, self.v1, {"valido_al": ieri.isoformat()}),
        )
        self.assertEqual(errore.code, "E_LISTINO_VERSIONE_FINE_NEL_PASSATO")
        self.assertEqual(errore.fields, ("valido_al",))
        fine = self.oggi + timedelta(days=20)
        out = fn_programma_chiusura_versione(self.listino_id, self.v1, {"valido_al": fine.isoformat()})
        self.assertEqual((out["stato"], out["valido_al"], out["chiusura_programmata"]), ("ATTIVA", fine, True))
        out = fn_programma_chiusura_versione(self.listino_id, self.v1, {"valido_al": None})
        self.assertIsNone(out["valido_al"])
        errore = self._rifiuto(
            lambda: fn_programma_chiusura_versione(self.listino_id, self.v2, {"valido_al": fine.isoformat()}),
        )
        self.assertEqual(errore.code, "E_LISTINO_VERSIONE_NON_CHIUDIBILE")

    # 10. Il clone e' il verbo, anche da una BOZZA (C-1 = a): la copia nasce
    #     BOZZA coi prezzi attivi; prima della sorgente e' rifiutata sul campo
    #     `valido_dal` (D2).
    def test_clona_dal_verbo(self) -> None:
        self._con_un_prezzo(self.v2)
        dal = self.v2_dal + timedelta(days=5)
        out = fn_clone_versione(self.listino_id, self.v2, {"codice_versione": "COPIA", "valido_dal": dal.isoformat()})
        self.assertEqual((out["stato"], out["valido_dal"], out["righe_count"]), ("BOZZA", dal, 1))
        self.assertEqual((out["righe_copiate"], out["componenti_copiati"], out["componenti_saltati"]), (1, 0, 0))
        self.assertEqual(out["righe_saltate"], 0)
        prima = self.v2_dal - timedelta(days=1)
        errore = self._rifiuto(
            lambda: fn_clone_versione(
                self.listino_id, self.v2, {"codice_versione": "PRIMA", "valido_dal": prima.isoformat()},
            ),
        )
        self.assertEqual(errore.code, "E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE")
        self.assertEqual(errore.fields, ("valido_dal",))

    # 10-bis. Il clone non ricopia il prezzo di un articolo ritirato alla data
    #     operativa, e lo conta: `righe_saltate` arriva fino alla risposta del
    #     service (brief-db-articoli-obsoleto-dal §8). Il caso si costruisce:
    #     un secondo articolo col suo prezzo, ritirato DOPO (una riga nuova su
    #     un articolo gia' ritirato la respinge il guard di riga).
    def test_clona_salta_l_articolo_ritirato(self) -> None:
        self._con_un_prezzo(self.v2)
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_crea_articolo(%s, false, p_listino_tipologia_id =>"
                " (SELECT listino_tipologia_id FROM catalogo.articoli WHERE id = %s))",
                [f"LSMOD-RIT-{uuid4().hex[:8].upper()}", self.articolo_id],
            )
            ritirato = cur.fetchone()[0]
            cur.execute("SELECT uom_id FROM catalogo.articoli WHERE id = %s", [ritirato])
            uom_ritirato = cur.fetchone()[0]
        self.repo.create_riga(self.v2, {
            "articolo_id": str(ritirato), "uom_id": uom_ritirato, "prezzo": Decimal("7"),
        })
        with connection.cursor() as cur:
            cur.execute("UPDATE catalogo.articoli SET obsoleto_dal = %s WHERE id = %s", [self.oggi, ritirato])
        dal = self.v2_dal + timedelta(days=5)
        out = fn_clone_versione(self.listino_id, self.v2, {"codice_versione": "COPIA-R", "valido_dal": dal.isoformat()})
        self.assertEqual((out["righe_copiate"], out["righe_saltate"], out["righe_count"]), (1, 1, 1))
