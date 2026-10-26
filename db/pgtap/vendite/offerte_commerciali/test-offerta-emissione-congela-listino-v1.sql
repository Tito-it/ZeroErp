-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'offerta vive sulla versione di listino in vigore e la CONGELA
--       all'emissione; il contratto la congela all'attivazione, e senza una
--       versione in vigore non si attiva. Pulsanti e guard leggono lo stesso
--       predicato.
--       Brief: brief-db-offerta-emissione-ed-erogazione §A, §C.1 (decisioni
--       A-D2, A-D3 di Tid del 2026-10-07). ChangeSet 20261007-40 … -47.
--       ⚠️ rev 2026-10-19 (20261019-22, brief-db-grammatica-unica-documenti
--       lotto 1): p_documento ancorato a config.sorgenti.codice_interno, la
--       firma passa da text a character varying (test 2).
-- rev 2026-10-26 (brief-modello-documento-vendita §11): l'attivazione del contratto (19, 20a, 21a) dal verbo vendite.fn_cambia_stato_contratto, non piu' con l'UPDATE diretto dello stato che la porta ora rifiuta; prima del 18 si concede emetti_contratto, senza la quale la capability nasconde «Attiva». Nessuna attesa cambiata.
--
--       ⭐ Il test 8 e' il difetto del collaudo: un'offerta in BOZZA senza
--       versione fissata, su un listino che una versione in vigore ce l'ha,
--       aveva «Emetti» SPENTO (LISTINO_VERSIONE_MANCANTE). Il 9-10 provano
--       che il DB congela da se', senza il backend.
--
-- ⚠️ Fixture COSTRUITA: cliente e BA da dbops.fn_pgtap_crea_cliente_ba, due
--   listini da dbops.fn_pgtap_crea_listino — uno valido da oggi, uno con la
--   sola versione 2022 (ATTIVA ma scaduta: nessuna versione in vigore). Niente
--   dal DB esistente.
-- ⚠️ I codici si leggono dal canale CONSTRAINT dell'eccezione (pg_temp.codice),
--   non dalla frase: la frase la cambia il CSV dei messaggi.
-- ⚠️ Il test 22 legge il catalogo dei codici: rosso nella prova pre-apply
--   (il CSV si carica in 80_data), verde dopo l'apply.
--
-- Indice test (1..25; 15, 20, 21 in due asserzioni a/b):
--   Struttura
--   1)  vendite.fn_listino_versione_operativa: STABLE, non STRICT, INVOKER
--   2)  script.fn_check_listino_congelabile: STABLE, non STRICT, INVOKER
--   La regola sui valori
--   3)  nessun listino -> NULL
--   4)  listino senza versione fissata -> la versione in vigore oggi
--   5)  versione fissata -> vince la fissata
--   6)  check con un documento sconosciuto -> E_DOC_TIPO_NON_GESTITO
--   7)  check senza listino (negoziato puro) -> nessun motivo
--   Offerta
--   8)  BOZZA senza versione, listino in vigore: «Emetti» ACCESO
--   9)  …e l'emissione passa
--   10) …e congela la versione in vigore
--   11) listino senza versione in vigore: «Emetti» spento, reason
--   12) …con la reason_key nuova
--   13) …e l'emissione e' rifiutata con E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO
--   14) la revisione nasce SENZA versione (A-D3)
--   15) …e la congela alla sua emissione
--   16) versione fissata CHIUSA: «Emetti» spento con LISTINO_VERSIONE_NON_ATTIVA
--   17) …e l'emissione e' rifiutata con E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA
--   Contratto
--   18) listino senza versione in vigore: «Attiva» spento, reason (A-D2)
--   19) …e l'attivazione e' rifiutata con E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO
--   20) listino in vigore: l'attivazione congela la versione in vigore
--   21) versione gia' fissata (anche CHIUSA): l'attivazione la tiene
--   Catalogo
--   22) E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO a catalogo, CONFLITTO_STATO, frase in italiano
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga i DEFERRABLE INITIALLY DEFERRED non
--   scatterebbero mai (il file si chiude in ROLLBACK).
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(25);

