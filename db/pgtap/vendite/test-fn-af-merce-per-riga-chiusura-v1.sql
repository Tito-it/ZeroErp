-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §14, giro 10): il passaggio a PRONTA_FATTURAZIONE dal verbo chiede l'azione cambia_stato_commessa: il file prova il conto, non il permesso, e la concede all'utente del contesto.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_af_merce_per_riga — il contatore delle attivita'
--       fatturabili per riga di documento, letto PER CHIAVE DI SEGMENTO
--       (D14 giro 4 — D5; brief-db-partita-merce-per-documento §11;
--        changeSet 20260921-50..-54).
--
-- Indice test (plan 13):
--   1) la funzione esiste, e' BEGIN ATOMIC (dipendenze nel catalogo) e NON e'
--      SECURITY DEFINER (la RLS resta di chi legge)
--   2) ⭐ pin di D1: la vista e' la PROIEZIONE della funzione — nomina
--      fn_af_merce_per_riga e nessuna tabella
--   3) ⭐ pin dei tipi: 7 colonne e tipo_movimento varchar(32) — il RETURNS
--      TABLE lo perde, la vista lo ricasta per nome
--   4) ⭐ pin dell'indice: ix_commesse_attivita_segment_key ha l'opclass
--      varchar_pattern_ops — senza, il range a byte non ha da dove partire
--   5) chiave semplice DDT: NORMALE 12 e RETTIFICA -4 (il suffisso #RET:1 entra
--      dalla chiave BASE), esattamente due righe
--   6) ⭐ IL VICINO NUMERICO: la chiave :R:900001 NON prende :R:9000010, e la
--      chiave :R:90000 (prefisso di un numero che esiste) non prende niente —
--      e' il caso che distingue il range a byte da un prefisso ingenuo
--   7) kit #CMP con coefficienti 2 / 1 / 0.5: quantita 10 in unita' del PADRE,
--      da_componenti, misurabile, UNA voce (l'istanza di kit, non i tre
--      componenti) — i suffissi entrano dalla base
--   8) stesso numero di riga su corsia ORD: la chiave ORD prende la sua riga
--      sola, la chiave DDT non la vede (le due sequenze)
--   9) suffisso ignoto (#FOO): la base e' cio' che precede il primo '#', come
--      la vista lo conta oggi — 5 + 6 = 11
--  10) ⭐ equivalenza: per OGNI chiave costruita fn(ARRAY[k]) = vista filtrata
--      su (corsia, riga_id), EXCEPT ALL nei due versi
--  11) ⭐ normalizzazione: la chiave ripetuta, e passata anche col suffisso
--      accanto alla base, NON raddoppia la somma
--  12) niente da seminare: array VUOTO e chiave inesistente -> zero righe
--      (vuoto NON e' «tutte»)
--  13) scope: chi non vede la commessa non vede il conto — zero righe
--
-- Scopo:
--  - la lettura per chiave e' «equivalente per costruzione» alla vista, e
--    questo file la prova COSTRUENDO le chiavi in cui la forma del predicato
--    sbaglierebbe: il vicino numerico (6), i suffissi (5, 7, 9), le corsie (8),
--    i duplicati (11). Le riga_id sono numeri ALTI e inventati: la funzione
--    non dereferenzia niente, e il test non collide con righe vere.
--  - ⛔ il predicato NON e' un LIKE, e non deve tornarlo: sotto la policy RLS
--    di commesse_attivita un LIKE non diventa mai Index Cond (textlike non e'
--    leakproof). La forma e' `= k OR (~>=~ k||'#' AND ~<~ k||'$')` con i bordi
--    precalcolati; il 4 pinna l'indice che la serve.
--  - ⭐ il mondo (cliente, articolo) e' COSTRUITO dai builder di dbops, non
--    cercato: il file deve girare identico su dbdev e su un database da zero.
--  - il 13 e' rosso da OWNER per costruzione (l'owner salta la RLS) e verde
--    come app: sta per ultimo perche' cambia il contesto.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);

