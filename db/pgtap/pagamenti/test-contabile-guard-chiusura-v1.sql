-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: una distinta non si chiude con righe pronte da registrare, e la
--       matrice parla prima della chiusura —
--       pagamenti.trgfn_vendite_contabili_guard_chiusura
--       (trigger trg_vendite_contabili_a10_guard_verifica_chiusura_upd)
--
-- Elenco test (plan 8):
--  1) fixture: una distinta MANUALE in BOZZA con una riga ABBINATA
--  2) ⭐ BOZZA -> CHIUSA con una riga pronta: parla la MATRICE, non la chiusura
--  3) BOZZA -> VALIDATA passa
--  4) 🔴 VALIDATA -> CHIUSA con una riga pronta: E_CONTABILE_CHIUSURA_CON_RIGHE_PRONTE
--  5) ...e la distinta e' rimasta VALIDATA
--  6) con la riga sospesa (non piu' pronta) la chiusura passa
--  7) l'ordine dei guard di stato e' quello dei nomi: transizione, validazione, verifica_chiusura
--  8) Cleanup
--
-- Scopo:
--  - la regola della chiusura (4-6): una distinta CHIUSA non viene piu'
--    registrata, quindi una riga pronta (stato is_postabile) lasciata sotto
--    sparirebbe da tutti i conti. Le righe NON pronte non la fermano (6): con
--    loro la distinta non si chiuderebbe mai;
--  - ⭐ l'ordine (2, 7): i BEFORE ROW scattano in ordine alfabetico di nome.
--    Il trigger della chiusura si chiamava `…_a10_guard_chiusura_upd` e
--    parlava prima della matrice: un passaggio non ammesso verso CHIUSA
--    riceveva «ci sono righe pronte» invece di «passaggio non ammesso». Dal
--    2026-11-03 si chiama `…_a10_guard_verifica_chiusura_upd` e viene dopo.
--    ⚠️ Il test 2 asserisce il CODICE: e' l'unico modo perche' una rinomina
--    futura che rimette la chiusura davanti diventi rossa;
--  - ⚠️ la distinta si INSERISCE diretta, come in
--    test-righe-distinta-annullata-congelate-v1: la chiave di riuso di
--    fn_get_or_create_vendite_contabile potrebbe restituirne una esistente.
--  - ⚠️ MUTAZIONE: col nome vecchio del trigger il test 2 risponde
--    E_CONTABILE_CHIUSURA_CON_RIGHE_PRONTE e il 7 e' rosso.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- ⚠️ 2. CONTESTO APPLICATIVO.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- Il codice del rifiuto (campo CONSTRAINT dell'eccezione)
-- ============================================================
CREATE FUNCTION pg_temp.codice_rifiuto(p_sql text)
RETURNS text
LANGUAGE plpgsql
AS $fn$
DECLARE
    v_codice text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN_RIFIUTO';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME;
        RETURN COALESCE(NULLIF(v_codice, ''), 'SQLSTATE ' || SQLSTATE);
    END;
END;
$fn$;

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_costanti AS
SELECT 'pgtap_contabile_guard_chiusura'::text AS test_scope;

CREATE TEMP TABLE tmp_cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('contabile guard chiusura') c;

CREATE TEMP TABLE tmp_refs AS
SELECT script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id)                      AS registro_id,
       (SELECT billing_account_id FROM tmp_cli)                                     AS billing_account_id,
       (SELECT utility_id FROM tmp_cli)                                             AS utility_id,
       (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_fiscale_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                          AS valuta_id,
       m.soggetto_ruolo_id                                                         AS emittente_soggetto_ruolo_id,
       (SELECT c.id FROM pagamenti.centri_riscossione c
         WHERE c.attivo IS TRUE AND c.codice_interno = 'BANCA' ORDER BY c.id LIMIT 1) AS centro_banca_id,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'ABBINATA' ORDER BY s.id LIMIT 1)                AS st_abbinata,
       (SELECT s.id FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.codice_interno = 'SOSPESA'  ORDER BY s.id LIMIT 1)                AS st_sospesa,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'BOZZA'    ORDER BY s.id LIMIT 1)                AS d_bozza,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'VALIDATA' ORDER BY s.id LIMIT 1)                AS d_validata,
       (SELECT s.id FROM pagamenti.vendite_contabili_stati s
         WHERE s.codice_interno = 'CHIUSA'   ORDER BY s.id LIMIT 1)                AS d_chiusa
  FROM _mondo m;

CREATE TEMP TABLE tmp_fattura AS
WITH ins AS (
  INSERT INTO vendite.fatture (
      registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
      tipo_doc_fiscale_id, valuta_id, utility_id, totale_a_pagare, meta)
  SELECT r.registro_id, script.fn_data_operativa(), r.emittente_soggetto_ruolo_id, r.billing_account_id,
         r.tipo_doc_fiscale_id, r.valuta_id, r.utility_id, 200.00,
         jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
    FROM tmp_refs r
  RETURNING id
)
SELECT id AS fattura_id FROM ins;

