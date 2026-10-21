-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: una veste e' utilizzabile se e' accesa E nelle sue date; per
--       l'operatore umano anche il rapporto. Una regola, a DB.
-- ChangeSet: 20261007-01 (script.fn_veste_utilizzabile), -02 … -15 (le sedi
--            che la ricopiavano); codici_errore.csv (ritiro dei due codici delle
--            date, obsoleto_dal)
-- Brief: brief-db-veste-utilizzabile (L-6 del piano accessi, A-7)
--
-- Elenco test (plan 28):
--   Il building block
--    1) esiste script.fn_veste_utilizzabile(bigint) -> boolean
--    2) ...ed e' STABLE
--   Operatore umano (casi costruiti sulla stessa veste, ripristinata fra l'uno
--   e l'altro)
--    3) accesa e senza fine: utilizzabile
--    4) spenta: no
--    5) valido_dal domani: no
--    6) valido_al ieri: no (rapporto valido: la veste scade da sola)
--    7) valido_al OGGI: si' (l'estremo e' compreso)
--    8) D-2: veste valida e rapporto chiuso ieri: no
--    9) D-2: rapporto con valido_dal domani: no
--   10) D-2: rapporto spento (costruito: veste spenta, rapporto spento, veste
--       riaccesa — il guard «figli prima» lo consente): no
--   Le altre vesti
--   11) identita' TECNICA di un processo, senza risorsa umana: utilizzabile
--   12) ...e scaduta: no
--   13) veste CLIENTE_PORTALE sulla stessa credenziale: utilizzabile, senza
--       rapporto
--   14) id assente: false
--   15) NULL: false
--   Le sedi rispondono come il building block (la divergenza e' il difetto)
--   16) fn_has_identita_attiva(OPERATORE) col rapporto chiuso: false
--   17) fn_sync_auth_user_is_active col rapporto chiuso: la credenziale resta
--       accesa per la veste cliente (OR sulle vesti)
--   18) ...spenta anche la cliente: la credenziale si spegne
--   19) fn_get_user_profile col rapporto chiuso: E_UTENTE_DISABILITATO
--   20) fn_get_user_profile con la veste non ancora valida: E_UTENTE_DISABILITATO
--   21a/b) il perimetro del cliente (fn_get_identita_sr_perimetro): il suo
--       soggetto sulla veste valida, NULL quando scade (rev 2026-10-21:
--       fn_scope_cliente_ownership ritirata da 20261021-40)
--   22a/b) fn_scope_identita_processo: vera sull'identita' tecnica valida,
--       falsa quando scade
--   23) fn_is_super_admin_account: un SUPER_ADMIN col rapporto chiuso non lo e'
--       piu'
--   24) fn_sync_auth_user_expired: spegne la credenziale accesa senza vesti
--       utilizzabili (il caso che il tempo produce senza scrivere niente)
--   I codici delle date
--   25) E_UTENTE_NON_ATTIVO ed E_UTENTE_SCADUTO ritirati con obsoleto_dal (la
--       riga resta: dbops.error_log ci punta) e non sollevati da nessuna funzione
--   Il presidio
--   26) le sedi del brief chiamano tutte il building block (le due check
--       dell'anti-lockout attraverso fn_identita_super_admin_senza_scadenza, -16)
--
-- ⚠️ D-3 (soggetto attivo) NON ha un caso: un soggetto con un soggetto_ruolo
--   non si spegne (guard generico dell'automazione ATTIVO, figlia senza
--   colonna attivo), e una veste ha sempre un soggetto_ruolo. La condizione
--   resta nel building block per decisione di Tid (2026-10-07), dichiarata
--   come non costruibile, non provata.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(28);

-- ============================================================
-- Fixture
-- ============================================================
-- Il codice dell'errore viaggia nel canale CONSTRAINT_NAME dell'eccezione
-- P0001 (fn_log_and_raise_error).
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

-- Operatore umano dal percorso di produzione: persona, risorsa umana,
-- credenziale, veste OPERATORE accesa.
CREATE TEMP TABLE _op AS
SELECT o.* FROM dbops.fn_pgtap_crea_operatore_umano('veste utilizzabile', false) o;

-- Identita' tecnica di un processo (OPERATORE, tecnica = true, nessuna
-- risorsa umana per costruzione).
CREATE TEMP TABLE _tec AS
SELECT t.* FROM dbops.fn_pgtap_crea_emittente_operatore() t;

