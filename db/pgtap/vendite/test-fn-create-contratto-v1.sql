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

SELECT plan(12);

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
-- ⚠️ La prima stesura cercava un billing_account **senza** precontrattuali. Non
--    e' piu' soddisfacibile: tutti i BA ne hanno (verificato 2026-07-27, 42/42),
--    e il test era rosso da fixture — non da codice. Il trigger pero' non
--    guarda il BA: guarda la coppia (istanza_utility_id, utility_id) del
--    contratto, che arriva dal payload. Quindi si sceglie la prima utility
--    **libera da precontrattuali** per l'istanza del BA, preferendo quella del
--    BA stesso quando gia' lo e' (`ORDER BY (u.id = ba.utility_id) DESC`): il
--    caso realistico resta il primo candidato, la variante subentra solo
--    quando serve. La `CROSS JOIN LATERAL` scarta i BA per cui nessuna utility
--    e' libera, cosi' la coppia scelta e' garantita, non sperata.
CREATE TEMP TABLE tmp_ba AS
SELECT ba.id AS billing_account_id, ba.istanza_utility_id,
       libera.utility_id,
       ef.id AS emittente_fiscale_id
FROM anagrafiche.billing_account ba
JOIN anagrafiche.emittenti_fiscali_billing_account efba
       ON efba.billing_account_id = ba.id
JOIN anagrafiche.emittenti_fiscali ef
       ON ef.soggetto_ruolo_id = efba.emittente_soggetto_ruolo_id
CROSS JOIN LATERAL (
    SELECT u.id AS utility_id
      FROM config.utilities u
     WHERE NOT EXISTS (
             SELECT 1
               FROM anagrafiche.istanze_dati_precontrattuali idp
              WHERE idp.istanza_utility_id = ba.istanza_utility_id
                AND idp.utility_id         = u.id)
     ORDER BY (u.id = ba.utility_id) DESC, u.id
     LIMIT 1
) AS libera
ORDER BY ba.id
LIMIT 1;

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

SELECT throws_ok(
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
    NULL::text,
    NULL::text,
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

SELECT * FROM finish();

ROLLBACK;
