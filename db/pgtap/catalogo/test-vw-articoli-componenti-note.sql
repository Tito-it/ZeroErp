-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- View: catalogo.vw_articoli_componenti_note
-- ------------------------------------------------------------

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⚠️ Questo file non apre una transazione propria: la riga va prima di plan().
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

CREATE TEMP TABLE tmp_seed AS
SELECT
  (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_BASE') AS prodotto_id,
  (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_FALLBACK') AS componente_id;

SELECT ok(
  (SELECT prodotto_id IS NOT NULL FROM tmp_seed),
  'Seed prodotto presente'
);

SELECT ok(
  (SELECT componente_id IS NOT NULL FROM tmp_seed),
  'Seed componente presente'
);

CREATE TEMP TABLE tmp_note_stile AS
SELECT id, codice
FROM config.note_stili
ORDER BY id
LIMIT 1;

SELECT ok(
  (SELECT count(*) FROM tmp_note_stile) = 1,
  'note_stili di base presente'
);

CREATE TEMP TABLE tmp_lingua AS
SELECT id, codice_iso
FROM config.lingue
WHERE attivo IS TRUE
ORDER BY id
LIMIT 1;

SELECT ok(
  (SELECT count(*) FROM tmp_lingua) = 1,
  'Lingua di base presente'
);

SELECT diag(
  format(
    'Seed note comp: prodotto_id=%s componente_id=%s stile_id=%s stile_codice=%s lingua_id=%s lingua_codice=%s',
    COALESCE((SELECT prodotto_id::text FROM tmp_seed), 'NULL'),
    COALESCE((SELECT componente_id::text FROM tmp_seed), 'NULL'),
    COALESCE((SELECT id::text FROM tmp_note_stile), 'NULL'),
    COALESCE((SELECT codice FROM tmp_note_stile), 'NULL'),
    COALESCE((SELECT id::text FROM tmp_lingua), 'NULL'),
    COALESCE((SELECT codice_iso FROM tmp_lingua), 'NULL')
  )
);

CREATE TEMP TABLE tmp_art_comp_rel (id uuid);
CREATE TEMP TABLE tmp_note (id bigint);

DO $$
DECLARE
  v_comp_id uuid;
  v_nota_id bigint;
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
    DATE '2026-02-01',
    DATE '2026-02-28',
    true
  )
  RETURNING id INTO v_comp_id;

  INSERT INTO catalogo.note_articoli_componenti (
    target_tipo,
    target_id,
    anchor_tipo,
    posizione,
    seq,
    testo,
    id_stile,
    id_lingua
  )
  VALUES (
    'ARTICOLI_COMPONENTI',
    v_comp_id,
    'DOCUMENTO',
    'HEADER',
    10,
    'Nota test view componenti',
    (SELECT id FROM tmp_note_stile),
    (SELECT id FROM tmp_lingua)
  )
  RETURNING id INTO v_nota_id;

  INSERT INTO tmp_art_comp_rel (id) VALUES (v_comp_id);
  INSERT INTO tmp_note (id) VALUES (v_nota_id);
END $$;

SELECT ok(
  (SELECT count(*) FROM tmp_note) = 1
  AND (SELECT count(*) FROM tmp_art_comp_rel) = 1,
  'Creati componente e nota di test'
);

SELECT is(
  (SELECT count(*)
   FROM catalogo.vw_articoli_componenti_note v
   WHERE v.articolo_componente_id = (SELECT id FROM tmp_art_comp_rel)
     AND v.nota_id = (SELECT id FROM tmp_note)),
  1::bigint,
  'View note componenti espone la nota'
);

SELECT is(
  (SELECT v.lingua_codice_iso
   FROM catalogo.vw_articoli_componenti_note v
   WHERE v.nota_id = (SELECT id FROM tmp_note)),
  (SELECT codice_iso FROM tmp_lingua),
  'View note componenti espone lingua corretta'
);

SELECT is(
  (SELECT v.stile_codice
   FROM catalogo.vw_articoli_componenti_note v
   WHERE v.nota_id = (SELECT id FROM tmp_note)),
  (SELECT codice FROM tmp_note_stile),
  'View note componenti espone stile corretto'
);

SELECT throws_ok(
  $$
  INSERT INTO catalogo.note_articoli_componenti (
    target_tipo,
    target_id,
    anchor_tipo,
    posizione,
    seq,
    testo,
    id_stile,
    id_lingua
  )
  VALUES (
    'ARTICOLI',
    (SELECT id FROM tmp_art_comp_rel),
    'DOCUMENTO',
    'HEADER',
    20,
    'Nota target errato',
    (SELECT id FROM tmp_note_stile),
    (SELECT id FROM tmp_lingua)
  );
  $$,
  NULL,
  NULL,
  'note_target_tipo errato: bloccato'
);

-- Cleanup
DELETE FROM catalogo.note_articoli_componenti
WHERE id = (SELECT id FROM tmp_note);

DELETE FROM catalogo.articoli_componenti
WHERE id = (SELECT id FROM tmp_art_comp_rel);
