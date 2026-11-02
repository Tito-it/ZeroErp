-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): gli ordini D (DRAFT) e E (ANNULLATO) da dbops.fn_pgtap_crea_ordine_con_righe (5 x 15, data 2026-07-08); il BA e' costruito, quindi via i ripieghi «OR push_ba_id IS NULL» (e «stato ANNULLATO assente»: il builder solleva) e le colonne dei riferimenti rimaste senza lettori.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): le bolle da ordine (A, B, C) dal builder dbops.fn_pgtap_crea_ddt_da_ordine, col trigger e lo stato finale del caso; restano a mano gli ordini D (DRAFT) e E (ANNULLATO), che non hanno bolla.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_ordini_da_pushare — fix «orfano da push»
--       (decoupling fatturazione <-> spedizione, rev 20260710-01)
-- Piano: piano-db-fix-orfano-push-ordine-confermato.md §4.2
-- Brief: brief-db-ddt-vendita-evasione-e-stati §16 (casi 7-10)
-- ------------------------------------------------------------
-- Indice test (1..10):
--  1) riferimenti minimi disponibili (BA pushabile CONFERMATO)
--  2) sanity: evasione full -> ordine EVASO (proiezione C5 invariata)
--  3) caso 7  — orfano recuperato: ordine EVASO trigger CONFERMATO in fn_list (>=1)
--  4) caso 8  — XOR: DDT ordine-sourced (src_trigger=CONFERMATO) a SPEDITO
--               NON compare in fn_list_ddt_da_pushare
--  5) caso 10 — no doppione: dopo push simulato (commessa+attivita EMESSA)
--               la re-list ritorna 0
--  6) caso 7b — evasione parziale: ordine PARZIALMENTE_EVASO in fn_list (>=1)
--  7) caso 9  — non-regressione SPEDITO: ordine trigger SPEDITO evaso
--               NON compare in fn_list_ordini_da_pushare
--  8) caso 9b — il DDT dell'ordine trigger SPEDITO (a SPEDITO) compare
--               in fn_list_ddt_da_pushare
--  9) DRAFT escluso (non-regressione predicato stato)
-- 10) ANNULLATO escluso (predicato stato)
-- ------------------------------------------------------------
-- Nota fixture: trgfn_ordini_normalize eredita fatturazione_trigger dal
--   billing_account su INSERT: il BA costruito ha fatturazione_ordini =
--   'CONFERMATO'; le bolle A, B, C dichiarano comunque al builder il trigger
--   del caso (lo scrive sull'ordine in bozza).

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- ============================================================
-- Riferimenti minimi: il mondo COSTRUITO, dal DB solo il catalogo di seed
-- ============================================================
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti). Prima il BA pushabile, il ruolo e l'articolo si
--   pescavano col LIMIT 1: su zeroerp_ci erano NULL, la fixture restava vuota e
--   la riga di ddt_indirizzi (ddt_id NULL) moriva sulla RLS. Ora un'azienda
--   nuova col suo operatore (contesto aperto su di lui), il cliente legato a
--   lei (dbops.fn_pgtap_crea_mondo_cliente) e un articolo merce non gestito.
--   Il BA pushabile e' quello costruito, con fatturazione_ordini = 'CONFERMATO'
--   dichiarato con un UPDATE (oggi e' anche il default della colonna).
--   Modello: test-ddt-magazzino-testata-v1.
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP list ordini v3');
UPDATE anagrafiche.billing_account SET fatturazione_ordini = 'CONFERMATO'
 WHERE id = (SELECT billing_account_id FROM _m);

CREATE TEMP TABLE tmp_refs_v3 AS
SELECT
  m.billing_account_id                               AS push_ba_id,
  m.cliente_soggetto_ruolo_id                        AS soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-LIST-ORD-V3', false) AS articolo_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'CONFERMATO' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.codice_interno = 'EMESSO' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1)     AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s
    WHERE s.codice_interno = 'SPEDITO' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1)    AS stato_ddt_spedito_id
FROM _m m;

SELECT ok(
  (SELECT push_ba_id IS NOT NULL
      AND soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_ord_conf_id IS NOT NULL
      AND stato_ddt_emesso_id IS NOT NULL
      AND stato_ddt_spedito_id IS NOT NULL
   FROM tmp_refs_v3),
  '1) riferimenti minimi disponibili (BA pushabile CONFERMATO)'
);

-- ============================================================
-- FIXTURE A: ordine trigger CONFERMATO, evasione FULL (orfano)
-- ============================================================
-- Il builder: ordine 10 @30 trigger CONFERMATO, evasione FULL (e' il gesto che
-- PRIMA del fix chiudeva la finestra di push), bolla portata a SPEDITO per il
-- caso 8 (il trigger e' CONFERMATO: la bolla non diventa una seconda sorgente).
CREATE TEMP TABLE tmp_a3 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('list ordini v3 A', 'SPEDITO',
    (SELECT push_ba_id FROM tmp_refs_v3), p_quantita => 10, p_prezzo => 30,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_v3), p_fatturazione_trigger => 'CONFERMATO');
