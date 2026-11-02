-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: le cause si COSTRUISCONO — processi seminati in
--   dbops.processi, corse scritte in maintenance.job_run_log e, dove
--   l'estensione c'e', job finti in pgagent.pga_job. Sono scritture che il
--   ruolo applicativo non fa e non deve fare; tutto in transazione, annullato.
--
-- Test: il presidio dei processi da' il testo della CAUSA di ogni riga
-- Brief: brief-db-presidio-processi-testo-per-causa.md §3 B
-- ChangeSet: 20261009-32 / -33 (modello delle varianti) · 20261009-34 / -35
--            (la causa nelle due viste) · 20261009-36 / -37 (il catalogo delle
--            cause, §5.5) · 80_data presidi.csv / presidi_cause.csv /
--            presidi_testi.csv · 20261014-54 (pgAgent: la corsa dovuta,
--            brief-db-statistiche-tabelle-job-notturno §8)
--
-- Elenco test (plan 18):
--  1) il censimento delle cause dalla definizione del panorama non e' vuoto
--  2) il catalogo dice che il presidio sceglie il testo dalla colonna `causa`
--  3) ⭐ COMPLETEZZA — ogni causa che il panorama puo' produrre e' nel
--     catalogo delle cause del presidio (dbops.presidi_cause, rev §5.5)
--  4) ⛔ RITIRO — nessuna causa a catalogo che il panorama non produce piu'
--  5) ⛔ ogni causa censita ha una COSTRUZIONE dichiarata in questo test
--  6..13) ⭐ ogni causa, costruita, esce dal presidio con lo stato e la causa
--     attesi: TIMER_FERMO, TIMER_NON_INSTALLATO, SERVIZIO_GIU,
--     NON_PROGRAMMATO, JOB_ASSENTE, JOB_SPENTO, JOB_MAI_PARTITO,
--     GIRA_E_NON_REGISTRA (gli ultimi tre solo dove pgAgent c'e' e si lascia
--     scrivere: altrove si DICHIARA con skip)
-- 14) ⛔ i tre stati sani (OK, FUORI_PORTATA, SU_RICHIESTA), costruiti, non
--     hanno causa e non sono da guardare
-- 15) ⛔ nel presidio nessuna riga e' senza causa
-- 16) ⭐ ogni causa che il panorama puo' produrre ha il suo testo italiano
-- 17) ⭐ rev 2026-10-14: PGAGENT che ha girato e la cui corsa dovuta e'
--     passata da piu' di un'ora: IN_RITARDO per JOB_IN_RITARDO — il demone
--     fermo, che prima restava OK per sempre (solo dove pgAgent c'e')
-- 18) ⛔ rev 2026-10-14: PGAGENT mai girato con la prima corsa ancora futura:
--     IN_ATTESA, senza causa, non da guardare — il falso allarme del 14-10 su
--     analyze_statistiche (solo dove pgAgent c'e')
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ IL TEST 3 NON DIPENDE DALLE RIGHE DI OGGI, E NEMMENO DA pgAGENT.
--   L'elenco delle cause si legge dalla DEFINIZIONE del panorama: ogni ramo
--   del CASE consegna la coppia ARRAY['<stato>', '<causa>'], e pg_get_viewdef
--   la stampa cosi'. Su un database ricostruito da zero (CI), dove non c'e'
--   nessun processo guasto e pgAgent manca, l'elenco e' lo stesso: il test
--   non passa a vuoto.
--   ⚠️ Il censimento dice che la parola c'e', non che la vista si comporta di
--   conseguenza: per questo i test 6..13 COSTRUISCONO ogni causa, e il 5
--   pretende che ogni causa censita abbia la sua costruzione. Una causa nuova
--   nel CASE fa rosso il 3 (finche' non ha il testo) e il 5 (finche' non ha la
--   costruzione), e il messaggio la NOMINA.
--   ⛔ Se il censimento smettesse di vedere le coppie (una riscrittura del CASE
--   in un'altra forma), il test 1 diventa rosso: e' quello che impedisce al 3
--   di essere verde per sottrazione.
--
-- ⛔ IL GENERICO NON E' IL RIPIEGO DI UNA CAUSA (brief §3 B.4): il test 3
--   cerca la riga con `variante = causa`, mai quella NULL.
--
-- ⚠️ I processi si SEMINANO: lo stato dei processi veri dipende dal giorno in
--   cui gira il test. Il soggetto si sceglie sulla struttura, non sul verdetto
--   di oggi (vedi test-vw-processi-programmazione, test 5).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(18);

-- ============================================================
-- Il censimento: le cause che il panorama puo' produrre
-- ============================================================
CREATE TEMP TABLE _t_cause ON COMMIT DROP AS
SELECT DISTINCT m[1] AS stato, m[2] AS causa
  FROM regexp_matches(
           pg_get_viewdef('dbops.vw_processi_programmazione'::regclass),
           'ARRAY\[''([A-Z_]+)''::text, ''([A-Z_]+)''::text\]', 'g') AS m;

-- ============================================================
-- 1) Il censimento non e' degradato
-- ============================================================
SELECT cmp_ok(
    (SELECT count(*) FROM _t_cause)::bigint,
    '>', 0::bigint,
    'test 1 — dalla definizione del panorama si leggono le coppie [stato, causa] (censimento non degradato)');

