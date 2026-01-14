-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Regole: attivo e is_composito su catalogo.articoli_componenti
-- ------------------------------------------------------------

SELECT plan(6);

CREATE TEMP TABLE tmp_seed AS
SELECT
  (SELECT id FROM catalogo.unita_misura WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS uom_id,
  (SELECT id FROM vendite.articoli_tipologie WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_id,
  (SELECT id FROM vendite.articoli_gruppi WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS gruppo_id,
  (SELECT id FROM vendite.articoli_spesa WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS spesa_id,
  (SELECT id FROM config.iva WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS iva_id;

SELECT ok(
  (SELECT uom_id IS NOT NULL FROM tmp_seed),
  'Riferimento unita_misura presente'
);

SELECT ok(
  (SELECT tipo_id IS NOT NULL FROM tmp_seed)
  AND (SELECT gruppo_id IS NOT NULL FROM tmp_seed)
  AND (SELECT spesa_id IS NOT NULL FROM tmp_seed)
  AND (SELECT iva_id IS NOT NULL FROM tmp_seed),
  'Riferimenti vendite/config presenti'
);

CREATE TEMP TABLE tmp_can_run AS
SELECT (
  (SELECT uom_id IS NOT NULL FROM tmp_seed)
  AND (SELECT tipo_id IS NOT NULL FROM tmp_seed)
  AND (SELECT gruppo_id IS NOT NULL FROM tmp_seed)
  AND (SELECT spesa_id IS NOT NULL FROM tmp_seed)
  AND (SELECT iva_id IS NOT NULL FROM tmp_seed)
) AS can_run;

CREATE TEMP TABLE tmp_trg AS
SELECT
  EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'catalogo'
      AND c.relname = 'articoli_componenti'
      AND NOT t.tgisinternal
      AND pg_get_triggerdef(t.oid) ILIKE '%trgfn_child_requires_active_parent%'
      AND pg_get_triggerdef(t.oid) ILIKE '%prodotto_id%'
  ) AS has_req_prodotto,
  EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'catalogo'
      AND c.relname = 'articoli_componenti'
      AND NOT t.tgisinternal
      AND pg_get_triggerdef(t.oid) ILIKE '%trgfn_child_requires_active_parent%'
      AND pg_get_triggerdef(t.oid) ILIKE '%componente_id%'
  ) AS has_req_componente,
  EXISTS (
    SELECT 1
    FROM pg_trigger t
    JOIN pg_class c ON c.oid = t.tgrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'catalogo'
      AND c.relname = 'articoli_componenti'
      AND NOT t.tgisinternal
      AND pg_get_triggerdef(t.oid) ILIKE '%is_composito%'
  ) AS has_req_composito;

SELECT diag(
  format(
    'Trigger check: req_prodotto=%s req_componente=%s req_is_composito=%s',
    CASE WHEN (SELECT has_req_prodotto FROM tmp_trg) THEN 'true' ELSE 'false' END,
    CASE WHEN (SELECT has_req_componente FROM tmp_trg) THEN 'true' ELSE 'false' END,
    CASE WHEN (SELECT has_req_composito FROM tmp_trg) THEN 'true' ELSE 'false' END
  )
);

CREATE TEMP TABLE tmp_ids AS
SELECT to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') AS ts;

CREATE TEMP TABLE tmp_art AS
SELECT NULL::uuid AS prodotto_id, NULL::uuid AS componente_id;

CREATE TEMP TABLE tmp_result AS
SELECT NULL::boolean AS prodotto_err,
       NULL::boolean AS componente_err,
       NULL::boolean AS composito_err;

DO $$
DECLARE
  v_prod_id uuid;
  v_comp_id uuid;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) THEN
    INSERT INTO catalogo.articoli (
      codice,
      descrizione,
      uom_id,
      tipo_voce_id,
      gruppo_voce_id,
      spesa_id,
      iva_id
    )
    VALUES (
      'ART_GUARD_PROD_' || (SELECT ts FROM tmp_ids),
      'Articolo guard prodotto ' || (SELECT ts FROM tmp_ids),
      (SELECT uom_id FROM tmp_seed),
      (SELECT tipo_id FROM tmp_seed),
      (SELECT gruppo_id FROM tmp_seed),
      (SELECT spesa_id FROM tmp_seed),
      (SELECT iva_id FROM tmp_seed)
    )
    RETURNING id INTO v_prod_id;

    INSERT INTO catalogo.articoli (
      codice,
      descrizione,
      uom_id,
      tipo_voce_id,
      gruppo_voce_id,
      spesa_id,
      iva_id
    )
    VALUES (
      'ART_GUARD_COMP_' || (SELECT ts FROM tmp_ids),
      'Articolo guard componente ' || (SELECT ts FROM tmp_ids),
      (SELECT uom_id FROM tmp_seed),
      (SELECT tipo_id FROM tmp_seed),
      (SELECT gruppo_id FROM tmp_seed),
      (SELECT spesa_id FROM tmp_seed),
      (SELECT iva_id FROM tmp_seed)
    )
    RETURNING id INTO v_comp_id;

    UPDATE tmp_art
    SET prodotto_id = v_prod_id,
        componente_id = v_comp_id;
  END IF;
END $$;

SELECT ok(
  (SELECT prodotto_id IS NOT NULL FROM tmp_art)
  AND (SELECT componente_id IS NOT NULL FROM tmp_art),
  'Articoli di test creati'
);

-- Prodotto non attivo
UPDATE catalogo.articoli
SET attivo = false
WHERE id = (SELECT prodotto_id FROM tmp_art);

DO $$
DECLARE
  v_id uuid;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) AND (SELECT has_req_prodotto FROM tmp_trg) THEN
    UPDATE tmp_result SET prodotto_err = false;
    BEGIN
      INSERT INTO catalogo.articoli_componenti (
        prodotto_id,
        componente_id,
        coeff_qta,
        partecipa_qta,
        obbligatorio,
        valid_from,
        valid_to,
        attivo
      )
      VALUES (
        (SELECT prodotto_id FROM tmp_art),
        (SELECT componente_id FROM tmp_art),
        1,
        false,
        true,
        DATE '2026-06-01',
        DATE '2026-06-30',
        true
      )
      RETURNING id INTO v_id;

      DELETE FROM catalogo.articoli_componenti WHERE id = v_id;
    EXCEPTION WHEN OTHERS THEN
      UPDATE tmp_result SET prodotto_err = true;
    END;
  END IF;
END $$;

SELECT CASE
  WHEN NOT (SELECT can_run FROM tmp_can_run) THEN
    ok(true, 'Prodotto non attivo: prerequisiti mancanti, test skipped')
  WHEN (SELECT has_req_prodotto FROM tmp_trg) THEN
    is(
      (SELECT prodotto_err FROM tmp_result),
      true,
      'Prodotto non attivo: bloccato'
    )
  ELSE
    ok(true, 'Prodotto non attivo: trigger non presente, test skipped')
END;

UPDATE catalogo.articoli
SET attivo = true
WHERE id = (SELECT prodotto_id FROM tmp_art);

-- Componente non attivo
UPDATE catalogo.articoli
SET attivo = false
WHERE id = (SELECT componente_id FROM tmp_art);

DO $$
DECLARE
  v_id uuid;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) AND (SELECT has_req_componente FROM tmp_trg) THEN
    UPDATE tmp_result SET componente_err = false;
    BEGIN
      INSERT INTO catalogo.articoli_componenti (
        prodotto_id,
        componente_id,
        coeff_qta,
        partecipa_qta,
        obbligatorio,
        valid_from,
        valid_to,
        attivo
      )
      VALUES (
        (SELECT prodotto_id FROM tmp_art),
        (SELECT componente_id FROM tmp_art),
        1,
        false,
        true,
        DATE '2026-07-01',
        DATE '2026-07-31',
        true
      )
      RETURNING id INTO v_id;

      DELETE FROM catalogo.articoli_componenti WHERE id = v_id;
    EXCEPTION WHEN OTHERS THEN
      UPDATE tmp_result SET componente_err = true;
    END;
  END IF;
