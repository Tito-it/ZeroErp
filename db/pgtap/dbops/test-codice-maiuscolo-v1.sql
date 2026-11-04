-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test fa DDL — crea uno schema di prova con tabelle e un trigger generatore, lancia il runner che monta e toglie trigger, e scrive nel registro dbops.automazione_codice_eccezioni
-- pgTAP test per Zero ERP
--
-- Automazione CODICE_MAIUSCOLO (decisione Tid 2026-11-04): ogni colonna codice
-- dell'ambito si salva in upper(btrim(codice)), tranne le eccezioni di
-- dbops.automazione_codice_eccezioni. Regola per esclusione.
--
-- Elenco test (plan 24):
--  1-4)  gli oggetti: trigger function, perimetro, runner, registro
--  5)    ⭐ PRESIDIO: su tutto il database il perimetro non ha azioni
--  6)    ⭐ PRESIDIO: nessuna riga di una tabella dovuta ha un codice non
--        normalizzato (seed e dati gia' scritti)
--  7)    catalogo.articoli e' dovuta e ha il trigger (il caso da cui nasce)
--  8)    le eccezioni decise da Tid ci sono, e nessuna ha il trigger
--  9)    lo schema di prova: CREA sulle due tabelle stringa e sulla generata,
--        niente sulla colonna intera
--  10)   DRY RUN: nessuna DDL
--  11)   dopo il giro nessuna azione nello schema di prova
--  12)   un trigger solo per tabella, BEFORE INSERT OR UPDATE FOR EACH ROW
--  13)   INSERT: ' vite-m8 ' si salva 'VITE-M8'
--  14)   ⭐ l'unicita' e' senza maiuscole: 'Vite-M8' urta l'indice UNIQUE
--  15)   un UPDATE che riscrive il codice uguale non lo tocca (riga di prima)
--  16)   un UPDATE che cambia il codice lo normalizza
--  17)   NULL resta NULL
--  18)   ⭐ fase a15: un codice scritto da un generatore a10 si salva normalizzato
--  19)   idempotente: un secondo giro non ricrea il trigger (stesso oid)
--  20)   un'eccezione nuova: TOGLIE
--  21)   ...il giro lo toglie, e la tabella in eccezione salva com'e'
--  22)   colonna tolta: TOGLIE, e il giro lo toglie
--  23)   senza regola accesa la tabella non si tocca
--  24)   ...e il perimetro la lascia in CREA (la convergenza del migrate si ferma)
--
-- Scopo:
--  - il criterio sta in dbops.fn_codice_maiuscolo_perimetro, e i presidi lo
--    chiamano per intero invece di ricalcolarlo;
--  - lo schema di prova si COSTRUISCE: riga scritta prima del trigger,
--    generatore a10, colonna non stringa, eccezione, colonna tolta, regola
--    spenta non si cercano nei dati di oggi.
-- ⚠️ I test 5-8 vanno PRIMA che lo schema di prova esista: dopo, lo schema
--   avrebbe azioni volute.
-- ⚠️ Il 6 su dbdev e' rosso finche' non gira la bonifica una tantum delle righe
--   scritte prima del trigger (sql-una-tantum-codice-maiuscolo.sql): e' il suo
--   mestiere, dice quali tabelle.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(24);

-- ============================================================
-- Gli oggetti
-- ============================================================
SELECT has_function('script', 'trgfn_codice_maiuscolo', ARRAY[]::text[],
    '1) script.trgfn_codice_maiuscolo() esiste');
SELECT has_function('dbops', 'fn_codice_maiuscolo_perimetro', ARRAY['text[]'],
    '2) dbops.fn_codice_maiuscolo_perimetro(text[]) esiste');
SELECT has_function('dbops', 'fn_run_automations_codice_maiuscolo', ARRAY['text', 'text[]', 'boolean'],
    '3) dbops.fn_run_automations_codice_maiuscolo(text, text[], boolean) esiste');
SELECT has_table('dbops', 'automazione_codice_eccezioni',
    '4) dbops.automazione_codice_eccezioni esiste');

-- ============================================================
-- ⭐ I presidi, su tutto il database
-- ============================================================
SELECT is(
    (SELECT COALESCE(array_agg(d.schema_name || '.' || d.table_name || ' ' || d.azione
                               ORDER BY d.schema_name, d.table_name), ARRAY[]::text[])
       FROM dbops.fn_codice_maiuscolo_perimetro(NULL) AS d
      WHERE d.azione IS NOT NULL),
    ARRAY[]::text[],
    '5) nessuna tabella dell''ambito ha il trigger del codice da allineare'
);

