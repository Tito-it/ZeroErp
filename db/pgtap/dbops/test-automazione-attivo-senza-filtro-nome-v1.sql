-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL — crea uno schema di prova con un padre, una figlia, una radice partizionata con due partizioni e un trigger ATTIVO montato a mano — e lancia il runner ATTIVO
--
-- Test: l'automazione ATTIVO lega ogni FK, qualunque sia il nome della
--   colonna; chi non si lega sta nel registro delle eccezioni. Le FK ereditate
--   da una radice partizionata si legano e si escludono sulla radice.
--   Tid, 2026-11-21: D-1 «a» (il filtro _id si toglie), D-5 «a» (la radice).
--   Brief: brief-db-attivo-fk-senza-suffisso-id §5.
--   ChangeSet: 20261121-21 (dbops.fn_attivo_fk_esclusa), -22 (runner),
--   -23 (ritiro), mirror 20260925-49 (le 13 eccezioni), -24 (provision),
--   -25 (ritiro del registro delle inclusioni).
--
-- ⭐ E' il presidio che impedisce di ricreare un'esclusione silenziosa: il
--   test 1 guarda TUTTE le FK del perimetro, con o senza _id, e il caso
--   costruito (6-13) prova la regola su tabelle fatte dal test, non solo
--   sulle FK che lo schema contiene oggi.
-- ⛔ Il test 1 NON chiede a dbops.fn_attivo_fk_esclusa chi si lega: legge il
--   registro delle eccezioni e i trigger. Altrimenti misurerebbe il building
--   block con se stesso.
-- ⛔ I trigger si cercano per FUNZIONE e ARGOMENTI, non per nome.
-- ⚠️ In CI i trigger ATTIVO li genera la passata ci_apply, che gira PRIMA dei
--   pgTAP: i test 1-4 sono veri anche li'.
--
-- Elenco test (plan 13):
--   Lo schema
--    1) ⭐ ogni FK monocolonna propria del perimetro del runner verso un padre
--       con attivo (override ATTIVO_COL) ha require e block, oppure e' nel
--       registro delle eccezioni
--    2) le 36 FK del giro hanno require e block (le decisioni del §3.2)
--    3) nessun trigger ATTIVO proprio sulle partizioni delle note: le FK
--       ereditate si decidono sulla radice
--    4) il registro delle inclusioni non c'e' piu'
--    5) dbops.fn_attivo_fk_esclusa: eccezione, FK ereditata, FK senza _id
--   Il caso costruito (schema pgtap_attfk)
--    6) ⭐ una FK senza _id verso un codice del padre: require e block
--    7) ⭐ la radice partizionata: un require proprio sulla radice e i suoi
--       cloni sulle partizioni, nessun require proprio sulle partizioni
--    8) un block solo sul padre per la radice, nessuno per le partizioni
--    9) ⭐ il block della radice conta le righe di tutte le partizioni (la
--       radice non ha attivo: E_ATTIVO_BLOCK_CHILDREN_EXIST)
--   10) il require clonato vale sulla partizione: E_ATTIVO_PADRE_NON_ATTIVO
--   11) ⭐ il ritiro non tocca i cloni (un DROP sul clone e' rifiutato)
--   12) ⭐ il ritiro toglie un require proprio montato su una partizione per
--       una FK ereditata (il raddoppio del caso B, §3.1 del brief)
--   13) ⭐ un'eccezione sulla radice vale per tutte le partizioni: dopo il
--       giro, nessun require (ne' proprio ne' clonato) e nessun block
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- I trigger ATTIVO, con gli argomenti letti dalla grammatica condivisa.
-- ⛔ Il nome della tabella si compone dal catalogo, NON con tgrelid::regclass::text,
--   che dipende dal search_path. Si rifa' dopo ogni giro del runner.
CREATE TEMP VIEW _trg AS
SELECT cn.nspname::text || '.' || c.relname::text AS rel,
       p.proname::text AS proname,
       t.tgparentid,
       g.*
  FROM pg_trigger t
  JOIN pg_class c      ON c.oid = t.tgrelid
  JOIN pg_namespace cn ON cn.oid = c.relnamespace
  JOIN pg_proc p       ON p.oid = t.tgfoid
  JOIN pg_namespace pn ON pn.oid = p.pronamespace AND pn.nspname = 'dbops'
  CROSS JOIN LATERAL dbops.fn_trigger_attivo_argomenti(
      p.proname, dbops.fn_trigger_argomenti(t.tgargs)) AS g
 WHERE NOT t.tgisinternal
   AND p.proname IN ('trgfn_child_requires_active_parent',
                     'trgfn_prevent_deactivate_if_children');

