-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: le ORIGINI di una fattura (vendite.fn_fattura_origini, 20261027-22) e il
--   registro dei tipi che si citano (config.sorgenti.citato_in_fattura, 20261027-21).
--   Brief: brief-modello-documento-vendita §15.10 (D-G1 = c, Q-F6 = b, P-3 di Tid,
--   2026-10-27).
-- ------------------------------------------------------------
-- Il mondo costruito, sulla commessa C1:
--   * una riga dall'ordine O1, che nasce dal preventivo P1 con una riga portata
--     (legame vivo): la riga di O1 si fattura (fattura F);
--   * una riga dal preventivo PA, ANNULLATO;
--   * una riga dall'ordine O3, che dichiara come origine il preventivo P3 senza
--     righe portate (legame RITIRATO);
--   * un DDT legato alla commessa senza righe in F.
--   Sulla commessa C2: una riga dall'ordine O2. La fattura U copre le righe di
--   O2 (C2), di O3 e di PA (C1): due commesse (P-3). Una fattura S senza documenti a monte.
-- ⚠️ Lo stesso ordine in due commesse non si costruisce: un documento sta in una
--   sola commessa aperta alla volta (vendite.fn_link_commessa_sorgente).
-- Indice test (1..10):
--   1) il lettore e' SECURITY INVOKER e STABLE (come il lineage)
--   2) il registro: si citano DDT, ordine, contratto, offerta, preventivo e (dal
--      20261027-26) fattura e reso; la commessa no
--   3) p_fattura_id NULL: E_VENDITE_CHIAMATA_NON_VALIDA
--   4) F cita l'ordine della riga (livello 1) e il preventivo da cui nasce (livello 2)
--   5) ...non la commessa (contenitore interno)
--   6) il preventivo annullato non si cita, anche con una riga in U
--   7) ...non i documenti della commessa senza righe in F (l'ordine O3, il DDT):
--      si parte dalle righe fatturate, non dalla commessa intera
--   8) P-3: U, su due commesse, cita i due ordini, ciascuno una volta
--   9) ...e non il preventivo P3, raggiunto solo da un legame ritirato
--  10) S, senza documenti a monte: zero righe
-- ------------------------------------------------------------
BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ Vincoli DIFFERITI: in un test che chiude in ROLLBACK non scatterebbero mai.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- Il mondo
-- ============================================================
-- Le commesse in bozza, con la sorgente ROOT (il pull la pretende): le righe
-- prima del passaggio, perche' la riga porta il legame col documento a monte.
CREATE TEMP TABLE t_c1 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('pgtap origini 1', NULL, NULL, false, true);

CREATE TEMP TABLE t_c2 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('pgtap origini 2', NULL,
                                          (SELECT billing_account_id FROM t_c1), false, true);

CREATE TEMP TABLE t_o1 AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('pgtap origini 1', 'DRAFT', (SELECT billing_account_id FROM t_c1));
CREATE TEMP TABLE t_o2 AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('pgtap origini 2', 'DRAFT', (SELECT billing_account_id FROM t_c1));
CREATE TEMP TABLE t_o3 AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('pgtap origini 3', 'DRAFT', (SELECT billing_account_id FROM t_c1));

CREATE TEMP TABLE t_p1 AS SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgtap origini 1', 'DRAFT');
CREATE TEMP TABLE t_p3 AS SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgtap origini 3', 'DRAFT');
CREATE TEMP TABLE t_pa AS SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgtap origini A', 'ANNULLATO');

-- O1 nasce da P1 con una riga portata (arco A vivo); O3 dichiara P3 senza
-- righe portate (arco A ritirato: non ha portato nulla).
UPDATE vendite.ordini o
   SET documento_origine_tipo = 'PREVENTIVO',
       documento_origine_id   = CASE o.id WHEN (SELECT ordine_id FROM t_o1)
                                          THEN (SELECT preventivo_id FROM t_p1)
                                          ELSE (SELECT preventivo_id FROM t_p3) END
 WHERE o.id IN ((SELECT ordine_id FROM t_o1), (SELECT ordine_id FROM t_o3));

