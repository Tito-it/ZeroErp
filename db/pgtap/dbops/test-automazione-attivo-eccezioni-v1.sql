-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le ECCEZIONI dell'automazione ATTIVO — e la prima: porta e profili
--   si sganciano (config.profili_accesso_bindings.identita_digitale_id).
--   Brief: brief-db-blocco-login-per-credenziale, sezione 12.3.
--   ChangeSet: 20260925-46 (registro), -47 (ritiro), -48 (motore), -49 (seed),
--   -50 (ritiro una tantum).
--
-- ⭐ Perche': col P-2 la veste OPERATORE nasce SPENTA (20260925-42). Col require
--   generato fra binding e identita' un SUPER_ADMIN non si creava piu' («Padre
--   non attivo: figlio attivo non consentito» al COMMIT). Decisione Tid del
--   2026-09-25: la veste dice se la porta e' aperta, il binding cosa si puo'
--   fare dentro; i lettori chiedono gia' entrambe.
--
-- ⛔ I trigger si cercano per FUNZIONE e ARGOMENTI, non per nome: i nomi
--   generati sono hashati oltre i 63 caratteri.
-- ⚠️ In CI i trigger ATTIVO li genera la passata ci_apply, che gira PRIMA dei
--   pgTAP: i test 2-4 sono veri anche li' (il 4 in particolare dice che il
--   motore ha continuato a generare le coppie non eccettuate).
--
-- rev 2026-11-09 (brief-db-revisione-dbops, giro 14, M37): i test 1-4 guardano la
--   prima eccezione; il 9 guarda TUTTE le righe del registro.
--
-- Elenco test (plan 9):
--   Il registro e il framework
--    1) la riga di registro c'e', col suo motivo
--    2) nessun require su profili_accesso_bindings per identita_digitale_id
--    3) nessun block su identita_digitali per quella FK
--    4) ⭐ le ALTRE coppie di profili_accesso_bindings sono ancora legate
--       (profilo_accesso_id, unita_organizzativa_id): l'eccezione e' per FK,
--       non per tabella
--   Il comportamento
--    5) ⭐ un SUPER_ADMIN nasce dalla madre con la veste SPENTA e il binding
--       attivo, e la saga si chiude (vincoli IMMEDIATE)
--    6) ...e finche' la veste e' spenta NON e' super admin (la porta e' chiusa)
--    7) invito accettato (veste accesa): e' super admin
--    8) spegnere la veste di un SUPER_ADMIN (non l'ultimo) si puo', e il
--       binding resta: il reinvito lo riaccende uguale (D-3)
--   Il registro intero
--    9) ⭐ per OGNI riga di dbops.automazione_attivo_eccezioni nessun require
--       sulla figlia e nessun block sul padre per quella FK
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- I trigger ATTIVO, con gli argomenti decodificati (tgargs: bytea separato da NUL).
-- ⛔ Il nome della tabella si compone dal catalogo, NON con tgrelid::regclass::text:
--   quello dipende dal search_path, e con `config` nel path esce senza schema
--   (`profili_accesso_bindings`). Il confronto con 'config.…' falliva sempre: il 4
--   rosso con NULL, il 2 verde per coincidenza (contava zero comunque).
CREATE TEMP TABLE _trg AS
SELECT cn.nspname || '.' || c.relname AS rel,
       p.proname,
       string_to_array(rtrim(encode(t.tgargs, 'escape'), '\000'), '\000') AS a
  FROM pg_trigger t
  JOIN pg_class c      ON c.oid = t.tgrelid
  JOIN pg_namespace cn ON cn.oid = c.relnamespace
  JOIN pg_proc p      ON p.oid = t.tgfoid
  JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE NOT t.tgisinternal
   AND n.nspname = 'dbops'
   AND p.proname IN ('trgfn_child_requires_active_parent', 'trgfn_prevent_deactivate_if_children');

-- ============================================================
-- 1-4) Il registro e il framework
-- ============================================================
SELECT is(
    (SELECT count(*)::int FROM dbops.automazione_attivo_eccezioni
      WHERE schema_figlia = 'config' AND tabella_figlia = 'profili_accesso_bindings'
        AND colonna_fk = 'identita_digitale_id' AND btrim(motivo) <> ''),
    1,
    '1) registro: profili_accesso_bindings.identita_digitale_id e'' un''eccezione, col suo motivo');

SELECT is(
    (SELECT count(*)::int FROM _trg
      WHERE proname = 'trgfn_child_requires_active_parent'
        AND rel = 'config.profili_accesso_bindings' AND a[4] = 'identita_digitale_id'),
    0,
    '2) nessun require: un binding attivo puo'' stare sotto una veste spenta');

