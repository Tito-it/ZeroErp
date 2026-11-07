-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2e): chiavi del push e corsia col codice della sorgente (ORDINE_VENDITA, DDT_VENDITA).
-- pgTAP test per Zero ERP
-- Test: vendite.vw_af_merce_per_riga — la base del contatore merce
--       (brief-design-partita-merce-generalizzata, slice S1, changeSet 20260817-06).
--
-- Elenco test (plan 11):
--   1) la vista esiste
--   2) e' security_invoker=on (RLS su commesse_attivita)
--   3) espone le colonne del contratto
--   4) corsia DDT, riga semplice: quantita = quella dell'attivita'
--   5) corsia ORD, riga semplice: quantita = quella dell'attivita'
--   6) ONERE esce come RIGA A SE' sulla stessa riga_id: la vista NON filtra
--      tipo_movimento (e' il vincolo che tiene aperta la porta alla NC)
--   7) ⭐ KIT con coefficienti DIVERSI DA 1: quantita in unita' del PADRE
--   8) quel kit e' marcato da_componenti + misurabile
--   9) kit senza `coeff_qta` nel meta -> misurabile = false
--  10) kit i cui componenti NON concordano -> misurabile = false
--  11) stesso riga_id su corsia ORD e su corsia DDT -> DUE righe distinte
--
-- Scopo:
--  - il 7) e' la ragione per cui questo file esiste. In sviluppo TUTTI i
--    `coeff_qta` valgono 1, quindi la divisione che normalizza i kit non e' mai
--    davvero esercitata: un ramo verde che nessun dato attraversa. Qui il kit
--    si costruisce apposta con tre coefficienti diversi (2, 1, 0.5) che devono
--    concordare tutti sullo stesso padre.
--  - il 6) protegge una decisione, non un calcolo: se un domani qualcuno
--    aggiungesse `WHERE tipo_movimento = 'NORMALE'` qui dentro, la nota di
--    credito dovrebbe riscrivere la base invece di cambiare un consumatore.
--  - l' 11) presidia la trappola delle DUE SEQUENZE: `riga_id` e' una riga
--    d'ordine o una riga di DDT a seconda della corsia, e i due id non hanno
--    alcun rapporto fra loro.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE. Senza, un fallimento a meta' lascia i dati di prova nel
--   database e rompe la corsa successiva, che vede un rosso non suo.
BEGIN;

-- ⚠️ 2. VINCOLI DIFFERITI. Scattano al COMMIT, e qui il COMMIT non arriva mai
--   (si chiude in ROLLBACK): senza questa riga non verrebbero mai esercitati e
--   il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- ⚠️ 3. CONTESTO APPLICATIVO. Il test gira come `zeroerp_app` con la RLS
--   ATTIVA: `commesse_attivita` ha una policy (scope via commessa). Senza una
--   veste dichiarata le SELECT della fixture leggono ZERO righe.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

-- rev 2026-10-27 (lotto 4 di D7): via il vecchio «SET LOCAL app.current_user_id
--   = '1'» (con ruolo OPERATORE): l'utente 1 da zero non esiste, e su dev e' un
--   super admin senza azienda. Chi agisce e' l'operatore del contesto qui sopra.

-- ============================================================
-- 1-3) Struttura della vista
-- ============================================================
SELECT has_view('vendite', 'vw_af_merce_per_riga', '1) la vista esiste');

