-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test monta i trigger ATTIVO su tabelle TEMP sue
--   (CREATE TRIGGER, DDL): l'applicazione non monta trigger. E le letture dei
--   guard (dbops.fn_trigger_padre_stato, dbops.fn_trigger_figlie_presenti)
--   rispondono solo per tabelle del proprietario del database: una TEMP
--   dell'applicazione la rifiutano apposta (lo prova, come app,
--   dbops/test-guard-attivo-occhi-del-proprietario-v1).
--
-- Test: i guard ATTIVO — la grammatica condivisa degli argomenti, i codici dei
--   rifiuti, il padre assente, i rami di montaggio.
-- Riferimento: brief-db-revisione-dbops, giro 3 (D5, D18, D46, D47, D49).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - gli argomenti dei tre trigger ATTIVO si leggono per nome da
--     dbops.fn_trigger_attivo_argomenti, con TG_ARGV (base 0) come con
--     dbops.fn_trigger_argomenti (base 1), e sono tutti obbligatori (D18, D49);
--   - «padre non attivo» e' E_ATTIVO_PADRE_NON_ATTIVO, un conflitto di stato
--     che nomina padre e figlia, non un 500 (D46);
--   - un padre assente (chiave polimorfa, senza FK) e' E_PADRE_INESISTENTE,
--     per tutte e due le require (D5);
--   - un trigger montato male e' E_TRIGGER_ARGOMENTI_INVALIDI per le require
--     (D47: prima l'obsoleto diceva E_CATALOGO_OBSOLETO_NUOVA_ISTANZA) ed
--     E_ATTIVO_BLOCK_ARGS per il block; una colonna FK che la figlia non ha non
--     passa piu' in silenzio.
--
-- Elenco test (plan 23):
--   1-3) le firme dei tre building block
--   4)   grammatica del block, per nome
--   5)   grammatica del require non obsoleto, con l'esenzione
--   6)   TG_ARGV (base 0) e l'array di fn_trigger_argomenti (base 1): stessa risposta
--   7)   i montaggi fuori grammatica sono rifiutati, ognuno col suo perche'
--   8)   PRESIDIO: ogni trigger ATTIVO montato nel database rispetta la grammatica
--   9)   D46: figlia attiva su padre spento -> E_ATTIVO_PADRE_NON_ATTIVO
--  10)   ... e la frase nomina padre, chiave e figlia, nell'ordine del catalogo
--  11)   una figlia spenta su un padre spento passa
--  12)   D5: require attivo su chiave polimorfa, padre assente -> E_PADRE_INESISTENTE
--  13)   D5: require non obsoleto, padre assente -> E_PADRE_INESISTENTE
--  14)   il catalogo obsoleto resta E_CATALOGO_OBSOLETO_NUOVA_ISTANZA
--  15)   la riga derivata (esenzione all'INSERT) passa sul catalogo obsoleto
--  16)   D49: require attivo con quattro argomenti -> E_TRIGGER_ARGOMENTI_INVALIDI
--  17)   D47: require non obsoleto con quattro argomenti -> E_TRIGGER_ARGOMENTI_INVALIDI
--  18)   D47: colonna di esenzione assente -> E_TRIGGER_ARGOMENTI_INVALIDI
--  19)   colonna FK assente sulla figlia -> E_TRIGGER_ARGOMENTI_INVALIDI (prima passava)
--  20)   D49: block con quattro argomenti -> E_ATTIVO_BLOCK_ARGS
--  21)   il block resta E_ATTIVO_BLOCK_CHILDREN_ACTIVE con una figlia attiva
--  22)   la lettura del padre rifiuta un trigger che non e' un require
--  23)   PRESIDIO sul testo: nessuno dei cinque legge gli argomenti per posizione,
--        tutti passano dalla grammatica
--
-- ⚠️ I test 8 e 23 sono PRESIDI su cio' che c'e' (i montaggi, i corpi): il 8
--   in CI guarda i trigger che ci_apply ha generato. La regola la provano i
--   test 4-7 e 9-22, sulla fixture che si costruiscono.
-- ⚠️ Fixture su tabelle TEMP: nessun DDL su tabelle condivise, il ROLLBACK porta
--   via tutto. I trigger sono AFTER ROW immediati (non differiti) e scritti a
--   mano con la grammatica del generatore.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il file legge il catalogo e scrive solo tabelle
--   TEMP sue: nessuna tabella sotto RLS, nessuna veste da aprire.

