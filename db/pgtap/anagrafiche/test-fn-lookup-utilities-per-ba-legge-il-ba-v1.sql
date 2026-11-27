-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il lookup delle utility di un billing account legge il billing account.
-- Oggetti: anagrafiche.fn_lookup_utilities_per_ba (20261126-39, 20261126-42).
-- Riferimento: brief-db-revisione-anagrafiche §24.5 (S32), §24.9.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - un id che non e' un billing account -> E_BILLING_ACCOUNT_NOT_FOUND:
--     la cosa indicata non esiste (prima del -39 ricadeva sulla predefinita
--     e rispondeva; col -39 era E_PARAMETRO_INVALIDO);
--   - un ruolo che non e' quello del billing account -> E_PARAMETRO_INVALIDO;
--   - il ruolo del billing account -> la funzione risponde.
--   I casi si COSTRUISCONO: il BA e il suo ruolo li fabbrica il mondo del
--   cliente, l'id inesistente si calcola oltre il massimo.
--
-- Elenco test (plan 3):
--   1) un id che non e' un billing account -> E_BILLING_ACCOUNT_NOT_FOUND
--   2) il BA del mondo con un ruolo che non e' il suo -> E_PARAMETRO_INVALIDO
--   3) il BA del mondo col suo ruolo -> risponde
-- ------------------------------------------------------------

BEGIN;

-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_mondo_cliente.
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('lookup legge il ba');

CREATE TEMP TABLE _t_ref AS
SELECT m.billing_account_id AS ba_id,
       (SELECT tr.codice_interno::text
          FROM anagrafiche.billing_account ba
          JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ba.soggetto_ruolo_id
          JOIN config.tipi_ruoli tr          ON tr.id = sr.tipo_ruolo_id
         WHERE ba.id = m.billing_account_id) AS ruolo,
       (SELECT COALESCE(max(id), 0) + 1000 FROM anagrafiche.billing_account) AS ba_inesistente
  FROM _t_mondo m;

-- Un ruolo che non e' quello del BA: un altro codice_interno a catalogo.
CREATE TEMP TABLE _t_altro AS
SELECT (SELECT tr.codice_interno::text FROM config.tipi_ruoli tr
         WHERE tr.codice_interno <> (SELECT ruolo FROM _t_ref)
         ORDER BY tr.id LIMIT 1) AS ruolo_altro;

SELECT is(
    dbops.fn_pgtap_codice_errore(
        format($$SELECT * FROM anagrafiche.fn_lookup_utilities_per_ba(%s, %L)$$,
               (SELECT ba_inesistente FROM _t_ref), (SELECT ruolo FROM _t_ref))),
    'E_BILLING_ACCOUNT_NOT_FOUND',
    '1) un id che non e'' un billing account -> E_BILLING_ACCOUNT_NOT_FOUND');

SELECT is(
    dbops.fn_pgtap_codice_errore(
        format($$SELECT * FROM anagrafiche.fn_lookup_utilities_per_ba(%s, %L)$$,
               (SELECT ba_id FROM _t_ref), (SELECT ruolo_altro FROM _t_altro))),
    'E_PARAMETRO_INVALIDO',
    '2) un ruolo che non e'' quello del BA -> E_PARAMETRO_INVALIDO');

SELECT lives_ok(
    format($$SELECT * FROM anagrafiche.fn_lookup_utilities_per_ba(%s, %L)$$,
           (SELECT ba_id FROM _t_ref), (SELECT ruolo FROM _t_ref)),
    '3) il BA col suo ruolo -> risponde');

SELECT * FROM finish();
ROLLBACK;
