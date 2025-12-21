-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Verifica guard DEFERRABLE: indirizzi obbligatori per soggetti
-- (config.tipi_soggetto_dettaglio_tipi_indirizzo).
--
-- Casi:
-- - PR (CF): RES + DOMFISC obbligatori
-- - SC (P.IVA): SEDELEG obbligatorio
-- ------------------------------------------------------------

-- Cleanup iniziale (solo per test precedenti non rollbackati)
DO $$
BEGIN
  DELETE FROM anagrafiche.indirizzi_soggetti i
  WHERE i.soggetto_id IN (
    SELECT s.id
    FROM anagrafiche.soggetti s
    WHERE s.codice IN ('TST-IND-PR-ERR','TST-IND-PR-OK','TST-IND-SC-ERR','TST-IND-SC-OK')
  );

  DELETE FROM anagrafiche.contatti c
  WHERE c.soggetto_id IN (
    SELECT s.id
    FROM anagrafiche.soggetti s
    WHERE s.codice IN ('TST-IND-PR-ERR','TST-IND-PR-OK','TST-IND-SC-ERR','TST-IND-SC-OK')
  );

  DELETE FROM anagrafiche.soggetti s
  WHERE s.codice IN ('TST-IND-PR-ERR','TST-IND-PR-OK','TST-IND-SC-ERR','TST-IND-SC-OK');
END;
$$;

SELECT plan(9);

-- =========================================================
-- Precondizioni base: stato, tipo_contatto, tipi
-- =========================================================
CREATE TEMP TABLE tmp_stato_test AS
SELECT id AS stato_id
FROM config.stati
ORDER BY id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_stato_test) = 1,
    'Esiste almeno uno stato in config.stati'
);

CREATE TEMP TABLE tmp_tipo_contatto_test AS
SELECT id AS tipo_contatto_id
FROM config.tipi_contatti
ORDER BY id
LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM tmp_tipo_contatto_test) = 1,
    'Esiste almeno un tipo_contatto in config.tipi_contatti'
);

CREATE TEMP TABLE tmp_tipi_soggetto_test AS
SELECT id, codice_interno
FROM config.tipi_soggetto_dettaglio
WHERE codice_interno IN ('PR','SC');

SELECT is(
    (SELECT count(*)::int FROM tmp_tipi_soggetto_test),
    2,
    'Trovati tipi_soggetto_dettaglio per PR e SC'
);

CREATE TEMP TABLE tmp_tipi_indirizzo_test AS
SELECT id, codice_interno
FROM config.tipi_indirizzi
WHERE codice_interno IN ('RES','DOMFISC','SEDELEG');

SELECT is(
    (SELECT count(*)::int FROM tmp_tipi_indirizzo_test),
    3,
    'Trovati tipi_indirizzi per RES/DOMFISC/SEDELEG'
);

CREATE TEMP TABLE tmp_tipo_pr AS
SELECT id AS tipo_soggetto_dettaglio_id
FROM tmp_tipi_soggetto_test
WHERE codice_interno = 'PR';

CREATE TEMP TABLE tmp_tipo_sc AS
SELECT id AS tipo_soggetto_dettaglio_id
FROM tmp_tipi_soggetto_test
WHERE codice_interno = 'SC';

CREATE TEMP TABLE tmp_tipo_res AS
SELECT id AS tipo_indirizzo_id
FROM tmp_tipi_indirizzo_test
WHERE codice_interno = 'RES';

CREATE TEMP TABLE tmp_tipo_domfisc AS
SELECT id AS tipo_indirizzo_id
FROM tmp_tipi_indirizzo_test
WHERE codice_interno = 'DOMFISC';

CREATE TEMP TABLE tmp_tipo_sedeleg AS
SELECT id AS tipo_indirizzo_id
FROM tmp_tipi_indirizzo_test
WHERE codice_interno = 'SEDELEG';

-- Provincia (per dati_societari.id_prov_iscri_rea)
CREATE TEMP TABLE tmp_provincia_test AS
SELECT id AS provincia_id
FROM config.province
where trim(sigla) ='MC'
ORDER BY id
LIMIT 1;


-- =========================================================
-- Caso 1: PR senza indirizzi obbligatori -> fallisce
-- =========================================================
BEGIN;

WITH ins AS (
  INSERT INTO anagrafiche.soggetti (
      codice,
      ragione_sociale,
      cognome,
      nome,
      stato_id,
      codice_fiscale,
      partita_iva,
      tipo_soggetto_dettaglio_id,
      storicizza,
      attivo
  )
  SELECT
      'TST-IND-PR-ERR',
      NULL,
      'Test',
      'PR ERR',
      (SELECT stato_id FROM tmp_stato_test),
      'QMMTPK69T01G127B',
      NULL,
      (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_pr),
      TRUE,
      TRUE
  RETURNING id
)
SELECT *
INTO TEMP TABLE tmp_soggetto_pr_err
FROM ins;

INSERT INTO anagrafiche.contatti (
    tipo_contatto_id,
    soggetto_id,
    nominativo,
    email,
    is_default
)
SELECT
    (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test),
    s.id,
    'Contatto PR ERR',
    'pr.err@example.com',
    TRUE
FROM tmp_soggetto_pr_err s;

SELECT throws_ok(
    $$
      SET CONSTRAINTS ALL IMMEDIATE;
    $$,
    NULL,
    NULL,
    'PR senza indirizzi obbligatori: guard blocca'
);

ROLLBACK;

-- =========================================================
-- Caso 2: PR con RES + DOMFISC -> passa
-- =========================================================
BEGIN;

