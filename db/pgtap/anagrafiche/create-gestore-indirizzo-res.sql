-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: ruolo Gestore + abbinamento indirizzo di SEDE OPERATIVA
--       con indirizzo normalizzato in anagrafiche.indirizzi_dettaglio
--       e associazione in anagrafiche.indirizzi
--
-- Scenario:
--   - Prende il Gestore dell'installazione, o lo costruisce se non c'e'
--     (dbops.fn_pgtap_crea_gestore)
--   - Recupera il tipo indirizzo 'SEDEOP' da config.tipi_indirizzi
--   - Crea un indirizzo_dettaglio dedicato (indirizzo normalizzato di test)
--   - Crea un indirizzo di sede operativa per il Gestore in anagrafiche.indirizzi
--   - Verifica coerenza ruolo, tipo, dettaglio normalizzato e tx_id
--   - Verifica che RES (residenza) su un GESTORE sia RESPINTO
-- ------------------------------------------------------------

-- ============================================================================
-- rev 2026-08-18 — bonifica baseline. Il file era NON TRANSAZIONALE: chiudeva
-- in COMMIT e lasciava nel database l'indirizzo di prova. Alla corsa dopo tre
-- DELETE di «pulizia preventiva» provavano a toglierlo e fallivano — il
-- dettaglio normalizzato era ormai referenziato da anagrafiche.indirizzi
-- (fk_indirizzi_dettaglio, RESTRICT). Il file moriva alla riga 81 con ZERO
-- asserzioni eseguite.
--
-- Ora: BEGIN ... ROLLBACK e le tre pulizie spariscono — il ROLLBACK e' la
-- garanzia. Qui non serve l'helper dei soggetti: il test non ne crea, legge il
-- gestore che c'e'.
-- rev 2026-09-23 — il gestore si costruisce (brief-db-fixture-che-costruiscono-
-- giro-2, lotto 2). Il file leggeva MIN(id) da anagrafiche.gestori, che e' dato
-- di MACCHINA: su un database ricostruito (la CI) e' vuota, e il file moriva al
-- test 1 con cinque asserzioni su otto rosse. Ora il gestore lo da'
-- dbops.fn_pgtap_crea_gestore(): lo PRENDE se c'e' (dbdev: nessuna scrittura),
-- lo COSTRUISCE se non c'e'. Costruito, ha SEDELEG e FATT come ogni GE (sono
-- gli obbligatori, il guard differito li pretende): il punto 2 qui sotto vale
-- anche per lui.
--
-- ⚠️ E il tipo indirizzo e' passato da RES a SEDEOP. Non e' cosmesi, sono due
-- fatti in fila che il test non controllava:
--   1. RES (residenza) NON e' ammesso per il ruolo GESTORE —
--      config.tipi_ruolo_tipi_indirizzo per GE prevede SEDELEG (obbligatorio),
--      FATT (obbligatorio) e SEDEOP. Una residenza su una societa' non vuol
--      dire niente, e il guard la respinge;
--   2. dei tre ammessi, SEDELEG e FATT il gestore LI HA GIA' — sono gli
--      obbligatori — e uq_indirizzi_ruolo_tipo_no_istanza e' UNIQUE su
--      (soggetto_ruolo_id, tipo_indirizzo_id). Resta SEDEOP, l'unico che il
--      ruolo ammette e non ha.
-- Il soggetto del test — indirizzo NORMALIZZATO agganciato al ruolo via
-- indirizzi_dettaglio, con tx_id e coerenza — e' intatto: era stale la scelta
-- del tipo, non cio' che il file verifica.
-- ============================================================================

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- =========================================================
-- Costanti per il test (TEMP TABLE)
-- (le teniamo, anche se non le usiamo più in pulizia)
-- =========================================================
-- ⚠️ rev 2026-08-18: il CIVICO e' unico per corsa. uq_indirizzi_dettaglio_norm_v2
--   e' UNIQUE su (stradario_id, civico, estensione, palazzina, scala, piano...):
--   con un civico fisso la corsa sbatteva sul dettaglio lasciato dal COMMIT
--   della corsa precedente, che non si puo' cancellare perche' nel frattempo e'
--   referenziato da anagrafiche.indirizzi. Con un civico diverso ogni volta il
--   residuo resta li' e non da' piu' fastidio a nessuno.
CREATE TEMP TABLE tmp_costanti_indirizzo_gestore AS
SELECT
    'VIA TEST RESIDENZA GESTORE'::text AS via_norm_test,
    (1000 + (abs(hashtext(clock_timestamp()::text)) % 90000))::text AS civico_norm_test,
    NULL::text                        AS interno_test,
    NULL::text                        AS piano_test,
    NULL::text                        AS palazzina_test;

