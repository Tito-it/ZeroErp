-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard OBSOLETO (dbops.trgfn_child_requires_non_obsolete_parent)
--       cablato su pratiche.pratiche (tipo_prestazione_id) e
--       pratiche.flussi (template_flusso_id).
--       (brief-db-obsoleto-dal-filtro-lookup-e-guard, Obiettivo 2)
--
-- Indice test (0..9):
--  0) Precondizioni (config + fixture catalogo)
--  1) INSERT pratica su tipo selezionabile (obsoleto_dal NULL): lives
--  2) INSERT pratica su tipo con ritiro PROGRAMMATO (futura): lives
--  3) INSERT pratica su tipo OBSOLETO (passato): throws
--  4) UPDATE non-FK (descrizione) di pratica esistente: lives (guard inerte)
--  5) Tipo diventa obsoleto: UPDATE non-FK della pratica storica: lives
--  6) UPDATE che ri-collega la pratica a un tipo obsoleto (cambio FK): throws
--  7) INSERT flusso su template selezionabile (NULL): lives
--  8) INSERT flusso su template OBSOLETO (passato): throws
--  9) Asse attivo intatto: il tipo obsoleto resta attivo=true
-- ------------------------------------------------------------
BEGIN;
SELECT plan(10);

-- =========================================================
-- 0) Precondizioni: config data idempotente
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA', 'BOZZA', 'Bozza', true) ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true) ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT id FROM anagrafiche.emittenti_fiscali WHERE attivo = true LIMIT 1) AS emittente_id,
  (SELECT id FROM anagrafiche.soggetti LIMIT 1)                              AS soggetto_id,
  (SELECT id FROM config.stati_pratiche        WHERE codice_interno = 'BOZZA'       LIMIT 1) AS stato_bozza_id,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE' LIMIT 1) AS stato_da_eseguire_id,
  (SELECT id FROM config.priorita_pratiche     WHERE codice_interno = 'NORMALE'     LIMIT 1) AS priorita_normale_id;

-- Fixture catalogo: 4 tipi (selezionabile / ritiro programmato / obsoleto / per-flussi).
CREATE TEMP TABLE tmp_tipi AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo, obsoleto_dal)
  VALUES
    ('ZZGUARD_OK',  'ZZGUARD_OK',  'tipo selezionabile',       true, NULL),
    ('ZZGUARD_FUT', 'ZZGUARD_FUT', 'tipo ritiro programmato',  true, CURRENT_DATE + 30),
    ('ZZGUARD_OBS', 'ZZGUARD_OBS', 'tipo obsoleto',            true, CURRENT_DATE - 1),
    ('ZZGUARD_FL',  'ZZGUARD_FL',  'tipo per flussi',          true, NULL)
  RETURNING id, codice_interno
)
SELECT
  max(id) FILTER (WHERE codice_interno = 'ZZGUARD_OK')  AS tipo_ok_id,
  max(id) FILTER (WHERE codice_interno = 'ZZGUARD_FUT') AS tipo_fut_id,
  max(id) FILTER (WHERE codice_interno = 'ZZGUARD_OBS') AS tipo_obs_id,
  max(id) FILTER (WHERE codice_interno = 'ZZGUARD_FL')  AS tipo_fl_id
FROM ins;

-- Template flussi sotto il tipo per-flussi: uno selezionabile, uno obsoleto.
CREATE TEMP TABLE tmp_tf AS
WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, attivo, obsoleto_dal)
  VALUES
    ((SELECT tipo_fl_id FROM tmp_tipi), 'TF_OK',  'template selezionabile', true, NULL),
    ((SELECT tipo_fl_id FROM tmp_tipi), 'TF_OBS', 'template obsoleto',      true, CURRENT_DATE - 1)
  RETURNING id, codice
)
SELECT
  max(id) FILTER (WHERE codice = 'TF_OK')  AS tf_ok_id,
  max(id) FILTER (WHERE codice = 'TF_OBS') AS tf_obs_id
FROM ins;

SELECT ok(
  (SELECT emittente_id IS NOT NULL AND soggetto_id IS NOT NULL
       AND stato_bozza_id IS NOT NULL AND stato_da_eseguire_id IS NOT NULL
       AND priorita_normale_id IS NOT NULL FROM tmp_refs)
  AND (SELECT tipo_ok_id IS NOT NULL AND tipo_obs_id IS NOT NULL FROM tmp_tipi)
  AND (SELECT tf_ok_id IS NOT NULL AND tf_obs_id IS NOT NULL FROM tmp_tf),
  '0. Precondizioni e fixture catalogo soddisfatte'
);

-- =========================================================
-- 1-3) INSERT pratica: selezionabile / programmato / obsoleto
-- =========================================================
SELECT lives_ok(
  format(
    $q$INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
       VALUES (%s, %s, %L, %s, %s)$q$,
    (SELECT emittente_id FROM tmp_refs),
    (SELECT tipo_ok_id FROM tmp_tipi),
    (SELECT soggetto_id FROM tmp_refs),
    (SELECT stato_bozza_id FROM tmp_refs),
    (SELECT priorita_normale_id FROM tmp_refs)),
  '1. INSERT pratica su tipo selezionabile (obsoleto_dal NULL): consentito'
);

