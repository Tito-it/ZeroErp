-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: ruolo Gestore + abbinamento indirizzo RES (residenza)
--       con indirizzo normalizzato in anagrafiche.indirizzi_dettaglio
--       e associazione in anagrafiche.indirizzi
--
-- Scenario:
--   - Legge automaticamente il primo Gestore da anagrafiche.gestori
--     (via anagrafiche.soggetti_ruoli + anagrafiche.soggetti)
--   - Recupera il tipo indirizzo 'RES' da config.tipi_indirizzi
--   - Crea un indirizzo_dettaglio dedicato (indirizzo normalizzato di test)
--   - Crea un indirizzo RES per il Gestore in anagrafiche.indirizzi
--   - Verifica coerenza ruolo, tipo, dettaglio normalizzato e tx_id
-- ------------------------------------------------------------

-- Numero di test che ci aspettiamo di eseguire
SELECT plan(7);

-- =========================================================
-- Costanti per il test (TEMP TABLE)
-- (le teniamo, anche se non le usiamo più in pulizia)
-- =========================================================
CREATE TEMP TABLE tmp_costanti_indirizzo_gestore AS
SELECT
    'VIA TEST RESIDENZA GESTORE'::text AS via_norm_test,
    '1'::text                         AS civico_norm_test,
    NULL::text                        AS interno_test,
    NULL::text                        AS piano_test,
    NULL::text                        AS palazzina_test;

-- =========================================================
-- Pulizia preventiva di eventuali residui (indirizzo test)
-- =========================================================

-- 0) Identifico il Gestore che userò nel test (il primo per id)
CREATE TEMP TABLE tmp_first_gestore AS
SELECT
    MIN(id) AS gestore_id
FROM anagrafiche.gestori;

-- 1) Elimino QUALSIASI indirizzo RES esistente per il Gestore scelto
DELETE FROM anagrafiche.indirizzi i
USING anagrafiche.soggetti_ruoli sr,
      anagrafiche.gestori g,
      config.tipi_indirizzi ti,
      tmp_first_gestore fg
WHERE i.soggetto_ruolo_id = sr.id
  AND g.soggetto_ruolo_id = sr.id
  AND g.id = fg.gestore_id
  AND i.tipo_indirizzo_id = ti.id
  AND ti.codice_interno = 'RES';

-- 2) Elimino eventuali indirizzi RES del Gestore che puntano
--    a un indirizzo_dettaglio marcato come test
DELETE FROM anagrafiche.indirizzi i
USING anagrafiche.soggetti_ruoli sr,
      anagrafiche.gestori g,
      config.tipi_indirizzi ti,
      anagrafiche.indirizzi_dettaglio idd,
      tmp_first_gestore fg
WHERE i.soggetto_ruolo_id = sr.id
  AND g.soggetto_ruolo_id = sr.id
  AND g.id = fg.gestore_id
  AND i.tipo_indirizzo_id = ti.id
  AND ti.codice_interno = 'RES'
  AND i.indirizzo_dettaglio_id = idd.id
  AND idd.altro = 'Indirizzo test RES Gestore (pgTAP)';

-- 3) Elimino eventuali indirizzi_dettaglio di test rimasti orfani
DELETE FROM anagrafiche.indirizzi_dettaglio idd
WHERE idd.altro = 'Indirizzo test RES Gestore (pgTAP)';

-- =========================================================
-- Inizio transazione “applicativa”
-- =========================================================
BEGIN;

-- ---------------------------------------------------------
-- 1) Recupero del Gestore (con soggetto e stato/comune)
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_gestore AS
SELECT
    g.id                AS gestore_id,
    g.soggetto_ruolo_id AS soggetto_ruolo_id,
    sr.soggetto_id      AS soggetto_id,
    s.stato_id          AS soggetto_stato_id,
    s.comune_id         AS soggetto_comune_id
FROM anagrafiche.gestori g
JOIN tmp_first_gestore fg
  ON g.id = fg.gestore_id
JOIN anagrafiche.soggetti_ruoli sr
  ON sr.id = g.soggetto_ruolo_id
JOIN anagrafiche.soggetti s
  ON s.id = sr.soggetto_id;

-- Test 1: esiste almeno un Gestore
SELECT ok(
    (SELECT count(*) FROM tmp_gestore) = 1,
    'Esiste almeno un Gestore in anagrafiche.gestori (letto il primo disponibile)'
);

-- ---------------------------------------------------------
-- 2) Recupero del tipo indirizzo RES (residenza)
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_tipo_indirizzo_res AS
SELECT
    ti.id,
    ti.codice_interno,
    ti.codice,
    ti.descrizione
FROM config.tipi_indirizzi ti
WHERE ti.codice_interno = 'RES'
ORDER BY ti.id
LIMIT 1;

-- Test 2: esiste almeno un tipo indirizzo con codice_interno = ''RES''
SELECT ok(
    (SELECT count(*) FROM tmp_tipo_indirizzo_res) = 1,
    'Esiste almeno un tipo indirizzo RES in config.tipi_indirizzi (codice_interno = ''RES'')'
);

-- ---------------------------------------------------------
-- 3) Recupero di uno stradario da usare per indirizzo_dettaglio
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_stradario AS
SELECT
    s.id