-- Veste CLIENTE_PORTALE sulla STESSA credenziale dell'operatore.
CREATE TEMP TABLE _cl AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('veste utilizzabile') c;

-- La veste dal BB anagrafiche.fn_crea_veste_portale (rev 2026-10-18,
-- brief-db-processi-accensione-per-ambiente 2b-1 lotto 6).
DO $veste$
BEGIN
    PERFORM 1 FROM (
        SELECT anagrafiche.fn_crea_veste_portale(_op.auth_user_id, _cl.soggetto_ruolo_id, 'CLIENTE_PORTALE'::config.ruolo_applicativo, true) FROM _cl, _op
    ) AS v;
END
$veste$;

ALTER TABLE _cl ADD COLUMN identita_id bigint;
UPDATE _cl SET identita_id = idg.id
  FROM anagrafiche.identita_digitali idg, _op
 WHERE idg.auth_user_id      = _op.auth_user_id
   AND idg.ruolo_applicativo = 'CLIENTE_PORTALE'::config.ruolo_applicativo;

-- Le finestre partono indietro di dieci giorni, cosi' «ieri» e «oggi» sono
-- fini ammesse da chk_identita_digitali_date (valido_al >= valido_dal).
UPDATE anagrafiche.identita_digitali SET valido_dal = script.fn_data_operativa() - 10
 WHERE id IN ((SELECT identita_id FROM _op), (SELECT identita_id FROM _tec),
              (SELECT identita_id FROM _cl));
UPDATE anagrafiche.risorse_umane SET valido_dal = script.fn_data_operativa() - 10
 WHERE id = (SELECT risorsa_umana_id FROM _op);

CREATE OR REPLACE FUNCTION pg_temp.vu(p_id bigint) RETURNS boolean
LANGUAGE sql AS $$ SELECT script.fn_veste_utilizzabile(p_id) $$;

-- Ripristina l'operatore: veste e rapporto accesi, senza fine.
CREATE OR REPLACE FUNCTION pg_temp.ripristina_op() RETURNS void
LANGUAGE sql AS $$
    UPDATE anagrafiche.identita_digitali
       SET attivo = true, valido_dal = script.fn_data_operativa() - 10, valido_al = NULL
     WHERE id = (SELECT identita_id FROM _op);
    UPDATE anagrafiche.risorse_umane
       SET attivo = true, valido_dal = script.fn_data_operativa() - 10, valido_al = NULL
     WHERE id = (SELECT risorsa_umana_id FROM _op);
$$;

-- ============================================================
-- 1-2. Il building block
-- ============================================================
SELECT function_returns('script', 'fn_veste_utilizzabile', ARRAY['bigint'], 'boolean',
    '1) script.fn_veste_utilizzabile(bigint) -> boolean');

SELECT volatility_is('script', 'fn_veste_utilizzabile', ARRAY['bigint'], 'stable',
    '2) ...ed e'' STABLE');

-- ============================================================
-- 3-10. Operatore umano
-- ============================================================
SELECT is(pg_temp.vu((SELECT identita_id FROM _op)), true,
    '3) operatore acceso e senza fine: utilizzabile');

UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = (SELECT identita_id FROM _op);
SELECT is(pg_temp.vu((SELECT identita_id FROM _op)), false, '4) veste spenta: no');
SELECT pg_temp.ripristina_op();

UPDATE anagrafiche.identita_digitali SET valido_dal = script.fn_data_operativa() + 1 WHERE id = (SELECT identita_id FROM _op);
SELECT is(pg_temp.vu((SELECT identita_id FROM _op)), false, '5) veste con valido_dal domani: no');
SELECT pg_temp.ripristina_op();

