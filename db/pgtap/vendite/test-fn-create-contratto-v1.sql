-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: vendite.fn_create_contratto (piano analisi-fix-transazioni, #2)
--
-- Copre:
--   * happy senza utility : crea la testata (stato DRAFT) + numero, nessuna
--                           riga utility.
--   * happy con utility    : crea testata + riga contratti_utilities dal payload.
--   * ATOMICITA'           : se l'INSERT utility fallisce (classe_utenza
--                            inesistente), il contratto NON deve restare creato
--                            (nessun orfano). E' il cuore del fix.
--   * WHITELIST fatt.imm.  : (10-12, changeset 20260727-40) la corsia di
--                            instradamento `fatturazione_immediata` e' accettata
--                            dal p_testata; assente -> DEFAULT false; null ->
--                            errore, mai un silenzio.
--   * WHITELIST atto       : (13-15, changeset 20260831-24) i TRE riferimenti
--                            dell'atto — CIG, CUP, commessa — sono accettati dal
--                            p_testata e RILETTI dalla riga; assenti -> NULL;
--                            null esplicito -> NULL, senza errore.
--   * WHITELIST canone     : (16-18, changeset 20261031-28, brief-db-contratto-
--                            righe-periodiche-in-commessa D-5) generazione_canone
--                            e mese_partenza_canone accettati e RILETTI; assenti
--                            -> i default (INIZIO_PERIODO, 1); null -> 23502.
--
-- ⚠️ I casi 13-15 si aggiungono QUI e non in un file nuovo: e' lo stesso
--    difetto dei casi 10-12, sulla stessa funzione, e la copertura di
--    fn_create_contratto sta in un posto solo. Il precedente e' quello.
--
-- ⛔ E il caso 13 e' l'UNICO che discrimina: la funzione **non solleva** su una
--    chiave fuori whitelist, la **scarta**. Asserire che la chiamata riesce non
--    prova niente — riesce anche con la versione vecchia. Bisogna RILEGGERE il
--    valore. Controprova di mutazione: rilanciare il caso 13 contro la funzione
--    senza le tre stringhe in v_testata_allowed e vederlo diventare rosso.
--
-- Nota sul numero: `script.fn_generate_codice` usa una SEQUENCE (nextval), che
-- per definizione NON fa rollback. Quindi un fallimento lascia un "buco" nella
-- numerazione (gap innocuo, gia' cosi' prima del fix). Il fix elimina il danno
-- reale — il contratto orfano — non il gap di sequenza: il test verifica quello.
--
-- Riusa un billing_account esistente SENZA precontrattuali (per non far scattare
-- lo snapshot automatico trgfn_contratti_snapshot_precontrattuali). Idempotente:
-- BEGIN ... ROLLBACK.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(18);

-- =========================================================
-- Precondizione: coppia (istanza_utility, utility) SENZA precontrattuali
-- =========================================================
-- Serve un emittente fiscale risolvibile (efba) da passare esplicito nel
-- payload: in sessione pgTAP la GUC e' vuota (il trigger default_emittente
-- richiede l'emittente esplicito senza GUC; il guard_emittente_scope invece fa
-- skip con GUC vuota).
--
-- Serve inoltre che il contratto NON faccia scattare lo snapshot automatico
-- `trgfn_contratti_snapshot_precontrattuali`, che creerebbe da solo una riga
-- `contratti_utilities` e falserebbe i casi 5-7.
--
-- Storia: la prima stesura cercava un billing_account senza precontrattuali;
--   dal 2026-07-27 tutti i BA di dbdev ne avevano, e si era ripiegato su una
--   utility «libera» diversa da quella del BA. Vedi la nota qui sotto.
-- ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba, R-2 e D-2): il cliente si
--   COSTRUISCE con dbops.fn_pgtap_crea_cliente_ba, che da' un BA nuovo, sulla
--   sua utility e SENZA dati precontrattuali (il builder non li scrive): la
--   coppia (istanza, utility) del contratto e' quella del suo BA. Fino a quel
--   giorno si pescava un BA e, siccome tutti i BA di dbdev avevano gia' i loro
--   dati precontrattuali (42/42 dal 2026-07-27), si sceglieva una utility
--   «libera» DIVERSA da quella del BA: un contratto col BA di un'altra coppia,
--   che fk_contratti_ba_coppia (20261008-54) ora rifiuta. ⛔ Il builder scrive;
--   si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_cli_cc AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('create contratto');

