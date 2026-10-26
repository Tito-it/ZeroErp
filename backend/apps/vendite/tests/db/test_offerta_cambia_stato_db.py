# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Lo stato dell'offerta DAI SUOI VERBI sul DATABASE PROVVISTO
#        (brief-modello-documento-vendita §13.6, giro 9): «Emetti» e l'esito
#        arrivano a `vendite.fn_cambia_stato_offerta`, l'annullo a
#        `vendite.fn_annulla_offerta` con la conferma dei legami, e i rifiuti
#        arrivano al client col codice che il DB ha scelto. E' la giuntura
#        Python↔PL/pgSQL che i test del service (mock) non vedono: firme, la
#        motivazione che arriva al verbo, il legame della revisione precedente.
# Note: ⚠️ Le REGOLE dei verbi (matrice, azione, motivazione, porta, proiezione
#       della revisione) le prova il pgTAP `vendite/test-offerta-al-modello-v1`.
#       Il mondo si COSTRUISCE (cliente, listino con una versione in vigore, un
#       articolo, un'offerta in bozza con la sua riga), in transazione
#       ANNULLATA; ogni rifiuto atteso in un SAVEPOINT. Opt-in
#       `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti (opt-in `ZEROERP_TEST_DB_E2E=1`):
1) OffertaCambiaStatoDbTests.test_emetti_dal_verbo
2) OffertaCambiaStatoDbTests.test_emetti_senza_azione — E_PERMESSO_NEGATO dalla riga del passaggio
3) OffertaCambiaStatoDbTests.test_il_secondo_emetti_e_rifiutato — E_DOC_GIA_NELLO_STATO
4) OffertaCambiaStatoDbTests.test_rifiuto_senza_motivazione_e_con — E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA (campo `motivazione`), poi RIFIUTATA
5) OffertaCambiaStatoDbTests.test_annullo_della_bozza_senza_azione_vuole_la_motivazione — M-4, O-3
6) OffertaCambiaStatoDbTests.test_annullo_di_una_revisione_chiede_la_conferma — O-4: legami, rifiuto, conferma
"""
from __future__ import annotations

import unittest
from typing import Any

from django.db import connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.services.offerte_service import OfferteService

# Il mondo, come in `test_genera_ordine_da_offerta_db`: un bene sul listino del
# cliente, con una versione in vigore da oggi (le condizioni dell'emissione).
_FIXTURE: tuple[str, ...] = (
    "CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('OFFSTATO')",
    "CREATE TEMP TABLE _l AS SELECT * FROM dbops.fn_pgtap_crea_listino("
    " (SELECT utility_id FROM _m), 'OFFSTATO')",
    "CREATE TEMP TABLE _a AS SELECT dbops.fn_pgtap_crea_articolo('OFFSTATO-M',"
    " p_natura_vendita_id => (SELECT n.id FROM config.nature_vendita n"
    " WHERE n.codice_interno = 'MERCE')) AS id",
)
_OFFERTA = (
    "INSERT INTO vendite.offerte_commerciali (emittente_fiscale_id, billing_account_id,"
    " istanza_utility_id, utility_id, listino_id, validita_dal)"
    " SELECT m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id, m.utility_id,"
    " (SELECT listino_id FROM _l), script.fn_data_operativa()"
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


class OffertaCambiaStatoDbTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # La sonda sulla firma FINALE del verbo d'annullo (giro 9): il verbo di
        # stato nasce nello stesso giro.
        richiedi_db_provvisto("vendite.fn_annulla_offerta(bigint,text,integer)")

    def setUp(self) -> None:
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            for sql in _FIXTURE:
                cur.execute(sql)
            cur.execute("SELECT auth_user_id FROM _m")
            self.auth_user_id = int(cur.fetchone()[0])
            cur.execute(_OFFERTA)
            self.offerta_id = int(cur.fetchone()[0])
            cur.execute(_RIGA, [self.offerta_id])
        self.servizio = OfferteService()

    def _concedi_emetti_offerta(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT dbops.fn_pgtap_concedi_azione(%s, 'emetti_offerta')", [self.auth_user_id],
            )

    def _stato(self, offerta_id: int | None = None) -> dict[str, Any]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT s.codice_interno AS stato, o.motivazione_rifiuto"
                " FROM vendite.offerte_commerciali o"
                " JOIN config.stati_doc_offerte s ON s.id = o.stato_doc_offerta_id"
                " WHERE o.id = %s",
                [offerta_id or self.offerta_id],
            )
            riga = row_to_dict(cur)
        assert riga is not None
        return riga

    def _rifiuto(self, chiamata: Any) -> ServiceError:
        with self.assertRaises(ServiceError) as cm, transaction.atomic():
            chiamata()
        return cm.exception

    def test_emetti_dal_verbo(self) -> None:
        self._concedi_emetti_offerta()
        out = self.servizio.emetti(self.offerta_id)
        self.assertEqual(out["stato_codice_interno"], "EMESSA")
        self.assertEqual(self._stato()["stato"], "EMESSA")

    def test_emetti_senza_azione(self) -> None:
        errore = self._rifiuto(lambda: self.servizio.emetti(self.offerta_id))
        self.assertEqual(errore.code, "E_PERMESSO_NEGATO")
        self.assertEqual(self._stato()["stato"], "BOZZA")

    def test_il_secondo_emetti_e_rifiutato(self) -> None:
        self._concedi_emetti_offerta()
        self.servizio.emetti(self.offerta_id)
        errore = self._rifiuto(lambda: self.servizio.emetti(self.offerta_id))
        self.assertEqual(errore.code, "E_DOC_GIA_NELLO_STATO")
        self.assertEqual(self._stato()["stato"], "EMESSA")

    # L'obbligo della motivazione lo dice la riga del passaggio, al verbo (O-3):
    # il service non la controlla piu'. Vuota o di soli spazi = assente.
    def test_rifiuto_senza_motivazione_e_con(self) -> None:
        self._concedi_emetti_offerta()
        self.servizio.emetti(self.offerta_id)

        errore = self._rifiuto(lambda: self.servizio.registra_esito(
            self.offerta_id, esito="RIFIUTATA", motivazione="   ",
        ))
        self.assertEqual(errore.code, "E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA")
        # Il verbo nomina la colonna (`motivazione_rifiuto`, canale COLUMN): al
        # client il campo della richiesta.
        self.assertEqual(errore.fields, ("motivazione",))
        self.assertEqual(self._stato()["stato"], "EMESSA")

        self.servizio.registra_esito(self.offerta_id, esito="RIFIUTATA", motivazione=" prezzo alto ")
        self.assertEqual(self._stato(), {"stato": "RIFIUTATA", "motivazione_rifiuto": "prezzo alto"})

    # L'annullo della bozza chiede il solo livello sul documento (M-4): nessuna
    # azione concessa. La motivazione si'.
    def test_annullo_della_bozza_senza_azione_vuole_la_motivazione(self) -> None:
        errore = self._rifiuto(lambda: self.servizio.annulla(self.offerta_id, motivazione=None))
        self.assertEqual(errore.code, "E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA")
        self.assertEqual(errore.fields, ("motivazione",))
        self.assertEqual(self._stato()["stato"], "BOZZA")

        out = self.servizio.annulla(self.offerta_id, motivazione="errore di impostazione")
        self.assertEqual(out["stato_codice_interno"], "ANNULLATA")
        self.assertEqual(
            self._stato(), {"stato": "ANNULLATA", "motivazione_rifiuto": "errore di impostazione"},
        )

    # O-4: annullare l'ultima revisione viva fa tornare emessa la precedente.
    # Non in silenzio: il primo tentativo e' la domanda, la finestra legge un
    # legame (la revisione precedente), la conferma lo dichiara.
    def test_annullo_di_una_revisione_chiede_la_conferma(self) -> None:
        self._concedi_emetti_offerta()
        self.servizio.emetti(self.offerta_id)
        revisione_id = int(self.servizio.crea_revisione(self.offerta_id)["id"])
        self.assertEqual(self._stato()["stato"], "SUPERATA")

        domanda = self._rifiuto(lambda: self.servizio.annulla(revisione_id, motivazione="sbagliata"))
        self.assertEqual(domanda.code, "E_DOC_ANNULLO_CON_LEGAMI")
        self.assertEqual(self._stato(revisione_id)["stato"], "BOZZA")
        self.assertEqual(self._stato()["stato"], "SUPERATA")

        legami = self.servizio.get_legami(revisione_id)
        self.assertEqual(legami["documento"], "OFFERTA_COMMERCIALE")
        self.assertEqual(legami["legami"], 1)
        self.assertEqual(
            [(r["origine"], r["natura"], r["origine_id"]) for r in legami["righe"]],
            [("OFFERTA_COMMERCIALE", "PROVENIENZA", self.offerta_id)],
        )

        self.servizio.annulla(revisione_id, motivazione="sbagliata", legami_confermati=legami["legami"])
        self.assertEqual(self._stato(revisione_id)["stato"], "ANNULLATA")
        self.assertEqual(self._stato()["stato"], "EMESSA")
