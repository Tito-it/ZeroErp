-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test scrive nel registro dbops.automazione_overlap (configurazione delle
--   migrazioni) per provarne il CHECK.
-- pgTAP test per Zero ERP
--
-- I nomi generati e le chiavi del registro dell'overlap.
-- Brief: brief-db-revisione-dbops, giro 10c, blocco 10c-4 (§28.11-28.13).
--
-- Elenco test (plan 9):
--  1-2) key_columns e key_expressions di dbops.automazione_overlap sono jsonb
--  3)   il CHECK rifiuta una chiave che non e' un array...
--  4)   ...e un array con un elemento che non e' un testo
--  5)   ⭐ dbops.fn_name_from_template e' idempotente anche sui nomi accorciati
--  6)   ⭐ PRESIDIO: nessun trigger vivo ha un doppio trattino basso nel nome (l'accorciamento
--       non lo lascia piu'; i vivi li rigenerano i runner)
--  7-8) fn_apply_cleanup_at e fn_purge_cleanup_expired senza p_cleanup_column
--  9)   ⭐ PRESIDIO: nessuna tabella ha due trigger ATTIVO con la stessa funzione e gli stessi
--       argomenti (prima, su una partizione, la riconciliazione del nome ne creava un secondo)
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

SELECT col_type_is('dbops', 'automazione_overlap', 'key_columns', 'jsonb',
    '1) key_columns e'' jsonb: il registro si carica dal suo CSV');
SELECT col_type_is('dbops', 'automazione_overlap', 'key_expressions', 'jsonb',
    '2) key_expressions e'' jsonb');

SELECT throws_ok(
    $$ INSERT INTO dbops.automazione_overlap (target_schema, target_table, key_columns, active, exec_mode)
       VALUES ('pgtap_nomi', 't_oggetto', '{"a": 1}'::jsonb, false, 'AUTO') $$,
    '23514', NULL,
    '3) una chiave che non e'' un array e'' rifiutata (chk_automazione_overlap_chiavi)');
SELECT throws_ok(
    $$ INSERT INTO dbops.automazione_overlap (target_schema, target_table, key_columns, active, exec_mode)
       VALUES ('pgtap_nomi', 't_numero', '["a", 1]'::jsonb, false, 'AUTO') $$,
    '23514', NULL,
    '4) un array con un elemento che non e'' un testo e'' rifiutato');

SELECT is(
    (SELECT count(*)::int
       FROM (SELECT dbops.fn_name_from_template('trg_' || repeat('ab_', k) || 'x_tabella_lunga_' || k,
                                                NULL, NULL) AS n
               FROM generate_series(1, 40) AS g(k)) s
      WHERE dbops.fn_name_from_template(s.n, NULL, NULL) <> s.n),
    0,
    '5) un nome gia'' risolto, ripassato a fn_name_from_template, esce uguale (prima uno su quaranta cambiava)');

SELECT is(
    (SELECT COALESCE(array_agg(n.nspname || '.' || c.relname || ' ' || t.tgname ORDER BY 1), ARRAY[]::text[])
       FROM pg_trigger t
       JOIN pg_class c     ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT t.tgisinternal
        AND t.tgname ~ '__'
        AND n.nspname !~ '^pg_'),
    ARRAY[]::text[],
    '6) nessun trigger vivo ha un doppio trattino basso nel nome');

SELECT has_function('dbops', 'fn_apply_cleanup_at', ARRAY['text', 'text', 'text', 'integer', 'boolean', 'boolean'],
    '7) fn_apply_cleanup_at(schema, tabella, base, ttl, apply_on_update, dry_run): niente p_cleanup_column');
SELECT has_function('dbops', 'fn_purge_cleanup_expired', ARRAY['text', 'text', 'integer', 'boolean'],
    '8) fn_purge_cleanup_expired(schema, tabella, batch_limit, dry_run): niente p_cleanup_column');

SELECT is(
    (SELECT COALESCE(array_agg(x.tabella ORDER BY 1), ARRAY[]::text[])
       FROM (SELECT t.tgrelid::regclass::text AS tabella
               FROM pg_trigger t
              WHERE NOT t.tgisinternal
                AND t.tgfoid IN ('dbops.trgfn_child_requires_active_parent()'::regprocedure,
                                 'dbops.trgfn_prevent_deactivate_if_children()'::regprocedure)
              GROUP BY t.tgrelid, t.tgfoid, t.tgargs
             HAVING count(*) > 1) x),
    ARRAY[]::text[],
    '9) nessuna tabella ha due trigger ATTIVO con la stessa funzione e gli stessi argomenti');

SELECT * FROM finish();
ROLLBACK;
