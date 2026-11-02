-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_user_emittenti_scope(p_auth_user_id)
--   Vista dichiarativa "scope emittenti" per il drawer Operatore
--   (Fase 2 P1 2026-04-29).
--
-- Strategia:
--   Riusa il pattern mk_admin/disable_other_sa per generare scenari
--   ultimo-SA controllabili. Setup di una riga
--   user_emittenti_fiscali transitoria su un'OPERATORE vergine per
--   esercitare il ramo SINGLE. Stato accumulato tra i casi
--   (no SAVEPOINT) e rolled-back a fine file.
--
-- Indice test (1..6):
--   1. Auth user senza righe -> scope_mode=GLOBAL, emittente_id=NULL
--   2. Auth user con riga    -> scope_mode=SINGLE, emittente_id valued
--   3. allowed_scope_modes   -> sempre ['GLOBAL','SINGLE']
--   4. emittente_descrizione -> valorizzata in SINGLE
--   5. Multi super-admin     -> can_change_scope=true (target non e' ultimo)
--   6. Single super-admin    -> can_change_scope=false + reason valorizzato
--
-- Niente SAVEPOINT (azzera il counter pgTAP).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- ⛔ LE TRE IDENTITA' SI COSTRUISCONO, non si cercano (2026-09-12). Fino a quel
--   giorno il file pescava fra le identita' ESISTENTI l'operatore di contesto,
--   quello da portare in GLOBAL e quello da promuovere super admin: su un
--   database ricostruito dai changelog non ce n'e' nessuna, e il file moriva
--   nella fixture (auth_user_id NULL al test 2). Tre aziende con
--   `dbops.fn_pgtap_crea_emittente_operatore()`, PRIMA di aprire il contesto.
CREATE TEMP TABLE _mondi AS
SELECT 'CTX'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'GLOBAL' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'SA'     AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'SA2'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⚠️ Il SECONDO super admin si costruisce anche lui: il test 5 dice «il target
--   non e' l'ultimo SA», e su un database ricostruito dai changelog di super
--   admin non ce n'e' nessuno — senza questa riga il caso «multi» non esiste e
--   il test 5 misurerebbe il caso «single» con l'etichetta sbagliata.
DO $lega$ BEGIN PERFORM config.fn_lega_profilo_identita((SELECT id FROM config.profili_accesso WHERE codice = 'SUPER_ADMIN'), (SELECT identita_id FROM _mondi WHERE lato = 'SA2')); END $lega$;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'CTX'));
END $ctx$;

SELECT plan(6);

-- =========================================================
-- Helper: l'identita' OPERATORE costruita per il ruolo SA + binding SA
-- =========================================================
CREATE OR REPLACE FUNCTION pg_temp.mk_admin(OUT id_id bigint, OUT au_id integer, OUT bind_id bigint)
LANGUAGE plpgsql
AS $$
BEGIN
    SELECT m.identita_id, m.auth_user_id INTO id_id, au_id
      FROM _mondi m
     WHERE m.lato = 'SA';

    bind_id := config.fn_lega_profilo_identita((SELECT id FROM config.profili_accesso WHERE codice = 'SUPER_ADMIN'), id_id);
END
$$;

CREATE OR REPLACE FUNCTION pg_temp.disable_other_sa(p_keep_bind_id bigint)
RETURNS int LANGUAGE plpgsql AS $$
DECLARE v_b record; v_count int := 0;
BEGIN
    FOR v_b IN
        SELECT pab.id FROM config.profili_accesso_bindings pab
          JOIN config.profili_accesso pa ON pa.id = pab.profilo_accesso_id
         WHERE pa.codice = 'SUPER_ADMIN' AND pab.attivo = true
           AND pab.id <> p_keep_bind_id
    LOOP
        UPDATE config.profili_accesso_bindings SET attivo = false WHERE id = v_b.id;
        v_count := v_count + 1;
    END LOOP;
    RETURN v_count;
END
$$;

-- =========================================================
-- Setup: OPERATORE non-SA in stato GLOBAL — l'azienda GLOBAL, a cui si
-- toglie la riga in user_emittenti_fiscali
-- =========================================================
-- 🔴 FIXTURE RICOSTRUITA il 2026-08-18 — gemella di quella in
--   test-fn-change-user-emittenti-scope, e rotta dalla stessa causa.
--   Cercava un operatore GIA' in stato GLOBAL (senza riga in
--   user_emittenti_fiscali) e si affidava al fatto che in sviluppo ne
--   esistesse uno. Il cantiere perimetro emittente (DL-A) li ha portati a
--   ZERO: la ricerca tornava vuota e l'INSERT del test 2 moriva su
--   `auth_user_id` NULL.
--   ⚠️ La precondizione non si CERCA, si COSTRUISCE: la fixture ha smesso di
--   funzionare il giorno in cui il progetto ha sistemato i dati, che e' il
--   momento peggiore per scoprirlo.
--   Il DELETE passa dall'override GUC (la tabella ha un guard sul delete) e il
--   file e' transazionale: lo scope vero torna al ROLLBACK.
CREATE TEMP TABLE _t_user_global AS
SELECT m.auth_user_id AS au_id FROM _mondi m WHERE m.lato = 'GLOBAL';

SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT au_id FROM _t_user_global);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

-- Setup: l'emittente per il ramo SINGLE e' quello dell'azienda GLOBAL,
-- che il test 2 gli riassegna.
CREATE TEMP TABLE _t_ef AS
SELECT m.emittente_fiscale_id AS ef_id FROM _mondi m WHERE m.lato = 'GLOBAL';

-- =========================================================
-- 1) Auth user senza righe -> scope_mode=GLOBAL, emittente_id=NULL
-- =========================================================
SELECT is(
    (SELECT (scope_mode, emittente_id::text)
       FROM script.fn_get_user_emittenti_scope((SELECT au_id FROM _t_user_global))),
    -- 🔴 `'GLOBAL'::text` il 2026-08-18: senza il cast il letterale resta di tipo
    --   `unknown`, e il confronto fra RECORD pretende colonne dello stesso tipo
    --   («non e' possibile confrontare i tipi di colonne dissimili text e
    --   unknown»). Il secondo elemento il cast ce l'aveva gia': mancava al primo.
    --   ⚠️ Il file non falliva, MORIVA: 6 asserzioni su 6 mai eseguite.
    --   ⭐ Verificato che NON e' una conseguenza di P-2a (20260818-11/-12): il
    --   rosso e' storico e riguarda la forma del confronto, non il valore
    --   restituito dalla funzione.
    ROW('GLOBAL'::text, NULL::text)::record,
    '1. Senza riga in user_emittenti_fiscali -> scope_mode=GLOBAL, emittente_id NULL'
);

-- =========================================================
-- 2) Auth user con riga -> scope_mode=SINGLE, emittente_id valued
-- =========================================================
INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
VALUES ((SELECT au_id FROM _t_user_global), (SELECT ef_id FROM _t_ef));

SELECT is(
    (SELECT scope_mode FROM script.fn_get_user_emittenti_scope((SELECT au_id FROM _t_user_global))),
    'SINGLE',
    '2. Con riga in user_emittenti_fiscali -> scope_mode=SINGLE'
);

-- =========================================================
-- 3) allowed_scope_modes -> sempre ['GLOBAL','SINGLE']
-- =========================================================
SELECT is(
    (SELECT allowed_scope_modes
       FROM script.fn_get_user_emittenti_scope((SELECT au_id FROM _t_user_global))),
    ARRAY['GLOBAL','SINGLE']::text[],
    '3. allowed_scope_modes esposto sempre come [GLOBAL, SINGLE]'
);

-- =========================================================
-- 4) emittente_descrizione valorizzata in SINGLE
-- =========================================================
SELECT ok(
    (SELECT emittente_descrizione IS NOT NULL AND length(emittente_descrizione) > 0
       FROM script.fn_get_user_emittenti_scope((SELECT au_id FROM _t_user_global))),
    '4. emittente_descrizione valorizzata in scope SINGLE'
);

-- =========================================================
-- 5) Multi super-admin: SA2 c'e' gia' dalla fixture, aggiungo SA -> >=2 SA.
--    Sul nuovo SA: can_change_scope=true.
-- =========================================================
CREATE TEMP TABLE _t_sa AS SELECT * FROM pg_temp.mk_admin();

SELECT is(
    (SELECT can_change_scope
       FROM script.fn_get_user_emittenti_scope((SELECT au_id FROM _t_sa))),
    true,
    '5. Multi super-admin: can_change_scope=true (target non e'' ultimo SA)'
);

-- =========================================================
-- 6) Single super-admin: disabilito tutti gli altri SA bindings
--    -> il SA di _t_sa diventa l'unico. can_change_scope=false +
--    change_scope_reason valorizzato.
-- =========================================================
SELECT pg_temp.disable_other_sa((SELECT bind_id FROM _t_sa));

SELECT is(
    (SELECT (NOT can_change_scope)
            AND change_scope_reason ILIKE '%lockout%'
       FROM script.fn_get_user_emittenti_scope((SELECT au_id FROM _t_sa))),
    true,
    '6. Single super-admin: can_change_scope=false + change_scope_reason cita lockout'
);

SELECT * FROM finish();
ROLLBACK;
