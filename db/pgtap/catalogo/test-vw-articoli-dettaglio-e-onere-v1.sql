-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la vista dell'articolo dice se l'articolo e' un onere, per il picker
--   delle righe di documento e per il form articolo.
--   catalogo.vw_articoli_dettaglio (e_onere, causale_onere_id,
--   causale_onere_codice_interno, causale_onere_descrizione)
-- ChangeSet: 20261103-53, 20261112-40
-- Brief: brief-db-addebito-trasporto-ordine §9.9 (richiesta del team FE), §9.10
-- ------------------------------------------------------------
-- Indice test (plan 7):
--   1) l'articolo-onere: e_onere vero, la sua causale
--   2) la merce: e_onere falso, causale NULL
--   3) e_onere segue causale_onere_id: tolta la causale, lo stesso articolo
--      costruito non e' piu' un onere (prima il test iterava su tutto il catalogo:
--      brief-db-revisione-catalogo, giro 5-A)
--   4) le due colonne nuove stanno subito dopo requires_lotto, dove le ha
--      messe in coda il 20261103-53 (il BE legge per nome, il resto non si
--      sposta). Si controlla la posizione relativa e non "le ultime 3": le
--      colonne aggiunte in coda dopo (obsoleto_dal ed e_obsoleto, 20261106-03)
--      sono legittime e non devono far diventare rosso il test.
--      Rev. 2026-11-06.
--   5) l'articolo-onere decodifica la causale: codice_interno e descrizione
--      della fixture (il codice utente, diverso apposta, non esce: C-1)
--   6) la merce: le due decodifiche NULL
--   7) le due decodifiche stanno subito dopo e_obsoleto, in coda
--      (20261112-40). Rev. 2026-11-12.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

CREATE TEMP TABLE _caus AS
WITH ins AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
    VALUES ('PGT_VAE_1', 'PGT_VAE_UTENTE', 'Fixture pgTAP: vista articolo onere')
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
  (SELECT v.causale_onere_codice_interno || '|' || v.causale_onere_descrizione
     FROM catalogo.vw_articoli_dettaglio v WHERE v.id = (SELECT onere FROM _a)),
  'PGT_VAE_1|Fixture pgTAP: vista articolo onere',
  '5) l''articolo-onere decodifica la causale: codice_interno e descrizione');

SELECT is(
  (SELECT coalesce(v.causale_onere_codice_interno, 'NULL') || '|'
          || coalesce(v.causale_onere_descrizione, 'NULL')
     FROM catalogo.vw_articoli_dettaglio v WHERE v.id = (SELECT merce FROM _a)),
  'NULL|NULL',
  '6) la merce: le due decodifiche NULL');

UPDATE catalogo.articoli SET causale_onere_id = NULL WHERE id = (SELECT onere FROM _a);

SELECT is(
  (SELECT v.e_onere::text || '|' || coalesce(v.causale_onere_id::text, 'NULL')
     FROM catalogo.vw_articoli_dettaglio v WHERE v.id = (SELECT onere FROM _a)),
  'false|NULL',
  '3) tolta la causale, lo stesso articolo non e'' piu'' un onere');

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

SELECT is(
  (SELECT string_agg(c.column_name::text, ',' ORDER BY c.ordinal_position)
     FROM information_schema.columns c
    CROSS JOIN (SELECT c2.ordinal_position AS pos
                  FROM information_schema.columns c2
                 WHERE c2.table_schema = 'catalogo'
                   AND c2.table_name = 'vw_articoli_dettaglio'
                   AND c2.column_name = 'e_obsoleto') r
    WHERE c.table_schema = 'catalogo' AND c.table_name = 'vw_articoli_dettaglio'
      AND c.ordinal_position BETWEEN r.pos AND r.pos + 2),
  'e_obsoleto,causale_onere_codice_interno,causale_onere_descrizione',
  '7) le due decodifiche della causale subito dopo e_obsoleto');

SELECT * FROM finish();
ROLLBACK;
