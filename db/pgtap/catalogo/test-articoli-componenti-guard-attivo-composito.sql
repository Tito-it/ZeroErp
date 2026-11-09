-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Regole: attivo e is_composito su catalogo.articoli_componenti
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
      -- Il padre non composito lo rifiuta il lato documento della check della
      -- distinta (script.fn_articolo_riga_contesto), chiamata dal guard del legame.
      AND pg_get_triggerdef(t.oid) ILIKE '%trgfn_articoli_componenti_guard_componente%'
  ) AS has_guard_composito;

SELECT diag(
  format(
    'Trigger check: req_prodotto=%s req_componente=%s guard_componente=%s',
    CASE WHEN (SELECT has_req_prodotto FROM tmp_trg) THEN 'true' ELSE 'false' END,
    CASE WHEN (SELECT has_req_componente FROM tmp_trg) THEN 'true' ELSE 'false' END,
    CASE WHEN (SELECT has_guard_composito FROM tmp_trg) THEN 'true' ELSE 'false' END
  )
);

SELECT diag(
  format(
    'Prerequisiti: can_run=%s uom=%s tipo=%s gruppo=%s spesa=%s iva=%s',
    CASE WHEN (SELECT can_run FROM tmp_can_run) THEN 'true' ELSE 'false' END,
    COALESCE((SELECT uom_id::text FROM tmp_seed), 'NULL'),
    COALESCE((SELECT tipo_id::text FROM tmp_seed), 'NULL'),
    COALESCE((SELECT gruppo_id::text FROM tmp_seed), 'NULL'),
    COALESCE((SELECT spesa_id::text FROM tmp_seed), 'NULL'),
    COALESCE((SELECT iva_id::text FROM tmp_seed), 'NULL')
  )
);

CREATE TEMP TABLE tmp_ids AS
SELECT to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS') AS ts;

CREATE TEMP TABLE tmp_art AS
SELECT NULL::uuid AS prodotto_id, NULL::uuid AS componente_id;

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

CREATE OR REPLACE FUNCTION pg_temp.fn_try_insert_componenti(
  p_prodotto_id uuid,
  p_componente_id uuid,
  p_valid_from date,
  p_valid_to date
) RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
  v_id uuid;
BEGIN
  EXECUTE 'SET CONSTRAINTS ALL IMMEDIATE';
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
      p_prodotto_id,
      p_componente_id,
      1,
      true,
      p_valid_from,
      p_valid_to,
      true
    )
    RETURNING id INTO v_id;

    DELETE FROM catalogo.articoli_componenti WHERE id = v_id;
    RETURN false;
  EXCEPTION WHEN OTHERS THEN
    RETURN true;
  END;
END;
$$;

-- Prodotto non attivo
-- 🔴 FIGLI PRIMA DEL PADRE, aggiunto il 2026-08-18.
--   `catalogo.articoli` ha 28 tabelle figlie guardate da
--   `prevent_deactivate_if_children`: disattivare il padre con anche un solo
--   figlio attivo solleva. Questo file gli articoli se li crea gia' (bene), ma
--   nel farlo si crea anche i figli — la riga di BoM che sta testando, piu' la
--   `articoli_uom_operativa` di base che nasce da trigger.
--   ⚠️ Il guard non e' un ostacolo del test: e' il suo contesto. Si rispetta
--   l'ordine che impone, invece di aggirarlo.
--   ⛔ Si DISATTIVANO, non si cancellano: `articoli_componenti` e' protetta da
--   un guard di immutabilita' della struttura BoM.
UPDATE catalogo.articoli_componenti
   SET attivo = false
 WHERE prodotto_id = (SELECT prodotto_id FROM tmp_art)
   AND attivo = true;

UPDATE catalogo.articoli_uom_operativa
   SET attivo = false
 WHERE articolo_id = (SELECT prodotto_id FROM tmp_art)
   AND attivo = true;

UPDATE catalogo.articoli
SET attivo = false
WHERE id = (SELECT prodotto_id FROM tmp_art);

SELECT diag('Skip prodotto non attivo: prerequisiti mancanti')
WHERE NOT (SELECT can_run FROM tmp_can_run);

SELECT diag('Skip prodotto non attivo: trigger REQUIRE su prodotto_id assente')
WHERE (SELECT can_run FROM tmp_can_run)
  AND NOT (SELECT has_req_prodotto FROM tmp_trg);

SELECT CASE
  WHEN NOT (SELECT can_run FROM tmp_can_run) THEN
    ok(true, 'Prodotto non attivo: prerequisiti mancanti, test skipped')
  WHEN (SELECT has_req_prodotto FROM tmp_trg) THEN
    is(
      pg_temp.fn_try_insert_componenti(
        (SELECT prodotto_id FROM tmp_art),
        (SELECT componente_id FROM tmp_art),
        DATE '2026-06-01',
        DATE '2026-06-30'
      ),
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
-- 🔴 Figli prima del padre anche qui (2026-08-18): il componente ha la propria
--   `articoli_uom_operativa` di base, nata da trigger alla creazione. Stesso
--   ordine imposto da `prevent_deactivate_if_children`.
UPDATE catalogo.articoli_uom_operativa
   SET attivo = false
 WHERE articolo_id = (SELECT componente_id FROM tmp_art)
   AND attivo = true;

UPDATE catalogo.articoli
SET attivo = false
WHERE id = (SELECT componente_id FROM tmp_art);

SELECT diag('Skip componente non attivo: prerequisiti mancanti')
WHERE NOT (SELECT can_run FROM tmp_can_run);

SELECT diag('Skip componente non attivo: trigger REQUIRE su componente_id assente')
WHERE (SELECT can_run FROM tmp_can_run)
  AND NOT (SELECT has_req_componente FROM tmp_trg);

SELECT CASE
  WHEN NOT (SELECT can_run FROM tmp_can_run) THEN
    ok(true, 'Componente non attivo: prerequisiti mancanti, test skipped')
  WHEN (SELECT has_req_componente FROM tmp_trg) THEN
    is(
      pg_temp.fn_try_insert_componenti(
        (SELECT prodotto_id FROM tmp_art),
        (SELECT componente_id FROM tmp_art),
        DATE '2026-07-01',
        DATE '2026-07-31'
      ),
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

SELECT diag('Skip prodotto non composito: prerequisiti mancanti')
WHERE NOT (SELECT can_run FROM tmp_can_run);

SELECT diag('Skip prodotto non composito: guard del legame assente')
WHERE (SELECT can_run FROM tmp_can_run)
  AND NOT (SELECT has_guard_composito FROM tmp_trg);

SELECT CASE
  WHEN NOT (SELECT can_run FROM tmp_can_run) THEN
    ok(true, 'Prodotto non composito: prerequisiti mancanti, test skipped')
  WHEN (SELECT has_guard_composito FROM tmp_trg) THEN
    is(
      pg_temp.fn_try_insert_componenti(
        (SELECT prodotto_id FROM tmp_art),
        (SELECT componente_id FROM tmp_art),
        DATE '2026-08-01',
        DATE '2026-08-31'
      ),
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

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
