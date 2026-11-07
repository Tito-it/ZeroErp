-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Una grammatica sola per i tipi di documento — lotto 2b: l'origine
--   dell'ordine (vendite.ordini.documento_origine_tipo), la destinazione della
--   natura (config.nature_vendita.destinazione_tipo) e l'origine dei legami
--   (vendite.fn_documento_legami) parlano il codice della sorgente. Il
--   vocabolario e' config.sorgenti, per vincolo: niente CHECK coi codici scritti
--   a mano (G-3).
--   Brief: brief-db-grammatica-unica-documenti §12 (G-1, G-3 di Tid).
--   ChangeSet: 20261019-87 … -99.
--
-- Elenco test (plan 12):
--  1) ordini.documento_origine_tipo: FK verso config.sorgenti(codice_interno)
--  2) nature_vendita.destinazione_tipo: FK verso config.sorgenti(codice_interno)
--  3) nessun CHECK enumera i codici sulle due colonne
--  4) le due colonne sono lunghe quanto config.sorgenti.codice_interno
--  5) la natura MERCE va in ORDINE_VENDITA (il seed parla il codice della
--       sorgente)
--  6) l'unicita' «un'offerta, un ordine vivo» nomina OFFERTA_COMMERCIALE
--  7) nessuna vista e nessuna funzione di vendite, catalogo, script confronta
--       una delle due colonne col codice corto (OFFERTA, ORDINE)
--  8) un ordine con origine OFFERTA (il codice corto) e' rifiutato dalla FK
--  9) …con OFFERTA_COMMERCIALE passa
-- 10) fn_documento_legami dell'ordine: il legame di provenienza ha origine
--       OFFERTA_COMMERCIALE e punta all'offerta
-- 11) fn_offerta_documenti_vivi dell'offerta: l'ordine, col codice
--       ORDINE_VENDITA
-- 12) la colonna origine di fn_documento_legami e' ancorata al codice della
--       sorgente (character varying, non text)
--
-- ⭐ 8 … 11 costruiscono il caso su un ordine in bozza dello stampo
--   (dbops.fn_pgtap_crea_ordine) e un'offerta vera in bozza (cliente e listino
--   dai builder). rev 2026-11-07 (brief-db-sorgente-documento-e-riga, giro T.3):
--   i due lettori leggono la provenienza (sorgente_*), che il guard unico vuole
--   verso un documento che esiste; prima bastava un id d'offerta inventato nella
--   colonna parallela. Il 9 scrive le due, come i verbi.
-- ⚠️ Il 7 legge il TESTO delle definizioni: vede i confronti scritti sulla
--   colonna (`documento_origine_tipo = 'OFFERTA'`), non quelli su una variabile
--   che ne porta il valore. Per quelli il presidio e' il comportamento (8 … 11 e
--   i pgTAP dei lettori: smistamento del preventivo, legami, onere).
-- ------------------------------------------------------------

BEGIN;

-- Vincoli differiti: scattano a fine istruzione, non al COMMIT che qui non arriva.
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

CREATE OR REPLACE FUNCTION pg_temp.vincolo_violato(p_sql text)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_cst text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME;
        RETURN coalesce(nullif(v_cst, ''), SQLSTATE);
    END;
END;
$fx$;

CREATE TEMP TABLE _col ON COMMIT DROP AS
SELECT * FROM (VALUES
    ('vendite.ordini'::regclass,        'documento_origine_tipo'::name),
    ('config.nature_vendita'::regclass, 'destinazione_tipo'::name)) v(tabella, colonna);

-- 1) e 2) la FK verso le sorgenti, una per colonna
SELECT ok(
    EXISTS (SELECT 1
              FROM pg_constraint c
              JOIN pg_attribute a  ON a.attrelid = c.conrelid  AND a.attnum = c.conkey[1]
              JOIN pg_attribute ar ON ar.attrelid = c.confrelid AND ar.attnum = c.confkey[1]
             WHERE c.contype = 'f'
               AND c.conrelid = 'vendite.ordini'::regclass
               AND a.attname = 'documento_origine_tipo'
               AND c.confrelid = 'config.sorgenti'::regclass
               AND ar.attname = 'codice_interno'),
    '1) ordini.documento_origine_tipo: FK verso config.sorgenti(codice_interno)');

SELECT ok(
    EXISTS (SELECT 1
              FROM pg_constraint c
              JOIN pg_attribute a  ON a.attrelid = c.conrelid  AND a.attnum = c.conkey[1]
              JOIN pg_attribute ar ON ar.attrelid = c.confrelid AND ar.attnum = c.confkey[1]
             WHERE c.contype = 'f'
               AND c.conrelid = 'config.nature_vendita'::regclass
               AND a.attname = 'destinazione_tipo'
               AND c.confrelid = 'config.sorgenti'::regclass
               AND ar.attname = 'codice_interno'),
    '2) nature_vendita.destinazione_tipo: FK verso config.sorgenti(codice_interno)');

-- 3) nessun CHECK coi codici scritti a mano
SELECT is_empty(
    $$SELECT c.conname
        FROM pg_constraint c
        JOIN _col k ON k.tabella = c.conrelid
       WHERE c.contype = 'c'
         AND pg_get_constraintdef(c.oid) LIKE '%' || k.colonna || '%'
         AND pg_get_constraintdef(c.oid) ~ '''[A-Z_]+'''$$,
    '3) nessun CHECK enumera i codici sulle due colonne');

