-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Verifica guard DEFERRABLE: indirizzi obbligatori per soggetti_ruoli
-- (config.tipi_ruolo_tipi_indirizzo).
-- Catalogo assert (6/6)
--  1) Esiste almeno uno stato in config.stati
--  2) Esiste almeno un tipo_contatto in config.tipi_contatti
--  3) Esiste almeno una regola obbligatoria attiva in config.tipi_ruolo_tipi_indirizzo
--  4) Inserimento soggetti_ruoli senza indirizzo obbligatorio: consentito prima del check deferred
--  5) Guard deferred su soggetti_ruoli: blocco a SET CONSTRAINTS ALL IMMEDIATE se manca indirizzo obbligatorio
--  6) Guard deferred su soggetti_ruoli: passa con indirizzo obbligatorio presente
--
-- ------------------------------------------------------------
-- Cleanup iniziale (solo per test precedenti non rollbackati)
DO $$ BEGIN
DELETE FROM anagrafiche.indirizzi i
WHERE i.soggetto_ruolo_id IN (
    SELECT sr.id
    FROM anagrafiche.soggetti_ruoli sr
      JOIN anagrafiche.soggetti s ON s.id = sr.soggetto_id
    WHERE s.codice IN ('TST-RUOLO-IND-ERR', 'TST-RUOLO-IND-OK')
  );
DELETE FROM anagrafiche.soggetti_ruoli sr USING anagrafiche.soggetti s
WHERE sr.soggetto_id = s.id
  AND s.codice IN ('TST-RUOLO-IND-ERR', 'TST-RUOLO-IND-OK');
DELETE FROM anagrafiche.contatti c
WHERE c.soggetto_id IN (
    SELECT s.id
    FROM anagrafiche.soggetti s
    WHERE s.codice IN ('TST-RUOLO-IND-ERR', 'TST-RUOLO-IND-OK')
  );
DELETE FROM anagrafiche.soggetti s
WHERE s.codice IN ('TST-RUOLO-IND-ERR', 'TST-RUOLO-IND-OK');
END;
$$;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⛔ 2026-09-23: LA RIGA DI CONTESTO NON STA PIU' IN AUTOCOMMIT, sta dentro
--   OGNI caso. Questo file e' multi-transazione per disegno (ogni caso e' un
--   BEGIN … ROLLBACK a se', perche' collauda guard DEFERRABLE), e la riga
--   fuori da una transazione, su un database ricostruito, COSTRUIVA e
--   COMMITTAVA azienda + operatore: un residuo per corsa e una maschera per
--   tutti i file che vengono dopo. Dentro il caso, il mondo si costruisce e il
--   ROLLBACK se lo porta via.
--   ⚠️ `tmp_run_sfx` invece resta fuori, ed e' giusto: e' una TEMP TABLE, non
--   tocca il database condiviso, e dentro un caso il ROLLBACK la cancellerebbe.

SELECT plan(6);
-- =========================================================
-- Precondizioni base
-- =========================================================
CREATE TEMP TABLE tmp_stato_test AS
SELECT id AS stato_id
FROM config.stati
ORDER BY id
LIMIT 1;
SELECT ok(
    (
      SELECT count(*)
      FROM tmp_stato_test
    ) = 1,
    'Esiste almeno uno stato in config.stati'
  );
CREATE TEMP TABLE tmp_tipo_contatto_test AS
SELECT id AS tipo_contatto_id
FROM config.tipi_contatti
ORDER BY id
LIMIT 1;
SELECT ok(
    (
      SELECT count(*)
      FROM tmp_tipo_contatto_test
    ) = 1,
    'Esiste almeno un tipo_contatto in config.tipi_contatti'
  );
CREATE TEMP TABLE tmp_regola_ruolo_required AS
SELECT m.tipo_ruolo_id,
  m.tipo_indirizzo_id
FROM config.tipi_ruolo_tipi_indirizzo m
WHERE m.obbligatorio = TRUE
  AND m.attivo = TRUE
  AND (
    m.valido_dal IS NULL
    OR m.valido_dal <= script.fn_data_operativa()
  )
  AND (
    m.valido_al IS NULL
    OR m.valido_al >= script.fn_data_operativa()
  )
ORDER BY m.tipo_ruolo_id,
  m.tipo_indirizzo_id
LIMIT 1;
SELECT ok(
    (
      SELECT count(*)
      FROM tmp_regola_ruolo_required
    ) = 1,
    'Esiste almeno una regola obbligatoria attiva in config.tipi_ruolo_tipi_indirizzo'
  );
