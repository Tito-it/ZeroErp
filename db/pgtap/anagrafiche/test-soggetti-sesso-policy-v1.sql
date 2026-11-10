-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-differiti: escluso — i soggetti persona fisica costruiti qui restano
--   SENZA indirizzi e contatti completi: il soggetto del test e' il guard
--   BEFORE ROW del sesso (e il CHECK di riga), che scattano all'INSERT/UPDATE,
--   non la saga di completezza, che ha i suoi test. Con IMMEDIATE i guard
--   differiti di soggetti rifiuterebbero ogni fixture prima dell'asserzione.
--   La finestra la apre il file subito dopo il contesto (DEFERRED).
-- pgTAP test per Zero ERP
--
-- Il sesso di un soggetto: vocabolario, natura, nessun default.
--   Brief: brief-db-sesso-senza-default (changeSet 20261009-19 ... -31)
--
-- Elenco test (plan 20):
--   struttura (il contratto, dal catalogo)
--    1) CHECK chk_soggetti_sesso: NULL, M, F, X
--    2) anagrafiche.soggetti.sesso senza default
--    3) sesso_policy per natura: PR REQUIRED, DI OPTIONAL, SP/SC/ENC NONE
--    4) CHECK chk_tipi_soggetto_dettaglio_sesso_policy_natura esiste
--    5) config.dati_societari_policy_enum ritirato (sostituito da presenza_policy_enum)
--   societa' (prima delle persone: il builder chiude la finestra differita)
--    6) builder PG: la societa' nasce con sesso NULL (non piu' 'S'; il default
--       lo misura il 2, perche' il builder scrive NULL esplicito)
--    7) un sesso su una societa' -> E_SESSO_NON_AMMESSO
--   privato (PR)
--    8) fn_crea_soggetto_pf senza sesso -> E_SESSO_OBBLIGATORIO
--    9) ... e il rifiuto porta il campo 'sesso' (canale COLUMN, per il form)
--   10) PR con X («non si puo' stabilire») -> nasce
--   11) INSERT diretto di un PR senza sesso -> E_SESSO_OBBLIGATORIO
--   ditta individuale (DI)
--   12) fn_crea_soggetto_pf con DI, P.IVA e senza sesso -> nasce
--   13) ... e nasce DI, con la P.IVA e sesso NULL (non piu' «privato»)
--   14) 'S' su una DI -> CHECK chk_soggetti_sesso (il guard la lascia passare)
--   15) la DI diventa PR senza sesso -> E_SESSO_OBBLIGATORIO
--   porte e chiamanti
--   16) fn_crea_soggetto_pf senza natura -> E_ADMIN_VALIDAZIONE
--   17) fn_crea_soggetto_pf con una societa' -> E_SOGGETTO_CREAZIONE_NATURA_ERRATA
--   18) fn_crea_soggetto_pg con un privato   -> E_SOGGETTO_CREAZIONE_NATURA_ERRATA
--   19) fn_crea_operatore_v2, soggetto nuovo, senza sesso -> E_SESSO_OBBLIGATORIO
--   20) un soggetto senza natura e senza sesso -> passa (il guard tace)
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: il test gira come l'applicazione (RLS attiva).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- Il SUPER_ADMIN del test 15 (S-BE-3): costruito qui, con le fixture.
CREATE TEMP TABLE _sa AS SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP-SA-sesso', true);

-- La finestra differita la dichiara il file (vedi l'esenzione in testa).
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(20);

-- ============================================================
-- Struttura
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM pg_catalog.pg_constraint c
             WHERE c.conrelid = 'anagrafiche.soggetti'::regclass
               AND c.conname  = 'chk_soggetti_sesso'
               AND pg_get_constraintdef(c.oid) LIKE '%''M''%''F''%''X''%'),
    '1. CHECK chk_soggetti_sesso: il vocabolario e'' M, F, X (o NULL)');

SELECT col_hasnt_default('anagrafiche', 'soggetti', 'sesso',
    '2. soggetti.sesso non ha default: lo sceglie chi lo vede');

SELECT results_eq(
    $$SELECT codice_interno::text, sesso_policy::text
        FROM config.tipi_soggetto_dettaglio
       WHERE codice_interno IN ('PR', 'DI', 'SP', 'SC', 'ENC')
       ORDER BY codice_interno$$,
    $$VALUES ('DI', 'OPTIONAL'), ('ENC', 'NONE'), ('PR', 'REQUIRED'), ('SC', 'NONE'), ('SP', 'NONE')$$,
    '3. sesso_policy: privato obbligatorio, ditta individuale facoltativo, societa'' ed enti vietato');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_catalog.pg_constraint c
             WHERE c.conrelid = 'config.tipi_soggetto_dettaglio'::regclass
               AND c.conname  = 'chk_tipi_soggetto_dettaglio_sesso_policy_natura'),
    '4. CHECK: solo una natura PF puo'' avere una sesso_policy diversa da NONE');