-- ============================================================
-- 2) Il catalogo dice da dove si legge la variante
-- ============================================================
-- ⚠️ Senza questa riga il backend non saprebbe che il presidio ha un testo
--   per causa, e mostrerebbe il generico — cioe' il difetto del 2026-10-09.
SELECT is(
    (SELECT colonna_variante FROM dbops.presidi
      WHERE vista = 'dbops.vw_processi_programmazione_da_guardare'),
    'causa',
    'test 2 — il presidio dei processi sceglie il testo dalla colonna `causa`');

-- ============================================================
-- 3) ⭐ Ogni causa della vista e' nel catalogo delle cause
-- ============================================================
-- ⭐ Rev 2026-10-09 (§5.5): la causa e' un'entita' con il suo «chi agisce»
--   (dbops.presidi_cause), e i testi le sono figli per FK. Che ogni causa a
--   catalogo abbia il testo `it` lo presidia dbops/test-presidi-testi-v1
--   (test 16), per tutti i presidi; qui si lega il catalogo alla VISTA.
SELECT is(
    coalesce((
        SELECT string_agg(c.causa, ', ' ORDER BY c.causa)
          FROM _t_cause c
         WHERE NOT EXISTS (
               SELECT 1 FROM dbops.presidi_cause k
                WHERE k.vista = 'dbops.vw_processi_programmazione_da_guardare'
                  AND k.causa = c.causa)), ''),
    '',
    'test 3 — ogni causa che il panorama puo'' produrre e'' nel catalogo delle cause, con chi la spegne');

-- ============================================================
-- 4) ⛔ Nessuna causa a catalogo che non esiste piu'
-- ============================================================
-- Il verso opposto del 3: una causa ritirata dal CASE lascerebbe a catalogo un
-- «chi agisce» e un testo che nessuno leggera' piu'.
SELECT is(
    coalesce((
        SELECT string_agg(k.causa, ', ' ORDER BY k.causa)
          FROM dbops.presidi_cause k
         WHERE k.vista = 'dbops.vw_processi_programmazione_da_guardare'
           AND k.causa NOT IN (SELECT causa FROM _t_cause)), ''),
    '',
    'test 4 — nessuna causa a catalogo che il panorama non produce');

-- ============================================================
-- Le costruzioni
-- ============================================================
-- ⭐ Una causa = una ricetta. Le ATTESE stanno qui, l'ELENCO viene dal
--   censimento: una causa nuova non ha una ricetta, e il test 5 la NOMINA
--   invece di lasciarla senza prova.
CREATE TEMP TABLE _t_ricette ON COMMIT DROP AS
SELECT *
  FROM (VALUES
        ('TIMER_FERMO',          'MUTO',                'PGTAP-CAUSA-TIMER-FERMO'),
        ('TIMER_NON_INSTALLATO', 'MAI_PARTITO',         'PGTAP-CAUSA-TIMER-MAI'),
        ('SERVIZIO_GIU',         'MUTO',                'PGTAP-CAUSA-SERVIZIO-GIU'),
        ('NON_PROGRAMMATO',      'NON_PROGRAMMATO',     'PGTAP-CAUSA-NON-PROGRAMMATO'),
        ('JOB_ASSENTE',          'JOB_ASSENTE',         'PGTAP-CAUSA-JOB-ASSENTE'),
        ('JOB_SPENTO',           'JOB_SPENTO',          'PGTAP-CAUSA-JOB-SPENTO'),
        ('JOB_MAI_PARTITO',      'MAI_PARTITO',         'PGTAP-CAUSA-JOB-MAI'),
        ('JOB_IN_RITARDO',       'IN_RITARDO',          'PGTAP-CAUSA-JOB-RITARDO'),
        ('GIRA_E_NON_REGISTRA',  'GIRA_E_NON_REGISTRA', 'PGTAP-CAUSA-GIRA-MUTO')
       ) AS r(causa, stato_atteso, processo);

