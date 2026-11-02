-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2e): le chiavi del push col codice della sorgente (PREVENTIVO:, DDT_VENDITA:, ORDINE_VENDITA:, CONTRATTO:, ATTIVITA_CONSUMI:), stessa forma di script.fn_segment_key carattere per carattere.
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato; il preventivo
--   «non ACCETTATO» nasce DRAFT e basta (prima, se DRAFT mancava, ripiegava su
--   COALESCE(bozza, accettato): una nascita ACCETTATO che il trigger della
--   nascita ora rifiuta).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): i due preventivi
--   vengono da dbops.fn_pgtap_crea_preventivo e la commessa del test 7 da
--   dbops.fn_pgtap_crea_commessa sullo stesso billing account; prima billing
--   account, emittente e stato commessa erano «il primo» del database, che su
--   uno ricostruito non c'e'.
-- rev 2026-10-24 (brief-modello-documento-vendita §4-octies): l'attivita' EMESSA del test 7 la scrive dbops.fn_pgtap_crea_commessa_attivita con la sorgente, invece dell'INSERT con la chiave composta a mano; valuta, tipo documento e uom non si pescano piu'.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_preventivi_da_pushare — parametro p_preventivo_id (v2)
-- ------------------------------------------------------------
-- Indice test (1..10):
-- 1) Firma funzione: 5 parametri (pronargs) [era 4, stale: p_righe_ids dal 12-06-2026]
-- 2) p_preventivo_id NULL: regressione — preventivo ACCETTATO restituito (comportamento batch invariato)
-- 3) p_preventivo_id valido pushable: restituisce solo le righe del preventivo specificato
-- 4) p_preventivo_id valido preventivo non-ACCETTATO (BOZZA): 0 righe, no errore
-- 5) p_preventivo_id inesistente: 0 righe, no errore
-- 6) p_preventivo_id valido + p_billing_account_id di BA diverso: 0 righe (filtri in AND)
-- 7) p_preventivo_id preventivo gia` pushato (segment_key EMESSA in commesse_attivita): 0 righe
-- 8) Guard p_preventivo_id = 0: eccezione sollevata
-- 9) uom_id valorizzato da catalogo.articoli (fix bug proiezione NULL)
-- 10) anti-regressione: rename codice sorgente PREVENTIVO -> risoluzione per codice_interno (no E_CODICE)
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

-- ============================================================
-- Setup riferimenti minimi.
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-2/Q-4): il preventivo principale nasce qui, in bozza,
--   da dbops.fn_pgtap_crea_preventivo, e i riferimenti ne leggono cliente ed
--   emittente. ⛔ Cio' che il builder scrive si legge in un'istruzione SEPARATA.
CREATE TEMP TABLE tmp_prev_p2_b AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('list prev da pushare v2');

CREATE TEMP TABLE tmp_refs_p2 AS
SELECT
  -- ⭐ rev 2026-10-24 (Q-4): billing account, utility, istanza ed emittente
  --   sono quelli del preventivo principale, costruito qui sopra (tmp_prev_p2_b).
  --   Prima: «il primo billing account» e «il primo emittente» del database.
  b.billing_account_id,
  b.utility_id,
  b.istanza_utility_id,
  -- ⛔ rev 2026-10-13: l'articolo si COSTRUISCE. Prima era «il piu' recente
  --   del catalogo», cioe' quello che l'ultimo smoke aveva lasciato: il
  --   2026-10-13 era un composito MERCE, la riga andava all'ordine e il lister
  --   delle commesse giustamente non la restituiva. La natura (destinazione
  --   COMMESSA: e' il ramo che questo lister serve) si sceglie alla nascita:
  --   e' la condizione del caso.
  dbops.fn_pgtap_crea_articolo('PGT-LPP-V2', false,
    p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                             WHERE nv.destinazione_tipo = 'COMMESSA' AND nv.attivo
                             ORDER BY nv.id LIMIT 1)) AS articolo_id,
  (SELECT s.id
     FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'ACCETTATO' AND s.attivo IS TRUE
  ) AS stato_accettato_id,
  (SELECT s.id
     FROM config.stati_doc_preventivi s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE
  ) AS stato_bozza_id,
  -- Richiesto da fn_get_aliquota_iva (trigger su preventivi_righe).
  (SELECT i.id
     FROM config.iva i
    WHERE i.attivo IS TRUE
    ORDER BY i.id LIMIT 1
  ) AS iva_id
FROM tmp_prev_p2_b b;

-- Preventivo ACCETTATO con una riga valida (fixture principale).
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende le righe, poi passa ad ACCETTATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-91).
CREATE TEMP TABLE tmp_prev_p2 AS
SELECT b.preventivo_id AS id, b.preventivo_uid AS uid
  FROM tmp_prev_p2_b b;

CREATE TEMP TABLE tmp_riga_p2 AS
WITH ins AS (
  INSERT INTO vendite.preventivi_righe (
    preventivo_id, articolo_id, qta_operativa, quantita, prezzo_unitario,
    iva_id, attivo, meta
  )
  SELECT
    p.id, r.articolo_id, 10.000000, 10.000000, 25.500000,
    r.iva_id, true, jsonb_build_object('test_scope', 'pgtap_fn_list_prev_v2')
  FROM tmp_prev_p2 p, tmp_refs_p2 r
  RETURNING id
)
SELECT * FROM ins;

DO $porta$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', (SELECT id FROM tmp_prev_p2), 'ACCETTATO');
END $porta$;

-- Preventivo BOZZA con riga valida (per test 4).
CREATE TEMP TABLE tmp_prev_p2_bozza_b AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('list prev v2 bozza');

CREATE TEMP TABLE tmp_prev_p2_bozza AS
SELECT b.preventivo_id AS id, b.preventivo_uid AS uid
  FROM tmp_prev_p2_bozza_b b;

INSERT INTO vendite.preventivi_righe (
  preventivo_id, articolo_id, qta_operativa, quantita, prezzo_unitario,
  iva_id, attivo, meta
)
SELECT
  pb.id, r.articolo_id, 5.000000, 5.000000, 10.000000,
  r.iva_id, true, jsonb_build_object('test_scope', 'pgtap_fn_list_prev_v2', 'case', 'bozza')
FROM tmp_prev_p2_bozza pb, tmp_refs_p2 r;

-- ============================================================
-- TEST 1) Firma funzione: 5 parametri
-- (p_competenza_mese, p_billing_account_id, p_limit, p_preventivo_id,
--  p_righe_ids — quest'ultimo aggiunto rev 12-06-2026, brief smistamento.
--  Asserzione aggiornata: il test v2 era rimasto a 4.)
-- ============================================================
SELECT ok(
  (SELECT p.pronargs = 5
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_preventivi_da_pushare'
    LIMIT 1),
  'fn_list_preventivi_da_pushare ha 5 parametri (pronargs = 5)'
);

-- ============================================================
-- TEST 2) p_preventivo_id NULL: regressione batch invariata
-- ============================================================
CREATE TEMP TABLE tmp_r2_null AS
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_competenza_mese    => NULL,
  p_billing_account_id => NULL,
  p_limit              => NULL,
  p_preventivo_id      => NULL
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_r2_null rp
    WHERE rp.preventivo_id = (SELECT id FROM tmp_prev_p2)
  ),
  'p_preventivo_id NULL: preventivo ACCETTATO restituito (regressione batch)'
);

-- ============================================================
-- TEST 3) p_preventivo_id valido: solo le righe di quel preventivo
-- ============================================================
CREATE TEMP TABLE tmp_r2_singolo AS
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_preventivo_id => (SELECT id FROM tmp_prev_p2)
);

SELECT ok(
  -- Il preventivo principale e` presente
  EXISTS (
    SELECT 1
    FROM tmp_r2_singolo rp
    WHERE rp.preventivo_id = (SELECT id FROM tmp_prev_p2)
  )
  -- Il preventivo BOZZA non compare (filtro per id esclude altri)
  AND NOT EXISTS (
    SELECT 1
    FROM tmp_r2_singolo rp
    WHERE rp.preventivo_id = (SELECT id FROM tmp_prev_p2_bozza)
  ),
  'p_preventivo_id valido: solo le righe del preventivo specificato'
);

