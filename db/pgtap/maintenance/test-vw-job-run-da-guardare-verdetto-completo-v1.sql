-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: la fixture scrive su maintenance.job_run_log (lo scrivono
--   solo i job e le porte DEFINER del backend) e su dbops.processi (catalogo del
--   migratore). Il ruolo applicativo li legge.
--
-- Test: maintenance.vw_job_run_da_guardare — il verde di un verdetto completo
--   spegne la spia, salvo ricaduta
-- ChangeSet: 00_schema/dbops/20261018-01 · 20_code/maintenance/20261018-02
--   · 80_data/20260904-13 (colonna nel mirror)
-- Brief: brief-db-intermittente-e-verdetto-completo (§4.2, §4.4, §6)
--
-- Elenco test (plan 17):
--  1) la colonna e' NOT NULL
--  2) e nasce false: chi non dichiara resta com'era
--  3) lo smoke notturno, il caso che ha aperto il brief, e' dichiarato verdetto completo
--  4) ⭐ rosso → verde: il verdetto completo ESCE
--  5) rosso → verde: l'altro resta, intermittente, con un rosso
--  6) ⭐ rosso → in corso (D2): il verdetto completo resta FALLITA, sull'ultima chiusa
--  7) rosso → in corso: l'altro e' «in corso adesso … intermittente», come prima
--  8) verde → in corso: nessuno dei due
--  9) rosso → in corso da tre ore: tutti e due «presa e mai chiusa»
-- 10) verde → rosso: tutti e due FALLITA
-- 11) ⭐ rosso → verde → rosso → verde: il verdetto completo resta, RICADUTO (instabile)
-- 12) rosso → verde → rosso → verde: l'altro resta, intermittente
-- 13) ⭐ due rossi di fila e poi verdi: UN tratto, il verdetto completo esce
--     (conta i tratti, non i rossi)
-- 14) un tratto fuori dalla finestra e uno dentro: il verdetto completo esce
-- 15) stessa storia: l'altro resta (un rosso negli ultimi sette giorni)
-- 16) falliti_ultimi_7_giorni resta per tutti: la ricaduta ne ha due
-- 17) la causa della ricaduta si legge dall'ultimo rosso
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ I CASI SI COSTRUISCONO, non si pescano dal giornale (regola zero,
--   corollario sui test): due processi di prova con la stessa storia di corse,
--   uno a corsa_verdetto_completo = true e uno a false. Il confronto e' fra i
--   due, cosi' ogni caso dice anche che per i processi a false niente e' cambiato.
-- ⚠️ IL CASO «LAVORO SENZA PROCESSO A CATALOGO» (§6.6 del brief) NON E'
--   COSTRUIBILE: chk_job_run_log_processo_dichiarato (NOT VALID) vieta a una corsa
--   nuova di nascere senza processo. La vista lo tratta come false
--   (COALESCE(pr.corsa_verdetto_completo, false) sotto un LEFT JOIN): e' il
--   comportamento di prima, e lo presidiano i pgTAP che c'erano
--   (test-vw-job-run-da-guardare, -causa-v1), che non dichiarano la colonna.
-- ⚠️ Il test 3 legge una riga di CATALOGO (seed di 80_data/sql/dbops/processi.csv),
--   non il giornale: e' contratto, non popolazione.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- ============================================================
-- Fixture
-- ============================================================
-- Due processi uguali tranne la colonna in esame. CODA: niente sveglia, quindi
-- niente colonne di accensione.
INSERT INTO dbops.processi
    (id, codice, descrizione, classe, canale, causa_fallimento, corsa_verdetto_completo)
VALUES (9971, 'PGTAP-VC-COMPLETO', 'prova verdetto completo', 'MANUTENZIONE', 'CODA', 'PROGRAMMA', true),
       (9972, 'PGTAP-VC-PARZIALE', 'prova verdetto parziale', 'MANUTENZIONE', 'CODA', 'PROGRAMMA', false);

-- Una corsa: p_ok NULL = in corso (aperta, senza fine). Chiusa un minuto dopo
-- l'avvio. Torna l'id, per i test che dicono da quale corsa la vista ha letto.
CREATE FUNCTION pg_temp.corsa(p_job text, p_proc text, p_fa interval, p_ok boolean)
RETURNS bigint
LANGUAGE sql
AS $$
    INSERT INTO maintenance.job_run_log
        (jobname, stepname, processo_codice, origine, started_at, ended_at, ok, message, error_code)
    VALUES (p_job, 's', p_proc, 'PGAGENT', now() - p_fa,
            CASE WHEN p_ok IS NOT NULL THEN now() - p_fa + interval '1 minute' END,
            p_ok,
            CASE p_ok WHEN true THEN 'done' WHEN false THEN 'rotto' END,
            CASE WHEN p_ok IS FALSE THEN 'PGTAP_VC_ROTTO' END)
    RETURNING id
