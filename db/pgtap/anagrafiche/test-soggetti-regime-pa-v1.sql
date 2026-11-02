-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-differiti: escluso — le persone fisiche costruite qui restano SENZA
--   indirizzi e contatti completi: il soggetto del test e' il guard BEFORE ROW
--   del regime PA, che scatta all'INSERT/UPDATE, non la saga di completezza,
--   che ha i suoi test. Con IMMEDIATE i guard differiti di soggetti
--   rifiuterebbero ogni fixture prima dell'asserzione. La finestra la apre il
--   file subito dopo il contesto (DEFERRED), e la richiude il builder delle
--   societa', che per questo viene PRIMA.
-- pgTAP test per Zero ERP
--
-- «Cliente PA» e «Split payment»: quali nature li ammettono.
--   Brief: brief-db-dati-fiscali-e-societari-del-soggetto (Parte A)
--   changeSet 20261010-85 (colonne), -86 (guard), -87 (CHECK), CSV del catalogo.
--
-- Elenco test (plan 15):
--   struttura (il contratto, dal catalogo)
--    1) per natura: PR e DI nessuno, SP e SC solo split, ENC tutti e due (A-2)
--    2) CHECK chk_tipi_soggetto_dettaglio_regime_pa_natura: PF => tutti e due false
--    3) trigger agganciato a cliente_pa, split_payment, tipo_soggetto_dettaglio_id
--   societa' ed enti (prima delle persone: il builder chiude la finestra differita)
--    4) SC in split -> passa
--    5) SC cliente PA -> E_CLIENTE_PA_NON_AMMESSO (A-2: le societa' no)
--    6) ... e il rifiuto porta il campo 'cliente_pa' (canale COLUMN, per il form)
--    7) ENC cliente PA e in split -> passa
--    8) ENC cliente PA che diventa SC -> E_CLIENTE_PA_NON_AMMESSO (cambio di natura)
--    9) ... ma con il flag riportato a N nella stessa scrittura -> passa
--   persone fisiche
--   10) PR cliente PA -> E_CLIENTE_PA_NON_AMMESSO
--   11) DI in split -> E_SPLIT_PAYMENT_NON_AMMESSO
--   12) ... col campo 'split_payment'
--   13) PR con i due flag a N scritti esplicitamente -> passa
--   senza natura (A-5)
--   14) un flag a S senza natura -> E_DATO_FISCALE_SENZA_TIPO_SOGGETTO, campo tipo_soggetto_dettaglio_id
--   15) senza natura e con i flag a N -> passa
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il test gira come l'applicazione (RLS attiva).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- La finestra differita la dichiara il file (vedi l'esenzione in testa).
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(15);

-- Il campo del rifiuto (canale COLUMN): e' cio' che accende il campo nel form.
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

-- ============================================================
-- Struttura
-- ============================================================
SELECT results_eq(
    $$SELECT codice_interno::text, cliente_pa_ammesso, split_payment_ammesso
        FROM config.tipi_soggetto_dettaglio
       WHERE codice_interno IN ('PR', 'DI', 'SP', 'SC', 'ENC')
       ORDER BY codice_interno$$,
    $$VALUES ('DI', false, false), ('ENC', true, true), ('PR', false, false),
             ('SC', false, true), ('SP', false, true)$$,
    '1. per natura: persone fisiche nessuno, societa'' solo split, enti tutti e due (A-2)');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_catalog.pg_constraint c
             WHERE c.conrelid = 'config.tipi_soggetto_dettaglio'::regclass
               AND c.conname  = 'chk_tipi_soggetto_dettaglio_regime_pa_natura'
               AND pg_get_constraintdef(c.oid) LIKE '%PF%cliente_pa_ammesso%split_payment_ammesso%'),
    '2. CHECK: una natura PF non ammette ne'' cliente PA ne'' split payment');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_catalog.pg_trigger t
             WHERE t.tgrelid = 'anagrafiche.soggetti'::regclass
               AND t.tgname  = 'trg_soggetti_a10_guard_regime_pa_ins_upd'
               AND pg_get_triggerdef(t.oid) LIKE '%UPDATE OF cliente_pa, split_payment, tipo_soggetto_dettaglio_id%'),
    '3. il guard copre i due flag e il cambio di natura');

-- ============================================================
-- Societa' ed enti. Per PRIMI: il builder esce con i vincoli IMMEDIATE, e
-- farebbe scattare i guard differiti sulle persone fisiche ancora incomplete.
-- ============================================================
CREATE TEMP TABLE _sc AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Regime PA pgTAP srl') AS id;   -- default: SC

CREATE TEMP TABLE _enc AS
SELECT dbops.fn_pgtap_crea_soggetto_pg(
           'Regime PA pgTAP ente',
           p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio
                                             WHERE codice_interno = 'ENC')::integer) AS id;
SET CONSTRAINTS ALL DEFERRED;

SELECT lives_ok(
    $$UPDATE anagrafiche.soggetti SET split_payment = 'S' WHERE id = (SELECT id FROM _sc)$$,
    '4. una societa'' di capitali in split payment -> passa (controllate dalla PA, quotate)');

