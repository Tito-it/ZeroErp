-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_get_next_progressivo (reset annuale + CANCELLO di monotonia)
-- ------------------------------------------------------------
-- Indice test
-- 1)  Inserimento registro di test
-- 2)  Primo progressivo anno 2025 = 1
-- 3)  Secondo progressivo anno 2025 = 2
-- 4)  Primo progressivo anno 2026 = 1 (reset)
-- 5)  Esistenza righe progressivi 2025/2026
-- 6)  ultima_data valorizzata a ogni numero emesso, riga per riga  (DB-7)
-- 7)  Stessa data dell'ultimo numerato: AMMESSA                    (decisione 7)
-- 8)  Il pavimento SALE con una data successiva
-- 9)  Data anteriore nello stesso anno -> rifiutata (SQLSTATE)
-- 10) ... e la FRASE nomina la data da cui ripartire (throws_like)
-- 11) CROSS-ANNO: data dell'anno precedente -> rifiutata lo stesso
-- 12) Due serie sullo stesso registro non si bloccano a vicenda
-- 13) fn_get_pavimento_sequenza risolve la serie dal serie_default
-- 14) Cleanup completato
-- ------------------------------------------------------------
-- Scopo:
--  - il progressivo riparte per anno (comportamento storico);
--  - ⭐ dal 2026-08-25 il numero NON si consegna a un documento la cui data e'
--    anteriore all'ultima gia' numerata sullo stesso (registro, serie).
--
-- ⚠️ COSA QUESTO FILE **NON** PUO' PROVARE, ed e' scritto qui invece di essere
--   scoperto da chi verra' dopo: che il cancello stia SOTTO l'advisory lock.
--   pgTAP e' mono-sessione, il lock non si contende, e spostando il controllo
--   PRIMA del lock questo file resterebbe interamente VERDE. La posizione si
--   presidia in review e la si legge nel changeSet 20260825-11 — e' la stessa
--   lezione gia' scritta in testa a test-numerazione-guard-coerenza-v1.sql sul
--   guard D-K.
--   Cio' che questo file prova e' il PREDICATO: quali date passano e quali no.
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

SELECT plan(14);

-- ============================================================
-- 0) Costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_reg AS
SELECT
  'pgtap_registri_progressivi'::text AS test_scope;

-- ============================================================
-- 1) Inserimento registro di test
-- ============================================================
CREATE TEMP TABLE tmp_registro AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione (
    codice,
    descrizione,
    reset_policy,
    attivo,
    -- ⛔ IL LIMITE DI EMISSIONE SI DISATTIVA QUI, E NON E' UN TRUCCO.
    --   Dal 2026-08-26 il cancello rifiuta una data piu' vecchia di N giorni,
    --   e i test 2..5 di questo file numerano con date del 2025 e del 2026
    --   perche' provano il RESET D'ANNO: servono due anni civili, e nessuna
    --   data relativa a oggi li da'. Con il limite attivo cadrebbero 12
    --   asserzioni su 14 — un file verde che diventa rosso da solo.
    --   ⭐ Si CONFIGURA il registro di prova invece di aggirare il presidio:
    --   e' il primo uso legittimo della colonna di override, e prova la
    --   colonna mentre disinnesca il test.
    --   ⚠️ Questo file NON verifica il limite di emissione: quello vive in
    --   test-limite-emissione-v1.sql. Qui si prova il CANCELLO DI MONOTONIA,
    --   e il limite dev'essere fuori strada.
    limite_emissione_giorni,
    -- ⛔ NOT NULL dal 2026-08-30 (C1-2, 20260830-11): un registro di
    --   numerazione appartiene a UN emittente. Qui ne basta uno
    --   qualsiasi — questo file prova il CONTATORE, non il perimetro —
    --   ma va dato, e si PRENDE dal catalogo invece di cablarlo.
    emittente_soggetto_ruolo_id,
    meta
  )
  SELECT
    left('REGP_' || (SELECT test_scope FROM tmp_costanti_reg), 16),
    'Registro test progressivi',
    'ANNUALE',
    true,
    9999,
    (SELECT ef.soggetto_ruolo_id
       FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.attivo IS TRUE
      ORDER BY ef.id
      LIMIT 1),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_reg))
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_registro),
  'Inserimento registro di test'
);

