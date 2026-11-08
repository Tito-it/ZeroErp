-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL — crea uno schema di prova con tabelle e trigger di lock scritti a mano, e scrive nel registro dbops.automation_lock_columns
-- pgTAP test per Zero ERP
--
-- La convergenza dei lock di colonna: il lock VIVO portato a quello ATTESO
-- (codice_interno + registro), e il runner che si FERMA invece di cancellare
-- un lock che il registro non conosce.
-- Brief: brief-db-lock-di-colonna-fuori-registro, sezioni 4 (D2, D3) e 7
--
-- Elenco test (plan 30):
--  1-3)  gli oggetti: le due funzioni nuove ci sono, drop_lock_trg e' ritirata
--  4)    ⭐ PRESIDIO: su tutto il database nessun lock diverge dal registro
--  5-7)  fn_trigger_argomenti: zero finale, accento, nessun argomento
--  8-9)  le divergenze dello schema di prova: RIGENERA e TOGLIE, con le
--        colonne che il registro non nomina
--  10)   il runner si FERMA e le nomina tutte e due
--  11)   ...e non ha toccato niente: i lock scritti a mano ci sono ancora
--  12)   DRY RUN: nessuna DDL
--  13-15) col registro completo: un solo lock per t_a, col nome da template,
--         gli argomenti attesi; nessuno su t_b (riga con enabled = false)
--  16)   idempotente: un secondo giro non ricrea il trigger (stesso oid)
--  17)   una colonna AGGIUNTA al registro arriva nel lock vivo
--  18-19) il lock funziona: la colonna bloccata no, quella libera si'
--  20)   nessuna divergenza residua nello schema di prova
--  21)   una riga di un ALTRO exec_mode non si toglie se la colonna e' gia' bloccata
--  22)   ...e non si crea se non lo e'
--  23)   ⭐ PRESIDIO: fuori dall'ambito un lock c'e' solo se il registro lo dichiara:
--        ogni sua colonna ha una riga attiva con lo stesso codice (il runner non
--        ci arriva, il lock lo monta una migrazione; giro 10b, blocco 10b-4)
--  24)   una tabella che solo una regola di un ALTRO modo copre non si confronta
--  25-26) un lock disabilitato non e' allineato: RIGENERA, e torna abilitato
--  27)   regola LOCK_COLUMNS spenta: TOGLIE, e codice_interno non e' «persa»
--  28)   ...e il runner toglie il lock senza fermarsi
--  29)   regola spenta e lock a mano su una colonna ignota al registro: si FERMA
--        (D32 e Q3 di brief-db-revisione-dbops, giro 10a: prima una tabella
--        senza regola usciva dal confronto con i suoi lock)
--  30)   ⭐ PRESIDIO: ...e ogni riga attiva del registro su una tabella fuori
--        dall'ambito ha il suo lock vivo, abilitato e con la colonna nell'UPDATE OF
--        (la meta' che mancava: una riga senza lock e' una promessa senza
--        esecutore, il caso di dbops.domini_task.codice)
--
-- Scopo:
--  - il criterio sta in dbops.fn_lock_columns_divergenze, e il test 4 lo
--    chiama per intero invece di ricalcolarlo;
--  - lo schema di prova si COSTRUISCE: i casi (lock scritto a mano, colonna
--    ignota al registro, riga disattivata) non si cercano nei dati di oggi.
-- ⚠️ Il test 4 va PRIMA che lo schema di prova esista: dopo, lo schema stesso
--   avrebbe divergenze volute.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(30);

-- ============================================================
-- Gli oggetti
-- ============================================================
SELECT has_function('dbops', 'fn_trigger_argomenti', ARRAY['bytea'],
    '1) dbops.fn_trigger_argomenti(bytea) esiste');
SELECT has_function('dbops', 'fn_lock_columns_divergenze', ARRAY['text', 'text[]'],
    '2) dbops.fn_lock_columns_divergenze(text, text[]) esiste');
SELECT hasnt_function('dbops', 'fn_run_automations_drop_lock_trg',
    '3) dbops.fn_run_automations_drop_lock_trg e'' ritirata (il suo lavoro e'' il ramo TOGLIE del runner)');