WITH ins AS (
  INSERT INTO anagrafiche.soggetti (
      codice,
      ragione_sociale,
      cognome,
      nome,
      stato_id,
      codice_fiscale,
      partita_iva,
      tipo_soggetto_dettaglio_id,
      storicizza,
      attivo
  )
  SELECT
      'TST-IND-PR-OK',
      NULL,
      'Test',
      'PR OK',
      (SELECT stato_id FROM tmp_stato_test),
      'QMMTPK69T01G127B',
      NULL,
      (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_pr),
      TRUE,
      TRUE
  RETURNING id
)
SELECT *
INTO TEMP TABLE tmp_soggetto_pr_ok
FROM ins;

INSERT INTO anagrafiche.contatti (
    tipo_contatto_id,
    soggetto_id,
    nominativo,
    email,
    is_default
)
SELECT
    (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test),
    s.id,
    'Contatto PR OK',
    'pr.ok@example.com',
    TRUE
FROM tmp_soggetto_pr_ok s;

INSERT INTO anagrafiche.indirizzi_soggetti (
    soggetto_id,
    tipo_indirizzo_id,
    indirizzo_libero
)
SELECT
    s.id,
    t.tipo_indirizzo_id,
    'Via Test PR RES'
FROM tmp_soggetto_pr_ok s
JOIN tmp_tipo_res t ON TRUE;

INSERT INTO anagrafiche.indirizzi_soggetti (
    soggetto_id,
    tipo_indirizzo_id,
    indirizzo_libero
)
SELECT
    s.id,
    t.tipo_indirizzo_id,
    'Via Test PR DOMFISC'
FROM tmp_soggetto_pr_ok s
JOIN tmp_tipo_domfisc t ON TRUE;

SELECT lives_ok(
    $$
      SET CONSTRAINTS ALL IMMEDIATE;
    $$,
    'PR con indirizzi obbligatori: ok'
);

ROLLBACK;

-- =========================================================
-- Caso 3: SC senza SEDELEG -> fallisce
-- =========================================================
BEGIN;

WITH ins AS (
  INSERT INTO anagrafiche.soggetti (
      codice,
      ragione_sociale,
      cognome,
      nome,
      stato_id,
      codice_fiscale,
      partita_iva,
      tipo_soggetto_dettaglio_id,
      storicizza,
      attivo
  )
  SELECT
      'TST-IND-SC-ERR',
      'Societa Test ERR',
      NULL,
      NULL,
      (SELECT stato_id FROM tmp_stato_test),
      NULL,
      '55048230233',
      (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_sc),
      TRUE,
      TRUE
  RETURNING id
)
SELECT *
INTO TEMP TABLE tmp_soggetto_sc_err
FROM ins;

INSERT INTO anagrafiche.contatti (
    tipo_contatto_id,
    soggetto_id,
    nominativo,
    email,
    is_default
)
SELECT
    (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test),
    s.id,
    'Contatto SC ERR',
    'sc.err@example.com',
    TRUE
FROM tmp_soggetto_sc_err s;

SELECT throws_ok(
    $$
      SET CONSTRAINTS ALL IMMEDIATE;
    $$,
    NULL,
    NULL,
    'SC senza indirizzo SEDELEG: guard blocca'
);

ROLLBACK;

-- =========================================================
-- Caso 4: SC con SEDELEG -> passa
-- =========================================================
BEGIN;

WITH ins AS (
  INSERT INTO anagrafiche.soggetti (
      codice,
      ragione_sociale,
      cognome,
      nome,
      stato_id,
      codice_fiscale,
      partita_iva,
      tipo_soggetto_dettaglio_id,
      storicizza,
      attivo
  )
  SELECT
      'TST-IND-SC-OK',
      'Societa Test OK',
      NULL,
      NULL,
      (SELECT stato_id FROM tmp_stato_test),
      NULL,
      '29878230910',
      (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_sc),
      TRUE,
      TRUE
  RETURNING id
)
SELECT *
INTO TEMP TABLE tmp_soggetto_sc_ok
FROM ins;

INSERT INTO anagrafiche.contatti (
    tipo_contatto_id,
    soggetto_id,
    nominativo,
    email,
    is_default
)
SELECT
    (SELECT tipo_contatto_id FROM tmp_tipo_contatto_test),
    s.id,
    'Contatto SC OK',
    'sc.ok@example.com',
    TRUE
FROM tmp_soggetto_sc_ok s;

INSERT INTO anagrafiche.indirizzi_soggetti (
    soggetto_id,
    tipo_indirizzo_id,
    indirizzo_libero
)
SELECT
    s.id,
    t.tipo_indirizzo_id,
    'Via Test SC SEDELEG'
FROM tmp_soggetto_sc_ok s
JOIN tmp_tipo_sedeleg t ON TRUE;


-- 3.b) Inserimento successivo di dati_societari: deve essere ammesso
SELECT lives_ok(
    $$
      INSERT INTO anagrafiche.dati_societari (
          soggetto_id,
          forma_giuridica,
          capitale_sociale,
          id_prov_iscri_rea,
          iscrizione_rea,
          socio_unico,
          liquidazione,
          destinatario_fe,
          pec_fatturazione,
          codice_sdi,
          data_costituzione
      )
      SELECT
          s.id,
          'SPA',
          50000.00,
          (SELECT provincia_id FROM tmp_provincia_test),
          'SP-REA-077',
          'SM',
          'LN',
          'XXXXXXX002',
          'fatturazione.ciccio@example.com',
          'SPCOD12377',
          CURRENT_DATE
      FROM anagrafiche.soggetti s
      WHERE s.codice = 'TST-IND-SC-OK';
    $$,
    'Soggetto SP OPTIONAL con dati_societari: insert OK'
);




SELECT lives_ok(
    $$
      SET CONSTRAINTS ALL IMMEDIATE;
    $$,
    'SC con indirizzo SEDELEG: ok'
);

commit;

SELECT * FROM finish();
