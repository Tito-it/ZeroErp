-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d/2e): chiavi del push e ambito degli indirizzi col codice della sorgente.
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato (prima il
--   preventivo del test 9 nasceva gia' ACCETTATO).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): i quattro
--   preventivi vengono da dbops.fn_pgtap_crea_preventivo (cliente, emittente e
--   testata costruiti, numero dal dominio) e l'articolo da
--   dbops.fn_pgtap_crea_articolo; l'operatore e' quello del contesto. Prima si
--   pescavano il primo billing account, il primo emittente, l'articolo piu'
--   recente e il primo utente di config.user_emittenti_fiscali: su un database
--   ricostruito non ci sono.
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): il preventivo
--   ACCETTATO del test 9 viene da dbops.fn_pgtap_crea_preventivo_con_righe. Lo
--   stato ora passa dal verbo sotto la porta, e l'emissione (DRAFT -> EMESSO,
--   sulla strada verso ACCETTATO) chiede almeno una riga attiva: senza righe
--   la fixture si fermava su E_PREV_NESSUNA_RIGA_ATTIVA. L'attesa non cambia.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_crea_revisione_preventivo
-- ------------------------------------------------------------
-- Indice test (1..9):
-- 1) Funzione presente
-- 2) Riferimenti minimi disponibili
-- 3) Setup preventivo EMESSO con righe e indirizzi
-- 4) Revisione da EMESSO ammessa: nuova rev in DRAFT
-- 5) Revisione copia righe attive
-- 6) Revisione copia indirizzi
-- 7) Revisione disattiva precedente (vw_preventivi.is_attiva = false)
-- 8) Revisione da DRAFT vietata
-- 9) Revisione da ACCETTATO vietata (rev 03-05-2026: ACCETTATO chiude
--    la negoziazione, non rivisitabile - regola di dominio)
-- 10) anti-regressione: rename codice stati -> revisione risolta per codice_interno
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- ⭐ rev 2026-10-24 (Q-4): app.current_user_id e' quella del contesto aperto
--   qui sopra, l'operatore della cui azienda sono i preventivi del mondo:
--   fn_crea_revisione_preventivo risolve da li' l'emittente della nuova
--   revisione. Prima la si riscriveva col primo utente di
--   config.user_emittenti_fiscali, che puo' non essere un operatore e su un
--   database ricostruito non c'e'.

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_crea_revisione_preventivo'
  ),
  '1. fn_crea_revisione_preventivo presente'
);

-- ============================================================
-- 2) Riferimenti minimi
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-4): il mondo si COSTRUISCE. Il preventivo del test 3
--   nasce qui, in bozza, da dbops.fn_pgtap_crea_preventivo, e i riferimenti
--   ne leggono billing account ed emittente; l'articolo lo costruisce
--   dbops.fn_pgtap_crea_articolo. I cataloghi (stati, IVA, tipo indirizzo)
--   si scelgono per codice e con un ORDER BY stabile.
--   ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_rv_b_emesso AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('revisione emesso');

CREATE TEMP TABLE tmp_rv_refs AS
SELECT
  b.billing_account_id,
  b.utility_id,
  b.istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-RVP-A') AS articolo_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE
  ) AS stato_draft_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'EMESSO' AND s.attivo IS TRUE
  ) AS stato_emesso_id,
  (SELECT s.id FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE
  ) AS stato_accettato_id,
  b.valuta_id,
  b.emittente_fiscale_id,
  (SELECT i.id FROM config.iva i
    WHERE i.attivo IS TRUE AND i.aliquota_iva > 0
    ORDER BY i.id LIMIT 1
  ) AS iva_id,
  (SELECT a.tipo_indirizzo_id
     FROM config.tipi_indirizzi_allowed a
    WHERE a.ambito = 'PREVENTIVO' AND a.attivo IS TRUE
    ORDER BY a.tipo_indirizzo_id LIMIT 1
  ) AS tipo_indirizzo_id
FROM tmp_rv_b_emesso b;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_draft_id IS NOT NULL
      AND stato_emesso_id IS NOT NULL
      AND stato_accettato_id IS NOT NULL
      AND emittente_fiscale_id IS NOT NULL
   FROM tmp_rv_refs),
  '2. Riferimenti minimi disponibili (DRAFT/EMESSO/ACCETTATO + emittente)'
);

