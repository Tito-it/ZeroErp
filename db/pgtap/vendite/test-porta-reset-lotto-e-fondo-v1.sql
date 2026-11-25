-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: le porte 1-8, il reset del lotto e il fondo fattura, si aprono solo dai
--   verbi, col loro permesso e nel loro perimetro.
-- Riferimento: brief-db-porte-aperte-dalla-sola-guc §13 (giro 8 + 1-7; D-A a,
--   D-T b, D-U a, D-W a, D-X a, D-Y a, D-Z a di Tid); changeSet 20261125-01 …
--   -22 e -26. Che cosa fanno i verbi lo provano i loro test
--   (test-annulla-lotto-*, test-riporta-lotto-a-draft-v1,
--   test-elimina-fattura-da-lotto-*, test-uscita-documento-dal-giro-v1,
--   test-fondo-fattura-cancellazione, test-sistemazione-annullo-riporto); il
--   ramo della porta aperta, da proprietario, i test marcati owner del giro.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - i sei verbi sono SECURITY DEFINER col search_path fissato; il BB della
--     porta, i due guard e le sette funzioni di trigger restano INVOKER;
--   - le tre primitive (la pulizia, il reset dei fondi, la cancellazione del
--     fondo) non sono eseguibili dall'app; i sei verbi si';
--   - la porta del reset la legge solo vendite.fn_porta_reset_lotto_aperta e la
--     accende solo vendite.fn_cleanup_fatture_by_ids; accesa dall'app non apre:
--     il BB risponde false e una riga viva del log non si cancella;
--   - ogni verbo chiede il permesso dell'endpoint: reset_lotto_fattura_draft
--     per togliere ed escludere; per annullo e ritorno in bozza l'azione della
--     riga del passaggio o, senza, il livello TUTTO sull'area vendite; per il
--     fondo governa_fondo_fattura; per la sistemazione TUTTO sull'area pagamenti;
--   - DUE EMITTENTI: il lotto, l'atto di fondo e la sistemazione dell'altra
--     azienda «non ci sono», con la risposta di un oggetto inesistente, e restano
--     com'erano;
--   - col permesso l'annullo riesce anche con la GUC accesa davanti, e dopo il
--     verbo la GUC e' vuota.
--
-- ⛔ IL MONDO SI COSTRUISCE: due aziende coi loro operatori e clienti
--   (dbops.fn_pgtap_crea_mondo_cliente; per B dbops.fn_pgtap_crea_emittente_operatore).
--   Le cose di B si costruiscono nel contesto di B, poi il contesto passa ad A,
--   che e' chi agisce. I permessi li danno i builder dbops.fn_pgtap_concedi_azione
--   e dbops.fn_pgtap_concedi_livello_area.
-- ⚠️ Gira come l'applicazione (runner di default). Da proprietario la porta si
--   apre: 7 e 8 sono rossi per costruzione, e 3 vede i privilegi del proprietario.
--
-- Elenco test (plan 23):
--    1) i sei verbi: SECURITY DEFINER, search_path fissato
--    2) il BB della porta, i due guard, le sette funzioni di trigger: INVOKER
--    3) l'app non esegue le tre primitive
--    4) l'app esegue i sei verbi
--    5) la GUC del reset la legge solo il BB
--    6) la GUC del reset la accende solo la pulizia
--    7) ⭐ GUC accesa dall'app: il BB risponde false
--    8) ⭐ GUC accesa dall'app: la riga viva del log del lotto non si cancella
--    9) «togli la fattura» senza reset_lotto_fattura_draft: E_PERMESSO_NEGATO
--   10) «escludi dal giro» senza reset_lotto_fattura_draft: E_PERMESSO_NEGATO
--   11) annullo, area vendite a LETTURA: E_PERMESSO_NEGATO
--   12) ritorno in bozza del lotto gia' in bozza, area a LETTURA: E_PERMESSO_NEGATO
--   13) il passaggio EMESSA -> DRAFT, area a TUTTO, senza numera_fatture_lotti: rifiuta
--   14) … con numera_fatture_lotti: passa
--   15) ⭐ il lotto di B: l'annullo risponde E_LOTTO_NON_TROVATO
--   16) ⭐ il lotto di B: «togli la fattura» risponde E_LOTTO_NON_TROVATO
--   17) col permesso, e la GUC accesa davanti, l'annullo del lotto di A riesce
--   18) dopo il verbo la GUC del reset e' vuota
--   19) il fondo senza governa_fondo_fattura: E_PERMESSO_NEGATO
--   20) ⭐ l'atto di fondo di B: E_FONDO_NON_TROVATO
--   21) la sistemazione, area pagamenti a LETTURA: E_PERMESSO_NEGATO
--   22) ⭐ la sistemazione di B: E_SISTEMAZIONE_NON_TROVATA
--   23) … e il lotto, l'atto e la sistemazione di B restano com'erano (letti nel contesto di B)
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- Due aziende. ⚠️ Con un contesto aperto il builder del mondo riusa l'azienda di
--   chi agisce: A nasce senza contesto, B dal suo operatore, nel suo contesto.
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, m.* FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP porta reset A') m;

