-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-11-07 (giro T.5, 20261106-92 … -97): le colonne parallele sono ritirate e i verbi non le
--   scrivono piu'. I test 5-7 guardano la sola provenienza; l'azzeramento prima dei lettori (9-18)
--   non serve piu', perche' le colonne non ci sono: i lettori leggono la provenienza per forza.
-- pgTAP test per Zero ERP
-- Test: la PROVENIENZA di testata di ordini, contratti e fatture nella
--   grammatica del modello: il tipo del documento + una sola chiave
--   (sorgente_id o sorgente_uid, secondo il key_selector). La scrivono i tre
--   verbi di push, la valida il guard unico, la leggono documenti vivi,
--   annullabilita' del preventivo, legami, lineage, lista ordini e dashboard.
-- ChangeSet: 20261106-74 … -87 (giro T.3)
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto T, giro T.3
-- ------------------------------------------------------------
-- Indice test (plan 24):
--   LA FORMA
--    1) gli indici unici «import» (tipo, uid) di ordini e fatture non ci sono piu'
--    2) le tre testate hanno il CHECK di forma
--    3) le tre testate montano il guard unico, DOCUMENTO e BLOCCA
--    4) D-8: il predicato dei due indici «un'offerta, un documento vivo» nomina
--       l'id di OFFERTA_COMMERCIALE nel catalogo, NULLS NOT DISTINCT
--   I VERBI
--    5) push preventivo -> ordine: PREVENTIVO + uid
--    6) ordine dall'offerta: OFFERTA_COMMERCIALE + uid
--    7) contratto dall'offerta: OFFERTA_COMMERCIALE + uid
--    8) ... con una pratica: il contratto entra in pratiche_sorgenti con l'id in sorgente_id (V-1)
--   I LETTORI, su documenti che hanno SOLO la provenienza (colonne parallele ritirate, giro T.5)
--    9) i documenti vivi dell'offerta: l'ordine
--   10) ... e il contratto
--   11) il preventivo con un ordine vivo non si annulla (E_PREV_ORDINE_GIA_GENERATO)
--   12) i legami: PROVENIENZA dell'ordine verso l'offerta
--   13) ... e del contratto
--   14) la lineage col seme: A (preventivo -> ordine), D (offerta -> ordine), C (offerta -> contratto)
--   15) ... col seme a valle (archi entranti)
--   16) ... e senza seme
--   17) la lista ordini: tipo, id e numero dell'origine dalla provenienza
--   18) la dashboard delle offerte: le due offerte sono transitate
--   19) un secondo ordine dalla stessa offerta: E_ORD_OFFERTA_GIA_CONVERTITA
--   L'UNICITA' (D-8)
--   20) un secondo ordine vivo che cita la stessa offerta: uq_ordini_v_sorgente_offerta
--   IL GUARD UNICO E LA FORMA
--   21) la chiave della specie sbagliata (id per un tipo a uid): E_SORG_CHIAVE_NON_CONFORME
--   22) un documento che non c'e': E_SORG_NOT_FOUND
--   23) la chiave senza tipo: il CHECK di forma (23514)
--   IN USCITA
--   24) il preventivo citato da un ordine non si cancella: E_SORG_ORIGINE_REFERENZIATA
--
-- ⚠️ Il mondo si COSTRUISCE coi builder dbops.fn_pgtap_* (cliente, listino,
--   articoli), come vendite/test-sorgente-righe-vendita-v1. Gira come
--   l'applicazione (operatore in sessione, RLS attiva).
-- ⚠️ I casi 9-18 leggono documenti che hanno la sola provenienza: fino al giro
--   T.5 il file azzerava le colonne parallele (documento_origine_*, offerta_id),
--   dal giro T.5 non ci sono piu'.
-- ⚠️ L'unicita' sul contratto (uq_contratti_sorgente_offerta) si prova dalla
--   definizione (4), uguale a quella dell'ordine: un secondo contratto vivo
--   sulla stessa istanza si ferma prima, sulla successione dei contratti.
-- rev 2026-11-08 (brief-db-sorgente-documento-e-riga lotto P, giro P.1): il test 8 legge l'id del contratto in sorgente_id del link alla pratica.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(24);

