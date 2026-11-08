-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: ui.fn_resolve_lista_config — flag preset_aggiornato (DEF-2)
-- ------------------------------------------------------------
-- Indice test (1..6):
-- Caso A) snapshot allineato (preset_base_contenuto_aggiornato_il = lista_preset.contenuto_aggiornato_il)
--         → preset_aggiornato = FALSE
-- Caso B) admin modifica il preset (UPDATE lista_preset.contenuto_aggiornato_il a ts_v2 > snapshot)
--         → preset_aggiornato = TRUE
-- Caso C) utente preme "Ignora" (preset_aggiornato_ignored_at = ts_ignored > ts_v2)
--         → preset_aggiornato = FALSE
-- Caso D) admin modifica il preset di nuovo (ts_v3 > ts_ignored)
--         → preset_aggiornato = TRUE (ignored_at < contenuto_aggiornato_il)
-- Caso E) nessuna preferenza utente (usa preset di sistema, no snapshot)
--         → preset_aggiornato = FALSE
-- Caso F) cambio preset_base_id (trigger azzera snapshot e ignored_at)
--         → preset_aggiornato = FALSE
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
-- Timestamp fissi per test deterministici
-- ============================================================
-- ts_v1: prima versione del preset (usata come snapshot iniziale)
-- ts_v2: admin aggiorna preset dopo ts_v1
-- ts_ignored: utente ignora dopo ts_v2
-- ts_v3: admin aggiorna preset di nuovo dopo ts_ignored
-- ============================================================

-- ============================================================
-- Setup: lista di test + 1 colonna + preset sistema + auth_user
-- ============================================================

-- Lista di test
CREATE TEMP TABLE _t_lista_pa AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (
    codice, descrizione, schema_dati, vista_sql, attivo, user_insert
  ) VALUES (
    '_pgtap.test_pa_' || substr(md5(clock_timestamp()::text), 1, 6),
    'Lista test pgTAP preset_aggiornato DEF-2',
    'pgtap', NULL, TRUE, '_pgtap'
  )
  RETURNING id, codice
)
SELECT id AS lista_id, codice AS lista_codice FROM ins;

-- Colonna di test (tipo informazione, non sensibile)
CREATE TEMP TABLE _t_col_pa AS
WITH ins AS (
  INSERT INTO ui.lista_colonna (
    lista_id, codice, etichetta, campo_sorgente,
    tipo_colonna, tipo_dato, ordine_default, attivo, user_insert
  )
  SELECT lista_id, 'col_pa', 'Colonna PA', 'col_pa',
         'informazione', 'string', 10, TRUE, '_pgtap'
  FROM _t_lista_pa
  RETURNING id
)
SELECT id AS col_id FROM ins;

-- Preset sistema per la lista (ambito='sistema', is_default=TRUE)
CREATE TEMP TABLE _t_preset_pa AS
WITH ins AS (
  INSERT INTO ui.lista_preset (
    lista_id, codice, descrizione, ambito, is_default,
    pagina_dimensione, attivo, user_insert
  )
  SELECT lista_id, 'SISTEMA_PA', 'Preset sistema test PA',
         'sistema', TRUE, 25, TRUE, '_pgtap'
  FROM _t_lista_pa
  RETURNING id
)
SELECT id AS preset_id FROM ins;

-- Colonna nel preset
INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, visibile, fissata)
SELECT p.preset_id, c.col_id, 10, TRUE, FALSE
FROM _t_preset_pa p, _t_col_pa c;

-- Imposta contenuto_aggiornato_il del preset a ts_v1 (prima versione)
UPDATE ui.lista_preset
   SET contenuto_aggiornato_il = TIMESTAMP '2026-01-01 10:00:00'
 WHERE id = (SELECT preset_id FROM _t_preset_pa);

-- auth_user di test
CREATE TEMP TABLE _t_au_pa AS
WITH ins AS (
  INSERT INTO django.auth_user (
    username, password, is_active, is_staff, is_superuser,
    first_name, last_name, email, date_joined
  ) VALUES (
    '_pgtap_pa_' || substr(md5(clock_timestamp()::text), 1, 8),
    'unusable', TRUE, FALSE, FALSE,
    'PGTap', 'PresetAggiornato', '_pgtap_pa@example.com', NOW()
  )
  RETURNING id
)
SELECT id AS user_id FROM ins;

-- Preferenza utente con preset_base_id puntato al preset sistema,
-- snapshot allineato (preset_base_contenuto_aggiornato_il = ts_v1 = contenuto_aggiornato_il corrente del preset)
CREATE TEMP TABLE _t_pref_pa AS
WITH ins AS (
  INSERT INTO ui.lista_preferenza_utente (
    auth_user_id, lista_id, preset_base_id, preset_base_contenuto_aggiornato_il,
    configurazione
  )
  SELECT
    u.user_id, l.lista_id, p.preset_id,
    TIMESTAMP '2026-01-01 10:00:00',
    jsonb_build_object(
      'colonne', jsonb_build_array(
        jsonb_build_object(
          'codice', 'col_pa', 'ordine', 10,
          'larghezza', 100, 'visibile', true, 'fissata', false
        )
      ),
      'ordinamento', '[]'::jsonb,
      'filtri', '{}'::jsonb,
      'pagina_dimensione', 25
    )
  FROM _t_au_pa u, _t_lista_pa l, _t_preset_pa p
  RETURNING id, auth_user_id, lista_id
)
SELECT id AS pref_id, auth_user_id, lista_id FROM ins;

