-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
-- ------------------------------------------------------------
-- Test: l'articolo ritirato (catalogo.articoli.obsoleto_dal) nei casi che NON passano da un verbo
--   di derivazione. brief-db-articoli-obsoleto-dal §3, §4, §7.3 (lotti A, C, D), 2026-11-06.
--
--   · la vista dell'articolo dice se e' ritirato alla data operativa (e_obsoleto, BB script.fn_e_obsoleto);
--   · la riga NUOVA di listino su un articolo ritirato e' respinta (E_ARTICOLO_OBSOLETO, lotto A);
--     il ritiro programmato (data futura) passa;
--   · la copia di una versione di listino salta la riga, il kit e i componenti dell'articolo ritirato
--     (O-6) e lo conta in righe_saltate;
--   · il kit nuovo su un articolo ritirato e' respinto; quello esistente si modifica (O-2);
--   · l'ONERE scelto a mano (porta oneri, senza sorgente) e' respinto; quello CON sorgente (dal push)
--     e' derivato e passa; quello gia' inserito si riscrive (O-9).
--
--   ⚠️ FUORI da qui le righe DERIVATE dai verbi (push, revisione, bolle): aspettano il lotto B, che si
--   riscrive sul modello di brief-db-sorgente-documento-e-riga. L'ONERE con sorgente si costruisce
--   copiando la riga della porta oneri con una sorgente d'ordine: l'esenzione legge solo «la sorgente
--   c'e'», non la forma della chiave.
-- ------------------------------------------------------------
BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(17);

CREATE OR REPLACE FUNCTION pg_temp.tip(p text) RETURNS smallint LANGUAGE sql STABLE AS
$fx$ SELECT t.id FROM config.listini_tipologie t WHERE t.codice = p $fx$;

CREATE OR REPLACE FUNCTION pg_temp.msg(p_codice text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT split_part(m.messaggio, '%s', 1) || '%' FROM config.messaggi_errore m
   WHERE m.codice = p_codice AND m.lingua = 'it'
$fx$;

-- ===== fixture: listino, versione, articoli =====
CREATE TEMP TABLE tmp_ar_mondo AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('articolo ritirato');

CREATE TEMP TABLE tmp_ar_lst AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
  SELECT 'PGTAP_AR_' || substr(md5(clock_timestamp()::text || random()::text), 1, 10),
         'Fixture pgTAP: articolo ritirato', (SELECT utility_id FROM tmp_ar_mondo),
         pg_temp.tip('QUOTA_FISSA'), script.fn_pgtap_emittente_sr_operatore()
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_ar_ver AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
  SELECT id, 'PGTAP_V1', date '2026-01-01' FROM tmp_ar_lst
  RETURNING id)
SELECT * FROM ins;

CREATE OR REPLACE FUNCTION pg_temp.ver() RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_ar_ver $fx$;

-- Q resta; R (riga) e K (kit, composito) si ritirano ieri; N fra trenta giorni (programmato).
CREATE TEMP TABLE tmp_ar_art AS
SELECT v.s, dbops.fn_pgtap_crea_articolo('PGTAP-AR-' || v.s,
         p_listino_tipologia_id => pg_temp.tip('QUOTA_FISSA'),
         p_is_composito         => v.s = 'K') AS id
  FROM (VALUES ('Q'), ('R'), ('K'), ('F1'), ('N')) v(s);

CREATE OR REPLACE FUNCTION pg_temp.art(p text) RETURNS uuid LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_ar_art WHERE s = p $fx$;

INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
VALUES (pg_temp.art('K'), pg_temp.art('F1'), 1, '2020-01-01');

DO $fx$ BEGIN
  PERFORM dbops.fn_pgtap_listino_aggiungi_articoli(pg_temp.ver(), ARRAY[pg_temp.art('Q'), pg_temp.art('R')], 100);
END $fx$;
UPDATE vendite.listini_righe SET periodicita = 'MENSILE' WHERE listino_versione_id = pg_temp.ver();

INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,
       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal)
SELECT pg_temp.ver(), ac.id, ac.prodotto_id, ac.componente_id, 10, date '2026-01-01'
  FROM catalogo.articoli_componenti ac
 WHERE ac.prodotto_id = pg_temp.art('K');
INSERT INTO vendite.listini_kit (listino_versione_id, articolo_padre_id, periodicita)
VALUES (pg_temp.ver(), pg_temp.art('K'), 'TRIMESTRALE');

-- ===== la vista =====
SELECT has_column('catalogo', 'vw_articoli_dettaglio', 'obsoleto_dal', '1) vw_articoli_dettaglio.obsoleto_dal');
SELECT has_column('catalogo', 'vw_articoli_dettaglio', 'e_obsoleto', '2) vw_articoli_dettaglio.e_obsoleto');

