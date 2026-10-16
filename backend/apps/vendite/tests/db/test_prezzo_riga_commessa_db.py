# ------------------------------------------------------------
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: RIALLINEA, SBLOCCA E VARIA IL PREZZO DI UNA RIGA DI COMMESSA, sul
#        DATABASE VERO (L0 di piano-be-type-checker §4, 2026-10-08): il prezzo
#        arriva dal resolver vero, e con il prezzo si scrive la sua provenienza.
#
# 🔴 PERCHE' SUL DB VERO, ed e' il difetto da cui nasce: dal 2026-04-15 i due
#    percorsi chiamavano `ListiniRepository.test_resolver`, un metodo che non
#    esisteva piu' — un 500 su entrambi i pulsanti del drawer di gestione
#    commessa. Il test unitario era VERDE: mockava il repository e dichiarava
#    `test_resolver.return_value = {...}`, cioe' fabbricava il metodo mancante.
#    E leggeva `prezzo`, che il resolver chiama `prezzo_finale`. Solo una
#    chiamata vera vede la giuntura fra il service e la funzione DB.
#
# ⭐ IL MONDO SI COSTRUISCE (regola zero), con i builder dei pgTAP (la riga la
#    scrive `dbops.fn_pgtap_crea_commessa_attivita`, che passa dalla madre
#    `vendite.fn_upsert_commessa_attivita`): commessa con una riga, cliente con una categoria mappata su un listino, il listino con
#    due versioni — V1 (2020, chiusa) e V2 (dal 2021, aperta: e' quella in
#    vigore alla data della riga). La riga nasce «registrata sotto V1»: e' la
#    riga di un push fatto quando V1 era in vigore. Tutto in transazione
#    ANNULLATA.
#
# ⚠️ RICHIEDE IL DB VERO, opt-in `ZEROERP_TEST_DB_E2E=1` (accesa in CI).
#
# Indice test:
#   1. test_riallinea_chiede_conferma_poi_scrive_prezzo_e_versione
#   2. test_variazione_manuale_poi_sblocco_dal_listino
#   3. test_componente_di_kit_prende_il_prezzo_del_kit
#   4. test_riallinea_rende_propagata_la_riga_di_listino
#   5. test_porta_batch_scrive_la_riga_di_listino
#
# ⭐ 4-5 (brief-db-riga-listino-propagata-dalla-commessa §5, 2026-10-09): la
#    riga di listino che ha dato il prezzo si scrive sulla riga di commessa, e
#    da li' e' «propagata» — la rettifica N6 la rifiuta e il guard DB anche.
#    Prima nessun percorso la scriveva, e la rettifica passava.
# ------------------------------------------------------------
from __future__ import annotations

from decimal import Decimal
from unittest import TestCase

from django.db import DatabaseError, connection, transaction

from apps.core.services.service_errors import ServiceError
from apps.core.tests.db_e2e import apri_transazione_annullata, richiedi_db_provvisto
from apps.vendite.db.commesse_repository import CommessaAttivitaInput, CommesseRepository
from apps.vendite.services.commesse_service import (
    fn_riallinea_prezzo,
    fn_sblocca_prezzo,
    fn_variazione_prezzo_eccezionale,
)
from apps.vendite.services.listini_service import fn_rettifica_controllata_riga

# Il prezzo con cui la riga arriva dal push, prima di ogni riallineamento.
_PREZZO_PUSH = Decimal("10")
_PREZZO_V2 = Decimal("46.00")
_PREZZO_KIT = Decimal("75.00")

