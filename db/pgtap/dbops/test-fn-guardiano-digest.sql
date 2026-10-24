-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: per costruire «il digest e' MUTO» il test deve
--   scrivere e retrodatare righe di maintenance.job_run_log, e per provare
--   il verso «tipo acceso» deve cambiare dbops.coda_lavori_tipi.attivo — un
--   catalogo che a runtime non scrive nessuno. Scritture che il ruolo
--   applicativo non fa e non deve fare; il ROLLBACK le annulla. Stessa
--   motivazione di test-vw-processi-programmazione.sql.
--
-- Test: dbops.fn_guardiano_digest — chi guarda il guardiano
-- ChangeSet: 20260911-15 / -16 / -17 · seed processi.csv (guardiano_digest)
--            · seed coda_lavori_tipi.csv (NOTIFICA_DIGEST_MUTO)
-- Brief: brief-db-quattro-processi-senza-presidio §6 · §10.2
--
-- Elenco test (plan 9):
--  1) ⭐ il guardiano e' a catalogo come PGAGENT, col jobname uguale al codice
--  2) ✅ digest vivo: il guardiano torna DIGEST_OK e (2-bis) non accoda niente
--  3) ⛔ digest MUTO col tipo SPENTO: il guardiano SOLLEVA (ho visto e non ho
--     potuto dirlo), non tace
--  4) ⭐ digest MUTO col tipo acceso: ACCODA — e (4-bis) SISTEMA, senza scope,
--     con la chiave del giorno e il payload che dice da quanto
--  5) ⭐ un'ora dopo: GIA_NOTIFICATO_OGGI — una notifica al giorno, non una
--     all'ora, anche se il lavoro e' gia' FATTO
--  6) ✅ digest tornato vivo: DIGEST_OK — il guardiano non ha memoria
--  7) ⛔ digest tolto dal catalogo: il guardiano solleva, non torna un esito
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 3 E' QUELLO CHE TIENE ONESTO IL GUARDIANO.
--   Finche' il backend non ha l'handler, il tipo e' attivo = false. Un
--   guardiano che in quel caso tornasse «ok» silenzioso sarebbe un presidio
--   che tace proprio quando serve. Solleva: la corsa e' rossa nel giornale, e
--   nel pannello si legge «il guardiano ha visto e non ha potuto dirlo».
--
-- ⭐ IL TEST 5 E' LA RAGIONE DELLA CHIAVE PER GIORNO.
--   fn_accoda_lavoro dedupe solo fra PENDING/IN_CORSO: un lavoro gia' FATTO
--   non fermerebbe il successivo. Il guardiano controlla la chiave in
--   qualunque stato, e il test lo prova marcando il lavoro FATTO prima della
--   seconda chiamata.
--
-- ⚠️ Il digest si rende MUTO retrodatando le sue corse, e vivo con una corsa
--   fresca: su un database ricostruito da zero non ha corse (MAI_PARTITO), e
--   il test gliene DA' una prima di retrodatarla. Il caso si costruisce.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- 1. ⭐ Il guardiano e' un processo come gli altri
-- ============================================================
-- Passando dal giornale con jobname = codice, il panorama lo guarda: il
-- digest riporta il guardiano, il guardiano accoda per il digest.
SELECT is(
    (SELECT canale || '/' || classe || '/' || coalesce(jobname_pgagent, 'NULL')
       FROM dbops.processi WHERE codice = 'guardiano_digest'),
    'PGAGENT/MANUTENZIONE/guardiano_digest',
    '1. guardiano_digest e'' a catalogo: PGAGENT, MANUTENZIONE, jobname = codice'
);

-- ============================================================
-- Fixture: il digest ha una corsa FRESCA (anche su un DB da zero)
-- ============================================================
-- ⚠️ Prima si tolgono le corse vere del digest (in transazione): cosi' lo
--   stato lo decide la fixture e non il giorno in cui gira il test.
DELETE FROM maintenance.job_run_log
 WHERE processo_codice = 'digest_presidi' OR jobname LIKE 'digest_presidi%';
INSERT INTO maintenance.job_run_log
    (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message)
VALUES ('digest_presidi:giornaliera', 'giornaliera', 'digest_presidi', 'CRON',
        now() - interval '1 hour', now() - interval '1 hour', true, 'pgtap');

-- Il tipo parte SPENTO, com'e' nel seed finche' il backend non ha l'handler.
UPDATE dbops.coda_lavori_tipi SET attivo = false WHERE codice = 'NOTIFICA_DIGEST_MUTO';

