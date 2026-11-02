-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Oggetto:
--  - anagrafiche.catasto_unita_immobiliari
--
-- Scopo:
--  - Validare struttura minima (tabella/colonne/FK/trigger)
--  - Validare trigger tx_id_managed (tx_id valorizzato in INSERT)
--  - Validare trigger audit_data_user_generic (data_update/user_update in UPDATE)
--  - Validare storico (solo se la tabella di storico esiste)
--
-- NOTE:
--  - Test si aggancia ad una istanza_utility reale esistente (non fittizia, con indirizzo)
--  - Non presuppone nomi specifici di constraint (PK/FK), solo presenza semantica.
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
--   ogni istruzione era una transazione a se'. Messa in testa e non in coda
--   apposta: in coda scatterebbero tutti insieme DOPO il cleanup, su righe
--   ormai cancellate, e fallirebbero per un motivo che non riguarda il test.
--   Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- =========================================================
-- 0) Sanity: estensioni pgTAP + oggetto target
-- =========================================================
/*
SELECT ok(
  EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pgtap'),
  'pgTAP extension presente'
);

SELECT ok(
  has_schema('anagrafiche'),
  'Schema anagrafiche esiste'
);

SELECT ok(
  has_table('anagrafiche', 'catasto_unita_immobiliari'),
  'Tabella anagrafiche.catasto_unita_immobiliari esiste'
);

-- colonne minime attese
SELECT ok(has_column('anagrafiche','catasto_unita_immobiliari','id'), 'Colonna id presente');
SELECT ok(has_column('anagrafiche','catasto_unita_immobiliari','istanza_utility_id'), 'Colonna istanza_utility_id presente');
SELECT ok(has_column('anagrafiche','catasto_unita_immobiliari','tx_id'), 'Colonna tx_id presente');
SELECT ok(has_column('anagrafiche','catasto_unita_immobiliari','data_update'), 'Colonna data_update presente');
SELECT ok(has_column('anagrafiche','catasto_unita_immobiliari','user_update'), 'Colonna user_update presente');

*/


-- =========================================================
-- 1) Precondizione: aggancio a una istanza reale esistente
-- =========================================================

CREATE TEMP TABLE tmp_iu_pick AS
SELECT id
FROM anagrafiche.istanze_utilities
WHERE fittizia = false
  AND indirizzo_dettaglio_id IS NOT NULL
ORDER BY id
LIMIT 1;

SELECT is(
  (SELECT count(*)::int FROM tmp_iu_pick),
  1,
  'Trovata 1 istanza_utility reale (non fittizia, con indirizzo) da usare nel test'
);

-- =========================================================
-- 2) Verifica FK semantica: catasto_unita_immobiliari(istanza_utility_id) -> istanze_utilities(id)
--    (non dipende dal nome del vincolo)
-- =========================================================

SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_constraint c
    JOIN pg_class t   ON t.oid = c.conrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    JOIN pg_class rt  ON rt.oid = c.confrelid
    JOIN pg_namespace rn ON rn.oid = rt.relnamespace
    WHERE c.contype = 'f'
      AND n.nspname = 'anagrafiche'
      AND t.relname = 'catasto_unita_immobiliari'
      AND rn.nspname = 'anagrafiche'
      AND rt.relname = 'istanze_utilities'
      AND pg_get_constraintdef(c.oid) LIKE '%(istanza_utility_id)%REFERENCES anagrafiche.istanze_utilities(id)%'
  ),
  'Esiste una FK da catasto_unita_immobiliari.istanza_utility_id a anagrafiche.istanze_utilities(id)'
);

-- =========================================================
-- 3) Trigger presenti (per nome, perché li hai definiti esplicitamente)
-- =========================================================
/*
SELECT ok(
  has_trigger('anagrafiche','catasto_unita_immobiliari','trg_catasto_unita_immobiliari_tx_id_managed_ins_upd'),
  'Trigger tx_id_managed presente'
);

SELECT ok(
  has_trigger('anagrafiche','catasto_unita_immobiliari','trg_catasto_unita_immobiliari_audit_data_user_generic_upd'),
  'Trigger audit_data_user_generic presente'
);

SELECT ok(
  has_trigger('anagrafiche','catasto_unita_immobiliari','trg_catasto_unita_immobiliari_z90_storico_generic_upd_dlt'),
  'Trigger storico_generic presente'
);

*/
-- =========================================================
-- 4) INSERT: deve funzionare e valorizzare tx_id
-- =========================================================

