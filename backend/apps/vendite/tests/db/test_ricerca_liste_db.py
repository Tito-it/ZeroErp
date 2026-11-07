# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: La ricerca libera delle liste di vendite convertite al BB
#        `add_ricerca_full_condition` al passo 7 di
#        brief-be-ricerca-full-liste-residue (listini, righe di listino, promo,
#        gruppi di competenza, famiglie di documento), provata sul DATABASE
#        PROVVISTO dal repository: per ogni colonna che il CATALOGO accende, il
#        valore di una riga COSTRUITA la trova, e un termine che non c'e' non
#        trova niente (`verifica_ricerca_colonna_per_colonna`).
#        ⭐ Le liste non hanno `vista_sql` (tranne le famiglie): questo e' il
#        loro esercizio sul DB vero, quello che `test_ricerca_full_db` nomina in
#        `_ESERCITATE_DAL_REPOSITORY`. I test di servizio mockano il repository
#        e non vedono la SQL; `EXPLAIN` dice che la SQL parte, non che TROVA.
# Note: ⚠️ Il mondo si COSTRUISCE, non si cerca (regola zero, .codex/AGENTS.md):
#       azienda, operatore, cliente, articolo, listino, promo, preventivo e la
#       sua attivita' di competenza, un contratto con la sua riga e un'offerta sul listino nascono dai BB `dbops.fn_pgtap_*` e dalle
#       madri di dominio, in transazione ANNULLATA e col contesto operatore
#       aperto dal builder. Le famiglie di documento sono SEED (contratto, non
#       fotografia): se ne ritocca una riga, sempre in transazione annullata.
#       Opt-in `ZEROERP_TEST_DB_E2E=1` (acceso in CI).
# ------------------------------------------------------------
"""
Indice test eseguiti:
1) RicercaListeVenditeDbTests.test_la_ricerca_trova_ogni_colonna_accesa
"""
from __future__ import annotations

import unittest
from datetime import date
from uuid import uuid4

from django.db import connection, transaction

from apps.core.tests.db_e2e import (
    Annulla,
    richiedi_db_provvisto,
    verifica_ricerca_colonna_per_colonna,
)
from apps.vendite.db.contratti_repository import ContrattoRigheListaRepository
from apps.vendite.db.famiglie_repository import FamiglieDocumentoRepository
from apps.vendite.db.listini_repository import ListiniRepository
from apps.vendite.db.offerte_repository import OffertaRigheListaRepository
from apps.vendite.db.promo_articoli_repository import PromoArticoliRepository
from apps.vendite.db.vendite_repository import VenditeRepository

# Il mese di competenza del gruppo costruito: lontano da qualunque dato vero,
# cosi' la lista del mese contiene solo cio' che il test ha fatto nascere.
_COMPETENZA = date(2083, 2, 1)

