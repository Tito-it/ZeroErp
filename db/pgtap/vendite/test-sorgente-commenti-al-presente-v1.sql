-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: i COMMENT degli oggetti della provenienza (lotto 0 giro 0.3, lotto R)
--   descrivono l'oggetto al presente, come vuole linee-guida-sql §5d: niente
--   brief, marcatori di revisione, id di changeSet, sigle di decisione.
--   Il giro 0.3 li aveva scritti con un prefisso di cronaca; il giro R.2 li
--   riscrive interi, e questo file tiene il punto.
-- ChangeSet: 20261106-59 (e i COMMENT di -46 … -58)
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto R, giro R.2
-- ------------------------------------------------------------
-- Indice test (plan 5):
--   1) l'elenco chiuso esiste tutto (un oggetto rinominato o ritirato si toglie da qui)
--   2) nessun COMMENT di funzione dell'elenco porta un marcatore di storia
--   3) nessun COMMENT di colonna
--   4) nessun COMMENT di vincolo
--   5) nessun COMMENT di indice
--
-- ⚠️ Il perimetro e' un ELENCO, per nome: un oggetto nuovo di questa famiglia
--   entra qui nello stesso changeSet che lo crea. Il marcatore e' una regex sul
--   testo: rev + anno, «brief-», un id di changeSet (AAAAMMGG-NN), la stella, una
--   sigla di decisione (D-4, S-2, …). «lotto» non e' vietato: i lotti di
--   fatturazione sono dominio.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

CREATE TEMP TABLE _marcatore (re text);
INSERT INTO _marcatore VALUES
  ('(\mrev\M\s*20[0-9]{2}|brief-|\m20[0-9]{6}-[0-9]{2}\M|⭐|\m[DSOKPR]-[0-9]+\M)');

CREATE TEMP TABLE _fn (firma text PRIMARY KEY);
INSERT INTO _fn VALUES
  -- giro 0.3, riscritti da 20261106-59
  ('vendite.fn_documento_ritira_legami(character varying,bigint,integer)'),
  ('vendite.trgfn_resi_normalize()'),
  ('vendite.fn_documento_lineage_legami(text[],bigint[],text[],bigint[],text[])'),
  ('vendite.trgfn_resi_guard_cliente_ddt()'),
  ('vendite.fn_documento_lineage_archi(bigint[],text[])'),
  ('vendite.fn_documento_legami(character varying,bigint)'),
  ('vendite.trgfn_ddt_guard_cliente_sorgente()'),
  ('script.fn_get_sorgente_emittente_sr_id(bigint,text)'),
  ('script.trgfn_default_emittente_fiscale()'),
  ('script.fn_get_sorgente_emittente_sr_id(bigint,bigint,uuid)'),
  ('vendite.fn_ddt_trigger_ordine_testata(bigint,uuid,bigint)'),
  ('vendite.fn_ddt_vincoli_cliente(bigint,bigint,uuid,bigint)'),
  ('vendite.trgfn_resi_guard_ddt_consegnato()'),
  ('script.fn_check_ordine_annullabile(bigint)'),
  ('script.fn_available_actions_ddt(bigint)'),
  ('vendite.trgfn_ddt_normalize()'),
  ('vendite.trgfn_resi_default_magazzino()'),
  ('vendite.fn_conferma_reso(bigint)'),
  ('vendite.fn_annulla_reso(bigint)'),
  ('vendite.fn_ddt_push_diagnosi(bigint)'),
  ('script.fn_check_ddt_emittibile(vendite.ddt)'),
  -- lotto R, giro R.1
  ('script.fn_sorgente_provenienza(character varying,text)'),
  ('vendite.fn_offerta_righe_espanse(bigint)'),
  ('script.fn_check_righe_offerta_in_ordine(bigint)'),
  ('vendite.fn_genera_ordine_da_offerta(bigint)'),
  ('vendite.fn_push_preventivo_a_ordine(bigint,bigint[],bigint,character varying,bigint)'),
  ('vendite.fn_crea_revisione_preventivo(bigint,text)'),
  ('vendite.fn_push_offerta_a_contratto(bigint,bigint,boolean)'),
  ('vendite.fn_genera_ddt_da_ordine(bigint,jsonb,date)'),
  ('vendite.fn_genera_ddt_riconsegna(bigint,jsonb,date)');