-- ============================================================
-- 5) ⛔ Ogni causa censita ha la sua costruzione
-- ============================================================
SELECT is(
    coalesce((
        SELECT string_agg(c.stato || '/' || c.causa, ', ' ORDER BY c.causa)
          FROM _t_cause c
         WHERE NOT EXISTS (SELECT 1 FROM _t_ricette r
                            WHERE r.causa = c.causa
                              AND r.stato_atteso = c.stato)), ''),
    '',
    'test 5 — ogni coppia [stato, causa] del panorama ha una costruzione dichiarata in questo test');

DO $semina$
BEGIN
    -- COMMAND col giornale: corsa piu' vecchia della tolleranza / nessuna corsa.
    -- COMMAND con la sessione: nessuna connessione col suo codice.
    -- PGAGENT senza job / con un job che pgAgent non conosce.
    -- I tre sani: una corsa fresca, un COMMAND senza contratto, un CODA.
    -- rev 2026-09-26: un processo con job pgAgent dichiara se gira in CI
    --   (chk_processi_convergenza_ci): ci_esclusione su quelli che ne nominano uno.
    -- 20261016-20: chi ha una sveglia dichiara l'accensione (accesi ovunque:
    --   le cause si costruiscono su processi ACCESI); un CODA no.
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                jobname_pgagent, tolleranza_minuti, segno_di_vita,
                                ci_esclusione,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
    VALUES
        (9601, 'PGTAP-CAUSA-TIMER-FERMO',     'prova causa', 'MANUTENZIONE', 'COMMAND', NULL, 30,   'GIORNALE', NULL, true, true, true, 'PROGRAMMA', true),
        (9602, 'PGTAP-CAUSA-TIMER-MAI',       'prova causa', 'MANUTENZIONE', 'COMMAND', NULL, 30,   'GIORNALE', NULL, true, true, true, 'PROGRAMMA', true),
        (9603, 'PGTAP-CAUSA-SERVIZIO-GIU',    'prova causa', 'MANUTENZIONE', 'COMMAND', NULL, NULL, 'SESSIONE', NULL, true, true, true, 'PROGRAMMA', true),
        (9604, 'PGTAP-CAUSA-NON-PROGRAMMATO', 'prova causa', 'MANUTENZIONE', 'PGAGENT', NULL, NULL, 'GIORNALE', NULL, true, true, true, 'PROGRAMMA', true),
        (9605, 'PGTAP-CAUSA-JOB-ASSENTE',     'prova causa', 'MANUTENZIONE', 'PGAGENT',
               'PGTAP-JOB-CAUSA-ASSENTE', NULL, 'GIORNALE', 'pgTAP: processo di prova', true, true, true, 'PROGRAMMA', true),
        (9611, 'PGTAP-CAUSA-SANO-OK',         'prova causa', 'MANUTENZIONE', 'COMMAND', NULL, 30,   'GIORNALE', NULL, true, true, true, 'PROGRAMMA', true),
        (9612, 'PGTAP-CAUSA-SANO-FUORI',      'prova causa', 'MANUTENZIONE', 'COMMAND', NULL, NULL, 'GIORNALE', NULL, true, true, true, 'PROGRAMMA', true),
        (9613, 'PGTAP-CAUSA-SANO-CODA',       'prova causa', 'MANUTENZIONE', 'CODA',    NULL, NULL, 'GIORNALE', NULL, NULL, NULL, NULL, 'PROGRAMMA', NULL);

    INSERT INTO maintenance.job_run_log (jobname, processo_codice, origine, started_at, ended_at, ok, message)
    VALUES ('PGTAP-CAUSA-TIMER-FERMO', 'PGTAP-CAUSA-TIMER-FERMO', 'CRON',
            now() - interval '2 hours', now() - interval '2 hours', true, 'pgtap'),
           ('PGTAP-CAUSA-SANO-OK', 'PGTAP-CAUSA-SANO-OK', 'CRON',
            now() - interval '10 minutes', now() - interval '10 minutes', true, 'pgtap');
END
$semina$;

