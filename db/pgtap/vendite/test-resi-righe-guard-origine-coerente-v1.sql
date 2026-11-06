-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; la bolla nasce in DRAFT perche' il test le aggiunge la riga a mano (il caso: la spedizione mista), poi CONSEGNATA con dbops.fn_pgtap_porta_a_stato; restano scritti a mano il reso e le sue righe (il caso del test, e giro 2).
-- pgTAP test per Zero ERP
-- Test: vendite.trgfn_resi_righe_guard_origine_coerente — il riferimento
--       all'ordine sul reso deve combaciare con la riga di merce resa.
--       (brief-design-partita-merce-generalizzata §8.5, slice S6a,
--        changeSet 20260817-13)
--
-- Elenco test (plan 6):
--   1) la funzione guard esiste
--   2) il trigger e' agganciato in fase _a20_ su resi_righe
--   3) merce ORDINATA + riferimento a una riga d'ordine SBAGLIATA -> P0001
--   4) merce ORDINATA + riferimento VUOTO -> P0001
--   5) merce SENZA ordine + riferimento valorizzato -> P0001
--   6) il caso corretto passa (il guard non blocca cio' che va bene)
--
-- Scopo:
--  - `resi_righe.ordine_riga_id` e' una denormalizzazione ricavabile dal
--    fulfillment, e la legge `fn_ordine_riga_qta_riconsegna` per riaprire il
--    residuo dell'ordine. Sbagliata o vuota, la merce torna indietro e
--    l'ordine non se ne accorge.
--  - I test 3-4-5 sono le TRE facce dello stesso errore, e servono tutte:
--    presidiare solo il valore sbagliato lascerebbe passare il vuoto, che e'
--    il caso piu' probabile perche' non richiede di sbagliare nulla — basta
--    non compilare.
--
-- ⚠️ Lo SQLSTATE nei `throws_ok` NON e' pedanteria. Scrivendo questo guard il
--    primo tentativo bloccava con `42883 la funzione non esiste` — mancava
--    l'argomento VARIADIC di `fn_log_and_raise_error` — cioe' il guard
--    falliva per una ragione che non c'entrava nulla col dominio. Un
--    `throws_ok` senza discriminante avrebbe dato quel rosso per verde.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE. Senza, un fallimento a meta' lascia i dati di prova nel
--   database e rompe la corsa successiva, che vede un rosso non suo.
BEGIN;

-- ⚠️ 2. VINCOLI DIFFERITI. Scattano al COMMIT, e qui il COMMIT non arriva mai:
--   senza questa riga il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- ⚠️ 3. CONTESTO APPLICATIVO. Il test gira come `zeroerp_app` con la RLS attiva.
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (in CI l'utente 1 non esiste;
--   anagrafiche e articoli sono vuoti). Prima il mondo — azienda, operatore,
--   cliente legato a quell'azienda — poi il contesto, sul SUO operatore.
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP guard origine coerente');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

SELECT plan(6);

-- ============================================================
-- 1-2) Il guard esiste ed e' agganciato dove deve
-- ============================================================
SELECT has_function('vendite', 'trgfn_resi_righe_guard_origine_coerente',
  '1) la funzione guard esiste');

SELECT ok(
  (SELECT COUNT(*) = 1 FROM pg_trigger t
     JOIN pg_class c ON c.oid = t.tgrelid
     JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite' AND c.relname = 'resi_righe'
      AND t.tgname = 'trg_resi_righe_a20_guard_origine_coerente_ins_upd'
      AND NOT t.tgisinternal),
  '2) il trigger e'' agganciato in fase _a20_ su resi_righe');

-- ============================================================
-- Fixture: due righe di merce sullo STESSO DDT — una che evade l'ordine,
-- una aggiunta a mano. E' la spedizione mista, cioe' il documento su cui il
-- riferimento all'ordine si puo' sbagliare in tutti e tre i modi.
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-13: cliente ed emittente dal mondo costruito, non il primo BA
  --   del database; l'articolo si costruisce (nasce merce, non solo componente:
  --   ordine e bolla lo ammettono — brief-db-articoli-ammessi-per-documento, Lotto 3a).
  (SELECT billing_account_id FROM _m)                                    AS billing_account_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-RESI-ORIGINE', false)             AS articolo_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo LIMIT 1)     AS sorgente_ddt_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo LIMIT 1)     AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_A_CREDITO' AND t.attivo LIMIT 1) AS tipo_credito_id;

