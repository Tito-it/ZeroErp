-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: le ORIGINI di una nota di credito (vendite.fn_fattura_origini,
--   20261027-26): le sorgenti di ogni tipo. Brief: brief-modello-documento-vendita
--   §15.11 (Q-F7 di Tid, 2026-10-27: «anche se di tipo diverso, sono sempre
--   sorgenti»; la nota cita anche il DDT e l'ordine del reso).
-- ------------------------------------------------------------
-- Il mondo costruito, sulla commessa C, dal percorso vero (builder e verbi):
--   * l'ordine OA consegnato con la bolla DA (10 pezzi), fatturata: fattura F;
--   * la bolla DB con una riga sulla commessa C, mai fatturata: si raggiunge da
--     F solo passando dalla commessa (arco G), con un legame vivo;
--   * il reso R di 3 pezzi su DA, accreditato dal verbo: la rettifica fatturata
--     nella nota NR. La riga della nota porta la riga rettificata come la scrive
--     il generatore del backend (fatture_righe.riga_rettificata_id dalla
--     attivita' fatturabile): e' il legame dell'arco N;
--   * la nota NC2, di sola correzione: una riga che rettifica la riga di F,
--     senza reso.
-- Indice test (1..8):
--   1) il registro: si citano anche FATTURA e RESO_VENDITA (Q-F7)
--   2) fixture: NR ha i due archi diretti, N (da F) e S (da R)
--   3) ⭐ NR cita F e R (livello 1), il DDT del reso (2) e l'ordine (3)
--   4) ⭐ ...non la bolla DB, che da F si raggiunge solo dalla commessa
--      (precondizione: DB e' nel lineage all'indietro di F con un legame VIVO)
--   5) ...non la commessa, ne' se stessa
--   6) ogni documento una volta
--   7) NC2, sola correzione: cita la sola F
--   8) F, fattura ordinaria: invariata (la bolla e l'ordine delle sue righe)
-- ------------------------------------------------------------
BEGIN;

-- ⚠️ Vincoli DIFFERITI: in un test che chiude in ROLLBACK non scatterebbero mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Il mondo si costruisce: azienda, operatore, cliente BA; il builder apre da se'
-- il contesto su quell'operatore (OPERATORE + RLS attiva, come l'applicazione).
CREATE TEMP TABLE t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP origini nota');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_mondo)); END $ctx$;

SELECT plan(8);

-- ============================================================
-- Il mondo
-- ============================================================
CREATE TEMP TABLE t_refs AS
SELECT m.billing_account_id,
       dbops.fn_pgtap_crea_articolo('PGTAP-ORIG-NOTA', false) AS articolo_id
  FROM t_mondo m;

CREATE TEMP TABLE t_c AS
SELECT c.commessa_id
  FROM dbops.fn_pgtap_crea_commessa('origini nota', NULL,
           (SELECT billing_account_id FROM t_refs), p_con_sorgente_root => true) c;

-- OA -> DA, consegnata: la merce fatturata.
CREATE TEMP TABLE t_da AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('origini nota A',
           p_billing_account_id   => (SELECT billing_account_id FROM t_refs),
           p_quantita             => 10,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM t_refs),
           p_fatturazione_trigger => 'CONSEGNATO');

-- DB: legata alla commessa, mai fatturata.
CREATE TEMP TABLE t_db AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('origini nota B',
           p_billing_account_id   => (SELECT billing_account_id FROM t_refs),
           p_quantita             => 2,
           p_prezzo               => 10,
           p_articolo_id          => (SELECT articolo_id FROM t_refs),
           p_fatturazione_trigger => 'CONSEGNATO');

-- ⚠️ Con una RIGA sulla commessa, non col solo legame: un documento legato
--   senza righe arriva con un legame RITIRATO, e lo scarterebbe il filtro dei
--   legami vivi, non quello su G. Il test 4 sarebbe verde per il motivo
--   sbagliato (misurato col mutante, 2026-10-27).
CREATE TEMP TABLE t_att_b AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c), 10,
           p_articolo_id      => (SELECT articolo_id FROM t_refs),
           p_sorgente_codice  => 'DDT_VENDITA',
           p_sorgente_uid     => (SELECT ddt_uid FROM t_db)::text,
           p_sorgente_riga_id => (SELECT ddt_riga_id FROM t_db),
           p_quantita         => 2);