-- Scopo: esegue uno statement che deve essere rifiutato e ne rende il codice,
--   dal canale CONSTRAINT dell'eccezione ('NESSUN ERRORE' se passa).
CREATE OR REPLACE FUNCTION pg_temp.codice(p_sql text)
RETURNS text LANGUAGE plpgsql AS $fx$
DECLARE v_cst text;
BEGIN
    BEGIN
        EXECUTE p_sql;
        RETURN 'NESSUN ERRORE';
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME;
        RETURN coalesce(nullif(v_cst, ''), '-');
    END;
END;
$fx$;

-- Scopo: l'azione di una capability verso uno stato, come jsonb.
CREATE OR REPLACE FUNCTION pg_temp.azione(p_blob jsonb, p_stato text)
RETURNS jsonb LANGUAGE sql IMMUTABLE AS $fx$
    SELECT a FROM jsonb_array_elements(p_blob -> 'available_actions') a
     WHERE a ->> 'target_state' = p_stato;
$fx$;

-- ============================================================
-- Fixture COSTRUITA
-- ============================================================
CREATE TEMP TABLE tmp_cl_utility AS
SELECT u.id AS utility_id
  FROM config.utilities u
 WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
 ORDER BY u.id LIMIT 1;

CREATE TEMP TABLE tmp_cl_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'congela listino offerte', (SELECT utility_id FROM tmp_cl_utility));

-- Listino con una versione valida da oggi.
CREATE TEMP TABLE tmp_cl_ok AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_cl_utility), 'congela in vigore');

-- Listino con la sola versione del 2022: ATTIVA ma scaduta, nessuna in vigore.
CREATE TEMP TABLE tmp_cl_scad AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_cl_utility), 'congela scaduto',
    DATE '2022-01-01', DATE '2022-12-31');

CREATE TEMP TABLE tmp_cl_ctx AS
SELECT
    (SELECT billing_account_id FROM tmp_cl_cli)       AS billing_account_id,
    (SELECT istanza_utility_id FROM tmp_cl_cli)       AS istanza_utility_id,
    (SELECT utility_id FROM tmp_cl_cli)               AS utility_id,
    script.fn_pgtap_emittente_operatore()             AS emittente_fiscale_id,
    (SELECT listino_id FROM tmp_cl_ok)                AS listino_ok,
    (SELECT listino_versione_id FROM tmp_cl_ok)       AS versione_ok,
    (SELECT listino_id FROM tmp_cl_scad)              AS listino_scad,
    (SELECT listino_versione_id FROM tmp_cl_scad)     AS versione_scad,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'BOZZA')    AS stato_bozza_id,
    (SELECT id FROM config.stati_doc_offerte WHERE codice_interno = 'EMESSA')   AS stato_emessa_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT')  AS stato_draft_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO') AS stato_attivo_id;

CREATE TEMP TABLE tmp_cl_off (slot text PRIMARY KEY, offerta_id bigint);

-- Scopo: un'offerta in BOZZA sul listino e con la versione dati.
CREATE OR REPLACE FUNCTION pg_temp.offerta(p_slot text, p_listino bigint, p_versione bigint)
RETURNS bigint LANGUAGE plpgsql AS $fx$
DECLARE v_id bigint;
BEGIN
    INSERT INTO vendite.offerte_commerciali (
        emittente_fiscale_id, billing_account_id, istanza_utility_id, utility_id,
        listino_id, listino_versione_id, validita_dal, stato_doc_offerta_id)
    SELECT ctx.emittente_fiscale_id, ctx.billing_account_id, ctx.istanza_utility_id,
           ctx.utility_id, p_listino, p_versione, script.fn_data_operativa(), ctx.stato_bozza_id
      FROM tmp_cl_ctx ctx
    RETURNING id INTO v_id;
    INSERT INTO tmp_cl_off VALUES (p_slot, v_id);
    RETURN v_id;
END;
$fx$;

DO $fx$ BEGIN
    PERFORM pg_temp.offerta('A', (SELECT listino_ok FROM tmp_cl_ctx), NULL);
    PERFORM pg_temp.offerta('B', (SELECT listino_scad FROM tmp_cl_ctx), NULL);
END $fx$;

-- ============================================================
-- 1-2) Struttura
-- ============================================================
SELECT is(
    (SELECT format('%s/%s/%s', p.provolatile, p.proisstrict, p.prosecdef) FROM pg_proc p
      WHERE p.oid = 'vendite.fn_listino_versione_operativa(bigint,bigint)'::regprocedure),
    's/f/f',
    '1) vendite.fn_listino_versione_operativa: STABLE, non STRICT, SECURITY INVOKER');

