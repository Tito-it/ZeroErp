-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: porta oneri (vendite.fn_aggiungi_onere_commessa).
-- Brief: brief-db-immutabilita-quantita-e-porta-oneri §4c (step 4/5/6/7, 2026-07-21).
--
-- Modello articolo<->causale (Tid 2026-07-21): l'operatore passa un ARTICOLO-ONERE
-- (catalogo.articoli.causale_onere_id NOT NULL, 1:1); la madre deriva causale+uom
-- (e a valle l'IVA, propria dell'articolo) e crea una riga commesse_attivita di
-- puro valore (qta=1, tipo_movimento='ONERE') gia' APPROVATA, SOURCELESS, con
-- audit su commesse_attivita_log. Rifiuta importo <=0/NULL e articolo non-onere.
--
-- Nota fixture: NON si usa fn_emit (richiede ROOT source documentale reale).
-- La porta e' sourceless per costruzione, quindi la creazione non passa da emit.
--
-- Concorrenza (brief-db-race-segment-key-onere, 2026-07-23): i test 20-22
-- coprono il fix della race sul progressivo segment_key. ATTENZIONE al limite:
-- la race vive solo FRA TRANSAZIONI CONCORRENTI, che pgTAP (mono-sessione,
-- BEGIN/ROLLBACK) non sa riprodurre — nella stessa transazione il calcolo del
-- progressivo vede gia' la riga non committata, quindi il test 14 e' una
-- NON-REGRESSIONE della numerazione, non la prova del fix. I test 20-21 sono
-- percio' STRUTTURALI (il codice c'e'), non comportamentali (serializza).
-- La prova di serializzazione e' manuale, a due sessioni psql: vedi §3 del
-- brief. La via dblink e' stata scartata: il canale e' provisioning disabilitato
-- e condizionato a una password non valorizzata in sviluppo -> non eseguibile
-- in CI.
-- ------------------------------------------------------------
-- Indice test (1..22):
--   1   funzione madre presente
--   2   vocabolario causali con almeno una voce attiva
--   3   5 articoli-onere seedati e attivi (con causale)
--   4   IVA per-onere varia (penale fuori campo != trasferta 22%)
--   5   colonna commesse_attivita.causale_onere_id presente
--   6   riferimenti minimi disponibili
--   7   commessa creata
--   8   onere creato (attivita_id non NULL)
--   9   riga: qta=1, ONERE, APPROVATA, NON_EMESSA
--  10   causale derivata dall'articolo + prezzo=importo + SOURCELESS
--  11   segment_key MAN:
--  12   articolo riga = articolo-onere passato
--  13   evento ONERE_AGGIUNTO su commesse_attivita_log
--  14   secondo onere: progressivo MAN:...:2 (non-regressione numerazione)
--  15   rifiuta importo <= 0
--  16   rifiuta importo NULL
--  17   rifiuta articolo non-onere (id inesistente)
--  18   CHECK biconditional: NORMALE con causale bloccato
--  19   codici errore porta oneri presenti (552/553/554)
--  20   [strutturale] progressivo sotto pg_advisory_xact_lock per commessa
--  21   [strutturale] guard E_ONERE_SEGMENT_DUPLICATO (porta = CREATE, non upsert)
--  22   codice errore 557 E_ONERE_SEGMENT_DUPLICATO a catalogo
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

SELECT plan(22);

-- ===== 1..5 struttura =====
SELECT has_function('vendite', 'fn_aggiungi_onere_commessa',
    '1) madre fn_aggiungi_onere_commessa presente');

SELECT ok(
  (SELECT count(*) >= 1 FROM config.causali_onere WHERE attivo),
  '2) config.causali_onere con almeno una voce attiva');

-- rev 2026-11-03 (brief-db-addebito-trasporto-ordine, giro 2): + ONERE_TRASPORTO.
--   Si contano i codici del SEED, per nome: il conteggio di tutti gli
--   articoli-onere attivi diventava rosso al primo onere creato dall'utente.
SELECT ok(
  (SELECT count(*) = 6 FROM catalogo.articoli
    WHERE causale_onere_id IS NOT NULL AND attivo
      AND codice IN ('ONERE_SENZA_CONTRATTO', 'ONERE_TRASFERTA', 'ONERE_MAGG_URGENZA',
                     'ONERE_SPESE_AMM', 'ONERE_PENALE', 'ONERE_TRASPORTO')),
  '3) i 6 articoli-onere del seed, attivi e con causale');

SELECT ok(
  (SELECT (SELECT iva_id FROM catalogo.articoli WHERE codice = 'ONERE_PENALE')
       IS DISTINCT FROM
          (SELECT iva_id FROM catalogo.articoli WHERE codice = 'ONERE_TRASFERTA')),
  '4) IVA per-onere varia (penale fuori campo != trasferta 22%)');

