-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Le note di catalogo hanno la forma delle note degli altri schemi, e non
-- tengono acceso il loro bersaglio (D16, Q12, R6).
--   - catalogo.note: testo non vuoto (chk_note_testo_non_vuoto), ancora solo
--     DOCUMENTO e nessuna riga (chk_note_catalogo_ancora_documento), user_* text,
--     tx_id scritto dal trigger generato;
--   - la nota non e' un figlio vivo: un articolo con una nota si spegne, e su un
--     articolo spento una nota si scrive (automazione_attivo_eccezioni);
--   - catalogo.vw_note e' la proiezione unica; vw_articoli_note e
--     vw_articoli_componenti_note la leggono, con le colonne di prima.
-- Brief: brief-db-revisione-catalogo, giro 4.
--
-- Elenco test (plan 12):
--  1)  nota senza testo ne' testo_md: rifiutata (chk_note_testo_non_vuoto)
--  2)  nota ancorata a RIGA: rifiutata (chk_note_catalogo_ancora_documento)
--  3)  nota DOCUMENTO con target_riga_id: rifiutata (stesso CHECK)
--  4)  user_insert, user_update text; tx_id uuid
--  5)  la nota scritta ha tx_id
--  6)  l'articolo con una nota si spegne
--  7)  su un articolo spento una nota si scrive
--  8)  nessun block_deact ne' require fra le note e i loro bersagli
--  9)  vw_articoli_note: le note dell'articolo sono quelle di vw_note per ARTICOLO
--  10) vw_articoli_note: le colonne di prima, nello stesso ordine
--  11) vw_articoli_componenti_note: le colonne di prima, nello stesso ordine
--  12) vw_note: una riga per nota del padre
--
-- Fixture costruita (ROLLBACK finale): l'articolo e' del test; stile e lingua
-- sono seed di 80_data.
-- ------------------------------------------------------------

BEGIN;

-- Vincoli differiti a fine istruzione: senza, al ROLLBACK non scatterebbero mai.
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

