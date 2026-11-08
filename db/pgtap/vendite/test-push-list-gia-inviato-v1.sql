-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): i due ordini CONFERMATI da dbops.fn_pgtap_crea_ordine_con_righe (10 x 25, trigger CONFERMATO, data 2026-07-19), ritirato l'helper pg_temp.mk_ordine; restano a mano la commessa ospite e le attivita' con le chiavi del caso.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: predicato "gia' inviato" delle push-list + reason capability
--       (brief-db-push-commessa-gia-inviato, rilievo ORD0000227;
--       migrations 20260719-05..11).
--       Riproduce il caso vivo: ordine con attivita' componenti BoM
--       ('#CMP:', NON_EMESSA) che il vecchio predicato (uguaglianza +
--       stato_emissione='EMESSA') non vedeva -> riga ri-elencata e
--       azione ri-offerta dopo il push.
-- ------------------------------------------------------------
-- Indice test (1..10):
--   1)  esiste script.fn_get_stato_push_segment
--   2)  classificatore: segment mai instradato -> LIBERA
--   3)  classificatore: solo attivita' componenti #CMP NON_EMESSA -> ALLOCATA
--   4)  classificatore: tutte le attivita' EMESSE -> EMESSA
--   5)  classificatore: nessuna collisione di prefisso riga
--       (R:24 non matcha R:241#CMP:...)
--   6)  fn_list_ordini_da_pushare: ordine con attivita' #CMP NON_EMESSA
--       -> 0 righe (era 1 = bug ORD0000227)
--   7)  capability ordine: can_push_commessa=false + reason ORDINE_GIA_INVIATO
--   8)  dopo la fatturazione (stato_emissione=EMESSA su tutte)
--       -> reason ORDINE_GIA_FATTURATO
--   9)  controprova: ordine gemello MAI pushato -> 1 riga in lista
--  10)  controprova capability: can_push_commessa=true sul gemello
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

-- ⛔ 2026-09-04 — QUI IL TEST SPEGNEVA IL GUARD, e adesso non piu'.
--   La riga rimossa era `set_config('app.current_user_id', '', true)`: senza
--   utente in sessione `script.trgfn_guard_emittente_scope` usciva subito con
--   RETURN NEW, e le fixture entravano senza che nessuno guardasse l'emittente.
--   La fase 6 di `brief-db-processi-automatici-identita-e-perimetro` chiude quel
--   ramo — una sessione applicativa senza utente non scrive piu'.
--   ⇒ Il contesto operatore del preambolo RESTA valido per tutto il file, e le
--     fixture prendono l'emittente su cui quell'operatore puo' davvero scrivere
--     (`script.fn_pgtap_emittente_operatore()`).
--   ⭐ Non e' una riparazione di comodo: prima questo file collaudava il
--     comportamento di una porta aperta, adesso attraversa il guard come lo
--     attraversa l'applicazione.

-- ============================================================
-- Riferimenti minimi
-- ============================================================
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): cliente fatturabile legato all'azienda di chi agisce,
--   articolo merce non gestito a magazzino (il test non misura il magazzino).
--   Dal DB si legge solo il seed.
CREATE TEMP TABLE tmp_gi_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP push gia inviato');
CREATE TEMP TABLE tmp_gi_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-PGI-V1', false) AS id;

CREATE TEMP TABLE tmp_gi_refs AS
SELECT
  (SELECT m.billing_account_id FROM tmp_gi_mondo m)                      AS billing_account_id,
  (SELECT m.utility_id FROM tmp_gi_mondo m)                              AS utility_id,
  (SELECT m.istanza_utility_id FROM tmp_gi_mondo m)                      AS istanza_utility_id,
  (SELECT t.id FROM tmp_gi_art t)                                        AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)              AS valuta_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='ORDINE_VENDITA' AND s.attivo LIMIT 1) AS src_ordine_id;

-- ============================================================
-- 1) il classificatore esiste
-- ============================================================
SELECT has_function('script', 'fn_get_stato_push_segment',
  '1) esiste script.fn_get_stato_push_segment');

