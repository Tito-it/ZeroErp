-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il lotto e' dell'azienda:
--   magazzino.lotti.emittente_fiscale_id, unicita' per azienda, RLS  (20261122-14)
--   default di sessione e guard di perimetro                          (20261122-15)
--   magazzino.fn_modifica_lotto nel perimetro                         (20261122-16)
--   script.trgfn_guard_riferimento_stesso_emittente sui sei figli     (20261122-17)
--   script.fn_check_riga_magazzino, passo 6                           (20261122-18)
--   Brief: brief-db-magazzino-lotto-dell-azienda, D-L1, D-L2, D-L4, D-L5, D-L6.
--
-- ⭐ I casi si COSTRUISCONO: due emittenti con il loro operatore
--   (fn_pgtap_crea_emittente_operatore: BLOCCATO ovunque, il livello lo scrive
--   il test con dbops.fn_pgtap_concedi_livello_area). Il mondo di B (lotto con lo STESSO
--   codice e seriale dello stesso articolo) nasce nel SUO contesto; i
--   tentativi si fanno in quello di A.
--
-- ⚠️ Gira come l'APPLICAZIONE: la RLS di lettura e il no-leak si provano solo
--   cosi'. Le righe di inventario l'app le scrive ancora diretta (Lotto 2 del
--   brief vicino): e' la strada su cui il guard dei figli si prova.
--
-- Elenco test (plan 17):
--   la struttura
--    1) emittente_fiscale_id NOT NULL
--    2) l'unicita' e' (emittente_fiscale_id, articolo_id, codice), in quest'ordine
--    3) RLS accesa, senza FORCE, con rls_lotti_ef_whitelist
--    4) default di sessione e guard di perimetro montati, per funzione e argomenti
--   la nascita e la lettura
--    5) fn_aggiungi_lotto in A con il codice del lotto di B: nasce, dell'emittente di A
--    6) A vede un solo lotto con quel codice: il suo (RLS)
--    7) lo stesso codice due volte in A: uq_mag_lotti_emittente_articolo_codice
--   il no-leak
--    8) fn_modifica_lotto sul lotto di B: E_MAG_LOTTO_NON_TROVATO
--    9) fn_check_riga_magazzino sotto RLS col lotto di B: LOTTO_DI_ALTRO_ARTICOLO,
--       non «di altro emittente» (il lotto altrui non si vede)
--   il guard dei figli (inventari_righe)
--   10) riga col lotto proprio: passa
--   11) riga col lotto di B: E_RIFERIMENTO_DI_ALTRO_EMITTENTE, campo lotto_id
--   12) riga col seriale di B: E_RIFERIMENTO_DI_ALTRO_EMITTENTE
--   13) riga con un lotto che non esiste: lo stesso codice (no-leak)
--   14) modifica della riga (verbo) verso il lotto di B, con la quantita': E_RIFERIMENTO_DI_ALTRO_EMITTENTE
--   15) modifica della riga (verbo) che non tocca il riferimento: passa
--   la forma
--   16) i dodici montaggi: lotto_id e asset_id dei sei figli, coi modi giusti
--   17) fra gli a10 di movimenti il perimetro parla prima del riferimento
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(17);

-- ============================================================
-- Fixture: B (l'altro emittente), nel suo contesto
-- ============================================================
CREATE TEMP TABLE _b AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
CREATE TEMP TABLE _a AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Gli articoli sono comuni a tutte le aziende: nascono una volta.
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-LDA-LOTTI',   true, true,  false) AS lotti,
       dbops.fn_pgtap_crea_articolo('PGT-LDA-SERIALE', true, false, true)  AS ser;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _b)); END $ctx$;
CREATE TEMP TABLE _fb AS
SELECT dbops.fn_pgtap_crea_lotto_di_magazzino(a.lotti, 'PGT-LDA-L1', DATE '2026-11-01') AS lotto,
       dbops.fn_pgtap_crea_asset(a.ser, 'PGT-LDA-SB')                                   AS asset
  FROM _art a;

-- ============================================================
-- Fixture: A (chi agisce), nel suo contesto
-- ============================================================
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _a)); END $ctx$;
CREATE TEMP TABLE _fa AS
SELECT dbops.fn_pgtap_crea_magazzino('PGT-LDA-A', false)                                AS mag,
       dbops.fn_pgtap_crea_lotto_di_magazzino(a.lotti, 'PGT-LDA-L0', DATE '2026-11-01') AS lotto,
       (SELECT emittente_fiscale_id FROM _a)                                            AS ef
  FROM _art a;

-- Un inventario in bozza di A, per le righe.
CREATE TEMP TABLE _inv AS SELECT dbops.fn_pgtap_crea_inventario(mag) AS inv FROM _fa;

-- Il livello d'area dell'operatore A.
-- ⭐ rev 2026-11-25 (D-L a, brief-db-porte-aperte-dalla-sola-guc): il livello d'area lo
--   da' il builder dbops.fn_pgtap_concedi_livello_area; la copia pg_temp.livello_area
--   che stava qui e' ritirata (regola del 2).
SELECT dbops.fn_pgtap_concedi_livello_area((SELECT auth_user_id FROM _a), 'magazzino', 'TUTTO');