-- ============================================================
-- CASO A) snapshot allineato → preset_aggiornato = FALSE
-- lista_preset.contenuto_aggiornato_il = TIMESTAMP '2026-01-01 10:00:00'
-- preset_base_contenuto_aggiornato_il  = TIMESTAMP '2026-01-01 10:00:00'
-- → contenuto_aggiornato_il NON > snapshot → FALSE
-- ============================================================
SELECT is(
  (SELECT ui.fn_resolve_lista_config(l.lista_codice, u.user_id, NULL)->>'preset_aggiornato'
     FROM _t_lista_pa l, _t_au_pa u
  ),
  'false',
  'Caso A: snapshot allineato → preset_aggiornato = FALSE'
);

-- ============================================================
-- CASO B) admin modifica il preset → preset_aggiornato = TRUE
-- Simula: UPDATE lista_preset SET contenuto_aggiornato_il = ts_v2 (> ts_v1)
-- ============================================================
UPDATE ui.lista_preset
   SET contenuto_aggiornato_il = TIMESTAMP '2026-03-01 10:00:00'
 WHERE id = (SELECT preset_id FROM _t_preset_pa);

SELECT is(
  (SELECT ui.fn_resolve_lista_config(l.lista_codice, u.user_id, NULL)->>'preset_aggiornato'
     FROM _t_lista_pa l, _t_au_pa u
  ),
  'true',
  'Caso B: preset aggiornato dopo snapshot → preset_aggiornato = TRUE'
);

-- ============================================================
-- CASO C) utente ignora il banner → preset_aggiornato = FALSE
-- preset_aggiornato_ignored_at = ts_ignored (> ts_v2)
-- ============================================================
UPDATE ui.lista_preferenza_utente
   SET preset_aggiornato_ignored_at = TIMESTAMP '2026-04-01 10:00:00'
 WHERE id = (SELECT pref_id FROM _t_pref_pa);

SELECT is(
  (SELECT ui.fn_resolve_lista_config(l.lista_codice, u.user_id, NULL)->>'preset_aggiornato'
     FROM _t_lista_pa l, _t_au_pa u
  ),
  'false',
  'Caso C: ignored_at >= contenuto_aggiornato_il → preset_aggiornato = FALSE'
);

-- ============================================================
-- CASO D) admin modifica il preset di nuovo dopo l'ignore → TRUE
-- contenuto_aggiornato_il = ts_v3 > ts_ignored → banner riappare
-- ============================================================
UPDATE ui.lista_preset
   SET contenuto_aggiornato_il = TIMESTAMP '2026-05-01 10:00:00'
 WHERE id = (SELECT preset_id FROM _t_preset_pa);

SELECT is(
  (SELECT ui.fn_resolve_lista_config(l.lista_codice, u.user_id, NULL)->>'preset_aggiornato'
     FROM _t_lista_pa l, _t_au_pa u
  ),
  'true',
  'Caso D: preset modificato di nuovo dopo ignored_at → preset_aggiornato = TRUE'
);

-- ============================================================
-- CASO E) nessuna preferenza → il preset di sistema viene usato
--         ma non c''e'' snapshot → preset_aggiornato = FALSE
-- Usa un secondo auth_user senza preferenza
-- ============================================================
CREATE TEMP TABLE _t_au_pa2 AS
WITH ins AS (
  INSERT INTO django.auth_user (
    username, password, is_active, is_staff, is_superuser,
    first_name, last_name, email, date_joined
  ) VALUES (
    '_pgtap_pa2_' || substr(md5(clock_timestamp()::text), 1, 8),
    'unusable', TRUE, FALSE, FALSE,
    'PGTap2', 'PresetAggiornato2', '_pgtap_pa2@example.com', NOW()
  )
  RETURNING id
)
SELECT id AS user_id FROM ins;

SELECT is(
  (SELECT ui.fn_resolve_lista_config(l.lista_codice, u.user_id, NULL)->>'preset_aggiornato'
     FROM _t_lista_pa l, _t_au_pa2 u
  ),
  'false',
  'Caso E: nessuna preferenza utente (preset sistema) → preset_aggiornato = FALSE'
);

-- ============================================================
-- CASO F) cambio preset_base_id → trigger azzera snapshot e ignored_at
--         fn legge preset_base_id=NULL → preset_aggiornato = FALSE
-- ============================================================
UPDATE ui.lista_preferenza_utente
   SET preset_base_id = NULL
 WHERE id = (SELECT pref_id FROM _t_pref_pa);

SELECT is(
  (SELECT ui.fn_resolve_lista_config(l.lista_codice, u.user_id, NULL)->>'preset_aggiornato'
     FROM _t_lista_pa l, _t_au_pa u
  ),
  'false',
  'Caso F: preset_base_id → NULL (trigger azzera snapshot e ignored_at) → preset_aggiornato = FALSE'
);

SELECT * FROM finish();
ROLLBACK;