CREATE TEMP TABLE tmp_distinta AS
WITH ins AS (
    INSERT INTO pagamenti.vendite_contabili
        (centro_riscossione_id, data_contabile, data_registrazione, stato_id, origine, meta)
    SELECT r.centro_banca_id, script.fn_data_operativa(), script.fn_data_operativa(),
           r.d_bozza, 'MANUALE',
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
      FROM tmp_refs r
    RETURNING id
)
SELECT id FROM ins;

-- Una riga ABBINATA: is_postabile, cioe' pronta da registrare.
CREATE TEMP TABLE tmp_riga AS
WITH ins AS (
    INSERT INTO pagamenti.vendite_contabili_righe
        (contabile_id, riferimento_ente, data_pagamento, importo,
         fattura_id, billing_account_id, stato_id, meta)
    SELECT (SELECT id FROM tmp_distinta), 'PGTAP_CHIUSURA_PRONTA', script.fn_data_operativa(), 50.00,
           (SELECT fattura_id FROM tmp_fattura), r.billing_account_id, r.st_abbinata,
           jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti))
      FROM tmp_refs r
    RETURNING id
)
SELECT id FROM ins;

SELECT ok(
    (SELECT count(*) = 1 FROM tmp_distinta) AND (SELECT count(*) = 1 FROM tmp_riga),
    '1) fixture: una distinta MANUALE in BOZZA con una riga ABBINATA');

-- ============================================================
-- 2. L'ordine: la matrice prima della chiusura
-- ============================================================
SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
        (SELECT d_chiusa FROM tmp_refs), (SELECT id FROM tmp_distinta))),
    'E_CONTABILE_TRANSIZIONE_NON_AMMESSA',
    '2) BOZZA -> CHIUSA con una riga pronta: parla la matrice, non la chiusura');

-- ============================================================
-- 3-6. La regola della chiusura
-- ============================================================
SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
        (SELECT d_validata FROM tmp_refs), (SELECT id FROM tmp_distinta))),
    'NESSUN_RIFIUTO',
    '3) BOZZA -> VALIDATA passa: la riga e'' lavorata');

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
        (SELECT d_chiusa FROM tmp_refs), (SELECT id FROM tmp_distinta))),
    'E_CONTABILE_CHIUSURA_CON_RIGHE_PRONTE',
    '4) VALIDATA -> CHIUSA con una riga pronta da registrare: rifiutata');

SELECT is(
    (SELECT c.stato_id FROM pagamenti.vendite_contabili c WHERE c.id = (SELECT id FROM tmp_distinta)),
    (SELECT d_validata FROM tmp_refs),
    '5) ...e la distinta e'' rimasta VALIDATA');

-- La riga si sospende (una decisione: sotto una validata e' ammessa) e non
-- e' piu' pronta.
UPDATE pagamenti.vendite_contabili_righe
   SET stato_id = (SELECT st_sospesa FROM tmp_refs), motivo_sospeso = 'da verificare'
 WHERE id = (SELECT id FROM tmp_riga);

SELECT is(
    pg_temp.codice_rifiuto(format(
        $q$UPDATE pagamenti.vendite_contabili SET stato_id = %s WHERE id = %s$q$,
        (SELECT d_chiusa FROM tmp_refs), (SELECT id FROM tmp_distinta))),
    'NESSUN_RIFIUTO',
    '6) con la riga sospesa, cioe'' non pronta, la chiusura passa');

-- ============================================================
-- 7. L'ordine dei guard di stato, scritto nei nomi
-- ============================================================
SELECT is(
    (SELECT array_agg(t.tgname::text ORDER BY t.tgname)
       FROM pg_trigger t
      WHERE t.tgrelid = 'pagamenti.vendite_contabili'::regclass
        AND NOT t.tgisinternal
        AND t.tgname IN ('trg_vendite_contabili_a10_guard_transizione_upd',
                         'trg_vendite_contabili_a10_guard_validazione_upd',
                         'trg_vendite_contabili_a10_guard_verifica_chiusura_upd',
                         'trg_vendite_contabili_a10_guard_chiusura_upd')),
    ARRAY['trg_vendite_contabili_a10_guard_transizione_upd',
          'trg_vendite_contabili_a10_guard_validazione_upd',
          'trg_vendite_contabili_a10_guard_verifica_chiusura_upd']::text[],
    '7) i guard di stato scattano nell''ordine dei nomi: transizione, validazione, verifica_chiusura');

-- ============================================================
-- Cleanup
-- ============================================================
SELECT ok(true, '8) Cleanup: la transazione viene annullata, nessun residuo');

SELECT * FROM finish();
ROLLBACK;