CREATE TEMP TABLE tmp_ord_a3 AS SELECT ordine_id AS id FROM tmp_a3;
CREATE TEMP TABLE tmp_ddt_a3 AS SELECT ddt_id FROM tmp_a3;

-- 2) sanity: proiezione stato C5 invariata (full -> EVASO)
SELECT ok(
  (SELECT sdo.codice_interno = 'EVASO'
     FROM vendite.ordini o
     JOIN config.stati_doc_ordini sdo ON sdo.id = o.stato_doc_ordine_id
    WHERE o.id = (SELECT id FROM tmp_ord_a3)),
  '2) sanity: evasione full -> ordine EVASO (C5 invariata)'
);

-- 3) caso 7 — ORFANO RECUPERATO: l'ordine EVASO trigger CONFERMATO
--    (mai pushato) e' di nuovo eleggibile al push
SELECT ok(
  (SELECT count(*) >= 1
     FROM vendite.fn_list_ordini_da_pushare(
            p_ordine_id => (SELECT id FROM tmp_ord_a3))),
  '3) caso 7: ordine EVASO trigger CONFERMATO eleggibile al push (orfano recuperato)'
);

-- 4) caso 8 — XOR preservato: il DDT ordine-sourced (src_trigger=CONFERMATO)
--    portato a SPEDITO NON diventa una seconda sorgente di push
SELECT ok(
  (SELECT count(*) = 0
     FROM vendite.fn_list_ddt_da_pushare(
            p_ddt_id => (SELECT ddt_id FROM tmp_ddt_a3))),
  '4) caso 8: DDT src_trigger=CONFERMATO a SPEDITO escluso da fn_list_ddt_da_pushare (XOR)'
);

-- 5) caso 10 — NO DOPPIONE: simulazione push a livello DB (commessa +
--    attivita con stato_emissione=EMESSA) -> la re-list torna 0.
--    E' la cintura che sostituisce la transizione forzata ->EVASO del BE.
CREATE TEMP TABLE tmp_pushrow_a3 AS
SELECT * FROM vendite.fn_list_ordini_da_pushare(
         p_ordine_id => (SELECT id FROM tmp_ord_a3));

CREATE TEMP TABLE tmp_commessa_a3 AS
SELECT vendite.fn_get_or_create_commessa(
         p_billing_account_id          => pr.billing_account_id,
         p_utility_id                  => pr.utility_id,
         p_competenza_dal              => pr.competenza_dal,
         p_competenza_al               => pr.competenza_al,
         p_meta => jsonb_build_object('test_scope','pgtap_list_ordini_v3')
       ) AS commessa_id
  FROM tmp_pushrow_a3 pr
 ORDER BY pr.segment_key
 LIMIT 1;

SELECT vendite.fn_upsert_commessa_attivita(
         p_commessa_id                   => c.commessa_id,
         p_segment_key                   => pr.segment_key,
         p_articolo_id                   => pr.articolo_id,
         p_istanza_utility_id            => pr.istanza_utility_id,
         p_data_attivita                 => pr.data_attivita,
         p_uom_id                        => pr.uom_id,
         p_quantita                      => pr.quantita,
         p_competenza_mese               => pr.competenza_mese,
         p_competenza_dal                => pr.competenza_dal,
         p_competenza_al                 => pr.competenza_al,
         p_prezzo_snapshot               => pr.prezzo_snapshot,
         p_prezzo_base_snapshot          => NULL,
         p_origine_prezzo                => NULL,
         p_tipo_variazione_applicata     => NULL,
         p_valore_variazione_applicata   => NULL,
         p_promo_id                      => NULL,
         p_contratto_id                  => NULL,
         p_categoria_cliente_id_snapshot => NULL,
         p_classe_utenza_id_snapshot     => NULL,
         p_qta_operativa                 => pr.qta_operativa,
         p_uom_operativa_id              => pr.uom_operativa_id,
         p_factor_to_base                => pr.factor_to_base,
         p_tipo_doc_fiscale_id           => pr.tipo_doc_fiscale_id,
         p_valuta_id                     => pr.valuta_id,
         p_prezzo_bloccato               => pr.prezzo_bloccato,
         p_pricing_mode                  => pr.pricing_mode,
         p_stato_emissione               => 'EMESSA',
         p_sorgente_tipo_id              => pr.sorgente_tipo_id,
         p_sorgente_uid                  => pr.sorgente_uid,
         p_meta                          => pr.meta)
  FROM tmp_pushrow_a3 pr, tmp_commessa_a3 c;

