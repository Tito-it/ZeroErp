-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il profilo di accesso SUPER_ADMIN si risolve in una sede sola (2026-10-18).
-- R-BE-11 del BE (regola del 2, ok Tid 2026-10-18),
-- brief-db-processi-accensione-per-ambiente §6.10 (la richiesta) e §6.15 (la
-- risposta). ChangeSet 20261019-16, -17.
--
-- Elenco test (plan 5):
--  1)   la firma del lettore
--  2)   STABLE e SECURITY INVOKER
--  3)   un secondo profilo SUPER_ADMIN SPENTO non conta: il lettore risponde
--       l'unico attivo
--  4)   due profili SUPER_ADMIN attivi: E_CONFIG_MANCANTE, «trovati 2»
--  5)   ... e la madre della risorsa umana si ferma sullo stesso codice, prima
--       di scrivere (la regola non e' piu' sua: la legge dal lettore). Senza la
--       regola si fermerebbe piu' avanti, sul soggetto inventato, con un altro
--       errore: e' questo che rende il pattern discriminante.
--
-- ⚠️ Non provato qui: zero profili attivi. Il profilo del seed non si spegne
--   finche' ha legami (trg_profili_accesso_..._bindings_block_deact), e i legami
--   ci sono su ogni database con un operatore super admin. Il ramo e' lo
--   stesso del 4) (v_n <> 1).
--
-- Scopo:
--  - provare la regola COSTRUENDO il secondo profilo (regola zero: il test non
--    conta i profili di oggi).
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE _ctx ON COMMIT DROP AS
SELECT script.fn_pgtap_set_contesto_operatore() AS auth_user_id;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- Fixture: un secondo profilo SUPER_ADMIN, spento
-- ============================================================
CREATE TEMP TABLE _p (profilo_id integer) ON COMMIT DROP;
WITH p AS (
    -- ⚠️ Un profilo SUPER_ADMIN chiede il secondo fattore
    --   (chk_profili_accesso_super_admin_secondo_fattore).
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo, richiede_secondo_fattore)
    VALUES ('SUPER_ADMIN'::config.tipo_profilo_accesso,
            'PGTAP_SA_' || replace(gen_random_uuid()::text, '-', ''),
            'Profilo pgTAP: secondo SUPER_ADMIN', false, true)
    RETURNING id
)
INSERT INTO _p SELECT p.id FROM p;

CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT c.auth_user_id,
       gen_random_uuid() AS soggetto_id,
       (SELECT q.id FROM config.qualifiche q WHERE q.attivo ORDER BY q.id LIMIT 1) AS qualifica_id
  FROM _ctx c;

-- ============================================================
-- 1-3) Il lettore
-- ============================================================
SELECT has_function('config', 'fn_profilo_super_admin_id', ARRAY[]::text[],
    '1) config.fn_profilo_super_admin_id()');

SELECT is(
    (SELECT p.provolatile::text || '/' || p.prosecdef::text
       FROM pg_proc p WHERE p.oid = 'config.fn_profilo_super_admin_id()'::regprocedure),
    's/false',
    '2) STABLE e SECURITY INVOKER');

-- ⚠️ Il lettore in un'istruzione sua, poi si legge la riga.
CREATE TEMP TABLE _r ON COMMIT DROP AS
SELECT config.fn_profilo_super_admin_id() AS profilo_id;

SELECT is(
    (SELECT pa.tipo::text || '/' || pa.attivo::text || '/' || (pa.id <> _p.profilo_id)::text
       FROM config.profili_accesso pa, _r, _p
      WHERE pa.id = _r.profilo_id),
    'SUPER_ADMIN/true/true',
    '3) un secondo profilo SUPER_ADMIN spento non conta: risponde l''unico attivo');

-- ============================================================
-- 4-5) Due profili attivi
-- ============================================================
UPDATE config.profili_accesso SET attivo = true WHERE id = (SELECT profilo_id FROM _p);

SELECT throws_like(
    $$SELECT config.fn_profilo_super_admin_id()$$,
    '%trovati 2%',
    '4) due profili SUPER_ADMIN attivi: E_CONFIG_MANCANTE, nessuno scelto per id');

SELECT throws_like(
    (SELECT format(
        'SELECT anagrafiche.fn_crea_risorsa_umana_v2(p_soggetto_id => %L::uuid, p_qualifica_id => %s, '
        'p_auth_user_id => %s, p_is_super_admin => true)',
        soggetto_id, qualifica_id, auth_user_id) FROM _f),
    '%trovati 2%',
    '5) ... e la madre della risorsa umana si ferma sullo stesso codice, prima di scrivere');

SELECT * FROM finish();
ROLLBACK;