SELECT ok(
  (SELECT 'security_invoker=on' = ANY(c.reloptions)
     FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite' AND c.relname = 'vw_af_merce_per_riga'),
  '2) vw_af_merce_per_riga e'' security_invoker=on (RLS su commesse_attivita)');

SELECT columns_are('vendite', 'vw_af_merce_per_riga',
  ARRAY['corsia','riga_id','tipo_movimento','quantita','misurabile','da_componenti','voci'],
  '3) espone corsia/riga_id/tipo_movimento/quantita/misurabile/da_componenti/voci');

-- ============================================================
-- Riferimenti minimi.
-- Questa vista non conosce ordini ne' DDT: bastano una commessa e le sue
-- attivita'. Le riga_id dei segmenti sono numeri ALTI e inventati apposta —
-- la vista non dereferenzia nulla, e cosi' il test non puo' collidere con
-- righe di documento reali del DB di sviluppo.
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il cliente e l'articolo si COSTRUISCONO.
--   Prima si pescavano il primo BA con emittente e l'ultimo articolo non
--   composito, e su un database ricostruito da zero non c'erano: ora il BA
--   viene da dbops.fn_pgtap_crea_cliente_ba (legato all'azienda di chi agisce)
--   e l'articolo da dbops.fn_pgtap_crea_articolo (merce semplice, non
--   composito). Restano letture di catalogo di SEED: unita_misura,
--   tipi_doc_fiscale, sorgenti, causali_onere.
CREATE TEMP TABLE tmp_cli_afm AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('vw af merce per riga');

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_afm)                          AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_afm)                                  AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_afm)                          AS istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-AFM-ART')                        AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA' AND s.attivo LIMIT 1) AS sorgente_root_id;

-- I prefissi di segmento del test, calcolati UNA volta sola: se si generassero
-- a ogni uso, ogni chiamata produrrebbe un uid diverso e i componenti di uno
-- stesso kit finirebbero in istanze diverse.
CREATE TEMP TABLE tmp_seg AS
SELECT gen_random_uuid() AS u_ddt,
       gen_random_uuid() AS u_ord,
       gen_random_uuid() AS u_onere,
       gen_random_uuid() AS u_kit_ok,
       gen_random_uuid() AS u_kit_senza_coeff,
       gen_random_uuid() AS u_kit_incoerente,
       gen_random_uuid() AS u_collisione_ord,
       gen_random_uuid() AS u_collisione_ddt;

CREATE TEMP TABLE tmp_com AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false, p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31',
  p_meta => jsonb_build_object('test_scope','pgtap_af_merce'), p_force_new => true
) AS commessa_id;

-- ROOT sorgente: fn_emit pretende che una ROOT esista. Sorgente COMMESSA
-- (key_selector='id') con uid = id della commessa stessa: la riga esiste per
-- costruzione, quindi passa il guard sorgente polimorfa su entrambi i fronti.
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_com),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  p_sorgente_uid => (SELECT commessa_id FROM tmp_com)::text,
  p_sorgente_riga => NULL, p_meta => '{}'::jsonb);

-- Helper: una CA con segment_key esplicito, tipo_movimento e meta.
-- La causale onere e' obbligatoria se e solo se tipo_movimento='ONERE'
-- (CHECK biconditional chk_commesse_attivita_causale_onere).
CREATE OR REPLACE FUNCTION pg_temp.mk_af(p_segment varchar, p_qta numeric,
                                         p_tipo_mov varchar, p_meta jsonb)
RETURNS void AS $$
DECLARE
  r RECORD;
  v_causale_id bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  IF p_tipo_mov = 'ONERE' THEN
    SELECT id INTO v_causale_id FROM config.causali_onere WHERE attivo ORDER BY id LIMIT 1;
  END IF;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com),
    -- La riga NORMALE ha la sua sorgente; ONERE e RETTIFICA no (vincolo 20261012-27).
    p_sorgente_tipo_id => CASE WHEN p_tipo_mov = 'NORMALE' THEN (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA') END,
    p_sorgente_uid => CASE WHEN p_tipo_mov = 'NORMALE' THEN ((SELECT commessa_id FROM tmp_com))::text END,
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
    p_meta => p_meta, p_causale_onere_id => v_causale_id);
END $$ LANGUAGE plpgsql;

-- ============================================================
-- Le attivita' del test
-- ============================================================

