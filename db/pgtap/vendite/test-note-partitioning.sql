-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.note — struttura partitioned table e routing
--
-- Elenco test:
--   1) vendite.note è una PARTITIONED TABLE
--   2) Strategia di partizione è LIST (partstrat='l')
--   3) Partizione note_preventivo esiste
--   4) Partizione note_contratto esiste
--   5) Partizione note_ordini esiste
--   6) Partizione note_ddt esiste
--   7) Partizione note_fatture esiste
--   8) Partizione note_attivita_fatturabili esiste
--   9) note_preventivo           — FK testata (fk_prevnote_testata) esiste
--  10) note_contratto            — FK testata (fk_contnote_testata) esiste
--  11) note_ordini               — FK testata (fk_ordini_note_testata) esiste
--  12) note_ddt                  — FK testata (fk_ddt_note_testata) esiste
--  13) note_fatture              — FK testata (fk_fatture_note_testata) esiste
--  14) note_attivita_fatturabili — FK testata (fk_ven_note_att_testata) esiste
--  15) note_preventivo           — trigger validate (trg_note_preventivo_validate_ins_upd) esiste
--  16) note_contratto            — trigger validate (trg_note_contratto_validate_ins_upd) esiste
--  17) note_ordini               — trigger validate (trg_note_ordini_validate_ins_upd) esiste
--  18) note_ddt                  — trigger validate (trg_note_ddt_validate_ins_upd) esiste
--  19) note_fatture              — trigger validate (trg_note_fatture_validate_ins_upd) esiste
--  20) note_attivita_fatturabili — trigger validate ASSENTE (attivita non hanno righe documento)
--  21) Routing: target_tipo non valido → errore (no matching partition)
--  22) config.note_stili contiene riga codice_interno='DEFAULT' (seed 20260519-02)
--  23) config.parameters contiene code='NOTE_DEFAULT_STILE' con default_value='DEFAULT'
-- ------------------------------------------------------------
--
-- Nota architetturale:
--   trgfn_note_validate_generic è definita su OGNI partizione con parametri
--   specifici (tabella righe, colonna FK). Il dominio dell'errore lo prende da
--   NEW.target_tipo (rev 2026-10-25, 20261025-66/-67: il terzo argomento, che
--   ripeteva il confine della partizione, è ritirato). Non è sul
--   padre vendite.note — ogni partizione ha il proprio trigger con i parametri
--   corretti per la propria testata/riga. La partizione note_attivita_fatturabili
--   non ha questo trigger perché attività fatturabili non hanno "righe" nel
--   senso documentale (target_riga_id rimane NULL).
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

SELECT plan(23);

-- ============================================================
-- 1) vendite.note è PARTITIONED TABLE
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'note'
           AND c.relkind = 'p'
    ),
    '1) vendite.note e'' una PARTITIONED TABLE (relkind=p)'
);

-- ============================================================
-- 2) Strategia partizione LIST
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1
          FROM pg_partitioned_table pt
          JOIN pg_class c ON c.oid = pt.partrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'note'
           AND pt.partstrat = 'l'
    ),
    '2) vendite.note usa strategia LIST (partstrat=l)'
);

-- ============================================================
-- 3-8) Le 6 partizioni esistono
-- ============================================================
SELECT has_table('vendite', 'note_preventivo',           '3) partizione note_preventivo esiste');
SELECT has_table('vendite', 'note_contratto',            '4) partizione note_contratto esiste');
SELECT has_table('vendite', 'note_ordini',               '5) partizione note_ordini esiste');
SELECT has_table('vendite', 'note_ddt',                  '6) partizione note_ddt esiste');
SELECT has_table('vendite', 'note_fatture',              '7) partizione note_fatture esiste');
SELECT has_table('vendite', 'note_attivita_fatturabili', '8) partizione note_attivita_fatturabili esiste');

