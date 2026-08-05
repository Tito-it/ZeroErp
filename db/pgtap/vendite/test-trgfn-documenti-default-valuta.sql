-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: trigger di seed valuta_id sui documenti vendite
--   vendite.trgfn_offerte_commerciali_default_valuta
--   vendite.trgfn_contratti_default_valuta
--   vendite.trgfn_preventivi_default_valuta
-- (changeset 20260529-03..05)
--
-- I tre trigger condividono la stessa logica (delega a
-- vendite.fn_get_valuta_id). Il preflight verifica l'esistenza su tutte
-- e tre le tabelle; i test comportamentali usano il path preventivi
-- (INSERT piu' semplice) per esercitare la catena BA -> emittente ->
-- gestore e lo skip su payload esplicito.
--
-- Indice test (1..5):
--   1. Preflight: i tre trigger _a10_default_valuta_ins esistono
--   2. Override BA: BA.valuta valorizzata -> valuta_id = BA (vince su emittente)
--   3. Override emittente: BA senza valuta, emittente con valuta -> emittente
--   4. Fallback gestore: BA ed emittente senza valuta -> gestore
--   5. Skip: payload con valuta_id esplicito -> trigger NON sovrascrive
--
-- IMPORTANTE: nessun SAVEPOINT/ROLLBACK TO SAVEPOINT (pgTAP traccia lo
-- stato in temp table). Una sola tx con ROLLBACK finale ripulisce tutto.
-- GUC con is_local=true per scope tx. numero random per evitare collisioni
-- UNIQUE (uq_preventivi_numero_rev).
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

SET LOCAL zeroerp.allow_lock_columns_override = 'on';

-- ============================================================
-- Setup: contesto comune (dati reali esistenti)
-- ============================================================
CREATE TEMP TABLE _t_stato AS
SELECT id AS stato_id FROM config.stati_doc_preventivi
 WHERE attivo = true ORDER BY id LIMIT 1;

CREATE TEMP TABLE _t_ba AS
SELECT ba.id AS ba_id, ba.istanza_utility_id, ba.utility_id
  FROM anagrafiche.billing_account ba
 WHERE ba.istanza_utility_id IS NOT NULL
   AND ba.utility_id IS NOT NULL
 ORDER BY ba.id LIMIT 1;

-- Utente con EF: il trigger emittente assegnera' questo ef al preventivo.
CREATE TEMP TABLE _t_user_with_ef AS
SELECT au.id AS user_id, uef.emittente_fiscale_id AS ef_id
  FROM django.auth_user au
  JOIN config.user_emittenti_fiscali uef ON uef.auth_user_id = au.id
 WHERE au.is_active = true
 ORDER BY au.id LIMIT 1;

-- Valute: gestore (fallback) + due valute distinte da esso per discriminare
-- i livelli BA/emittente dal fallback gestore.
CREATE TEMP TABLE _t_v AS
SELECT
  (SELECT g.valuta_id FROM anagrafiche.gestori g ORDER BY g.id LIMIT 1) AS gestore_valuta,
  (SELECT v.id FROM config.valute v
     WHERE v.id <> (SELECT g.valuta_id FROM anagrafiche.gestori g ORDER BY g.id LIMIT 1)
     ORDER BY v.id LIMIT 1) AS v1,
  (SELECT v.id FROM config.valute v
     WHERE v.id <> (SELECT g.valuta_id FROM anagrafiche.gestori g ORDER BY g.id LIMIT 1)
     ORDER BY v.id OFFSET 1 LIMIT 1) AS v2;

-- Baseline pulita: azzera valuta su BA e sull'EF dell'utente.
UPDATE anagrafiche.billing_account
   SET valuta_id = NULL
 WHERE id = (SELECT ba_id FROM _t_ba);
UPDATE anagrafiche.emittenti_fiscali
   SET valuta_id = NULL
 WHERE id = (SELECT ef_id FROM _t_user_with_ef);

-- GUC operatore: necessaria al trigger emittente (che ordina prima).
SELECT set_config('app.current_user_id',
                  (SELECT user_id::text FROM _t_user_with_ef), true);

-- ============================================================
-- 1) Preflight: i tre trigger esistono.
-- ============================================================
SELECT ok(
  (SELECT count(*) FROM pg_trigger t
     JOIN pg_class c     ON c.oid = t.tgrelid
     JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND t.tgname IN (
        'trg_offerte_commerciali_a10_default_valuta_ins',
        'trg_contratti_a10_default_valuta_ins',
        'trg_preventivi_a10_default_valuta_ins'
      )
  ) = 3,
  '1. I tre trigger _a10_default_valuta_ins (offerte, contratti, preventivi) esistono'
);

