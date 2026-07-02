-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: proiezione stato di dominio — D1 seed + guard is_verdetto +
--       resolver vendite + union script.vw_stato_sorgente +
--       pratiche.fn_stato_sorgente (brief-db-proiezione-stato-dominio)
-- ------------------------------------------------------------
-- Indice test (1..17):
-- 1)  Seed D1: DRAFT     -> fase APERTO,    esito NULL,     terminale false
-- 2)  Seed D1: EMESSO    -> fase IN_ATTESA, esito NULL,     terminale false
-- 3)  Seed D1: ACCETTATO -> fase IN_CORSO,  esito POSITIVO, terminale false
-- 4)  Seed D1: ANNULLATO -> fase CHIUSO,    esito NEGATIVO, terminale true
-- 5)  Invariante mappa: nessuno stato terminale fuori da fase CHIUSO
-- 6)  is_verdetto: i 4 esiti strutturali sono verdetti
-- 7)  Guard verdetto: esito inesistente -> errore parlante
-- 8)  Guard verdetto: esito di instradamento (MERCE_PRESENTE) -> errore
--     (skip se il dominio non ha ancora seedato l'esito)
-- 9)  vw_stato_sorgente: riga per il preventivo EMESSO, risolto=true
-- 10) vw_stato_sorgente: al piu' una riga per (tipo, uid)
-- 11) fn_stato_sorgente EMESSO    -> (true, EMESSO, 'Emesso', IN_ATTESA, NULL, false)
-- 12) fn_stato_sorgente ACCETTATO -> (IN_CORSO, POSITIVO)
-- 13) fn_stato_sorgente ANNULLATO -> (CHIUSO, NEGATIVO, terminale true)
-- 14) fn_stato_sorgente tipo senza resolver -> UNKNOWN (risolto=false) senza errore
--     (skip se esiste solo il tipo PREVENTIVO)
-- 15) fn_stato_sorgente uid inesistente su tipo PREVENTIVO -> UNKNOWN (risolto=false)
-- 16) fn_stato_sorgente guard: sorgente_tipo_id NULL -> errore parametri
-- 17) fn_stato_sorgente guard: sorgente_tipo_id 0 -> errore parametri
-- ------------------------------------------------------------

BEGIN;
SELECT plan(17);

