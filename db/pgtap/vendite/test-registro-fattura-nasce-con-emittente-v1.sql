-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
--
-- Il registro delle fatture nasce con l'emittente (2026-10-18). R-BE-14 del
-- BE, decisioni D-14a … D-14d di Tid, brief-db-processi-accensione-per-ambiente
-- §6.12 (la richiesta) e §6.14 (la risposta). ChangeSet 20261019-07 … -12.
--
-- Il difetto: nessun emittente nasceva col registro delle fatture, e il primo
-- documento fiscale si fermava su vendite.fn_get_registro_id con
-- E_CONFIG_MANCANTE «registro non risolto».
--
-- Elenco test (plan 16):
--  1)   la regola del codice: FAT-<emittente>
--  -- un emittente che nasce (D-14a, D-14b) --
--  2)   ha il registro delle fatture standard, per tutte le utility
--  3)   ... e nessuna coppia (tipo documento, natura) scoperta
--  4)   ... e fn_get_registro_id risolve ogni coppia sullo standard
--  5)   ... e i registri delle altre famiglie nascono come prima
--  -- una coppia nuova --
--  6)   una natura che nasce attiva si collega allo standard di ogni emittente
--  7)   un UPDATE che non accende (attivo resta vero) non ricollega niente
--  8)   ... una natura che si riaccende si'
--  -- un emittente configurato a mano (D-14c) --
--  9)   riceve lo standard solo per la coppia che non ha
--  -- il guard sull'ambiguita' (D-14d) --
--  10)  una seconda coppia sullo stesso emittente e utility: E_REGISTRO_COPPIA_GIA_COPERTA
--  11)  un registro di UNA utility accanto a quello di tutte: ammesso
--  12)  ... portato a «tutte le utility» diventa ambiguo: rifiutato
--  13)  un UPDATE del collegamento che non cambia niente passa (no-op)
--  -- il builder pgTAP --
--  14)  fn_pgtap_registro_fattura salta lo standard: il suo registro, limite 9999
--  -- un registro standard spento --
--  15)  non si rifa' e non si ricollega: spegnerlo e' una scelta
--  -- per ultimo --
--  16)  la sistemazione degli emittenti di oggi e' idempotente: rilanciata non crea niente
--
-- Scopo:
--  - provare la primitiva, i trigger e i guard COSTRUENDO emittenti, coppie e
--    registri (regola zero: il test non legge la configurazione di oggi).
-- ------------------------------------------------------------

BEGIN;

-- Il mondo prima del contesto: l'emittente A con il suo operatore, e B.
CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT ceo.soggetto_ruolo_id AS sr_a, ceo.auth_user_id
  FROM dbops.fn_pgtap_crea_emittente_operatore() ceo;
ALTER TABLE _e ADD COLUMN sr_b bigint;
UPDATE _e SET sr_b = (SELECT e.soggetto_ruolo_id FROM dbops.fn_pgtap_crea_emittente('PGTFATB'::varchar) e);

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e)); END $ctx$;
-- I builder degli emittenti chiudono da se' la loro finestra dei differiti.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(16);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _f ON COMMIT DROP AS
SELECT e.sr_a, e.sr_b,
       vendite.fn_codice_registro_provisionato('FATTURA', e.sr_a) AS cod_a,
       vendite.fn_codice_registro_provisionato('FATTURA', e.sr_b) AS cod_b,
       (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1) AS utility_id
  FROM _e e;

ALTER TABLE _f ADD COLUMN std_a bigint, ADD COLUMN std_b bigint;
UPDATE _f SET std_a = (SELECT r.id FROM vendite.registri_fatturazione r WHERE r.codice = _f.cod_a),
              std_b = (SELECT r.id FROM vendite.registri_fatturazione r WHERE r.codice = _f.cod_b);

-- Le coppie attive, una volta.
CREATE TEMP TABLE _coppie ON COMMIT DROP AS
SELECT t.id AS tipo_id, n.id AS natura_id
  FROM config.tipi_doc_fiscale t CROSS JOIN config.nature_doc_fiscale n
 WHERE t.attivo IS TRUE AND n.attivo IS TRUE;

-- ============================================================
-- 1-5) Un emittente che nasce
-- ============================================================
SELECT is(vendite.fn_codice_registro_provisionato('FATTURA', 123), 'FATTURA-123',
    '1) la regola del codice: prime tre lettere della famiglia, trattino, emittente');

SELECT is(
    (SELECT r.famiglia_documento || '/' || coalesce(r.utility_id::text, 'tutte') || '/' || r.attivo::text
       FROM vendite.registri_fatturazione r, _f
      WHERE r.id = _f.std_a AND r.emittente_soggetto_ruolo_id = _f.sr_a),
    'FATTURA/tutte/true',
    '2) un emittente che nasce ha il registro delle fatture standard, per tutte le utility');

SELECT is(
    (SELECT count(*)::int FROM _f, vendite.fn_coppie_fattura_scoperte(_f.sr_a)),
    0,
    '3) ... e nessuna coppia (tipo documento, natura) scoperta');

