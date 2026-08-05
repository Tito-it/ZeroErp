-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: porta oneri — il CONTATORE è cieco alle righe MAN (della porta).
-- Brief: brief-db-immutabilita-quantita-e-porta-oneri §5 (step 9) +
--        brief-db-fatturazione-ddt-resi §3a (vw_contatore_merce, 20260717-11).
--
-- Il contatore misura i "fatturati" della merce come Σ attivita_fatturabili.quantita
-- sulla sorgente `af_seg`, filtrata da TRE cinture:
--   1) af.tipo_movimento = 'NORMALE'
--   2) segmento ∈ ('ORD','DDT')
--   3) segment_key ~ ':R:[0-9]+'
-- Una riga onere della porta (fn_aggiungi_onere_commessa) è tipo_movimento='ONERE',
-- segment 'MAN:<commessa>:<n>', senza ':R:' → esclusa da TUTTE e tre. Questo test
-- crea l'onere per la via reale (madre → emit) e prova che non entra nel contatore.
--
-- Complementare a test-vw-contatore-merce-v1 (che prova l'esclusione ONERE su un
-- segmento ORD): qui l'onere è quello VERO della porta (MAN:, sourceless).
-- ------------------------------------------------------------
-- Indice test (1..5):
--   1  onere emesso → AF esiste
--   2  cintura #1: AF tipo_movimento='ONERE' (≠ NORMALE)
--   3  cintura #2: segment 'MAN:' (∉ ORD/DDT)
--   4  cintura #3: segment senza ':R:'
--   5  l'onere è INVISIBILE alla sorgente fatturati del contatore (0 righe af_seg)
-- ------------------------------------------------------------

BEGIN;
-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
SET LOCAL app.current_user_id = '1';

-- ===== riferimenti =====
CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS billing_account_id,
  (SELECT ba.utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS utility_id,
  (SELECT ba.istanza_utility_id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS istanza_utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(ba.id) FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1) AS emittente_soggetto_ruolo_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  -- Sorgente ROOT: COMMESSA (target vendite.commesse) con uid = id della commessa
  -- stessa -> riga esistente per costruzione (passa il guard sorgente polimorfa).
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA' AND s.attivo LIMIT 1) AS sorgente_root_id,
  (SELECT id FROM catalogo.articoli WHERE codice='ONERE_TRASFERTA') AS articolo_onere_id;

-- ===== commessa + ROOT + onere + emit =====
CREATE TEMP TABLE tmp_com AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false, p_priorita_operativa => 'NORMALE',
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs),
  p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope','pgtap_onere_contatore'), p_force_new => true
) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_com),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  p_sorgente_uid => (SELECT commessa_id FROM tmp_com)::text,
  p_sorgente_riga => 1, p_meta => '{}'::jsonb);

CREATE TEMP TABLE tmp_onere AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id        => (SELECT commessa_id FROM tmp_com),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_articolo_onere_id  => (SELECT articolo_onere_id FROM tmp_refs),
  p_importo            => 30.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs)
) AS commessa_attivita_id;

SELECT vendite.fn_cambia_stato_commessa((SELECT commessa_id FROM tmp_com), 'PRONTA_FATTURAZIONE');
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com));

-- AF + CA dell'onere
CREATE TEMP TABLE tmp_af AS
SELECT a.id AS af_id, a.tipo_movimento, ca.segment_key
FROM vendite.attivita_fatturabili a
JOIN vendite.commesse_attivita ca ON ca.id = a.commessa_attivita_id
WHERE a.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_onere);

SELECT ok((SELECT af_id IS NOT NULL FROM tmp_af), '1) onere emesso → AF esiste');

SELECT is((SELECT tipo_movimento FROM tmp_af), 'ONERE'::varchar,
  '2) cintura #1: AF tipo_movimento=ONERE (≠ NORMALE)');

SELECT ok(
  (SELECT segment_key LIKE 'MAN:%' AND split_part(segment_key, ':', 1) NOT IN ('ORD','DDT') FROM tmp_af),
  '3) cintura #2: segment MAN: (∉ ORD/DDT)');

SELECT ok(
  (SELECT segment_key !~ ':R:[0-9]+' FROM tmp_af),
  '4) cintura #3: segment senza :R:');

-- 5) L'onere NON entra nella sorgente `af_seg` del contatore: replica esatta del
--    predicato di vw_contatore_merce per la sola AF dell'onere → deve dare 0.
SELECT is(
  (SELECT count(*)::int
     FROM vendite.attivita_fatturabili af
     JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
    WHERE af.id = (SELECT af_id FROM tmp_af)
      AND af.tipo_movimento = 'NORMALE'
      AND split_part(ca.segment_key, ':', 1) IN ('ORD','DDT')
      AND ca.segment_key ~ ':R:[0-9]+'),
  0,
  '5) l''onere è invisibile alla sorgente fatturati del contatore (0 righe af_seg)');

SELECT * FROM finish();
ROLLBACK;