-- ============================================================
-- LA FORMA
-- ============================================================
SELECT ok(
  to_regclass('vendite.uq_ordini_v_sorgente_fk') IS NULL
  AND to_regclass('vendite.uq_fatture_v_sorgente_fk') IS NULL,
  '1) niente unicita'' «import» per (tipo, uid) su ordini e fatture: due ordini dallo stesso preventivo sono la regola');

SELECT is(
  (SELECT count(*)::int FROM pg_constraint k
    WHERE k.contype = 'c'
      AND k.conname IN ('chk_ordini_sorgente_forma', 'chk_contratti_sorgente_forma', 'chk_fatture_sorgente_forma')),
  3,
  '2) le tre testate hanno il CHECK di forma della provenienza');

SELECT results_eq(
  -- ⚠️ Schema e nome dal catalogo, non da regclass::text: quello toglie lo schema
  --   quando sta nel search_path di chi lancia (rev 2026-11-07, giro T.5).
  $$SELECT format('%I.%I', n.nspname, c.relname) COLLATE "default", m.livello_minimo, m.azione_cancellazione
      FROM script.fn_sorgente_guard_montaggi() m
      JOIN pg_class c     ON c.oid = m.tabella
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE m.tabella IN ('vendite.ordini'::regclass, 'vendite.contratti'::regclass, 'vendite.fatture'::regclass)
     ORDER BY 1$$,
  $$VALUES ('vendite.contratti', 'DOCUMENTO', 'BLOCCA'),
           ('vendite.fatture', 'DOCUMENTO', 'BLOCCA'),
           ('vendite.ordini', 'DOCUMENTO', 'BLOCCA')$$,
  '3) il guard unico e'' montato sulle tre testate: livello DOCUMENTO, BLOCCA in cancellazione');

-- D-8: l'indice non puo' leggere il catalogo, e nomina l'id. Si confronta il
-- predicato con l'id che il catalogo da' oggi al codice.
SELECT is(
  (SELECT string_agg(format('%s|%s|%s', c.relname, x.indnullsnotdistinct,
                            pg_get_expr(x.indpred, x.indrelid)
                              = format('((sorgente_tipo_id = %s) AND (NOT is_abortito_snapshot))',
                                       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'OFFERTA_COMMERCIALE'))),
                     ',' ORDER BY c.relname)
     FROM pg_index x JOIN pg_class c ON c.oid = x.indexrelid
    WHERE x.indexrelid IN (to_regclass('vendite.uq_ordini_v_sorgente_offerta'),
                           to_regclass('vendite.uq_contratti_sorgente_offerta'))
      AND x.indisunique),
  'uq_contratti_sorgente_offerta|t|t,uq_ordini_v_sorgente_offerta|t|t',
  '4) D-8: i due indici «un''offerta, un documento vivo» sono unici, NULLS NOT DISTINCT, e il predicato nomina l''id di OFFERTA_COMMERCIALE');

-- ============================================================
-- Fixture: il mondo
-- ============================================================
CREATE TEMP TABLE _cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'sorgente testate',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE _lis AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM _cli), 'sorgente testate');

