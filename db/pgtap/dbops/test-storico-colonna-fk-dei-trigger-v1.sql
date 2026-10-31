-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test — il trigger di storico trova la colonna FK della gemella
--   script.trgfn_storico_generic · dbops.fn_run_automations_storico
--
-- Brief: brief-db-storico-colonna-fk-dei-trigger.md §5.3, §5.4
-- ChangeSet: 00_schema/storico/20260925-26 · 20_code/dbops/20260925-27
--
-- ⭐ L'INVARIANTE. trgfn_storico_generic riceve in TG_ARGV[0] il nome della
--   colonna che lega la riga storica alla madre, e nel ramo di chiusura fa
--   `UPDATE storico.<tab> … WHERE <TG_ARGV[0]> = <id>`. Se la colonna non c'e',
--   ogni UPDATE/DELETE di una riga storicizzata della madre muore con
--   E_SNAPSHOT_CLOSE_ERROR. Fino al 2026-09-25 cinque madri erano cosi', e
--   nessun test lo vedeva: nessuno modificava una loro riga storicizzata.
--
-- ⭐ DUE DOMANDE DIVERSE DAL RUBINETTO. Il 20260925-27 ferma un trigger rotto
--   mentre NASCE. Questo file guarda i trigger che CI SONO, compresi quelli nati
--   prima del rubinetto e le gemelle ricreate a mano (su dbdev storico.parameters
--   era stata droppata e ricreata dal provisioning).
--
-- ⚠️ Gira dopo ci_apply, quando i trigger esistono: il test 1 pretende che ce
--   ne sia almeno uno, perche' il 2 su zero trigger sarebbe verde a vuoto.
--
-- ⚠️ Gira come l'applicazione (runner di default): i test 1-12 leggono solo il
--   catalogo; i 13-16 scrivono su config.parameters, che l'app scrive dal
--   pannello di amministrazione, ed e' ESATTAMENTE il percorso che moriva.
--
-- Elenco test (plan 16):
--   INVARIANTE — su tutti i trigger di storico
--    1  : gemello «esiste»: ci sono trigger su trgfn_storico_generic
--    2  : ogni argomento e' una colonna della gemella storico.<tabella>
--   LE CINQUE GEMELLE DEL 2025 — il nome vecchio non c'e' piu'
--    3-7 : has_column del nome dell'automazione (<tabella>_id)
--    8-12: hasnt_column del nome al singolare (se restassero ENTRAMBE, il
--          test 2 sarebbe verde e due colonne direbbero la stessa cosa)
--   COMPORTAMENTO — config.parameters, riga costruita con storicizza = true
--   13  : UPDATE della madre: vive (moriva con E_SNAPSHOT_CLOSE_ERROR)
--   14  : lo snapshot e' nella gemella, legato per parameters_id
--   15  : DELETE della madre: vive
--   16  : lo snapshot del DELETE e' nella gemella
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- INVARIANTE
-- ============================================================
CREATE TEMP TABLE tmp_trg_storico ON COMMIT DROP AS
SELECT n.nspname AS madre_schema,
       c.relname AS madre_tab,
       t.tgname,
       split_part(encode(t.tgargs, 'escape'), E'\\000', 1) AS fk_col
  FROM pg_trigger t
  JOIN pg_class c     ON c.oid = t.tgrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  JOIN pg_proc p      ON p.oid = t.tgfoid
 WHERE NOT t.tgisinternal
   AND p.proname = 'trgfn_storico_generic'
   AND p.pronamespace = 'script'::regnamespace;

-- 1
SELECT ok(
  (SELECT count(*) FROM tmp_trg_storico) > 0,
  'Gemello: esistono trigger montati su script.trgfn_storico_generic (il test 2 non e'' a vuoto)'
);

-- 2
SELECT is_empty(
  $$
  SELECT s.madre_schema || '.' || s.madre_tab || ' → storico.' || s.madre_tab || '.' || s.fk_col
    FROM tmp_trg_storico s
   WHERE NOT EXISTS (
           SELECT 1
             FROM pg_attribute a
             JOIN pg_class g     ON g.oid = a.attrelid
             JOIN pg_namespace gn ON gn.oid = g.relnamespace
            WHERE gn.nspname = 'storico'
              AND g.relname  = s.madre_tab
              AND a.attname  = s.fk_col
              AND a.attnum   > 0
              AND NOT a.attisdropped)
   ORDER BY 1
  $$,
  'Ogni trigger di storico cerca una colonna che la gemella ha davvero (il nome mancante e'' nel dettaglio)'
);