CREATE TEMP TABLE tmp_ba AS
SELECT c.billing_account_id, c.istanza_utility_id, c.utility_id,
       anagrafiche.fn_get_emittente_fiscale_pk(c.billing_account_id) AS emittente_fiscale_id
  FROM tmp_cli_cc c;

SELECT is((SELECT count(*)::int FROM tmp_ba), 1,
          'Precondizione: BA con emittente + coppia (istanza,utility) senza precontrattuali');

-- =========================================================
-- HAPPY senza utility
-- =========================================================
CREATE TEMP TABLE r1 AS
SELECT * FROM vendite.fn_create_contratto(
    jsonb_build_object(
        'billing_account_id',  (SELECT billing_account_id FROM tmp_ba),
        'emittente_fiscale_id',(SELECT emittente_fiscale_id FROM tmp_ba),
        'istanza_utility_id',  (SELECT istanza_utility_id FROM tmp_ba),
        'utility_id',          (SELECT utility_id FROM tmp_ba)
    ),
    NULL
);

SELECT ok((SELECT contratto_id FROM r1) IS NOT NULL,
          'Happy no-utility: contratto_id ritornato non nullo');

SELECT is(
    (SELECT sd.codice_interno
       FROM vendite.contratti c
       JOIN config.stati_doc_contratti sd ON sd.id = c.stato_doc_contratto_id
      WHERE c.id = (SELECT contratto_id FROM r1)),
    'DRAFT',
    'Happy no-utility: contratto creato in stato DRAFT');

SELECT is(
    (SELECT c.numero FROM vendite.contratti c WHERE c.id = (SELECT contratto_id FROM r1)),
    (SELECT numero FROM r1),
    'Happy no-utility: numero ritornato = numero persistito');

SELECT is(
    (SELECT count(*)::int FROM vendite.contratti_utilities
      WHERE contratto_id = (SELECT contratto_id FROM r1)),
    0,
    'Happy no-utility: nessuna riga contratti_utilities');

-- =========================================================
-- HAPPY con utility
-- =========================================================
CREATE TEMP TABLE r2 AS
SELECT * FROM vendite.fn_create_contratto(
    jsonb_build_object(
        'billing_account_id',  (SELECT billing_account_id FROM tmp_ba),
        'emittente_fiscale_id',(SELECT emittente_fiscale_id FROM tmp_ba),
        'istanza_utility_id',  (SELECT istanza_utility_id FROM tmp_ba),
        'utility_id',          (SELECT utility_id FROM tmp_ba)
    ),
    -- utility 'BASE' non ammette dimensione tipo/classe: usiamo un campo libero
    jsonb_build_object(
        'istanza_utility_id', (SELECT istanza_utility_id FROM tmp_ba),
        'utility_id',         (SELECT utility_id FROM tmp_ba),
        'param_2_txt',        'PGTAP2'
    )
);

SELECT ok((SELECT contratto_id FROM r2) IS NOT NULL,
          'Happy con-utility: contratto_id ritornato non nullo');

SELECT is(
    (SELECT param_2_txt FROM vendite.contratti_utilities
      WHERE contratto_id = (SELECT contratto_id FROM r2)),
    'PGTAP2',
    'Happy con-utility: riga contratti_utilities creata con param_2_txt');

-- =========================================================
-- ATOMICITA': INSERT utility invalido (classe non ammessa per questa utility)
-- => l'intera fn fallisce e NON deve restare alcun contratto orfano.
-- =========================================================
CREATE TEMP TABLE tmp_cnt_before AS
SELECT count(*)::int AS n FROM vendite.contratti
 WHERE billing_account_id = (SELECT billing_account_id FROM tmp_ba);

