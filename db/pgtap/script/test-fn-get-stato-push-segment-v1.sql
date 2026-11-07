-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_get_stato_push_segment — il classificatore dello stato-push
--       di una chiave di segmento, nella forma a RANGE leakproof
--       (D14 giro 4 — D8; brief-db-partita-merce-per-documento §11;
--        changeSet 20260921-50 e -55).
--
-- Indice test (plan 12):
--   1) la funzione esiste, e' BEGIN ATOMIC (dipendenze nel catalogo), NON e'
--      SECURITY DEFINER, e' STABLE e torna text
--   2) ⭐ pin di FORMA: il corpo non contiene LIKE ne' `~~` — sotto la policy
--      RLS di commesse_attivita un LIKE non diventa mai Index Cond
--   3) chiave mai esistita -> LIBERA
--   4) chiave esatta NON_EMESSA -> ALLOCATA
--   5) chiave esatta EMESSA -> EMESSA
--   6) solo componenti #CMP NON_EMESSA (nessuna riga esatta) -> ALLOCATA
--   7) rettifica #RET:1 EMESSA (nessuna riga esatta) -> EMESSA
--   8) rettifica per componente #RET:1#CMP:c1 NON_EMESSA -> ALLOCATA
--   9) ANNULLATA non occupa: il segmento con la sola riga ritirata e' LIBERA
--      (rev 2026-10-12, 20261012-08, brief-db-annullo-a-valle-riapre-a-monte
--      D-5 di Tid: prima «ANNULLATA conta come ALLOCATA»; annullata la
--      commessa, il documento a monte deve tornare spingibile)
--  10) ⭐ IL VICINO NUMERICO: :R:1 (EMESSA) non vede :R:12 (NON_EMESSA) ->
--      EMESSA, e :R:12 da sola -> ALLOCATA
--  11) suffisso ignoto #FOO -> LIBERA: la semantica e' quella di prima
--      (solo #CMP e #RET), non «qualunque #»
--  12) scope: chi non vede la commessa legge LIBERA — e' il contratto INVOKER
--      del classificatore, dichiarato, non un difetto di questo giro
--
-- Scopo:
--  - il 2 e' la ragione del file: il -55 riscrive i due LIKE nel range a byte
--    `~>=~ k||'#CMP:' AND ~<~ k||'#CMP;'` perche' textlike non e' leakproof e
--    sotto una policy la clausola non sale mai nell'indice (provato il
--    2026-09-21 come app). Se un giorno un LIKE tornasse, il test lo dice.
--  - i casi 3-11 pinnano che la forma nuova risponde IDENTICA alla vecchia,
--    COSTRUENDO le chiavi: il vicino numerico (10) e il suffisso ignoto (11)
--    sono i due punti in cui un range scritto male divergerebbe.
--  - ⭐ il mondo e' COSTRUITO dai builder di dbops: gira identico su dbdev e
--    su un database da zero. Le attivita' si inseriscono DIRETTAMENTE in
--    commesse_attivita (come test-push-list-gia-inviato-v1): il classificatore
--    legge solo quella tabella.
--  - il 12 e' rosso da OWNER per costruzione (l'owner salta la RLS) e verde
--    come app: sta per ultimo perche' cambia il contesto.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ============================================================
-- 1-2) Struttura e forma
-- ============================================================
SELECT ok(
  (SELECT p.prosqlbody IS NOT NULL AND NOT p.prosecdef AND p.provolatile = 's'
          AND p.prorettype = 'text'::regtype
     FROM pg_proc p
    WHERE p.proname = 'fn_get_stato_push_segment' AND p.pronamespace = 'script'::regnamespace),
  '1) fn_get_stato_push_segment esiste, e'' BEGIN ATOMIC, non DEFINER, STABLE, torna text');

