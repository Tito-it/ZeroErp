-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il seed di primo impianto visto dall'INSTALLAZIONE (l'applicazione).
--   Brief: brief-db-seed-primo-impianto-non-si-riscrive (§15.7, §16.3).
--   ChangeSet: 20261117-01 … -21 (registro, porta, trigger, runner, rete, postura);
--   20261117-28 (solo disattivazione: la DELETE di account e template e' bloccata, §16.14).
--
-- Gira come l'applicazione (runner di default): chi scrive si riconosce da
--   session_user, che non si simula. Il lato del SOFTWARE (il blocco DO del
--   mirror, la porta aperta dal migratore, l'iscrizione) sta in
--   db/pgtap/dbops/test-seed-primo-impianto-software-v1.sql, col runner owner.
--
-- I soggetti sono le righe vere del seed: le nove di config.email_template
--   (forma per colonna) e la riga SISTEMA di config.email_account (solo
--   inserimento). In CI esistono perche' le carica il CSV e la rete di 90_end
--   le iscrive in dbops.seed_righe; se mancano, i test che le usano si saltano.
--
-- Elenco test (plan 24):
--    1) le due tabelle hanno un trigger solo sulla funzione, BEFORE INSERT OR
--       UPDATE OR DELETE FOR EACH ROW
--    2) e' il primo dei BEFORE UPDATE di riga, in ordine di nome
--    3) le divergenze della regola sono a zero
--    4) le nove righe di email_template e SISTEMA sono nate dal seed
--    5) l'app che tocca solo meta: passa
--    6) … e la riga NON diventa personalizzata (Q10)
--    7) l'app che cambia il corpo del template: passa
--    8) … e la riga diventa personalizzata, con chi
--    9) l'app che cambia il codice di un template di seed: E_SEED_COLONNA_DEL_SOFTWARE
--   10) … la lingua
--   11) … il reparto
--   12) … le variabili disponibili
--   13) l'app che cancella un template di seed: E_SEED_RIGA_NON_CANCELLABILE
--   14) l'app che accende la porta del seed e cancella: rifiutato lo stesso
--   15) per l'app la porta e' chiusa, e il diario non cambia
--   16) il template creato dall'app non e' nato dal seed
--   17) … l'app gli cambia il codice
--   18) … ma non lo cancella: E_DELETE_NOT_ALLOWED (solo disattivazione, §16.14)
--   19) SISTEMA: l'app cambia l'host SMTP
--   20) SISTEMA: l'app non la cancella
--   21) l'app che accende la porta del lucchetto non cambia codice_interno
--   22) fn_ruolo_del_migratore su un nome che non e' un ruolo: false, senza errore
--   23) fn_ruolo_del_migratore su zeroerp_app e su NULL: false
--   24) fn_sessione_del_migratore come app: false
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(24);

-- ============================================================
-- 1-3 La forma: il trigger c'e', e' il primo, la regola converge
-- ============================================================
SELECT is(
    -- Il nome dal catalogo, non da regclass::text: il testo di regclass omette
    -- lo schema quando e' nel search_path, e quello dell'app lo contiene.
    (SELECT string_agg(format('%s.%s=%s', n.nspname, c.relname, tg.tgtype), ','
                       ORDER BY n.nspname COLLATE "C", c.relname COLLATE "C")
       FROM pg_trigger tg
       JOIN pg_class c ON c.oid = tg.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT tg.tgisinternal
        AND tg.tgfoid = 'script.trgfn_seed_primo_impianto()'::regprocedure
        AND tg.tgrelid IN ('config.email_account'::regclass, 'config.email_template'::regclass)),
    'config.email_account=31,config.email_template=31',
    '1) un trigger solo per tabella, BEFORE INSERT OR UPDATE OR DELETE FOR EACH ROW');

