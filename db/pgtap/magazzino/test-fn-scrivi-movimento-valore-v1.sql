-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto sono i CONTROLLI della primitiva
--   magazzino.fn_scrivi_movimento, che dal 2026-09-24 l'app non esegue piu': la
--   raggiunge solo dai verbi fn_posta_inventario / fn_posta_rettifica
--   (brief-db-magazzino-verbi-con-permesso, P-4). Chiamarla coi parametri che il
--   test sceglie e' cosa che solo uno scrittore privilegiato puo' fare: forma 3
--   del criterio del runner, come i test del ledger del Lotto 2. Il contesto
--   operatore resta impostato: il guard di scope e i controlli lo leggono.
--
-- Test: il VALORE (M-4, D-L2-c, C6, C7) — i tre significati del costo nella
--   primitiva, la copia valore_giacenza, la ri-somma, le spie. Brief:
--   brief-db-magazzino-lotto-2-motore, sezioni 4.2 (passi 12-14) e 4.4, sezione 7.
--
-- ⚠️ Fixture COSTRUITA: due magazzini, un articolo, le sorgenti (una riga di
--   inventario DRAFT per scrittura). La scrittura FUORI PORTA che fa
--   comparire la divergenza ha il suo file owner
--   (test-valore-giacenza-divergenza-owner-v1). Da P-4 (2026-09-24) anche questo
--   file gira come owner: l'app non esegue piu' la primitiva (marcatore in testa).
--
-- Elenco test (plan 10):
--   1) entrata 5 a 10 EUR + entrata 5 a 20 EUR -> valore 150, media 15
--   2) uscita 4 -> costo 15 SUL MOVIMENTO (la media corrente, dentro il lock), valore 90
--   3) entrata senza costo CON una media -> eredita la media (COALESCE): valore 120
--   4) entrata senza costo e SENZA media (articolo nuovo) -> costo NULL, valore 0, riga in vw_magazzino_movimenti_senza_costo
--   5) trasferimento: OUT 3 da A (media 15) e IN 3 in B con lo stesso transfer_uid -> la IN porta 15
--   6) ...e i due valori si spostano: A 120 - 45 = 75, B 45
--   7) storno della OUT (STORNO_POS +3, stessa sorgente e posizione) -> costo dell'originale (15)
--   8) la ri-somma coincide con la copia: nessuna divergenza sul mondo costruito
--   9) fn_ricalcola_valore_giacenza(A) tocca le coppie di A e non cambia niente (prima = dopo)
--  10) la divergenza NON prova l'aritmetica: e' security_invoker e legge le stesse righe (reloptions)
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

CREATE TEMP TABLE _fix (mag_a bigint, mag_b bigint, art uuid, art2 uuid, src bigint,
                        r1 bigint, r2 bigint, r3 bigint, r4 bigint, r5 bigint, r6 bigint);
DO $fix$
DECLARE
    v_a bigint; v_b bigint; v_art uuid; v_art2 uuid; v_inv bigint; v_tmp bigint;
    v_r bigint[] := '{}'; i int;
BEGIN
    v_a := dbops.fn_pgtap_crea_magazzino('PGT-L2V-A', false);
    v_b := dbops.fn_pgtap_crea_magazzino('PGT-L2V-B', false);
    v_art  := dbops.fn_pgtap_crea_articolo('PGT-L2V-ART', true, false, false);
    v_art2 := dbops.fn_pgtap_crea_articolo('PGT-L2V-NUOVO', true, false, false);
    FOR i IN 1..6 LOOP
        INSERT INTO magazzino.inventari (magazzino_id) VALUES (v_a) RETURNING id INTO v_inv;
        INSERT INTO magazzino.inventari_righe (inventario_id, articolo_id, qta_contata) VALUES (v_inv, CASE WHEN i = 4 THEN v_art2 ELSE v_art END, i) RETURNING id INTO v_tmp;
        v_r := v_r || v_tmp;
    END LOOP;
    INSERT INTO _fix VALUES (v_a, v_b, v_art, v_art2,
                             (SELECT id FROM config.sorgenti WHERE codice_interno = 'INVENTARIO_RIGA'),
                             v_r[1], v_r[2], v_r[3], v_r[4], v_r[5], v_r[6]);
END $fix$;

-- 1) 5 x 10 + 5 x 20
SELECT magazzino.fn_scrivi_movimento(mag_a, art, 'INV_INIZIALE', 5, src, r1, NULL, 10) FROM _fix;
SELECT magazzino.fn_scrivi_movimento(mag_a, art, 'RETT_POS',     5, src, r2, NULL, 20) FROM _fix;
SELECT is(
    (SELECT (trim_scale(v.valore), trim_scale(v.costo_medio))::text FROM magazzino.vw_giacenza_valorizzata v JOIN _fix f ON v.magazzino_id = f.mag_a AND v.articolo_id = f.art),
    '(150,15)',
    '1) 5 a 10 EUR + 5 a 20 EUR: valore 150, media 15');

