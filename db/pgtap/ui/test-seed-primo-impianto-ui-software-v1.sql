-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il soggetto e' la scrittura del SOFTWARE (la sessione del migratore: il blocco DO del mirror sulla composizione, il runner che monta la forma figlia), che l'applicazione non raggiunge; il test fa anche DDL su una tabella di prova e scrive il registro delle automazioni
--
-- Test: la forma FIGLIA del seed di primo impianto, vista dal SOFTWARE.
--   Brief: brief-db-seed-primo-impianto-non-si-riscrive (§16.15, QU2).
--   ChangeSet: 20261119-01 … -05; le righe 5 e 6 di
--   dbops.automazione_seed_primo_impianto (80_data).
--   Il lato dell'installazione: db/pgtap/ui/test-seed-primo-impianto-ui-installazione-v1.sql.
--
-- Il blocco DO del mirror si scrive qui com'e' il SQL di loadUpdateData su
--   PostgreSQL: `UPDATE …; IF not found THEN INSERT …; END IF`. La
--   personalizzazione del preset si simula scrivendo il registro da
--   proprietario. I soggetti sono il preset di sistema 1 e la sua composizione
--   (80_data, contratto); la grammatica e le divergenze si provano su tabelle
--   di prova create qui.
--
-- Elenco test (plan 21):
--    1) mirror della composizione sotto un preset intatto: nessun errore
--    2) … la riga segue il CSV
--    3) mirror sotto il preset personalizzato: nessuna chiave duplicata
--    4) … la riga resta com'era
--    5) il software toglie una riga della composizione del preset
--       personalizzato: passa (una colonna ritirata)
--    6) mirror che reinserisce quella riga: nessun errore
--    7) … e la riga non c'e': il preset personalizzato non la riceve
--    8) grammatica: FIGLIA con colonna e padre e' valida, senza elenchi
--    9) … FIGLIA con due argomenti non e' valida
--   10) … FIGLIA con il padre senza schema non e' valida
--   11) … FIGLIA con la colonna NULL non e' valida
--   12) registro: una riga figlia con gli elenchi e' rifiutata (CHECK)
--   13) divergenze: una figlia senza id sotto un padre iscritto e' CREA, non SENZA_ID
--   14) … sotto un padre non iscritto e' PADRE_NON_ISCRITTO
--   15) … con la colonna del padre assente e' NON_CLASSIFICATA
--   16) il runner monta la figlia e non la iscrive
--   Le colonne derivate (brief-db-revisione-ui, giro 7, Q54 (a); numerati in coda)
--   17) ⭐ dopo il ritiro del caso 5 l'impronta del preset personalizzato e' quella
--       della sua composizione: il seed non l'ha riportata indietro
--   18) … e non e' finita fra i valori scartati del registro
--   19) grammatica: COLONNA con le colonne derivate come quarto argomento e' valida
--   20) … una derivata che non sta fra le colonne dell'installazione no
--   21) controllo del seed: il montaggio su ui.lista_preset porta
--       composizione_impronta come colonna derivata (riga 5 del registro)
-- ------------------------------------------------------------
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(21);

-- ============================================================
-- 1-2 Sotto un preset intatto la composizione segue il CSV
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($mirror$
        DO $$ BEGIN
            UPDATE ui.lista_preset_colonna SET larghezza = 111
             WHERE preset_id = 1 AND colonna_id = 3;
            IF not found THEN
                INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, larghezza)
                VALUES (1, 3, 10, 111);
            END IF;
        END $$ $mirror$),
    NULL,
    '1) mirror della composizione sotto un preset intatto: nessun errore');

SELECT is(
    (SELECT larghezza FROM ui.lista_preset_colonna WHERE preset_id = 1 AND colonna_id = 3),
    111,
    '2) … la riga segue il CSV');

-- ============================================================
-- 3-7 Sotto il preset personalizzato il software non scrive
-- ============================================================
UPDATE dbops.seed_righe
   SET personalizzata_il = now(), personalizzata_da = 'pgtap_installazione'
 WHERE schema_name = 'ui' AND table_name = 'lista_preset' AND riga_id = '1';

