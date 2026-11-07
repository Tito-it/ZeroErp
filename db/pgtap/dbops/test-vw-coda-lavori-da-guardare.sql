-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.vw_coda_lavori_da_guardare — i lavori che chiedono un occhio
-- Brief: brief-db-processi-automatici-identita-e-perimetro §12.12 (DB-1)
--
-- Elenco test (plan 7):
--  1) ⛔ ERRORE compare, e il motivo lo dice
--  2) ⛔ IN_CORSO da oltre un'ora compare: il worker e' morto a meta'
--  3) ⛔ PENDING da oltre un'ora compare: IL WORKER NON STA GIRANDO
--  4) ✅ PENDING appena accodato NON compare: la soglia esiste davvero
--  5) ✅ IN_CORSO appena preso NON compare
--  6) ⚠️ ANNULLATO non compare: qualcuno l'ha deciso
--  7) ⚠️ archiviato non compare: qualcuno l'ha gia' guardato
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 3 E' LA RAGIONE PER CUI QUESTO FILE ESISTE.
--   Un lavoro fallito produce un errore, e un errore prima o poi si vede. Un
--   worker SPENTO non produce niente: produce ASSENZA. E' la forma esatta di
--   R-12 — `apply_storicizza_weekly` morto ogni settimana per sei mesi senza
--   che nessuno lo sapesse — ed e' il modo in cui lo spostamento dei processi
--   di dominio sulla coda tradirebbe la sua promessa: avremmo cambiato il
--   posto del silenzio, non tolto il silenzio.
--
-- ⚠️ I TEST 4..7 SONO LA META' CHE TIENE IL PRESIDIO LEGGIBILE.
--   Una vista che elenca tutto e' una vista che nessuno apre. Se i lavori
--   freschi, quelli annullati da una persona e quelli gia' guardati e
--   archiviati finissero qui dentro, la riga vera resterebbe in mezzo al
--   rumore — che e' il difetto da cui questo cantiere e' partito.
--
-- ⚠️ Le soglie: `run_after` (o `data_insert`) e `claimed_at` si scrivono a
--   mano, indietro nel tempo. Non si aspetta un'ora e non si finge con
--   `pg_sleep`: la soglia e' una regola sul dato, e si prova sul dato.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- Fixture: i sette casi, uno per riga
-- ============================================================
-- ⭐ Ogni riga porta in `payload` il proprio nome: le asserzioni interrogano il
--   presidio per NOME, non per posizione. Cosi' i lavori veri gia' presenti sul
--   database (al 2026-09-05 ce ne sono quattro in ERRORE) non falsano niente —
--   ne' in verde ne' in rosso.
DO $fixture$
DECLARE
    -- ⚠️ Il nome del caso viaggia nello SCOPE e non nel payload: la vista
    --   espone `scope` — chi ha chiesto il lavoro — e non `payload`. Un test
    --   che marcasse le righe in una colonna che il presidio non mostra non
    --   potrebbe interrogarle per nome.
    -- ⭐ Rev 2026-11-07 (giro 5 di brief-db-revisione-dbops): lo scope di chi e'
    --   in sessione, con la sua azienda. Un lavoro OPERATORE nasce dentro
    --   un'azienda (chk_coda_lavori_run_as_emittente), e la vista, letta da una
    --   persona, mostra il suo perimetro.
    v_scope jsonb := dbops.fn_pgtap_scope_operatore();
    v_emitt bigint := (dbops.fn_pgtap_scope_operatore() ->> 'emittente_attivo_id')::bigint;
