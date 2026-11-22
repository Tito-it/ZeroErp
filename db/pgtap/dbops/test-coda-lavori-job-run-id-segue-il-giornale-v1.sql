-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive su dbops.processi e su
--   maintenance.job_run_log, che a runtime scrivono solo il seed, i job e le
--   funzioni del giornale; la potatura e il DELETE sul giornale l'applicazione
--   non li puo' fare. Per mostrare che l'azione della FK non subisce la RLS,
--   la transazione accende FORCE ROW LEVEL SECURITY su dbops.coda_lavori, che
--   solo il proprietario puo' dare e che il ROLLBACK spegne.
--
-- Test: dbops.coda_lavori.job_run_id segue il giornale delle corse
--   fk_coda_lavori_job_run_log, ON DELETE SET NULL verso maintenance.job_run_log
-- ChangeSet: 20261122-33 · Brief: brief-db-giornale-corse-indici §9.2, §10
--
-- Elenco test (plan 11):
--  1) ✅ la FK c'e', verso maintenance.job_run_log(id), ON DELETE SET NULL,
--     convalidata (nessun job_run_id senza corsa, pregresso compreso)
--  2) ✅ la policy degli indici la decide CON_INDICE, parziale (seed)
--  3) ✅ l'indice parziale c'e' (lo crea apply_fk_index_policy in 90_end)
--  4) ⛔ un job_run_id che non porta a nessuna corsa e' respinto (23503)
--  5) ✅ la RLS e' armata: in sessione si vede solo il lavoro di IO
--  6) ✅ la potatura cancella la corsa vecchia (la fixture e' quella giusta)
--  7) ⭐ il lavoro dell'azienda in sessione perde il riferimento
--  8) ⭐ il lavoro di un'altra azienda, invisibile in sessione (test 5), lo
--     perde lo stesso: l'azione della FK non subisce la RLS
--  9) ⭐ il lavoro archiviato lo perde e resta archiviato, con data e autore
--     dell'archiviazione e lo stato di prima
-- 10) ⭐ il lavoro della corsa tenuta dalla potatura (l'ultima della coppia)
--     tiene il riferimento
-- 11) ⭐ la regola e' la FK, non la potatura: un DELETE qualunque sul
--     giornale azzera il riferimento
--
-- ⚠️ Le corse e i lavori si COSTRUISCONO (regola zero, corollario sui test):
--   la soglia della prova e' 400 giorni fa, la corsa da potare sta a 550 e
--   quella tenuta a 540, della stessa coppia (processo, jobname). La potatura
--   gira su tutto il giornale, dentro la transazione che finisce in ROLLBACK:
--   le asserzioni guardano solo le righe della fixture.
-- ⚠️ Prima dell'apply di 90_end (apply_fk_index_policy) il test 3 e' rosso, e
--   prima del mirror del CSV lo e' il 2: e' il segnale giusto.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ── 1-3: la struttura ────────────────────────────────────────
SELECT is(
    (SELECT c.confrelid::regclass::text || '(' || a.attname || ')/' || c.confdeltype::text || '/' || c.convalidated::text
       FROM pg_constraint c
       JOIN pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = c.confkey[1]
      WHERE c.conrelid = 'dbops.coda_lavori'::regclass
        AND c.conname  = 'fk_coda_lavori_job_run_log'
        AND c.contype  = 'f'
        AND c.conkey   = ARRAY[(SELECT attnum FROM pg_attribute
                                 WHERE attrelid = 'dbops.coda_lavori'::regclass
                                   AND attname  = 'job_run_id')]),
    'maintenance.job_run_log(id)/n/true',
    'fk_coda_lavori_job_run_log: job_run_id verso maintenance.job_run_log(id), ON DELETE SET NULL, convalidata'
);

SELECT is(
    (SELECT decisione || ' | ' || dll_command
       FROM dbops.fk_index_policy
      WHERE schema_name = 'dbops' AND table_name = 'coda_lavori'
        AND constraint_name = 'fk_coda_lavori_job_run_log'),
    'CON_INDICE | CREATE INDEX IF NOT EXISTS ix_coda_lavori_job_run_id ON dbops.coda_lavori(job_run_id) WHERE job_run_id IS NOT NULL;',
    'la policy degli indici decide la FK CON_INDICE, con l''indice parziale (seed)'
);

