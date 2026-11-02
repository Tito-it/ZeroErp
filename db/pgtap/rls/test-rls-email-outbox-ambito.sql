-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: config.email_outbox — la policy `rls_email_outbox_ambito`
-- ChangeSet: 20260905-32 · Decisione:
--   brief-db-processi-automatici-identita-e-perimetro §12.15
--
-- Elenco test (plan 3):
--  1) la policy esiste sulla tabella
--  2) e' PERMISSIVE e FOR ALL, come la famiglia
--  3) ⭐ il ramo si sceglie su `ambito` e NON su `emittente_fiscale_id IS NULL`
--
-- ⛔ 2026-09-05, rev: i test 4 e 5 SONO STATI TOLTI, non dimenticati.
--   Chiedevano che la policy nominasse `send_pending_emails` e che quel processo
--   avesse un'identita' tecnica. Il changeSet `20260905-33` ha RITIRATO quel
--   ramo: era sulla tabella sbagliata — il processo legge `config.email_log`, e
--   l'outbox non la apre mai, ne' inviando una bozza ne' ritentando.
--   ⇒ Le due asserzioni si spostano sul file della policy di `email_log`, quando
--     esistera'. Tenerle qui vorrebbe dire presidiare una cosa che non c'e'.
--   ⭐ E il rischio che il test 4 copriva — il codice del processo rinominato
--     senza toccare la regola — resta coperto: `send_pending_emails` e' un
--     letterale anche in `db/pgtap/script/test-fn-scope-identita-processo.sql`,
--     dove una rinomina fa fallire il test 2.
--
-- ⚠️ Rev 2026-09-25 — IL BLOCCO QUI SOTTO E' SUPERATO, e resta come storia.
--   La RLS sull'outbox e' ACCESA (20260905-37), e dal 20260925-67 la policy
--   distingue REPARTO e OPERATORE (script.fn_scope_email_ambito). Il collaudo
--   FUNZIONALE che il blocco chiedeva esiste: e'
--   db/pgtap/rls/test-rls-email-ambito-reparto-operatore.sql (A non vede, non
--   modifica e non «regala» la bozza di B). Questo file resta sulla FORMA.
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ CHE COSA QUESTO FILE NON PROVA, E VA DETTO.
--   La `ROW LEVEL SECURITY` su `config.email_outbox` e' SPENTA di proposito
--   (§12.15: l'API scrive `ambito = 'SISTEMA'` per default, quindi accenderla
--   romperebbe le bozze). ⇒ Un collaudo FUNZIONALE — «l'operatore A non vede la
--   riga di B» — qui non e' possibile: la policy non filtra niente finche'
--   qualcuno non fa l'`ALTER TABLE`.
--   ⭐ Quello che si puo' collaudare, e che serve davvero, e' la FORMA della
--     decisione di sicurezza: quale colonna sceglie il ramo, e chi viene
--     nominato. Sono le due cose che, sbagliate, si scoprirebbero il giorno
--     dell'accensione — cioe' troppo tardi.
--
-- ⛔ E NON si asserisce che la RLS e' spenta. Sarebbe fissare un DEBITO come
--   invariante: il test diventerebbe rosso il giorno in cui il lavoro riesce.
--   Lo stato lo dichiara il presidio (`dbops.vw_processi_dominio_senza_difesa`),
--   che e' fatto per arrivare a zero.
--
-- ⚠️ Quando la RLS verra' accesa, questo file va affiancato da un collaudo
--   funzionale della famiglia (vedi `test-rls-listini-ef-whitelist-write.sql`),
--   non sostituito: le due domande restano diverse.
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: qui non serve (la RLS sulla tabella e' spenta), ma il
-- preambolo e' presidiato e la riga non costa niente.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

-- ============================================================
-- 1. La policy c'e'
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM pg_policy
      WHERE polrelid = 'config.email_outbox'::regclass
        AND polname  = 'rls_email_outbox_ambito'),
    1,
    '1. la policy rls_email_outbox_ambito esiste su config.email_outbox'
);

-- ============================================================
-- 2. PERMISSIVE e FOR ALL, come la famiglia
-- ============================================================
-- ⚠️ `FOR SELECT` sarebbe attivamente sbagliata: e' deny-all in scrittura, e
--   `INSERT ... RETURNING` passa comunque dalla `USING`.
SELECT is(
    (SELECT polpermissive::text || '/' || polcmd::text
       FROM pg_policy
      WHERE polrelid = 'config.email_outbox'::regclass
        AND polname  = 'rls_email_outbox_ambito'),
    'true/*',
    '2. la policy e'' PERMISSIVE e FOR ALL'
);

-- ============================================================
-- 3. ⭐ Il ramo si sceglie sull'ETICHETTA, non sulla colonna nulla
-- ============================================================
-- ⛔ E' LA DECISIONE DI SICUREZZA, non uno stile. `chk_email_outbox_ambito_emittente`
--   permette a una riga `SISTEMA` di AVERE un emittente — una mail di reset
--   «marchiata». Scegliendo il ramo su `emittente_fiscale_id IS NULL`, quella
--   riga finirebbe nella whitelist dell'azienda: un operatore leggerebbe un link
--   di reset password.
-- ⚠️ Il perimetro di questo presidio e' UNA policy, quella nominata qui: non
--   dice niente sulle altre.
SELECT ok(
    (SELECT pg_get_expr(polqual, polrelid) LIKE '%ambito%'
        AND pg_get_expr(polqual, polrelid) NOT LIKE '%emittente_fiscale_id IS NULL%'
       FROM pg_policy
      WHERE polrelid = 'config.email_outbox'::regclass
        AND polname  = 'rls_email_outbox_ambito'),
    '3. il ramo si sceglie su `ambito`, non su `emittente_fiscale_id IS NULL`'
);

SELECT * FROM finish();
ROLLBACK;