-- ============================================================
-- 2) Progressivi per anno 2025/2026
-- ============================================================
-- ⚠️ Le date sono in ordine CRESCENTE, e adesso non e' piu' un dettaglio di
--   stile: dal 2026-08-25 il cancello di monotonia rifiuterebbe una sequenza
--   che va indietro. Questo blocco resta verde perche' 31/12/2025 -> 31/12/2025
--   -> 01/01/2026 e' monotona.
SELECT is(
  vendite.fn_get_next_progressivo(
    p_registro_id => (SELECT id FROM tmp_registro),
    p_data => date '2025-12-31',
    -- ⚠️ rev 2026-08-26: p_competenza_mese e' OBBLIGATORIO. NULL significa
    --   «non la so» e il cancello ripiega sul mese della data.
    p_competenza_mese => NULL,
    p_serie => NULL
  ),
  1::bigint,
  'Primo progressivo anno 2025 = 1'
);

SELECT is(
  vendite.fn_get_next_progressivo(
    p_registro_id => (SELECT id FROM tmp_registro),
    p_data => date '2025-12-31',
    -- ⚠️ rev 2026-08-26: p_competenza_mese e' OBBLIGATORIO. NULL significa
    --   «non la so» e il cancello ripiega sul mese della data.
    p_competenza_mese => NULL,
    p_serie => NULL
  ),
  2::bigint,
  'Secondo progressivo anno 2025 = 2'
);

SELECT is(
  vendite.fn_get_next_progressivo(
    p_registro_id => (SELECT id FROM tmp_registro),
    p_data => date '2026-01-01',
    p_competenza_mese => NULL,
    p_serie => NULL
  ),
  1::bigint,
  'Primo progressivo anno 2026 = 1 (reset)'
);

SELECT ok(
  (
    SELECT count(*) = 2
    FROM vendite.registri_fatturazione_progressivi rp
    WHERE rp.registro_id = (SELECT id FROM tmp_registro)
      AND rp.anno IN (2025, 2026)
  ),
  'Esistenza righe progressivi 2025/2026'
);

-- ============================================================
-- 6) DB-7: la memoria della sequenza si scrive a ogni numero
-- ============================================================
-- ⭐ Riga per riga: il contatore e' per anno, quindi ciascuna riga porta la
--   data dell'ultimo numero uscito DA LEI. Il cancello poi guardera' il massimo
--   attraverso gli anni — sono due cose diverse e vanno provate separate.
SELECT is(
  (SELECT array_agg(rp.ultima_data ORDER BY rp.anno)
     FROM vendite.registri_fatturazione_progressivi rp
    WHERE rp.registro_id = (SELECT id FROM tmp_registro)),
  ARRAY[date '2025-12-31', date '2026-01-01'],
  'ultima_data valorizzata a ogni numero emesso, riga per riga'
);

-- ============================================================
-- 7) La STESSA data dell'ultimo numerato e' ammessa
-- ============================================================
-- ⭐ Decisione 7 di Tid: `>=`, non `>`. E' il caso PIU' COMUNE — due fatture
--   emesse lo stesso giorno — quindi se questo si rompesse il cancello
--   bloccherebbe l'esercizio normale invece dell'eccezione.
SELECT is(
  vendite.fn_get_next_progressivo(
    p_registro_id => (SELECT id FROM tmp_registro),
    p_data => date '2026-01-01',
    p_competenza_mese => NULL,
    p_serie => NULL
  ),
  2::bigint,
  'Stessa data dell''ultimo numerato: AMMESSA'
);

-- ============================================================
-- 8) Il pavimento sale con una data successiva
-- ============================================================
SELECT is(
  vendite.fn_get_next_progressivo(
    p_registro_id => (SELECT id FROM tmp_registro),
    p_data => date '2026-03-15',
    p_competenza_mese => NULL,
    p_serie => NULL
  ),
  3::bigint,
  'Data successiva: passa, e diventa il nuovo pavimento'
);

-- ============================================================
-- 9) Data anteriore nello stesso anno -> RIFIUTATA
-- ============================================================
-- ⚠️ `throws_like` e non solo `throws_ok`: qui LA FRASE E' LA POSTA IN GIOCO.
--   E' l'unica cosa che dice all'operatore da quale data ripartire, e un test
--   che si accontenta dello SQLSTATE resterebbe verde anche se il messaggio
--   smettesse di nominare la data.
SELECT throws_ok(
  format($$ SELECT vendite.fn_get_next_progressivo(%s, date '2026-02-01', NULL, NULL) $$,
         (SELECT id FROM tmp_registro)),
  'P0001', NULL,
  'Data anteriore nello stesso anno -> rifiutata (P0001)'
);

SELECT throws_like(
  format($$ SELECT vendite.fn_get_next_progressivo(%s, date '2026-02-01', NULL, NULL) $$,
         (SELECT id FROM tmp_registro)),
  '%15/03/2026%',
  'La frase del rifiuto NOMINA la data da cui ripartire'
);