-- ============================================================
-- ⭐ Il presidio (D3): il lock vivo e' quello che il registro dichiara
-- ============================================================
-- Nomi delle tabelle divergenti, perche' un rosso dica DOVE.
SELECT is(
    (SELECT COALESCE(array_agg(d.schema_name||'.'||d.table_name||' '||d.azione
                               ORDER BY d.schema_name, d.table_name), ARRAY[]::text[])
       FROM dbops.fn_lock_columns_divergenze('CI', NULL) AS d),
    ARRAY[]::text[],
    '4) nessun trigger di lock diverge dal registro (codice_interno + dbops.automation_lock_columns)'
);

-- Fuori dall'ambito il runner non agisce: li' un lock lo monta una migrazione, e il
--   registro lo dichiara comunque. Le due meta': ogni coppia (colonna, codice) del lock
--   vivo ha la sua riga attiva (23), ogni riga attiva ha il suo lock (30).
CREATE TEMP TABLE _fuori_ambito_vivi AS
SELECT v.schema_name, v.table_name, v.trigger_name, v.abilitato, v.colonne_update_of,
       v.argomenti[i] AS colonna, v.argomenti[i + 1] AS codice
  FROM dbops.vw_lock_columns_vivi v
  CROSS JOIN LATERAL generate_series(1, cardinality(v.argomenti), 2) AS i
 WHERE NOT (    v.tipo_tabella = 'r'
            AND v.schema_name = ANY (dbops.fn_resolve_scope(NULL))
            AND dbops.fn_table_in_scope(v.schema_name, v.table_name));

SELECT is(
    (SELECT COALESCE(array_agg(f.schema_name||'.'||f.table_name||' '||f.trigger_name||' '||f.colonna
                               ORDER BY f.schema_name, f.table_name, f.trigger_name, f.colonna), ARRAY[]::text[])
       FROM _fuori_ambito_vivi f
      WHERE NOT EXISTS (SELECT 1 FROM dbops.automation_lock_columns r
                         WHERE r.enabled
                           AND r.target_schema = f.schema_name
                           AND r.target_table  = f.table_name
                           AND r.column_name   = f.colonna
                           AND r.error_code    = f.codice)),
    ARRAY[]::text[],
    '23) fuori dall''ambito ogni colonna di un lock ha la sua riga attiva nel registro, con lo stesso codice'
);

SELECT is(
    (SELECT COALESCE(array_agg(r.target_schema||'.'||r.target_table||' '||r.column_name
                               ORDER BY r.target_schema, r.target_table, r.column_name), ARRAY[]::text[])
       FROM dbops.automation_lock_columns r
       JOIN pg_class c     ON c.relname = r.target_table
       JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = r.target_schema
      WHERE r.enabled
        AND NOT (    c.relkind = 'r'
                 AND r.target_schema = ANY (dbops.fn_resolve_scope(NULL))
                 AND dbops.fn_table_in_scope(r.target_schema, r.target_table))
        AND NOT EXISTS (SELECT 1 FROM _fuori_ambito_vivi f
                         WHERE f.schema_name = r.target_schema
                           AND f.table_name  = r.target_table
                           AND f.colonna     = r.column_name
                           AND f.codice      = r.error_code
                           AND f.abilitato
                           AND r.column_name = ANY (f.colonne_update_of))),
    ARRAY[]::text[],
    '30) fuori dall''ambito ogni riga attiva del registro ha il suo lock vivo, abilitato, con la colonna nell''UPDATE OF'
);

-- ============================================================
-- fn_trigger_argomenti
-- ============================================================
SELECT is(dbops.fn_trigger_argomenti('\x636f6c00455f58313000'::bytea),
          ARRAY['col', 'E_X10'],
          '5) un ultimo argomento che finisce con zero resta intero (la forma rtrim lo troncava)');
SELECT is(dbops.fn_trigger_argomenti(convert_to('città', 'UTF8') || '\x00'::bytea),
          ARRAY['città'],
          '6) un argomento non ASCII torna com''e''');
SELECT is(dbops.fn_trigger_argomenti(''::bytea), ARRAY[]::text[],
          '7) nessun argomento: array vuoto');

-- ============================================================
-- Fixture: lo schema di prova
-- ============================================================
-- t_a ha codice_interno (lock implicito) e un lock SCRITTO A MANO su x, che il
--   registro non nomina: e' il caso di vendite.fatture.natura_doc_id.
-- t_b non ha codice_interno e un lock scritto a mano su w: il caso che
--   drop_lock_trg cancellava per funzione.
CREATE SCHEMA pgtap_lock_conv;
CREATE TABLE pgtap_lock_conv.t_a (
    id bigint PRIMARY KEY, codice_interno text, x int, y int, z int);
