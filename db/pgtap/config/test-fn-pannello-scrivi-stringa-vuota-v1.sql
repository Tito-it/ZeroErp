-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il verbo del pannello scrive l'assenza come NULL —
--   config.fn_pannello_scrivi, passo 2-bis (20_code/config/20261112-57).
-- Riferimento: brief-db-token-null-dei-seed (D5 (a), Tid 2026-11-13).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - una stringa vuota o di soli spazi destinata a una colonna di testo
--     NULLABLE si scrive NULL: svuotare il campo dal drawer, che in modifica
--     manda '', non urta il CHECK «mai la stringa vuota» della colonna;
--   - un testo vero passa intatto, spazi compresi;
--   - una colonna di testo NOT NULL riceve la stringa vuota com'e'.
--
-- Elenco test (plan 7):
--   config.iva_assoggettamenti.note (il CHECK di 90_end/20261112-36)
--    1) UPDATE con note '': passa (prima: 23514)
--    2) ...e la nota scritta e' NULL
--    3) note di soli spazi: NULL
--    4) un testo vero, con spazi ai bordi: intatto
--   config.note_stili.note (il CHECK di 90_end/20261112-58)
--    5) INSERT con note '': la riga nasce con note NULL
--   Una colonna NOT NULL
--    6) config.tipi_nota.descrizione (text NOT NULL) con '': resta ''
--   Il valore non testuale
--    7) attivo = false resta false
--
-- ⚠️ Gira come l'APPLICAZIONE (runner di default). Operatore COSTRUITO
--   (fn_pgtap_crea_emittente_operatore) con TUTTO sull'area Configurazione,
--   come in config/test-fn-pannello-scrivi-v1.
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

CREATE TEMP TABLE _mondo AS SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _mondo)); END $ctx$;

-- TUTTO sull'area Configurazione, come lo concede il pannello dei permessi.
INSERT INTO config.user_override_aree (auth_user_id, area_id, livello, motivo)
SELECT m.auth_user_id, af.id, 'TUTTO', 'Fixture pgTAP'
  FROM _mondo m, config.aree_funzionali af WHERE af.schema_db = 'config';

-- Il codice di un rifiuto (fn_log_and_raise_error lo mette in CONSTRAINT_NAME).
CREATE FUNCTION pg_temp.codice_di(p_sql text) RETURNS text AS $$
DECLARE v_cod text;
BEGIN
  EXECUTE p_sql;
  RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_cod, ''), 'SQLSTATE:' || SQLSTATE);
END $$ LANGUAGE plpgsql;

-- La riga di prova di iva_assoggettamenti: una del seed.
CREATE TEMP TABLE _ass AS
SELECT min(ia.id) AS id FROM config.iva_assoggettamenti ia;

-- ============================================================
-- 1-4 iva_assoggettamenti.note
-- ============================================================
SELECT is(pg_temp.codice_di(format(
            $q$ SELECT config.fn_pannello_scrivi('config.iva_assoggettamenti', %s, '{"note":""}') $q$,
            (SELECT id FROM _ass))),
    'PASSA',
    '1) UPDATE con note vuota: passa, il CHECK di -36 non scatta');

SELECT is((SELECT ia.note FROM config.iva_assoggettamenti ia WHERE ia.id = (SELECT id FROM _ass)),
    NULL,
    '2) ...e la nota scritta e'' NULL');

SELECT is(
    (SELECT config.fn_pannello_scrivi('config.iva_assoggettamenti', id, '{"note":"   "}') ->> 'note' FROM _ass),
    NULL,
    '3) una nota di soli spazi si scrive NULL');

SELECT is(
    (SELECT config.fn_pannello_scrivi('config.iva_assoggettamenti', id, '{"note":"  Una nota  "}') ->> 'note' FROM _ass),
    '  Una nota  ',
    '4) un testo vero passa intatto, spazi compresi');

-- ============================================================
-- 5 note_stili.note, in creazione
-- ============================================================
SELECT is(
    config.fn_pannello_scrivi('config.note_stili', NULL,
        '{"codice":"PGTNS1","codice_interno":"PGTNS1","descrizione":"pgTAP","note":""}') ->> 'note',
    NULL,
    '5) INSERT su note_stili con note vuota: la riga nasce con note NULL');

-- ============================================================
-- 6-7 Cio' che non cambia
-- ============================================================
CREATE TEMP TABLE _nota AS
SELECT config.fn_pannello_scrivi('config.tipi_nota', NULL,
           '{"codice":"PGT_VUOTA","codice_interno":"PGT_VUOTA","descrizione":"pgTAP"}') AS riga;

SELECT is(
    (SELECT config.fn_pannello_scrivi('config.tipi_nota', (riga ->> 'id')::bigint,
                                      '{"descrizione":""}') ->> 'descrizione' FROM _nota),
    '',
    '6) colonna di testo NOT NULL: la stringa vuota arriva com''e''');

SELECT is(
    (SELECT config.fn_pannello_scrivi('config.tipi_nota', (riga ->> 'id')::bigint,
                                      '{"attivo":false}') ->> 'attivo' FROM _nota),
    'false',
    '7) un valore non testuale resta quello che e''');

SELECT * FROM finish();
ROLLBACK;