SELECT plan(23);

-- Il codice di dominio di un rifiuto: fn_log_and_raise_error lo scrive in CONSTRAINT.
CREATE FUNCTION pg_temp.codice_di(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

-- ============================================================
-- 1-3) Le firme
-- ============================================================
SELECT has_function('dbops', 'fn_trigger_attivo_argomenti', ARRAY['name', 'text[]'],
    'dbops.fn_trigger_attivo_argomenti(name, text[]) esiste');
SELECT has_function('dbops', 'fn_trigger_padre_stato', ARRAY['oid', 'name', 'text'],
    'dbops.fn_trigger_padre_stato(oid, name, text) esiste');
SELECT has_function('dbops', 'fn_trigger_figlie_presenti', ARRAY['oid', 'name', 'text'],
    'dbops.fn_trigger_figlie_presenti(oid, name, text) esiste');

-- ============================================================
-- 4-7) La grammatica
-- ============================================================
SELECT is(
    (SELECT to_jsonb(g) FROM dbops.fn_trigger_attivo_argomenti(
        'trgfn_prevent_deactivate_if_children', ARRAY['s', 'figlia', 'padre_id', 'id', 'attivo']) g),
    jsonb_build_object('valido', true, 'dettaglio', NULL,
                       'figlia_schema', 's', 'figlia_tabella', 'figlia',
                       'padre_schema', NULL, 'padre_tabella', NULL,
                       'fk_col', 'padre_id', 'ref_col', 'id', 'stato_col', 'attivo',
                       'esenzione_col', NULL),
    '4) block: figlia_schema, figlia_tabella, fk_col, ref_col, stato_col'
);

SELECT is(
    (SELECT to_jsonb(g) FROM dbops.fn_trigger_attivo_argomenti(
        'trgfn_child_requires_non_obsolete_parent',
        ARRAY['s', 'padre', 'obsoleto_dal', 'padre_id', 'id', 'sorgente']) g),
    jsonb_build_object('valido', true, 'dettaglio', NULL,
                       'figlia_schema', NULL, 'figlia_tabella', NULL,
                       'padre_schema', 's', 'padre_tabella', 'padre',
                       'fk_col', 'padre_id', 'ref_col', 'id', 'stato_col', 'obsoleto_dal',
                       'esenzione_col', 'sorgente'),
    '5) require non obsoleto: padre_schema, padre_tabella, stato_col, fk_col, ref_col, esenzione_col'
);

SELECT is(
    (SELECT to_jsonb(g) FROM dbops.fn_trigger_attivo_argomenti(
        'trgfn_child_requires_active_parent', '[0:4]={s,padre,attivo,padre_id,id}'::text[]) g),
    (SELECT to_jsonb(g) FROM dbops.fn_trigger_attivo_argomenti(
        'trgfn_child_requires_active_parent', ARRAY['s', 'padre', 'attivo', 'padre_id', 'id']) g),
    '6) TG_ARGV (base 0) e l''array di fn_trigger_argomenti (base 1) danno la stessa risposta'
);