-- ============================================================
-- 3) Setup preventivo EMESSO con righe e indirizzi
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): i
--   preventivi EMESSO di questo file (qui e al test 10) nascono DRAFT,
--   prendono le righe, poi passano a EMESSO con dbops.fn_pgtap_porta_a_stato —
--   fuori bozza le righe non si scrivono piu' (20261008-91).
-- ============================================================
-- Il preventivo e' nato in bozza ai riferimenti (tmp_rv_b_emesso): qui se ne
--   legge il numero, che assegna il dominio.
CREATE TEMP TABLE tmp_rv_prev AS
SELECT p.id, p.uid, p.numero
  FROM vendite.preventivi p
  JOIN tmp_rv_b_emesso b ON b.preventivo_id = p.id;

-- 2 righe attive + 1 inattiva
INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita,
  prezzo_unitario, iva_id, attivo, ordine, meta
)
SELECT p.id, r.articolo_id, 10, 10, 100.00, r.iva_id, true, 1,
       jsonb_build_object('test_scope', 'pgtap_revisione', 'riga', 1)
FROM tmp_rv_prev p, tmp_rv_refs r
UNION ALL
SELECT p.id, r.articolo_id, 5, 5, 50.00, r.iva_id, true, 2,
       jsonb_build_object('test_scope', 'pgtap_revisione', 'riga', 2)
FROM tmp_rv_prev p, tmp_rv_refs r
UNION ALL
SELECT p.id, r.articolo_id, 1, 1, 10.00, r.iva_id, false, 3,
       jsonb_build_object('test_scope', 'pgtap_revisione', 'riga', 3)
FROM tmp_rv_prev p, tmp_rv_refs r;

-- 1 indirizzo
INSERT INTO vendite.preventivi_indirizzi (
  preventivo_id, tipo_indirizzo_id, snapshot
)
SELECT p.id, r.tipo_indirizzo_id,
       jsonb_build_object('test', true)
FROM tmp_rv_prev p, tmp_rv_refs r
WHERE r.tipo_indirizzo_id IS NOT NULL;

DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_rv_prev), 'EMESSO');
END $x$;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_rv_prev),
  '3. Setup preventivo EMESSO con righe e indirizzi'
);

-- ============================================================
-- 4) Revisione da EMESSO: nuova rev in DRAFT
-- ============================================================
CREATE TEMP TABLE tmp_rv_result AS
SELECT * FROM vendite.fn_crea_revisione_preventivo(
  (SELECT id FROM tmp_rv_prev),
  'pgtap'
);

SELECT ok(
  (SELECT nuova_rev = 1
      AND nuovo_preventivo_id IS NOT NULL
      AND numero = (SELECT numero FROM tmp_rv_prev)
   FROM tmp_rv_result),
  '4. Revisione da EMESSO: rev=1, stesso numero, nuovo id'
);

-- ============================================================
-- 5) Righe copiate: solo le 2 attive (non la inattiva)
-- ============================================================
SELECT ok(
  (SELECT COUNT(*) = 2
   FROM vendite.preventivi_righe pr
   WHERE pr.preventivo_id = (SELECT nuovo_preventivo_id FROM tmp_rv_result)
     AND pr.attivo IS TRUE),
  '5. Revisione copia solo righe attive (2 su 3)'
);

-- ============================================================
-- 6) Indirizzi copiati (stessa quantita' dell'originale)
-- ============================================================
SELECT ok(
  (SELECT COUNT(*) FROM vendite.preventivi_indirizzi
    WHERE preventivo_id = (SELECT nuovo_preventivo_id FROM tmp_rv_result))
  =
  (SELECT COUNT(*) FROM vendite.preventivi_indirizzi
    WHERE preventivo_id = (SELECT id FROM tmp_rv_prev)),
  '6. Revisione copia indirizzi (stesso numero dell''originale)'
);

-- ============================================================
-- 7) Revisione precedente disattivata
-- ============================================================
SELECT ok(
  (SELECT is_attiva = false
   FROM vendite.vw_preventivi
   WHERE id = (SELECT id FROM tmp_rv_prev)),
  '7. Revisione precedente disattivata (vw_preventivi.is_attiva = false; is_revision_attiva droppata 20260515-05)'
);

