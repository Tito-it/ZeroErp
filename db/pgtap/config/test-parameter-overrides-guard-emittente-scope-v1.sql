-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il perimetro emittente sugli override dei parametri:
--   config.trgfn_parameter_overrides_guard_emittente_scope  (20261124-13)
--   trg_parameter_overrides_a10_guard_emittente_scope_ins_upd_dlt
--   Brief: brief-db-emittente-del-super-admin §3.1 (R-DB-1, forma (A)).
--
-- ⭐ Il caso si COSTRUISCE: due aziende X e Y, ciascuna col suo operatore
--   (dbops.fn_pgtap_crea_emittente_operatore), un super admin umano
--   (dbops.fn_pgtap_crea_operatore_umano), due parametri col codice del test.
--   Le righe di partenza le scrive il super admin in «tutti gli emittenti»,
--   che per costruzione passa.
--
-- ⭐ Perche' un guard dedicato e non il BB script.trgfn_guard_emittente_scope:
--   la tabella non ha la RLS. I casi 5, 7 e 16 sono i tre buchi che il BB
--   avrebbe lasciato (UPDATE a emittente invariato, DELETE, app senza utente).
--
-- Elenco test (plan 17):
--   forma
--    1) il guard e' SECURITY INVOKER
--    2) montato BEFORE INSERT OR UPDATE OR DELETE, per riga, senza UPDATE OF
--    3) ⭐ il presupposto della forma (A): la tabella non ha la RLS
--   super admin con X scelto
--    4) INSERT di un override su Y -> E_SCOPE_EMITTENTE
--    5) UPDATE del SOLO valore di un override di Y -> E_SCOPE_EMITTENTE
--    6) UPDATE che sposta un override da X a Y -> E_SCOPE_EMITTENTE
--    7) DELETE di un override di Y -> E_SCOPE_EMITTENTE
--    8) su X: l'INSERT passa
--    9) su X: l'UPDATE del valore passa
--   10) su X: il DELETE passa
--   l'operatore di X
--   11) sul proprio emittente l'INSERT passa
--   12) l'UPDATE del valore di un override di Y -> E_SCOPE_EMITTENTE
--   13) un override per utente (emittente NULL) passa
--   il limite dichiarato (§3 del brief)
--   14) il super admin in «tutti gli emittenti» modifica l'override di Y
--   senza utente in sessione
--   15) ⭐ il presupposto: questa sessione non e' il proprietario della tabella
--   16) app senza utente, override per emittente -> E_SCOPE_SENZA_UTENTE
--   17) app senza utente, override per utente (nessun padrone) -> passa
--
-- ⚠️ Runner: APPLICATIVO (nessun marcatore `pgtap-runner`). Il 15 lo rende
--   un'asserzione: da proprietario la sessione senza utente passa per
--   costruzione, e il 16 sarebbe rosso per la ragione giusta ma non
--   proverebbe niente. scripts/prova_changeset.py gira da owner: li' 15 e 16
--   sono rossi per costruzione, e l'esito vero arriva dopo l'apply.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI (il padre attivo dell'emittente e della categoria):
--   senza questa riga scatterebbero al COMMIT, che qui non arriva.
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(17);

-- ============================================================
-- Fixture
-- ============================================================
-- Chi agisce: utente, ruolo applicativo, emittente scelto (NULL = «tutti»).
CREATE OR REPLACE FUNCTION pg_temp.agisci(p_user integer, p_emittente bigint)
RETURNS void LANGUAGE sql AS $$
    SELECT set_config('app.ruolo_applicativo', 'OPERATORE', false),
           set_config('app.current_user_id', coalesce(p_user::text, ''), false),
           set_config('app.current_emittente_id', coalesce(p_emittente::text, ''), false);
$$;

CREATE TEMP TABLE t_x AS
SELECT c.emittente_fiscale_id AS ef, c.auth_user_id AS op
  FROM dbops.fn_pgtap_crea_emittente_operatore() c;

CREATE TEMP TABLE t_y AS
SELECT c.emittente_fiscale_id AS ef, c.auth_user_id AS op
  FROM dbops.fn_pgtap_crea_emittente_operatore() c;

CREATE TEMP TABLE t_sa AS
SELECT o.auth_user_id AS sa
  FROM dbops.fn_pgtap_crea_operatore_umano('pgTAP SA scope override', true) o;

-- Due parametri con override, uno per non far urtare l'unicita' nello spostamento.
INSERT INTO config.parameters (id, code, default_value, description, ammette_override, tipo_valore)
VALUES (99931, '_TEST_OVR_EF_SCOPE_1_', 'DEF', 'pgTAP guard di scope degli override (1)', true, 'TESTO'),
       (99932, '_TEST_OVR_EF_SCOPE_2_', 'DEF', 'pgTAP guard di scope degli override (2)', true, 'TESTO');

-- Le righe di partenza, scritte dal super admin in «tutti»: P1 su Y, P2 su X.
SELECT pg_temp.agisci((SELECT sa FROM t_sa), NULL);
INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, emittente_fiscale_id)
SELECT 99941, 99931, 'Y1', y.ef FROM t_y y;
INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, emittente_fiscale_id)
SELECT 99942, 99932, 'X2', x.ef FROM t_x x;

-- ============================================================
-- Forma
-- ============================================================
SELECT is(
    (SELECT p.prosecdef FROM pg_proc p
      WHERE p.oid = 'config.trgfn_parameter_overrides_guard_emittente_scope()'::regprocedure),
    false,
    '1. il guard e'' SECURITY INVOKER');