-- ============================================================
-- 1-4) Struttura: funzione, pin di D1, pin dei tipi, pin dell'indice
-- ============================================================
SELECT ok(
  (SELECT p.prosqlbody IS NOT NULL AND NOT p.prosecdef
     FROM pg_proc p
    WHERE p.proname = 'fn_af_merce_per_riga' AND p.pronamespace = 'vendite'::regnamespace),
  '1) fn_af_merce_per_riga esiste, e'' BEGIN ATOMIC (dipendenze in pg_depend) e non e'' SECURITY DEFINER');

SELECT ok(
  (SELECT d ~ 'fn_af_merce_per_riga' AND d !~ 'commesse_attivita' AND d !~ 'attivita_fatturabili'
     FROM pg_get_viewdef('vendite.vw_af_merce_per_riga'::regclass, true) AS d),
  '2) la vista e'' la proiezione di fn_af_merce_per_riga: nomina la funzione e nessuna tabella');

SELECT is(
  (SELECT count(*)::int || '|' || max(format_type(a.atttypid, a.atttypmod)) FILTER (WHERE a.attname = 'tipo_movimento')
     FROM pg_attribute a
    WHERE a.attrelid = 'vendite.vw_af_merce_per_riga'::regclass AND a.attnum > 0 AND NOT a.attisdropped),
  '7|character varying(32)',
  '3) la vista ha 7 colonne e tipo_movimento resta varchar(32)');

SELECT is(
  (SELECT string_agg(oc.opcname, ',' ORDER BY k.ord)
     FROM pg_index i
     CROSS JOIN LATERAL unnest(i.indclass) WITH ORDINALITY AS k(opc, ord)
     JOIN pg_opclass oc ON oc.oid = k.opc
    WHERE i.indexrelid = 'vendite.ix_commesse_attivita_segment_key'::regclass),
  'varchar_pattern_ops',
  '4) ix_commesse_attivita_segment_key ha l''opclass varchar_pattern_ops (il range a byte lo usa; un btree it_IT no)');

-- ============================================================
-- Il mondo si COSTRUISCE, non si cerca. Cliente e articolo dai builder di
-- dbops; la commessa via fn_get_or_create_commessa sul BA costruito (cosi'
-- e' nello scope dell'operatore del contesto). Le attivita' portano chiavi
-- di segmento INVENTATE con riga_id alti: la funzione non dereferenzia.
-- ============================================================
CREATE TEMP TABLE tmp_cli_afk AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_af_chiave');

CREATE TEMP TABLE tmp_refs_afk AS
SELECT
  c.billing_account_id,
  c.utility_id,
  c.istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-AFK-ART', false)                                        AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)   AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA' AND s.attivo ORDER BY s.id LIMIT 1) AS sorgente_root_id
FROM tmp_cli_afk c;

-- I prefissi di segmento, calcolati UNA volta: i componenti di uno stesso
-- kit devono condividere l'istanza.
CREATE TEMP TABLE tmp_seg_afk AS
SELECT gen_random_uuid() AS u_ddt,      -- 5, 6, 8, 11
       gen_random_uuid() AS u_kit,      -- 7
       gen_random_uuid() AS u_coll,     -- 8: ORD con lo stesso numero di riga
       gen_random_uuid() AS u_foo;      -- 9

CREATE TEMP TABLE tmp_com_afk AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_afk),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_afk),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-08-01',
  p_competenza_al          => DATE '2026-08-31',
  p_meta                   => jsonb_build_object('test_scope','pgtap_af_chiave'),
  p_force_new              => true) AS commessa_id;

-- ROOT sorgente: l'emit pretende che esista.
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_com_afk),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs_afk),
  p_sorgente_uid     => (SELECT commessa_id FROM tmp_com_afk)::text,
  p_sorgente_riga    => 1,
  p_meta             => '{}'::jsonb);

