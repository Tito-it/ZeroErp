-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_ricalcola_riepilogo_iva_fattura / vendite.fn_ricalcola_riepiloghi_iva_lotto
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Inserimento registro di test
-- 3) Inserimento fattura di test
-- 4) Inserimento righe fattura di test
-- 5) Ricalcolo IVA fattura (inserted_rows=1)
-- 6) Imposta ricalcolata da imponibile * aliquota_iva
-- 7) Override iva_stati applicato
-- 8) Ricalcolo IVA fattura idempotente (deleted_rows=1)
-- 9) Inserimento lotto + collegamento fattura
-- 10) Ricalcolo IVA lotto (fatture_count=1)
-- 11) Totali testata aggiornati
-- 12) Cleanup completato
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

SELECT plan(12);
-- ============================================================
-- 0) Riferimenti
-- ============================================================
CREATE TEMP TABLE tmp_costanti_iva AS
SELECT 'pgtap_ricalcola_iva'::text AS test_scope;
-- ⚠️ 2026-07-28: emittente e billing account NON si scelgono piu' in modo
--   indipendente. `fn_ricalcola_totali_fattura` richiede la configurazione
--   (emittente, utility) su anagrafiche.emittenti_fiscali_utilities per leggere
--   decimali e metodo di arrotondamento del totale, e solleva E_CONFIG_MANCANTE
--   se non la trova. Prendendo «l'emittente piu' recente» e «il BA piu' recente»
--   la coppia risultante non era configurata, e il test si fermava a meta'.
--   Ora si parte DALLA configurazione e si sceglie un BA con quella utility.
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA dell'azienda di chi agisce) e
--   l'emittente e' quello dell'operatore di contesto. Prima la coppia
--   (emittente, utility) si pescava da emittenti_fiscali_utilities e il BA era
--   l'ultimo inserito con quella utility: da zero non c'era niente. Senza la
--   riga (emittente, utility) il ricalcolo usa i parametri di sistema
--   dell'utility (rev 20261021-17). Registro, fattura e lotto restano scritti
--   a mano: sono i test 2, 3 e 9.
CREATE TEMP TABLE tmp_cli_iva AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('ricalcola riepiloghi iva');

CREATE TEMP TABLE tmp_refs_iva AS
SELECT
  script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
  (SELECT billing_account_id FROM tmp_cli_iva) AS billing_account_id,
  (
    SELECT id
    FROM config.iva
    WHERE attivo IS TRUE
    ORDER BY id
    LIMIT 1
  ) AS iva_id,
  (
    SELECT id
    FROM config.tipi_doc_fiscale
    WHERE attivo IS TRUE
    ORDER BY id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT id
    FROM config.stati_doc_fiscale
    WHERE codice_interno IN ('DRAFT')
    ORDER BY id
    LIMIT 1
  ) AS stato_doc_fiscale_id,
  -- 3b.3: l'utility va portata IN TESTATA. Il ricalcolo non la deduce piu'
  -- da lotto/BA, la legge da vendite.fatture.utility_id: e' quella del
  -- cliente costruito.
  (SELECT utility_id FROM tmp_cli_iva) AS utility_id;
SELECT ok(
    (
      SELECT emittente_soggetto_ruolo_id IS NOT NULL
        AND billing_account_id IS NOT NULL
        AND iva_id IS NOT NULL
        AND tipo_doc_fiscale_id IS NOT NULL
        AND stato_doc_fiscale_id IS NOT NULL
      FROM tmp_refs_iva
    ),
    'Riferimenti minimi presenti'
  );