CREATE TEMP TABLE _op_b AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⚠️ 2. CONTESTO APPLICATIVO: prima B, per costruirne le cose.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _op_b)); END $ctx$;

INSERT INTO _mondi
SELECT 'B', m.* FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP porta reset B') m;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(23);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE _k AS
SELECT (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1) AS tipo_doc_id,
       (SELECT id FROM config.valute ORDER BY id LIMIT 1)                           AS valuta_id,
       (SELECT t.id FROM vendite.tipi_fondi_fattura t
         WHERE t.attivo IS TRUE AND t.codice_interno = 'F_F_ADD_ACC' ORDER BY t.id LIMIT 1) AS tipo_fondo_id,
       (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'DRAFT')  AS st_draft,
       (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno = 'EMESSA') AS st_emessa;

CREATE TEMP TABLE _lotti (lato text, lotto_id bigint);
CREATE TEMP TABLE _fondi (lato text, source_id bigint, sistemazione_id bigint);

-- Un lotto in bozza, vuoto, dell'azienda di chi e' in contesto.
CREATE OR REPLACE FUNCTION pg_temp.lotto(p_lato text)
RETURNS void LANGUAGE sql AS $f$
  INSERT INTO _lotti
  SELECT p_lato, vendite.fn_get_or_create_lotto(
           p_competenza_mese             => (date_trunc('month', script.fn_data_operativa()) + interval '3 month')::date,
           p_tipo_doc_fiscale_id         => (SELECT tipo_doc_id FROM _k),
           p_utility_id                  => (SELECT utility_id FROM _mondi WHERE lato = p_lato),
           p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM _mondi WHERE lato = p_lato),
           p_tipo_lotto                  => 'MASSIVO');
$f$;

SELECT pg_temp.lotto('B');

-- Di B anche un atto di fondo non eseguito e una sistemazione, nel suo contesto.
CREATE TEMP TABLE _fatt_b AS
SELECT (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura(
            'porta reset B sorgente', 'DEFINITIVA', (SELECT billing_account_id FROM _mondi WHERE lato = 'B'),
            false, false, p_minimo => true, p_totale_a_pagare => 100.00) f) AS sorgente;
ALTER TABLE _fatt_b ADD COLUMN figlia bigint;
UPDATE _fatt_b SET figlia = (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura(
            'porta reset B figlia', 'DRAFT', (SELECT billing_account_id FROM _mondi WHERE lato = 'B'),
            false, false, p_minimo => false, p_totale_a_pagare => 200.00) f);

WITH atto AS (
  INSERT INTO vendite.fatture_fondi_fattura_source (
      fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
      fattura_figlia_id, data_assegnazione, user_assegnazione,
      billing_account_id, utility_id, tipo_doc_fiscale_id,
      emittente_soggetto_ruolo_id, valuta_id, origine, motivo)
  SELECT fb.sorgente, k.tipo_fondo_id, 20.00, 'ASSEGNATO',
         fb.figlia, now(), current_user,
         m.billing_account_id, m.utility_id, k.tipo_doc_id,
         m.emittente_soggetto_ruolo_id, k.valuta_id, 'MANUALE', 'pgTAP porta reset: atto di B'
    FROM _fatt_b fb, _k k, _mondi m
   WHERE m.lato = 'B'
  RETURNING id
), sist AS (
  INSERT INTO pagamenti.sistemazioni
      (destinazione, importo, cliente_soggetto_ruolo_id, emittente_soggetto_ruolo_id,
       fattura_origine_id, motivo)
  SELECT 'RIMBORSO', 10, m.cliente_soggetto_ruolo_id, m.emittente_soggetto_ruolo_id,
         (SELECT sorgente FROM _fatt_b), 'pgTAP porta reset: sistemazione di B'
    FROM _mondi m
   WHERE m.lato = 'B'
  RETURNING id
)
INSERT INTO _fondi SELECT 'B', (SELECT id FROM atto), (SELECT id FROM sist);

