-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: generazione cross-pratica
--       Completamento flusso con regola auto=true → nuova pratica generata
--       Regola auto=false → nessuna generazione automatica
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) Setup: 2 tipi_prestazione (sorgente, destinazione), template, pratica
-- 2) Setup regola generazione con auto=true
-- 3) INSERT flusso su pratica sorgente
-- 4) UPDATE flusso → COMPLETATO: pratica target generata
-- 5) Verifica pratica generata: flusso_origine_id corretto
-- 6) Verifica pratica generata: emittente, soggetto, priorita ereditati
-- 7) Regola auto=false: nessuna generazione automatica
-- 8) Cleanup
-- ------------------------------------------------------------
SELECT plan(6);
-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA', 'BOZZA', 'Bozza', true) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES (
    'DA_ESEGUIRE',
    'DA_ESEGUIRE',
    'Da eseguire',
    true
  ),
  (
    'COMPLETATO',
    'COMPLETATO',
    'Completato',
    true
  ) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (
    codice,
    codice_interno,
    descrizione,
    sequenza,
    attivo
  )
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true) ON CONFLICT (codice_interno) DO NOTHING;
CREATE TEMP TABLE tmp_gen_refs AS
SELECT (
    SELECT id
    FROM anagrafiche.emittenti_fiscali
    WHERE attivo = true
    LIMIT 1
  ) AS emittente_id,
  (
    SELECT id
    FROM anagrafiche.soggetti
    LIMIT 1
  ) AS soggetto_id,
  (
    SELECT id
    FROM config.stati_pratiche
    WHERE codice_interno = 'BOZZA'
      AND attivo = true
    LIMIT 1
  ) AS stato_bozza_id,
  (
    SELECT id
    FROM config.stati_flussi_pratiche
    WHERE codice_interno = 'DA_ESEGUIRE'
      AND attivo = true
    LIMIT 1
  ) AS stato_da_eseguire_id,
  (
    SELECT id
    FROM config.stati_flussi_pratiche
    WHERE codice_interno = 'COMPLETATO'
      AND attivo = true
    LIMIT 1
  ) AS stato_completato_id,
  (
    SELECT id
    FROM config.priorita_pratiche
    WHERE codice_interno = 'NORMALE'
      AND attivo = true
    LIMIT 1
  ) AS priorita_normale_id;
SELECT ok(
    (
      SELECT emittente_id IS NOT NULL
        AND soggetto_id IS NOT NULL
        AND stato_bozza_id IS NOT NULL
        AND stato_da_eseguire_id IS NOT NULL
        AND stato_completato_id IS NOT NULL
        AND priorita_normale_id IS NOT NULL
      FROM tmp_gen_refs
    ),
    '0. Precondizioni soddisfatte'
  );
-- =========================================================
-- 1) Setup: 2 tipi_prestazione, template, pratica sorgente
-- =========================================================
CREATE TEMP TABLE tmp_gen_tp_src AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES (
      'TEST_GEN_SRC',
      'TEST_GEN_SRC',
      'Tipo sorgente test generazione',
      true
    ) ON CONFLICT (codice_interno) DO
  UPDATE
  SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id
FROM ins;
CREATE TEMP TABLE tmp_gen_tp_dest AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES (
      'TEST_GEN_DEST',
      'TEST_GEN_DEST',
      'Tipo destinazione test generazione',
      true
    ) ON CONFLICT (codice_interno) DO
  UPDATE
  SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id
FROM ins;
CREATE TEMP TABLE tmp_gen_tf AS WITH ins AS (
  INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, attivo)
  VALUES (
      (
        SELECT tp_id
        FROM tmp_gen_tp_src
      ),
      'TF_GEN_SRC',
      'Template sorgente generazione',
      true
    ) ON CONFLICT (tipo_prestazione_id, codice) DO
  UPDATE
  SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tf_id
