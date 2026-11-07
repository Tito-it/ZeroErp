-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: porta oneri — il CONTO DELLA MERCE è cieco alle righe MAN (della porta).
-- Brief: brief-db-immutabilita-quantita-e-porta-oneri §5 (step 9) +
--        brief-db-partita-merce-per-documento §13 (rev 2026-09-22).
--
-- Il conto delle attivita' fatturabili per riga di documento e'
-- vendite.fn_af_merce_per_riga (D14 giro 4; la vista vw_af_merce_per_riga ne e'
-- la proiezione): e' la sorgente `af` della PARTITA di merce, e la sua CTE
-- `base` tiene solo le AF con segmento ∈ ('ORD','DDT') e segment_key ~
-- ':R:[0-9]+'; il filtro tipo_movimento = 'NORMALE' lo mette la partita
-- (fn_partite_merce), che legge quel conto per chiave.
-- Una riga onere della porta (fn_aggiungi_onere_commessa) e' tipo_movimento='ONERE',
-- segment 'MAN:<commessa>:<n>', senza ':R:' → fuori da TUTTE le cinture. Questo
-- test crea l'onere per la via reale (madre → emit) e prova che il conto,
-- chiesto proprio con la SUA chiave, non lo vede.
--
-- ⚠️ rev 2026-09-22 (D6): fino a oggi il test 5 replicava a mano il predicato
--    di vw_contatore_merce — una COPIA, che restava verde anche se il conto
--    vero fosse cambiato. vw_contatore_merce e' ritirata (20260922-08); il
--    test 5 chiama il conto vivo. Il gemello sull'esclusione ONERE su un
--    segmento ORD e' il caso 5 di test-fn-partite-merce-chiusura-v1.
-- ------------------------------------------------------------
-- Indice test (1..5):
--   1  onere emesso → AF esiste
--   2  cintura #1: AF tipo_movimento='ONERE' (≠ NORMALE)
--   3  cintura #2: segment 'MAN:' (∉ ORD/DDT)
--   4  cintura #3: segment senza ':R:'
--   5  l'onere e' INVISIBILE al conto vivo: fn_af_merce_per_riga(ARRAY[la sua
--      chiave]) = 0 righe (MAN non e' una corsia del conto, e non c'e' ':R:')
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

SELECT plan(5);

-- rev 2026-10-27 (lotto 4 di D7): via il vecchio «SET LOCAL app.current_user_id
--   = '1'» (con ruolo OPERATORE): l'utente 1 da zero non esiste, e su dev e' un
--   super admin senza azienda. Chi agisce e' l'operatore del contesto qui sopra.
--   Il cliente si COSTRUISCE con dbops.fn_pgtap_crea_cliente_ba (BA legato
--   all'azienda di chi agisce): prima si pescava il primo BA con emittente, e
--   da zero non c'era. L'emittente si deriva dal BA costruito. Restano letture
--   di catalogo di SEED: tipi_doc_fiscale, sorgenti, articoli-onere.
CREATE TEMP TABLE tmp_cli_occ AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('porta oneri contatore cieco');

-- ===== riferimenti =====
CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_occ) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_occ) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_occ) AS istanza_utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(billing_account_id) FROM tmp_cli_occ) AS emittente_soggetto_ruolo_id,
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
  p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope','pgtap_onere_contatore'), p_force_new => true
) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_id FROM tmp_com),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  p_sorgente_chiave => (SELECT commessa_id FROM tmp_com)::text,
  p_sorgente_riga => NULL, p_meta => '{}'::jsonb);

CREATE TEMP TABLE tmp_onere AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id        => (SELECT commessa_id FROM tmp_com),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_articolo_onere_id  => (SELECT articolo_onere_id FROM tmp_refs),
  p_importo            => 30.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs)
) AS commessa_attivita_id;

-- rev 2026-10-27: il verbo della commessa chiede cambia_stato_commessa
-- all'operatore del test (giro 10); senza, su un db dove l'operatore non ce l'ha,
-- si ferma qui con E_PERMESSO_NEGATO.
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'cambia_stato_commessa');
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

-- 5) L'onere NON entra nel conto vivo. Si chiede a fn_af_merce_per_riga la
--    chiave ESATTA dell'onere (la funzione normalizza sulla base prima del
--    primo #, quindi «la sua chiave» e' proprio lei): zero righe. Non e' una
--    copia del predicato — e' il conto che la partita legge.
SELECT is(
  (SELECT count(*)::int
     FROM vendite.fn_af_merce_per_riga(ARRAY[(SELECT segment_key FROM tmp_af)]) f),
  0,
  '5) l''onere della porta e'' invisibile al conto vivo: fn_af_merce_per_riga(ARRAY[chiave MAN]) = 0 righe');

SELECT * FROM finish();
ROLLBACK;