-- ============================================================
-- 2) Override BA: BA.valuta=v1, emittente.valuta=v2 -> vince BA (v1).
-- ============================================================
UPDATE anagrafiche.billing_account
   SET valuta_id = (SELECT v1 FROM _t_v) WHERE id = (SELECT ba_id FROM _t_ba);
UPDATE anagrafiche.emittenti_fiscali
   SET valuta_id = (SELECT v2 FROM _t_v) WHERE id = (SELECT ef_id FROM _t_user_with_ef);

CREATE TEMP TABLE _t_r2 AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, data, stato_doc_preventivo_id, billing_account_id,
    istanza_utility_id, utility_id
  )
  SELECT
    'PGT_V2_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    CURRENT_DATE,
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba),
    (SELECT utility_id FROM _t_ba)
  RETURNING valuta_id
)
SELECT valuta_id FROM ins;

SELECT is(
  (SELECT valuta_id FROM _t_r2),
  (SELECT v1 FROM _t_v),
  '2. Override BA: valuta_id = BA.valuta_id (vince su emittente)'
);

-- ============================================================
-- 3) Override emittente: BA senza valuta, emittente=v2 -> emittente (v2).
-- ============================================================
UPDATE anagrafiche.billing_account
   SET valuta_id = NULL WHERE id = (SELECT ba_id FROM _t_ba);
-- emittente.valuta resta v2 dal test 2.

CREATE TEMP TABLE _t_r3 AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, data, stato_doc_preventivo_id, billing_account_id,
    istanza_utility_id, utility_id
  )
  SELECT
    'PGT_V3_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    CURRENT_DATE,
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba),
    (SELECT utility_id FROM _t_ba)
  RETURNING valuta_id
)
SELECT valuta_id FROM ins;

SELECT is(
  (SELECT valuta_id FROM _t_r3),
  (SELECT v2 FROM _t_v),
  '3. Override emittente: BA senza valuta -> valuta_id = emittente.valuta_id'
);

-- ============================================================
-- 4) Fallback gestore: BA ed emittente senza valuta -> gestore.
-- ============================================================
UPDATE anagrafiche.emittenti_fiscali
   SET valuta_id = NULL WHERE id = (SELECT ef_id FROM _t_user_with_ef);

CREATE TEMP TABLE _t_r4 AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, data, stato_doc_preventivo_id, billing_account_id,
    istanza_utility_id, utility_id
  )
  SELECT
    'PGT_V4_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    CURRENT_DATE,
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba),
    (SELECT utility_id FROM _t_ba)
  RETURNING valuta_id
)
SELECT valuta_id FROM ins;

SELECT is(
  (SELECT valuta_id FROM _t_r4),
  (SELECT gestore_valuta FROM _t_v),
  '4. Fallback gestore: BA ed emittente senza valuta -> valuta_id = gestore.valuta_id'
);

-- ============================================================
-- 5) Skip: payload con valuta_id esplicito -> NON sovrascritto.
--    BA.valuta=v1 risolverebbe v1, ma passiamo v2 esplicito -> resta v2.
-- ============================================================
UPDATE anagrafiche.billing_account
   SET valuta_id = (SELECT v1 FROM _t_v) WHERE id = (SELECT ba_id FROM _t_ba);

CREATE TEMP TABLE _t_r5 AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, data, stato_doc_preventivo_id, billing_account_id,
    istanza_utility_id, utility_id, valuta_id
  )
  SELECT
    'PGT_V5_' || substring(md5(clock_timestamp()::text) from 1 for 8),
    CURRENT_DATE,
    (SELECT stato_id FROM _t_stato),
    (SELECT ba_id FROM _t_ba),
    (SELECT istanza_utility_id FROM _t_ba),
    (SELECT utility_id FROM _t_ba),
    (SELECT v2 FROM _t_v)
  RETURNING valuta_id
)
SELECT valuta_id FROM ins;

SELECT is(
  (SELECT valuta_id FROM _t_r5),
  (SELECT v2 FROM _t_v),
  '5. Payload con valuta_id esplicito -> trigger NON sovrascrive'
);

SELECT * FROM finish();
ROLLBACK;