-- ============================================================
-- 2. ✅ Digest vivo
-- ============================================================
SELECT is(
    dbops.fn_guardiano_digest(),
    'DIGEST_OK',
    '2. col digest vivo il guardiano torna DIGEST_OK'
);

SELECT is_empty(
    $$SELECT id FROM dbops.coda_lavori WHERE job_type = 'NOTIFICA_DIGEST_MUTO'$$,
    '2-bis. e non accoda niente'
);

-- ============================================================
-- 3. ⛔ Digest MUTO, tipo spento: si SOLLEVA
-- ============================================================
UPDATE maintenance.job_run_log
   SET started_at = started_at - interval '30 days',
       ended_at   = ended_at   - interval '30 days'
 WHERE processo_codice = 'digest_presidi';

-- ⚠️ Non basta il solo SQLSTATE: si chiede la frase, che nomina il tipo.
SELECT throws_like(
    $$SELECT dbops.fn_guardiano_digest()$$,
    '%NOTIFICA_DIGEST_MUTO%',
    '3. digest MUTO e tipo spento: il guardiano SOLLEVA (E_JOB_TYPE_NON_ATTIVO), non tace'
);

-- ============================================================
-- 4. ⭐ Tipo acceso: accoda, con la forma giusta
-- ============================================================
UPDATE dbops.coda_lavori_tipi SET attivo = true WHERE codice = 'NOTIFICA_DIGEST_MUTO';

SELECT alike(
    dbops.fn_guardiano_digest(),
    'ACCODATO:%',
    '4. digest MUTO e tipo acceso: il guardiano accoda'
);

-- ⭐ SISTEMA senza scope (non e' un lavoro di dominio), chiave del giorno, e
--   nel payload il processo e da quanto tace — cio' che serve all'handler per
--   comporre la mail senza rileggere niente.
SELECT is(
    (SELECT run_as || '/' || coalesce(scope::text, 'NULL') || '/' || idempotency_key
            || '/' || (payload ? 'muto_da')::text
            || '/' || (payload ->> 'processo_codice')
       FROM dbops.coda_lavori
      WHERE job_type = 'NOTIFICA_DIGEST_MUTO'
      ORDER BY id DESC LIMIT 1),
    'SISTEMA/NULL/guardiano_digest:' || script.fn_data_operativa()::text || '/true/digest_presidi',
    '4-bis. il lavoro e'' SISTEMA senza scope, con la chiave del giorno e il payload che dice chi e da quanto'
);

-- ============================================================
-- 5. ⭐ Una notifica al giorno
-- ============================================================
-- Il lavoro viene eseguito (FATTO): fn_accoda_lavoro non lo vedrebbe piu' come
-- doppione. Il guardiano si'.
UPDATE dbops.coda_lavori SET stato = 'FATTO', ended_at = now()
 WHERE job_type = 'NOTIFICA_DIGEST_MUTO';

SELECT is(
    dbops.fn_guardiano_digest(),
    'GIA_NOTIFICATO_OGGI',
    '5. stesso giorno, lavoro gia'' FATTO: GIA_NOTIFICATO_OGGI — una notifica al giorno'
);

-- ============================================================
-- 6. ✅ Il digest torna vivo
-- ============================================================
INSERT INTO maintenance.job_run_log
    (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message)
VALUES ('digest_presidi:giornaliera', 'giornaliera', 'digest_presidi', 'CRON',
        now(), now(), true, 'pgtap');

SELECT is(
    dbops.fn_guardiano_digest(),
    'DIGEST_OK',
    '6. una corsa fresca e il guardiano torna DIGEST_OK: non ha memoria'
);

-- ============================================================
-- 7. ⛔ Senza il digest a catalogo, il guardiano non dorme: solleva
-- ============================================================
-- ⚠️ obsoleto_dal e non attivo = false: il panorama filtra su entrambi, e il
--   primo non sveglia nessun guard di disattivazione con figlie.
-- ⚠️ 20261016-20: un processo ritirato non ha sveglia, e chk_processi_accensione
--   vuole le colonne dell'accensione a NULL (quattro dal 20261018-10).
UPDATE dbops.processi
   SET obsoleto_dal         = script.fn_data_operativa() - 1,
       acceso_in_sviluppo   = NULL,
       acceso_in_produzione = NULL,
       spegnibile           = NULL,
       accendibile_in_produzione = NULL
 WHERE codice = 'digest_presidi';

SELECT throws_like(
    $$SELECT dbops.fn_guardiano_digest()$$,
    '%digest_presidi%',
    '7. digest tolto dal catalogo: il guardiano solleva E_CONFIG_MANCANTE, non torna un esito'
);

SELECT * FROM finish();

ROLLBACK;
