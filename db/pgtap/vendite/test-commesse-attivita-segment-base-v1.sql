-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: vendite.commesse_attivita.segment_base — la base della chiave di
--       segmento, e le due funzioni che entrano da li'.
--       Brief: brief-db-segment-base-commesse-attivita (P-4);
--       changeSet 20261010-80 / -81 / -82.
--
-- Elenco test (plan 6):
--  1) la colonna e' GENERATA STORED, NOT NULL, varchar(128)
--  2) ⭐ la base e' cio' che precede il primo '#', su chiavi COSTRUITE: esatta,
--     componente #CMP, rettifica per componente #RET:…#CMP:…, suffisso ignoto
--  3) ⭐ segue segment_key: cambiata la chiave, la base si ricalcola da sola
--  4) l'indice ix_commesse_attivita_segment_base esiste, btree, sulla colonna
--  5) ⭐ pin di FORMA: fn_af_merce_per_riga entra dall'uguaglianza su
--     segment_base
--  6) ⭐ pin di FORMA: fn_get_stato_push_segment entra dall'uguaglianza su
--     segment_base, con la base calcolata sul PARAMETRO
--
-- Scopo:
--  - 5 e 6 sono la ragione del file. Con le chiavi come parametro (piano
--    generico) l'intervallo per prefisso su segment_key era stimato all'11 %
--    della tabella e perdeva contro la scansione intera sotto la policy
--    (misura dbdev come app, 2026-10-10: 31 ms contro 3 ms). L'uguaglianza su
--    una colonna e' leakproof e ha statistiche vere. Un REPLACE che la perde
--    restituisce le STESSE righe — nessun test di comportamento se ne accorge
--    — e torna lento: per questo si pinna la forma.
--  - L'equivalenza dei risultati la provano i casi costruiti dei pgTAP delle
--    due funzioni (script/test-fn-get-stato-push-segment-v1: vicino numerico,
--    suffisso ignoto; vendite/test-fn-af-merce-per-riga-chiusura-v1), che
--    restano invariati: l'uguaglianza si AGGIUNGE al predicato di prima, che
--    la implica.
--  - ⭐ il mondo e' COSTRUITO dai builder di dbops: gira identico su dbdev e
--    su un database da zero.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- ============================================================
-- 1) La colonna
-- ============================================================
SELECT is(
  (SELECT a.attgenerated::text || '|' || a.attnotnull::text || '|' || format_type(a.atttypid, a.atttypmod)
     FROM pg_attribute a
    WHERE a.attrelid = 'vendite.commesse_attivita'::regclass
      AND a.attname = 'segment_base' AND NOT a.attisdropped),
  's|true|character varying(128)',
  '1) segment_base e'' generata STORED, NOT NULL, varchar(128)');

-- ============================================================
-- Il mondo si COSTRUISCE, non si cerca.
-- ============================================================
CREATE TEMP TABLE tmp_cli_sb AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_segment_base');

CREATE TEMP TABLE tmp_refs_sb AS
SELECT
  c.billing_account_id,
  c.utility_id,
  c.istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-SB-ART', false)                                         AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)   AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                  AS valuta_id
FROM tmp_cli_sb c;

CREATE TEMP TABLE tmp_com_sb AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_sb),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_sb),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-08-01',
  p_competenza_al          => DATE '2026-08-31',
  p_meta                   => jsonb_build_object('test_scope','pgtap_segment_base'),
  p_force_new              => true) AS commessa_id;

-- Un prefisso di segmento INVENTATO: la colonna non dereferenzia nulla.
CREATE TEMP TABLE tmp_seg_sb AS SELECT 'PGTAPSB:' || gen_random_uuid()::text AS pre;

-- Helper: un'attivita' con segment_key esplicita, in BOZZA (cosi' il CHECK
-- del tipo documento emittibile non pretende nulla). Restituisce l'id.
CREATE OR REPLACE FUNCTION pg_temp.sb_mk(p_segment vendite.commesse_attivita.segment_key%TYPE)
RETURNS vendite.commesse_attivita.id%TYPE AS $$
DECLARE
  r    RECORD;
  v_id vendite.commesse_attivita.id%TYPE;