SELECT lives_ok(
  format(
    $q$INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
       VALUES (%s, %s, %L, %s, %s)$q$,
    (SELECT emittente_id FROM tmp_refs),
    (SELECT tipo_fut_id FROM tmp_tipi),
    (SELECT soggetto_id FROM tmp_refs),
    (SELECT stato_bozza_id FROM tmp_refs),
    (SELECT priorita_normale_id FROM tmp_refs)),
  '2. INSERT pratica su tipo con ritiro programmato (futura): consentito'
);

SELECT throws_ok(
  format(
    $q$INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
       VALUES (%s, %s, %L, %s, %s)$q$,
    (SELECT emittente_id FROM tmp_refs),
    (SELECT tipo_obs_id FROM tmp_tipi),
    (SELECT soggetto_id FROM tmp_refs),
    (SELECT stato_bozza_id FROM tmp_refs),
    (SELECT priorita_normale_id FROM tmp_refs)),
  NULL, NULL,
  '3. INSERT pratica su tipo OBSOLETO (passato): bloccato'
);

-- =========================================================
-- Pratica storica P creata su tipo selezionabile (per i test UPDATE).
-- =========================================================
CREATE TEMP TABLE tmp_p AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_refs),
    (SELECT tipo_ok_id FROM tmp_tipi),
    (SELECT soggetto_id FROM tmp_refs),
    (SELECT stato_bozza_id FROM tmp_refs),
    (SELECT priorita_normale_id FROM tmp_refs))
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- 4) UPDATE non-FK (descrizione): il guard (UPDATE OF tipo_prestazione_id) non scatta.
SELECT lives_ok(
  format(
    $q$UPDATE pratiche.pratiche SET descrizione = 'agg-1' WHERE id = %s$q$,
    (SELECT pratica_id FROM tmp_p)),
  '4. UPDATE non-FK (descrizione) su pratica esistente: consentito (guard inerte)'
);

-- Il tipo della pratica storica diventa obsoleto (asse obsoleto_dal, attivo invariato).
UPDATE pratiche.tipi_prestazione
   SET obsoleto_dal = CURRENT_DATE - 1
 WHERE id = (SELECT tipo_ok_id FROM tmp_tipi);

-- 5) La pratica storica ora punta a un tipo obsoleto: UPDATE non-FK ancora consentito.
SELECT lives_ok(
  format(
    $q$UPDATE pratiche.pratiche SET descrizione = 'agg-2' WHERE id = %s$q$,
    (SELECT pratica_id FROM tmp_p)),
  '5. UPDATE non-FK su pratica storica con tipo ora obsoleto: consentito'
);

-- 6) Ri-collegare la pratica a un tipo obsoleto (cambio FK): bloccato.
SELECT throws_ok(
  format(
    $q$UPDATE pratiche.pratiche SET tipo_prestazione_id = %s WHERE id = %s$q$,
    (SELECT tipo_obs_id FROM tmp_tipi),
    (SELECT pratica_id FROM tmp_p)),
  NULL, NULL,
  '6. UPDATE che ri-collega la pratica a un tipo obsoleto (cambio FK): bloccato'
);

-- =========================================================
-- 7-8) Flussi: template selezionabile vs obsoleto.
-- Pratica PF su tipo per-flussi (selezionabile) come contenitore.
-- =========================================================
CREATE TEMP TABLE tmp_pf AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_refs),
    (SELECT tipo_fl_id FROM tmp_tipi),
    (SELECT soggetto_id FROM tmp_refs),
    (SELECT stato_bozza_id FROM tmp_refs),
    (SELECT priorita_normale_id FROM tmp_refs))
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT lives_ok(
  format(
    $q$INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
       VALUES (%s, %s, %s)$q$,
    (SELECT pratica_id FROM tmp_pf),
    (SELECT tf_ok_id FROM tmp_tf),
    (SELECT stato_da_eseguire_id FROM tmp_refs)),
  '7. INSERT flusso su template selezionabile (NULL): consentito'
);

SELECT throws_ok(
  format(
    $q$INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
       VALUES (%s, %s, %s)$q$,
    (SELECT pratica_id FROM tmp_pf),
    (SELECT tf_obs_id FROM tmp_tf),
    (SELECT stato_da_eseguire_id FROM tmp_refs)),
  NULL, NULL,
  '8. INSERT flusso su template OBSOLETO (passato): bloccato'
);

-- 9) Asse attivo intatto: il tipo obsoleto resta attivo=true.
SELECT is(
  (SELECT attivo FROM pratiche.tipi_prestazione WHERE id = (SELECT tipo_obs_id FROM tmp_tipi)),
  true,
  '9. Il tipo obsoleto resta attivo=true (asse obsoleto_dal separato da attivo)'
);

SELECT * FROM finish();
ROLLBACK;