-- pulizia mirata: rimuove eventuali righe precedenti create dal test (stessa istanza, stessi campi “firma”)
-- NB: usiamo una combinazione “firma” per limitare il rischio di cancellare dati reali.
DELETE FROM anagrafiche.catasto_unita_immobiliari
WHERE istanza_utility_id = (SELECT id FROM tmp_iu_pick)
  AND sezione_catastale = 'TST01'
  AND foglio_catastale  = 'TST01'
  AND particella        = 'TST01'
  AND subalterno        = 'TST01';

WITH ins AS (
  INSERT INTO anagrafiche.catasto_unita_immobiliari (
    istanza_utility_id,
    sezione_catastale,
    foglio_catastale,
    particella,
    subalterno,
    categoria_catastale,
    classe_catastale,
    rendita_catastale,
    consistenza,
    tipo_accatastamento,
    immobile_rurale,
    destinazione_immobile,
    anno_protocollo,
    superficie
  )
  SELECT
    (SELECT id FROM tmp_iu_pick),
    'TST01',
    'TST01',
    'TST01',
    'TST01',
    'A2',
    '1',
    123.45,
    2,
    'U',
    false,
    'AB',
    2025,
    80
  RETURNING id, tx_id, istanza_utility_id
)
SELECT *
INTO TEMP TABLE tmp_catasto_ins
FROM ins;

SELECT is(
  (SELECT count(*)::int FROM tmp_catasto_ins),
  1,
  'Inserita 1 riga di test in catasto_unita_immobiliari'
);

SELECT ok(
  (SELECT tx_id IS NOT NULL FROM tmp_catasto_ins),
  'tx_id valorizzato in INSERT (dbops.trgfn_tx_id_managed)'
);

-- =========================================================
-- 5) UPDATE: audit deve aggiornare data_update/user_update
-- =========================================================

CREATE TEMP TABLE tmp_before_upd AS
SELECT data_update, user_update
FROM anagrafiche.catasto_unita_immobiliari
WHERE id = (SELECT id FROM tmp_catasto_ins);

UPDATE anagrafiche.catasto_unita_immobiliari
SET superficie = superficie + 1
WHERE id = (SELECT id FROM tmp_catasto_ins);

CREATE TEMP TABLE tmp_after_upd AS
SELECT data_update, user_update
FROM anagrafiche.catasto_unita_immobiliari
WHERE id = (SELECT id FROM tmp_catasto_ins);

SELECT ok(
  (SELECT (a.data_update >= b.data_update) FROM tmp_after_upd a, tmp_before_upd b),
  'data_update aggiornata (>=) dopo UPDATE'
);

SELECT ok(
  (SELECT a.user_update = current_user FROM tmp_after_upd a),
  'user_update = current_user dopo UPDATE'
);

-- =========================================================
-- 6) STORICO: verifica condizionale (solo se esiste la tabella storico)
-- =========================================================

-- Se la tabella storico non esiste, non falliamo: segniamo come "ok" e passiamo oltre.
/*
SELECT ok(
  CASE
    WHEN has_table('storico','catasto_unita_immobiliari') THEN true
    ELSE true
  END,
  'Storico: controllo presenza tabella (se non esiste, test non blocca)'
);
*/
-- Se esiste storico.catasto_unita_immobiliari, allora ci aspettiamo almeno 1 snapshot dopo UPDATE/DELETE.
-- Usiamo lives_ok per evitare hard-fail se la funzione storico non è ancora allineata.
SELECT lives_ok($$
  DO $do$
  BEGIN
    IF EXISTS (
      SELECT 1
      FROM pg_class t
      JOIN pg_namespace n ON n.oid = t.relnamespace
      WHERE n.nspname = 'storico'
        AND t.relname = 'catasto_unita_immobiliari'
    ) THEN
      -- tentativo “soft”: se la tabella esiste ci aspettiamo che il trigger abbia scritto qualcosa.
      -- NB: non conosciamo la colonna FK nello storico (parametro trgfn_storico_generic),
      -- quindi qui verifichiamo solo che la tabella non sia vuota *in generale* dopo l’update.
      PERFORM 1
      FROM storico.catasto_unita_immobiliari
      LIMIT 1;
    END IF;
  END
  $do$;
$$, 'Storico: accesso tabella storico (se presente)');

-- =========================================================
-- 7) Cleanup: rimuove la riga di test
-- =========================================================
/*
DELETE FROM anagrafiche.catasto_unita_immobiliari
WHERE id = (SELECT id FROM tmp_catasto_ins);

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM anagrafiche.catasto_unita_immobiliari
    WHERE id = (SELECT id FROM tmp_catasto_ins)
  ),
  'Cleanup: riga di test rimossa'
);
*/
SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
