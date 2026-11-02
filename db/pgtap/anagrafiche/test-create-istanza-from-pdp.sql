-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Scopo:
--  - Recuperare un PDP esistente (GAS)
--  - Recuperare un soggetto qualsiasi esistente
--  - Creare una istanza_utility collegata al PDP
--  - Verificare coerenza indirizzo e legami FK
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

SELECT plan(9);


-- =========================================================
--  Pulizia preliminare: rimuove eventuali istanze_utility di test
-- =========================================================

delete from anagrafiche.istanze_utilities
where codice = 'TEST-IU-PDP-001';

-- =========================================================
-- 0) Recupero una utility GAS (precondizione)
-- =========================================================
CREATE TEMP TABLE tmp_utility_gas AS
SELECT id
FROM config.utilities
WHERE codice_interno = 'GAS'
LIMIT 1;

SELECT is(
    (SELECT count(*)::int FROM tmp_utility_gas),
    1,
    'Esiste almeno una utility con codice_interno = GAS'
);

-- =========================================================
-- 1) Un PDP GAS con indirizzo, COSTRUITO
-- =========================================================
-- ⛔ 2026-09-23: il PDP era «il primo GAS con un indirizzo» e il soggetto
--   quello con codice 'TST-PR-001', entrambi dati di QUESTA macchina: su un
--   database ricostruito dai changelog non ci sono, e il file moriva sulle
--   precondizioni (7 asserzioni rosse). Ora si COSTRUISCONO.
CREATE TEMP TABLE tmp_pdp_test AS
SELECT p.pdp_id AS id,
       p.indirizzo_dettaglio_id
FROM dbops.fn_pgtap_crea_pdp('GAS') p;

SELECT is(
    (SELECT count(*)::int FROM tmp_pdp_test WHERE indirizzo_dettaglio_id IS NOT NULL),
    1,
    'Costruito un PDP GAS con indirizzo_dettaglio_id valorizzato'
);

-- =========================================================
-- 2) Un soggetto, COSTRUITO
-- =========================================================
CREATE TEMP TABLE tmp_soggetto_test AS
SELECT dbops.fn_pgtap_crea_soggetto_pg('Istanza da PDP') AS id;

SELECT is(
    (SELECT count(*)::int FROM tmp_soggetto_test WHERE id IS NOT NULL),
    1,
    'Costruito il soggetto da usare per l’istanza_utility'
);

-- =========================================================
-- 3) Creazione istanza_utility collegata al PDP
--    - fittizia = TRUE
--    - indirizzo_dettaglio_id = stesso del PDP
--    - pdp_id = id del PDP
-- =========================================================
-- ⭐ FINESTRA DIFFERITA. Un'istanza utility non e' un INSERT, e' una SAGA:
--   `trg_istanze_utilities_z90_require_utility_dichiarata_ins` e' un
--   CONSTRAINT TRIGGER DEFERRABLE INITIALLY DEFERRED che al COMMIT pretende
--   il billing account (dal 2026-10-08, brief-db-istanza-nasce-col-ba R-1:
--   prima bastava un satellite qualunque) — un'istanza senza BA non e' uno
--   stato legale del modello.
--   Il preambolo obbligatorio (SET CONSTRAINTS ALL IMMEDIATE) lo fa scattare sul
--   PRIMO insert, cioe' prima che il satellite possa esistere: e' li' che questo
--   file moriva, con ZERO asserzioni eseguite.
--   Si apre la finestra, si costruisce l'istanza CON il suo satellite, e si
--   RICHIUDE: la verifica non si perde, si sposta dove il modello la vuole.
-- Il ruolo CLIENTE del soggetto, che il BA pretende: si crea PRIMA di aprire
-- la finestra, perche' gli helper dbops.fn_pgtap_* escono con i vincoli
-- IMMEDIATE e dentro la finestra farebbero scattare il controllo
-- dell'istanza prima che il BA esista. ⛔ Si legge in un'istruzione separata.
CREATE TEMP TABLE tmp_sr_test AS
SELECT dbops.fn_pgtap_crea_soggetto_ruolo(s.id, 'CL'::character varying) AS soggetto_ruolo_id
  FROM tmp_soggetto_test s;

SET CONSTRAINTS ALL DEFERRED;