-- F: la riga della bolla DA.
CREATE TEMP TABLE t_att_a AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM t_c), 25,
           p_articolo_id      => (SELECT articolo_id FROM t_refs),
           p_sorgente_codice  => 'DDT_VENDITA',
           p_sorgente_uid     => (SELECT ddt_uid FROM t_da)::text,
           p_sorgente_riga_id => (SELECT ddt_riga_id FROM t_da),
           p_quantita         => 10);

CREATE TEMP TABLE t_f AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('origini nota F',
           ARRAY[(SELECT attivita_id FROM t_att_a)]);

-- R: il reso di 3 su DA, accreditato dal verbo (la rettifica sulla commessa).
CREATE TEMP TABLE t_r AS
SELECT * FROM dbops.fn_pgtap_crea_reso('origini nota', (SELECT ddt_id FROM t_da), 3,
           p_ddt_riga_id => (SELECT ddt_riga_id FROM t_da));

CREATE TEMP TABLE t_acc AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM t_r));

-- NR: la nota che fattura la rettifica. La riga rettificata la scrive il
-- generatore del backend, dall'attivita' fatturabile: qui come fa lui.
CREATE TEMP TABLE t_nr AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('origini nota NR',
           ARRAY[(SELECT commessa_attivita_id FROM t_acc)]);

UPDATE vendite.fatture_righe fr
   SET riga_rettificata_id = af.fattura_riga_rettificata_id
  FROM vendite.attivita_fatturabili af
 WHERE af.fattura_riga_id = fr.id
   AND fr.id = (SELECT fattura_riga_id FROM t_nr);

-- NC2: sola correzione, una riga che rettifica la riga di F, senza reso.
CREATE TEMP TABLE t_nc2 AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('origini nota NC2', 'DRAFT',
           (SELECT billing_account_id FROM t_refs));

INSERT INTO vendite.fatture_righe (
    fattura_id, riga_nr, articolo_id, descrizione, uom_id,
    qta, prezzo_unitario, iva_id, imponibile_riga,
    competenza_dal, competenza_al, riga_rettificata_id, meta)
SELECT (SELECT fattura_id FROM t_nc2), 1, fr.articolo_id, 'Fixture pgTAP: origini nota NC2', fr.uom_id,
       -1, fr.prezzo_unitario, fr.iva_id, -fr.prezzo_unitario,
       fr.competenza_dal, fr.competenza_al, fr.id,
       jsonb_build_object('test_scope', 'pgtap_origini_nota')
  FROM vendite.fatture_righe fr
 WHERE fr.id = (SELECT fattura_riga_id FROM t_f);

-- La risposta del lettore, in una forma confrontabile: tipo@livello=chiave.
CREATE FUNCTION pg_temp.origini(p_fattura_id bigint) RETURNS text
LANGUAGE sql STABLE AS $$
    SELECT string_agg(o.tipo_codice_interno || '@' || o.livello || '=' || o.uid,
                      ',' ORDER BY o.livello, o.tipo_codice_interno, o.uid)
      FROM vendite.fn_fattura_origini(p_fattura_id) o
$$;

CREATE TEMP TABLE t_id AS
SELECT (SELECT fattura_id FROM vendite.fatture_righe WHERE id = (SELECT fattura_riga_id FROM t_f))  AS f,
       (SELECT fattura_id FROM vendite.fatture_righe WHERE id = (SELECT fattura_riga_id FROM t_nr)) AS nr,
       (SELECT fattura_id FROM t_nc2) AS nc2;