DO $leg$
DECLARE
  v_art uuid; v_iva bigint; v_pr bigint;
BEGIN
  v_art := dbops.fn_pgtap_crea_articolo('PGT-ORIG-' || substr(md5(random()::text), 1, 8), false);
  SELECT i.id INTO v_iva FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1;

  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id)
  VALUES ((SELECT preventivo_id FROM t_p1), v_art, 1, 10, v_iva)
  RETURNING id INTO v_pr;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, qta_operativa,
                                    prezzo_unitario, iva_id, preventivo_riga_id)
  VALUES ((SELECT ordine_id FROM t_o1), 1, v_art, 'Riga pgTAP origini', 1, 10, v_iva, v_pr);
END $leg$;

-- Le righe di commessa. ⚠️ La chiave della riga e' l'uid della testata: con
--   l'id il legame risulterebbe ritirato.
CREATE TEMP TABLE t_a_o1 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c1),
    p_sorgente_codice => 'ORDINE_VENDITA', p_sorgente_uid => (SELECT ordine_uid::text FROM t_o1));
CREATE TEMP TABLE t_a_pa AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c1),
    p_sorgente_codice => 'PREVENTIVO', p_sorgente_uid => (SELECT preventivo_uid::text FROM t_pa));
CREATE TEMP TABLE t_a_o3 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c1),
    p_sorgente_codice => 'ORDINE_VENDITA', p_sorgente_uid => (SELECT ordine_uid::text FROM t_o3));
CREATE TEMP TABLE t_a_o2 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c2),
    p_sorgente_codice => 'ORDINE_VENDITA', p_sorgente_uid => (SELECT ordine_uid::text FROM t_o2));

-- Il DDT legato alla commessa C1, senza righe in nessuna fattura.
CREATE TEMP TABLE t_ddt AS
SELECT dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM t_o1),
                               (SELECT cliente_soggetto_ruolo_id FROM t_o1),
                               'VENDITA') AS ddt_id;

INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
SELECT (SELECT commessa_id FROM t_c1), s.id, (SELECT ddt_id::text FROM t_ddt), 'COLLEGATO'
  FROM config.sorgenti s
 WHERE s.codice_interno = 'DDT_VENDITA';

-- Le due commesse emittibili, poi le fatture.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');
SELECT * FROM vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM t_c1), 'PRONTA_FATTURAZIONE');
SELECT * FROM vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM t_c2), 'PRONTA_FATTURAZIONE');

-- F: la sola riga di O1.
CREATE TEMP TABLE t_f AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('pgtap origini F', ARRAY[(SELECT attivita_id FROM t_a_o1)]);

-- U: le righe di O2 (C2), di O3 e del preventivo annullato PA (C1): due commesse.
CREATE TEMP TABLE t_u AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('pgtap origini U',
                                              ARRAY[(SELECT attivita_id FROM t_a_o2),
                                                    (SELECT attivita_id FROM t_a_o3),
                                                    (SELECT attivita_id FROM t_a_pa)]);

CREATE TEMP TABLE t_s AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('pgtap origini S');

CREATE TEMP TABLE t_orig_f AS
SELECT o.* FROM vendite.fn_fattura_origini((SELECT DISTINCT fattura_id FROM t_f)) o;

CREATE TEMP TABLE t_orig_u AS
SELECT o.* FROM vendite.fn_fattura_origini((SELECT DISTINCT fattura_id FROM t_u)) o;

-- ============================================================
-- 1-3) Il lettore e il registro
-- ============================================================
SELECT is(
    (SELECT p.prosecdef::text || ':' || p.provolatile::text
       FROM pg_proc p
      WHERE p.oid = 'vendite.fn_fattura_origini(bigint)'::regprocedure),
    'false:s',
    '1) il lettore e'' SECURITY INVOKER e STABLE, come il lineage'
);

