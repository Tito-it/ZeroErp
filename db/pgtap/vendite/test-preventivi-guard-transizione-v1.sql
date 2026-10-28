-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la matrice degli stati del preventivo e' vincolante per il DATABASE,
--       non solo per i bottoni.
--       Brief: brief-db-vie-uscita-operatore §6.2 e §7.4 punto 4.
--
-- PERCHE' ESISTE. Fino al 2026-08-05 il preventivo era l'unico documento la cui
-- matrice governava quali pulsanti comparivano, ma non che cosa il database
-- accettava: un `UPDATE` diretto sullo stato passava comunque. La misura fatta
-- prima di chiudere quel buco (§7.1) diceva che nessun percorso vivo violava la
-- matrice — la regola era vera per disciplina. Questo file serve a renderla vera
-- per costruzione, e soprattutto a **restare rosso** il giorno in cui qualcuno
-- cambiera' idea senza dirlo.
--
-- ⚠️ SE UN GIORNO IL TEST 3 DIVENTA ROSSO non significa «aggiusta il test».
-- Significa che qualcuno ha aggiunto una transizione alla matrice, oppure ne ha
-- disattivata una: la risposta legittima e' aggiornare il caso qui sotto DOPO
-- aver capito perche', non prima.
--
-- COME SONO SCRITTE LE ASSERZIONI. I casi vietati non sono inventati: si
-- prendono dalla matrice stessa, cercando una coppia (stato_da, stato_a) che
-- NON vi compare. Cosi' il test non invecchia il giorno in cui gli stati
-- cambiano nome, e non afferma «DRAFT -> ACCETTATO e' vietata» come fatto
-- eterno: afferma «cio' che la matrice non prevede, il database lo rifiuta».
--
-- Indice test (1..6):
--   1) Preflight: il trigger esiste ed e' agganciato alla colonna di stato
--   2) Preflight: il codice errore nuovo e' a catalogo
--   3) Una transizione FUORI matrice viene rifiutata
--   4) Una transizione IN matrice passa
--   5) Un UPDATE che non tocca lo stato non viene disturbato dal guard
--   6) Una regola, una voce: il codice lo solleva il SOLO guard, il verbo non
--      ne tiene una copia
--
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): lo stato del
--   preventivo si cambia solo dal verbo vendite.fn_cambia_stato_preventivo; un
--   UPDATE diretto lo ferma la porta (E_DOC_STATO_SOLO_DAL_VERBO, P0001) prima
--   del guard _a10_. Quindi:
--   - 3 e 4 chiedono il passaggio al VERBO, che arriva al guard. Il 3 asserisce
--     la FRASE di E_PREV_TRANSIZIONE_NON_AMMESSA e non piu' il solo P0001: con
--     la porta, P0001 lo solleverebbe anche lei, e il test sarebbe verde per la
--     ragione sbagliata;
--   - la destinazione ammessa si sceglie fra i passaggi MANUALI (il verbo e' la
--     strada dei soli passaggi manuali), e il preventivo si COSTRUISCE in bozza
--     con una riga valida (dbops.fn_pgtap_crea_preventivo_con_righe): prima si
--     pescava un DRAFT dal database, e l'emissione ora chiede almeno una riga
--     attiva. L'operatore riceve emetti_preventivo, il permesso dell'emissione:
--     il file prova la matrice, non il permesso;
--   - il 6 cambia attesa: dal 20261025-42 il verbo non ricopia la matrice
--     (ritirata dal suo corpo la copia), quindi E_PREV_TRANSIZIONE_NON_AMMESSA
--     sta nel solo guard. «Una regola, una voce» si prova ora cosi': il guard lo
--     solleva, il verbo no (e il 3 mostra che dal verbo arriva quello del guard).
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

SELECT plan(6);

-- ============================================================
-- 1-2) Preflight. Senza questi, i test dopo passerebbero per caso.
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger t
      WHERE t.tgrelid = 'vendite.preventivi'::regclass
        AND t.tgname = 'trg_preventivi_a10_guard_transizione_upd'
        AND NOT t.tgisinternal),
    1,
    '1) preflight: il trigger di matrice esiste su vendite.preventivi');

SELECT ok(
    EXISTS (SELECT 1 FROM config.messaggi_errore
             WHERE codice = 'E_PREV_TRANSIZIONE_NON_AMMESSA'),
    '2) preflight: E_PREV_TRANSIZIONE_NON_AMMESSA e'' a catalogo');

-- ------------------------------------------------------------
-- Le due destinazioni si prendono DALLA MATRICE — una ammessa e una no — invece
-- di scriverle a mano. Cosi' il test non invecchia se gli stati cambiano nome, e
-- non afferma «DRAFT -> ACCETTATO e' vietata» come fatto eterno.
-- ------------------------------------------------------------
CREATE TEMP TABLE _t_gt AS
SELECT
    (SELECT id FROM config.stati_doc_preventivi WHERE codice_interno = 'DRAFT' LIMIT 1) AS stato_draft_id,
    -- destinazione AMMESSA da DRAFT
    -- ⚠️ fra i passaggi MANUALI: sono i soli che il verbo accetta.
    (SELECT sa.codice_interno
       FROM config.transizioni_stati_preventivi t
       JOIN config.stati_doc_preventivi sd ON sd.id = t.stato_da_id
       JOIN config.stati_doc_preventivi sa ON sa.id = t.stato_a_id
      WHERE sd.codice_interno = 'DRAFT' AND t.attivo IS TRUE
        AND COALESCE((t.meta ->> 'manuale')::boolean, true)
      ORDER BY t.stato_a_id LIMIT 1) AS stato_ammesso,
    -- destinazione NON ammessa da DRAFT: uno stato attivo qualunque per cui
    -- la coppia non compare in matrice
    (SELECT s.id
       FROM config.stati_doc_preventivi s
      WHERE s.attivo IS TRUE
        AND s.codice_interno <> 'DRAFT'
        AND NOT EXISTS (
            SELECT 1 FROM config.transizioni_stati_preventivi t
             JOIN config.stati_doc_preventivi sd ON sd.id = t.stato_da_id
            WHERE sd.codice_interno = 'DRAFT'
              AND t.stato_a_id = s.id
              AND t.attivo IS TRUE)
      ORDER BY s.id LIMIT 1) AS stato_vietato_id,
    (SELECT s.codice_interno
       FROM config.stati_doc_preventivi s
      WHERE s.attivo IS TRUE
        AND s.codice_interno <> 'DRAFT'
        AND NOT EXISTS (
            SELECT 1 FROM config.transizioni_stati_preventivi t
             JOIN config.stati_doc_preventivi sd ON sd.id = t.stato_da_id
            WHERE sd.codice_interno = 'DRAFT'
              AND t.stato_a_id = s.id
              AND t.attivo IS TRUE)
      ORDER BY s.id LIMIT 1) AS stato_vietato;