-- ============================================================
-- LE CINQUE GEMELLE DEL 2025
-- ============================================================
-- 3-7
SELECT has_column('storico', 'parameters',                'parameters_id',                'storico.parameters ha parameters_id');
SELECT has_column('storico', 'comuni',                    'comuni_id',                    'storico.comuni ha comuni_id');
SELECT has_column('storico', 'indirizzi',                 'indirizzi_id',                 'storico.indirizzi ha indirizzi_id');
SELECT has_column('storico', 'indirizzi_dettaglio',       'indirizzi_dettaglio_id',       'storico.indirizzi_dettaglio ha indirizzi_dettaglio_id');
SELECT has_column('storico', 'catasto_unita_immobiliari', 'catasto_unita_immobiliari_id', 'storico.catasto_unita_immobiliari ha catasto_unita_immobiliari_id');

-- 8-12
SELECT hasnt_column('storico', 'parameters',                'parameter_id',                 'storico.parameters non ha piu'' parameter_id');
SELECT hasnt_column('storico', 'comuni',                    'comune_id',                    'storico.comuni non ha piu'' comune_id');
SELECT hasnt_column('storico', 'indirizzi',                 'indirizzo_id',                 'storico.indirizzi non ha piu'' indirizzo_id');
SELECT hasnt_column('storico', 'indirizzi_dettaglio',       'indirizzo_dettaglio_id',       'storico.indirizzi_dettaglio non ha piu'' indirizzo_dettaglio_id');
SELECT hasnt_column('storico', 'catasto_unita_immobiliari', 'catasto_unita_immobiliare_id', 'storico.catasto_unita_immobiliari non ha piu'' catasto_unita_immobiliare_id');

-- ============================================================
-- COMPORTAMENTO — config.parameters
-- ============================================================
-- ⚠️ Le righe si COSTRUISCONO, con storicizza = true: pescare un parametro
--   esistente farebbe dipendere il test da quanti sono storicizzati oggi (su
--   dbdev 20, sullo scratch 45 il 2026-09-25 — e nessuno dei due numeri conta).
-- ⚠️ Due righe e non una: dopo il primo UPDATE il trigger puo' riportare
--   storicizza a false (reset, se la tabella non e' in config.storico_set_storicizza),
--   e il DELETE della stessa riga non passerebbe piu' dal ramo che si prova.
-- ⚠️ config.parameters.id non ha default: la chiave si genera larga, lontana
--   da quelle a catalogo.
CREATE TEMP TABLE tmp_par ON COMMIT DROP AS
SELECT (SELECT COALESCE(max(id), 0) FROM config.parameters) + 1000000 AS id_upd,
       (SELECT COALESCE(max(id), 0) FROM config.parameters) + 1000001 AS id_dlt;

-- 2026-10-25 (brief-db-parametri-senza-override): config.parameters.ammette_override
-- e' NOT NULL senza DEFAULT, un parametro dichiara la sua famiglia.
INSERT INTO config.parameters (id, code, default_value, description, storicizza, ammette_override, tipo_valore)
SELECT id_upd, 'PGTAP_STORICO_FK_UPD', '1', 'pgTAP test-storico-colonna-fk-dei-trigger', true, true, 'TESTO' FROM tmp_par;

INSERT INTO config.parameters (id, code, default_value, description, storicizza, ammette_override, tipo_valore)
SELECT id_dlt, 'PGTAP_STORICO_FK_DLT', '1', 'pgTAP test-storico-colonna-fk-dei-trigger', true, true, 'TESTO' FROM tmp_par;

-- 13
SELECT lives_ok(
  $$ UPDATE config.parameters SET default_value = '2'
      WHERE id = (SELECT id_upd FROM tmp_par) $$,
  'UPDATE di un parametro storicizzato: vive (il ramo di chiusura trova la colonna)'
);

-- 14
SELECT ok(
  EXISTS (SELECT 1 FROM storico.parameters
           WHERE parameters_id = (SELECT id_upd FROM tmp_par)),
  'L''UPDATE ha scritto lo snapshot nella gemella, legato per parameters_id'
);

-- 15
SELECT lives_ok(
  $$ DELETE FROM config.parameters
      WHERE id = (SELECT id_dlt FROM tmp_par) $$,
  'DELETE di un parametro storicizzato: vive'
);

-- 16
SELECT ok(
  EXISTS (SELECT 1 FROM storico.parameters
           WHERE parameters_id = (SELECT id_dlt FROM tmp_par)),
  'Il DELETE ha scritto lo snapshot nella gemella, legato per parameters_id'
);

SELECT * FROM finish();

ROLLBACK;