-- tgtype: 1 ROW, 2 BEFORE, 4 INSERT, 8 DELETE, 16 UPDATE. tgattr vuoto: niente OF.
SELECT is(
    (SELECT format('%s|%s', t.tgtype::int & 31, cardinality(t.tgattr::int2[]))
       FROM pg_trigger t
      WHERE t.tgrelid = 'config.parameter_overrides'::regclass
        AND t.tgfoid  = 'config.trgfn_parameter_overrides_guard_emittente_scope'::regproc
        AND NOT t.tgisinternal),
    '31|0',
    '2. montato BEFORE INSERT OR UPDATE OR DELETE, per riga, senza UPDATE OF');

SELECT is(
    (SELECT c.relrowsecurity FROM pg_class c WHERE c.oid = 'config.parameter_overrides'::regclass),
    false,
    '3. la tabella non ha la RLS: e'' il presupposto del guard dedicato (se nasce una policy, si torna al BB)');

-- ============================================================
-- Super admin con X scelto
-- ============================================================
SELECT pg_temp.agisci((SELECT sa FROM t_sa), (SELECT ef FROM t_x));

SELECT throws_like(
    format($$INSERT INTO config.parameter_overrides (parameter_id, overridden_value, emittente_fiscale_id)
             VALUES (99932, 'Y2', %s)$$, (SELECT ef FROM t_y)),
    '%scope emittente fiscale%',
    '4. super admin con X: INSERT di un override su Y -> E_SCOPE_EMITTENTE');

SELECT throws_like(
    $$UPDATE config.parameter_overrides SET overridden_value = 'Y1bis' WHERE id = 99941$$,
    '%scope emittente fiscale%',
    '5. super admin con X: UPDATE del solo valore di un override di Y -> E_SCOPE_EMITTENTE');

SELECT throws_like(
    format($$UPDATE config.parameter_overrides SET emittente_fiscale_id = %s WHERE id = 99942$$,
           (SELECT ef FROM t_y)),
    '%scope emittente fiscale%',
    '6. super admin con X: UPDATE che sposta un override da X a Y -> E_SCOPE_EMITTENTE');

SELECT throws_like(
    $$DELETE FROM config.parameter_overrides WHERE id = 99941$$,
    '%scope emittente fiscale%',
    '7. super admin con X: DELETE di un override di Y -> E_SCOPE_EMITTENTE');

SELECT lives_ok(
    format($$INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, emittente_fiscale_id)
             VALUES (99943, 99931, 'X1', %s)$$, (SELECT ef FROM t_x)),
    '8. super admin con X: l''INSERT su X passa');

SELECT lives_ok(
    $$UPDATE config.parameter_overrides SET overridden_value = 'X1bis' WHERE id = 99943$$,
    '9. super admin con X: l''UPDATE del valore su X passa');

SELECT lives_ok(
    $$DELETE FROM config.parameter_overrides WHERE id = 99943$$,
    '10. super admin con X: il DELETE su X passa');

-- ============================================================
-- L'operatore di X
-- ============================================================
SELECT pg_temp.agisci((SELECT op FROM t_x), NULL);

SELECT lives_ok(
    format($$INSERT INTO config.parameter_overrides (parameter_id, overridden_value, emittente_fiscale_id)
             VALUES (99931, 'X1', %s)$$, (SELECT ef FROM t_x)),
    '11. operatore di X: l''INSERT sul proprio emittente passa');

SELECT throws_like(
    $$UPDATE config.parameter_overrides SET overridden_value = 'Y1ter' WHERE id = 99941$$,
    '%scope emittente fiscale%',
    '12. operatore di X: l''UPDATE del valore di un override di Y -> E_SCOPE_EMITTENTE');

SELECT lives_ok(
    format($$INSERT INTO config.parameter_overrides (parameter_id, overridden_value, django_user_id)
             VALUES (99931, 'U1', %s)$$, (SELECT op FROM t_x)),
    '13. operatore di X: un override per utente (emittente NULL) passa');

-- ============================================================
-- Il limite dichiarato: in «tutti» il super admin passa
-- ============================================================
SELECT pg_temp.agisci((SELECT sa FROM t_sa), NULL);

SELECT lives_ok(
    $$UPDATE config.parameter_overrides SET overridden_value = 'Y1quater' WHERE id = 99941$$,
    '14. super admin in «tutti»: modifica l''override di Y (la sola lettura la garantisce il BE, brief §3)');

-- ============================================================
-- Senza utente in sessione
-- ============================================================
SELECT ok(
    NOT pg_has_role(current_user,
                    (SELECT c.relowner FROM pg_class c WHERE c.oid = 'config.parameter_overrides'::regclass),
                    'USAGE')
    AND NOT (SELECT r.rolsuper OR r.rolbypassrls FROM pg_roles r WHERE r.rolname = current_user),
    '15. questa sessione non e'' ne'' il proprietario ne'' esente dalla RLS: il 16 ha senso');

SELECT pg_temp.agisci(NULL, NULL);

SELECT throws_ok(
    $$UPDATE config.parameter_overrides SET overridden_value = 'Y1quinquies' WHERE id = 99941$$,
    'P0001',
    'Scrittura su config.parameter_overrides senza un utente in sessione: il processo non dichiara chi agisce.',
    '16. app senza utente su un override per emittente -> E_SCOPE_SENZA_UTENTE');

SELECT lives_ok(
    format($$INSERT INTO config.parameter_overrides (parameter_id, overridden_value, django_user_id)
             VALUES (99932, 'U2', %s)$$, (SELECT sa FROM t_sa)),
    '17. app senza utente su un override per utente: nessun padrone, passa');

SELECT * FROM finish();

ROLLBACK;
