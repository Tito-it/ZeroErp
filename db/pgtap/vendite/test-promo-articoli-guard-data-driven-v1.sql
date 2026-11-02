-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.promo_articoli DISABLE TRIGGER del guard sotto test, per
--   piantare le fixture nei tre stati pre-esistenti che il guard oggi vieta.
--   ⚠️ E' l'unico dei marcati in cui il DDL e' una scorciatoia di fixture, non
--   lo strumento del collaudo: si potrebbe togliere riscrivendo le fixture.
-- pgTAP test per Zero ERP
--
-- Test: guard data-driven su vendite.promo_articoli (migration
--       20260427-01-create-trgfn-promo-articoli-guard-data-driven).
--
-- Lo stato della promo (FUTURA/INIZIATA/SCADUTA) e' derivato dalle
-- date e mai persistito. Il guard data-driven applica:
--   INSERT  -> valido_dal > script.fn_data_operativa() (no retroattiva)
--   UPDATE  FUTURA   tutti mutabili, date solo nel futuro
--           INIZIATA solo descrizione/valido_al(>=today)/meta
--           SCADUTA  immutabile (nessun campo dominio mutabile)
--
-- Indice test (1..18):
--   1)  INSERT con valido_dal = oggi -> E_PROMO_RETROATTIVA
--   2)  INSERT con valido_dal = ieri -> E_PROMO_RETROATTIVA
--   3)  INSERT con valido_dal = domani -> ammesso
--   4)  UPDATE descrizione su SCADUTA -> E_PROMO_SCADUTA_IMMUTABILE
--   5)  UPDATE valido_al su SCADUTA -> E_PROMO_SCADUTA_IMMUTABILE
--   6)  UPDATE no-op (no campo dominio cambia) su SCADUTA -> ammesso
--   7)  UPDATE descrizione su INIZIATA -> ammesso
--   8)  UPDATE valido_al > oggi su INIZIATA -> ammesso
--   9)  UPDATE valido_al < oggi su INIZIATA -> E_PROMO_RETROATTIVA
--   10) UPDATE tipo_variazione su INIZIATA -> E_PROMO_INIZIATA_CAMPI_RISTRETTI
--   11) UPDATE valore_variazione su INIZIATA -> E_PROMO_INIZIATA_CAMPI_RISTRETTI
--   12) UPDATE valido_dal su INIZIATA -> E_PROMO_INIZIATA_CAMPI_RISTRETTI
--   13) UPDATE attivo=false su INIZIATA -> E_PROMO_INIZIATA_CAMPI_RISTRETTI
--   14) UPDATE meta su INIZIATA -> ammesso
--   15) UPDATE tipo_variazione su FUTURA -> ammesso
--   16) UPDATE valido_dal verso futuro su FUTURA -> ammesso
--   17) UPDATE valido_dal = oggi su FUTURA -> E_PROMO_RETROATTIVA
--   18) UPDATE valido_al < oggi su FUTURA -> E_PROMO_RETROATTIVA
--
-- Strategia fixture:
--   Il guard INSERT blocca la creazione diretta di promo INIZIATA o
--   SCADUTA (date <= oggi). Per allestire le fixture si disabilita
--   temporaneamente il trigger guard, si inseriscono le 3 promo nei
--   tre stati, poi si riabilita per testare gli UPDATE. Si usano 3
--   articoli "vergini" (senza promo preesistenti) per evitare
--   collisioni con ex_promo_articoli_no_overlap.
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(18);

-- ============================================================
-- Setup fixture
-- ============================================================

