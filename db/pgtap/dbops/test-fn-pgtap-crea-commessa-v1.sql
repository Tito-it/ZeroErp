-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.fn_pgtap_crea_commessa — il BB della commessa
-- Riferimento: brief-db-fixture-rls-documenti-costruiti (giro 3).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - costruisce il mondo e apre la commessa con la MADRE del dominio
--     (vendite.fn_get_or_create_commessa): codice ed emittente li decide lei;
--   - l'emittente e' quello del billing account;
--   - la competenza e' il mese corrente;
--   - una seconda chiamata riusa l'azienda di chi agisce, con un cliente nuovo.
--
-- Elenco test (plan 6):
--   1) la funzione esiste con la firma dichiarata
--   2) la commessa esiste, col codice e il billing account tornati
--   3) l'emittente e' quello del billing account
--   4) la competenza e' il mese corrente
--   5) il codice l'ha assegnato il dominio (non vuoto)
--   6) seconda chiamata: stessa azienda, cliente nuovo
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre la funzione esaminata, che qui
--   viene chiamata come la chiamera' un file su un database ricostruito: senza
--   nessuna veste in sessione. Aprirlo prima nasconderebbe meta' del contratto.

SELECT plan(6);

-- 1) La firma
SELECT has_function(
    'dbops', 'fn_pgtap_crea_commessa',
    ARRAY['text'],
    'dbops.fn_pgtap_crea_commessa(text) esiste con la firma dichiarata'
);

-- Fixture: la prima commessa, dal nulla
CREATE TEMP TABLE t_c1 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('presidio commessa 1');

-- 2) La commessa c'e', ed e' quella tornata
SELECT is(
    (SELECT c.codice::text || '/' || c.billing_account_id::text
       FROM vendite.commesse c
      WHERE c.id = (SELECT commessa_id FROM t_c1)),
    (SELECT commessa_codice::text || '/' || billing_account_id::text FROM t_c1),
    'la commessa esiste e porta il codice e il billing account tornati dalla funzione'
);

-- 3) L'emittente e' quello del billing account
SELECT is(
    (SELECT c.emittente_soggetto_ruolo_id FROM vendite.commesse c
      WHERE c.id = (SELECT commessa_id FROM t_c1)),
    anagrafiche.fn_get_emittente_fiscale_id((SELECT billing_account_id FROM t_c1)),
    'l''emittente della commessa e'' quello del billing account'
);

-- 4) La competenza e' il mese corrente
SELECT is(
    (SELECT c.competenza_dal::text || '/' || c.competenza_al::text
       FROM vendite.commesse c WHERE c.id = (SELECT commessa_id FROM t_c1)),
    date_trunc('month', script.fn_data_operativa())::date::text || '/'
        || (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date::text,
    'la competenza e'' il mese corrente: le attivita'' del builder gemello ci cadono dentro'
);

-- 5) Il codice dal dominio
SELECT ok(
    (SELECT btrim(commessa_codice) <> '' FROM t_c1),
    'il codice l''ha assegnato la madre (vendite.fn_get_or_create_commessa), non la fixture'
);

-- 6) Seconda chiamata: il contesto e' ormai aperto, l'azienda si riusa
CREATE TEMP TABLE t_c2 AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('presidio commessa 2');

SELECT is(
    (SELECT (c2.emittente_fiscale_id = c1.emittente_fiscale_id)::text
         || ' ' || (c2.billing_account_id <> c1.billing_account_id)::text
         || ' ' || (c2.commessa_id <> c1.commessa_id)::text
       FROM t_c1 c1, t_c2 c2),
    'true true true',
    'seconda chiamata: stessa azienda di chi agisce, cliente nuovo, commessa nuova'
);

SELECT * FROM finish();
ROLLBACK;