-- La bolla dal builder, in DRAFT: ordine di 10 a 25, trigger SPEDITO, del
--   cliente del mondo, confermato, bolla generata. Resta in bozza perche' il
--   test le aggiunge la riga a mano.
CREATE TEMP TABLE tmp_doc AS
SELECT b.ordine_id, b.ordine_riga_id, b.ddt_id, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('guard origine coerente', 'DRAFT',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs),
           p_quantita             => 10,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs),
           p_fatturazione_trigger => 'SPEDITO') b;

-- La riga che evade l'ordine (ha un fulfillment) e quella aggiunta a mano.
-- ⚠️ La riga a mano entra PRIMA delle transizioni (rev 2026-09-22): il BB
--   trgfn_doc_righe_lock_fuori_bozza non ammette righe in un DDT fuori bozza.
-- ⚠️ In due passi e non in uno: un `INSERT ... RETURNING` non sta dentro una
-- sottoquery scalare, va incapsulato in una CTE che modifica i dati.
CREATE TEMP TABLE tmp_righe AS
SELECT d.ddt_riga_id AS riga_ordinata, NULL::bigint AS riga_manuale
  FROM tmp_doc d;

WITH m AS (
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  SELECT (SELECT ddt_id FROM tmp_doc), 900, r.articolo_id, 'Riga a mano', 4, 4, 25,
         r.iva_id, true, false, jsonb_build_object('test_scope','pgtap_guard_origine')
  FROM tmp_refs r RETURNING id
)
UPDATE tmp_righe SET riga_manuale = (SELECT id FROM m);

-- Poi il DDT si consegna, nel verso vero: per la matrice.
DO $x$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM tmp_doc), 'CONSEGNATO'); END $x$;

-- La testata di reso su cui si tenteranno gli inserimenti.
CREATE TEMP TABLE tmp_reso AS
WITH t AS (
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_id, storicizza, meta)
  SELECT r.stato_reso_draft_id, r.sorgente_ddt_id,
         (SELECT ddt_id FROM tmp_doc),
         false, jsonb_build_object('test_scope','pgtap_guard_origine')
  FROM tmp_refs r RETURNING id
)
SELECT id FROM t;

-- ============================================================
-- 3-5) Le tre facce dello stesso errore
-- ============================================================
SELECT throws_ok(
  format($f$INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
              articolo_id, descrizione, qta_operativa, tipo_reso_id, storicizza)
            VALUES (%s, 1, %s, 999999999, '%s', 'x', 2, %s, false)$f$,
    (SELECT id FROM tmp_reso), (SELECT riga_ordinata FROM tmp_righe),
    (SELECT articolo_id FROM tmp_refs), (SELECT tipo_credito_id FROM tmp_refs)),
  'P0001', NULL,
  '3) merce ordinata + riga d''ordine SBAGLIATA -> errore di dominio');

SELECT throws_ok(
  format($f$INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
              articolo_id, descrizione, qta_operativa, tipo_reso_id, storicizza)
            VALUES (%s, 2, %s, NULL, '%s', 'x', 2, %s, false)$f$,
    (SELECT id FROM tmp_reso), (SELECT riga_ordinata FROM tmp_righe),
    (SELECT articolo_id FROM tmp_refs), (SELECT tipo_credito_id FROM tmp_refs)),
  'P0001', NULL,
  '4) merce ordinata + riferimento VUOTO -> errore di dominio (il caso piu'' probabile)');

SELECT throws_ok(
  format($f$INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
              articolo_id, descrizione, qta_operativa, tipo_reso_id, storicizza)
            VALUES (%s, 3, %s, %s, '%s', 'x', 2, %s, false)$f$,
    (SELECT id FROM tmp_reso), (SELECT riga_manuale FROM tmp_righe),
    (SELECT ordine_riga_id FROM tmp_doc),
    (SELECT articolo_id FROM tmp_refs), (SELECT tipo_credito_id FROM tmp_refs)),
  'P0001', NULL,
  '5) merce SENZA ordine + riferimento valorizzato -> errore di dominio');

-- ============================================================
-- 6) E il caso corretto passa. Un guard che blocca tutto non e' un guard.
-- ============================================================
SELECT lives_ok(
  format($f$INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
              articolo_id, descrizione, qta_operativa, tipo_reso_id, storicizza)
            VALUES (%s, 4, %s, %s, '%s', 'x', 2, %s, false)$f$,
    (SELECT id FROM tmp_reso), (SELECT riga_ordinata FROM tmp_righe),
    (SELECT ordine_riga_id FROM tmp_doc),
    (SELECT articolo_id FROM tmp_refs), (SELECT tipo_credito_id FROM tmp_refs)),
  '6) riferimento corretto: il guard lascia passare');

SELECT * FROM finish();
ROLLBACK;