-- 4 articoli COSTRUITI, senza promo (uno per stato, piu' quello del test 3).
-- ⚠️ Rev 2026-10-14 (20261014-05, D-6 di brief-db-articoli-ammessi-per-documento):
--   prima si pescavano «i primi articoli attivi senza promo per id», e uno
--   poteva essere solo componente, su cui una promo ora e' rifiutata. Il
--   builder li fa nascere merce e non solo componente. La UoM in una seconda
--   istruzione: la riga nata dal builder non e' visibile alla stessa.
CREATE TEMP TABLE tmp_ctx_articoli AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-PROMO-GD-' || g, false) AS articolo_id,
       NULL::bigint AS uom_id,
       g AS rn
  FROM generate_series(1, 4) AS g;
UPDATE tmp_ctx_articoli t SET uom_id = a.uom_id
  FROM catalogo.articoli a
 WHERE a.id = t.articolo_id;

-- Disabilita il guard data-driven solo per inserire le fixture nei
-- 3 stati pre-esistenti. Gli altri trigger (audit, tx_id, il guard comune
-- delle date), l'EXCLUDE e la colonna generata validita restano attivi.
ALTER TABLE vendite.promo_articoli
    DISABLE TRIGGER trg_promo_articoli_a10_guard_data_driven_ins_upd;

INSERT INTO vendite.promo_articoli(
    codice, descrizione, articolo_id, uom_id,
    tipo_variazione, valore_variazione, valido_dal, valido_al
)
SELECT 'PGTAP_PROMO_GD_FUT', 'Test FUTURA', a.articolo_id, a.uom_id,
       'PERCENTUALE', 10, script.fn_data_operativa() + 30, script.fn_data_operativa() + 60
  FROM tmp_ctx_articoli a WHERE a.rn = 1;

INSERT INTO vendite.promo_articoli(
    codice, descrizione, articolo_id, uom_id,
    tipo_variazione, valore_variazione, valido_dal, valido_al
)
SELECT 'PGTAP_PROMO_GD_INI', 'Test INIZIATA', a.articolo_id, a.uom_id,
       'PERCENTUALE', 10, script.fn_data_operativa() - 5, script.fn_data_operativa() + 5
  FROM tmp_ctx_articoli a WHERE a.rn = 2;

INSERT INTO vendite.promo_articoli(
    codice, descrizione, articolo_id, uom_id,
    tipo_variazione, valore_variazione, valido_dal, valido_al
)
SELECT 'PGTAP_PROMO_GD_SCAD', 'Test SCADUTA', a.articolo_id, a.uom_id,
       'PERCENTUALE', 10, script.fn_data_operativa() - 60, script.fn_data_operativa() - 30
  FROM tmp_ctx_articoli a WHERE a.rn = 3;

-- Forza la fire degli eventi DEFERRED accodati dagli INSERT delle
-- fixture (constraint trigger dbops.trgfn_child_requires_active_parent
-- registrati come CONSTRAINT TRIGGER DEFERRABLE INITIALLY DEFERRED).
-- Senza questo SET, l'ALTER TABLE ENABLE successivo fallisce con
-- "non e' possibile effettuare ALTER TABLE perche' ha eventi trigger
-- in sospeso".
SET CONSTRAINTS ALL IMMEDIATE;

ALTER TABLE vendite.promo_articoli
    ENABLE TRIGGER trg_promo_articoli_a10_guard_data_driven_ins_upd;

-- ============================================================
-- 1) INSERT con valido_dal = oggi -> E_PROMO_RETROATTIVA
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO vendite.promo_articoli(
          codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_GD_INS_OGGI', 'Test', a.articolo_id, a.uom_id,
             'PERCENTUALE', 5, script.fn_data_operativa(), script.fn_data_operativa() + 10
        FROM tmp_ctx_articoli a WHERE a.rn = 1$$,
    'P0001',
    NULL,
    'INSERT con valido_dal=oggi deve essere bloccato (no-retroattiva)'
);

-- ============================================================
-- 2) INSERT con valido_dal = ieri -> E_PROMO_RETROATTIVA
-- ============================================================
SELECT throws_ok(
    $$INSERT INTO vendite.promo_articoli(
          codice, descrizione, articolo_id, uom_id,
          tipo_variazione, valore_variazione, valido_dal, valido_al)
      SELECT 'PGTAP_PROMO_GD_INS_IERI', 'Test', a.articolo_id, a.uom_id,
             'PERCENTUALE', 5, script.fn_data_operativa() - 1, script.fn_data_operativa() + 10
        FROM tmp_ctx_articoli a WHERE a.rn = 1$$,
    'P0001',
    NULL,
    'INSERT con valido_dal nel passato deve essere bloccato'
);

-- ============================================================
-- 3) INSERT con valido_dal = domani -> ammesso
--    Il quarto articolo costruito: diverso dai 3 delle promo
--    nei tre stati, per evitare overlap con la FUTURA su rn=1.
-- ============================================================
INSERT INTO vendite.promo_articoli(
    codice, descrizione, articolo_id, uom_id,
    tipo_variazione, valore_variazione, valido_dal, valido_al)
SELECT 'PGTAP_PROMO_GD_INS_OK', 'Test', a.articolo_id, a.uom_id,
       'PERCENTUALE', 5, script.fn_data_operativa() + 1, script.fn_data_operativa() + 10
  FROM tmp_ctx_articoli a WHERE a.rn = 4;

SELECT ok(
    EXISTS (
        SELECT 1 FROM vendite.promo_articoli
         WHERE codice = 'PGTAP_PROMO_GD_INS_OK'
    ),
    'INSERT con valido_dal=domani ammesso (happy path)'
);

-- ============================================================
-- 4) UPDATE descrizione su SCADUTA -> E_PROMO_SCADUTA_IMMUTABILE
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.promo_articoli
         SET descrizione = 'Modifica vietata'
       WHERE codice = 'PGTAP_PROMO_GD_SCAD'$$,
    'P0001',
    NULL,
    'UPDATE descrizione su SCADUTA deve essere bloccato (immutabile)'
);

-- ============================================================
-- 5) UPDATE valido_al su SCADUTA -> E_PROMO_SCADUTA_IMMUTABILE
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.promo_articoli
         SET valido_al = script.fn_data_operativa() + 30
       WHERE codice = 'PGTAP_PROMO_GD_SCAD'$$,
    'P0001',
    NULL,
    'UPDATE valido_al su SCADUTA deve essere bloccato (immutabile)'
);