CREATE TEMP TABLE tmp_stradario_test AS
SELECT id
FROM config.stradario
ORDER BY id
LIMIT 1;
CREATE TEMP TABLE tmp_indirizzo_dettaglio_test AS WITH upsert AS (
  INSERT INTO anagrafiche.indirizzi_dettaglio (
      stradario_id,
      civico,
      via_norm,
      civico_norm,
      attivo,
      storicizza
    )
  SELECT s.id,
    1,
    'VIA TEST RUOLO REQUIRED',
    '1',
    TRUE,
    FALSE
  FROM tmp_stradario_test s ON CONFLICT (stradario_id, civico, estensione_civico, palazzina, scala, piano, interno) DO
  UPDATE
  SET data_update = now(),
    user_update = CURRENT_USER
  RETURNING id
)
SELECT id
FROM upsert;
-- =========================================================
-- Caso 1: ruolo senza indirizzo obbligatorio -> blocco deferred
-- =========================================================
BEGIN;

-- Contesto applicativo, dentro il caso (vedi la nota in testa).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ E LA FINESTRA DIFFERITA SI RIAPRE, DICHIARANDOLO. La riga di contesto,
--   quando COSTRUISCE il mondo (database ricostruito), esce con i vincoli
--   IMMEDIATE come ogni helper: questo caso invece si regge sulla finestra
--   differita — inserisce l'incompleto e forza IMMEDIATE dentro throws_ok.
--   Contare sulla finestra «di default» e' verde su dev e rosso in CI.
SET CONSTRAINTS ALL DEFERRED;
WITH ins AS (
  INSERT INTO anagrafiche.soggetti (
      codice,
      cognome,
      nome,
      sesso,   -- un privato: obbligatorio (sesso_policy REQUIRED)
      stato_id,
      tipo_soggetto_dettaglio_id,
      codice_fiscale,
      storicizza,
      attivo
    )
  SELECT 'TST-RUOLO-IND-ERR',
    'Test',
    'Ruolo ERR',
    'M',
    (
      SELECT stato_id
      FROM tmp_stato_test
    ),
    -- Rev 2026-10-09: la natura per NOME (era «il primo id», cioe' PR per
    --   caso): dal sesso in poi la natura decide cosa la riga deve portare.
    --   brief-db-sesso-senza-default.
    (
      SELECT id
      FROM config.tipi_soggetto_dettaglio
      WHERE codice_interno = 'PR'
    ),
    'QMMTPK69T01G127B',
    TRUE,
    TRUE
  RETURNING id
)
SELECT * INTO TEMP TABLE tmp_soggetto_ruolo_err
FROM ins;
INSERT INTO anagrafiche.contatti (
    tipo_contatto_id,
    soggetto_id,
    nominativo,
    email,
    is_default
  )
SELECT (
    SELECT tipo_contatto_id
    FROM tmp_tipo_contatto_test
  ),
  s.id,
  'Contatto ruolo ERR',
  'ruolo.err@example.com',
  TRUE
FROM tmp_soggetto_ruolo_err s;

-- Soddisfa i requisiti indirizzo del soggetto, per isolare il guard del ruolo
INSERT INTO anagrafiche.indirizzi_soggetti (
    soggetto_id,
    tipo_indirizzo_id,
    indirizzo_dettaglio_id,
    storicizza
  )
SELECT s.id,
  m.tipo_indirizzo_id,
  d.id,
  FALSE
FROM tmp_soggetto_ruolo_err s
  JOIN anagrafiche.soggetti sg ON sg.id = s.id
  JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo m ON m.tipo_soggetto_dettaglio_id = sg.tipo_soggetto_dettaglio_id
  JOIN tmp_indirizzo_dettaglio_test d ON TRUE
WHERE m.obbligatorio = TRUE
  AND m.attivo = TRUE
  AND (m.valido_dal IS NULL OR m.valido_dal <= script.fn_data_operativa())
  AND (m.valido_al IS NULL OR m.valido_al >= script.fn_data_operativa());

SELECT lives_ok(
    $$
    INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
    SELECT s.id,
      r.tipo_ruolo_id
    FROM tmp_soggetto_ruolo_err s
      JOIN tmp_regola_ruolo_required r ON TRUE;
$$,
'Insert soggetti_ruoli senza indirizzo: passa prima del check deferred'
);
SELECT throws_ok(
    $$
    SET CONSTRAINTS ALL IMMEDIATE;
$$,
NULL,
NULL,
'Senza indirizzo obbligatorio, il guard su soggetti_ruoli blocca a SET CONSTRAINTS'
);
ROLLBACK;
-- =========================================================
-- Caso 2: ruolo con indirizzo obbligatorio -> ok
-- =========================================================
BEGIN;

