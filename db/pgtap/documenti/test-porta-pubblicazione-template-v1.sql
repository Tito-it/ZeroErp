-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la porta 16, la pubblicazione del template, si apre solo dal verbo.
-- Riferimento: brief-db-porte-aperte-dalla-sola-guc §9 (giro 16; D-A a, D-M a,
--   D-N a di Tid, 2026-11-23/24); changeSet 20_code/documenti/20261123-98 (il
--   trigger: GUC sull'id del modello E proprietario; il seed dalla sessione del
--   migratore) e 20261123-99 (il verbo SECURITY DEFINER col guard di
--   documenti_template_manage).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il verbo e' SECURITY DEFINER col search_path fissato; il trigger resta
--     INVOKER, che e' cio' che gli fa vedere chi scrive;
--   - il verbo chiede in prima riga l'azione documenti_template_manage: senza,
--     E_PERMESSO_NEGATO e nessuna scrittura;
--   - l'applicazione non apre la porta, ne' con la GUC accesa ('on') ne' col
--     valore giusto (l'id del modello): una scrittura diretta che porta una bozza
--     a PUBBLICATA, o chiude una pubblicata, resta rifiutata;
--   - con l'azione il verbo pubblica e chiude la versione precedente, e lascia la
--     GUC vuota.
--
-- L'operatore e' COSTRUITO (dbops.fn_pgtap_crea_emittente_operatore): nasce
--   senza azioni, quindi il caso «senza l'azione» c'e' su ogni database.
--   L'azione la da' dbops.fn_pgtap_concedi_azione, fra un caso e l'altro.
-- Gira come l'applicazione (runner di default). ⚠️ Da proprietario la sessione e'
--   del migratore: il guard del verbo non gira (D-M a) e il proprietario passa la
--   porta, quindi 3, 4, 6 e 9 sono rossi per costruzione.
--
-- Elenco test (plan 10):
--    1) il verbo: SECURITY DEFINER, search_path fissato
--    2) il trigger: SECURITY INVOKER
--    3) senza l'azione il verbo rifiuta: E_PERMESSO_NEGATO
--    4) … e non scrive: la bozza resta bozza
--    5) l'app accende la GUC ('on') e scrive diretta: rifiutata
--    6) ⭐ l'app scrive la GUC col valore giusto (l'id del modello) e scrive
--       diretta: rifiutata
--    7) con l'azione il verbo pubblica
--    8) dopo il verbo la GUC e' vuota
--    9) ⭐ l'app chiude a mano la versione pubblicata, GUC sul modello: rifiutata
--   10) il verbo pubblica la seconda e chiude la prima: la sua porta vale per tutte
--       e due le scritture
-- ------------------------------------------------------------

BEGIN;

-- Un'azienda nuova col suo operatore, senza azioni.
CREATE TEMP TABLE _e ON COMMIT DROP AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

-- Contesto applicativo (preambolo, guardrail_pgtap_preambolo).
DO $ctx$ BEGIN
  PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _e));
END $ctx$;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

-- ============================================================
-- Fixture: un modello dell'azienda, due bozze
-- ============================================================
CREATE TEMP TABLE _t ON COMMIT DROP AS
WITH ins AS (
    INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
        is_default, attivo)
    SELECT (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'PREVENTIVO'),
           'PGTAP-PORTA16', 'PGTAP_PORTA16', 'Template per la porta della pubblicazione',
           (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO'),
           'pgtap.builder', e.emittente_fiscale_id, false, true
      FROM _e e
    RETURNING id
)
SELECT id FROM ins;

-- ⚠️ In un'istruzione separata dal padre (guida pgTAP, «Padre e figlio»).
CREATE TEMP TABLE _v ON COMMIT DROP AS
WITH ins AS (
    INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo, html_template, render_engine_id,
        versione_contesto)
    SELECT (SELECT id FROM _t), n, 'BOZZA', 'Versione ' || n, '<p>v' || n || '</p>',
           (SELECT r.id FROM documenti.render_engine_documento r WHERE r.codice_interno = 'WEASYPRINT'), 1
      FROM generate_series(1, 2) n
    RETURNING id, versione
)
SELECT id, versione FROM ins;

-- La pubblicazione di una versione col verbo, come istruzione da provare.
CREATE OR REPLACE FUNCTION pg_temp.pubblica(p_versione integer, p_dal date)
RETURNS text LANGUAGE sql AS $f$
  SELECT format('SELECT * FROM documenti.fn_pubblica_template_documento_versione(%s, %L::date, 1, NULL)',
                (SELECT id FROM _v WHERE versione = p_versione), p_dal);
