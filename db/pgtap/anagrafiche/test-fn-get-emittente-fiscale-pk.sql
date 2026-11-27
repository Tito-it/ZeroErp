-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_get_emittente_fiscale_pk
-- ⭐ Rev 2026-09-13 (D13, brief-db-ba-riserva-emittente-operatore-d13.md):
--   dal 20260913-03 la funzione DELEGA la regola a
--   script.fn_get_ba_emittente_sr_id — tre livelli: mapping specifico; in
--   sessione, l'emittente dell'operatore; senza sessione, il default. Il
--   test 6 si spezza in due (6, 7) e il mondo SI COSTRUISCE: il file stava
--   nel registro dei rossi della CI perche' cercava emittente e mapping fra i
--   dati esistenti, e su un database ricostruito dai changelog non ce ne sono.
-- ⭐ Rev 2026-11-27 (brief-db-revisione-anagrafiche §25.9, D-T8b-1, 20261126-85):
--   un id che non e' un billing account non riceve piu' i livelli 2 e 3 del
--   lettore: e' E_BILLING_ACCOUNT_NOT_FOUND, in sessione e senza. I livelli 2
--   e 3 restano del lettore, e li prova il suo test
--   (script/test-ba-emittente-risoluzione-v1). Il controllo dell'esistenza
--   e' SECURITY DEFINER: un BA fuori dal perimetro di chi chiama risponde la
--   sua azienda (test 11).
--
-- Elenco test (plan 11):
--  1) Funzione presente con firma corretta
--  2) PRECONDIZIONE: due aziende costruite, e B NON e' il default
--  3) Guard input: NULL solleva un errore di dominio (E_PARAMETRO_INVALIDO)
--  4) Guard input: <= 0 solleva un errore di dominio (E_PARAMETRO_INVALIDO)
--  5) BA con mapping specifico -> la PK di quell'emittente (livello 1)
--  6) ⭐ un id che non e' un BA, IN SESSIONE -> E_BILLING_ACCOUNT_NOT_FOUND
--  7) ⭐ un id che non e' un BA, SENZA sessione -> E_BILLING_ACCOUNT_NOT_FOUND
--  8) Il valore restituito e' davvero emittenti_fiscali.id (PK reale)
--  9) La delega e' esatta: PK -> soggetto_ruolo coincide con il lettore
-- 10) Il corpo non riscrive piu' la regola: nomina il lettore e non is_default
-- 11) ⭐ un BA fuori dal perimetro di chi chiama -> la PK della SUA azienda
--
-- Scopo:
--  ⚠️ Fino al 2026-09-13 questa funzione teneva una COPIA della regola a due
--     livelli (mapping, altrimenti default). Con il terzo livello del lettore
--     le due copie avrebbero risposto cose diverse sullo stesso BA senza
--     legame: la RLS lo mostra all'operatore, il guard del preventivo (che
--     passa da qui) lo rifiuta. Il test 10 e' il presidio anti-ritorno della
--     copia; il 9 dice che la delega non ha perso niente per strada.
--  ⚠️ Il 6 e il 7 provano che NESSUNO dei due livelli di riserva risponde:
--     per questo l'operatore di contesto NON e' quello del default (sullo
--     scratch della CI il PRIMO emittente creato diventa il default per
--     bootstrap, quindi le aziende sono due e il contesto e' della seconda).
--     Il test 2 lo asserisce. L'11 vuole un BA dell'altra azienda (A): lo
--     crea l'operatore di A, poi il contesto torna a B.
-- ------------------------------------------------------------

BEGIN;

-- ⛔ LE DUE AZIENDE SI COSTRUISCONO, in DUE istruzioni: l'ordine di creazione
--   e' portante (sullo scratch la prima diventa il default) e in una UNION
--   ALL l'ordine dei rami e' del planner, non del test.
CREATE TEMP TABLE _mondi AS
SELECT 'A'::text AS lato, m.*
  FROM dbops.fn_pgtap_crea_emittente_operatore() m;

INSERT INTO _mondi
SELECT 'B'::text, m.*
  FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- Contesto applicativo: l'operatore di B (ruolo OPERATORE + RLS attiva).
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'B'));
END $ctx$;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   L'helper esce gia' IMMEDIATE; la riga sta qui perche' e' il preambolo
--   obbligatorio, e la fixture del cliente li riapre e richiude da sola.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture
-- ============================================================
-- Un cliente costruito NEL contesto di B: il legame lo scrive il trigger z90
-- verso l'emittente di chi agisce. E' il mapping specifico del test 5.
CREATE TEMP TABLE _t_cli ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('fiscale pk');

-- Un cliente dell'azienda A, creato dal suo operatore: per B e' fuori dal
-- perimetro (test 11). Poi il contesto torna a B.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'A'));
END $ctx$;

CREATE TEMP TABLE _t_cli_a ON COMMIT DROP AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('fiscale pk di A');

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM _mondi WHERE lato = 'B'));
END $ctx$;

-- La PK dell'emittente di default, se c'e'. Al massimo uno.
CREATE TEMP TABLE _t_def ON COMMIT DROP AS
SELECT ef.id AS ef_id, d.emittente_soggetto_ruolo_id AS ef_sr_id
  FROM anagrafiche.emittenti_fiscali_billing_account d
  JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = d.emittente_soggetto_ruolo_id
 WHERE d.is_default;

-- Un billing_account_id che NON esiste. Si calcola dai collegamenti, che non
-- hanno la RLS e sono uno per ogni BA: il massimo di anagrafiche.billing_account
-- letto da qui sarebbe quello dei soli BA visibili.
CREATE TEMP TABLE _t_ba_ignoto ON COMMIT DROP AS
SELECT COALESCE(MAX(efba.billing_account_id), 0) + 1000000 AS ba_id
  FROM anagrafiche.emittenti_fiscali_billing_account efba;