-- ============================================================
-- TEST 4) p_preventivo_id valido preventivo BOZZA: 0 righe
-- ============================================================
CREATE TEMP TABLE tmp_r2_bozza AS
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_preventivo_id => (SELECT id FROM tmp_prev_p2_bozza)
);

SELECT ok(
  NOT EXISTS (SELECT 1 FROM tmp_r2_bozza),
  'p_preventivo_id preventivo BOZZA (non ACCETTATO): 0 righe, no errore'
);

-- ============================================================
-- TEST 5) p_preventivo_id inesistente: 0 righe
-- ============================================================
CREATE TEMP TABLE tmp_r2_ghost AS
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_preventivo_id => 999999999::bigint
);

SELECT ok(
  NOT EXISTS (SELECT 1 FROM tmp_r2_ghost),
  'p_preventivo_id inesistente: 0 righe, no errore'
);

-- ============================================================
-- TEST 6) p_preventivo_id valido + p_billing_account_id diverso: 0 righe
-- Verifica che i filtri siano applicati in AND.
-- ============================================================
CREATE TEMP TABLE tmp_r2_ba_mismatch AS
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_preventivo_id      => (SELECT id FROM tmp_prev_p2),
  p_billing_account_id => -999999::bigint
);

SELECT ok(
  NOT EXISTS (SELECT 1 FROM tmp_r2_ba_mismatch),
  'p_preventivo_id + p_billing_account_id diverso: 0 righe (filtri in AND)'
);

