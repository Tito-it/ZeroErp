-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- I livelli di un tipo di documento nel catalogo delle sorgenti: la tabella
--   delle righe e quella del dettaglio, ognuna con la sua FK verso il livello
--   sopra (config.sorgenti.righe_table / righe_fk_column / dettaglio_table /
--   dettaglio_fk_column), e il BB che li legge, config.fn_sorgente_livelli.
--   Brief: brief-db-sorgente-documento-e-riga §7.2 lotto 0 (S-2, S-3, D-2, D-5).
--   ChangeSet: 20261106-04 (colonne e CHECK), sorgenti.csv (80_data, mirror
--   20251002-21), 20261106-10 (config.fn_sorgente_livelli, fn_sorgente_tabella).
--
-- Elenco test (plan 12):
--  1) le quattro colonne esistono
--  2) i sei CHECK di forma esistono
--  3) ⭐ ogni tabella delle righe dichiarata ha davvero la FK dichiarata verso la
--       tabella del documento (pg_constraint): dichiarata, non ricavata
--  4) ⭐ ogni tabella del dettaglio dichiarata ha davvero la FK verso le righe
--  5) la mappa del seed: i quattordici tipi che hanno righe, con la loro colonna
--  6) la mappa del seed: i due tipi con il dettaglio (bolla e reso)
--  7) i tipi senza livelli hanno le quattro colonne a NULL (nessun *_RIGA, ne'
--       i livelli sotto la riga, ne' ATTIVITA_CONSUMI ed EMAIL, ha righe)
--  8) fn_sorgente_livelli(DDT_VENDITA): documento, righe e dettaglio con le loro
--       colonne, uid ed etichetta presenti
--  9) fn_sorgente_livelli(COMMESSA): la tabella del documento non ha uid
-- 10) fn_sorgente_livelli di un tipo che non esiste: nessuna riga
-- 11) fn_sorgente_livelli dichiara ROWS 1
-- 12) config.fn_sorgente_tabella e' invariata: ORDINE_VENDITA -> vendite.ordini
--
-- ⭐ Legge il SEED e il catalogo di PostgreSQL, non una popolazione: le righe le
--   porta il CSV di 80_data, presente anche sul database ricostruito da zero.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- 1) le colonne
SELECT is(
    (SELECT count(*)::int FROM information_schema.columns
      WHERE table_schema = 'config' AND table_name = 'sorgenti'
        AND column_name IN ('righe_table', 'righe_fk_column', 'dettaglio_table', 'dettaglio_fk_column')),
    4,
    '1) config.sorgenti ha righe_table, righe_fk_column, dettaglio_table, dettaglio_fk_column');

-- 2) i CHECK di forma
SELECT is(
    (SELECT array_agg(c.conname::text COLLATE "default" ORDER BY c.conname::text COLLATE "default")
       FROM pg_constraint c
      WHERE c.conrelid = 'config.sorgenti'::regclass AND c.contype = 'c'
        AND c.conname IN ('chk_sorgenti_righe_coppia', 'chk_sorgenti_dettaglio_coppia',
                          'chk_sorgenti_righe_sotto_documento', 'chk_sorgenti_dettaglio_sotto_righe',
                          'chk_sorgenti_righe_fk_column_identificatore',
                          'chk_sorgenti_dettaglio_fk_column_identificatore')),
    ARRAY['chk_sorgenti_dettaglio_coppia', 'chk_sorgenti_dettaglio_fk_column_identificatore',
          'chk_sorgenti_dettaglio_sotto_righe', 'chk_sorgenti_righe_coppia',
          'chk_sorgenti_righe_fk_column_identificatore', 'chk_sorgenti_righe_sotto_documento'],
    '2) i sei CHECK di forma dei livelli esistono');

-- 3) la FK delle righe esiste davvero
SELECT is_empty(
    $$SELECT s.codice_interno
        FROM config.sorgenti s
       WHERE s.righe_table IS NOT NULL
         AND NOT EXISTS (
             SELECT 1
               FROM pg_constraint c
               JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
              WHERE c.contype = 'f'
                AND c.conrelid = s.righe_table
                AND c.confrelid = s.target_table
                AND array_length(c.conkey, 1) = 1
                AND a.attname = s.righe_fk_column::name)
       ORDER BY 1$$,
    '3) ogni righe_table dichiarata ha la FK righe_fk_column verso la target_table');

-- 4) la FK del dettaglio esiste davvero
SELECT is_empty(
    $$SELECT s.codice_interno
        FROM config.sorgenti s
       WHERE s.dettaglio_table IS NOT NULL
         AND NOT EXISTS (
             SELECT 1
               FROM pg_constraint c
               JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
              WHERE c.contype = 'f'
                AND c.conrelid = s.dettaglio_table
                AND c.confrelid = s.righe_table
                AND array_length(c.conkey, 1) = 1
                AND a.attname = s.dettaglio_fk_column::name)
       ORDER BY 1$$,
    '4) ogni dettaglio_table dichiarata ha la FK dettaglio_fk_column verso la righe_table');

