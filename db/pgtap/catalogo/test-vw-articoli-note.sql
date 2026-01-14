-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- View: catalogo.vw_articoli_note
-- ------------------------------------------------------------

SELECT plan(7);

CREATE TEMP TABLE tmp_seed AS
SELECT
  (SELECT id FROM catalogo.articoli WHERE codice = 'ART_TEST_BASE') AS articolo_id;

SELECT ok(
  (SELECT articolo_id IS NOT NULL FROM tmp_seed),
  'Seed articolo presente per note'
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
    'Seed note: articolo_id=%s stile_id=%s stile_codice=%s lingua_id=%s lingua_codice=%s',
    COALESCE((SELECT articolo_id::text FROM tmp_seed), 'NULL'),
    COALESCE((SELECT id::text FROM tmp_note_stile), 'NULL'),
    COALESCE((SELECT codice FROM tmp_note_stile), 'NULL'),
    COALESCE((SELECT id::text FROM tmp_lingua), 'NULL'),
    COALESCE((SELECT codice_iso FROM tmp_lingua), 'NULL')
  )
);

WITH ins AS (
  INSERT INTO catalogo.note_articoli (
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
    (SELECT articolo_id FROM tmp_seed),
    'DOCUMENTO',
    'HEADER',
    10,
    'Nota test view',
    (SELECT id FROM tmp_note_stile),
    (SELECT id FROM tmp_lingua)
  )
  RETURNING id
)
SELECT id
INTO TEMP TABLE tmp_note
FROM ins;

SELECT ok(
  (SELECT count(*) FROM tmp_note) = 1,
  'Creata nota articolo di test'
);

SELECT is(
  (SELECT count(*)
   FROM catalogo.vw_articoli_note v
   WHERE v.articolo_id = (SELECT articolo_id FROM tmp_seed)
     AND v.nota_id = (SELECT id FROM tmp_note)),
  1::bigint,
  'View note articoli espone la nota'
);

SELECT is(
  (SELECT v.stile_codice
   FROM catalogo.vw_articoli_note v
   WHERE v.nota_id = (SELECT id FROM tmp_note)),
  (SELECT codice FROM tmp_note_stile),
  'View note articoli espone stile corretto'
);

SELECT is(
  (SELECT v.lingua_codice_iso
   FROM catalogo.vw_articoli_note v
   WHERE v.nota_id = (SELECT id FROM tmp_note)),
  (SELECT codice_iso FROM tmp_lingua),
  'View note articoli espone lingua corretta'
);

-- Cleanup
DELETE FROM catalogo.note_articoli
WHERE id = (SELECT id FROM tmp_note);
