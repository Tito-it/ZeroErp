-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: strutture base permessi e autorizzazioni
--       ENUM ruolo_sistema, livello_accesso,
--       colonna ruolo_sistema su risorse_umane_auth_user,
--       tabelle catalogo aree_funzionali, azioni_processo,
--       area_model_overrides + seed data.
--
-- Elenco test:
--  1) ENUM config.ruolo_sistema esiste
--  2) ENUM ruolo_sistema: valori ADMIN, OPERATIVO, DISABILITATO
--  3) ENUM config.livello_accesso esiste
--  4) ENUM livello_accesso: valori TUTTO, LETTURA, BLOCCATO
--  5) Colonna risorse_umane_auth_user.ruolo_sistema esiste
--  6) Default ruolo_sistema = OPERATIVO
--  7) Tabella config.aree_funzionali esiste
--  8) Seed aree_funzionali: 10 righe attive
--  9) Seed aree_funzionali: tutti i 10 codici attesi
-- 10) Seed aree_funzionali: schema_db = codice per tutte
-- 11) Seed aree_funzionali: ordinamento positivo
-- 12) UQ codice: duplicato bloccato
-- 13) UQ schema_db: duplicato bloccato
-- 14) Tabella config.azioni_processo esiste
-- 15) Seed azioni_processo: 5 righe attive
-- 16) Seed: genera_fatture_lotti marcata pericolosa
-- 17) Seed: FK area_id tutte valide
-- 18) UQ permission_codename: duplicato bloccato
-- 19) FK area_id: valore invalido bloccato
-- 20) Tabella config.area_model_overrides esiste
-- 21) area_model_overrides: INSERT valido accettato
-- 22) UQ (app_label, model_name): duplicato bloccato
-- 23) FK area_id: valore invalido bloccato
-- ------------------------------------------------------------

BEGIN;

SELECT plan(23);

-- ============================================================
-- 1. ENUM config.ruolo_sistema
-- ============================================================

SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'config'
          AND t.typname = 'ruolo_sistema'
    ),
    'ENUM config.ruolo_sistema esiste'
);

SELECT is(
    (SELECT array_agg(e.enumlabel ORDER BY e.enumsortorder)::text[]
     FROM pg_enum e
     JOIN pg_type t ON t.oid = e.enumtypid
     JOIN pg_namespace n ON n.oid = t.typnamespace
     WHERE n.nspname = 'config'
       AND t.typname = 'ruolo_sistema'),
    ARRAY['ADMIN', 'OPERATIVO', 'DISABILITATO'],
    'ENUM ruolo_sistema: valori ADMIN, OPERATIVO, DISABILITATO'
);

-- ============================================================
-- 2. ENUM config.livello_accesso
-- ============================================================

SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'config'
          AND t.typname = 'livello_accesso'
    ),
    'ENUM config.livello_accesso esiste'
);

SELECT is(
    (SELECT array_agg(e.enumlabel ORDER BY e.enumsortorder)::text[]
     FROM pg_enum e
     JOIN pg_type t ON t.oid = e.enumtypid
     JOIN pg_namespace n ON n.oid = t.typnamespace
     WHERE n.nspname = 'config'
       AND t.typname = 'livello_accesso'),
    ARRAY['TUTTO', 'LETTURA', 'BLOCCATO'],
    'ENUM livello_accesso: valori TUTTO, LETTURA, BLOCCATO'
);

-- ============================================================
-- 3. Colonna ruolo_sistema su risorse_umane_auth_user
-- ============================================================

SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'anagrafiche'
          AND c.relname = 'risorse_umane_auth_user'
          AND a.attname = 'ruolo_sistema'
          AND NOT a.attisdropped
    ),
    'Colonna anagrafiche.risorse_umane_auth_user.ruolo_sistema esiste'
);