-- ============================================================
-- Riferimenti minimi per creare preventivi in pgTAP
-- (pattern test-fn-available-actions-preventivo-v1)
-- ============================================================
CREATE TEMP TABLE tmp_refs_pss AS
SELECT
  (SELECT ba.istanza_utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS istanza_utility_id,
  (SELECT ba.utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS utility_id,
  (SELECT v.id
     FROM config.valute v
    ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  (SELECT ef.id
     FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1
  ) AS emittente_fiscale_id,
  (SELECT s.id
     FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS sorgente_tipo_id,
  (SELECT sd.id FROM config.stati_doc_preventivi sd
    WHERE sd.codice_interno = 'EMESSO' LIMIT 1)    AS stato_emesso_id,
  (SELECT sd.id FROM config.stati_doc_preventivi sd
    WHERE sd.codice_interno = 'ACCETTATO' LIMIT 1) AS stato_accettato_id,
  (SELECT sd.id FROM config.stati_doc_preventivi sd
    WHERE sd.codice_interno = 'ANNULLATO' LIMIT 1) AS stato_annullato_id;

-- Tre preventivi fixture: EMESSO / ACCETTATO / ANNULLATO
CREATE TEMP TABLE tmp_prev_pss AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, istanza_utility_id, utility_id,
    validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, fatturazione_immediata,
    storicizza, meta, emittente_fiscale_id
  )
  SELECT
    'PGTAP-PSS-' || x.suffisso || '-' || substr(md5(clock_timestamp()::text || x.suffisso), 1, 8),
    0,
    r.istanza_utility_id, r.utility_id,
    DATE '2026-07-01', DATE '2026-07-31', r.valuta_id,
    x.stato_id, DATE '2026-07-01', false,
    false, '{"test_scope":"pgtap_proiezione_stato_sorgente"}'::jsonb,
    r.emittente_fiscale_id
  FROM tmp_refs_pss r
  CROSS JOIN (
    SELECT 'EMESSO' AS suffisso, (SELECT stato_emesso_id    FROM tmp_refs_pss) AS stato_id
    UNION ALL
    SELECT 'ACCETT',             (SELECT stato_accettato_id FROM tmp_refs_pss)
    UNION ALL
    SELECT 'ANNULL',             (SELECT stato_annullato_id FROM tmp_refs_pss)
  ) x
  RETURNING id, uid, stato_doc_preventivo_id
)
SELECT
  i.id,
  (i.uid)::text AS uid,
  sd.codice_interno AS stato_codice_interno
FROM ins i
JOIN config.stati_doc_preventivi sd ON sd.id = i.stato_doc_preventivo_id;

-- ============================================================
-- 1-4) Seed D1: la mappa dichiarata dal dominio (criteri §6)
-- ============================================================
SELECT results_eq(
  $$SELECT fase, esito, terminale FROM config.stati_doc_preventivi WHERE codice_interno = 'DRAFT'$$,
  $$VALUES ('APERTO'::varchar, NULL::varchar, false)$$,
  'Seed D1: DRAFT -> APERTO / NULL / non terminale'
);

SELECT results_eq(
  $$SELECT fase, esito, terminale FROM config.stati_doc_preventivi WHERE codice_interno = 'EMESSO'$$,
  $$VALUES ('IN_ATTESA'::varchar, NULL::varchar, false)$$,
  'Seed D1: EMESSO -> IN_ATTESA / NULL / non terminale'
);

SELECT results_eq(
  $$SELECT fase, esito, terminale FROM config.stati_doc_preventivi WHERE codice_interno = 'ACCETTATO'$$,
  $$VALUES ('IN_CORSO'::varchar, 'POSITIVO'::varchar, false)$$,
  'Seed D1: ACCETTATO -> IN_CORSO / POSITIVO / non terminale'
);

SELECT results_eq(
  $$SELECT fase, esito, terminale FROM config.stati_doc_preventivi WHERE codice_interno = 'ANNULLATO'$$,
  $$VALUES ('CHIUSO'::varchar, 'NEGATIVO'::varchar, true)$$,
  'Seed D1: ANNULLATO -> CHIUSO / NEGATIVO / terminale'
);

-- ============================================================
-- 5) Invariante mappa universale: terminale => fase CHIUSO
-- ============================================================
SELECT is(
  (SELECT COUNT(*)::int FROM config.stati_doc_preventivi
    WHERE terminale AND fase <> 'CHIUSO'),
  0,
  'Invariante: nessuno stato terminale fuori da fase CHIUSO'
);

-- ============================================================
-- 6) is_verdetto sui 4 esiti strutturali
-- ============================================================
SELECT is(
  (SELECT COUNT(*)::int FROM config.esiti_flussi_pratiche
    WHERE is_verdetto
      AND codice_interno IN ('POSITIVO', 'NEGATIVO', 'PARZIALE', 'NON_APPLICABILE')),
  4,
  'is_verdetto: i 4 esiti strutturali di motore sono verdetti'
);

-- ============================================================
-- 7-8) Guard verdetto sulla proiezione esito
-- ============================================================
SELECT throws_like(
  $$UPDATE config.stati_doc_preventivi
       SET esito = 'ESITO_INESISTENTE_PGTAP'
     WHERE codice_interno = 'ACCETTATO'$$,
  '%verdetto%',
  'Guard verdetto: esito inesistente bloccato con errore parlante'
);

SELECT CASE
  WHEN EXISTS (SELECT 1 FROM config.esiti_flussi_pratiche
                WHERE codice_interno = 'MERCE_PRESENTE')
  THEN throws_like(
    $$UPDATE config.stati_doc_preventivi
         SET esito = 'MERCE_PRESENTE'
       WHERE codice_interno = 'ACCETTATO'$$,
    '%verdetto%',
    'Guard verdetto: esito di instradamento (MERCE_PRESENTE) bloccato'
  )
  ELSE skip('MERCE_PRESENTE non seedato in questo DB', 1)
END;

-- ============================================================
-- 9-10) Vista union script.vw_stato_sorgente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
      FROM script.vw_stato_sorgente v
     WHERE v.sorgente_tipo_id = (SELECT sorgente_tipo_id FROM tmp_refs_pss)
       AND v.sorgente_uid = (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'EMESSO')
       AND v.risolto
       AND v.fase = 'IN_ATTESA'
  ),
  'vw_stato_sorgente: il preventivo EMESSO proietta risolto=true / IN_ATTESA'
);