-- Righe semplici, una per corsia.
SELECT pg_temp.mk_af('DDT_VENDITA:' || (SELECT u_ddt FROM tmp_seg)::text || ':R:900005', 12, 'NORMALE', '{}'::jsonb);
SELECT pg_temp.mk_af('ORDINE_VENDITA:' || (SELECT u_ord FROM tmp_seg)::text || ':R:900006',  4, 'NORMALE', '{}'::jsonb);

-- ONERE sulla STESSA riga_id 900006, da un documento diverso: stessa riga
-- sorgente, movimento diverso. Deve uscire come riga a se'.
SELECT pg_temp.mk_af('ORDINE_VENDITA:' || (SELECT u_onere FROM tmp_seg)::text || ':R:900006', 9, 'ONERE', '{}'::jsonb);

-- ⭐ KIT BEN FORMATO, con tre coefficienti DIVERSI che concordano sul padre 10:
--     20 / 2   = 10
--     10 / 1   = 10
--      5 / 0.5 = 10
-- E' il caso che il DB di sviluppo non contiene (li' i coeff valgono tutti 1)
-- e che rende la divisione una verifica invece di una formalita'.
SELECT pg_temp.mk_af('ORDINE_VENDITA:' || (SELECT u_kit_ok FROM tmp_seg)::text || ':R:900001#CMP:c1', 20, 'NORMALE',
                     jsonb_build_object('coeff_qta','2'));
SELECT pg_temp.mk_af('ORDINE_VENDITA:' || (SELECT u_kit_ok FROM tmp_seg)::text || ':R:900001#CMP:c2', 10, 'NORMALE',
                     jsonb_build_object('coeff_qta','1'));
SELECT pg_temp.mk_af('ORDINE_VENDITA:' || (SELECT u_kit_ok FROM tmp_seg)::text || ':R:900001#CMP:c3',  5, 'NORMALE',
                     jsonb_build_object('coeff_qta','0.5'));

-- Kit SENZA coefficiente nel meta: la quantita' del padre non e' ricostruibile.
SELECT pg_temp.mk_af('ORDINE_VENDITA:' || (SELECT u_kit_senza_coeff FROM tmp_seg)::text || ':R:900002#CMP:c1', 6, 'NORMALE', '{}'::jsonb);
SELECT pg_temp.mk_af('ORDINE_VENDITA:' || (SELECT u_kit_senza_coeff FROM tmp_seg)::text || ':R:900002#CMP:c2', 6, 'NORMALE', '{}'::jsonb);

-- Kit INCOERENTE: i due componenti non concordano sul padre (10/1=10 vs 10/2=5).
-- Succede se il kit e' stato fatturato solo in parte: il padre e' ambiguo.
SELECT pg_temp.mk_af('ORDINE_VENDITA:' || (SELECT u_kit_incoerente FROM tmp_seg)::text || ':R:900003#CMP:c1', 10, 'NORMALE',
                     jsonb_build_object('coeff_qta','1'));
SELECT pg_temp.mk_af('ORDINE_VENDITA:' || (SELECT u_kit_incoerente FROM tmp_seg)::text || ':R:900003#CMP:c2', 10, 'NORMALE',
                     jsonb_build_object('coeff_qta','2'));

-- Stesso NUMERO di riga su due corsie diverse: due righe di documento senza
-- alcun rapporto fra loro (sequenze diverse).
SELECT pg_temp.mk_af('ORDINE_VENDITA:' || (SELECT u_collisione_ord FROM tmp_seg)::text || ':R:900004', 7, 'NORMALE', '{}'::jsonb);
SELECT pg_temp.mk_af('DDT_VENDITA:' || (SELECT u_collisione_ddt FROM tmp_seg)::text || ':R:900004', 3, 'NORMALE', '{}'::jsonb);

-- Emissione: PRONTA_FATTURAZIONE + pull -> nascono le attivita' fatturabili.
-- La vista legge le AF: senza questo passo non vedrebbe nulla.
-- rev 2026-10-27: il verbo della commessa chiede cambia_stato_commessa
-- all'operatore del test (giro 10); senza, su un db dove l'operatore non ce l'ha,
-- si ferma qui con E_PERMESSO_NEGATO.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');
SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com));

