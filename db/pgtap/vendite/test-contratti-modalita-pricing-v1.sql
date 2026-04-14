-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test F1-DB-T2 (parte 1/2): modalita' pricing contratti v5.
-- Copre CHECK su (listino_id, tipo_variazione_globale, valore_variazione_globale)
-- e i guard trigger di modalita' C (attivazione + riga).
--
-- Elenco test (1..8):
--   1) Modalita' A: listino NOT NULL + variazione globale NOT NULL -> ok
--   2) Modalita' C: listino NULL + variazione globale NULL -> ok (in DRAFT)
--   3) CHECK: listino NULL con variazione globale NOT NULL -> fallisce
--   4) CHECK: tipo_variazione_globale senza valore -> fallisce (coerenza)
--   5) Guard attivazione: contratto modalita' C senza righe -> fallisce passaggio ad ATTIVO
--   6) Guard attivazione: contratto modalita' C con riga senza prezzo -> fallisce
--   7) Guard riga: contratto ATTIVO modalita' C + insert riga senza prezzo -> fallisce
--   8) Contratto ATTIVO modalita' A: riga senza prezzo_unitario ammessa (non vincolo)
-- ------------------------------------------------------------

BEGIN;
SELECT plan(8);

-- Precondizioni: BA su utility SENZA dimensione tipo/classe (commercio/Base).
-- Il trigger AFTER INSERT su contratti crea automaticamente una riga in
-- contratti_utilities: con una utility "tecnica" (tipi_utenze popolata)
-- il guard trgfn_contratti_utilities_guard_tipo_classe bloccherebbe la
-- insert del contratto di test. Usando utility commercio evitiamo il guard
-- isolando il test alla sola modalita' pricing.
CREATE TEMP TABLE tmp_ctx_ba AS
SELECT ba.id AS billing_account_id,
       ba.istanza_utility_id,
       ba.utility_id
  FROM anagrafiche.billing_account ba
 WHERE NOT EXISTS (
     SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = ba.utility_id
 )
 ORDER BY ba.id
 LIMIT 1;

-- Precondizione esplicita: se il DB di dev non ha un BA su utility commercio,
-- i test sottostanti non possono essere isolati. Segnalo chiaramente.

CREATE TEMP TABLE tmp_ctx_stato_draft AS
SELECT id AS stato_id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT';

CREATE TEMP TABLE tmp_ctx_stato_attivo AS
SELECT id AS stato_id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO';

CREATE TEMP TABLE tmp_ctx_listino AS
SELECT id AS listino_id FROM vendite.listini WHERE attivo IS TRUE ORDER BY id LIMIT 1;

CREATE TEMP TABLE tmp_ctx_articolo AS
SELECT id AS articolo_id, uom_id FROM catalogo.articoli WHERE attivo IS TRUE ORDER BY id LIMIT 1;

-- Nota: periodi dei contratti di test sono disgiunti per non violare
-- ex_contratti_no_overlap sul medesimo (billing_account, istanza_utility,
-- utility, ambito). Senza valido_al esplicito la validita' sarebbe
-- aperta a +infinity e due contratti su date diverse si sovrapporrebbero.

-- 1) Modalita' A: listino NOT NULL + variazione globale NOT NULL, in DRAFT
SELECT lives_ok(
    $$INSERT INTO vendite.contratti(
          numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
          valido_dal, valido_al, listino_id, tipo_variazione_globale, valore_variazione_globale)
      SELECT 'PGTAP_CONTR_A', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
             sd.stato_id, '2050-01-01', '2050-12-31',
             l.listino_id, 'PERCENTUALE', -10
        FROM tmp_ctx_ba ba, tmp_ctx_stato_draft sd, tmp_ctx_listino l$$,
    'Modalita A: listino + variazione globale (DRAFT) ammessa'
);

-- 2) Modalita' C: tutto NULL, in DRAFT, periodo disgiunto dal contratto A
SELECT lives_ok(
    $$INSERT INTO vendite.contratti(
          numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
          valido_dal, valido_al, listino_id, tipo_variazione_globale, valore_variazione_globale)
      SELECT 'PGTAP_CONTR_C', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
             sd.stato_id, '2051-01-01', '2051-12-31',
             NULL, NULL, NULL
        FROM tmp_ctx_ba ba, tmp_ctx_stato_draft sd$$,
    'Modalita C in DRAFT (listino NULL, variazione NULL) ammessa'
);