# Il mondo, in ordine. ⚠️ `fn_pgtap_crea_mondo_cliente` PRIMA di tutto: senza
# contesto costruisce l'azienda col suo operatore e APRE il contesto su di lui —
# il listino (guard emittente_scope) e la vista dei gruppi (fail-closed senza
# GUC) vogliono proprio quello. `%(sfx)s` rende unici i codici che hanno un
# vincolo UNIQUE globale.
_FIXTURE: tuple[str, ...] = (
    "CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('ricerca liste vendite')",
    """
    CREATE TEMP TABLE _refs AS
    SELECT (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
           (SELECT t.id FROM config.tipi_doc_fiscale t
             WHERE t.attivo IS TRUE
               AND EXISTS (SELECT 1 FROM vendite.tipi_doc_fiscale_registri m
                            WHERE m.tipo_doc_fiscale_id = t.id)
             ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
           (SELECT s.id FROM config.sorgenti s
             WHERE s.codice_interno = 'PREVENTIVO' ORDER BY s.id LIMIT 1) AS src_preventivo_id
    """,
    # ── Listino e riga ─────────────────────────────────────────────────────
    # ⚠️ L'articolo nasce della TIPOLOGIA del listino: il guard
    #    `trgfn_listini_righe_guard_tipologia` rifiuta un articolo senza, e su
    #    un articolo usato la tipologia non cambia piu' (guard A-10). Per
    #    questo il listino nasce prima dell'articolo.
    "CREATE TEMP TABLE _lst AS SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _mondo), 'ricerca')",
    "CREATE TEMP TABLE _art AS SELECT dbops.fn_pgtap_crea_articolo('RVART-' || %(sfx)s, false,"
    " p_listino_tipologia_id => (SELECT tipologia_id FROM _lst)) AS articolo_id",
    """
    UPDATE catalogo.articoli
       SET descrizione = 'Articolo ricdescart'
     WHERE id = (SELECT articolo_id FROM _art)
    """,
    """
    UPDATE vendite.listini
       SET codice = 'RVLST-' || %(sfx)s, descrizione = 'Listino ricdesclst'
     WHERE id = (SELECT listino_id FROM _lst)
    """,
    """
    CREATE TEMP TABLE _riga AS
    WITH ins AS (
        INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id, prezzo)
        SELECT l.listino_versione_id, a.id, a.uom_id, 10.00
          FROM _lst l, catalogo.articoli a
         WHERE a.id = (SELECT articolo_id FROM _art)
        RETURNING id
    )
    SELECT id AS riga_id FROM ins
    """,
    # ── Promo ──────────────────────────────────────────────────────────────
    # ⚠️ `valido_dal` da domani: il guard data-driven rifiuta una promo che
    #    nasce gia' iniziata.
    """
    CREATE TEMP TABLE _promo AS
    WITH ins AS (
        INSERT INTO vendite.promo_articoli
            (codice, descrizione, articolo_id, uom_id, tipo_variazione, valore_variazione,
             valido_dal, valido_al)
        SELECT 'RVPRM-' || %(sfx)s, 'Promo ricdescprm', a.id, a.uom_id, 'PERCENTUALE', 5,
               script.fn_data_operativa() + 1, script.fn_data_operativa() + 30
          FROM catalogo.articoli a
         WHERE a.id = (SELECT articolo_id FROM _art)
        RETURNING id
    )
    SELECT id AS promo_id FROM ins
    """,
    # ── Il gruppo di competenza: preventivo → commessa → attivita' ─────────
    # Un preventivo spinto in una commessa: il `riferimento` del gruppo e' il
    # NUMERO del documento, distinto dal codice commessa (un gruppo senza
    # documento avrebbe riferimento = codice commessa, e le due colonne non
    # sarebbero provate separatamente).
    # ⭐ Il preventivo NASCE in bozza (lo stato lo mette il DB, BB
    #    `script.trgfn_doc_stato_iniziale`) e va a EMESSO per la matrice, sotto
    #    i guard veri: brief-modello-documento-vendita N-1. L'emissione
    #    chiede almeno una riga attiva (guard di transizione, giro 6 §8.5): la
    #    riga e il passaggio li fa il builder, non una copia qui.
    """
    CREATE TEMP TABLE _prev AS
    WITH ins AS (
        INSERT INTO vendite.preventivi
            (numero, rev, billing_account_id, istanza_utility_id, utility_id,
             validita_dal, validita_al, valuta_id, data,
             fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
        SELECT 'RVPRV-' || %(sfx)s, 0, m.billing_account_id, m.istanza_utility_id, m.utility_id,
               DATE '2083-02-01', DATE '2083-12-31', r.valuta_id, DATE '2083-02-01',
               false, false, '{"test_scope": "be_ricerca_liste_vendite"}'::jsonb, m.emittente_fiscale_id
          FROM _mondo m, _refs r
        RETURNING id, uid, numero
    )
    SELECT * FROM ins
    """,
    "SELECT dbops.fn_pgtap_crea_preventivo_con_righe("
    "'be_ricerca_liste_vendite', 'EMESSO', p_preventivo_id => (SELECT id FROM _prev))",
    """
    CREATE TEMP TABLE _comm AS
    SELECT vendite.fn_get_or_create_commessa(
        p_billing_account_id     => (SELECT billing_account_id FROM _mondo),
        p_utility_id             => (SELECT utility_id FROM _mondo),
        p_tipo_commessa          => 'AUTO',
        p_policy_fatturazione    => 'DA_DOCUMENTO',
        p_fatturazione_immediata => false,
        p_priorita_operativa     => 'NORMALE',
        p_competenza_dal         => DATE '2083-02-01',
        p_competenza_al          => DATE '2083-02-28',
        p_meta                   => '{"test_scope": "be_ricerca_liste_vendite"}'::jsonb,
        p_force_new              => true
      ) AS commessa_id
    """,
    """
    SELECT vendite.fn_link_commessa_sorgente(
        p_commessa_id      => (SELECT commessa_id FROM _comm),
        p_sorgente_tipo_id => (SELECT src_preventivo_id FROM _refs),
        p_sorgente_chiave  => (SELECT uid::text FROM _prev),
        p_meta             => '{"test_scope": "be_ricerca_liste_vendite"}'::jsonb
    )
    """,
    """
    SELECT * FROM vendite.fn_upsert_commessa_attivita(
        p_commessa_id                   => (SELECT commessa_id FROM _comm),
        -- ⛔ La chiave nomina il documento della provenienza (giro C.3 di
        --    brief-db-sorgente-documento-e-riga): la compone il dominio, e
        --    l'etichetta del test ne e' il suffisso.
        p_segment_key                   => (script.fn_segment_key(
                                               'PREVENTIVO', (SELECT uid::text FROM _prev))
                                            || ':SEG-RICVEN-1')::varchar,
        p_articolo_id                   => (SELECT articolo_id FROM _art),
        p_istanza_utility_id            => (SELECT istanza_utility_id FROM _mondo),
        p_data_attivita                 => DATE '2083-02-15',
        p_uom_id                        => (SELECT uom_id FROM catalogo.articoli
                                             WHERE id = (SELECT articolo_id FROM _art)),
        p_quantita                      => 1.000000,
        p_competenza_mese               => DATE '2083-02-01',
        p_competenza_dal                => DATE '2083-02-01',
        p_competenza_al                 => DATE '2083-02-28',
        p_prezzo_snapshot               => 100.00,
        p_prezzo_base_snapshot          => NULL,
        p_origine_prezzo                => NULL,
        p_tipo_variazione_applicata     => NULL,
        p_valore_variazione_applicata   => NULL,
        p_promo_id                      => NULL,
        p_contratto_id                  => NULL,
        p_categoria_cliente_id_snapshot => NULL,
        p_classe_utenza_id_snapshot     => NULL,
        p_tipo_doc_fiscale_id           => (SELECT tipo_doc_fiscale_id FROM _refs),
        p_valuta_id                     => (SELECT valuta_id FROM _refs),
        p_stato_approvazione            => 'APPROVATA',
        p_stato_emissione               => 'NON_EMESSA',
        p_sorgente_tipo_id              => (SELECT src_preventivo_id FROM _refs),
        p_sorgente_chiave               => (SELECT uid::text FROM _prev),
        p_tipo_movimento                => 'NORMALE',
        p_meta                          => '{"test_scope": "be_ricerca_liste_vendite"}'::jsonb
    )
    """,
    # ── Le righe di un contratto (lista 103, 2026-09-30) ───────────────────
    # Senza listino: la sola riga e' l'AGGIUNTA sull'articolo costruito, e la
    # funzione sorgente la restituisce con chiave `A:<id>`.
    """
    CREATE TEMP TABLE _cnt AS
    WITH ins AS (
        INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
               valido_dal, valido_al)
        SELECT 'RVCNT-' || %(sfx)s, m.billing_account_id, m.istanza_utility_id, m.utility_id,
               script.fn_data_operativa(), script.fn_data_operativa() + 365
          FROM _mondo m
        RETURNING id
    )
    SELECT id AS contratto_id FROM ins
    """,
    """
    CREATE TEMP TABLE _cnt_riga AS
    WITH ins AS (
        -- Erogazione e fonte VUOTE: le eredita dall'articolo (B-R2 di
        -- brief-db-offerta-emissione-ed-erogazione). Scritte a mano, il guard
        -- del perimetro le giudicherebbe sulla tipologia, e qui sono incidentali.
        -- ⭐ La quantita' solo se la fonte ereditata e' FISSA: con una fonte a
        -- valle il DB la rifiuta (E_RIGA_QUANTITA_CON_FONTE_A_VALLE, §E.2), e
        -- quale fonte l'articolo porti lo dice la sede unica, non il test.
        INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
               quantita, qta_operativa, uom_operativa_id)
        SELECT (SELECT contratto_id FROM _cnt), a.id, 'AGGIUNTA', 40.00, q.qta, q.qta, a.uom_id
          FROM catalogo.articoli a
          CROSS JOIN LATERAL (
              SELECT CASE WHEN ae.fonte_quantita_attesa = 'FISSA' THEN 1 END AS qta
                FROM vendite.fn_articolo_erogazioni(a.id) ae
               WHERE ae.e_default
          ) q
         WHERE a.id = (SELECT articolo_id FROM _art)
        RETURNING id
    )
    SELECT id AS riga_id FROM ins
    """,
    # ── Le righe di un'offerta (lista 106, 2026-10-05) ─────────────────────
    # Gemella della 103 sulla stessa funzione comune. L'offerta vuole un
    # listino (`listino_id` NOT NULL): quello del mondo, in vigore oggi, quindi
    # la riga e' quella DEL LISTINO sull'articolo costruito, con chiave
    # `L:<articolo>:<uom>` — l'altra gamba della funzione rispetto al contratto.
    """
    CREATE TEMP TABLE _off AS
    WITH ins AS (
        INSERT INTO vendite.offerte_commerciali (emittente_fiscale_id, billing_account_id,
               istanza_utility_id, utility_id, listino_id, validita_dal)
        SELECT m.emittente_fiscale_id, m.billing_account_id, m.istanza_utility_id, m.utility_id,
               (SELECT listino_id FROM _lst), script.fn_data_operativa()
          FROM _mondo m
        RETURNING id
    )
    SELECT id AS offerta_id FROM ins
    """,
    # ── La famiglia di documento: SEED, se ne ritocca una riga ─────────────
    # ⭐ `codice` e' la colonna nuova (changeSet `20260924-03…-07`), mutabile:
    #    e' quella che la lista mostra e cerca al posto del `codice_interno`.
    """
    CREATE TEMP TABLE _fam AS
    WITH upd AS (
        UPDATE vendite.famiglie_documento f
           SET codice = 'RVFAM-' || %(sfx)s,
               descrizione = 'Famiglia ricdescfam',
               prefisso_default = 'RVX/'
         WHERE f.id = (SELECT min(id) FROM vendite.famiglie_documento)
        RETURNING f.id
    )
    SELECT id AS famiglia_id FROM upd
    """,
)


