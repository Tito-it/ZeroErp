-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: la riga di preventivo a natura NULL (pregresso) si costruisce solo dalla porta di manutenzione del lock, che si apre solo alla sessione del migratore (script.fn_porta_manutenzione_aperta)
-- pgTAP test per Zero ERP
--
-- Test: la riga di preventivo LEGACY, a natura di vendita NULL, e come la
--   leggono il push su commessa e le viste di smistamento.
--   Brief: brief-db-seed-primo-impianto-non-si-riscrive (§16.13, Q21)
--
-- ⭐ Perche' un file a parte, e su owner. La natura NULL e' uno stato REALE
--   (le righe nate prima del trigger di ereditarieta'), ma oggi nessun percorso
--   la produce: `catalogo.articoli.natura_vendita_id` e' NOT NULL e
--   `preventivi_righe.natura_vendita_id` e' sotto lock di colonna
--   (E_RIGA_NATURA_VENDITA_IMMUTABILE). Si costruisce solo dalla porta
--   zeroerp.allow_lock_columns_override, e dal giro 20261117-07 la porta si
--   apre solo alla sessione del migratore: l'app che accende la GUC trova il
--   lucchetto chiuso (lo prova test-seed-primo-impianto-installazione-v1).
--   Qui stanno SOLO i casi che hanno bisogno di quella riga; il resto dei tre
--   file da cui vengono resta come app, e continua a provare la RLS:
--     test-fn-list-preventivi-da-pushare-natura-aware-v1 (era il caso 3),
--     test-vw-preventivi-smistamento-v1 (era il caso 5, e il pregresso nei
--       contatori 1, 7, 8),
--     test-righe-natura-vendita-congelata-v1 (era il caso 15).
--   ⚠️ Da owner la RLS non si esercita: questo file non prova il perimetro.
--
-- Elenco test (plan 5):
--   1) dalla porta del lock la natura si scrive NULL: il BB della natura non la
--      rimette a OLD (20261013-14)
--   2) … e il passaggio sta nel diario delle porte
--   3) il push su commessa include la riga a natura NULL (pregresso = COMMESSA)
--   4) vista righe: destinazione COMMESSA, natura NULL, RESIDUA
--   5) aggregata: la riga a natura NULL conta fra i servizi e fra le residue
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: in ROLLBACK il COMMIT non arriva mai, IMMEDIATE li fa
--   scattare a fine istruzione. Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Il contesto dell'operatore serve ai builder (l'azienda di chi agisce), non
-- alla RLS: da owner la RLS non si applica.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- ============================================================
-- Fixture: preventivo in bozza, una riga servizio e una riga legacy
-- ============================================================
-- ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE _b AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('pgTAP natura legacy');

CREATE TEMP TABLE _refs AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-NATL-SERV', false,
           p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                                    WHERE codice_interno = 'SERVIZIO_UNA_TANTUM')) AS art_serv_id,
       (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id;

CREATE TEMP TABLE _riga_serv AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT b.preventivo_id, r.art_serv_id, 3.000000, 10.000000, r.iva_id, true
    FROM _b b, _refs r
  RETURNING id)
SELECT * FROM ins;

-- La riga legacy nasce servizio, poi la porta le toglie la natura.
CREATE TEMP TABLE _riga_null AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario, iva_id, attivo)
  SELECT b.preventivo_id, r.art_serv_id, 1.000000, 15.000000, r.iva_id, true
    FROM _b b, _refs r
  RETURNING id)
SELECT * FROM ins;

-- La porta si RICHIUDE subito: aperta, renderebbe verdi per sottrazione le
-- asserzioni che toccano colonne sotto lock.
SET LOCAL zeroerp.allow_lock_columns_override = 'on';
UPDATE vendite.preventivi_righe SET natura_vendita_id = NULL
 WHERE id = (SELECT id FROM _riga_null);
SET LOCAL zeroerp.allow_lock_columns_override = 'off';

-- ============================================================
-- 1-2 La porta del migratore
-- ============================================================
SELECT is(
  (SELECT natura_vendita_id FROM vendite.preventivi_righe WHERE id = (SELECT id FROM _riga_null)),
  NULL::bigint,
  '1) dalla porta del lock la natura si scrive NULL (il BB non la rimette a OLD)');

SELECT is(
  (SELECT count(*)::int FROM dbops.porte_manutenzione_passaggi p
    WHERE p.chiave = 'zeroerp.allow_lock_columns_override'
      AND p.schema_name = 'vendite' AND p.table_name = 'preventivi_righe'
      AND p.riga_id = (SELECT id::text FROM _riga_null)
      AND p.operazione = 'UPDATE'),
  1,
  '2) … e il passaggio sta nel diario delle porte');

-- Fuori bozza le righe non si scrivono piu' (20261008-91): si accetta dopo.
DO $porta$ BEGIN PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT preventivo_id FROM _b), 'ACCETTATO'); END $porta$;

-- ============================================================
-- 3-5 Come la leggono il push e le viste
-- ============================================================
SELECT ok(
  EXISTS(SELECT 1 FROM vendite.fn_list_preventivi_da_pushare(NULL, NULL, NULL, (SELECT preventivo_id FROM _b)) f
          WHERE f.riga_id = (SELECT id FROM _riga_null)),
  '3) push su commessa: la riga a natura NULL e'' inclusa (pregresso = COMMESSA)');

SELECT ok(
  (SELECT v.destinazione_tipo = 'COMMESSA'
      AND v.natura_vendita_id IS NULL
      AND v.stato_smistamento = 'RESIDUA'
     FROM vendite.vw_preventivi_smistamento_righe v
    WHERE v.riga_id = (SELECT id FROM _riga_null)),
  '4) vista righe: destinazione effettiva COMMESSA, natura NULL, RESIDUA');

SELECT is(
  (SELECT format('%s|%s|%s|%s', a.righe_totali, a.righe_merce, a.righe_servizi, a.righe_residue)
     FROM vendite.vw_preventivi_smistamento a
    WHERE a.preventivo_id = (SELECT preventivo_id FROM _b)),
  '2|0|2|2',
  '5) aggregata: la riga a natura NULL conta fra i servizi e fra le residue (totali|merce|servizi|residue)');

SELECT * FROM finish();
ROLLBACK;