UPDATE anagrafiche.identita_digitali SET valido_al = script.fn_data_operativa() - 1 WHERE id = (SELECT identita_id FROM _op);
SELECT is(pg_temp.vu((SELECT identita_id FROM _op)), false,
    '6) veste con valido_al ieri e rapporto valido: no');
SELECT pg_temp.ripristina_op();

UPDATE anagrafiche.identita_digitali SET valido_al = script.fn_data_operativa() WHERE id = (SELECT identita_id FROM _op);
SELECT is(pg_temp.vu((SELECT identita_id FROM _op)), true,
    '7) veste con valido_al OGGI: si'' (estremo compreso)');
SELECT pg_temp.ripristina_op();

UPDATE anagrafiche.risorse_umane SET valido_al = script.fn_data_operativa() - 1 WHERE id = (SELECT risorsa_umana_id FROM _op);
SELECT is(pg_temp.vu((SELECT identita_id FROM _op)), false,
    '8) D-2: veste valida e rapporto chiuso ieri: no');
SELECT pg_temp.ripristina_op();

UPDATE anagrafiche.risorse_umane SET valido_dal = script.fn_data_operativa() + 1 WHERE id = (SELECT risorsa_umana_id FROM _op);
SELECT is(pg_temp.vu((SELECT identita_id FROM _op)), false,
    '9) D-2: rapporto con valido_dal domani: no');
SELECT pg_temp.ripristina_op();

UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = (SELECT identita_id FROM _op);
UPDATE anagrafiche.risorse_umane     SET attivo = false WHERE id = (SELECT risorsa_umana_id FROM _op);
UPDATE anagrafiche.identita_digitali SET attivo = true  WHERE id = (SELECT identita_id FROM _op);
SELECT is(pg_temp.vu((SELECT identita_id FROM _op)), false,
    '10) D-2: veste accesa e rapporto spento: no');
SELECT pg_temp.ripristina_op();

-- ============================================================
-- 11-15. Le altre vesti
-- ============================================================
SELECT is(pg_temp.vu((SELECT identita_id FROM _tec)), true,
    '11) identita'' tecnica senza risorsa umana: utilizzabile');

UPDATE anagrafiche.identita_digitali SET valido_al = script.fn_data_operativa() - 1 WHERE id = (SELECT identita_id FROM _tec);
SELECT is(pg_temp.vu((SELECT identita_id FROM _tec)), false,
    '12) identita'' tecnica scaduta: no');
UPDATE anagrafiche.identita_digitali SET valido_al = NULL WHERE id = (SELECT identita_id FROM _tec);

SELECT is(pg_temp.vu((SELECT identita_id FROM _cl)), true,
    '13) veste CLIENTE_PORTALE: utilizzabile senza rapporto');

SELECT is(pg_temp.vu((SELECT max(id) + 1000000 FROM anagrafiche.identita_digitali)), false,
    '14) id assente: false');

SELECT is(pg_temp.vu(NULL), false, '15) NULL: false');

-- ============================================================
-- 16-24. Le sedi rispondono come il building block
-- ============================================================
UPDATE anagrafiche.risorse_umane SET valido_al = script.fn_data_operativa() - 1 WHERE id = (SELECT risorsa_umana_id FROM _op);

SELECT is(script.fn_has_identita_attiva((SELECT auth_user_id FROM _op),
                                        'OPERATORE'::config.ruolo_applicativo),
    false,
    '16) fn_has_identita_attiva(OPERATORE) col rapporto chiuso: false');

-- Il trigger sul rapporto ha gia' chiamato il sync; lo si richiama per
-- leggere lo stato senza dipendere dall'ordine dei trigger.
SELECT anagrafiche.fn_sync_auth_user_is_active((SELECT auth_user_id FROM _op));
SELECT is((SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _op)),
    true,
    '17) sync col rapporto chiuso: credenziale accesa per la veste cliente (OR)');

UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = (SELECT identita_id FROM _cl);
SELECT anagrafiche.fn_sync_auth_user_is_active((SELECT auth_user_id FROM _op));
SELECT is((SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _op)),
    false,
    '18) ...spenta anche la cliente: la credenziale si spegne');
