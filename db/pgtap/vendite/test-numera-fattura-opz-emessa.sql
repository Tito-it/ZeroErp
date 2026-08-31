-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_numera_fattura_opz_emessa
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Inserimento registro di test
-- 3) Inserimento fattura di test
-- 4) Numerazione fattura (numero=1)
-- 5) Numerazione idempotente (numero invariato)
-- 6) Cleanup completato
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

SELECT plan(6);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_nf AS
SELECT
  'pgtap_numera_fattura'::text AS test_scope;

-- ⚠️ La terna (emittente, utility, billing account) si sceglie INSIEME, non a
--   tre pescate indipendenti. Il ricalcolo dei totali pretende una riga di
--   configurazione in anagrafiche.emittenti_fiscali_utilities per la coppia
--   (emittente, utility) e fallisce con E_CONFIG_MANCANTE se non c'e': prendere
--   l'ultimo emittente e l'ultimo BA separatamente li accoppia a caso, e il
--   test diventa una lotteria sui dati. Qui si parte DALLA configurazione e si
--   scende al BA che le corrisponde — la fixture seleziona sulla proprieta' che
--   le serve.
CREATE TEMP TABLE tmp_refs_nf AS
SELECT efu.emittente_soggetto_ruolo_id,
       efu.utility_id,
       (SELECT ba.id
          FROM anagrafiche.billing_account ba
         WHERE ba.utility_id = efu.utility_id
         ORDER BY ba.id
         LIMIT 1) AS billing_account_id
  FROM anagrafiche.emittenti_fiscali_utilities efu
  JOIN anagrafiche.emittenti_fiscali ef
    ON ef.soggetto_ruolo_id = efu.emittente_soggetto_ruolo_id
   AND ef.attivo IS TRUE
 WHERE efu.attivo IS TRUE
   AND EXISTS (SELECT 1 FROM anagrafiche.billing_account ba
                WHERE ba.utility_id = efu.utility_id)
 ORDER BY efu.emittente_soggetto_ruolo_id, efu.utility_id
 LIMIT 1;

SELECT ok(
  (SELECT count(*) = 1 FROM tmp_refs_nf
    WHERE emittente_soggetto_ruolo_id IS NOT NULL
      AND billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL),
  'Riferimenti minimi presenti (terna emittente/utility/BA con configurazione)'
);

-- ============================================================
-- 1) Registro di test
-- ============================================================
CREATE TEMP TABLE tmp_reg_nf AS
WITH ins AS (
  -- ⛔ emittente_soggetto_ruolo_id e' NOT NULL dal 2026-08-30 (C1-2,
  --   20260830-11), e dev'essere lo STESSO delle fatture di questo file:
  --   vendite.trgfn_fatture_guard_registro_emittente rifiuta un documento
  --   sul registro di un altro emittente (C1-3, 20260830-10).
  INSERT INTO vendite.registri_fatturazione (
    codice,
    descrizione,
    reset_policy,
    attivo,
    emittente_soggetto_ruolo_id,
    meta
  )
  SELECT
    left('REGNF_' || (SELECT test_scope FROM tmp_costanti_nf), 16),
    'Registro test numerazione',
    'ANNUALE',
    true,
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_nf),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_nf))
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_reg_nf),
  'Inserimento registro di test'
);

-- ============================================================
-- 2) Fattura di test
-- ============================================================
CREATE TEMP TABLE tmp_fattura_nf AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id,
    data,
    emittente_soggetto_ruolo_id,
    billing_account_id,
    utility_id,
    stato_doc_fiscale_id,
    tipo_doc_fiscale_id,
    valuta_id,
    termine_pagamento_id,
    meta
  )
  SELECT
    (SELECT id FROM tmp_reg_nf),
    current_date,
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_nf),
    (SELECT billing_account_id FROM tmp_refs_nf),
    (SELECT utility_id FROM tmp_refs_nf),
    -- ⚠️ Lo stato va valorizzato: una fattura senza stato non esiste nella
    --   realta' (l'unico creatore, fn_get_or_create_fattura_header, inserisce
    --   sempre in DRAFT). Con lo stato a NULL
    --   fn_ricalcola_riepilogo_iva_fattura risponde «fattura non trovata»,
    --   perche' legge lo stato con SELECT INTO e diagnostica l'IS NULL della
    --   VARIABILE come riga assente: il documento c'e', e' il suo stato a
    --   mancare. Difetto reale della funzione, ma la fixture non deve
    --   esercitarlo per sbaglio partendo da uno stato impossibile.
    (SELECT id FROM config.stati_doc_fiscale WHERE codice_interno = 'DRAFT'),
    -- tipo documento e valuta servono al ricalcolo: sono due dei sette elementi
    -- della chiave di fatture_arrotondamenti_scope, che li vuole NOT NULL.
    (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1),
    -- config.valute non ha la colonna `attivo`: si preferisce EUR e si ripiega
    -- sull'id piu' basso, cosi' la scelta resta deterministica in ogni caso.
    (SELECT id FROM config.valute ORDER BY (iso_code <> 'EUR'), id LIMIT 1),
    (SELECT id FROM config.termini_pagamento
      WHERE codice_interno = 'TP_1RATA' AND attivo IS TRUE),
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_nf))
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_fattura_nf),
  'Inserimento fattura di test'
);