_FIXTURE = (
    "CREATE TEMP TABLE _c ON COMMIT DROP AS"
    " SELECT * FROM dbops.fn_pgtap_crea_commessa('L0 prezzo riga')",
    # Il cliente ha una categoria, e la categoria porta al listino.
    "CREATE TEMP TABLE _cat ON COMMIT DROP AS WITH ins AS ("
    " INSERT INTO anagrafiche.categorie_clienti (codice, codice_interno, descrizione, partecipa_promo)"
    " SELECT s.sigla, s.sigla, 'Fixture L0 prezzo riga', FALSE"
    " FROM (SELECT 'L0-PRZ-' || substr(md5(clock_timestamp()::text || random()::text), 1, 12) AS sigla) s"
    " RETURNING id) SELECT id FROM ins",
    "UPDATE anagrafiche.billing_account SET categoria_cliente_id = (SELECT id FROM _cat)"
    " WHERE id = (SELECT billing_account_id FROM _c)",
    # V1 nel 2020, chiusa; V2 dal 2021, aperta, nasce in BOZZA per riceverne le righe.
    "CREATE TEMP TABLE _l ON COMMIT DROP AS SELECT * FROM dbops.fn_pgtap_crea_listino("
    " (SELECT utility_id FROM _c), 'L0 prezzo riga', '2020-01-01'::date, '2020-12-31'::date)",
    "CREATE TEMP TABLE _v2 ON COMMIT DROP AS WITH ins AS ("
    " INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, stato)"
    " SELECT listino_id, 'L0_V2', '2021-01-01'::date, 'BOZZA' FROM _l RETURNING id"
    ") SELECT id FROM ins",
    # ⛔ L'articolo nasce GIA' della tipologia del listino, e solo dopo va sulla
    #    riga di commessa: un articolo usato non cambia la tipologia (guard
    #    `catalogo.trgfn_articoli_guard_struttura_se_usato`, A-10 del
    #    2026-10-13). Per questo il builder lo riceve dal chiamante.
    "CREATE TEMP TABLE _art ON COMMIT DROP AS SELECT dbops.fn_pgtap_crea_articolo("
    " ('PGT-L0P-' || substr(md5(clock_timestamp()::text || random()::text), 1, 12))::varchar,"
    " false) AS articolo_id",
    "UPDATE catalogo.articoli SET listino_tipologia_id = (SELECT tipologia_id FROM _l)"
    " WHERE id = (SELECT articolo_id FROM _art)",
    # La riga «registrata sotto V1»: e' la riga di un push fatto quando V1 era
    # in vigore. La scrive il builder `dbops.fn_pgtap_crea_commessa_attivita`
    # (contesto dalla commessa), che passa dalla madre
    # `vendite.fn_upsert_commessa_attivita`: il chiamante sceglie l'articolo,
    # la versione e il prezzo (brief-db-coerenza-listino-della-riga-di-
    # commessa §5.3). ⛔ Il prezzo si passa anche se e' quello di default del
    # builder: il test 1 lo rilegge, e non deve dipendere da un default altrui. Fino al 2026-10-16 qui c'era una copia della chiamata
    # alla madre, con tutti i suoi parametri.
    "CREATE TEMP TABLE _a ON COMMIT DROP AS"
    " SELECT b.attivita_id, b.articolo_id, b.uom_id"
    " FROM _l l, _art a, _c c,"
    " dbops.fn_pgtap_crea_commessa_attivita("
    "   c.commessa_id,"
    f"   p_prezzo_snapshot     => {_PREZZO_PUSH},"
    "   p_articolo_id         => a.articolo_id,"
    "   p_listino_versione_id => l.listino_versione_id) b",
    "INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)"
    f" SELECT (SELECT id FROM _v2), a.articolo_id, a.uom_id, {_PREZZO_V2} FROM _a a",
    # Il kit P di cui l'articolo della riga e' componente: nel listino, il
    # componente dentro P costa diverso dal componente sciolto.
    "CREATE TEMP TABLE _p ON COMMIT DROP AS"
    " SELECT dbops.fn_pgtap_crea_articolo('L0-KIT-' || substr(md5(random()::text), 1, 10), false) AS id",
    "UPDATE catalogo.articoli SET listino_tipologia_id = (SELECT tipologia_id FROM _l),"
    " is_composito = TRUE WHERE id = (SELECT id FROM _p)",
    "INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)"
    " SELECT (SELECT id FROM _p), (SELECT articolo_id FROM _a), 1, '2020-01-01'",
    "INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,"
    " articolo_padre_id, articolo_figlio_id, prezzo, valido_dal)"
    f" SELECT (SELECT id FROM _v2), ac.id, ac.prodotto_id, ac.componente_id, {_PREZZO_KIT}, '2021-01-01'"
    " FROM catalogo.articoli_componenti ac WHERE ac.prodotto_id = (SELECT id FROM _p)",
    "UPDATE vendite.listini_versioni SET stato = 'ATTIVA' WHERE id = (SELECT id FROM _v2)",
    "INSERT INTO anagrafiche.categorie_clienti_listini (categoria_cliente_id, utility_id,"
    " emittente_soggetto_ruolo_id, classe_utenza_id, listino_id, valido_dal)"
    " SELECT (SELECT id FROM _cat), c.utility_id, c.emittente_soggetto_ruolo_id, NULL,"
    " (SELECT listino_id FROM _l), '2021-01-01' FROM _c c",
)

_RIGA = (
    "SELECT prezzo_snapshot, prezzo_bloccato, listino_versione_id, origine_prezzo,"
    " prezzo_base_snapshot FROM vendite.commesse_attivita WHERE id = %s"
)


