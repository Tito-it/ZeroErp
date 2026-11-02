-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Verifica guard DEFERRABLE: indirizzi obbligatori per soggetti
-- (config.tipi_soggetto_dettaglio_tipi_indirizzo).
--
-- Casi:
-- - PR (CF): RES + DOMFISC obbligatori
-- - SC (P.IVA): SEDELEG obbligatorio
-- ------------------------------------------------------------

-- ============================================================================
-- rev 2026-08-18 — bonifica baseline. Qui c'era un blocco di «cleanup
-- iniziale» che cancellava i soggetti di prova delle corse precedenti. Non
-- funziona piu': quei soggetti hanno nel frattempo acquisito riferimenti e le
-- FK sono RESTRICT (fk_risorse_umane_soggetti), quindi il DELETE moriva e con
-- lui tutto il file — ZERO asserzioni su 9.
--
-- ⭐ Il file NON lascia residui suoi: ogni caso e' gia' un BEGIN ... ROLLBACK
-- a se' (e' cosi' che si collauda un guard DEFERRABLE — si inserisce
-- l'incompleto e si forza SET CONSTRAINTS ALL IMMEDIATE dentro throws_ok).
-- I residui in giro sono di quando non era cosi'. Il rimedio e' non collidere
-- invece di cancellare: codici e partite IVA sono UNICI PER CORSA.
--
-- ⚠️ tmp_run_sfx si crea PRIMA del primo BEGIN, in autocommit: se nascesse
-- dentro una delle transazioni di caso, il ROLLBACK se la porterebbe via e i
-- casi successivi non la troverebbero.
-- ============================================================================

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

SELECT plan(9);

-- ⛔ LE PARTITE IVA NON SI PRECALCOLANO QUI (2026-09-23), e la ragione e'
--   sottile: `dbops.fn_pgtap_piva_libera()` risponde «la prima libera ADESSO».
--   Due chiamate nella stessa istruzione danno lo STESSO numero (misurato), e
--   soprattutto su un database ricostruito la partita libera all'inizio del
--   file e' la stessa che il mondo — costruito dalla riga di contesto dentro
--   il primo caso — si prende un attimo dopo: il soggetto del test collideva
--   con il soggetto dell'azienda su `uq_soggetto_idstato_id_fiscale_univoco`.
--   ⇒ Ogni caso chiede la sua partita DOPO aver costruito il mondo. Il
--   suffisso random invece resta qui: non tocca il database.
CREATE TEMP TABLE tmp_run_sfx AS
SELECT substr(md5(clock_timestamp()::text), 1, 8) AS sfx;

-- =========================================================
-- Precondizioni base: stato, tipo_contatto, tipi
-- =========================================================
CREATE TEMP TABLE tmp_stato_test AS
SELECT id AS stato_id
FROM config.stati
ORDER BY id
LIMIT 1;
-- rev 2026-10-18: i campi della forma che il guard vuole per questo stato
--   (dbops.fn_pgtap_indirizzo_libero_forma: comune e CAP per l'Italia).
ALTER TABLE tmp_stato_test ADD COLUMN comune_id integer, ADD COLUMN codice_postale_id integer,
                           ADD COLUMN locality varchar, ADD COLUMN postal_code varchar;
UPDATE tmp_stato_test
   SET (comune_id, codice_postale_id, locality, postal_code) =
       (SELECT f.comune_id, f.codice_postale_id, f.locality, f.postal_code
          FROM dbops.fn_pgtap_indirizzo_libero_forma(tmp_stato_test.stato_id) f);

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
      ragione_sociale,
      cognome,
      nome,
      sesso,   -- un privato: obbligatorio (sesso_policy REQUIRED)
      stato_id,
      codice_fiscale,
      partita_iva,
      tipo_soggetto_dettaglio_id,
      storicizza,
      attivo
  )
  SELECT
      'TST-IND-PR-ERR-' || (SELECT sfx FROM tmp_run_sfx),
      NULL,
      'Test',
      'PR ERR',
      'M',
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
    -- ⚠️ rev 2026-08-18: era NULL, cioe' «un errore qualunque va bene» —
    --   compreso il crash del guard che questo test deve verificare.
    'P0001',
    NULL,
    'PR senza indirizzi obbligatori: guard blocca'
);

ROLLBACK;

-- =========================================================
-- Caso 2: PR con RES + DOMFISC -> passa
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
      ragione_sociale,
      cognome,
      nome,
      sesso,   -- un privato: obbligatorio (sesso_policy REQUIRED)
      stato_id,
      codice_fiscale,
      partita_iva,
      tipo_soggetto_dettaglio_id,
      storicizza,
      attivo
  )
  SELECT
      'TST-IND-PR-OK-' || (SELECT sfx FROM tmp_run_sfx),
      NULL,
      'Test',
      'PR OK',
      'M',
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