-- ============================================================
-- Fixture: commessa ospite + 2 ordini CONFERMATI con una riga con prezzo
-- (eleggibili al push). L'ordine A ricevera' attivita' componenti #CMP.
-- ============================================================
CREATE TEMP TABLE tmp_gi_commessa AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id)
  SELECT 'PGTAP-GIAINV-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id
    FROM tmp_gi_refs r
  RETURNING id
)
SELECT id FROM ins;

-- I due ordini: CONFERMATI con una riga 10 x 25, trigger CONFERMATO.
CREATE TEMP TABLE tmp_gi_ord_a AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('gia_inviato_A', 'CONFERMATO',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_gi_refs),
    p_quantita => 10, p_prezzo => 25, p_articolo_id => (SELECT articolo_id FROM tmp_gi_refs),
    p_fatturazione_trigger => 'CONFERMATO', p_data_ordine => DATE '2026-07-19');
CREATE TEMP TABLE tmp_gi_ord_b AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('gia_inviato_B', 'CONFERMATO',
    p_billing_account_id => (SELECT billing_account_id FROM tmp_gi_refs),
    p_quantita => 10, p_prezzo => 25, p_articolo_id => (SELECT articolo_id FROM tmp_gi_refs),
    p_fatturazione_trigger => 'CONFERMATO', p_data_ordine => DATE '2026-07-19');

CREATE TEMP TABLE tmp_gi_ord AS
SELECT a.ordine_id AS ord_a, a.ordine_uid AS uid_a, a.ordine_riga_id AS riga_a,
       b.ordine_id AS ord_b, b.ordine_uid AS uid_b, b.ordine_riga_id AS riga_b
  FROM tmp_gi_ord_a a, tmp_gi_ord_b b;

-- La base delle chiavi sintetiche del classificatore: la chiave del push di un
-- consumo vero della commessa (la provenienza di quelle righe).
CREATE TEMP TABLE tmp_gi_base AS
SELECT x.segment_key::text AS base
  FROM dbops.fn_pgtap_consumo_della_commessa((SELECT id FROM tmp_gi_commessa)) x;

-- Helper: inserisce un'attivita' in commessa con la segment_key data; la
-- provenienza e' il documento che la chiave nomina (a livello di documento).
CREATE OR REPLACE FUNCTION pg_temp.mk_attivita(p_segment text, p_stato_emissione text)
RETURNS bigint AS $$
DECLARE r RECORD; v_id bigint;
BEGIN
  SELECT * INTO r FROM tmp_gi_refs;
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
    competenza_mese, competenza_dal, competenza_al, tipo_doc_fiscale_id, valuta_id,
    prezzo_snapshot, pricing_mode, stato_approvazione, stato_emissione,
    sorgente_tipo_id, sorgente_id, sorgente_uid
  )
  VALUES (
    (SELECT id FROM tmp_gi_commessa), p_segment, r.articolo_id, r.istanza_utility_id,
    DATE '2026-07-01', r.uom_id, 1,
    DATE '2026-07-01', DATE '2026-07-01', DATE '2026-07-31',
    r.tipo_doc_fiscale_id, r.valuta_id, 25.00,
    'FIXED', 'BOZZA', p_stato_emissione,
    (SELECT k.sorgente_tipo_id FROM dbops.fn_pgtap_provenienza_da_chiave(p_segment) k),
    (SELECT c.sorgente_id FROM dbops.fn_pgtap_provenienza_da_chiave(p_segment) k,
            script.fn_sorgente_chiave(k.sorgente_tipo_id, k.sorgente_chiave) c),
    (SELECT c.sorgente_uid FROM dbops.fn_pgtap_provenienza_da_chiave(p_segment) k,
            script.fn_sorgente_chiave(k.sorgente_tipo_id, k.sorgente_chiave) c)
  )
  RETURNING id INTO v_id;
  RETURN v_id;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- 2..5) unita' del classificatore (segment key sintetiche dedicate)
-- ============================================================
SELECT is(
  script.fn_get_stato_push_segment(((SELECT base FROM tmp_gi_base) || ':mai-esistita:R:1')),
  'LIBERA',
  '2) segment mai instradato -> LIBERA'
);

