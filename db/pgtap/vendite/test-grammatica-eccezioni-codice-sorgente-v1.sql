-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Una grammatica sola per i tipi di documento — lotto 1: la famiglia dei
--   documenti con eccezioni (contratto, offerta) parla il codice della
--   sorgente, CONTRATTO | OFFERTA_COMMERCIALE. Il codice corto OFFERTA non
--   passa piu'.
--   Brief: brief-db-grammatica-unica-documenti §9 (G-1, G-4 di Tid).
--   ChangeSet: 20261019-18 … -32.
--
-- Elenco test (plan 12):
--  1) le sette funzioni che ricevono p_documento: UNA sola per nome (il DROP
--       + CREATE non ha lasciato l'overload text)
--  2) …e il primo argomento e' character varying (ancorato a
--       config.sorgenti.codice_interno)
--  3) fn_documento_listino_operativo('OFFERTA', …): E_DOC_TIPO_NON_GESTITO
--  4) fn_documento_righe_eccezione('OFFERTA', …): E_DOC_TIPO_NON_GESTITO
--  5) fn_check_listino_congelabile('OFFERTA', …): E_DOC_TIPO_NON_GESTITO
--  6) fn_check_riga_erogazione('OFFERTA', …): E_DOC_TIPO_NON_GESTITO
--  7) OFFERTA_COMMERCIALE e' accettato: listino operativo, righe eccezione e
--       righe preview di un'offerta che non c'e' danno zero righe, non errore
--  8) fn_check_listino_congelabile('OFFERTA_COMMERCIALE', NULL, NULL): nessun
--       motivo (senza listino)
--  9) i due montaggi del guard dell'erogazione sull'offerta passano
--       OFFERTA_COMMERCIALE; quelli del contratto CONTRATTO
-- 10) nessun montaggio del guard passa piu' OFFERTA
-- 11) il contesto dell'articolo per un'offerta non porta piu' doc_listino
-- 12) …e la sua etichetta viene ancora dalla grammatica delle testate
--       (ponte residuo, lotto 2): «Offerta #<id>» per un'offerta che non c'e'
--
-- ⭐ Non serve un'offerta vera: i rami si distinguono dal codice. Il
--   comportamento sulle offerte vere lo provano i pgTAP della famiglia
--   (test-righe-esclusione-solo-non-si-vende-v1,
--   offerte_commerciali/test-offerta-emissione-congela-listino-v1,
--   script/test-fn-available-actions-offerta-v1, i test delle erogazioni).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

CREATE OR REPLACE FUNCTION pg_temp.codice(p_sql text)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_cst text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME;
        RETURN coalesce(nullif(v_cst, ''), '-');
    END;
END;
$fx$;

CREATE TEMP TABLE _fam ON COMMIT DROP AS
SELECT * FROM (VALUES
    ('vendite', 'fn_documento_listino_operativo'),
    ('vendite', 'fn_documento_righe_eccezione'),
    ('vendite', 'fn_documento_righe_preview'),
    ('vendite', 'fn_documento_riga_erogazioni'),
    ('script',  'fn_check_esclusione_articolo_documento'),
    ('script',  'fn_check_riga_erogazione'),
    ('script',  'fn_check_listino_congelabile')) v(schema_nome, fn_nome);

-- 1) una sola per nome
SELECT is_empty(
    $$SELECT f.fn_nome
        FROM _fam f
        JOIN pg_namespace n ON n.nspname = f.schema_nome
        LEFT JOIN pg_proc p ON p.pronamespace = n.oid AND p.proname = f.fn_nome
       GROUP BY f.fn_nome
      HAVING count(p.oid) <> 1$$,
    '1) le sette funzioni della famiglia esistono in una sola firma');

-- 2) primo argomento varchar
SELECT is_empty(
    $$SELECT f.fn_nome
        FROM _fam f
        JOIN pg_namespace n ON n.nspname = f.schema_nome
        JOIN pg_proc p ON p.pronamespace = n.oid AND p.proname = f.fn_nome
       WHERE p.proargtypes[0] <> 'character varying'::regtype$$,
    '2) p_documento e'' character varying (config.sorgenti.codice_interno%TYPE)');