SELECT is(
    dbops.fn_pgtap_codice_errore($mirror$
        DO $$ BEGIN
            UPDATE ui.lista_preset_colonna SET larghezza = 222
             WHERE preset_id = 1 AND colonna_id = 3;
            IF not found THEN
                INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine, larghezza)
                VALUES (1, 3, 10, 222);
            END IF;
        END $$ $mirror$),
    NULL,
    '3) mirror sotto il preset personalizzato: l''UPDATE trova la riga, nessuna chiave duplicata');

SELECT is(
    (SELECT larghezza FROM ui.lista_preset_colonna WHERE preset_id = 1 AND colonna_id = 3),
    111,
    '4) … la riga resta com''era');

SELECT is(
    dbops.fn_pgtap_codice_errore($$DELETE FROM ui.lista_preset_colonna WHERE preset_id = 1 AND colonna_id = 14$$),
    NULL,
    '5) il software toglie una riga della composizione del preset personalizzato: passa');

SELECT is(
    dbops.fn_pgtap_codice_errore($mirror$
        DO $$ BEGIN
            UPDATE ui.lista_preset_colonna SET ordine = 140
             WHERE preset_id = 1 AND colonna_id = 14;
            IF not found THEN
                INSERT INTO ui.lista_preset_colonna (preset_id, colonna_id, ordine)
                VALUES (1, 14, 140);
            END IF;
        END $$ $mirror$),
    NULL,
    '6) mirror che reinserisce quella riga: nessun errore');

SELECT is(
    (SELECT count(*)::int FROM ui.lista_preset_colonna WHERE preset_id = 1 AND colonna_id = 14),
    0,
    '7) … e la riga non c''e'': il preset personalizzato non la riceve');

-- 17-18) Il caso 5 ha tolto una riga della composizione nella sessione del
--   migratore: il trigger della composizione ha riscritto l'impronta del preset, e
--   il seed (a00) non la riporta a OLD perche' e' una colonna derivata.
SELECT is(
    (SELECT lp.composizione_impronta FROM ui.lista_preset lp WHERE lp.id = 1),
    ui.fn_preset_impronta('lista', 1),
    '17) ⭐ dopo il ritiro l''impronta del preset personalizzato e'' quella della sua composizione');

SELECT is(
    (SELECT COALESCE(s.scartati ? 'composizione_impronta', false)
       FROM dbops.seed_righe s
      WHERE s.schema_name = 'ui' AND s.table_name = 'lista_preset' AND s.riga_id = '1'),
    false,
    '18) … e l''impronta non e'' fra i valori scartati del registro');

-- ============================================================
-- 8-11 La grammatica
-- ============================================================
SELECT is(
    (SELECT valido::text || ',' || forma || ',' || (colonne_software IS NULL)::text
       FROM dbops.fn_seed_primo_impianto_argomenti(ARRAY['FIGLIA', 'preset_id', 'ui.lista_preset'])),
    'true,FIGLIA,true',
    '8) grammatica: FIGLIA con colonna e padre e'' valida, senza elenchi');

SELECT is(
    (SELECT valido FROM dbops.fn_seed_primo_impianto_argomenti(ARRAY['FIGLIA', 'preset_id'])),
    false,
    '9) … FIGLIA con due argomenti non e'' valida');

SELECT is(
    (SELECT valido FROM dbops.fn_seed_primo_impianto_argomenti(ARRAY['FIGLIA', 'preset_id', 'lista_preset'])),
    false,
    '10) … FIGLIA con il padre senza schema non e'' valida');

SELECT is(
    (SELECT valido FROM dbops.fn_seed_primo_impianto_argomenti(ARRAY['FIGLIA', NULL, 'ui.lista_preset'])),
    false,
    '11) … FIGLIA con la colonna NULL non e'' valida');

SELECT is(
    (SELECT valido::text || ',' || forma
       FROM dbops.fn_seed_primo_impianto_argomenti(
                ARRAY['COLONNA', 'codice', 'descrizione,impronta', 'impronta'])),
    'true,COLONNA',
    '19) grammatica: COLONNA con le colonne derivate come quarto argomento e'' valida');