SELECT throws_like(
    $$ SELECT * FROM vendite.fn_create_contratto(
           jsonb_build_object(
               'billing_account_id',  (SELECT billing_account_id FROM tmp_ba),
               'emittente_fiscale_id',(SELECT emittente_fiscale_id FROM tmp_ba),
               'istanza_utility_id',  (SELECT istanza_utility_id FROM tmp_ba),
               'utility_id',          (SELECT utility_id FROM tmp_ba)),
           jsonb_build_object(
               'istanza_utility_id', (SELECT istanza_utility_id FROM tmp_ba),
               'utility_id',         (SELECT utility_id FROM tmp_ba),
               'classe_utenza_id',   999999)) $$,
    '%senza dimensione tipo/classe%',
    'Atomicita'': INSERT utility invalido fa fallire l''intera chiamata');

SELECT is(
    (SELECT count(*)::int FROM vendite.contratti
      WHERE billing_account_id = (SELECT billing_account_id FROM tmp_ba)),
    (SELECT n FROM tmp_cnt_before),
    'Atomicita'': nessun contratto orfano creato (INSERT testata annullato)');

-- =========================================================
-- WHITELIST `fatturazione_immediata` (changeset 20260727-40)
-- Garanzie C1/C2/C4 del brief-db-fatturazione-immediata-create-contratto.
--
-- C3 (il guard respinge l'UPDATE del flag su documento gia' pushato) NON si
-- ritesta qui: e' gia' coperto da test-fatturazione-immediata-simmetria-
-- sorgenti-v1.sql caso 15, e riguarda l'UPDATE — la create non tocca quel
-- trigger (BEFORE UPDATE OF).
-- =========================================================

-- C2: la create SENZA la chiave lascia il DEFAULT false. Riusa r1 (happy
-- no-utility, payload privo del flag): e' esattamente il caso "chiamata
-- esistente non toccata dalla modifica" — la non-regressione delle create gia'
-- in produzione.
SELECT is(
    (SELECT c.fatturazione_immediata
       FROM vendite.contratti c WHERE c.id = (SELECT contratto_id FROM r1)),
    false,
    'C2) create senza la chiave: fatturazione_immediata resta al DEFAULT false');

-- C1: la create CON la chiave a true la persiste. Prima del 20260727-40 questo
-- test sarebbe fallito in silenzio (colonna false), non con un errore: la
-- chiave fuori whitelist veniva filtrata via senza dirlo a nessuno.
CREATE TEMP TABLE r3 AS
SELECT * FROM vendite.fn_create_contratto(
    jsonb_build_object(
        'billing_account_id',    (SELECT billing_account_id FROM tmp_ba),
        'emittente_fiscale_id',  (SELECT emittente_fiscale_id FROM tmp_ba),
        'istanza_utility_id',    (SELECT istanza_utility_id FROM tmp_ba),
        'utility_id',            (SELECT utility_id FROM tmp_ba),
        'fatturazione_immediata', true
    ),
    NULL
);

SELECT is(
    (SELECT c.fatturazione_immediata
       FROM vendite.contratti c WHERE c.id = (SELECT contratto_id FROM r3)),
    true,
    'C1) create con fatturazione_immediata=true: valore persistito');

-- C4: chiave PRESENTE con valore null. Il filtro della whitelist e' sulla
-- presenza, non sul valore: la colonna entra nell'INSERT come NULL e la NOT NULL
-- respinge (23502). Comportamento voluto e documentato — il contratto per il BE
-- e' "ometti la chiave oppure manda un booleano": meglio un errore che una
-- corsia decisa da un default nascosto.
SELECT throws_ok(
    $$ SELECT * FROM vendite.fn_create_contratto(
           jsonb_build_object(
               'billing_account_id',    (SELECT billing_account_id FROM tmp_ba),
               'emittente_fiscale_id',  (SELECT emittente_fiscale_id FROM tmp_ba),
               'istanza_utility_id',    (SELECT istanza_utility_id FROM tmp_ba),
               'utility_id',            (SELECT utility_id FROM tmp_ba),
               'fatturazione_immediata', null)) $$,
    '23502',
    NULL::text,
    'C4) create con fatturazione_immediata=null: errore NOT NULL, mai un silenzio');

