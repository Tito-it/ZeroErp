-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Regola: articoli "solo componente" non possono essere prodotti
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

SELECT plan(5);

CREATE TEMP TABLE tmp_seed AS
SELECT
  (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_BASE') AS prodotto_id,
  (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_FALLBACK') AS componente_id,
  (SELECT is_solo_componente FROM catalogo.articoli WHERE codice = 'ART_TEST_BASE') AS prodotto_solo,
  (SELECT is_solo_componente FROM catalogo.articoli WHERE codice = 'ART_TEST_FALLBACK') AS componente_solo;

SELECT ok(
  (SELECT prodotto_id IS NOT NULL FROM tmp_seed),
  'Seed prodotto presente'
);

SELECT ok(
  (SELECT componente_id IS NOT NULL FROM tmp_seed),
  'Seed componente presente'
);

UPDATE catalogo.articoli
SET is_solo_componente = true
WHERE id = (SELECT prodotto_id FROM tmp_seed);

SELECT throws_ok(
  $$
  INSERT INTO catalogo.articoli_componenti (
    prodotto_id,
    componente_id,
    coeff_qta,
    partecipa_qta,
    obbligatorio,
    valido_dal,
    valido_al,
    attivo
  )
  VALUES (
    (SELECT prodotto_id FROM tmp_seed),
    (SELECT componente_id FROM tmp_seed),
    1,
    false,
    true,
    DATE '2026-03-01',
    DATE '2026-03-31',
    true
  );
  $$,
  NULL,
  NULL,
  'Prodotto solo componente: inserimento bloccato'
);

UPDATE catalogo.articoli
SET is_solo_componente = (SELECT prodotto_solo FROM tmp_seed)
WHERE id = (SELECT prodotto_id FROM tmp_seed);

UPDATE catalogo.articoli
SET is_solo_componente = (SELECT componente_solo FROM tmp_seed)
WHERE id = (SELECT componente_id FROM tmp_seed);

SELECT lives_ok(
  $$
  DO $do$
  DECLARE v_id uuid;
  BEGIN
    INSERT INTO catalogo.articoli_componenti (
      prodotto_id,
      componente_id,
      coeff_qta,
      partecipa_qta,
      obbligatorio,
      valido_dal,
      valido_al,
      attivo
    )
    VALUES (
      (SELECT prodotto_id FROM tmp_seed),
      (SELECT componente_id FROM tmp_seed),
      1,
      false,
      true,
      DATE '2026-04-01',
      DATE '2026-04-30',
      true
    )
    RETURNING id INTO v_id;

    DELETE FROM catalogo.articoli_componenti WHERE id = v_id;
  END $do$;
  $$,
  'Prodotto valido: inserimento consentito'
);

UPDATE catalogo.articoli
SET is_solo_componente = true
WHERE id = (SELECT componente_id FROM tmp_seed);

SELECT lives_ok(
  $$
  DO $do$
  DECLARE v_id uuid;
  BEGIN
    INSERT INTO catalogo.articoli_componenti (
      prodotto_id,
      componente_id,
      coeff_qta,
      partecipa_qta,
      obbligatorio,
      valido_dal,
      valido_al,
      attivo
    )
    VALUES (
      (SELECT prodotto_id FROM tmp_seed),
      (SELECT componente_id FROM tmp_seed),
      1,
      false,
      true,
      DATE '2026-05-01',
      DATE '2026-05-31',
      true
    )
    RETURNING id INTO v_id;

    DELETE FROM catalogo.articoli_componenti WHERE id = v_id;
  END $do$;
  $$,
  'Componente solo componente: inserimento consentito'
);

-- Restore flags
UPDATE catalogo.articoli
SET is_solo_componente = (SELECT prodotto_solo FROM tmp_seed)
WHERE id = (SELECT prodotto_id FROM tmp_seed);

UPDATE catalogo.articoli
SET is_solo_componente = (SELECT componente_solo FROM tmp_seed)
WHERE id = (SELECT componente_id FROM tmp_seed);

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