CREATE TABLE pgtap_lock_conv.t_b (id bigint PRIMARY KEY, w int);

CREATE TRIGGER trg_t_a_a10_lock_x_a_mano
    BEFORE UPDATE ON pgtap_lock_conv.t_a
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_lock_columns('x', 'E_COLONNA_NON_MODIFICABILE');
CREATE TRIGGER trg_t_b_a10_lock_w_a_mano
    BEFORE UPDATE OF w ON pgtap_lock_conv.t_b
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_lock_columns('w', 'E_COLONNA_NON_MODIFICABILE');

INSERT INTO pgtap_lock_conv.t_a VALUES (1, 'A', 1, 1, 1);

-- ============================================================
-- Il registro non conosce le colonne: il runner si ferma
-- ============================================================
SELECT is(
    (SELECT d.azione||' '||array_to_string(d.colonne_perse, ',')
       FROM dbops.fn_lock_columns_divergenze('SCHEDULED', ARRAY['pgtap_lock_conv']) AS d
      WHERE d.table_name = 't_a'),
    'RIGENERA x',
    '8) t_a: da rigenerare, e x e'' una colonna che il registro non nomina'
);
SELECT is(
    (SELECT d.azione||' '||array_to_string(d.colonne_perse, ',')
       FROM dbops.fn_lock_columns_divergenze('SCHEDULED', ARRAY['pgtap_lock_conv']) AS d
      WHERE d.table_name = 't_b'),
    'TOGLIE w',
    '9) t_b: niente da bloccare per il registro, ma w e'' bloccata dal vivo'
);

SELECT throws_like(
    $$ SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', ARRAY['pgtap_lock_conv'], false) $$,
    '%non nomina: pgtap_lock_conv.t_a (x); pgtap_lock_conv.t_b (w)%',
    '10) il runner si FERMA e nomina tutte le colonne fuori dal registro, invece di cancellarle'
);

SELECT is(
    (SELECT array_agg(t.tgname::text ORDER BY t.tgname)
       FROM pg_trigger t
      WHERE t.tgrelid IN ('pgtap_lock_conv.t_a'::regclass, 'pgtap_lock_conv.t_b'::regclass)
        AND t.tgfoid = 'script.trgfn_lock_columns()'::regprocedure),
    ARRAY['trg_t_a_a10_lock_x_a_mano', 'trg_t_b_a10_lock_w_a_mano'],
    '11) dopo lo stop i lock scritti a mano ci sono ancora'
);

-- ============================================================
-- Il registro completo: x si blocca, w si toglie per decisione
-- ============================================================
INSERT INTO dbops.automation_lock_columns
       (target_schema, target_table, column_name, error_code, exec_mode, enabled, note)
VALUES ('pgtap_lock_conv', 't_a', 'x', 'E_COLONNA_NON_MODIFICABILE', 'AUTO', true,  'pgTAP'),
       ('pgtap_lock_conv', 't_b', 'w', 'E_COLONNA_NON_MODIFICABILE', 'AUTO', false, 'pgTAP: blocco tolto per decisione');

SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', ARRAY['pgtap_lock_conv'], true);

SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
      WHERE t.tgrelid IN ('pgtap_lock_conv.t_a'::regclass, 'pgtap_lock_conv.t_b'::regclass)
        AND t.tgname LIKE '%a_mano'),
    2,
    '12) DRY RUN: nessuna DDL, i due lock scritti a mano ci sono ancora'
);

SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', ARRAY['pgtap_lock_conv'], false);