-- Helper: un'attivita' con segment_key esplicita, tipo_movimento e meta.
CREATE OR REPLACE FUNCTION pg_temp.afk_mk(p_segment varchar, p_qta numeric,
                                          p_tipo_mov varchar, p_meta jsonb)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs_afk;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com_afk),
    -- La riga NORMALE ha la sua sorgente; ONERE e RETTIFICA no (vincolo 20261012-27).
    p_sorgente_tipo_id => CASE WHEN p_tipo_mov = 'NORMALE' THEN (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA') END,
    p_sorgente_uid => CASE WHEN p_tipo_mov = 'NORMALE' THEN ((SELECT commessa_id FROM tmp_com_afk))::text END,
    p_segment_key => p_segment,
    p_articolo_id => r.articolo_id,
    p_istanza_utility_id => r.istanza_utility_id,
    p_data_attivita => DATE '2026-08-15',
    p_uom_id => r.uom_id, p_quantita => p_qta,
    p_competenza_mese => DATE '2026-08-01',
    p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31',
    p_prezzo_snapshot => 10.0, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL,
    p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id,
    p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => p_tipo_mov,
    p_meta => p_meta);
END $$ LANGUAGE plpgsql;

-- Le chiavi del test, come le compone chi le passa: BASE, senza suffisso.
CREATE TEMP TABLE tmp_k AS
SELECT ('DDT_VENDITA:' || u_ddt::text  || ':R:900001')::varchar  AS k_ddt,
       ('DDT_VENDITA:' || u_ddt::text  || ':R:9000010')::varchar AS k_vicino,   -- 900001 e' un PREFISSO di 9000010
       ('DDT_VENDITA:' || u_ddt::text  || ':R:90000')::varchar   AS k_prefisso,  -- prefisso di 900001, non esiste
       ('ORDINE_VENDITA:' || u_kit::text  || ':R:900002')::varchar  AS k_kit,
       ('ORDINE_VENDITA:' || u_coll::text || ':R:900001')::varchar  AS k_coll,      -- stesso NUMERO, altra corsia
       ('DDT_VENDITA:' || u_foo::text  || ':R:900004')::varchar  AS k_foo
  FROM tmp_seg_afk;

-- 5, 6, 8: la riga DDT semplice, la sua rettifica, il vicino numerico
SELECT pg_temp.afk_mk((SELECT k_ddt    FROM tmp_k), 12, 'NORMALE',   '{}'::jsonb);
SELECT pg_temp.afk_mk((SELECT k_ddt    FROM tmp_k) || '#RET:1', -4, 'RETTIFICA', '{}'::jsonb);
SELECT pg_temp.afk_mk((SELECT k_vicino FROM tmp_k),  3, 'NORMALE',   '{}'::jsonb);
-- 7: il kit, tre coefficienti che concordano sul padre 10
SELECT pg_temp.afk_mk((SELECT k_kit FROM tmp_k) || '#CMP:c1', 20, 'NORMALE', jsonb_build_object('coeff_qta','2'));
SELECT pg_temp.afk_mk((SELECT k_kit FROM tmp_k) || '#CMP:c2', 10, 'NORMALE', jsonb_build_object('coeff_qta','1'));
SELECT pg_temp.afk_mk((SELECT k_kit FROM tmp_k) || '#CMP:c3',  5, 'NORMALE', jsonb_build_object('coeff_qta','0.5'));
-- 8: la collisione di numero fra corsie
SELECT pg_temp.afk_mk((SELECT k_coll FROM tmp_k), 7, 'NORMALE', '{}'::jsonb);
-- 9: il suffisso ignoto
SELECT pg_temp.afk_mk((SELECT k_foo FROM tmp_k),            5, 'NORMALE', '{}'::jsonb);
SELECT pg_temp.afk_mk((SELECT k_foo FROM tmp_k) || '#FOO:1', 6, 'NORMALE', '{}'::jsonb);

