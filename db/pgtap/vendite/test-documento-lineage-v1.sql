-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Lineage documenti vendite (Step 5).
--   Oggetti: vendite.vw_documento_lineage_nodi, vw_documento_lineage_archi,
--            vw_documento_lineage, vendite.fn_documento_lineage.
--   Brief: brief-db-lineage-documenti-vendite §5.
--
-- Impostazione: la maggior parte dei test e' SEED-AGNOSTICA (forma degli oggetti,
--   security_invoker, invarianti che valgono su QUALSIASI dato — anche DB vuoto).
--   I 2 spot-check sui casi reali §5 (PRV0000185, commessa 186) sono protetti da
--   skip() quando i dati non sono presenti (es. CI su DB fresco).
--
-- Indice test (1..26):
--    1) vw_documento_lineage_nodi esiste
--    2) vw_documento_lineage_archi esiste
--    3) vw_documento_lineage esiste
--    4) fn_documento_lineage(bigint,text,text) esiste
--    5) colonne di vw_documento_lineage_nodi
--    6) colonne di vw_documento_lineage_archi
--    7) colonne di vw_documento_lineage
--    8) nodi: security_invoker attivo
--    9) archi: security_invoker attivo
--   10) summary: security_invoker attivo
--   11) fn: STABLE
--   12) fn: SECURITY INVOKER (NON definer)
--   13) archi: arco solo in A..H,R
--   14) archi: arco 'R' punta sempre a un nodo RESO_VENDITA
--   15) nodi: pipeline_rank sempre in 0..5
--   16) config.sorgenti RESO_VENDITA seedato e attivo (prereq Step 1)
--   17) summary: frontiera sempre valorizzata (self e' sempre candidato)
--   18) summary: RESO mai frontiera di un nodo non-reso (arco R escluso;
--       un reso e' pero' frontiera di se stesso come foglia)
--   19) invariante: n_discendenti_attivi>0 -> frontiera_fase <> 'CHIUSO'
--   20) invariante: nodo attivo -> frontiera attiva
--   21) fn guard: p_tipo_id <= 0 solleva
--   22) fn guard: p_uid vuoto solleva
--   23) fn guard: p_direzione non valida solleva
--   24) fn: direzione di default ('avanti') non solleva
--   25) §5 (skip-able): PRV0000185 -> catena forward raggiunge un DDT (arco H)
--   26) §5 (skip-able): commessa 186 -> indietro trova >=2 sorgenti (ROOT+COLLEGATO)
-- ------------------------------------------------------------

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

SELECT plan(26);

-- ---- 1..4: esistenza oggetti ---------------------------------------------
SELECT has_view('vendite', 'vw_documento_lineage_nodi',  'vw_documento_lineage_nodi esiste');
SELECT has_view('vendite', 'vw_documento_lineage_archi', 'vw_documento_lineage_archi esiste');
SELECT has_view('vendite', 'vw_documento_lineage',       'vw_documento_lineage esiste');
SELECT has_function('vendite', 'fn_documento_lineage',
                    ARRAY['bigint','text','text'],
                    'fn_documento_lineage(bigint,text,text) esiste');

-- ---- 5..7: forma (set colonne) -------------------------------------------
SELECT columns_are('vendite', 'vw_documento_lineage_nodi',
    ARRAY['tipo_id','uid','codice','stato_codice_interno','stato_codice',
          'stato_descrizione','fase','is_abortito','pipeline_rank'],
    'colonne di vw_documento_lineage_nodi');

SELECT columns_are('vendite', 'vw_documento_lineage_archi',
    ARRAY['from_tipo_id','from_uid','from_codice','to_tipo_id','to_uid','to_codice',
          'to_stato_codice_interno','to_fase','to_is_abortito','ruolo','arco'],
    'colonne di vw_documento_lineage_archi');

SELECT columns_are('vendite', 'vw_documento_lineage',
    ARRAY['tipo_id','uid','codice','stato_codice_interno','stato_codice','stato_descrizione',
          'fase','is_abortito','pratica_id','pratica_numero','n_pratiche',
          'frontiera_tipo_id','frontiera_uid','frontiera_codice',
          'frontiera_stato_codice_interno','frontiera_fase',
          'n_discendenti_diretti','n_discendenti_attivi','is_transitato',
          'n_sorgenti','root_tipo_id','root_uid','root_codice'],
    'colonne di vw_documento_lineage');

-- ---- 8..10: security_invoker=on sulle 3 viste ----------------------------
SELECT ok(
    EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) opt
             WHERE c.oid = 'vendite.vw_documento_lineage_nodi'::regclass
               AND opt IN ('security_invoker=on','security_invoker=true')),
    'nodi: security_invoker attivo');
SELECT ok(
    EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) opt
             WHERE c.oid = 'vendite.vw_documento_lineage_archi'::regclass
               AND opt IN ('security_invoker=on','security_invoker=true')),
    'archi: security_invoker attivo');
