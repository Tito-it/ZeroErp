-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la vista dell'articolo dice se l'articolo e' un onere, per il picker
--   delle righe di documento e per il form articolo.
--   catalogo.vw_articoli_dettaglio (e_onere, causale_onere_id)
-- ChangeSet: 20261103-53
-- Brief: brief-db-addebito-trasporto-ordine §9.9 (richiesta del team FE)
-- ------------------------------------------------------------
-- Indice test (plan 4):
--   1) l'articolo-onere: e_onere vero, la sua causale
--   2) la merce: e_onere falso, causale NULL
--   3) e_onere e' la definizione di articolo-onere su tutto il catalogo
--      (causale_onere_id IS NOT NULL), seed compreso
--   4) le due colonne nuove stanno subito dopo requires_lotto, dove le ha
--      messe in coda il 20261103-53 (il BE legge per nome, il resto non si
--      sposta). Si controlla la posizione relativa e non "le ultime 3": le
--      colonne aggiunte in coda dopo (obsoleto_dal ed e_obsoleto, 20261106-03)
--      sono legittime e non devono far diventare rosso il test.
--      Rev. 2026-11-06.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

CREATE TEMP TABLE _caus AS
WITH ins AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
    VALUES ('PGT_VAE_1', 'PGT_VAE_1', 'Fixture pgTAP: vista articolo onere')
    RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE _a AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-VAE-ONERE', false,
         p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                                  WHERE nv.codice_interno = 'SERVIZIO_UNA_TANTUM'),
         p_causale_onere_id  => (SELECT id FROM _caus)) AS onere,
       dbops.fn_pgtap_crea_articolo('PGT-VAE-MERCE', false) AS merce;

SELECT is(
  (SELECT v.e_onere::text || '|' || (v.causale_onere_id = (SELECT id FROM _caus))::text
     FROM catalogo.vw_articoli_dettaglio v WHERE v.id = (SELECT onere FROM _a)),
  'true|true',
  '1) l''articolo-onere: e_onere vero, con la sua causale');

SELECT is(
  (SELECT v.e_onere::text || '|' || coalesce(v.causale_onere_id::text, 'NULL')
     FROM catalogo.vw_articoli_dettaglio v WHERE v.id = (SELECT merce FROM _a)),
  'false|NULL',
  '2) la merce: e_onere falso, causale NULL');

SELECT is(
  (SELECT count(*)::int
     FROM catalogo.vw_articoli_dettaglio v
     JOIN catalogo.articoli a ON a.id = v.id
    WHERE v.e_onere IS DISTINCT FROM (a.causale_onere_id IS NOT NULL)),
  0,
  '3) e_onere e'' causale_onere_id IS NOT NULL su tutto il catalogo');

SELECT is(
  (SELECT string_agg(c.column_name::text, ',' ORDER BY c.ordinal_position)
     FROM information_schema.columns c
    CROSS JOIN (SELECT c2.ordinal_position AS pos
                  FROM information_schema.columns c2
                 WHERE c2.table_schema = 'catalogo'
                   AND c2.table_name = 'vw_articoli_dettaglio'
                   AND c2.column_name = 'requires_lotto') r
    WHERE c.table_schema = 'catalogo' AND c.table_name = 'vw_articoli_dettaglio'
      AND c.ordinal_position BETWEEN r.pos AND r.pos + 2),
  'requires_lotto,e_onere,causale_onere_id',
  '4) e_onere e causale_onere_id subito dopo requires_lotto');

SELECT * FROM finish();
ROLLBACK;