SELECT is(
    (SELECT format('%s/%s/%s', p.provolatile, p.proisstrict, p.prosecdef) FROM pg_proc p
      WHERE p.oid = 'script.fn_check_listino_congelabile(character varying,bigint,bigint)'::regprocedure),
    's/f/f',
    '2) script.fn_check_listino_congelabile: STABLE, non STRICT, SECURITY INVOKER');

-- ============================================================
-- 3-7) La regola sui valori
-- ============================================================
SELECT is(vendite.fn_listino_versione_operativa(NULL, NULL), NULL::bigint,
    '3) nessun listino: nessuna versione');

SELECT is(
    vendite.fn_listino_versione_operativa((SELECT listino_ok FROM tmp_cl_ctx), NULL),
    (SELECT versione_ok FROM tmp_cl_ctx),
    '4) listino senza versione fissata: la versione in vigore oggi');

SELECT is(
    vendite.fn_listino_versione_operativa((SELECT listino_ok FROM tmp_cl_ctx),
                                          (SELECT versione_scad FROM tmp_cl_ctx)),
    (SELECT versione_scad FROM tmp_cl_ctx),
    '5) versione fissata: vince la fissata, anche se non e'' quella in vigore');

SELECT is(
    pg_temp.codice($$ SELECT script.fn_check_listino_congelabile('PREVENTIVO', NULL, NULL) $$),
    'E_DOC_TIPO_NON_GESTITO',
    '6) check con un documento che non congela un listino: E_DOC_TIPO_NON_GESTITO');

SELECT is(
    script.fn_check_listino_congelabile('CONTRATTO', NULL, NULL),
    '[]'::jsonb,
    '7) check senza listino (negoziato puro): nessun motivo');

-- ============================================================
-- 8-10) Offerta su un listino in vigore, senza versione fissata
-- ============================================================
SELECT is(
    pg_temp.azione(script.fn_available_actions_offerta(
        (SELECT offerta_id FROM tmp_cl_off WHERE slot = 'A')), 'EMESSA') -> 'enabled',
    'true'::jsonb,
    '8) BOZZA senza versione su un listino in vigore: «Emetti» acceso (era spento: LISTINO_VERSIONE_MANCANTE)');

SELECT lives_ok(
    format('UPDATE vendite.offerte_commerciali SET stato_doc_offerta_id = %s WHERE id = %s',
           (SELECT stato_emessa_id FROM tmp_cl_ctx),
           (SELECT offerta_id FROM tmp_cl_off WHERE slot = 'A')),
    '9) …e l''emissione passa, senza che nessuno fissi prima la versione');

SELECT is(
    (SELECT o.listino_versione_id FROM vendite.offerte_commerciali o
      WHERE o.id = (SELECT offerta_id FROM tmp_cl_off WHERE slot = 'A')),
    (SELECT versione_ok FROM tmp_cl_ctx),
    '10) …e il DB congela la versione in vigore, nella stessa scrittura');

-- ============================================================
-- 11-13) Offerta su un listino senza versione in vigore
-- ============================================================
SELECT is(
    pg_temp.azione(script.fn_available_actions_offerta(
        (SELECT offerta_id FROM tmp_cl_off WHERE slot = 'B')), 'EMESSA') ->> 'reason',
    'LISTINO_SENZA_VERSIONE_IN_VIGORE',
    '11) listino senza versione in vigore: «Emetti» spento col motivo LISTINO_SENZA_VERSIONE_IN_VIGORE');

SELECT is(
    pg_temp.azione(script.fn_available_actions_offerta(
        (SELECT offerta_id FROM tmp_cl_off WHERE slot = 'B')), 'EMESSA') ->> 'reason_key',
    'vendite.offerte.azione_reason.listino_senza_versione_in_vigore',
    '12) …con la reason_key vendite.offerte.azione_reason.listino_senza_versione_in_vigore');

