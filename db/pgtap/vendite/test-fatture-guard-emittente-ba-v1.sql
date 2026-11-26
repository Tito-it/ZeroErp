-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la fattura e' emessa dall'azienda del suo cliente.
-- Oggetti: trg_fatture_a10_guard_emittente_ba_ins_upd (20261126-36),
--   script.trgfn_doc_guard_emittente_ba.
-- Riferimento: brief-db-revisione-anagrafiche §24.5 (S27).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - emittente_soggetto_ruolo_id della fattura e' l'azienda che il suo
--     billing account risolve, come per gli altri documenti di vendita;
--   - un'azienda diversa e' rifiutata con E_DOC_EMITTENTE_BA_INCOERENTE, la
--     frase che nomina il documento e le due aziende, il campo della colonna.
--
-- Elenco test (plan 3):
--   1) il guard e' montato su vendite.fatture (cercato per funzione)
--   2) la fattura in bozza del cliente passa a un'altra azienda -> rifiutato
--   3) ... col campo emittente_soggetto_ruolo_id
-- ------------------------------------------------------------

BEGIN;

-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_mondo_cliente.
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

-- Il campo del rifiuto (canale COLUMN).
CREATE OR REPLACE FUNCTION pg_temp.colonna_del_rifiuto(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_col text;
BEGIN
    EXECUTE p_sql;
    RETURN '(nessun rifiuto)';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_col = COLUMN_NAME;
    RETURN v_col;
END $f$;

CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('fattura azienda del cliente');

-- Una fattura in bozza del cliente del mondo, e un'altra azienda.
CREATE TEMP TABLE _t_fat AS
SELECT f.fattura_id
  FROM dbops.fn_pgtap_crea_fattura('fattura azienda del cliente', 'DRAFT',
                                   (SELECT billing_account_id FROM _t_mondo)) f;

CREATE TEMP TABLE _t_altra AS
SELECT e.soggetto_ruolo_id AS ef_altro FROM dbops.fn_pgtap_crea_emittente() e;

SELECT is(
    (SELECT count(*)::int FROM pg_catalog.pg_trigger t
      WHERE t.tgrelid = 'vendite.fatture'::regclass
        AND NOT t.tgisinternal
        AND t.tgfoid = 'script.trgfn_doc_guard_emittente_ba'::regproc),
    1,
    '1) il guard dell''azienda del cliente e'' montato su vendite.fatture');

SELECT throws_like(
    format($$UPDATE vendite.fatture SET emittente_soggetto_ruolo_id = %s WHERE id = %s$$,
           (SELECT ef_altro FROM _t_altra), (SELECT fattura_id FROM _t_fat)),
    '%non e'' quella del cliente%',
    '2) la fattura in bozza passa a un''altra azienda -> E_DOC_EMITTENTE_BA_INCOERENTE');

SELECT is(
    pg_temp.colonna_del_rifiuto(
        format($$UPDATE vendite.fatture SET emittente_soggetto_ruolo_id = %s WHERE id = %s$$,
               (SELECT ef_altro FROM _t_altra), (SELECT fattura_id FROM _t_fat))),
    'emittente_soggetto_ruolo_id',
    '3) ... col campo emittente_soggetto_ruolo_id');

SELECT * FROM finish();
ROLLBACK;