SELECT is(
    (SELECT count(*)::int FROM _trg
      WHERE proname = 'trgfn_prevent_deactivate_if_children'
        AND a[1] = 'config' AND a[2] = 'profili_accesso_bindings' AND a[3] = 'identita_digitale_id'),
    0,
    '3) nessun block: una veste si spegne anche con binding attivi');

SELECT is(
    (SELECT string_agg(a[4], ',' ORDER BY a[4]) FROM _trg
      WHERE proname = 'trgfn_child_requires_active_parent'
        AND rel = 'config.profili_accesso_bindings'),
    'profilo_accesso_id,unita_organizzativa_id',
    '4) le altre coppie di profili_accesso_bindings restano legate: l''eccezione e'' per FK, non per tabella');

-- 9) Il registro intero: un'eccezione che ha ancora un trigger ATTIVO e' un registro
--    che mente (fn_run_automations_attivo non doveva generarlo, fn_ritira_attivo_eccezioni
--    doveva toglierlo). Si scrive qui, prima della parte che costruisce, perche' _trg e'
--    la fotografia dei trigger presa in testa.
SELECT is(
    (SELECT COALESCE(array_agg(DISTINCT e.schema_figlia || '.' || e.tabella_figlia || '.' || e.colonna_fk
                               ORDER BY e.schema_figlia || '.' || e.tabella_figlia || '.' || e.colonna_fk),
                     ARRAY[]::text[])
       FROM dbops.automazione_attivo_eccezioni e
       JOIN _trg t
         ON (t.proname = 'trgfn_child_requires_active_parent'
             AND t.rel = e.schema_figlia || '.' || e.tabella_figlia AND t.a[4] = e.colonna_fk)
         OR (t.proname = 'trgfn_prevent_deactivate_if_children'
             AND t.a[1] = e.schema_figlia AND t.a[2] = e.tabella_figlia AND t.a[3] = e.colonna_fk)),
    ARRAY[]::text[],
    '9) nessuna eccezione del registro ha ancora un require o un block');

-- ============================================================
-- 5-8) Il comportamento
-- ============================================================
-- Un altro SUPER_ADMIN pronto, cosi' quello del test non e' mai l'ultimo.
CREATE TEMP TABLE _sa_altro AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('eccezione altro SA', true);

SET CONSTRAINTS ALL DEFERRED;
CREATE TEMP TABLE _sa AS
SELECT m.auth_user_id
  FROM anagrafiche.fn_crea_operatore_v2(
           p_cognome                      := 'Eccezione',
           p_nome                         := 'pgTAP',
           p_codice_fiscale               := dbops.fn_pgtap_cf_libero(),
           p_username                     := '_pgtap_ecc_sa_' || substring(md5(clock_timestamp()::text) from 1 for 8),
           p_email                        := '_pgtap_ecc_sa_' || substring(md5(clock_timestamp()::text) from 1 for 8) || '@example.com',
           p_password_hash                := 'pgtap-nessun-login',
           p_qualifica_id                 := (SELECT q.id FROM config.qualifiche q WHERE q.codice_interno = 'DIPENDENTE'),
           p_is_super_admin               := true,
           p_indirizzo_resid_dettaglio_id := dbops.fn_pgtap_crea_indirizzo_dettaglio('eccezione SA'),
           p_sesso := 'M') m;

-- I vincoli differiti (il require, se ci fosse) scattano QUI.
SELECT lives_ok(
    'SET CONSTRAINTS ALL IMMEDIATE',
    '5) SUPER_ADMIN dalla madre: veste spenta + binding attivo, la saga si chiude');

SELECT is(
    script.fn_is_super_admin((SELECT auth_user_id FROM _sa)),
    false,
    '6) veste spenta: non e'' super admin (la porta e'' chiusa, il binding non basta)');

-- L'invito accettato.
UPDATE anagrafiche.identita_digitali
   SET attivo = true
 WHERE auth_user_id = (SELECT auth_user_id FROM _sa)
   AND ruolo_applicativo = 'OPERATORE';

SELECT is(
    script.fn_is_super_admin((SELECT auth_user_id FROM _sa)),
    true,
    '7) veste accesa: e'' super admin');

UPDATE anagrafiche.identita_digitali
   SET attivo = false
 WHERE auth_user_id = (SELECT auth_user_id FROM _sa)
   AND ruolo_applicativo = 'OPERATORE';

SELECT is(
    (SELECT string_agg(pab.attivo::text, ',')
       FROM config.profili_accesso_bindings pab
       JOIN anagrafiche.identita_digitali i ON i.id = pab.identita_digitale_id
      WHERE i.auth_user_id = (SELECT auth_user_id FROM _sa)
        AND NOT i.attivo),
    'true',
    '8) veste di un SUPER_ADMIN spenta (non l''ultimo): si puo'', e il binding resta attivo');

SELECT * FROM finish();
ROLLBACK;