SELECT is(
    (SELECT pg_get_expr(d.adbin, d.adrelid)
     FROM pg_attrdef d
     JOIN pg_attribute a ON a.attrelid = d.adrelid AND a.attnum = d.adnum
     JOIN pg_class c ON c.oid = a.attrelid
     JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'anagrafiche'
       AND c.relname = 'risorse_umane_auth_user'
       AND a.attname = 'ruolo_sistema'),
    '''OPERATIVO''::config.ruolo_sistema',
    'Default ruolo_sistema = OPERATIVO'
);

-- ============================================================
-- 4. Tabella config.aree_funzionali + seed
-- ============================================================

SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'config'
          AND c.relname = 'aree_funzionali'
          AND c.relkind = 'r'
    ),
    'Tabella config.aree_funzionali esiste'
);

SELECT is(
    (SELECT count(*)::int FROM config.aree_funzionali WHERE attivo = true),
    10,
    'Seed aree_funzionali: 10 righe attive'
);

SELECT ok(
    (SELECT count(*)::int
     FROM config.aree_funzionali
     WHERE codice IN (
         'anagrafiche', 'vendite', 'acquisti', 'catalogo',
         'contabilita', 'magazzino', 'pagamenti', 'storico',
         'config', 'core'
     )
    ) = 10,
    'Seed aree_funzionali: tutti i 10 codici attesi presenti'
);

SELECT ok(
    (SELECT count(*)::int
     FROM config.aree_funzionali
     WHERE schema_db = codice
    ) = 10,
    'Seed aree_funzionali: schema_db = codice per tutte le righe'
);

SELECT ok(
    (SELECT count(*)::int
     FROM config.aree_funzionali
     WHERE ordinamento > 0
    ) = 10,
    'Seed aree_funzionali: ordinamento positivo per tutte le righe'
);

SELECT throws_ok(
    $$INSERT INTO config.aree_funzionali
          (codice, codice_interno, descrizione, schema_db, ordinamento)
      VALUES ('anagrafiche', 'pgtap_dup_ci', 'Test', 'pgtap_dup_schema', 999)$$,
    '23505',
    NULL,
    'UQ codice: duplicato bloccato'
);

SELECT throws_ok(
    $$INSERT INTO config.aree_funzionali
          (codice, codice_interno, descrizione, schema_db, ordinamento)
      VALUES ('pgtap_dup_codice', 'pgtap_dup_ci2', 'Test', 'anagrafiche', 999)$$,
    '23505',
    NULL,
    'UQ schema_db: duplicato bloccato'
);

-- ============================================================
-- 5. Tabella config.azioni_processo + seed
-- ============================================================

SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'config'
          AND c.relname = 'azioni_processo'
          AND c.relkind = 'r'
    ),
    'Tabella config.azioni_processo esiste'
);

SELECT is(
    (SELECT count(*)::int FROM config.azioni_processo WHERE attivo = true),
    5,
    'Seed azioni_processo: 5 righe attive'
);

SELECT is(
    (SELECT pericolosa
     FROM config.azioni_processo
     WHERE permission_codename = 'genera_fatture_lotti'),
    true,
    'Seed: genera_fatture_lotti marcata come pericolosa'
);

SELECT is(
    (SELECT count(*)::int
     FROM config.azioni_processo ap
     JOIN config.aree_funzionali af ON af.id = ap.area_id),
    (SELECT count(*)::int FROM config.azioni_processo),
    'Seed azioni_processo: FK area_id tutte valide'
);

SELECT throws_ok(
    format(
        $$INSERT INTO config.azioni_processo
              (area_id, permission_codename, descrizione)
          VALUES (%s, 'genera_fatture_lotti', 'Duplicato')$$,
        (SELECT id FROM config.aree_funzionali WHERE codice = 'vendite')
    ),
    '23505',
    NULL,
    'UQ permission_codename: duplicato bloccato'
);

SELECT throws_ok(
    $$INSERT INTO config.azioni_processo
          (id, area_id, permission_codename, descrizione)
      VALUES (99999, 999999, 'pgtap_fk_invalid', 'Test FK')$$,
    '23503',
    NULL,
    'FK area_id: valore invalido bloccato'
);

-- ============================================================
-- 6. Tabella config.area_model_overrides
-- ============================================================

SELECT ok(
    EXISTS (
        SELECT 1
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'config'
          AND c.relname = 'area_model_overrides'
          AND c.relkind = 'r'
    ),
    'Tabella config.area_model_overrides esiste'
);

SELECT lives_ok(
    format(
        $$INSERT INTO config.area_model_overrides
              (app_label, model_name, area_id)
          VALUES ('pgtap_test_app', 'pgtap_test_model', %s)$$,
        (SELECT id FROM config.aree_funzionali WHERE codice = 'vendite')
    ),
    'area_model_overrides: INSERT valido accettato'
);

SELECT throws_ok(
    format(
        $$INSERT INTO config.area_model_overrides
              (app_label, model_name, area_id)
          VALUES ('pgtap_test_app', 'pgtap_test_model', %s)$$,
        (SELECT id FROM config.aree_funzionali WHERE codice = 'vendite')
    ),
    '23505',
    NULL,
    'UQ (app_label, model_name): duplicato bloccato'
);

SELECT throws_ok(
    $$INSERT INTO config.area_model_overrides
          (app_label, model_name, area_id)
      VALUES ('pgtap_test_app2', 'pgtap_test_model2', 999999)$$,
    '23503',
    NULL,
    'FK area_id: valore invalido bloccato'
);

SELECT * FROM finish();

ROLLBACK;
