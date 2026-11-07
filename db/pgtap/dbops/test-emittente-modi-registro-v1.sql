-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive righe in dbops.emittente_modi e in
--   dbops.processi_bersagli: il registro dei modi lo scrive solo il proprietario
--   della tabella (dbops.trgfn_emittente_modi_solo_migrazione, provato come app
--   in dbops/test-emittente-modi-solo-migrazione-v1), i bersagli sono catalogo
--   del seed (stessa forma di dbops/test-processi-registro).
--
-- Test: il registro dei modi dell'emittente e i due risolutori generati.
-- Riferimento: brief-db-revisione-dbops, blocco 4b (D21, M18).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - i modi e le loro strade hanno una sede sola, dbops.emittente_modi: i due
--     risolutori vivi (fiscale e soggetto-ruolo) sono quelli che il registro
--     genera, e a regime il generatore non riscrive niente;
--   - un modo si risolve seguendo i salti fino a una radice, e la radice da'
--     l'emittente fiscale o il soggetto-ruolo, nella convenzione chiesta;
--   - un modo sconosciuto solleva E_PARAMETRO_INVALIDO, e il messaggio elenca i
--     modi del registro;
--   - un registro che nomina una colonna inesistente non genera niente:
--     E_EMITTENTE_MODI_INVALIDO;
--   - ogni modo nominato da un guard, una funzione o una policy e' nel
--     registro; la via di un bersaglio e' un modo (FK), e quella del guard montato.
--
-- Elenco test (plan 16):
--   1-3) il registro e le due funzioni del generatore
--   4)   PRESIDIO: il corpo vivo del risolutore fiscale e' quello del registro
--   5)   PRESIDIO: il corpo vivo del gemello soggetto-ruolo e' quello del registro
--   6)   a regime il generatore non riscrive niente
--   7)   un SALTO senza modo padre e' respinto
--   8)   fiscale: due salti fino a una radice PK
--   9)   fiscale: una radice SR passa dall'emittente fiscale del soggetto-ruolo
--  10)   soggetto-ruolo: due salti fino a una radice PK danno il soggetto-ruolo dell'emittente
--  11)   un modo sconosciuto: E_PARAMETRO_INVALIDO, coi modi del registro nel messaggio
--  12)   un registro con una colonna che non c'e': E_EMITTENTE_MODI_INVALIDO, col modo nominato
--  13)   PRESIDIO: ogni modo letterale dei montaggi del guard, delle funzioni e delle policy e' nel registro
--  14)   PRESIDIO: ogni bersaglio su una tabella col guard dichiara la via e la colonna del guard
--  15)   padre non e' una via (FK verso il registro)
--  16)   magazzino si', che il CHECK di prima non ammetteva
--
-- ⚠️ I test 4, 5, 6, 13 e 14 sono PRESIDI su cio' che c'e' (corpi, montaggi,
--   seed). La regola del generatore la provano i test 8-12, su tabelle TEMP e
--   righe del registro costruite qui, e i 15-16 su righe di bersaglio costruite: i risolutori costruiti si creano in
--   pg_temp, quelli veri non si toccano.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il file legge il catalogo e scrive solo righe di
--   catalogo di dbops (non sotto RLS) e tabelle TEMP sue: nessuna veste da aprire.

SELECT plan(16);

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

CREATE FUNCTION pg_temp.messaggio_di(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    RETURN SQLERRM;
END $$;

-- ============================================================
-- 1-3) Le firme
-- ============================================================
SELECT has_table('dbops', 'emittente_modi', '1) dbops.emittente_modi esiste');
SELECT has_function('dbops', 'fn_risolutore_emittente_corpo', ARRAY['boolean'],
    '2) dbops.fn_risolutore_emittente_corpo(boolean) esiste');
SELECT has_function('dbops', 'fn_genera_risolutori_emittente', ARRAY[]::text[],
    '3) dbops.fn_genera_risolutori_emittente() esiste');

-- ============================================================
-- 4-6) I risolutori vivi sono quelli del registro
-- ============================================================
SELECT ok(
    (SELECT p.prosrc FROM pg_catalog.pg_proc p
      WHERE p.oid = 'script.fn_resolve_emittente_fiscale_id(text, bigint)'::regprocedure)
    = dbops.fn_risolutore_emittente_corpo(false),
    '4) presidio: il risolutore fiscale vivo e'' quello che il registro genera (nessun ramo scritto a mano)'
);
SELECT ok(
    (SELECT p.prosrc FROM pg_catalog.pg_proc p
      WHERE p.oid = 'script.fn_resolve_emittente_sr_id(text, bigint)'::regprocedure)
    = dbops.fn_risolutore_emittente_corpo(true),
    '5) presidio: il gemello soggetto-ruolo vivo e'' quello che il registro genera'
);
SELECT is(dbops.fn_genera_risolutori_emittente(), 0,
    '6) a regime il generatore non riscrive niente');