-- ============================================================
-- TEST 7) Preventivo gia` pushato (NOT EXISTS EMESSA): 0 righe
-- Crea una commessa + attivita con segment_key del preventivo
-- in stato EMESSA, poi verifica che la fn restituisca 0 righe.
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-2/Q-4): la commessa la scrive la madre del dominio
--   tramite dbops.fn_pgtap_crea_commessa, sul billing account del preventivo
--   e nello stato iniziale; l'emittente e' quello del billing account. Prima:
--   INSERT a mano col primo stato commessa per id. L'attivita' EMESSA con la
--   chiave del preventivo resta scritta qui: e' il caso del test.
CREATE TEMP TABLE tmp_commessa_p2_b AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
  'list prev v2 pushato',
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_p2));

CREATE TEMP TABLE tmp_commessa_p2 AS
SELECT b.commessa_id AS id FROM tmp_commessa_p2_b b;

-- rev 2026-10-24 (§4-octies): l'attivita' EMESSA la scrive il builder con la
--   sorgente; la chiave (quella che il lister produce per questo
--   preventivo/riga) la compone il dominio, script.fn_segment_key. Unita' di
--   misura dall'articolo, tipo documento fiscale e valuta dalla madre.
CREATE TEMP TABLE tmp_att_p2 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
    p_commessa_id        => (SELECT id FROM tmp_commessa_p2),
    p_prezzo_snapshot    => 25.500000,
    p_articolo_id        => (SELECT articolo_id FROM tmp_refs_p2),
    p_sorgente_codice    => 'PREVENTIVO',
    p_sorgente_uid       => (SELECT uid::text FROM tmp_prev_p2),
    p_sorgente_riga_id   => (SELECT id FROM tmp_riga_p2),
    p_quantita           => 10,
    p_stato_approvazione => 'BOZZA',
    p_stato_emissione    => 'EMESSA',
    p_competenza_dal     => DATE '2026-06-01',
    p_competenza_al      => DATE '2026-06-30');

-- La riga scritta davvero, sulla chiave della riga (controllo, non test).
DO $chk$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM vendite.commesse_attivita ca
                   JOIN tmp_att_p2 t ON t.attivita_id = ca.id
                  WHERE ca.stato_emissione = 'EMESSA'
                    AND ca.segment_key = script.fn_segment_key('PREVENTIVO',
                                           (SELECT uid FROM tmp_prev_p2)::text,
                                           (SELECT id FROM tmp_riga_p2))) THEN
    RAISE EXCEPTION 'fixture: manca l''attivita'' EMESSA della riga del preventivo';
  END IF;
END $chk$;

CREATE TEMP TABLE tmp_r2_pushed AS
SELECT *
FROM vendite.fn_list_preventivi_da_pushare(
  p_preventivo_id => (SELECT id FROM tmp_prev_p2)
);

SELECT ok(
  NOT EXISTS (SELECT 1 FROM tmp_r2_pushed),
  'p_preventivo_id preventivo gia` pushato (NOT EXISTS EMESSA): 0 righe'
);

-- ============================================================
-- TEST 8) Guard p_preventivo_id = 0: eccezione sollevata
-- ============================================================
SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_list_preventivi_da_pushare(p_preventivo_id => 0) $$,
  NULL,
  NULL,
  'Guard p_preventivo_id = 0: eccezione sollevata (E_PUSH_SORGENTE_ID_INVALIDO)'
);

-- ============================================================
-- TEST 9) uom_id valorizzato da catalogo.articoli (fix bug proiezione NULL)
-- tmp_r2_singolo e` stato creato nel test 3 con le righe del preventivo di
-- fixture. L'articolo e` catalogo.articoli con uom_id NOT NULL garantito
-- dalla colonna NOT NULL del catalogo.
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_r2_singolo
    WHERE preventivo_id = (SELECT id FROM tmp_prev_p2)
      AND uom_id IS NOT NULL
  ),
  'p_preventivo_id: uom_id valorizzato da catalogo.articoli (fix bug proiezione NULL)'
);

-- ============================================================
-- TEST 10) Anti-regressione codice_interno (analisi-hardcoded-codice §3a):
--   rinominando il `codice` (mutabile) della sorgente, la funzione DEVE
--   continuare a risolverla per `codice_interno` (immutabile): nessun E_CODICE.
-- ============================================================
UPDATE config.sorgenti
   SET codice = codice || '_RENAMED'
 WHERE codice_interno = 'PREVENTIVO';

SELECT lives_ok(
  $$ SELECT 1 FROM vendite.fn_list_preventivi_da_pushare(p_limit => 1) $$,
  '10. anti-regressione: rename codice sorgente PREVENTIVO -> risoluzione per codice_interno (no E_CODICE)'
);

SELECT * FROM finish();
ROLLBACK;