SELECT is(
    (SELECT valido::text || ',' || COALESCE(dettaglio, '')
       FROM dbops.fn_seed_primo_impianto_argomenti(
                ARRAY['COLONNA', 'codice', 'descrizione', 'impronta'])),
    'false,forma COLONNA: una colonna derivata non sta fra quelle dell''installazione',
    '20) … una derivata che non sta fra le colonne dell''installazione no');

-- ============================================================
-- 12-16 Registro, divergenze e runner, su tabelle di prova
-- ============================================================
CREATE TABLE ui.pgtap_seed_figlia_a (padre_id integer NOT NULL, valore text);
CREATE TABLE ui.pgtap_seed_figlia_b (padre_id integer NOT NULL, valore text);

SELECT is(
    dbops.fn_pgtap_codice_errore($$
        INSERT INTO dbops.automazione_seed_primo_impianto
               (id, schema_name, table_name, colonne_software, colonne_installazione, motivo,
                tabella_padre, colonna_padre)
        VALUES (9001, 'ui', 'pgtap_seed_figlia_a', ARRAY['valore'], ARRAY['padre_id'], 'prova',
                'ui.lista_preset', 'padre_id')$$),
    'chk_automazione_seed_primo_impianto_figlia',
    '12) registro: una riga figlia con gli elenchi e'' rifiutata');

INSERT INTO dbops.automazione_seed_primo_impianto
       (id, schema_name, table_name, motivo, tabella_padre, colonna_padre)
VALUES (9001, 'ui', 'pgtap_seed_figlia_a', 'prova: padre iscritto', 'ui.lista_preset', 'padre_id'),
       (9002, 'ui', 'pgtap_seed_figlia_b', 'prova: padre non iscritto', 'ui.lista_colonna_permesso', 'padre_id');

SELECT is(
    (SELECT azione FROM dbops.fn_seed_primo_impianto_divergenze(ARRAY['ui'])
      WHERE table_name = 'pgtap_seed_figlia_a'),
    'CREA',
    '13) divergenze: una figlia senza id sotto un padre iscritto e'' CREA, non SENZA_ID');

SELECT is(
    (SELECT azione FROM dbops.fn_seed_primo_impianto_divergenze(ARRAY['ui'])
      WHERE table_name = 'pgtap_seed_figlia_b'),
    'PADRE_NON_ISCRITTO',
    '14) … sotto un padre non iscritto e'' PADRE_NON_ISCRITTO');

ALTER TABLE ui.pgtap_seed_figlia_a RENAME COLUMN padre_id TO altro_id;

SELECT is(
    (SELECT azione FROM dbops.fn_seed_primo_impianto_divergenze(ARRAY['ui'])
      WHERE table_name = 'pgtap_seed_figlia_a'),
    'NON_CLASSIFICATA',
    '15) … con la colonna del padre assente e'' NON_CLASSIFICATA');

ALTER TABLE ui.pgtap_seed_figlia_a RENAME COLUMN altro_id TO padre_id;
DELETE FROM dbops.automazione_seed_primo_impianto WHERE id = 9002;
DROP TABLE ui.pgtap_seed_figlia_b;

SELECT dbops.fn_run_automations_seed_primo_impianto('AUTO', ARRAY['ui'], false);

SELECT is(
    (SELECT count(*)::int FROM pg_trigger tg
      WHERE tg.tgrelid = 'ui.pgtap_seed_figlia_a'::regclass
        AND tg.tgfoid = 'script.trgfn_seed_primo_impianto()'::regprocedure)
    || ',' ||
    (SELECT count(*)::int FROM dbops.seed_righe
      WHERE schema_name = 'ui' AND table_name = 'pgtap_seed_figlia_a'),
    '1,0',
    '16) il runner monta la figlia e non la iscrive');

-- 21) Un controllo del seed, non del modello: lo dichiara la riga 5 del registro.
SELECT is(
    (SELECT (dbops.fn_trigger_argomenti(tg.tgargs))[4]
       FROM pg_trigger tg
      WHERE tg.tgrelid = 'ui.lista_preset'::regclass
        AND tg.tgfoid = 'script.trgfn_seed_primo_impianto()'::regprocedure
        AND NOT tg.tgisinternal),
    'composizione_impronta',
    '21) controllo del seed: il montaggio su ui.lista_preset porta composizione_impronta come colonna derivata');

SELECT * FROM finish();
ROLLBACK;
