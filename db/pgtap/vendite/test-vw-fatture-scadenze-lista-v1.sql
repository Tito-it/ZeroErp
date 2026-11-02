-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.vw_fatture_scadenze_lista — la vista d'identita' delle RATE
--       (changeSet 20260917-06, brief-db-distinta-ricerca-rate §4-bis.3, P-2)
--
-- ⭐ COSA PRESIDIA, in una riga: che la vista sia UNA RIGA PER RATA, non perda
--   rate e non ne aggiunga, e porti il documento coi nomi canonici — SENZA
--   saldi, che sono di pagamenti (il nucleo fn_get_saldi_rate).
--
-- Elenco test (plan 8):
-- 1) la vista esiste ed e' `security_invoker=on`
--    ⛔ La reloption NON sta nel corpo: un CREATE OR REPLACE che non la ripete
--    la AZZERA in silenzio, e la vista leggerebbe coi diritti del proprietario
--    — cioe' senza RLS, mostrando le rate di tutti gli emittenti.
-- 2) i nomi canonici ci sono tutti (l'insieme dei MANCANTI e' vuoto)
-- 3) nessun saldo nella vista: residuo/in_lavorazione/incassato NON sono colonne
-- 4) nessun FAN-OUT: una riga per ogni rata visibile, ne' una in piu' ne' una in meno
-- 5) due soli JOIN interni (fatture, nature_doc_fiscale): tutto il resto e' LEFT
-- 6) fixture: una rata su una BOZZA compare, con numero_documento NULL
-- 7) ...e la stessa rata, numerato il documento, porta «numero - serie» e il registro
-- 8) la vista non fa scope per conto suo: le rate sono esattamente quelle che
--    l'operatore vede su vendite.fatture_scadenze
--
-- ⚠️ COSA QUESTO FILE NON MISURA: il ramo in cui la testata NON e' visibile
--   mentre la rata lo e'. Non puo' darsi — la policy della rata e' lo STESSO
--   EXISTS sulla testata — ed e' la ragione per cui vendite.fatture e' INNER.
--   E il ramo del billing account invisibile con la rata visibile (LEFT), che
--   vorrebbe una fixture a due perimetri: un file a se'.
--
-- ⛔ LA FIXTURE SI COSTRUISCE, non si cerca (rev 2026-09-17 sera). La prima
--   stesura pescava «un billing account con emittente» fra i dati esistenti:
--   su un database ricostruito dai changelog (zeroerp_ci, la CI) le anagrafiche
--   sono a ZERO, la fixture usciva vuota e i test 6-7 confrontavano NULL —
--   ASSERZIONE, con la copertura che valeva zero. Ora: un'azienda col suo
--   operatore (dbops.fn_pgtap_crea_emittente_operatore) PRIMA del contesto, e
--   un cliente fatturabile (dbops.fn_pgtap_crea_cliente_ba) NEL contesto —
--   guida pgtap-come-si-scrive-un-test §«Il mondo si costruisce, non si cerca».
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- ⚠️ 2. CONTESTO APPLICATIVO: si gira come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- 1) security_invoker
-- ============================================================
SELECT is(
  (SELECT coalesce((SELECT string_agg(x, ',' ORDER BY x) FROM unnest(c.reloptions) x), 'ASSENTE')
     FROM pg_class c
     JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite' AND c.relname = 'vw_fatture_scadenze_lista'),
  'security_invoker=on',
  '1) vendite.vw_fatture_scadenze_lista e'' security_invoker=on: e'' la RLS di fatture_scadenze a mordere'
);

-- ============================================================
-- 2) I nomi canonici: si asserisce l'insieme dei MANCANTI, non il numero
-- ============================================================
SELECT is(
  (SELECT coalesce(string_agg(x, ', ' ORDER BY x), '')
     FROM unnest(ARRAY['scadenza_id','fattura_id','numero_rata','data_scadenza','importo',
                       'numero','numero_documento','serie','anno','data',
                       'registro_codice','registro_descrizione',
                       'natura_doc_codice_interno','natura_doc_descrizione',
                       'tipo_doc_fiscale_codice_interno','tipo_doc_fiscale_descrizione',
                       'stato_codice_interno','stato_descrizione',
                       'totale_doc','totale_a_pagare','valuta_codice',
                       'billing_account_id','ba_codice','soggetto_id',
                       'ragione_sociale_completa','id_fiscale_univoco_cf_piva',
                       'emittente_soggetto_ruolo_id','emittente_fiscale_id',
                       'emittente_fiscale_codice','emittente_ragione_sociale']) AS x
    WHERE NOT EXISTS (
      SELECT 1 FROM pg_attribute a
       WHERE a.attrelid = 'vendite.vw_fatture_scadenze_lista'::regclass
         AND a.attnum > 0 AND NOT a.attisdropped AND a.attname = x)),
  '',
  '2) i nomi canonici della rata, del documento, del cliente e dell''emittente ci sono tutti'
);

-- ============================================================
-- 3) Nessun saldo: il residuo e' di pagamenti, e vive nel nucleo
-- ============================================================
SELECT is(
  (SELECT coalesce(string_agg(a.attname, ', ' ORDER BY a.attname), '')
     FROM pg_attribute a
    WHERE a.attrelid = 'vendite.vw_fatture_scadenze_lista'::regclass
      AND a.attnum > 0 AND NOT a.attisdropped
      AND a.attname IN ('residuo', 'saldo', 'in_lavorazione', 'incassato', 'has_movimenti', 'scaduta', 'insoluta')),
  '',
  '3) nessun saldo e nessuna colonna derivata dal residuo: sono di pagamenti.fn_get_saldi_rate'
);

