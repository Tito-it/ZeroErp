-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto e' la scrittura del SOFTWARE (la sessione del migratore: il blocco DO del mirror, la porta di manutenzione, l'iscrizione del runner), che l'applicazione non raggiunge; il test fa anche DDL su tabelle del modello
--
-- Test: il seed di primo impianto visto dal SOFTWARE.
--   Brief: brief-db-seed-primo-impianto-non-si-riscrive (§15.7, §16.3, §16.9).
--   ChangeSet: 20261117-01 … -21.
--   Il lato dell'installazione: db/pgtap/config/test-seed-primo-impianto-installazione-v1.sql.
--
-- Il blocco DO del mirror si scrive qui com'e' il SQL di loadUpdateData su
--   PostgreSQL: `UPDATE …; IF not found THEN INSERT …; END IF`. La
--   personalizzazione dell'installazione si simula scrivendo il registro da
--   proprietario: l'app non la puo' fare in una sessione del migratore.
--
-- Elenco test (plan 26):
--    1) mirror su una riga di seed intatta: nessun errore
--    2) … la riga segue il CSV
--    3) mirror su una riga personalizzata: nessuna chiave duplicata
--    4) … le colonne dell'installazione restano
--    5) … quelle del software si aggiornano
--    6) … i valori scartati sono nel registro
--    7) SOLO_INSERIMENTO: il mirror su SISTEMA che cambia codice_interno e host
--       non va in errore (il lucchetto a10 vede il valore rimesso: l'ordine)
--    8) … SISTEMA non cambia
--    9) … e il registro resta pulito: nessun valore scartato (il WARNING
--       della Q22 va nell'output, il pgTAP non lo legge)
--   10) SOLO_INSERIMENTO: la riga che manca si inserisce
--   11) … e nasce nel registro, segnata dall'INSERT
--   12) il migratore senza porta non cancella una riga di seed
--   13) con la porta la cancella
--   14) … e la riga esce dal registro
--   15) … e il diario la registra
--   16) con la porta il migratore riscrive la riga personalizzata
--   17) … che resta personalizzata (D6)
--   18) porta del lucchetto aperta dal migratore: il codice bloccato cambia
--   19) … e il diario la registra
--   20) senza porta il lucchetto rifiuta
--   21) una colonna aggiunta e non classificata: NON_CLASSIFICATA
--   22) … il runner lascia il trigger di prima
--   23) l'iscrizione segna le righe con user_insert SEED o di un ruolo del migratore
--   24) … non quelle di uno username
--   25) la rigenerazione non ripassa dall'iscrizione
--   26) fn_sessione_del_migratore da proprietario: true
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(26);

-- ============================================================
-- 1-2 Riga di seed intatta: segue il CSV
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($mirror$
        DO $$ BEGIN
            UPDATE config.email_template
               SET corpo_testo = 'Testo nuovo dal CSV', variabili_disponibili = '["nome","link"]'::jsonb
             WHERE id = 5;
            IF not found THEN
                INSERT INTO config.email_template (id, codice, lingua, oggetto, corpo_html, corpo_testo)
                VALUES (5, 'INVITO_PORTALE', 'it', 'x', 'x', 'Testo nuovo dal CSV');
            END IF;
        END $$ $mirror$),
    NULL,
    '1) mirror su una riga di seed intatta: nessun errore');

SELECT is(
    (SELECT corpo_testo FROM config.email_template WHERE id = 5),
    'Testo nuovo dal CSV',
    '2) … la riga segue il CSV');

-- ============================================================
-- 3-6 Riga personalizzata: il CSV non la riscrive
-- ============================================================
UPDATE dbops.seed_righe
   SET personalizzata_il = now(), personalizzata_da = 'pgtap_installazione'
 WHERE schema_name = 'config' AND table_name = 'email_template' AND riga_id = '6';

CREATE TEMP TABLE _prima AS
SELECT corpo_testo FROM config.email_template WHERE id = 6;

