-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- View: catalogo.vw_articoli_note
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

SELECT plan(7);

-- ⛔ L'articolo si COSTRUISCE (2026-09-23): `ART_TEST_BASE` non sta in nessun
--   changelog — e' una riga messa a mano su questa macchina — e su un database
--   ricostruito la nota finiva con `target_id` NULL, cioe' il file moriva in
--   fixture. ⚠️ Lo stile e la lingua invece restano PESCATI: sono seed di
--   `80_data` e ci sono anche da zero.
CREATE TEMP TABLE tmp_seed AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-NOTE-ART') AS articolo_id;

SELECT ok(
  (SELECT articolo_id IS NOT NULL FROM tmp_seed),
  'Articolo costruito per le note'
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
    'ARTICOLO',
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

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
