-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la versione del listino in vigore a una data, in UNA sede.
--   vendite.fn_listino_versione_in_vigore, il vincolo
--   ex_listini_versioni_no_overlap esteso a CHIUSA, il guard che blocca le date
--   di una versione chiusa, e il ritiro delle sette copie della regola.
--   Brief: brief-db-liste-righe-documento §8.15 (decisione di Tid, 2026-09-28:
--   «le versioni valide oggi», e il buco si chiude).
--   changeSet: 20260928-33 (vincolo), -34 (guard), -35 (funzione),
--   -36 -> -41 (i consumatori), -42 (registro overlap).
--
-- ⭐ TUTTO COSTRUITO: mondo e listino dai builder dbops.fn_pgtap_crea_*, le
--   versioni scritte qui. Vale anche su un DB ricostruito da zero, come in CI.
--
-- LA STORIA DEL LISTINO COSTRUITA:
--   V1  2020-01-01 .. 2020-12-31   ATTIVA, poi CHIUSA (fine gia' passata)
--   V2  2021-01-01 .. aperta       BOZZA, poi ATTIVA
--   VX  2020-06-01 .. aperta       BOZZA che prova a diventare ATTIVA sopra V1
--
-- ⛔ COSA PRESIDIA:
--   · per ogni data la versione in vigore e' al piu' UNA, per costruzione:
--     l'esclusione vale anche per le CHIUSE (8) e le date di una CHIUSA non si
--     spostano (6);
--   · la funzione risponde anche per il PASSATO (una CHIUSA vale per il suo
--     periodo, 4) — e' cio' che serve al risolutore del prezzo, che lavora sulla
--     data del documento;
--   · la regola non e' piu' scritta altrove (12), e i sei consumatori la
--     chiedono alla funzione (13).
--
-- Indice test (1..13):
--    1) la funzione: STABLE, non STRICT, SECURITY INVOKER
--    2) il vincolo vale per ATTIVA e CHIUSA
--    3) il registro dbops.automazione_overlap dice lo stesso predicato del vincolo
--    4) V1 ATTIVA: in vigore nel suo periodo, NULL fuori
--    5) V1 si chiude (fine gia' passata)
--    6) ⛔ le date di V1 CHIUSA non si spostano (messaggio del codice)
--    7) un UPDATE che riscrive le STESSE date di una CHIUSA passa
--    8) ⛔ una versione che si sovrappone alla CHIUSA non diventa ATTIVA
--    9) V2 diventa ATTIVA sul periodo libero
--   10) oggi e' in vigore V2
--   11) nel 2020 e' in vigore V1, CHIUSA: la storia risponde
--   12) nessuna copia della regola rimasta in vendite/script
--   13) i sei consumatori chiamano la funzione
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo): il builder del
-- mondo lo riapre poi sul suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- FIXTURE — il mondo apre anche il contesto applicativo
-- ============================================================
CREATE TEMP TABLE tmp_lvv_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('versione in vigore');

-- V1: la versione del builder, ATTIVA sul 2020.
CREATE TEMP TABLE tmp_lvv_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_lvv_mondo), 'versione in vigore',
    '2020-01-01'::date, '2020-12-31'::date);

-- Scopo: la versione in vigore del listino della fixture alla data.
CREATE OR REPLACE FUNCTION pg_temp.in_vigore(p_data date)
RETURNS bigint LANGUAGE sql STABLE AS $fx$
  SELECT vendite.fn_listino_versione_in_vigore((SELECT listino_id FROM tmp_lvv_listino), p_data);
$fx$;

-- Scopo: una versione in BOZZA del listino della fixture.
CREATE OR REPLACE FUNCTION pg_temp.bozza(p_codice text, p_dal date)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, stato)
  SELECT listino_id, p_codice, p_dal, 'BOZZA' FROM tmp_lvv_listino
  RETURNING id;
$fx$;

CREATE TEMP TABLE tmp_lvv_v2 AS SELECT pg_temp.bozza('PGTAP_LVV_V2', '2021-01-01') AS id;
CREATE TEMP TABLE tmp_lvv_vx AS SELECT pg_temp.bozza('PGTAP_LVV_VX', '2020-06-01') AS id;

