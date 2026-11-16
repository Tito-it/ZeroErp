-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la stampa e' storia — il giro 1 della revisione dello schema documenti.
-- ChangeSet: 20261115-82 … -89, e il registro dbops.automazione_attivo_eccezioni
--
-- Elenco test (plan 15):
--   Il PDF principale
--   1) una stampa senza file principale non si registra (codice)
--   2) ... e la frase dice quale, col nome del file
--   3) una stampa col suo PDF principale si registra
--   4) il file di una stampa non si cancella
--   Lo snapshot
--   5) l'id di una stampa non cambia
--   La coerenza alla nascita
--   6) cambiato il tipo del modello dopo la stampa, la stampa vecchia si
--      modifica ancora nel suo meta
--   Le stampe non tengono accesi i padri
--   7) la versione che ha stampato si spegne
--   8) il modello che ha stampato si spegne
--   9) ... e la risoluzione per l'azienda torna allo standard
--  10) il tipo di file non ha un interruttore: la stampa non tiene acceso niente
--   Il building block «rifiuta sempre»
--  11) senza argomenti: E_TABELLA_OP_NON_CONSENTITA
--  12) col codice e le colonne: la frase porta i valori, la data in GG/MM/AAAA
--  13) una colonna che la tabella non ha: E_TRIGGER_ARGOMENTI_INVALIDI
--  14) i sei montaggi (stampa, eventi x2, file, asset, movimenti IVA) sono sul BB
--  15) le cinque copie ritirate non esistono piu'
--
-- Scopo:
--  - provare sui casi COSTRUITI le regole del giro: un'azienda nuova, un suo
--    modello predefinito con la versione pubblicata, una stampa di un suo
--    preventivo. Nessuna riga di dbdev entra come soggetto.
--  - ⚠️ 7-9 chiedono che il motore ATTIVO abbia gia' tolto i trigger delle FK
--    a registro (dbops.fn_run_automations_attivo, o il job serale): su un
--    database aggiornato e non ancora ripassato dal motore sono rossi, come il
--    test 9 di test-automazione-attivo-eccezioni-v1.
--  - Lo standard del preventivo (test 9) e' il seed di 80_data: e' il contratto
--    della risoluzione, non una riga di passaggio.
-- ------------------------------------------------------------

BEGIN;

-- Un'azienda nuova, senza modelli suoi.
CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e));
END $ctx$;

-- La stampa e' di un preventivo vero del mondo dell'operatore: il guard della
-- sorgente verifica che il documento stampato esista.
CREATE TEMP TABLE _src ON COMMIT DROP AS
SELECT p.preventivo_uid FROM dbops.fn_pgtap_crea_preventivo('dg storia', 'DRAFT') p;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture: il modello dell'azienda, predefinito, con la versione pubblicata
-- ============================================================
CREATE TEMP TABLE _k ON COMMIT DROP AS
SELECT
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')                   AS sorg,
  (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'PREVENTIVO')    AS tipo,
  (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'CONTRATTO')     AS tipo2,
  (SELECT r.id FROM documenti.render_engine_documento r WHERE r.codice_interno = 'WEASYPRINT') AS render,
  (SELECT f.id FROM documenti.tipi_file_documento f WHERE f.codice_interno = 'PDF_FINALE')     AS pdf,
  (SELECT emittente_fiscale_id FROM _e)                                                        AS em;

CREATE TEMP TABLE _m ON COMMIT DROP AS
WITH t AS (
  INSERT INTO documenti.template_documenti (
      tipo_documento_output_id, codice, codice_interno, descrizione,
      sorgente_tipo_id, context_builder_code, emittente_fiscale_id, is_default, attivo)
  SELECT tipo, 'PGTAP-STORIA', 'pgtap-storia', 'Modello della stampa storia', sorg,
         'PREVENTIVO', em, true, true
    FROM _k
  RETURNING id
)
SELECT id FROM t;

CREATE TEMP TABLE _v ON COMMIT DROP AS
WITH v AS (
  INSERT INTO documenti.template_documenti_versioni (
      template_documento_id, versione, stato, titolo, html_template,
      render_engine_id, valido_dal, valido_al, versione_contesto)
  SELECT (SELECT id FROM _m), 1, 'PUBBLICATA', 'storia v1', '<html>storia</html>',
         render, DATE '2026-01-01', NULL, 1
    FROM _k
  RETURNING id
)
SELECT id FROM v;