SELECT is(
  (SELECT bool_or(v.e_obsoleto) FROM catalogo.vw_articoli_dettaglio v WHERE v.id IN (SELECT id FROM tmp_ar_art)),
  false,
  '3) prima del ritiro nessun articolo della fixture e'' ritirato');

UPDATE catalogo.articoli SET obsoleto_dal = script.fn_data_operativa() - 1
 WHERE id IN (pg_temp.art('R'), pg_temp.art('K'));
UPDATE catalogo.articoli SET obsoleto_dal = script.fn_data_operativa() + 30
 WHERE id = pg_temp.art('N');

SELECT is(
  (SELECT string_agg(v.codice || '=' || v.e_obsoleto::text, ',' ORDER BY v.codice)
     FROM catalogo.vw_articoli_dettaglio v WHERE v.id IN (pg_temp.art('R'), pg_temp.art('K'), pg_temp.art('N'))),
  'PGTAP-AR-K=true,PGTAP-AR-N=false,PGTAP-AR-R=true',
  '4) e_obsoleto alla data operativa: ritirato ieri = true, ritiro programmato = false');

-- ===== la copia della versione (O-6) =====
CREATE TEMP TABLE tmp_ar_clone AS
SELECT * FROM vendite.fn_clona_versione_listino(pg_temp.ver(), 'PGTAP_V2', date '2027-01-01', NULL);

SELECT is(
  (SELECT format('%s|%s|%s|%s', c.righe_copiate, c.righe_saltate, c.componenti_copiati, c.componenti_saltati)
     FROM tmp_ar_clone c),
  '1|1|0|1',
  '5) la copia salta la riga e il componente dell''articolo ritirato, e lo conta');

SELECT is(
  (SELECT string_agg(a.codice, ',' ORDER BY a.codice)
     FROM vendite.listini_righe r JOIN catalogo.articoli a ON a.id = r.articolo_id
    WHERE r.listino_versione_id = (SELECT versione_id FROM tmp_ar_clone)),
  'PGTAP-AR-Q',
  '6) sulla versione nuova resta solo l''articolo vivo');

SELECT is(
  (SELECT count(*)::int FROM vendite.listini_kit k WHERE k.listino_versione_id = (SELECT versione_id FROM tmp_ar_clone)),
  0,
  '7) il kit dell''articolo ritirato non si copia');

-- ===== la riga nuova di listino (lotto A) =====
SELECT throws_like(
  format($$SELECT dbops.fn_pgtap_listino_aggiungi_articoli(%s, ARRAY[%L::uuid], 50)$$,
         (SELECT versione_id FROM tmp_ar_clone), pg_temp.art('R')),
  pg_temp.msg('E_ARTICOLO_OBSOLETO'),
  '8) riga nuova di listino su un articolo ritirato: E_ARTICOLO_OBSOLETO');

SELECT lives_ok(
  format($$SELECT dbops.fn_pgtap_listino_aggiungi_articoli(%s, ARRAY[%L::uuid], 50)$$,
         (SELECT versione_id FROM tmp_ar_clone), pg_temp.art('N')),
  '9) riga nuova su un ritiro programmato (data futura): passa');

-- ===== il kit (O-2) =====
SELECT throws_like(
  format($$INSERT INTO vendite.listini_kit (listino_versione_id, articolo_padre_id, periodicita)
           VALUES (%s, %L, 'MENSILE')$$, (SELECT versione_id FROM tmp_ar_clone), pg_temp.art('K')),
  pg_temp.msg('E_CATALOGO_OBSOLETO_NUOVA_ISTANZA'),
  '10) kit nuovo su un articolo ritirato: E_CATALOGO_OBSOLETO_NUOVA_ISTANZA');

SELECT lives_ok(
  format($$UPDATE vendite.listini_kit SET periodicita = 'MENSILE' WHERE listino_versione_id = %s$$, pg_temp.ver()),
  '11) il kit esistente, il cui articolo e'' poi ritirato, si modifica');

-- ===== l'onere di commessa (O-9) =====
CREATE TEMP TABLE tmp_ar_cli AS SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('articolo ritirato onere');

CREATE TEMP TABLE tmp_ar_comm AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_ar_cli),
  p_utility_id             => (SELECT utility_id FROM tmp_ar_cli),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-07-01',
  p_competenza_al          => DATE '2026-07-31',
  p_meta                   => jsonb_build_object('test_scope', 'pgtap_articolo_ritirato'),
  p_force_new              => true
) AS commessa_id;

CREATE TEMP TABLE tmp_ar_onere AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id         => (SELECT commessa_id FROM tmp_ar_comm),
  p_istanza_utility_id  => (SELECT istanza_utility_id FROM tmp_ar_cli),
  p_articolo_onere_id   => (SELECT id FROM catalogo.articoli WHERE codice = 'ONERE_TRASFERTA'),
  p_importo             => 10,
  p_tipo_doc_fiscale_id => (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1)
) AS attivita_id;

