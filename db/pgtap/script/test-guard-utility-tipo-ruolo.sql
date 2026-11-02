-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Elenco test:
-- 1) Esiste almeno una utility in config.utilities
-- 2) Esistono almeno due tipi ruolo in config.tipi_ruoli
-- 3) Esiste una utility senza matrice attiva/valida (precondizione fail-open)
-- 4) Con utility senza matrice, il guard passa (fail-open)
-- 5) Inserita regola utility->ruolo ammesso
-- 6) Con matrice presente, il ruolo ammesso passa
-- 7) Con matrice presente, ruolo non ammesso viene bloccato
-- 8) Regola non attiva non abilita il ruolo
-- 9) Regola fuori validita non abilita il ruolo
-- 10) Duplicato utility+tipo_ruolo bloccato da UNIQUE
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. In testa e non in coda apposta:
--   in coda scatterebbero tutti insieme DOPO il cleanup, su righe ormai
--   cancellate. Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(10);

-- 1) Utility disponibili
CREATE TEMP TABLE tmp_utilities AS
SELECT id
FROM config.utilities
ORDER BY id;

SELECT ok(
  (SELECT count(*) FROM tmp_utilities) >= 1,
  'Esiste almeno una utility in config.utilities'
);

-- 2) Tipi ruolo disponibili
CREATE TEMP TABLE tmp_tipi_ruoli AS
SELECT id
FROM config.tipi_ruoli
ORDER BY id;

SELECT ok(
  (SELECT count(*) FROM tmp_tipi_ruoli) >= 2,
  'Esistono almeno due tipi ruolo in config.tipi_ruoli'
);

-- 3) Utility senza matrice attiva/valida
-- 🔴 PRECONDIZIONE COSTRUITA, non cercata — 2026-08-18.
--   Questa fixture cercava «una utility senza matrice attiva/valida» e si
--   affidava al fatto che in sviluppo ce ne fosse una. Non ce n'e' piu':
--   la ricerca tornava vuota, `utility_id` usciva NULL e l'INSERT sotto moriva
--   sul NOT NULL — 4 asserzioni su 12.
--
--   ⚠️ Terza occorrenza dello stesso difetto in questo giro (con
--   test-fn-change-user-emittenti-scope e test-fn-get-user-emittenti-scope):
--   una fixture che CERCA la propria precondizione invece di costruirla smette
--   di funzionare il giorno in cui qualcuno sistema i dati — cioe' viene punita
--   da un miglioramento.
--
--   Qui la si costruisce: si prende la prima utility e le si toglie la matrice.
--   Il file e' transazionale, la matrice vera torna al ROLLBACK.
DELETE FROM config.utilities_tipi_ruolo m
 WHERE m.utility_id = (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1);

CREATE TEMP TABLE tmp_utility_no_matrix AS
SELECT u.id AS utility_id
FROM config.utilities u
WHERE NOT EXISTS (
  SELECT 1
  FROM config.utilities_tipi_ruolo m
  WHERE m.utility_id = u.id
    AND m.attivo = true
    AND (m.valido_dal IS NULL OR m.valido_dal <= script.fn_data_operativa())
    AND (m.valido_al IS NULL OR m.valido_al >= script.fn_data_operativa())
)
ORDER BY u.id
LIMIT 1;

SELECT is(
  (SELECT count(*)::int FROM tmp_utility_no_matrix),
  1,
  'Esiste una utility senza matrice attiva/valida (precondizione fail-open)'
);

-- Ruoli per test: uno ammesso e uno negato
CREATE TEMP TABLE tmp_ruoli_ctx AS
WITH r AS (
  SELECT id, row_number() OVER (ORDER BY id) AS rn
  FROM config.tipi_ruoli
)
SELECT
  (SELECT id FROM r WHERE rn = 1) AS tipo_ruolo_allow_id,
  (SELECT id FROM r WHERE rn = 2) AS tipo_ruolo_deny_id;

-- 4) Fail-open: nessuna matrice -> consentito
SELECT lives_ok(
  format(
    $$SELECT script.fn_guard_utility_tipo_ruolo(%s, %s, 'pgtap_fail_open');$$,
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_allow_id FROM tmp_ruoli_ctx)
  ),
  'Con utility senza matrice, il guard passa (fail-open)'
);

-- 5) Inserimento regola utility->ruolo ammesso
CREATE TEMP TABLE tmp_rule_allow AS
WITH ins AS (
  INSERT INTO config.utilities_tipi_ruolo (
    utility_id,
    tipo_ruolo_id,
    attivo,
    valido_dal,
    valido_al
  )
  SELECT
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_allow_id FROM tmp_ruoli_ctx),
    true,
    NULL::date,
    NULL::date
  RETURNING id
)
SELECT * FROM ins;

SELECT is(
  (SELECT count(*)::int FROM tmp_rule_allow),
  1,
  'Inserita regola utility->ruolo ammesso'
);

