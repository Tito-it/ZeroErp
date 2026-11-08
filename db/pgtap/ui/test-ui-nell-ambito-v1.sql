-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — il file legge il catalogo e i registri delle
--   automazioni, e costruisce un preset con il trigger di audit montato a mano:
--   nessuna tabella sotto RLS, una veste applicativa non cambierebbe risposta.
-- pgtap-runner: owner
-- pgtap-runner-motivo: il caso 9-10 MONTA il trigger di audit del framework su
--   ui.lista_preset (DDL), come lo monterebbe la convergenza: l'applicazione non
--   ha il privilegio di creare trigger. Tutto in transazione annullata.
-- pgTAP test per Zero ERP
--
-- Test: lo schema ui entra nell'ambito delle automazioni, col terreno pronto
--   Brief: brief-db-revisione-dbops, giro 7-bis blocco c (§23.12; decisioni
--   di Tid del 2026-11-08). ChangeSet: 20261109-32 (la colonna del contenuto
--   dei preset), -33 (audit NOT NULL), -34 ... -39 (le funzioni), CSV
--   automation_scope, automazione_attivo_eccezioni.
--
-- Elenco test (plan 10):
--   1) ui e' nell'ambito: dbops.fn_table_in_scope la vede, tabella per tabella
--   2) ⭐ il guard ATTIVO resta sulle cinque FK fra entita' con attivo: nessuna
--      e' nel registro delle eccezioni
--   3) ⭐ le sedici FK in eccezione (preferenze, righe di composizione, altri
--      domini) sono nel registro, ciascuna col suo motivo
--   4) le sei colonne codice di ui sono in eccezione per CODICE_MAIUSCOLO
--   5) le sette tabelle che prendono l'audit hanno data_update e user_update
--      NOT NULL col DEFAULT
--   6) i due preset hanno contenuto_aggiornato_il NOT NULL; le due preferenze
--      lo snapshot rinominato, e il nome vecchio non c'e' piu'
--   7) la funzione del contenuto e' quella nuova, la vecchia e' ritirata
--   8) i due trigger a20 dei preset sono sulla funzione nuova
--   9) ⭐ con l'audit montato, un UPDATE che non tocca il contenuto sposta
--      data_update e NON contenuto_aggiornato_il (caso COSTRUITO)
--  10) ⭐ ... e un UPDATE del contenuto li sposta tutti e due
--
-- ⚠️ I montaggi veri della convergenza (ci_apply) non si provano qui: dipendono
--   da quando la convergenza e' girata. Il caso 9-10 monta il trigger come lo
--   monterebbe il framework (stessa funzione, stesso momento) e prova la
--   regola, non lo stato di una macchina.
-- ------------------------------------------------------------
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli
--   (il COMMIT non arriva mai). Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- 1) L'ambito
-- ============================================================
SELECT is_empty(
    $q$SELECT c.relname::text
         FROM pg_class c
        WHERE c.relnamespace = 'ui'::regnamespace
          AND c.relkind IN ('r', 'p')
          AND NOT dbops.fn_table_in_scope('ui', c.relname::text)$q$,
    '1) ogni tabella di ui e'' nell''ambito delle automazioni');

-- ============================================================
-- 2-3) Il guard ATTIVO: dove resta, dove no
-- ============================================================
CREATE TEMP TABLE _fk_guard (tabella text, colonna text) ON COMMIT DROP;
INSERT INTO _fk_guard VALUES
    ('lista_colonna', 'lista_id'), ('lista_preset', 'lista_id'),
    ('dashboard_preset', 'dashboard_id'), ('widget', 'area_id'), ('widget', 'azione_id');

CREATE TEMP TABLE _fk_eccezione (tabella text, colonna text) ON COMMIT DROP;
INSERT INTO _fk_eccezione VALUES
    ('lista_preferenza_utente', 'lista_id'), ('lista_preferenza_utente', 'preset_base_id'),
    ('dashboard_preferenza_utente', 'dashboard_id'), ('dashboard_preferenza_utente', 'preset_base_id'),
    ('lista_preset_colonna', 'preset_id'), ('lista_preset_colonna', 'colonna_id'),
    ('lista_colonna_permesso', 'colonna_id'),
    ('dashboard_widget', 'dashboard_id'), ('dashboard_widget', 'widget_id'),
    ('dashboard_preset_widget', 'preset_id'), ('dashboard_preset_widget', 'widget_id'),
    ('lista_preset', 'emittente_fiscale_id'), ('lista_preset', 'profilo_accesso_id'),
    ('dashboard_preset', 'emittente_fiscale_id'), ('dashboard_preset', 'profilo_accesso_id'),
    ('lista_colonna_permesso', 'profilo_accesso_id');