-- L'INSERT della stampa, senza RETURNING: il test 1 lo esegue nudo, l'helper
-- dbops.fn_pgtap_stampa_con_pdf col suo PDF.
CREATE FUNCTION pg_temp.insert_stampa(p_progressivo integer, p_nome_file text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format($i$
    INSERT INTO documenti.documenti_generati (
        tipo_documento_output_id, template_documento_id, template_versione_id,
        sorgente_tipo_id, sorgente_uid, sorgente_riga, progressivo_sorgente,
        titolo, nome_file, context_json, context_hash, template_hash, pdf_hash,
        emittente_fiscale_id)
    SELECT k.tipo, (SELECT id FROM _m), (SELECT id FROM _v), k.sorg,
           (SELECT preventivo_uid FROM _src), NULL, %s,
           'Stampa storia', %L, '{"_meta": {"context_version": 1}}'::jsonb,
           repeat('1', 64), repeat('2', 64), repeat('3', 64), k.em
      FROM _k k$i$, p_progressivo, p_nome_file)
$f$;

-- ============================================================
-- Il PDF principale
-- ============================================================
-- 1
SELECT is(
  dbops.fn_pgtap_codice_errore(pg_temp.insert_stampa(1, 'pgtap-senza.pdf')),
  'E_DOCUMENTI_GENERATO_SENZA_FILE_PRINCIPALE',
  '1) una stampa senza file principale non si registra');

-- 2
SELECT throws_like(
  pg_temp.insert_stampa(1, 'pgtap-senza.pdf'),
  '%La stampa pgtap-senza.pdf non si registra: manca il suo PDF principale%',
  '2) ... e la frase dice quale stampa, col nome del file');

-- 3
CREATE TEMP TABLE _s ON COMMIT DROP AS
SELECT dbops.fn_pgtap_stampa_con_pdf(pg_temp.insert_stampa(1, 'pgtap-storia.pdf')) AS id;

SELECT is(
  (SELECT count(*)::int FROM documenti.documenti_generati_file f
    WHERE f.documento_generato_id = (SELECT id FROM _s) AND f.is_principale),
  1,
  '3) una stampa col suo PDF principale si registra');

-- 4
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'DELETE FROM documenti.documenti_generati_file WHERE documento_generato_id = %s',
    (SELECT id FROM _s))),
  'E_FILE_DOCUMENTO_DELETE_VIETATA',
  '4) il file di una stampa non si cancella');

-- ============================================================
-- Lo snapshot
-- ============================================================
-- 5: una stampa senza figli non avrebbe fermato il cambio con la FK; qui ha il
--    suo file, e a parlare dev'essere comunque il guard dello snapshot.
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    'UPDATE documenti.documenti_generati SET id = id + 1000000000 WHERE id = %s',
    (SELECT id FROM _s))),
  'E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE',
  '5) l''id di una stampa non cambia');

-- ============================================================
-- La coerenza alla nascita
-- ============================================================
-- 6: il modello cambia tipo dopo la stampa (nessun lucchetto lo vieta). La
--    stampa vecchia resta modificabile nel suo meta: la coerenza la giudica la
--    nascita, e sull'UPDATE le colonne le tiene ferme lo snapshot.
UPDATE documenti.template_documenti SET tipo_documento_output_id = (SELECT tipo2 FROM _k)
 WHERE id = (SELECT id FROM _m);

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $$UPDATE documenti.documenti_generati SET meta = '{"nota": "dopo"}'::jsonb WHERE id = %s$$,
    (SELECT id FROM _s))),
  NULL,
  '6) cambiato il modello dopo la stampa, la stampa vecchia si modifica ancora nel meta');

UPDATE documenti.template_documenti SET tipo_documento_output_id = (SELECT tipo FROM _k)
 WHERE id = (SELECT id FROM _m);

-- ============================================================
-- Le stampe non tengono accesi i padri
-- ============================================================
-- 7
SELECT lives_ok(
  format('UPDATE documenti.template_documenti_versioni SET attivo = false WHERE id = %s',
         (SELECT id FROM _v)),
  '7) la versione che ha stampato si spegne');

-- 8
SELECT lives_ok(
  format('UPDATE documenti.template_documenti SET attivo = false WHERE id = %s',
         (SELECT id FROM _m)),
  '8) il modello che ha stampato si spegne');

-- 9
SELECT is(
  (SELECT r.livello
     FROM _k, documenti.fn_risolvi_template_applicabile(_k.sorg, _k.em, _k.tipo) r),
  'STANDARD',
  '9) ... e l''azienda torna allo standard');

-- 10
-- Dal giro dei vocabolari il tipo di file non ha attivo: un tipo c'e' o non c'e',
-- e nasce o si ritira con un changeSet. Non resta nessuna coppia ATTIVO.
SELECT hasnt_column('documenti', 'tipi_file_documento', 'attivo',
  '10) il tipo di file non ha un interruttore: la stampa non tiene acceso niente');