BEGIN
  SELECT * INTO r FROM tmp_refs_sb;
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
    competenza_mese, competenza_dal, competenza_al, tipo_doc_fiscale_id, valuta_id,
    prezzo_snapshot, pricing_mode, stato_approvazione, stato_emissione,
    sorgente_tipo_id, sorgente_uid)   -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
  VALUES (
    (SELECT commessa_id FROM tmp_com_sb), p_segment, r.articolo_id, r.istanza_utility_id,
    DATE '2026-08-15', r.uom_id, 1,
    DATE '2026-08-01', DATE '2026-08-01', DATE '2026-08-31',
    r.tipo_doc_fiscale_id, r.valuta_id, 10.0,
    'FIXED', 'BOZZA', 'NON_EMESSA',
    (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'), (SELECT commessa_id FROM tmp_com_sb)::text)
  RETURNING id INTO v_id;
  RETURN v_id;
END $$ LANGUAGE plpgsql;

CREATE TEMP TABLE tmp_att_sb AS
SELECT x.suffisso, pg_temp.sb_mk((SELECT pre FROM tmp_seg_sb) || x.suffisso) AS id
  FROM (VALUES (':R:4'), (':R:6#CMP:c1'), (':R:8#RET:1#CMP:c1'), (':R:11#FOO:1')) x(suffisso);

-- ============================================================
-- 2) La base, su chiavi costruite
-- ============================================================
SELECT results_eq(
  $q$SELECT t.suffisso, ca.segment_base::text
       FROM tmp_att_sb t JOIN vendite.commesse_attivita ca ON ca.id = t.id
      ORDER BY t.suffisso$q$,
  $q$SELECT x.suffisso, (SELECT pre FROM tmp_seg_sb) || x.base
       FROM (VALUES (':R:11#FOO:1', ':R:11'), (':R:4', ':R:4'),
                    (':R:6#CMP:c1', ':R:6'), (':R:8#RET:1#CMP:c1', ':R:8')) x(suffisso, base)
      ORDER BY x.suffisso$q$,
  '2) segment_base e'' cio'' che precede il primo #: esatta, #CMP, #RET…#CMP, suffisso ignoto');

-- ============================================================
-- 3) Segue la chiave
-- ============================================================
UPDATE vendite.commesse_attivita
   SET segment_key = (SELECT pre FROM tmp_seg_sb) || ':R:44#CMP:c9'
 WHERE id = (SELECT id FROM tmp_att_sb WHERE suffisso = ':R:4');

SELECT is(
  (SELECT segment_base::text FROM vendite.commesse_attivita
    WHERE id = (SELECT id FROM tmp_att_sb WHERE suffisso = ':R:4')),
  (SELECT pre FROM tmp_seg_sb) || ':R:44',
  '3) cambiata segment_key, segment_base si ricalcola da sola (generata, nessuno la scrive)');

-- ============================================================
-- 4) L'indice
-- ============================================================
SELECT is(
  (SELECT am.amname || '|' || pg_get_indexdef(i.indexrelid, 1, true) || '|' || i.indisunique::text
     FROM pg_index i
     JOIN pg_class c ON c.oid = i.indexrelid
     JOIN pg_am am ON am.oid = c.relam
    WHERE i.indexrelid = 'vendite.ix_commesse_attivita_segment_base'::regclass),
  'btree|segment_base|false',
  '4) ix_commesse_attivita_segment_base: btree non unico su segment_base');

-- ============================================================
-- 5-6) La forma delle due funzioni. pg_get_functiondef di un BEGIN ATOMIC
--      stampa il corpo deparsato, con gli alias della query.
-- ============================================================
SELECT ok(
  (SELECT d ~ 'ca\.segment_base\)?::text = \(?s\.k\)?::text'
     FROM pg_get_functiondef('vendite.fn_af_merce_per_riga(character varying[])'::regprocedure) AS d),
  '5) fn_af_merce_per_riga entra dall''uguaglianza ca.segment_base = s.k (leakproof, indicizzata)');

SELECT ok(
  (SELECT d ~ 'ca\.segment_base\)?::text = split_part\('
     FROM pg_get_functiondef('script.fn_get_stato_push_segment(character varying)'::regprocedure) AS d),
  '6) fn_get_stato_push_segment entra dall''uguaglianza ca.segment_base = split_part(<parametro>, ''#'', 1)');

SELECT * FROM finish();
ROLLBACK;
