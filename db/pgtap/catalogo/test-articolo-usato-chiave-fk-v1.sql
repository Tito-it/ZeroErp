-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- pgtap-runner: owner
-- pgtap-runner-motivo: il test crea una tabella con una FK verso
--   catalogo.articoli(codice): e' DDL, che il ruolo applicativo non fa. Una
--   tabella temporanea non puo' avere una FK verso una tabella permanente. La
--   tabella nasce e muore nella transazione del test.
--
-- Test: catalogo.fn_articolo_usato conta una FK sulla chiave a cui punta.
--
-- Elenco test (plan 3):
--  1) una tabella con una FK verso il codice dell'articolo, vuota: non usato,
--     senza errore
--  2) con una riga che punta al codice: usato, senza errore
--  3) un altro articolo, non puntato: non usato
--
-- Scopo:
--  - D18: il predicato confrontava ogni colonna FK con l'uuid dell'articolo, senza
--    guardare a quale colonna puntasse. Una FK verso il codice falliva con un
--    errore di tipo (e con lei il guard dell'uso e il form).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(3);

CREATE TEMP TABLE tmp_uf AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-USFK-A') AS a,
       dbops.fn_pgtap_crea_articolo('PGTAP-USFK-B') AS b;

CREATE TABLE catalogo.pgtap_usato_per_codice (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codice_articolo varchar(64) NOT NULL REFERENCES catalogo.articoli (codice)
);

-- 1
SELECT is(catalogo.fn_articolo_usato((SELECT a FROM tmp_uf)), false,
          '1) FK verso il codice, tabella vuota: non usato, senza errore');

INSERT INTO catalogo.pgtap_usato_per_codice (codice_articolo)
SELECT a.codice FROM catalogo.articoli a WHERE a.id = (SELECT a FROM tmp_uf);

-- 2
SELECT is(catalogo.fn_articolo_usato((SELECT a FROM tmp_uf)), true,
          '2) una riga punta al codice: usato');

-- 3
SELECT is(catalogo.fn_articolo_usato((SELECT b FROM tmp_uf)), false,
          '3) un altro articolo, non puntato: non usato');

SELECT * FROM finish();
ROLLBACK;