-- 6) Con matrice presente, ruolo ammesso -> passa
SELECT lives_ok(
  format(
    $$SELECT script.fn_guard_utility_tipo_ruolo(%s, %s, 'pgtap_allow');$$,
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_allow_id FROM tmp_ruoli_ctx)
  ),
  'Con matrice presente, il ruolo ammesso passa'
);

-- 7) Con matrice presente, ruolo non ammesso -> blocco
SELECT throws_ok(
  format(
    $$SELECT script.fn_guard_utility_tipo_ruolo(%s, %s, 'pgtap_deny');$$,
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx)
  ),
  'P0001',
  -- 🔴 FRASE AGGIORNATA il 2026-08-18. Il guard funziona e blocca: era il suo
  --   MESSAGGIO a essere cambiato, da quando l'errore passa per
  --   script.fn_log_and_raise_error e prende il testo dal catalogo.
  --   ⚠️ Asserire la FRASE e' fragile per costruzione: si rompe a ogni
  --   riscrittura del messaggio, e non verifica cio' che conta. La forma
  --   durevole e' leggere il canale strutturato (CONSTRAINT = codice di
  --   dominio) con GET STACKED DIAGNOSTICS, come in
  --   db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1 (test 8-9).
  --   Qui si allinea la frase e si lascia scritto il debito: cambiarne la
  --   forma e' una slice a se', non una riga di questa pulizia.
  format(
    'Tipo ruolo %2$s non ammesso per utility %1$s in base alla matrice configurata.',
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx)
  ),
  'Con matrice presente, ruolo non ammesso viene bloccato'
);

-- 8) Regola non attiva non abilita il ruolo deny
INSERT INTO config.utilities_tipi_ruolo (
  utility_id,
  tipo_ruolo_id,
  attivo,
  valido_dal,
  valido_al
)
SELECT
  (SELECT utility_id FROM tmp_utility_no_matrix),
  (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx),
  false,
  NULL::date,
  NULL::date;

SELECT throws_ok(
  format(
    $$SELECT script.fn_guard_utility_tipo_ruolo(%s, %s, 'pgtap_deny_inactive');$$,
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx)
  ),
  'P0001',
  -- 🔴 FRASE AGGIORNATA il 2026-08-18. Il guard funziona e blocca: era il suo
  --   MESSAGGIO a essere cambiato, da quando l'errore passa per
  --   script.fn_log_and_raise_error e prende il testo dal catalogo.
  --   ⚠️ Asserire la FRASE e' fragile per costruzione: si rompe a ogni
  --   riscrittura del messaggio, e non verifica cio' che conta. La forma
  --   durevole e' leggere il canale strutturato (CONSTRAINT = codice di
  --   dominio) con GET STACKED DIAGNOSTICS, come in
  --   db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1 (test 8-9).
  --   Qui si allinea la frase e si lascia scritto il debito: cambiarne la
  --   forma e' una slice a se', non una riga di questa pulizia.
  format(
    'Tipo ruolo %2$s non ammesso per utility %1$s in base alla matrice configurata.',
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx)
  ),
  'Regola non attiva non abilita il ruolo'
);

-- 9) Regola fuori validita non abilita il ruolo deny
UPDATE config.utilities_tipi_ruolo
SET attivo = true,
    valido_dal = script.fn_data_operativa() + 1,
    valido_al = NULL
WHERE utility_id = (SELECT utility_id FROM tmp_utility_no_matrix)
  AND tipo_ruolo_id = (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx);

SELECT throws_ok(
  format(
    $$SELECT script.fn_guard_utility_tipo_ruolo(%s, %s, 'pgtap_deny_out_of_validity');$$,
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx)
  ),
  'P0001',
  -- 🔴 FRASE AGGIORNATA il 2026-08-18. Il guard funziona e blocca: era il suo
  --   MESSAGGIO a essere cambiato, da quando l'errore passa per
  --   script.fn_log_and_raise_error e prende il testo dal catalogo.
  --   ⚠️ Asserire la FRASE e' fragile per costruzione: si rompe a ogni
  --   riscrittura del messaggio, e non verifica cio' che conta. La forma
  --   durevole e' leggere il canale strutturato (CONSTRAINT = codice di
  --   dominio) con GET STACKED DIAGNOSTICS, come in
  --   db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1 (test 8-9).
  --   Qui si allinea la frase e si lascia scritto il debito: cambiarne la
  --   forma e' una slice a se', non una riga di questa pulizia.
  format(
    'Tipo ruolo %2$s non ammesso per utility %1$s in base alla matrice configurata.',
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_deny_id FROM tmp_ruoli_ctx)
  ),
  'Regola fuori validita non abilita il ruolo'
);

-- 10) Duplicato utility+tipo_ruolo -> UNIQUE
SELECT throws_ok(
  format(
    $$INSERT INTO config.utilities_tipi_ruolo(utility_id, tipo_ruolo_id, attivo)
      VALUES (%s, %s, true);$$,
    (SELECT utility_id FROM tmp_utility_no_matrix),
    (SELECT tipo_ruolo_allow_id FROM tmp_ruoli_ctx)
  ),
  '23505',
  NULL,
  'Duplicato utility+tipo_ruolo bloccato da UNIQUE'
);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
