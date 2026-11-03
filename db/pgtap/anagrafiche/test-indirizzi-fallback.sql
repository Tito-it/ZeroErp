-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test:
--   - Guard anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo
--     su RES/SEDELEG per Gestore
--   - Fallback fn_get_indirizzo per SEDEOP → SEDELEG
--   - Coerenza funzioni/vista resolved:
--       script.fn_get_indirizzi_by_ruolo
--       script.fn_get_indirizzi_by_soggetto
--       anagrafiche.vw_indirizzi_resolved_all
-- ------------------------------------------------------------

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

SELECT plan(14);

-- Catalogo assert (14/14)
--  1) Esiste almeno un Gestore (tmp_gestore_guard valorizzata)
--  2) Esistono almeno RES e SEDELEG in config.tipi_indirizzi
--  3) Upsert indirizzo_dettaglio di test produce esattamente 1 id
--  4) Pre-condizione: nessun indirizzo RES/SEDELEG/SEDEOP sul ruolo test
--  5) Guard blocca inserimento RES per Gestore (throws_ok)
--  6) Dopo il tentativo RES fallito non esistono RES sul ruolo test
--  7) Inserimento SEDELEG sul ruolo test riuscito (count=1)
--  8) fn_get_indirizzo(SEDEOP) applica fallback a SEDELEG
--  9) fn_get_indirizzi_by_ruolo allineata a vw_indirizzi_resolved_base scope=RUOLO
-- 10) fn_get_indirizzi_by_ruolo include SEDELEG del ruolo test
-- 11) fn_get_indirizzi_by_soggetto allineata a vw_indirizzi_resolved_base scope=SOGGETTO
-- 12) vw_indirizzi_resolved_all ha source valorizzato nel dominio RUOLO/SOGGETTO
-- 13) vw_indirizzi_resolved_all espone SEDELEG del ruolo test con source=RUOLO
-- 14) Coerenza cardinalita viste: ALL = RUOLO + SOGGETTO
--
-- =========================================================
-- 1) Gestore e soggetto_ruolo
-- =========================================================
-- ⛔ Rev 2026-11-03: il gestore si PRENDE-O-COSTRUISCE, non si pesca.
--   anagrafiche.gestori e' dato di macchina: su un database ricostruito da
--   zero (CI, scratch zeroerp_ruoli) e' vuota, MIN(id) dava NULL e ogni
--   scrittura del file lavorava su zero righe — rosso su tutte le asserzioni,
--   senza un errore. Il builder risponde il gestore che c'e' (dbdev) o ne
--   costruisce uno col ruolo GE completo dei suoi obbligatori.
CREATE TEMP TABLE tmp_gestore_guard AS
SELECT
    g.gestore_id                AS gestore_id,
    g.gestore_soggetto_ruolo_id AS soggetto_ruolo_id,
    g.gestore_soggetto_id       AS soggetto_id
FROM dbops.fn_pgtap_crea_gestore('indirizzi fallback') g;

SELECT ok(
    (SELECT count(*) FROM tmp_gestore_guard) = 1,
    'Esiste almeno un Gestore (tmp_gestore_guard valorizzata)'
);

-- =========================================================
-- 2) Recupero tipi indirizzo RES / SEDELEG / SEDEOP
-- =========================================================
CREATE TEMP TABLE tmp_tipi_indirizzo_guard AS
SELECT
    ti.id,
    ti.codice_interno,
    ti.codice,
    ti.descrizione
FROM config.tipi_indirizzi ti
WHERE ti.codice_interno IN ('RES', 'SEDELEG', 'SEDEOP');

SELECT ok(
    (SELECT count(*) FROM tmp_tipi_indirizzo_guard) >= 2,
    'Esistono almeno RES e SEDELEG in config.tipi_indirizzi (eventualmente anche SEDEOP)'
);

-- comodo avere le 3 righe “esplicite”
CREATE TEMP TABLE tmp_tipo_res_guard AS
SELECT * FROM tmp_tipi_indirizzo_guard WHERE codice_interno = 'RES';

CREATE TEMP TABLE tmp_tipo_sedeleg_guard AS
SELECT * FROM tmp_tipi_indirizzo_guard WHERE codice_interno = 'SEDELEG';

CREATE TEMP TABLE tmp_tipo_sedeop_guard AS
SELECT * FROM tmp_tipi_indirizzo_guard WHERE codice_interno = 'SEDEOP';

