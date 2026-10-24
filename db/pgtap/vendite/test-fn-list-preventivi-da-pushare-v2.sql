-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2e): le chiavi del push col codice della sorgente (PREVENTIVO:, DDT_VENDITA:, ORDINE_VENDITA:, CONTRATTO:, ATTIVITA_CONSUMI:), stessa forma di script.fn_segment_key carattere per carattere.
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): i documenti nascono in
--   bozza e si portano avanti con dbops.fn_pgtap_porta_a_stato; il preventivo
--   «non ACCETTATO» nasce DRAFT e basta (prima, se DRAFT mancava, ripiegava su
--   COALESCE(bozza, accettato): una nascita ACCETTATO che il trigger della
--   nascita ora rifiuta).
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
-- Setup riferimenti minimi (estende tmp_refs_prev aggiungendo
-- uom_id, tipo_doc_fiscale_id, stato_commessa_id per i test
-- di push gia` eseguito).
-- ============================================================
CREATE TEMP TABLE tmp_refs_p2 AS
SELECT
  (SELECT ba.id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS billing_account_id,
  (SELECT ba.utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS utility_id,
  (SELECT ba.istanza_utility_id
     FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL
      AND ba.istanza_utility_id IS NOT NULL
    ORDER BY ba.id LIMIT 1
  ) AS istanza_utility_id,
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
    WHERE s.codice = 'ACCETTATO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_accettato_id,
  (SELECT s.id
     FROM config.stati_doc_preventivi s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_bozza_id,
  (SELECT v.id
     FROM config.valute v
    ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  (SELECT u.id
     FROM catalogo.unita_misura u
    WHERE u.attivo IS TRUE
    ORDER BY u.id LIMIT 1
  ) AS uom_id,
  (SELECT t.id
     FROM config.tipi_doc_fiscale t
    WHERE t.attivo IS TRUE
    ORDER BY t.id LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (SELECT sc.id
     FROM vendite.stati_commessa sc
    WHERE sc.attivo IS TRUE
    ORDER BY sc.id LIMIT 1
  ) AS stato_commessa_id,
  -- Obbligatorio in contesto non-API: il trigger trgfn_preventivi_default_emittente
  -- legge l'emittente dalla GUC app.current_user_id (vuota in pgTAP) e solleva
  -- se non valorizzata. Passiamo emittente_fiscale_id esplicito da emittenti_fiscali.
  (SELECT ef.id
     FROM anagrafiche.emittenti_fiscali ef
    WHERE ef.attivo IS TRUE
    ORDER BY ef.id LIMIT 1
  ) AS emittente_fiscale_id,
  -- Richiesto da fn_get_aliquota_iva (trigger su preventivi_righe).
  (SELECT i.id
     FROM config.iva i
    WHERE i.attivo IS TRUE
    ORDER BY i.id LIMIT 1
  ) AS iva_id;

-- Preventivo ACCETTATO con una riga valida (fixture principale).
-- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata nasce DRAFT, prende le righe, poi passa ad ACCETTATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le righe non si scrivono piu' (20261008-91).
CREATE TEMP TABLE tmp_prev_p2 AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id,
    utility_id, validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, fatturazione_immediata,
    storicizza, meta, emittente_fiscale_id
  )
  SELECT
    'PGTAP-P2-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_bozza_id, DATE '2026-06-01', false,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_prev_v2'),
    r.emittente_fiscale_id
  FROM tmp_refs_p2 r
  RETURNING id, uid
)
SELECT * FROM ins;

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
CREATE TEMP TABLE tmp_prev_p2_bozza AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
    numero, rev, billing_account_id, istanza_utility_id,
    utility_id, validita_dal, validita_al, valuta_id,
    stato_doc_preventivo_id, data, fatturazione_immediata,
    storicizza, meta, emittente_fiscale_id
  )
  SELECT
    'PGTAP-P2B-' || substr(md5(clock_timestamp()::text), 1, 8),
    0,
    r.billing_account_id, r.istanza_utility_id, r.utility_id,
    DATE '2026-06-01', DATE '2026-06-30', r.valuta_id,
    r.stato_bozza_id,  -- nasce nello stato iniziale (rev 2026-10-24)
    DATE '2026-06-01', false,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_prev_v2', 'case', 'bozza'),
    r.emittente_fiscale_id
  FROM tmp_refs_p2 r
  RETURNING id, uid
)
SELECT * FROM ins;

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
CREATE TEMP TABLE tmp_commessa_p2 AS
WITH ins AS (
-- 🔴 EMITTENTE, aggiunto il 2026-08-18.
--   La policy `rls_commesse_ef_whitelist` ammette, per il ruolo OPERATORE, solo gli
--   emittenti nella whitelist dell'utente — e la stessa espressione sta nel
--   `WITH CHECK`, quindi vale in scrittura. Senza
--   `emittente_soggetto_ruolo_id` l'INSERT moriva con «la nuova riga viola la
--   regola di sicurezza per riga» e il file si fermava li'.
--   L'emittente non si sceglie a mano: `script.fn_pgtap_emittente_sr_operatore()`
--   e' la compagna esatta della `fn_scope_ef_whitelist_via_sr` che la policy
--   interroga. Brief: brief-db-pgtap-runner-rls-baseline §26.
  INSERT INTO vendite.commesse (
    codice, billing_account_id, utility_id, stato_commessa_id, emittente_soggetto_ruolo_id
  )
  SELECT
    'PGTAP-CMD-' || substr(md5(clock_timestamp()::text), 1, 8),
    r.billing_account_id,
    r.utility_id,
    r.stato_commessa_id,
    script.fn_pgtap_emittente_sr_operatore()
  FROM tmp_refs_p2 r
  RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.commesse_attivita (
  commessa_id, segment_key,
  articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
  competenza_mese, competenza_dal, competenza_al,
  tipo_doc_fiscale_id, valuta_id, prezzo_snapshot,
  pricing_mode, stato_approvazione, stato_emissione,
  sorgente_tipo_id, sorgente_uid
)
SELECT
  (SELECT id FROM tmp_commessa_p2),
  -- segment_key identico a quello che produce la fn per questo preventivo/riga
  'PREVENTIVO:' || (SELECT uid FROM tmp_prev_p2)::text || ':R:' || (SELECT id FROM tmp_riga_p2)::text,
  r.articolo_id, r.istanza_utility_id, DATE '2026-06-01', r.uom_id, 10,
  DATE '2026-06-01', DATE '2026-06-01', DATE '2026-06-30',
  r.tipo_doc_fiscale_id, r.valuta_id, 25.500000,
  'FIXED', 'BOZZA', 'EMESSA',
  (SELECT s.id FROM config.sorgenti s WHERE s.codice = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1),
  (SELECT uid FROM tmp_prev_p2)::text
FROM tmp_refs_p2 r;

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