-- I montaggi di una funzione trigger, come «schema.tabella:arg1:arg2:…»,
-- letti per funzione e argomenti (linee-guida-trigger: mai per nome).
CREATE OR REPLACE FUNCTION pg_temp.montaggi(p_fn regprocedure) RETURNS text[]
LANGUAGE sql AS $fx$
    -- ⚠️ L'ordine sull'espressione, in una sottoquery: dentro un aggregato
    --   ORDER BY 1 ordina per la costante 1, cioe' non ordina.
    SELECT COALESCE(array_agg(m.montaggio ORDER BY m.montaggio COLLATE "C"), '{}')
      FROM (SELECT n.nspname || '.' || c.relname || ':'
                   || array_to_string(dbops.fn_trigger_argomenti(t.tgargs), ':') AS montaggio
              FROM pg_catalog.pg_trigger t
              JOIN pg_catalog.pg_class c     ON c.oid = t.tgrelid
              JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
             WHERE t.tgfoid = p_fn AND NOT t.tgisinternal) AS m
$fx$;

-- ============================================================
-- 1-4 La struttura
-- ============================================================
SELECT col_not_null('magazzino', 'lotti', 'emittente_fiscale_id',
    '1. magazzino.lotti.emittente_fiscale_id e'' NOT NULL');

SELECT is(
    (SELECT array_agg(a.attname::text ORDER BY k.ord)
       FROM pg_catalog.pg_constraint c
      CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord)
       JOIN pg_catalog.pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
      WHERE c.conrelid = 'magazzino.lotti'::regclass
        AND c.conname = 'uq_mag_lotti_emittente_articolo_codice'
        AND c.contype = 'u'),
    ARRAY['emittente_fiscale_id', 'articolo_id', 'codice'],
    '2. il codice e'' unico per (emittente_fiscale_id, articolo_id, codice)');

SELECT ok(
    (SELECT c.relrowsecurity AND NOT c.relforcerowsecurity
            AND EXISTS (SELECT 1 FROM pg_catalog.pg_policy p
                         WHERE p.polrelid = c.oid AND p.polname = 'rls_lotti_ef_whitelist')
       FROM pg_catalog.pg_class c WHERE c.oid = 'magazzino.lotti'::regclass),
    '3. RLS accesa senza FORCE, con rls_lotti_ef_whitelist');

SELECT ok(
    'magazzino.lotti:SOLLEVA' = ANY (pg_temp.montaggi('script.trgfn_default_emittente_fiscale()'::regprocedure))
    AND 'magazzino.lotti:fiscale:emittente_fiscale_id' = ANY (pg_temp.montaggi('script.trgfn_guard_emittente_scope()'::regprocedure)),
    '4. su lotti: il default di sessione (SOLLEVA) e il guard di perimetro (fiscale, emittente_fiscale_id)');

-- ============================================================
-- 5-7 La nascita e la lettura
-- ============================================================
CREATE TEMP TABLE _nato AS
SELECT magazzino.fn_aggiungi_lotto(a.lotti, 'PGT-LDA-L1', DATE '2026-11-02') AS lotto FROM _art a;

SELECT is(
    (SELECT l.emittente_fiscale_id FROM magazzino.lotti l WHERE l.id = (SELECT lotto FROM _nato)),
    (SELECT ef FROM _fa),
    '5. fn_aggiungi_lotto col codice del lotto di B: nasce, dell''emittente della sessione (A)');

SELECT is(
    (SELECT array_agg(l.id) FROM magazzino.lotti l
      WHERE l.articolo_id = (SELECT lotti FROM _art) AND l.codice = 'PGT-LDA-L1'),
    ARRAY[(SELECT lotto FROM _nato)],
    '6. A vede un solo lotto con quel codice, il suo: quello di B la RLS non lo mostra');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_aggiungi_lotto((SELECT lotti FROM _art),
        'PGT-LDA-L1', DATE '2026-11-03')$$),
    'uq_mag_lotti_emittente_articolo_codice',
    '7. lo stesso codice due volte nella stessa azienda: uq_mag_lotti_emittente_articolo_codice');

-- ============================================================
-- 8-9 Il no-leak
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_lotto((SELECT lotto FROM _fb),
        '{"data_scadenza": "2027-01-01"}'::jsonb)$$),
    'E_MAG_LOTTO_NON_TROVATO',
    '8. fn_modifica_lotto sul lotto di B: E_MAG_LOTTO_NON_TROVATO, come un id che non esiste');

SELECT is(
    (SELECT script.fn_check_riga_magazzino(f.mag, a.lotti, b.lotto) -> 0 ->> 'reason'
       FROM _fa f, _art a, _fb b),
    'LOTTO_DI_ALTRO_ARTICOLO',
    '9. fn_check_riga_magazzino sotto RLS col lotto di B: LOTTO_DI_ALTRO_ARTICOLO, non dice che esiste');