CREATE TEMP TABLE _ref AS
SELECT c.billing_account_id, c.istanza_utility_id, c.utility_id, c.soggetto_ruolo_id,
       script.fn_pgtap_emittente_operatore()                                        AS emittente_fiscale_id,
       dbops.fn_pgtap_crea_articolo('PGT-SRT-PREV', false)                          AS art_prev,
       dbops.fn_pgtap_crea_articolo('PGT-SRT-OFF', false)                           AS art_off,
       (SELECT l.listino_id FROM _lis l)                                            AS listino_id,
       (SELECT l.listino_versione_id FROM _lis l)                                   AS listino_versione_id,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                     AS valuta_id,
       (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
       (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT') AS prev_draft_id,
       (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA')    AS off_bozza_id,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')          AS t_prev,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'OFFERTA_COMMERCIALE') AS t_off,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA')      AS t_ord,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'CONTRATTO')           AS t_con
  FROM _cli c;

SELECT dbops.fn_pgtap_listino_aggiungi_articoli(
    (SELECT listino_versione_id FROM _ref), ARRAY[(SELECT art_off FROM _ref)]);

CREATE TEMP TABLE _fix (chiave text PRIMARY KEY, id bigint);
CREATE FUNCTION pg_temp.fix(p text) RETURNS bigint LANGUAGE sql AS $$ SELECT id FROM _fix WHERE chiave = p $$;

-- Un preventivo con una riga, nato DRAFT e portato allo stato chiesto.
CREATE FUNCTION pg_temp.mk_preventivo(p_chiave text, p_stato text, p_articolo uuid)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE r RECORD; v_prev bigint;
BEGIN
  SELECT * INTO r FROM _ref;
  INSERT INTO vendite.preventivi (rev, billing_account_id, istanza_utility_id, utility_id,
      validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
      fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  VALUES (0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
          script.fn_data_operativa(), script.fn_data_operativa() + 30, r.valuta_id, r.prev_draft_id,
          script.fn_data_operativa(), false, false,
          jsonb_build_object('test_scope', 'pgtap_sorgente_testate'), r.emittente_fiscale_id)
  RETURNING id INTO v_prev;
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario,
      iva_id, attivo, meta)
  VALUES (v_prev, p_articolo, 4, 25, r.iva_id, true, jsonb_build_object('test_scope', 'pgtap_sorgente_testate'));
  IF p_stato <> 'DRAFT' THEN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', v_prev, p_stato);
  END IF;
  INSERT INTO _fix VALUES (p_chiave, v_prev);
END $$;

-- Un'offerta ACCETTATA sul listino, con un OVERRIDE sull'articolo a listino.
CREATE FUNCTION pg_temp.mk_offerta(p_chiave text)
RETURNS void LANGUAGE plpgsql AS $$
DECLARE r RECORD; v_off bigint;
BEGIN
  SELECT * INTO r FROM _ref;
  INSERT INTO vendite.offerte_commerciali (emittente_fiscale_id, billing_account_id,
      istanza_utility_id, utility_id, listino_id, listino_versione_id,
      validita_dal, validita_al, stato_doc_offerta_id)
  VALUES (r.emittente_fiscale_id, r.billing_account_id, r.istanza_utility_id, r.utility_id,
          r.listino_id, r.listino_versione_id, script.fn_data_operativa(),
          script.fn_data_operativa() + 364, r.off_bozza_id)
  RETURNING id INTO v_off;
  INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
      tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, attivo, qta_operativa)
  VALUES (v_off, r.art_off, 'OVERRIDE'::vendite.tipo_eccezione_contratto, NULL, NULL, 200, true,
          (SELECT 1.00 FROM vendite.fn_articolo_erogazioni(r.art_off) e
            WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1));
  INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
  VALUES (v_off, r.istanza_utility_id, r.utility_id);
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.offerte_commerciali', v_off, 'ACCETTATA');
  INSERT INTO _fix VALUES (p_chiave, v_off);
END $$;

-- La pratica a cui agganciare il contratto, come la crea il backend.
INSERT INTO _fix
SELECT 'pratica',
       pratiche.fn_crea_pratica(
           r.emittente_fiscale_id,
           (SELECT tp.id FROM pratiche.tipi_prestazione tp WHERE tp.codice_interno = 'APPROVAZIONE_PREZZO'),
           NULL, NULL, NULL, NULL,
           'pgTAP sorgente testate',
           jsonb_build_object('test_scope', 'pgtap_sorgente_testate'))
  FROM _ref r;

-- ============================================================
-- I VERBI
-- ============================================================
SELECT pg_temp.mk_preventivo('acc', 'ACCETTATO', (SELECT art_prev FROM _ref));
INSERT INTO _fix SELECT 'ord_prev', vendite.fn_push_preventivo_a_ordine(pg_temp.fix('acc'));