-- Il contesto passa ad A, che e' chi agisce.
DO $ctxa$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondi WHERE lato = 'A')); END $ctxa$;

SELECT pg_temp.lotto('A');

-- Una riga viva del log del lotto di A, per la porta del log.
SELECT vendite.fn_log_pipeline_fase((SELECT lotto_id FROM _lotti WHERE lato = 'A'),
                                    (SELECT st_draft FROM _k), 'PGTAP', 'I'::char,
                                    'pgTAP porta reset: riga viva');

CREATE OR REPLACE FUNCTION pg_temp.a() RETURNS integer LANGUAGE sql AS $f$
  SELECT auth_user_id FROM _mondi WHERE lato = 'A';
$f$;
CREATE OR REPLACE FUNCTION pg_temp.lotto_di(p_lato text) RETURNS bigint LANGUAGE sql AS $f$
  SELECT lotto_id FROM _lotti WHERE lato = p_lato;
$f$;

-- ============================================================
-- 1-4 La forma
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pg_catalog.pg_proc p
    WHERE p.oid IN ('vendite.fn_annulla_lotto_da_draft'::regproc, 'vendite.fn_riporta_lotto_a_draft'::regproc,
                    'vendite.fn_elimina_fattura_da_lotto'::regproc, 'vendite.fn_escludi_documento_da_giro'::regproc,
                    'vendite.fn_cancella_fondo_fattura'::regproc, 'pagamenti.fn_annulla_sistemazione'::regproc)
      AND p.prosecdef
      AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search\_path=%')),
  6,
  '1) i sei verbi: SECURITY DEFINER, search_path fissato');

SELECT is(
  (SELECT count(*)::int
     FROM pg_catalog.pg_proc p
    WHERE p.oid IN ('vendite.fn_porta_reset_lotto_aperta'::regproc, 'vendite.fn_guard_passaggio_lotto'::regproc,
                    'script.fn_guard_livello_area'::regproc,
                    'vendite.trgfn_attivita_fatturabili_guard_fatturato'::regproc,
                    'vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile'::regproc,
                    'vendite.trgfn_commesse_attivita_guard_quantita_immutabile'::regproc,
                    'vendite.trgfn_commesse_guard_chiave_immutabile'::regproc,
                    'vendite.trgfn_fattura_satellite_guard_congelamento'::regproc,
                    'vendite.trgfn_fatturazione_lotti_guard_stato'::regproc,
                    'vendite.trgfn_logs_guard_delete'::regproc)
      AND NOT p.prosecdef),
  10,
  '2) il BB della porta, i due guard e le sette funzioni di trigger: INVOKER (vedono chi scrive)');

SELECT is(
  (SELECT count(*)::int
     FROM pg_catalog.pg_proc p
    WHERE p.oid IN ('vendite.fn_cleanup_fatture_by_ids'::regproc, 'vendite.fn_reset_fondi_fattura'::regproc,
                    'vendite.fn_applica_cancellazione_fondo_fattura'::regproc)
      AND has_function_privilege(current_user, p.oid, 'EXECUTE')),
  0,
  '3) l''app non esegue le tre primitive: la pulizia, il reset dei fondi, la cancellazione del fondo');

SELECT is(
  (SELECT count(*)::int
     FROM pg_catalog.pg_proc p
    WHERE p.oid IN ('vendite.fn_annulla_lotto_da_draft'::regproc, 'vendite.fn_riporta_lotto_a_draft'::regproc,
                    'vendite.fn_elimina_fattura_da_lotto'::regproc, 'vendite.fn_escludi_documento_da_giro'::regproc,
                    'vendite.fn_cancella_fondo_fattura'::regproc, 'pagamenti.fn_annulla_sistemazione'::regproc)
      AND has_function_privilege(current_user, p.oid, 'EXECUTE')),
  6,
  '4) l''app esegue i sei verbi');