-- ============================================================
-- 1) Funzione presente
-- ============================================================
SELECT has_function(
    'anagrafiche', 'fn_get_emittente_fiscale_pk',
    ARRAY['bigint'],
    '1) fn_get_emittente_fiscale_pk presente con firma (bigint)'
);

-- ============================================================
-- 2) PRECONDIZIONE
-- ============================================================
SELECT ok(
    (SELECT count(*) FROM _mondi) = 2
    AND (SELECT ef_sr_id FROM _t_def) IS DISTINCT FROM
        (SELECT soggetto_ruolo_id FROM _mondi WHERE lato = 'B'),
    '2) PRECONDIZIONE: due aziende costruite, e B non e'' l''emittente di default'
);

-- ============================================================
-- 3-4) Guard input — un errore si ASSERISCE: P0001 e' l'errore di dominio
--      di fn_log_and_raise_error, e la frase e' quella del guard.
-- ============================================================
SELECT throws_like(
    $$ SELECT anagrafiche.fn_get_emittente_fiscale_pk(NULL::bigint) $$,
    '%obbligatorio%',
    '3) NULL solleva l''errore di dominio del guard (E_PARAMETRO_INVALIDO)'
);

SELECT throws_like(
    $$ SELECT anagrafiche.fn_get_emittente_fiscale_pk(0::bigint) $$,
    '%obbligatorio%',
    '4) 0 solleva l''errore di dominio del guard (E_PARAMETRO_INVALIDO)'
);

-- ============================================================
-- 5) Livello 1: il mapping specifico
-- ============================================================
SELECT is(
    anagrafiche.fn_get_emittente_fiscale_pk((SELECT billing_account_id FROM _t_cli)),
    (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'B'),
    '5) BA con mapping specifico -> la PK di quell''emittente (livello 1)'
);

-- ============================================================
-- 6-7) ⭐ Un id che non e' un BA: rifiutato, in sessione e senza. Prima
--      rispondeva l'azienda dell'operatore (in sessione) o la predefinita
--      (senza): un id sbagliato del chiamante diventava un'azienda.
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(
        format($$SELECT anagrafiche.fn_get_emittente_fiscale_pk(%s)$$,
               (SELECT ba_id FROM _t_ba_ignoto))),
    'E_BILLING_ACCOUNT_NOT_FOUND',
    '6) un id che non e'' un BA, IN SESSIONE -> E_BILLING_ACCOUNT_NOT_FOUND (non l''azienda dell''operatore)'
);

SELECT set_config('app.current_user_id', '', true);

SELECT is(
    dbops.fn_pgtap_codice_errore(
        format($$SELECT anagrafiche.fn_get_emittente_fiscale_pk(%s)$$,
               (SELECT ba_id FROM _t_ba_ignoto))),
    'E_BILLING_ACCOUNT_NOT_FOUND',
    '7) un id che non e'' un BA, SENZA sessione -> E_BILLING_ACCOUNT_NOT_FOUND (non la predefinita)'
);

SELECT set_config('app.current_user_id',
                  (SELECT auth_user_id::text FROM _mondi WHERE lato = 'B'),
                  true);

-- ============================================================
-- 8) Il valore ritornato e' davvero emittenti_fiscali.id
-- ============================================================
SELECT ok(
    EXISTS(
        SELECT 1
          FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.id = anagrafiche.fn_get_emittente_fiscale_pk((SELECT billing_account_id FROM _t_cli))
    ),
    '8) valore restituito esiste come PK in anagrafiche.emittenti_fiscali'
);

-- ============================================================
-- 9) La delega e' ESATTA: PK -> soggetto_ruolo coincide con cio' che il
--    lettore risponde. Se la funzione tornasse a riscrivere la regola,
--    questo e' il primo confronto a dissentire.
-- ============================================================
SELECT ok(
    (SELECT ef.soggetto_ruolo_id FROM anagrafiche.emittenti_fiscali ef
      WHERE ef.id = anagrafiche.fn_get_emittente_fiscale_pk((SELECT billing_account_id FROM _t_cli)))
        = script.fn_get_ba_emittente_sr_id((SELECT billing_account_id FROM _t_cli)),
    '9) la delega e'' esatta: PK -> soggetto_ruolo coincide con script.fn_get_ba_emittente_sr_id'
);

-- ============================================================
-- 10) Presidio anti-copia: il corpo nomina il lettore e NON is_default.
--     Una regola in due posti diverge alla prima modifica, in silenzio —
--     e' successo proprio qui (rev 20260913-03).
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'anagrafiche'
           AND p.proname = 'fn_get_emittente_fiscale_pk'
           AND p.prosrc LIKE '%script.fn_get_ba_emittente_sr_id(%'
           AND p.prosrc NOT LIKE '%is_default%'
    ),
    '10) il corpo delega a script.fn_get_ba_emittente_sr_id e non nomina is_default'
);

-- ============================================================
-- 11) ⭐ Il controllo dell'esistenza vede ogni BA, non solo quelli del
--     perimetro di chi chiama: un BA di A, chiesto dall'operatore di B,
--     risponde l'azienda A. La funzione decide CHI fattura, non chi vede.
-- ============================================================
SELECT is(
    anagrafiche.fn_get_emittente_fiscale_pk((SELECT billing_account_id FROM _t_cli_a)),
    (SELECT emittente_fiscale_id FROM _mondi WHERE lato = 'A'),
    '11) un BA fuori dal perimetro di chi chiama -> la PK della sua azienda, non E_BILLING_ACCOUNT_NOT_FOUND'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