-- ============================================================
-- 1..3 — forma
-- ============================================================
SELECT ok(
    (SELECT provolatile = 's' AND NOT proisstrict AND NOT prosecdef FROM pg_proc
      WHERE oid = 'vendite.fn_listino_versione_in_vigore(bigint,date)'::regprocedure),
    '1) fn_listino_versione_in_vigore: STABLE, non STRICT, SECURITY INVOKER');

SELECT ok(
    (SELECT pg_get_constraintdef(c.oid) ~ 'ATTIVA' AND pg_get_constraintdef(c.oid) ~ 'CHIUSA'
       FROM pg_constraint c
      WHERE c.conrelid = 'vendite.listini_versioni'::regclass
        AND c.conname = 'ex_listini_versioni_no_overlap' AND c.contype = 'x'),
    '2) ex_listini_versioni_no_overlap: EXCLUDE su ATTIVA e CHIUSA');

-- ⚠️ Il registro e' la sede da cui il framework ricreerebbe il vincolo: se dicesse
--    un predicato diverso, una ricreazione riaprirebbe il buco in silenzio.
--    Il registro conserva il predicato come e' SCRITTO, PostgreSQL lo ristampa
--    normalizzato: si confronta il SIGNIFICATO. Il predicato del registro diventa
--    il CHECK di una tabella temporanea con le stesse colonne, e PostgreSQL
--    normalizza le due espressioni allo stesso modo.
CREATE TEMP TABLE tmp_lvv_pred (attivo boolean, stato character varying(16));
DO $pred$
BEGIN
    EXECUTE format('ALTER TABLE tmp_lvv_pred ADD CONSTRAINT chk_pred CHECK (%s)',
                   (SELECT where_predicate FROM dbops.automazione_overlap
                     WHERE target_schema = 'vendite' AND target_table = 'listini_versioni'));
END $pred$;

SELECT is(
    (SELECT substring(pg_get_constraintdef(c.oid) FROM '^CHECK (.*)$')
       FROM pg_constraint c WHERE c.conname = 'chk_pred' AND c.conrelid = 'tmp_lvv_pred'::regclass),
    (SELECT substring(pg_get_constraintdef(c.oid) FROM ' WHERE (.*)$')
       FROM pg_constraint c
      WHERE c.conrelid = 'vendite.listini_versioni'::regclass
        AND c.conname = 'ex_listini_versioni_no_overlap'),
    '3) il registro overlap dice lo stesso predicato del vincolo (confronto normalizzato)');

-- ============================================================
-- 4..7 — V1: attiva, poi chiusa, e le sue date ferme
-- ============================================================
SELECT ok(
    pg_temp.in_vigore('2020-06-01') = (SELECT listino_versione_id FROM tmp_lvv_listino)
    AND pg_temp.in_vigore('2021-06-01') IS NULL,
    '4) V1 ATTIVA: in vigore nel 2020, NULL nel 2021 (V2 e'' ancora BOZZA)');

SELECT lives_ok(
    $$UPDATE vendite.listini_versioni SET stato = 'CHIUSA'
       WHERE id = (SELECT listino_versione_id FROM tmp_lvv_listino)$$,
    '5) V1 si chiude: la sua fine e'' gia'' passata');

SELECT throws_like(
    $$UPDATE vendite.listini_versioni SET valido_al = NULL
       WHERE id = (SELECT listino_versione_id FROM tmp_lvv_listino)$$,
    '%chiusa: le sue date di validita%',
    '6) le date di V1 CHIUSA non si spostano: il guard rifiuta col messaggio del codice');

SELECT lives_ok(
    $$UPDATE vendite.listini_versioni SET valido_al = '2020-12-31'
       WHERE id = (SELECT listino_versione_id FROM tmp_lvv_listino)$$,
    '7) riscrivere le STESSE date di una CHIUSA non e'' un cambio: passa');

