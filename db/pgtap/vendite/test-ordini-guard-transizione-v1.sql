-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.trgfn_ordini_guard_transizione (+ trigger)
-- ------------------------------------------------------------
-- Brief: docs/it/dev/work-in-progress/brief-ordini-azioni-data-driven.md
-- Enforcement DB-first del grafo transizioni stato ordine letto da
-- config.transizioni_stati_ordini.
-- Indice test (1..6):
-- 1) trg_ordini_a10_guard_transizione_upd esiste
-- 2) DRAFT->CONFERMATO con riga -> ok (lives)
-- 3) DRAFT->CONFERMATO senza righe -> throws E_ORDINE_CONFERMA_SENZA_RIGHE
-- 4) DRAFT->ANNULLATO -> ok (transizione manuale attiva)
-- 5) DRAFT->SPEDITO (fuori matrice) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA
-- 6) CONFERMATO->ANNULLATO senza figli a valle -> ok (lives)
-- 7) CONFERMATO->ANNULLATO con l'ordine gia' in commessa -> throws
-- 8) ...e il CODICE di dominio esce nel campo strutturato CONSTRAINT
--    (gruppo C: il codice arriva da `v_motivi -> 0 ->> 'codice'`, non da un
--     letterale — vedi brief-db-codice-errore-strutturato §2)
--
-- rev 2026-08-04: il caso 6 fissava la transizione come DISATTIVA
-- (attivo=false) e si aspettava E_ORDINE_TRANSIZIONE_NON_AMMESSA. Quella
-- disattivazione lasciava un ordine confermato senza NESSUNA via d'uscita
-- azionabile da una persona: decisione di Tid, si riattiva con tutti i
-- controlli che devono impedirla. Il test segue la decisione nuova e diventa
-- piu' forte: non basta che l'annullamento sia ammesso, deve essere ammesso
-- SOLO quando non c'e' gia' qualcosa a valle.
-- Brief: docs/it/dev/work-in-progress/brief-db-vie-uscita-operatore.md
-- ------------------------------------------------------------

-- Nota emittente: gli ordini passano emittente_fiscale_id esplicito e
--   billing_account_id=NULL (GUC vuota in pgTAP); cosi' bypassano sia
--   trgfn_ordini_default_emittente sia il guard di coerenza BA. Le transizioni
--   di stato testate non dipendono dal billing_account.

BEGIN;
SELECT plan(8);

-- Contesto non-API: GUC vuota.
SELECT set_config('app.current_user_id', '', true);

-- ============================================================
-- Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_gt AS
SELECT
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE ORDER BY ef.id LIMIT 1
  ) AS emittente_fiscale_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1
  ) AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a WHERE a.attivo IS TRUE
    ORDER BY a.data_insert DESC NULLS LAST, a.id LIMIT 1
  ) AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'DRAFT'      LIMIT 1) AS stato_draft_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'CONFERMATO' LIMIT 1) AS stato_conf_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'ANNULLATO'  LIMIT 1) AS stato_ann_id,
  (SELECT id FROM config.stati_doc_ordini WHERE codice_interno = 'SPEDITO'    LIMIT 1) AS stato_sped_id;

-- Helper: crea ordine DRAFT e ritorna id. Slot via meta.
-- Slot A: DRAFT con riga (test 2)
CREATE TEMP TABLE tmp_gt_a AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"A"}'::jsonb
  FROM tmp_refs_gt r RETURNING id
) SELECT id FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga A', 3.0, 3.0, 10.0, true, false, '{}'::jsonb
FROM tmp_gt_a o, tmp_refs_gt r;

-- Slot B: DRAFT senza righe (test 3)
CREATE TEMP TABLE tmp_gt_b AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"B"}'::jsonb
  FROM tmp_refs_gt r RETURNING id
) SELECT id FROM ins;

-- Slot C: DRAFT con riga (test 4 annulla)
CREATE TEMP TABLE tmp_gt_c AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"C"}'::jsonb
  FROM tmp_refs_gt r RETURNING id
) SELECT id FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga C', 3.0, 3.0, 10.0, true, false, '{}'::jsonb
FROM tmp_gt_c o, tmp_refs_gt r;

-- Slot D: DRAFT con riga (test 5 transizione fuori matrice)
CREATE TEMP TABLE tmp_gt_d AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,r.stato_draft_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"D"}'::jsonb
  FROM tmp_refs_gt r RETURNING id
) SELECT id FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga D', 3.0, 3.0, 10.0, true, false, '{}'::jsonb
FROM tmp_gt_d o, tmp_refs_gt r;

-- Slot E: CONFERMATO con riga (test 6 CONFERMATO->ANNULLATO disabilitata)
CREATE TEMP TABLE tmp_gt_e AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id,r.stato_conf_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"E"}'::jsonb
  FROM tmp_refs_gt r RETURNING id
) SELECT id FROM ins;
INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, attivo, storicizza, meta)
SELECT o.id, 1, r.articolo_id, 'riga E', 3.0, 3.0, 10.0, true, false, '{}'::jsonb
FROM tmp_gt_e o, tmp_refs_gt r;

-- ============================================================
-- 1) trigger esiste
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_trigger
     WHERE tgname = 'trg_ordini_a10_guard_transizione_upd'
       AND NOT tgisinternal
  ),
  '1) trg_ordini_a10_guard_transizione_upd esiste'
);

-- ============================================================
-- 2) DRAFT->CONFERMATO con riga -> ok
-- ============================================================
SELECT lives_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_conf_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_a)),
  '2) DRAFT->CONFERMATO con riga -> ok'
);