-- ============================================================
-- 1) Registro di test
-- ============================================================
CREATE TEMP TABLE tmp_reg_iva AS WITH ins AS (
  -- ⛔ emittente_soggetto_ruolo_id e' NOT NULL dal 2026-08-30 (C1-2,
  --   20260830-11), e dev'essere lo STESSO delle fatture di questo file:
  --   vendite.trgfn_fatture_guard_registro_emittente rifiuta un documento
  --   sul registro di un altro emittente (C1-3, 20260830-10).
  INSERT INTO vendite.registri_fatturazione (
      codice,
      descrizione,
      reset_policy,
      attivo,
      emittente_soggetto_ruolo_id,
      meta
    )
  SELECT left(
      'REGIVA_' || (
        SELECT test_scope
        FROM tmp_costanti_iva
      ),
      16
    ),
    'Registro test IVA',
    'ANNUALE',
    true,
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_iva),
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_iva
      )
    )
  RETURNING id
)
SELECT *
FROM ins;
SELECT ok(
    (
      SELECT id IS NOT NULL
      FROM tmp_reg_iva
    ),
    'Inserimento registro di test'
  );
-- ============================================================
-- 2) Fattura di test
-- ============================================================
CREATE TEMP TABLE tmp_fattura_iva AS WITH ins AS (
  -- ⚠️ 2026-07-28: aggiunta `valuta_id`, richiesta da
  --   fn_ricalcola_totali_fattura (p_valuta_id obbligatorio) per risolvere lo
  --   scope di arrotondamento. Senza, il test si fermava prima degli ultimi casi.
  INSERT INTO vendite.fatture (
      registro_id,
      data,
      emittente_soggetto_ruolo_id,
      billing_account_id,
      tipo_doc_fiscale_id,
      stato_doc_fiscale_id,
      valuta_id,
      utility_id,
      meta
    )
  SELECT (
      SELECT id
      FROM tmp_reg_iva
    ),
    script.fn_data_operativa(),
    (
      SELECT emittente_soggetto_ruolo_id
      FROM tmp_refs_iva
    ),
    (
      SELECT billing_account_id
      FROM tmp_refs_iva
    ),
    (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_iva
    ),
    (
      SELECT stato_doc_fiscale_id
      FROM tmp_refs_iva
    ),
    (
      SELECT id FROM config.valute ORDER BY id LIMIT 1
    ),
    (
      SELECT utility_id
      FROM tmp_refs_iva
    ),
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_iva
      )
    )
  RETURNING id
)
SELECT *
FROM ins;
SELECT ok(
    (
      SELECT id IS NOT NULL
      FROM tmp_fattura_iva
    ),
    'Inserimento fattura di test'
  );
-- ============================================================
-- 3) Righe fattura di test
-- ============================================================
INSERT INTO vendite.fatture_righe (
    fattura_id,
    riga_nr,
    descrizione,
    qta,
    prezzo_unitario,
    iva_id,
    meta, competenza_dal, competenza_al
  )
SELECT (
    SELECT id
    FROM tmp_fattura_iva
  ),
  v.riga_nr,
  v.descrizione,
  v.qta,
  v.prezzo_unitario,
  (
    SELECT iva_id
    FROM tmp_refs_iva
  ),
  jsonb_build_object(
    'test_scope',
    (
      SELECT test_scope
      FROM tmp_costanti_iva
    )
  ), script.fn_data_operativa(), script.fn_data_operativa()
FROM (
    -- ⚠️ 2026-07-28: la fixture NON fornisce piu' gli importi di riga.
    --   `imponibile_riga` e' calcolato dal trigger a20 (qta * prezzo * (1-sconto/100),
    --   arrotondato secondo le regole dell'articolo), e `imposta_riga`/`totale_riga`
    --   non esistono piu' sul modello: l'imposta di riga non esiste nel regime
    --   italiano, l'IVA si liquida per aliquota nei riepiloghi.
    --   Gli attesi NON cambiano: 1x100 -> 100 e 1x50 -> 50 sono esattamente cio'
    --   che il trigger produce. Prima la fixture forniva alla catena il dato che
    --   il percorso di produzione non generava mai — ed e' il motivo per cui il
    --   difetto e' sopravvissuto a una suite verde.
    --   brief-fix-importi-riga-fattura-zero §8.1.
    VALUES (
        1,
        'Riga IVA 1',
        1::numeric,
        100::numeric
      ),
      (
        2,
        'Riga IVA 2',
        1::numeric,
        50::numeric
      )
  ) AS v(
    riga_nr,
    descrizione,
    qta,
    prezzo_unitario
  );
