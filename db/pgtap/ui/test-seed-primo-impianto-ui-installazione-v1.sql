-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il seed di primo impianto sulle tabelle di ui, visto
--   dall'INSTALLAZIONE (l'applicazione).
--   Brief: brief-db-seed-primo-impianto-non-si-riscrive (§16.15, QU1-QU3).
--   ChangeSet: 20261119-01 … -05 (la forma figlia) e le righe 3-6 di
--   dbops.automazione_seed_primo_impianto (80_data).
--
-- Gira come l'applicazione (runner di default): chi scrive si riconosce da
--   session_user, che non si simula. Il lato del SOFTWARE (il blocco DO del
--   mirror sulla composizione) sta in
--   db/pgtap/ui/test-seed-primo-impianto-ui-software-v1.sql, col runner owner.
--
-- I soggetti sono righe del seed di 80_data, contratto: la lista 1
--   (anagrafiche.clienti), le sue colonne 2 e 3, il preset di sistema 1 e la
--   sua composizione. In CI esistono perche' le carica il CSV e la rete di
--   90_end le iscrive in dbops.seed_righe.
--
-- Elenco test (plan 18):
--    1) le quattro tabelle hanno un trigger solo sulla funzione, BEFORE
--       INSERT OR UPDATE OR DELETE FOR EACH ROW
--    2) la composizione e' montata nella forma figlia del preset
--    3) le divergenze della regola su ui sono a zero
--    4) lista 1, colonna 3 e preset 1 sono nati dal seed
--    5) l'app cambia l'etichetta della colonna 3: passa
--    6) … e la colonna 3 diventa personalizzata
--    7) l'app cambia il codice della colonna 2: E_SEED_COLONNA_DEL_SOFTWARE
--    8) … il campo sorgente
--    9) l'app cancella la colonna 2: E_SEED_RIGA_NON_CANCELLABILE
--   10) l'app cambia la vista della lista 1: E_SEED_COLONNA_DEL_SOFTWARE
--   11) l'app cambia la soglia della ricerca della lista 1: passa
--   12) l'app cambia il codice del preset 1: E_SEED_COLONNA_DEL_SOFTWARE
--   13) l'app cancella il preset 1: E_SEED_RIGA_NON_CANCELLABILE
--   14) il preset 1 e' ancora intatto
--   15) l'app cambia una riga della composizione del preset 1: passa
--   16) … e il preset 1 diventa personalizzato (la data del contenuto)
--   17) l'app cancella una riga della composizione: passa
--   18) la composizione non ha registro: nessuna riga in dbops.seed_righe
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- 1-3 Il montaggio
-- ============================================================
SELECT is(
    (SELECT string_agg(c.relname || '=' || tg.tgtype, ',' ORDER BY c.relname COLLATE "C")
       FROM pg_trigger tg
       JOIN pg_class c ON c.oid = tg.tgrelid
      WHERE NOT tg.tgisinternal
        AND tg.tgfoid = 'script.trgfn_seed_primo_impianto()'::regprocedure
        AND tg.tgrelid IN ('ui.lista_definizione'::regclass, 'ui.lista_colonna'::regclass,
                           'ui.lista_preset'::regclass, 'ui.lista_preset_colonna'::regclass)),
    'lista_colonna=31,lista_definizione=31,lista_preset=31,lista_preset_colonna=31',
    '1) un trigger solo per tabella, BEFORE INSERT OR UPDATE OR DELETE FOR EACH ROW');

SELECT is(
    (SELECT dbops.fn_trigger_argomenti(tg.tgargs)
       FROM pg_trigger tg
      WHERE tg.tgrelid = 'ui.lista_preset_colonna'::regclass
        AND tg.tgfoid = 'script.trgfn_seed_primo_impianto()'::regprocedure),
    ARRAY['FIGLIA', 'preset_id', 'ui.lista_preset'],
    '2) la composizione segue il preset: forma figlia');

SELECT is(
    (SELECT count(*)::int FROM dbops.fn_seed_primo_impianto_divergenze(ARRAY['ui'])),
    0,
    '3) le divergenze della regola su ui sono a zero');