class RicercaListeVenditeDbTests(unittest.TestCase):
    """Le cinque liste di vendite del passo 7 (brief-be-ricerca-full-liste-
    residue §7-bis e §3.5 del brief DB): ogni colonna che il catalogo accende
    trova la riga costruita, dal repository."""

    @classmethod
    def setUpClass(cls) -> None:
        richiedi_db_provvisto("ui.fn_lista_colonne_ricerca_full(character varying)")

    # Scopo: costruisce il mondo e prova le cinque liste, in una transazione
    #        SEMPRE annullata.
    # ⚠️ I valori cercati sono PEZZI del valore mostrato (`ricdesclst` dentro
    #    «Listino ricdesclst»): la ricerca e' un `ILIKE %…%`, e un pezzo che
    #    sta solo li' dice che la colonna giusta e' stata cercata.
    def test_la_ricerca_trova_ogni_colonna_accesa(self):
        sfx = uuid4().hex[:8].upper()
        try:
            with transaction.atomic(), connection.cursor() as cur:
                for passo in _FIXTURE:
                    cur.execute(passo, {"sfx": sfx})
                cur.execute("SELECT listino_id, listino_versione_id FROM _lst")
                listino, versione = cur.fetchone()
                cur.execute("SELECT riga_id FROM _riga")
                riga = cur.fetchone()[0]
                cur.execute("SELECT promo_id FROM _promo")
                promo = cur.fetchone()[0]
                cur.execute("SELECT famiglia_id FROM _fam")
                famiglia = cur.fetchone()[0]
                cur.execute(
                    "SELECT g.gruppo_key, g.commessa_codice, g.ba_codice_fatturazione, g.id_fiscale "
                    "  FROM vendite.vw_dash_competenza_gruppi g "
                    " WHERE g.commessa_id = (SELECT commessa_id FROM _comm)"
                )
                gruppi = cur.fetchall()
                # Il caso si e' formato davvero: una riga sola, e il cliente
                # di fatturazione valorizzato (senza, due colonne su cinque non
                # avrebbero niente da trovare e il test lo direbbe tardi).
                self.assertEqual(len(gruppi), 1, gruppi)
                gruppo_key, commessa_codice, ba_codice, id_fiscale = gruppi[0]
                self.assertIsNotNone(ba_codice)
                self.assertIsNotNone(id_fiscale)

                verifica_ricerca_colonna_per_colonna(
                    self, cur, "vendite.listini", listino,
                    {"codice": f"RVLST-{sfx}", "descrizione": "ricdesclst"},
                    lambda t: ListiniRepository().list_listini(
                        utility_id=None, tipologia_id=None, attivo=None, search=t,
                        order_by="codice", order_dir="asc", limit=200, offset=0,
                    )[0],
                )
                # Le versioni del listino (2026-10-31): il codice lo da' la
                # fabbrica, lo si legge (una versione ATTIVA non lo cambia).
                cur.execute("SELECT codice_versione FROM vendite.listini_versioni WHERE id = %s", [versione])
                codice_versione = cur.fetchone()[0]
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "vendite.listini_versioni", versione,
                    {"codice_versione": codice_versione},
                    lambda t: ListiniRepository().list_versioni_pagina(listino, search=t, limit=200)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "vendite.listini_righe", riga,
                    {"articolo_codice": f"RVART-{sfx}", "articolo_descrizione": "ricdescart"},
                    lambda t: ListiniRepository().list_righe(
                        listino, versione, search=t, attivo=None, limit=200,
                    )[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "vendite.promo_articoli", promo,
                    {"codice": f"RVPRM-{sfx}", "descrizione": "ricdescprm",
                     "articolo_codice": f"RVART-{sfx}", "articolo_descrizione": "ricdescart"},
                    lambda t: PromoArticoliRepository().list_promo(search=t, limit=200)[0],
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "vendite.dash_competenza_gruppi", gruppo_key,
                    {"riferimento": f"RVPRV-{sfx}", "cliente_display": "ricerca liste vendite",
                     "commessa_codice": commessa_codice, "ba_codice_fatturazione": ba_codice,
                     "id_fiscale": id_fiscale},
                    lambda t: VenditeRepository().list_dash_competenza_gruppi(
                        competenza_mese=_COMPETENZA, stadio=None, search=t, limit=200, offset=0,
                    )[0],
                    chiave="gruppo_key",
                )
                # ⭐ Il riepilogo segue la stessa ricerca della lista (CTE
                #    `filtrato`, colonne dichiarate da `_where_gruppi_filtri`):
                #    se la CTE `base` non si portasse dietro le colonne, qui
                #    sarebbe un 500, non un numero sbagliato.
                acc = VenditeRepository().get_dash_competenza_gruppi_accessori(
                    competenza_mese=_COMPETENZA, stadio=None, search=f"RVPRV-{sfx}",
                )
                self.assertEqual(acc["riepilogo"]["n_gruppi"], 1)
                cur.execute("SELECT c.contratto_id, r.riga_id FROM _cnt c, _cnt_riga r")
                contratto, riga_contratto = cur.fetchone()
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "vendite.contratto_righe", f"A:{riga_contratto}",
                    {"articolo_codice": f"RVART-{sfx}", "articolo_descrizione": "ricdescart"},
                    lambda t: ContrattoRigheListaRepository().list_righe_pagina(
                        contratto, search=t, limit=200,
                    )[0],
                    chiave="riga_key",
                )
                cur.execute(
                    "SELECT o.offerta_id, 'L:' || a.id || ':' || a.uom_id"
                    " FROM _off o, catalogo.articoli a WHERE a.id = (SELECT articolo_id FROM _art)"
                )
                offerta, riga_offerta = cur.fetchone()
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "vendite.offerta_righe", riga_offerta,
                    {"articolo_codice": f"RVART-{sfx}", "articolo_descrizione": "ricdescart"},
                    lambda t: OffertaRigheListaRepository().list_righe_pagina(
                        offerta, search=t, limit=200,
                    )[0],
                    chiave="riga_key",
                )
                verifica_ricerca_colonna_per_colonna(
                    self, cur, "vendite.famiglie_documento", famiglia,
                    {"codice": f"RVFAM-{sfx}", "descrizione": "ricdescfam", "prefisso_default": "RVX/"},
                    lambda t: FamiglieDocumentoRepository().list_famiglie(search=t, limit=200)[0],
                )
                raise Annulla
        except Annulla:
            pass