SELECT is(
  (SELECT COUNT(*)::int
     FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id = (SELECT sorgente_tipo_id FROM tmp_refs_pss)
      AND v.sorgente_uid = (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'EMESSO')),
  1,
  'vw_stato_sorgente: al piu'' una riga per (sorgente_tipo_id, sorgente_uid)'
);

-- ============================================================
-- 11-13) fn_stato_sorgente: descrittore per stato (criteri §6)
-- ============================================================
SELECT results_eq(
  $$SELECT risolto, stato_codice_interno, stato_descrizione, fase, esito, terminale
      FROM pratiche.fn_stato_sorgente(
             (SELECT sorgente_tipo_id FROM tmp_refs_pss),
             (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'EMESSO'))$$,
  $$VALUES (true, 'EMESSO'::text, 'Emesso'::text, 'IN_ATTESA'::text, NULL::text, false)$$,
  'fn_stato_sorgente EMESSO: risolto / IN_ATTESA / esito NULL / non terminale / descrizione Emesso'
);

SELECT results_eq(
  $$SELECT risolto, fase, esito
      FROM pratiche.fn_stato_sorgente(
             (SELECT sorgente_tipo_id FROM tmp_refs_pss),
             (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'ACCETTATO'))$$,
  $$VALUES (true, 'IN_CORSO'::text, 'POSITIVO'::text)$$,
  'fn_stato_sorgente ACCETTATO: IN_CORSO / POSITIVO'
);

SELECT results_eq(
  $$SELECT risolto, fase, esito, terminale
      FROM pratiche.fn_stato_sorgente(
             (SELECT sorgente_tipo_id FROM tmp_refs_pss),
             (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'ANNULLATO'))$$,
  $$VALUES (true, 'CHIUSO'::text, 'NEGATIVO'::text, true)$$,
  'fn_stato_sorgente ANNULLATO: CHIUSO / NEGATIVO / terminale'
);

-- ============================================================
-- 14-15) Degrado con grazia: UNKNOWN senza errore
-- ============================================================
SELECT CASE
  WHEN EXISTS (SELECT 1 FROM config.sorgenti
                WHERE codice_interno <> 'PREVENTIVO' AND attivo IS TRUE)
  THEN results_eq(
    $$SELECT risolto, stato_codice_interno, stato_descrizione, fase, esito, terminale
        FROM pratiche.fn_stato_sorgente(
               (SELECT id FROM config.sorgenti
                 WHERE codice_interno <> 'PREVENTIVO' AND attivo IS TRUE
                 ORDER BY id LIMIT 1),
               (SELECT uid FROM tmp_prev_pss WHERE stato_codice_interno = 'EMESSO'))$$,
    $$VALUES (false, 'UNKNOWN'::text, 'n/d'::text, 'APERTO'::text, NULL::text, false)$$,
    'fn_stato_sorgente: tipo senza resolver -> UNKNOWN (risolto=false) senza errore'
  )
  ELSE skip('nessun tipo sorgente diverso da PREVENTIVO nel DB', 1)
END;

SELECT results_eq(
  $$SELECT risolto, stato_codice_interno
      FROM pratiche.fn_stato_sorgente(
             (SELECT sorgente_tipo_id FROM tmp_refs_pss),
             (uuidv7())::text)$$,
  $$VALUES (false, 'UNKNOWN'::text)$$,
  'fn_stato_sorgente: uid inesistente -> UNKNOWN (risolto=false) senza errore'
);

-- ============================================================
-- 16-17) Guard parametri
-- ============================================================
SELECT throws_like(
  $$SELECT * FROM pratiche.fn_stato_sorgente(NULL::bigint, 'abc')$$,
  '%stato sorgente non validi%',
  'fn_stato_sorgente: sorgente_tipo_id NULL -> E_STATO_SORGENTE_PARAM_INVALIDO'
);

SELECT throws_like(
  $$SELECT * FROM pratiche.fn_stato_sorgente(0::bigint, 'abc')$$,
  '%stato sorgente non validi%',
  'fn_stato_sorgente: sorgente_tipo_id 0 -> E_STATO_SORGENTE_PARAM_INVALIDO'
);

SELECT * FROM finish();
ROLLBACK;