-- ⭐ rev 2026-10-25 (giro 6): il preventivo si COSTRUISCE, in DRAFT con una
--   riga valida, dal builder (che tiene le colonne obbligatorie e i trigger in
--   un posto solo). Prima si pescava un DRAFT dal database: la fixture a mano
--   sarebbe stata piu' fragile della cosa da verificare. Il «nessun
--   preventivo» dei test resta come rete, se il builder smettesse di darne.
CREATE TEMP TABLE _t_gt_prev AS
SELECT p.preventivo_id
  FROM dbops.fn_pgtap_crea_preventivo_con_righe('pgTAP guard transizione', 'DRAFT') p;

-- Si prova la matrice, non il permesso: l'emissione chiede emetti_preventivo.
DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_preventivo');
END $az$;

-- ============================================================
-- 3) Fuori matrice -> rifiutata. E' il cuore del cantiere.
--    Data-dependent: se la matrice ammettesse OGNI coppia non ci sarebbe
--    niente da vietare, e il test lo dice invece di passare in silenzio.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _t_gt_prev) = 0
  THEN fail('3) nessun preventivo in DRAFT nel database: il test non ha misurato nulla')
  WHEN (SELECT stato_vietato_id FROM _t_gt) IS NULL
  THEN fail('3) nessuna coppia fuori matrice da DRAFT: il test non ha misurato nulla, verificare la matrice')
  ELSE throws_like(
    format($sql$ SELECT * FROM vendite.fn_cambia_stato_preventivo(%L::bigint, %L) $sql$,
           (SELECT preventivo_id FROM _t_gt_prev),
           (SELECT stato_vietato FROM _t_gt)),
    '%Transizione del preventivo non ammessa%',
    '3) transizione FUORI matrice rifiutata dal database, non solo dalla UI')
END;

-- ============================================================
-- 4) In matrice -> passa. Senza questo, un guard che rifiuta TUTTO
--    supererebbe il test 3 e romperebbe l'applicazione.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _t_gt_prev) = 0
  THEN fail('4) nessun preventivo in DRAFT nel database: il test non ha misurato nulla')
  ELSE lives_ok(
    format($sql$ SELECT * FROM vendite.fn_cambia_stato_preventivo(%L::bigint, %L) $sql$,
           (SELECT preventivo_id FROM _t_gt_prev),
           (SELECT stato_ammesso FROM _t_gt)),
    '4) transizione IN matrice ammessa')
END;

-- ============================================================
-- 5) Il guard e' su UPDATE OF dello stato: un update su altre colonne
--    non lo sveglia. Se lo svegliasse, ogni scrittura sul preventivo
--    pagherebbe una query in piu' per niente.
-- ============================================================
SELECT CASE WHEN (SELECT count(*) FROM _t_gt_prev) = 0
  THEN fail('5) nessun preventivo in DRAFT nel database: il test non ha misurato nulla')
  ELSE lives_ok(
    format($sql$ UPDATE vendite.preventivi SET user_update = 'pgtap' WHERE id = %L::bigint $sql$,
           (SELECT preventivo_id FROM _t_gt_prev)),
    '5) un UPDATE che non tocca lo stato non viene disturbato dal guard')
END;

-- ============================================================
-- 6) Una regola, una voce. E' la lezione del §7.3 — due sedi per la stessa
--    domanda producono due messaggi diversi, e un giorno divergono davvero.
--    Fino al 2026-10-25 il verbo ricopiava la matrice e il test chiedeva che
--    le due copie sollevassero lo STESSO codice. Dal 20261025-42 la copia nel
--    verbo e' ritirata: il codice sta nel SOLO guard, e il verbo lo riceve da
--    lui (test 3). Si confronta il sorgente: il guard lo nomina, il verbo no.
--    ⚠️ Se il verbo tornasse a nominarlo, sarebbe una seconda sede: rosso.
-- ============================================================
SELECT is(
    (SELECT string_agg(p.proname || '=' ||
                       (p.prosrc LIKE '%''E_PREV_TRANSIZIONE_NON_AMMESSA''%')::text,
                       ',' ORDER BY p.proname)
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname IN ('fn_cambia_stato_preventivo', 'trgfn_preventivi_guard_transizione')),
    'fn_cambia_stato_preventivo=false,trgfn_preventivi_guard_transizione=true',
    '6) E_PREV_TRANSIZIONE_NON_AMMESSA lo solleva il solo guard: il verbo non ne tiene una copia');

SELECT * FROM finish();
ROLLBACK;