-- ============================================================
-- 9-14) FK testata su ogni partizione (verifica per nome vincolo
--       via information_schema — pattern consolidato nel progetto)
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_schema = 'vendite' AND table_name = 'note_preventivo'
              AND constraint_name = 'fk_prevnote_testata' AND constraint_type = 'FOREIGN KEY'),
    '9)  note_preventivo — FK testata (fk_prevnote_testata) esiste'
);
SELECT ok(
    EXISTS(SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_schema = 'vendite' AND table_name = 'note_contratto'
              AND constraint_name = 'fk_contnote_testata' AND constraint_type = 'FOREIGN KEY'),
    '10) note_contratto — FK testata (fk_contnote_testata) esiste'
);
SELECT ok(
    EXISTS(SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_schema = 'vendite' AND table_name = 'note_ordini'
              AND constraint_name = 'fk_ordini_note_testata' AND constraint_type = 'FOREIGN KEY'),
    '11) note_ordini — FK testata (fk_ordini_note_testata) esiste'
);
SELECT ok(
    EXISTS(SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_schema = 'vendite' AND table_name = 'note_ddt'
              AND constraint_name = 'fk_ddt_note_testata' AND constraint_type = 'FOREIGN KEY'),
    '12) note_ddt — FK testata (fk_ddt_note_testata) esiste'
);
SELECT ok(
    EXISTS(SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_schema = 'vendite' AND table_name = 'note_fatture'
              AND constraint_name = 'fk_fatture_note_testata' AND constraint_type = 'FOREIGN KEY'),
    '13) note_fatture — FK testata (fk_fatture_note_testata) esiste'
);
SELECT ok(
    EXISTS(SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_schema = 'vendite' AND table_name = 'note_attivita_fatturabili'
              AND constraint_name = 'fk_ven_note_att_testata' AND constraint_type = 'FOREIGN KEY'),
    '14) note_attivita_fatturabili — FK testata (fk_ven_note_att_testata) esiste'
);

-- ============================================================
-- 15-19) Trigger validate su 5 partizioni (con parametri partition-specifici)
--        Ogni partizione ha il proprio trigger con tabella righe e FK column propri.
--        I trigger non sono sul padre vendite.note ma su ogni singola partizione.
-- ============================================================
SELECT has_trigger('vendite', 'note_preventivo', 'trg_note_preventivo_validate_ins_upd',
    '15) note_preventivo — trg_note_preventivo_validate_ins_upd esiste');

SELECT has_trigger('vendite', 'note_contratto',  'trg_note_contratto_validate_ins_upd',
    '16) note_contratto — trg_note_contratto_validate_ins_upd esiste');

SELECT has_trigger('vendite', 'note_ordini',     'trg_note_ordini_validate_ins_upd',
    '17) note_ordini — trg_note_ordini_validate_ins_upd esiste');

SELECT has_trigger('vendite', 'note_ddt',        'trg_note_ddt_validate_ins_upd',
    '18) note_ddt — trg_note_ddt_validate_ins_upd esiste');

SELECT has_trigger('vendite', 'note_fatture',    'trg_note_fatture_validate_ins_upd',
    '19) note_fatture — trg_note_fatture_validate_ins_upd esiste');

-- ============================================================
-- 20) note_attivita_fatturabili NON ha il trigger validate
--     (attività fatturabili non hanno righe documento: target_riga_id rimane NULL)
-- ============================================================
SELECT ok(
    NOT EXISTS(
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = 'vendite'
           AND c.relname = 'note_attivita_fatturabili'
           AND t.tgname  = 'trg_note_attivita_fatturabili_validate_ins_upd'
    ),
    '20) note_attivita_fatturabili — trigger validate ASSENTE (by design: no righe)'
);

-- ============================================================
-- 21) Routing: target_tipo non valido → errore (no matching partition)
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM config.note_stili LIMIT 1)
    THEN skip('21) nessuno stile in config.note_stili — routing test saltato')
    ELSE throws_ok(
        format(
            $$INSERT INTO vendite.note
                (target_tipo, target_id, id_stile, anchor_tipo, posizione, testo)
              VALUES ('TIPO_INESISTENTE_XYZ', -1, %s, 'TESTATA', 'PRIMA', 'test routing')$$,
            (SELECT id FROM config.note_stili ORDER BY id LIMIT 1)
        ),
        NULL,
        NULL,
        '21) target_tipo non valido → errore (no matching partition)'
    )
END;

-- ============================================================
-- 22) Seed DEFAULT in config.note_stili (migration 20260519-02)
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1 FROM config.note_stili
         WHERE codice_interno = 'DEFAULT'
           AND attivo = true
    ),
    '22) config.note_stili contiene riga codice_interno=DEFAULT attiva (seed 20260519-02)'
);

-- ============================================================
-- 23) Parametro NOTE_DEFAULT_STILE con default_value='DEFAULT' (migration 20260519-04)
-- ============================================================
SELECT is(
    (SELECT p.default_value FROM config.parameters p WHERE p.code = 'NOTE_DEFAULT_STILE'),
    'DEFAULT',
    '23) config.parameters.NOTE_DEFAULT_STILE ha default_value=DEFAULT (seed 20260519-04)'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