-- La FK e' legata: il require sulla figlia (proprio) e il block sul padre.
CREATE FUNCTION pg_temp.legata(p_cs text, p_ct text, p_col text, p_ps text, p_pt text)
RETURNS boolean LANGUAGE sql STABLE AS $$
    SELECT EXISTS (SELECT 1 FROM _trg r
                    WHERE r.proname = 'trgfn_child_requires_active_parent'
                      AND r.tgparentid = 0
                      AND r.rel = p_cs || '.' || p_ct
                      AND r.padre_schema = p_ps AND r.padre_tabella = p_pt
                      AND r.fk_col = p_col)
       AND EXISTS (SELECT 1 FROM _trg b
                    WHERE b.proname = 'trgfn_prevent_deactivate_if_children'
                      AND b.rel = p_ps || '.' || p_pt
                      AND b.figlia_schema = p_cs AND b.figlia_tabella = p_ct
                      AND b.fk_col = p_col)
$$;

-- ============================================================
-- 1-5) Lo schema
-- ============================================================
-- Il perimetro e' quello del runner: gli schemi di fn_resolve_scope(NULL), le
-- tabelle di fn_table_in_scope, la colonna attivo del padre con l'override
-- ATTIVO_COL, le FK monocolonna. Solo le FK proprie (conparentid = 0): una
-- FK ereditata la decide la radice.
CREATE TEMP TABLE _fk AS
SELECT nc.nspname::text AS cs, cc.relname::text AS ct, a.attname::text AS col,
       np.nspname::text AS ps, cp.relname::text AS pt
  FROM pg_constraint k
  JOIN pg_class cc     ON cc.oid = k.conrelid
  JOIN pg_namespace nc ON nc.oid = cc.relnamespace
  JOIN pg_class cp     ON cp.oid = k.confrelid
  JOIN pg_namespace np ON np.oid = cp.relnamespace
  JOIN pg_attribute a  ON a.attrelid = k.conrelid AND a.attnum = k.conkey[1]
 WHERE k.contype = 'f'
   AND cardinality(k.conkey) = 1 AND cardinality(k.confkey) = 1
   AND k.conparentid = 0
   AND nc.nspname = ANY (dbops.fn_resolve_scope(NULL))
   AND np.nspname = ANY (dbops.fn_resolve_scope(NULL))
   AND dbops.fn_table_in_scope(nc.nspname, cc.relname)
   AND dbops.fn_table_in_scope(np.nspname, cp.relname)
   AND dbops.fn_col_exists(np.nspname, cp.relname,
           dbops.fn_get_override_col(np.nspname, cp.relname, 'ATTIVO_COL', 'attivo'));

SELECT is(
    (SELECT COALESCE(array_agg(f.cs || '.' || f.ct || '.' || f.col ORDER BY 1), '{}'::text[])
       FROM _fk f
      WHERE NOT EXISTS (SELECT 1 FROM dbops.automazione_attivo_eccezioni e
                         WHERE (e.schema_figlia, e.tabella_figlia, e.colonna_fk) = (f.cs, f.ct, f.col))
        AND NOT pg_temp.legata(f.cs, f.ct, f.col, f.ps, f.pt)),
    '{}'::text[],
    '1) ogni FK del perimetro verso un padre con attivo e'' legata, o e'' un''eccezione');