-- ⭐ La forma. pg_get_functiondef di un BEGIN ATOMIC stampa il corpo deparsato:
--    un LIKE comparirebbe come `~~`, e cosi' lo si cerca in entrambe le grafie.
SELECT ok(
  (SELECT d !~* '\mLIKE\M' AND d !~ '~~' AND d ~ '~>=~' AND d ~ '~<~'
     FROM pg_get_functiondef('script.fn_get_stato_push_segment(character varying)'::regprocedure) AS d),
  '2) il corpo non contiene LIKE ne'' ~~ e usa il range ~>=~ / ~<~ (leakproof: sale sopra la policy)');

-- ============================================================
-- Il mondo si COSTRUISCE, non si cerca.
-- ============================================================
CREATE TEMP TABLE tmp_cli_cls AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_classificatore');

CREATE TEMP TABLE tmp_refs_cls AS
SELECT
  c.billing_account_id,
  c.utility_id,
  c.istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-CLS-ART', false)                                        AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)   AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                  AS valuta_id
FROM tmp_cli_cls c;

CREATE TEMP TABLE tmp_com_cls AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_cls),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_cls),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-08-01',
  p_competenza_al          => DATE '2026-08-31',
  p_meta                   => jsonb_build_object('test_scope','pgtap_classificatore'),
  p_force_new              => true) AS commessa_id;

-- Un prefisso di segmento INVENTATO: il classificatore non dereferenzia nulla.
-- La base delle chiavi del test: la chiave del push di un consumo vero della
-- commessa (la provenienza delle righe), a cui il test aggiunge i suoi suffissi.
CREATE TEMP TABLE tmp_seg_cls AS
SELECT x.segment_key::text AS pre, x.consumo_id, x.sorgente_tipo_id
  FROM dbops.fn_pgtap_consumo_della_commessa((SELECT commessa_id FROM tmp_com_cls)) x;

-- Helper: un'attivita' con segment_key e stato_emissione espliciti, in BOZZA
-- (cosi' il CHECK del tipo documento emittibile non pretende nulla).
CREATE OR REPLACE FUNCTION pg_temp.cls_mk(p_segment varchar, p_stato_emissione varchar)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs_cls;
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
    competenza_mese, competenza_dal, competenza_al, tipo_doc_fiscale_id, valuta_id,
    prezzo_snapshot, pricing_mode, stato_approvazione, stato_emissione,
    sorgente_tipo_id, sorgente_id)   -- La riga NORMALE ha la sua sorgente: il consumo della commessa.
  VALUES (
    (SELECT commessa_id FROM tmp_com_cls), p_segment, r.articolo_id, r.istanza_utility_id,
    DATE '2026-08-15', r.uom_id, 1,
    DATE '2026-08-01', DATE '2026-08-01', DATE '2026-08-31',
    r.tipo_doc_fiscale_id, r.valuta_id, 10.0,
    'FIXED', 'BOZZA', p_stato_emissione,
    (SELECT sorgente_tipo_id FROM tmp_seg_cls), (SELECT consumo_id FROM tmp_seg_cls));
END $$ LANGUAGE plpgsql;

-- Le chiavi del test.
SELECT pg_temp.cls_mk((SELECT pre FROM tmp_seg_cls) || ':R:4',                'NON_EMESSA');   -- 4
SELECT pg_temp.cls_mk((SELECT pre FROM tmp_seg_cls) || ':R:5',                'EMESSA');       -- 5
SELECT pg_temp.cls_mk((SELECT pre FROM tmp_seg_cls) || ':R:6#CMP:c1',         'NON_EMESSA');   -- 6
SELECT pg_temp.cls_mk((SELECT pre FROM tmp_seg_cls) || ':R:6#CMP:c2',         'EMESSA');
SELECT pg_temp.cls_mk((SELECT pre FROM tmp_seg_cls) || ':R:7#RET:1',          'EMESSA');       -- 7
SELECT pg_temp.cls_mk((SELECT pre FROM tmp_seg_cls) || ':R:8#RET:1#CMP:c1',   'NON_EMESSA');   -- 8
SELECT pg_temp.cls_mk((SELECT pre FROM tmp_seg_cls) || ':R:9',                'ANNULLATA');    -- 9
SELECT pg_temp.cls_mk((SELECT pre FROM tmp_seg_cls) || ':R:1',                'EMESSA');       -- 10: il vicino
SELECT pg_temp.cls_mk((SELECT pre FROM tmp_seg_cls) || ':R:12',               'NON_EMESSA');   -- 10
SELECT pg_temp.cls_mk((SELECT pre FROM tmp_seg_cls) || ':R:11#FOO:1',         'NON_EMESSA');   -- 11