SELECT is(
    (SELECT string_agg(prima, ',' ORDER BY rel)
       FROM (SELECT tg.tgrelid::regclass::text AS rel,
                    (array_agg(tg.tgfoid = 'script.trgfn_seed_primo_impianto()'::regprocedure
                               ORDER BY tg.tgname COLLATE "C"))[1]::text AS prima
               FROM pg_trigger tg
              WHERE NOT tg.tgisinternal
                AND tg.tgrelid IN ('config.email_account'::regclass, 'config.email_template'::regclass)
                AND (tg.tgtype & 2) = 2     -- BEFORE
                AND (tg.tgtype & 1) = 1     -- ROW
                AND (tg.tgtype & 16) = 16   -- UPDATE
              GROUP BY tg.tgrelid) x),
    'true,true',
    '2) e'' il primo BEFORE UPDATE di riga: i guard vedono i valori rimessi');

SELECT is(
    (SELECT count(*)::int FROM dbops.fn_seed_primo_impianto_divergenze(NULL)),
    0,
    '3) le divergenze della regola sono a zero');

-- ============================================================
-- 4 Le righe del seed sono segnate
-- ============================================================
SELECT is(
    (SELECT string_agg(s.table_name || ':' || s.riga_id, ',' ORDER BY s.table_name, s.riga_id::int)
       FROM dbops.seed_righe s
      WHERE s.schema_name = 'config'
        AND ((s.table_name = 'email_template' AND s.riga_id IN ('1','2','3','4','5','6','7','8','9'))
          OR (s.table_name = 'email_account'
              AND s.riga_id = (SELECT a.id::text FROM config.email_account a WHERE a.codice_interno = 'SISTEMA')))),
    'email_account:' || (SELECT a.id::text FROM config.email_account a WHERE a.codice_interno = 'SISTEMA')
      || ',email_template:1,email_template:2,email_template:3,email_template:4,email_template:5,'
      || 'email_template:6,email_template:7,email_template:8,email_template:9',
    '4) le nove righe di email_template e SISTEMA sono nate dal seed');

-- ============================================================
-- 5-8 La personalizzazione: solo le colonne dell'installazione contano
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE config.email_template SET meta = meta || '{"prova_seed": 1}'::jsonb WHERE id = 2$$),
    NULL,
    '5) l''app che tocca solo meta: passa');

SELECT is(
    (SELECT s.personalizzata_il IS NULL FROM dbops.seed_righe s
      WHERE s.schema_name = 'config' AND s.table_name = 'email_template' AND s.riga_id = '2'),
    true,
    '6) … e la riga NON diventa personalizzata: meta non conta');

SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE config.email_template SET corpo_testo = 'Testo della mia azienda' WHERE id = 2$$),
    NULL,
    '7) l''app che cambia il corpo del template: passa');

SELECT is(
    (SELECT s.personalizzata_il IS NOT NULL AND s.personalizzata_da IS NOT NULL FROM dbops.seed_righe s
      WHERE s.schema_name = 'config' AND s.table_name = 'email_template' AND s.riga_id = '2'),
    true,
    '8) … e la riga diventa personalizzata, con chi');

-- ============================================================
-- 9-12 Le colonne del software sulla riga di seed
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE config.email_template SET codice = 'RINOMINATO_DA_ME' WHERE id = 3$$),
    'E_SEED_COLONNA_DEL_SOFTWARE',
    '9) l''app che cambia il codice di un template di seed: rifiutato');

SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE config.email_template SET lingua = 'en' WHERE id = 3$$),
    'E_SEED_COLONNA_DEL_SOFTWARE',
    '10) … la lingua: il ripiego di sistema sparirebbe');

SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE config.email_template
                                     SET unita_organizzativa_id = (SELECT min(u.id) FROM config.unita_organizzative u)
                                   WHERE id = 3$$),
    'E_SEED_COLONNA_DEL_SOFTWARE',
    '11) … il reparto');

SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE config.email_template SET variabili_disponibili = '["mia"]'::jsonb WHERE id = 3$$),
    'E_SEED_COLONNA_DEL_SOFTWARE',
    '12) … le variabili disponibili');

-- ============================================================
-- 13-15 Il DELETE di una riga di seed, e la porta per l'app
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$DELETE FROM config.email_template WHERE id = 4$$),
    'E_SEED_RIGA_NON_CANCELLABILE',
    '13) l''app che cancella un template di seed: rifiutato (si spegne)');

CREATE TEMP TABLE _diario AS
SELECT count(*)::int AS n FROM dbops.porte_manutenzione_passaggi;

