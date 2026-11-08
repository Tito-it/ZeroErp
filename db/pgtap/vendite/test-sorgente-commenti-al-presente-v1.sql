-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: i COMMENT degli oggetti della provenienza (lotto 0 giro 0.3, lotto R, lotto T giro T.3,
--   lotto C giri C.1, C.2 e C.3, lotto P giro P.1, lotto M giro M.2, giro finale)
--   descrivono l'oggetto al presente, come vuole linee-guida-sql §5d: niente
--   brief, marcatori di revisione, id di changeSet, sigle di decisione.
--   Il giro 0.3 li aveva scritti con un prefisso di cronaca; il giro R.2 li
--   riscrive interi, e questo file tiene il punto.
-- ChangeSet: 20261106-59 (e i COMMENT di -46 … -58, -74 … -87; giro C.3: 20261107-70 … -99, 20261108-01 … -04; giro P.1: 20261108-64 … -86; giro M.2: 20261109-15 … -18; giro Z.5: 20261109-82, la firma nuova del riferimento; giro finale: 20261110-07 … -13; giro finale bis: 20261110-32, le righe di fattura escono dall'elenco)
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto R, giro R.2
-- ------------------------------------------------------------
-- Indice test (plan 7):
--   1) l'elenco chiuso esiste tutto (un oggetto rinominato o ritirato si toglie da qui)
--   2) nessun COMMENT di funzione dell'elenco porta un marcatore di storia
--   3) nessun COMMENT di colonna
--   4) nessun COMMENT di vincolo
--   5) nessun COMMENT di indice
--   6) nessun COMMENT di vista (giro finale)
--   7) nessun COMMENT delle colonne nominate una per una (giro finale)
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

SELECT plan(7);

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
  ('vendite.fn_genera_ddt_riconsegna(bigint,jsonb,date)'),
  -- lotto T, giro T.3
  ('vendite.fn_offerta_documenti_vivi(bigint)'),
  ('script.fn_check_preventivo_annullabile(bigint)'),
  -- lotto C, giro C.1
  ('vendite.fn_emit_attivita_fatturabili_da_commessa(bigint,boolean,boolean,text[],uuid)'),
  ('vendite.trgfn_attivita_fatturabili_normalize()'),
  ('vendite.fn_resolve_termini_pagamento(bigint)'),
  ('dbops.fn_sorgenti_orfane_perimetro()'),
  -- lotto C, giro C.2
  ('vendite.fn_commessa_viva_di_sorgente(bigint,bigint,uuid)'),
  ('vendite.fn_link_commessa_sorgente(bigint,bigint,text,bigint,jsonb)'),
  ('vendite.trgfn_guard_fatturazione_immediata_immutabile()'),
  ('vendite.fn_check_commessa_sorgente_emittente_omogeneo(bigint,bigint,bigint,uuid)'),
  ('vendite.fn_guard_commessa_sorgente_emittente(bigint,bigint,bigint,uuid)'),
  ('vendite.trgfn_commesse_sorgenti_guard_emittente()'),
  ('dbops.fn_pgtap_crea_commessa(text,character varying,bigint,boolean,boolean)'),
  -- lotto C, giro C.3
  ('script.fn_segment_key_uid(character varying)'),
  ('vendite.fn_build_gruppo_fatturabile_key(bigint,text,bigint)'),
  ('vendite.fn_documento_uid_di_attivita(bigint,character varying)'),
  ('vendite.fn_gruppo_fatturabile_key_di_attivita(bigint,character varying,bigint)'),
  ('vendite.fn_upsert_commessa_attivita(bigint,character varying,uuid,bigint,date,bigint,numeric,date,date,date,numeric,numeric,character varying,character varying,numeric,bigint,bigint,smallint,integer,numeric,bigint,numeric,date,bigint,integer,bigint,bigint,boolean,character varying,boolean,character varying,character varying,bigint,text,character varying,jsonb,bigint,bigint,bigint,bigint,bigint)'),
  ('vendite.fn_batch_upsert_commessa_attivita(jsonb)'),
  ('vendite.fn_contratti_addebiti_maturati(date,bigint,bigint)'),
  ('vendite.fn_ritira_commessa_attivita_da_sorgente(bigint,bigint,uuid,text,bigint)'),
  ('script.fn_check_sorgente_chiudibile(bigint,bigint,uuid)'),
  ('vendite.trgfn_commesse_attivita_guard_sorgente_segment()'),
  ('dbops.fn_pgtap_crea_consumo(bigint,date,jsonb)'),
  ('dbops.fn_pgtap_consumo_della_commessa(bigint)'),
  ('dbops.fn_pgtap_provenienza_da_chiave(character varying)'),
  ('dbops.fn_pgtap_crea_commessa_attivita(bigint,numeric,uuid,bigint,bigint,character varying,text,bigint,numeric,character varying,character varying,date,date,text)'),
  -- lotto C, V-7
  ('vendite.fn_riferimento_gruppo_fatturabile(text,bigint)'),
  -- lotto P, giro P.1
  ('pratiche.fn_pratica_del_documento(bigint,bigint,uuid)'),
  ('pratiche.fn_stato_sorgente(bigint,bigint,uuid)'),
  ('pratiche.fn_reconcile_sorgente(bigint,bigint,uuid)'),
  ('pratiche.trgfn_documento_reconcile_proiezione()'),
  ('vendite.fn_genera_pratica_da_preventivo(bigint,integer,integer,text)'),
  -- lotto M, giro M.2
  ('dbops.fn_sorgenti_orfane()'),
  -- giro finale (20261110-07 … -13)
  ('script.fn_sorgente_chiave_id(text)'),
  ('script.fn_sorgente_chiave_uuid(text)'),
  ('script.trgfn_componenti_guard_coerenza_bom()'),
  ('script.trgfn_note_validate_generic()'),
  ('dbops.fn_pgtap_crea_sorgente(character varying,regclass)'),
  ('vendite.fn_documento_lineage_nodi(bigint[],text[])'),
  ('vendite.fn_documento_lineage(bigint,text,text)'),
  ('vendite.fn_fattura_origini(bigint)'),
  ('vendite.trgfn_commesse_attivita_proietta_stato_preventivo()'),
  ('vendite.fn_select_attivita_fatturabili(date,bigint,uuid,boolean,date,bigint,integer,integer,bigint,bigint,integer,text[])'),
  ('vendite.fn_reso_muove_merce(vendite.resi)');

