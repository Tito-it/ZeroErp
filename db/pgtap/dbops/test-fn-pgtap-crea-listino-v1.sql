-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_listino e dbops.fn_pgtap_listino_aggiungi_articoli —
--   la quota fissa non e' un default, e la periodicita' si puo' dare
-- Riferimento: brief-db-revisione-dbops D69 (giro 8, blocco 8c); changeSet
--   20261108-59 e -60; 20261115-73 (p_in_bozza).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - la tipologia di default del listino e' la prima ammessa per l'utility
--     che NON e' una quota fissa: l'articolo d'appoggio ne prende la
--     tipologia, e una quota fissa a canone senza periodicita' non lascia
--     attivare la versione (script.fn_check_versione_listino_attivabile);
--   - il caso si COSTRUISCE dentro la transazione: sull'utility del mondo la
--     prima tipologia ammessa diventa una quota fissa (le precedenti spente),
--     e dopo di lei ne resta ammessa una che non lo e';
--   - p_periodicita scrive la periodicita' delle righe;
--   - con p_in_bozza la versione resta in bozza (le righe si scrivono solo li',
--     dal 20261115-65); senza, nasce ATTIVA come prima.
--
-- Elenco test (plan 5):
--   1) utility con la quota fissa come prima ammessa: il listino nasce, ATTIVO
--   2) la sua tipologia non e' una quota fissa
--   3) p_periodicita: la riga aggiunta ha la periodicita' data (in bozza)
--   4) senza p_in_bozza la versione e' fuori dalla bozza (ATTIVA)
--   5) con p_in_bozza la versione e' nello stato iniziale del vocabolario
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo): il builder del
-- mondo lo riapre poi sul suo operatore.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

CREATE TEMP TABLE tmp_cl_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('crea listino');

-- La quota fissa che si mette in testa, e la prima non quota fissa dopo di lei.
CREATE TEMP TABLE tmp_cl_tip AS
SELECT (SELECT lt.id FROM config.listini_tipologie lt
         WHERE lt.e_quota_fissa AND lt.attivo
         ORDER BY lt.ordinamento, lt.id LIMIT 1) AS quota_fissa;
ALTER TABLE tmp_cl_tip ADD COLUMN dopo smallint;
UPDATE tmp_cl_tip t SET dopo = (
    SELECT lt.id FROM config.listini_tipologie lt, config.listini_tipologie qf
     WHERE qf.id = t.quota_fissa
       AND lt.attivo AND lt.e_quota_fissa IS NOT TRUE
       AND (lt.ordinamento, lt.id) > (qf.ordinamento, qf.id)
     ORDER BY lt.ordinamento, lt.id LIMIT 1);

-- Ammesse sull'utility del mondo: la quota fissa e quella dopo; spente le precedenti.
INSERT INTO config.listini_tipologie_utilities (utility_id, tipologia_id, attivo)
SELECT (SELECT utility_id FROM tmp_cl_mondo), x.id, true
  FROM tmp_cl_tip t CROSS JOIN LATERAL (VALUES (t.quota_fissa), (t.dopo)) x(id)
ON CONFLICT (utility_id, tipologia_id) DO UPDATE SET attivo = true;

UPDATE config.listini_tipologie_utilities ltu
   SET attivo = false
  FROM config.listini_tipologie lt, config.listini_tipologie qf, tmp_cl_tip t
 WHERE ltu.utility_id = (SELECT utility_id FROM tmp_cl_mondo)
   AND lt.id = ltu.tipologia_id
   AND qf.id = t.quota_fissa
   AND (lt.ordinamento, lt.id) < (qf.ordinamento, qf.id)
   AND ltu.attivo;

-- 1-2) Il listino nasce e si attiva, su una tipologia che non e' una quota fissa.
SELECT lives_ok(
    $$CREATE TEMP TABLE tmp_cl_listino AS
      SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_cl_mondo), 'crea listino')$$,
    '1) la quota fissa e'' la prima ammessa: il listino nasce lo stesso, con la versione attiva');

SELECT is(
    (SELECT lt.e_quota_fissa FROM tmp_cl_listino l
       JOIN config.listini_tipologie lt ON lt.id = l.tipologia_id),
    false,
    '2) la tipologia del listino non e'' una quota fissa');

-- 3) La periodicita' delle righe. Dentro una funzione: senza il parametro la
--   chiamata solleva, e il test legge la frase invece di fermare il file.
--   Dal 20261115-65 le righe si scrivono solo in bozza: la riga va su una
--   versione in bozza (p_in_bozza).
CREATE TEMP TABLE tmp_cl_bozza AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_cl_mondo), 'crea listino bozza',
                                          p_in_bozza => true);

CREATE OR REPLACE FUNCTION pg_temp.riga_con_periodicita() RETURNS text
LANGUAGE plpgsql AS $fx$
DECLARE
    v_art   catalogo.articoli.id%TYPE;
    v_per   config.periodicita.codice%TYPE;
    v_esito text;
BEGIN
    SELECT p.codice INTO v_per FROM config.periodicita p ORDER BY p.codice LIMIT 1;
    v_art := dbops.fn_pgtap_crea_articolo('PGTAP_CL_PER_' || substr(md5(clock_timestamp()::text), 1, 8), false);
    PERFORM dbops.fn_pgtap_listino_aggiungi_articoli(
        (SELECT listino_versione_id FROM tmp_cl_bozza), ARRAY[v_art],
        p_periodicita => v_per);
    SELECT (r.periodicita = v_per)::text INTO v_esito
      FROM vendite.listini_righe r
     WHERE r.listino_versione_id = (SELECT listino_versione_id FROM tmp_cl_bozza)
       AND r.articolo_id = v_art;
    RETURN v_esito;
EXCEPTION WHEN others THEN
    RETURN SQLERRM;
END;
$fx$;

SELECT is(
    pg_temp.riga_con_periodicita(),
    'true',
    '3) p_periodicita: la riga aggiunta ha la periodicita'' data');

-- 4-5) Lo stato della versione, dalla marca del vocabolario.
SELECT is(
    (SELECT s.iniziale FROM vendite.listini_versioni lv
       JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
      WHERE lv.id = (SELECT listino_versione_id FROM tmp_cl_listino)),
    false,
    '4) senza p_in_bozza la versione e'' fuori dalla bozza (ATTIVA)');

SELECT is(
    (SELECT s.iniziale FROM vendite.listini_versioni lv
       JOIN config.stati_doc_listino_versioni s ON s.id = lv.stato_doc_listino_versione_id
      WHERE lv.id = (SELECT listino_versione_id FROM tmp_cl_bozza)),
    true,
    '5) con p_in_bozza la versione resta nello stato iniziale');

SELECT * FROM finish();
ROLLBACK;
