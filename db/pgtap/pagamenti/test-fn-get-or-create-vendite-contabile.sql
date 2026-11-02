-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: pagamenti.fn_get_or_create_vendite_contabile
-- ------------------------------------------------------------
-- Indice test
-- 1) Presenza funzione fn_get_or_create_vendite_contabile
-- 2) Riferimenti a catalogo (centro/stato/tipo_doc) e lotto costruito dell'azienda
-- 3) Create contabile senza lotto
-- 4) Reuse contabile senza lotto (stessi parametri)
-- 5) Create contabile con lotto e link tabella ponte
-- 6) Reuse contabile con stesso lotto
-- 7) Idempotenza link lotto-contabile (una sola riga ponte)
-- 8) Guard parametri: blocco centro_riscossione_id non valido
-- 9) Il rifiuto parla all'operatore: nomina il dato, non il parametro
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (rev 2026-09-17 sera). Fino a quel
--   giorno il file apriva il contesto su «un operatore qualunque» e prendeva
--   «l'ultimo lotto» dai dati della macchina: su un database ricostruito dai
--   changelog (zeroerp_ci, la CI) non c'e' nessun operatore e nessun lotto —
--   la distinta senza lotto moriva su E_CONTABILE_EMITTENTE_OBBLIGATORIO (la
--   sede unica non risolve nessun emittente dalla sessione) e il lotto di
--   ripiego nasceva senza `codice` ne' emittente, entrambi NOT NULL —
--   ERRORE_FIXTURE in baseline-rossi-ci.tsv. Ora: un'azienda col suo operatore
--   (dbops.fn_pgtap_crea_emittente_operatore) PRIMA del contesto, e un lotto
--   di QUELL'emittente scritto dal test — guida pgtap-come-si-scrive-un-test
--   §«Il mondo si costruisce, non si cerca». Con un emittente nuovo la chiave
--   di riuso (che dal 2026-09-15 comprende l'emittente) non puo' agganciare una
--   distinta preesistente della macchina: i test 3-4 e 5-6 misurano DAVVERO
--   create-poi-reuse.
-- ------------------------------------------------------------

BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

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
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

SELECT plan(9);

-- ============================================================
-- 0) Costanti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_goc AS
SELECT
  'pgtap_get_or_create_contabile'::text AS test_scope,
  date_trunc('month', script.fn_data_operativa())::date AS data_contabile,
  script.fn_data_operativa()::date AS data_registrazione;

-- ============================================================
-- 1) Presenza funzione
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'pagamenti'
      AND p.proname = 'fn_get_or_create_vendite_contabile'
  ),
  'Presenza funzione fn_get_or_create_vendite_contabile'
);

-- ============================================================
-- 2) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_centro_ref AS
WITH existing AS (
  SELECT c.id
  FROM pagamenti.centri_riscossione c
  WHERE c.attivo IS TRUE
  ORDER BY c.id
  LIMIT 1
), ins AS (
  INSERT INTO pagamenti.centri_riscossione (
    codice,
    codice_interno,
    descrizione,
    is_compensazione,
    is_fondo_fattura,
    attivo,
    meta
  )
  SELECT
    'GOC_CENTRO_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'GOC_TEST',
    'Centro riscossione test fn_get_or_create',
    false,
    false,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc))
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING id
)
SELECT id FROM existing
UNION ALL
SELECT id FROM ins;

CREATE TEMP TABLE tmp_stato_ref AS
WITH existing AS (
  SELECT s.codice_interno
  FROM pagamenti.vendite_contabili_stati s
  WHERE s.attivo IS TRUE
  ORDER BY s.id
  LIMIT 1
), ins AS (
  INSERT INTO pagamenti.vendite_contabili_stati (
    codice,
    codice_interno,
    descrizione,
    is_final,
    ordine,
    attivo,
    meta
  )
  SELECT
    'GOC_STATO_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'),
    'GOC_STATO',
    'Stato contabile test fn_get_or_create',
    false,
    10,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc))
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING codice_interno
)
SELECT codice_interno FROM existing
UNION ALL
SELECT codice_interno FROM ins;

CREATE TEMP TABLE tmp_tipo_doc_ref AS
SELECT id
FROM config.tipi_doc_fiscale
WHERE attivo IS TRUE
ORDER BY id
LIMIT 1;

-- Il lotto e' dell'azienda costruita: da qui la funzione deriva l'emittente
-- della distinta (livello 2 della sede unica), e sotto la RLS di
-- fatturazione_lotti un lotto altrui non si vedrebbe nemmeno.
CREATE TEMP TABLE tmp_lotto_ref AS
WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
    codice,
    tipo_doc_fiscale_id,
    competenza_mese,
    emittente_soggetto_ruolo_id,
    meta
  )
  SELECT
    'PGTAP-GOC-' || m.soggetto_ruolo_id,
    (SELECT id FROM tmp_tipo_doc_ref),
    (SELECT data_contabile FROM tmp_costanti_goc),
    m.soggetto_ruolo_id,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc))
  FROM _mondo m
  RETURNING id
)
SELECT id FROM ins;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_centro_ref)
  AND (SELECT count(*) = 1 FROM tmp_stato_ref)
  AND (SELECT count(*) = 1 FROM tmp_tipo_doc_ref)
  AND (SELECT count(*) = 1 FROM tmp_lotto_ref),
  'Riferimenti a catalogo (centro/stato/tipo_doc) e lotto costruito dell''azienda'
);