CREATE TEMP TABLE _t AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-NOTE-FORMA') AS art,
       (SELECT id FROM config.note_stili ORDER BY id LIMIT 1) AS stile,
       (SELECT id FROM config.lingue WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS lingua;

-- Scopo: inserisce una nota sull'articolo del test e ne restituisce l'id.
CREATE OR REPLACE FUNCTION pg_temp.nota(p_testo text) RETURNS bigint
LANGUAGE sql AS $fx$
    INSERT INTO catalogo.note (target_tipo, target_id, anchor_tipo, posizione, seq, testo, id_stile, id_lingua)
    SELECT 'ARTICOLO', t.art, 'DOCUMENTO', 'HEADER', 10, p_testo, t.stile, t.lingua FROM _t t
    RETURNING id;
$fx$;

-- ============================================================
-- La forma (1-5)
-- ============================================================
SELECT throws_ok(
    $$ INSERT INTO catalogo.note (target_tipo, target_id, anchor_tipo, posizione, id_stile)
       SELECT 'ARTICOLO', art, 'DOCUMENTO', 'HEADER', stile FROM _t $$,
    '23514', NULL,
    '1) una nota senza testo ne'' testo_md e'' rifiutata');

SELECT throws_ok(
    $$ INSERT INTO catalogo.note (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, testo, id_stile)
       SELECT 'ARTICOLO', art, uuidv7(), 'RIGA', 'BEFORE', 'x', stile FROM _t $$,
    '23514', NULL,
    '2) una nota di catalogo ancorata a RIGA e'' rifiutata');

SELECT throws_ok(
    $$ INSERT INTO catalogo.note (target_tipo, target_id, target_riga_id, anchor_tipo, posizione, testo, id_stile)
       SELECT 'ARTICOLO', art, uuidv7(), 'DOCUMENTO', 'HEADER', 'x', stile FROM _t $$,
    '23514', NULL,
    '3) una nota DOCUMENTO con una riga e'' rifiutata');

SELECT is(
    (SELECT string_agg(attname || ':' || format_type(atttypid, atttypmod), ' ' ORDER BY attname)
       FROM pg_attribute
      WHERE attrelid = 'catalogo.note'::regclass AND NOT attisdropped
        AND attname IN ('user_insert', 'user_update', 'tx_id')),
    'tx_id:uuid user_insert:text user_update:text',
    '4) user_insert e user_update sono text, tx_id e'' uuid');

CREATE TEMP TABLE _n AS SELECT pg_temp.nota('Prima nota') AS id;

SELECT ok(
    (SELECT n.tx_id IS NOT NULL FROM catalogo.note n WHERE n.id = (SELECT id FROM _n)),
    '5) la nota scritta ha il suo tx_id');

-- ============================================================
-- La nota non tiene acceso il bersaglio (6-8)
-- ============================================================
SELECT lives_ok(
    $$ UPDATE catalogo.articoli SET attivo = false WHERE id = (SELECT art FROM _t) $$,
    '6) un articolo con una nota si spegne');

SELECT lives_ok(
    $$ SELECT pg_temp.nota('Nota su articolo spento') $$,
    '7) su un articolo spento una nota si scrive');

SELECT is(
    (SELECT count(*)::int FROM pg_trigger t
      WHERE NOT t.tgisinternal
        AND t.tgfoid IN ('dbops.trgfn_prevent_deactivate_if_children'::regproc,
                         'dbops.trgfn_child_requires_active_parent'::regproc)
        AND (t.tgrelid IN ('catalogo.note_articoli'::regclass, 'catalogo.note_articoli_componenti'::regclass)
             OR pg_get_triggerdef(t.oid) ~ '''note_articoli(_componenti)?''')),
    0,
    '8) nessun block_deact ne'' require fra le note di catalogo e i loro bersagli');

-- ============================================================
-- Le viste (9-12)
-- ============================================================
SELECT set_eq(
    $$ SELECT nota_id, nota_testo, stile_codice, lingua_codice_iso FROM catalogo.vw_articoli_note
        WHERE articolo_id = (SELECT art FROM _t) $$,
    $$ SELECT nota_id, nota_testo, stile_codice, lingua_codice_iso FROM catalogo.vw_note
        WHERE nota_target_tipo = 'ARTICOLO' AND nota_target_id = (SELECT art FROM _t) $$,
    '9) vw_articoli_note mostra le note dell''articolo come vw_note');

SELECT is(
    (SELECT string_agg(attname, ',' ORDER BY attnum) FROM pg_attribute
      WHERE attrelid = 'catalogo.vw_articoli_note'::regclass AND attnum > 0),
    'articolo_id,articolo_codice,articolo_descrizione,nota_id,nota_target_tipo,nota_target_id,'
    'nota_target_riga_id,nota_anchor_tipo,nota_posizione,nota_seq,nota_testo,nota_testo_md,'
    'nota_visibile,nota_solo_stampa,nota_meta,nota_data_insert,nota_user_insert,nota_data_update,'
    'nota_user_update,stile_id,stile_codice,stile_descrizione,lingua_id,lingua_codice_iso,'
    'lingua_descrizione,lingua_descrizione_locale',
    '10) vw_articoli_note ha le colonne di prima, nello stesso ordine');

SELECT is(
    (SELECT string_agg(attname, ',' ORDER BY attnum) FROM pg_attribute
      WHERE attrelid = 'catalogo.vw_articoli_componenti_note'::regclass AND attnum > 0),
    'articolo_componente_id,prodotto_id,prodotto_codice,prodotto_descrizione,componente_id,'
    'componente_codice,componente_descrizione,nota_id,nota_target_tipo,nota_target_id,'
    'nota_target_riga_id,nota_anchor_tipo,nota_posizione,nota_seq,nota_testo,nota_testo_md,'
    'nota_visibile,nota_solo_stampa,nota_meta,nota_data_insert,nota_user_insert,nota_data_update,'
    'nota_user_update,stile_id,stile_codice,stile_descrizione,lingua_id,lingua_codice_iso,'
    'lingua_descrizione,lingua_descrizione_locale',
    '11) vw_articoli_componenti_note ha le colonne di prima, nello stesso ordine');

SELECT is(
    (SELECT count(*) FROM catalogo.vw_note),
    (SELECT count(*) FROM catalogo.note),
    '12) vw_note ha una riga per nota');

SELECT * FROM finish();
ROLLBACK;