-- ============================================================
-- 7-12) Il generatore, su un mondo costruito
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO dbops.emittente_modi (modo, schema_tabella, nome_tabella, forma, colonna)
      VALUES ('pgtap_salto_orfano', 'vendite', 'ddt_righe', 'SALTO', 'ddt_id')$$,
    '23514',
    NULL,
    '7) un SALTO senza modo padre e'' respinto (chk_emittente_modi_padre)'
);

CREATE TEMP TABLE t_emittente AS
SELECT * FROM dbops.fn_pgtap_crea_emittente('PGTD21');

CREATE TEMP TABLE t_testa  (id bigint PRIMARY KEY, emittente_fiscale_id bigint);
CREATE TEMP TABLE t_riga   (id bigint PRIMARY KEY, testa_id bigint);
CREATE TEMP TABLE t_nipote (id bigint PRIMARY KEY, riga_id bigint);
CREATE TEMP TABLE t_sr     (id bigint PRIMARY KEY, sr_id bigint);

INSERT INTO t_testa  SELECT 1, e.emittente_fiscale_id FROM t_emittente e;
INSERT INTO t_riga   VALUES (10, 1);
INSERT INTO t_nipote VALUES (100, 10);
INSERT INTO t_sr     SELECT 7, e.soggetto_ruolo_id FROM t_emittente e;

INSERT INTO dbops.emittente_modi (modo, schema_tabella, nome_tabella, forma, colonna, modo_padre) VALUES
    ('pgtap_testa',  'pg_temp', 't_testa',  'PK',    'emittente_fiscale_id', NULL),
    ('pgtap_riga',   'pg_temp', 't_riga',   'SALTO', 'testa_id',             'pgtap_testa'),
    ('pgtap_nipote', 'pg_temp', 't_nipote', 'SALTO', 'riga_id',              'pgtap_riga'),
    ('pgtap_sr',     'pg_temp', 't_sr',     'SR',    'sr_id',                NULL);

-- I due risolutori generati da questo registro, in pg_temp: quelli veri restano com'erano.
DO $$
BEGIN
    EXECUTE 'CREATE FUNCTION pg_temp.ris_fiscale(p_modo text, p_valore bigint) RETURNS bigint '
         || 'LANGUAGE plpgsql STABLE AS $c$' || dbops.fn_risolutore_emittente_corpo(false) || '$c$';
    EXECUTE 'CREATE FUNCTION pg_temp.ris_sr(p_modo text, p_valore bigint) RETURNS bigint '
         || 'LANGUAGE plpgsql STABLE AS $c$' || dbops.fn_risolutore_emittente_corpo(true) || '$c$';
END $$;

SELECT is(
    pg_temp.ris_fiscale('pgtap_nipote', 100),
    (SELECT e.emittente_fiscale_id FROM t_emittente e),
    '8) fiscale: dal nipote alla riga, dalla riga alla testata, la testata porta l''emittente fiscale'
);
SELECT is(
    pg_temp.ris_fiscale('pgtap_sr', 7),
    (SELECT e.emittente_fiscale_id FROM t_emittente e),
    '9) fiscale: una radice SR risponde con l''emittente fiscale del suo soggetto-ruolo'
);
SELECT is(
    pg_temp.ris_sr('pgtap_nipote', 100),
    (SELECT e.soggetto_ruolo_id FROM t_emittente e),
    '10) soggetto-ruolo: due salti fino a una radice PK danno il soggetto-ruolo dell''emittente (prima il gemello conosceva tre modi)'
);
SELECT ok(
    pg_temp.codice_di($$SELECT pg_temp.ris_fiscale('pgtap_inesistente', 1)$$) = 'E_PARAMETRO_INVALIDO'
    AND pg_temp.messaggio_di($$SELECT pg_temp.ris_fiscale('pgtap_inesistente', 1)$$) ~ 'pgtap_nipote',
    '11) un modo sconosciuto solleva E_PARAMETRO_INVALIDO, e il messaggio elenca i modi del registro'
);