SET LOCAL zeroerp.allow_seed_primo_impianto_override = 'on';

SELECT is(
    dbops.fn_pgtap_codice_errore($$DELETE FROM config.email_template WHERE id = 4$$),
    'E_SEED_RIGA_NON_CANCELLABILE',
    '14) l''app che accende la porta del seed e cancella: rifiutato lo stesso');

SELECT is(
    format('%s|%s',
           script.fn_porta_manutenzione_aperta('zeroerp.allow_seed_primo_impianto_override',
                                               'config.email_template'::regclass, 'DELETE', '4')::text,
           ((SELECT count(*)::int FROM dbops.porte_manutenzione_passaggi) = (SELECT n FROM _diario))::text),
    'false|true',
    '15) per l''app la porta e'' chiusa anche a GUC accesa, e il diario non cambia');

RESET zeroerp.allow_seed_primo_impianto_override;

-- ============================================================
-- 16-18 La riga creata dall'installazione e' sua
-- ============================================================
CREATE TEMP TABLE _mio AS
WITH ins AS (
    INSERT INTO config.email_template (codice, lingua, oggetto, corpo_html)
    VALUES ('PGTAP_SEED_MIO', 'it', 'Oggetto mio', '<p>mio</p>')
    RETURNING id)
SELECT id FROM ins;

SELECT is(
    (SELECT count(*)::int FROM dbops.seed_righe s
      WHERE s.schema_name = 'config' AND s.table_name = 'email_template'
        AND s.riga_id = (SELECT id::text FROM _mio)),
    0,
    '16) il template creato dall''app non e'' nato dal seed');

SELECT is(
    dbops.fn_pgtap_codice_errore(format($$UPDATE config.email_template SET codice = 'PGTAP_SEED_MIO_2' WHERE id = %s$$,
                                        (SELECT id FROM _mio))),
    NULL,
    '17) … l''app gli cambia il codice');

SELECT is(
    dbops.fn_pgtap_codice_errore(format($$DELETE FROM config.email_template WHERE id = %s$$, (SELECT id FROM _mio))),
    -- Dal 2026-11-19 (§16.14) un template non si cancella, nemmeno quello
    -- dell'installazione: si spegne. Sulla riga di seed parla prima il guard del
    -- seed (13), qui il blocco della DELETE (dbops.automation_delete_block).
    'E_DELETE_NOT_ALLOWED',
    '18) … ma non lo cancella: si spegne (solo disattivazione)');

-- ============================================================
-- 19-21 SISTEMA, in solo inserimento
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE config.email_account SET smtp_host = 'smtp.mia-azienda.it' WHERE codice_interno = 'SISTEMA'$$),
    NULL,
    '19) SISTEMA: l''app cambia l''host SMTP');

SELECT is(
    dbops.fn_pgtap_codice_errore($$DELETE FROM config.email_account WHERE codice_interno = 'SISTEMA'$$),
    'E_SEED_RIGA_NON_CANCELLABILE',
    '20) SISTEMA: l''app non la cancella');

SET LOCAL zeroerp.allow_lock_columns_override = 'on';

SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE config.email_account SET codice_interno = 'SISTEMA_2' WHERE codice_interno = 'SISTEMA'$$),
    'E_CODICE_NON_MODIFICABILE',
    '21) l''app che accende la porta del lucchetto non cambia codice_interno');

RESET zeroerp.allow_lock_columns_override;

-- ============================================================
-- 22-24 Chi e' il migratore
-- ============================================================
SELECT is(
    dbops.fn_ruolo_del_migratore('pgtap_nessun_ruolo_si_chiama_cosi'),
    false,
    '22) fn_ruolo_del_migratore su un nome che non e'' un ruolo: false, senza errore');

SELECT is(
    format('%s|%s', dbops.fn_ruolo_del_migratore('zeroerp_app')::text, dbops.fn_ruolo_del_migratore(NULL)::text),
    'false|false',
    '23) fn_ruolo_del_migratore su zeroerp_app e su NULL: false');

SELECT is(
    dbops.fn_sessione_del_migratore(),
    false,
    '24) fn_sessione_del_migratore come app: false');

SELECT * FROM finish();
ROLLBACK;