SELECT is(
    (SELECT count(*)::int
       FROM _coppie c, _f
      CROSS JOIN LATERAL vendite.fn_get_registro_id(
                 p_tipo_doc_fiscale_id         => c.tipo_id,
                 p_natura_doc_id               => c.natura_id,
                 p_utility_id                  => NULL,
                 p_emittente_soggetto_ruolo_id => _f.sr_a) g
      WHERE g.registro_id = _f.std_a),
    (SELECT count(*)::int FROM _coppie),
    '4) ... e fn_get_registro_id risolve ogni coppia sul registro standard');

SELECT is(
    (SELECT count(*)::int FROM vendite.registri_fatturazione r, _f
      WHERE r.emittente_soggetto_ruolo_id = _f.sr_a AND r.famiglia_documento <> 'FATTURA'),
    (SELECT count(*)::int FROM vendite.famiglie_documento fd
      WHERE fd.attivo IS TRUE AND fd.codice_interno <> 'FATTURA'),
    '5) ... e i registri delle altre famiglie nascono come prima, uno per famiglia');

-- ============================================================
-- 6-8) Una coppia nuova
-- ============================================================
INSERT INTO config.nature_doc_fiscale (codice_interno, codice, descrizione, attivo)
VALUES ('PGTAP_NAT_STD', 'PGTAPNS', 'Natura pgTAP registro standard', true);

SELECT is(
    (SELECT count(*)::int
       FROM vendite.tipi_doc_fiscale_registri m, _f, config.nature_doc_fiscale n
      WHERE n.codice_interno = 'PGTAP_NAT_STD'
        AND m.natura_doc_id = n.id
        AND m.registro_id IN (_f.std_a, _f.std_b)),
    2 * (SELECT count(*)::int FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE),
    '6) una natura che nasce attiva si collega allo standard di ogni emittente, per ogni tipo documento');

DELETE FROM vendite.tipi_doc_fiscale_registri m
 USING config.nature_doc_fiscale n
 WHERE n.codice_interno = 'PGTAP_NAT_STD' AND m.natura_doc_id = n.id;
UPDATE config.nature_doc_fiscale SET attivo = true WHERE codice_interno = 'PGTAP_NAT_STD';

SELECT is(
    (SELECT count(*)::int FROM vendite.tipi_doc_fiscale_registri m, config.nature_doc_fiscale n
      WHERE n.codice_interno = 'PGTAP_NAT_STD' AND m.natura_doc_id = n.id),
    0,
    '7) un UPDATE che non accende (attivo resta vero) non ricollega niente');

UPDATE config.nature_doc_fiscale SET attivo = false WHERE codice_interno = 'PGTAP_NAT_STD';
UPDATE config.nature_doc_fiscale SET attivo = true  WHERE codice_interno = 'PGTAP_NAT_STD';

SELECT is(
    (SELECT count(*)::int
       FROM vendite.tipi_doc_fiscale_registri m, _f, config.nature_doc_fiscale n
      WHERE n.codice_interno = 'PGTAP_NAT_STD'
        AND m.natura_doc_id = n.id
        AND m.registro_id IN (_f.std_a, _f.std_b)),
    2 * (SELECT count(*)::int FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE),
    '8) ... una natura che si riaccende si'' collega');

-- La natura di prova si spegne: le coppie dei test che seguono sono quelle vere.
DELETE FROM vendite.tipi_doc_fiscale_registri m
 USING config.nature_doc_fiscale n
 WHERE n.codice_interno = 'PGTAP_NAT_STD' AND m.natura_doc_id = n.id;
UPDATE config.nature_doc_fiscale SET attivo = false WHERE codice_interno = 'PGTAP_NAT_STD';

-- ============================================================
-- 9) Un emittente configurato a mano (D-14c)
-- ============================================================
-- B passa a un registro suo, scritto a mano, per tutte le coppie tranne una;
-- lo standard perde i collegamenti.
CREATE TEMP TABLE _m ON COMMIT DROP AS
SELECT c.tipo_id, c.natura_id,
       row_number() OVER (ORDER BY c.tipo_id, c.natura_id) AS n
  FROM _coppie c;

CREATE TEMP TABLE _man (manuale_id bigint) ON COMMIT DROP;
WITH r AS (
    INSERT INTO vendite.registri_fatturazione (
        codice, descrizione, famiglia_documento, emittente_soggetto_ruolo_id,
        reset_policy, attivo, meta)
    SELECT 'PGTMAN-' || sr_b::text, 'Registro pgTAP scritto a mano', 'FATTURA', sr_b,
           'ANNUALE', true, jsonb_build_object('test_scope', 'pgtap_registro_standard')
      FROM _f
    RETURNING id
)
INSERT INTO _man SELECT r.id FROM r;

DELETE FROM vendite.tipi_doc_fiscale_registri WHERE registro_id = (SELECT std_b FROM _f);
INSERT INTO vendite.tipi_doc_fiscale_registri (tipo_doc_fiscale_id, natura_doc_id, registro_id)
SELECT m.tipo_id, m.natura_id, (SELECT manuale_id FROM _man)
  FROM _m m
 WHERE m.n > 1;

