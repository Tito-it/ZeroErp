-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il building block «la natura e' merce»: script.fn_natura_e_merce.
-- Brief: brief-db-addebito-trasporto-ordine §8.1 (regola del 2)
-- ChangeSet: 20261103-16
--
-- Elenco test (plan 6):
--   1) ogni natura con destinazione ORDINE_VENDITA (merce): vero
--   2) ogni natura con destinazione COMMESSA (servizio una tantum): falso
--   3) ogni natura con destinazione CONTRATTO (servizio ricorrente): falso
--   4) natura NULL: NULL (decide il chiamante)
--   5) natura che non esiste: NULL
--   6) il verdetto coincide con la destinazione su tutto il vocabolario
--      (nessuna natura fuori dalla regola)
--
-- Scopo:
--  - il contratto del BB scritto nel suo COMMENT: vero/falso dalla
--    destinazione di config.nature_vendita, NULL se la natura manca.
--  Il vocabolario e' catalogo (seed): si legge per DESTINAZIONE, non per id
--  ne' per codice. Nessun dato di dominio da costruire.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ⚠️ bool_and su TUTTE le nature della destinazione, non una a caso: dice
--   «nessuna e' incoerente». Il count > 0 tiene il test fuori dal verde per
--   sottrazione (vocabolario vuoto = bool_and NULL = rosso, non verde).
SELECT ok(
    (SELECT count(*) > 0 AND bool_and(script.fn_natura_e_merce(nv.id) IS TRUE)
       FROM config.nature_vendita nv WHERE nv.destinazione_tipo = 'ORDINE_VENDITA'),
    '1) natura merce (destinazione ORDINE_VENDITA): vero');

SELECT ok(
    (SELECT count(*) > 0 AND bool_and(script.fn_natura_e_merce(nv.id) IS FALSE)
       FROM config.nature_vendita nv WHERE nv.destinazione_tipo = 'COMMESSA'),
    '2) servizio una tantum (destinazione COMMESSA): falso');

SELECT ok(
    (SELECT count(*) > 0 AND bool_and(script.fn_natura_e_merce(nv.id) IS FALSE)
       FROM config.nature_vendita nv WHERE nv.destinazione_tipo = 'CONTRATTO'),
    '3) servizio ricorrente (destinazione CONTRATTO): falso');

SELECT is(script.fn_natura_e_merce(NULL), NULL::boolean,
    '4) natura NULL: NULL');

SELECT is(script.fn_natura_e_merce((SELECT COALESCE(max(nv.id), 0) + 1000 FROM config.nature_vendita nv)),
          NULL::boolean,
    '5) natura che non esiste: NULL');

SELECT is(
    (SELECT count(*) FROM config.nature_vendita nv
      WHERE script.fn_natura_e_merce(nv.id) IS DISTINCT FROM (nv.destinazione_tipo = 'ORDINE_VENDITA')),
    0::bigint,
    '6) su tutto il vocabolario il verdetto e'' la destinazione ORDINE_VENDITA');

SELECT * FROM finish();
ROLLBACK;