SELECT ok(
    EXISTS (SELECT 1 FROM pg_class c, unnest(c.reloptions) opt
             WHERE c.oid = 'vendite.vw_documento_lineage'::regclass
               AND opt IN ('security_invoker=on','security_invoker=true')),
    'summary: security_invoker attivo');

-- ---- 11..12: proprieta' della funzione -----------------------------------
SELECT is(
    (SELECT provolatile::text FROM pg_proc
      WHERE oid = 'vendite.fn_documento_lineage(bigint,text,text)'::regprocedure),
    's', 'fn_documento_lineage e'' STABLE');
SELECT is(
    (SELECT prosecdef FROM pg_proc
      WHERE oid = 'vendite.fn_documento_lineage(bigint,text,text)'::regprocedure),
    false, 'fn_documento_lineage e'' SECURITY INVOKER');

-- ---- 13..16: invarianti strutturali sugli archi/nodi ---------------------
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
      WHERE arco NOT IN ('A','B','C','D','E','F','G','H','R')),
    0, 'archi: arco sempre in A..H,R');

SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_archi
      WHERE arco = 'R'
        AND to_tipo_id <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')),
    0, 'archi: arco R punta sempre a un nodo RESO_VENDITA');

SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage_nodi
      WHERE pipeline_rank NOT BETWEEN 0 AND 5),
    0, 'nodi: pipeline_rank sempre in 0..5');

SELECT ok(
    EXISTS (SELECT 1 FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA' AND attivo IS TRUE),
    'config.sorgenti RESO_VENDITA seedato e attivo (prereq Step 1)');

-- ---- 17..20: invarianti sulla summary/frontiera --------------------------
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage WHERE frontiera_tipo_id IS NULL),
    0, 'summary: frontiera sempre valorizzata (il nodo stesso e'' candidato)');

-- Un RESO non e' mai raggiunto via forward (arco R escluso), quindi non e' mai
-- frontiera di un ALTRO documento. Un reso e' pero' legittimamente frontiera di
-- SE STESSO (foglia, lvl 0) -> escludere le origini che sono gia' un reso.
SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage
      WHERE frontiera_tipo_id = (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')
        AND tipo_id           <> (SELECT id FROM config.sorgenti WHERE codice_interno = 'RESO_VENDITA')),
    0, 'summary: RESO mai frontiera di un nodo non-reso (forward)');

SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage
      WHERE n_discendenti_attivi > 0 AND frontiera_fase = 'CHIUSO'),
    0, 'invariante: discendenti attivi -> frontiera non CHIUSO');

SELECT is(
    (SELECT count(*)::int FROM vendite.vw_documento_lineage
      WHERE fase <> 'CHIUSO' AND NOT is_abortito AND frontiera_fase = 'CHIUSO'),
    0, 'invariante: nodo attivo -> frontiera attiva');

-- ---- 21..24: guardie e default della funzione ----------------------------
SELECT throws_ok(
    $$ SELECT * FROM vendite.fn_documento_lineage(0::bigint, 'x', 'avanti') $$,
    NULL::text, NULL::text, 'fn guard: p_tipo_id <= 0 solleva');
SELECT throws_ok(
    $$ SELECT * FROM vendite.fn_documento_lineage(1::bigint, '', 'avanti') $$,
    NULL::text, NULL::text, 'fn guard: p_uid vuoto solleva');
SELECT throws_ok(
    $$ SELECT * FROM vendite.fn_documento_lineage(1::bigint, 'x', 'laterale') $$,
    NULL::text, NULL::text, 'fn guard: p_direzione non valida solleva');
SELECT lives_ok(
    $$ SELECT * FROM vendite.fn_documento_lineage(
           (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO'),
           '00000000-0000-0000-0000-000000000000') $$,
    'fn: direzione di default (avanti) non solleva');

-- ---- 25..26: casi reali §5 (skip-able quando i dati non ci sono) ----------
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM vendite.preventivi WHERE numero = 'PRV0000185') THEN
        ok(
            EXISTS (
                SELECT 1 FROM vendite.fn_documento_lineage(
                    (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO'),
                    (SELECT uid::text FROM vendite.preventivi WHERE numero = 'PRV0000185'),
                    'avanti')
                 WHERE arco = 'H'),
            '§5 PRV0000185: la catena forward raggiunge un DDT (arco H)')
    ELSE skip('PRV0000185 non presente nei dati', 1)
END;

SELECT CASE
    WHEN EXISTS (SELECT 1 FROM vendite.commesse WHERE id = 186) THEN
        ok(
            (SELECT count(*) FROM vendite.fn_documento_lineage(
                    (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA'),
                    '186', 'indietro')
              WHERE ruolo IN ('ROOT','COLLEGATO')) >= 2,
            '§5 commessa 186: indietro trova >=2 sorgenti (ROOT+COLLEGATO)')
    ELSE skip('commessa id=186 non presente nei dati', 1)
END;

SELECT * FROM finish();
ROLLBACK;
