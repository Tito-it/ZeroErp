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
-- ChangeSet: 20260907-01 / -02
-- Brief: brief-db-sveglia-dei-processi §6 (richiesta del backend) e §8.2
--
-- Elenco test (plan 6):
--  1) la vista esiste
--  2) ⚠️ e ha un commento: il pannello ci legge la NATURA del presidio
--  3) ⭐ non contiene MAI uno stato sano — la proiezione
--  4) ⭐ e nomina un guasto COSTRUITO (senza, il 3 passerebbe a vuoto)
--  5) ⛔ panorama e presidio non possono dissentire
--  6) il ruolo applicativo la legge
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

SELECT plan(6);

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
    INSERT INTO dbops.processi (id, codice, descrizione, classe, canale,
                                jobname_pgagent)
    VALUES (9750, 'PGTAP-PRESIDIO-GUASTO',
            'processo che dichiara un job inesistente',
            'MANUTENZIONE', 'PGAGENT', 'PGTAP-JOB-CHE-NON-ESISTE-MAI');
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

SELECT * FROM finish();

ROLLBACK;