SELECT has_column('vendite', 'commesse_attivita', 'causale_onere_id',
    '5) colonna commesse_attivita.causale_onere_id presente');

-- ===== fixture: riferimenti =====
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE con
--   dbops.fn_pgtap_crea_cliente_ba (BA legato all'azienda di chi agisce);
--   prima si pescava il primo BA con emittente, e su un database
--   ricostruito da zero non c'era. L'emittente si deriva dal BA costruito.
--   Restano letture di catalogo di SEED: tipi_doc_fiscale e articoli-onere.
CREATE TEMP TABLE tmp_cli_po AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('porta oneri');

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_po) AS billing_account_id,
  (SELECT utility_id FROM tmp_cli_po) AS utility_id,
  (SELECT istanza_utility_id FROM tmp_cli_po) AS istanza_utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(billing_account_id) FROM tmp_cli_po) AS emittente_soggetto_ruolo_id,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
  (SELECT id FROM catalogo.articoli WHERE codice = 'ONERE_TRASFERTA') AS articolo_onere_id,
  (SELECT causale_onere_id FROM catalogo.articoli WHERE codice = 'ONERE_TRASFERTA') AS causale_attesa;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL AND utility_id IS NOT NULL
      AND istanza_utility_id IS NOT NULL AND emittente_soggetto_ruolo_id IS NOT NULL
      AND tipo_doc_fiscale_id IS NOT NULL AND articolo_onere_id IS NOT NULL
      AND causale_attesa IS NOT NULL
   FROM tmp_refs),
  '6) riferimenti minimi disponibili');

-- Commessa
CREATE TEMP TABLE tmp_commessa AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa => 'AUTO',
  p_policy_fatturazione => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa => 'NORMALE',
  p_competenza_dal => DATE '2026-07-01',
  p_competenza_al => DATE '2026-07-31',
  p_meta => jsonb_build_object('test_scope', 'pgtap_porta_oneri'),
  p_force_new => true
) AS commessa_id;

SELECT ok((SELECT commessa_id IS NOT NULL FROM tmp_commessa), '7) commessa creata');

-- ===== creazione onere =====
CREATE TEMP TABLE tmp_onere AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id        => (SELECT commessa_id FROM tmp_commessa),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_articolo_onere_id  => (SELECT articolo_onere_id FROM tmp_refs),
  p_importo            => 42.00,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs),
  p_motivo             => 'test onere pgtap',
  p_data_attivita      => DATE '2026-07-15'
) AS attivita_id;

SELECT ok((SELECT attivita_id IS NOT NULL FROM tmp_onere), '8) onere creato (attivita_id non NULL)');

-- 9) stato/registro della riga
SELECT ok(
  (SELECT ca.quantita = 1
      AND ca.tipo_movimento = 'ONERE'
      AND ca.stato_approvazione = 'APPROVATA'
      AND ca.stato_emissione = 'NON_EMESSA'
   FROM vendite.commesse_attivita ca
   WHERE ca.id = (SELECT attivita_id FROM tmp_onere)),
  '9) riga onere: qta=1, ONERE, APPROVATA, NON_EMESSA');

-- 10) causale derivata dall'articolo + prezzo = importo + sourceless
SELECT ok(
  (SELECT ca.causale_onere_id = (SELECT causale_attesa FROM tmp_refs)
      AND ca.prezzo_snapshot = 42.00
      AND ca.sorgente_tipo_id IS NULL
      AND ca.sorgente_uid IS NULL
   FROM vendite.commesse_attivita ca
   WHERE ca.id = (SELECT attivita_id FROM tmp_onere)),
  '10) causale derivata dall''articolo + prezzo=importo + SOURCELESS');

-- 11) segment MAN:
SELECT ok(
  (SELECT ca.segment_key LIKE 'MAN:%'
   FROM vendite.commesse_attivita ca
   WHERE ca.id = (SELECT attivita_id FROM tmp_onere)),
  '11) segment_key MAN:');

-- 12) articolo riga = articolo-onere passato
SELECT ok(
  (SELECT ca.articolo_id = (SELECT articolo_onere_id FROM tmp_refs)
   FROM vendite.commesse_attivita ca
   WHERE ca.id = (SELECT attivita_id FROM tmp_onere)),
  '12) articolo riga = articolo-onere passato');

-- 13) evento su commesse_attivita_log
SELECT ok(
  (SELECT count(*) = 1
   FROM vendite.commesse_attivita_log l
   WHERE l.commessa_attivita_id = (SELECT attivita_id FROM tmp_onere)
     AND l.evento = 'ONERE_AGGIUNTO'),
  '13) evento ONERE_AGGIUNTO su commesse_attivita_log');

