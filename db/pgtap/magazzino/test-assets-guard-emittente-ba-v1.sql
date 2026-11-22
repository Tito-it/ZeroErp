-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: il cliente (billing_account_id) di un seriale e' dell'azienda del
--   seriale — script.trgfn_doc_guard_emittente_ba montato su magazzino.assets.
--   ChangeSet: 20_code/magazzino/20261122-12, 20_code/script/20261122-13.
--   Brief: brief-db-magazzino-tutte-le-scritture-dal-verbo §5.3 (Tid 2026-11-22).
--
-- ⭐ Il mondo si COSTRUISCE: due aziende col loro operatore e un cliente
--   ciascuna; il mondo di B nel SUO contesto, il tentativo in quello di A.
--   I seriali nascono dal builder, cioe' dal verbo magazzino.fn_aggiungi_asset.
-- ⚠️ Gira come l'APPLICAZIONE.
--
-- Elenco test (plan 5):
--   1) il trigger e' montato, BEFORE INSERT OR UPDATE OF billing_account_id,
--      emittente_fiscale_id, con gli argomenti del seriale
--   2) seriale di A col cliente di A: nasce, col cliente
--   3) seriale di A senza cliente: nasce
--   4) seriale di A col cliente di B: E_DOC_EMITTENTE_BA_INCOERENTE
--   5) ... e la frase non nomina il codice del cliente di B (no-leak dentro il verbo;
--      i nomi delle aziende no: anagrafiche.soggetti non ha RLS)
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- B: il suo cliente, nel suo contesto.
CREATE TEMP TABLE _b AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _b)); END $ctx$;
CREATE TEMP TABLE _bb0 AS
SELECT r.billing_account_id AS ba
  FROM dbops.fn_pgtap_crea_cliente_ba('PGT-AGB-B', NULL, (SELECT soggetto_ruolo_id FROM _b)) r;
-- Il codice del BA di B si legge QUI, nel suo contesto: da A, sotto RLS, non si vede.
CREATE TEMP TABLE _bb AS
SELECT b.ba, (SELECT ba.codice FROM anagrafiche.billing_account ba WHERE ba.id = b.ba) AS codice
  FROM _bb0 b;

-- A: chi agisce, col suo cliente e un articolo a seriale.
CREATE TEMP TABLE _a AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _a)); END $ctx$;
CREATE TEMP TABLE _fa AS
SELECT r.billing_account_id                                              AS ba,
       dbops.fn_pgtap_crea_articolo('PGT-AGB-SER', true, false, true)    AS art
  FROM dbops.fn_pgtap_crea_cliente_ba('PGT-AGB-A', NULL, (SELECT soggetto_ruolo_id FROM _a)) r;

-- 1
SELECT ok(
    EXISTS (SELECT 1 FROM pg_trigger t
             WHERE t.tgrelid = 'magazzino.assets'::regclass
               AND t.tgname  = 'trg_assets_a10_guard_emittente_ba_ins_upd'
               AND pg_get_triggerdef(t.oid) LIKE
                   '%BEFORE INSERT OR UPDATE OF billing_account_id, emittente_fiscale_id ON magazzino.assets%'
               AND pg_get_triggerdef(t.oid) LIKE
                   '%trgfn_doc_guard_emittente_ba(''Seriale'', ''seriale'', ''emittente_fiscale_id'', ''E_DOC_EMITTENTE_BA_INCOERENTE'')%'),
    '1) trg_assets_a10_guard_emittente_ba_ins_upd e'' montato con gli argomenti del seriale');

-- 2-3
-- ⚠️ La nascita e la lettura in due istruzioni: nella stessa, la lettura non vede la riga.
CREATE TEMP TABLE _n AS
SELECT dbops.fn_pgtap_crea_asset(f.art, 'PGT-AGB-SN1', jsonb_build_object('billing_account_id', f.ba)) AS con_ba,
       dbops.fn_pgtap_crea_asset(f.art, 'PGT-AGB-SN2')                                              AS senza_ba
  FROM _fa f;

SELECT is(
    (SELECT a.billing_account_id FROM magazzino.assets a JOIN _n n ON n.con_ba = a.id),
    (SELECT ba FROM _fa),
    '2) seriale di A col cliente di A: nasce, col cliente');

SELECT ok(
    (SELECT a.billing_account_id IS NULL FROM magazzino.assets a JOIN _n n ON n.senza_ba = a.id),
    '3) seriale di A senza cliente: nasce');

-- 4-5
CREATE TEMP TABLE _err (codice text, messaggio text);
DO $e$
BEGIN
    PERFORM dbops.fn_pgtap_crea_asset((SELECT art FROM _fa), 'PGT-AGB-SN3',
                                      jsonb_build_object('billing_account_id', (SELECT ba FROM _bb)));
    INSERT INTO _err VALUES (NULL, 'nessun errore');
EXCEPTION WHEN OTHERS THEN
    INSERT INTO _err VALUES (dbops.fn_pgtap_codice_errore(format(
        $q$SELECT dbops.fn_pgtap_crea_asset(%L::uuid, 'PGT-AGB-SN4', jsonb_build_object('billing_account_id', %s))$q$,
        (SELECT art FROM _fa), (SELECT ba FROM _bb))), SQLERRM);
END $e$;

SELECT is((SELECT codice FROM _err), 'E_DOC_EMITTENTE_BA_INCOERENTE',
          '4) seriale di A col cliente di B: E_DOC_EMITTENTE_BA_INCOERENTE');

SELECT ok(
    (SELECT bb.codice IS NOT NULL AND position(bb.codice IN e.messaggio) = 0 FROM _err e, _bb bb),
    '5) ... e la frase non nomina il codice del cliente di B');

SELECT * FROM finish();
ROLLBACK;