SELECT is(
    dbops.fn_pgtap_codice_errore($mirror$
        DO $$ BEGIN
            UPDATE config.email_template
               SET corpo_testo = 'Testo del CSV da scartare', variabili_disponibili = '["nuova"]'::jsonb
             WHERE id = 6;
            IF not found THEN
                INSERT INTO config.email_template (id, codice, lingua, oggetto, corpo_html)
                VALUES (6, 'INVITO_SHOP', 'it', 'x', 'x');
            END IF;
        END $$ $mirror$),
    NULL,
    '3) mirror su una riga personalizzata: l''UPDATE trova la riga, nessuna chiave duplicata');

SELECT is(
    (SELECT corpo_testo IS NOT DISTINCT FROM (SELECT corpo_testo FROM _prima) FROM config.email_template WHERE id = 6),
    true,
    '4) … la colonna dell''installazione resta');

SELECT is(
    (SELECT variabili_disponibili FROM config.email_template WHERE id = 6),
    '["nuova"]'::jsonb,
    '5) … la colonna del software si aggiorna');

SELECT is(
    (SELECT s.scartati ->> 'corpo_testo' FROM dbops.seed_righe s
      WHERE s.schema_name = 'config' AND s.table_name = 'email_template' AND s.riga_id = '6'),
    'Testo del CSV da scartare',
    '6) … il valore scartato e'' nel registro');

-- ============================================================
-- 7-11 SOLO_INSERIMENTO su config.email_account
-- ============================================================
CREATE TEMP TABLE _sistema AS
SELECT id, smtp_host, codice_interno FROM config.email_account WHERE codice_interno = 'SISTEMA';

SELECT is(
    dbops.fn_pgtap_codice_errore(format($mirror$
        DO $$ BEGIN
            UPDATE config.email_account
               SET codice_interno = 'SISTEMA_DAL_CSV', smtp_host = 'smtp.example.com'
             WHERE id = %s;
            IF not found THEN
                INSERT INTO config.email_account (id, codice, codice_interno, descrizione, smtp_host,
                                                  smtp_username, smtp_password_encrypted, email_from)
                VALUES (%s, 'SISTEMA', 'SISTEMA', 'x', 'x', 'x', 'x', 'x');
            END IF;
        END $$ $mirror$, (SELECT id FROM _sistema), (SELECT id FROM _sistema))),
    NULL,
    '7) mirror su SISTEMA che cambia codice_interno e host: nessun errore, il lucchetto vede il valore rimesso');

SELECT is(
    (SELECT format('%s|%s', a.codice_interno, (a.smtp_host IS NOT DISTINCT FROM s.smtp_host)::text)
       FROM config.email_account a JOIN _sistema s ON s.id = a.id),
    'SISTEMA|true',
    '8) … SISTEMA non cambia');

SELECT is(
    (SELECT s.scartati IS NULL FROM dbops.seed_righe s
      WHERE s.schema_name = 'config' AND s.table_name = 'email_account'
        AND s.riga_id = (SELECT id::text FROM _sistema)),
    true,
    '9) … e il registro resta pulito: nessun valore scartato');

SELECT is(
    dbops.fn_pgtap_codice_errore($mirror$
        DO $$ BEGIN
            UPDATE config.email_account SET descrizione = 'Account di seed nuovo' WHERE id = 990001;
            IF not found THEN
                INSERT INTO config.email_account (id, codice, codice_interno, descrizione, smtp_host,
                                                  smtp_username, smtp_password_encrypted, email_from)
                VALUES (990001, 'PGTAP_SEED_NUOVO', 'PGTAP_SEED_NUOVO', 'Account di seed nuovo',
                        'smtp.example.com', 'x', 'x', 'noreply@example.com');
            END IF;
        END $$ $mirror$),
    NULL,
    '10) SOLO_INSERIMENTO: la riga che manca si inserisce');

