-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Un articolo-onere e' un addebito, non un bene: non e' gestito a magazzino,
-- non e' composito, non e' a lotti ne' a matricola.
-- Brief: brief-db-addebito-trasporto-ordine §8.1 (decisione 10 di Tid,
--   2026-11-03)
-- ChangeSet: 20261103-16 (script.fn_natura_e_merce), 20261103-18
--   (catalogo.trgfn_articoli_guard_onere_natura), 20261103-20 (montaggio)
--
-- Elenco test (plan 15):
--  L'onere che nasce da bene (INSERT)
--   1) gestito a magazzino -> E_ARTICOLO_ONERE_STRUTTURA
--   2) composito -> E_ARTICOLO_ONERE_STRUTTURA
--   3) a lotti -> E_ARTICOLO_ONERE_STRUTTURA
--   4) a matricola -> E_ARTICOLO_ONERE_STRUTTURA
--   5) l'onere corretto (non gestito, natura di servizio) nasce
--  L'onere che diventa bene (UPDATE della SOLA colonna nuova: il montaggio
--  la deve avere nell'elenco OF, linee-guida-trigger)
--   6) gestito a magazzino -> E_ARTICOLO_ONERE_STRUTTURA
--   7) composito -> E_ARTICOLO_ONERE_STRUTTURA
--   8) a lotti -> E_ARTICOLO_ONERE_STRUTTURA
--   9) a matricola -> E_ARTICOLO_ONERE_STRUTTURA
--  10) un UPDATE che non tocca le sei colonne passa (non rigiudica)
--  Il bene che diventa onere
--  11) merce gestita che riceve una causale con natura di servizio
--      -> E_ARTICOLO_ONERE_STRUTTURA
--  12) merce gestita che riceve una causale tenendo la natura merce: parla
--      la natura (E_ARTICOLO_ONERE_NATURA_MERCE), regola 1 prima della 2
--  La merce non e' toccata
--  13) la merce nasce gestita, a lotti e a matricola
--  14) e cambia i suoi flag
--  Il montaggio
--  15) il trigger scatta su UPDATE OF le sei colonne della funzione
--
-- Scopo:
--  - la regola 2 di catalogo.trgfn_articoli_guard_onere_natura e il suo
--    montaggio. La regola 1 (natura) e' di
--    catalogo/test-distinta-un-livello-e-onere-natura-v1.sql.
--  Il mondo si costruisce: articoli e causali propri (la causale e' 1:1 con
--  l'articolo-onere). Le nature si leggono dal vocabolario per DESTINAZIONE.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(15);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _nat AS
SELECT (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'ORDINE_VENDITA' AND nv.attivo ORDER BY nv.id LIMIT 1) AS merce,
       (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'COMMESSA' AND nv.attivo ORDER BY nv.id LIMIT 1)       AS servizio;

-- Una causale per ogni articolo-onere che il test fa nascere o diventare.
CREATE TEMP TABLE _causale AS
WITH ins AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
    VALUES ('PGT_AOS_1', 'PGT_AOS_1', 'Fixture pgTAP: onere struttura 1'),
           ('PGT_AOS_2', 'PGT_AOS_2', 'Fixture pgTAP: onere struttura 2'),
           ('PGT_AOS_3', 'PGT_AOS_3', 'Fixture pgTAP: onere struttura 3')
    RETURNING id, codice_interno
)
SELECT (SELECT id FROM ins WHERE codice_interno = 'PGT_AOS_1') AS c1,
       (SELECT id FROM ins WHERE codice_interno = 'PGT_AOS_2') AS c2,
       (SELECT id FROM ins WHERE codice_interno = 'PGT_AOS_3') AS c3;

-- ============================================================
-- L'onere che nasce da bene (1-5)
-- ============================================================
-- ⚠️ Il pattern e' la frase del messaggio prima del segnaposto della
--   caratteristica: ogni caso accende UNA colonna sola, quindi la frase basta.
SELECT throws_like(
    $$ SELECT dbops.fn_pgtap_crea_articolo('PGT-AOS-N1', true,
           p_natura_vendita_id => (SELECT servizio FROM _nat),
           p_causale_onere_id  => (SELECT c1 FROM _causale)) $$,
    '%un onere non può essere%',
    '1) onere che nasce gestito a magazzino: E_ARTICOLO_ONERE_STRUTTURA');

SELECT throws_like(
    $$ SELECT dbops.fn_pgtap_crea_articolo('PGT-AOS-N2', false,
           p_is_composito      => true,
           p_natura_vendita_id => (SELECT servizio FROM _nat),
           p_causale_onere_id  => (SELECT c1 FROM _causale)) $$,
    '%un onere non può essere%',
    '2) onere che nasce composito: E_ARTICOLO_ONERE_STRUTTURA');

SELECT throws_like(
    $$ SELECT dbops.fn_pgtap_crea_articolo('PGT-AOS-N3', false, true,
           p_natura_vendita_id => (SELECT servizio FROM _nat),
           p_causale_onere_id  => (SELECT c1 FROM _causale)) $$,
    '%un onere non può essere%',
    '3) onere che nasce a lotti: E_ARTICOLO_ONERE_STRUTTURA');