CREATE TEMP TABLE _codici_non_normalizzati (tabella text, righe bigint) ON COMMIT DROP;
DO $sporchi$
DECLARE
    r      record;
    v_n    bigint;
BEGIN
    FOR r IN
        SELECT d.schema_name, d.table_name
          FROM dbops.fn_codice_maiuscolo_perimetro(NULL) AS d
         WHERE d.nel_perimetro AND NOT d.in_eccezione
    LOOP
        EXECUTE format('SELECT count(*) FROM %I.%I WHERE codice IS DISTINCT FROM upper(btrim(codice))',
                       r.schema_name, r.table_name)
           INTO v_n;
        IF v_n > 0 THEN
            INSERT INTO _codici_non_normalizzati VALUES (r.schema_name || '.' || r.table_name, v_n);
        END IF;
    END LOOP;
END
$sporchi$;

SELECT is(
    (SELECT COALESCE(array_agg(tabella || ' (' || righe || ')' ORDER BY tabella), ARRAY[]::text[])
       FROM _codici_non_normalizzati),
    ARRAY[]::text[],
    '6) nessuna riga di una tabella dovuta ha un codice non in maiuscolo (seed in CSV, dati scritti prima del trigger)'
);

SELECT ok(
    EXISTS (SELECT 1 FROM dbops.fn_codice_maiuscolo_perimetro(ARRAY['catalogo']) AS d
             WHERE d.schema_name = 'catalogo' AND d.table_name = 'articoli'
               AND d.nel_perimetro AND NOT d.in_eccezione
               AND cardinality(d.trigger_vivi) = 1),
    '7) catalogo.articoli e'' dovuta e ha il trigger del codice'
);

SELECT is(
    (SELECT array_agg(e.schema_name || '.' || e.table_name ORDER BY e.schema_name, e.table_name)
       FROM dbops.automazione_codice_eccezioni e
      WHERE e.column_name = 'codice'
        AND (e.schema_name, e.table_name) IN (
              ('ui', 'lista_colonna'), ('ui', 'lista_definizione'), ('ui', 'lista_preset'),
              ('ui', 'widget'), ('ui', 'dashboard_definizione'), ('ui', 'dashboard_preset'),
              ('dbops', 'processi'), ('config', 'aree_funzionali'),
              ('config', 'assets_ownership'), ('config', 'note_stili'))
        AND NOT EXISTS (
              SELECT 1
                FROM pg_catalog.pg_trigger tg
                JOIN pg_catalog.pg_proc p ON p.oid = tg.tgfoid
                JOIN pg_catalog.pg_class c ON c.oid = tg.tgrelid
                JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
               WHERE p.proname = 'trgfn_codice_maiuscolo'
                 AND n.nspname = e.schema_name AND c.relname = e.table_name)),
    ARRAY['config.aree_funzionali', 'config.assets_ownership', 'config.note_stili',
          'dbops.processi',
          'ui.dashboard_definizione', 'ui.dashboard_preset', 'ui.lista_colonna',
          'ui.lista_definizione', 'ui.lista_preset', 'ui.widget'],
    '8) le dieci eccezioni decise da Tid sono a registro e nessuna ha il trigger'
);

-- ============================================================
-- Lo schema di prova
-- ============================================================
CREATE SCHEMA pgtap_codice_maiuscolo;
CREATE TABLE pgtap_codice_maiuscolo.t_a (
    id     integer PRIMARY KEY,
    codice varchar(20) CONSTRAINT uq_pgtap_t_a_codice UNIQUE,
    nota   text
);
CREATE TABLE pgtap_codice_maiuscolo.t_b (id integer PRIMARY KEY, codice text);
CREATE TABLE pgtap_codice_maiuscolo.t_c (id integer PRIMARY KEY, codice integer);
CREATE TABLE pgtap_codice_maiuscolo.t_g (id integer PRIMARY KEY, codice text);

-- Il generatore a10, come i trgfn_*_gen_codice: valorizza il codice vuoto.
CREATE FUNCTION pgtap_codice_maiuscolo.trgfn_t_g_gen_codice()
 RETURNS trigger LANGUAGE plpgsql AS $f$
BEGIN
    IF NEW.codice IS NULL OR btrim(NEW.codice) = '' THEN
        NEW.codice := 'gen-' || NEW.id;
    END IF;
    RETURN NEW;