SELECT is(
    (SELECT array_agg(t.tgname::text)
       FROM pg_trigger t
      WHERE t.tgrelid = 'pgtap_lock_conv.t_a'::regclass
        AND t.tgfoid = 'script.trgfn_lock_columns()'::regprocedure),
    ARRAY['trg_t_a_a10_lock_columns_upd'],
    '13) t_a: UN solo lock, col nome da template; quello scritto a mano non c''e'' piu'''
);
SELECT is(
    (SELECT dbops.fn_trigger_argomenti(t.tgargs)
       FROM pg_trigger t
      WHERE t.tgrelid = 'pgtap_lock_conv.t_a'::regclass
        AND t.tgfoid = 'script.trgfn_lock_columns()'::regprocedure),
    ARRAY['codice_interno', 'E_CODICE_NON_MODIFICABILE', 'x', 'E_COLONNA_NON_MODIFICABILE'],
    '14) t_a: codice_interno (implicito) e x (dal registro), con i loro codici'
);
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
      WHERE t.tgrelid = 'pgtap_lock_conv.t_b'::regclass
        AND t.tgfoid = 'script.trgfn_lock_columns()'::regprocedure),
    0,
    '15) t_b: nessun lock, perche'' la riga del registro e'' enabled = false'
);

-- Idempotenza: il secondo giro non tocca un lock allineato.
CREATE TEMP TABLE tmp_lock_oid ON COMMIT DROP AS
SELECT t.oid FROM pg_trigger t WHERE t.tgname = 'trg_t_a_a10_lock_columns_upd';

SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', ARRAY['pgtap_lock_conv'], false);

SELECT is(
    (SELECT t.oid FROM pg_trigger t WHERE t.tgname = 'trg_t_a_a10_lock_columns_upd'),
    (SELECT oid FROM tmp_lock_oid),
    '16) un secondo giro non ricrea un lock gia'' allineato (stesso oid)'
);

-- ============================================================
-- Una colonna AGGIUNTA al registro arriva nel lock vivo
-- ============================================================
-- Con il runner «crea se manca» non arrivava mai: il trigger c'era gia'.
INSERT INTO dbops.automation_lock_columns
       (target_schema, target_table, column_name, error_code, exec_mode, enabled, note)
VALUES ('pgtap_lock_conv', 't_a', 'y', 'E_COLONNA_NON_MODIFICABILE', 'AUTO', true, 'pgTAP');

SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', ARRAY['pgtap_lock_conv'], false);

SELECT is(
    (SELECT dbops.fn_trigger_argomenti(t.tgargs)
       FROM pg_trigger t
      WHERE t.tgrelid = 'pgtap_lock_conv.t_a'::regclass
        AND t.tgfoid = 'script.trgfn_lock_columns()'::regprocedure),
    ARRAY['codice_interno', 'E_CODICE_NON_MODIFICABILE',
          'x', 'E_COLONNA_NON_MODIFICABILE', 'y', 'E_COLONNA_NON_MODIFICABILE'],
    '17) la riga nuova (y) e'' arrivata nel lock vivo'
);

SELECT throws_like(
    $$ UPDATE pgtap_lock_conv.t_a SET y = 2 WHERE id = 1 $$,
    '%Colonna non modificabile%',
    '18) il lock rigenerato funziona: y non si cambia'
);
SELECT lives_ok(
    $$ UPDATE pgtap_lock_conv.t_a SET z = 2 WHERE id = 1 $$,
    '19) una colonna che nessuno blocca si cambia'
);

SELECT is(
    (SELECT count(*)::int FROM dbops.fn_lock_columns_divergenze('SCHEDULED', ARRAY['pgtap_lock_conv'])),
    0,
    '20) nessuna divergenza residua nello schema di prova'
);

-- ============================================================
-- exec_mode: in quale giro un lock NASCE, non in quale giro esiste
-- ============================================================
-- z entra con exec_mode 'CI'. Un giro 'SCHEDULED' non la crea (22), ma se un
-- giro 'CI' l'ha gia' messa, il giro 'SCHEDULED' non la toglie (21).
INSERT INTO dbops.automation_lock_columns
       (target_schema, target_table, column_name, error_code, exec_mode, enabled, note)
VALUES ('pgtap_lock_conv', 't_a', 'z', 'E_COLONNA_NON_MODIFICABILE', 'CI', true, 'pgTAP');

SELECT dbops.fn_run_automations_lock_columns('CI', ARRAY['pgtap_lock_conv'], false);

SELECT is(
    (SELECT count(*)::int FROM dbops.fn_lock_columns_divergenze('SCHEDULED', ARRAY['pgtap_lock_conv'])),
    0,
    '21) una colonna messa dal giro CI non diverge per il giro SCHEDULED (non si toglie ogni notte)'
);

DROP TRIGGER trg_t_a_a10_lock_columns_upd ON pgtap_lock_conv.t_a;
SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', ARRAY['pgtap_lock_conv'], false);

