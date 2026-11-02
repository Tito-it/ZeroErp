-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un ruolo con indirizzi RES e DOMFISC che condividono lo stesso
--       indirizzo_dettaglio (la residenza che e' anche domicilio fiscale)
--
-- Scenario:
--   - Costruisce un soggetto con ruolo CLIENTE (CL), senza indirizzi di ruolo
--   - Recupera i tipi indirizzo RES e DOMFISC da config.tipi_indirizzi
--   - Crea un indirizzo_dettaglio normalizzato di test
--   - Crea l'indirizzo RES del ruolo su quell'indirizzo_dettaglio
--   - Crea l'indirizzo DOMFISC del ruolo sullo stesso indirizzo_dettaglio
--   - Verifica:
--       * l'indirizzo_dettaglio si ritrova con fn_search_indirizzi_dettaglio
--       * 1 indirizzo RES e 1 DOMFISC per il ruolo
--       * entrambi puntano allo stesso indirizzo_dettaglio_id

--  Aggiunta del 2024-06-11  utilizzo di fn_search_indirizzi_dettaglio
--  per verificare che l'indirizzo_dettaglio creato sia effettivamente
--  reperibile tramite la funzione di ricerca indirizzi_dettaglio 3-bis)

-- ------------------------------------------------------------

-- ============================================================================
-- rev 2026-09-23 — riscritto sul modello (brief-db-fixture-che-costruiscono-
-- giro-2, lotto 2). Il file (nome storico: create-gestore-...) dava al GESTORE
-- un RES e un DOMFISC, e aveva quattro difetti in fila, non uno:
--   1. leggeva MIN(id) da anagrafiche.gestori, dato di MACCHINA: su un
--      database ricostruito (la CI) e' vuota, e il file moriva al test 1;
--   2. RES e DOMFISC NON sono ammessi per il ruolo GE:
--      config.tipi_ruolo_tipi_indirizzo per GE prevede SEDELEG, FATT e SEDEOP.
--      Il fratello create-gestore-indirizzo-res.sql asserisce proprio che RES
--      su un GESTORE viene respinto. I due file si contraddicevano;
--   3. ON CONFLICT ON CONSTRAINT uq_indirizzi_ruolo_tipo: quel vincolo non
--      esiste piu', oggi l'unicita' e' l'indice PARZIALE
--      uq_indirizzi_ruolo_tipo_no_istanza (WHERE istanza_utility_id IS NULL),
--      che ON CONSTRAINT non puo' nominare;
--   4. la ricerca cercava via_norm_test, ma il trigger normalize riscrive
--      via_norm dallo stradario: il pattern non poteva trovare niente.
-- Il soggetto del test — due indirizzi dello stesso ruolo sullo STESSO
-- dettaglio — e' intatto. Cambia il veicolo: un ruolo CL, che RES e DOMFISC li
-- ammette entrambi e non li ha obbligatori, quindi nasce senza. Gli upsert
-- diventano INSERT: il ruolo e' nuovo, e il civico e' unico per corsa.
-- ============================================================================

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. Messa in testa e non in coda
--   apposta: in coda scatterebbero tutti insieme DOPO il cleanup, su righe
--   ormai cancellate, e fallirebbero per un motivo che non riguarda il test.
--   Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- =========================================================
-- 0) Il ruolo del test: un soggetto nuovo con ruolo CL.
--    Dopo la riga di contesto: il mondo (azienda + operatore) esiste gia', e
--    la partita IVA del soggetto e' «libera ADESSO».
--    ⛔ Cio' che i builder scrivono si legge in un'istruzione SEPARATA.
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_test AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Cliente RES/DOMFISC pgTAP') AS soggetto_id;

CREATE TEMP TABLE tmp_ruolo_test_id AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(t.soggetto_id, 'CL') AS soggetto_ruolo_id
FROM tmp_soggetto_test t;

CREATE TEMP TABLE tmp_ruolo AS
SELECT
    r.soggetto_ruolo_id,
    s.id           AS soggetto_id,
    s.stato_id     AS soggetto_stato_id,
    s.comune_id    AS soggetto_comune_id
