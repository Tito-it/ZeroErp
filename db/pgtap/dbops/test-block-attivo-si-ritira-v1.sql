-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: dbops.trgfn_prevent_deactivate_if_children, il ramo del ritiro.
--       Una voce che ha il ritiro (obsoleto_dal) e che altre righe nominano
--       non si spegne: il rifiuto e' E_ATTIVO_BLOCK_SI_RITIRA, col campo
--       obsoleto_dal. Il caso costruito e' la distinta (Q35 (c)): un kit e un
--       suo componente, legati da un legame in vigore.
-- ChangeSet: 20_code/dbops/20261112-29; codice in config/codici_errore.csv e
--   config/messaggi_errore.csv.
--
-- Elenco test (plan 7):
--  1) spegnere il componente: E_ATTIVO_BLOCK_SI_RITIRA
--  2) ...col campo obsoleto_dal
--  3) spegnere il kit: E_ATTIVO_BLOCK_SI_RITIRA
--  4) il kit col legame CHIUSO resta nominato: E_ATTIVO_BLOCK_SI_RITIRA
--  5) il ritiro invece passa: la data di ritiro si scrive sul kit
--  6) il codice e' a catalogo, CONFLITTO_STATO, con la frase italiana
--  7) una tabella senza ritiro resta coi codici di prima: catalogo.unita_misura
--     usata da un articolo -> E_ATTIVO_BLOCK_CHILDREN_ACTIVE
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: IMMEDIATE li riporta a scattare a fine di ogni
--   istruzione (il COMMIT qui non arriva mai).
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come l'applicazione (ruolo OPERATORE +
-- RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- ============================================================
-- Fixture: un kit e un componente COSTRUITI, legati da oggi
-- ============================================================
CREATE TEMP TABLE tmp_sr AS
SELECT dbops.fn_pgtap_crea_articolo(
           ('PGT-SR-K-' || upper(substr(md5(clock_timestamp()::text || 'k'), 1, 8)))::varchar,
           p_is_composito => true) AS kit_id,
       dbops.fn_pgtap_crea_articolo(
           ('PGT-SR-C-' || upper(substr(md5(clock_timestamp()::text || 'c'), 1, 8)))::varchar) AS comp_id;

INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal, attivo)
SELECT kit_id, comp_id, 1, script.fn_data_operativa(), TRUE FROM tmp_sr;

-- Il codice e il campo di un rifiuto, dalla diagnostica dell'eccezione.
CREATE FUNCTION pg_temp.rifiuto(p_sql text) RETURNS jsonb
LANGUAGE plpgsql AS $$
DECLARE
    v_codice text;
    v_campo  text;
BEGIN
    EXECUTE p_sql;
    RETURN jsonb_build_object('codice', '(nessun errore)');
EXCEPTION WHEN others THEN
    GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME,
                            v_campo  = COLUMN_NAME;
    RETURN jsonb_build_object('codice', v_codice, 'campo', v_campo);
END $$;

-- ============================================================
-- 1-2) Il componente
-- ============================================================
CREATE TEMP TABLE tmp_sr_comp AS
SELECT pg_temp.rifiuto(format(
    'UPDATE catalogo.articoli SET attivo = false WHERE id = %L',
    (SELECT comp_id FROM tmp_sr))) AS r;

SELECT is((SELECT r ->> 'codice' FROM tmp_sr_comp), 'E_ATTIVO_BLOCK_SI_RITIRA',
    '1) spegnere un componente di una distinta: si ritira, non si spegne');

SELECT is((SELECT r ->> 'campo' FROM tmp_sr_comp), 'obsoleto_dal',
    '2) il campo del rifiuto e'' la data di ritiro');

-- ============================================================
-- 3) Il kit
-- ============================================================
SELECT is(
    pg_temp.rifiuto(format(
        'UPDATE catalogo.articoli SET attivo = false WHERE id = %L',
        (SELECT kit_id FROM tmp_sr))) ->> 'codice',
    'E_ATTIVO_BLOCK_SI_RITIRA',
    '3) spegnere un kit con la distinta: si ritira, non si spegne');

-- ============================================================
-- 4) Il legame chiuso resta attivo: il kit resta nominato
-- ============================================================
UPDATE catalogo.articoli_componenti ac
   SET valido_al = script.fn_data_operativa()
  FROM tmp_sr s
 WHERE ac.prodotto_id = s.kit_id;

SELECT is(
    pg_temp.rifiuto(format(
        'UPDATE catalogo.articoli SET attivo = false WHERE id = %L',
        (SELECT kit_id FROM tmp_sr))) ->> 'codice',
    'E_ATTIVO_BLOCK_SI_RITIRA',
    '4) col legame chiuso il kit resta nominato dalla sua storia: si ritira');

-- ============================================================
-- 5) Il ritiro passa
-- ============================================================
SELECT lives_ok(
    format('UPDATE catalogo.articoli SET obsoleto_dal = script.fn_data_operativa() WHERE id = %L',
           (SELECT kit_id FROM tmp_sr)),
    '5) il ritiro del kit con la distinta passa');

-- ============================================================
-- 6) Il codice a catalogo
-- ============================================================
SELECT is(
    (SELECT c.classe || ' / ' || (m.messaggio IS NOT NULL)::text
       FROM config.codici_errore c
       JOIN config.messaggi_errore m ON m.codice = c.codice AND m.lingua = 'it'
      WHERE c.codice = 'E_ATTIVO_BLOCK_SI_RITIRA' AND c.obsoleto_dal IS NULL),
    'CONFLITTO_STATO / true',
    '6) E_ATTIVO_BLOCK_SI_RITIRA e'' a catalogo, CONFLITTO_STATO, con la frase italiana');

-- ============================================================
-- 7) Senza ritiro, i codici di prima
-- ============================================================
--   L'unita' base del componente: catalogo.unita_misura non ha obsoleto_dal, e
--   l'articolo (attivo) la nomina.
SELECT is(
    pg_temp.rifiuto(format(
        'UPDATE catalogo.unita_misura SET attivo = false WHERE id = %L',
        (SELECT a.uom_id FROM catalogo.articoli a WHERE a.id = (SELECT comp_id FROM tmp_sr)))) ->> 'codice',
    'E_ATTIVO_BLOCK_CHILDREN_ACTIVE',
    '7) una tabella senza ritiro resta col codice di prima');

SELECT * FROM finish();
ROLLBACK;
