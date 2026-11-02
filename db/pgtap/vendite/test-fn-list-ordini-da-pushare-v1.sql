-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): i quattro ordini con dbops.fn_pgtap_crea_ordine_con_righe (10 x 25.5, data 2026-06-15; SPEDITO/CONSEGNATO col trigger scritto in bozza, quello del test 3 ereditato dal BA, la bozza in DRAFT); a mano resta solo il mondo (azienda, cliente, articolo).
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_ordini_da_pushare + trgfn_ordini_normalize
-- ------------------------------------------------------------
-- Indice test (1..10):
-- 1) fn_list_ordini_da_pushare presente
-- 2) Riferimenti minimi disponibili
-- 3) Ordine CONFERMATO con fatturazione_trigger CONFERMATO restituito
-- 4) Segment key formato corretto (ORD:<uid>:R:<riga_id>)
-- 5) prezzo_bloccato = TRUE per ordini
-- 6) Ordine con fatturazione_trigger SPEDITO escluso
-- 7) Ordine con fatturazione_trigger CONSEGNATO escluso
-- 8) Ordine non CONFERMATO escluso
-- 9) Filtro p_billing_account_id rispettato
-- 10) trgfn_ordini_normalize eredita fatturazione_trigger da billing_account
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
-- 0) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_ordini_da_pushare'
  ),
  'fn_list_ordini_da_pushare presente'
);

-- ============================================================
-- 0b) Riferimenti minimi
-- ============================================================
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti). Prima BA, ruolo e articolo si pescavano col LIMIT 1:
--   su zeroerp_ci erano NULL e l'ordine moriva sul NOT NULL di
--   soggetto_ruolo_id. Ora un'azienda nuova col suo operatore (contesto aperto
--   su di lui), il cliente legato a lei (dbops.fn_pgtap_crea_mondo_cliente) e un
--   articolo merce non gestito. Il BA nasce con fatturazione_ordini al default
--   CONFERMATO, che e' cio' che il test 3 pretende. Le asserzioni leggono solo
--   gli ordini costruiti qui. Modello: test-ddt-magazzino-testata-v1.
CREATE TEMP TABLE _az AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _az)); END $ctx$;
CREATE TEMP TABLE _m AS SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP list ordini');

CREATE TEMP TABLE tmp_refs_ord AS
SELECT
  m.billing_account_id,
  m.cliente_soggetto_ruolo_id AS soggetto_ruolo_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-LIST-ORD-V1', false) AS articolo_id,
  (SELECT s.id
     FROM config.stati_doc_ordini s
    WHERE s.codice = 'CONFERMATO' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1
  ) AS stato_confermato_id,
  (SELECT s.id
     FROM config.stati_doc_ordini s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1
  ) AS stato_bozza_id,
  (SELECT s.id
     FROM config.sorgenti s
    WHERE s.codice = 'ORDINE_VENDITA' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1
  ) AS sorgente_tipo_id
FROM _m m;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_confermato_id IS NOT NULL
      AND sorgente_tipo_id IS NOT NULL
   FROM tmp_refs_ord),
  'Riferimenti minimi disponibili'
);

-- ============================================================
-- 1) Ordine CONFERMATO con fatturazione_trigger CONFERMATO
-- ============================================================
-- Il trigger trgfn_ordini_normalize imposta fatturazione_trigger
-- da billing_account.fatturazione_ordini (default CONFERMATO) su INSERT:
-- per questo il builder NON riceve p_fatturazione_trigger (il test 10 lo misura).
-- La riga porta l'aliquota (la mette il builder): la conferma rifiuta
-- «un prezzo senza aliquota».
CREATE TEMP TABLE tmp_ordine AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('fn_list_ord', 'CONFERMATO',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ord),
    p_quantita => 10, p_prezzo => 25.5,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_ord),
    p_data_ordine => DATE '2026-06-15');