SELECT ok(
    array_position(
        (SELECT dbops.fn_trigger_argomenti(t.tgargs)
           FROM pg_trigger t
          WHERE t.tgrelid = 'pgtap_lock_conv.t_a'::regclass
            AND t.tgfoid = 'script.trgfn_lock_columns()'::regprocedure),
        'z') IS NULL,
    '22) il giro SCHEDULED non crea una colonna che nasce solo nel giro CI'
);

-- ============================================================
-- La regola LOCK_COLUMNS: di un altro modo, spenta
-- ============================================================
-- Qui t_a ha il lock del giro SCHEDULED del 22 (codice_interno, x, y): si toglie a
-- mano, per vedere che il giro SCHEDULED non lo rifa'. Le regole si cambiano
-- dentro la transazione.
UPDATE dbops.automation_rules_tbl
   SET exec_mode = 'CI'
 WHERE upper(btrim(rule_type)) = 'LOCK_COLUMNS' AND enabled;

DROP TRIGGER IF EXISTS trg_t_a_a10_lock_columns_upd ON pgtap_lock_conv.t_a;

SELECT is(
    (SELECT count(*)::int FROM dbops.fn_lock_columns_divergenze('SCHEDULED', ARRAY['pgtap_lock_conv'])
      WHERE table_name = 't_a'),
    0,
    '24) regola solo CI: per il giro SCHEDULED t_a non diverge, nemmeno senza lock (la governa l''altro giro)'
);

UPDATE dbops.automation_rules_tbl
   SET exec_mode = 'AUTO'
 WHERE upper(btrim(rule_type)) = 'LOCK_COLUMNS' AND enabled;

SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', ARRAY['pgtap_lock_conv'], false);
ALTER TABLE pgtap_lock_conv.t_a DISABLE TRIGGER trg_t_a_a10_lock_columns_upd;

SELECT is(
    (SELECT azione FROM dbops.fn_lock_columns_divergenze('SCHEDULED', ARRAY['pgtap_lock_conv'])
      WHERE table_name = 't_a'),
    'RIGENERA',
    '25) un lock disabilitato non blocca niente: diverge (RIGENERA)'
);

SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', ARRAY['pgtap_lock_conv'], false);

SELECT is(
    (SELECT t.tgenabled::text FROM pg_trigger t
      WHERE t.tgrelid = 'pgtap_lock_conv.t_a'::regclass
        AND t.tgfoid = 'script.trgfn_lock_columns()'::regprocedure),
    'O',
    '26) dopo il giro il lock di t_a e'' di nuovo abilitato'
);

-- Regola spenta = trigger tolto (Q3).
UPDATE dbops.automation_rules_tbl
   SET enabled = false
 WHERE upper(btrim(rule_type)) = 'LOCK_COLUMNS';

SELECT is(
    (SELECT azione || '|' || cardinality(colonne_perse)
       FROM dbops.fn_lock_columns_divergenze('SCHEDULED', ARRAY['pgtap_lock_conv'])
      WHERE table_name = 't_a'),
    'TOGLIE|0',
    '27) regola spenta: t_a da togliere, e codice_interno (implicito) non e'' una colonna persa'
);

SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', ARRAY['pgtap_lock_conv'], false);

SELECT is(
    (SELECT count(*)::int FROM pg_trigger t
      WHERE t.tgrelid = 'pgtap_lock_conv.t_a'::regclass
        AND t.tgfoid = 'script.trgfn_lock_columns()'::regprocedure),
    0,
    '28) regola spenta: il runner toglie il lock di t_a senza fermarsi'
);

-- Un lock scritto a mano su una tabella senza regola, su una colonna che il
-- registro non nomina: non si cancella in silenzio.
CREATE TRIGGER trg_t_b_a10_lock_id_a_mano
    BEFORE UPDATE OF id ON pgtap_lock_conv.t_b
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_lock_columns('id', 'E_COLONNA_NON_MODIFICABILE');

SELECT throws_like(
    $$ SELECT dbops.fn_run_automations_lock_columns('SCHEDULED', ARRAY['pgtap_lock_conv'], false) $$,
    '%non nomina: pgtap_lock_conv.t_b (id)%',
    '29) regola spenta e lock a mano su una colonna ignota al registro: il runner si FERMA e la nomina'
);

SELECT * FROM finish();
ROLLBACK;