SELECT is_empty(
    $q$SELECT g.tabella, g.colonna
         FROM _fk_guard g
         JOIN dbops.automazione_attivo_eccezioni e
           ON e.schema_figlia = 'ui' AND e.tabella_figlia = g.tabella AND e.colonna_fk = g.colonna$q$,
    '2) le cinque FK fra entita'' con attivo tengono il guard ATTIVO (nessuna in eccezione)');

SELECT is_empty(
    $q$SELECT x.tabella, x.colonna
         FROM _fk_eccezione x
        WHERE NOT EXISTS (SELECT 1 FROM dbops.automazione_attivo_eccezioni e
                           WHERE e.schema_figlia = 'ui' AND e.tabella_figlia = x.tabella
                             AND e.colonna_fk = x.colonna AND btrim(e.motivo) <> '')$q$,
    '3) le sedici FK fuori dal guard ATTIVO sono nel registro delle eccezioni, col motivo');

-- ============================================================
-- 4) I codici
-- ============================================================
SELECT is_empty(
    $q$SELECT t
         FROM unnest(ARRAY['lista_definizione', 'lista_colonna', 'lista_preset',
                           'dashboard_definizione', 'dashboard_preset', 'widget']) AS t
        WHERE NOT EXISTS (SELECT 1 FROM dbops.automazione_codice_eccezioni e
                           WHERE e.schema_name = 'ui' AND e.table_name = t
                             AND e.column_name = 'codice')$q$,
    '4) le sei colonne codice di ui sono chiavi tecniche in eccezione per CODICE_MAIUSCOLO');

-- ============================================================
-- 5-6) Le colonne
-- ============================================================
SELECT is_empty(
    $q$SELECT c.relname::text, a.attname::text
         FROM pg_attribute a
         JOIN pg_class c ON c.oid = a.attrelid
         LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE c.relnamespace = 'ui'::regnamespace
          AND c.relname IN ('dashboard_definizione', 'dashboard_preset', 'lista_colonna',
                            'lista_colonna_permesso', 'lista_definizione', 'lista_preset', 'widget')
          AND a.attname IN ('data_update', 'user_update')
          AND NOT a.attisdropped
          AND (NOT a.attnotnull OR d.adbin IS NULL)$q$,
    '5) le sette tabelle che prendono l''audit hanno data_update e user_update NOT NULL col DEFAULT');

SELECT is(
    (SELECT string_agg(format('%s.%s:%s', c.relname, a.attname, a.attnotnull::text), ',' ORDER BY c.relname, a.attname)
       FROM pg_attribute a
       JOIN pg_class c ON c.oid = a.attrelid
      WHERE c.relnamespace = 'ui'::regnamespace
        AND c.relname IN ('lista_preset', 'dashboard_preset', 'lista_preferenza_utente', 'dashboard_preferenza_utente')
        AND a.attname IN ('contenuto_aggiornato_il', 'preset_base_contenuto_aggiornato_il', 'preset_base_data_update')
        AND a.attnum > 0 AND NOT a.attisdropped),
    'dashboard_preferenza_utente.preset_base_contenuto_aggiornato_il:false,'
    || 'dashboard_preset.contenuto_aggiornato_il:true,'
    || 'lista_preferenza_utente.preset_base_contenuto_aggiornato_il:false,'
    || 'lista_preset.contenuto_aggiornato_il:true',
    '6) la data del contenuto ha la sua colonna sui preset, lo snapshot il nome nuovo');

-- ============================================================
-- 7-8) La funzione del contenuto e i suoi trigger
-- ============================================================
SELECT is(
    (SELECT string_agg(p.proname::text, ',' ORDER BY p.proname)
       FROM pg_proc p
      WHERE p.pronamespace = 'ui'::regnamespace
        AND p.proname IN ('trgfn_preset_contenuto_aggiornato', 'trgfn_preset_data_update_contenuto')),
    'trgfn_preset_contenuto_aggiornato',
    '7) la funzione del contenuto e'' quella nuova, la vecchia e'' ritirata');