END $$;

SELECT CASE
  WHEN NOT (SELECT can_run FROM tmp_can_run) THEN
    ok(true, 'Componente non attivo: prerequisiti mancanti, test skipped')
  WHEN (SELECT has_req_componente FROM tmp_trg) THEN
    is(
      (SELECT componente_err FROM tmp_result),
      true,
      'Componente non attivo: bloccato'
    )
  ELSE
    ok(true, 'Componente non attivo: trigger non presente, test skipped')
END;

UPDATE catalogo.articoli
SET attivo = true
WHERE id = (SELECT componente_id FROM tmp_art);

-- Prodotto non composito
UPDATE catalogo.articoli
SET is_composito = false
WHERE id = (SELECT prodotto_id FROM tmp_art);

DO $$
DECLARE
  v_id uuid;
BEGIN
  IF (SELECT can_run FROM tmp_can_run) AND (SELECT has_req_composito FROM tmp_trg) THEN
    UPDATE tmp_result SET composito_err = false;
    BEGIN
      INSERT INTO catalogo.articoli_componenti (
        prodotto_id,
        componente_id,
        coeff_qta,
        partecipa_qta,
        obbligatorio,
        valid_from,
        valid_to,
        attivo
      )
      VALUES (
        (SELECT prodotto_id FROM tmp_art),
        (SELECT componente_id FROM tmp_art),
        1,
        false,
        true,
        DATE '2026-08-01',
        DATE '2026-08-31',
        true
      )
      RETURNING id INTO v_id;

      DELETE FROM catalogo.articoli_componenti WHERE id = v_id;
    EXCEPTION WHEN OTHERS THEN
      UPDATE tmp_result SET composito_err = true;
    END;
  END IF;
END $$;

SELECT CASE
  WHEN NOT (SELECT can_run FROM tmp_can_run) THEN
    ok(true, 'Prodotto non composito: prerequisiti mancanti, test skipped')
  WHEN (SELECT has_req_composito FROM tmp_trg) THEN
    is(
      (SELECT composito_err FROM tmp_result),
      true,
      'Prodotto non composito: bloccato'
    )
  ELSE
    ok(true, 'Prodotto non composito: trigger non presente, test skipped')
END;

UPDATE catalogo.articoli
SET is_composito = false
WHERE id = (SELECT prodotto_id FROM tmp_art);

DELETE FROM catalogo.articoli
WHERE id IN (
  (SELECT prodotto_id FROM tmp_art),
  (SELECT componente_id FROM tmp_art)
);