SELECT throws_like(
    $$ SELECT dbops.fn_pgtap_crea_articolo('PGT-AOS-N4', false, false, true,
           p_natura_vendita_id => (SELECT servizio FROM _nat),
           p_causale_onere_id  => (SELECT c1 FROM _causale)) $$,
    '%un onere non può essere%',
    '4) onere che nasce a matricola: E_ARTICOLO_ONERE_STRUTTURA');

CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-AOS-ONERE', false,
           p_natura_vendita_id => n.servizio,
           p_causale_onere_id  => (SELECT c1 FROM _causale))   AS onere,
       dbops.fn_pgtap_crea_articolo('PGT-AOS-BENE-A', true,
           p_natura_vendita_id => n.merce)                     AS bene_a,
       dbops.fn_pgtap_crea_articolo('PGT-AOS-BENE-B', true,
           p_natura_vendita_id => n.merce)                     AS bene_b
  FROM _nat n;

SELECT ok(
    (SELECT a.causale_onere_id = (SELECT c1 FROM _causale)
            AND NOT a.gestito_a_magazzino AND NOT a.is_composito
            AND NOT a.requires_lotto AND NOT a.requires_serial
       FROM catalogo.articoli a WHERE a.id = (SELECT onere FROM _art)),
    '5) l''onere corretto (non gestito, natura di servizio) nasce');

-- ============================================================
-- L'onere che diventa bene (6-10): UPDATE della SOLA colonna
-- ============================================================
SELECT throws_like(
    $$ UPDATE catalogo.articoli SET gestito_a_magazzino = true WHERE id = (SELECT onere FROM _art) $$,
    '%un onere non può essere%',
    '6) onere che diventa gestito a magazzino: E_ARTICOLO_ONERE_STRUTTURA');

SELECT throws_like(
    $$ UPDATE catalogo.articoli SET is_composito = true WHERE id = (SELECT onere FROM _art) $$,
    '%un onere non può essere%',
    '7) onere che diventa composito: E_ARTICOLO_ONERE_STRUTTURA');

SELECT throws_like(
    $$ UPDATE catalogo.articoli SET requires_lotto = true WHERE id = (SELECT onere FROM _art) $$,
    '%un onere non può essere%',
    '8) onere che diventa a lotti: E_ARTICOLO_ONERE_STRUTTURA');

SELECT throws_like(
    $$ UPDATE catalogo.articoli SET requires_serial = true WHERE id = (SELECT onere FROM _art) $$,
    '%un onere non può essere%',
    '9) onere che diventa a matricola: E_ARTICOLO_ONERE_STRUTTURA');

SELECT lives_ok(
    $$ UPDATE catalogo.articoli SET descrizione = 'Fixture pgTAP: onere corretto, descrizione nuova'
        WHERE id = (SELECT onere FROM _art) $$,
    '10) un UPDATE che non tocca le sei colonne passa');

-- ============================================================
-- Il bene che diventa onere (11-12)
-- ============================================================
SELECT throws_like(
    $$ UPDATE catalogo.articoli
          SET causale_onere_id  = (SELECT c2 FROM _causale),
              natura_vendita_id = (SELECT servizio FROM _nat)
        WHERE id = (SELECT bene_a FROM _art) $$,
    '%un onere non può essere%',
    '11) merce gestita che diventa onere con natura di servizio: E_ARTICOLO_ONERE_STRUTTURA');

SELECT throws_like(
    $$ UPDATE catalogo.articoli SET causale_onere_id = (SELECT c3 FROM _causale)
        WHERE id = (SELECT bene_b FROM _art) $$,
    '%e'' un onere, e un onere non puo'' avere la natura%',
    '12) merce gestita che diventa onere con natura merce: parla la natura (regola 1 prima della 2)');

-- ============================================================
-- La merce non e' toccata (13-14)
-- ============================================================
SELECT lives_ok(
    $$ SELECT dbops.fn_pgtap_crea_articolo('PGT-AOS-BENE-LS', true, true, true,
           p_natura_vendita_id => (SELECT merce FROM _nat)) $$,
    '13) la merce nasce gestita, a lotti e a matricola');

SELECT lives_ok(
    $$ UPDATE catalogo.articoli
          SET requires_lotto = true, requires_serial = true
        WHERE id = (SELECT bene_a FROM _art) $$,
    '14) la merce cambia i suoi flag');

-- ============================================================
-- Il montaggio (15)
-- ============================================================
SELECT is(
    (SELECT array_agg(a.attname::text ORDER BY a.attname)
       FROM pg_trigger t
       CROSS JOIN LATERAL unnest(t.tgattr) AS k(attnum)
       JOIN pg_attribute a ON a.attrelid = t.tgrelid AND a.attnum = k.attnum
      WHERE t.tgrelid = 'catalogo.articoli'::regclass
        AND t.tgname  = 'trg_articoli_a10_guard_onere_natura_ins_upd'),
    ARRAY['causale_onere_id', 'gestito_a_magazzino', 'is_composito',
          'natura_vendita_id', 'requires_lotto', 'requires_serial'],
    '15) il guard scatta su UPDATE OF le sei colonne che la funzione giudica');

SELECT * FROM finish();
ROLLBACK;