UPDATE catalogo.articoli SET obsoleto_dal = script.fn_data_operativa() - 1 WHERE codice = 'ONERE_TRASFERTA';

SELECT throws_like(
  format($$SELECT vendite.fn_aggiungi_onere_commessa(
             p_commessa_id => %s, p_istanza_utility_id => %s,
             p_articolo_onere_id => %L::uuid, p_importo => 10, p_tipo_doc_fiscale_id => %s)$$,
         (SELECT commessa_id FROM tmp_ar_comm), (SELECT istanza_utility_id FROM tmp_ar_cli),
         (SELECT id FROM catalogo.articoli WHERE codice = 'ONERE_TRASFERTA'),
         (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1)),
  pg_temp.msg('E_CATALOGO_OBSOLETO_NUOVA_ISTANZA'),
  '12) onere dalla porta su un articolo-onere ritirato: E_CATALOGO_OBSOLETO_NUOVA_ISTANZA');

SELECT lives_ok(
  format($$UPDATE vendite.commesse_attivita SET articolo_id = articolo_id WHERE id = %s$$,
         (SELECT attivita_id FROM tmp_ar_onere)),
  '13) l''onere gia'' inserito, con l''articolo poi ritirato, si riscrive uguale');

-- La stessa riga copiata con (o senza) una sorgente d'ordine: e' il caso dell'onere dal push.
-- L'ordine lo costruisce il test: da zero non ce n'e' nessuno (rev 2026-11-06, rosso sullo scratch).
CREATE TEMP TABLE tmp_ar_ord AS SELECT * FROM dbops.fn_pgtap_crea_ordine('articolo ritirato onere');

CREATE OR REPLACE FUNCTION pg_temp.copia_onere(p_con_sorgente boolean, p_suffisso text)
RETURNS void LANGUAGE plpgsql AS $fx$
DECLARE
  v_cols text;
  v_src  jsonb;
BEGIN
  SELECT string_agg(quote_ident(a.attname), ',' ORDER BY a.attnum) INTO v_cols
    FROM pg_attribute a
   WHERE a.attrelid = 'vendite.commesse_attivita'::regclass AND a.attnum > 0 AND NOT a.attisdropped
     AND a.attname <> 'id' AND a.attgenerated = '';
  SELECT to_jsonb(ca) || jsonb_build_object(
           'sorgente_tipo_id', CASE WHEN p_con_sorgente
                                    THEN (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA') END,
           'sorgente_uid',     CASE WHEN p_con_sorgente
                                    THEN (SELECT o.ordine_uid::text FROM tmp_ar_ord o) END,
           'segment_key',      ca.segment_key || p_suffisso,
           'tx_id',            NULL)
    INTO v_src
    FROM vendite.commesse_attivita ca WHERE ca.id = (SELECT attivita_id FROM tmp_ar_onere);
  EXECUTE format('INSERT INTO vendite.commesse_attivita (%s) SELECT %s FROM jsonb_populate_record(NULL::vendite.commesse_attivita, $1)',
                 v_cols, v_cols) USING v_src;
END $fx$;

SELECT lives_ok(
  $$SELECT pg_temp.copia_onere(true, ':PGTAP_AR_1')$$,
  '14) onere CON sorgente (derivato) su un articolo ritirato: passa');

SELECT throws_like(
  $$SELECT pg_temp.copia_onere(false, ':PGTAP_AR_2')$$,
  pg_temp.msg('E_CATALOGO_OBSOLETO_NUOVA_ISTANZA'),
  '15) la stessa riga SENZA sorgente: respinta');

-- ===== montaggio e privilegi =====
SELECT ok(
  (SELECT pg_get_triggerdef(t.oid) ~ $re$WHEN \(\(\(new\.tipo_movimento\)::text = 'ONERE'::text\)\)$re$
      AND pg_get_triggerdef(t.oid) ~ $re$'sorgente_tipo_id'\)$re$
     FROM pg_trigger t
    WHERE t.tgrelid = 'vendite.commesse_attivita'::regclass
      AND t.tgname = 'trg_commesse_attivita_a10_onere_articolo_non_obsoleto_ins_upd'),
  '16) il guard dell''onere scatta solo su ONERE ed esenta la riga con sorgente');

SELECT ok(
  has_function_privilege('zeroerp_app', 'vendite.fn_clona_versione_listino(bigint,character varying,date,date)', 'EXECUTE')
  AND NOT EXISTS (SELECT 1 FROM pg_proc p, aclexplode(p.proacl) x
                   WHERE p.oid = 'vendite.fn_clona_versione_listino(bigint,character varying,date,date)'::regprocedure
                     AND x.grantee = 0),
  '17) la copia, ricreata: EXECUTE all''applicazione, non a PUBLIC');

SELECT * FROM finish();
ROLLBACK;
