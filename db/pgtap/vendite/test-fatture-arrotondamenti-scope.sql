-- ============================================================
-- Test: vendite.fatture_arrotondamenti_scope + fn_get/fn_set
-- Indice test:
-- 1) Setup: riferimenti base (BA, utility, tipo doc, emittente, valuta)
-- 2) Get su scope assente -> 0
-- 3) Set saldo -> ritorno saldo
-- 4) Get saldo -> valore aggiornato
-- 5) Update saldo (upsert)
-- 6) Guard parametri numerici (NULL o <=0)
-- ============================================================
SELECT plan(6);
-- ============================================================
-- 1) Setup riferimenti base
-- ============================================================
CREATE TEMP TABLE tmp_refs_arrotondamenti AS
SELECT ba.id AS billing_account_id,
  u.id AS utility_id,
  tdf.id AS tipo_doc_fiscale_id,
  sr.id AS emittente_soggetto_ruolo_id,
  v.id AS valuta_id
FROM anagrafiche.billing_account ba
  JOIN config.utilities u ON u.id = ba.utility_id
  JOIN config.tipi_doc_fiscale tdf ON tdf.id = 1 -- Assumendo che il valore di default sia 1
  JOIN anagrafiche.emittenti_fiscali ef ON ef.id = 32
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
  JOIN config.valute v ON v.id = 1 -- Assumendo che il valore di default sia 1
ORDER BY ba.id,
  u.id,
  tdf.id,
  sr.id,
  v.id
LIMIT 1;
SELECT ok(
    (
      SELECT count(*) = 1
      FROM tmp_refs_arrotondamenti
    ),
    'Setup riferimenti base'
  );
-- ============================================================
-- 2) Get su scope assente -> 0
-- ============================================================
SELECT is(
    vendite.fn_get_arrotondamento_scope(
      (
        SELECT billing_account_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT utility_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT valuta_id
        FROM tmp_refs_arrotondamenti
      )
    ),
    0::numeric,
    'Get saldo scope assente = 0'
  );
-- ============================================================
-- 3) Set saldo -> ritorno saldo
-- ============================================================
SELECT is(
    vendite.fn_set_arrotondamento_scope(
      (
        SELECT billing_account_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT utility_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT valuta_id
        FROM tmp_refs_arrotondamenti
      ),
      0.03::numeric
    ),
    0.03::numeric,
    'Set saldo scope = 0.03'
  );
-- ============================================================
-- 4) Get saldo -> valore aggiornato
-- ============================================================
SELECT is(
    vendite.fn_get_arrotondamento_scope(
      (
        SELECT billing_account_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT utility_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT valuta_id
        FROM tmp_refs_arrotondamenti
      )
    ),
    0.03::numeric,
    'Get saldo scope = 0.03'
  );
-- ============================================================
-- 5) Update saldo (upsert)
-- ============================================================
SELECT is(
    vendite.fn_set_arrotondamento_scope(
      (
        SELECT billing_account_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT utility_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT tipo_doc_fiscale_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT emittente_soggetto_ruolo_id
        FROM tmp_refs_arrotondamenti
      ),
      (
        SELECT valuta_id
        FROM tmp_refs_arrotondamenti
      ),
      -0.02::numeric
    ),
    -0.02::numeric,
    'Update saldo scope = -0.02'
  );
-- ============================================================
-- 6) Guard parametri numerici (NULL o <=0)
-- ============================================================
SELECT throws_ok(
    $sql$
    SELECT vendite.fn_get_arrotondamento_scope(NULL, 1, 1, 1, 1);
$sql$,
'P0001',
NULL,
'Guard: billing_account_id NULL'
);
-- Cleanup (non necessario: upsert su scope viene mantenuto)
SELECT *
FROM finish();