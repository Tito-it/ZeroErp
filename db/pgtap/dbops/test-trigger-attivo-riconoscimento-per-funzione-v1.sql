-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il riconoscimento dei trigger ATTIVO per funzione e argomenti, e il
--   ritiro per argomenti.
-- Riferimento: brief-db-revisione-dbops, giro 4 (D6).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - dbops.fn_trigger_exists_block_by_args e dbops.fn_trigger_exists_require_by_args
--     riconoscono un block o un require montati con la grammatica del
--     generatore, dalla funzione del trigger e dagli argomenti letti per nome;
--   - un argomento diverso, anche solo per una maiuscola o per un carattere
--     che un LIKE prenderebbe per jolly, non e' lo stesso montaggio;
--   - la risposta non dipende dal search_path di chi chiama (prima, con
--     dbops nel search_path, PostgreSQL non scriveva lo schema nel testo del
--     trigger e il riconoscimento falliva sempre);
--   - dbops.fn_drop_triggers_by_function_args toglie i soli trigger con
--     quella funzione e quegli argomenti esatti, con qualunque search_path,
--     e risponde 0 per una funzione che non esiste.
--
-- Elenco test (plan 15):
--   1-3) le firme, ancorate al catalogo (name)
--   4)   block montato dal generatore: riconosciuto
--   5)   require montato dal generatore: riconosciuto
--   6)   block con la colonna attivo diversa: non riconosciuto
--   7)   «_» non e' un jolly: attiv_ non e' attivo
--   8)   le maiuscole contano: PADRE_ID non e' padre_id
--   9)   un require dell'obsoleto con gli stessi argomenti non e' un require attivo
--  10)   col search_path dell'applicazione (dbops dentro): block riconosciuto
--  11)   col search_path dell'applicazione: require riconosciuto
--  12)   ritiro per argomenti: tolto il solo require con gli argomenti chiesti
--  13)   ... e l'altro require resta
--  14)   ritiro col search_path dell'applicazione: tolto
--  15)   ritiro per una funzione che non esiste: 0, niente tolto
--
-- ⚠️ Fixture su tabelle TEMP: i trigger si montano e non scattano mai (nessuna
--   scrittura sulle tabelle), il ROLLBACK porta via tutto. Gli argomenti sono
--   stringhe: non devono nominare tabelle vere.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il file legge il catalogo e monta trigger su
--   tabelle TEMP sue: nessuna tabella sotto RLS, nessuna veste da aprire.

SELECT plan(15);

CREATE TEMP TABLE t_padre (id bigint PRIMARY KEY, attivo boolean NOT NULL DEFAULT true);
CREATE TEMP TABLE t_figlia (id bigint PRIMARY KEY, padre_id bigint, attivo boolean NOT NULL DEFAULT true);

-- I montaggi, con la grammatica del generatore (dbops.fn_run_automations_attivo)
CREATE TRIGGER trg_t_blk
    BEFORE UPDATE OF attivo ON t_padre
    FOR EACH ROW
    EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('s_figlia', 't_figlia', 'padre_id', 'id', 'attivo');
CREATE TRIGGER trg_t_blk_x
    BEFORE UPDATE OF attivo ON t_padre
    FOR EACH ROW
    EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('s_figlia', 't_figlia', 'padreXid', 'id', 'attivo');
CREATE TRIGGER trg_t_req
    AFTER INSERT OR UPDATE OF attivo, padre_id ON t_figlia
    FOR EACH ROW
    EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('s_padre', 't_padre', 'attivo', 'padre_id', 'id');
CREATE TRIGGER trg_t_req_altro
    AFTER INSERT OR UPDATE OF attivo, padre_id ON t_figlia
    FOR EACH ROW
    EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('s_padre', 't_altro', 'attivo', 'padre_id', 'id');
CREATE TRIGGER trg_t_obs
    AFTER INSERT OR UPDATE OF padre_id ON t_figlia
    FOR EACH ROW
    EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent('s_padre', 't_obsoleto', 'attivo', 'padre_id', 'id');

-- ============================================================
-- 1-3) Le firme
-- ============================================================
SELECT has_function('dbops', 'fn_trigger_exists_block_by_args',
    ARRAY['regclass', 'name', 'name', 'name', 'name', 'name'],
    '1) dbops.fn_trigger_exists_block_by_args(regclass, name x5) esiste');
SELECT has_function('dbops', 'fn_trigger_exists_require_by_args',
    ARRAY['regclass', 'name', 'name', 'name', 'name', 'name'],
    '2) dbops.fn_trigger_exists_require_by_args(regclass, name x5) esiste');