WITH ins AS (
    INSERT INTO anagrafiche.istanze_utilities (
        fittizia,
        codice,
        proprietario_inquilino,
        soggetto_id,
        indirizzo_dettaglio_id,
        pdp_id
    )
    SELECT
        FALSE,                               -- fittizia
        'TEST-IU-PDP-001',                  -- codice di test
        'I',                                -- inquilino (valore di default logico)
        s.id,                               -- soggetto di test
        p.indirizzo_dettaglio_id,           -- indirizzo coerente col PDP
        p.id                                -- collegamento al PDP
    FROM tmp_soggetto_test s,
         tmp_pdp_test p
    RETURNING id,
              soggetto_id,
              indirizzo_dettaglio_id,
              pdp_id
)
SELECT *
INTO TEMP TABLE tmp_istanza_test
FROM ins;

-- Il billing account GAS: qui serve a rendere l'istanza uno stato legale,
-- non e' il soggetto del test. ⚠️ rev 2026-10-08 (brief-db-istanza-nasce-col-ba,
-- R-1): fino a quel giorno il satellite era la riga precontrattuale, «la piu'
-- leggera»; ora quella riga pretende il BA della sua coppia, e il BA a sua
-- volta il ruolo CLIENTE del soggetto (D-3: il ruolo nasce con l'istanza).
INSERT INTO anagrafiche.billing_account
    (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id)
SELECT i.id,
       (SELECT soggetto_ruolo_id FROM tmp_sr_test),
       u.id,
       (SELECT cc.id FROM anagrafiche.categorie_clienti cc
         WHERE cc.codice_interno = 'STANDARD')
  FROM tmp_istanza_test i, tmp_utility_gas u;

-- Saga completa: il guard differito scatta QUI, su un'istanza finita.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT is(
    (SELECT count(*)::int FROM tmp_istanza_test),
    1,
    'Inserita esattamente 1 istanza_utility collegata al PDP'
);

-- =========================================================
-- 4) Verifica coerenza indirizzo istanza ↔ PDP
-- =========================================================
SELECT results_eq(
    $$
    SELECT
        i.indirizzo_dettaglio_id::bigint,
        i.pdp_id::bigint
    FROM tmp_istanza_test i
    $$,
    $$
    SELECT
        p.indirizzo_dettaglio_id::bigint,
        p.id::bigint
    FROM tmp_pdp_test p
    $$,
    'istanza_utility.indirizzo_dettaglio_id e pdp_id coerenti con anagrafiche.pdp'
);

-- =========================================================
-- 5) Verifica esistenza delle righe collegate (FK logica)
-- =========================================================
SELECT ok(
    EXISTS (
        SELECT 1
        FROM anagrafiche.istanze_utilities iu
        JOIN anagrafiche.pdp p
          ON p.id = iu.pdp_id
         AND p.indirizzo_dettaglio_id = iu.indirizzo_dettaglio_id
        JOIN anagrafiche.soggetti s
          ON s.id = iu.soggetto_id
        WHERE iu.id = (SELECT id FROM tmp_istanza_test)
    ),
    'Istanza_utility è collegata coerentemente a PDP e Soggetto'
);

-- =========================================================
-- 6) Verifica vincolo implicito su indirizzo (pdp_id → indirizzo non nullo)
--    (ridondante rispetto alla FK, ma esplicito a livello di test)
-- =========================================================
SELECT ok(
    (
        SELECT indirizzo_dettaglio_id IS NOT NULL
        FROM anagrafiche.istanze_utilities
        WHERE id = (SELECT id FROM tmp_istanza_test)
    ),
    'Per istanza_utility con pdp_id valorizzato, indirizzo_dettaglio_id è NOT NULL'
);


-- =========================================================
-- 7) Non è consentito mettere fittizia = TRUE se pdp_id NON è NULL
-- =========================================================

-- Precondizione: l'istanza di test esiste e ha pdp_id valorizzato
SELECT is(
    (
        SELECT count(*)::int
        FROM anagrafiche.istanze_utilities
        WHERE codice = 'TEST-IU-PDP-001'
          AND pdp_id IS NOT NULL
    ),
    1,
    'Esiste esattamente 1 istanza TEST-IU-PDP-001 con pdp_id valorizzato'
);

-- Tentativo di violare il vincolo: deve sollevare errore di CHECK (23514)
SELECT throws_ok(
    $$
    UPDATE anagrafiche.istanze_utilities
       SET fittizia = TRUE
     WHERE codice = 'TEST-IU-PDP-001';
    $$,
    '23514',                                      -- check_violation
     NULL,                   -- oppure NULL / '' se vuoi ignorare il messaggio
    'threw 23514 per vincolo chk_iu_pdp_not_fittizia'
);



-- Fine test
SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