-- 14) secondo onere: progressivo MAN:...:2
CREATE TEMP TABLE tmp_onere2 AS
SELECT vendite.fn_aggiungi_onere_commessa(
  p_commessa_id        => (SELECT commessa_id FROM tmp_commessa),
  p_istanza_utility_id => (SELECT istanza_utility_id FROM tmp_refs),
  p_articolo_onere_id  => (SELECT id FROM catalogo.articoli WHERE codice = 'ONERE_PENALE'),
  p_importo            => 7.50,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs)
) AS attivita_id;

SELECT is(
  (SELECT ca.segment_key
   FROM vendite.commesse_attivita ca
   WHERE ca.id = (SELECT attivita_id FROM tmp_onere2)),
  ('MAN:' || (SELECT commessa_id FROM tmp_commessa) || ':2')::varchar,
  '14) secondo onere: progressivo MAN:...:2');

-- 15) rifiuta importo <= 0
SELECT throws_ok(
  $$ SELECT vendite.fn_aggiungi_onere_commessa(
       (SELECT commessa_id FROM tmp_commessa),
       (SELECT istanza_utility_id FROM tmp_refs),
       (SELECT articolo_onere_id FROM tmp_refs),
       0, (SELECT tipo_doc_fiscale_id FROM tmp_refs)) $$,
  'P0001', NULL,
  '15) rifiuta importo <= 0');

-- 16) rifiuta importo NULL
SELECT throws_ok(
  $$ SELECT vendite.fn_aggiungi_onere_commessa(
       (SELECT commessa_id FROM tmp_commessa),
       (SELECT istanza_utility_id FROM tmp_refs),
       (SELECT articolo_onere_id FROM tmp_refs),
       NULL, (SELECT tipo_doc_fiscale_id FROM tmp_refs)) $$,
  'P0001', NULL,
  '16) rifiuta importo NULL');

-- 17) rifiuta articolo non-onere (uuid inesistente)
SELECT throws_ok(
  $$ SELECT vendite.fn_aggiungi_onere_commessa(
       (SELECT commessa_id FROM tmp_commessa),
       (SELECT istanza_utility_id FROM tmp_refs),
       '00000000-0000-7000-8000-0000000000ff'::uuid,
       15, (SELECT tipo_doc_fiscale_id FROM tmp_refs)) $$,
  'P0001', NULL,
  '17) rifiuta articolo non-onere (id inesistente)');

-- 18) CHECK biconditional: portare la riga onere a NORMALE lasciando la causale
--     viola chk_commesse_attivita_causale_onere (23514 = check_violation).
SELECT throws_ok(
  $$ UPDATE vendite.commesse_attivita
        SET tipo_movimento = 'NORMALE'
      WHERE id = (SELECT attivita_id FROM tmp_onere) $$,
  '23514', NULL,
  '18) CHECK biconditional: NORMALE con causale bloccato');

-- 19) codici errore porta oneri presenti
SELECT is(
  (SELECT count(*)::int FROM config.messaggi_errore
    WHERE codice IN ('E_ONERE_IMPORTO_NON_VALIDO',
                     'E_ONERE_CAUSALE_NON_VALIDA',
                     'E_ONERE_ARTICOLO_MANCANTE')
      AND lingua = 'it'),
  3,
  '19) codici errore porta oneri presenti nel catalogo');

-- ===== 20..22 fix race sul progressivo segment_key =====
-- (brief-db-race-segment-key-onere, 2026-07-23)
-- Test STRUTTURALI: verificano che il presidio sia nel corpo della funzione
-- viva. Non possono verificare la serializzazione (serve una seconda sessione,
-- vedi nota in testa al file). Pattern di casa: test-ordini-lock-cliente.sql.

-- 20) il progressivo si calcola sotto advisory lock per commessa
SELECT ok(
  pg_get_functiondef(
    'vendite.fn_aggiungi_onere_commessa(bigint,bigint,uuid,numeric,bigint,text,date)'::regprocedure
  ) LIKE '%pg_advisory_xact_lock%',
  '20) progressivo segment_key calcolato sotto pg_advisory_xact_lock per commessa');

-- 21) guard di difesa in profondita': la porta e' una CREATE, un update non
--     e' mai legittimo (is_new = false -> errore parlante, non sovrascrittura)
SELECT ok(
  pg_get_functiondef(
    'vendite.fn_aggiungi_onere_commessa(bigint,bigint,uuid,numeric,bigint,text,date)'::regprocedure
  ) LIKE '%E_ONERE_SEGMENT_DUPLICATO%',
  '21) guard E_ONERE_SEGMENT_DUPLICATO presente (porta = CREATE, non upsert)');

-- 22) codice errore 557 a catalogo (append a messaggi_errore.csv)
SELECT is(
  (SELECT count(*)::int FROM config.messaggi_errore
    WHERE codice = 'E_ONERE_SEGMENT_DUPLICATO'
      AND id = 557
      AND lingua = 'it'),
  1,
  '22) codice errore 557 E_ONERE_SEGMENT_DUPLICATO presente nel catalogo');

SELECT * FROM finish();
ROLLBACK;
