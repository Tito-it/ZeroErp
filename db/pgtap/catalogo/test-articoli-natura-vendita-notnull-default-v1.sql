-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: catalogo.articoli.natura_vendita_id obbligatoria (brief-preventivi-ordini.md
--       D3), migration 20260609-03. Backfill conservativo NULL->MERCE + DEFAULT
--       MERCE + NOT NULL. Il DEFAULT permette ai nuovi articoli (BE non ancora
--       aggiornato) di partire da MERCE; servizi/ricorrenti si classificano poi.
--
-- Indice test (1..4):
--   1) natura_vendita_id NOT NULL
--   2) nessun articolo con natura_vendita_id NULL (backfill completo)
--   3) INSERT articolo senza natura_vendita_id -> ammesso (DEFAULT)
--   4) la natura dell'articolo appena inserito = MERCE (default applicato)
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

SELECT plan(4);

-- ============================================================
-- 1) natura_vendita_id NOT NULL
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM information_schema.columns
            WHERE table_schema='catalogo' AND table_name='articoli'
              AND column_name='natura_vendita_id' AND is_nullable='NO'),
    '1) catalogo.articoli.natura_vendita_id NOT NULL'
);

-- ============================================================
-- 2) nessun articolo con natura NULL (backfill completo)
-- ============================================================
SELECT is(
    (SELECT count(*) FROM catalogo.articoli WHERE natura_vendita_id IS NULL),
    0::bigint,
    '2) nessun articolo con natura_vendita_id NULL (backfill -> MERCE completo)'
);

-- ============================================================
-- Fixture: valori FK validi presi da un articolo esistente
-- ============================================================
CREATE TEMP TABLE tmp_art_ref AS
SELECT uom_id, tipo_voce_id, gruppo_voce_id, spesa_id, iva_id
  FROM catalogo.articoli
 ORDER BY id LIMIT 1;

-- ============================================================
-- 3) INSERT senza natura_vendita_id -> ammesso (DEFAULT MERCE)
-- ============================================================
SELECT lives_ok(
    $$INSERT INTO catalogo.articoli (codice, descrizione, uom_id, tipo_voce_id, gruppo_voce_id, spesa_id, iva_id)
      SELECT 'PGTAP_NAT_NOTNULL_ART', 'Articolo test natura default',
             uom_id, tipo_voce_id, gruppo_voce_id, spesa_id, iva_id
        FROM tmp_art_ref$$,
    '3) INSERT articolo senza natura_vendita_id -> ammesso (DEFAULT)'
);

-- ============================================================
-- 4) natura dell'articolo inserito = MERCE
-- ============================================================
SELECT is(
    (SELECT natura_vendita_id FROM catalogo.articoli WHERE codice='PGTAP_NAT_NOTNULL_ART'),
    (SELECT id FROM config.nature_vendita WHERE codice_interno='MERCE'),
    '4) articolo senza natura -> DEFAULT = MERCE'
);

SELECT * FROM finish();
ROLLBACK;