SELECT ok(
  (SELECT count(*) = 0
     FROM vendite.fn_list_ordini_da_pushare(
            p_ordine_id => (SELECT id FROM tmp_ord_a3))),
  '5) caso 10: dopo push simulato (EMESSA) la re-list = 0 (no doppione)'
);

-- ============================================================
-- FIXTURE B: ordine trigger CONFERMATO, evasione PARZIALE
-- ============================================================
-- Il builder: ordine 10 @20 trigger CONFERMATO, evasione parziale 4/10 ->
-- PARZIALMENTE_EVASO; la bolla resta in bozza (il caso misura l'ordine).
CREATE TEMP TABLE tmp_b3 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('list ordini v3 B', 'DRAFT',
    (SELECT push_ba_id FROM tmp_refs_v3), p_quantita => 10, p_prezzo => 20,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_v3), p_fatturazione_trigger => 'CONFERMATO',
    p_qta_da_evadere => 4);
CREATE TEMP TABLE tmp_ord_b3 AS SELECT ordine_id AS id FROM tmp_b3;

-- 6) caso 7b — anche il PARZIALMENTE_EVASO resta eleggibile
SELECT ok(
  ((SELECT sdo.codice_interno = 'PARZIALMENTE_EVASO'
      FROM vendite.ordini o
      JOIN config.stati_doc_ordini sdo ON sdo.id = o.stato_doc_ordine_id
     WHERE o.id = (SELECT id FROM tmp_ord_b3))
   AND (SELECT count(*) >= 1
          FROM vendite.fn_list_ordini_da_pushare(
                 p_ordine_id => (SELECT id FROM tmp_ord_b3)))),
  '6) caso 7b: ordine PARZIALMENTE_EVASO trigger CONFERMATO eleggibile al push'
);

-- ============================================================
-- FIXTURE C: ordine trigger SPEDITO (non-regressione XOR lato DDT)
-- trgfn_ordini_normalize e' INSERT-only: il trigger si aggiorna DOPO
-- ============================================================
-- Il builder: ordine 5 @15 trigger SPEDITO, evaso, bolla a SPEDITO (caso 9b).
CREATE TEMP TABLE tmp_c3 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('list ordini v3 C', 'SPEDITO',
    (SELECT push_ba_id FROM tmp_refs_v3), p_quantita => 5, p_prezzo => 15,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_v3), p_fatturazione_trigger => 'SPEDITO');
CREATE TEMP TABLE tmp_ord_c3 AS SELECT ordine_id AS id FROM tmp_c3;
CREATE TEMP TABLE tmp_ddt_c3 AS SELECT ddt_id FROM tmp_c3;

-- 7) caso 9 — l'ordine trigger SPEDITO evaso NON pusha (filtro trigger)
SELECT ok(
  (SELECT count(*) = 0
     FROM vendite.fn_list_ordini_da_pushare(
            p_ordine_id => (SELECT id FROM tmp_ord_c3))),
  '7) caso 9: ordine trigger SPEDITO evaso escluso da fn_list_ordini_da_pushare'
);

-- 8) caso 9b — per il trigger SPEDITO pusha il DDT (invariato)
SELECT ok(
  (SELECT count(*) >= 1
     FROM vendite.fn_list_ddt_da_pushare(
            p_ddt_id => (SELECT ddt_id FROM tmp_ddt_c3))),
  '8) caso 9b: DDT dell''ordine trigger SPEDITO (a SPEDITO) eleggibile in fn_list_ddt_da_pushare'
);

-- ============================================================
-- 9-10) Predicato stato: DRAFT e ANNULLATO restano esclusi
-- ============================================================
CREATE TEMP TABLE tmp_ord_d3 AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('list ordini v3 D', 'DRAFT',
    p_billing_account_id => (SELECT push_ba_id FROM tmp_refs_v3),
    p_quantita => 5, p_prezzo => 15,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_v3),
    p_data_ordine => DATE '2026-07-08');

SELECT ok(
  (SELECT count(*) = 0
     FROM vendite.fn_list_ordini_da_pushare(
            p_ordine_id => (SELECT ordine_id FROM tmp_ord_d3))),
  '9) DRAFT escluso dal push (non-regressione predicato stato)'
);

-- L'annullo per la matrice, sotto i guard veri: lo fa il builder.
CREATE TEMP TABLE tmp_ord_e3 AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('list ordini v3 E', 'ANNULLATO',
    p_billing_account_id => (SELECT push_ba_id FROM tmp_refs_v3),
    p_quantita => 5, p_prezzo => 15,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_v3),
    p_data_ordine => DATE '2026-07-08');

SELECT ok(
  (SELECT count(*) = 0
     FROM vendite.fn_list_ordini_da_pushare(
            p_ordine_id => (SELECT ordine_id FROM tmp_ord_e3))),
  '10) ANNULLATO escluso dal push (predicato stato)'
);
SELECT * FROM finish();
ROLLBACK;