-- ============================================================
-- Il building block «rifiuta sempre»
-- ============================================================
CREATE TEMP TABLE _bb (id integer, cosa text, quando date) ON COMMIT DROP;
INSERT INTO _bb VALUES (1, 'FORZATURA', DATE '2026-11-15');

CREATE TRIGGER trg_bb_dlt BEFORE DELETE ON _bb
  FOR EACH ROW EXECUTE FUNCTION script.trgfn_prevent_modification_generic();
CREATE TRIGGER trg_bb_upd BEFORE UPDATE ON _bb
  FOR EACH ROW EXECUTE FUNCTION script.trgfn_prevent_modification_generic(
      'E_TITOLO_IVA_MOVIMENTO_IMMUTABILE', 'cosa', 'quando');
CREATE TRIGGER trg_bb_ins BEFORE INSERT ON _bb
  FOR EACH ROW EXECUTE FUNCTION script.trgfn_prevent_modification_generic(
      'E_TITOLO_IVA_MOVIMENTO_IMMUTABILE', 'colonna_che_non_esiste');

-- 11
SELECT is(
  dbops.fn_pgtap_codice_errore('DELETE FROM _bb'),
  'E_TABELLA_OP_NON_CONSENTITA',
  '11) senza argomenti: il codice di riserva');

-- 12
SELECT throws_like(
  'UPDATE _bb SET cosa = ''ALTRO''',
  '%Il movimento FORZATURA del 15/11/2026 non si puo''%',
  '12) col codice e le colonne: i valori della riga nella frase, la data in GG/MM/AAAA');

-- 13
SELECT is(
  dbops.fn_pgtap_codice_errore('INSERT INTO _bb VALUES (2, ''X'', NULL)'),
  'E_TRIGGER_ARGOMENTI_INVALIDI',
  '13) una colonna che la tabella non ha e'' un montaggio sbagliato');

-- 14: i montaggi, cercati per funzione, evento e codice (non per nome)
CREATE TEMP TABLE _attesi (tabella regclass, evento text, codice text) ON COMMIT DROP;
INSERT INTO _attesi VALUES
  ('documenti.documenti_generati',                'DELETE', 'E_DOCUMENTI_GENERATO_DELETE_BLOCKED'),
  ('documenti.documenti_generati_eventi',         'DELETE', 'E_EVENTO_DOCUMENTO_DELETE_VIETATA'),
  ('documenti.documenti_generati_eventi',         'UPDATE', 'E_EVENTO_DOCUMENTO_UPDATE_VIETATA'),
  ('documenti.documenti_generati_file',           'DELETE', 'E_FILE_DOCUMENTO_DELETE_VIETATA'),
  ('documenti.template_asset',                    'DELETE', 'E_DOCUMENTI_ASSET_DELETE_BLOCKED'),
  ('anagrafiche.soggetti_titoli_iva_movimenti',   'UPDATE', 'E_TITOLO_IVA_MOVIMENTO_IMMUTABILE'),
  ('anagrafiche.soggetti_titoli_iva_movimenti',   'DELETE', 'E_TITOLO_IVA_MOVIMENTO_IMMUTABILE');

SELECT is(
  (SELECT coalesce(string_agg(a.tabella::text || ' ' || a.evento, ', ' ORDER BY 1), '')
     FROM _attesi a
    WHERE NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_trigger t
         WHERE t.tgrelid = a.tabella
           AND t.tgfoid = 'script.trgfn_prevent_modification_generic'::regproc
           AND (t.tgtype & 2) <> 0                                         -- BEFORE
           AND (t.tgtype & CASE a.evento WHEN 'DELETE' THEN 8 ELSE 16 END) <> 0
           AND split_part(encode(t.tgargs, 'escape'), '\000', 1) = a.codice)),
  '',
  '14) i rifiuti di stampa, eventi, file, asset e movimenti IVA sono montati sul BB col loro codice');

-- 15
SELECT is(
  (SELECT count(*)::int FROM pg_catalog.pg_proc p
     JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname, p.proname) IN (
        ('documenti',   'trgfn_documenti_generati_block_delete'),
        ('documenti',   'trgfn_documenti_generati_eventi_block_delete'),
        ('documenti',   'trgfn_documenti_generati_eventi_block_update'),
        ('documenti',   'trgfn_template_asset_block_delete'),
        ('anagrafiche', 'trgfn_stiva_movimenti_append_only'))),
  0,
  '15) le cinque copie del «rifiuta sempre» sono ritirate');

SELECT * FROM finish();
ROLLBACK;