-- 3) CHECK chk_contratti_modalita_pricing: listino NULL + variazione globale NOT NULL -> fallisce
SELECT throws_ok(
    $$INSERT INTO vendite.contratti(
          numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
          valido_dal, listino_id, tipo_variazione_globale, valore_variazione_globale)
      SELECT 'PGTAP_CONTR_BAD1', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
             sd.stato_id, '2052-01-01',
             NULL, 'PERCENTUALE', -10
        FROM tmp_ctx_ba ba, tmp_ctx_stato_draft sd$$,
    '23514',
    NULL,
    'listino NULL con variazione globale valorizzata viola chk_contratti_modalita_pricing'
);

-- 4) CHECK chk_contratti_variazione_globale_coerente: tipo senza valore -> fallisce
SELECT throws_ok(
    $$INSERT INTO vendite.contratti(
          numero, billing_account_id, istanza_utility_id, utility_id, stato_doc_contratto_id,
          valido_dal, listino_id, tipo_variazione_globale, valore_variazione_globale)
      SELECT 'PGTAP_CONTR_BAD2', ba.billing_account_id, ba.istanza_utility_id, ba.utility_id,
             sd.stato_id, '2053-01-01',
             l.listino_id, 'PERCENTUALE', NULL
        FROM tmp_ctx_ba ba, tmp_ctx_stato_draft sd, tmp_ctx_listino l$$,
    '23514',
    NULL,
    'tipo_variazione_globale senza valore viola chk_contratti_variazione_globale_coerente'
);

-- 5) Attivazione contratto modalita' C senza righe -> E_CONTRATTO_MODALITA_C_SENZA_RIGHE
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT stato_id FROM tmp_ctx_stato_attivo)
       WHERE numero = 'PGTAP_CONTR_C'$$,
    'P0001',
    NULL,
    'Attivazione contratto modalita C senza righe bloccata'
);

-- Aggiungo una riga senza prezzo al contratto C
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, prezzo_unitario, attivo, qta_operativa)
SELECT c.id, a.articolo_id, NULL, TRUE, 1
  FROM vendite.contratti c, tmp_ctx_articolo a
 WHERE c.numero = 'PGTAP_CONTR_C';

-- 6) Attivazione contratto C con riga senza prezzo -> E_CONTRATTO_MODALITA_C_RIGHE_INCOMPLETE
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT stato_id FROM tmp_ctx_stato_attivo)
       WHERE numero = 'PGTAP_CONTR_C'$$,
    'P0001',
    NULL,
    'Attivazione contratto modalita C con riga senza prezzo bloccata'
);

-- Completo la riga con prezzo e attivo il contratto C
UPDATE vendite.contratti_righe
   SET prezzo_unitario = 50
 WHERE contratto_id = (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_CONTR_C');

UPDATE vendite.contratti
   SET stato_doc_contratto_id = (SELECT stato_id FROM tmp_ctx_stato_attivo)
 WHERE numero = 'PGTAP_CONTR_C';

-- 7) Contratto ATTIVO modalita' C: insert riga senza prezzo bloccato da guard riga
SELECT throws_ok(
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, prezzo_unitario, attivo, qta_operativa)
      SELECT c.id, a.articolo_id, NULL, TRUE, 1
        FROM vendite.contratti c, tmp_ctx_articolo a
       WHERE c.numero = 'PGTAP_CONTR_C'$$,
    'P0001',
    NULL,
    'Contratto ATTIVO modalita C: insert riga senza prezzo_unitario bloccato'
);

-- 8) Contratto modalita' A (con listino): riga senza prezzo ammessa (pricing via listino).
-- Attivo prima il contratto A.
UPDATE vendite.contratti
   SET stato_doc_contratto_id = (SELECT stato_id FROM tmp_ctx_stato_attivo)
 WHERE numero = 'PGTAP_CONTR_A';

SELECT lives_ok(
    $$INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, prezzo_unitario, attivo, qta_operativa)
      SELECT c.id, a.articolo_id, NULL, TRUE, 1
        FROM vendite.contratti c, tmp_ctx_articolo a
       WHERE c.numero = 'PGTAP_CONTR_A'$$,
    'Contratto modalita A: riga senza prezzo_unitario ammessa (guard C non si applica)'
);

SELECT * FROM finish();
ROLLBACK;