-- =========================================================
-- 3) indirizzo_dettaglio di test
-- =========================================================
-- Rev 2026-11-03: dal builder, non da un upsert scritto a mano che ne
-- ricopiava la logica (stradario di seed + ON CONFLICT sulla chiave
-- normalizzata).
CREATE TEMP TABLE tmp_indirizzo_dettaglio_guard AS
SELECT dbops.fn_pgtap_crea_indirizzo_dettaglio('fallback') AS id;

SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzo_dettaglio_guard),
    1,
    'Upsert indirizzo_dettaglio_guard: ottenuto esattamente 1 id (nuovo o esistente)'
);

-- =========================================================
-- 4) Pulizia pre-test: elimino RES / SEDELEG / SEDEOP per il soggetto_ruolo del Gestore
-- =========================================================
DELETE FROM anagrafiche.indirizzi i
USING tmp_gestore_guard g, tmp_tipi_indirizzo_guard t
WHERE i.soggetto_ruolo_id = g.soggetto_ruolo_id
  AND i.tipo_indirizzo_id = t.id;

SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_gestore_guard g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipi_indirizzo_guard t
          ON t.id = i.tipo_indirizzo_id
    ),
    0,
    'Pre-condizione: nessun indirizzo RES/SEDELEG/SEDEOP per il soggetto_ruolo del Gestore'
);

-- =========================================================
-- 5) Inserimento RES per Gestore: deve FALLIRE (guard)
-- =========================================================
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.indirizzi (
        soggetto_ruolo_id,
        tipo_indirizzo_id,
        indirizzo_dettaglio_id,
        indirizzo_libero,
        stato_id,
        administrative_area,
        locality,
        sublocality,
        postal_code,
        geoloc,
        comune_id,
        codice_postale_id,
        storicizza
    )
    SELECT
        g.soggetto_ruolo_id,
        t.id,
        idd.id,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        FALSE
    FROM tmp_gestore_guard g
    JOIN tmp_tipo_res_guard t
      ON TRUE
    JOIN tmp_indirizzo_dettaglio_guard idd
      ON TRUE;
    $$,
    NULL,  -- errcode: qualsiasi
    NULL,  -- errmsg: qualsiasi
    'Guard blocca RES per il Gestore (tipo non ammesso in matrice)'
);

-- Nessun indirizzo RES deve essere stato inserito
SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_gestore_guard g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipo_res_guard t
          ON t.id = i.tipo_indirizzo_id
    ),
    0,
    'Dopo tentativo RES fallito: ancora nessun indirizzo RES per il Gestore'
);

-- =========================================================
-- 6) Inserimento SEDELEG per Gestore: deve andare a buon fine
-- =========================================================
INSERT INTO anagrafiche.indirizzi (
    soggetto_ruolo_id,
    tipo_indirizzo_id,
    indirizzo_dettaglio_id,
    indirizzo_libero,
    stato_id,
    administrative_area,
    locality,
    sublocality,
    postal_code,
    geoloc,
    comune_id,
    codice_postale_id,
    storicizza
)
SELECT
    g.soggetto_ruolo_id,
    t.id,
    idd.id,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    FALSE
FROM tmp_gestore_guard g
JOIN tmp_tipo_sedeleg_guard t
  ON TRUE
JOIN tmp_indirizzo_dettaglio_guard idd
  ON TRUE;

SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_gestore_guard g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipo_sedeleg_guard t
          ON t.id = i.tipo_indirizzo_id
    ),
    1,
    'Inserimento SEDELEG per Gestore riuscito: 1 indirizzo SEDELEG presente'
);

-- =========================================================
-- 7) Test fallback fn_get_indirizzo: richiesta SEDEOP → ritorna SEDELEG
-- =========================================================

-- Se non hai configurato SEDEOP in tipi_indirizzi / matrice, puoi saltare questo step.
-- Qui assumiamo:
--   - in config.tipi_ruolo_tipi_indirizzo per GE:
--       SEDEOP has fallback_tipo_indirizzo_id = SEDELEG

-- Il tipo si confronta per id (rev 2026-11-01): tipo_indirizzo e' il codice
-- di display, che l'utente puo' rinominare; la funzione non espone il
-- codice interno.
SELECT results_eq(
    $$
    SELECT tipo_indirizzo_id
    FROM script.fn_get_indirizzo(
        (SELECT soggetto_ruolo_id FROM tmp_gestore_guard),
        'SEDEOP'
    )
    ORDER BY tipo_indirizzo_id
    $$,
    $$
    SELECT id FROM tmp_tipo_sedeleg_guard
    $$,
    'fn_get_indirizzo: richiesta SEDEOP per Gestore usa fallback SEDELEG'
);