SELECT ok(true, 'Inserimento righe fattura di test');
-- ============================================================
-- 4) Ricalcolo IVA su fattura (prima volta)
-- ============================================================
SELECT is(
    (
      SELECT inserted_rows
      FROM vendite.fn_ricalcola_riepilogo_iva_fattura(
          (
            SELECT id
            FROM tmp_fattura_iva
          )
        )
    ),
    1::int,
    'Ricalcolo IVA fattura (inserted_rows=1)'
  );
SELECT is(
    (
      SELECT imposta
      FROM vendite.fatture_riepiloghi_iva
      WHERE fattura_id = (
          SELECT id
          FROM tmp_fattura_iva
        )
    ),
    (
      SELECT ROUND(
          ROUND(SUM(COALESCE(r.imponibile_riga, 0)), 2) * (
            COALESCE(MAX(i.aliquota_iva), 0)::numeric / 100::numeric
          ),
          2
        )
      FROM vendite.fatture_righe r
        LEFT JOIN config.iva i ON i.id = r.iva_id
      WHERE r.fattura_id = (
          SELECT id
          FROM tmp_fattura_iva
        )
    ),
    'Imposta ricalcolata da imponibile * aliquota_iva'
  );
-- ============================================================
-- 6) Override iva_stati
-- ============================================================
INSERT INTO config.iva_stati (
    iva_id,
    stato_id,
    aliquota_override,
    assoggettamento_id_override
  )
SELECT (
    SELECT iva_id
    FROM tmp_refs_iva
  ),
  s.stato_id,
  5::numeric,
  null
  /*
   (
   SELECT assoggettamento_id
   FROM config.iva
   WHERE id = (
   SELECT iva_id
   FROM tmp_refs_iva
   )
   )*/
FROM vendite.fatture f
  JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.emittente_soggetto_ruolo_id
  JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
WHERE f.id = (
    SELECT id
    FROM tmp_fattura_iva
  );
SELECT *
FROM vendite.fn_ricalcola_riepilogo_iva_fattura(
    (
      SELECT id
      FROM tmp_fattura_iva
    )
  );
SELECT is(
    (
      SELECT imposta
      FROM vendite.fatture_riepiloghi_iva
      WHERE fattura_id = (
          SELECT id
          FROM tmp_fattura_iva
        )
    ),
    (
      SELECT ROUND(
          ROUND(SUM(COALESCE(r.imponibile_riga, 0)), 2) * (5::numeric / 100::numeric),
          2
        )
      FROM vendite.fatture_righe r
      WHERE r.fattura_id = (
          SELECT id
          FROM tmp_fattura_iva
        )
    ),
    'Override iva_stati applicato'
  );
-- ============================================================
-- 5) Ricalcolo IVA su fattura (idempotente)
-- ============================================================
SELECT is(
    (
      SELECT deleted_rows
      FROM vendite.fn_ricalcola_riepilogo_iva_fattura(
          (
            SELECT id
            FROM tmp_fattura_iva
          )
        )
    ),
    1::int,
    'Ricalcolo IVA fattura idempotente (deleted_rows=1)'
  );
-- ============================================================
-- 6) Lotto + collegamento fattura
-- ============================================================
-- ⚠️ 2026-07-28: aggiunto `emittente_soggetto_ruolo_id`, diventato NOT NULL su
--   vendite.fatturazione_lotti dopo la stesura di questo test. Era la ragione per
--   cui il file risultava in `baseline-rossi.tsv` come ERRORE_FIXTURE: si fermava
--   qui e non eseguiva gli ultimi quattro casi. Il riferimento era gia'
--   disponibile in tmp_refs_iva, non serviva altro.
CREATE TEMP TABLE tmp_lotto_iva AS WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
      competenza_mese,
      tipo_doc_fiscale_id,
      emittente_soggetto_ruolo_id,
      meta
    )
  SELECT date_trunc('month', script.fn_data_operativa())::date,
    (
      SELECT tipo_doc_fiscale_id
      FROM tmp_refs_iva
    ),
    (
      SELECT emittente_soggetto_ruolo_id
      FROM tmp_refs_iva
    ),
    jsonb_build_object(
      'test_scope',
      (
        SELECT test_scope
        FROM tmp_costanti_iva
      )
    )
  RETURNING id
)
SELECT *
FROM ins;
INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, meta)
SELECT (
    SELECT id
    FROM tmp_lotto_iva
  ),
  (
    SELECT id
    FROM tmp_fattura_iva
  ),
  jsonb_build_object(
    'test_scope',
    (
      SELECT test_scope
      FROM tmp_costanti_iva
    )
  );