UPDATE anagrafiche.identita_digitali SET attivo = true WHERE id = (SELECT identita_id FROM _cl);

SELECT is(
    pg_temp.codice_errore(format('SELECT script.fn_get_user_profile(%s)',
                                 (SELECT auth_user_id FROM _op))),
    'E_UTENTE_DISABILITATO',
    '19) profilo col rapporto chiuso: E_UTENTE_DISABILITATO');
SELECT pg_temp.ripristina_op();

UPDATE anagrafiche.identita_digitali SET valido_dal = script.fn_data_operativa() + 1 WHERE id = (SELECT identita_id FROM _op);
SELECT is(
    pg_temp.codice_errore(format('SELECT script.fn_get_user_profile(%s)',
                                 (SELECT auth_user_id FROM _op))),
    'E_UTENTE_DISABILITATO',
    '20) profilo con la veste non ancora valida: E_UTENTE_DISABILITATO');
SELECT pg_temp.ripristina_op();

SELECT is(script.fn_get_identita_sr_perimetro((SELECT identita_id FROM _cl),
                                              ARRAY['CLIENTE_PORTALE', 'SHOP_CUSTOMER']::config.ruolo_applicativo[]),
    (SELECT soggetto_ruolo_id FROM _cl),
    '21a) il perimetro del cliente: il suo soggetto, sulla veste valida');
UPDATE anagrafiche.identita_digitali SET valido_al = script.fn_data_operativa() - 1 WHERE id = (SELECT identita_id FROM _cl);
SELECT is(script.fn_get_identita_sr_perimetro((SELECT identita_id FROM _cl),
                                              ARRAY['CLIENTE_PORTALE', 'SHOP_CUSTOMER']::config.ruolo_applicativo[]),
    NULL::bigint,
    '21b) ...NULL, cioe'' nessuna riga, quando la veste scade');
UPDATE anagrafiche.identita_digitali SET valido_al = NULL WHERE id = (SELECT identita_id FROM _cl);

SELECT is(script.fn_scope_identita_processo((SELECT auth_user_id FROM _tec), 'chiusura_scadenze_daily'),
    true, '22a) fn_scope_identita_processo: vera sull''identita'' tecnica valida');
UPDATE anagrafiche.identita_digitali SET valido_al = script.fn_data_operativa() - 1 WHERE id = (SELECT identita_id FROM _tec);
SELECT is(script.fn_scope_identita_processo((SELECT auth_user_id FROM _tec), 'chiusura_scadenze_daily'),
    false, '22b) ...falsa quando scade');
UPDATE anagrafiche.identita_digitali SET valido_al = NULL WHERE id = (SELECT identita_id FROM _tec);

-- ⚠️ Rev 2026-10-07 (-20, decisione di Tid): chiudere il rapporto di un
--   SUPER_ADMIN si ferma se non resta nessun SUPER_ADMIN senza scadenza. Su un
--   database senza altri amministratori (la CI) il caso morirebbe sul guard:
--   un secondo SUPER_ADMIN senza scadenza tiene la garanzia, e il caso prova
--   solo cio' che dice.
CREATE TEMP TABLE _sa_garante AS
SELECT o.* FROM dbops.fn_pgtap_crea_operatore_umano('veste utilizzabile SA garante', true) o;
CREATE TEMP TABLE _sa AS
SELECT o.* FROM dbops.fn_pgtap_crea_operatore_umano('veste utilizzabile SA', true) o;
UPDATE anagrafiche.risorse_umane SET valido_dal = script.fn_data_operativa() - 10, valido_al = script.fn_data_operativa() - 1
 WHERE id = (SELECT risorsa_umana_id FROM _sa);
UPDATE anagrafiche.identita_digitali SET valido_dal = script.fn_data_operativa() - 10
 WHERE id = (SELECT identita_id FROM _sa);
SELECT is(script.fn_is_super_admin_account((SELECT auth_user_id FROM _sa)), false,
    '23) fn_is_super_admin_account: col rapporto chiuso non e'' piu'' SUPER_ADMIN');

