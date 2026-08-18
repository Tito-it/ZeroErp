-- ============================================================
-- Test: vendite.fatture_arrotondamenti_scope + fn_get/fn_set
-- Indice test:
-- 1) Setup: riferimenti base (BA, utility, tipo doc, emittente, valuta)
-- 2) Get su scope assente -> 0
-- 3) Set saldo -> ritorno saldo
-- 4) Get saldo -> valore aggiornato
-- 5) Update saldo (upsert)
-- 6) Guard parametri numerici (NULL o <=0)
-- ============================================================
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
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);
-- ============================================================
-- 1) Setup riferimenti base
-- ============================================================
CREATE TEMP TABLE tmp_refs_arrotondamenti AS
SELECT ba.id AS billing_account_id,
  u.id AS utility_id,
  tdf.id AS tipo_doc_fiscale_id,
  sr.id AS emittente_soggetto_ruolo_id,
  v.id AS valuta_id
FROM anagrafiche.billing_account ba
  JOIN config.utilities u ON u.id = ba.utility_id
  JOIN config.tipi_doc_fiscale tdf ON tdf.id = 1 -- Assumendo che il valore di default sia 1
  JOIN anagrafiche.emittenti_fiscali ef ON ef.id = 32
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
  JOIN config.valute v ON v.id = 1 -- Assumendo che il valore di default sia 1
-- 🔴 SCOPE DAVVERO ASSENTE, aggiunto il 2026-08-18.
--   Il test 2 si chiama «Get saldo scope assente = 0» ma i riferimenti erano
--   scelti senza chiedere che lo scope fosse assente: prendevano il primo
--   billing account e basta. Su quella combinazione un saldo c'era (-0.02), e
--   il test falliva dicendo il vero.
--   ⚠️ E' la premessa che mancava, non l'asserzione a essere sbagliata: senza
--   questa condizione il caso «assente» non veniva mai attraversato, e il test
--   passava o falliva a seconda dei dati del giorno.
WHERE NOT EXISTS (
    SELECT 1
      FROM vendite.fatture_arrotondamenti_scope s
     WHERE s.billing_account_id = ba.id
       AND s.utility_id = u.id
       AND s.tipo_doc_fiscale_id = tdf.id
       AND s.emittente_soggetto_ruolo_id = sr.id
       AND s.valuta_id = v.id
)
ORDER BY ba.id,
  u.id,
  tdf.id,
  sr.id,
  v.id
LIMIT 1;
SELECT ok(
    (
      SELECT count(*) = 1
      FROM tmp_refs_arrotondamenti
    ),
    'Setup riferimenti base'
  );
-- ============================================================
-- 2) Get su scope assente -> 0
-- ============================================================
SELECT is(
    vendite.fn_get_arrotondamento_scope(
      (
        SELECT billing_account_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT utility_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT valuta_id
        FROM tmp_refs_arrotondamenti
      )
    ),
    0::numeric,
    'Get saldo scope assente = 0'
  );
-- ============================================================
-- 3) Set saldo -> l'operazione va a buon fine
-- ============================================================
-- 🔴 `is()` -> `lives_ok()`, 2026-08-18.
--   `vendite.fn_set_arrotondamento_scope` ritorna **void**: non ritorna piu' il
--   saldo impostato. Il test lo confrontava con `is(...)` e PostgreSQL
--   rispondeva «la funzione is(void, numeric, unknown) non esiste» — un errore
--   di risoluzione, quindi il file moriva li' senza eseguire il resto.
--   ⚠️ Non si perde copertura: che il valore sia stato scritto lo verifica gia'
--   il test 4 con il GETTER, che e' anche il modo giusto — si controlla
--   l'effetto dove si legge, non nel valore di ritorno di chi scrive.
SELECT lives_ok(
    $$SELECT vendite.fn_set_arrotondamento_scope(
      (
        SELECT billing_account_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT utility_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT valuta_id
        FROM tmp_refs_arrotondamenti
      ),
      0.03::numeric
    )$$,
    'Set saldo scope = 0.03 eseguito'
  );
-- ============================================================
-- 4) Get saldo -> valore aggiornato
-- ============================================================
SELECT is(
    vendite.fn_get_arrotondamento_scope(
      (
        SELECT billing_account_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT utility_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT valuta_id
        FROM tmp_refs_arrotondamenti
      )
    ),
    0.03::numeric,
    'Get saldo scope = 0.03'
  );
-- ============================================================
-- 5) Update saldo (upsert)
-- ============================================================
-- ⚠️ Stesso motivo del test 3: il setter ritorna void. L'effetto si verifica
--   col getter, non nel valore di ritorno.
SELECT lives_ok(
    $$SELECT vendite.fn_set_arrotondamento_scope(
      (
        SELECT billing_account_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT utility_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT valuta_id
        FROM tmp_refs_arrotondamenti
      ),
      -0.02::numeric
    )$$,
    'Update saldo scope = -0.02 eseguito'
  );
-- ============================================================
-- 6) Guard parametri numerici (NULL o <=0)
-- ============================================================
SELECT throws_ok(
    $sql$
    SELECT vendite.fn_get_arrotondamento_scope(NULL, 1, 1, 1, 1);
$sql$,
'P0001',
NULL,
'Guard: billing_account_id NULL'
);
-- Cleanup (non necessario: upsert su scope viene mantenuto)
SELECT *
FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
