-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: legge pg_proc delle funzioni del framework automazioni,
--   che appartengono al migratore; nessuna scrittura.
-- pgtap-contesto: escluso — il file non legge tabelle con RLS: interroga il
--   catalogo (pg_proc) e una funzione pura sul codice SQLSTATE. Un contesto
--   operatore non cambierebbe nessuna risposta.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti §6.4): il preambolo
--   dichiara il contesto escluso e richiude i vincoli differiti, come chiede
--   scripts/guardrail_pgtap_preambolo.py; i test non cambiano.
--
-- Test: un guasto dell'ambiente dentro un'automazione esce col suo SQLSTATE
--   (script.fn_sqlstate_di_ambiente e i gestori WHEN others del framework)
-- ChangeSet: 20_code/script/20261016-44 · 20_code/dbops/20261016-45…-52
-- Brief: brief-db-presidio-job-run-a-chi-tocca §10 (D8, D10, D11)
--
-- Elenco test (plan 6):
--  1) ⭐ il predicato: si' per 08/53/57/58, 42501 e 55P03
--  2) no per i difetti di programma: altre 42xxx, 23xxx, P0001, 40P01
--  3) NULL -> false, non NULL
--  4) ⛔ nessun gestore delle automazioni passa ancora DRITTO all'involucro
--     (WHEN others THEN PERFORM fn_log_and_raise_error)
--  5) ogni domanda al predicato apre il blocco intero: registro errori (D11),
--     poi RAISE; dell'originale
--  6) e dopo il blocco l'involucro di prima usa lo STESSO contesto (v_ctx_errore)
--
-- ────────────────────────────────────────────────────────────────
-- ⚠️ I TEST 4-6 SONO PRESIDI SUL TESTO, e si dichiarano tali. Provocare un
--   42501 o un 55P03 dentro un'automazione vorrebbe un ruolo senza diritti
--   proprietario di una tabella, o un lock tenuto da una seconda sessione
--   (dblink): il primo non e' costruibile dall'owner, il secondo e' la trappola
--   delle due sessioni dentro una transazione di prova. Il perimetro e' quello
--   del censimento (§9.2 del brief): dbops.fn_run_automations_% e
--   dbops.fn_ensure_storico_table.
-- ⚠️ Il test 4 guarda la FORMA di prima (il PERFORM subito dopo THEN): un
--   involucro nuovo scritto alla vecchia maniera lo fa rosso, ed e' voluto.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa, come in ogni file. Qui nessuna scrittura li
--   farebbe scattare (la tabella temporanea e' del test), ma la riga e' il
--   contratto del preambolo: chi aggiungera' una fixture la trova gia' al suo posto.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

CREATE TEMP TABLE _automazioni ON COMMIT DROP AS
SELECT p.proname::text AS nome, p.prosrc AS corpo
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'dbops'
   AND (p.proname LIKE 'fn\_run\_automations\_%' OR p.proname = 'fn_ensure_storico_table');

-- ============================================================
-- 1..3. Il predicato
-- ============================================================
SELECT is(
    (SELECT bool_and(script.fn_sqlstate_di_ambiente(s))
       FROM unnest(ARRAY['08006', '08P01', '53100', '53200', '57014', '57P01', '58030',
                         '42501', '55P03']) s),
    true,
    '1. il predicato dice si'' per connessione, risorse, arresto, sistema, privilegio e lock'
);

SELECT is(
    (SELECT bool_or(script.fn_sqlstate_di_ambiente(s))
       FROM unnest(ARRAY['42P01', '42703', '23505', '23514', 'P0001', '40P01', '22023']) s),
    false,
    '2. e no per i difetti di programma: oggetto inesistente, vincolo, dominio, deadlock'
);

SELECT is(
    script.fn_sqlstate_di_ambiente(NULL),
    false,
    '3. senza SQLSTATE non si afferma un guasto dell''ambiente'
);

-- ============================================================
-- 4..6. I gestori (presidi sul testo)
-- ============================================================
SELECT is(
    (SELECT string_agg(nome, ', ' ORDER BY nome)
       FROM _automazioni
      WHERE corpo ~* 'WHEN\s+others\s+THEN\s+PERFORM\s+script\.fn_log_and_raise_error'),
    NULL,
    '4. nessun gestore delle automazioni passa dritto all''involucro'
);

-- ⭐ Uguaglianza per funzione, contata sul BLOCCO e non sui RAISE; sparsi:
--   fn_run_automations_cleanup ha un suo RAISE; legittimo (rilancia la
--   cancellazione della query), che un conteggio nudo prenderebbe per un gestore.
SELECT is(
    (SELECT string_agg(nome, ', ' ORDER BY nome)
       FROM _automazioni
      WHERE (SELECT count(*) FROM regexp_matches(corpo, 'fn_sqlstate_di_ambiente\(SQLSTATE\)', 'g'))
         <> (SELECT count(*) FROM regexp_matches(corpo,
               'fn_sqlstate_di_ambiente\(SQLSTATE\)\s+THEN\s+PERFORM\s+script\.fn_log_error_only\([^;]*;\s*RAISE;', 'g'))),
    NULL,
    '5. ogni domanda al predicato scrive nel registro errori e rilancia l''originale (D11)'
);

SELECT is(
    (SELECT string_agg(nome, ', ' ORDER BY nome)
       FROM _automazioni
      WHERE (SELECT count(*) FROM regexp_matches(corpo, 'fn_sqlstate_di_ambiente\(SQLSTATE\)', 'g'))
         <> (SELECT count(*) FROM regexp_matches(corpo,
               'END IF;\s+PERFORM\s+script\.fn_log_and_raise_error\([^;]*v_ctx_errore', 'g'))),
    NULL,
    '6. e l''involucro dopo il blocco usa lo stesso contesto'
);

SELECT * FROM finish();

ROLLBACK;