END $f$;
CREATE TRIGGER trg_t_g_a10_gen_codice_ins_upd
    BEFORE INSERT OR UPDATE ON pgtap_codice_maiuscolo.t_g
    FOR EACH ROW EXECUTE FUNCTION pgtap_codice_maiuscolo.trgfn_t_g_gen_codice();

-- Una riga scritta PRIMA del trigger, come i dati di oggi.
INSERT INTO pgtap_codice_maiuscolo.t_a VALUES (1, 'vecchio', 'x');

SELECT is(
    (SELECT array_agg(d.table_name || ' ' || d.azione ORDER BY d.table_name)
       FROM dbops.fn_codice_maiuscolo_perimetro(ARRAY['pgtap_codice_maiuscolo']) AS d),
    ARRAY['t_a CREA', 't_b CREA', 't_g CREA'],
    '9) CREA sulle colonne codice stringa; la colonna intera (t_c) non e'' nel perimetro'
);

SELECT dbops.fn_run_automations_codice_maiuscolo('SCHEDULED', ARRAY['pgtap_codice_maiuscolo'], true);
SELECT is(
    (SELECT count(*)::int
       FROM pg_catalog.pg_trigger tg
       JOIN pg_catalog.pg_proc p ON p.oid = tg.tgfoid
       JOIN pg_catalog.pg_class c ON c.oid = tg.tgrelid
      WHERE p.proname = 'trgfn_codice_maiuscolo'
        AND c.relnamespace = 'pgtap_codice_maiuscolo'::regnamespace),
    0,
    '10) dry run: nessun trigger montato'
);

SELECT dbops.fn_run_automations_codice_maiuscolo('SCHEDULED', ARRAY['pgtap_codice_maiuscolo'], false);
SELECT is(
    (SELECT count(*)::int
       FROM dbops.fn_codice_maiuscolo_perimetro(ARRAY['pgtap_codice_maiuscolo']) AS d
      WHERE d.azione IS NOT NULL),
    0,
    '11) dopo il giro nessuna azione nello schema di prova'
);

-- tgtype: ROW (1) + BEFORE (2) + INSERT (4) + UPDATE (16) = 23
SELECT is(
    (SELECT array_agg(c.relname::text || ':' || tg.tgtype ORDER BY c.relname)
       FROM pg_catalog.pg_trigger tg
       JOIN pg_catalog.pg_proc p ON p.oid = tg.tgfoid
       JOIN pg_catalog.pg_class c ON c.oid = tg.tgrelid
      WHERE p.proname = 'trgfn_codice_maiuscolo'
        AND c.relnamespace = 'pgtap_codice_maiuscolo'::regnamespace),
    ARRAY['t_a:23', 't_b:23', 't_g:23'],
    '12) un trigger per tabella, BEFORE INSERT OR UPDATE FOR EACH ROW'
);

INSERT INTO pgtap_codice_maiuscolo.t_a VALUES (2, ' vite-m8 ', 'x');
SELECT is((SELECT codice::text FROM pgtap_codice_maiuscolo.t_a WHERE id = 2), 'VITE-M8',
    '13) INSERT: il codice si salva in maiuscolo e senza spazi ai lati');

SELECT throws_ok(
    $$ INSERT INTO pgtap_codice_maiuscolo.t_a VALUES (3, 'Vite-M8', 'x') $$,
    '23505', NULL,
    '14) l''unicita'' e'' senza maiuscole: Vite-M8 urta VITE-M8 sull''indice UNIQUE'
);

UPDATE pgtap_codice_maiuscolo.t_a SET codice = codice, nota = 'y' WHERE id = 1;
SELECT is((SELECT codice::text FROM pgtap_codice_maiuscolo.t_a WHERE id = 1), 'vecchio',
    '15) un UPDATE che riscrive il codice uguale non lo tocca (il lucchetto non scatterebbe a vuoto)');

UPDATE pgtap_codice_maiuscolo.t_a SET codice = 'nuovo' WHERE id = 1;
SELECT is((SELECT codice::text FROM pgtap_codice_maiuscolo.t_a WHERE id = 1), 'NUOVO',
    '16) un UPDATE che cambia il codice lo normalizza');

INSERT INTO pgtap_codice_maiuscolo.t_a VALUES (4, NULL, 'x');
SELECT ok((SELECT codice IS NULL FROM pgtap_codice_maiuscolo.t_a WHERE id = 4),
    '17) NULL resta NULL');