SELECT is(
  (SELECT format('%s|%s|%s', o.sorgente_tipo_id = k.t_prev, o.sorgente_id IS NULL,
                 o.sorgente_uid = p.uid)
     FROM vendite.ordini o, _ref k, vendite.preventivi p
    WHERE o.id = pg_temp.fix('ord_prev') AND p.id = pg_temp.fix('acc')),
  't|t|t',
  '5) push preventivo -> ordine: la testata cita PREVENTIVO con l''uid');

SELECT pg_temp.mk_offerta('off_ord');
INSERT INTO _fix SELECT 'ord_off', vendite.fn_genera_ordine_da_offerta(pg_temp.fix('off_ord'));

SELECT is(
  (SELECT format('%s|%s|%s', o.sorgente_tipo_id = k.t_off, o.sorgente_id IS NULL,
                 o.sorgente_uid = f.uid)
     FROM vendite.ordini o, _ref k, vendite.offerte_commerciali f
    WHERE o.id = pg_temp.fix('ord_off') AND f.id = pg_temp.fix('off_ord')),
  't|t|t',
  '6) ordine dall''offerta: la testata cita OFFERTA_COMMERCIALE con l''uid');

SELECT pg_temp.mk_offerta('off_ctr');
INSERT INTO _fix SELECT 'ctr', vendite.fn_push_offerta_a_contratto(pg_temp.fix('off_ctr'), pg_temp.fix('pratica'));

SELECT is(
  (SELECT format('%s|%s|%s', c.sorgente_tipo_id = k.t_off, c.sorgente_id IS NULL,
                 c.sorgente_uid = f.uid)
     FROM vendite.contratti c, _ref k, vendite.offerte_commerciali f
    WHERE c.id = pg_temp.fix('ctr') AND f.id = pg_temp.fix('off_ctr')),
  't|t|t',
  '7) contratto dall''offerta: la testata cita OFFERTA_COMMERCIALE con l''uid');

SELECT is(
  -- Dal giro P.1 il link tiene la chiave nelle colonne del modello: l'id del
  -- contratto in sorgente_id, sorgente_uid NULL.
  (SELECT string_agg(ps.sorgente_id || '|' || (ps.sorgente_uid IS NULL) || '|' || ps.ruolo_link, ',')
     FROM pratiche.pratiche_sorgenti ps, _ref k
    WHERE ps.pratica_id = pg_temp.fix('pratica') AND ps.sorgente_tipo_id = k.t_con),
  pg_temp.fix('ctr')::text || '|true|COLLEGATO',
  '8) ... con una pratica: il contratto entra in pratiche_sorgenti con la sua chiave, l''id in sorgente_id (V-1)');

-- ============================================================
-- I LETTORI, sulla sola provenienza (le colonne parallele sono ritirate dal
-- giro T.5: fino ad allora qui si azzeravano).
-- ============================================================

SELECT is(
  (SELECT string_agg(v.tipo || ':' || (v.documento_id = pg_temp.fix('ord_off')), ',')
     FROM vendite.fn_offerta_documenti_vivi(pg_temp.fix('off_ord')) v),
  'ORDINE_VENDITA:true',
  '9) i documenti vivi dell''offerta: l''ordine che la dichiara come provenienza');

SELECT is(
  (SELECT string_agg(v.tipo || ':' || (v.documento_id = pg_temp.fix('ctr')), ',')
     FROM vendite.fn_offerta_documenti_vivi(pg_temp.fix('off_ctr')) v),
  'CONTRATTO:true',
  '10) ... e il contratto che la dichiara come provenienza');

SELECT is(
  (SELECT string_agg(m ->> 'codice', ',')
     FROM jsonb_array_elements(script.fn_check_preventivo_annullabile(pg_temp.fix('acc'))) m),
  'E_PREV_ORDINE_GIA_GENERATO',
  '11) il preventivo con un ordine vivo nato da lui non si annulla: l''ordine si trova dalla provenienza');