SELECT is(
    pg_temp.codice(format(
        'UPDATE vendite.offerte_commerciali SET stato_doc_offerta_id = %s WHERE id = %s',
        (SELECT stato_emessa_id FROM tmp_cl_ctx),
        (SELECT offerta_id FROM tmp_cl_off WHERE slot = 'B'))),
    'E_OFFERTA_EMISSIONE_SENZA_VERSIONE_LISTINO',
    '13) …e il guard rifiuta l''emissione con lo stesso motivo');

-- ============================================================
-- 14-15) La revisione congela alla SUA emissione (A-D3)
-- ============================================================
INSERT INTO tmp_cl_off
SELECT 'A2', vendite.fn_crea_revisione_offerta(
    (SELECT offerta_id FROM tmp_cl_off WHERE slot = 'A'), 'pgtap');

SELECT is(
    (SELECT o.listino_versione_id FROM vendite.offerte_commerciali o
      WHERE o.id = (SELECT offerta_id FROM tmp_cl_off WHERE slot = 'A2')),
    NULL::bigint,
    '14) la revisione nasce senza versione: non eredita quella congelata del padre');

-- ⚠️ Il verbo e la lettura in due istruzioni: nella stessa, la lettura vedrebbe
--   la fotografia di prima del verbo.
SELECT is(
    pg_temp.codice(format(
        'UPDATE vendite.offerte_commerciali SET stato_doc_offerta_id = %s WHERE id = %s',
        (SELECT stato_emessa_id FROM tmp_cl_ctx),
        (SELECT offerta_id FROM tmp_cl_off WHERE slot = 'A2'))),
    'NESSUN ERRORE',
    '15a) la revisione si emette');

SELECT is(
    (SELECT d.listino_versione_id FROM vendite.offerte_commerciali d
      WHERE d.id = (SELECT offerta_id FROM tmp_cl_off WHERE slot = 'A2')),
    (SELECT versione_ok FROM tmp_cl_ctx),
    '15b) …e congela la versione in vigore alla sua emissione');

-- ============================================================
-- 16-17) Versione fissata e CHIUSA
-- ============================================================
-- La versione 2022 e' scaduta: la chiusura passa il guard di transizione.
UPDATE vendite.listini_versioni SET stato = 'CHIUSA'
 WHERE id = (SELECT versione_scad FROM tmp_cl_ctx);

DO $fx$ BEGIN
    PERFORM pg_temp.offerta('D', (SELECT listino_scad FROM tmp_cl_ctx),
                                 (SELECT versione_scad FROM tmp_cl_ctx));
END $fx$;

SELECT is(
    pg_temp.azione(script.fn_available_actions_offerta(
        (SELECT offerta_id FROM tmp_cl_off WHERE slot = 'D')), 'EMESSA') ->> 'reason',
    'LISTINO_VERSIONE_NON_ATTIVA',
    '16) versione fissata CHIUSA: «Emetti» spento col motivo LISTINO_VERSIONE_NON_ATTIVA');

SELECT is(
    pg_temp.codice(format(
        'UPDATE vendite.offerte_commerciali SET stato_doc_offerta_id = %s WHERE id = %s',
        (SELECT stato_emessa_id FROM tmp_cl_ctx),
        (SELECT offerta_id FROM tmp_cl_off WHERE slot = 'D'))),
    'E_OFFERTA_EMISSIONE_VERSIONE_LISTINO_NON_ATTIVA',
    '17) …e il guard rifiuta l''emissione con lo stesso motivo');

-- ============================================================
-- 18-21) Contratto (A-D2)
-- ============================================================
CREATE TEMP TABLE tmp_cl_ctr (slot text PRIMARY KEY, contratto_id bigint);

-- Scopo: un contratto DRAFT sul listino e con la versione dati.
-- ⚠️ Un cliente per contratto: ex_contratti_no_overlap ammette un solo
--   contratto per (billing account, istanza, utility, ambito, periodo).
CREATE OR REPLACE FUNCTION pg_temp.contratto(p_slot text, p_listino bigint, p_versione bigint)
RETURNS bigint LANGUAGE plpgsql AS $fx$
DECLARE c record; v_id bigint;
BEGIN
    SELECT * INTO c FROM dbops.fn_pgtap_crea_cliente_ba(
        'congela listino contratto ' || p_slot, (SELECT utility_id FROM tmp_cl_utility));
    INSERT INTO vendite.contratti
        (numero, billing_account_id, istanza_utility_id, utility_id,
         stato_doc_contratto_id, emittente_fiscale_id, listino_id, listino_versione_id)
    SELECT 'PGT-CL-' || p_slot || '-' || substring(md5(clock_timestamp()::text) FOR 6),
           c.billing_account_id, c.istanza_utility_id, c.utility_id,
           ctx.stato_draft_id, ctx.emittente_fiscale_id, p_listino, p_versione
      FROM tmp_cl_ctx ctx
    RETURNING id INTO v_id;
    INSERT INTO tmp_cl_ctr VALUES (p_slot, v_id);
    RETURN v_id;
