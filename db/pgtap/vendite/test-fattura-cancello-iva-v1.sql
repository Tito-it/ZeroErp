-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: una fattura non si emette con una riga senza aliquota IVA; la bozza
--   resta libera e il suo riepilogo non si rompe.
--   script.fn_check_fattura_emettibile, vendite.trgfn_fatture_guard_stato,
--   vendite.fn_ricalcola_riepilogo_iva_fattura.
-- Riferimento: decisione di Tid del 2026-08-29 (bozza libera, cancello
--   all'emissione, guardia nel riepilogo: DDT, ordini, preventivi), estesa
--   alla fattura con D-3 del 2026-10-22; richiesta BE §9.9 di
--   brief-be-utenti-di-sviluppo. changeSet 20261022-06 … -08; codice
--   E_FATTURA_RIGA_IVA_MANCANTE.
-- rev 2026-10-27 (brief-modello-documento-vendita §15, giro 11): con la porta
--   sulla fattura (20261027-17) il test 4 emette dal verbo della fattura
--   (vendite.fn_fattura_proietta_stato), e il cancello scatta come prima. Attese
--   invariate.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - una riga senza codice IVA si salva in bozza, e il riepilogo IVA della
--     bozza si calcola (prima sollevava un errore tecnico di catalogo);
--   - la check elenca il motivo, con la riga e la sua descrizione;
--   - entrare in EMESSA con quella riga e' rifiutato col codice di dominio;
--   - una fattura con tutte le aliquote non ha motivi.
--
-- Elenco test (plan 6):
--   1) il riepilogo della bozza con una riga senza IVA si calcola
--   2) la check: E_FATTURA_RIGA_IVA_MANCANTE, con riga_nr nel dettaglio
--   3) i valori della frase: fattura, riga_nr, descrizione
--   4) DRAFT -> EMESSA con la riga senza IVA -> E_FATTURA_RIGA_IVA_MANCANTE
--   5) data l'aliquota alla riga, la check non ha piu' motivi
--   6) il codice e' registrato, classe CONFLITTO_STATO
--
-- ⚠️ I rifiuti si asseriscono sul CODICE (CONSTRAINT_NAME dell'eccezione).
-- ⚠️ La riga si scrive a mano: nessuna funzione DB inserisce in
--   vendite.fatture_righe (le costruisce il giro del backend).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre il builder della fattura, che
--   qui si chiama come su un database ricostruito.

SELECT plan(6);

-- ============================================================
-- Fixture
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.codice_errore(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

CREATE TEMP TABLE t_f AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('cancello iva');

-- Una riga SENZA codice IVA: e' il caso dell'articolo senza iva_id su una
-- fornitura senza tipo d'uso (origine ASSENTE del risolutore).
CREATE TEMP TABLE t_r AS
WITH ins AS (
    INSERT INTO vendite.fatture_righe (
        fattura_id, riga_nr, descrizione, qta, prezzo_unitario, imponibile_riga,
        competenza_dal, competenza_al, iva_id)
    SELECT f.fattura_id, 1, 'Riga senza IVA', 1, 10.00, 10.00,
           script.fn_data_operativa(), script.fn_data_operativa(), NULL
      FROM t_f f
    RETURNING id
)
SELECT id AS riga_id FROM ins;

-- ============================================================
-- 1) Il riepilogo della bozza si calcola
-- ============================================================
SELECT lives_ok(
    format('SELECT * FROM vendite.fn_ricalcola_riepilogo_iva_fattura(%s)',
           (SELECT fattura_id FROM t_f)),
    '1) il riepilogo IVA della bozza con una riga senza IVA si calcola (prima: errore tecnico di catalogo)'
);

-- ============================================================
-- 2-3) La check
-- ============================================================
CREATE TEMP TABLE t_m AS
SELECT script.fn_check_fattura_emettibile((SELECT fattura_id FROM t_f)) AS motivi;

SELECT is(
    (SELECT (motivi -> 0 ->> 'codice') || ' ' || (motivi -> 0 -> 'dettaglio' ->> 'riga_nr')
       FROM t_m),
    'E_FATTURA_RIGA_IVA_MANCANTE 1',
    '2) la check elenca E_FATTURA_RIGA_IVA_MANCANTE, con la riga nel dettaglio'
);

SELECT is(
    (SELECT motivi -> 0 -> 'valori' FROM t_m),
    jsonb_build_array((SELECT fattura_id FROM t_f)::text, '1', 'Riga senza IVA'),
    '3) i valori della frase: la fattura (id, in bozza non ha numero), la riga, la descrizione'
);

-- ============================================================
-- 4) Il cancello all'emissione
-- ============================================================
SELECT is(
    pg_temp.codice_errore(format(
        $$SELECT vendite.fn_fattura_proietta_stato(%s, (SELECT s.id FROM config.stati_doc_fiscale s
                                                          WHERE s.codice_interno = 'EMESSA'))$$,
        (SELECT fattura_id FROM t_f))),
    'E_FATTURA_RIGA_IVA_MANCANTE',
    '4) DRAFT -> EMESSA con una riga senza IVA -> E_FATTURA_RIGA_IVA_MANCANTE'
);

-- ============================================================
-- 5) Con l'aliquota, nessun motivo
-- ============================================================
UPDATE vendite.fatture_righe
   SET iva_id = (SELECT i.id FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1)
 WHERE id = (SELECT riga_id FROM t_r);

SELECT is(
    script.fn_check_fattura_emettibile((SELECT fattura_id FROM t_f)),
    '[]'::jsonb,
    '5) data l''aliquota alla riga, la check non ha piu'' motivi'
);

-- ============================================================
-- 6) Il codice e' registrato
-- ============================================================
SELECT is(
    (SELECT ce.classe::text FROM config.codici_errore ce
      WHERE ce.codice = 'E_FATTURA_RIGA_IVA_MANCANTE'),
    'CONFLITTO_STATO',
    '6) E_FATTURA_RIGA_IVA_MANCANTE e'' registrato, classe CONFLITTO_STATO'
);

SELECT * FROM finish();
ROLLBACK;