SELECT is(
    (SELECT string_agg(format('%s:%s', c.relname, t.tgname), ',' ORDER BY c.relname)
       FROM pg_trigger t
       JOIN pg_class c ON c.oid = t.tgrelid
      WHERE NOT t.tgisinternal
        AND t.tgfoid = 'ui.trgfn_preset_contenuto_aggiornato()'::regprocedure),
    'dashboard_preset:trg_ui_dashboard_preset_a20_contenuto_aggiornato_upd,'
    || 'lista_preset:trg_ui_lista_preset_a20_contenuto_aggiornato_upd',
    '8) i due trigger a20 dei preset sono sulla funzione nuova');

-- ============================================================
-- 9-10) Il caso costruito: l'audit montato non tocca la data del contenuto
-- ============================================================
-- Il trigger come lo monta il framework (regola AUDIT_UPDATE): BEFORE INSERT
-- OR UPDATE, script.trgfn_audit_data_user_generic. Se la convergenza l'ha gia'
-- montato, il secondo non cambia niente: stessa funzione, stessi valori.
CREATE TRIGGER _pgtap_lista_preset_audit_data_user_upd
    BEFORE INSERT OR UPDATE ON ui.lista_preset
    FOR EACH ROW EXECUTE FUNCTION script.trgfn_audit_data_user_generic();

CREATE TEMP TABLE _l ON COMMIT DROP AS
WITH ins AS (
  INSERT INTO ui.lista_definizione (codice, descrizione, schema_dati, vista_sql, attivo, user_insert)
  VALUES ('_pgtap.ambito_' || substr(md5(clock_timestamp()::text), 1, 6),
          'Lista test pgTAP ui nell''ambito', 'pgtap', NULL, TRUE, '_pgtap')
  RETURNING id
)
SELECT id AS lista_id FROM ins;

CREATE TEMP TABLE _p ON COMMIT DROP AS
WITH ins AS (
  INSERT INTO ui.lista_preset (lista_id, codice, descrizione, ambito, is_default,
                               ordinamento_default, attivo, user_insert)
  SELECT l.lista_id, 'pgtap_ambito', 'Preset test ui nell''ambito', 'sistema', TRUE,
         '[]'::jsonb, TRUE, '_pgtap'
    FROM _l l
  RETURNING id
)
SELECT id AS preset_id FROM ins;

-- Le due date indietro, a un istante noto: il trigger di audit va spento per
-- poterle scrivere, poi si riaccende.
ALTER TABLE ui.lista_preset DISABLE TRIGGER _pgtap_lista_preset_audit_data_user_upd;
UPDATE ui.lista_preset
   SET data_update = TIMESTAMPTZ '2026-01-01 10:00:00+00',
       contenuto_aggiornato_il = TIMESTAMPTZ '2026-01-01 10:00:00+00'
 WHERE id = (SELECT preset_id FROM _p);
ALTER TABLE ui.lista_preset ENABLE TRIGGER _pgtap_lista_preset_audit_data_user_upd;

UPDATE ui.lista_preset SET descrizione = 'Preset test ui nell''ambito, rinominato'
 WHERE id = (SELECT preset_id FROM _p);

SELECT is(
    (SELECT format('%s|%s', (data_update = now())::text, (contenuto_aggiornato_il = TIMESTAMPTZ '2026-01-01 10:00:00+00')::text)
       FROM ui.lista_preset WHERE id = (SELECT preset_id FROM _p)),
    'true|true',
    '9) con l''audit montato, cambiare la descrizione sposta data_update e non la data del contenuto');

UPDATE ui.lista_preset SET ordinamento_default = '[{"col": "x", "dir": "asc"}]'::jsonb
 WHERE id = (SELECT preset_id FROM _p);

SELECT is(
    (SELECT format('%s|%s', (data_update = now())::text, (contenuto_aggiornato_il = now())::text)
       FROM ui.lista_preset WHERE id = (SELECT preset_id FROM _p)),
    'true|true',
    '10) ... e cambiare il contenuto sposta tutte e due le date');

SELECT * FROM finish();
ROLLBACK;