SELECT ok(
    EXISTS (SELECT 1 FROM pg_indexes
             WHERE schemaname = 'dbops' AND tablename = 'coda_lavori'
               AND indexname  = 'ix_coda_lavori_job_run_id'
               AND indexdef ~ '\(job_run_id\) WHERE \(job_run_id IS NOT NULL\)$'),
    'l''indice parziale ix_coda_lavori_job_run_id c''e'': ogni corsa cancellata trova i suoi lavori'
);

-- ── Fixture ─────────────────────────────────────────────────
CREATE TEMP TABLE _mondi ON COMMIT DROP AS
SELECT 'IO'    AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRO' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

INSERT INTO dbops.processi (id, codice, descrizione, classe, canale, causa_fallimento)
VALUES (9981, 'PGTAP-CODA-CORSA', 'prova: il lavoro segue la corsa', 'MANUTENZIONE', 'CODA', 'PROGRAMMA');

-- Due corse vecchie della stessa coppia: la prima si pota, la seconda e'
-- l'ultima di tutto e resta.
CREATE TEMP TABLE _corse ON COMMIT DROP AS
WITH ins AS (
    INSERT INTO maintenance.job_run_log
        (jobname, processo_codice, origine, started_at, ended_at, ok, saltata, message)
    VALUES
        ('PGTAP-CODA-CORSA', 'PGTAP-CODA-CORSA', 'COMMAND',
         now() - interval '550 days', now() - interval '550 days', true, false, 'da-potare'),
        ('PGTAP-CODA-CORSA', 'PGTAP-CODA-CORSA', 'COMMAND',
         now() - interval '540 days', now() - interval '540 days', true, false, 'tenuta')
    RETURNING id, message AS etichetta
)
SELECT * FROM ins;

CREATE FUNCTION pg_temp.corsa(p_etichetta text) RETURNS bigint LANGUAGE sql AS $f$
    SELECT id FROM _corse WHERE etichetta = p_etichetta
$f$;