SELECT ok(
    NOT EXISTS (SELECT 1 FROM pg_catalog.pg_type t
                  JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
                 WHERE n.nspname = 'config' AND t.typname = 'dati_societari_policy_enum'),
    '5. config.dati_societari_policy_enum ritirato: la policy usa config.presenza_policy_enum');

-- ============================================================
-- Societa'. Per PRIMA: il builder esce con i vincoli IMMEDIATE, e farebbe
-- scattare i guard differiti sulle persone fisiche ancora incomplete.
-- ============================================================
CREATE TEMP TABLE _pg AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Sesso policy pgTAP srl') AS id;
SET CONSTRAINTS ALL DEFERRED;

SELECT is(
    (SELECT s.sesso FROM anagrafiche.soggetti s JOIN _pg ON _pg.id = s.id),
    NULL,
    '6. il builder di una societa'' scrive sesso NULL (non piu'' ''S'')');

SELECT throws_like(
    $$UPDATE anagrafiche.soggetti SET sesso = 'M' WHERE id = (SELECT id FROM _pg)$$,
    '%sesso non si indica%',
    '7. un sesso su una societa'' -> E_SESSO_NON_AMMESSO');

-- ============================================================
-- Privato (PR)
-- ============================================================
SELECT throws_like(
    format($$SELECT anagrafiche.fn_crea_soggetto_pf(
               p_cognome := 'Sesso', p_nome := 'Mancante', p_codice_fiscale := %L,
               p_email := 'pgtap.sesso.mancante@example.com',
               p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio
                                                 WHERE codice_interno = 'PR'))$$,
           dbops.fn_pgtap_cf_libero()),
    '%sesso e'' obbligatorio%',
    '8. privato senza sesso -> E_SESSO_OBBLIGATORIO (niente piu'' ''M'' di comodo)');

-- Il campo nel canale COLUMN: e' cio' che accende il campo nel form.
CREATE OR REPLACE FUNCTION pg_temp.colonna_del_rifiuto() RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_col text;
BEGIN
    PERFORM anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'Sesso', p_nome := 'Colonna', p_codice_fiscale := dbops.fn_pgtap_cf_libero(),
        p_email := 'pgtap.sesso.colonna@example.com',
        p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio
                                          WHERE codice_interno = 'PR'));
    RETURN '(nessun rifiuto)';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_col = COLUMN_NAME;
    RETURN v_col;
END $f$;

SELECT is(pg_temp.colonna_del_rifiuto(), 'sesso',
    '9. il rifiuto porta il campo ''sesso'' (canale COLUMN)');

CREATE TEMP TABLE _pr_x AS
SELECT anagrafiche.fn_crea_soggetto_pf(
           p_cognome := 'Sesso', p_nome := 'Indeterminabile', p_codice_fiscale := dbops.fn_pgtap_cf_libero(),
           p_email := 'pgtap.sesso.x@example.com', p_sesso := 'X',
           p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio
                                             WHERE codice_interno = 'PR')) AS id;

SELECT is(
    (SELECT s.sesso FROM anagrafiche.soggetti s JOIN _pr_x ON _pr_x.id = s.id),
    'X',
    '10. privato con X («non si puo'' stabilire») -> nasce, con X');

SELECT throws_like(
    format($$INSERT INTO anagrafiche.soggetti (cognome, nome, codice_fiscale, stato_id, tipo_soggetto_dettaglio_id)
             VALUES ('Sesso', 'Diretto', %L, (SELECT id FROM config.stati WHERE codice_iso2 = 'IT'),
                     (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR'))$$,
           dbops.fn_pgtap_cf_libero()),
    '%sesso e'' obbligatorio%',
    '11. INSERT diretto di un privato senza sesso -> E_SESSO_OBBLIGATORIO (la regola e'' nella tabella)');

-- ============================================================
-- Ditta individuale (DI)
-- ============================================================
CREATE TEMP TABLE _di AS
SELECT anagrafiche.fn_crea_soggetto_pf(
           p_cognome := 'Sesso', p_nome := 'Ditta', p_codice_fiscale := dbops.fn_pgtap_cf_libero(),
           p_email := 'pgtap.sesso.di@example.com',
           p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio
                                             WHERE codice_interno = 'DI'),
           p_partita_iva := dbops.fn_pgtap_piva_libera()) AS id;

SELECT is((SELECT count(*)::int FROM _di WHERE id IS NOT NULL), 1,
    '12. ditta individuale senza sesso, con P.IVA -> nasce (sesso facoltativo)');

SELECT ok(
    EXISTS (SELECT 1 FROM anagrafiche.soggetti s
              JOIN _di ON _di.id = s.id
              JOIN config.tipi_soggetto_dettaglio t ON t.id = s.tipo_soggetto_dettaglio_id
             WHERE t.codice_interno = 'DI' AND s.partita_iva IS NOT NULL AND s.sesso IS NULL),
    '13. nasce DITTA INDIVIDUALE con la P.IVA e sesso NULL (prima nasceva privato, senza P.IVA)');

SELECT throws_ok(
    $$UPDATE anagrafiche.soggetti SET sesso = 'S' WHERE id = (SELECT id FROM _di)$$,
    '23514', NULL,
    '14. ''S'' su una ditta individuale -> CHECK chk_soggetti_sesso (fuori vocabolario)');

-- ⚠️ Dal 2026-11-09 (brief-db-revisione-dbops, S-BE-3, N4 deciso da Tid: strada a) una P.IVA gia'
--   scritta la toglie solo il SUPER_ADMIN (anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile):
--   il passaggio da ditta individuale a privato lo fa lui, e il test prova il sesso; poi si torna
--   all'operatore di prima.
CREATE TEMP TABLE _op_prima AS SELECT current_setting('app.current_user_id', true)::integer AS auth_user_id;
SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _sa));