END;
$fx$;

DO $fx$ BEGIN
    PERFORM pg_temp.contratto('C1', (SELECT listino_scad FROM tmp_cl_ctx), NULL);
    PERFORM pg_temp.contratto('C2', (SELECT listino_ok FROM tmp_cl_ctx), NULL);
    PERFORM pg_temp.contratto('C3', (SELECT listino_scad FROM tmp_cl_ctx),
                                    (SELECT versione_scad FROM tmp_cl_ctx));
END $fx$;

-- ⚠️ «Attiva» e' dell'azione emetti_contratto: senza, la capability lo
--   nasconde e il verbo risponde E_PERMESSO_NEGATO (giro 8).
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_contratto');

SELECT is(
    pg_temp.azione(script.fn_available_actions_contratto(
        (SELECT contratto_id FROM tmp_cl_ctr WHERE slot = 'C1')), 'ATTIVO') ->> 'reason_key',
    'vendite.contratti.azione_reason.listino_senza_versione_in_vigore',
    '18) contratto su un listino senza versione in vigore: «Attiva» spento col motivo');

SELECT is(
    pg_temp.codice(format(
        $$SELECT * FROM vendite.fn_cambia_stato_contratto(%s, 'ATTIVO')$$,
        (SELECT contratto_id FROM tmp_cl_ctr WHERE slot = 'C1'))),
    'E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO',
    '19) …e l''attivazione e'' rifiutata: prima passava con la versione NULL');

-- ⚠️ Il verbo e la lettura in due istruzioni: nella stessa, la lettura vedrebbe
--   la fotografia di prima del verbo.
SELECT is(
    pg_temp.codice(format(
        $$SELECT * FROM vendite.fn_cambia_stato_contratto(%s, 'ATTIVO')$$,
        (SELECT contratto_id FROM tmp_cl_ctr WHERE slot = 'C2'))),
    'NESSUN ERRORE',
    '20a) listino in vigore: l''attivazione passa');

SELECT is(
    (SELECT d.listino_versione_id FROM vendite.contratti d
      WHERE d.id = (SELECT contratto_id FROM tmp_cl_ctr WHERE slot = 'C2')),
    (SELECT versione_ok FROM tmp_cl_ctx),
    '20b) …e congela la versione in vigore');

-- ⚠️ Il verbo e la lettura in due istruzioni: nella stessa, la lettura vedrebbe
--   la fotografia di prima del verbo.
SELECT is(
    pg_temp.codice(format(
        $$SELECT * FROM vendite.fn_cambia_stato_contratto(%s, 'ATTIVO')$$,
        (SELECT contratto_id FROM tmp_cl_ctr WHERE slot = 'C3'))),
    'NESSUN ERRORE',
    '21a) versione gia'' fissata, anche CHIUSA: l''attivazione passa');

SELECT is(
    (SELECT d.listino_versione_id FROM vendite.contratti d
      WHERE d.id = (SELECT contratto_id FROM tmp_cl_ctr WHERE slot = 'C3')),
    (SELECT versione_scad FROM tmp_cl_ctx),
    '21b) …e la tiene (e'' quella che l''offerta accettata ha portato)');

-- ============================================================
-- 22) Il codice nuovo a catalogo
-- ============================================================
SELECT is(
    (SELECT ce.classe::text || ' / ' || (me.messaggio LIKE 'Impossibile attivare il contratto%')::text
       FROM config.codici_errore ce
       JOIN config.messaggi_errore me ON me.codice = ce.codice AND me.lingua = 'it'
      WHERE ce.codice = 'E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO'),
    'CONFLITTO_STATO / true',
    '22) E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO a catalogo: CONFLITTO_STATO, frase in italiano');

SELECT * FROM finish();
ROLLBACK;
