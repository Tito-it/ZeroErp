-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test 4 deve SEMINARE un processo guasto in
--   dbops.processi (in transazione, poi annullata). E' un catalogo che a
--   runtime non scrive nessuno — lo popola il mirror CSV di 80_data — e su cui
--   il ruolo applicativo ha SELECT-only. Verificato cercando gli scrittori, non
--   dedotto.
--
-- Test: dbops.vw_processi_programmazione_da_guardare — il presidio
-- ChangeSet: 20260907-01 / -02 / -07
-- Brief: brief-db-sveglia-dei-processi §6 (richiesta del backend), §8.2, §9.5-bis
--
-- Elenco test (plan 7):
--  1) la vista esiste
--  2) ⚠️ e ha un commento: il pannello ci legge la NATURA del presidio
--  3) ⭐ non contiene MAI uno stato sano — la proiezione
--  4) ⭐ e nomina un guasto COSTRUITO (senza, il 3 passerebbe a vuoto)
--  5) ⛔ panorama e presidio non possono dissentire
--  6) il ruolo applicativo la legge
--  7) ⛔ il presidio porta la colonna su cui POGGIA il verdetto
--
-- ────────────────────────────────────────────────────────────────
-- ⭐ I TEST 3 E 4 VANNO LETTI INSIEME, ed e' la ragione per cui sono due.
--   Il 3 da solo passerebbe su una vista che non torna MAI niente — cioe' su un
--   presidio spento, che e' peggio di uno assente perche' sembra verde. Il 4 e'
--   il verso che lo rende una misura: si costruisce un guasto e si pretende che
--   la vista lo nomini.
--
-- ⛔ IL TEST 5 E' QUELLO CHE PROTEGGE LA DECISIONE. La vista-presidio PROIETTA
--   il panorama su `da_guardare`, e non ripete nessun `NOT IN`: il criterio del
--   guasto sta in un posto solo, accanto al `CASE` che produce gli stati. Se un
--   giorno qualcuno riscrivesse qui una WHERE «per chiarezza», i due elenchi
--   comincerebbero a divergere in silenzio — e questo test lo dice subito.
--
-- ⚠️ ZERO RIGHE NON E' L'INVARIANTE DI QUESTO FILE. La vista «deve restare
--   vuota» sul database di PRODUZIONE, ed e' cio' che il pannello mostra; qui
--   si prova che *quando* ha righe sono le righe giuste, e che non ne perde.
--   Al 2026-09-06 ne aveva due, una delle quali e' R-12 ancora vivo (§8.1): un
--   test che avesse preteso il vuoto sarebbe nato rosso su un difetto vero, e
--   sarebbe finito in baseline.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

-- ============================================================
-- 1..2. La vista, e cio' che il pannello legge di lei
-- ============================================================
SELECT has_view('dbops', 'vw_processi_programmazione_da_guardare',
    '1. la vista-presidio esiste');

-- ⚠️ Il pannello dei presidi (PresidiProcessiPanel.vue) rende `obj_description`
--   e NON ha un elenco di eccezioni suo: e' da quel commento che un lettore
--   capisce se la vista «deve restare vuota» o se e' un registro di debito che
--   deve calare. ⛔ Una vista senza commento consegna al pannello un numero
--   senza significato — e un numero senza significato si impara a saltare.
SELECT isnt(
    NULLIF(btrim(COALESCE(
        obj_description('dbops.vw_processi_programmazione_da_guardare'::regclass,
                        'pg_class'), '')), ''),
    NULL,
    '2. la vista dichiara la propria natura nel commento: e'' cio'' che il pannello mostra'
);

-- ============================================================
-- 3. ⭐ La proiezione: nessuno stato sano entra
-- ============================================================
-- ⛔ I tre stati sani lo sono per ragioni diverse, e nessuna e' «va tutto
--   bene»: OK e' verificato, FUORI_PORTATA e' «non lo so io — lo sa il
--   backend», SU_RICHIESTA e' «una cadenza non esiste». Metterne anche uno solo
--   in un presidio insegnerebbe a leggere il verde come debito.
SELECT is_empty(
    $$SELECT processo_codice
        FROM dbops.vw_processi_programmazione_da_guardare
       WHERE stato IN ('OK', 'FUORI_PORTATA', 'SU_RICHIESTA')$$,
    '3. nel presidio non entra nessuno stato sano'
);