-- ⚠️ Le tre cause che vivono in pgAgent si costruiscono con un job FINTO in
--   pgagent.pga_job: e' l'unico modo, perche' la funzione che le legge
--   (dbops.fn_get_pgagent_job_stato) guarda li'. Dove l'estensione manca (CI)
--   o il ruolo non puo' scriverci, il caso NON si costruisce e lo si DICHIARA:
--   il test 3 copre comunque il loro testo, dal censimento.
CREATE TEMP TABLE _t_pgagent ON COMMIT DROP AS
SELECT false AS costruito, ''::text AS motivo;

DO $pgagent$
DECLARE
    v_classe integer;
BEGIN
    IF to_regclass('pgagent.pga_job') IS NULL THEN
        UPDATE _t_pgagent SET motivo = 'pgAgent non e'' installato su questo database (CI?)';
        RETURN;
    END IF;

    BEGIN
        EXECUTE 'SELECT jclid FROM pgagent.pga_jobclass ORDER BY jclid LIMIT 1' INTO v_classe;
        -- ⭐ Rev 2026-10-14: jobnextrun ESPLICITO, perche' ora decide (la corsa
        --   dovuta). Il trigger di pgAgent (pga_job_trigger) scatta solo su
        --   UPDATE: all'INSERT il valore scritto resta.
        EXECUTE $sql$
            INSERT INTO pgagent.pga_job (jobjclid, jobname, jobenabled, joblastrun, jobnextrun)
            VALUES ($1, 'PGTAP-JOB-CAUSA-SPENTO',  false, NULL,                        NULL),
                   -- mai girato, la corsa dovuta e' passata da due ore
                   ($1, 'PGTAP-JOB-CAUSA-MAI',     true,  NULL,                        now() - interval '2 hours'),
                   ($1, 'PGTAP-JOB-CAUSA-GIRA',    true,  now() - interval '3 hours', now() + interval '1 hour'),
                   -- ha girato (e il giornale lo sa), la corsa dovuta e' passata
                   ($1, 'PGTAP-JOB-CAUSA-RITARDO', true,  now() - interval '3 hours', now() - interval '2 hours'),
                   -- mai girato, la prima corsa e' fra tre ore: il job nuovo
                   ($1, 'PGTAP-JOB-CAUSA-ATTESA',  true,  NULL,                        now() + interval '3 hours')
        $sql$ USING v_classe;
    EXCEPTION WHEN insufficient_privilege OR not_null_violation OR foreign_key_violation THEN
        UPDATE _t_pgagent SET motivo = 'non si puo'' seminare pgagent.pga_job da qui: ' || SQLERRM;
        RETURN;
    END;

    -- 20261016-20: chi ha una sveglia dichiara l'accensione (accesi ovunque).
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                jobname_pgagent, ci_esclusione,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento, accendibile_in_produzione)
    VALUES
        (9606, 'PGTAP-CAUSA-JOB-SPENTO', 'prova causa', 'MANUTENZIONE', 'PGAGENT',
               'PGTAP-JOB-CAUSA-SPENTO', 'pgTAP: processo di prova', true, true, true, 'PROGRAMMA', true),
        (9607, 'PGTAP-CAUSA-JOB-MAI',    'prova causa', 'MANUTENZIONE', 'PGAGENT',
               'PGTAP-JOB-CAUSA-MAI',    'pgTAP: processo di prova', true, true, true, 'PROGRAMMA', true),
        -- ⭐ pgAgent dice che e' girato tre ore fa, il giornale non ha niente.
        (9608, 'PGTAP-CAUSA-GIRA-MUTO',  'prova causa', 'MANUTENZIONE', 'PGAGENT',
               'PGTAP-JOB-CAUSA-GIRA',   'pgTAP: processo di prova', true, true, true, 'PROGRAMMA', true),
        (9609, 'PGTAP-CAUSA-JOB-RITARDO', 'prova causa', 'MANUTENZIONE', 'PGAGENT',
               'PGTAP-JOB-CAUSA-RITARDO', 'pgTAP: processo di prova', true, true, true, 'PROGRAMMA', true),
        (9610, 'PGTAP-CAUSA-JOB-ATTESA',  'prova causa', 'MANUTENZIONE', 'PGAGENT',
               'PGTAP-JOB-CAUSA-ATTESA',  'pgTAP: processo di prova', true, true, true, 'PROGRAMMA', true);

    -- ⚠️ Il giornale sa della corsa di RITARDO: senza, il caso uscirebbe
    --   GIRA_E_NON_REGISTRA, che viene prima nel CASE.
    INSERT INTO maintenance.job_run_log (jobname, processo_codice, origine, started_at, ended_at, ok, message)
    VALUES ('PGTAP-CAUSA-JOB-RITARDO', 'PGTAP-CAUSA-JOB-RITARDO', 'PGAGENT',
            now() - interval '3 hours', now() - interval '3 hours', true, 'pgtap');

    UPDATE _t_pgagent SET costruito = true;