$$;

-- La stessa storia per tutti e due i processi: il jobname e' <caso>-SI (verdetto
-- completo) e <caso>-NO. Le corse, dalla piu' vecchia, come (fa quanto, esito).
CREATE TEMP TABLE _t_storie (caso text, ordine int, fa interval, ok boolean);
INSERT INTO _t_storie VALUES
    -- 4-5) rosso → verde
    ('ROSSO-VERDE',       1, '1 day',      false),
    ('ROSSO-VERDE',       2, '5 minutes',  true),
    -- 6-7) rosso → in corso da cinque minuti
    ('ROSSO-INCORSO',     1, '1 day',      false),
    ('ROSSO-INCORSO',     2, '5 minutes',  NULL),
    -- 8) verde → in corso
    ('VERDE-INCORSO',     1, '1 day',      true),
    ('VERDE-INCORSO',     2, '5 minutes',  NULL),
    -- 9) rosso → in corso da tre ore: appesa
    ('ROSSO-APPESA',      1, '1 day',      false),
    ('ROSSO-APPESA',      2, '3 hours',    NULL),
    -- 10) verde → rosso
    ('VERDE-ROSSO',       1, '1 day',      true),
    ('VERDE-ROSSO',       2, '5 minutes',  false),
    -- 11-12, 16-17) rosso → verde → rosso → verde: ricaduto
    ('RICADUTA',          1, '4 days',     false),
    ('RICADUTA',          2, '3 days',     true),
    ('RICADUTA',          3, '2 days',     false),
    ('RICADUTA',          4, '1 day',      true),
    -- 13) due rossi di fila, poi verdi: un tratto solo
    ('UN-TRATTO',         1, '4 days',     true),
    ('UN-TRATTO',         2, '3 days',     false),
    ('UN-TRATTO',         3, '2 days',     false),
    ('UN-TRATTO',         4, '1 day',      true),
    ('UN-TRATTO',         5, '5 minutes',  true),
    -- 14-15) un tratto rosso fuori dalla finestra, uno dentro
    ('TRATTO-VECCHIO',    1, '10 days',    false),
    ('TRATTO-VECCHIO',    2, '9 days',     true),
    ('TRATTO-VECCHIO',    3, '2 days',     false),
    ('TRATTO-VECCHIO',    4, '1 day',      true);

CREATE TEMP TABLE _t_corse (jobname text, caso text, ordine int, ok boolean, id bigint);
INSERT INTO _t_corse
SELECT s.caso || '-' || v.suffisso, s.caso, s.ordine, s.ok,
       pg_temp.corsa('PGTAP-VC-' || s.caso || '-' || v.suffisso, v.processo, s.fa, s.ok)
  FROM _t_storie s
 CROSS JOIN (VALUES ('SI', 'PGTAP-VC-COMPLETO'), ('NO', 'PGTAP-VC-PARZIALE')) v(suffisso, processo)
 ORDER BY s.caso, s.ordine, v.suffisso;

-- La riga della vista per un caso, o NULL se il job non c'e'.
CREATE FUNCTION pg_temp.motivo(p_job text)
RETURNS text
LANGUAGE sql
AS $$
    SELECT motivo FROM maintenance.vw_job_run_da_guardare WHERE jobname = 'PGTAP-VC-' || p_job
$$;

-- ============================================================
-- 1..3. La colonna e il catalogo
-- ============================================================
SELECT col_not_null('dbops', 'processi', 'corsa_verdetto_completo',
    '1. la colonna e'' NOT NULL');

SELECT col_default_is('dbops', 'processi', 'corsa_verdetto_completo', 'false',
    '2. e nasce false: chi non dichiara resta com''era');

SELECT is(
    (SELECT corsa_verdetto_completo FROM dbops.processi WHERE codice = 'smoke_notturno'),
    true,
    '3. lo smoke notturno e'' dichiarato verdetto completo'
);

-- ============================================================
-- 4..10. Le storie semplici, verdetto completo contro parziale
-- ============================================================
SELECT is(pg_temp.motivo('ROSSO-VERDE-SI'), NULL,
    '4. rosso → verde: il verdetto completo esce');

