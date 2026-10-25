-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): il verbo ha la
--   firma a DUE argomenti (id, stato): p_user e' uscito perche' user_update lo
--   scrive il trigger di audit. L'emissione chiede l'azione di processo
--   emetti_preventivo: la si concede all'utente di contesto
--   (dbops.fn_pgtap_concedi_azione). Matrice e righe non le giudica piu' il
--   corpo del verbo ma il guard di transizione, con gli stessi codici: i test
--   7 e 8 asseriscono ora QUEL rifiuto (E_PREV_TRANSIZIONE_NON_AMMESSA,
--   E_PREV_NESSUNA_RIGA_ATTIVA) invece di «qualunque errore» — con la firma
--   vecchia passavano sull'errore di funzione inesistente.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_cambia_stato_preventivo
-- ------------------------------------------------------------
-- Indice test (1..11):
-- 1) Funzione presente
-- 2) Riferimenti minimi disponibili
-- 3) Setup preventivo DRAFT con riga valida
-- 4) DRAFT -> EMESSO ammessa (riga attiva + totale > 0)
-- 5) EMESSO -> ACCETTATO ammessa
-- 6) DRAFT -> ANNULLATO ammessa (senza commessa; ACCETTATO->ANNULLATO disattivata nel seed)
-- 7) DRAFT -> ACCETTATO vietata (non in matrice)
-- 8) DRAFT -> EMESSO vietata senza righe attive
-- 9a) Premessa: il preventivo di prova ha totale_documento = 0
-- 9b) DRAFT -> EMESSO AMMESSA con totale = 0 (regola rev 2026-07-16)
-- 10) anti-regressione: rename codice stati -> DRAFT->EMESSO risolta per codice_interno
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

SELECT plan(11);
-- ============================================================
-- Setup GUC app.current_user_id: il trigger trgfn_preventivi_default_emittente
-- richiede l'emittente fiscale dell'operatore loggato (GUC popolata in API da
-- JwtAuditAuthentication). In contesto pgTAP la GUC e' vuota -> la valorizziamo
-- con un utente che ha un emittente in config.user_emittenti_fiscali, altrimenti
-- l'INSERT su preventivi solleva E_PREV_EMITTENTE_NON_RISOLTO. (Stesso pattern di
-- test-fn-crea-revisione-preventivo.)
-- ============================================================
SELECT set_config(
  'app.current_user_id',
  (SELECT uef.auth_user_id::text
     FROM config.user_emittenti_fiscali uef
    ORDER BY uef.auth_user_id LIMIT 1),
  true
);
-- ⭐ rev 2026-10-25 (giro 6): l'emissione (DRAFT -> EMESSO, test 4, 9b, 10)
--   chiede l'azione di processo emetti_preventivo, e il verbo la controlla
--   sull'utente di contesto. Si concede a quello appena fissato.
SELECT dbops.fn_pgtap_concedi_azione(
  nullif(current_setting('app.current_user_id', true), '')::integer,
  'emetti_preventivo'
);
-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT ok(
    EXISTS (
      SELECT 1
      FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite'
        AND p.proname = 'fn_cambia_stato_preventivo'
    ),
    '1. fn_cambia_stato_preventivo presente'
  );