-- Riproduzione ORD0000227: SOLO attivita' componenti #CMP, NON_EMESSE.
-- Insert in statement SEPARATA dall'assert: il classificatore e' STABLE e
-- usa lo snapshot d'inizio statement — nella stessa statement non vedrebbe
-- le righe appena inserite (visibilita' per command id).
DO $$
BEGIN
  PERFORM pg_temp.mk_attivita(((SELECT base FROM tmp_gi_base) || ':doc1:R:241#CMP:comp-a'), 'NON_EMESSA');
  PERFORM pg_temp.mk_attivita(((SELECT base FROM tmp_gi_base) || ':doc1:R:241#CMP:comp-b'), 'NON_EMESSA');
  PERFORM pg_temp.mk_attivita(((SELECT base FROM tmp_gi_base) || ':doc2:R:7#CMP:comp-a'), 'EMESSA');
END $$;

SELECT is(
  script.fn_get_stato_push_segment(((SELECT base FROM tmp_gi_base) || ':doc1:R:241')),
  'ALLOCATA',
  '3) solo componenti #CMP NON_EMESSA -> ALLOCATA (il vecchio predicato non li vedeva)'
);

SELECT is(
  script.fn_get_stato_push_segment(((SELECT base FROM tmp_gi_base) || ':doc2:R:7')),
  'EMESSA',
  '4) tutte le attivita EMESSE -> EMESSA'
);

SELECT is(
  script.fn_get_stato_push_segment(((SELECT base FROM tmp_gi_base) || ':doc1:R:24')),
  'LIBERA',
  '5) R:24 non matcha R:241#CMP (nessuna collisione di prefisso riga)'
);

-- ============================================================
-- 6..8) il caso vivo: ordine A con attivita' componenti NON_EMESSE
-- ============================================================
-- Insert separata dall'assert (stessa ragione di visibilita' dei test 3-4).
DO $$
BEGIN
  PERFORM pg_temp.mk_attivita('ORDINE_VENDITA:' || (SELECT uid_a::text FROM tmp_gi_ord)
                               || ':R:' || (SELECT riga_a::text FROM tmp_gi_ord)
                               || '#CMP:comp-1', 'NON_EMESSA');
END $$;

SELECT is(
  (SELECT count(*)::int FROM vendite.fn_list_ordini_da_pushare(
     p_ordine_id := (SELECT ord_a FROM tmp_gi_ord))),
  0,
  '6) ordine con componenti #CMP NON_EMESSA -> 0 righe pushabili (era il bug)'
);

SELECT is(
  (SELECT (j->>'can_push_commessa') || '|' || (j->>'can_push_commessa_reason')
     FROM script.fn_available_actions_ordine((SELECT ord_a FROM tmp_gi_ord)) AS j),
  'false|ORDINE_GIA_INVIATO',
  '7) capability: pushato ma non fatturato -> ORDINE_GIA_INVIATO'
);

UPDATE vendite.commesse_attivita
   SET stato_emissione = 'EMESSA'
 WHERE segment_key LIKE 'ORDINE_VENDITA:' || (SELECT uid_a::text FROM tmp_gi_ord) || ':%';

SELECT is(
  (SELECT (j->>'can_push_commessa') || '|' || (j->>'can_push_commessa_reason')
     FROM script.fn_available_actions_ordine((SELECT ord_a FROM tmp_gi_ord)) AS j),
  'false|ORDINE_GIA_FATTURATO',
  '8) dopo la fatturazione -> ORDINE_GIA_FATTURATO'
);

-- ============================================================
-- 9..10) controprova: l'ordine B mai pushato resta eleggibile
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.fn_list_ordini_da_pushare(
     p_ordine_id := (SELECT ord_b FROM tmp_gi_ord))),
  1,
  '9) ordine mai pushato -> 1 riga in lista'
);

SELECT is(
  (SELECT j->>'can_push_commessa'
     FROM script.fn_available_actions_ordine((SELECT ord_b FROM tmp_gi_ord)) AS j),
  'true',
  '10) capability: ordine mai pushato -> can_push_commessa=true'
);

SELECT * FROM finish();
ROLLBACK;