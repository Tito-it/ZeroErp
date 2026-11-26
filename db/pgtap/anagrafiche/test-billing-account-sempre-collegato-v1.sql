-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: ogni billing account ha sempre il suo collegamento a un'azienda.
-- Oggetti: trg_emittenti_fiscali_ba_a05_block_delete_dlt (20261126-30),
--   trg_emittenti_fiscali_ba_a05_block_sposta_upd (-31),
--   anagrafiche.trgfn_efba_guard_storia_emittente (-32),
--   trg_billing_account_a05_block_delete_dlt (-40),
--   la storia di anagrafiche.fn_ba_ha_storia_emittente (-26).
-- Riferimento: brief-db-revisione-anagrafiche §24.5 (D-T4-3, D-T4-4), §24.7.1.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il collegamento di un billing account non si cancella
--     (E_BA_COLLEGAMENTO_NON_SI_TOGLIE) e non passa a un altro conto
--     (E_BA_COLLEGAMENTO_NON_SI_SPOSTA);
--   - il billing account non si cancella: il cliente si annulla
--     (E_BA_NON_SI_CANCELLA);
--   - l'azienda di un billing account si cambia modificando il collegamento,
--     finche' non ha documenti; un documento anche in bozza lo chiude
--     (E_BA_EMITTENTE_CON_STORIA);
--   - spostare l'azienda predefinita non cambia l'azienda di nessun cliente;
--   - presidio: nessun billing account e' senza collegamento.
--   La nascita senza sessione collegata alla predefinita la prova
--   anagrafiche/test-billing-account-auto-link-ef (test 1).
--
-- Elenco test (plan 9):
--   1) cancellare il collegamento del BA -> E_BA_COLLEGAMENTO_NON_SI_TOGLIE
--   2) spostare il collegamento su un altro BA -> E_BA_COLLEGAMENTO_NON_SI_SPOSTA
--   3) cancellare il BA -> E_BA_NON_SI_CANCELLA, col codice del BA
--   4) il BA senza documenti cambia azienda modificando il collegamento -> passa
--   5) ... e torna all'azienda di partenza -> passa
--   6) con una fattura in bozza il cambio d'azienda e' respinto
--   7) spostare la predefinita su un'altra azienda -> passa
--   8) ... e il BA resta all'azienda del suo collegamento
--   9) presidio: nessun billing account senza collegamento
-- ------------------------------------------------------------

BEGIN;

-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_mondo_cliente.
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- Fixture: due clienti del mondo (due BA sulla stessa azienda) e una seconda
-- azienda. ⛔ Cio' che un builder scrive si legge in un'istruzione SEPARATA.
-- ============================================================
CREATE TEMP TABLE _t_m1 AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('sempre collegato 1');
CREATE TEMP TABLE _t_m2 AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('sempre collegato 2');

CREATE TEMP TABLE _t_ref AS
SELECT m1.billing_account_id          AS ba_1,
       m2.billing_account_id          AS ba_2,
       m1.emittente_soggetto_ruolo_id AS ef_mio,
       (SELECT e.soggetto_ruolo_id FROM dbops.fn_pgtap_crea_emittente() e) AS ef_altro
  FROM _t_m1 m1, _t_m2 m2;

-- ============================================================
-- Il collegamento non si toglie e non si sposta; il BA non si cancella
-- ============================================================
SELECT throws_like(
    format($$DELETE FROM anagrafiche.emittenti_fiscali_billing_account WHERE billing_account_id = %s$$,
           (SELECT ba_1 FROM _t_ref)),
    '%non si cancella: per cambiare azienda si modifica%',
    '1) cancellare il collegamento del BA -> E_BA_COLLEGAMENTO_NON_SI_TOGLIE');

SELECT throws_like(
    format($$UPDATE anagrafiche.emittenti_fiscali_billing_account SET billing_account_id = %s
              WHERE billing_account_id = %s$$,
           (SELECT ba_2 FROM _t_ref), (SELECT ba_1 FROM _t_ref)),
    '%non passa a un altro cliente%',
    '2) spostare il collegamento su un altro BA -> E_BA_COLLEGAMENTO_NON_SI_SPOSTA');

SELECT throws_like(
    format($$DELETE FROM anagrafiche.billing_account WHERE id = %s$$, (SELECT ba_1 FROM _t_ref)),
    '%' || (SELECT codice FROM anagrafiche.billing_account WHERE id = (SELECT ba_1 FROM _t_ref))
        || ' non si cancella%',
    '3) cancellare il BA -> E_BA_NON_SI_CANCELLA, col codice del BA');

-- ============================================================
-- Il cambio d'azienda: modificando il collegamento, solo senza documenti
-- ============================================================
SELECT lives_ok(
    format($$UPDATE anagrafiche.emittenti_fiscali_billing_account SET emittente_soggetto_ruolo_id = %s
              WHERE billing_account_id = %s$$,
           (SELECT ef_altro FROM _t_ref), (SELECT ba_2 FROM _t_ref)),
    '4) il BA senza documenti cambia azienda modificando il collegamento -> passa');

SELECT lives_ok(
    format($$UPDATE anagrafiche.emittenti_fiscali_billing_account SET emittente_soggetto_ruolo_id = %s
              WHERE billing_account_id = %s$$,
           (SELECT ef_mio FROM _t_ref), (SELECT ba_2 FROM _t_ref)),
    '5) ... e torna all''azienda di partenza -> passa');

-- Una fattura in bozza sul BA 2: un documento, anche senza numero.
CREATE TEMP TABLE _t_fat AS
SELECT f.fattura_id
  FROM dbops.fn_pgtap_crea_fattura('sempre collegato', 'DRAFT', (SELECT ba_2 FROM _t_ref)) f;

SELECT throws_like(
    format($$UPDATE anagrafiche.emittenti_fiscali_billing_account SET emittente_soggetto_ruolo_id = %s
              WHERE billing_account_id = %s$$,
           (SELECT ef_altro FROM _t_ref), (SELECT ba_2 FROM _t_ref)),
    '%ha gia'' documenti%',
    '6) con una fattura in bozza il cambio d''azienda e'' respinto -> E_BA_EMITTENTE_CON_STORIA');

-- ============================================================
-- La predefinita si sposta senza toccare nessun cliente
-- ============================================================
CREATE TEMP TABLE _t_prima AS
SELECT script.fn_get_ba_emittente_sr_id_installazione((SELECT ba_1 FROM _t_ref)) AS azienda_ba_1;

SELECT lives_ok(
    format($$UPDATE anagrafiche.emittenti_fiscali_billing_account SET emittente_soggetto_ruolo_id = %s
              WHERE is_default$$,
           (SELECT ef_altro FROM _t_ref)),
    '7) spostare la predefinita su un''altra azienda -> passa');

SELECT is(
    script.fn_get_ba_emittente_sr_id_installazione((SELECT ba_1 FROM _t_ref)),
    (SELECT azienda_ba_1 FROM _t_prima),
    '8) ... e il BA resta all''azienda del suo collegamento');

-- ============================================================
-- Presidio
-- ⚠️ Conta righe esistenti: su un database nuovo e' vero anche a vuoto. Il
--   caso lo costruiscono i test 1-8; questo dice che i dati del database
--   rispettano la regola (il collegamento dei BA nati prima, 20261126-29).
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM anagrafiche.billing_account ba
      WHERE NOT EXISTS (SELECT 1 FROM anagrafiche.emittenti_fiscali_billing_account e
                         WHERE e.billing_account_id = ba.id)),
    0,
    '9) presidio: nessun billing account senza collegamento');

SELECT * FROM finish();
ROLLBACK;
