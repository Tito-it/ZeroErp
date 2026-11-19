-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: account e template di posta si spengono e non si cancellano, e il
--   segno del seed di primo impianto che leggono le loro superfici.
--   Brief: brief-db-seed-primo-impianto-non-si-riscrive (§16.14; decisione di
--   Tid del 2026-11-19, Q24: solo disattivazione).
--   ChangeSet: 20261117-23 … -28, e le righe dei registri
--   dbops.automation_delete_block (9, 10) e dbops.automazione_attivo_eccezioni.
--
-- Gira come l'applicazione (runner di default): chi scrive si riconosce da
--   session_user, e una riga creata dal proprietario nascerebbe dal seed. Il
--   lato del migratore (le due porte per ritirare una riga di seed) sta in
--   db/pgtap/dbops/test-seed-primo-impianto-software-v1.sql.
--
-- I soggetti di seed sono le righe vere: il primo template iscritto in
--   dbops.seed_righe e la riga SISTEMA di config.email_account. In CI esistono
--   perche' le carica il CSV e la rete di 90_end le iscrive.
--
-- Elenco test (plan 14):
--    1) le due tabelle hanno il blocco della DELETE, BEFORE DELETE per riga,
--       con la porta zeroerp.maintenance_email_delete
--    2) nessun trigger ATTIVO fra account/template e lo storico delle mail
--       (block_deact sui padri, require su email_log ed email_outbox)
--    3) il template creato dall'app non si cancella: E_DELETE_NOT_ALLOWED
--    4) … si spegne
--    5) l'app che accende la porta della cancellazione: rifiutata lo stesso
--    6) il template di seed non si cancella: parla prima il guard del seed
--       (E_SEED_RIGA_NON_CANCELLABILE)
--    7) SISTEMA si spegne
--    8) vista dei template, riga di seed: nata dal seed, coi campi del software
--       del registro della regola
--    9) … e sono colonne vere della tabella
--   10) vista dei template, riga dell'app: non nata dal seed, nessun campo
--   11) vista degli account, SISTEMA: nata dal seed, nessun campo (solo
--       inserimento)
--   12) le viste hanno una riga per riga della tabella
--   13) fn_seed_colonne_del_software su una tabella fuori dal seed: vuoto
--   14) fn_seed_riga con id NULL: nessuna riga
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(14);

-- ============================================================
-- 1-2 La forma: il blocco c'e', il legame con lo storico no
-- ============================================================
SELECT is(
    -- Il nome dal catalogo, non da regclass::text (dipende dal search_path).
    (SELECT string_agg(format('%s.%s=%s:%s', n.nspname, c.relname, tg.tgtype,
                              (dbops.fn_trigger_argomenti(tg.tgargs))[1]), ','
                       ORDER BY n.nspname COLLATE "C", c.relname COLLATE "C")
       FROM pg_trigger tg
       JOIN pg_class c ON c.oid = tg.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT tg.tgisinternal
        AND tg.tgenabled <> 'D'
        AND tg.tgfoid = 'script.trgfn_delete_block_by_guc()'::regprocedure
        AND tg.tgrelid IN ('config.email_account'::regclass, 'config.email_template'::regclass)),
    'config.email_account=11:zeroerp.maintenance_email_delete,'
    'config.email_template=11:zeroerp.maintenance_email_delete',
    '1) il blocco della DELETE su account e template, BEFORE DELETE FOR EACH ROW');

SELECT is(
    (SELECT count(*)::int
       FROM pg_trigger tg
      WHERE NOT tg.tgisinternal
        AND (   (    tg.tgfoid = 'dbops.trgfn_prevent_deactivate_if_children()'::regprocedure
                 AND tg.tgrelid IN ('config.email_account'::regclass, 'config.email_template'::regclass)
                 AND (dbops.fn_trigger_argomenti(tg.tgargs))[2] IN ('email_log', 'email_outbox'))
             OR (    tg.tgfoid = 'dbops.trgfn_child_requires_active_parent()'::regprocedure
                 AND tg.tgrelid IN ('config.email_log'::regclass, 'config.email_outbox'::regclass)
                 AND (dbops.fn_trigger_argomenti(tg.tgargs))[2] IN ('email_account', 'email_template')))),
    0,
    '2) nessun trigger ATTIVO fra account/template e lo storico delle mail');