FROM ins;
CREATE TEMP TABLE tmp_gen_pratica AS WITH ins AS (
  INSERT INTO pratiche.pratiche (
      emittente_fiscale_id,
      tipo_prestazione_id,
      soggetto_id,
      stato_id,
      priorita_id
    )
  VALUES (
      (
        SELECT emittente_id
        FROM tmp_gen_refs
      ),
      (
        SELECT tp_id
        FROM tmp_gen_tp_src
      ),
      (
        SELECT soggetto_id
        FROM tmp_gen_refs
      ),
      (
        SELECT stato_bozza_id
        FROM tmp_gen_refs
      ),
      (
        SELECT priorita_normale_id
        FROM tmp_gen_refs
      )
    )
  RETURNING id
)
SELECT id AS pratica_id
FROM ins;
SELECT ok(
    (
      SELECT pratica_id IS NOT NULL
      FROM tmp_gen_pratica
    ),
    '1. Setup completato: pratica sorgente creata'
  );
-- =========================================================
-- 2) Setup regola generazione con auto=true
-- =========================================================
CREATE TEMP TABLE tmp_gen_regola AS WITH ins AS (
  INSERT INTO pratiche.regole_generazione (
      template_flusso_origine_id,
      tipo_prestazione_dest_id,
      auto,
      attivo,
      descrizione
    )
  VALUES (
      (
        SELECT tf_id
        FROM tmp_gen_tf
      ),
      (
        SELECT tp_id
        FROM tmp_gen_tp_dest
      ),
      true,
      true,
      'Regola test generazione auto'
    )
  RETURNING id
)
SELECT id AS regola_id
FROM ins;
-- =========================================================
-- 3) INSERT flusso su pratica sorgente
-- =========================================================
CREATE TEMP TABLE tmp_gen_flusso AS WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES (
      (
        SELECT pratica_id
        FROM tmp_gen_pratica
      ),
      (
        SELECT tf_id
        FROM tmp_gen_tf
      ),
      (
        SELECT stato_da_eseguire_id
        FROM tmp_gen_refs
      )
    )
  RETURNING id
)
SELECT id AS flusso_id
FROM ins;
-- Conta pratiche prima della generazione
CREATE TEMP TABLE tmp_gen_count_before AS
SELECT count(*) AS cnt
FROM pratiche.pratiche
WHERE tipo_prestazione_id = (
    SELECT tp_id
    FROM tmp_gen_tp_dest
  );
-- =========================================================
-- 4) UPDATE flusso → COMPLETATO: pratica target generata
-- =========================================================
UPDATE pratiche.flussi
SET stato_id = (
    SELECT stato_completato_id
    FROM tmp_gen_refs
  )
WHERE id = (
    SELECT flusso_id
    FROM tmp_gen_flusso
  );
SELECT is(
    (
      SELECT (
          count(*) - (
            SELECT cnt
            FROM tmp_gen_count_before
          )
        )::integer
      FROM pratiche.pratiche
      WHERE tipo_prestazione_id = (
          SELECT tp_id
          FROM tmp_gen_tp_dest
        )
    ),
    1,
    '2. Pratica target generata dopo completamento flusso'
  );
-- =========================================================
-- 5) Verifica pratica generata: flusso_origine_id corretto
-- =========================================================
CREATE TEMP TABLE tmp_gen_pratica_target AS
SELECT id AS pratica_id,
  flusso_origine_id,
  emittente_fiscale_id,
  soggetto_id,
  priorita_id
FROM pratiche.pratiche
WHERE tipo_prestazione_id = (
    SELECT tp_id
    FROM tmp_gen_tp_dest
  )
  AND flusso_origine_id = (
    SELECT flusso_id
    FROM tmp_gen_flusso
  )
LIMIT 1;
SELECT is(
    (
      SELECT flusso_origine_id
      FROM tmp_gen_pratica_target
    ),
    (
      SELECT flusso_id
      FROM tmp_gen_flusso
    ),
    '3. Pratica generata ha flusso_origine_id corretto'
  );
