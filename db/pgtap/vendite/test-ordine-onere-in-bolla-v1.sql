-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la riga-onere dell'ordine dice se e' gia' passata in una bolla, per il
--   dialog «Genera DDT» (la nota «passa intero nella prima bolla» solo sugli
--   oneri ancora da passare).
--   vendite.vw_ordini_righe_dettaglio.onere_in_bolla
-- ChangeSet: 20261103-65
-- Brief: brief-db-addebito-trasporto-ordine (richiesta del team FE, 2026-11-03)
-- ------------------------------------------------------------
-- Indice test (plan 5):
--   1) prima della bolla: l'onere e' da passare (false), la merce NULL
--   2) dopo la prima bolla: l'onere e' passato (true), la merce resta NULL
--   3) la vista e la copia dicono la stessa cosa: una seconda bolla non porta
--      l'onere che la vista dice passato
--   4) il legame ritirato con la riga di bolla: l'onere torna da passare
--   5) su tutto l'archivio onere_in_bolla e' «la riga-onere ha il suo legame»
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP onere in bolla');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

CREATE TEMP TABLE _caus AS
WITH ins AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
    VALUES ('PGT_OIB_1', 'PGT_OIB_1', 'Fixture pgTAP: onere in bolla')
    RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE _a AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-OIB-ONERE', false,
         p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                                  WHERE nv.codice_interno = 'SERVIZIO_UNA_TANTUM'),
         p_causale_onere_id  => (SELECT id FROM _caus)) AS onere,
       dbops.fn_pgtap_crea_articolo('PGT-OIB-MERCE', false) AS merce;

CREATE TEMP TABLE _o AS
SELECT o.ordine_id AS id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('pgTAP OIB', 'CONFERMATO',
         (SELECT billing_account_id FROM _m),
         p_righe => jsonb_build_array(
             jsonb_build_object('articolo_id', (SELECT merce FROM _a), 'quantita', 3, 'prezzo', 5),
             jsonb_build_object('articolo_id', (SELECT onere FROM _a), 'quantita', 1, 'prezzo', 15))) o;

CREATE OR REPLACE FUNCTION pg_temp.stato() RETURNS text
LANGUAGE sql AS $$
  SELECT string_agg(d.articolo_codice || ':' || coalesce(d.onere_in_bolla::text, 'NULL'), ',' ORDER BY d.riga_nr)
    FROM vendite.vw_ordini_righe_dettaglio d WHERE d.ordine_id = (SELECT id FROM _o)
$$;

SELECT is(pg_temp.stato(), 'PGT-OIB-MERCE:NULL,PGT-OIB-ONERE:false',
  '1) prima della bolla: l''onere e'' da passare, la merce NULL');

-- La prima bolla porta una parte della merce: l'ordine resta da evadere.
CREATE TEMP TABLE _d AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP OIB bolla 1', 'DRAFT',
         p_ordine_id => (SELECT id FROM _o),
         p_righe => jsonb_build_array(jsonb_build_object(
             'ordine_riga_id', (SELECT r.id FROM vendite.ordini_righe r
                                 WHERE r.ordine_id = (SELECT id FROM _o) AND r.articolo_id = (SELECT merce FROM _a)),
             'qta_da_evadere', 1)));

SELECT is(pg_temp.stato(), 'PGT-OIB-MERCE:NULL,PGT-OIB-ONERE:true',
  '2) dopo la prima bolla: l''onere e'' passato, la merce resta NULL');

CREATE TEMP TABLE _d2 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP OIB bolla 2', 'DRAFT',
         p_ordine_id => (SELECT id FROM _o));

SELECT is(
  (SELECT count(*)::int FROM vendite.ddt_righe dr
    WHERE dr.ddt_id = (SELECT ddt_id FROM _d2) AND dr.articolo_id = (SELECT onere FROM _a)),
  0,
  '3) la seconda bolla non porta l''onere che la vista dice passato');

SELECT vendite.fn_ddt_riga_ritira_legami(
         (SELECT dr.id FROM vendite.ddt_righe dr
           WHERE dr.ddt_id = (SELECT ddt_id FROM _d) AND dr.articolo_id = (SELECT onere FROM _a)));

SELECT is(pg_temp.stato(), 'PGT-OIB-MERCE:NULL,PGT-OIB-ONERE:false',
  '4) il legame ritirato con la riga di bolla: l''onere torna da passare');

SELECT is(
  (SELECT count(*)::int
     FROM vendite.vw_ordini_righe_dettaglio d
    WHERE d.e_onere
      AND d.onere_in_bolla IS DISTINCT FROM EXISTS (
            SELECT 1 FROM vendite.ordini_righe_fulfillment f WHERE f.ordine_riga_id = d.id)),
  0,
  '5) onere_in_bolla e'' «la riga-onere ha il suo legame», su tutto l''archivio');

SELECT * FROM finish();
ROLLBACK;