-- Verifica che il trigger ha impostato CONFERMATO
-- (prerequisito per il test funzionale)
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL) rp
    WHERE rp.ordine_id = (SELECT ordine_id FROM tmp_ordine)
  ),
  'Ordine CONFERMATO con fatturazione_trigger CONFERMATO restituito'
);

-- ============================================================
-- 2) Formato segment_key
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL) rp
    WHERE rp.ordine_id = (SELECT ordine_id FROM tmp_ordine)
      AND rp.segment_key = 'ORDINE_VENDITA:' || (SELECT ordine_uid FROM tmp_ordine)::text
                           || ':R:' || (SELECT ordine_riga_id FROM tmp_ordine)::text
  ),
  'Segment key formato corretto (ORD:<uid>:R:<riga_id>)'
);

-- ============================================================
-- 3) prezzo_bloccato = TRUE
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL) rp
    WHERE rp.ordine_id = (SELECT ordine_id FROM tmp_ordine)
      AND rp.prezzo_bloccato IS TRUE
  ),
  'prezzo_bloccato = TRUE per ordini'
);

-- ============================================================
-- 4) Ordine con fatturazione_trigger SPEDITO escluso
-- ============================================================
-- Il trigger SPEDITO e' una condizione della bozza: lo scrive il builder.
CREATE TEMP TABLE tmp_ordine_spedito AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('fn_list_ord spedito', 'CONFERMATO',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ord),
    p_quantita => 10, p_prezzo => 25.5,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_ord),
    p_fatturazione_trigger => 'SPEDITO',
    p_data_ordine => DATE '2026-06-15');

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL) rp
    WHERE rp.ordine_id = (SELECT ordine_id FROM tmp_ordine_spedito)
  ),
  'Ordine con fatturazione_trigger SPEDITO escluso'
);

-- ============================================================
-- 5) Ordine con fatturazione_trigger CONSEGNATO escluso
-- ============================================================
CREATE TEMP TABLE tmp_ordine_consegnato AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('fn_list_ord consegnato', 'CONFERMATO',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ord),
    p_quantita => 10, p_prezzo => 25.5,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_ord),
    p_fatturazione_trigger => 'CONSEGNATO',
    p_data_ordine => DATE '2026-06-15');

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL) rp
    WHERE rp.ordine_id = (SELECT ordine_id FROM tmp_ordine_consegnato)
  ),
  'Ordine con fatturazione_trigger CONSEGNATO escluso'
);

-- ============================================================
-- 6) Ordine non CONFERMATO escluso
-- ============================================================
CREATE TEMP TABLE tmp_ordine_bozza AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('fn_list_ord bozza', 'DRAFT',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_ord),
    p_quantita => 10, p_prezzo => 25.5,
    p_articolo_id => (SELECT articolo_id FROM tmp_refs_ord),
    p_data_ordine => DATE '2026-06-15');

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, NULL, NULL) rp
    WHERE rp.ordine_id = (SELECT ordine_id FROM tmp_ordine_bozza)
  )
  OR (SELECT stato_bozza_id IS NULL FROM tmp_refs_ord),
  'Ordine non CONFERMATO escluso (o stato BOZZA non configurato)'
);

-- ============================================================
-- 7) Filtro p_billing_account_id rispettato
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ordini_da_pushare(NULL, -999999, NULL) rp
    WHERE rp.ordine_id = (SELECT ordine_id FROM tmp_ordine)
  ),
  'Filtro p_billing_account_id rispettato'
);

-- ============================================================
-- 8) trgfn_ordini_normalize eredita fatturazione_trigger da BA
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.ordini o
    WHERE o.id = (SELECT ordine_id FROM tmp_ordine)
      AND o.fatturazione_trigger = COALESCE(
        (SELECT ba.fatturazione_ordini
           FROM anagrafiche.billing_account ba
          WHERE ba.id = o.billing_account_id),
        'CONFERMATO'
      )
  ),
  'trgfn_ordini_normalize eredita fatturazione_trigger da billing_account'
);

SELECT * FROM finish();