-- ============================================================
-- 6) UPDATE no-op su SCADUTA -> ammesso
--    Riassegna campi a se stessi: nessun campo dominio cambia,
--    il guard SCADUTA lascia passare.
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.promo_articoli
         SET descrizione = descrizione
       WHERE codice = 'PGTAP_PROMO_GD_SCAD'$$,
    'UPDATE no-op (nessun campo dominio cambia) su SCADUTA ammesso'
);

-- ============================================================
-- 7) UPDATE descrizione su INIZIATA -> ammesso
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.promo_articoli
         SET descrizione = 'Descr aggiornata'
       WHERE codice = 'PGTAP_PROMO_GD_INI'$$,
    'UPDATE descrizione su INIZIATA ammesso'
);

-- ============================================================
-- 8) UPDATE valido_al verso futuro su INIZIATA -> ammesso
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.promo_articoli
         SET valido_al = script.fn_data_operativa() + 30
       WHERE codice = 'PGTAP_PROMO_GD_INI'$$,
    'UPDATE valido_al verso futuro su INIZIATA ammesso'
);

-- ============================================================
-- 9) UPDATE valido_al < oggi su INIZIATA -> E_PROMO_RETROATTIVA
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.promo_articoli
         SET valido_al = script.fn_data_operativa() - 1
       WHERE codice = 'PGTAP_PROMO_GD_INI'$$,
    'P0001',
    NULL,
    'UPDATE valido_al nel passato su INIZIATA deve essere bloccato'
);

-- ============================================================
-- 10) UPDATE tipo_variazione su INIZIATA -> E_PROMO_INIZIATA_CAMPI_RISTRETTI
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.promo_articoli
         SET tipo_variazione = 'VALORE_FISSO'
       WHERE codice = 'PGTAP_PROMO_GD_INI'$$,
    'P0001',
    NULL,
    'UPDATE tipo_variazione su INIZIATA fuori whitelist'
);

-- ============================================================
-- 11) UPDATE valore_variazione su INIZIATA -> E_PROMO_INIZIATA_CAMPI_RISTRETTI
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.promo_articoli
         SET valore_variazione = 99
       WHERE codice = 'PGTAP_PROMO_GD_INI'$$,
    'P0001',
    NULL,
    'UPDATE valore_variazione su INIZIATA fuori whitelist'
);

-- ============================================================
-- 12) UPDATE valido_dal su INIZIATA -> E_PROMO_INIZIATA_CAMPI_RISTRETTI
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.promo_articoli
         SET valido_dal = script.fn_data_operativa() - 10
       WHERE codice = 'PGTAP_PROMO_GD_INI'$$,
    'P0001',
    NULL,
    'UPDATE valido_dal su INIZIATA fuori whitelist (frozen)'
);

-- ============================================================
-- 13) UPDATE attivo = false su INIZIATA -> E_PROMO_INIZIATA_CAMPI_RISTRETTI
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.promo_articoli
         SET attivo = false
       WHERE codice = 'PGTAP_PROMO_GD_INI'$$,
    'P0001',
    NULL,
    'UPDATE attivo su INIZIATA fuori whitelist'
);

-- ============================================================
-- 14) UPDATE meta su INIZIATA -> ammesso
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.promo_articoli
         SET meta = '{"note":"aggiornato"}'::jsonb
       WHERE codice = 'PGTAP_PROMO_GD_INI'$$,
    'UPDATE meta su INIZIATA ammesso (in whitelist)'
);

-- ============================================================
-- 15) UPDATE tipo_variazione su FUTURA -> ammesso
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.promo_articoli
         SET tipo_variazione = 'VALORE_FISSO',
             valore_variazione = 7
       WHERE codice = 'PGTAP_PROMO_GD_FUT'$$,
    'UPDATE tipo_variazione su FUTURA ammesso (tutti mutabili)'
);

-- ============================================================
-- 16) UPDATE valido_dal verso futuro su FUTURA -> ammesso
-- ============================================================
SELECT lives_ok(
    $$UPDATE vendite.promo_articoli
         SET valido_dal = script.fn_data_operativa() + 90,
             valido_al  = script.fn_data_operativa() + 120
       WHERE codice = 'PGTAP_PROMO_GD_FUT'$$,
    'UPDATE date verso futuro su FUTURA ammesso'
);

-- ============================================================
-- 17) UPDATE valido_dal = oggi su FUTURA -> E_PROMO_RETROATTIVA
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.promo_articoli
         SET valido_dal = script.fn_data_operativa()
       WHERE codice = 'PGTAP_PROMO_GD_FUT'$$,
    'P0001',
    NULL,
    'UPDATE valido_dal=oggi su FUTURA deve essere bloccato'
);

-- ============================================================
-- 18) UPDATE valido_al < oggi su FUTURA -> E_PROMO_RETROATTIVA
-- ============================================================
SELECT throws_ok(
    $$UPDATE vendite.promo_articoli
         SET valido_al = script.fn_data_operativa() - 1
       WHERE codice = 'PGTAP_PROMO_GD_FUT'$$,
    'P0001',
    NULL,
    'UPDATE valido_al nel passato su FUTURA deve essere bloccato'
);

SELECT * FROM finish();
ROLLBACK;