$f$;

-- Una scrittura diretta dell'app, con la GUC scritta nella stessa istruzione.
-- p_guc: il valore della GUC; p_set: l'assegnazione dell'UPDATE.
CREATE OR REPLACE FUNCTION pg_temp.diretta(p_guc text, p_versione integer, p_set text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format($q$WITH porta AS (
                    SELECT set_config('zeroerp.allow_template_versione_pubblicazione_override', %L, true))
                  UPDATE documenti.template_documenti_versioni
                     SET %s
                   WHERE id = %s AND EXISTS (SELECT 1 FROM porta)$q$,
                p_guc, p_set, (SELECT id FROM _v WHERE versione = p_versione));
$f$;

CREATE OR REPLACE FUNCTION pg_temp.stato(p_versione integer)
RETURNS text LANGUAGE sql AS $f$
  SELECT v.stato FROM documenti.template_documenti_versioni v
   WHERE v.id = (SELECT id FROM _v WHERE versione = p_versione);
$f$;

-- ============================================================
-- 1-2 La forma
-- ============================================================
SELECT is(
  (SELECT p.prosecdef AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search\_path=%')
     FROM pg_catalog.pg_proc p
    WHERE p.oid = 'documenti.fn_pubblica_template_documento_versione'::regproc),
  true,
  '1) il verbo: SECURITY DEFINER, search_path fissato');

SELECT is(
  (SELECT p.prosecdef FROM pg_catalog.pg_proc p
    WHERE p.oid = 'documenti.trgfn_template_documenti_versioni_protect_pubblicata'::regproc),
  false,
  '2) il trigger: SECURITY INVOKER, vede chi scrive');

-- ============================================================
-- 3-6 Senza l'azione, e senza il verbo
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.pubblica(1, DATE '2026-01-01')),
          'E_PERMESSO_NEGATO',
          '3) senza documenti_template_manage il verbo rifiuta');

SELECT is(pg_temp.stato(1), 'BOZZA',
          '4) … e non scrive: la bozza resta bozza');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.diretta('on', 1,
            $s$stato = 'PUBBLICATA', valido_dal = DATE '2026-01-01'$s$)),
          'E_DOCUMENTI_VERSIONE_STATO_FUORI_VERBO',
          '5) l''app accende la GUC e pubblica a mano: rifiutata');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.diretta((SELECT id FROM _t)::text, 1,
            $s$stato = 'PUBBLICATA', valido_dal = DATE '2026-01-01'$s$)),
          'E_DOCUMENTI_VERSIONE_STATO_FUORI_VERBO',
          '6) l''app scrive la GUC con l''id del modello e pubblica a mano: rifiutata, la porta chiede anche il proprietario');

-- ============================================================
-- 7-10 Con l'azione, dal verbo
-- ============================================================
DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione((SELECT auth_user_id FROM _e), 'documenti_template_manage');
END $az$;

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.pubblica(1, DATE '2026-01-01')), NULL,
          '7) con l''azione il verbo pubblica');

SELECT is(
  (SELECT pg_temp.stato(1) || ' / ' || coalesce(current_setting('zeroerp.allow_template_versione_pubblicazione_override', true), '')),
  'PUBBLICATA / ',
  '8) la versione e'' pubblicata, e dopo il verbo la GUC e'' vuota');

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.diretta((SELECT id FROM _t)::text, 1,
            $s$stato = 'OBSOLETA', valido_al = DATE '2026-02-28'$s$)),
          'E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE',
          '9) l''app chiude a mano la versione pubblicata, GUC sul modello: rifiutata');

-- ⚠️ La scrittura in un'istruzione e la rilettura nella successiva: nella stessa
--   istruzione lo snapshot non vedrebbe le righe appena scritte.
CREATE TEMP TABLE _esito_10 ON COMMIT DROP AS
SELECT coalesce(dbops.fn_pgtap_codice_errore(pg_temp.pubblica(2, DATE '2026-03-01')), 'ok') AS esito;

SELECT is(
  (SELECT e.esito || ' / ' || pg_temp.stato(1) || ' / ' || pg_temp.stato(2) FROM _esito_10 e),
  'ok / OBSOLETA / PUBBLICATA',
  '10) il verbo pubblica la seconda e chiude la prima: la sua porta vale per le due scritture');

SELECT * FROM finish();
ROLLBACK;