class PrezzoRigaCommessaDbTests(TestCase):
    """Riallinea, sblocca e varia: prezzo e provenienza dal resolver vero."""

    def setUp(self) -> None:
        richiedi_db_provvisto("dbops.fn_pgtap_crea_commessa(text)")
        apri_transazione_annullata(self)
        with connection.cursor() as cur:
            for sql in _FIXTURE:
                cur.execute(sql)
            cur.execute(
                "SELECT c.commessa_id, a.attivita_id, l.listino_id, l.listino_versione_id, v.id,"
                " r.id"
                " FROM _c c, _a a, _l l, _v2 v"
                " JOIN vendite.listini_righe r ON r.listino_versione_id = v.id"
                " WHERE r.articolo_id = a.articolo_id AND r.uom_id = a.uom_id"
            )
            (
                self.commessa, self.attivita, self.listino, self.v1, self.v2, self.riga_v2,
            ) = cur.fetchone()

    # Scopo: la riga di listino citata ADESSO dalla riga di commessa.
    def _listino_riga_della_commessa(self) -> int | None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT listino_riga_id FROM vendite.commesse_attivita WHERE id = %s",
                [self.attivita],
            )
            return cur.fetchone()[0]

    # Scopo: la rettifica N6 della riga di listino V2.
    def _rettifica(self) -> dict:
        return fn_rettifica_controllata_riga(
            self.listino, self.v2, self.riga_v2, {"prezzo": "47.00", "motivo": "refuso"},
        )

    def _riga(self) -> tuple:
        with connection.cursor() as cur:
            cur.execute(_RIGA, [self.attivita])
            return cur.fetchone()

    # 1. Registrata sotto V1, oggi vale V2: prima si chiede conferma senza
    #    scrivere; confermato, si scrivono prezzo E versione; il riallineamento
    #    dopo non chiede piu' niente (la versione si e' aggiornata).
    def test_riallinea_chiede_conferma_poi_scrive_prezzo_e_versione(self) -> None:
        domanda = fn_riallinea_prezzo(self.commessa, self.attivita, {})
        self.assertTrue(domanda["richiede_conferma"])
        self.assertEqual(
            (domanda["versione_originale_id"], domanda["versione_attuale_id"]),
            (self.v1, self.v2),
        )
        self.assertEqual(Decimal(domanda["prezzo_ricalcolato"]), _PREZZO_V2)
        self.assertEqual(self._riga()[0], _PREZZO_PUSH, "senza conferma non si scrive")

        fatto = fn_riallinea_prezzo(
            self.commessa, self.attivita, {"conferma_versione_diversa": True},
        )
        self.assertTrue(fatto["versione_cambiata"])
        prezzo, bloccato, versione, origine, base = self._riga()
        self.assertEqual(prezzo, _PREZZO_V2)
        self.assertFalse(bloccato)
        self.assertEqual(versione, self.v2)
        self.assertEqual(origine, "CATEGORIA")
        self.assertEqual(base, _PREZZO_V2)

        di_nuovo = fn_riallinea_prezzo(self.commessa, self.attivita, {})
        self.assertFalse(di_nuovo["versione_cambiata"])
        self.assertNotIn("richiede_conferma", di_nuovo)

    # 2. Il prezzo a mano dice di esserlo (MANUALE, niente provenienza da
    #    listino); lo sblocco lo ricalcola e riscrive la provenienza.
    def test_variazione_manuale_poi_sblocco_dal_listino(self) -> None:
        fn_variazione_prezzo_eccezionale(
            self.commessa, self.attivita, {"prezzo": "33.00", "motivo": "accordo"},
        )
        prezzo, bloccato, versione, origine, base = self._riga()
        self.assertEqual((prezzo, bloccato), (Decimal("33.00"), True))
        self.assertEqual(origine, "MANUALE")
        self.assertIsNone(versione)
        self.assertIsNone(base)

        fn_sblocca_prezzo(self.commessa, self.attivita, {"motivo": "fine accordo"})
        prezzo, bloccato, versione, origine, base = self._riga()
        self.assertEqual((prezzo, bloccato), (_PREZZO_V2, False))
        self.assertEqual((versione, origine), (self.v2, "CATEGORIA"))

    # 3. La riga e' il componente del kit P (`componente_di` nel meta, come la
    #    scrive l'espansione del push): il prezzo e' quello del componente
    #    dentro P, non quello sciolto. L'origine dello stadio kit
    #    (`LISTINO_BUNDLE`) non e' fra quelle del CHECK: resta NULL.
    def test_componente_di_kit_prende_il_prezzo_del_kit(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "UPDATE vendite.commesse_attivita"
                " SET meta = jsonb_build_object('componente_di', (SELECT id FROM _p)::text),"
                "     listino_versione_id = NULL"
                " WHERE id = %s",
                [self.attivita],
            )

        fn_riallinea_prezzo(self.commessa, self.attivita, {})
        prezzo, _, versione, origine, _ = self._riga()
        self.assertEqual(prezzo, _PREZZO_KIT)
        self.assertEqual(versione, self.v2)
        self.assertIsNone(origine)

    # 4. Riallineata, la riga di commessa cita la riga di listino V2, che da li'
    #    e' «propagata»: la rettifica N6 la rifiuta con il codice del guard DB
    #    (l'unica sede della regola dal 2026-10-09), e cosi' il guard a chi la
    #    scrivesse senza passare dal service (letto dal CONSTRAINT_NAME, non da
    #    un errore qualunque). Un prezzo a mano non la cita piu', e la riga
    #    torna rettificabile: «propagata» vuol dire citata ADESSO (D-1).
    def test_riallinea_rende_propagata_la_riga_di_listino(self) -> None:
        self._rettifica()  # nessuno la cita: passa

        fn_riallinea_prezzo(self.commessa, self.attivita, {"conferma_versione_diversa": True})
        self.assertEqual(self._listino_riga_della_commessa(), self.riga_v2)

        with self.assertRaises(ServiceError) as ctx:
            self._rettifica()
        self.assertEqual(ctx.exception.code, "E_RIGA_LISTINO_PROPAGATA")

        with self.assertRaises(DatabaseError) as db_ctx, transaction.atomic(), \
                connection.cursor() as cur:
            cur.execute(
                "UPDATE vendite.listini_righe SET prezzo = prezzo + 1 WHERE id = %s",
                [self.riga_v2],
            )
        diag = getattr(db_ctx.exception.__cause__, "diag", None)
        self.assertEqual(getattr(diag, "constraint_name", None), "E_RIGA_LISTINO_PROPAGATA")

        fn_variazione_prezzo_eccezionale(
            self.commessa, self.attivita, {"prezzo": "33.00", "motivo": "accordo"},
        )
        self.assertIsNone(self._listino_riga_della_commessa())
        self._rettifica()

    # 5. La porta batch del repository (quella che usa il push) porta la riga
    #    di listino fino alla madre: e' la giuntura fra `_inp_to_jsonb_row` e la
    #    chiave JSON che `fn_batch_upsert_commessa_attivita` legge, che un mock
    #    non vede. ⚠️ Oggi l'handler del push la passa NULL (decisione B,
    #    2026-10-09): la riempira' la provenienza del documento
    #    (brief-db-provenienza-prezzo-segue-il-prezzo). Qui la si passa a mano.
    def test_porta_batch_scrive_la_riga_di_listino(self) -> None:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT segment_key, quantita, competenza_mese, articolo_id, prezzo_snapshot,"
                " uom_id, istanza_utility_id, data_attivita, competenza_dal, competenza_al,"
                " tipo_doc_fiscale_id, valuta_id, sorgente_tipo_id, sorgente_uid"
                " FROM vendite.commesse_attivita WHERE id = %s",
                [self.attivita],
            )
            (
                segment_key, quantita, competenza_mese, articolo_id, prezzo, uom_id,
                istanza_utility_id, data_attivita, competenza_dal, competenza_al,
                tipo_doc_fiscale_id, valuta_id, sorgente_tipo_id, sorgente_uid,
            ) = cur.fetchone()

        # Il re-push della stessa riga (stesso segmento: ramo ON CONFLICT).
        # ⛔ Con la SUA sorgente, come il push vero: dal 2026-10-12 una riga
        #   NORMALE senza sorgente non entra
        #   (`chk_commesse_attivita_senza_sorgente_onere_rettifica`,
        #   brief-db-annullo-a-valle-riapre-a-monte §8.5).
        esito = CommesseRepository().batch_upsert_attivita([CommessaAttivitaInput(
            commessa_id=self.commessa,
            segment_key=segment_key,
            quantita=quantita,
            competenza_mese=competenza_mese,
            articolo_id=articolo_id,
            prezzo_snapshot=prezzo,
            uom_id=uom_id,
            istanza_utility_id=istanza_utility_id,
            data_attivita=data_attivita,
            competenza_dal=competenza_dal,
            competenza_al=competenza_al,
            tipo_doc_fiscale_id=tipo_doc_fiscale_id,
            valuta_id=valuta_id,
            listino_versione_id=self.v2,
            listino_riga_id=self.riga_v2,
            sorgente_tipo_id=sorgente_tipo_id,
            sorgente_uid=sorgente_uid,
        )])
        self.assertEqual(esito.errors, [])
        self.assertEqual(self._listino_riga_della_commessa(), self.riga_v2)
        with self.assertRaises(ServiceError) as ctx:
            self._rettifica()
        self.assertEqual(ctx.exception.code, "E_RIGA_LISTINO_PROPAGATA")