-- ============================================================
-- 2) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_cs_refs AS
SELECT (
    SELECT ba.id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS billing_account_id,
  (
    SELECT ba.utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS utility_id,
  (
    SELECT ba.istanza_utility_id
    FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id
    LIMIT 1
  ) AS istanza_utility_id,
  (
    SELECT a.id
    FROM catalogo.articoli a
    WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST
    LIMIT 1
  ) AS articolo_id,
  (
    SELECT s.id
    FROM config.stati_doc_preventivi s
    WHERE s.codice = 'DRAFT'
      AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_draft_id,
  (
    SELECT s.id
    FROM config.stati_doc_preventivi s
    WHERE s.codice = 'EMESSO'
      AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_emesso_id,
  (
    SELECT s.id
    FROM config.stati_doc_preventivi s
    WHERE s.codice = 'ACCETTATO'
      AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_accettato_id,
  (
    SELECT s.id
    FROM config.stati_doc_preventivi s
    WHERE s.codice = 'ANNULLATO'
      AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_annullato_id,
  (
    SELECT v.id
    FROM config.valute v
    ORDER BY v.id
    LIMIT 1
  ) AS valuta_id,
  (
    SELECT i.id
    FROM config.iva i
    WHERE i.attivo IS TRUE
    ORDER BY i.id LIMIT 1
  ) AS iva_id;
SELECT ok(
    (
      SELECT billing_account_id IS NOT NULL
        AND articolo_id IS NOT NULL
        AND stato_draft_id IS NOT NULL
        AND stato_emesso_id IS NOT NULL
        AND stato_accettato_id IS NOT NULL
        AND stato_annullato_id IS NOT NULL
      FROM tmp_cs_refs
    ),
    '2. Riferimenti minimi disponibili (incluso ANNULLATO)'
  );
-- ============================================================
-- 3) Setup preventivo DRAFT con riga valida
-- ============================================================
CREATE TEMP TABLE tmp_cs_prev1 AS WITH ins AS (
  INSERT INTO vendite.preventivi (
      numero,
      rev,
      billing_account_id,
      istanza_utility_id,
      utility_id,
      validita_dal,
      validita_al,
      valuta_id,
      stato_doc_preventivo_id,
      data,
      storicizza,
      meta
    )
  SELECT 'PGTAP-CS-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id,
    r.istanza_utility_id,
    r.utility_id,
    DATE '2026-06-01',
    DATE '2026-06-30',
    r.valuta_id,
    r.stato_draft_id,
    DATE '2026-06-01',
    false,
    jsonb_build_object('test_scope', 'pgtap_cambia_stato')
  FROM tmp_cs_refs r
  RETURNING id,
    uid,
    numero
)
SELECT *
FROM ins;
-- Riga con quantita e prezzo > 0
INSERT INTO vendite.preventivi_righe (
    preventivo_id,
    articolo_id,
    qta_operativa,
    quantita,
    prezzo_unitario,
    iva_id,
    attivo,
    meta
  )
SELECT p.id,
  r.articolo_id,
  10,
  10,
  100.00,
  r.iva_id,
  true,
  jsonb_build_object('test_scope', 'pgtap_cambia_stato')
FROM tmp_cs_prev1 p,
  tmp_cs_refs r;
SELECT ok(
    (
      SELECT id IS NOT NULL
      FROM tmp_cs_prev1
    ),
    '3. Setup preventivo DRAFT con riga valida'
  );
-- ============================================================
-- 4) DRAFT -> EMESSO ammessa
-- ============================================================
SELECT lives_ok(
    format(
      'SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, ''EMESSO'')',
      (
        SELECT id
        FROM tmp_cs_prev1
      )
    ),
    '4. DRAFT -> EMESSO ammessa'
  );
-- ============================================================
-- 5) EMESSO -> ACCETTATO ammessa
-- ============================================================
SELECT lives_ok(
    format(
      'SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, ''ACCETTATO'')',
      (
        SELECT id
        FROM tmp_cs_prev1
      )
    ),
    '5. EMESSO -> ACCETTATO ammessa'
  );
-- ============================================================
-- 6) DRAFT -> ANNULLATO ammessa (senza commessa)
--    Matrice attuale (config.transizioni_stati_preventivi): ANNULLATO e'
--    raggiungibile SOLO da DRAFT (1->9). ACCETTATO->ANNULLATO e' stata
--    DISATTIVATA nel seed (row id 7, attivo=f, mctit 2026-05-22): da ACCETTATO
--    si transita a EVASO. Si verifica la transizione verso ANNULLATO + guard
--    "no commessa" su un preventivo DRAFT dedicato.
-- ============================================================
CREATE TEMP TABLE tmp_cs_prev_ann AS WITH ins AS (
  INSERT INTO vendite.preventivi (
      numero,
      rev,
      billing_account_id,
      istanza_utility_id,
      utility_id,
      validita_dal,
      validita_al,
      valuta_id,
      stato_doc_preventivo_id,
      data,
      storicizza,
      meta
    )
  SELECT 'PGTAP-CSA-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id,
    r.istanza_utility_id,
    r.utility_id,
    DATE '2026-06-01',
    DATE '2026-06-30',
    r.valuta_id,
    r.stato_draft_id,
    DATE '2026-06-01',
    false,
    jsonb_build_object('test_scope', 'pgtap_cambia_stato')
  FROM tmp_cs_refs r
  RETURNING id,
    uid,
    numero
)
SELECT *
FROM ins;
SELECT lives_ok(
    format(
      'SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, ''ANNULLATO'')',
      (
        SELECT id
        FROM tmp_cs_prev_ann
      )
    ),
    '6. DRAFT -> ANNULLATO ammessa (no commessa)'
  );
-- ============================================================
-- 7) DRAFT -> ACCETTATO vietata (non in matrice transizioni)
-- ============================================================
CREATE TEMP TABLE tmp_cs_prev2 AS WITH ins AS (
  INSERT INTO vendite.preventivi (
      numero,
      rev,
      billing_account_id,
      istanza_utility_id,
      utility_id,
      validita_dal,
      validita_al,
      valuta_id,
      stato_doc_preventivo_id,
      data,
      storicizza,
      meta
    )
  SELECT 'PGTAP-CS2-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id,
    r.istanza_utility_id,
    r.utility_id,
    DATE '2026-06-01',
    DATE '2026-06-30',
    r.valuta_id,
    r.stato_draft_id,
    DATE '2026-06-01',
    false,
    jsonb_build_object('test_scope', 'pgtap_cambia_stato')
  FROM tmp_cs_refs r
  RETURNING id,
    uid,
    numero
)
SELECT *
FROM ins;
-- Riga valida per prev2
INSERT INTO vendite.preventivi_righe (
    preventivo_id,
    articolo_id,
    qta_operativa,
    quantita,
    prezzo_unitario,
    iva_id,
    attivo,
    meta
  )
SELECT p.id,
  r.articolo_id,
  5,
  5,
  50.00,
  r.iva_id,
  true,
  jsonb_build_object('test_scope', 'pgtap_cambia_stato')
FROM tmp_cs_prev2 p,
  tmp_cs_refs r;
SELECT throws_like(
    format(
      'SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, ''ACCETTATO'')',
      (
        SELECT id
        FROM tmp_cs_prev2
      )
    ),
    '%Transizione del preventivo non ammessa%',
    '7. DRAFT -> ACCETTATO vietata (non in matrice: E_PREV_TRANSIZIONE_NON_AMMESSA dal guard di transizione)'
  );
-- ============================================================
-- 8) DRAFT -> EMESSO vietata senza righe attive
-- ============================================================
CREATE TEMP TABLE tmp_cs_prev3 AS WITH ins AS (
  INSERT INTO vendite.preventivi (
      numero,
      rev,
      billing_account_id,
      istanza_utility_id,
      utility_id,
      validita_dal,
      validita_al,
      valuta_id,
      stato_doc_preventivo_id,
      data,
      storicizza,
      meta
    )
  SELECT 'PGTAP-CS3-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id,
    r.istanza_utility_id,
    r.utility_id,
    DATE '2026-06-01',
    DATE '2026-06-30',
    r.valuta_id,
    r.stato_draft_id,
    DATE '2026-06-01',
    false,
    jsonb_build_object('test_scope', 'pgtap_cambia_stato')
  FROM tmp_cs_refs r
  RETURNING id,
    uid,
    numero
)
SELECT *
FROM ins;
-- Nessuna riga inserita
SELECT throws_like(
    format(
      'SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, ''EMESSO'')',
      (
        SELECT id
        FROM tmp_cs_prev3
      )
    ),
    '%senza righe attive%',
    '8. DRAFT -> EMESSO vietata senza righe attive (E_PREV_NESSUNA_RIGA_ATTIVA dal guard di transizione)'
  );