-- ============================================================
-- 8..11 — la storia risponde una versione per data
-- ============================================================
-- ⛔ Il buco che l'esclusione solo-ATTIVA lasciava aperto: VX parte a giugno 2020,
--    dentro il periodo di V1 CHIUSA.
SELECT throws_ok(
    $$UPDATE vendite.listini_versioni SET stato = 'ATTIVA' WHERE id = (SELECT id FROM tmp_lvv_vx)$$,
    '23P01',
    NULL,
    '8) una versione che copre il periodo di una CHIUSA non diventa ATTIVA');

SELECT lives_ok(
    $$UPDATE vendite.listini_versioni SET stato = 'ATTIVA' WHERE id = (SELECT id FROM tmp_lvv_v2)$$,
    '9) V2 diventa ATTIVA sul periodo libero');

SELECT is(pg_temp.in_vigore(script.fn_data_operativa()), (SELECT id FROM tmp_lvv_v2),
    '10) oggi e'' in vigore V2');

SELECT is(pg_temp.in_vigore('2020-06-01'), (SELECT listino_versione_id FROM tmp_lvv_listino),
    '11) nel 2020 e'' in vigore V1, anche CHIUSA: la storia risponde');

-- ============================================================
-- 12..13 — la regola in un posto solo
-- ============================================================
-- ⚠️ Presidio sul TESTO, commenti tolti: prende la ricopiatura della forma che
--    c'era (lo stato ATTIVA/CHIUSA scritto su listini_versioni), non una
--    riscrittura con altri nomi. Perimetro: le funzioni di vendite e script.
SELECT is(
    (SELECT count(*)::integer FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname IN ('vendite', 'script')
        AND p.proname <> 'fn_listino_versione_in_vigore'
        AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'stato\s+IN\s*\(\s*''ATTIVA''\s*,\s*''CHIUSA''\s*\)'),
    0,
    '12) nessuna copia della regola «ATTIVA o CHIUSA» fuori dalla sede unica');

-- rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende): per le righe di
--   contratto e offerta la versione la chiede una sede sola,
--   vendite.fn_documento_listino_operativo. I quattro consumatori delle righe
--   (check dell'esclusione, guard dell'aggiunta, lista delle righe, righe
--   espanse dell'offerta) chiamano il risolutore.
-- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.3): fra le due
--   c'e' vendite.fn_listino_versione_operativa, «la fissata, altrimenti quella
--   in vigore oggi» sui VALORI della testata. La chiamano il risolutore delle
--   righe, la check del congelamento e i due guard che congelano (emissione
--   dell'offerta, attivazione del contratto). Chiedono questa funzione
--   direttamente solo lei e il risolutore dei prezzi.
SELECT is(
    (SELECT count(*)::integer FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE ((n.nspname, p.proname) IN (
              ('vendite', 'fn_listino_versione_operativa'),
              ('vendite', 'fn_resolve_prezzo_listino_v2_esito'))
             AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'fn_listino_versione_in_vigore\s*\(')
         OR ((n.nspname, p.proname) IN (
              ('vendite', 'fn_documento_listino_operativo'),
              ('script',  'fn_check_listino_congelabile'),
              ('vendite', 'trgfn_offerte_commerciali_guard_transizione'),
              ('vendite', 'trgfn_contratti_freeze_listino_versione'))
             AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'fn_listino_versione_operativa\s*\(')
         OR ((n.nspname, p.proname) IN (
              ('script',  'fn_check_esclusione_articolo_documento'),
              -- rev 2026-10-13 (sera): al posto del guard ritirato
              --   trgfn_righe_guard_aggiunta_fuori_listino (20261013-57), la check
              --   per tipo di riga che ne ha preso la regola.
              -- rev 2026-10-14 (Lotto 4, 20261014-01): la check legge il
              --   documento una volta, nel suo contesto: il consumatore e'
              --   script.fn_articolo_riga_contesto, non piu' la check.
              ('script',  'fn_articolo_riga_contesto'),
              ('vendite', 'fn_documento_righe_preview'),
              ('vendite', 'fn_offerta_righe_espanse'))
             AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'fn_documento_listino_operativo\s*\(')),
    10,
    '13) i consumatori chiedono la versione alla sede unica: due direttamente, quattro dalla regola sui valori, quattro dal risolutore delle righe');

SELECT * FROM finish();
ROLLBACK;