-- ============================================================
-- 4. ⭐ E il verso che rende il 3 una misura
-- ============================================================
-- Si costruisce il guasto piu' semplice che non dipende da pgAgent: un processo
-- che DICHIARA un job che non esiste. ⚠️ Vale anche in CI, dove l'estensione
-- manca e `fn_get_pgagent_job_stato` torna zero righe per tutti.
DO $guasto$
BEGIN
    -- rev 2026-09-26: un processo con job pgAgent dichiara se gira in CI
    --   (chk_processi_convergenza_ci, brief-db-job-notturni-in-ci).
    -- 20261016-20: un processo con una sveglia dichiara l'accensione.
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                jobname_pgagent, ci_esclusione,
                                acceso_in_sviluppo, acceso_in_produzione, spegnibile, causa_fallimento)
    VALUES (9750, 'PGTAP-PRESIDIO-GUASTO',
            'processo che dichiara un job inesistente',
            'MANUTENZIONE', 'PGAGENT', 'PGTAP-JOB-CHE-NON-ESISTE-MAI',
            'pgTAP: processo guasto seminato', true, true, true, 'PROGRAMMA');
END
$guasto$;

SELECT isnt_empty(
    $$SELECT processo_codice
        FROM dbops.vw_processi_programmazione_da_guardare
       WHERE processo_codice = 'PGTAP-PRESIDIO-GUASTO'$$,
    '4. un processo che dichiara un job inesistente il presidio lo nomina'
);

-- ============================================================
-- 5. ⛔ Panorama e presidio non possono dissentire
-- ============================================================
-- ⭐ E' il test che protegge la decisione del §8.2: il criterio del guasto sta
--   in `da_guardare`, dentro il panorama, e questa vista lo PROIETTA. Se
--   qualcuno riscrivesse qui una `WHERE stato NOT IN (...)` «per chiarezza»,
--   tornerebbero a esserci due enumerazioni degli stati — e la seconda diverge.
SELECT set_eq(
    $$SELECT processo_codice FROM dbops.vw_processi_programmazione
       WHERE da_guardare$$,
    $$SELECT processo_codice FROM dbops.vw_processi_programmazione_da_guardare$$,
    '5. il presidio e'' esattamente il panorama dove da_guardare: nessun secondo criterio'
);

-- ⛔ Si toglie subito: il seminato non deve sopravvivere ai test che seguono.
DELETE FROM dbops.processi WHERE codice = 'PGTAP-PRESIDIO-GUASTO';

-- ============================================================
-- 6. Chi la deve leggere la legge
-- ============================================================
-- ⚠️ Il pannello gira come `zeroerp_app`: senza il GRANT il presidio non
--   consegna «zero righe», consegna un ERRORE — e una vista che non si apre non
--   presidia niente. Il GRANT sta nel changeSet, dentro un DO che salta se il
--   ruolo non c'e' (CI).
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'zeroerp_app')
        THEN skip('6. ruolo zeroerp_app assente su questo database (CI?)', 1)
    ELSE ok(
        has_table_privilege('zeroerp_app',
            'dbops.vw_processi_programmazione_da_guardare', 'SELECT'),
        '6. zeroerp_app puo'' leggere il presidio: il pannello gira con quel ruolo'
    )
END;

-- ============================================================
-- 7. ⛔ La PROVA del verdetto deve stare nella riga
-- ============================================================
-- Dal 20260907-06 `GIRA_E_NON_REGISTRA` non si legge piu' su
-- `giornale_ultima_corsa` ma su `giornale_ultima_corsa_pgagent`: sono le sole
-- corse che possono valere come risposta di pgAgent.
-- ⛔ Un presidio che mostra due date e ne usa una terza consegna al pannello un
--   verdetto che chi guarda non puo' contestare — vedrebbe due timestamp
--   coerenti e una riga rossa. ⚠️ E il difetto sarebbe MUTO: le colonne le
--   sceglie chi scrive la vista, e toglierne una non fa rumore.
-- ⭐ Le due date restano ENTRAMBE, e la differenza fra loro e' informazione: se
--   `giornale_ultima_corsa` e' avanti e l'altra indietro, qualcuno ha
--   registrato sotto questo codice senza essere pgAgent — il §9.5-bis, visibile
--   a occhio.
SELECT is_empty(
    $$SELECT c.attesa
        FROM (VALUES ('pgagent_ultima_corsa'),
                     ('giornale_ultima_corsa_pgagent'),
                     ('giornale_ultima_corsa')) AS c(attesa)
       WHERE NOT EXISTS (
           SELECT 1 FROM pg_attribute a
            WHERE a.attrelid = 'dbops.vw_processi_programmazione_da_guardare'::regclass
              AND a.attname = c.attesa
              AND a.attnum > 0
              AND NOT a.attisdropped)$$,
    '7. il presidio porta le date su cui poggia il verdetto, quella di pgAgent inclusa'
);

SELECT * FROM finish();

ROLLBACK;