SELECT is(
    (SELECT s.segnata_da FROM dbops.seed_righe s
      WHERE s.schema_name = 'config' AND s.table_name = 'email_account' AND s.riga_id = '990001'),
    'INSERT',
    '11) … e nasce nel registro, segnata dall''INSERT del migratore');

-- ============================================================
-- 12-17 La porta del seed, aperta dal migratore
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$DELETE FROM config.email_template WHERE id = 7$$),
    'E_SEED_RIGA_NON_CANCELLABILE',
    '12) il migratore senza porta non cancella una riga di seed');

SET LOCAL zeroerp.allow_seed_primo_impianto_override = 'on';

SELECT is(
    dbops.fn_pgtap_codice_errore($$DELETE FROM config.email_template WHERE id = 7$$),
    NULL,
    '13) con la porta la cancella: il DELETE forward-only');

SELECT is(
    (SELECT count(*)::int FROM dbops.seed_righe s
      WHERE s.schema_name = 'config' AND s.table_name = 'email_template' AND s.riga_id = '7'),
    0,
    '14) … e la riga esce dal registro');

SELECT is(
    (SELECT count(*)::int FROM dbops.porte_manutenzione_passaggi p
      WHERE p.chiave = 'zeroerp.allow_seed_primo_impianto_override'
        AND p.schema_name = 'config' AND p.table_name = 'email_template'
        AND p.riga_id = '7' AND p.operazione = 'DELETE' AND p.utente_sessione = session_user::text),
    1,
    '15) … e il diario la registra, col ruolo di login');

SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE config.email_template SET corpo_testo = 'Bonifica voluta' WHERE id = 6$$),
    NULL,
    '16) con la porta il migratore riscrive la riga personalizzata');

SELECT is(
    (SELECT format('%s|%s', t.corpo_testo, (s.personalizzata_il IS NOT NULL)::text)
       FROM config.email_template t
       JOIN dbops.seed_righe s ON s.schema_name = 'config' AND s.table_name = 'email_template' AND s.riga_id = t.id::text
      WHERE t.id = 6),
    'Bonifica voluta|true',
    '17) … che resta personalizzata');

RESET zeroerp.allow_seed_primo_impianto_override;

-- ============================================================
-- 18-20 La porta del lucchetto, su una tabella fuori dal seed
-- ============================================================
SET LOCAL zeroerp.allow_lock_columns_override = 'on';

SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE dbops.domini_task SET codice = codice || '_PGTAP' WHERE id = (SELECT min(id) FROM dbops.domini_task)$$),
    NULL,
    '18) porta del lucchetto aperta dal migratore: il codice bloccato cambia');

SELECT is(
    (SELECT count(*)::int FROM dbops.porte_manutenzione_passaggi p
      WHERE p.chiave = 'zeroerp.allow_lock_columns_override'
        AND p.schema_name = 'dbops' AND p.table_name = 'domini_task' AND p.operazione = 'UPDATE'),
    1,
    '19) … e il diario la registra');

RESET zeroerp.allow_lock_columns_override;

SELECT is(
    dbops.fn_pgtap_codice_errore($$UPDATE dbops.domini_task SET codice = codice || '_DI_NUOVO' WHERE id = (SELECT min(id) FROM dbops.domini_task)$$),
    'E_CODICE_NON_MODIFICABILE',
    '20) senza porta il lucchetto rifiuta');

-- ============================================================
-- 21-22 La colonna non classificata (D8)
-- ============================================================
CREATE TEMP TABLE _args_prima AS
SELECT dbops.fn_trigger_argomenti(tg.tgargs) AS args
  FROM pg_trigger tg
 WHERE tg.tgrelid = 'config.email_template'::regclass
   AND tg.tgfoid = 'script.trgfn_seed_primo_impianto()'::regprocedure;

ALTER TABLE config.email_template ADD COLUMN pgtap_colonna_nuova text;