-- I lavori, in ERRORE (nessuno e' vivo: non li prende nessun drenatore).
--   IO e ALTRO puntano alla corsa da potare; ALTRO e' anche archiviato.
--   SISTEMA punta alla corsa tenuta.
CREATE TEMP TABLE _lavori ON COMMIT DROP AS
WITH op AS (
    INSERT INTO dbops.coda_lavori
        (job_type, payload, run_as, scope, emittente_fiscale_id, origine, stato,
         tentativi, max_tentativi, job_run_id)
    SELECT 'CHIUSURA_SCADENZE', jsonb_build_object('pgtap', m.lato), 'OPERATORE',
           jsonb_build_object('auth_user_id', m.auth_user_id, 'username', 'pgtap',
                              'identita_id', m.identita_id,
                              'emittente_attivo_id', m.emittente_fiscale_id,
                              'emittente_ids', jsonb_build_array(m.emittente_fiscale_id)),
           m.emittente_fiscale_id, 'CRON', 'ERRORE', 1, 1, pg_temp.corsa('da-potare')
      FROM _mondi m
    RETURNING id, payload ->> 'pgtap' AS lato
), si AS (
    INSERT INTO dbops.coda_lavori
        (job_type, payload, run_as, scope, emittente_fiscale_id, origine, stato,
         tentativi, max_tentativi, job_run_id)
    VALUES ('NOTIFICA_DIGEST_MUTO', '{"pgtap": "SISTEMA"}'::jsonb, 'SISTEMA', NULL, NULL,
            'CRON', 'ERRORE', 1, 1, pg_temp.corsa('tenuta'))
    RETURNING id, 'SISTEMA'::text AS lato
)
SELECT * FROM op UNION ALL SELECT * FROM si;

UPDATE dbops.coda_lavori
   SET archiviato = true
 WHERE id = (SELECT id FROM _lavori WHERE lato = 'ALTRO');

-- L'archiviazione com'era prima della potatura: il test 9 la confronta.
CREATE TEMP TABLE _prima ON COMMIT DROP AS
SELECT c.id, c.stato, c.archiviato, c.archiviato_il, c.archiviato_da
  FROM dbops.coda_lavori c
 WHERE c.id = (SELECT id FROM _lavori WHERE lato = 'ALTRO');

CREATE FUNCTION pg_temp.corsa_del_lavoro(p_lato text) RETURNS bigint LANGUAGE sql AS $f$
    SELECT c.job_run_id FROM dbops.coda_lavori c
      JOIN _lavori l ON l.id = c.id
     WHERE l.lato = p_lato
$f$;

-- ── 4: lo scrittore ──────────────────────────────────────────
SELECT throws_ok(
    format($$UPDATE dbops.coda_lavori SET job_run_id = %s WHERE id = %s$$,
           (SELECT coalesce(max(id), 0) + 1000000 FROM maintenance.job_run_log),
           (SELECT id FROM _lavori WHERE lato = 'IO')),
    '23503',
    NULL,
    'un job_run_id che non porta a nessuna corsa e'' respinto'
);

-- ── 5-10: la potatura, con la RLS armata ─────────────────────
-- In sessione l'operatore di IO: con FORCE il proprietario subisce la policy,
-- e i lavori di ALTRO e SISTEMA gli sono invisibili.
ALTER TABLE dbops.coda_lavori FORCE ROW LEVEL SECURITY;
SELECT script.fn_pgtap_set_contesto_operatore(
           (SELECT m.auth_user_id::integer FROM _mondi m WHERE m.lato = 'IO'));

-- Senza questa, il test 7 sarebbe verde anche con la RLS spenta.
SELECT is(
    (SELECT string_agg(l.lato, ',' ORDER BY l.lato)
       FROM dbops.coda_lavori c JOIN _lavori l ON l.id = c.id),
    'IO',
    'la RLS e'' armata: in sessione si vede solo il lavoro di IO'
);

CREATE TEMP TABLE _esito ON COMMIT DROP AS
SELECT maintenance.fn_pota_giornale_corse(now() - interval '400 days') AS esito;

-- Le letture, fuori dalla policy.
ALTER TABLE dbops.coda_lavori NO FORCE ROW LEVEL SECURITY;

SELECT ok(
    NOT EXISTS (SELECT 1 FROM maintenance.job_run_log WHERE id = pg_temp.corsa('da-potare'))
    AND EXISTS (SELECT 1 FROM maintenance.job_run_log WHERE id = pg_temp.corsa('tenuta')),
    'la potatura cancella la corsa vecchia e tiene l''ultima della coppia'
);

SELECT ok(
    (SELECT c.job_run_id IS NULL FROM dbops.coda_lavori c
      WHERE c.id = (SELECT id FROM _lavori WHERE lato = 'IO')),
    'il lavoro dell''azienda in sessione perde il riferimento alla corsa potata'
);

SELECT ok(
    (SELECT c.job_run_id IS NULL FROM dbops.coda_lavori c
      WHERE c.id = (SELECT id FROM _lavori WHERE lato = 'ALTRO')),
    'il lavoro di un''altra azienda, invisibile con la RLS armata, lo perde lo stesso'
);

SELECT is(
    (SELECT row(c.stato, c.archiviato, c.archiviato_il, c.archiviato_da)::text
       FROM dbops.coda_lavori c
      WHERE c.id = (SELECT id FROM _lavori WHERE lato = 'ALTRO')),
    (SELECT row(p.stato, p.archiviato, p.archiviato_il, p.archiviato_da)::text FROM _prima p),
    'il lavoro archiviato resta archiviato, con stato, data e autore dell''archiviazione di prima'
);

SELECT is(
    pg_temp.corsa_del_lavoro('SISTEMA'),
    pg_temp.corsa('tenuta'),
    'il lavoro della corsa che la potatura tiene conserva il riferimento'
);

-- ── 11: la regola e' la FK ───────────────────────────────────
DELETE FROM maintenance.job_run_log WHERE id = pg_temp.corsa('tenuta');

SELECT ok(
    pg_temp.corsa_del_lavoro('SISTEMA') IS NULL,
    'un DELETE qualunque sul giornale azzera il riferimento: la regola e'' la FK, non la potatura'
);

SELECT * FROM finish();

ROLLBACK;