SELECT ok(true, 'Inserimento lotto + collegamento fattura');
-- ============================================================
-- 7) Ricalcolo IVA su lotto
-- ============================================================
SELECT is(
    (
      SELECT fatture_count
      FROM vendite.fn_ricalcola_riepiloghi_iva_lotto(
          (
            SELECT id
            FROM tmp_lotto_iva
          ),
          1000
        )
    ),
    1::int,
    'Ricalcolo IVA lotto (fatture_count=1)'
  );

SELECT ok(
    (
      SELECT imponibile_tot IS NOT NULL
         AND imposta_tot IS NOT NULL
         AND totale_doc IS NOT NULL
      FROM vendite.fatture
      WHERE id = (
          SELECT id
          FROM tmp_fattura_iva
        )
    ),
    'Totali testata aggiornati'
  );
-- ============================================================
-- Cleanup
-- ============================================================
UPDATE vendite.fatture_riepiloghi_iva
SET data_update = now()
WHERE fattura_id = (
    SELECT id
    FROM tmp_fattura_iva
  );
UPDATE vendite.fatture_righe
SET storicizza = false
WHERE fattura_id = (
    SELECT id
    FROM tmp_fattura_iva
  );
UPDATE vendite.fatture
SET storicizza = false
WHERE id = (
    SELECT id
    FROM tmp_fattura_iva
  );
UPDATE vendite.fatturazione_lotti_fatture
SET storicizza = false
WHERE lotto_id = (
    SELECT id
    FROM tmp_lotto_iva
  );
UPDATE vendite.fatturazione_lotti
SET storicizza = false
WHERE id = (
    SELECT id
    FROM tmp_lotto_iva
  );
UPDATE vendite.registri_fatturazione
SET storicizza = false
WHERE id = (
    SELECT id
    FROM tmp_reg_iva
  );
DELETE FROM vendite.fatture_riepiloghi_iva
WHERE fattura_id = (
    SELECT id
    FROM tmp_fattura_iva
  );
DELETE FROM vendite.fatture_righe
WHERE fattura_id = (
    SELECT id
    FROM tmp_fattura_iva
  );
DELETE FROM vendite.fatturazione_lotti_fatture
WHERE lotto_id = (
    SELECT id
    FROM tmp_lotto_iva
  );
DELETE FROM vendite.fatturazione_lotti
WHERE id = (
    SELECT id
    FROM tmp_lotto_iva
  );
DELETE FROM vendite.fatture
WHERE id = (
    SELECT id
    FROM tmp_fattura_iva
  );
DELETE FROM vendite.registri_fatturazione_progressivi
WHERE registro_id = (
    SELECT id
    FROM tmp_reg_iva
  );
DELETE FROM vendite.registri_fatturazione
WHERE id = (
    SELECT id
    FROM tmp_reg_iva
  );
DELETE FROM config.iva_stati
WHERE iva_id = (
    SELECT iva_id
    FROM tmp_refs_iva
  )
  AND stato_id IN (
    SELECT s.stato_id
    FROM vendite.fatture f
      JOIN anagrafiche.soggetti_ruoli sr ON sr.id = f.emittente_soggetto_ruolo_id
      JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
    WHERE f.id = (
        SELECT id
        FROM tmp_fattura_iva
      )
  );
SELECT ok(true, 'Cleanup completato');
SELECT *
FROM finish();
ROLLBACK;