-- ============================================================
-- 5-8 La porta del reset
-- ============================================================
-- Il codice senza i commenti: chi LEGGE la GUC e chi la ACCENDE. Una funzione
-- di trigger nuova che leggesse la GUC da se', senza il BB, tornerebbe la porta
-- della sola GUC.
CREATE TEMP TABLE _codice AS
SELECT p.oid::regprocedure::text AS fn,
       regexp_replace(p.prosrc, '--[^\n]*', '', 'g') AS src
  FROM pg_catalog.pg_proc p
  JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
   AND p.prosrc LIKE '%maintenance_reset_lotto_draft%';

SELECT is(
  (SELECT string_agg(fn, ', ' ORDER BY fn) FROM _codice
    WHERE src LIKE '%current\_setting(''zeroerp.maintenance\_reset\_lotto\_draft''%'),
  'vendite.fn_porta_reset_lotto_aperta(regclass)',
  '5) la GUC del reset la legge solo il BB della porta');

SELECT is(
  (SELECT string_agg(fn, ', ' ORDER BY fn) FROM _codice
    WHERE src LIKE '%set\_config(''zeroerp.maintenance\_reset\_lotto\_draft'', ''on''%'),
  'vendite.fn_cleanup_fatture_by_ids(bigint[],uuid)',
  '6) la GUC del reset la accende solo la pulizia');

DO $guc$ BEGIN PERFORM set_config('zeroerp.maintenance_reset_lotto_draft', 'on', true); END $guc$;

SELECT is(vendite.fn_porta_reset_lotto_aperta('vendite.fatturazione_lotti_log'::regclass), false,
          '7) GUC accesa dall''app: la porta non si apre, chiede anche il proprietario');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            $q$DELETE FROM vendite.fatturazione_lotti_log
                WHERE lotto_id = %s AND fase = 'PGTAP'$q$, pg_temp.lotto_di('A'))),
          'E_DELETE_NOT_ALLOWED',
          '8) GUC accesa dall''app e DELETE diretto di una riga viva del log: rifiutato');

-- La GUC resta accesa: i verbi la spengono all'ingresso (17-18).

-- ============================================================
-- 9-14 Il permesso del reset
-- ============================================================
SELECT dbops.fn_pgtap_concedi_livello_area(pg_temp.a(), 'vendite', 'LETTURA');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            'SELECT * FROM vendite.fn_elimina_fattura_da_lotto(%s, 1)', pg_temp.lotto_di('A'))),
          'E_PERMESSO_NEGATO',
          '9) «togli la fattura» senza reset_lotto_fattura_draft: rifiuta in prima riga');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            $q$SELECT vendite.fn_escludi_documento_da_giro(%s, 'PGTAP', 'prova')$q$, pg_temp.lotto_di('A'))),
          'E_PERMESSO_NEGATO',
          '10) «escludi dal giro» senza reset_lotto_fattura_draft: rifiuta in prima riga');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            'SELECT * FROM vendite.fn_annulla_lotto_da_draft(%s)', pg_temp.lotto_di('A'))),
          'E_PERMESSO_NEGATO',
          '11) annullo del lotto in bozza (riga senza azione), area vendite a LETTURA: rifiuta');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            'SELECT * FROM vendite.fn_riporta_lotto_a_draft(%s)', pg_temp.lotto_di('A'))),
          'E_PERMESSO_NEGATO',
          '12) ritorno in bozza di un lotto gia'' in bozza (nessun passaggio), area a LETTURA: rifiuta');

SELECT dbops.fn_pgtap_concedi_livello_area(pg_temp.a(), 'vendite', 'TUTTO');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            'SELECT vendite.fn_guard_passaggio_lotto(%s, %s, %s)',
            pg_temp.a(), (SELECT st_emessa FROM _k), (SELECT st_draft FROM _k))),
          'E_PERMESSO_NEGATO',
          '13) il passaggio EMESSA -> DRAFT chiede l''azione della sua riga: l''area a TUTTO non basta');

SELECT dbops.fn_pgtap_concedi_azione(pg_temp.a(), 'numera_fatture_lotti');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            'SELECT vendite.fn_guard_passaggio_lotto(%s, %s, %s)',
            pg_temp.a(), (SELECT st_emessa FROM _k), (SELECT st_draft FROM _k))),
          NULL,
          '14) … con numera_fatture_lotti il passaggio passa');