-- 2) uscita 4
SELECT magazzino.fn_scrivi_movimento(mag_a, art, 'RETT_NEG', -4, src, r3) FROM _fix;
SELECT is(
    (SELECT (trim_scale(m.costo_unitario), (SELECT trim_scale(vg.valore) FROM magazzino.valore_giacenza vg WHERE vg.magazzino_id = f.mag_a AND vg.articolo_id = f.art))::text
       FROM magazzino.movimenti m JOIN _fix f ON m.sorgente_riga = f.r3),
    '(15,90)',
    '2) uscita 4: costo 15 sul movimento (la media, letta dentro il lock), valore 90');

-- 3) entrata senza costo con una media
SELECT magazzino.fn_scrivi_movimento(mag_a, art, 'RETT_POS', 2, src, r5) FROM _fix;
SELECT is(
    (SELECT (trim_scale(m.costo_unitario), (SELECT trim_scale(vg.valore) FROM magazzino.valore_giacenza vg WHERE vg.magazzino_id = f.mag_a AND vg.articolo_id = f.art))::text
       FROM magazzino.movimenti m JOIN _fix f ON m.sorgente_riga = f.r5),
    '(15,120)',
    '3) entrata senza costo CON una media: eredita la media (COALESCE, D-L2-c), valore 120');

-- 4) entrata senza costo e senza media: l'articolo nuovo
SELECT magazzino.fn_scrivi_movimento(mag_a, art2, 'INV_INIZIALE', 3, src, r4) FROM _fix;
SELECT is(
    (SELECT (m.costo_unitario IS NULL,
             (SELECT trim_scale(vg.valore) FROM magazzino.valore_giacenza vg WHERE vg.magazzino_id = f.mag_a AND vg.articolo_id = f.art2),
             (SELECT count(*) FROM dbops.vw_magazzino_movimenti_senza_costo s WHERE s.id = m.id))::text
       FROM magazzino.movimenti m JOIN _fix f ON m.sorgente_riga = f.r4),
    '(t,0,1)',
    '4) entrata senza costo e senza media: costo NULL, valore 0, e la riga sta nella spia LAVORAZIONE');

-- 5-6) trasferimento con lo stesso transfer_uid
SELECT magazzino.fn_scrivi_movimento(mag_a, art, 'TRASF_OUT', -3, src, r6, NULL, NULL, NULL, NULL, NULL, now(), '22222222-2222-2222-2222-222222222222') FROM _fix;
SELECT magazzino.fn_scrivi_movimento(mag_b, art, 'TRASF_IN',   3, src, r6, NULL, NULL, NULL, NULL, NULL, now(), '22222222-2222-2222-2222-222222222222') FROM _fix;
SELECT is(
    (SELECT trim_scale(m.costo_unitario)::text FROM magazzino.movimenti m JOIN _fix f ON m.magazzino_id = f.mag_b AND m.transfer_uid = '22222222-2222-2222-2222-222222222222'),
    '15',
    '5) la IN del trasferimento porta il costo della OUT (media 15)');
SELECT is(
    (SELECT string_agg(mg.codice || '=' || trim_scale(vg.valore), ' ' ORDER BY mg.codice)
       FROM magazzino.valore_giacenza vg JOIN magazzino.magazzini mg ON mg.id = vg.magazzino_id JOIN _fix f ON vg.articolo_id = f.art),
    'PGT-L2V-A=75 PGT-L2V-B=45',
    '6) i valori si spostano: A 120 - 45, B 45');

-- 7) storno della OUT
SELECT magazzino.fn_scrivi_movimento(mag_a, art, 'STORNO_POS', 3, src, r6, NULL, NULL, NULL, NULL, NULL, now(), NULL,
           (SELECT m.id FROM magazzino.movimenti m WHERE m.transfer_uid = '22222222-2222-2222-2222-222222222222' AND m.qta < 0)) FROM _fix;
SELECT is(
    (SELECT trim_scale(m.costo_unitario)::text FROM magazzino.movimenti m WHERE m.storno_di_movimento_id IS NOT NULL AND m.sorgente_riga = (SELECT r6 FROM _fix)),
    '15',
    '7) lo storno va al costo dell''originale');

-- 8-9) ri-somma e divergenza
SELECT is(
    (SELECT count(*) FROM dbops.vw_magazzino_valore_giacenza_divergente d JOIN _fix f ON d.magazzino_id IN (f.mag_a, f.mag_b)),
    0::bigint,
    '8) copia e ri-somma coincidono per costruzione: nessuna divergenza');
SELECT is(
    (SELECT string_agg(trim_scale(r.valore_prima)::text || '->' || trim_scale(r.valore_dopo)::text, ' ' ORDER BY r.articolo_id::text)
       FROM magazzino.fn_ricalcola_valore_giacenza((SELECT mag_a FROM _fix)) r),
    (SELECT string_agg(trim_scale(vg.valore)::text || '->' || trim_scale(vg.valore)::text, ' ' ORDER BY vg.articolo_id::text)
       FROM magazzino.valore_giacenza vg WHERE vg.magazzino_id = (SELECT mag_a FROM _fix)),
    '9) il ricalcolo tocca le coppie del magazzino e non cambia niente: prima = dopo');

SELECT is(
    (SELECT reloptions::text FROM pg_class WHERE oid = 'dbops.vw_magazzino_valore_giacenza_divergente'::regclass),
    '{security_invoker=true}',
    '10) la spia della divergenza e'' security_invoker (letta a presidio come DEFINER da fn_conta_presidio)');

SELECT * FROM finish();
ROLLBACK;