-- 3-6) il codice corto non passa
SELECT is(pg_temp.codice($$SELECT * FROM vendite.fn_documento_listino_operativo('OFFERTA', -1)$$),
          'E_DOC_TIPO_NON_GESTITO', '3) fn_documento_listino_operativo rifiuta OFFERTA');
SELECT is(pg_temp.codice($$SELECT * FROM vendite.fn_documento_righe_eccezione('OFFERTA', -1)$$),
          'E_DOC_TIPO_NON_GESTITO', '4) fn_documento_righe_eccezione rifiuta OFFERTA');
SELECT is(pg_temp.codice($$SELECT script.fn_check_listino_congelabile('OFFERTA', NULL, NULL)$$),
          'E_DOC_TIPO_NON_GESTITO', '5) fn_check_listino_congelabile rifiuta OFFERTA');
SELECT is(pg_temp.codice($$SELECT script.fn_check_riga_erogazione('OFFERTA', -1, NULL, NULL, NULL, NULL)$$),
          'E_DOC_TIPO_NON_GESTITO', '6) fn_check_riga_erogazione rifiuta OFFERTA');

-- 7) il codice della sorgente passa
SELECT is(
    (SELECT count(*) FROM vendite.fn_documento_listino_operativo('OFFERTA_COMMERCIALE', -1))
  + (SELECT count(*) FROM vendite.fn_documento_righe_eccezione('OFFERTA_COMMERCIALE', -1))
  + (SELECT count(*) FROM vendite.fn_documento_righe_preview('OFFERTA_COMMERCIALE', -1)),
    0::bigint,
    '7) OFFERTA_COMMERCIALE accettato: zero righe per un''offerta che non c''e''');

-- 8) senza listino nessun motivo
SELECT is(script.fn_check_listino_congelabile('OFFERTA_COMMERCIALE', NULL, NULL), '[]'::jsonb,
          '8) fn_check_listino_congelabile(OFFERTA_COMMERCIALE) senza listino: nessun motivo');

-- 9) i montaggi
SELECT results_eq(
    $$SELECT c.relname::text COLLATE "default",
             split_part(encode(t.tgargs, 'escape'), E'\\000', 1) COLLATE "default"
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_proc p ON p.oid = t.tgfoid
       WHERE p.proname = 'trgfn_righe_guard_erogazione_perimetro' AND NOT t.tgisinternal
       ORDER BY 1, t.tgname$$,
    $$VALUES ('contratti_righe', 'CONTRATTO'), ('contratti_righe', 'CONTRATTO'),
             ('offerte_commerciali_eccezioni', 'OFFERTA_COMMERCIALE'),
             ('offerte_commerciali_eccezioni', 'OFFERTA_COMMERCIALE')$$,
    '9) guard dell''erogazione: CONTRATTO sul contratto, OFFERTA_COMMERCIALE sull''offerta');

-- 10) nessun OFFERTA negli argomenti
SELECT is_empty(
    $$SELECT t.tgname FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
       WHERE p.proname = 'trgfn_righe_guard_erogazione_perimetro'
         AND split_part(encode(t.tgargs, 'escape'), E'\\000', 1) = 'OFFERTA'$$,
    '10) nessun montaggio del guard dell''erogazione passa OFFERTA');

-- 11-12) il contesto
SELECT ok(
    NOT (script.fn_articolo_riga_contesto('OFFERTA_COMMERCIALE', -1, 'AGGIUNTA') ? 'doc_listino'),
    '11) il contesto di un''offerta non porta doc_listino');
SELECT is(
    script.fn_articolo_riga_contesto('OFFERTA_COMMERCIALE', -1, 'AGGIUNTA') ->> 'etichetta',
    'Offerta #-1',
    '12) l''etichetta viene dalla grammatica delle testate (ponte residuo, lotto 2)');

SELECT * FROM finish();
ROLLBACK;