SELECT set_eq(
    $$SELECT v.caso, g.valido, g.dettaglio, g.fk_col
        FROM (VALUES
          ('block a tre',        'trgfn_prevent_deactivate_if_children',     ARRAY['s','f','padre_id']),
          ('require a quattro',  'trgfn_child_requires_active_parent',       ARRAY['s','p','attivo','padre_id']),
          ('require a sei',      'trgfn_child_requires_active_parent',       ARRAY['s','p','attivo','padre_id','id','x']),
          ('obsoleto a sette',   'trgfn_child_requires_non_obsolete_parent', ARRAY['s','p','o','padre_id','id','x','y']),
          ('argomento vuoto',    'trgfn_child_requires_active_parent',       ARRAY['s','p',' ','padre_id','id']),
          ('funzione estranea',  'trgfn_altra',                              ARRAY['s','p','attivo','padre_id','id'])
        ) AS v(caso, funzione, argomenti)
        CROSS JOIN LATERAL dbops.fn_trigger_attivo_argomenti(v.funzione::name, v.argomenti) g$$,
    $$VALUES ('block a tre',       false, '3 argomenti, attesi 5',      NULL::name),
             ('require a quattro', false, '4 argomenti, attesi 5',      NULL::name),
             ('require a sei',     false, '6 argomenti, attesi 5',      NULL::name),
             ('obsoleto a sette',  false, '7 argomenti, attesi 5 o 6',  NULL::name),
             ('argomento vuoto',   false, 'un argomento e'' vuoto',     NULL::name),
             ('funzione estranea', false, 'trgfn_altra non e'' una funzione trigger ATTIVO', NULL::name)$$,
    '7) i montaggi fuori grammatica: rifiutati, col perche'', e senza campi da usare'
);

SELECT is_empty(
    $$SELECT format('%s %s: %s', t.tgrelid::regclass, t.tgname, g.dettaglio)
        FROM pg_catalog.pg_trigger t
        JOIN pg_catalog.pg_proc p      ON p.oid = t.tgfoid
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
        CROSS JOIN LATERAL dbops.fn_trigger_attivo_argomenti(p.proname, dbops.fn_trigger_argomenti(t.tgargs)) g
       WHERE n.nspname = 'dbops'
         AND p.proname IN ('trgfn_prevent_deactivate_if_children',
                           'trgfn_child_requires_active_parent',
                           'trgfn_child_requires_non_obsolete_parent')
         AND NOT t.tgisinternal
         AND NOT g.valido$$,
    '8) presidio: ogni trigger ATTIVO montato nel database rispetta la grammatica (tutti gli argomenti, non vuoti)'
);

-- ============================================================
-- Fixture: un padre, le sue figlie, le chiavi polimorfe, i montaggi rotti
-- ============================================================
CREATE TEMP TABLE t_padre      (id bigint PRIMARY KEY, attivo boolean NOT NULL DEFAULT true, obsoleto_dal date);
CREATE TEMP TABLE t_figlia     (id bigint PRIMARY KEY, padre_id bigint REFERENCES t_padre (id), attivo boolean NOT NULL DEFAULT true);
-- chiavi polimorfe: nessuna FK, il padre puo' mancare
CREATE TEMP TABLE t_poli       (id bigint PRIMARY KEY, target_id bigint);
CREATE TEMP TABLE t_poli_obs   (id bigint PRIMARY KEY, target_id bigint, sorgente text);
-- un montaggio rotto per tabella: fra due trigger sulla stessa riga parlerebbe il primo
CREATE TEMP TABLE t_rotta_a    (id bigint PRIMARY KEY, padre_id bigint);
CREATE TEMP TABLE t_rotta_o    (id bigint PRIMARY KEY, padre_id bigint);
CREATE TEMP TABLE t_rotta_es   (id bigint PRIMARY KEY, padre_id bigint);
CREATE TEMP TABLE t_rotta_fk   (id bigint PRIMARY KEY, padre_id bigint);
CREATE TEMP TABLE t_padre_rotto (id bigint PRIMARY KEY, attivo boolean NOT NULL DEFAULT true);

INSERT INTO t_padre (id, attivo, obsoleto_dal) VALUES
    (1, true,  NULL),
    (2, false, NULL),
    (3, true,  DATE '2000-01-01');
INSERT INTO t_padre_rotto (id) VALUES (1);

DO $fixture$
DECLARE
    v_s pg_catalog.pg_namespace.nspname%TYPE :=
        (SELECT n.nspname FROM pg_catalog.pg_namespace n WHERE n.oid = pg_my_temp_schema());
