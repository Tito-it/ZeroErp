-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Step 1.1 refactor cascata parametri
--       Nuova dimensione categoria_cliente_id su config.parameter_overrides
--       Migrations:
--         20260515-06 (ALTER TABLE — colonna + FK + UNIQUE v4 + indice)
--         20260515-07 (trigger trg_parameter_overrides_a10_cat_clienti_req_attivo_ins_upd)
--         20261007-70 (UNIQUE v5 NULLS NOT DISTINCT al posto del v4)
--         20261007-72 (CHECK chk_parameter_overrides_un_ambito: un ambito per override)
--
-- ⚠️ Rev 2026-10-07 (brief-db-codici-sfilati-e-lista-parametri §3): il v4 era
--   NULLS DISTINCT e non scattava su nessuna riga con una dimensione NULL, cioe'
--   mai. I test 7-8 seguono il vincolo nuovo e il 13 ne prova il comportamento.
--   Il parametro della fixture e' ora COSTRUITO dal test: col vincolo che vale
--   davvero, un override sul primo parametro reale (test 11: tutte le dimensioni
--   NULL) rifiuterebbe il giorno in cui quell'ambito esiste gia' sul DB.
-- ⚠️ Rev 2026-10-07 bis (§7.6 del brief, decisione di Tid): ogni override ha
--   ESATTAMENTE un ambito. Il test 11, che scriveva una riga senza ambito e se
--   l'aspettava accettata, ora ne pretende il rifiuto; il 14 prova il rifiuto
--   della riga mista, il 15 la presenza del vincolo.
--
-- Indice test (1..15):
--   1)  Colonna categoria_cliente_id presente
--   2)  Colonna nullable (smallint NULL)
--   3)  FK fk_overrides_categoria_cliente presente
--   4)  FK: ON UPDATE CASCADE
--   5)  FK: ON DELETE RESTRICT
--   6)  Indice ix_overrides_param_categoria_cliente presente
--   7)  UNIQUE v5 presente (uq_overrides_full_scope_v5), NULLS NOT DISTINCT
--   8)  UNIQUE v3 e v4 rimossi
--   9)  Trigger guard categoria attiva presente
--  10)  INSERT override con categoria attiva -> ok
--  11)  INSERT override senza nessun ambito -> 23514
--  12)  INSERT override con categoria disattiva -> raise
--  13)  Secondo override sullo stesso ambito (NULL compresi) -> 23505
--  14)  INSERT override con due ambiti (utente + categoria) -> 23514
--  15)  CHECK chk_parameter_overrides_un_ambito presente
-- ------------------------------------------------------------

BEGIN;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(15);

-- ============================================================
-- Setup: parametro esistente + due categorie clienti test
-- ============================================================
-- 2026-10-25 (brief-db-parametri-senza-override): config.parameters.ammette_override
-- e' NOT NULL senza DEFAULT, un parametro dichiara la sua famiglia.
INSERT INTO config.parameters (id, code, default_value, description, ammette_override, tipo_valore)
VALUES (99970, '_TEST_OVR_CAT_CLI_', 'DEF', 'Test parameter_overrides categoria cliente', true, 'TESTO');

CREATE TEMP TABLE tmp_cat_ctx AS
SELECT
    (SELECT id FROM config.parameters WHERE code = '_TEST_OVR_CAT_CLI_') AS param_id;

-- Due categorie test: una attiva, una disattiva.
-- IDs alti per evitare collisioni con dati seed.
INSERT INTO anagrafiche.categorie_clienti
    (id, codice, codice_interno, descrizione, partecipa_promo, ordinamento, attivo)
VALUES
    (9001, 'TEST_CATCLI_ATTIVA',   'TEST_CATCLI_ATTIVA',   'Categoria test attiva',   TRUE, 900, TRUE),
    (9002, 'TEST_CATCLI_DISATTIVA','TEST_CATCLI_DISATTIVA','Categoria test disattiva', TRUE, 901, FALSE);

-- ============================================================
-- 1) Colonna presente
-- ============================================================
SELECT has_column(
    'config', 'parameter_overrides', 'categoria_cliente_id',
    '1) Colonna categoria_cliente_id presente su config.parameter_overrides'
);

