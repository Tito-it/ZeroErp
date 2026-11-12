-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il registro dei processi e i jobname dei wrapper parlano la STESSA
--       lingua (DB-7)
-- Brief: brief-db-processi-automatici-residui-be.md, sezione DB-7 e §1-quater
-- pgtap-pgagent-owner: ammesso — pgagent solo in una query dinamica dopo has_schema_privilege: da app il test si salta
--
-- Elenco test (plan 4):
--  1) ⛔ IL PRESIDIO: ogni jobname passato da un wrapper esiste in dbops.processi
--  2) i quattro nomi del difetto storico sono a catalogo
--  3) i due nomi ritirati NON sono piu' a catalogo (o la rinomina e' a meta')
--  4) ⭐ i due job pgAgent nuovi esistono — ⚠️ e questo test e' CIECO in CI
--
-- ────────────────────────────────────────────────────────────────
-- ⛔ PERCHE' ESISTE, e perche' e' la parte che conta di tutto il lotto.
--
-- La fase 2 del cantiere prometteva che «i dodici job pgAgent si dichiarano da
-- soli, senza toccare 85_pgagent»: `maintenance.fn_run_and_log` deriva il
-- codice del processo dal jobname che riceve.
--
-- ⚠️ La precondizione era vera per OTTO su dodici, e nessuno l'aveva
--   verificata. Il registro e' stato seminato con i nomi dei **job pgAgent**,
--   mentre la funzione riceve il nome che le passano i **wrapper**
--   `maintenance.proc_*_job` — e i due insiemi non coincidevano:
--
--     il wrapper passava          il registro conteneva
--     apply_fk_index_policy       automations_apply_fk_indexes_policy
--     automations_cleanup         automations_cleanup_weekly
--     automations_lock_columns    — (niente)
--     automations_delete_block    — (niente)
--
--   Per quei nomi la derivazione non agganciava, l'attore restava NULL, e la
--   riga restava in `dbops.vw_run_senza_attore` PER SEMPRE.
--
-- ⭐ LA CORRETTIVA NON E' LA RINOMINA: E' QUESTO TEST. Rinominare ripara i
--   quattro casi di oggi; senza un presidio, il prossimo wrapper romperebbe la
--   stessa cosa in silenzio — che e' esattamente com'e' arrivata fin qui.
--
-- ⭐ E il perimetro NON e' un elenco scritto a mano: e' `proname LIKE
--   'proc_%_job'`. Un wrapper nuovo ci finisce dentro da solo, senza che
--   nessuno debba ricordarsi di aggiungerlo. Un presidio con l'elenco a mano ha
--   per perimetro quell'elenco, e invecchia il giorno dopo.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

-- ============================================================
-- 1. ⛔ IL PRESIDIO
-- ============================================================
-- ⚠️ Si legge il CODICE VIVO delle funzioni (`pg_proc.prosrc`), non un elenco:
--   e' l'unica fonte che dice davvero quale stringa arrivera' al giornale.
SELECT is_empty(
    $$SELECT p.proname || ' passa ''' ||
             (regexp_match(p.prosrc, 'p_jobname\s*:?=\s*''([^'']+)'''))[1] ||
             ''', che non e'' a catalogo'
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
       WHERE n.nspname = 'maintenance'
         AND p.proname LIKE 'proc\_%\_job'
         AND (regexp_match(p.prosrc, 'p_jobname\s*:?=\s*''([^'']+)'''))[1] IS NOT NULL
         AND NOT EXISTS (
                 SELECT 1 FROM dbops.processi pr
                  WHERE pr.codice =
                        (regexp_match(p.prosrc, 'p_jobname\s*:?=\s*''([^'']+)'''))[1])$$,
    '1. ogni jobname passato da un wrapper esiste in dbops.processi'
);

-- ============================================================
-- 2..3. La rinomina e' completa, in tutti e due i versi
-- ============================================================
-- Il verso «ci sono i nomi nuovi».
SELECT is(
    (SELECT count(*)::int FROM dbops.processi
      WHERE codice IN ('apply_fk_index_policy', 'automations_cleanup',
                       'automations_lock_columns', 'automations_delete_block')),
    4,
    '2. i quattro nomi del difetto storico sono a catalogo'
);

-- ⭐ E il verso opposto, che da solo il test 2 non copre: una rinomina fatta a
--   meta' — riga nuova aggiunta, vecchia lasciata — produrrebbe DUE processi
--   per lo stesso lavoro, e il registro comincerebbe a contare doppio.
SELECT is_empty(
    $$SELECT codice FROM dbops.processi
       WHERE codice IN ('automations_apply_fk_indexes_policy',
                        'automations_cleanup_weekly')$$,
    '3. i nomi vecchi non sono rimasti accanto ai nuovi'
);

-- ============================================================
-- 4. ⚠️ I due job notturni — e il limite di questo test
-- ============================================================
-- ⛔ QUESTO TEST E' CIECO DOVE SERVIREBBE DI PIU', e va detto invece che
--   lasciarlo credere. `85_pgagent` in CI e' MARK_RAN: segnata come eseguita
--   SENZA essere eseguita. Su un database ricostruito da zero i due job non
--   esistono, e qui si vedrebbe solo uno skip — non un rosso.
--   ⇒ Il test serve su dbdev e in produzione, dove i job ci sono davvero.
--     Su un ambiente nuovo la verifica e' A MANO. Registrato come R-11.
-- ⛔ IL CANCELLO NON PUO' ESSERE UN `CASE`, e questa e' la parte che sorprende.
--   Un `CASE WHEN <non posso> THEN skip() ELSE <query su pgagent.pga_job> END`
--   fallisce lo stesso con «permesso negato»: PostgreSQL verifica i privilegi
--   quando ANALIZZA l'istruzione, non quando prende il ramo. Il solo fatto che
--   il nome compaia nel testo basta.
--   ⇒ Il riferimento vive dentro una query DINAMICA, che esiste solo se la si
--     esegue. E' l'unico modo perche' lo skip sia davvero uno skip.
DO $pgagent$
DECLARE
    v_n integer;
BEGIN
    IF NOT has_schema_privilege(current_user, 'pgagent', 'USAGE') THEN
        PERFORM set_config('pgtap.job_notturni', '', true);
        RETURN;
    END IF;

    EXECUTE $q$SELECT count(*)::int FROM pgagent.pga_job
                WHERE jobname IN ('automations_lock_columns',
                                  'automations_delete_block')
                  AND jobenabled$q$
       INTO v_n;

    PERFORM set_config('pgtap.job_notturni', v_n::text, true);
END
$pgagent$;

SELECT CASE
    WHEN NULLIF(current_setting('pgtap.job_notturni', true), '') IS NULL
        THEN skip('4. questa sessione non vede lo schema pgagent (il ruolo '
                  'applicativo non ha USAGE, e in CI la fase 85 e'' MARK_RAN): '
                  'la verifica dei due job e'' A MANO — R-11', 1)
    ELSE is(
        current_setting('pgtap.job_notturni')::int,
        2,
        '4. i due job notturni che mancavano alla famiglia esistono e sono attivi'
    )
END;

SELECT * FROM finish();

ROLLBACK;