-- ============================================================
-- 3-9) i tre valori, con e senza suffissi
-- ============================================================
SELECT is(script.fn_get_stato_push_segment((SELECT pre FROM tmp_seg_cls) || ':R:999'), 'LIBERA',
  '3) chiave mai esistita -> LIBERA');
SELECT is(script.fn_get_stato_push_segment((SELECT pre FROM tmp_seg_cls) || ':R:4'), 'ALLOCATA',
  '4) chiave esatta NON_EMESSA -> ALLOCATA');
SELECT is(script.fn_get_stato_push_segment((SELECT pre FROM tmp_seg_cls) || ':R:5'), 'EMESSA',
  '5) chiave esatta EMESSA -> EMESSA');
SELECT is(script.fn_get_stato_push_segment((SELECT pre FROM tmp_seg_cls) || ':R:6'), 'ALLOCATA',
  '6) solo componenti #CMP, uno NON_EMESSA -> ALLOCATA (i #CMP entrano dal range)');
SELECT is(script.fn_get_stato_push_segment((SELECT pre FROM tmp_seg_cls) || ':R:7'), 'EMESSA',
  '7) solo la rettifica #RET:1 EMESSA -> EMESSA (il #RET entra dal range)');
SELECT is(script.fn_get_stato_push_segment((SELECT pre FROM tmp_seg_cls) || ':R:8'), 'ALLOCATA',
  '8) rettifica per componente #RET:1#CMP:c1 NON_EMESSA -> ALLOCATA');
SELECT is(script.fn_get_stato_push_segment((SELECT pre FROM tmp_seg_cls) || ':R:9'), 'LIBERA',
  '9) ANNULLATA non occupa: la sola riga ritirata lascia il segmento LIBERO (D-5, 20261012-08)');

-- ============================================================
-- 10) ⭐ il vicino numerico: :R:1 non vede :R:12
-- ============================================================
SELECT is(
  script.fn_get_stato_push_segment((SELECT pre FROM tmp_seg_cls) || ':R:1')
  || '|' || script.fn_get_stato_push_segment((SELECT pre FROM tmp_seg_cls) || ':R:12'),
  'EMESSA|ALLOCATA',
  '10) il vicino numerico: :R:1 (EMESSA) non vede :R:12 (NON_EMESSA) — EMESSA; :R:12 da sola ALLOCATA');

-- ============================================================
-- 11) il suffisso ignoto resta fuori: solo #CMP e #RET, come prima
-- ============================================================
SELECT is(script.fn_get_stato_push_segment((SELECT pre FROM tmp_seg_cls) || ':R:11'), 'LIBERA',
  '11) suffisso ignoto #FOO: LIBERA — la semantica e'' quella dei due LIKE di prima, non «qualunque #»');

-- ============================================================
-- 12) Scope: INVOKER, chi non vede la commessa legge LIBERA.
-- ⚠️ E' il contratto di sempre del classificatore, scritto qui perche' si
--    veda: un'attivita' fuori scope e' «mai instradata» per chi non la vede.
--    Rosso da owner per costruzione, verde come app.
-- ============================================================
SELECT set_config('app.current_user_id', '999999999', true);

SELECT is(script.fn_get_stato_push_segment((SELECT pre FROM tmp_seg_cls) || ':R:5'), 'LIBERA',
  '12) scope che non vede la commessa: LIBERA (INVOKER: la RLS resta di chi legge)');

SELECT * FROM finish();
ROLLBACK;
