# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: LA PROVENIENZA DEL PREZZO LA SCRIVE CHI SCRIVE IL PREZZO, sul DATABASE
#        VERO (K-5 e K-7 di brief-db-provenienza-prezzo-segue-il-prezzo §8.7,
#        D-5 del §8.11): le righe le scrive il SERVICE, cioe' il gate prezzi
#        (`resolve_or_check_override_prezzo`), col resolver vero, e il lister
#        del push restituisce cio' che il gate ha scritto. I tre casi di R-6:
#          * il prezzo dal listino → la riga cita la riga di listino, e quella
#            e' «propagata» (non si rettifica piu');
#          * il prezzo scritto a mano, anche uguale a quello del listino →
#            MANUALE, senza listino;
#          * il prezzo cambiato dopo la precompilazione → decaduto a MANUALE, e
#            la riga di listino che nessuno cita piu' torna rettificabile.
#        Piu' la provenienza dichiarata dal form: verificata, o 409.
#
# 🔴 PERCHE' SUL DB VERO. Le quattro colonne passano tre giunture che un mock
#    non vede: il contesto lo calcola il DB (`vendite.fn_prezzo_resolver_contesto`
#    nella query del resolver), il CHECK `chk_ordrighe_provenienza_prezzo` e il
#    guard `trgfn_riga_documento_guard_listino_provenienza` giudicano la riga
#    scritta, e la «propagata» la decide il guard delle righe di listino.
#
# ⭐ Il mondo si COSTRUISCE (regola zero), con i builder dei pgTAP: l'ordine in
#    bozza del mondo (`dbops.fn_pgtap_crea_ordine`, che apre il contesto
#    sull'operatore), un cliente con una categoria mappata su un listino, il
#    listino con una versione ATTIVA e quattro articoli, tre a listino. L'ordine
#    e' il documento: K-5 ve lo porta per la prima volta (strada A di Tid,
#    2026-11-15). Transazione ANNULLATA.
#
# ⚠️ I gate L1 e L2 si neutralizzano: il soggetto e' la provenienza, non il
#    permesso dell'operatore del mondo (`test_pricing_gate_helpers`).
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
# ------------------------------------------------------------
"""Indice test:

1. test_senza_prezzo_la_riga_cita_il_listino_e_lo_propaga
2. test_lo_stesso_prezzo_scritto_a_mano_e_manuale
3. test_il_prezzo_cambiato_decade_e_libera_la_riga_di_listino
4. test_la_provenienza_dichiarata_si_verifica_o_e_409
5. test_il_lister_del_push_restituisce_cio_che_il_gate_ha_scritto
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest import TestCase
from unittest.mock import patch

from django.db import DatabaseError, connection, transaction

from apps.core.db._helpers import row_to_dict
from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.services import ordini_service

_PREZZO = Decimal("50.00")

_FIXTURE = (
    "CREATE TEMP TABLE _o ON COMMIT DROP AS"
    " SELECT * FROM dbops.fn_pgtap_crea_ordine('K7 provenienza dal gate', 'DRAFT')",
    # Il trigger di fatturazione e' una condizione della bozza: CONFERMATO,
    # perche' il lister restituisca le righe appena l'ordine e' confermato.
    "UPDATE vendite.ordini SET fatturazione_trigger = 'CONFERMATO'"
    " WHERE id = (SELECT ordine_id FROM _o)",
    "CREATE TEMP TABLE _cat ON COMMIT DROP AS WITH ins AS ("
    " INSERT INTO anagrafiche.categorie_clienti (codice, codice_interno, descrizione, partecipa_promo)"
    " SELECT s.sigla, s.sigla, 'Fixture K7 provenienza', FALSE"
    " FROM (SELECT 'K7-PRV-' || substr(md5(clock_timestamp()::text || random()::text), 1, 12) AS sigla) s"
    " RETURNING id) SELECT id FROM ins",
    "UPDATE anagrafiche.billing_account SET categoria_cliente_id = (SELECT id FROM _cat)"
    " WHERE id = (SELECT billing_account_id FROM _o)",
    "CREATE TEMP TABLE _l ON COMMIT DROP AS SELECT * FROM dbops.fn_pgtap_crea_listino("
    " (SELECT utility_id FROM _o), 'K7 provenienza', '2020-01-01'::date, NULL::date)",
    "CREATE TEMP TABLE _art ON COMMIT DROP AS"
    " SELECT v.k, dbops.fn_pgtap_crea_articolo(('PGT-K7-' || v.k || '-'"
    "   || substr(md5(clock_timestamp()::text || random()::text), 1, 10))::varchar,"
    "   false, p_listino_tipologia_id => (SELECT tipologia_id FROM _l)) AS id"
    " FROM (VALUES ('A1'), ('A2'), ('A3'), ('A4')) v(k)",
    # A1, A3 e A4 a listino; A2 no.
    "CREATE TEMP TABLE _r ON COMMIT DROP AS WITH ins AS ("
    " INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)"
    f" SELECT (SELECT listino_versione_id FROM _l), ar.id, ar.uom_id, {_PREZZO}"
    " FROM catalogo.articoli ar JOIN _art a ON a.id = ar.id WHERE a.k <> 'A2'"
    " RETURNING id, articolo_id) SELECT a.k, i.id FROM ins i JOIN _art a ON a.id = i.articolo_id",
    "INSERT INTO anagrafiche.categorie_clienti_listini (categoria_cliente_id, utility_id,"
    " emittente_soggetto_ruolo_id, classe_utenza_id, listino_id, valido_dal)"
    " SELECT (SELECT id FROM _cat), o.utility_id, o.emittente_soggetto_ruolo_id, NULL,"
    " (SELECT listino_id FROM _l), '2020-01-01' FROM _o o",
)

_RIGA = (
    "SELECT prezzo_unitario, origine_prezzo, listino_versione_id, listino_riga_id,"
    " prezzo_resolver_context FROM vendite.ordini_righe WHERE id = %s"
)


class ProvenienzaPrezzoDalGateDbTests(TestCase):

    def setUp(self) -> None:
        richiedi_db_provvisto("vendite.fn_prezzo_resolver_contesto(jsonb)")
        apri_transazione_annullata(self)
        for bersaglio in ("check_permesso_override_prezzo", "check_limite_variazione_prezzo"):
            gate = patch(
                f"apps.vendite.services._pricing_gate_helpers.{bersaglio}", return_value=None,
            )
            gate.start()
            self.addCleanup(gate.stop)
        with connection.cursor() as cur:
            for sql in _FIXTURE:
                cur.execute(sql)
            cur.execute("SELECT ordine_id, auth_user_id FROM _o")
            self.ordine_id, self.utente = cur.fetchone()
            cur.execute("SELECT listino_versione_id FROM _l")
            self.versione = cur.fetchone()[0]
            cur.execute("SELECT a.k, a.id::text, ar.uom_id FROM _art a JOIN catalogo.articoli ar ON ar.id = a.id")
            self.articoli = {k: (art, uom) for k, art, uom in cur.fetchall()}
            cur.execute("SELECT k, id FROM _r")
            self.righe_listino = dict(cur.fetchall())

    def _riga(self, chiave: str, **campi: Any) -> int:
        articolo, uom = self.articoli[chiave]
        esito = ordini_service.gestisci_riga(
            self.ordine_id,
            {"articolo_id": articolo, "uom_operativa_id": uom, "qta_operativa": 1,
             "descrizione": f"K7 {chiave}", **campi},
            auth_user_id=self.utente,
        )
        return int(esito["riga_id"])

    def _letta(self, riga_id: int) -> dict[str, Any]:
        with connection.cursor() as cur:
            cur.execute(_RIGA, [riga_id])
            letta = row_to_dict(cur)
        assert letta is not None
        return letta

    # Vero se la riga di listino si rettifica: il guard la rifiuta se e' propagata.
    def _rettificabile(self, chiave: str) -> bool:
        try:
            with transaction.atomic(), connection.cursor() as cur:
                cur.execute(
                    "UPDATE vendite.listini_righe SET prezzo = prezzo + 1 WHERE id = %s",
                    [self.righe_listino[chiave]],
                )
                raise _Annulla
        except _Annulla:
            return True
        except DatabaseError as exc:
            self.assertIn("E_RIGA_LISTINO_PROPAGATA", str(exc))
            return False

    # 1. Senza prezzo: il resolver vero, e la riga cita la riga di listino.
    def test_senza_prezzo_la_riga_cita_il_listino_e_lo_propaga(self) -> None:
        self.assertTrue(self._rettificabile("A1"))
        letta = self._letta(self._riga("A1"))
        self.assertEqual(letta["prezzo_unitario"], _PREZZO)
        self.assertNotEqual(letta["origine_prezzo"], "MANUALE")
        self.assertEqual(letta["listino_versione_id"], self.versione)
        self.assertEqual(letta["listino_riga_id"], self.righe_listino["A1"])
        # Il contesto lo calcola il DB, senza le chiavi che hanno una sede loro.
        self.assertIsInstance(letta["prezzo_resolver_context"], dict)
        self.assertNotIn("listino_riga_id", letta["prezzo_resolver_context"])
        self.assertFalse(self._rettificabile("A1"))

    # 2. ⛔ K-5: lo stesso numero del listino, senza la dichiarazione, e' MANUALE.
    def test_lo_stesso_prezzo_scritto_a_mano_e_manuale(self) -> None:
        letta = self._letta(self._riga("A3", prezzo_unitario=str(_PREZZO)))
        self.assertEqual(letta["origine_prezzo"], "MANUALE")
        self.assertIsNone(letta["listino_riga_id"])
        self.assertIsNone(letta["listino_versione_id"])
        self.assertTrue(self._rettificabile("A3"))

    # 3. Precompilata dal listino, poi il prezzo cambia: decade, e libera R.
    def test_il_prezzo_cambiato_decade_e_libera_la_riga_di_listino(self) -> None:
        riga_id = self._riga("A3")
        self.assertFalse(self._rettificabile("A3"))
        ordini_service.aggiorna_riga(
            self.ordine_id, riga_id, {"prezzo_unitario": "47"}, auth_user_id=self.utente,
        )
        letta = self._letta(riga_id)
        self.assertEqual(letta["prezzo_unitario"], Decimal("47"))
        self.assertEqual(letta["origine_prezzo"], "MANUALE")
        self.assertIsNone(letta["listino_riga_id"])
        self.assertIsNone(letta["prezzo_resolver_context"])
        self.assertTrue(self._rettificabile("A3"))
        # E la quantita' corretta col prezzo di prima non ripassa dal gate.
        ordini_service.aggiorna_riga(
            self.ordine_id, riga_id, {"prezzo_unitario": "47.00", "qta_operativa": 3},
            auth_user_id=self.utente,
        )
        self.assertEqual(self._letta(riga_id)["origine_prezzo"], "MANUALE")

    # 4. D-5: la provenienza che il form rimanda si verifica sul listino di adesso.
    def test_la_provenienza_dichiarata_si_verifica_o_e_409(self) -> None:
        origine = self._letta(self._riga("A1"))["origine_prezzo"]
        dichiarata = {
            "origine_prezzo": origine, "listino_versione_id": self.versione,
            "listino_riga_id": self.righe_listino["A4"],
        }
        letta = self._letta(self._riga(
            "A4", prezzo_unitario=str(_PREZZO), provenienza_prezzo=dichiarata,
        ))
        self.assertEqual(letta["origine_prezzo"], origine)
        self.assertEqual(letta["listino_riga_id"], self.righe_listino["A4"])

        # La riga di listino di un altro articolo: il listino non la conferma.
        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            self._riga("A4", prezzo_unitario=str(_PREZZO), provenienza_prezzo={
                **dichiarata, "listino_riga_id": self.righe_listino["A1"],
            })
        self.assertEqual(ctx.exception.code, "E_PRICING_PROVENIENZA_SUPERATA")
        # Un articolo che il listino non ha: niente da confermare.
        with self.assertRaises(ServiceError) as ctx, transaction.atomic():
            self._riga("A2", prezzo_unitario="33", provenienza_prezzo=dichiarata)
        self.assertEqual(ctx.exception.code, "E_PRICING_PROVENIENZA_SUPERATA")

    # 5. Il push legge cio' che il gate ha scritto: la riga di listino per A1,
    #    nessuna per il prezzo a mano.
    def test_il_lister_del_push_restituisce_cio_che_il_gate_ha_scritto(self) -> None:
        self._riga("A1")
        self._riga("A2", prezzo_unitario="33")
        with connection.cursor() as cur:
            # L'aliquota che la conferma pretende: il mondo del test non ha un
            # trattamento IVA per i suoi articoli, e non e' il soggetto. Si
            # sceglie come fa il builder dei pgTAP (`fn_pgtap_crea_ordine_con_righe`).
            cur.execute(
                "UPDATE vendite.ordini_righe SET iva_id = (SELECT i.id FROM config.iva i"
                " WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)"
                " WHERE ordine_id = %s AND iva_id IS NULL",
                [self.ordine_id],
            )
            cur.execute(
                "SELECT dbops.fn_pgtap_porta_a_stato('vendite.ordini'::regclass, %s, 'CONFERMATO')",
                [self.ordine_id],
            )
            cur.execute(
                "SELECT a.k, l.origine_prezzo, l.listino_riga_id, l.listino_versione_id"
                " FROM vendite.fn_list_ordini_da_pushare(p_ordine_id := %s) l"
                " JOIN _art a ON a.id = l.articolo_id",
                [self.ordine_id],
            )
            uscite = {k: (o, r, v) for k, o, r, v in cur.fetchall()}
        self.assertEqual(uscite["A1"][1:], (self.righe_listino["A1"], self.versione))
        self.assertNotEqual(uscite["A1"][0], "MANUALE")
        self.assertEqual(uscite["A2"], ("MANUALE", None, None))


class _Annulla(Exception):
    pass