-- Le decisioni del §3.2 del brief: 30 «si lega» e 6 «incerte» legate (Tid, 2026-11-22).
SELECT is(
    (SELECT COALESCE(array_agg(d.cs || '.' || d.ct || '.' || d.col ORDER BY 1), '{}'::text[])
       FROM (VALUES
         ('config', 'stati_doc_offerte_transizioni',        'azione_processo_codename', 'config', 'azioni_processo'),
         ('config', 'transizioni_stati_contratti',          'azione_processo_codename', 'config', 'azioni_processo'),
         ('config', 'transizioni_stati_ddt',                'azione_processo_codename', 'config', 'azioni_processo'),
         ('config', 'transizioni_stati_listino_versioni',   'azione_processo_codename', 'config', 'azioni_processo'),
         ('config', 'transizioni_stati_ordini',             'azione_processo_codename', 'config', 'azioni_processo'),
         ('config', 'transizioni_stati_preventivi',         'azione_processo_codename', 'config', 'azioni_processo'),
         ('config', 'transizioni_stati_reso',               'azione_processo_codename', 'config', 'azioni_processo'),
         ('vendite', 'transizioni_stati_commessa',          'azione_processo_codename', 'config', 'azioni_processo'),
         ('config', 'stati_doc_fiscale_transizioni',        'azione_processo_codename', 'config', 'azioni_processo'),
         ('config', 'stati_doc_contratti',                  'esito', 'config', 'esiti_flussi_pratiche'),
         ('config', 'stati_doc_ddt',                        'esito', 'config', 'esiti_flussi_pratiche'),
         ('config', 'stati_doc_offerte',                    'esito', 'config', 'esiti_flussi_pratiche'),
         ('config', 'stati_doc_ordini',                     'esito', 'config', 'esiti_flussi_pratiche'),
         ('config', 'stati_doc_preventivi',                 'esito', 'config', 'esiti_flussi_pratiche'),
         ('config', 'stati_doc_reso',                       'esito', 'config', 'esiti_flussi_pratiche'),
         ('pratiche', 'template_flussi',                    'esito_default',   'config', 'esiti_flussi_pratiche'),
         ('pratiche', 'template_flussi_handler_eventi',     'esito_richiesto', 'config', 'esiti_flussi_pratiche'),
         ('pratiche', 'template_flussi_avanzamento_proiezione', 'esito_richiesto', 'config', 'esiti_flussi_pratiche'),
         ('pratiche', 'template_flussi_prerequisiti',       'esito_richiesto', 'config', 'esiti_flussi_pratiche'),
         ('config', 'tipi_indirizzi_allowed',               'ambito',            'config', 'sorgenti'),
         ('vendite', 'famiglie_documento',                  'codice_interno',    'config', 'sorgenti'),
         ('config', 'nature_vendita',                       'destinazione_tipo', 'config', 'sorgenti'),
         ('vendite', 'registri_fatturazione',               'famiglia_documento', 'vendite', 'famiglie_documento'),
         ('config', 'causali_trasporto',                    'causale_magazzino', 'magazzino', 'causali'),
         ('config', 'iva',                                  'id_iva_split',      'config', 'iva'),
         ('config', 'iva_stati',                            'assoggettamento_id_override', 'config', 'iva_assoggettamenti'),
         ('magazzino', 'eventi_assets',                     'magazzino_id_from', 'magazzino', 'magazzini'),
         ('magazzino', 'eventi_assets',                     'magazzino_id_to',   'magazzino', 'magazzini'),
         ('anagrafiche', 'emittenti_fiscali',               'regime_fiscale_rf', 'config', 'regimi_fiscali'),
         ('anagrafiche', 'fornitori',                       'regime_fiscale_rf', 'config', 'regimi_fiscali'),
         ('magazzino', 'trasferimenti',                     'magazzino_id_from', 'magazzino', 'magazzini'),
         ('magazzino', 'trasferimenti',                     'magazzino_id_to',   'magazzino', 'magazzini'),
         ('magazzino', 'trasferimenti_righe',               'ubicazione_id_da',  'magazzino', 'ubicazioni'),
         ('magazzino', 'trasferimenti_righe',               'ubicazione_id_a',   'magazzino', 'ubicazioni'),
         ('pratiche', 'flussi',                             'esito',             'config', 'esiti_flussi_pratiche'),
         ('vendite', 'fatturazione_lotti',                  'stato_lotto',       'config', 'stati_lotto_job')
       ) AS d(cs, ct, col, ps, pt)
      WHERE NOT pg_temp.legata(d.cs, d.ct, d.col, d.ps, d.pt)),
    '{}'::text[],
    '2) le 36 FK del giro hanno require e block');

SELECT is(
    (SELECT COALESCE(array_agg(r.rel || ':' || r.proname ORDER BY 1), '{}'::text[])
       FROM _trg r
      WHERE r.tgparentid = 0
        -- la FK di cui parla il trigger e' ereditata sulla tabella che la porta
        -- (il require sta sulla figlia, il block nomina la figlia): le FK proprie
        -- delle partizioni (target_id) si legano li', ed e' giusto
        AND EXISTS (
              SELECT 1
                FROM pg_constraint k
                JOIN pg_attribute a ON a.attrelid = k.conrelid AND a.attnum = k.conkey[1]
               WHERE k.contype = 'f' AND k.conparentid <> 0
                 AND k.conrelid = to_regclass(CASE WHEN r.proname = 'trgfn_child_requires_active_parent'
                                                   THEN r.rel
                                                   ELSE r.figlia_schema || '.' || r.figlia_tabella END)
                 AND a.attname = r.fk_col)),
    '{}'::text[],
    '3) nessun trigger ATTIVO proprio per una FK ereditata da una radice partizionata');