-- ============================================================
-- 4-5) Righe semplici: la quantita' passa invariata
-- ============================================================
SELECT is(
  (SELECT quantita FROM vendite.vw_af_merce_per_riga
    WHERE corsia='DDT_VENDITA' AND riga_id=900005 AND tipo_movimento='NORMALE'),
  12::numeric,
  '4) corsia DDT, riga semplice: quantita = 12 (invariata)');

SELECT is(
  (SELECT quantita FROM vendite.vw_af_merce_per_riga
    WHERE corsia='ORDINE_VENDITA' AND riga_id=900006 AND tipo_movimento='NORMALE'),
  4::numeric,
  '5) corsia ORD, riga semplice: quantita = 4 (invariata)');

-- ============================================================
-- 6) tipo_movimento NON e' filtrato: l'ONERE esce come riga a se'
--    sulla stessa riga_id. E' il vincolo §4.3 del brief, scritto come test:
--    se qualcuno filtrasse qui, la nota di credito dovrebbe riscrivere la base.
-- ============================================================
SELECT is(
  (SELECT quantita FROM vendite.vw_af_merce_per_riga
    WHERE corsia='ORDINE_VENDITA' AND riga_id=900006 AND tipo_movimento='ONERE'),
  9::numeric,
  '6) ONERE esce come riga a se'' sulla stessa riga_id: la vista non filtra tipo_movimento');

-- ============================================================
-- 7-8) ⭐ Il kit con coefficienti diversi da 1
-- ============================================================
SELECT is(
  (SELECT quantita FROM vendite.vw_af_merce_per_riga
    WHERE corsia='ORDINE_VENDITA' AND riga_id=900001 AND tipo_movimento='NORMALE'),
  10::numeric,
  '7) kit con coeff 2/1/0.5 su qta 20/10/5: quantita = 10 in unita'' del PADRE (non 35)');

SELECT ok(
  (SELECT da_componenti AND misurabile FROM vendite.vw_af_merce_per_riga
    WHERE corsia='ORDINE_VENDITA' AND riga_id=900001 AND tipo_movimento='NORMALE'),
  '8) quel kit e'' marcato da_componenti e misurabile');

-- ============================================================
-- 9-10) I due modi in cui un kit NON e' misurabile.
--   In entrambi la quantita' esce comunque un numero: e' `misurabile` a dire
--   che non va usato. Zero e «non lo so» non sono la stessa cosa.
-- ============================================================
SELECT ok(
  (SELECT NOT misurabile FROM vendite.vw_af_merce_per_riga
    WHERE corsia='ORDINE_VENDITA' AND riga_id=900002 AND tipo_movimento='NORMALE'),
  '9) kit senza coeff_qta nel meta -> misurabile = false');

SELECT ok(
  (SELECT NOT misurabile FROM vendite.vw_af_merce_per_riga
    WHERE corsia='ORDINE_VENDITA' AND riga_id=900003 AND tipo_movimento='NORMALE'),
  '10) kit con componenti che non concordano (10/1 vs 10/2) -> misurabile = false');

-- ============================================================
-- 11) Le due sequenze: stesso numero, due righe diverse.
--     Se un giorno qualcuno unisse le corsie, questo test diventa rosso —
--     ed e' il solo posto in cui quel difetto si vedrebbe.
-- ============================================================
SELECT results_eq(
  $$SELECT corsia::text, quantita FROM vendite.vw_af_merce_per_riga
     WHERE riga_id = 900004 ORDER BY corsia$$,
  $$VALUES ('DDT_VENDITA'::text, 3::numeric), ('ORDINE_VENDITA'::text, 7::numeric)$$,
  '11) stesso riga_id su corsia ORD e DDT: due righe distinte, 7 e 3');

SELECT * FROM finish();
ROLLBACK;