-- ============================================================
-- 3) Create contabile senza lotto
-- ============================================================
CREATE TEMP TABLE tmp_contabile_no_lotto AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
  p_centro_riscossione_id => (SELECT id FROM tmp_centro_ref),
  p_data_contabile => (SELECT data_contabile FROM tmp_costanti_goc),
  p_data_registrazione => (SELECT data_registrazione FROM tmp_costanti_goc),
  p_ente_incasso_id => NULL,
  p_lotto_id => NULL,
  p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc), 'case', 'no_lotto')
) AS contabile_id;

SELECT ok(
  (SELECT contabile_id IS NOT NULL FROM tmp_contabile_no_lotto),
  'Create contabile senza lotto'
);

-- ============================================================
-- 4) Reuse contabile senza lotto
-- ============================================================
SELECT is(
  pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT id FROM tmp_centro_ref),
    p_data_contabile => (SELECT data_contabile FROM tmp_costanti_goc),
    p_data_registrazione => (SELECT data_registrazione FROM tmp_costanti_goc),
    p_ente_incasso_id => NULL,
    p_lotto_id => NULL,
    p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
    p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc), 'case', 'no_lotto_reuse')
  ),
  (SELECT contabile_id::bigint FROM tmp_contabile_no_lotto),
  'Reuse contabile senza lotto (stessi parametri)'
);

-- ============================================================
-- 5) Create contabile con lotto e link
-- ============================================================
CREATE TEMP TABLE tmp_contabile_lotto AS
SELECT pagamenti.fn_get_or_create_vendite_contabile(
  p_centro_riscossione_id => (SELECT id FROM tmp_centro_ref),
  p_data_contabile => (SELECT data_contabile FROM tmp_costanti_goc),
  p_data_registrazione => (SELECT data_registrazione FROM tmp_costanti_goc),
  p_ente_incasso_id => NULL,
  p_lotto_id => (SELECT id FROM tmp_lotto_ref),
  p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc), 'case', 'with_lotto')
) AS contabile_id;

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pagamenti.vendite_contabili_lotti l
    WHERE l.lotto_id = (SELECT id FROM tmp_lotto_ref)
      AND l.contabile_id = (SELECT contabile_id FROM tmp_contabile_lotto)
  ),
  'Create contabile con lotto e link tabella ponte'
);

-- ============================================================
-- 6) Reuse contabile con stesso lotto
-- ============================================================
SELECT is(
  pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => (SELECT id FROM tmp_centro_ref),
    p_data_contabile => (SELECT data_contabile FROM tmp_costanti_goc),
    p_data_registrazione => (SELECT data_registrazione FROM tmp_costanti_goc),
    p_ente_incasso_id => NULL,
    p_lotto_id => (SELECT id FROM tmp_lotto_ref),
    p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
    p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_goc), 'case', 'with_lotto_reuse')
  ),
  (SELECT contabile_id::bigint FROM tmp_contabile_lotto),
  'Reuse contabile con stesso lotto'
);

-- ============================================================
-- 7) Idempotenza link lotto-contabile
-- ============================================================
SELECT is(
  (
    SELECT count(*)::int
    FROM pagamenti.vendite_contabili_lotti l
    WHERE l.lotto_id = (SELECT id FROM tmp_lotto_ref)
      AND l.contabile_id = (SELECT contabile_id FROM tmp_contabile_lotto)
  ),
  1,
  'Idempotenza link lotto-contabile (una sola riga ponte)'
);

-- ============================================================
-- 8) Guard parametri
-- ============================================================
SELECT throws_ok(
  $$
  SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => 0,
    p_data_contabile => script.fn_data_operativa(),
    p_data_registrazione => script.fn_data_operativa(),
    p_ente_incasso_id => NULL,
    p_lotto_id => NULL,
    p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
    p_meta => '{}'::jsonb
  );
  $$,
  'P0001',
  NULL,
  'Guard parametri: blocco centro_riscossione_id non valido'
);

-- ============================================================
-- 9) ⭐ Il rifiuto NOMINA IL DATO, non il parametro PL/pgSQL
--   Presidia una decisione, non un dettaglio: il centro di riscossione lo
--   sceglie una PERSONA in un form, quindi il messaggio lo legge una persona.
--   Fino al 2026-08-21 questo guard sollevava E_GENERICO; la prima bonifica lo
--   portava su E_PARAMETRO_INVALIDO, il cui messaggio è «Parametro non valido:
--   %s» — e il %s sarebbe stato «p_centro_riscossione_id», cioè un messaggio di
--   qualità E_GENERICO sotto un codice registrato.
--   ⚠️ Si asserisce sulla FRASE e non sul codice perché P0001 dice «errore di
--   dominio», non QUALE: qui il discriminante è proprio il testo che l'operatore
--   leggerà. E il pattern non attraversa il segnaposto.
-- ============================================================
SELECT throws_like(
  $$
  SELECT pagamenti.fn_get_or_create_vendite_contabile(
    p_centro_riscossione_id => 0,
    p_data_contabile => script.fn_data_operativa(),
    p_data_registrazione => script.fn_data_operativa(),
    p_ente_incasso_id => NULL,
    p_lotto_id => NULL,
    p_codice_stato_interno => (SELECT codice_interno FROM tmp_stato_ref),
    p_meta => '{}'::jsonb
  );
  $$,
  '%distinta contabile%centro di riscossione%',
  'Il rifiuto nomina il centro di riscossione, non il parametro PL/pgSQL'
);

SELECT * FROM finish();

ROLLBACK;