SELECT throws_like(
    $$UPDATE anagrafiche.soggetti
         SET tipo_soggetto_dettaglio_id = (SELECT id FROM config.tipi_soggetto_dettaglio
                                            WHERE codice_interno = 'PR'),
             partita_iva = NULL
       WHERE id = (SELECT id FROM _di)$$,
    '%sesso e'' obbligatorio%',
    '15. la ditta individuale diventa privato senza sesso -> E_SESSO_OBBLIGATORIO');

SELECT script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _op_prima));

-- ============================================================
-- Porte e chiamanti
-- ============================================================
SELECT throws_like(
    format($$SELECT anagrafiche.fn_crea_soggetto_pf(
               p_cognome := 'Sesso', p_nome := 'SenzaNatura', p_codice_fiscale := %L,
               p_email := 'pgtap.sesso.natura@example.com', p_sesso := 'F')$$,
           dbops.fn_pgtap_cf_libero()),
    '%Tipo soggetto obbligatorio%',
    '16. fn_crea_soggetto_pf senza natura -> E_ADMIN_VALIDAZIONE (non piu'' PR per default)');

SELECT throws_like(
    format($$SELECT anagrafiche.fn_crea_soggetto_pf(
               p_cognome := 'Sesso', p_nome := 'Societa', p_codice_fiscale := %L,
               p_email := 'pgtap.sesso.sc@example.com', p_sesso := 'F',
               p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio
                                                 WHERE codice_interno = 'SC'))$$,
           dbops.fn_pgtap_cf_libero()),
    '%non si crea da questo percorso%',
    '17. fn_crea_soggetto_pf con una societa'' -> E_SOGGETTO_CREAZIONE_NATURA_ERRATA');

SELECT throws_like(
    $$SELECT anagrafiche.fn_crea_soggetto_pg(
          p_ragione_sociale := 'Sesso privato da pg',
          p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio
                                            WHERE codice_interno = 'PR'),
          p_email := 'pgtap.sesso.pg@example.com')$$,
    '%non si crea da questo percorso%',
    '18. fn_crea_soggetto_pg con un privato -> E_SOGGETTO_CREAZIONE_NATURA_ERRATA (la DI ha una porta sola)');

SELECT throws_like(
    format($$SELECT * FROM anagrafiche.fn_crea_operatore_v2(
               p_cognome := 'Sesso', p_nome := 'Operatore', p_codice_fiscale := %L,
               p_username := %L, p_email := %L, p_password_hash := 'pgtap-nessun-login',
               p_qualifica_id := (SELECT id FROM config.qualifiche WHERE codice_interno = 'DIPENDENTE'))$$,
           dbops.fn_pgtap_cf_libero(),
           'pgtap_sesso_op_' || floor(random() * 1000000)::text,
           'pgtap.sesso.op.' || floor(random() * 1000000)::text || '@example.com'),
    '%sesso e'' obbligatorio%',
    '19. operatore con soggetto nuovo senza sesso -> E_SESSO_OBBLIGATORIO (non piu'' ''M'' dalla firma)');

SELECT lives_ok(
    $$INSERT INTO anagrafiche.soggetti (ragione_sociale, stato_id)
      VALUES ('Sesso pgTAP senza natura', (SELECT id FROM config.stati WHERE codice_iso2 = 'IT'))$$,
    '20. senza natura il guard tace (limite dichiarato, come il guard su CF e P.IVA)');

SELECT * FROM finish();
ROLLBACK;