-- ============================================================
-- 3-7 Si spegne, non si cancella
-- ============================================================
CREATE TEMP TABLE _mio AS
WITH ins AS (
    INSERT INTO config.email_template (codice, lingua, oggetto, corpo_html)
    VALUES ('PGTAP_POSTA_MIO', 'it', 'Oggetto mio', '<p>mio</p>')
    RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE _seed AS
SELECT min(s.riga_id::int) AS id
  FROM dbops.seed_righe s
 WHERE s.schema_name = 'config' AND s.table_name = 'email_template';

SELECT is(
    dbops.fn_pgtap_codice_errore(format($$DELETE FROM config.email_template WHERE id = %s$$,
                                        (SELECT id FROM _mio))),
    'E_DELETE_NOT_ALLOWED',
    '3) il template creato dall''app non si cancella');

SELECT is(
    dbops.fn_pgtap_codice_errore(format($$UPDATE config.email_template SET attivo = false WHERE id = %s$$,
                                        (SELECT id FROM _mio))),
    NULL,
    '4) … si spegne');

SET LOCAL zeroerp.maintenance_email_delete = 'on';

SELECT is(
    dbops.fn_pgtap_codice_errore(format($$DELETE FROM config.email_template WHERE id = %s$$,
                                        (SELECT id FROM _mio))),
    'E_DELETE_NOT_ALLOWED',
    '5) l''app che accende la porta della cancellazione: rifiutata lo stesso');

RESET zeroerp.maintenance_email_delete;

SELECT is(
    dbops.fn_pgtap_codice_errore(format($$DELETE FROM config.email_template WHERE id = %s$$,
                                        (SELECT id FROM _seed))),
    'E_SEED_RIGA_NON_CANCELLABILE',
    '6) il template di seed non si cancella: parla prima il guard del seed');

-- SISTEMA puo' avere spedito: dal -28 lo storico non lo tiene acceso (test 2).
SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE config.email_account SET attivo = false WHERE codice_interno = 'SISTEMA'$$),
    NULL,
    '7) SISTEMA si spegne');

-- ============================================================
-- 8-12 Le superfici
-- ============================================================
SELECT is(
    (SELECT format('%s|%s', v.nata_dal_seed::text,
                   ((SELECT array_agg(c ORDER BY c COLLATE "C") FROM unnest(v.campi_del_software) c)
                  = (SELECT array_agg(c ORDER BY c COLLATE "C")
                       FROM dbops.automazione_seed_primo_impianto r, unnest(r.colonne_software) c
                      WHERE r.schema_name = 'config' AND r.table_name = 'email_template'))::text)
       FROM config.vw_email_template_seed v
      WHERE v.email_template_id = (SELECT id FROM _seed)),
    'true|true',
    '8) template di seed: nato dal seed, coi campi del software del registro della regola');

SELECT is(
    (SELECT count(*)::int
       FROM config.vw_email_template_seed v, unnest(v.campi_del_software) c
      WHERE v.email_template_id = (SELECT id FROM _seed)
        AND NOT EXISTS (SELECT 1 FROM pg_attribute a
                         WHERE a.attrelid = 'config.email_template'::regclass
                           AND a.attname = c AND a.attnum > 0 AND NOT a.attisdropped)),
    0,
    '9) … e sono colonne vere della tabella');

SELECT is(
    (SELECT format('%s|%s', v.nata_dal_seed::text, v.campi_del_software)
       FROM config.vw_email_template_seed v
      WHERE v.email_template_id = (SELECT id FROM _mio)),
    'false|{}',
    '10) template dell''app: non nato dal seed, nessun campo del software');

SELECT is(
    (SELECT format('%s|%s', v.nata_dal_seed::text, v.campi_del_software)
       FROM config.vw_email_account_seed v
       JOIN config.email_account ea ON ea.id = v.email_account_id
      WHERE ea.codice_interno = 'SISTEMA'),
    'true|{}',
    '11) SISTEMA: nato dal seed, nessun campo (solo inserimento)');

SELECT is(
    format('%s|%s',
           ((SELECT count(*) FROM config.vw_email_template_seed) = (SELECT count(*) FROM config.email_template))::text,
           ((SELECT count(*) FROM config.vw_email_account_seed) = (SELECT count(*) FROM config.email_account))::text),
    'true|true',
    '12) le viste hanno una riga per riga della tabella');

-- ============================================================
-- 13-14 I due building block ai bordi
-- ============================================================
SELECT is(
    dbops.fn_seed_colonne_del_software('config.email_log'::regclass),
    ARRAY[]::text[],
    '13) fn_seed_colonne_del_software su una tabella fuori dal seed: vuoto, non NULL');

SELECT is(
    (SELECT count(*)::int FROM dbops.fn_seed_riga('config.email_template'::regclass, NULL)),
    0,
    '14) fn_seed_riga con id NULL: nessuna riga');

SELECT * FROM finish();
ROLLBACK;