-- 5) i tipi con le righe (il seed)
SELECT results_eq(
    $$SELECT s.codice_interno::text, (l.righe_schema::text || '.' || l.righe_tabella::text) COLLATE "default",
             s.righe_fk_column::text
        FROM config.sorgenti s
        CROSS JOIN LATERAL config.fn_sorgente_livelli(s.id) l
       WHERE s.righe_table IS NOT NULL
       ORDER BY 1$$,
    $$VALUES ('COMMESSA', 'vendite.commesse_attivita', 'commessa_id'),
             ('CONTRATTO', 'vendite.contratti_righe', 'contratto_id'),
             ('DDT_ACQUISTO', 'acquisti.ddt_righe', 'ddt_id'),
             ('DDT_VENDITA', 'vendite.ddt_righe', 'ddt_id'),
             ('DISTINTA_INCASSO', 'pagamenti.vendite_contabili_righe', 'contabile_id'),
             ('FATTURA', 'vendite.fatture_righe', 'fattura_id'),
             ('INVENTARIO', 'magazzino.inventari_righe', 'inventario_id'),
             ('OFFERTA_COMMERCIALE', 'vendite.offerte_commerciali_eccezioni', 'offerta_id'),
             ('ORDINE_ACQUISTO', 'acquisti.ordini_righe', 'ordine_id'),
             ('ORDINE_VENDITA', 'vendite.ordini_righe', 'ordine_id'),
             ('PREVENTIVO', 'vendite.preventivi_righe', 'preventivo_id'),
             ('RESO_VENDITA', 'vendite.resi_righe', 'reso_id'),
             ('RETTIFICA', 'magazzino.rettifiche_righe', 'rettifica_id'),
             ('TRASFERIMENTO', 'magazzino.trasferimenti_righe', 'trasferimento_id')$$,
    '5) le righe dei quattordici tipi che le hanno, con la colonna verso il documento');

-- 6) i tipi con il dettaglio (il seed)
SELECT results_eq(
    $$SELECT s.codice_interno::text, (l.dettaglio_schema::text || '.' || l.dettaglio_tabella::text) COLLATE "default",
             s.dettaglio_fk_column::text
        FROM config.sorgenti s
        CROSS JOIN LATERAL config.fn_sorgente_livelli(s.id) l
       WHERE s.dettaglio_table IS NOT NULL
       ORDER BY 1$$,
    $$VALUES ('DDT_VENDITA', 'vendite.ddt_righe_prelievi', 'ddt_riga_id'),
             ('RESO_VENDITA', 'vendite.resi_righe_rientri', 'resi_riga_id')$$,
    '6) il dettaglio della bolla (il prelievo) e del reso (il rientro)');

-- 7) chi non ha livelli
SELECT is_empty(
    $$SELECT s.codice_interno
        FROM config.sorgenti s
       WHERE (s.codice_interno LIKE '%\_RIGA' OR s.codice_interno IN
                 ('DDT_VENDITA_PRELIEVO', 'RESO_VENDITA_RIENTRO', 'EVENTO_ASSET',
                  'ATTIVITA', 'ATTIVITA_CONSUMI', 'EMAIL'))
         AND (s.righe_table IS NOT NULL OR s.righe_fk_column IS NOT NULL
              OR s.dettaglio_table IS NOT NULL OR s.dettaglio_fk_column IS NOT NULL)$$,
    '7) i tipi di riga, i livelli sotto la riga, gli oggetti senza righe: livelli a NULL');

-- 8) il BB su un tipo a tre livelli
SELECT results_eq(
    $$SELECT l.codice_interno::text, l.key_selector::text,
             (l.documento_schema::text || '.' || l.documento_tabella::text) COLLATE "default",
             l.documento_ha_uid, l.documento_ha_label,
             (l.righe_schema::text || '.' || l.righe_tabella::text) COLLATE "default", l.righe_fk_column::text,
             (l.dettaglio_schema::text || '.' || l.dettaglio_tabella::text) COLLATE "default", l.dettaglio_fk_column::text,
             l.documento_relid = 'vendite.ddt'::regclass::oid
        FROM config.sorgenti s
        CROSS JOIN LATERAL config.fn_sorgente_livelli(s.id) l
       WHERE s.codice_interno = 'DDT_VENDITA'$$,
    $$VALUES ('DDT_VENDITA', 'id', 'vendite.ddt', true, true,
              'vendite.ddt_righe', 'ddt_id', 'vendite.ddt_righe_prelievi', 'ddt_riga_id', true)$$,
    '8) fn_sorgente_livelli(DDT_VENDITA): bolla, righe, prelievi, con uid ed etichetta');

-- 9) una tabella del documento senza uid
SELECT is(
    (SELECT l.documento_ha_uid
       FROM config.sorgenti s
       CROSS JOIN LATERAL config.fn_sorgente_livelli(s.id) l
      WHERE s.codice_interno = 'COMMESSA'),
    false,
    '9) fn_sorgente_livelli(COMMESSA): vendite.commesse non ha la colonna uid');

-- 10) un tipo che non esiste
SELECT is(
    (SELECT count(*)::int FROM config.fn_sorgente_livelli(-1::bigint)),
    0,
    '10) fn_sorgente_livelli di un tipo che non esiste: nessuna riga');

-- 11) ROWS 1
SELECT is(
    (SELECT p.prorows::int FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'config' AND p.proname = 'fn_sorgente_livelli'),
    1,
    '11) fn_sorgente_livelli dichiara ROWS 1');

-- 12) fn_sorgente_tabella, ora sopra il BB
SELECT results_eq(
    $$SELECT schema_tabella::text COLLATE "default", nome_tabella::text COLLATE "default", relid = 'vendite.ordini'::regclass::oid
        FROM config.fn_sorgente_tabella('ORDINE_VENDITA')$$,
    $$VALUES ('vendite', 'ordini', true)$$,
    '12) config.fn_sorgente_tabella(ORDINE_VENDITA) -> vendite.ordini, come prima');

SELECT * FROM finish();
ROLLBACK;