-- Emissione: nascono le attivita' fatturabili, che il conto legge.
-- rev 2026-10-26 (giro 10): «rendi pronta» chiede l'azione cambia_stato_commessa
-- (brief-modello-documento-vendita §14, C-1); questo file prova il conto della merce per riga, non il
-- permesso: la si concede all'utente del contesto.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');
SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com_afk), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com_afk));

-- Il confronto fn(ARRAY[k]) = vista filtrata su (corsia, riga_id), nei DUE versi.
CREATE OR REPLACE FUNCTION pg_temp.afk_diff(p_k varchar) RETURNS bigint AS $$
  SELECT (SELECT count(*) FROM (SELECT * FROM vendite.fn_af_merce_per_riga(ARRAY[p_k])
                                 EXCEPT ALL
                                SELECT * FROM vendite.vw_af_merce_per_riga v
                                 WHERE v.corsia = split_part(p_k, ':', 1)
                                   AND v.riga_id = substring(p_k FROM ':R:([0-9]+)')::bigint) a)
       + (SELECT count(*) FROM (SELECT * FROM vendite.vw_af_merce_per_riga v
                                 WHERE v.corsia = split_part(p_k, ':', 1)
                                   AND v.riga_id = substring(p_k FROM ':R:([0-9]+)')::bigint
                                 EXCEPT ALL
                                SELECT * FROM vendite.fn_af_merce_per_riga(ARRAY[p_k])) b);
$$ LANGUAGE sql;

-- ============================================================
-- 5) la chiave semplice: NORMALE 12 e RETTIFICA -4, due righe
-- ============================================================
SELECT results_eq(
  $q$SELECT f.tipo_movimento::text, f.quantita
       FROM vendite.fn_af_merce_per_riga(ARRAY[(SELECT k_ddt FROM tmp_k)]) f
      ORDER BY f.tipo_movimento$q$,
  $q$VALUES ('NORMALE'::text, 12::numeric), ('RETTIFICA'::text, -4::numeric)$q$,
  '5) chiave DDT semplice: NORMALE 12 e la RETTIFICA -4 del suffisso #RET:1, due righe e basta');

-- ============================================================
-- 6) ⭐ il vicino numerico
-- ============================================================
SELECT is(
  (SELECT count(*) FROM vendite.fn_af_merce_per_riga(ARRAY[(SELECT k_ddt FROM tmp_k)]) f WHERE f.riga_id = 9000010)::text
  || '|' || (SELECT count(*) || ':' || (max(f.quantita) = 3)::text FROM vendite.fn_af_merce_per_riga(ARRAY[(SELECT k_vicino FROM tmp_k)]) f)
  || '|' || (SELECT count(*) FROM vendite.fn_af_merce_per_riga(ARRAY[(SELECT k_prefisso FROM tmp_k)]))::text,
  '0|1:true|0',
  '6) il vicino numerico: :R:900001 non prende :R:9000010; :R:9000010 da sola prende 3; :R:90000 (prefisso) prende niente');

-- ============================================================
-- 7) il kit: i #CMP entrano dalla chiave base, in unita' del padre
-- ============================================================
SELECT results_eq(
  $q$SELECT f.corsia::text, (f.quantita = 10), f.misurabile, f.da_componenti, f.voci
       FROM vendite.fn_af_merce_per_riga(ARRAY[(SELECT k_kit FROM tmp_k)]) f$q$,
  $q$VALUES ('ORDINE_VENDITA'::text, true, true, true, 1)$q$,
  '7) kit con coeff 2/1/0.5 su qta 20/10/5: una riga ORD da 10 in unita'' del PADRE, da_componenti, misurabile, una voce (l''istanza)');

