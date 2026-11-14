-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- La ricevuta dello shop nella grammatica dei documenti, e registrata nel
-- catalogo delle sorgenti.
--   Brief: brief-db-cambio-natura-soggetto-conferma-e-pulizia §0, D-9 e D-10
--   (Tid, 2026-11-14), giro 1. ChangeSet: 00_schema/shop/20261114-59; le righe
--   RICEVUTA di config/sorgenti.csv e config/tipi_entita.csv; il trigger «in
--   uscita» lo monta dbops.fn_sorgente_converge_uscita in 90_end.
--
-- Elenco test (plan 11):
--  1) shop.ricevute.id e' bigint
--  2) shop.ricevute.id e' la PK
--  3) shop.ricevute.id e' identity BY DEFAULT, come vendite.resi
--  4) shop.ricevute.uid e' uuid NOT NULL con default uuidv7()
--  5) shop.ricevute.uid ha un indice UNIQUE di sola uid
--  6) la shadow storico.ricevute ha ricevute_id del TIPO della PK della madre
--  7) config.sorgenti RICEVUTA: DOCUMENTO, attiva, key_selector id
--  8) config.sorgenti RICEVUTA punta a shop.ricevute
--  9) config.fn_sorgente_tabella('RICEVUTA') risponde shop.ricevute
-- 10) config.tipi_entita RICEVUTA e' dichiarata is_sorgente
-- 11) script.trgfn_sorgente_in_uscita e' montato su shop.ricevute
--
-- ⭐ Il 6 e' l'invariante che il changeSet ripara: dbops.fn_ensure_storico_table
--   da' a ricevute_id il tipo della PK della madre, e se la shadow c'e' gia' non
--   la tocca. Si confrontano i due tipi letti dal catalogo, non un letterale:
--   un cambio di chiave futuro che dimentica la shadow diventa rosso qui.
-- ⚠️ Il 6 salta solo dove la shadow non esiste ancora: su un database da zero
--   la crea ci_apply, dopo i changeSet (in CI i pgTAP girano dopo, e c'e').
-- ⚠️ 7-11 leggono il seed (80_data) e il montaggio di 90_end: davanti al solo
--   estratto del changeSet (scripts/prova_changeset.py) sono rossi, e diventano
--   verdi con l'apply.
-- ⛔ NON PROVATO, e dichiarato: il percorso con una ricevuta vera (INSERT,
--   UPDATE, riga di storico con ricevute_id = id). La ricevuta vuole un billing
--   account del canale SHOP (trgfn_ricevute_guard_ba_canale), canale_origine e'
--   immutabile dopo la nascita, e nessuna fixture dbops.fn_pgtap_* sa creare un
--   BA di quel canale. La ricevuta oggi non ha scrittori: il percorso si prova
--   quando il cantiere dello shop le dara' un verbo.
-- ⚠️ 8 e 11: la tabella si legge da pg_class/pg_namespace o per OID, mai con
--   target_table::text (dipende dal search_path di chi legge).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

SELECT col_type_is('shop', 'ricevute', 'id', 'bigint',
    '1) shop.ricevute.id e'' bigint');

SELECT col_is_pk('shop', 'ricevute', 'id',
    '2) shop.ricevute.id e'' la PK');

SELECT is(
    (SELECT a.attidentity::text
       FROM pg_attribute a
      WHERE a.attrelid = 'shop.ricevute'::regclass AND a.attname = 'id'),
    'd',
    '3) shop.ricevute.id e'' identity BY DEFAULT, come vendite.resi');

SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_attribute a
          JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
         WHERE a.attrelid = 'shop.ricevute'::regclass
           AND a.attname = 'uid'
           AND a.atttypid = 'uuid'::regtype
           AND a.attnotnull
           AND pg_get_expr(d.adbin, d.adrelid) = 'uuidv7()'),
    '4) shop.ricevute.uid e'' uuid NOT NULL con default uuidv7()');

SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_index i
         WHERE i.indrelid = 'shop.ricevute'::regclass
           AND i.indisunique
           AND i.indnatts = 1
           AND i.indkey[0] = (SELECT a.attnum FROM pg_attribute a
                               WHERE a.attrelid = 'shop.ricevute'::regclass
                                 AND a.attname = 'uid')),
    '5) shop.ricevute.uid ha un indice UNIQUE di sola uid');

SELECT CASE
    WHEN to_regclass('storico.ricevute') IS NULL THEN
        skip('6) la shadow storico.ricevute non esiste ancora (la crea ci_apply)', 1)
    ELSE
        is(
            (SELECT a.atttypid::regtype::text
               FROM pg_attribute a
              WHERE a.attrelid = to_regclass('storico.ricevute')
                AND a.attname = 'ricevute_id' AND NOT a.attisdropped),
            (SELECT a.atttypid::regtype::text
               FROM pg_attribute a
              WHERE a.attrelid = 'shop.ricevute'::regclass
                AND a.attname = 'id'),
            '6) storico.ricevute.ricevute_id ha il tipo della PK di shop.ricevute')
END;

SELECT ok(
    EXISTS (
        SELECT 1 FROM config.sorgenti s
         WHERE s.codice_interno = 'RICEVUTA'
           AND s.categoria = 'DOCUMENTO'
           AND s.attivo
           AND s.key_selector = 'id'),
    '7) config.sorgenti RICEVUTA: DOCUMENTO, attiva, key_selector id');

SELECT ok(
    EXISTS (
        SELECT 1
          FROM config.sorgenti s
          JOIN pg_class c ON c.oid = s.target_table
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE s.codice_interno = 'RICEVUTA'
           AND n.nspname = 'shop' AND c.relname = 'ricevute'),
    '8) config.sorgenti RICEVUTA punta a shop.ricevute');

SELECT is(
    (SELECT t.relid FROM config.fn_sorgente_tabella('RICEVUTA') t),
    'shop.ricevute'::regclass::oid,
    '9) config.fn_sorgente_tabella(''RICEVUTA'') risponde shop.ricevute');

SELECT ok(
    EXISTS (SELECT 1 FROM config.tipi_entita te
             WHERE te.codice = 'RICEVUTA' AND te.is_sorgente),
    '10) config.tipi_entita RICEVUTA e'' dichiarata is_sorgente');

SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_trigger g
         WHERE g.tgrelid = 'shop.ricevute'::regclass
           AND g.tgfoid = 'script.trgfn_sorgente_in_uscita'::regproc
           AND NOT g.tgisinternal),
    '11) script.trgfn_sorgente_in_uscita e'' montato su shop.ricevute (per funzione, non per nome)');

SELECT * FROM finish();

ROLLBACK;