-- Contesto applicativo, dentro il caso (vedi la nota in testa).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ E LA FINESTRA DIFFERITA SI RIAPRE, DICHIARANDOLO. La riga di contesto,
--   quando COSTRUISCE il mondo (database ricostruito), esce con i vincoli
--   IMMEDIATE come ogni helper: questo caso invece si regge sulla finestra
--   differita — inserisce l'incompleto e forza IMMEDIATE dentro throws_ok.
--   Contare sulla finestra «di default» e' verde su dev e rosso in CI.
SET CONSTRAINTS ALL DEFERRED;
WITH ins AS (
  INSERT INTO anagrafiche.soggetti (
      codice,
      cognome,
      nome,
      sesso,   -- un privato: obbligatorio (sesso_policy REQUIRED)
      stato_id,
      tipo_soggetto_dettaglio_id,
      codice_fiscale,
      storicizza,
      attivo
    )
  SELECT 'TST-RUOLO-IND-OK',
    'Test',
    'Ruolo OK',
    'M',
    (
      SELECT stato_id
      FROM tmp_stato_test
    ),
    -- Rev 2026-10-09: la natura per NOME (era «il primo id», cioe' PR per
    --   caso): dal sesso in poi la natura decide cosa la riga deve portare.
    --   brief-db-sesso-senza-default.
    (
      SELECT id
      FROM config.tipi_soggetto_dettaglio
      WHERE codice_interno = 'PR'
    ),
    'QMMTPK69T01G127B',
    TRUE,
    TRUE
  RETURNING id
)
SELECT * INTO TEMP TABLE tmp_soggetto_ruolo_ok
FROM ins;
INSERT INTO anagrafiche.contatti (
    tipo_contatto_id,
    soggetto_id,
    nominativo,
    email,
    is_default
  )
SELECT (
    SELECT tipo_contatto_id
    FROM tmp_tipo_contatto_test
  ),
  s.id,
  'Contatto ruolo OK',
  'ruolo.ok@example.com',
  TRUE
FROM tmp_soggetto_ruolo_ok s;

-- Soddisfa i requisiti indirizzo del soggetto, per isolare il guard del ruolo
INSERT INTO anagrafiche.indirizzi_soggetti (
    soggetto_id,
    tipo_indirizzo_id,
    indirizzo_dettaglio_id,
    storicizza
  )
SELECT s.id,
  m.tipo_indirizzo_id,
  d.id,
  FALSE
FROM tmp_soggetto_ruolo_ok s
  JOIN anagrafiche.soggetti sg ON sg.id = s.id
  JOIN config.tipi_soggetto_dettaglio_tipi_indirizzo m ON m.tipo_soggetto_dettaglio_id = sg.tipo_soggetto_dettaglio_id
  JOIN tmp_indirizzo_dettaglio_test d ON TRUE
WHERE m.obbligatorio = TRUE
  AND m.attivo = TRUE
  AND (m.valido_dal IS NULL OR m.valido_dal <= script.fn_data_operativa())
  AND (m.valido_al IS NULL OR m.valido_al >= script.fn_data_operativa());

WITH ins_role AS (
  INSERT INTO anagrafiche.soggetti_ruoli (soggetto_id, tipo_ruolo_id)
  SELECT s.id,
    r.tipo_ruolo_id
  FROM tmp_soggetto_ruolo_ok s
    JOIN tmp_regola_ruolo_required r ON TRUE
  RETURNING id
)
SELECT * INTO TEMP TABLE tmp_ruolo_ok
FROM ins_role;
INSERT INTO anagrafiche.indirizzi (
    soggetto_ruolo_id,
    tipo_indirizzo_id,
    indirizzo_dettaglio_id,
    storicizza
  )
SELECT r.id,
  rr.tipo_indirizzo_id,
  d.id,
  FALSE
FROM tmp_ruolo_ok r
  JOIN tmp_regola_ruolo_required rr ON TRUE
  JOIN tmp_indirizzo_dettaglio_test d ON TRUE;
SELECT lives_ok(
    $$
    SET CONSTRAINTS ALL IMMEDIATE;
$$,
'Con indirizzo obbligatorio presente, il guard su soggetti_ruoli passa'
);
ROLLBACK;
SELECT *
FROM finish();