-- ============================================================
-- 8) le due sequenze: stesso numero, corsie diverse, chiavi diverse
-- ============================================================
SELECT is(
  (SELECT count(*) || ':' || max(f.corsia::text) || ':' || (max(f.quantita) = 7)::text
     FROM vendite.fn_af_merce_per_riga(ARRAY[(SELECT k_coll FROM tmp_k)]) f)
  || '|' || (SELECT count(*) FROM vendite.fn_af_merce_per_riga(ARRAY[(SELECT k_ddt FROM tmp_k)]) f WHERE f.corsia = 'ORDINE_VENDITA')::text,
  '1:ORDINE_VENDITA:true|0',
  '8) stesso riga_id 900001 su corsia ORD: la chiave ORD prende la sua riga (7), la chiave DDT non la vede');

-- ============================================================
-- 9) il suffisso ignoto: la base e' cio' che precede il primo '#'
-- ============================================================
SELECT is(
  (SELECT f.quantita FROM vendite.fn_af_merce_per_riga(ARRAY[(SELECT k_foo FROM tmp_k)]) f WHERE f.tipo_movimento = 'NORMALE'),
  11::numeric,
  '9) suffisso ignoto #FOO: entra dalla base come lo conta la vista (5 + 6 = 11)');

-- ============================================================
-- 10) ⭐ equivalenza con la vista, chiave per chiave, nei due versi
-- ============================================================
SELECT is(
  (SELECT sum(pg_temp.afk_diff(k))::bigint
     FROM (SELECT unnest(ARRAY[k_ddt, k_vicino, k_kit, k_coll, k_foo]) AS k FROM tmp_k) x),
  0::bigint,
  '10) per ognuna delle cinque chiavi costruite fn(ARRAY[k]) = vista filtrata su (corsia, riga_id), nei due versi');

-- ============================================================
-- 11) ⭐ normalizzazione: duplicati e chiave col suffisso non raddoppiano
-- ============================================================
SELECT results_eq(
  $q$SELECT f.tipo_movimento::text, f.quantita, f.voci
       FROM vendite.fn_af_merce_per_riga(ARRAY[(SELECT k_ddt FROM tmp_k), (SELECT k_ddt FROM tmp_k),
                                              (SELECT k_ddt FROM tmp_k) || '#RET:1']) f
      ORDER BY f.tipo_movimento$q$,
  $q$SELECT f.tipo_movimento::text, f.quantita, f.voci
       FROM vendite.fn_af_merce_per_riga(ARRAY[(SELECT k_ddt FROM tmp_k)]) f
      ORDER BY f.tipo_movimento$q$,
  '11) la chiave ripetuta e passata anche con #RET:1 accanto alla base: stesse righe, stesse somme, stesse voci');

-- ============================================================
-- 12) niente da seminare
-- ============================================================
SELECT is(
  (SELECT count(*) FROM vendite.fn_af_merce_per_riga(ARRAY[]::varchar[]))::text
  || '|' || (SELECT count(*) FROM vendite.fn_af_merce_per_riga(ARRAY['DDT_VENDITA:00000000-0000-0000-0000-000000000000:R:1']))::text,
  '0|0',
  '12) array VUOTO e chiave inesistente: zero righe — vuoto non e'' «tutte»');

-- ============================================================
-- 13) Scope: chi non vede la commessa non vede il conto.
-- ⚠️ Con la veste OPERATORE e un utente senza whitelist la RLS di
--    commesse_attivita non fa vedere le attivita', e la funzione — INVOKER —
--    risponde ZERO righe. Rosso da owner per costruzione (l'owner salta la
--    RLS), verde come app.
-- ============================================================
SELECT set_config('app.current_user_id', '999999999', true);

SELECT is(
  (SELECT count(*) FROM vendite.fn_af_merce_per_riga(ARRAY[(SELECT k_ddt FROM tmp_k)])),
  0::bigint,
  '13) scope che non vede la commessa: il conto sparisce, non esce a zero');

SELECT * FROM finish();
ROLLBACK;
