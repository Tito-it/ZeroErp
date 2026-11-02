-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- View: catalogo.vw_articoli_componenti_note
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

SELECT plan(9);

-- 🔴 ARTICOLI PROPRI invece di ART_TEST_BASE / ART_TEST_FALLBACK — 2026-08-18.
--   Il file agganciava un componente a `ART_TEST_BASE`, che NON e' composito:
--   il guard rispondeva «Articolo deve essere composito = true» e il file
--   moriva. Non e' un difetto del guard — e' la fixture che usa un articolo
--   condiviso e ne assume una proprieta' che quell'articolo non ha (e non deve
--   avere: e' l'articolo base di mezza suite).
--   ⭐ Stesso rimedio degli altri quattro test di questa cartella: l'articolo
--   se lo crea il test, con la proprieta' che gli serve. Il padre nasce
--   `is_composito = true` perche' e' il presupposto del soggetto in esame.
CREATE OR REPLACE FUNCTION pg_temp.mk_articolo(p_codice text, p_composito boolean)
RETURNS uuid AS $mk$
DECLARE v_id uuid;
BEGIN
    -- Riferimenti CLONATI da un articolo esistente: la fixture non deve
    -- conoscere il dominio (tipo voce, gruppo, spesa, iva) ne' inseguirlo
    -- quando cambia. ORDER BY id, non «il primo che capita».
    INSERT INTO catalogo.articoli (codice, descrizione, uom_id, tipo_voce_id,
                                   gruppo_voce_id, spesa_id, iva_id, is_composito)
    SELECT p_codice, 'pgTAP note componenti',
           a.uom_id, a.tipo_voce_id, a.gruppo_voce_id, a.spesa_id, a.iva_id, p_composito
      FROM catalogo.articoli a ORDER BY a.id LIMIT 1
    RETURNING id INTO v_id;
    RETURN v_id;
END $mk$ LANGUAGE plpgsql;

CREATE TEMP TABLE tmp_seed AS
SELECT pg_temp.mk_articolo('PGTAP_VWNOTE_PADRE', true)  AS prodotto_id,
       pg_temp.mk_articolo('PGTAP_VWNOTE_COMP',  false) AS componente_id;

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
    'ARTICOLO_COMPONENTE',
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
    'ARTICOLO',
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

-- 🔴 DELETE della riga di BoM RIMOSSA il 2026-08-18.
--   `catalogo.articoli_componenti` e' protetta da un guard di immutabilita'
--   («Struttura BoM immutabile: modifica dei campi di struttura o eliminazione
--   di righe non ammesse»), arrivato dopo questo file. La cancellazione non e'
--   piu' una operazione lecita, e insistere qui vorrebbe dire chiedere al test
--   un permesso che il dominio nega a tutti.
--   ⭐ E non serve: il ROLLBACK in coda toglie la riga insieme all'articolo che
--   la porta. Il commento qui sotto dice che le DELETE restano «dove sono
--   un'asserzione» — questa non lo era, era solo pulizia.

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