SELECT is(
    (SELECT motivo || ' | rossi=' || falliti_ultimi_7_giorni
       FROM maintenance.vw_job_run_da_guardare WHERE jobname = 'PGTAP-VC-ROSSO-VERDE-NO'),
    'ultima corsa OK, ma ha fallito di recente: intermittente | rossi=1',
    '5. rosso → verde: l''altro resta, intermittente');

-- ⭐ D2: il giro nuovo non ha ancora detto niente. La riga e' quella del rosso.
SELECT is(
    (SELECT v.motivo || ' | ' || (v.job_run_id = c.id)::text
       FROM maintenance.vw_job_run_da_guardare v
       JOIN _t_corse c ON 'PGTAP-VC-' || c.jobname = v.jobname AND c.ordine = 1
      WHERE v.jobname = 'PGTAP-VC-ROSSO-INCORSO-SI'),
    'l''ultima corsa e'' FALLITA | true',
    '6. rosso → in corso: il verdetto completo resta FALLITA, sull''ultima corsa chiusa');

SELECT is(pg_temp.motivo('ROSSO-INCORSO-NO'),
    'in corso adesso, ma ha fallito di recente: intermittente',
    '7. rosso → in corso: l''altro come prima');

SELECT is(
    (SELECT count(*) FROM maintenance.vw_job_run_da_guardare
      WHERE jobname IN ('PGTAP-VC-VERDE-INCORSO-SI', 'PGTAP-VC-VERDE-INCORSO-NO')),
    0::bigint,
    '8. verde → in corso: nessuno dei due');

SELECT results_eq(
    $$SELECT motivo FROM maintenance.vw_job_run_da_guardare
       WHERE jobname IN ('PGTAP-VC-ROSSO-APPESA-SI', 'PGTAP-VC-ROSSO-APPESA-NO')
       ORDER BY jobname$$,
    $$VALUES ('presa e mai chiusa: il job e'' morto senza dire niente'::text),
             ('presa e mai chiusa: il job e'' morto senza dire niente'::text)$$,
    '9. rosso → in corso da tre ore: tutti e due «presa e mai chiusa»');

SELECT results_eq(
    $$SELECT motivo FROM maintenance.vw_job_run_da_guardare
       WHERE jobname IN ('PGTAP-VC-VERDE-ROSSO-SI', 'PGTAP-VC-VERDE-ROSSO-NO')
       ORDER BY jobname$$,
    $$VALUES ('l''ultima corsa e'' FALLITA'::text), ('l''ultima corsa e'' FALLITA'::text)$$,
    '10. verde → rosso: tutti e due FALLITA');

-- ============================================================
-- 11..15. ⭐ Rientro contro ricaduta
-- ============================================================
SELECT is(pg_temp.motivo('RICADUTA-SI'),
    'ultima corsa OK, ma e'' ricaduto dopo essere tornato verde: instabile',
    '11. rosso → verde → rosso → verde: il verdetto completo resta, ricaduto');

SELECT is(pg_temp.motivo('RICADUTA-NO'),
    'ultima corsa OK, ma ha fallito di recente: intermittente',
    '12. rosso → verde → rosso → verde: l''altro resta, intermittente');

-- ⛔ Contare i rossi direbbe «due», e lo terrebbe dentro: e' un tratto solo.
SELECT is(pg_temp.motivo('UN-TRATTO-SI'), NULL,
    '13. due rossi di fila e poi verdi: un tratto, il verdetto completo esce');

SELECT is(pg_temp.motivo('TRATTO-VECCHIO-SI'), NULL,
    '14. un tratto fuori dalla finestra e uno dentro: il verdetto completo esce');

SELECT is(pg_temp.motivo('TRATTO-VECCHIO-NO'),
    'ultima corsa OK, ma ha fallito di recente: intermittente',
    '15. stessa storia: l''altro resta');

-- ============================================================
-- 16..17. Le colonne che non cambiano
-- ============================================================
SELECT is(
    (SELECT falliti_ultimi_7_giorni FROM maintenance.vw_job_run_da_guardare
      WHERE jobname = 'PGTAP-VC-RICADUTA-SI'),
    2::bigint,
    '16. falliti_ultimi_7_giorni resta per tutti: la ricaduta ne ha due');

SELECT is(
    (SELECT v.ultimo_rosso_job_run_id = c.id
       FROM maintenance.vw_job_run_da_guardare v
       JOIN _t_corse c ON 'PGTAP-VC-' || c.jobname = v.jobname AND c.ordine = 3
      WHERE v.jobname = 'PGTAP-VC-RICADUTA-SI'),
    true,
    '17. la causa della ricaduta si legge dall''ultimo rosso');

SELECT * FROM finish();

ROLLBACK;