SELECT vendite.fn_provision_registri_emittente((SELECT sr_b FROM _f));

SELECT is(
    (SELECT string_agg(m.tipo_doc_fiscale_id::text || '/' || m.natura_doc_id::text, ',')
       FROM vendite.tipi_doc_fiscale_registri m, _f
      WHERE m.registro_id = _f.std_b),
    (SELECT tipo_id::text || '/' || natura_id::text FROM _m WHERE n = 1),
    '9) l''emittente configurato a mano riceve lo standard solo per la coppia che non ha');

-- ============================================================
-- 10-13) Il guard sull'ambiguita' (D-14d)
-- ============================================================
SELECT throws_like(
    (SELECT format('INSERT INTO vendite.tipi_doc_fiscale_registri (tipo_doc_fiscale_id, natura_doc_id, registro_id) VALUES (%s, %s, %s)',
                   m.tipo_id, m.natura_id, (SELECT manuale_id FROM _man))
       FROM _m m WHERE m.n = 1),
    '%numera già%sul registro FATTURA-%',
    '10) la coppia ha gia'' un registro per lo stesso emittente e utility: E_REGISTRO_COPPIA_GIA_COPERTA');

-- Un registro di UNA utility, per la stessa coppia.
CREATE TEMP TABLE _uti (utility_reg_id bigint) ON COMMIT DROP;
WITH r AS (
    INSERT INTO vendite.registri_fatturazione (
        codice, descrizione, famiglia_documento, emittente_soggetto_ruolo_id, utility_id,
        reset_policy, attivo, meta)
    SELECT 'PGTUTI-' || sr_b::text, 'Registro pgTAP di una utility', 'FATTURA', sr_b, utility_id,
           'ANNUALE', true, jsonb_build_object('test_scope', 'pgtap_registro_standard')
      FROM _f
    RETURNING id
)
INSERT INTO _uti SELECT r.id FROM r;

SELECT lives_ok(
    (SELECT format('INSERT INTO vendite.tipi_doc_fiscale_registri (tipo_doc_fiscale_id, natura_doc_id, registro_id) VALUES (%s, %s, %s)',
                   m.tipo_id, m.natura_id, (SELECT utility_reg_id FROM _uti))
       FROM _m m WHERE m.n = 1),
    '11) un registro di UNA utility accanto a quello di tutte: ammesso, il lookup preferisce il piu'' specifico');

SELECT throws_like(
    (SELECT format('UPDATE vendite.registri_fatturazione SET utility_id = NULL WHERE id = %s', utility_reg_id) FROM _uti),
    '%numera già%sul registro FATTURA-%',
    '12) ... portato a «tutte le utility» diventa ambiguo: rifiutato');

SELECT lives_ok(
    (SELECT format('UPDATE vendite.tipi_doc_fiscale_registri SET registro_id = registro_id WHERE registro_id = %s', std_b) FROM _f),
    '13) un UPDATE del collegamento che non cambia niente passa');

-- ============================================================
-- 14) Il builder pgTAP salta lo standard
-- ============================================================
-- ⚠️ Il builder in un'istruzione sua: la riga che crea non e' visibile alla
--   SELECT che lo chiama.
CREATE TEMP TABLE _b ON COMMIT DROP AS
SELECT script.fn_pgtap_registro_fattura(_f.sr_a) AS registro_id FROM _f;

SELECT is(
    (SELECT r.codice <> _f.cod_a AND r.limite_emissione_giorni = 9999
       FROM vendite.registri_fatturazione r, _f, _b
      WHERE r.id = _b.registro_id),
    true,
    '14) fn_pgtap_registro_fattura salta lo standard: il suo registro, col limite aperto');

-- ============================================================
-- 15) Un registro standard spento non si rifa' e non si ricollega
-- ============================================================
DELETE FROM vendite.tipi_doc_fiscale_registri WHERE registro_id = (SELECT std_a FROM _f);
UPDATE vendite.registri_fatturazione SET attivo = false WHERE id = (SELECT std_a FROM _f);

SELECT is(
    (SELECT vendite.fn_provision_registri_emittente(_f.sr_a)::text || '/'
            || (SELECT count(*) FROM vendite.fn_coppie_fattura_scoperte(_f.sr_a))::text
       FROM _f),
    '0/' || (SELECT count(*) FROM _coppie)::text,
    '15) uno standard spento non si rifa'' e non si ricollega: le coppie restano scoperte');

-- ============================================================
-- 16) Per ultimo: la sistemazione di oggi e' idempotente
-- ============================================================
SELECT vendite.fn_provision_registri_famiglia('FATTURA');
SELECT is(
    vendite.fn_provision_registri_famiglia('FATTURA'),
    0,
    '16) la sistemazione degli emittenti di oggi, rilanciata, non crea niente');

SELECT * FROM finish();
ROLLBACK;
