-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_get_emittente_fiscale_id, l'azienda (il suo ruolo EF)
--   che fattura un billing account.
-- Oggetti: anagrafiche.fn_get_emittente_fiscale_id, anagrafiche.fn_check_billing_account_esiste.
-- Riferimento: brief-db-revisione-anagrafiche §25.3 (S54a), §25.9 (D-T8b-1).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - un BA risponde l'azienda del suo collegamento;
--   - nessun BA (NULL) risponde l'azienda predefinita: e' il giro del lotto,
--     che non ha un BA (vendite.fn_get_or_create_lotto ->
--     vendite.fn_resolve_lotto_utility_emittente);
--   - un id che non e' un BA -> E_BILLING_ACCOUNT_NOT_FOUND, in sessione e
--     senza: non riceve l'azienda dell'operatore ne' la predefinita;
--   - un id <= 0 -> E_PARAMETRO_INVALIDO (la forma del parametro);
--   - un BA fuori dal perimetro di chi chiama risponde la SUA azienda: il
--     controllo dell'esistenza e' SECURITY DEFINER.
--   I casi si COSTRUISCONO: due aziende, un cliente per ciascuna, l'id
--   inesistente calcolato oltre il massimo dei collegamenti.
--
-- Elenco test (plan 7):
--   1) PRECONDIZIONE: due aziende costruite, e B non e' la predefinita
--   2) il BA di B -> l'azienda B
--   3) NULL -> l'azienda predefinita
--   4) un id che non e' un BA, in sessione -> E_BILLING_ACCOUNT_NOT_FOUND
--   5) un id che non e' un BA, senza sessione -> E_BILLING_ACCOUNT_NOT_FOUND
--   6) 0 -> E_PARAMETRO_INVALIDO
--   7) il BA di A, chiesto dall'operatore di B -> l'azienda A
-- ------------------------------------------------------------

BEGIN;

-- ⛔ LE DUE AZIENDE SI COSTRUISCONO, in DUE istruzioni: l'ordine di creazione
--   e' portante (sullo scratch la prima diventa la predefinita).
CREATE TEMP TABLE _mondi AS
SELECT 'A'::text AS lato, m.*
  FROM dbops.fn_pgtap_crea_emittente_operatore() m;

INSERT INTO _mondi
SELECT 'B'::text, m.*
  FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- Il cliente di A lo crea l'operatore di A; poi il contesto passa a B.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'A'));
END $ctx$;

CREATE TEMP TABLE _t_cli_a AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('fiscale id di A');

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'B'));
END $ctx$;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

CREATE TEMP TABLE _t_cli_b AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('fiscale id di B');

-- La predefinita: al massimo una (uq_emittenti_fiscali_ba_default).
CREATE TEMP TABLE _t_def AS
SELECT d.emittente_soggetto_ruolo_id AS ef_sr_id
  FROM anagrafiche.emittenti_fiscali_billing_account d
 WHERE d.is_default;

-- Un id che non e' un BA: oltre il massimo dei collegamenti, che sono uno per
-- ogni BA e non hanno la RLS (il massimo di billing_account letto da qui
-- sarebbe quello dei soli BA visibili).
CREATE TEMP TABLE _t_ba_ignoto AS
SELECT COALESCE(MAX(efba.billing_account_id), 0) + 1000000 AS ba_id
  FROM anagrafiche.emittenti_fiscali_billing_account efba;

SELECT ok(
    (SELECT count(*) FROM _mondi) = 2
    AND (SELECT ef_sr_id FROM _t_def) IS DISTINCT FROM
        (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'B'),
    '1) PRECONDIZIONE: due aziende costruite, e B non e'' la predefinita');

SELECT is(
    anagrafiche.fn_get_emittente_fiscale_id((SELECT billing_account_id FROM _t_cli_b)),
    (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'B'),
    '2) il BA di B -> l''azienda B');

SELECT is(
    anagrafiche.fn_get_emittente_fiscale_id(NULL::bigint),
    (SELECT ef_sr_id FROM _t_def),
    '3) nessun BA (il giro del lotto) -> l''azienda predefinita');

SELECT is(
    dbops.fn_pgtap_codice_errore(
        format($$SELECT anagrafiche.fn_get_emittente_fiscale_id(%s)$$,
               (SELECT ba_id FROM _t_ba_ignoto))),
    'E_BILLING_ACCOUNT_NOT_FOUND',
    '4) un id che non e'' un BA, in sessione -> E_BILLING_ACCOUNT_NOT_FOUND (non l''azienda dell''operatore)');

-- Senza sessione: si svuota la sola GUC dell'utente, e la si rimette.
SELECT set_config('app.current_user_id', '', true);

SELECT is(
    dbops.fn_pgtap_codice_errore(
        format($$SELECT anagrafiche.fn_get_emittente_fiscale_id(%s)$$,
               (SELECT ba_id FROM _t_ba_ignoto))),
    'E_BILLING_ACCOUNT_NOT_FOUND',
    '5) un id che non e'' un BA, senza sessione -> E_BILLING_ACCOUNT_NOT_FOUND (non la predefinita)');

SELECT set_config('app.current_user_id',
                  (SELECT auth_user_id::text FROM _mondi WHERE lato = 'B'),
                  true);

SELECT is(
    dbops.fn_pgtap_codice_errore(
        $$SELECT anagrafiche.fn_get_emittente_fiscale_id(0::bigint)$$),
    'E_PARAMETRO_INVALIDO',
    '6) 0 -> E_PARAMETRO_INVALIDO (la forma del parametro)');

SELECT is(
    anagrafiche.fn_get_emittente_fiscale_id((SELECT billing_account_id FROM _t_cli_a)),
    (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'A'),
    '7) il BA di A, chiesto dall''operatore di B -> l''azienda A, non E_BILLING_ACCOUNT_NOT_FOUND');

SELECT * FROM finish();
ROLLBACK;