-- =========================================================
-- 8) fn_get_indirizzi_by_ruolo: set coerente con vista base scope=RUOLO
-- =========================================================
SELECT results_eq(
    $$
    SELECT f.tipo_indirizzo, f.indirizzo_id
    FROM script.fn_get_indirizzi_by_ruolo(
        (SELECT soggetto_ruolo_id FROM tmp_gestore_guard)
    ) f
    ORDER BY f.tipo_indirizzo, f.indirizzo_id
    $$,
    $$
    SELECT r.tipo_indirizzo_codice, r.indirizzo_id
    FROM anagrafiche.vw_indirizzi_resolved_base r
    WHERE r.scope = 'RUOLO'
      AND r.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM tmp_gestore_guard)
    ORDER BY r.tipo_indirizzo_codice, r.indirizzo_id
    $$,
    'fn_get_indirizzi_by_ruolo: risultato allineato a vw_indirizzi_resolved_base (scope=RUOLO)'
);

-- =========================================================
-- 9) fn_get_indirizzi_by_ruolo: presenza SEDELEG inserito nel test
-- =========================================================
SELECT is(
    (
      SELECT count(*)::int
      FROM script.fn_get_indirizzi_by_ruolo(
          (SELECT soggetto_ruolo_id FROM tmp_gestore_guard)
      ) f
      WHERE f.tipo_indirizzo_id = (SELECT id FROM tmp_tipo_sedeleg_guard)  -- per id, non sul display
    ),
    1,
    'fn_get_indirizzi_by_ruolo include SEDELEG del soggetto_ruolo di test'
);

-- =========================================================
-- 10) fn_get_indirizzi_by_soggetto: set coerente con vista base scope=SOGGETTO
-- =========================================================
SELECT results_eq(
    $$
    SELECT f.tipo_indirizzo_codice, f.indirizzo_id
    FROM script.fn_get_indirizzi_by_soggetto(
      (SELECT soggetto_id FROM tmp_gestore_guard)
    ) f
    ORDER BY f.tipo_indirizzo_codice, f.indirizzo_id
    $$,
    $$
    SELECT r.tipo_indirizzo_codice, r.indirizzo_id
    FROM anagrafiche.vw_indirizzi_resolved_base r
    WHERE r.scope = 'SOGGETTO'
      AND r.soggetto_id = (SELECT soggetto_id FROM tmp_gestore_guard)
    ORDER BY r.tipo_indirizzo_codice, r.indirizzo_id
    $$,
    'fn_get_indirizzi_by_soggetto: risultato allineato a vw_indirizzi_resolved_base (scope=SOGGETTO)'
);

-- =========================================================
-- 11) vw_indirizzi_resolved_all: source valorizzato solo RUOLO/SOGGETTO
-- =========================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM anagrafiche.vw_indirizzi_resolved_all a
    WHERE a.source IS NULL
       OR a.source NOT IN ('RUOLO', 'SOGGETTO')
  ),
  'vw_indirizzi_resolved_all: source sempre valorizzato e nel dominio RUOLO/SOGGETTO'
);

-- =========================================================
-- 12) vw_indirizzi_resolved_all: riga SEDELEG di ruolo marcata source=RUOLO
-- =========================================================
SELECT is(
  (
    SELECT count(*)::int
    FROM anagrafiche.vw_indirizzi_resolved_all a
    WHERE a.soggetto_ruolo_id = (SELECT soggetto_ruolo_id FROM tmp_gestore_guard)
      AND a.tipo_indirizzo_codice_interno = 'SEDELEG'  -- rev 2026-11-01: il codice interno, non il display
      AND a.source = 'RUOLO'
  ),
  1,
  'vw_indirizzi_resolved_all: SEDELEG del ruolo di test ha source=RUOLO'
);

-- =========================================================
-- 13) Partizionamento viste: ALL = RUOLO + SOGGETTO
-- =========================================================
SELECT ok(
  (
    SELECT count(*) FROM anagrafiche.vw_indirizzi_resolved_all
  ) = (
    (SELECT count(*) FROM anagrafiche.vw_indirizzi_resolved_ruolo) +
    (SELECT count(*) FROM anagrafiche.vw_indirizzi_resolved_soggetto)
  ),
  'vw_indirizzi_resolved_all coerente con union logica di ruolo+soggetto'
);

-- Fine test
SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