-- ⚠️ Forma libera COMPLETA: la forma la sceglie dallo stato il guard
--   anagrafiche.trgfn_indirizzi_guard_forma_libera (rev 2026-10-18: l'Italia
--   vuole comune e CAP del catalogo, in tmp_stato_test dall'helper).
--   Il solo indirizzo_libero non basta.
INSERT INTO anagrafiche.indirizzi_soggetti (
    soggetto_id,
    tipo_indirizzo_id,
    indirizzo_libero,
    stato_id,
    comune_id,
    codice_postale_id,
    locality,
    postal_code
)
SELECT
    s.id,
    t.tipo_indirizzo_id,
    'Via Test PR RES',
    (SELECT stato_id FROM tmp_stato_test),
    (SELECT comune_id FROM tmp_stato_test),
    (SELECT codice_postale_id FROM tmp_stato_test),
    (SELECT locality FROM tmp_stato_test),
    (SELECT postal_code FROM tmp_stato_test)
FROM tmp_soggetto_pr_ok s
JOIN tmp_tipo_res t ON TRUE;

-- ⚠️ Forma libera COMPLETA: la forma la sceglie dallo stato il guard
--   anagrafiche.trgfn_indirizzi_guard_forma_libera (rev 2026-10-18: l'Italia
--   vuole comune e CAP del catalogo, in tmp_stato_test dall'helper).
--   Il solo indirizzo_libero non basta.
INSERT INTO anagrafiche.indirizzi_soggetti (
    soggetto_id,
    tipo_indirizzo_id,
    indirizzo_libero,
    stato_id,
    comune_id,
    codice_postale_id,
    locality,
    postal_code
)
SELECT
    s.id,
    t.tipo_indirizzo_id,
    'Via Test PR DOMFISC',
    (SELECT stato_id FROM tmp_stato_test),
    (SELECT comune_id FROM tmp_stato_test),
    (SELECT codice_postale_id FROM tmp_stato_test),
    (SELECT locality FROM tmp_stato_test),
    (SELECT postal_code FROM tmp_stato_test)
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

-- Contesto applicativo, dentro il caso (vedi la nota in testa).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
-- ⚠️ E LA FINESTRA DIFFERITA SI RIAPRE, DICHIARANDOLO. La riga di contesto,
--   quando COSTRUISCE il mondo (database ricostruito), esce con i vincoli
--   IMMEDIATE come ogni helper: questo caso invece si regge sulla finestra
--   differita — inserisce l'incompleto e forza IMMEDIATE dentro throws_ok.
--   Contare sulla finestra «di default» e' verde su dev e rosso in CI.
SET CONSTRAINTS ALL DEFERRED;

-- La partita IVA del caso, chiesta DOPO che il mondo esiste (vedi la nota
-- in testa): «libera» vuol dire «libera adesso».
CREATE TEMP TABLE tmp_piva_caso_err AS SELECT dbops.fn_pgtap_piva_libera() AS piva;

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
      'TST-IND-SC-ERR-' || (SELECT sfx FROM tmp_run_sfx),
      'Societa Test ERR',
      NULL,
      NULL,
      (SELECT stato_id FROM tmp_stato_test),
      -- ⚠️ rev 2026-08-18: il codice fiscale non c'era. Per una societa' di
      --   capitali trgfn_soggetti_guard_cf_piva_obbligatori lo pretende, e per
      --   una PG coincide con la partita IVA.
      (SELECT piva FROM tmp_piva_caso_err),
      (SELECT piva FROM tmp_piva_caso_err),
      (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_sc),
      TRUE,
      TRUE
  RETURNING id
)
SELECT *
INTO TEMP TABLE tmp_soggetto_sc_err
FROM ins;

-- ⚠️ Dati societari: servono a ENTRAMBI i casi SC, non solo a quello buono.
--   Una societa' di capitali senza riga in anagrafiche.dati_societari viene
--   bloccata da quel guard — e nel caso «ERR» il test verrebbe verde per il
--   motivo sbagliato, non per l'indirizzo mancante che vuole verificare.
-- ⭐ Rev 20261011 (brief-db-dati-fiscali-e-societari-del-soggetto, B-5): dal
--   20261011-04 l'app non scrive la tabella, si passa dal verbo; la forma e'
--   NOT NULL e ammessa dalla natura (SC -> SRL, C-1, C-2).
SELECT anagrafiche.fn_scrivi_dati_societari(
           p_soggetto_id        := s.id,
           p_forma_giuridica_id := (SELECT fg.id FROM config.forme_giuridiche fg WHERE fg.codice = 'SRL'),
           p_id_prov_iscri_rea  := (SELECT p.id FROM config.province p ORDER BY p.id LIMIT 1),
           p_iscrizione_rea     := 'REA-' || (SELECT sfx FROM tmp_run_sfx) || '-SCERR',
           p_capitale_sociale   := 10000.00,
           p_socio_unico        := 'SM',
           p_liquidazione       := 'LN',
           p_destinatario_fe    := NULL,   -- nessun canale FE (D-6, 20261010-37)
           p_pec_fatturazione   := NULL,
           p_codice_sdi         := NULL,
           p_data_costituzione  := NULL)
  FROM tmp_soggetto_sc_err s;

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
    -- ⚠️ rev 2026-08-18: era NULL, cioe' «un errore qualunque va bene» —
    --   compreso il crash del guard che questo test deve verificare.
    'P0001',
    NULL,
    'SC senza indirizzo SEDELEG: guard blocca'
);