-- ============================================================
-- 8) Revisione da DRAFT vietata
-- ============================================================
CREATE TEMP TABLE tmp_rv_b_draft AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('revisione draft');

CREATE TEMP TABLE tmp_rv_prev_draft AS
SELECT p.id, p.uid, p.numero
  FROM vendite.preventivi p
  JOIN tmp_rv_b_draft b ON b.preventivo_id = p.id;

SELECT throws_ok(
  format(
    'SELECT * FROM vendite.fn_crea_revisione_preventivo(%s, ''pgtap'')',
    (SELECT id FROM tmp_rv_prev_draft)
  ),
  NULL, NULL,
  '8. Revisione da DRAFT vietata'
);

-- ============================================================
-- 9) Revisione da ACCETTATO vietata (rev 03-05-2026)
--    Setup: nuovo preventivo portato ad ACCETTATO.
--    ⚠️ rev 2026-10-24: nasce DRAFT e va ad ACCETTATO (DRAFT -> EMESSO ->
--    ACCETTATO) sotto i guard veri. Prima nasceva gia' ACCETTATO con
--    un INSERT diretto, che il trigger della nascita ora rifiuta.
--    ⚠️ rev 2026-10-25 (giro 6): l'emissione chiede una riga attiva, e la
--    scrive dbops.fn_pgtap_crea_preventivo_con_righe, che porta anche ad
--    ACCETTATO (prima: fn_pgtap_crea_preventivo + porta_a_stato, senza righe).
-- ============================================================
CREATE TEMP TABLE tmp_rv_b_accettato AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo_con_righe('revisione accettato', 'ACCETTATO');

CREATE TEMP TABLE tmp_rv_prev_accettato AS
SELECT p.id, p.uid, p.numero
  FROM vendite.preventivi p
  JOIN tmp_rv_b_accettato b ON b.preventivo_id = p.id;

SELECT throws_ok(
  format(
    'SELECT * FROM vendite.fn_crea_revisione_preventivo(%s, ''pgtap'')',
    (SELECT id FROM tmp_rv_prev_accettato)
  ),
  'P0001', NULL,
  '9. Revisione da ACCETTATO vietata (E_PREV_REVISIONE_STATO_NON_AMMESSO)'
);

-- ============================================================
-- 10) Anti-regressione codice_interno (analisi-hardcoded-codice §3a #2):
--     rinominando il `codice` (mutabile) degli stati, la creazione revisione
--     DEVE risolvere stato corrente (EMESSO) e DRAFT per `codice_interno`.
--     Col vecchio codice lo stato corrente non risulterebbe 'EMESSO' ->
--     E_PREV_REVISIONE_STATO_NON_AMMESSO. Preventivo EMESSO fresco (numero nuovo,
--     nessuna revisione DRAFT preesistente).
-- ============================================================
CREATE TEMP TABLE tmp_rv_b_antireg AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('revisione antiregressione');

CREATE TEMP TABLE tmp_rv_prev_antireg AS
SELECT p.id, p.uid, p.numero
  FROM vendite.preventivi p
  JOIN tmp_rv_b_antireg b ON b.preventivo_id = p.id;

-- Riga attiva con quantita > 0 (copiata dalla revisione)
INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita,
  prezzo_unitario, iva_id, attivo, ordine, meta
)
SELECT p.id, r.articolo_id, 10, 10, 100.00, r.iva_id, true, 1,
       jsonb_build_object('test_scope', 'pgtap_revisione')
FROM tmp_rv_prev_antireg p, tmp_rv_refs r;

DO $x$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_rv_prev_antireg), 'EMESSO');
END $x$;

-- Rinomina il codice (mutabile) di EMESSO/DRAFT; codice_interno invariato.
UPDATE config.stati_doc_preventivi
   SET codice = codice || '_RENAMED'
 WHERE codice_interno IN ('EMESSO', 'DRAFT');

SELECT lives_ok(
  format(
    'SELECT * FROM vendite.fn_crea_revisione_preventivo(%s, ''pgtap'')',
    (SELECT id FROM tmp_rv_prev_antireg)
  ),
  '10. anti-regressione: rename codice stati -> revisione risolta per codice_interno'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
