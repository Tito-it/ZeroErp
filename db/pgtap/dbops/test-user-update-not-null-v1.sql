-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — test STRUTTURALE sul catalogo
--   (pg_attribute, pg_trigger): nessuna tabella sotto RLS viene
--   letta, il contesto operatore non cambierebbe nessuna risposta.
-- pgTAP test per Zero ERP
--
-- Chi ha toccato per ultimo una riga si sa sempre: user_update e' NOT NULL
--   su ogni tabella del progetto (linee-guida-sql §7), salvo il debito
--   DICHIARATO qui sotto.
--   Brief: brief-db-righe-e-componenti-debiti-residui (§2, D-2 di Tid,
--   2026-10-08: un giro solo, col presidio).
--   ChangeSet: 20261008-31 (righe e componenti di documento), 20261008-80
--   … -86 (uno per schema: acquisti, anagrafiche, catalogo, config,
--   magazzino, pagamenti, vendite).
--
-- Elenco test (plan 4):
--  1) ⛔ INVARIANTE: nessuna tabella con user_update nullable fuori dal
--        registro del debito
--  2) il registro e' VERO: ogni voce esiste ancora ed e' ancora nullable —
--        una voce chiusa si toglie dal registro, che cosi' puo' solo calare
--  3) il registro e' quello deciso: solo tabelle SENZA il trigger di audit
--        (script.trgfn_audit_data_user_generic). Una tabella che lo prende
--        si chiude, non resta nel debito
--  4) gemello «esiste»: la lente vede le colonne user_update — il test 1
--        non e' muto per un catalogo letto male (ruolo, schema sbagliato)
--
-- ⭐ PERCHE' UN INVARIANTE E NON I NOMI SANATI. Il difetto nasce nel DDL
--   (una tabella nuova con la colonna di audit nullable) e rinasce con la
--   prossima tabella scritta cosi'. Un elenco di nomi chiusi direbbe che
--   quelle sono a posto; il catalogo dice che NESSUNA e' fuori posto,
--   compresa quella nata domani.
--
-- ⚠️ IL REGISTRO DEL DEBITO, e cosa costa. Dichiarare una tabella zittisce
--   il test 1 su di lei: per questo il registro sta QUI, a vista, con il
--   perche' di ciascuna voce, e i test 2 e 3 provano il verso opposto (una
--   voce chiusa, o una voce che ha preso l'audit, rende rosso il test).
--   Le voci al 2026-10-08 sono le tabelle senza trigger di audit, dove la
--   colonna non la scrive nessuno: chiuderle chiede di decidere chi la
--   scrive, non un ALTER.
--     * dbops.fk_index_policy (registro caricato dai seed fk_index_policy_*,
--       senza la colonna) e dbops.transaction_ids (lo scrivono le funzioni
--       del tx_id, dbops.fn_generate_tx_id e vicine): registri tecnici, fuori dal perimetro
--       delle automazioni di audit;
--     * ui.dashboard_definizione, ui.dashboard_preset, ui.lista_colonna,
--       ui.lista_colonna_permesso, ui.lista_definizione, ui.lista_preset,
--       ui.widget: cataloghi della UI, caricati da seed senza la colonna e
--       senza DEFAULT.
--
-- ⚠️ pg_attribute e non information_schema.columns: la vista standard
--   mostra solo le colonne su cui il ruolo connesso ha un privilegio, e i
--   pgTAP girano come zeroerp_app. Una tabella senza grant all'app
--   sparirebbe dalla lente e il test 1 passerebbe per sottrazione.
-- ⚠️ Le partizioni (le note_* sotto le madri *.note) ereditano il NOT NULL
--   dalla madre: la lente le vede comunque, e non sono un caso a parte.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

-- ============================================================
-- Il registro del debito: le sole tabelle ammesse con user_update nullable
-- ============================================================
CREATE TEMP TABLE _debito_user_update (tabella text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO _debito_user_update (tabella) VALUES
    ('dbops.fk_index_policy'),
    ('dbops.transaction_ids'),
    ('ui.dashboard_definizione'),
    ('ui.dashboard_preset'),
    ('ui.lista_colonna'),
    ('ui.lista_colonna_permesso'),
    ('ui.lista_definizione'),
    ('ui.lista_preset'),
    ('ui.widget');

-- ============================================================
-- La lente: le colonne user_update delle tabelle del progetto
-- ============================================================
CREATE TEMP TABLE _user_update ON COMMIT DROP AS
SELECT n.nspname || '.' || c.relname AS tabella,
       NOT a.attnotnull                AS nullable,
       c.oid                           AS relid
  FROM pg_attribute a
  JOIN pg_class c     ON c.oid = a.attrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind IN ('r', 'p')
   AND a.attname = 'user_update'
   AND a.attnum > 0 AND NOT a.attisdropped
   AND n.nspname NOT IN ('pg_catalog', 'information_schema');

-- ============================================================
-- 1. L'invariante, con i NOMI nel messaggio di errore
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(u.tabella, ', ' ORDER BY u.tabella), '')
       FROM _user_update u
      WHERE u.nullable
        AND u.tabella NOT IN (SELECT tabella FROM _debito_user_update)),
    '',
    '1) nessuna tabella con user_update nullable fuori dal registro del debito (linee-guida-sql §7)'
);

-- ============================================================
-- 2. Il registro e' vero: ogni voce esiste ed e' ancora nullable
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(d.tabella, ', ' ORDER BY d.tabella), '')
       FROM _debito_user_update d
      WHERE NOT EXISTS (SELECT 1 FROM _user_update u
                         WHERE u.tabella = d.tabella AND u.nullable)),
    '',
    '2) ogni voce del registro e'' ancora nullable: una voce chiusa si toglie dal registro'
);

-- ============================================================
-- 3. Il registro e' quello deciso: solo tabelle senza audit
-- ============================================================
SELECT is(
    (SELECT coalesce(string_agg(u.tabella, ', ' ORDER BY u.tabella), '')
       FROM _user_update u
       JOIN _debito_user_update d ON d.tabella = u.tabella
      WHERE EXISTS (SELECT 1
                      FROM pg_trigger t
                      JOIN pg_proc p      ON p.oid = t.tgfoid
                      JOIN pg_namespace pn ON pn.oid = p.pronamespace
                     WHERE t.tgrelid = u.relid
                       AND NOT t.tgisinternal
                       AND pn.nspname = 'script'
                       AND p.proname  = 'trgfn_audit_data_user_generic')),
    '',
    '3) nel registro solo tabelle senza il trigger di audit: con l''audit la colonna si chiude'
);

-- ============================================================
-- 4. La lente vede: il test 1 non passa per sottrazione
-- ============================================================
SELECT cmp_ok(
    (SELECT count(*) FROM _user_update WHERE NOT nullable),
    '>', 300::bigint,
    '4) la lente vede le colonne user_update NOT NULL del progetto (erano 354 su dev il 2026-10-08)'
);

SELECT * FROM finish();
ROLLBACK;