-- ============================================================
-- 9a) Premessa: il preventivo di prova ha totale_documento = 0
-- 9b) DRAFT -> EMESSO AMMESSA con totale = 0 (regola rev 2026-07-16)
--    (riga con prezzo = 0)
-- ============================================================
CREATE TEMP TABLE tmp_cs_prev4 AS WITH ins AS (
  INSERT INTO vendite.preventivi (
      numero,
      rev,
      billing_account_id,
      istanza_utility_id,
      utility_id,
      validita_dal,
      validita_al,
      valuta_id,
      stato_doc_preventivo_id,
      data,
      storicizza,
      meta
    )
  SELECT 'PGTAP-CS4-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id,
    r.istanza_utility_id,
    r.utility_id,
    DATE '2026-06-01',
    DATE '2026-06-30',
    r.valuta_id,
    r.stato_draft_id,
    DATE '2026-06-01',
    false,
    jsonb_build_object('test_scope', 'pgtap_cambia_stato')
  FROM tmp_cs_refs r
  RETURNING id,
    uid,
    numero
)
SELECT *
FROM ins;
-- Riga con prezzo = 0 (totale sara' 0)
INSERT INTO vendite.preventivi_righe (
    preventivo_id,
    articolo_id,
    qta_operativa,
    quantita,
    prezzo_unitario,
    iva_id,
    attivo,
    meta
  )
SELECT p.id,
  r.articolo_id,
  10,
  10,
  0.00,
  r.iva_id,
  true,
  jsonb_build_object('test_scope', 'pgtap_cambia_stato')
FROM tmp_cs_prev4 p,
  tmp_cs_refs r;
-- La premessa: il documento e' davvero a totale zero?
SELECT is(
    (
      SELECT coalesce(p.totale_documento, 0)
      FROM vendite.preventivi p
      WHERE p.id = (SELECT id FROM tmp_cs_prev4)
    ),
    0::numeric,
    '9a. Premessa: il preventivo di prova ha totale_documento = 0'
  );

SELECT lives_ok(
    format(
      'SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, ''EMESSO'')',
      (
        SELECT id
        FROM tmp_cs_prev4
      )
    ),
    '9b. DRAFT -> EMESSO ammessa con totale = 0 (rev 2026-07-16: basta che ci siano righe)'
  );
-- ============================================================
-- 10) Anti-regressione codice_interno (analisi-hardcoded-codice §3a #1):
--     rinominando il `codice` (mutabile) degli stati, la transizione DEVE
--     continuare a risolvere stato corrente e destinazione per `codice_interno`.
--     Col vecchio codice la risoluzione di 'EMESSO' fallirebbe (E_STATO_SCONOSCIUTO).
-- ============================================================
CREATE TEMP TABLE tmp_cs_prev5 AS WITH ins AS (
  INSERT INTO vendite.preventivi (
      numero,
      rev,
      billing_account_id,
      istanza_utility_id,
      utility_id,
      validita_dal,
      validita_al,
      valuta_id,
      stato_doc_preventivo_id,
      data,
      storicizza,
      meta
    )
  SELECT 'PGTAP-CS5-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id,
    r.istanza_utility_id,
    r.utility_id,
    DATE '2026-06-01',
    DATE '2026-06-30',
    r.valuta_id,
    r.stato_draft_id,
    DATE '2026-06-01',
    false,
    jsonb_build_object('test_scope', 'pgtap_cambia_stato')
  FROM tmp_cs_refs r
  RETURNING id,
    uid,
    numero
)
SELECT *
FROM ins;
-- Riga con quantita e prezzo > 0 (guard DRAFT->EMESSO soddisfatto)
INSERT INTO vendite.preventivi_righe (
    preventivo_id,
    articolo_id,
    qta_operativa,
    quantita,
    prezzo_unitario,
    iva_id,
    attivo,
    meta
  )
SELECT p.id,
  r.articolo_id,
  10,
  10,
  100.00,
  r.iva_id,
  true,
  jsonb_build_object('test_scope', 'pgtap_cambia_stato')
FROM tmp_cs_prev5 p,
  tmp_cs_refs r;
-- Rinomina il codice (mutabile) di DRAFT/EMESSO; codice_interno resta invariato.
UPDATE config.stati_doc_preventivi
   SET codice = codice || '_RENAMED'
 WHERE codice_interno IN ('DRAFT', 'EMESSO');
SELECT lives_ok(
    format(
      'SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, ''EMESSO'')',
      (
        SELECT id
        FROM tmp_cs_prev5
      )
    ),
    '10. anti-regressione: rename codice stati -> DRAFT->EMESSO risolta per codice_interno'
  );
-- ============================================================
-- Finish
-- ============================================================
SELECT *
FROM finish();
ROLLBACK;