SELECT has_function('dbops', 'fn_drop_triggers_by_function_args',
    ARRAY['regclass', 'name', 'name', 'text[]'],
    '3) dbops.fn_drop_triggers_by_function_args(regclass, name, name, VARIADIC text[]) esiste');

-- ============================================================
-- 4-9) Il riconoscimento
-- ============================================================
SELECT ok(
    dbops.fn_trigger_exists_block_by_args('t_padre'::regclass, 's_figlia', 't_figlia', 'padre_id', 'id', 'attivo'),
    '4) il block montato dal generatore e'' riconosciuto (D6: prima, mai)'
);
SELECT ok(
    dbops.fn_trigger_exists_require_by_args('t_figlia'::regclass, 's_padre', 't_padre', 'attivo', 'padre_id', 'id'),
    '5) il require montato dal generatore e'' riconosciuto (D6: prima, mai)'
);
SELECT ok(
    NOT dbops.fn_trigger_exists_block_by_args('t_padre'::regclass, 's_figlia', 't_figlia', 'padre_id', 'id', 'abilitato'),
    '6) un block con la colonna attivo diversa non e'' lo stesso montaggio'
);
SELECT ok(
    NOT dbops.fn_trigger_exists_block_by_args('t_padre'::regclass, 's_figlia', 't_figlia', 'padre_id', 'id', 'attiv_'),
    '7) «_» non e'' un jolly: attiv_ non riconosce il montaggio con attivo (un ILIKE si'')'
);
SELECT ok(
    NOT dbops.fn_trigger_exists_require_by_args('t_figlia'::regclass, 's_padre', 't_padre', 'attivo', 'PADRE_ID', 'id'),
    '8) le maiuscole contano: PADRE_ID non e'' padre_id (sono identificatori)'
);
SELECT ok(
    NOT dbops.fn_trigger_exists_require_by_args('t_figlia'::regclass, 's_padre', 't_obsoleto', 'attivo', 'padre_id', 'id'),
    '9) un require dell''obsoleto con gli stessi argomenti non e'' un require attivo: conta la funzione'
);

-- ============================================================
-- 10-11) Lo stesso esito col search_path dell'applicazione
-- ============================================================
SET LOCAL search_path TO django, public, config, dbops, script, anagrafiche;

SELECT ok(
    dbops.fn_trigger_exists_block_by_args('t_padre'::regclass, 's_figlia', 't_figlia', 'padre_id', 'id', 'attivo'),
    '10) con dbops nel search_path il block e'' riconosciuto lo stesso'
);
SELECT ok(
    dbops.fn_trigger_exists_require_by_args('t_figlia'::regclass, 's_padre', 't_padre', 'attivo', 'padre_id', 'id'),
    '11) con dbops nel search_path il require e'' riconosciuto lo stesso'
);

RESET search_path;

-- ============================================================
-- 12-15) Il ritiro per argomenti
-- ============================================================
SELECT is(
    dbops.fn_drop_triggers_by_function_args('t_figlia'::regclass, 'dbops', 'trgfn_child_requires_active_parent',
                                            's_padre', 't_padre', 'attivo', 'padre_id', 'id'),
    1,
    '12) il ritiro toglie il solo require con quegli argomenti'
);
SELECT is(
    ARRAY(SELECT t.tgname::text FROM pg_catalog.pg_trigger t
           WHERE t.tgrelid = 't_figlia'::regclass AND NOT t.tgisinternal ORDER BY 1),
    ARRAY['trg_t_obs', 'trg_t_req_altro'],
    '13) ... e lascia l''altro require e il require dell''obsoleto'
);

SET LOCAL search_path TO django, public, config, dbops, script, anagrafiche;
SELECT is(
    dbops.fn_drop_triggers_by_function_args('t_padre'::regclass, 'dbops', 'trgfn_prevent_deactivate_if_children',
                                            's_figlia', 't_figlia', 'padreXid', 'id', 'attivo'),
    1,
    '14) con dbops nel search_path il ritiro trova e toglie il block (D6: prima, niente)'
);
RESET search_path;

SELECT is(
    dbops.fn_drop_triggers_by_function_args('t_padre'::regclass, 'dbops', 'trgfn_che_non_esiste',
                                            's_figlia', 't_figlia', 'padre_id', 'id', 'attivo'),
    0,
    '15) una funzione che non esiste non ha trigger da togliere: 0'
);

SELECT * FROM finish();
ROLLBACK;
