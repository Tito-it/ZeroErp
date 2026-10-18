-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard anti-lockout ultimo SUPER_ADMIN (13.3.6 WIP multi-face-auth)
--   Copre 2 trigger che delegano a script.fn_check_almeno_un_super_admin_attivo:
--     - config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin
--     - anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin
--
-- Strategia:
--   - Ambiente con SUPER_ADMIN preesistenti (seed 80_data).
--   - mk_admin() crea un binding SA su un'identita OPERATORE "vergine"
--     (mai avuta un binding, per rispettare uq_...bindings_identita
--     partial unique).
--   - Stato progressivamente "sporco" tra i casi: lo stato finale viene
--     rolled-back dal BEGIN/ROLLBACK implicito alla fine del file.
--   - Niente SAVEPOINT esterni: ROLLBACK TO SAVEPOINT azzera anche il
--     counter interno di pgTAP e causa "No tests run!".
--
-- Indice test (1..3):
--    1. Scenario SANO: disattivo 1 binding SA con altri attivi -> no raise
--    2. Scenario LOCKOUT binding: disattivo l'ultimo binding SA -> raise
--    3. Scenario LOCKOUT identita: disattivo l'identita portante -> raise
--
-- BEGIN; + rollback implicito a fine file.
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

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(3);

-- Il CODICE dell'errore viaggia nel canale CONSTRAINT_NAME dell'eccezione
-- P0001 (fn_log_and_raise_error). Si pinna il codice, non la frase del
-- catalogo: la frase si riscrive (rev 2026-10-07, giro 2 di
-- brief-db-veste-utilizzabile, «attivo e senza data di fine»), il codice no.
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

-- =========================================================
-- Helper: crea un binding SUPER_ADMIN ad-hoc su un'identita OPERATORE
-- "vergine" (mai avuta un binding). Ritorna (identita_id, binding_id).
-- Filtro su NOT EXISTS qualsiasi binding (attivo o meno) per rispettare
-- il vincolo uq_profili_accesso_bindings_identita (partial unique
-- WHERE identita_digitale_id IS NOT NULL).
-- =========================================================
CREATE OR REPLACE FUNCTION pg_temp.mk_admin(OUT id_id bigint, OUT bind_id bigint)
LANGUAGE plpgsql
AS $$
BEGIN
    -- ⛔ L'identita' si COSTRUISCE (2026-09-23). Cercare un'identita'
    --   OPERATORE «vergine» funzionava finche' il database ne aveva in
    --   abbondanza: su uno ricostruito ce n'e' UNA, quella dell'operatore di
    --   contesto, e dopo il primo scenario non e' piu' vergine — il terzo
    --   moriva sul «Setup impossibile». Un'azienda nuova con il suo operatore
    --   e' vergine per costruzione, e ogni scenario ha la sua.
    SELECT ceo.identita_id INTO id_id
      FROM dbops.fn_pgtap_crea_emittente_operatore() ceo;

    bind_id := config.fn_lega_profilo_identita((SELECT id FROM config.profili_accesso WHERE codice = 'SUPER_ADMIN'), id_id);
END
$$;

-- =========================================================
-- Helper: disattiva TUTTI i binding SUPER_ADMIN attivi tranne quello
-- passato come parametro. Ritorna il numero disattivati.
-- =========================================================
CREATE OR REPLACE FUNCTION pg_temp.disable_others(p_keep_bind_id bigint)
RETURNS int
LANGUAGE plpgsql
AS $$
DECLARE
    v_b record;
    v_count int := 0;
BEGIN
    FOR v_b IN
        SELECT pab.id
          FROM config.profili_accesso_bindings pab
          JOIN config.profili_accesso          pa
            ON pa.id = pab.profilo_accesso_id
         WHERE pa.codice = 'SUPER_ADMIN'
           AND pab.attivo = true
           AND pab.id <> p_keep_bind_id
    LOOP
        UPDATE config.profili_accesso_bindings
           SET attivo = false
         WHERE id = v_b.id;
        v_count := v_count + 1;
    END LOOP;
    RETURN v_count;
END
$$;

-- =========================================================
-- 0) Il SUPER_ADMIN che deve RESTARE
-- =========================================================
-- ⛔ Lo scenario 1 dice «ne disattivo uno e ne restano altri attivi»: su un
--   database ricostruito non ce n'e' nessun altro, quindi disattivare il
--   proprio era disattivare L'ULTIMO e il guard scattava — la fixture moriva
--   con il messaggio del guard, che e' il comportamento GIUSTO del prodotto
--   contro una precondizione che il file dava per scontata. Qui il
--   «preesistente» si costruisce, e lo scenario 1 torna a dire cio' che vuole
--   dire.
CREATE TEMP TABLE _t_c0 AS SELECT * FROM pg_temp.mk_admin();