-- =========================================================
-- 6) Verifica pratica generata: emittente, soggetto, priorita ereditati
-- =========================================================
SELECT ok(
    (
      SELECT t.emittente_fiscale_id = (
          SELECT emittente_id
          FROM tmp_gen_refs
        )
        AND t.soggetto_id = (
          SELECT soggetto_id
          FROM tmp_gen_refs
        )
        AND t.priorita_id = (
          SELECT priorita_normale_id
          FROM tmp_gen_refs
        )
      FROM tmp_gen_pratica_target t
    ),
    '4. Pratica generata eredita emittente, soggetto, priorita dalla sorgente'
  );
-- =========================================================
-- 7) Regola auto=false: nessuna generazione automatica
-- =========================================================
CREATE TEMP TABLE tmp_gen_regola_noauto AS WITH ins AS (
  INSERT INTO pratiche.regole_generazione (
      template_flusso_origine_id,
      tipo_prestazione_dest_id,
      auto,
      attivo,
      descrizione,
      esito_richiesto
    )
  VALUES (
      (
        SELECT tf_id
        FROM tmp_gen_tf
      ),
      (
        SELECT tp_id
        FROM tmp_gen_tp_dest
      ),
      false,
      true,
      'Regola test generazione NON auto',
      'POSITIVO'
    )
  RETURNING id
)
SELECT id AS regola_id
FROM ins;
CREATE TEMP TABLE tmp_gen_flusso2 AS WITH ins AS (
  INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
  VALUES (
      (
        SELECT pratica_id
        FROM tmp_gen_pratica
      ),
      (
        SELECT tf_id
        FROM tmp_gen_tf
      ),
      (
        SELECT stato_da_eseguire_id
        FROM tmp_gen_refs
      )
    )
  RETURNING id
)
SELECT id AS flusso_id
FROM ins;
CREATE TEMP TABLE tmp_gen_count_before2 AS
SELECT count(*) AS cnt
FROM pratiche.pratiche
WHERE tipo_prestazione_id = (
    SELECT tp_id
    FROM tmp_gen_tp_dest
  );
UPDATE pratiche.flussi
SET stato_id = (
    SELECT stato_completato_id
    FROM tmp_gen_refs
  )
WHERE id = (
    SELECT flusso_id
    FROM tmp_gen_flusso2
  );
SELECT is(
    (
      SELECT (
          count(*) - (
            SELECT cnt
            FROM tmp_gen_count_before2
          )
        )::integer
      FROM pratiche.pratiche
      WHERE tipo_prestazione_id = (
          SELECT tp_id
          FROM tmp_gen_tp_dest
        )
    ),
    1,
    '5. Regola auto=false non genera pratica (solo auto=true genera)'
  );
-- =========================================================
-- 8) Cleanup
-- =========================================================
-- Cleanup resiliente (gestisce orfani da run precedenti falliti)
-- 1) Pratiche generate (tipo dest) e relativi giornale
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
    SELECT id
    FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (
        SELECT tp_id
        FROM tmp_gen_tp_dest
      )
  );
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (
    SELECT tp_id
    FROM tmp_gen_tp_dest
  );
-- 2) Flussi, giornale e pratiche sorgente
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
    SELECT id
    FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (
        SELECT tp_id
        FROM tmp_gen_tp_src
      )
  );
DELETE FROM pratiche.flussi
WHERE pratica_id IN (
    SELECT id
    FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (
        SELECT tp_id
        FROM tmp_gen_tp_src
      )
  );
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (
    SELECT tp_id
    FROM tmp_gen_tp_src
  );
-- 3) Regole generazione
DELETE FROM pratiche.regole_generazione
WHERE template_flusso_origine_id IN (
    SELECT id
    FROM pratiche.template_flussi
    WHERE tipo_prestazione_id = (
        SELECT tp_id
        FROM tmp_gen_tp_src
      )
  );
-- 4) Template e tipi prestazione
DELETE FROM pratiche.template_flussi
WHERE tipo_prestazione_id = (
    SELECT tp_id
    FROM tmp_gen_tp_src
  );
DELETE FROM pratiche.tipi_prestazione
WHERE id = (
    SELECT tp_id
    FROM tmp_gen_tp_src
  );
DELETE FROM pratiche.tipi_prestazione
WHERE id = (
    SELECT tp_id
    FROM tmp_gen_tp_dest
  );
SELECT *
FROM finish();