-- ============================================================
-- 2) Colonna nullable + tipo smallint
-- ============================================================
SELECT ok(
    (SELECT is_nullable = 'YES' AND data_type = 'smallint'
       FROM information_schema.columns
      WHERE table_schema  = 'config'
        AND table_name    = 'parameter_overrides'
        AND column_name   = 'categoria_cliente_id'),
    '2) categoria_cliente_id e'' smallint nullable'
);

-- ============================================================
-- 3) FK presente (per nome constraint)
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t       ON t.oid = c.conrelid
          JOIN pg_namespace ns  ON ns.oid = t.relnamespace
         WHERE ns.nspname  = 'config'
           AND t.relname   = 'parameter_overrides'
           AND c.conname   = 'fk_overrides_categoria_cliente'
           AND c.contype   = 'f'
    ),
    '3) FK fk_overrides_categoria_cliente presente'
);

-- ============================================================
-- 4) FK ON UPDATE CASCADE (confupdtype = 'c')
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
         WHERE ns.nspname  = 'config'
           AND t.relname   = 'parameter_overrides'
           AND c.conname   = 'fk_overrides_categoria_cliente'
           AND c.confupdtype = 'c'   -- CASCADE
    ),
    '4) FK: ON UPDATE CASCADE'
);

-- ============================================================
-- 5) FK ON DELETE RESTRICT (confdeltype = 'r')
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
         WHERE ns.nspname  = 'config'
           AND t.relname   = 'parameter_overrides'
           AND c.conname   = 'fk_overrides_categoria_cliente'
           AND c.confdeltype = 'r'   -- RESTRICT
    ),
    '5) FK: ON DELETE RESTRICT'
);

-- ============================================================
-- 6) Indice per lookup COALESCE presente
-- ============================================================
SELECT has_index(
    'config', 'parameter_overrides',
    'ix_overrides_param_categoria_cliente',
    '6) Indice ix_overrides_param_categoria_cliente presente'
);

-- ============================================================
-- 7) UNIQUE v5 presente, e NULLS NOT DISTINCT
--    Il nome da solo non basta: e' la clausola sui NULL a far valere il
--    vincolo sulle righe reali, che hanno sempre qualche dimensione NULL.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
          JOIN pg_index i      ON i.indexrelid = c.conindid
         WHERE ns.nspname = 'config'
           AND t.relname  = 'parameter_overrides'
           AND c.conname  = 'uq_overrides_full_scope_v5'
           AND c.contype  = 'u'
           AND i.indnullsnotdistinct
    ),
    '7) UNIQUE uq_overrides_full_scope_v5 presente, NULLS NOT DISTINCT'
);

-- ============================================================
-- 8) UNIQUE v3 e v4 rimossi
-- ============================================================
SELECT ok(
    NOT EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
         WHERE ns.nspname = 'config'
           AND t.relname  = 'parameter_overrides'
           AND c.conname  IN ('uq_overrides_full_scope_v3', 'uq_overrides_full_scope_v4')
    ),
    '8) UNIQUE uq_overrides_full_scope_v3 e _v4 rimossi'
);

-- ============================================================
-- 9) Trigger guard presente
--    Il framework genera il nome con suffisso hash (es. ..._require_at_431944):
--    si verifica per funzione + tabella padre, non per nome esatto.
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_trigger t
          JOIN pg_class c      ON c.oid = t.tgrelid
          JOIN pg_namespace ns ON ns.oid = c.relnamespace
          JOIN pg_proc p       ON p.oid = t.tgfoid
         WHERE ns.nspname = 'config'
           AND c.relname  = 'parameter_overrides'
           AND p.proname  = 'trgfn_child_requires_active_parent'
           AND NOT t.tgisinternal
           AND pg_get_triggerdef(t.oid) ILIKE '%categorie_clienti%'
    ),
    '9) Trigger guard categoria attiva presente (nome generato dal framework)'
);