SELECT is(
    (SELECT format('%s|%s', d.azione, array_to_string(d.colonne_non_classificate, ','))
       FROM dbops.fn_seed_primo_impianto_divergenze(ARRAY['config']) d
      WHERE d.table_name = 'email_template'),
    'NON_CLASSIFICATA|pgtap_colonna_nuova',
    '21) una colonna aggiunta e non classificata: NON_CLASSIFICATA');

SELECT dbops.fn_run_automations_seed_primo_impianto('AUTO', ARRAY['config'], false);

SELECT is(
    (SELECT dbops.fn_trigger_argomenti(tg.tgargs)
       FROM pg_trigger tg
      WHERE tg.tgrelid = 'config.email_template'::regclass
        AND tg.tgfoid = 'script.trgfn_seed_primo_impianto()'::regprocedure),
    (SELECT args FROM _args_prima),
    '22) … il runner lascia il trigger di prima, che protegge le colonne gia'' dichiarate');

-- ============================================================
-- 23-25 L'iscrizione di una tabella
-- ============================================================
CREATE TABLE config.pgtap_seed_iscrizione (
    id          integer PRIMARY KEY,
    nome        text,
    user_insert text NOT NULL
);
INSERT INTO config.pgtap_seed_iscrizione VALUES
    (1, 'dal CSV, prima dell''audit', 'SEED'),
    (2, 'dal migrate',                current_user),
    (3, 'dall''applicazione',         'pgtap_username_qualunque');

-- id esplicito: gli id del registro li porta il CSV, e la sequenza non li conosce
INSERT INTO dbops.automazione_seed_primo_impianto (id, schema_name, table_name, motivo)
VALUES (990001, 'config', 'pgtap_seed_iscrizione', 'tabella di prova del pgTAP');

SELECT dbops.fn_run_automations_seed_primo_impianto('AUTO', ARRAY['config'], false);

SELECT is(
    (SELECT string_agg(s.riga_id || ':' || s.segnata_da, ',' ORDER BY s.riga_id)
       FROM dbops.seed_righe s
      WHERE s.schema_name = 'config' AND s.table_name = 'pgtap_seed_iscrizione'),
    '1:ISCRIZIONE,2:ISCRIZIONE',
    '23) l''iscrizione segna le righe con user_insert SEED o di un ruolo del migratore');

SELECT is(
    (SELECT count(*)::int FROM dbops.seed_righe s
      WHERE s.schema_name = 'config' AND s.table_name = 'pgtap_seed_iscrizione' AND s.riga_id = '3'),
    0,
    '24) … non quella di uno username: e'' dell''installazione');

DELETE FROM dbops.seed_righe
 WHERE schema_name = 'config' AND table_name = 'pgtap_seed_iscrizione' AND riga_id = '1';
UPDATE dbops.automazione_seed_primo_impianto
   SET trigger_name = 'trg_pgtap_seed_iscrizione_a00_rinominato'
 WHERE schema_name = 'config' AND table_name = 'pgtap_seed_iscrizione';

SELECT dbops.fn_run_automations_seed_primo_impianto('AUTO', ARRAY['config'], false);

SELECT is(
    (SELECT format('%s|%s',
                   (SELECT string_agg(tg.tgname, ',') FROM pg_trigger tg
                     WHERE tg.tgrelid = 'config.pgtap_seed_iscrizione'::regclass AND NOT tg.tgisinternal),
                   (SELECT count(*) FROM dbops.seed_righe s
                     WHERE s.schema_name = 'config' AND s.table_name = 'pgtap_seed_iscrizione' AND s.riga_id = '1'))),
    'trg_pgtap_seed_iscrizione_a00_rinominato|0',
    '25) la rigenerazione rinomina il trigger e non ripassa dall''iscrizione');

-- ============================================================
-- 26 Il proprietario e' il migratore
-- ============================================================
SELECT is(
    dbops.fn_sessione_del_migratore(),
    true,
    '26) fn_sessione_del_migratore da proprietario: true');

SELECT * FROM finish();
ROLLBACK;