-- =========================================================
-- WHITELIST dei TRE RIFERIMENTI DELL'ATTO (changeset 20260831-24)
-- Piano: brief-db-fn-create-contratto-codici-atto §4.
--
-- ⛔ IL TEST CHE DISCRIMINA E' IL 13, E NON E' «LA CHIAMATA RIESCE».
--    La funzione non solleva su una chiave fuori whitelist: la SCARTA
--    (`WHERE key = ANY(v_testata_allowed)`). Con la versione vecchia la
--    create andava a buon fine, restituiva un id, e i tre codici finivano
--    nel nulla — 200 al backend, nessun errore a video, CIG perso.
--    ⇒ L'unica asserzione che distingue le due versioni e' quella che
--    RILEGGE i valori dalla riga. E' la stessa forma di controprova gia'
--    usata su I9 e I10: rilanciarla contro la funzione precedente e vederla
--    diventare rossa.
-- =========================================================

CREATE TEMP TABLE r4 AS
SELECT * FROM vendite.fn_create_contratto(
    jsonb_build_object(
        'billing_account_id',   (SELECT billing_account_id FROM tmp_ba),
        'emittente_fiscale_id', (SELECT emittente_fiscale_id FROM tmp_ba),
        'istanza_utility_id',   (SELECT istanza_utility_id FROM tmp_ba),
        'utility_id',           (SELECT utility_id FROM tmp_ba),
        'codice_cig',           'PGTAPCIG01',
        'codice_cup',           'PGTAPCUP01',
        'codice_commessa',      'PGTAP-COMMESSA-01'
    ),
    NULL
);

-- 13) I TRE INSIEME, riletti dalla riga.
-- ⚠️ Si asseriscono in UN colpo solo, con una riga composita: i tre nascono e
--    si compilano insieme perche' nominano lo stesso atto (D9), e tre
--    asserzioni separate lascerebbero passare una whitelist che ne ha accolti
--    due su tre con un rosso solo su una riga — meno leggibile e non piu'
--    informativo.
SELECT is(
    (SELECT ROW(c.codice_cig, c.codice_cup, c.codice_commessa)::text
       FROM vendite.contratti c WHERE c.id = (SELECT contratto_id FROM r4)),
    ROW('PGTAPCIG01', 'PGTAPCUP01', 'PGTAP-COMMESSA-01')::text,
    '13) create con i tre codici dell''atto: TUTTI E TRE riletti dalla riga '
    '(con la whitelist vecchia sarebbero NULL, senza nessun errore)');

-- 14) NON-REGRESSIONE: la create senza le chiavi non inventa niente.
-- Riusa r1 (happy no-utility, payload privo dei tre codici): e' il caso
-- «chiamata esistente non toccata dalla modifica», cioe' la stragrande
-- maggioranza dei contratti, che con un atto non c'entrano nulla.
SELECT ok(
    (SELECT c.codice_cig IS NULL AND c.codice_cup IS NULL
        AND c.codice_commessa IS NULL
       FROM vendite.contratti c WHERE c.id = (SELECT contratto_id FROM r1)),
    '14) create senza le chiavi dell''atto: i tre restano NULL');