END
$pgagent$;

-- La vista di SESSIONE legge pg_stat_activity: si fissa una fotografia fresca.
SELECT pg_stat_clear_snapshot();

-- ============================================================
-- 6..13) ⭐ Ogni causa, costruita, esce dal PRESIDIO come atteso
-- ============================================================
-- ⚠️ Si legge la vista _da_guardare, non il panorama: e' quella che il
--   pannello e il digest leggono, e cosi' si prova anche che proietta la causa.
SELECT is(
    (SELECT stato || '/' || causa FROM dbops.vw_processi_programmazione_da_guardare
      WHERE processo_codice = 'PGTAP-CAUSA-TIMER-FERMO'),
    'MUTO/TIMER_FERMO',
    'test 6 — COMMAND col giornale, corsa oltre la tolleranza: MUTO per TIMER_FERMO');

SELECT is(
    (SELECT stato || '/' || causa FROM dbops.vw_processi_programmazione_da_guardare
      WHERE processo_codice = 'PGTAP-CAUSA-TIMER-MAI'),
    'MAI_PARTITO/TIMER_NON_INSTALLATO',
    'test 7 — COMMAND col giornale, nessuna corsa: MAI_PARTITO per TIMER_NON_INSTALLATO');

-- ⭐ Il caso del 2026-10-09: un servizio sempre acceso che tace NON e' un timer.
SELECT is(
    (SELECT stato || '/' || causa FROM dbops.vw_processi_programmazione_da_guardare
      WHERE processo_codice = 'PGTAP-CAUSA-SERVIZIO-GIU'),
    'MUTO/SERVIZIO_GIU',
    'test 8 — COMMAND con la sessione, nessuna connessione: MUTO per SERVIZIO_GIU, non TIMER_FERMO');

SELECT is(
    (SELECT stato || '/' || causa FROM dbops.vw_processi_programmazione_da_guardare
      WHERE processo_codice = 'PGTAP-CAUSA-NON-PROGRAMMATO'),
    'NON_PROGRAMMATO/NON_PROGRAMMATO',
    'test 9 — PGAGENT senza job dichiarato: NON_PROGRAMMATO');

SELECT is(
    (SELECT stato || '/' || causa FROM dbops.vw_processi_programmazione_da_guardare
      WHERE processo_codice = 'PGTAP-CAUSA-JOB-ASSENTE'),
    'JOB_ASSENTE/JOB_ASSENTE',
    'test 10 — PGAGENT con un job che pgAgent non conosce: JOB_ASSENTE');

SELECT CASE
    WHEN NOT (SELECT costruito FROM _t_pgagent)
        THEN skip('test 11 — ' || (SELECT motivo FROM _t_pgagent), 1)
    ELSE is(
        (SELECT stato || '/' || causa FROM dbops.vw_processi_programmazione_da_guardare
          WHERE processo_codice = 'PGTAP-CAUSA-JOB-SPENTO'),
        'JOB_SPENTO/JOB_SPENTO',
        'test 11 — PGAGENT con il job spento: JOB_SPENTO')
END;

SELECT CASE
    WHEN NOT (SELECT costruito FROM _t_pgagent)
        THEN skip('test 12 — ' || (SELECT motivo FROM _t_pgagent), 1)
    ELSE is(
        (SELECT stato || '/' || causa FROM dbops.vw_processi_programmazione_da_guardare
          WHERE processo_codice = 'PGTAP-CAUSA-JOB-MAI'),
        'MAI_PARTITO/JOB_MAI_PARTITO',
        'test 12 — PGAGENT con il job acceso, mai girato e la corsa dovuta passata: MAI_PARTITO per JOB_MAI_PARTITO, non un timer')
END;

SELECT CASE
    WHEN NOT (SELECT costruito FROM _t_pgagent)
        THEN skip('test 13 — ' || (SELECT motivo FROM _t_pgagent), 1)
    ELSE is(
        (SELECT stato || '/' || causa FROM dbops.vw_processi_programmazione_da_guardare
          WHERE processo_codice = 'PGTAP-CAUSA-GIRA-MUTO'),
        'GIRA_E_NON_REGISTRA/GIRA_E_NON_REGISTRA',
        'test 13 — pgAgent dice girato, il giornale no: GIRA_E_NON_REGISTRA')