ROLLBACK;

-- =========================================================
-- Caso 4: SC con SEDELEG -> passa
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

-- La partita IVA del caso, chiesta DOPO che il mondo esiste (vedi la nota
-- in testa): «libera» vuol dire «libera adesso».
CREATE TEMP TABLE tmp_piva_caso_ok AS SELECT dbops.fn_pgtap_piva_libera() AS piva;

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
      'TST-IND-SC-OK-' || (SELECT sfx FROM tmp_run_sfx),
      'Societa Test OK',
      NULL,
      NULL,
      (SELECT stato_id FROM tmp_stato_test),
      -- ⚠️ rev 2026-08-18: il codice fiscale non c'era. Per una societa' di
      --   capitali trgfn_soggetti_guard_cf_piva_obbligatori lo pretende, e per
      --   una PG coincide con la partita IVA.
      (SELECT piva FROM tmp_piva_caso_ok),
      (SELECT piva FROM tmp_piva_caso_ok),
      (SELECT tipo_soggetto_dettaglio_id FROM tmp_tipo_sc),
      TRUE,
      TRUE
  RETURNING id
)
SELECT *
INTO TEMP TABLE tmp_soggetto_sc_ok
FROM ins;

-- ⚠️ Il caso SC-OK i suoi dati societari se li mette da se', piu' avanti
--   (e' proprio quello che la sua asserzione verifica): qui non si duplicano.

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

-- ⚠️ Forma libera COMPLETA: la forma la sceglie dallo stato il guard
--   anagrafiche.trgfn_indirizzi_guard_forma_libera (rev 2026-10-18: l'Italia
--   vuole comune e CAP del catalogo, in tmp_stato_test dall'helper).
--   Il solo indirizzo_libero non basta.
INSERT INTO anagrafiche.indirizzi_soggetti (
    soggetto_id,
    tipo_indirizzo_id,
    indirizzo_libero,
    stato_id,
    comune_id,
    codice_postale_id,
    locality,
    postal_code
)
SELECT
    s.id,
    t.tipo_indirizzo_id,
    'Via Test SC SEDELEG',
    (SELECT stato_id FROM tmp_stato_test),
    (SELECT comune_id FROM tmp_stato_test),
    (SELECT codice_postale_id FROM tmp_stato_test),
    (SELECT locality FROM tmp_stato_test),
    (SELECT postal_code FROM tmp_stato_test)
FROM tmp_soggetto_sc_ok s
JOIN tmp_tipo_sedeleg t ON TRUE;


-- 3.b) Inserimento successivo di dati_societari: deve essere ammesso
SELECT lives_ok(
    $$
      -- ⭐ Rev 20261011 (B-5): dal verbo; la forma non e' piu' «la prima per id»
      --   ma una ammessa dalla natura SC (SRL), o il guard della forma la rifiuta.
      SELECT anagrafiche.fn_scrivi_dati_societari(
                 p_soggetto_id        := s.id,
                 p_forma_giuridica_id := (SELECT fg.id FROM config.forme_giuridiche fg WHERE fg.codice = 'SRL'),
                 p_id_prov_iscri_rea  := (SELECT provincia_id FROM tmp_provincia_test),
                 -- REA e SDI unici per corsa: i valori fissi sono bruciati da un
                 --   residuo del 2025 (uq su provincia+REA).
                 p_iscrizione_rea     := 'SP-REA-' || (SELECT sfx FROM tmp_run_sfx),
                 p_capitale_sociale   := 50000.00,
                 p_socio_unico        := 'SM',
                 p_liquidazione       := 'LN',
                 p_destinatario_fe    := 'C',    -- canale FE: codice SDI (D-6, 20261010-37)
                 p_pec_fatturazione   := 'fatt.' || (SELECT sfx FROM tmp_run_sfx) || '@example.com',
                 p_codice_sdi         := 'SP' || upper(substr((SELECT sfx FROM tmp_run_sfx), 1, 5)),
                 p_data_costituzione  := script.fn_data_operativa())
      FROM anagrafiche.soggetti s
      WHERE s.codice = 'TST-IND-SC-OK-' || (SELECT sfx FROM tmp_run_sfx);
    $$,
    'Soggetto SP OPTIONAL con dati_societari: insert OK'
);




SELECT lives_ok(
    $$
      SET CONSTRAINTS ALL IMMEDIATE;
    $$,
    'SC con indirizzo SEDELEG: ok'
);
-- ⛔ ROLLBACK, non COMMIT (2026-09-23): l'ultimo caso non ha piu' motivo
--   di lasciare le sue righe nel database, ora che il mondo se lo costruisce.
ROLLBACK;

SELECT * FROM finish();