UPDATE dbops.emittente_modi SET colonna = 'colonna_che_non_c_e' WHERE modo = 'pgtap_sr';
SELECT ok(
    pg_temp.codice_di($$SELECT dbops.fn_risolutore_emittente_corpo(false)$$) = 'E_EMITTENTE_MODI_INVALIDO'
    AND pg_temp.messaggio_di($$SELECT dbops.fn_risolutore_emittente_corpo(false)$$) ~ 'pgtap_sr',
    '12) un registro con una colonna che non c''e'' non genera niente: E_EMITTENTE_MODI_INVALIDO, col modo nominato'
);
DELETE FROM dbops.emittente_modi WHERE modo LIKE 'pgtap\_%';

-- ============================================================
-- 13) Ogni modo nominato altrove e' nel registro
-- ============================================================
SELECT is_empty(
    $$WITH nominati AS (
          -- il primo argomento dei guard di scrittura montati
          SELECT (dbops.fn_trigger_argomenti(t.tgargs))[1] AS modo,
                 format('trigger %s su %s', t.tgname, t.tgrelid::regclass) AS dove
            FROM pg_catalog.pg_trigger t
           WHERE t.tgfoid = 'script.trgfn_guard_emittente_scope()'::regprocedure
          UNION ALL
          -- i modi letterali passati ai due risolutori da funzioni e policy
          SELECT m[1], p.oid::regprocedure::text
            FROM pg_catalog.pg_proc p
           CROSS JOIN LATERAL regexp_matches(dbops.fn_testo_senza_commenti(p.prosrc),
                   'fn_resolve_emittente_(?:fiscale|sr)_id\s*\(\s*''([a-z_]+)''', 'g') AS m
           WHERE p.oid NOT IN ('script.fn_resolve_emittente_fiscale_id(text, bigint)'::regprocedure,
                               'script.fn_resolve_emittente_sr_id(text, bigint)'::regprocedure)
          UNION ALL
          SELECT m[1], format('policy %s su %s.%s', pol.policyname, pol.schemaname, pol.tablename)
            FROM pg_catalog.pg_policies pol
           CROSS JOIN LATERAL regexp_matches(coalesce(pol.qual, '') || ' ' || coalesce(pol.with_check, ''),
                   'fn_resolve_emittente_(?:fiscale|sr)_id\s*\(\s*''([a-z_]+)''', 'g') AS m
      )
      SELECT n.modo, n.dove FROM nominati n
       WHERE NOT EXISTS (SELECT 1 FROM dbops.emittente_modi e WHERE e.modo = n.modo)$$,
    '13) presidio: ogni modo dei guard montati, delle funzioni e delle policy e'' una riga del registro'
);

-- ============================================================
-- 14) Le vie dei bersagli
-- ============================================================
SELECT is_empty(
    $$SELECT b.id, b.schema_tabella, b.nome_tabella, b.emittente_via, b.emittente_colonna
        FROM dbops.processi_bersagli b
        JOIN pg_catalog.pg_namespace n ON n.nspname = b.schema_tabella
        JOIN pg_catalog.pg_class c     ON c.relnamespace = n.oid AND c.relname = b.nome_tabella
        CROSS JOIN LATERAL (
            SELECT count(*) AS guard,
                   count(*) FILTER (WHERE dbops.fn_trigger_argomenti(t.tgargs)
                                          = ARRAY[b.emittente_via, b.emittente_colonna]) AS dichiarati
              FROM pg_catalog.pg_trigger t
             WHERE t.tgrelid = c.oid
               AND NOT t.tgisinternal
               AND t.tgfoid = 'script.trgfn_guard_emittente_scope()'::regprocedure
        ) g
       WHERE g.guard > 0 AND g.dichiarati = 0$$,
    '14) presidio: ogni bersaglio su una tabella col guard di scrittura dichiara la via e la colonna del guard'
);
SELECT throws_ok(
    $$INSERT INTO dbops.processi_bersagli
          (id, processo_id, schema_tabella, nome_tabella, emittente_via, emittente_colonna)
      VALUES (9101, 12, 'vendite', 'listini_righe', 'padre', 'listino_versione_id')$$,
    '23503',
    NULL,
    '15) padre non e'' una via: non e'' un modo del registro (fk_processi_bersagli_emittente_via)'
);
SELECT lives_ok(
    $$INSERT INTO dbops.processi_bersagli
          (id, processo_id, schema_tabella, nome_tabella, emittente_via, emittente_colonna)
      VALUES (9102, 12, 'magazzino', 'movimenti', 'magazzino', 'magazzino_id')$$,
    '16) magazzino e'' una via (prima il CHECK non la ammetteva)'
);

SELECT * FROM finish();
ROLLBACK;