END;

-- ============================================================
-- 14) ⛔ I sani non hanno causa
-- ============================================================
-- ⭐ E' il verso che rende i 6..13 una misura: `da_guardare` e' «ha una
--   causa», quindi un CASE che desse una causa anche ai sani li farebbe
--   entrare tutti nel presidio. Si guarda il PANORAMA: nel presidio non ci
--   sono per costruzione.
SELECT is(
    (SELECT string_agg(processo_codice || '=' || stato || '/'
                       || coalesce(causa, '-') || '/' || da_guardare::text,
                       ', ' ORDER BY processo_codice)
       FROM dbops.vw_processi_programmazione
      WHERE processo_codice LIKE 'PGTAP-CAUSA-SANO-%'),
    'PGTAP-CAUSA-SANO-CODA=SU_RICHIESTA/-/false, '
    'PGTAP-CAUSA-SANO-FUORI=FUORI_PORTATA/-/false, '
    'PGTAP-CAUSA-SANO-OK=OK/-/false',
    'test 14 — OK, FUORI_PORTATA e SU_RICHIESTA non hanno causa e non sono da guardare');

-- ============================================================
-- 15) ⛔ Nel presidio nessuna riga senza causa
-- ============================================================
-- Una riga da guardare senza causa non troverebbe nessun testo: il pannello
-- mostrerebbe un guasto senza rimedio. Vale su tutta la vista, seminati
-- compresi: e' un invariante, non un conteggio.
SELECT is_empty(
    $$SELECT processo_codice FROM dbops.vw_processi_programmazione_da_guardare
       WHERE causa IS NULL$$,
    'test 15 — ogni riga del presidio ha la sua causa');

-- ============================================================
-- 16) ⭐ Ogni causa della vista ha il suo testo italiano
-- ============================================================
-- ⭐ Ridondante con 3 + test-presidi-testi-v1 test 16, ed e' voluto: e' la
--   promessa del brief (§3 B.4) detta per QUESTO presidio, e il messaggio
--   nomina la causa scoperta senza dover incrociare due file.
SELECT is(
    coalesce((
        SELECT string_agg(c.causa, ', ' ORDER BY c.causa)
          FROM _t_cause c
         WHERE NOT EXISTS (
               SELECT 1 FROM dbops.presidi_testi t
                WHERE t.vista = 'dbops.vw_processi_programmazione_da_guardare'
                  AND t.lingua = 'it'
                  AND t.variante = c.causa)), ''),
    '',
    'test 16 — ogni causa che il panorama puo'' produrre ha significato e azione in italiano');

-- ============================================================
-- 17..18) ⭐ pgAgent: il segnale e' la corsa DOVUTA (rev 2026-10-14)
-- ============================================================
SELECT CASE
    WHEN NOT (SELECT costruito FROM _t_pgagent)
        THEN skip('test 17 — ' || (SELECT motivo FROM _t_pgagent), 1)
    ELSE is(
        (SELECT stato || '/' || causa FROM dbops.vw_processi_programmazione_da_guardare
          WHERE processo_codice = 'PGTAP-CAUSA-JOB-RITARDO'),
        'IN_RITARDO/JOB_IN_RITARDO',
        'test 17 — PGAGENT che ha girato, con la corsa dovuta passata da piu'' di un''ora: IN_RITARDO per JOB_IN_RITARDO (il demone fermo)')
END;

-- ⛔ Il caso del 14-10: un job nuovo non e' un guasto finche' la sua prima
--   corsa non e' dovuta. Si guarda il PANORAMA: nel presidio non c'e'.
SELECT CASE
    WHEN NOT (SELECT costruito FROM _t_pgagent)
        THEN skip('test 18 — ' || (SELECT motivo FROM _t_pgagent), 1)
    ELSE is(
        (SELECT stato || '/' || coalesce(causa, '-') || '/' || da_guardare::text
           FROM dbops.vw_processi_programmazione
          WHERE processo_codice = 'PGTAP-CAUSA-JOB-ATTESA'),
        'IN_ATTESA/-/false',
        'test 18 — PGAGENT mai girato con la prima corsa ancora futura: IN_ATTESA, senza causa, non da guardare')
END;

SELECT * FROM finish();

ROLLBACK;
