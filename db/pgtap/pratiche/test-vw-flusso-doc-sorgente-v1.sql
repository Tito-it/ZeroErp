-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.vw_flusso_doc_sorgente — il documento di un flusso di pratica, la
--   sede DB della regola d'ancora per flusso (prima la copia stava nel backend).
--   Brief: brief-db-sorgente-documento-e-riga §7.2 lotto Z, giro Z.1 (R-P.1-1; regola
--   d'ordine di Tid, 2026-11-08: prima il ROOT, poi lo spareggio della pratica).
--
-- Il mondo si COSTRUISCE: un cliente, quattro commesse in bozza (i documenti, chiave id),
--   una pratica APERTA con due flussi. F1 ha il ROOT (commessa C1) e un collegato piu'
--   recente (C2); F2 non ha ROOT e ha due collegati (C3, poi C4). Un collegato senza
--   flusso (C1) appartiene alla pratica, non a un flusso.
--
-- Elenco test (plan 7):
--   1) la vista esiste ed e' security_invoker
--   2) le colonne sono quelle di script.vw_pratica_doc_sorgente, piu' flusso_id
--   3) F1: vince il ROOT, anche contro un collegato piu' recente
--   4) F2, senza ROOT: vince il collegato piu' recente
--   5) una riga per flusso, e il link senza flusso non ne crea una
--   6) un documento che la proiezione degli stati non risolve: risolto false, stato NULL, la sorgente
--      descritta (NULL-safe, come la gemella: la commessa non sta in script.vw_stato_sorgente)
--   7) il ROOT su un altro flusso della stessa pratica non cambia F2
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true)
ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE _cli AS SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('vista flusso doc');

CREATE TEMP TABLE _ref AS
SELECT script.fn_pgtap_emittente_operatore()                                          AS emittente_id,
       (SELECT soggetto_id FROM _cli)                                                 AS soggetto_id,
       (SELECT billing_account_id FROM _cli)                                          AS ba_id,
       (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA')         AS st_aperta,
       (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE')     AS priorita_id,
       (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS fl_da_eseguire,
       (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA')             AS t_commessa;

CREATE TEMP TABLE _doc AS
SELECT t.tag, c.commessa_id AS id
  FROM (VALUES ('C1'), ('C2'), ('C3'), ('C4')) AS t(tag)
 CROSS JOIN LATERAL dbops.fn_pgtap_crea_commessa('vista flusso ' || t.tag, NULL, (SELECT ba_id FROM _ref)) c;

CREATE TEMP TABLE _w (pratica_id bigint, f1 bigint, f2 bigint, f3 bigint);
DO $w$
DECLARE v_tp bigint; v_tf bigint; v_pr bigint; v_f1 bigint; v_f2 bigint; v_f3 bigint;
BEGIN
    INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
    VALUES ('TEST_VFDS', 'TEST_VFDS', 'Tipo test vista flusso', true)
    ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
    RETURNING id INTO v_tp;
    INSERT INTO pratiche.template_flussi (tipo_prestazione_id, codice, descrizione, sequenza, obbligatorio, attivo, ripetibilita)
    VALUES (v_tp, 'TEST_VFDS_STEP', 'Step test', 10, false, true, 'SEMPRE')
    ON CONFLICT (definizione_id, codice) DO UPDATE SET descrizione = EXCLUDED.descrizione, ripetibilita = EXCLUDED.ripetibilita
    RETURNING id INTO v_tf;
    INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
    SELECT emittente_id, v_tp, soggetto_id, st_aperta, priorita_id FROM _ref
    RETURNING id INTO v_pr;
    INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
    SELECT v_pr, v_tf, fl_da_eseguire FROM _ref RETURNING id INTO v_f1;
    INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
    SELECT v_pr, v_tf, fl_da_eseguire FROM _ref RETURNING id INTO v_f2;
    INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
    SELECT v_pr, v_tf, fl_da_eseguire FROM _ref RETURNING id INTO v_f3;

    -- F1: il ROOT (C1), poi un collegato piu' recente (C2).
    INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_id, ruolo_link, flusso_id)
    SELECT v_pr, t_commessa, (SELECT id FROM _doc WHERE tag = 'C1'), 'ROOT', v_f1 FROM _ref;
    INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_id, ruolo_link, flusso_id)
    SELECT v_pr, t_commessa, (SELECT id FROM _doc WHERE tag = 'C2'), 'COLLEGATO', v_f1 FROM _ref;
    -- F2: senza ROOT, due collegati (C3 prima, C4 dopo).
    INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_id, ruolo_link, flusso_id)
    SELECT v_pr, t_commessa, (SELECT id FROM _doc WHERE tag = 'C3'), 'COLLEGATO', v_f2 FROM _ref;
    INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_id, ruolo_link, flusso_id)
    SELECT v_pr, t_commessa, (SELECT id FROM _doc WHERE tag = 'C4'), 'COLLEGATO', v_f2 FROM _ref;
    -- Un collegato della pratica senza flusso.
    INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_id, ruolo_link, flusso_id)
    SELECT v_pr, t_commessa, (SELECT id FROM _doc WHERE tag = 'C1'), 'COLLEGATO', NULL FROM _ref;

    INSERT INTO _w VALUES (v_pr, v_f1, v_f2, v_f3);