-- 4) la lunghezza del nome (G-3: il vincolo si adegua al nome)
SELECT is_empty(
    $$SELECT k.colonna
        FROM _col k
        JOIN pg_attribute a ON a.attrelid = k.tabella AND a.attname = k.colonna
       WHERE format_type(a.atttypid, a.atttypmod)
             IS DISTINCT FROM (SELECT format_type(s.atttypid, s.atttypmod)
                                 FROM pg_attribute s
                                WHERE s.attrelid = 'config.sorgenti'::regclass
                                  AND s.attname = 'codice_interno')$$,
    '4) le due colonne sono lunghe quanto config.sorgenti.codice_interno');

-- 5) il seed
SELECT is(
    (SELECT nv.destinazione_tipo::text FROM config.nature_vendita nv WHERE nv.codice_interno = 'MERCE'),
    'ORDINE_VENDITA',
    '5) la natura MERCE va in ORDINE_VENDITA');

-- 6) l'unicita' dell'ordine da offerta
SELECT ok(
    (SELECT pg_get_indexdef('vendite.uq_ordini_v_documento_origine_offerta'::regclass))
        LIKE '%''OFFERTA_COMMERCIALE''%',
    '6) uq_ordini_v_documento_origine_offerta nomina OFFERTA_COMMERCIALE');

-- 7) nessun confronto col codice corto nelle definizioni vive
SELECT is_empty(
    $$SELECT d.oggetto
        FROM (SELECT c.oid::regclass::text AS oggetto, pg_get_viewdef(c.oid) AS testo
                FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE c.relkind IN ('v', 'm') AND n.nspname IN ('vendite', 'catalogo', 'script')
              UNION ALL
              SELECT p.oid::regprocedure::text, pg_get_functiondef(p.oid)
                FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
               WHERE p.prokind = 'f' AND n.nspname IN ('vendite', 'catalogo', 'script')) d
       WHERE d.testo ~ '(documento_origine_tipo|destinazione_tipo)\)?(::text)?\s*(=|<>|!=|IS DISTINCT FROM|IS NOT DISTINCT FROM)\s*''(OFFERTA|ORDINE)'''$$,
    '7) nessuna definizione confronta le due colonne con OFFERTA o ORDINE');

-- 8 … 11: il caso costruito
CREATE TEMP TABLE _ord ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('pgTAP grammatica 2b');

CREATE TEMP TABLE _cli ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'pgTAP grammatica 2b',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));
CREATE TEMP TABLE _lis ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _cli), 'pgTAP grammatica 2b');

CREATE TEMP TABLE _off ON COMMIT DROP AS
WITH ins AS (
  INSERT INTO vendite.offerte_commerciali (emittente_fiscale_id, billing_account_id,
      istanza_utility_id, utility_id, listino_id, listino_versione_id,
      validita_dal, validita_al, stato_doc_offerta_id)
  SELECT script.fn_pgtap_emittente_operatore(), c.billing_account_id, c.istanza_utility_id, c.utility_id,
         l.listino_id, l.listino_versione_id, script.fn_data_operativa(), script.fn_data_operativa() + 364,
         (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA')
    FROM _cli c, _lis l
  RETURNING id, uid)
SELECT id, uid FROM ins;

SELECT is(
    pg_temp.vincolo_violato(format(
        $$UPDATE vendite.ordini SET documento_origine_tipo = 'OFFERTA', documento_origine_id = %s WHERE id = %s$$,
        (SELECT id FROM _off), (SELECT ordine_id FROM _ord))),
    'fk_ordini_documento_origine_tipo_sorgenti',
    '8) origine OFFERTA (il codice corto): rifiutata dalla FK verso le sorgenti');

SELECT is(
    pg_temp.vincolo_violato(format(
        $$UPDATE vendite.ordini SET documento_origine_tipo = 'OFFERTA_COMMERCIALE', documento_origine_id = %s,
                 sorgente_tipo_id = (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'OFFERTA_COMMERCIALE'),
                 sorgente_uid = %L
           WHERE id = %s$$,
        (SELECT id FROM _off), (SELECT uid FROM _off), (SELECT ordine_id FROM _ord))),
    'NESSUN ERRORE',
    '9) origine OFFERTA_COMMERCIALE: passa');

SELECT results_eq(
    format($$SELECT l.origine::text, l.natura, l.origine_id
               FROM vendite.fn_documento_legami('ORDINE_VENDITA', %s) l
              WHERE l.natura = 'PROVENIENZA'$$, (SELECT ordine_id FROM _ord)),
    format($$VALUES ('OFFERTA_COMMERCIALE'::text, 'PROVENIENZA'::text, %s::bigint)$$, (SELECT id FROM _off)),
    '10) legami dell''ordine: la provenienza ha origine OFFERTA_COMMERCIALE');

SELECT results_eq(
    format($$SELECT v.tipo::text, v.documento_id FROM vendite.fn_offerta_documenti_vivi(%s) v$$,
           (SELECT id FROM _off)),
    format($$VALUES ('ORDINE_VENDITA'::text, %s::bigint)$$, (SELECT ordine_id FROM _ord)),
    '11) documenti vivi dell''offerta: l''ordine, ORDINE_VENDITA');

-- 12) la firma
SELECT ok(
    pg_get_function_result('vendite.fn_documento_legami(character varying, bigint)'::regprocedure)
        LIKE '%origine character varying%',
    '12) fn_documento_legami: origine ancorata al codice della sorgente');

SELECT * FROM finish();
ROLLBACK;
