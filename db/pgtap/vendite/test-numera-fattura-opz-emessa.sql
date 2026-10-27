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
-- 6) La fattura numerata non si cancella (rev 2026-10-04: era «Cleanup completato»)
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

-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA dell'azienda di chi agisce) e
--   l'emittente e' quello dell'operatore di contesto: la terna nasce coerente
--   per costruzione. Prima si partiva da emittenti_fiscali_utilities e si
--   scendeva al primo BA della stessa utility: da zero non c'era niente. Senza
--   la riga (emittente, utility) il ricalcolo usa i parametri di sistema
--   dell'utility (rev 20261021-17). Registro e fattura restano scritti a mano:
--   sono i test 2 e 3.
CREATE TEMP TABLE tmp_cli_nf AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('numera fattura opz emessa');

CREATE TEMP TABLE tmp_refs_nf AS
SELECT script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
       c.utility_id,
       c.billing_account_id
  FROM tmp_cli_nf c;

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
    script.fn_data_operativa(),
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
  fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, meta, competenza_dal, competenza_al
)
SELECT
  (SELECT id FROM tmp_fattura_nf),
  1,
  'Riga di test numerazione',
  1::numeric,
  100::numeric,
  (SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1),
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_nf)), script.fn_data_operativa(), script.fn_data_operativa();

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
-- 6) La fattura appena numerata non si cancella
-- ============================================================
-- ⚠️ Rev 2026-10-04 (Q-4, brief-db-esclusioni-implicite): qui c'era una
--   pulizia in coda (DELETE di fattura, progressivi e registro) chiusa da un
--   ok(true). Era superflua — il file chiude in ROLLBACK — e dal guard
--   vendite.trgfn_fatture_guard_numero_fiscale sarebbe rossa: cancellava una
--   fattura NUMERATA. Al suo posto l'asserzione che quel guard esiste per fare.
--   Il pattern si ferma prima e dopo il segnaposto del numero.
SELECT throws_like(
  $$DELETE FROM vendite.fatture WHERE id = (SELECT id FROM tmp_fattura_nf)$$,
  '%ha già un numero fiscale: non si può cancellare%',
  'La fattura numerata non si cancella (E_FATTURA_NUMERATA_NON_CANCELLABILE)'
);

SELECT * FROM finish();

ROLLBACK;