BEGIN
    EXECUTE format($t$CREATE TRIGGER trg_t_req AFTER INSERT OR UPDATE ON %1$I.t_figlia FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(%1$L, 't_padre', 'attivo', 'padre_id', 'id')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_blk BEFORE UPDATE OF attivo ON %1$I.t_padre FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children(%1$L, 't_figlia', 'padre_id', 'id', 'attivo')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_poli AFTER INSERT OR UPDATE ON %1$I.t_poli FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(%1$L, 't_padre', 'attivo', 'target_id', 'id')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_poli_obs BEFORE INSERT OR UPDATE ON %1$I.t_poli_obs FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent(%1$L, 't_padre', 'obsoleto_dal', 'target_id', 'id', 'sorgente')$t$, v_s);
    -- i montaggi rotti
    EXECUTE format($t$CREATE TRIGGER trg_t_rotta_a AFTER INSERT ON %1$I.t_rotta_a FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(%1$L, 't_padre', 'attivo', 'padre_id')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_rotta_o BEFORE INSERT ON %1$I.t_rotta_o FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent(%1$L, 't_padre', 'obsoleto_dal', 'padre_id')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_rotta_es BEFORE INSERT ON %1$I.t_rotta_es FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_non_obsolete_parent(%1$L, 't_padre', 'obsoleto_dal', 'padre_id', 'id', 'colonna_che_non_c_e')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_rotta_fk AFTER INSERT ON %1$I.t_rotta_fk FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(%1$L, 't_padre', 'attivo', 'colonna_che_non_c_e', 'id')$t$, v_s);
    EXECUTE format($t$CREATE TRIGGER trg_t_padre_rotto BEFORE UPDATE OF attivo ON %1$I.t_padre_rotto FOR EACH ROW
        EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children(%1$L, 't_figlia', 'padre_id', 'id')$t$, v_s);
END
$fixture$;

-- ============================================================
-- 9-11) D46: il padre spento
-- ============================================================
SELECT is(
    pg_temp.codice_di($$INSERT INTO t_figlia (id, padre_id) VALUES (10, 2)$$),
    'E_ATTIVO_PADRE_NON_ATTIVO',
    '9) D46: una figlia attiva su un padre spento -> E_ATTIVO_PADRE_NON_ATTIVO (conflitto di stato, non un 500)'
);

SELECT throws_like(
    $$INSERT INTO t_figlia (id, padre_id) VALUES (11, 2)$$,
    '%.t_padre (id = 2) non è attivo%.t_figlia.',
    '10) la frase nomina padre, chiave e figlia, nell''ordine dei segnaposti del catalogo'
);

SELECT lives_ok(
    $$INSERT INTO t_figlia (id, padre_id, attivo) VALUES (12, 2, false)$$,
    '11) una figlia spenta su un padre spento passa'
);

-- ============================================================
-- 12-15) D5: il padre assente; l'obsoleto resta com'era
-- ============================================================
SELECT is(
    pg_temp.codice_di($$INSERT INTO t_poli (id, target_id) VALUES (1, 999)$$),
    'E_PADRE_INESISTENTE',
    '12) D5: require attivo su chiave polimorfa, padre assente -> E_PADRE_INESISTENTE (prima: «non attivo»)'
);

SELECT is(
    pg_temp.codice_di($$INSERT INTO t_poli_obs (id, target_id) VALUES (1, 999)$$),
    'E_PADRE_INESISTENTE',
    '13) D5: require non obsoleto, padre assente -> E_PADRE_INESISTENTE (prima: passava)'
);

SELECT is(
    pg_temp.codice_di($$INSERT INTO t_poli_obs (id, target_id) VALUES (2, 3)$$),
    'E_CATALOGO_OBSOLETO_NUOVA_ISTANZA',
    '14) il catalogo obsoleto resta E_CATALOGO_OBSOLETO_NUOVA_ISTANZA'
);

SELECT lives_ok(
    $$INSERT INTO t_poli_obs (id, target_id, sorgente) VALUES (3, 3, 'derivata')$$,
    '15) la riga derivata (esenzione valorizzata all''INSERT) passa sul catalogo obsoleto'
);