END $w$;

-- 1) la vista
SELECT is(
    (SELECT coalesce(c.reloptions::text, '') FROM pg_catalog.pg_class c
      WHERE c.oid = to_regclass('script.vw_flusso_doc_sorgente')),
    '{security_invoker=on}',
    '1) script.vw_flusso_doc_sorgente esiste ed e'' security_invoker');

-- 2) le colonne: la gemella piu' flusso_id
SELECT is(
    (SELECT string_agg(a.attname::text, ',' ORDER BY a.attname)
       FROM pg_catalog.pg_attribute a
      WHERE a.attrelid = 'script.vw_flusso_doc_sorgente'::regclass AND a.attnum > 0 AND NOT a.attisdropped
        AND a.attname <> 'flusso_id'),
    (SELECT string_agg(a.attname::text, ',' ORDER BY a.attname)
       FROM pg_catalog.pg_attribute a
      WHERE a.attrelid = 'script.vw_pratica_doc_sorgente'::regclass AND a.attnum > 0 AND NOT a.attisdropped),
    '2) le colonne sono quelle di script.vw_pratica_doc_sorgente, piu'' flusso_id');

-- 3) F1: il ROOT vince sul collegato piu' recente
SELECT is(
    (SELECT (v.sorgente_id = (SELECT id FROM _doc WHERE tag = 'C1'), v.ruolo_link)::text
       FROM script.vw_flusso_doc_sorgente v WHERE v.flusso_id = (SELECT f1 FROM _w)),
    '(t,ROOT)',
    '3) F1: vince il ROOT (C1), anche contro un collegato piu'' recente (C2)');

-- 4) F2: senza ROOT, il collegato piu' recente
SELECT is(
    (SELECT (v.sorgente_id = (SELECT id FROM _doc WHERE tag = 'C4'), v.ruolo_link)::text
       FROM script.vw_flusso_doc_sorgente v WHERE v.flusso_id = (SELECT f2 FROM _w)),
    '(t,COLLEGATO)',
    '4) F2, senza ROOT: vince il collegato piu'' recente (C4)');

-- 5) una riga per flusso; il link senza flusso e il flusso senza link non ne creano
SELECT is(
    (SELECT string_agg(CASE v.flusso_id WHEN w.f1 THEN 'F1' WHEN w.f2 THEN 'F2' ELSE 'ALTRO' END, ',' ORDER BY v.flusso_id)
       FROM script.vw_flusso_doc_sorgente v, _w w
      WHERE v.pratica_id = w.pratica_id),
    'F1,F2',
    '5) una riga per flusso (F1, F2): il link senza flusso e il flusso senza link non ne creano');

-- 6) il descrittore del documento
SELECT is(
    (SELECT (v.risolto, v.stato_codice_interno IS NULL, v.sorgente_descrizione IS NOT NULL)::text
       FROM script.vw_flusso_doc_sorgente v WHERE v.flusso_id = (SELECT f1 FROM _w)),
    '(f,t,t)',
    '6) un documento non risolto dalla proiezione degli stati: risolto false, stato NULL, la sorgente descritta');

-- 7) un ROOT su F3 non tocca F2
INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_id, ruolo_link, flusso_id)
SELECT w.pratica_id, r.t_commessa, (SELECT id FROM _doc WHERE tag = 'C3'), 'ROOT', w.f3 FROM _w w, _ref r;
SELECT is(
    (SELECT v.sorgente_id = (SELECT id FROM _doc WHERE tag = 'C4')
       FROM script.vw_flusso_doc_sorgente v WHERE v.flusso_id = (SELECT f2 FROM _w)),
    true,
    '7) il ROOT su un altro flusso della stessa pratica non cambia il documento di F2');

SELECT * FROM finish();
ROLLBACK;
