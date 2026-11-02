-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--  8) Seed aree_funzionali: 11 righe attive
--  9) Seed aree_funzionali: tutti gli 11 codici attesi
-- 10) Seed aree_funzionali: schema_db = codice per tutte
-- 11) Seed aree_funzionali: ordinamento positivo
-- 12) UQ codice: vincolo UNIQUE presente
-- 13) UQ schema_db: vincolo UNIQUE presente
--     ⚠️ Fino al 2026-09-28 12-13 provavano un INSERT duplicato. Da quel giorno
--     l'app non scrive config.aree_funzionali (D-P9, 90_end/20260928-30): come app
--     l'INSERT darebbe 42501 prima di arrivare alla UNIQUE. La tabella la scrive
--     solo il seed, quindi si controlla il vincolo sul catalogo, non il
--     comportamento di una scrittura che l'applicazione non fa.
-- 14) Tabella config.azioni_processo esiste
-- 15) Seed azioni_processo: 8 righe attive
-- 16) Seed: genera_fatture_lotti marcata pericolosa
-- 17) Seed: FK area_id tutte valide
-- 18) UQ permission_codename: duplicato bloccato
-- 19) FK area_id: valore invalido bloccato
-- 20) Tabella config.area_model_overrides esiste
-- 21) area_model_overrides: INSERT valido accettato
-- 22) UQ (app_label, model_name): duplicato bloccato
-- 23) FK area_id: valore invalido bloccato
-- 24) Seed area_model_overrides: 11 righe attese
-- 25) Seed area_model_overrides: vendite.fattura → area_id 2
-- 26) Seed area_model_overrides: pratiche.pratica → area_id 12
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

SELECT plan(22);

-- ============================================================
-- 1. ⛔ RIMOSSO il 2026-08-18 — ENUM config.ruolo_sistema
--
--   Qui c'erano DUE asserzioni («l'enum esiste», «ha i valori ADMIN/OPERATIVO/
--   DISABILITATO»). L'enum e' stato ELIMINATO di proposito dal cutover
--   multi-face-auth: 90_end/20260429-20-drop-type-ruolo-sistema.
--
--   ⚠️ Non sono state «riparate» ma TOLTE, ed e' una differenza di merito:
--   asserivano l'esistenza di una cosa che una decisione ha rimosso. Un test
--   che pretende il contrario di una decisione presa non e' un presidio, e'
--   un ostacolo — e finche' era rosso in baseline zittiva le altre 22
--   asserzioni di questo file.
--
--   Stessa vittima del riferimento morto in
--   db/pgtap/config/test-user-emittenti-fiscali-immutable.sql: il cutover ha
--   lasciato indietro due file, non uno.
-- ============================================================

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
-- 3. ⛔ RIMOSSO il 2026-08-18 — colonna risorse_umane_auth_user.ruolo_sistema
--
--   Altre DUE asserzioni («la colonna esiste», «il default e' OPERATIVO») sulla
--   stessa vittima: la colonna e' stata eliminata da
--   90_end/20260429-19a-alter-legacy-rua-drop-ruolo-sistema, e la tabella
--   stessa e' oggi una VISTA su identita_digitali (l'originale e' archiviata
--   come _legacy_risorse_umane_auth_user).
-- ============================================================

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

SELECT cmp_ok(
    (SELECT count(*)::int FROM config.aree_funzionali WHERE attivo = true),
    '>=', 13,
    'Seed aree_funzionali: almeno 13 righe attive (nessuna sparita)'
);

SELECT ok(
    (SELECT count(*)::int
     FROM config.aree_funzionali
     WHERE codice IN (
         'anagrafiche', 'vendite', 'acquisti', 'catalogo',
         'contabilita', 'magazzino', 'pagamenti', 'storico',
         'config', 'core', 'pratiche'
     )
    ) = 11,
    'Seed aree_funzionali: tutti gli 11 codici attesi presenti'
);

SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM config.aree_funzionali
         WHERE schema_db IS DISTINCT FROM codice
    ),
    'Seed aree_funzionali: schema_db = codice per TUTTE le righe (invariante, non conteggio)'
);

SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM config.aree_funzionali
         WHERE ordinamento IS NULL OR ordinamento <= 0
    ),
    'Seed aree_funzionali: ordinamento positivo per TUTTE le righe (invariante, non conteggio)'
);

-- ⚠️ Il catalogo e non un INSERT: l'app non scrive la tabella (D-P9, 20260928-30).
SELECT col_is_unique(
    'config', 'aree_funzionali', ARRAY['codice'],
    'UQ codice: vincolo UNIQUE presente'
);

SELECT col_is_unique(
    'config', 'aree_funzionali', ARRAY['schema_db'],
    'UQ schema_db: vincolo UNIQUE presente (la chiave dei permessi)'
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

SELECT cmp_ok(
    (SELECT count(*)::int FROM config.azioni_processo WHERE attivo = true),
    '>=', 30,
    'Seed azioni_processo: almeno 30 righe attive (nessuna sparita)'
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

SELECT cmp_ok(
    (SELECT count(*)::int
       FROM config.area_model_overrides
      WHERE app_label NOT LIKE 'pgtap_test_app%'),
    '>=', 12,
    'Seed area_model_overrides: almeno 12 righe (nessuna sparita)'
);

SELECT is(
    (SELECT area_id
       FROM config.area_model_overrides
      WHERE app_label = 'vendite'
        AND model_name = 'fattura'),
    2,
    'Seed area_model_overrides: vendite.fattura → area_id 2'
);

SELECT is(
    (SELECT area_id
       FROM config.area_model_overrides
      WHERE app_label = 'pratiche'
        AND model_name = 'pratica'),
    12,
    'Seed area_model_overrides: pratiche.pratica → area_id 12'
);

SELECT * FROM finish();

ROLLBACK;