SELECT is(
    (SELECT string_agg(s.codice_interno, ',' ORDER BY s.codice_interno)
       FROM config.sorgenti s
      WHERE s.citato_in_fattura),
    -- rev 2026-10-27 (20261027-26, Q-F7): anche FATTURA e RESO_VENDITA, le
    -- origini della nota di credito (test-fattura-origini-nota-v1).
    'CONTRATTO,DDT_VENDITA,FATTURA,OFFERTA_COMMERCIALE,ORDINE_VENDITA,PREVENTIVO,RESO_VENDITA',
    '2) si citano DDT, ordine, contratto, offerta, preventivo, fattura e reso; la commessa no'
);

SELECT throws_like(
    $$SELECT * FROM vendite.fn_fattura_origini(NULL)$$,
    'Chiamata non valida a vendite.fn_fattura_origini%',
    '3) p_fattura_id NULL: E_VENDITE_CHIAMATA_NON_VALIDA'
);

-- ============================================================
-- 4-7) F
-- ============================================================
SELECT is(
    (SELECT string_agg(o.tipo_codice_interno || '@' || o.livello || '=' || o.uid, ','
                       ORDER BY o.livello)
       FROM t_orig_f o),
    'ORDINE_VENDITA@1=' || (SELECT ordine_id::text FROM t_o1)
      || ',PREVENTIVO@2=' || (SELECT preventivo_uid::text FROM t_p1),
    '4) F cita l''ordine della riga (livello 1) e il preventivo da cui nasce (livello 2)'
);

SELECT is(
    (SELECT count(*) FROM t_orig_f o WHERE o.tipo_codice_interno = 'COMMESSA')::integer,
    0,
    '5) la commessa non si cita: e'' un contenitore interno'
);

-- ⚠️ Su U, dove la riga di PA e' fatturata: su F lo zero non proverebbe nulla.
SELECT is(
    (SELECT count(*) FROM t_orig_u o
      WHERE o.uid = (SELECT preventivo_uid::text FROM t_pa))::integer,
    0,
    '6) il preventivo annullato non si cita, anche con una riga fatturata'
);

SELECT is(
    (SELECT count(*) FROM t_orig_f o
      WHERE (o.tipo_codice_interno, o.uid) IN (('ORDINE_VENDITA', (SELECT ordine_id::text FROM t_o3)),
                                               ('DDT_VENDITA',    (SELECT ddt_id::text FROM t_ddt))))::integer,
    0,
    '7) i documenti della commessa senza righe in F non si citano: si parte dalle righe fatturate'
);

-- ============================================================
-- 8-9) U, su due commesse (P-3)
-- ============================================================
SELECT is(
    (SELECT string_agg(o.uid, ',' ORDER BY o.uid::bigint)
       FROM t_orig_u o WHERE o.tipo_codice_interno = 'ORDINE_VENDITA'),
    (SELECT string_agg(x.id::text, ',' ORDER BY x.id)
       FROM (SELECT ordine_id AS id FROM t_o2 UNION ALL SELECT ordine_id FROM t_o3) x),
    '8) P-3: U, su due commesse, cita i due ordini, ciascuno una volta'
);

-- ⚠️ Non verde per sottrazione: il lineage dall'ordine O3 DEVE arrivare a P3,
--   col legame ritirato; altrimenti lo zero non proverebbe nulla.
SELECT is(
    (SELECT bool_and(l.is_legame_ritirato)::text
       FROM vendite.fn_documento_lineage(
                (SELECT s.id FROM config.sorgenti s WHERE s.target_table = 'vendite.ordini'::regclass),
                (SELECT ordine_id::text FROM t_o3), 'indietro') l
      WHERE l.from_uid = (SELECT preventivo_uid::text FROM t_p3))
    || ':' || (SELECT count(*) FROM t_orig_u o WHERE o.tipo_codice_interno = 'PREVENTIVO')::text,
    'true:0',
    '9) il preventivo raggiunto solo da un legame ritirato (il lineage lo trova, ritirato) non si cita'
);

-- ============================================================
-- 10) Nessun documento a monte
-- ============================================================
SELECT is(
    (SELECT count(*) FROM vendite.fn_fattura_origini((SELECT fattura_id FROM t_s)))::integer,
    0,
    '10) una fattura senza documenti a monte non cita nulla'
);

SELECT * FROM finish();
ROLLBACK;