-- ============================================================
-- Fixture: una fattura in BOZZA con due rate, costruite
-- ============================================================
-- Il cliente fatturabile, nel contesto dell'operatore: il legame BA -> emittente
-- lo scrive il trigger z90 verso l'emittente di chi agisce.
CREATE TEMP TABLE tmp_cli_vsl AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('vw fatture scadenze lista') c;

CREATE TEMP TABLE tmp_refs_vsl AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_vsl)               AS billing_account_id,
  m.soggetto_ruolo_id                                        AS emittente_sr_id,
  script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id)      AS registro_id,
  config.fn_get_natura_doc_fiscale_id('FATTURA')             AS natura_fattura_id
FROM _mondo m;

CREATE TEMP TABLE tmp_fatt_vsl AS
WITH ins AS (
    INSERT INTO vendite.fatture
        (registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
         tasso_cambio, natura_doc_id, meta)
    SELECT r.registro_id, DATE '2026-09-17', r.emittente_sr_id, r.billing_account_id,
           1, r.natura_fattura_id,
           jsonb_build_object('test_scope', 'pgtap_vw_fatture_scadenze_lista')
      FROM tmp_refs_vsl r
    RETURNING id
)
SELECT id FROM ins;

-- Padre e figlie in DUE istruzioni: la policy della rata risolve il perimetro
-- dalla testata, e in una CTE sola non la vedrebbe. DUE rate, non una: con
-- l'azienda costruita il perimetro visibile e' questo documento, e un
-- conteggio 1 = 1 non distinguerebbe una vista fedele da un JOIN che
-- moltiplica per uno.
CREATE TEMP TABLE tmp_rata_vsl AS
WITH ins AS (
    INSERT INTO vendite.fatture_scadenze (fattura_id, numero_rata, data_scadenza, importo, meta)
    SELECT f.id, v.n, v.scadenza, v.importo,
           jsonb_build_object('test_scope', 'pgtap_vw_fatture_scadenze_lista')
      FROM tmp_fatt_vsl f
      CROSS JOIN (VALUES (1, DATE '2026-10-17', 123.45::numeric),
                         (2, DATE '2026-11-17',  76.55::numeric)) AS v(n, scadenza, importo)
    RETURNING id, numero_rata
)
SELECT id FROM ins WHERE numero_rata = 1;

-- ============================================================
-- 4) Nessun fan-out: una riga per rata visibile
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.vw_fatture_scadenze_lista),
  (SELECT count(*)::int FROM vendite.fatture_scadenze),
  '4) una riga di vista per ogni rata visibile (due costruite): nessun join moltiplica, nessuno toglie'
);

-- ============================================================
-- 5) La forma: due soli INNER (fatture, nature_doc_fiscale)
--    Si conta sul corpo: un INNER in piu' farebbe sparire rate in silenzio.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM regexp_matches(pg_get_viewdef('vendite.vw_fatture_scadenze_lista'::regclass, true),
                         '(?<!LEFT )JOIN ', 'g')),
  2,
  '5) due soli JOIN interni nel corpo (fatture e nature_doc_fiscale): il resto e'' LEFT'
);

-- ============================================================
-- 6-7) La rata sulla bozza, prima e dopo la numerazione
-- ============================================================
SELECT is(
  (SELECT (v.numero_documento IS NULL)::text || '|' ||
          (v.fattura_id = (SELECT id FROM tmp_fatt_vsl))::text || '|' ||
          (v.importo = 123.45)::text || '|' ||
          (v.ragione_sociale_completa IS NOT NULL)::text || '|' ||
          (v.emittente_fiscale_id IS NOT NULL)::text || '|' ||
          (v.natura_doc_codice_interno = 'FATTURA')::text
     FROM vendite.vw_fatture_scadenze_lista v
    WHERE v.scadenza_id = (SELECT id FROM tmp_rata_vsl)),
  'true|true|true|true|true|true',
  '6) la rata sulla bozza compare, con numero_documento NULL e cliente/emittente/natura risolti'
);

UPDATE vendite.fatture
   SET numero = 4243, serie = 'PG', anno = 2026
 WHERE id = (SELECT id FROM tmp_fatt_vsl);

SELECT is(
  (SELECT v.numero_documento || '|' || v.numero::text || '|' || coalesce(v.registro_codice, '<NULL>')
     FROM vendite.vw_fatture_scadenze_lista v
    WHERE v.scadenza_id = (SELECT id FROM tmp_rata_vsl)),
  (SELECT '4243 - PG|4243|' || r.codice
     FROM vendite.registri_fatturazione r
    WHERE r.id = (SELECT registro_id FROM tmp_refs_vsl)),
  '7) numerato il documento, la rata porta «numero - serie» dalla sede unica, il contatore e il registro'
);

-- ============================================================
-- 8) La vista non fa scope per conto suo (il patto delle sorelle)
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM (
     (SELECT id FROM vendite.fatture_scadenze
      EXCEPT
      SELECT scadenza_id FROM vendite.vw_fatture_scadenze_lista)
     UNION ALL
     (SELECT scadenza_id FROM vendite.vw_fatture_scadenze_lista
      EXCEPT
      SELECT id FROM vendite.fatture_scadenze)
   ) d),
  0,
  '8) le rate della vista sono esattamente quelle che l''operatore vede su fatture_scadenze'
);

SELECT * FROM finish();
ROLLBACK;