-- ⚠️ 2026-07-28: la fattura di test deve avere ALMENO UNA RIGA.
--   Prima non ne aveva, e la si numerava comunque: una numerazione fiscale su
--   documento vuoto, cioe' proprio cio' che il guard D3 in
--   vendite.fn_assign_numero_fattura ora rifiuta (E_FATTURA_SENZA_RIGHE).
--   Il guard non e' troppo severo: la fixture simulava uno stato che nella
--   realta' ha prodotto le fatture 207 e 208, DEFINITIVE e senza alcuna riga.
--   L'importo della riga lo calcola il trigger a20 (1 x 100 -> 100,00).
--   brief-fix-importi-riga-fattura-zero §4.5.
INSERT INTO vendite.fatture_righe (
  fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, meta
)
SELECT
  (SELECT id FROM tmp_fattura_nf),
  1,
  'Riga di test numerazione',
  1::numeric,
  100::numeric,
  (SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1),
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_nf));

-- ⚠️ 2026-08-02: la fattura di test deve essere anche COERENTE.
--   Il guard D-K (Fase 4b, E_FATTURA_NON_NUMERABILE_INCOERENTE) rifiuta un
--   documento con i totali non calcolati, senza riepilogo IVA o senza piano
--   rate. La fixture aveva la riga ma nient'altro: numerava un documento privo
--   di IVA, di totali e di scadenze — cioe' esattamente la situazione della
--   fattura 362, DEFINITIVA con numero 6, totale 200 e zero rate, che e'
--   l'origine del guard. Anche qui il guard non e' troppo severo: la fixture
--   stava simulando uno stato che nella realta' si e' verificato.
--
--   I satelliti si costruiscono con le FUNZIONI VERE e non a mano: cosi' il
--   test resta valido quando cambiano le formule, e non si limita a soddisfare
--   il guard scrivendogli sotto i numeri che vuole leggere.
--   L'ordine e' quello della pipeline: IVA -> totali -> rate (le rate si
--   ripartiscono su totale_a_pagare, che prima non esiste).
SELECT vendite.fn_ricalcola_riepilogo_iva_fattura((SELECT id FROM tmp_fattura_nf));
SELECT vendite.fn_ricalcola_totali_fattura((SELECT id FROM tmp_fattura_nf));
SELECT vendite.fn_genera_scadenze_fattura((SELECT id FROM tmp_fattura_nf));

-- ============================================================
-- 3) Numerazione fattura
-- ============================================================
SELECT is(
  (
    SELECT numero
    FROM vendite.fn_numera_fattura_opz_emessa(
      p_fattura_id => (SELECT id FROM tmp_fattura_nf)
    )
  ),
  1::bigint,
  'Numerazione fattura (numero=1)'
);

SELECT is(
  (
    SELECT numero
    FROM vendite.fn_numera_fattura_opz_emessa(
      p_fattura_id => (SELECT id FROM tmp_fattura_nf)
    )
  ),
  1::bigint,
  'Numerazione idempotente (numero invariato)'
);

-- ============================================================
-- Cleanup
-- ============================================================
UPDATE vendite.fatture
SET storicizza = false
WHERE id = (SELECT id FROM tmp_fattura_nf);

UPDATE vendite.registri_fatturazione
SET storicizza = false
WHERE id = (SELECT id FROM tmp_reg_nf);

DELETE FROM vendite.fatture
WHERE id = (SELECT id FROM tmp_fattura_nf);

DELETE FROM vendite.registri_fatturazione_progressivi
WHERE registro_id = (SELECT id FROM tmp_reg_nf);

DELETE FROM vendite.registri_fatturazione
WHERE id = (SELECT id FROM tmp_reg_nf);

SELECT ok(true, 'Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
