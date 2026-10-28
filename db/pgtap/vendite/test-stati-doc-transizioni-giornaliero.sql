-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: matrice transizioni stato LOTTO giornaliero (DB-1, piano-fix-stato-fattura)
--
-- Dopo l'unificazione a 1->2->8: le transizioni lotto 1->2 e 2->8 sono universali
-- (meta={}), quindi valgono anche per il GIORNALIERO; la 1->8 (id 4, GIORNALIERO)
-- e' stata deprecata (ammesso=f). Si verifica il guard trgfn_fatturazione_lotti_guard_stato.
--
-- Indice test (1..3):
--   1) riferimenti minimi presenti (stati + anagrafiche)
--   2) lotto GIORNALIERO: 1->2 (DRAFT->EMESSA) AMMESSO (prima della fix era rifiutato)
--   3) lotto GIORNALIERO: 1->8 (DRAFT->DEFINITIVA) NON ammesso (deprecato)
--
-- rev 2026-10-27 (brief-modello-documento-vendita §15, giro 11): con la porta sul lotto
--   (20261027-18) lo stato si scrive dai verbi: i due passaggi li chiede il giro della
--   pipeline (vendite.fn_lotto_proietta_stato_step), che e' chi li scrive davvero, e il
--   guard di transizione li giudica come prima. Il 3 diventa throws_like sul messaggio del
--   guard: con throws_ok «qualunque errore» sarebbe stato verde anche per la porta.
-- ⚠️ Attesa cambiata: test 3, da «qualunque errore» a E_LOTTO_PARAMETRO_NON_COERENTE.
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

SELECT plan(3);

-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba) e l'emittente e' quello di chi agisce
--   (script.fn_pgtap_emittente_sr_operatore). Prima BA, utility ed emittente si
--   pescavano dall'ultimo BA con un emittente: da zero non c'era, e il lotto
--   scritto fuori dal perimetro dell'operatore lo rifiutava la RLS. I due lotti
--   GIORNALIERO restano INSERT a mano (il builder dei lotti nasce MASSIVO e
--   senza tipo_lotto); cambiano solo i valori. Stati e tipo: catalogo di seed.
CREATE TEMP TABLE tmp_cli_r AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('stati doc transizioni giornaliero');

CREATE TEMP TABLE tmp_r AS
SELECT
  (SELECT id FROM config.stati_doc_fiscale WHERE upper(btrim(codice)) = 'DRAFT'      LIMIT 1) AS draft,
  (SELECT id FROM config.stati_doc_fiscale WHERE upper(btrim(codice)) = 'EMESSA'     LIMIT 1) AS emessa,
  (SELECT id FROM config.stati_doc_fiscale WHERE upper(btrim(codice)) = 'DEFINITIVA' LIMIT 1) AS definitiva,
  (SELECT billing_account_id FROM tmp_cli_r) AS ba,
  (SELECT utility_id FROM tmp_cli_r) AS util,
  script.fn_pgtap_emittente_sr_operatore() AS emit,
  (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tdf;

SELECT ok(
  (SELECT draft IS NOT NULL AND emessa IS NOT NULL AND definitiva IS NOT NULL
       AND ba IS NOT NULL AND emit IS NOT NULL AND tdf IS NOT NULL FROM tmp_r),
  'Riferimenti minimi presenti'
);

-- lotto GIORNALIERO a DRAFT (per il caso 1->2)
CREATE TEMP TABLE tmp_g AS WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti
    (lock_batch_id, competenza_mese, tipo_doc_fiscale_id, utility_id, billing_account_id, emittente_soggetto_ruolo_id, stato_doc_fiscale_id, tipo_lotto)
  SELECT uuidv7(), date_trunc('month', script.fn_data_operativa())::date, tdf, util, ba, emit, draft, 'GIORNALIERO' FROM tmp_r
  RETURNING id
) SELECT * FROM ins;

-- 2) 1->2 ora ammesso per il giornaliero (transizione universale)
SELECT lives_ok(
  format('SELECT vendite.fn_lotto_proietta_stato_step(%s, %s)',
         (SELECT id FROM tmp_g), (SELECT emessa FROM tmp_r)),
  'GIORNALIERO lotto 1->2 (DRAFT->EMESSA) ammesso'
);

-- nuovo lotto GIORNALIERO a DRAFT (per il caso 1->8)
CREATE TEMP TABLE tmp_g2 AS WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti
    (lock_batch_id, competenza_mese, tipo_doc_fiscale_id, utility_id, billing_account_id, emittente_soggetto_ruolo_id, stato_doc_fiscale_id, tipo_lotto)
  SELECT uuidv7(), date_trunc('month', script.fn_data_operativa())::date, tdf, util, ba, emit, draft, 'GIORNALIERO' FROM tmp_r
  RETURNING id
) SELECT * FROM ins;

-- 3) 1->8 deprecato -> il guard solleva
SELECT throws_like(
  format('SELECT vendite.fn_lotto_proietta_stato_step(%s, %s)',
         (SELECT id FROM tmp_g2), (SELECT definitiva FROM tmp_r)),
  'Parametro non coerente con lotto esistente%',
  'GIORNALIERO lotto 1->8 (DRAFT->DEFINITIVA) NON ammesso (deprecato)'
);

SELECT * FROM finish();
ROLLBACK;
