-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Una causale onere va a un articolo solo: il picker offre le libere, il
-- guard rifiuta il doppione col suo codice.
-- Brief: brief-db-addebito-trasporto-ordine §9.10 (C-2, C-3, Tid 2026-11-12)
-- ChangeSet: 20261112-41 (catalogo.vw_causali_onere_assegnabili),
--   20261112-42 (regola 0 di catalogo.trgfn_articoli_guard_onere_natura);
--   seed config.tabelle_gestibili, codice E_ARTICOLO_CAUSALE_ONERE_GIA_USATA
--
-- Elenco test (plan 11):
--  Il picker (C-2)
--   1) una causale libera e' nella vista
--   2) data a un articolo, esce dalla vista
--   3) il lookup generico sulla vista da' la libera e non la legata
--   4) una causale libera ma non attiva: nella vista si', il lookup delle
--      attive la toglie (il filtro attivo e' del lookup, non della vista)
--   5) la vista e' nel lookup generico (config.tabelle_gestibili), fuori dal
--      pannello
--  Il doppione (C-3)
--   6) INSERT di un onere con la causale di un altro -> E_ARTICOLO_CAUSALE_ONERE_GIA_USATA,
--      la frase nomina l'articolo che la porta
--   7) UPDATE della SOLA causale verso una gia' usata -> stesso codice
--   8) un UPDATE che riscrive la stessa causale passa (non e' un doppione)
--   9) la regola 0 parla prima della struttura: doppione E gestito a
--      magazzino -> il doppione
--  10) l'indice uq_articoli_causale_onere resta (la rete per le scritture
--      concorrenti)
--  11) SQLSTATE e codice: P0001 col codice di dominio, non 23505
--
-- Il mondo si costruisce: causali e articoli propri. Le nature si leggono dal
-- vocabolario per DESTINAZIONE.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(11);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _nat AS
SELECT (SELECT nv.id FROM config.nature_vendita nv
         WHERE nv.destinazione_tipo = 'COMMESSA' AND nv.attivo ORDER BY nv.id LIMIT 1) AS servizio;

CREATE TEMP TABLE _causale AS
WITH ins AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione, attivo)
    VALUES ('PGT_COA_1', 'PGT_COA_1', 'Fixture pgTAP: causale assegnabile 1', true),
           ('PGT_COA_2', 'PGT_COA_2', 'Fixture pgTAP: causale assegnabile 2', true),
           ('PGT_COA_3', 'PGT_COA_3', 'Fixture pgTAP: causale assegnabile 3', false)
    RETURNING id, codice_interno
)
SELECT (SELECT id FROM ins WHERE codice_interno = 'PGT_COA_1') AS c1,
       (SELECT id FROM ins WHERE codice_interno = 'PGT_COA_2') AS c2,
       (SELECT id FROM ins WHERE codice_interno = 'PGT_COA_3') AS c3;

-- ============================================================
-- Il picker (1-5)
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM catalogo.vw_causali_onere_assegnabili v
             WHERE v.id = (SELECT c1 FROM _causale)),
    '1) una causale libera e'' nella vista');

CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-COA-A1', false,
           p_natura_vendita_id => (SELECT servizio FROM _nat),
           p_causale_onere_id  => (SELECT c1 FROM _causale)) AS a1,
       dbops.fn_pgtap_crea_articolo('PGT-COA-A2', false,
           p_natura_vendita_id => (SELECT servizio FROM _nat),
           p_causale_onere_id  => (SELECT c2 FROM _causale)) AS a2;

SELECT ok(
    NOT EXISTS (SELECT 1 FROM catalogo.vw_causali_onere_assegnabili v
                 WHERE v.id = (SELECT c1 FROM _causale)),
    '2) data a un articolo, la causale esce dalla vista');

-- Una causale libera e attiva tutta del test, per il lookup.
INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
VALUES ('PGT_COA_4', 'PGT_COA_4', 'Fixture pgTAP: causale assegnabile 4');

SELECT is(
    (SELECT string_agg(l.codice_interno, ',' ORDER BY l.codice_interno)
       FROM dbops.fn_get_lookup_codici('catalogo.vw_causali_onere_assegnabili'::regclass,
                                       p_attivo_only => true, p_limit => 10000) l
      WHERE starts_with(l.codice_interno, 'PGT_COA_')),
    'PGT_COA_4',
    '3) il lookup generico sulla vista: la libera attiva si'', le legate no');

SELECT is(
    (SELECT string_agg(l.codice_interno, ',' ORDER BY l.codice_interno)
       FROM dbops.fn_get_lookup_codici('catalogo.vw_causali_onere_assegnabili'::regclass,
                                       p_attivo_only => false, p_limit => 10000) l
      WHERE starts_with(l.codice_interno, 'PGT_COA_')),
    'PGT_COA_3,PGT_COA_4',
    '4) la libera non attiva e'' nella vista; il lookup delle attive la toglie (test 3)');

SELECT is(
    (SELECT tg.lookup::text || '|' || tg.pannello::text
       FROM config.tabelle_gestibili tg
      WHERE tg.codice_interno = 'catalogo.vw_causali_onere_assegnabili'),
    'true|false',
    '5) la vista e'' nel lookup generico, fuori dal pannello');

-- ============================================================
-- Il doppione (6-11)
-- ============================================================
SELECT throws_like(
    $$ SELECT dbops.fn_pgtap_crea_articolo('PGT-COA-D1', false,
           p_natura_vendita_id => (SELECT servizio FROM _nat),
           p_causale_onere_id  => (SELECT c1 FROM _causale)) $$,
    '%è già dell''articolo PGT-COA-A1%',
    '6) INSERT con la causale di un altro: E_ARTICOLO_CAUSALE_ONERE_GIA_USATA, nomina chi la porta');

SELECT throws_like(
    $$ UPDATE catalogo.articoli SET causale_onere_id = (SELECT c1 FROM _causale)
        WHERE id = (SELECT a2 FROM _art) $$,
    '%è già dell''articolo PGT-COA-A1%',
    '7) UPDATE della sola causale verso una gia'' usata: E_ARTICOLO_CAUSALE_ONERE_GIA_USATA');

SELECT lives_ok(
    $$ UPDATE catalogo.articoli SET causale_onere_id = causale_onere_id
        WHERE id = (SELECT a1 FROM _art) $$,
    '8) un UPDATE che riscrive la stessa causale passa');

SELECT throws_like(
    $$ SELECT dbops.fn_pgtap_crea_articolo('PGT-COA-D2', true,
           p_natura_vendita_id => (SELECT servizio FROM _nat),
           p_causale_onere_id  => (SELECT c1 FROM _causale)) $$,
    '%è già dell''articolo PGT-COA-A1%',
    '9) doppione e gestito a magazzino: parla il doppione (regola 0 prima della 2)');

SELECT ok(
    EXISTS (SELECT 1 FROM pg_index i
             WHERE i.indexrelid = to_regclass('catalogo.uq_articoli_causale_onere')
               AND i.indisunique),
    '10) l''indice uq_articoli_causale_onere resta');

SELECT throws_ok(
    $$ UPDATE catalogo.articoli SET causale_onere_id = (SELECT c1 FROM _causale)
        WHERE id = (SELECT a2 FROM _art) $$,
    'P0001',
    NULL,
    '11) il doppione e'' P0001 (codice di dominio), non 23505');

SELECT * FROM finish();
ROLLBACK;