CREATE TEMP TABLE _tab (tabella text PRIMARY KEY);
INSERT INTO _tab VALUES ('vendite.preventivi_righe'), ('vendite.ordini_righe'),
                        ('vendite.ddt_righe'), ('vendite.contratti_righe');

CREATE TEMP TABLE _ix (indice text PRIMARY KEY);
INSERT INTO _ix VALUES
  ('vendite.ix_ddt_v_sorgente_id'), ('vendite.ix_resi_sorgente_id'),
  ('vendite.ix_preventivi_righe_sorgente_uid'), ('vendite.ix_preventivi_righe_sorgente_riga'),
  ('vendite.ix_ordini_righe_sorgente_uid'), ('vendite.ix_ordini_righe_sorgente_riga'),
  ('vendite.ix_ddt_righe_sorgente_id'), ('vendite.ix_ddt_righe_sorgente_riga'),
  ('vendite.ix_contratti_righe_sorgente_uid'), ('vendite.ix_contratti_righe_sorgente_riga');

SELECT is(
  (SELECT count(*)::int FROM _fn WHERE to_regprocedure(firma) IS NULL)
  + (SELECT count(*)::int FROM _tab WHERE to_regclass(tabella) IS NULL)
  + (SELECT count(*)::int FROM _ix WHERE to_regclass(indice) IS NULL),
  0,
  '1) le funzioni, le tabelle e gli indici dell''elenco esistono tutti');

SELECT is(
  (SELECT coalesce(string_agg(f.firma, ', ' ORDER BY f.firma), '')
     FROM _fn f, _marcatore m
    WHERE coalesce(obj_description(to_regprocedure(f.firma), 'pg_proc'), '') ~* m.re
       OR obj_description(to_regprocedure(f.firma), 'pg_proc') IS NULL),
  '',
  '2) i COMMENT delle funzioni descrivono al presente: nessun brief, rev, changeSet, sigla (e nessuno manca)');

SELECT is(
  (SELECT coalesce(string_agg(t.tabella || '.' || a.attname, ', ' ORDER BY 1), '')
     FROM _tab t
     JOIN pg_attribute a ON a.attrelid = to_regclass(t.tabella)
                        AND a.attname IN ('sorgente_tipo_id', 'sorgente_id', 'sorgente_uid', 'sorgente_riga')
                        AND NOT a.attisdropped,
          _marcatore m
    WHERE coalesce(col_description(a.attrelid, a.attnum), '') ~* m.re
       OR col_description(a.attrelid, a.attnum) IS NULL),
  '',
  '3) i COMMENT delle colonne sorgente_* delle righe di vendita descrivono al presente');

SELECT is(
  (SELECT coalesce(string_agg(k.conname, ', ' ORDER BY k.conname), '')
     FROM _tab t
     JOIN pg_constraint k ON k.conrelid = to_regclass(t.tabella) AND k.conname LIKE 'chk_%_sorgente_forma',
          _marcatore m
    WHERE coalesce(obj_description(k.oid, 'pg_constraint'), '') ~* m.re
       OR obj_description(k.oid, 'pg_constraint') IS NULL),
  '',
  '4) i COMMENT dei CHECK di forma descrivono al presente');

SELECT is(
  (SELECT coalesce(string_agg(i.indice, ', ' ORDER BY i.indice), '')
     FROM _ix i, _marcatore m
    WHERE coalesce(obj_description(to_regclass(i.indice), 'pg_class'), '') ~* m.re
       OR obj_description(to_regclass(i.indice), 'pg_class') IS NULL),
  '',
  '5) i COMMENT degli indici descrivono al presente');

SELECT * FROM finish();
ROLLBACK;