-- ============================================================
-- 10) INSERT override con categoria attiva -> ok
-- ============================================================
SELECT lives_ok(
    format(
        $$INSERT INTO config.parameter_overrides
              (parameter_id, overridden_value, categoria_cliente_id)
          VALUES (%L::bigint, 'TEST_VALUE', 9001)$$,
        (SELECT param_id FROM tmp_cat_ctx)
    ),
    '10) INSERT override con categoria attiva -> ok'
);

-- ============================================================
-- 11) INSERT override senza nessun ambito -> 23514
--     Fino al 2026-10-07 il test se l'aspettava accettata: una riga che nessun
--     livello della cascata legge. Ora la rifiuta chk_parameter_overrides_un_ambito.
-- ============================================================
SELECT throws_ok(
    format(
        $$INSERT INTO config.parameter_overrides
              (parameter_id, overridden_value, categoria_cliente_id)
          VALUES (%L::bigint, 'TEST_VALUE_NULL', NULL)$$,
        (SELECT param_id FROM tmp_cat_ctx)
    ),
    '23514',
    NULL,
    '11) INSERT override senza nessun ambito -> 23514'
);

-- ============================================================
-- 12) INSERT override con categoria disattiva -> raise
--     Il guard e' un CONSTRAINT TRIGGER DEFERRABLE INITIALLY DEFERRED: la
--     violazione emerge al check del vincolo, non all'INSERT. Si forza il check
--     immediato per osservare il raise in modo sincrono nel throws_ok.
-- ============================================================
SET CONSTRAINTS ALL IMMEDIATE;

SELECT throws_ok(
    format(
        $$INSERT INTO config.parameter_overrides
              (parameter_id, overridden_value, categoria_cliente_id)
          VALUES (%L::bigint, 'TEST_VALUE_DIS', 9002)$$,
        (SELECT param_id FROM tmp_cat_ctx)
    ),
    'P0001',
    NULL,
    '12) INSERT override con categoria disattiva -> raise'
);

-- ============================================================
-- 13) Secondo override sullo stesso ambito -> 23505
--     Stesso parametro, stessa categoria (9001), le altre cinque dimensioni
--     NULL come nel test 10: e' lo stesso override, e il vincolo lo rifiuta.
--     Col v4 (NULLS DISTINCT) questa INSERT passava e nascevano due override
--     puri fra cui la cascata sceglieva a caso.
-- ============================================================
SELECT throws_ok(
    format(
        $$INSERT INTO config.parameter_overrides
              (parameter_id, overridden_value, categoria_cliente_id)
          VALUES (%L::bigint, 'TEST_VALUE_BIS', 9001)$$,
        (SELECT param_id FROM tmp_cat_ctx)
    ),
    '23505',
    NULL,
    '13) secondo override sullo stesso ambito (NULL compresi) -> 23505'
);

-- ============================================================
-- 14) INSERT override con due ambiti -> 23514
--     Utente + categoria: la cascata la prenderebbe al livello utente e
--     ignorerebbe la categoria. Un override vale per un ambito solo.
--     L'utente e' fittizio: il CHECK scatta prima delle FK.
-- ============================================================
SELECT throws_ok(
    format(
        $$INSERT INTO config.parameter_overrides
              (parameter_id, overridden_value, django_user_id, categoria_cliente_id)
          VALUES (%L::bigint, 'TEST_VALUE_MISTO', -1, 9001)$$,
        (SELECT param_id FROM tmp_cat_ctx)
    ),
    '23514',
    NULL,
    '14) INSERT override con due ambiti (utente + categoria) -> 23514'
);

-- ============================================================
-- 15) CHECK presente, col nome che il CONSTRAINT dell'errore porta
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_constraint c
          JOIN pg_class t      ON t.oid = c.conrelid
          JOIN pg_namespace ns ON ns.oid = t.relnamespace
         WHERE ns.nspname = 'config'
           AND t.relname  = 'parameter_overrides'
           AND c.conname  = 'chk_parameter_overrides_un_ambito'
           AND c.contype  = 'c'
    ),
    '15) CHECK chk_parameter_overrides_un_ambito presente'
);

SELECT * FROM finish();
ROLLBACK;