BEGIN
    INSERT INTO dbops.coda_lavori
        (job_type, payload, run_as, scope, emittente_fiscale_id, origine, stato,
         tentativi, max_tentativi, run_after, claimed_at,
         archiviato, archiviato_il, archiviato_da)
    VALUES
        -- 1) si e' arreso
        ('CHIUSURA_SCADENZE', '{}'::jsonb,
         'OPERATORE', v_scope || jsonb_build_object('caso', 'errore'), v_emitt, 'CRON', 'ERRORE', 3, 3, NULL, NULL,
         false, NULL, NULL),
        -- 2) preso e mai chiuso: il worker e' morto a meta'
        ('CHIUSURA_SCADENZE', '{}'::jsonb,
         'OPERATORE', v_scope || jsonb_build_object('caso', 'in_corso_stantio'), v_emitt, 'CRON', 'IN_CORSO', 1, 3, NULL,
         now() - interval '3 hours', false, NULL, NULL),
        -- 3) ⛔ mai preso: nessuno sta drenando la coda
        ('CHIUSURA_SCADENZE', '{}'::jsonb,
         'OPERATORE', v_scope || jsonb_build_object('caso', 'pending_vecchio'), v_emitt, 'CRON', 'PENDING', 0, 3,
         now() - interval '3 hours', NULL, false, NULL, NULL),
        -- 4) appena accodato: e' normale
        ('CHIUSURA_SCADENZE', '{}'::jsonb,
         'OPERATORE', v_scope || jsonb_build_object('caso', 'pending_fresco'), v_emitt, 'CRON', 'PENDING', 0, 3, now(), NULL,
         false, NULL, NULL),
        -- 5) appena preso: sta lavorando
        ('CHIUSURA_SCADENZE', '{}'::jsonb,
         'OPERATORE', v_scope || jsonb_build_object('caso', 'in_corso_fresco'), v_emitt, 'CRON', 'IN_CORSO', 1, 3, NULL, now(),
         false, NULL, NULL),
        -- 6) qualcuno ha deciso di non farlo
        ('CHIUSURA_SCADENZE', '{}'::jsonb,
         'OPERATORE', v_scope || jsonb_build_object('caso', 'annullato'), v_emitt, 'CRON', 'ANNULLATO', 0, 3,
         now() - interval '3 hours', NULL, false, NULL, NULL),
        -- 7) fallito, ma gia' guardato e messo via
        ('CHIUSURA_SCADENZE', '{}'::jsonb,
         'OPERATORE', v_scope || jsonb_build_object('caso', 'archiviato'), v_emitt, 'CRON', 'ERRORE', 3, 3, NULL, NULL,
         true, now(), 'pgtap');
END
$fixture$;

-- ============================================================
-- 1..3. ⛔ I tre guasti, e i tre motivi
-- ============================================================
-- Non basta «compare»: tre guasti diversi vogliono tre gesti diversi, e un
-- motivo sbagliato manda la persona a cercare dalla parte opposta.
SELECT is(
    (SELECT motivo FROM dbops.vw_coda_lavori_da_guardare
      WHERE scope->>'caso' = 'errore'),
    'fallito: tentativi esauriti',
    '1. il lavoro fallito compare, e il motivo lo dice'
);

SELECT is(
    (SELECT motivo FROM dbops.vw_coda_lavori_da_guardare
      WHERE scope->>'caso' = 'in_corso_stantio'),
    'preso e mai chiuso: il worker e'' morto a meta''',
    '2. IN_CORSO da oltre un''ora compare: il worker e'' morto a meta'''
);

-- ⭐ Il caso che conta di piu' e si vede di meno.
SELECT is(
    (SELECT motivo FROM dbops.vw_coda_lavori_da_guardare
      WHERE scope->>'caso' = 'pending_vecchio'),
    'mai preso: il worker non sta girando',
    '3. PENDING da oltre un''ora compare: il worker non sta girando'
);

-- ============================================================
-- 4..7. ✅ Cio' che NON deve comparire
-- ============================================================
SELECT is_empty(
    $$SELECT id FROM dbops.vw_coda_lavori_da_guardare
       WHERE scope->>'caso' = 'pending_fresco'$$,
    '4. un lavoro appena accodato non compare: la soglia esiste davvero'
);

SELECT is_empty(
    $$SELECT id FROM dbops.vw_coda_lavori_da_guardare
       WHERE scope->>'caso' = 'in_corso_fresco'$$,
    '5. un lavoro appena preso non compare: sta lavorando'
);

SELECT is_empty(
    $$SELECT id FROM dbops.vw_coda_lavori_da_guardare
       WHERE scope->>'caso' = 'annullato'$$,
    '6. un lavoro ANNULLATO non compare: qualcuno l''ha deciso'
);

-- ⚠️ Ed e' l'archiviazione a dare al presidio il modo di TORNARE vuoto: senza,
--   una riga guardata e risolta resterebbe li' per sempre, e la lista
--   smetterebbe di essere una lista di cose da fare.
SELECT is_empty(
    $$SELECT id FROM dbops.vw_coda_lavori_da_guardare
       WHERE scope->>'caso' = 'archiviato'$$,
    '7. un lavoro archiviato non compare: qualcuno l''ha gia'' guardato'
);

SELECT * FROM finish();

ROLLBACK;