CREATE TEMP TABLE _tab (tabella text PRIMARY KEY);
INSERT INTO _tab VALUES ('vendite.preventivi_righe'), ('vendite.ordini_righe'),
                        ('vendite.ddt_righe'), ('vendite.contratti_righe'),
                        -- lotto T, giro T.3: le testate
                        ('vendite.ordini'), ('vendite.contratti'), ('vendite.fatture'),
                        -- (le righe di fattura escono al giro finale bis, G-4: non hanno piu'
                        --  le colonne della provenienza)
                        -- lotto C, giro C.2: il link documento -> commessa
                        ('vendite.commesse_sorgenti'),
                        -- lotto C, giro C.3: la riga di commessa
                        ('vendite.commesse_attivita'),
                        -- lotto P, giro P.1: il link documento -> pratica e il log del reconcile
                        ('pratiche.pratiche_sorgenti'), ('pratiche.reconcile_errori'),
                        -- lotto M, giro M.2: le testate di magazzino e l'evento
                        ('magazzino.inventari'), ('magazzino.rettifiche'),
                        ('magazzino.trasferimenti'), ('magazzino.eventi_assets');

CREATE TEMP TABLE _ix (indice text PRIMARY KEY);
INSERT INTO _ix VALUES
  ('vendite.ix_ddt_v_sorgente_id'), ('vendite.ix_resi_sorgente_id'),
  ('vendite.ix_preventivi_righe_sorgente_uid'), ('vendite.ix_preventivi_righe_sorgente_riga'),
  ('vendite.ix_ordini_righe_sorgente_uid'), ('vendite.ix_ordini_righe_sorgente_riga'),
  ('vendite.ix_ddt_righe_sorgente_id'), ('vendite.ix_ddt_righe_sorgente_riga'),
  ('vendite.ix_contratti_righe_sorgente_uid'), ('vendite.ix_contratti_righe_sorgente_riga'),
  -- lotto T, giro T.3
  ('vendite.ix_ordini_v_sorgente_uid'), ('vendite.ix_ordini_v_sorgente_id'),
  ('vendite.ix_contratti_sorgente_uid'), ('vendite.ix_contratti_sorgente_id'),
  ('vendite.ix_fatture_v_sorgente_uid'), ('vendite.ix_fatture_v_sorgente_id'),
  ('vendite.uq_ordini_v_sorgente_offerta'), ('vendite.uq_contratti_sorgente_offerta'),
  -- (i tre indici della provenienza delle righe di fattura, del giro C.1, escono con le
  --  colonne al giro finale bis, G-4)
  -- lotto C, giro C.2 (l'unicita' porta il COMMENT sul vincolo, non sull'indice)
  ('vendite.ix_commesse_sorgenti_sorgente_uid'), ('vendite.ix_commesse_sorgenti_sorgente_riga'),
  -- lotto C, giro C.3
  ('vendite.ix_commesse_attivita_sorgente_id'), ('vendite.ix_commesse_attivita_sorgente_uid'),
  ('vendite.ix_commesse_attivita_sorgente_riga'),
  -- lotto P, giro P.1 (l'unicita' porta il COMMENT sul vincolo, non sull'indice)
  ('pratiche.ix_pratiche_sorgenti_sorgente_id'), ('pratiche.ix_pratiche_sorgenti_sorgente_uid'),
  ('pratiche.ix_pratiche_sorgenti_sorgente_riga'), ('pratiche.ix_reconcile_errori_sorgente'),
  -- lotto M, giro M.2
  ('magazzino.ix_mag_inventari_sorgente_id'), ('magazzino.ix_mag_inventari_sorgente_uid'),
  ('magazzino.ix_mag_inventari_sorgente_riga'),
  ('magazzino.ix_mag_rettifiche_sorgente_id'), ('magazzino.ix_mag_rettifiche_sorgente_uid'),
  ('magazzino.ix_mag_rettifiche_sorgente_riga'),
  ('magazzino.ix_mag_trasferimenti_sorgente_id'), ('magazzino.ix_mag_trasferimenti_sorgente_uid'),
  ('magazzino.ix_mag_trasferimenti_sorgente_riga'),
  ('magazzino.ix_mag_eventi_assets_sorgente_id'), ('magazzino.ix_mag_eventi_assets_sorgente_uid'),
  ('magazzino.ix_mag_eventi_assets_sorgente_riga'),
  -- giro finale
  ('vendite.uq_attivita_fatturabili_commessa_attivita');

-- giro finale: le viste della provenienza e le colonne nominate una per una
CREATE TEMP TABLE _vw (vista text PRIMARY KEY);
INSERT INTO _vw VALUES
  ('vendite.vw_documento_lineage_archi'), ('vendite.vw_documento_lineage_nodi'),
  ('vendite.vw_stato_sorgente_ddt'), ('vendite.vw_stato_sorgente_reso'),
  ('vendite.vw_stato_sorgente_preventivo'), ('vendite.vw_stato_sorgente_offerta'),
  ('vendite.vw_stato_sorgente_ordine'), ('vendite.vw_stato_sorgente_contratto'),
  ('vendite.vw_contratti_lista'),
  ('script.vw_stato_sorgente'), ('script.vw_stati_doc_reso_merce_rientrata'),
  ('script.vw_giornale_entita'),
  ('dbops.vw_ddt_emessi_senza_scarico'), ('dbops.vw_resi_confermati_senza_carico');

CREATE TEMP TABLE _col (tabella text, colonna text, PRIMARY KEY (tabella, colonna));
INSERT INTO _col VALUES
  ('config.sorgenti', 'scope'), ('config.sorgenti', 'apribile'),
  ('vendite.attivita_fatturabili', 'commessa_attivita_id'),
  ('vendite.attivita_fatturabili', 'commessa_id');

SELECT is(
  (SELECT count(*)::int FROM _fn WHERE to_regprocedure(firma) IS NULL)
  + (SELECT count(*)::int FROM _tab WHERE to_regclass(tabella) IS NULL)
  + (SELECT count(*)::int FROM _ix WHERE to_regclass(indice) IS NULL)
  + (SELECT count(*)::int FROM _vw WHERE to_regclass(vista) IS NULL)
  + (SELECT count(*)::int FROM _col c WHERE NOT EXISTS (
       SELECT 1 FROM pg_attribute a WHERE a.attrelid = to_regclass(c.tabella)
          AND a.attname = c.colonna AND NOT a.attisdropped)),
  0,
  '1) le funzioni, le tabelle, gli indici, le viste e le colonne dell''elenco esistono tutti');

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
  '3) i COMMENT delle colonne sorgente_* delle righe e delle testate (di vendita, di magazzino) descrivono al presente');

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

SELECT is(
  (SELECT coalesce(string_agg(v.vista, ', ' ORDER BY v.vista), '')
     FROM _vw v, _marcatore m
    WHERE coalesce(obj_description(to_regclass(v.vista), 'pg_class'), '') ~* m.re
       OR obj_description(to_regclass(v.vista), 'pg_class') IS NULL),
  '',
  '6) i COMMENT delle viste della provenienza descrivono al presente');

SELECT is(
  (SELECT coalesce(string_agg(c.tabella || '.' || c.colonna, ', ' ORDER BY 1), '')
     FROM _col c
     JOIN pg_attribute a ON a.attrelid = to_regclass(c.tabella) AND a.attname = c.colonna
                        AND NOT a.attisdropped,
          _marcatore m
    WHERE coalesce(col_description(a.attrelid, a.attnum), '') ~* m.re
       OR col_description(a.attrelid, a.attnum) IS NULL),
  '',
  '7) i COMMENT delle colonne nominate descrivono al presente');

SELECT * FROM finish();
ROLLBACK;