-- 24. Il tempo passa senza che nessuno scriva: la credenziale e' rimasta
-- accesa, ma non ha piu' vesti utilizzabili. Lo stato si simula riaccendendo
-- is_active a mano dopo aver chiuso tutto.
UPDATE anagrafiche.risorse_umane SET valido_al = script.fn_data_operativa() - 1 WHERE id = (SELECT risorsa_umana_id FROM _op);
UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = (SELECT identita_id FROM _cl);
UPDATE django.auth_user SET is_active = true WHERE id = (SELECT auth_user_id FROM _op);
SELECT anagrafiche.fn_sync_auth_user_expired();
SELECT is((SELECT is_active FROM django.auth_user WHERE id = (SELECT auth_user_id FROM _op)),
    false,
    '24) fn_sync_auth_user_expired spegne la credenziale senza vesti utilizzabili (rapporto scaduto)');

-- ============================================================
-- 25. I codici delle date
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM config.codici_errore
      WHERE codice IN ('E_UTENTE_NON_ATTIVO', 'E_UTENTE_SCADUTO')
        AND obsoleto_dal IS NOT NULL AND obsoleto_dal <= script.fn_data_operativa())
  + (SELECT count(*)::int
       FROM pg_catalog.pg_proc p
       JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
        AND (p.prosrc LIKE '%''E_UTENTE_NON_ATTIVO''%'
             OR p.prosrc LIKE '%''E_UTENTE_SCADUTO''%')),
    2,
    '25) E_UTENTE_NON_ATTIVO ed E_UTENTE_SCADUTO ritirati (obsoleto_dal) e non piu'' sollevati da nessuna funzione');

-- ============================================================
-- 26. Il presidio: le sedi del brief leggono il building block
-- ============================================================
SELECT set_eq(
    $$SELECT n.nspname || '.' || p.proname
        FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
       -- ⚠️ Una BEGIN ATOMIC ha prosrc VUOTO: il corpo sta compilato in
       --   prosqlbody, e si legge con pg_get_function_sqlbody.
       -- ⛔ Il deparse di pg_get_function_sqlbody OMETTE lo schema quando lo
       --   schema e' nel search_path: come app (script nel search_path) esce
       --   «fn_veste_utilizzabile(», da owner sullo scratch «script.fn_…(».
       --   Si cerca quindi il nome senza schema (2026-10-07: rosso solo come app).
       WHERE COALESCE(pg_get_function_sqlbody(p.oid), p.prosrc) LIKE '%fn_veste_utilizzabile(%'
         AND p.proname <> 'fn_veste_utilizzabile'
         AND n.nspname NOT LIKE 'pg\_temp%'$$,
    -- Rev 2026-10-07 (-16, -17, -18): le due check dell'anti-lockout la leggono
    -- attraverso script.fn_identita_super_admin_senza_scadenza, che e' qui al
    -- loro posto (il suo test: anagrafiche/test-super-admin-senza-scadenza-v1).
    $$VALUES ('script.fn_has_identita_attiva'), ('script.fn_is_super_admin_account'),
             ('script.fn_identita_super_admin_senza_scadenza'),
             ('script.fn_get_profili_accesso_applicabili'), ('script.fn_get_setup_status'),
             ('anagrafiche.fn_sync_auth_user_is_active'),
             ('anagrafiche.fn_sync_auth_user_expired'), ('script.fn_get_user_profile'),
             -- Rev 2026-10-21 (20261021-34): fn_scope_cliente_ownership la legge
             --   attraverso script.fn_get_identita_sr_perimetro.
             ('script.fn_scope_fornitore_ownership'),
             -- Rev 2026-10-21 (20261021-29, -31): la regola BA_OWNERSHIP la legge
             --   attraverso script.fn_get_identita_sr_perimetro, qui al posto di
             --   fn_scope_ba_ownership e _via_fattura.
             ('script.fn_get_identita_sr_perimetro'),
             ('script.fn_scope_identita_processo')$$,
    '26) le sedi del brief leggono script.fn_veste_utilizzabile (le check dell''anti-lockout attraverso fn_identita_super_admin_senza_scadenza)');

SELECT * FROM finish();
ROLLBACK;