-- ============================================================
-- 10-15 Il guard dei figli, sulle righe di inventario
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT dbops.fn_pgtap_crea_riga_inventario(i.inv, a.lotti, 1, jsonb_build_object('lotto_id', f.lotto))
        FROM _inv i, _art a, _fa f$$),
    NULL,
    '10. riga di inventario col lotto proprio: passa');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT dbops.fn_pgtap_crea_riga_inventario(i.inv, a.lotti, 2, jsonb_build_object('lotto_id', b.lotto))
        FROM _inv i, _art a, _fb b$$),
    'E_RIFERIMENTO_DI_ALTRO_EMITTENTE',
    '11. riga di inventario col lotto di B: E_RIFERIMENTO_DI_ALTRO_EMITTENTE');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT dbops.fn_pgtap_crea_riga_inventario(i.inv, a.ser, 1, jsonb_build_object('asset_id', b.asset))
        FROM _inv i, _art a, _fb b$$),
    'E_RIFERIMENTO_DI_ALTRO_EMITTENTE',
    '12. riga di inventario col seriale di B: E_RIFERIMENTO_DI_ALTRO_EMITTENTE');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT dbops.fn_pgtap_crea_riga_inventario(i.inv, a.lotti, 3,
            jsonb_build_object('lotto_id', (SELECT max(l.id) + 1000000 FROM magazzino.lotti l)))
        FROM _inv i, _art a$$),
    'E_RIFERIMENTO_DI_ALTRO_EMITTENTE',
    '13. riga con un lotto che non esiste: lo stesso codice del lotto altrui (no-leak)');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_riga_documento_interno('INVENTARIO', i.inv, r.id,
            jsonb_build_object('lotto_id', (SELECT lotto FROM _fb), 'qta_contata', 5))
        FROM _inv i JOIN magazzino.inventari_righe r ON r.inventario_id = i.inv
       WHERE r.lotto_id = (SELECT lotto FROM _fa)$$),
    'E_RIFERIMENTO_DI_ALTRO_EMITTENTE',
    '14. modifica della riga verso il lotto di B, con la quantita'': E_RIFERIMENTO_DI_ALTRO_EMITTENTE');

SELECT is(
    dbops.fn_pgtap_codice_errore($$SELECT magazzino.fn_modifica_riga_documento_interno('INVENTARIO', i.inv, r.id,
            jsonb_build_object('qta_contata', 7))
        FROM _inv i JOIN magazzino.inventari_righe r ON r.inventario_id = i.inv
       WHERE r.lotto_id = (SELECT lotto FROM _fa)$$),
    NULL,
    '15. modifica della riga che non tocca il riferimento: passa');

-- ============================================================
-- 16-17 La forma
-- ============================================================
SELECT is(
    pg_temp.montaggi('script.trgfn_guard_riferimento_stesso_emittente()'::regprocedure),
    ARRAY[
        'magazzino.inventari_righe:inventario:inventario_id:asset:asset_id',
        'magazzino.inventari_righe:inventario:inventario_id:lotto_magazzino:lotto_id',
        'magazzino.movimenti:magazzino:magazzino_id:asset:asset_id',
        'magazzino.movimenti:magazzino:magazzino_id:lotto_magazzino:lotto_id',
        'magazzino.movimenti_attesi:magazzino:magazzino_id:asset:asset_id',
        'magazzino.movimenti_attesi:magazzino:magazzino_id:lotto_magazzino:lotto_id',
        'magazzino.rettifiche_righe:rettifica:rettifica_id:asset:asset_id',
        'magazzino.rettifiche_righe:rettifica:rettifica_id:lotto_magazzino:lotto_id',
        'magazzino.trasferimenti_righe:trasferimento:trasferimento_id:asset:asset_id',
        'magazzino.trasferimenti_righe:trasferimento:trasferimento_id:lotto_magazzino:lotto_id',
        'vendite.ddt_righe_prelievi:ddt_riga:ddt_riga_id:asset:asset_id',
        'vendite.ddt_righe_prelievi:ddt_riga:ddt_riga_id:lotto_magazzino:lotto_id'],
    '16. il guard del riferimento: lotto_id e asset_id dei sei figli, coi modi della riga');

SELECT ok(
    (SELECT max(t.tgname::text COLLATE "C") FILTER (WHERE t.tgfoid = 'script.trgfn_guard_emittente_scope()'::regprocedure)
          < min(t.tgname::text COLLATE "C") FILTER (WHERE t.tgfoid = 'script.trgfn_guard_riferimento_stesso_emittente()'::regprocedure)
       FROM pg_catalog.pg_trigger t
      WHERE t.tgrelid = 'magazzino.movimenti'::regclass AND NOT t.tgisinternal),
    '17. su movimenti il guard di perimetro scatta prima di quello del riferimento');

SELECT * FROM finish();
ROLLBACK;
