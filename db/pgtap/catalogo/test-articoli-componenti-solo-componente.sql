-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Regola: articoli "solo componente" non possono essere prodotti
-- ------------------------------------------------------------

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