-- =========================================================
-- 1) Scenario SANO: disattivo 1 binding SA ad-hoc lasciando preesistenti
--    attivi -> il guard non scatta, fn_check resta true.
-- =========================================================
CREATE TEMP TABLE _t_c1 AS SELECT * FROM pg_temp.mk_admin();

UPDATE config.profili_accesso_bindings
   SET attivo = false
 WHERE id = (SELECT bind_id FROM _t_c1);

SELECT ok(
    script.fn_check_almeno_un_super_admin_attivo(),
    '1. Scenario sano: disattivo 1 binding SUPER_ADMIN con preesistenti attivi -> guard non scatta, sistema resta con admin'
);

-- =========================================================
-- 2) Scenario LOCKOUT binding: lascio solo il mio SA attivo, poi
--    tento di disattivarlo -> raise.
-- =========================================================
CREATE TEMP TABLE _t_c2 AS SELECT * FROM pg_temp.mk_admin();

SELECT pg_temp.disable_others((SELECT bind_id FROM _t_c2));

-- ⭐ Il discriminante c'e' (2026-09-23): un `throws_ok(sql, NULL, NULL)`
--   accetta QUALUNQUE errore — anche quello sbagliato, ed e' il debito che il
--   cancello `guardrail_pgtap_preambolo.py` conta. Gli errori di dominio del
--   progetto sono tutti `P0001`: il discriminante e' il CODICE, che viaggia
--   in CONSTRAINT_NAME (pg_temp.codice_errore).
--   ⛔ Fino al 2026-10-07 si pinnava la FRASE («zero SUPER_ADMIN attivi»), e
--   la riscrittura del messaggio nel giro 2 di brief-db-veste-utilizzabile
--   («attivo e senza data di fine») ha reso rosso il test senza che la regola
--   cambiasse. La frase e' del catalogo, non del guard.
SELECT is(
    pg_temp.codice_errore(
        format(
            $sql$ UPDATE config.profili_accesso_bindings SET attivo = false WHERE id = %s $sql$,
            (SELECT bind_id FROM _t_c2)
        )),
    'E_PROFILO_ULTIMO_SUPER_ADMIN',
    '2. Scenario lockout binding: UPDATE attivo=false dell''ultimo SUPER_ADMIN -> raise E_PROFILO_ULTIMO_SUPER_ADMIN');

-- =========================================================
-- 3) Scenario LOCKOUT identita: lascio solo il nuovo SA attivo, poi
--    disattivo l'identita portante -> raise.
--    Dopo caso 2, il binding mio caso 2 e' rimasto attivo (throws_ok
--    rolled-back l'UPDATE fallito), ma disable_others del caso 3 lo
--    disattivera'.
-- =========================================================
CREATE TEMP TABLE _t_c3 AS SELECT * FROM pg_temp.mk_admin();

SELECT pg_temp.disable_others((SELECT bind_id FROM _t_c3));

-- ⛔ TROVATO IL 2026-09-23: fino al 2026-09-25 questo UPDATE NON lo
--   rifiutava `E_PROFILO_ULTIMO_SUPER_ADMIN`, ma il guard GENERICO delle
--   figlie — `trgfn_prevent_deactivate_if_children` montato dall'automazione
--   ATTIVO fra identita_digitali e profili_accesso_bindings — che rifiutava
--   qualunque identita' con un binding attivo e scattava prima. Il ramo
--   specifico sull'identita' non era raggiungibile, e l'asserzione era
--   generica (P0001) per reggere in entrambi i mondi.
-- ⭐ Rev 2026-09-25 (brief-db-blocco-login-per-credenziale §12.3): porta e
--   profili si sono SGANCIATI — la coppia e' un'eccezione dichiarata in
--   dbops.automazione_attivo_eccezioni e quel block non c'e' piu'. Il ramo
--   specifico e' raggiungibile, e l'asserzione pinna la regola: E_PROFILO_ULTIMO_SUPER_ADMIN.
SELECT is(
    pg_temp.codice_errore(
        format(
            $sql$ UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = %s $sql$,
            (SELECT id_id FROM _t_c3)
        )),
    'E_PROFILO_ULTIMO_SUPER_ADMIN',
    '3. Scenario lockout identita: disattivare l''ultima identita'' con SUPER_ADMIN -> E_PROFILO_ULTIMO_SUPER_ADMIN');

SELECT * FROM finish();