SELECT hasnt_table('dbops', 'automazione_attivo_inclusioni',
    '4) il registro delle inclusioni non c''e'' piu''');

SELECT is(
    ARRAY[
      COALESCE(dbops.fn_attivo_fk_esclusa('config', 'profili_accesso_bindings', 'identita_digitale_id'), '<si lega>'),
      COALESCE(dbops.fn_attivo_fk_esclusa('vendite', 'note', 'id_lingua'), '<si lega>'),
      COALESCE(dbops.fn_attivo_fk_esclusa('catalogo', 'note_articoli', 'id_lingua'), '<si lega>'),
      COALESCE(dbops.fn_attivo_fk_esclusa('config', 'iva', 'id_iva_split'), '<si lega>'),
      COALESCE(dbops.fn_attivo_fk_esclusa('config', 'iva', 'assoggettamento_id'), '<si lega>')],
    ARRAY['ECCEZIONE_DICHIARATA', 'ECCEZIONE_DICHIARATA', 'FK_EREDITATA', '<si lega>', '<si lega>'],
    '5) fn_attivo_fk_esclusa: eccezione, eccezione sulla radice, FK ereditata, FK senza _id, FK con _id');

-- ============================================================
-- Il caso costruito
-- ============================================================
CREATE SCHEMA pgtap_attfk;
CREATE TABLE pgtap_attfk.padre (
    id     bigint PRIMARY KEY,
    codice text NOT NULL UNIQUE,
    attivo boolean NOT NULL DEFAULT true);
-- Una figlia con attivo e una FK senza _id verso il codice del padre.
CREATE TABLE pgtap_attfk.figlia (
    id     bigint PRIMARY KEY,
    attivo boolean NOT NULL DEFAULT true,
    padre  text REFERENCES pgtap_attfk.padre (codice));
-- Una radice partizionata senza attivo, come le note: la FK sta sulla radice.
CREATE TABLE pgtap_attfk.radice (
    id    bigint NOT NULL,
    k     int    NOT NULL,
    padre text   REFERENCES pgtap_attfk.padre (codice)
) PARTITION BY LIST (k);
CREATE TABLE pgtap_attfk.radice_p1 PARTITION OF pgtap_attfk.radice FOR VALUES IN (1);
CREATE TABLE pgtap_attfk.radice_p2 PARTITION OF pgtap_attfk.radice FOR VALUES IN (2);

INSERT INTO pgtap_attfk.padre (id, codice) VALUES (1, 'P1'), (2, 'P2'), (3, 'P3');

SELECT dbops.fn_run_automations_attivo('SCHEDULED', ARRAY['pgtap_attfk'], false);

-- ============================================================
-- 6-10) Che cosa genera il runner
-- ============================================================
SELECT ok(pg_temp.legata('pgtap_attfk', 'figlia', 'padre', 'pgtap_attfk', 'padre'),
    '6) una FK senza _id verso un codice del padre: require e block');

SELECT is(
    (SELECT array_agg(r.rel || ':' || CASE WHEN r.tgparentid = 0 THEN 'proprio' ELSE 'clone' END
                      ORDER BY r.rel COLLATE "C")
       FROM _trg r
      WHERE r.proname = 'trgfn_child_requires_active_parent'
        AND r.rel LIKE 'pgtap_attfk.radice%'),
    ARRAY['pgtap_attfk.radice:proprio', 'pgtap_attfk.radice_p1:clone', 'pgtap_attfk.radice_p2:clone'],
    '7) la radice ha il suo require, le partizioni solo i cloni');

SELECT is(
    (SELECT array_agg(b.figlia_tabella::text ORDER BY b.figlia_tabella COLLATE "C")
       FROM _trg b
      WHERE b.proname = 'trgfn_prevent_deactivate_if_children'
        AND b.rel = 'pgtap_attfk.padre'),
    ARRAY['figlia', 'radice'],
    '8) sul padre un block per la figlia e uno per la radice, nessuno per le partizioni');

INSERT INTO pgtap_attfk.radice (id, k, padre) VALUES (10, 2, 'P2');

SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$UPDATE pgtap_attfk.padre SET attivo = false WHERE codice = 'P2'$$),
    'E_ATTIVO_BLOCK_CHILDREN_EXIST',
    '9) un padre citato da una riga della partizione p2 non si spegne: E_ATTIVO_BLOCK_CHILDREN_EXIST');

UPDATE pgtap_attfk.padre SET attivo = false WHERE codice = 'P3';

SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$INSERT INTO pgtap_attfk.radice (id, k, padre) VALUES (11, 1, 'P3')$$),
    'E_ATTIVO_PADRE_NON_ATTIVO',
    '10) una riga nuova della partizione p1 verso un padre spento: E_ATTIVO_PADRE_NON_ATTIVO');

-- ============================================================
-- 11-12) Il ritiro
-- ============================================================
SELECT is(
    ARRAY[
      COALESCE(dbops.fn_pgtap_codice_errore($$SELECT dbops.fn_ritira_attivo_eccezioni()$$), 'ok'),
      (SELECT count(*)::text FROM _trg r
        WHERE r.proname = 'trgfn_child_requires_active_parent'
          AND r.rel LIKE 'pgtap_attfk.radice_p%' AND r.tgparentid <> 0)],
    ARRAY['ok', '2'],
    '11) il ritiro non tocca i cloni, e i cloni restano');

-- Il raddoppio del caso B: un require proprio sulla partizione per la FK
-- ereditata, con gli stessi argomenti di quello della radice.
DO $mano$
DECLARE
    v_args text;
BEGIN
    SELECT string_agg(quote_literal(x), ', ' ORDER BY o)
      INTO v_args
      FROM pg_trigger t
      CROSS JOIN LATERAL unnest(dbops.fn_trigger_argomenti(t.tgargs)) WITH ORDINALITY AS u(x, o)
     WHERE t.tgrelid = 'pgtap_attfk.radice'::regclass
       AND t.tgfoid = 'dbops.trgfn_child_requires_active_parent'::regproc;
    EXECUTE format(
        'CREATE CONSTRAINT TRIGGER trg_pgtap_doppione AFTER INSERT OR UPDATE OF padre ON pgtap_attfk.radice_p1 '
        'DEFERRABLE INITIALLY DEFERRED FOR EACH ROW '
        'EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent(%s)', v_args);
END
$mano$;

-- ⚠️ Tre istruzioni: dentro una sola, il conteggio dopo il ritiro vedrebbe la
--   fotografia di inizio istruzione, col trigger ancora vivo.
CREATE TEMP TABLE _r12 (passo int, n text);
INSERT INTO _r12 SELECT 1, count(*)::text FROM pg_trigger
 WHERE tgrelid = 'pgtap_attfk.radice_p1'::regclass AND tgname = 'trg_pgtap_doppione';
INSERT INTO _r12 SELECT 2, dbops.fn_ritira_attivo_eccezioni()::text;
INSERT INTO _r12 SELECT 3, count(*)::text FROM pg_trigger
 WHERE tgrelid = 'pgtap_attfk.radice_p1'::regclass AND tgname = 'trg_pgtap_doppione';

SELECT is(
    (SELECT array_agg(n ORDER BY passo) FROM _r12),
    ARRAY['1', '1', '0'],
    '12) il ritiro toglie il require proprio della partizione per la FK ereditata');

-- ============================================================
-- 13) Un'eccezione sulla radice
-- ============================================================
INSERT INTO dbops.automazione_attivo_eccezioni (schema_figlia, tabella_figlia, colonna_fk, motivo)
VALUES ('pgtap_attfk', 'radice', 'padre', 'Eccezione del pgTAP: vale per tutte le partizioni.');

SELECT dbops.fn_run_automations_attivo('SCHEDULED', ARRAY['pgtap_attfk'], false);

SELECT is(
    ARRAY[
      (SELECT count(*)::text FROM _trg r
        WHERE r.proname = 'trgfn_child_requires_active_parent'
          AND r.rel LIKE 'pgtap_attfk.radice%'),
      (SELECT count(*)::text FROM _trg b
        WHERE b.proname = 'trgfn_prevent_deactivate_if_children'
          AND b.rel = 'pgtap_attfk.padre' AND b.figlia_tabella::text LIKE 'radice%'),
      (SELECT pg_temp.legata('pgtap_attfk', 'figlia', 'padre', 'pgtap_attfk', 'padre')::text)],
    ARRAY['0', '0', 'true'],
    '13) l''eccezione sulla radice toglie require e cloni e block, e la figlia resta legata');

SELECT * FROM finish();
ROLLBACK;