-- 15) ⭐ LA SEMANTICA DEL NULL NON E' LA STESSA DEL CASO 12, ED E' VOLUTO.
--    `fatturazione_immediata` e' NOT NULL: chiave = null -> 23502 (caso 12).
--    I tre codici dell'atto sono NULLABLE: un null e' un VALORE LEGITTIMO e
--    significa «non c'e' un CIG». Il backend puo' mandarli sempre, senza
--    doversi ricordare di ometterli — ed e' la differenza che questo caso
--    esiste per fissare, perche' altrimenti il prossimo lettore applicherebbe
--    ai tre la regola scritta accanto per il flag.
CREATE TEMP TABLE r5 AS
SELECT * FROM vendite.fn_create_contratto(
    jsonb_build_object(
        'billing_account_id',   (SELECT billing_account_id FROM tmp_ba),
        'emittente_fiscale_id', (SELECT emittente_fiscale_id FROM tmp_ba),
        'istanza_utility_id',   (SELECT istanza_utility_id FROM tmp_ba),
        'utility_id',           (SELECT utility_id FROM tmp_ba),
        'codice_cig',           null,
        'codice_cup',           null,
        'codice_commessa',      null
    ),
    NULL
);

SELECT ok(
    (SELECT c.codice_cig IS NULL AND c.codice_cup IS NULL
        AND c.codice_commessa IS NULL
       FROM vendite.contratti c WHERE c.id = (SELECT contratto_id FROM r5)),
    '15) create con i tre codici a null: nessun errore e colonne NULL '
    '(nullable, a differenza di fatturazione_immediata del caso 12)');

-- =========================================================
-- WHITELIST DEI DUE CAMPI DEL CANONE (changeset 20261031-28)
-- Brief: brief-db-contratto-righe-periodiche-in-commessa §7.4 (D-5).
--
-- ⛔ Come il 13: discrimina solo la RILETTURA. Con la whitelist vecchia la
--    create riesce, e i due campi nascono coi default.
--    Si scelgono valori DIVERSI dai default (FINE_PERIODO, 2): coi default il
--    test sarebbe verde anche con la chiave scartata.
-- =========================================================
CREATE TEMP TABLE r6 AS
SELECT * FROM vendite.fn_create_contratto(
    jsonb_build_object(
        'billing_account_id',   (SELECT billing_account_id FROM tmp_ba),
        'emittente_fiscale_id', (SELECT emittente_fiscale_id FROM tmp_ba),
        'istanza_utility_id',   (SELECT istanza_utility_id FROM tmp_ba),
        'utility_id',           (SELECT utility_id FROM tmp_ba),
        'generazione_canone',   'FINE_PERIODO',
        'mese_partenza_canone', 2
    ),
    NULL
);

-- 16) I due insieme, riletti dalla riga.
SELECT is(
    (SELECT ROW(c.generazione_canone, c.mese_partenza_canone)::text
       FROM vendite.contratti c WHERE c.id = (SELECT contratto_id FROM r6)),
    ROW('FINE_PERIODO', 2)::text,
    '16) create con «canoni normali, da febbraio»: tutti e due riletti dalla riga '
    '(con la whitelist vecchia sarebbero INIZIO_PERIODO e 1, senza nessun errore)');

-- 17) Non-regressione: senza le chiavi, i default della colonna (r1).
SELECT is(
    (SELECT ROW(c.generazione_canone, c.mese_partenza_canone)::text
       FROM vendite.contratti c WHERE c.id = (SELECT contratto_id FROM r1)),
    ROW('INIZIO_PERIODO', 1)::text,
    '17) create senza le chiavi del canone: i default (anticipati, gennaio)');

-- 18) Le due colonne sono NOT NULL: come fatturazione_immediata (caso 12), un
--     null mandato e' un errore, mai un default nascosto.
SELECT throws_ok(
    $$ SELECT * FROM vendite.fn_create_contratto(
           jsonb_build_object(
               'billing_account_id',   (SELECT billing_account_id FROM tmp_ba),
               'emittente_fiscale_id', (SELECT emittente_fiscale_id FROM tmp_ba),
               'istanza_utility_id',   (SELECT istanza_utility_id FROM tmp_ba),
               'utility_id',           (SELECT utility_id FROM tmp_ba),
               'mese_partenza_canone', null)) $$,
    '23502',
    NULL::text,
    '18) create con mese_partenza_canone=null: errore NOT NULL, mai un silenzio');

SELECT * FROM finish();

ROLLBACK;