-- ============================================================
-- 4 Le righe del seed sono segnate
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM (VALUES ('ui.lista_definizione'::regclass, '1'),
                    ('ui.lista_colonna'::regclass, '3'),
                    ('ui.lista_preset'::regclass, '1')) v(t, id)
      CROSS JOIN LATERAL dbops.fn_seed_riga(v.t, v.id) s
      WHERE s.seed_riga_id IS NOT NULL),
    3,
    '4) lista 1, colonna 3 e preset 1 sono nati dal seed');

-- ============================================================
-- 5-9 La colonna
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE ui.lista_colonna SET etichetta = 'Codice del soggetto, a modo mio' WHERE id = 3$$),
    NULL,
    '5) l''app cambia l''etichetta della colonna 3: passa');

SELECT isnt(
    (SELECT s.personalizzata_il FROM dbops.fn_seed_riga('ui.lista_colonna'::regclass, '3') s),
    NULL,
    '6) … e la colonna 3 diventa personalizzata');

SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE ui.lista_colonna SET codice = 'ba_codice_mio' WHERE id = 2$$),
    'E_SEED_COLONNA_DEL_SOFTWARE',
    '7) l''app cambia il codice della colonna 2: E_SEED_COLONNA_DEL_SOFTWARE');

SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE ui.lista_colonna SET campo_sorgente = 'soggetto_codice' WHERE id = 2$$),
    'E_SEED_COLONNA_DEL_SOFTWARE',
    '8) … il campo sorgente');

SELECT is(
    dbops.fn_pgtap_codice_errore($$DELETE FROM ui.lista_colonna WHERE id = 2$$),
    'E_SEED_RIGA_NON_CANCELLABILE',
    '9) l''app cancella la colonna 2: E_SEED_RIGA_NON_CANCELLABILE');

-- ============================================================
-- 10-11 La definizione
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE ui.lista_definizione SET vista_sql = 'vw_soggetti_lista' WHERE id = 1$$),
    'E_SEED_COLONNA_DEL_SOFTWARE',
    '10) l''app cambia la vista della lista 1: E_SEED_COLONNA_DEL_SOFTWARE');

SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE ui.lista_definizione SET ricerca_min_caratteri = 2 WHERE id = 1$$),
    NULL,
    '11) l''app cambia la soglia della ricerca della lista 1: passa');

-- ============================================================
-- 12-14 Il preset
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE ui.lista_preset SET codice = 'clienti_mio' WHERE id = 1$$),
    'E_SEED_COLONNA_DEL_SOFTWARE',
    '12) l''app cambia il codice del preset 1: E_SEED_COLONNA_DEL_SOFTWARE');

SELECT is(
    dbops.fn_pgtap_codice_errore($$DELETE FROM ui.lista_preset WHERE id = 1$$),
    'E_SEED_RIGA_NON_CANCELLABILE',
    '13) l''app cancella il preset 1: E_SEED_RIGA_NON_CANCELLABILE');

SELECT is(
    (SELECT s.personalizzata_il FROM dbops.fn_seed_riga('ui.lista_preset'::regclass, '1') s),
    NULL,
    '14) il preset 1 e'' ancora intatto');

-- ============================================================
-- 15-18 La composizione segue il preset
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE ui.lista_preset_colonna SET larghezza = 321 WHERE preset_id = 1 AND colonna_id = 3$$),
    NULL,
    '15) l''app cambia una riga della composizione del preset 1: passa');

SELECT isnt(
    (SELECT s.personalizzata_il FROM dbops.fn_seed_riga('ui.lista_preset'::regclass, '1') s),
    NULL,
    '16) … e il preset 1 diventa personalizzato, attraverso la data del contenuto');

SELECT is(
    dbops.fn_pgtap_codice_errore($$DELETE FROM ui.lista_preset_colonna WHERE preset_id = 1 AND colonna_id = 14$$),
    NULL,
    '17) l''app cancella una riga della composizione: passa');

SELECT is(
    (SELECT count(*)::int FROM dbops.seed_righe
      WHERE schema_name = 'ui' AND table_name = 'lista_preset_colonna'),
    0,
    '18) la composizione non ha registro: le sue righe seguono il preset');

SELECT * FROM finish();
ROLLBACK;