INSERT INTO pgtap_codice_maiuscolo.t_g VALUES (1, NULL);
SELECT is((SELECT codice FROM pgtap_codice_maiuscolo.t_g WHERE id = 1), 'GEN-1',
    '18) fase a15: il codice scritto dal generatore a10 si salva normalizzato');

CREATE TEMP TABLE _oid_prima ON COMMIT DROP AS
SELECT tg.oid
  FROM pg_catalog.pg_trigger tg
  JOIN pg_catalog.pg_proc p ON p.oid = tg.tgfoid
 WHERE p.proname = 'trgfn_codice_maiuscolo'
   AND tg.tgrelid = 'pgtap_codice_maiuscolo.t_a'::regclass;
SELECT dbops.fn_run_automations_codice_maiuscolo('SCHEDULED', ARRAY['pgtap_codice_maiuscolo'], false);
SELECT is(
    (SELECT tg.oid
       FROM pg_catalog.pg_trigger tg
       JOIN pg_catalog.pg_proc p ON p.oid = tg.tgfoid
      WHERE p.proname = 'trgfn_codice_maiuscolo'
        AND tg.tgrelid = 'pgtap_codice_maiuscolo.t_a'::regclass),
    (SELECT oid FROM _oid_prima),
    '19) idempotente: il secondo giro non ricrea il trigger'
);

-- ============================================================
-- Il ritiro: eccezione nuova, colonna tolta
-- ============================================================
INSERT INTO dbops.automazione_codice_eccezioni (schema_name, table_name, column_name, motivo)
VALUES ('pgtap_codice_maiuscolo', 't_b', 'codice', 'pgTAP: tabella di prova in eccezione');
SELECT is(
    (SELECT d.azione
       FROM dbops.fn_codice_maiuscolo_perimetro(ARRAY['pgtap_codice_maiuscolo']) AS d
      WHERE d.table_name = 't_b'),
    'TOGLIE',
    '20) un''eccezione nuova su una tabella col trigger: TOGLIE'
);

SELECT dbops.fn_run_automations_codice_maiuscolo('SCHEDULED', ARRAY['pgtap_codice_maiuscolo'], false);
INSERT INTO pgtap_codice_maiuscolo.t_b VALUES (1, 'owned');
SELECT is((SELECT codice FROM pgtap_codice_maiuscolo.t_b WHERE id = 1), 'owned',
    '21) il giro toglie il trigger, e la tabella in eccezione salva il codice com''e''');

ALTER TABLE pgtap_codice_maiuscolo.t_g DROP COLUMN codice;
SELECT dbops.fn_run_automations_codice_maiuscolo('SCHEDULED', ARRAY['pgtap_codice_maiuscolo'], false);
SELECT is(
    (SELECT count(*)::int
       FROM pg_catalog.pg_trigger tg
       JOIN pg_catalog.pg_proc p ON p.oid = tg.tgfoid
      WHERE p.proname = 'trgfn_codice_maiuscolo'
        AND tg.tgrelid = 'pgtap_codice_maiuscolo.t_g'::regclass),
    0,
    '22) colonna codice tolta: il giro toglie il trigger (lasciarlo farebbe fallire ogni scrittura)'
);

-- ============================================================
-- La regola e' l'interruttore
-- ============================================================
UPDATE dbops.automation_rules_tbl SET enabled = false
 WHERE upper(btrim(rule_type)) = 'CODICE_MAIUSCOLO';
CREATE TABLE pgtap_codice_maiuscolo.t_e (id integer PRIMARY KEY, codice text);
SELECT dbops.fn_run_automations_codice_maiuscolo('SCHEDULED', ARRAY['pgtap_codice_maiuscolo'], false);
SELECT is(
    (SELECT count(*)::int
       FROM pg_catalog.pg_trigger tg
       JOIN pg_catalog.pg_proc p ON p.oid = tg.tgfoid
      WHERE p.proname = 'trgfn_codice_maiuscolo'
        AND tg.tgrelid = 'pgtap_codice_maiuscolo.t_e'::regclass),
    0,
    '23) senza regola CODICE_MAIUSCOLO accesa la tabella nuova non si tocca'
);
SELECT is(
    (SELECT d.azione
       FROM dbops.fn_codice_maiuscolo_perimetro(ARRAY['pgtap_codice_maiuscolo']) AS d
      WHERE d.table_name = 't_e'),
    'CREA',
    '24) ...e resta CREA nel perimetro: la convergenza del migrate la nomina e si ferma'
);

SELECT * FROM finish();
ROLLBACK;
