-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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

SELECT plan(5);

SET LOCAL zeroerp.allow_lock_columns_override = 'on';

-- ============================================================
-- Setup: contesto comune (dati reali esistenti)
-- ============================================================
CREATE TEMP TABLE _t_stato AS
SELECT id AS stato_id FROM config.stati_doc_preventivi
 WHERE attivo = true ORDER BY id LIMIT 1;

-- rev 2026-10-27 (lotto 4 di D7): cliente, emittente e gestore si COSTRUISCONO.
--   Prima si pescavano il primo BA, il primo utente django con un emittente
--   (e il contesto veniva ripuntato su di lui) e il primo gestore: da zero non
--   c'era nessuno dei tre e il primo INSERT moriva su E_CONFIG_MANCANTE.
--   Ora: BA costruito (legato all'azienda di chi agisce), emittente =
--   quello dell'operatore del contesto (lo stesso che il trigger emittente
--   assegna al preventivo), gestore = singleton prendi-o-costruisci.
--   Le valute v1/v2 si leggono dal catalogo di seed config.valute.
CREATE TEMP TABLE _t_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('default valuta documenti');

CREATE TEMP TABLE _t_ba AS
SELECT billing_account_id AS ba_id, istanza_utility_id, utility_id
  FROM _t_cli;

-- Utente con EF: l'operatore del contesto; il trigger emittente assegnera'
-- il suo ef al preventivo.
CREATE TEMP TABLE _t_user_with_ef AS
SELECT current_setting('app.current_user_id')::integer AS user_id,
       script.fn_pgtap_emittente_operatore() AS ef_id;

CREATE TEMP TABLE _t_gestore AS
SELECT * FROM dbops.fn_pgtap_crea_gestore('default valuta documenti');

-- Valute: gestore (fallback) + due valute distinte da esso per discriminare
-- i livelli BA/emittente dal fallback gestore.
CREATE TEMP TABLE _t_v AS
SELECT
  (SELECT g.valuta_id FROM anagrafiche.gestori g
                  WHERE g.id = (SELECT gestore_id FROM _t_gestore)) AS gestore_valuta,
  (SELECT v.id FROM config.valute v
     WHERE v.id <> (SELECT g.valuta_id FROM anagrafiche.gestori g
                  WHERE g.id = (SELECT gestore_id FROM _t_gestore))
     ORDER BY v.id LIMIT 1) AS v1,
  (SELECT v.id FROM config.valute v
     WHERE v.id <> (SELECT g.valuta_id FROM anagrafiche.gestori g
                  WHERE g.id = (SELECT gestore_id FROM _t_gestore))
     ORDER BY v.id OFFSET 1 LIMIT 1) AS v2;

-- Baseline pulita: azzera valuta su BA e sull'EF dell'utente.
UPDATE anagrafiche.billing_account
   SET valuta_id = NULL
 WHERE id = (SELECT ba_id FROM _t_ba);
UPDATE anagrafiche.emittenti_fiscali
   SET valuta_id = NULL
 WHERE id = (SELECT ef_id FROM _t_user_with_ef);

-- GUC operatore: necessaria al trigger emittente (che ordina prima). La mette
-- gia' il contesto in testa (rev 2026-10-27: non si ripunta piu' su un utente
-- pescato).

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
    script.fn_data_operativa(),
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
    script.fn_data_operativa(),
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
    script.fn_data_operativa(),
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
    script.fn_data_operativa(),
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