SELECT is(
  (SELECT string_agg(format('%s|%s|%s', l.origine, l.natura, l.origine_id = pg_temp.fix('off_ord')), ',')
     FROM vendite.fn_documento_legami('ORDINE_VENDITA', pg_temp.fix('ord_off')) l
    WHERE l.natura = 'PROVENIENZA'),
  'OFFERTA_COMMERCIALE|PROVENIENZA|t',
  '12) i legami dell''ordine: la PROVENIENZA verso l''offerta, con il suo id');

SELECT is(
  (SELECT string_agg(format('%s|%s|%s', l.origine, l.natura, l.origine_id = pg_temp.fix('off_ctr')), ',')
     FROM vendite.fn_documento_legami('CONTRATTO', pg_temp.fix('ctr')) l
    WHERE l.natura = 'PROVENIENZA'),
  'OFFERTA_COMMERCIALE|PROVENIENZA|t',
  '13) i legami del contratto: la PROVENIENZA verso l''offerta, con il suo id');

-- Gli archi attesi, con le chiavi dei nodi resi a text (key_selector).
CREATE TEMP TABLE _archi_attesi AS
SELECT k.t_prev AS from_tipo_id, p.uid::text AS from_uid, k.t_ord AS to_tipo_id, pg_temp.fix('ord_prev')::text AS to_uid, 'A'::text AS arco
  FROM _ref k, vendite.preventivi p WHERE p.id = pg_temp.fix('acc')
UNION ALL
SELECT k.t_off, f.uid::text, k.t_ord, pg_temp.fix('ord_off')::text, 'D'
  FROM _ref k, vendite.offerte_commerciali f WHERE f.id = pg_temp.fix('off_ord')
UNION ALL
SELECT k.t_off, f.uid::text, k.t_con, pg_temp.fix('ctr')::text, 'C'
  FROM _ref k, vendite.offerte_commerciali f WHERE f.id = pg_temp.fix('off_ctr');

SELECT set_eq(
  $$SELECT a.from_tipo_id, a.from_uid, a.to_tipo_id, a.to_uid, a.arco
      FROM vendite.fn_documento_lineage_archi(
             (SELECT array_agg(e.from_tipo_id) FROM _archi_attesi e),
             (SELECT array_agg(e.from_uid)     FROM _archi_attesi e)) a
     WHERE a.arco IN ('A', 'C', 'D')$$,
  $$SELECT * FROM _archi_attesi$$,
  '14) la lineage col seme a monte: gli archi A, D e C uscenti dal preventivo e dalle due offerte');

SELECT set_eq(
  $$SELECT a.from_tipo_id, a.from_uid, a.to_tipo_id, a.to_uid, a.arco
      FROM vendite.fn_documento_lineage_archi(
             (SELECT array_agg(e.to_tipo_id) FROM _archi_attesi e),
             (SELECT array_agg(e.to_uid)     FROM _archi_attesi e)) a
     WHERE a.arco IN ('A', 'C', 'D')$$,
  $$SELECT * FROM _archi_attesi$$,
  '15) ... col seme a valle: gli stessi archi, entranti nell''ordine e nel contratto');

SELECT set_eq(
  $$SELECT a.from_tipo_id, a.from_uid, a.to_tipo_id, a.to_uid, a.arco
      FROM vendite.fn_documento_lineage_archi() a
      JOIN _archi_attesi e ON e.to_tipo_id = a.to_tipo_id AND e.to_uid = a.to_uid
     WHERE a.arco IN ('A', 'C', 'D')$$,
  $$SELECT * FROM _archi_attesi$$,
  '16) ... e senza seme: gli stessi archi fra tutti');

SELECT is(
  (SELECT format('%s|%s|%s|%s', v.documento_origine_tipo, v.documento_origine_id = p.id,
                 v.documento_origine_codice = p.numero, v.sorgente_uid = p.uid)
     FROM vendite.vw_ordini_lista v, vendite.preventivi p
    WHERE v.id = pg_temp.fix('ord_prev') AND p.id = pg_temp.fix('acc')),
  'PREVENTIVO|t|t|t',
  '17) la lista ordini: tipo, id e numero dell''origine vengono dalla provenienza, che e'' anche in coda');

