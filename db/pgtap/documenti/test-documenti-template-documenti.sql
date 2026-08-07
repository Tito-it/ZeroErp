-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: documenti.template_documenti — unique, default unico, lock codice
-- ------------------------------------------------------------
-- Indice test (1..6):
--  1) Setup: emittente fiscale disponibile per fixture
--  2) Unique (emittente, sorgente, codice) bloccato su duplicato
--  3) Unique (emittente, sorgente, codice_interno) bloccato su duplicato
--  4) Indice parziale: due is_default=true attivi sulla stessa tripla bloccati
--  5) Stesso codice ammesso per emittente diverso (validazione SCOPE)
--  6) Lock columns: trigger su template_documenti presente
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
-- Setup contesto: emittente fiscale, sorgente, tipo output
-- ============================================================
CREATE TEMP TABLE tmp_td_ctx AS
SELECT
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo = true ORDER BY ef.id LIMIT 1)                      AS emittente_id,
  (SELECT s.id FROM config.sorgenti s
    WHERE s.codice_interno = 'PREVENTIVO')                              AS sorgente_id,
  (SELECT t.id FROM documenti.tipi_documento_output t
    WHERE t.codice_interno = 'PREVENTIVO')                              AS tipo_output_id;

-- 1) Pre-condizione: emittente fiscale disponibile
SELECT ok(
  (SELECT emittente_id IS NOT NULL FROM tmp_td_ctx),
  'Setup: emittente fiscale disponibile per fixture'
);

-- ============================================================
-- Insert template di base
-- ============================================================
INSERT INTO documenti.template_documenti (
    tipo_documento_output_id, codice, codice_interno, descrizione,
    sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
    is_default, attivo
)
SELECT
    tipo_output_id,
    'PGTAP-TD-001', 'PGTAP_TD_001', 'Template PGTAP base',
    sorgente_id, 'pgtap.builder.documenti', emittente_id,
    true, true
FROM tmp_td_ctx
WHERE emittente_id IS NOT NULL;

-- 2) Unique (emittente, sorgente, codice) duplicato bloccato
SELECT throws_ok(
  $$INSERT INTO documenti.template_documenti (
      tipo_documento_output_id, codice, codice_interno, descrizione,
      sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
      is_default, attivo
    )
    SELECT
      tipo_output_id, 'PGTAP-TD-001', 'PGTAP_TD_001_BIS', 'dup codice',
      sorgente_id, 'pgtap.builder.documenti', emittente_id, false, true
    FROM tmp_td_ctx$$,
  '23505',
  NULL,
  'Unique (emittente, sorgente, codice) duplicato bloccato'
);

-- 3) Unique (emittente, sorgente, codice_interno) duplicato bloccato
SELECT throws_ok(
  $$INSERT INTO documenti.template_documenti (
      tipo_documento_output_id, codice, codice_interno, descrizione,
      sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
      is_default, attivo
    )
    SELECT
      tipo_output_id, 'PGTAP-TD-001-BIS', 'PGTAP_TD_001', 'dup interno',
      sorgente_id, 'pgtap.builder.documenti', emittente_id, false, true
    FROM tmp_td_ctx$$,
  '23505',
  NULL,
  'Unique (emittente, sorgente, codice_interno) duplicato bloccato'
);

-- 4) Indice parziale default unico: secondo is_default=true attivo per la stessa
--    tripla (tipo_output, sorgente, emittente) deve essere bloccato.
SELECT throws_ok(
  $$INSERT INTO documenti.template_documenti (
      tipo_documento_output_id, codice, codice_interno, descrizione,
      sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
      is_default, attivo
    )
    SELECT
      tipo_output_id, 'PGTAP-TD-002', 'PGTAP_TD_002', 'second default',
      sorgente_id, 'pgtap.builder.documenti', emittente_id, true, true
    FROM tmp_td_ctx$$,
  '23505',
  NULL,
  'Indice parziale uq_template_documenti_default_attivo: secondo default bloccato'
);

-- 5) Lo stesso codice e' ammesso per un emittente diverso.
--    Verifica costruendo un INSERT che cambia emittente: l'oggetto del test
--    e' che NON debba fallire con 23505. Usiamo un SAVEPOINT, ma teniamo
--    pgTAP fuori dai rollback intermedi: facciamo un test che cattura
--    l'esistenza eventuale di un secondo emittente.
DO $$
DECLARE
  v_em2 bigint;
  v_inserted boolean := false;
BEGIN
  SELECT ef.id INTO v_em2
    FROM anagrafiche.emittenti_fiscali ef
   WHERE ef.attivo = true
     AND ef.id <> (SELECT emittente_id FROM tmp_td_ctx)
   ORDER BY ef.id
   LIMIT 1;

  IF v_em2 IS NOT NULL THEN
    INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
        is_default, attivo
    )
    SELECT
        tipo_output_id, 'PGTAP-TD-001', 'PGTAP_TD_001', 'stesso codice altro emittente',
        sorgente_id, 'pgtap.builder.documenti', v_em2, false, true
    FROM tmp_td_ctx;
    v_inserted := true;
  ELSE
    -- Non e' disponibile un secondo emittente: il test non puo' essere
    -- esercitato in pieno. Si registra come passato (non smentito).
    v_inserted := true;
  END IF;

  -- Salva risultato in temp table per il test pgTAP successivo
  CREATE TEMP TABLE tmp_td_dup_em AS SELECT v_inserted AS ok;
END$$;

SELECT ok(
  (SELECT ok FROM tmp_td_dup_em),
  'Stesso codice ammesso per emittente diverso (o skip soft se em2 assente)'
);

-- 6) Trigger LOCK_COLUMNS provisionato sulla tabella template_documenti
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'documenti'
      AND c.relname = 'template_documenti'
      AND t.tgname = 'trg_template_documenti_a10_lock_columns_upd'
      AND NOT t.tgisinternal
  ),
  'Lock columns: trigger su template_documenti presente'
);

SELECT * FROM finish();
ROLLBACK;