SELECT throws_like(
    $$UPDATE anagrafiche.soggetti SET cliente_pa = 'S' WHERE id = (SELECT id FROM _sc)$$,
    '%non puo'' essere una Pubblica Amministrazione%',
    '5. una societa'' di capitali cliente PA -> E_CLIENTE_PA_NON_AMMESSO');

SELECT is(
    pg_temp.colonna_del_rifiuto($$UPDATE anagrafiche.soggetti SET cliente_pa = 'S'
                                  WHERE id = (SELECT id FROM _sc)$$),
    'cliente_pa',
    '6. il rifiuto porta il campo ''cliente_pa'' (canale COLUMN)');

SELECT lives_ok(
    $$UPDATE anagrafiche.soggetti SET cliente_pa = 'S', split_payment = 'S' WHERE id = (SELECT id FROM _enc)$$,
    '7. un ente cliente PA e in split payment -> passa');

SELECT throws_like(
    $$UPDATE anagrafiche.soggetti
         SET tipo_soggetto_dettaglio_id = (SELECT id FROM config.tipi_soggetto_dettaglio
                                            WHERE codice_interno = 'SC')
       WHERE id = (SELECT id FROM _enc)$$,
    '%non puo'' essere una Pubblica Amministrazione%',
    '8. l''ente cliente PA che diventa societa'' -> E_CLIENTE_PA_NON_AMMESSO (il flag non si porta dietro)');

SELECT lives_ok(
    $$UPDATE anagrafiche.soggetti
         SET tipo_soggetto_dettaglio_id = (SELECT id FROM config.tipi_soggetto_dettaglio
                                            WHERE codice_interno = 'SC'),
             cliente_pa = 'N'
       WHERE id = (SELECT id FROM _enc)$$,
    '9. ... con il flag riportato a N nella stessa scrittura -> passa (lo split resta: SC lo ammette)');

-- ============================================================
-- Persone fisiche
-- ============================================================
CREATE TEMP TABLE _pr AS
SELECT anagrafiche.fn_crea_soggetto_pf(
           p_cognome := 'Regime', p_nome := 'Privato', p_codice_fiscale := dbops.fn_pgtap_cf_libero(),
           p_email := 'pgtap.regime.pr@example.com', p_sesso := 'F',
           p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio
                                             WHERE codice_interno = 'PR')) AS id;

CREATE TEMP TABLE _di AS
SELECT anagrafiche.fn_crea_soggetto_pf(
           p_cognome := 'Regime', p_nome := 'Ditta', p_codice_fiscale := dbops.fn_pgtap_cf_libero(),
           p_email := 'pgtap.regime.di@example.com',
           p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio
                                             WHERE codice_interno = 'DI'),
           p_partita_iva := dbops.fn_pgtap_piva_libera()) AS id;

SELECT throws_like(
    $$UPDATE anagrafiche.soggetti SET cliente_pa = 'S' WHERE id = (SELECT id FROM _pr)$$,
    '%non puo'' essere una Pubblica Amministrazione%',
    '10. un privato cliente PA -> E_CLIENTE_PA_NON_AMMESSO (il caso della segnalazione)');

SELECT throws_like(
    $$UPDATE anagrafiche.soggetti SET split_payment = 'S' WHERE id = (SELECT id FROM _di)$$,
    '%non puo'' essere in split payment%',
    '11. una ditta individuale in split payment -> E_SPLIT_PAYMENT_NON_AMMESSO');

SELECT is(
    pg_temp.colonna_del_rifiuto($$UPDATE anagrafiche.soggetti SET split_payment = 'S'
                                  WHERE id = (SELECT id FROM _di)$$),
    'split_payment',
    '12. il rifiuto porta il campo ''split_payment'' (canale COLUMN)');

SELECT lives_ok(
    $$UPDATE anagrafiche.soggetti SET cliente_pa = 'N', split_payment = 'N' WHERE id = (SELECT id FROM _pr)$$,
    '13. un privato con i due flag a N scritti esplicitamente -> passa (non ammesso = resta N)');

-- ============================================================
-- Senza natura (A-5): si rifiuta, non si tace
-- ============================================================
CREATE TEMP TABLE _senza AS
WITH ins AS (
    INSERT INTO anagrafiche.soggetti (ragione_sociale, stato_id)
    VALUES ('Regime PA pgTAP senza natura', (SELECT id FROM config.stati WHERE codice_iso2 = 'IT'))
    RETURNING id
)
SELECT id FROM ins;

SELECT is(
    pg_temp.colonna_del_rifiuto($$UPDATE anagrafiche.soggetti SET split_payment = 'S'
                                  WHERE id = (SELECT id FROM _senza)$$),
    'tipo_soggetto_dettaglio_id',
    '14. un flag a S senza natura -> E_DATO_FISCALE_SENZA_TIPO_SOGGETTO, campo tipo_soggetto_dettaglio_id');

SELECT is(
    (SELECT cliente_pa || split_payment FROM anagrafiche.soggetti WHERE id = (SELECT id FROM _senza)),
    'NN',
    '15. senza natura e con i flag a N il soggetto nasce: il guard giudica solo un flag acceso');

SELECT * FROM finish();
ROLLBACK;
