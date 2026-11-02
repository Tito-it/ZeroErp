-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: deprecabilità catalogo pratiche via obsoleto_dal
--       (brief-db-deprecabilita-catalogo-vs-istanze, P1; migrazioni 20260630-01/02)
-- ------------------------------------------------------------
-- Indice test (1..11):
--  1) colonna obsoleto_dal presente su tipi_prestazione
--  2) colonna obsoleto_dal presente su template_flussi
--  3) obsoleto_dal è di tipo date (tipi_prestazione)
--  4) PREVENTIVI_IMMEDIATA: obsoleto_dal valorizzato e <= oggi (ritirato)
--  5) PREVENTIVI_DIFFERITA: obsoleto_dal valorizzato e <= oggi (ritirato)
--  6) i vecchi tipi restano attivo=true (ritiro via data, NON disattivazione)
--  7) tipo unico PREVENTIVI: obsoleto_dal IS NULL (selezionabile)
--  8) tipo unico PREVENTIVI: attivo=true
--  9) nessun template dei vecchi tipi resta selezionabile (tutti obsoleto_dal NOT NULL)
-- 10) tutti i template del tipo unico restano selezionabili (obsoleto_dal NULL)
-- 11) predicato di selezione: tra i tipi PREVENTIVI* esattamente 1 è selezionabile
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

-- 1) / 2) / 3) struttura
SELECT has_column('pratiche', 'tipi_prestazione', 'obsoleto_dal',
  'obsoleto_dal presente su pratiche.tipi_prestazione');
SELECT has_column('pratiche', 'template_flussi', 'obsoleto_dal',
  'obsoleto_dal presente su pratiche.template_flussi');
SELECT col_type_is('pratiche', 'tipi_prestazione', 'obsoleto_dal', 'date',
  'obsoleto_dal è di tipo date');

-- 4) / 5) vecchi tipi ritirati (obsoleto_dal valorizzato e gia attivo)
SELECT ok(
  (SELECT obsoleto_dal IS NOT NULL AND obsoleto_dal <= script.fn_data_operativa()
     FROM pratiche.tipi_prestazione WHERE codice_interno = 'PREVENTIVI_IMMEDIATA'),
  'PREVENTIVI_IMMEDIATA: obsoleto_dal valorizzato e <= oggi (ritirato)'
);
SELECT ok(
  (SELECT obsoleto_dal IS NOT NULL AND obsoleto_dal <= script.fn_data_operativa()
     FROM pratiche.tipi_prestazione WHERE codice_interno = 'PREVENTIVI_DIFFERITA'),
  'PREVENTIVI_DIFFERITA: obsoleto_dal valorizzato e <= oggi (ritirato)'
);

-- 6) PUNTO CHIAVE DEL DISEGNO: i vecchi tipi NON sono stati disattivati.
SELECT ok(
  (SELECT bool_and(attivo) FROM pratiche.tipi_prestazione
    WHERE codice_interno IN ('PREVENTIVI_IMMEDIATA', 'PREVENTIVI_DIFFERITA')),
  'i vecchi tipi restano attivo=true (ritiro via obsoleto_dal, non disattivazione)'
);

-- 7) / 8) tipo unico selezionabile e attivo
SELECT ok(
  (SELECT obsoleto_dal IS NULL FROM pratiche.tipi_prestazione WHERE codice_interno = 'PREVENTIVI'),
  'tipo unico PREVENTIVI: obsoleto_dal IS NULL (selezionabile)'
);
SELECT ok(
  (SELECT attivo FROM pratiche.tipi_prestazione WHERE codice_interno = 'PREVENTIVI'),
  'tipo unico PREVENTIVI: attivo=true'
);

-- 9) template dei vecchi tipi: tutti ritirati
SELECT is(
  (SELECT count(*) FROM pratiche.template_flussi tf
     JOIN pratiche.tipi_prestazione tp ON tp.id = tf.tipo_prestazione_id
    WHERE tp.codice_interno IN ('PREVENTIVI_IMMEDIATA', 'PREVENTIVI_DIFFERITA')
      AND tf.obsoleto_dal IS NULL),
  0::bigint,
  'nessun template dei vecchi tipi resta selezionabile (obsoleto_dal tutti valorizzati)'
);

-- 10) template del tipo unico: tutti selezionabili
SELECT is(
  (SELECT count(*) FROM pratiche.template_flussi tf
     JOIN pratiche.tipi_prestazione tp ON tp.id = tf.tipo_prestazione_id
    WHERE tp.codice_interno = 'PREVENTIVI'
      AND tf.obsoleto_dal IS NOT NULL),
  0::bigint,
  'tutti i template del tipo unico restano selezionabili (obsoleto_dal NULL)'
);

-- 11) predicato di selezione-per-il-nuovo: tra i PREVENTIVI* solo il tipo unico passa
SELECT is(
  (SELECT count(*) FROM pratiche.tipi_prestazione
    WHERE codice_interno LIKE 'PREVENTIVI%'
      AND attivo
      AND (obsoleto_dal IS NULL OR obsoleto_dal > script.fn_data_operativa())),
  1::bigint,
  'predicato selezione: tra i tipi PREVENTIVI* esattamente 1 (il tipo unico) è selezionabile'
);

SELECT * FROM finish();
ROLLBACK;