-- ============================================================
-- 10) CROSS-ANNO: l'anno precedente non e' una scappatoia
-- ============================================================
-- ⛔ E' il caso per cui il cancello legge il massimo ATTRAVERSO GLI ANNI: la
--   riga di contatore del 2025 e' un'altra e ha il suo `ultima_data` fermo al
--   31/12/2025, quindi un controllo per anno lascerebbe passare questo
--   documento e aprirebbe un numero in un anno gia' chiuso.
SELECT throws_ok(
  format($$ SELECT vendite.fn_get_next_progressivo(%s, date '2025-12-31', NULL, NULL) $$,
         (SELECT id FROM tmp_registro)),
  'P0001', NULL,
  'CROSS-ANNO: data dell''anno precedente -> rifiutata lo stesso'
);

-- ============================================================
-- 11) Due serie sullo stesso registro sono sequenze INDIPENDENTI
-- ============================================================
-- Il modello lo ammette (tipi_doc_fiscale_registri mappa (tipo_doc, natura) ->
-- (registro, serie) e la sua UNIQUE lo consente apposta). Se il cancello
-- guardasse il solo registro, la data del 01/01 qui sotto sarebbe rifiutata dal
-- pavimento del 15/03 dell'altra serie — che e' una sequenza che non c'entra.
CREATE TEMP TABLE tmp_registro_b AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione (
    codice, descrizione, serie_default, reset_policy, attivo,
    -- ⛔ Come sopra: qui si prova la separazione fra due SERIE, non il limite
    --   di emissione, e le date sono d'archivio.
    limite_emissione_giorni, emittente_soggetto_ruolo_id, meta)
  SELECT
    left('REGB_' || (SELECT test_scope FROM tmp_costanti_reg), 16),
    'Registro test serie', 'PG1', 'ANNUALE', true,
    9999,
    (SELECT ef.soggetto_ruolo_id
       FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.attivo IS TRUE
      ORDER BY ef.id
      LIMIT 1),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_reg))
  RETURNING id)
SELECT * FROM ins;

-- ⚠️ rev 2026-08-26: la serie e' il QUARTO argomento — al terzo posto
--   ora c'e' la competenza. Lasciando 'PG1' al terzo posto, PostgreSQL
--   proverebbe a leggerlo come data e il test morirebbe su un errore di
--   cast, non su una regola.
SELECT vendite.fn_get_next_progressivo((SELECT id FROM tmp_registro_b), date '2026-05-10', NULL, 'PG1');

SELECT is(
  vendite.fn_get_next_progressivo(
    (SELECT id FROM tmp_registro_b), date '2026-01-01', NULL, 'PG2'),
  1::bigint,
  'Due serie sullo stesso registro: la seconda riparte da 1 e non e'' bloccata dal pavimento della prima'
);

-- ============================================================
-- 12) DB-10: la lettura risolve la serie dal serie_default
-- ⭐ rev 2026-08-26: la funzione si chiama ora fn_get_pavimento_sequenza — da
--   quando i pavimenti sono due, «data minima numerabile» e' il nome della
--   COMPOSIZIONE e non di questa primitiva. E p_serie ha perso il DEFAULT: da
--   primitiva interna, dimenticare la serie fa leggere il contatore di un'altra
--   sequenza. NULL resta legittimo e significa «quella del registro».
-- ============================================================
-- ⛔ E' la differenza voluta con fn_get_next_progressivo, che riceve la serie
--   gia' risolta dal chiamante. Chiedere «il minimo di questo registro» senza
--   nominare la serie deve dare la risposta del sezionale VIVO, non quella
--   della serie vuota — dove non c'e' nessun contatore.
SELECT is(
  ARRAY[
    vendite.fn_get_pavimento_sequenza((SELECT id FROM tmp_registro_b), NULL),
    vendite.fn_get_pavimento_sequenza((SELECT id FROM tmp_registro_b), 'PG1'),
    vendite.fn_get_pavimento_sequenza((SELECT id FROM tmp_registro_b), '')
  ],
  ARRAY[date '2026-05-10', date '2026-05-10', NULL::date],
  'fn_get_pavimento_sequenza: serie NULL = serie_default; serie vuota = nessun contatore'
);

-- ============================================================
-- Cleanup
-- ============================================================
UPDATE vendite.registri_fatturazione
SET storicizza = false
WHERE id IN ((SELECT id FROM tmp_registro), (SELECT id FROM tmp_registro_b));

DELETE FROM vendite.registri_fatturazione_progressivi
WHERE registro_id IN ((SELECT id FROM tmp_registro), (SELECT id FROM tmp_registro_b));

DELETE FROM vendite.registri_fatturazione
WHERE id IN ((SELECT id FROM tmp_registro), (SELECT id FROM tmp_registro_b));

SELECT ok(true, 'Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
