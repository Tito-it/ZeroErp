-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Ordine e bolla ammettono la merce e l'articolo-onere; un servizio che non
-- e' un onere resta fuori.
-- Brief: brief-db-addebito-trasporto-ordine §7.1, §8.1 (decisione 1 di Tid,
--   2026-11-03: D-1 e D-2 diventano «MERCE e oneri")
-- ChangeSet: 20261103-16 (script.fn_natura_e_merce), 20261103-17
--   (script.fn_check_articolo_riga_su_contesto)
--
-- Elenco test (plan 13):
--  La check (script.fn_check_articolo_riga, che compone quella su contesto)
--   1) onere su ordine: nessun motivo (fino al 20261103-17 era
--      E_RIGA_NATURA_NON_AMMESSA: la sua natura e' di servizio)
--   2) onere su bolla: nessun motivo
--   3) servizio non-onere su ordine: E_RIGA_NATURA_NON_AMMESSA
--   4) servizio non-onere su bolla: E_RIGA_NATURA_NON_AMMESSA
--   5) merce su ordine e su bolla: nessun motivo
--   6) onere su preventivo: nessun motivo, come prima (il ramo del preventivo
--      non cambia)
--  Il guard di riga (script.trgfn_righe_guard_articolo_ammesso)
--   7) ordine: la riga con l'onere entra
--   8) ordine: il servizio non-onere e' rifiutato
--   9) ordine: la merce entra
--  10) bolla: la riga con l'onere entra
--  11) bolla: il servizio non-onere e' rifiutato
--  12) bolla: la merce entra
--  Il picker (catalogo.fn_articoli_ammessi), che segue da se'
--  13) su ordine: onere e merce ammessi (motivo NULL), il servizio no
--
-- Scopo:
--  - il ramo ORDINE_VENDITA / DDT_VENDITA della check di ammissione: merce
--    OPPURE articolo con causale_onere_id; «e' merce» dal BB.
--  Il mondo si costruisce: articoli, causale onere (1:1 con l'articolo),
--  cliente, ordine e bolla propri. Le nature si leggono dal vocabolario per
--  DESTINAZIONE (la regola legge quella), non per id.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _nat AS
SELECT (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'ORDINE_VENDITA' AND nv.attivo ORDER BY nv.id LIMIT 1) AS merce,
       (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'COMMESSA' AND nv.attivo ORDER BY nv.id LIMIT 1)       AS servizio;

-- Una causale propria: la causale e' 1:1 con l'articolo-onere, e quelle del
-- seed hanno gia' il loro.
CREATE TEMP TABLE _causale AS
WITH ins AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
    VALUES ('PGT_AOR_ONERE', 'PGT_AOR_ONERE', 'Fixture pgTAP: onere su ordine e bolla')
    RETURNING id
)
SELECT id FROM ins;

-- M merce, S servizio una tantum (non onere), O onere (natura di servizio,
-- non gestito: un onere non e' un bene, 20261103-18).
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-AOR-M', false,
           p_natura_vendita_id => n.merce)                     AS m,
       dbops.fn_pgtap_crea_articolo('PGT-AOR-S', false,
           p_natura_vendita_id => n.servizio)                  AS s,
       dbops.fn_pgtap_crea_articolo('PGT-AOR-O', false,
           p_natura_vendita_id => n.servizio,
           p_causale_onere_id  => (SELECT id FROM _causale))   AS o
  FROM _nat n;

CREATE TEMP TABLE _iva AS
SELECT (SELECT i.id FROM config.iva i WHERE i.attivo AND i.aliquota_iva > 0 ORDER BY i.id LIMIT 1) AS id;

CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP oneri su ordine e bolla');

-- ============================================================
-- La check (1-6)
-- ============================================================
SELECT is(script.fn_check_articolo_riga('ORDINE_VENDITA', NULL, (SELECT o FROM _art)),
          '[]'::jsonb,
    '1) check: onere su ordine, nessun motivo');

SELECT is(script.fn_check_articolo_riga('DDT_VENDITA', NULL, (SELECT o FROM _art)),
          '[]'::jsonb,
    '2) check: onere su bolla, nessun motivo');

SELECT is(script.fn_check_articolo_riga('ORDINE_VENDITA', NULL, (SELECT s FROM _art)) -> 0 ->> 'codice',
          'E_RIGA_NATURA_NON_AMMESSA',
    '3) check: servizio non-onere su ordine, E_RIGA_NATURA_NON_AMMESSA');