-- ============================================================
-- 16-20) I montaggi sbagliati
-- ============================================================
SELECT is(
    pg_temp.codice_di($$INSERT INTO t_rotta_a (id, padre_id) VALUES (1, 1)$$),
    'E_TRIGGER_ARGOMENTI_INVALIDI',
    '16) D49: require attivo con quattro argomenti (niente ripiego su ''id'') -> E_TRIGGER_ARGOMENTI_INVALIDI'
);

SELECT is(
    pg_temp.codice_di($$INSERT INTO t_rotta_o (id, padre_id) VALUES (1, 1)$$),
    'E_TRIGGER_ARGOMENTI_INVALIDI',
    '17) D47: require non obsoleto con quattro argomenti -> E_TRIGGER_ARGOMENTI_INVALIDI, non un 409'
);

SELECT is(
    pg_temp.codice_di($$INSERT INTO t_rotta_es (id, padre_id) VALUES (1, 1)$$),
    'E_TRIGGER_ARGOMENTI_INVALIDI',
    '18) D47: una colonna di esenzione che la figlia non ha -> E_TRIGGER_ARGOMENTI_INVALIDI'
);

SELECT is(
    pg_temp.codice_di($$INSERT INTO t_rotta_fk (id, padre_id) VALUES (1, 2)$$),
    'E_TRIGGER_ARGOMENTI_INVALIDI',
    '19) una colonna FK che la figlia non ha -> E_TRIGGER_ARGOMENTI_INVALIDI (prima si leggeva NULL e passava)'
);

SELECT is(
    pg_temp.codice_di($$UPDATE t_padre_rotto SET attivo = false WHERE id = 1$$),
    'E_ATTIVO_BLOCK_ARGS',
    '20) D49: block con quattro argomenti (niente ripiego su ''attivo'') -> E_ATTIVO_BLOCK_ARGS'
);

-- ============================================================
-- 21-22) Il block, e il building block che rifiuta l'uso sbagliato
-- ============================================================
INSERT INTO t_figlia (id, padre_id) VALUES (20, 1);

SELECT is(
    pg_temp.codice_di($$UPDATE t_padre SET attivo = false WHERE id = 1$$),
    'E_ATTIVO_BLOCK_CHILDREN_ACTIVE',
    '21) il block resta E_ATTIVO_BLOCK_CHILDREN_ACTIVE con una figlia attiva'
);

SELECT is(
    pg_temp.codice_di($$SELECT * FROM dbops.fn_trigger_padre_stato('t_padre'::regclass, 'trg_t_blk', '1')$$),
    'E_DBOPS_CHIAMATA_NON_VALIDA',
    '22) la lettura del padre risponde solo per un trigger require: un block -> E_DBOPS_CHIAMATA_NON_VALIDA'
);

-- ============================================================
-- 23) Presidio sul testo: la grammatica in un posto solo
-- ============================================================
SELECT is_empty(
    $$SELECT p.oid::regprocedure::text
        FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
       WHERE n.nspname = 'dbops'
         AND p.proname IN ('trgfn_prevent_deactivate_if_children',
                           'trgfn_child_requires_active_parent',
                           'trgfn_child_requires_non_obsolete_parent',
                           'fn_trigger_attivo_orfani',
                           'fn_ritira_attivo_eccezioni')
         AND (   dbops.fn_testo_senza_commenti(p.prosrc) ~ 'TG_ARGV\s*\['
              OR dbops.fn_testo_senza_commenti(p.prosrc) ~ '\ma\s*\[\s*[0-9]'
              OR dbops.fn_testo_senza_commenti(p.prosrc) !~ 'dbops\.fn_trigger_attivo_argomenti\s*\(')$$,
    '23) presidio: i tre trigger e i due lettori non leggono gli argomenti per posizione, passano tutti da dbops.fn_trigger_attivo_argomenti'
);

SELECT * FROM finish();
ROLLBACK;