FROM config.stradario s
ORDER BY s.id
LIMIT 1;

-- Test 3: esiste almeno uno stradario
SELECT ok(
    (SELECT count(*) FROM tmp_stradario) = 1,
    'Esiste almeno un record in config.stradario da usare per indirizzi_dettaglio'
);

-- ---------------------------------------------------------
-- 4) Inserimento indirizzo_dettaglio per il Gestore
-- ---------------------------------------------------------
WITH nuovo_indirizzo_dettaglio AS (
    INSERT INTO anagrafiche.indirizzi_dettaglio (
        stradario_id,
        civico,
        estensione_civico,
        palazzina,
        interno,
        piano,
        civic_geoloc,
        altro,
        via_norm,
        civico_norm,
        street_geoloc,
        scala,
        attivo,
        storicizza
    )
    SELECT
        s.id,                            -- stradario_id
        1,                               -- civico numerico fittizio
        NULL,                            -- estensione_civico
        k.palazzina_test,
        k.interno_test,
        k.piano_test,
        NULL,                            -- civic_geoloc
        'Indirizzo test RES Gestore (pgTAP)', -- altro (nota per riconoscere test)
        k.via_norm_test,
        k.civico_norm_test,
        NULL,                            -- street_geoloc
        NULL,                            -- scala
        TRUE,                            -- attivo
        FALSE                            -- storicizza
    FROM tmp_stradario s,
         tmp_costanti_indirizzo_gestore k
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_indirizzo_dettaglio_gestore
FROM nuovo_indirizzo_dettaglio;

-- Test 4: indirizzo_dettaglio inserito
SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzo_dettaglio_gestore),
    1,
    'Inserito esattamente 1 indirizzo_dettaglio per il Gestore (indirizzo normalizzato di test)'
);

-- ---------------------------------------------------------
-- 5) Inserimento indirizzo RES per il ruolo Gestore
-- ---------------------------------------------------------
WITH nuovo_indirizzo AS (
    INSERT INTO anagrafiche.indirizzi (
        soggetto_ruolo_id,
        tipo_indirizzo_id,
        indirizzo_dettaglio_id,
        indirizzo_libero,
        stato_id,
        administrative_area,
        locality,
        sublocality,
        postal_box,
        geoloc,
        comune_id,
        codice_postale_id,
        storicizza
    )
    SELECT
        g.soggetto_ruolo_id,
        t.id,
        idd.id,
        NULL,                    -- indirizzo_libero NULL (usiamo solo indirizzo normalizzato)
        g.soggetto_stato_id,     -- stato dal soggetto del Gestore
        NULL,                    -- administrative_area (non usata per IT)
        NULL,                    -- locality
        NULL,                    -- sublocality
        NULL,                    -- postal_box
        NULL,                    -- geoloc (verrà eventualmente sincronizzata dal trigger)
        g.soggetto_comune_id,    -- comune_id (se valorizzato sul soggetto)
        NULL,                    -- codice_postale_id (non imposto nel test)
        FALSE                    -- storicizza: non vogliamo snapshot al primo update
    FROM tmp_gestore g,
         tmp_tipo_indirizzo_res t,
         tmp_indirizzo_dettaglio_gestore idd
    RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_indirizzo_gestore
FROM nuovo_indirizzo;

-- Test 5: indirizzo inserito
SELECT is(
    (SELECT count(*)::int FROM tmp_indirizzo_gestore),
    1,
    'Inserito esattamente 1 indirizzo RES per il ruolo Gestore'
);

-- ---------------------------------------------------------
-- 6) Verifica univocità per (soggetto_ruolo_id, tipo_indirizzo_id)
-- ---------------------------------------------------------
SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.indirizzi i
        JOIN tmp_gestore g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipo_indirizzo_res t
          ON t.id = i.tipo_indirizzo_id
    ),
    1,
    'Esiste esattamente 1 indirizzo RES per il ruolo Gestore (vincolo uq_indirizzi_ruolo_tipo rispettato)'
);

-- ---------------------------------------------------------
-- 7) Verifica di coerenza indirizzo (ruolo, tipo, dettaglio, tx_id)
-- ---------------------------------------------------------
SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.indirizzi i
        JOIN tmp_indirizzo_gestore tig
          ON tig.id = i.id
        JOIN tmp_gestore g
          ON g.soggetto_ruolo_id = i.soggetto_ruolo_id
        JOIN tmp_tipo_indirizzo_res t
          ON t.id = i.tipo_indirizzo_id
        JOIN anagrafiche.indirizzi_dettaglio idd
          ON idd.id = i.indirizzo_dettaglio_id
        WHERE i.indirizzo_libero IS NULL
          AND i.tx_id IS NOT NULL  -- trigger dbops.trgfn_tx_id_managed
          AND idd.altro = 'Indirizzo test RES Gestore (pgTAP)'
    ),
    'L’indirizzo RES del Gestore è coerente (ruolo, tipo, dettaglio normalizzato di test, nessun indirizzo_libero, tx_id valorizzato)'
);

-- Forzo la verifica dei constraint DEFERRABLE (se presenti)
SET CONSTRAINTS ALL IMMEDIATE;

COMMIT;

-- Fine test
SELECT * FROM finish();