FROM tmp_ruolo_test_id r
JOIN anagrafiche.soggetti_ruoli sr
  ON sr.id = r.soggetto_ruolo_id
JOIN anagrafiche.soggetti s
  ON s.id = sr.soggetto_id;

SELECT ok(
    (SELECT count(*) FROM tmp_ruolo) = 1,
    'Il ruolo CL del test e'' costruito e si legge col suo soggetto'
);

-- =========================================================
-- 1) Recupero tipi indirizzo RES e DOMFISC
-- =========================================================
CREATE TEMP TABLE tmp_tipi_indirizzo AS
SELECT
    ti.id,
    ti.codice_interno,
    ti.codice,
    ti.descrizione
FROM config.tipi_indirizzi ti
WHERE ti.codice_interno IN ('RES', 'DOMFISC');

SELECT ok(
    (SELECT count(*) FROM tmp_tipi_indirizzo WHERE codice_interno = 'RES') = 1
    AND
    (SELECT count(*) FROM tmp_tipi_indirizzo WHERE codice_interno = 'DOMFISC') = 1,
    'Esistono i tipi indirizzo RES e DOMFISC in config.tipi_indirizzi'
);

-- =========================================================
-- 2) Recupero uno stradario per indirizzi_dettaglio
-- =========================================================
CREATE TEMP TABLE tmp_stradario AS
SELECT
    s.id
FROM config.stradario s
ORDER BY s.id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_stradario) = 1,
    'Esiste almeno un record in config.stradario per indirizzi_dettaglio'
);

-- =========================================================
-- 3) indirizzo_dettaglio di test
--    ⚠️ Civico UNICO PER CORSA: uq_indirizzi_dettaglio_norm_v2 e' UNIQUE su
--    (stradario_id, civico, estensione, palazzina, scala, piano, interno), e
--    con un civico fisso la corsa pescherebbe un dettaglio di qualcun altro.
-- =========================================================
CREATE TEMP TABLE tmp_civico AS
SELECT (100000 + (abs(hashtext(clock_timestamp()::text)) % 800000))::integer AS civico;

WITH nuovo AS (
    INSERT INTO anagrafiche.indirizzi_dettaglio (
        stradario_id,
        civico,
        altro,
        via_norm,
        civico_norm,
        attivo,
        storicizza
    )
    SELECT
        s.id,
        c.civico,
        'Indirizzo test RES/DOMFISC (pgTAP)',
        -- ⚠️ via_norm lo riscrive il trigger normalize dallo stradario: il
        --   valore qui e' solo un segnaposto per il NOT NULL.
        'VIA TEST RES/DOMFISC',
        c.civico::text,
        TRUE,
        FALSE
    FROM tmp_stradario s,
         tmp_civico c
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_indirizzo_dettaglio
FROM nuovo;

SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzo_dettaglio),
    1,
    'Inserito esattamente 1 indirizzo_dettaglio di test'
);

-- =========================================================
-- 3-bis) Verifica tramite fn_search_indirizzi_dettaglio
--        (aggiunta del 2024-06-11)
--    Il pattern e' l'indirizzo_normalizzato che il dettaglio ha DAVVERO
--    (colonna generata da via_norm, riscritto dal trigger), riletto in
--    un'istruzione separata.
-- =========================================================
CREATE TEMP TABLE tmp_search_indirizzo AS
SELECT *
FROM anagrafiche.fn_search_indirizzi_dettaglio(
    p_stradario_id      => (SELECT id FROM tmp_stradario),
    p_civico            => (SELECT civico FROM tmp_civico),
    p_estensione_civico => NULL,
    p_palazzina         => NULL,
    p_scala             => NULL,
    p_piano             => NULL,
    p_interno           => NULL,
    p_indirizzo_norm    => (SELECT idd.indirizzo_normalizzato
                              FROM anagrafiche.indirizzi_dettaglio idd
                              JOIN tmp_indirizzo_dettaglio t ON t.id = idd.id),
    p_limit             => 10
);