-- ============================================================
-- 3) DRAFT->CONFERMATO senza righe -> throws E_ORDINE_CONFERMA_SENZA_RIGHE
-- ============================================================
SELECT throws_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_conf_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_b)),
  'P0001', NULL,
  '3) DRAFT->CONFERMATO senza righe -> throws E_ORDINE_CONFERMA_SENZA_RIGHE'
);

-- ============================================================
-- 4) DRAFT->ANNULLATO -> ok
-- ============================================================
SELECT lives_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_ann_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_c)),
  '4) DRAFT->ANNULLATO -> ok (transizione manuale attiva)'
);

-- ============================================================
-- 5) DRAFT->SPEDITO (fuori matrice) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA
-- ============================================================
SELECT throws_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_sped_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_d)),
  'P0001', NULL,
  '5) DRAFT->SPEDITO (fuori matrice) -> throws E_ORDINE_TRANSIZIONE_NON_AMMESSA'
);

-- ============================================================
-- 6) CONFERMATO->ANNULLATO senza figli a valle -> ok
--    L'ordine di fixture non ha DDT ne' commesse collegate:
--    script.fn_check_ordine_annullabile ritorna [] e il guard lascia passare.
-- ============================================================
SELECT lives_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_ann_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_e)),
  '6) CONFERMATO->ANNULLATO senza figli a valle -> ammesso'
);

-- ============================================================
-- 7) CONFERMATO->ANNULLATO con l'ordine gia' inviato a fatturazione -> throws
--    Un secondo ordine confermato, questa volta agganciato a una commessa:
--    il guard legge la stessa funzione pura del bottone e rifiuta.
-- ============================================================
CREATE TEMP TABLE tmp_gt_f AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, meta)
  SELECT r.soggetto_ruolo_id, NULL::bigint, r.emittente_fiscale_id, r.stato_conf_id, r.valuta_id,
         DATE '2026-06-15', false, '{"test_scope":"pgtap_guard_transizione","slot":"F"}'::jsonb
  FROM tmp_refs_gt r RETURNING id
) SELECT id FROM ins;

INSERT INTO vendite.commesse (codice, billing_account_id, utility_id, stato_commessa_id)
SELECT 'PGTAP-GT-COM', c.billing_account_id, c.utility_id, c.stato_commessa_id
  FROM vendite.commesse c LIMIT 1;

INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
SELECT (SELECT id FROM vendite.commesse WHERE codice = 'PGTAP-GT-COM'),
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA'),
       (SELECT id FROM tmp_gt_f)::text,
       'ROOT';

SELECT throws_ok(
  format($q$UPDATE vendite.ordini SET stato_doc_ordine_id =
              (SELECT stato_ann_id FROM tmp_refs_gt) WHERE id = %s$q$,
         (SELECT id FROM tmp_gt_f)),
  'P0001', NULL,
  '7) CONFERMATO->ANNULLATO con ordine gia'' in commessa -> rifiutato dal guard'
);

-- ============================================================
-- 8) Il codice di dominio esce nel campo strutturato CONSTRAINT
--    Migration 20260805-05 · brief-db-codice-errore-strutturato §6
--
--    ⚠️ PERCHE' QUI E NON SOLO SULL'HELPER. Questo e' uno dei nove call site
--    del "gruppo C": il codice non e' un letterale nella chiamata, arriva da
--    `v_motivi -> 0 ->> 'codice'`. Ed e' esattamente il caso che il vecchio
--    meccanismo NON copriva: il backend pescava il codice con una regex dal
--    testo dell'eccezione, dove pero' il driver riporta lo statement chiamante
--    — e li' c'era scritto il NOME DELLA VARIABILE, non il suo valore. Il
--    ripiego era E_DATABASE, classificato tecnico: messaggio localizzato
--    scartato e dettaglio soppresso. Chi provava ad annullare un ordine gia'
--    in commessa non leggeva perche' non si poteva.
--
--    Un test sul solo `script.fn_log_and_raise_error` (che pure esiste, in
--    test-fn-log-and-raise-error-constraint-codice.sql) non basterebbe a
--    coprire questo: li' il codice si sa gia' quando si chiama. Qui il
--    percorso e' quello vero, UPDATE -> trigger -> guard -> funzione pura ->
--    helper, e il codice lo decide il DB.
--
--    Il test 7 usa throws_ok, che vede solo SQLSTATE e messaggio: i campi
--    diagnostici richiedono un blocco EXCEPTION con GET STACKED DIAGNOSTICS.
--    Lo stesso UPDATE si puo' rieseguire perche' il fallimento del 7 ha
--    annullato solo il proprio statement, non la transazione del test.
-- ============================================================
CREATE FUNCTION pg_temp.capture_annulla(p_ordine_id bigint)
RETURNS TABLE(v_sqlstate text, v_constraint text)
LANGUAGE plpgsql
AS $fn$
BEGIN
    BEGIN
        UPDATE vendite.ordini
           SET stato_doc_ordine_id = (SELECT stato_ann_id FROM tmp_refs_gt)
         WHERE id = p_ordine_id;
        v_sqlstate := NULL; v_constraint := NULL;
        RETURN NEXT;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS
            v_sqlstate   = RETURNED_SQLSTATE,
            v_constraint = CONSTRAINT_NAME;
        RETURN NEXT;
    END;
END;
$fn$;

SELECT is(
  (SELECT ROW(v_sqlstate, v_constraint)::text
     FROM pg_temp.capture_annulla((SELECT id FROM tmp_gt_f))),
  ROW('P0001', 'E_ORD_ANNULLA_IN_COMMESSA')::text,
  '8) il codice di dominio (da v_motivi, non da letterale) esce nel campo CONSTRAINT'
);

SELECT * FROM finish();
ROLLBACK;