-- ============================================================
-- 15-18 Il perimetro, e il verbo col permesso
-- ============================================================
SELECT dbops.fn_pgtap_concedi_azione(pg_temp.a(), 'reset_lotto_fattura_draft');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            'SELECT * FROM vendite.fn_annulla_lotto_da_draft(%s)', pg_temp.lotto_di('B'))),
          'E_LOTTO_NON_TROVATO',
          '15) il lotto di B: per l''annullo di A non c''e''');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            'SELECT * FROM vendite.fn_elimina_fattura_da_lotto(%s, %s)',
            pg_temp.lotto_di('B'), (SELECT figlia FROM _fatt_b))),
          'E_LOTTO_NON_TROVATO',
          '16) il lotto di B: per «togli la fattura» di A non c''e''');

-- ⚠️ La scrittura in un'istruzione e la rilettura nelle successive.
CREATE TEMP TABLE _esito AS
SELECT coalesce(dbops.fn_pgtap_codice_errore(format(
         'SELECT * FROM vendite.fn_annulla_lotto_da_draft(%s)', pg_temp.lotto_di('A'))), 'ok') AS esito;

SELECT is(
  (SELECT esito FROM _esito) || ' / '
  || (SELECT s.codice_interno || ' ' || l.stato_operativo
        FROM vendite.fatturazione_lotti l
        JOIN config.stati_doc_fiscale s ON s.id = l.stato_doc_fiscale_id
       WHERE l.id = pg_temp.lotto_di('A')),
  'ok / ANNULLATA CHIUSO',
  '17) col permesso, e la GUC accesa davanti dall''app, l''annullo del lotto di A riesce');

SELECT is(coalesce(current_setting('zeroerp.maintenance_reset_lotto_draft', true), ''), '',
          '18) dopo il verbo la GUC del reset e'' vuota');

-- ============================================================
-- 19-22 Il fondo e la sistemazione
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(format(
            'SELECT * FROM vendite.fn_cancella_fondo_fattura(%s)', (SELECT source_id FROM _fondi WHERE lato = 'B'))),
          'E_PERMESSO_NEGATO',
          '19) il gesto sul fondo senza governa_fondo_fattura: rifiuta in prima riga');

SELECT dbops.fn_pgtap_concedi_azione(pg_temp.a(), 'governa_fondo_fattura');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            'SELECT * FROM vendite.fn_cancella_fondo_fattura(%s)', (SELECT source_id FROM _fondi WHERE lato = 'B'))),
          'E_FONDO_NON_TROVATO',
          '20) l''atto di fondo di B: per A non c''e''');

SELECT dbops.fn_pgtap_concedi_livello_area(pg_temp.a(), 'pagamenti', 'LETTURA');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            'SELECT pagamenti.fn_annulla_sistemazione(%s)', (SELECT sistemazione_id FROM _fondi WHERE lato = 'B'))),
          'E_PERMESSO_NEGATO',
          '21) l''annullo della sistemazione, area pagamenti a LETTURA: rifiuta in prima riga');

SELECT dbops.fn_pgtap_concedi_livello_area(pg_temp.a(), 'pagamenti', 'TUTTO');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            'SELECT pagamenti.fn_annulla_sistemazione(%s)', (SELECT sistemazione_id FROM _fondi WHERE lato = 'B'))),
          'E_SISTEMAZIONE_NON_TROVATA',
          '22) la sistemazione di B: per A non c''e''');

-- ============================================================
-- 23 B com'era
-- ============================================================
-- ⚠️ Si legge nel contesto dell'operatore di B: da A, sotto la row security,
--   le cose di B non si vedono (ed e' proprio il caso 15-22).
DO $ctxb$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondi WHERE lato = 'B')); END $ctxb$;

SELECT is(
  (SELECT s.codice_interno FROM vendite.fatturazione_lotti l
     JOIN config.stati_doc_fiscale s ON s.id = l.stato_doc_fiscale_id
    WHERE l.id = pg_temp.lotto_di('B'))
  || ' / ' || (SELECT count(*) FROM vendite.fatture_fondi_fattura_source s
                WHERE s.id = (SELECT source_id FROM _fondi WHERE lato = 'B'))
  || ' / ' || (SELECT s.stato FROM pagamenti.sistemazioni s
                WHERE s.id = (SELECT sistemazione_id FROM _fondi WHERE lato = 'B')),
  'DRAFT / 1 / BOZZA',
  '23) il lotto, l''atto e la sistemazione di B restano com''erano');

SELECT * FROM finish();
ROLLBACK;
