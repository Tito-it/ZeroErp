-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: param VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG presente e collisione
--       id=38 risolta (seed parameters_vendite_defaults, id 38 -> 53)
-- ------------------------------------------------------------
-- Indice test (1..3):
--  1) VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG presente con default_value = '30'
--  2) id=38 resta documenti_allegato_upload_max_mb (collisione risolta, niente clobber)
--  3) tutti i 12 codici vendite-default presenti (nessuno perso per collisione)
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

SELECT plan(3);

-- 1) Il parametro mancante e' stato creato col valore corretto.
SELECT is(
  (SELECT default_value FROM config.parameters
    WHERE code = 'VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG'),
  '30',
  'VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG presente con default_value = 30'
);

-- 2) id=38 non e' piu' conteso: resta il parametro documenti.
SELECT is(
  (SELECT code FROM config.parameters WHERE id = 38),
  'documenti_allegato_upload_max_mb',
  'id=38 resta documenti_allegato_upload_max_mb (collisione risolta)'
);

-- 3) Tutti i 12 codici del seed vendite-default sono presenti
--    (MODALITA esclusa di proposito: rimossa da 20260515-16).
SELECT is(
  (
    SELECT count(*)::int
    FROM config.parameters
    WHERE code = ANY(ARRAY[
      'VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG',
      'VENDITE_PREVENTIVO_DEFAULT_FATTURAZIONE_IMMEDIATA',
      'VENDITE_CONTRATTO_DEFAULT_AMBITO',
      'VENDITE_CONTRATTO_DEFAULT_TIPO_VARIAZIONE_GLOBALE',
      'VENDITE_CONTRATTO_DEFAULT_DATA_LEAD_GG',
      'VENDITE_CONTRATTO_DEFAULT_VALIDO_DAL_LEAD_GG',
      'VENDITE_LISTINI_NEW_VERSIONE_LEAD_GG',
      'VENDITE_LISTINI_CLONE_VERSIONE_LEAD_GG',
      'VENDITE_LISTINI_CLONE_VERSIONE_CODICE_SUFFIX',
      'VENDITE_LISTINI_CLOSE_VERSIONE_LEAD_GG',
      'VENDITE_PROMO_DEFAULT_VALIDO_DAL_LEAD_GG',
      'VENDITE_PROMO_DEFAULT_ATTIVO'
    ])
  ),
  12,
  'tutti i 12 codici vendite-default presenti'
);

SELECT * FROM finish();

ROLLBACK;
