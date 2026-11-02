-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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

-- 🔴 ARTICOLI PROPRI invece dei condivisi ART_TEST_* — 2026-08-18.
--   `ART_TEST_BASE` non e' composito, quindi il guard rifiutava di appendergli
--   un componente e i test 4 e 5 non potevano riuscire. Non e' un difetto del
--   guard: e' la fixture che assume su un articolo CONDIVISO una proprieta'
--   che quell'articolo non ha — e non deve avere, essendo la base di mezza
--   suite. Stessa radice degli altri quattro test di questa cartella.
CREATE OR REPLACE FUNCTION pg_temp.mk_articolo(p_codice text, p_composito boolean,
                                               p_solo_componente boolean)
RETURNS uuid AS $mk$
DECLARE v_id uuid;
BEGIN
    -- Riferimenti CLONATI da un articolo esistente (ORDER BY id: deterministico):
    -- la fixture non deve conoscere il dominio ne' inseguirlo quando cambia.
    INSERT INTO catalogo.articoli (codice, descrizione, uom_id, tipo_voce_id,
                                   gruppo_voce_id, spesa_id, iva_id,
                                   is_composito, is_solo_componente)
    SELECT p_codice, 'pgTAP solo componente',
           a.uom_id, a.tipo_voce_id, a.gruppo_voce_id, a.spesa_id, a.iva_id,
           p_composito, p_solo_componente
      FROM catalogo.articoli a ORDER BY a.id LIMIT 1
    RETURNING id INTO v_id;
    RETURN v_id;
END $mk$ LANGUAGE plpgsql;

CREATE TEMP TABLE tmp_seed AS
SELECT pg_temp.mk_articolo('PGTAP_SOLOCOMP_PADRE', true,  false) AS prodotto_id,
       pg_temp.mk_articolo('PGTAP_SOLOCOMP_FIGLIO', false, true) AS componente_id,
       false AS prodotto_solo,
       true  AS componente_solo;

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
    obbligatorio,
    valido_dal,
    valido_al,
    attivo
  )
  VALUES (
    (SELECT prodotto_id FROM tmp_seed),
    (SELECT componente_id FROM tmp_seed),
    1,
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
      obbligatorio,
      valido_dal,
      valido_al,
      attivo
    )
    VALUES (
      (SELECT prodotto_id FROM tmp_seed),
      (SELECT componente_id FROM tmp_seed),
      1,
      true,
      DATE '2026-04-01',
      DATE '2026-04-30',
      true
    )
    RETURNING id INTO v_id;

    -- 🔴 DELETE rimossa il 2026-08-18: `articoli_componenti` e' protetta da un
    -- guard di IMMUTABILITA' della struttura BoM, arrivato dopo questo file.
    -- Cancellare non e' piu' lecito per nessuno, e non serve: il ROLLBACK
    -- toglie la riga insieme all'articolo che la porta.
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
      obbligatorio,
      valido_dal,
      valido_al,
      attivo
    )
    VALUES (
      (SELECT prodotto_id FROM tmp_seed),
      (SELECT componente_id FROM tmp_seed),
      1,
      true,
      DATE '2026-05-01',
      DATE '2026-05-31',
      true
    )
    RETURNING id INTO v_id;

    -- 🔴 DELETE rimossa il 2026-08-18: `articoli_componenti` e' protetta da un
    -- guard di IMMUTABILITA' della struttura BoM, arrivato dopo questo file.
    -- Cancellare non e' piu' lecito per nessuno, e non serve: il ROLLBACK
    -- toglie la riga insieme all'articolo che la porta.
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
