-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un documento che somma negativo e' una nota di credito
--       (vendite.fn_lotto_natura_dal_segno, 20261031-45), la marca torna
--       indietro (vendite.fn_libera_attivita_fatturabili, -46) e la nota di
--       credito degli storni cita le fatture che corregge
--       (vendite.fn_popola_fatture_rettifiche, -48).
--       Brief: brief-db-contratto-righe-periodiche-in-commessa §7.1 e §7.7
--       (D-1, D-1-bis, D-1-ter di Tid, 2026-10-31; L17).
--
-- ⭐ TUTTO COSTRUITO. Le attivita' di commessa dal builder, emesse dalla madre,
--   messe nel lotto come le mette il giro (lucchetto del lotto, non fatturate):
--   e' il punto in cui il backend chiama il verbo, prima delle testate. Un
--   lotto per scenario: dentro un lotto le attivita' dello stesso conto hanno
--   la stessa chiave, cioe' vanno nello stesso documento.
--
-- Indice test (1..11):
--   1) soli storni (-300): l'attivita' diventa NOTA_CREDITO, con la marca
--   2) e la testata nasce nota di credito
--   3) misto a totale negativo (-300 + 50): tutte e due NOTA_CREDITO, una testata sola
--   4) misto a totale positivo (+300 - 50): resta FATTURA, nessuna marca
--   5) D-1-bis: l'attivita' nata NOTA_CREDITO (come l'accredito del reso) non si
--      tocca e non prende la marca; il suo vicino positivo resta FATTURA
--   6) rieseguibile: con un addebito in piu' il gruppo torna positivo, il verbo
--      ritira la marca e lo storno torna FATTURA
--   7) libera: l'attivita' battezzata dal segno riprende la natura FATTURA
--   8) ⛔ un lotto che non c'e': E_LOTTO_NON_TROVATO
--   9) D-1-ter: la nota di credito dello storno di un pezzo gia' fatturato...
--  10) ...cita la fattura di quel pezzo (vendite.fatture_rettifiche)
--  11) e la proiezione e' idempotente: un secondo giro non aggiunge niente
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

