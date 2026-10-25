-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test fn_get_or_create_indirizzo_dettaglio (building block):
--   1. Precondizioni: stradario di test esiste
--   2. Creazione nuovo civico con successo
--   3. Get civico esistente (stessa chiave → stesso id)
--   4. Creazione civico con dettagli completi (estensione, palazzina, scala, piano, interno)
--   5. Civico diverso nella stessa via → id diverso
--   6. Verifica indirizzo_normalizzato calcolato dal trigger
--   7. Errore: p_stradario_id NULL
--   8. Errore: p_stradario_id <= 0
--   9. Errore: stradario inesistente
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

SELECT plan(9);

-- =========================================================
-- Setup: trovare uno stradario attivo di test
-- =========================================================
CREATE TEMP TABLE tmp_ind_det_ctx (
    stradario_id   integer,
    civico_id_1    bigint,
    civico_id_2    bigint,
    civico_id_3    bigint
);

INSERT INTO tmp_ind_det_ctx (stradario_id)
SELECT id FROM config.stradario ORDER BY id LIMIT 1;

-- =========================================================
-- 1) Precondizioni: stradario di test esiste
-- =========================================================
SELECT ok(
    (SELECT stradario_id FROM tmp_ind_det_ctx) IS NOT NULL,
    '1. Stradario di test esiste in config.stradario'
  );

-- =========================================================
-- 2) Creazione nuovo civico con successo
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        p_stradario_id := %s,
        p_civico := 99990
      ) $$,
      (SELECT stradario_id FROM tmp_ind_det_ctx)
    ),
    '2. Creazione civico 99990 eseguita senza errori'
  );

-- Salva id creato
UPDATE tmp_ind_det_ctx
SET civico_id_1 = (
    SELECT id FROM anagrafiche.indirizzi_dettaglio
    WHERE stradario_id = (SELECT stradario_id FROM tmp_ind_det_ctx)
      AND civico = 99990
      AND COALESCE(estensione_civico, '') = ''
      AND COALESCE(palazzina, '') = ''
      AND COALESCE(scala, '') = ''
      AND COALESCE(piano, '') = ''
      AND COALESCE(interno, '') = ''
  );

-- =========================================================
-- 3) Get civico esistente (stessa chiave → stesso id)
-- =========================================================
SELECT is(
    anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        p_stradario_id := (SELECT stradario_id FROM tmp_ind_det_ctx),
        p_civico := 99990
    ),
    (SELECT civico_id_1 FROM tmp_ind_det_ctx),
    '3. Get civico esistente restituisce lo stesso id'
  );

-- =========================================================
-- 4) Creazione civico con dettagli completi
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        p_stradario_id := %s,
        p_civico := 99990,
        p_estensione_civico := 'A',
        p_palazzina := 'B',
        p_scala := '1',
        p_piano := '2',
        p_interno := '3'
      ) $$,
      (SELECT stradario_id FROM tmp_ind_det_ctx)
    ),
    '4. Creazione civico con dettagli completi senza errori'
  );

-- Salva secondo id
-- ⚠️ rev 2026-10-25: il trigger salva l'estensione col prefisso '/' ('A' ->
--   '/A'). La ricerca su 'A' non trovava niente, civico_id_2 restava NULL e il
--   test 5 confrontava un id con NULL: verde per sottrazione. Brief:
--   brief-db-unicita-civico-indirizzi-dettaglio.
UPDATE tmp_ind_det_ctx
SET civico_id_2 = (
    SELECT id FROM anagrafiche.indirizzi_dettaglio
    WHERE stradario_id = (SELECT stradario_id FROM tmp_ind_det_ctx)
      AND civico = 99990
      AND estensione_civico = '/A'
      AND palazzina = 'B'
  );

-- =========================================================
-- 5) Civico diverso nella stessa via → id diverso
-- =========================================================
SELECT ok(
    (SELECT civico_id_2 IS NOT NULL AND civico_id_2 <> civico_id_1 FROM tmp_ind_det_ctx),
    '5. Civico con dettagli diversi produce id diverso (e il secondo esiste)'
  );

-- =========================================================
-- 6) Verifica indirizzo_normalizzato calcolato dal trigger
-- =========================================================
SELECT ok(
    (SELECT indirizzo_normalizzato FROM anagrafiche.indirizzi_dettaglio
     WHERE id = (SELECT civico_id_1 FROM tmp_ind_det_ctx)
    ) IS NOT NULL,
    '6. indirizzo_normalizzato calcolato dal trigger (non NULL)'
  );

-- =========================================================
-- 7) Errore: p_stradario_id NULL
-- =========================================================
SELECT throws_matching(
    $$SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
      p_stradario_id := NULL
    ) $$,
    'p_stradario_id obbligatorio',
    '7. Errore p_stradario_id NULL'
  );

-- =========================================================
-- 8) Errore: p_stradario_id <= 0
-- =========================================================
SELECT throws_matching(
    $$SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
      p_stradario_id := 0
    ) $$,
    'p_stradario_id obbligatorio',
    '8. Errore p_stradario_id = 0'
  );

-- =========================================================
-- 9) Errore: stradario inesistente
-- =========================================================
-- ⚠️ Il messaggio a catalogo dice «non e' stato trovato», non «non trovato»: il
--   test inseguiva una formulazione vecchia e falliva su un ramo SANO. Il
--   pattern e' una regexp e nomina anche il codice cercato e la tabella, cosi'
--   non puo' essere soddisfatto da un errore qualunque che contenga «trovato».
--   ⛔ `throws_matching` non prende lo SQLSTATE: questa asserzione accetta
--   qualunque eccezione il cui testo combaci. E' il debito che il cancello dei
--   pgTAP presidia a soglia — qui resta perche' il messaggio e' l'oggetto del
--   test, ma se un giorno serve stringere, la forma e' throws_ok con 'P0001'.
SELECT throws_matching(
    $$SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
      p_stradario_id := 999999999
    ) $$,
    '999999999 non .* stato trovato.*config\.stradario',
    '9. Errore stradario inesistente'
  );

SELECT * FROM finish();
ROLLBACK;