SELECT is(
  (SELECT string_agg(format('%s', v.is_transitato), ',' ORDER BY v.documento_id)
     FROM vendite.vw_dash_fatturazione_offerte v
    WHERE v.documento_id IN (pg_temp.fix('off_ord'), pg_temp.fix('off_ctr'))),
  't,t',
  '18) la dashboard delle offerte: le due offerte sono transitate, all''ordine e al contratto');

SELECT is(
  dbops.fn_pgtap_codice_errore(format('SELECT vendite.fn_genera_ordine_da_offerta(%s)', pg_temp.fix('off_ord'))),
  'E_ORD_OFFERTA_GIA_CONVERTITA',
  '19) un secondo ordine dalla stessa offerta: E_ORD_OFFERTA_GIA_CONVERTITA, dai documenti vivi');

-- ============================================================
-- L'UNICITA' (D-8): l'ordine dal preventivo, in bozza, cita a mano l'offerta
-- che ha gia' un ordine vivo. Il guard lo accetta (l'offerta c'e'), l'indice no.
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'UPDATE vendite.ordini SET sorgente_tipo_id = %s, sorgente_id = NULL, sorgente_uid = %L WHERE id = %s',
    (SELECT t_off FROM _ref),
    (SELECT uid FROM vendite.offerte_commerciali WHERE id = pg_temp.fix('off_ord')),
    pg_temp.fix('ord_prev'))),
  'uq_ordini_v_sorgente_offerta',
  '20) un secondo ordine vivo che cita la stessa offerta: uq_ordini_v_sorgente_offerta');

-- ============================================================
-- IL GUARD UNICO E LA FORMA, sull'ordine dal preventivo, in bozza
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'UPDATE vendite.ordini SET sorgente_id = %s, sorgente_uid = NULL WHERE id = %s',
    pg_temp.fix('acc'), pg_temp.fix('ord_prev'))),
  'E_SORG_CHIAVE_NON_CONFORME',
  '21) la chiave della specie sbagliata (l''id per il preventivo, che ha chiave uid): E_SORG_CHIAVE_NON_CONFORME');

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'UPDATE vendite.ordini SET sorgente_uid = gen_random_uuid() WHERE id = %s', pg_temp.fix('ord_prev'))),
  'E_SORG_NOT_FOUND',
  '22) un preventivo che non c''e'': E_SORG_NOT_FOUND');

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'UPDATE vendite.ordini SET sorgente_tipo_id = NULL WHERE id = %s', pg_temp.fix('ord_prev'))),
  'chk_ordini_sorgente_forma',
  '23) la chiave senza tipo: il CHECK di forma');

-- ============================================================
-- IN USCITA: l'ordine in bozza cita un preventivo in bozza, che non si cancella.
-- ============================================================
SELECT pg_temp.mk_preventivo('bozza', 'DRAFT', (SELECT art_prev FROM _ref));
UPDATE vendite.ordini
   SET sorgente_uid = (SELECT uid FROM vendite.preventivi WHERE id = pg_temp.fix('bozza'))
 WHERE id = pg_temp.fix('ord_prev');

-- rev 2026-11-08 (giro Z.2 di brief-db-sorgente-documento-e-riga): il
-- preventivo si cancella solo da bozza vuota, e il guard della testata parla
-- prima del lato «in uscita». Le righe si disattivano (in bozza si puo'), la
-- bozza e' vuota, e il rifiuto che il test prova resta quello del figlio.
UPDATE vendite.preventivi_righe SET attivo = false WHERE preventivo_id = pg_temp.fix('bozza');

SELECT is(
  dbops.fn_pgtap_codice_errore(format('DELETE FROM vendite.preventivi WHERE id = %s', pg_temp.fix('bozza'))),
  'E_SORG_ORIGINE_REFERENZIATA',
  '24) il preventivo citato da un ordine non si cancella: E_SORG_ORIGINE_REFERENZIATA');

SELECT * FROM finish();
ROLLBACK;