SELECT is(script.fn_check_articolo_riga('DDT_VENDITA', NULL, (SELECT s FROM _art)) -> 0 ->> 'codice',
          'E_RIGA_NATURA_NON_AMMESSA',
    '4) check: servizio non-onere su bolla, E_RIGA_NATURA_NON_AMMESSA');

SELECT is(script.fn_check_articolo_riga('ORDINE_VENDITA', NULL, (SELECT m FROM _art))
          || script.fn_check_articolo_riga('DDT_VENDITA', NULL, (SELECT m FROM _art)),
          '[]'::jsonb,
    '5) check: merce su ordine e su bolla, nessun motivo');

SELECT is(script.fn_check_articolo_riga('PREVENTIVO', NULL, (SELECT o FROM _art)),
          '[]'::jsonb,
    '6) check: onere su preventivo, nessun motivo (ramo invariato)');

-- ============================================================
-- Il guard di riga (7-12)
-- ============================================================
CREATE TEMP TABLE _ord AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('pgTAP oneri su ordine e bolla',
                                         p_billing_account_id => (SELECT billing_account_id FROM _m));

SELECT lives_ok(
    format($$INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, iva_id, prezzo_unitario, qta_operativa)
             VALUES (%s, 1, %L, 'onere', %s, 10, 1)$$,
           (SELECT ordine_id FROM _ord), (SELECT o FROM _art), (SELECT id FROM _iva)),
    '7) ordine: la riga con l''onere entra');

-- ⚠️ Il pattern e' la frase stabile del messaggio 1297 (la conservano il
--   testo di prima e quello del 2026-11-03), non il messaggio intero: il codice
--   e la natura interpolati lo spezzano.
SELECT throws_like(
    format($$INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, iva_id, prezzo_unitario, qta_operativa)
             VALUES (%s, 2, %L, 'servizio', %s, 10, 1)$$,
           (SELECT ordine_id FROM _ord), (SELECT s FROM _art), (SELECT id FROM _iva)),
    '%vanno solo merci%',
    '8) ordine: il servizio non-onere e'' rifiutato (E_RIGA_NATURA_NON_AMMESSA)');

SELECT lives_ok(
    format($$INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione, iva_id, prezzo_unitario, qta_operativa)
             VALUES (%s, 3, %L, 'merce', %s, 10, 1)$$,
           (SELECT ordine_id FROM _ord), (SELECT m FROM _art), (SELECT id FROM _iva)),
    '9) ordine: la merce entra');

CREATE TEMP TABLE _ddt AS
SELECT dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _m),
                               (SELECT cliente_soggetto_ruolo_id FROM _m), 'VENDITA') AS id;

SELECT lives_ok(
    format($$INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, iva_id, prezzo_unitario)
             VALUES (%s, 1, %L, 'onere', 1, %s, 10)$$,
           (SELECT id FROM _ddt), (SELECT o FROM _art), (SELECT id FROM _iva)),
    '10) bolla: la riga con l''onere entra');

SELECT throws_like(
    format($$INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa)
             VALUES (%s, 2, %L, 'servizio', 1)$$,
           (SELECT id FROM _ddt), (SELECT s FROM _art)),
    '%vanno solo merci%',
    '11) bolla: il servizio non-onere e'' rifiutato (E_RIGA_NATURA_NON_AMMESSA)');

SELECT lives_ok(
    format($$INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, iva_id, prezzo_unitario)
             VALUES (%s, 3, %L, 'merce', 1, %s, 10)$$,
           (SELECT id FROM _ddt), (SELECT m FROM _art), (SELECT id FROM _iva)),
    '12) bolla: la merce entra');

-- ============================================================
-- Il picker (13)
-- ============================================================
SELECT is(
    (SELECT jsonb_object_agg(f.codice, f.motivo IS NULL)
       FROM catalogo.fn_articoli_ammessi('ORDINE_VENDITA', (SELECT ordine_id FROM _ord), 'PGT-AOR-') f),
    jsonb_build_object('PGT-AOR-M', true, 'PGT-AOR-O', true, 'PGT-AOR-S', false),
    '13) picker su ordine: onere e merce ammessi, il servizio no');

SELECT * FROM finish();
ROLLBACK;