-- 0) Il Gestore che si usera' nel test: preso o costruito.
--    ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA: il JOIN
--    su soggetti sta nella temp table sotto, non qui.
CREATE TEMP TABLE tmp_first_gestore AS
SELECT gestore_id FROM dbops.fn_pgtap_crea_gestore('indirizzo SEDEOP');

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

-- Test 1: il Gestore c'e' (preso o costruito) e si legge col suo soggetto
SELECT ok(
    (SELECT count(*) FROM tmp_gestore) = 1,
    'Il Gestore dell''installazione c''e'' (preso o costruito) e si legge col suo soggetto'
);

-- ---------------------------------------------------------
-- 2) Recupero del tipo indirizzo SEDEOP (sede operativa)
-- ---------------------------------------------------------
CREATE TEMP TABLE tmp_tipo_indirizzo_res AS  -- nome storico: ora contiene SEDEOP
SELECT
    ti.id,
    ti.codice_interno,
    ti.codice,
    ti.descrizione
FROM config.tipi_indirizzi ti
WHERE ti.codice_interno = 'SEDEOP'
ORDER BY ti.id
LIMIT 1;

-- Test 2: esiste almeno un tipo indirizzo con codice_interno = ''SEDEOP''
SELECT ok(
    (SELECT count(*) FROM tmp_tipo_indirizzo_res) = 1,
    'Esiste almeno un tipo indirizzo SEDEOP in config.tipi_indirizzi (ammesso per il ruolo GESTORE)'
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
        -- ⚠️ civico UNICO PER CORSA: e' questa la colonna dentro
        --   uq_indirizzi_dettaglio_norm_v2, non civico_norm.
        k.civico_norm_test::integer,     -- civico numerico, diverso a ogni corsa
        NULL,                            -- estensione_civico
        k.palazzina_test,
        k.interno_test,
        k.piano_test,
        NULL,                            -- civic_geoloc
        'Indirizzo test SEDEOP Gestore (pgTAP)', -- altro (nota per riconoscere test)
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
-- 5) Inserimento indirizzo di sede operativa per il ruolo Gestore
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
        NULL,                    -- indirizzo_libero NULL (usiamo solo indirizzo normalizzato)
        g.soggetto_stato_id,     -- stato dal soggetto del Gestore
        NULL,                    -- administrative_area (non usata per IT)
        NULL,                    -- locality
        NULL,                    -- sublocality
        NULL,                    -- postal_code
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
          AND idd.altro = 'Indirizzo test SEDEOP Gestore (pgTAP)'
    ),
    'L’indirizzo di sede operativa del Gestore è coerente (ruolo, tipo, dettaglio normalizzato di test, nessun indirizzo_libero, tx_id valorizzato)'
);

-- ---------------------------------------------------------
-- 8) ⭐ La regola che questo file ha scoperto diventa un presidio.
--
-- Il test nasceva per dare al Gestore un indirizzo RES, e RES su un GESTORE
-- non e' ammesso: config.tipi_ruolo_tipi_indirizzo per GE prevede SEDELEG,
-- FATT e SEDEOP, non la residenza — che su una societa' non vuol dire niente.
-- Invece di limitarsi a cambiare tipo e dimenticare la cosa, qui si asserisce
-- il divieto: se un giorno qualcuno aggiungesse RES alla matrice di GE senza
-- accorgersene, questo test lo direbbe.
-- ---------------------------------------------------------
SELECT throws_ok(
    $$
    INSERT INTO anagrafiche.indirizzi (
        soggetto_ruolo_id, tipo_indirizzo_id, istanza_utility_id,
        indirizzo_libero, stato_id, comune_id, codice_postale_id, locality, postal_code
    )
    SELECT g.soggetto_ruolo_id, ti.id, NULL,
           'Via pgTAP residenza illegittima', g.soggetto_stato_id,
           (dbops.fn_pgtap_indirizzo_libero_forma(g.soggetto_stato_id)).*  -- rev 2026-10-18: la forma dello stato
      FROM tmp_gestore g,
           config.tipi_indirizzi ti
     WHERE ti.codice_interno = 'RES';
    $$,
    'P0001',
    NULL,
    'Un indirizzo RES (residenza) su un ruolo GESTORE viene respinto: non e'' nella matrice del ruolo'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'.
-- ⚠️ finish() sta PRIMA: pgTAP tiene il suo stato in una temp table, e dopo il
-- ROLLBACK non esiste piu'.
ROLLBACK;