SELECT is(
    (SELECT count(*)::int FROM tmp_search_indirizzo),
    1,
    'fn_search_indirizzi_dettaglio trova esattamente 1 indirizzo per stradario, civico e indirizzo normalizzato'
);

SELECT is(
    (SELECT indirizzo_dettaglio_id FROM tmp_search_indirizzo),
    (SELECT id FROM tmp_indirizzo_dettaglio),
    'fn_search_indirizzi_dettaglio restituisce l''indirizzo_dettaglio_id appena creato'
);

-- =========================================================
-- 4) Indirizzo RES del ruolo
-- =========================================================
WITH nuovo_res AS (
    INSERT INTO anagrafiche.indirizzi (
        soggetto_ruolo_id,
        tipo_indirizzo_id,
        indirizzo_dettaglio_id,
        indirizzo_libero,
        stato_id,
        comune_id,
        storicizza
    )
    SELECT
        r.soggetto_ruolo_id,
        t.id,
        idd.id,
        NULL,
        r.soggetto_stato_id,
        r.soggetto_comune_id,
        FALSE
    FROM tmp_ruolo r
    JOIN tmp_tipi_indirizzo t
      ON t.codice_interno = 'RES'
    CROSS JOIN tmp_indirizzo_dettaglio idd
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_indirizzo_res
FROM nuovo_res;

SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzo_res),
    1,
    'Inserito l''indirizzo RES del ruolo'
);

-- =========================================================
-- 5) Indirizzo DOMFISC del ruolo (stesso indirizzo_dettaglio)
-- =========================================================
WITH nuovo_domfisc AS (
    INSERT INTO anagrafiche.indirizzi (
        soggetto_ruolo_id,
        tipo_indirizzo_id,
        indirizzo_dettaglio_id,
        indirizzo_libero,
        stato_id,
        comune_id,
        storicizza
    )
    SELECT
        r.soggetto_ruolo_id,
        t.id,
        idd.id,
        NULL,
        r.soggetto_stato_id,
        r.soggetto_comune_id,
        FALSE
    FROM tmp_ruolo r
    JOIN tmp_tipi_indirizzo t
      ON t.codice_interno = 'DOMFISC'
    CROSS JOIN tmp_indirizzo_dettaglio idd
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_indirizzo_domfisc
FROM nuovo_domfisc;

SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzo_domfisc),
    1,
    'Inserito l''indirizzo DOMFISC del ruolo sullo stesso indirizzo_dettaglio'
);

-- =========================================================
-- 6) Verifica: 1 RES e 1 DOMFISC per il ruolo
-- =========================================================
SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_ruolo r
          ON r.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipi_indirizzo t
          ON t.id = i.tipo_indirizzo_id
    ),
    2,
    'Esistono esattamente 2 indirizzi per il ruolo: 1 RES e 1 DOMFISC'
);

-- =========================================================
-- 7) Verifica: RES e DOMFISC condividono lo stesso indirizzo_dettaglio_id
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.indirizzi i_res
        JOIN anagrafiche.indirizzi i_dom
          ON i_dom.soggetto_ruolo_id     = i_res.soggetto_ruolo_id
         AND i_dom.indirizzo_dettaglio_id = i_res.indirizzo_dettaglio_id
        JOIN tmp_tipi_indirizzo t_res
          ON t_res.id = i_res.tipo_indirizzo_id
         AND t_res.codice_interno = 'RES'
        JOIN tmp_tipi_indirizzo t_dom
          ON t_dom.id = i_dom.tipo_indirizzo_id
         AND t_dom.codice_interno = 'DOMFISC'
        JOIN tmp_ruolo r
          ON r.soggetto_ruolo_id = i_res.soggetto_ruolo_id
        JOIN tmp_indirizzo_dettaglio idd
          ON idd.id = i_res.indirizzo_dettaglio_id
    ),
    'Indirizzi RES e DOMFISC del ruolo condividono lo stesso indirizzo_dettaglio_id'
);

-- Fine test
SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'.
ROLLBACK;