-- ============================================================
-- 1) Il registro
-- ============================================================
SELECT is(
    (SELECT string_agg(s.codice_interno || '=' || s.citato_in_fattura::text, ',' ORDER BY s.codice_interno)
       FROM config.sorgenti s
      WHERE s.codice_interno IN ('FATTURA', 'RESO_VENDITA')),
    'FATTURA=true,RESO_VENDITA=true',
    '1) Q-F7: si citano anche la fattura (rettificata) e il reso'
);

-- ============================================================
-- 2) La fixture: senza i due archi diretti i test seguenti sarebbero verdi
--    per sottrazione.
-- ============================================================
SELECT is(
    (SELECT string_agg(DISTINCT l.arco, ',' ORDER BY l.arco)
       FROM vendite.fn_documento_lineage(
                (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'FATTURA'),
                (SELECT nr FROM t_id)::text, 'indietro') l
      WHERE l.livello = 1 AND l.arco <> 'G'),
    'N,S',
    '2) fixture: la nota NR ha i due archi diretti, N (dalla fattura F) e S (dal reso R)'
);

-- ============================================================
-- 3) ⭐ La nota da reso
-- ============================================================
SELECT is(
    pg_temp.origini((SELECT nr FROM t_id)),
    format('FATTURA@1=%s,RESO_VENDITA@1=%s,DDT_VENDITA@2=%s,ORDINE_VENDITA@3=%s',
           (SELECT f FROM t_id), (SELECT reso_id FROM t_r),
           (SELECT ddt_id FROM t_da), (SELECT ordine_id FROM t_da)),
    '3) NR cita la fattura rettificata e il reso (1), il DDT del reso (2) e l''ordine (3)'
);

-- ============================================================
-- 4) ⭐ La risalita non attraversa G
-- ============================================================
SELECT is(
    (SELECT EXISTS (
         SELECT 1 FROM vendite.fn_documento_lineage(
                    (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'FATTURA'),
                    (SELECT f FROM t_id)::text, 'indietro') l
          JOIN config.sorgenti s ON s.id = l.from_tipo_id
         WHERE s.codice_interno = 'DDT_VENDITA'
           AND l.from_uid = (SELECT ddt_id FROM t_db)::text
           AND l.is_legame_ritirato IS NOT TRUE))::text
    || ':' ||
    (SELECT count(*) FROM vendite.fn_fattura_origini((SELECT nr FROM t_id)) o
      WHERE o.tipo_codice_interno = 'DDT_VENDITA'
        AND o.uid = (SELECT ddt_id FROM t_db)::text),
    'true:0',
    '4) NR non cita la bolla DB: da F si raggiunge solo dalla commessa (arco G)'
);

-- ============================================================
-- 5) Non la commessa, non se stessa
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM vendite.fn_fattura_origini((SELECT nr FROM t_id)) o
      WHERE o.tipo_codice_interno = 'COMMESSA'
         OR (o.tipo_codice_interno = 'FATTURA' AND o.uid = (SELECT nr FROM t_id)::text)),
    0,
    '5) NR non cita la commessa ne'' se stessa'
);

-- ============================================================
-- 6) Ogni documento una volta
-- ============================================================
SELECT is(
    (SELECT count(*) - count(DISTINCT (o.tipo_id, o.uid))
       FROM vendite.fn_fattura_origini((SELECT nr FROM t_id)) o),
    0::bigint,
    '6) NR cita ogni documento una volta'
);

-- ============================================================
-- 7) La nota di sola correzione
-- ============================================================
SELECT is(
    pg_temp.origini((SELECT nc2 FROM t_id)),
    format('FATTURA@1=%s', (SELECT f FROM t_id)),
    '7) NC2, sola correzione: cita la sola fattura rettificata'
);

-- ============================================================
-- 8) La fattura ordinaria, invariata
-- ============================================================
SELECT is(
    pg_temp.origini((SELECT f FROM t_id)),
    format('DDT_VENDITA@1=%s,ORDINE_VENDITA@2=%s',
           (SELECT ddt_id FROM t_da), (SELECT ordine_id FROM t_da)),
    '8) F, fattura ordinaria: la bolla della riga (1) e il suo ordine (2), non DB'
);

SELECT * FROM finish();
ROLLBACK;
