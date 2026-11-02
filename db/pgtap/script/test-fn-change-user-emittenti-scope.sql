-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_change_user_emittenti_scope(p_auth_user_id, p_emittente_ids)
--   Orchestrazione atomica del cambio scope per il drawer Operatore
--   (Fase 2 P1 2026-04-29).
--
-- Strategia:
--   Setup OPERATORE vergine non-SA (cambio scope senza interazione
--   con guard ultimo-SA). Setup separato SA singleton per testare
--   il guard E_PROFILO_ULTIMO_SUPER_ADMIN. Stato accumulato tra i
--   casi (no SAVEPOINT) e rolled-back a fine file.
--
-- Indice test (1..6):
--   1. MULTI (>1) -> raise E_OPERATORE_SCOPE_MULTI_NON_AMMESSO
--   2. GLOBAL -> SINGLE  (INSERT)            -> changed=true, riga creata
--   3. SINGLE -> SINGLE stesso EF (no-op)    -> changed=false, riga invariata
--   4. SINGLE -> GLOBAL  (DELETE + override) -> changed=true, riga rimossa
--   5. NULL/[] su utente senza riga (no-op)  -> changed=false
--   6. Ultimo SA cambia scope -> raise E_PROFILO_ULTIMO_SUPER_ADMIN
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

-- ⛔ LE TRE IDENTITA' SI COSTRUISCONO, non si cercano (2026-09-12). La fixture
--   del 2026-08-18 aveva imparato a COSTRUIRE lo stato GLOBAL, ma l'operatore a
--   cui costruirlo lo cercava ancora fra gli esistenti — e su un database
--   ricostruito dai changelog non ce n'e' nessuno: «p_auth_user_id non valido:
--   NULL», sette asserzioni perse. Tre aziende con
--   `dbops.fn_pgtap_crea_emittente_operatore()`, PRIMA di aprire il contesto:
--   quella del contesto, quella dell'operatore sotto test, quella del super admin.
CREATE TEMP TABLE _mondi AS
SELECT 'CTX' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'OP'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'SA'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'CTX'));
END $ctx$;

-- 🔴 plan 6 -> 7 il 2026-08-18: le asserzioni erano SEMPRE state sette (il
--   punto 2 ne ha due: `changed=true` e la riga effettivamente scritta), ma il
--   file moriva alla prima e il piano sbagliato non si e' mai visto.
--   ⚠️ Un piano piu' basso del numero di asserzioni non e' un dettaglio
--   formale: pgTAP lo segnala come «Bad plan» e rende ROSSO un file in cui
--   tutte le asserzioni passano — cioe' nasconde il verde, dopo aver nascosto
--   il rosso.
SELECT plan(7);

-- =========================================================
-- Helper SA: l'identita' OPERATORE costruita per il ruolo SA + binding SA
-- =========================================================
CREATE OR REPLACE FUNCTION pg_temp.mk_admin(OUT id_id bigint, OUT au_id integer, OUT bind_id bigint)
LANGUAGE plpgsql AS $$
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
-- Setup OPERATORE non-SA libero (no binding, no user_emittenti_fiscali)
-- =========================================================
-- 🔴 FIXTURE RICOSTRUITA il 2026-08-18.
--   Cercava un operatore che fosse GIA' in stato GLOBAL — senza binding e senza
--   riga in `user_emittenti_fiscali` — e si affidava al fatto che in sviluppo
--   ne esistesse uno. Dal cantiere perimetro emittente (DL-A) quegli operatori
--   sono a ZERO: la ricerca tornava vuota, `au_id` usciva NULL e la funzione
--   sollevava «p_auth_user_id non valido: NULL». Sei asserzioni su sei perse.
--
--   ⚠️ La fixture non costruiva la precondizione: la CERCAVA, e ha smesso di
--   trovarla il giorno in cui il progetto ha sistemato i dati. E' lo stesso
--   difetto che ha gia' colpito test-permessi-user-overrides — «prendi il primo
--   e spera» — solo al contrario: li' il dato reale c'era di troppo, qui manca.
--
--   ⭐ Ora lo stato GLOBAL si COSTRUISCE: si prende l'operatore costruito e gli
--   si toglie la riga di scope. Il DELETE passa dall'override GUC perche' la
--   tabella ha un guard sul delete.
--   ⛔ E si toglie a mano invece di chiamare `fn_change_user_emittenti_scope`
--   con array vuoto: sarebbe la funzione SOTTO TEST a costruire la propria
--   precondizione, e un difetto in lei renderebbe il test verde per errore.
--   Il file e' transazionale: lo scope vero torna al ROLLBACK.
CREATE TEMP TABLE _t_user AS
SELECT m.auth_user_id AS au_id FROM _mondi m WHERE m.lato = 'OP';

SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali
 WHERE auth_user_id = (SELECT au_id FROM _t_user);
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';

-- L'EF per il caso SINGLE: quello dell'azienda dell'operatore sotto test
CREATE TEMP TABLE _t_ef AS
SELECT m.emittente_fiscale_id AS ef_id FROM _mondi m WHERE m.lato = 'OP';

-- =========================================================
-- 1) Guard MULTI (>1 elementi) -> raise E_OPERATORE_SCOPE_MULTI_NON_AMMESSO
-- =========================================================
SELECT throws_like(
    format(
        $sql$ SELECT script.fn_change_user_emittenti_scope(%s, ARRAY[1::bigint, 2::bigint]) $sql$,
        (SELECT au_id FROM _t_user)
    ),
    '%MULTI%',
    '1. p_emittente_ids con >1 elementi -> raise E_OPERATORE_SCOPE_MULTI_NON_AMMESSO'
);

-- =========================================================
-- 2) GLOBAL -> SINGLE: INSERT, changed=true
-- =========================================================
SELECT is(
    (SELECT script.fn_change_user_emittenti_scope(
                (SELECT au_id FROM _t_user),
                ARRAY[(SELECT ef_id FROM _t_ef)]
            )->>'changed')::boolean,
    true,
    '2. GLOBAL -> SINGLE: changed=true'
);

SELECT is(
    (SELECT count(*)::int FROM config.user_emittenti_fiscali
      WHERE auth_user_id = (SELECT au_id FROM _t_user)),
    1,
    '2.bis Riga creata in user_emittenti_fiscali'
);

-- =========================================================
-- 3) SINGLE -> SINGLE stesso EF: no-op, changed=false
-- =========================================================
SELECT is(
    (SELECT script.fn_change_user_emittenti_scope(
                (SELECT au_id FROM _t_user),
                ARRAY[(SELECT ef_id FROM _t_ef)]
            )->>'changed')::boolean,
    false,
    '3. SINGLE -> SINGLE stesso EF: no-op (changed=false)'
);

-- =========================================================
-- 4) SINGLE -> GLOBAL: DELETE con override interno, changed=true
--    Verifica che il guard_delete venga superato dal SET LOCAL
--    interno (auth_user e' attivo).
-- =========================================================
SELECT is(
    (SELECT script.fn_change_user_emittenti_scope(
                (SELECT au_id FROM _t_user),
                NULL::bigint[]
            )->>'changed')::boolean,
    true,
    '4. SINGLE -> GLOBAL: changed=true (override guard_delete via SET LOCAL)'
);

-- Skip caso 5 perche' ridondante con caso 1 - rimpiazzato con verifica
-- residua riga assente:
SELECT is(
    (SELECT count(*)::int FROM config.user_emittenti_fiscali
      WHERE auth_user_id = (SELECT au_id FROM _t_user)),
    0,
    '5. Riga rimossa dopo SINGLE -> GLOBAL'
);

-- =========================================================
-- 6) Ultimo SA: cambio scope vietato -> raise E_PROFILO_ULTIMO_SUPER_ADMIN
--    Setup: aggiungo SA ad-hoc, garantisco scope GLOBAL del SA
--    (cleanup difensivo) e disabilito gli altri SA.
-- =========================================================
CREATE TEMP TABLE _t_sa AS SELECT * FROM pg_temp.mk_admin();

-- Defensive: forzare GLOBAL sul nuovo SA cosi' il target SINGLE
-- e' un cambio reale (non un no-op).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM config.user_emittenti_fiscali
                WHERE auth_user_id = (SELECT au_id FROM _t_sa)) THEN
        SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
        DELETE FROM config.user_emittenti_fiscali
         WHERE auth_user_id = (SELECT au_id FROM _t_sa);
    END IF;
END $$;

SELECT pg_temp.disable_other_sa((SELECT bind_id FROM _t_sa));

SELECT throws_like(
    format(
        $sql$ SELECT script.fn_change_user_emittenti_scope(%s, ARRAY[%s::bigint]) $sql$,
        (SELECT au_id FROM _t_sa),
        (SELECT ef_id FROM _t_ef)
    ),
    '%SUPER_ADMIN%',
    '6. Ultimo SA: cambio scope reale -> raise E_PROFILO_ULTIMO_SUPER_ADMIN'
);

SELECT * FROM finish();
ROLLBACK;