-- ============================================================
-- FIXTURE
-- ============================================================
-- Scopo: il prefisso fisso del messaggio di un codice, per throws_like.
CREATE OR REPLACE FUNCTION pg_temp.msg(p_codice text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT split_part(m.messaggio, '%s', 1) || '%' FROM config.messaggi_errore m
   WHERE m.codice = p_codice AND m.lingua = 'it'
$fx$;

CREATE TEMP TABLE tmp_ns_comm AS
SELECT v.k, c.*
  FROM (VALUES ('M1'), ('M2')) v(k),
       LATERAL dbops.fn_pgtap_crea_commessa('natura dal segno ' || v.k, p_con_attivita => false,
                                           p_con_sorgente_root => true) c;

CREATE OR REPLACE FUNCTION pg_temp.comm(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT commessa_id FROM tmp_ns_comm WHERE k = p $fx$;

-- Scopo: un'attivita' di commessa (quantita' x prezzo) emessa dalla madre;
--   ritorna l'attivita' fatturabile.
CREATE OR REPLACE FUNCTION pg_temp.af(p_comm text, p_qta numeric, p_prezzo numeric)
RETURNS bigint LANGUAGE plpgsql AS $fx$
DECLARE
  v_ca bigint;
  v_af bigint;
BEGIN
  SELECT a.attivita_id INTO v_ca
    FROM dbops.fn_pgtap_crea_commessa_attivita(pg_temp.comm(p_comm), p_prezzo,
           p_quantita => p_qta) a;
  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa(p_commessa_id => pg_temp.comm(p_comm));
  SELECT af.id INTO v_af FROM vendite.attivita_fatturabili af
   WHERE af.commessa_attivita_id = v_ca ORDER BY af.id DESC LIMIT 1;
  RETURN v_af;
END $fx$;

-- I lotti, uno per scenario, sul conto della commessa M1.
CREATE TEMP TABLE tmp_ns_lotti AS
SELECT v.k, l.*
  FROM (VALUES ('L1'), ('L2'), ('L3'), ('L4'), ('L5')) v(k),
       LATERAL dbops.fn_pgtap_crea_lotto('natura dal segno ' || v.k, 'DRAFT',
                 (SELECT billing_account_id FROM tmp_ns_comm WHERE k = 'M1')) l;

CREATE OR REPLACE FUNCTION pg_temp.lotto(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT lotto_id FROM tmp_ns_lotti WHERE k = p $fx$;

-- Scopo: mettere delle attivita' nel lotto, come il giro (lucchetto del lotto).
CREATE OR REPLACE FUNCTION pg_temp.nel_lotto(p_lotto text, p_af bigint[]) RETURNS void
LANGUAGE sql AS $fx$
  UPDATE vendite.attivita_fatturabili af
     SET lock_in_fatturazione = true,
         lock_batch_id = (SELECT lock_batch_id FROM tmp_ns_lotti WHERE k = p_lotto)
   WHERE af.id = ANY (p_af);
$fx$;

CREATE OR REPLACE FUNCTION pg_temp.natura(p_af bigint) RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT n.codice_interno || '|' || af.natura_dal_segno::text
    FROM vendite.attivita_fatturabili af
    JOIN config.nature_doc_fiscale n ON n.id = af.natura_doc_id
   WHERE af.id = p_af;
$fx$;

CREATE TEMP TABLE tmp_ns_af (k text PRIMARY KEY, id bigint);
INSERT INTO tmp_ns_af VALUES
  ('A', pg_temp.af('M1', -1, 300)),                                -- L1: solo storno
  ('B', pg_temp.af('M1', -1, 300)), ('C', pg_temp.af('M1', 1, 50)), -- L2: misto negativo
  ('D', pg_temp.af('M1', 1, 300)),  ('E', pg_temp.af('M1', -1, 50)),-- L3: misto positivo
  ('F', pg_temp.af('M1', -1, 100)), ('G', pg_temp.af('M1', 1, 300)),-- L4: nata NC + positivo
  ('H', pg_temp.af('M1', -1, 300));                                 -- L5: rieseguibile
CREATE OR REPLACE FUNCTION pg_temp.a(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_ns_af WHERE k = p $fx$;

-- F nasce NOTA_CREDITO, come l'accredito di un reso (D-1-bis).
UPDATE vendite.attivita_fatturabili SET natura_doc_id = config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO')
 WHERE id = pg_temp.a('F');

SELECT pg_temp.nel_lotto('L1', ARRAY[pg_temp.a('A')]);
SELECT pg_temp.nel_lotto('L2', ARRAY[pg_temp.a('B'), pg_temp.a('C')]);
SELECT pg_temp.nel_lotto('L3', ARRAY[pg_temp.a('D'), pg_temp.a('E')]);
SELECT pg_temp.nel_lotto('L4', ARRAY[pg_temp.a('F'), pg_temp.a('G')]);
SELECT pg_temp.nel_lotto('L5', ARRAY[pg_temp.a('H')]);

CREATE TEMP TABLE tmp_ns_esito AS
SELECT k, vendite.fn_lotto_natura_dal_segno(lotto_id) AS n FROM tmp_ns_lotti;

-- ============================================================
-- I casi di D-1
-- ============================================================
SELECT is(
  pg_temp.natura(pg_temp.a('A')) || '|' || (SELECT n FROM tmp_ns_esito WHERE k = 'L1'),
  'NOTA_CREDITO|true|1',
  '1) soli storni: l''attivita'' diventa NOTA_CREDITO, con la marca');

-- ⚠️ La testata si crea in un'istruzione a parte: la SELECT che la legge
--   nella stessa istruzione la vedrebbe con la fotografia di prima (NULL).
CREATE TEMP TABLE tmp_ns_h1 AS
SELECT vendite.fn_get_or_create_fattura_header(pg_temp.lotto('L1'), pg_temp.a('A')) AS fattura_id;
SELECT is(
  (SELECT n.codice_interno FROM vendite.fatture f
     JOIN config.nature_doc_fiscale n ON n.id = f.natura_doc_id
    WHERE f.id = (SELECT fattura_id FROM tmp_ns_h1)),
  'NOTA_CREDITO',
  '2) e la testata nasce nota di credito, dalla chiave');

SELECT ok(
  pg_temp.natura(pg_temp.a('B')) = 'NOTA_CREDITO|true'
  AND pg_temp.natura(pg_temp.a('C')) = 'NOTA_CREDITO|true'
  AND vendite.fn_get_or_create_fattura_header(pg_temp.lotto('L2'), pg_temp.a('B'))
      = vendite.fn_get_or_create_fattura_header(pg_temp.lotto('L2'), pg_temp.a('C')),
  '3) misto a totale negativo (-300 + 50): tutte e due NOTA_CREDITO, nello stesso documento');

SELECT is(
  pg_temp.natura(pg_temp.a('D')) || ' ' || pg_temp.natura(pg_temp.a('E'))
  || ' ' || (SELECT n FROM tmp_ns_esito WHERE k = 'L3'),
  'FATTURA|false FATTURA|false 0',
  '4) misto a totale positivo (+300 - 50): resta FATTURA, nessuna marca');

SELECT is(
  pg_temp.natura(pg_temp.a('F')) || ' ' || pg_temp.natura(pg_temp.a('G')),
  'NOTA_CREDITO|false FATTURA|false',
  '5) D-1-bis: l''attivita'' nata NOTA_CREDITO non prende la marca, il vicino positivo resta FATTURA');

-- Rieseguibile: H da sola e' negativa; con un addebito di 500 il gruppo e' positivo.
INSERT INTO tmp_ns_af VALUES ('J', pg_temp.af('M1', 1, 500));
SELECT pg_temp.nel_lotto('L5', ARRAY[pg_temp.a('J')]);
-- ⚠️ Il verbo in un'istruzione a parte, poi la lettura (fotografia dell'istruzione).
CREATE TEMP TABLE tmp_ns_l5 AS
SELECT pg_temp.natura(pg_temp.a('H')) AS prima;
UPDATE tmp_ns_l5 SET prima = prima || ' ' || vendite.fn_lotto_natura_dal_segno(pg_temp.lotto('L5'))::text;
SELECT is(
  (SELECT prima FROM tmp_ns_l5) || ' ' || pg_temp.natura(pg_temp.a('H')),
  'NOTA_CREDITO|true 0 FATTURA|false',
  '6) rieseguibile: con un addebito in piu'' il gruppo torna positivo e la marca si ritira');

CREATE TEMP TABLE tmp_ns_lib AS
SELECT x.updated_attivita FROM vendite.fn_libera_attivita_fatturabili(ARRAY[pg_temp.a('B')]) x;
SELECT is(
  (SELECT updated_attivita FROM tmp_ns_lib)::text || ' ' || pg_temp.natura(pg_temp.a('B')),
  '1 FATTURA|false',
  '7) libera: l''attivita'' battezzata dal segno riprende la natura FATTURA');

SELECT throws_like(
  'SELECT vendite.fn_lotto_natura_dal_segno(999999999)',
  pg_temp.msg('E_LOTTO_NON_TROVATO'),
  '8) un lotto che non c''e'': E_LOTTO_NON_TROVATO');

-- ============================================================
-- D-1-ter: la nota di credito cita le fatture
-- ============================================================
-- Il pezzo P (+300) fatturato a gennaio, in bozza: basta che la riga ci sia.
CREATE TEMP TABLE tmp_ns_p AS
SELECT a.attivita_id
  FROM dbops.fn_pgtap_crea_commessa_attivita(pg_temp.comm('M2'), 300, p_quantita => 1) a;
CREATE TEMP TABLE tmp_ns_f0 AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('natura dal segno F0',
                ARRAY[(SELECT attivita_id FROM tmp_ns_p)]);

-- Lo storno di P (-300), come lo scrive il lister: il meta nomina il pezzo.
CREATE TEMP TABLE tmp_ns_s AS
SELECT a.attivita_id
  FROM dbops.fn_pgtap_crea_commessa_attivita(pg_temp.comm('M2'), 300, p_quantita => -1) a;
UPDATE vendite.commesse_attivita
   SET meta = meta || jsonb_build_object('movimento', 'STORNO_CANONE',
                                         'storno_di_attivita_id', (SELECT attivita_id FROM tmp_ns_p))
 WHERE id = (SELECT attivita_id FROM tmp_ns_s);

CREATE TEMP TABLE tmp_ns_l6 AS
SELECT * FROM dbops.fn_pgtap_crea_lotto('natura dal segno L6', 'DRAFT',
                (SELECT billing_account_id FROM tmp_ns_comm WHERE k = 'M2'));
DO $fx$ BEGIN
  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa(p_commessa_id => pg_temp.comm('M2'));
END $fx$;
UPDATE vendite.attivita_fatturabili af
   SET lock_in_fatturazione = true, lock_batch_id = (SELECT lock_batch_id FROM tmp_ns_l6)
 WHERE af.commessa_attivita_id = (SELECT attivita_id FROM tmp_ns_s);
SELECT vendite.fn_lotto_natura_dal_segno((SELECT lotto_id FROM tmp_ns_l6));

-- La nota di credito: testata dalla chiave, riga dello storno e aggancio, come il giro.
CREATE TEMP TABLE tmp_ns_nc AS
SELECT vendite.fn_get_or_create_fattura_header(
         (SELECT lotto_id FROM tmp_ns_l6),
         (SELECT af.id FROM vendite.attivita_fatturabili af
           WHERE af.commessa_attivita_id = (SELECT attivita_id FROM tmp_ns_s))) AS fattura_id;
CREATE TEMP TABLE tmp_ns_nc_riga AS
WITH ins AS (
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione, uom_id,
         qta, prezzo_unitario, iva_id, imponibile_riga, competenza_dal, competenza_al, meta)
  SELECT (SELECT fattura_id FROM tmp_ns_nc), 1, af.articolo_id, 'Fixture pgTAP: storno', af.uom_id,
         af.quantita, af.prezzo_unitario,
         (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1),
         af.quantita * af.prezzo_unitario, af.competenza_dal, af.competenza_al,
         jsonb_build_object('test_scope', 'pgtap_natura_dal_segno')
    FROM vendite.attivita_fatturabili af
   WHERE af.commessa_attivita_id = (SELECT attivita_id FROM tmp_ns_s)
  RETURNING id)
SELECT id FROM ins;
UPDATE vendite.attivita_fatturabili af
   SET fattura_riga_id = (SELECT id FROM tmp_ns_nc_riga)
 WHERE af.commessa_attivita_id = (SELECT attivita_id FROM tmp_ns_s);

SELECT is(
  (SELECT n.codice_interno FROM vendite.fatture f
     JOIN config.nature_doc_fiscale n ON n.id = f.natura_doc_id
    WHERE f.id = (SELECT fattura_id FROM tmp_ns_nc)),
  'NOTA_CREDITO',
  '9) D-1-ter: lo storno di un pezzo fatturato nasce in una nota di credito');

CREATE TEMP TABLE tmp_ns_pop AS
SELECT vendite.fn_popola_fatture_rettifiche((SELECT fattura_id FROM tmp_ns_nc)) AS n;
SELECT is(
  (SELECT n FROM tmp_ns_pop)::text || '|'
  || (SELECT string_agg(r.rettificata_id::text, ',') FROM vendite.fatture_rettifiche r
       WHERE r.fattura_id = (SELECT fattura_id FROM tmp_ns_nc)),
  '1|' || (SELECT fattura_id FROM tmp_ns_f0)::text,
  '10) e cita la fattura del pezzo che storna (vendite.fatture_rettifiche)');

SELECT is(vendite.fn_popola_fatture_rettifiche((SELECT fattura_id FROM tmp_ns_nc)), 0,
  '11) la proiezione e'' idempotente: un secondo giro non aggiunge niente');

SELECT * FROM finish();
ROLLBACK;
