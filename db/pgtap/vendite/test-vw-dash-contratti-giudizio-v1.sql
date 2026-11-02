-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-11-01 (20261101-04/-06, passo 4 del brief): una riga a canone senza periodicita'
--   non si scrive piu'. K2 la costruiva con un'ADESIONE su P che dal listino ereditava una
--   periodicita' vuota: ora il suo canone che non puo' partire e' la quota P del listino, come
--   per K4 (l'unica strada che il modello lascia: il catalogo che cambia dopo l'attivazione).
--   Nessuna attesa cambiata.
-- pgTAP test per Zero ERP
--
-- Test: la dashboard giudica di nuovo i contratti dal push
--       (vendite.vw_dash_fatturazione_contratti, changeSet 20261031-04, sulla
--       sede vendite.fn_contratti_addebiti_maturati del 20261031-02; motivi in
--       config.motivi_fermo, seed 20260706-02). Brief:
--       brief-db-contratto-righe-periodiche-in-commessa §6.13 (Lotto 8).
--       Decisioni di Tid: F-12, F-13 (2026-10-30), F-14, F-15 (2026-10-31).
--
-- ⭐ TUTTO COSTRUITO. Un listino QUOTA_FISSA: O mensile, P SENZA periodicita'.
--   Contratti dal primo del mese in corso (il canone mensile anticipato e'
--   maturato oggi, qualunque sia il giorno): la vista giudica al giro di oggi.
--   L'invio come l'orchestratore, nella commessa del contratto senza periodo
--   (G-6), come in test-push-contratto-canoni-v1.
--
-- Indice test (1..11):
--   1) K1 (OVERRIDE su O, da mandare): fermo, CANONE_NON_GENERATO
--   2) K1 nel Backlog: RECUPERABILE, «Esegui il push dei canoni»
--   3) K1 «fermo da»: l'addebito piu' vecchio che aspetta (il primo del mese)
--   4) K1 nella situazione aperta
--   5) K1 mandato il giro: transitato, nessun motivo
--   6) K1 mandato: esce dalla situazione aperta e dal Backlog
--   7) K2 (OVERRIDE su O da mandare, e la quota P del listino senza
--      periodicita'): vince CANONE_NON_GENERABILE
--   8) K2 nel Backlog: ANOMALIA, «Rivedi il contratto»
--   9) K2 mandato quello che si puo': resta CANONE_NON_GENERABILE
--  10) K3 in bozza: sospeso (is_transitato e motivo NULL), resta nella
--      situazione aperta
--  11) K4 (OVERRIDE su O, nessuna riga su P): la quota P del listino senza
--      periodicita' non puo' partire: CANONE_NON_GENERABILE
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(11);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_dg_mondo AS
SELECT v.k, m.*
  FROM (VALUES ('K1'), ('K2'), ('K3'), ('K4')) v(k),
       LATERAL dbops.fn_pgtap_crea_mondo_cliente('dash giudizio contratti ' || v.k) m;

CREATE TEMP TABLE tmp_dg_lst AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
  SELECT 'PGTAP_DG_' || substr(md5(clock_timestamp()::text || random()::text), 1, 10),
         'Fixture pgTAP: dash giudizio contratti',
         (SELECT utility_id FROM tmp_dg_mondo WHERE k = 'K1'),
         (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA'),
         script.fn_pgtap_emittente_sr_operatore()
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_dg_ver AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
  SELECT id, 'PGTAP_V1', date '2026-01-01' FROM tmp_dg_lst
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_dg_art AS
SELECT v.s, dbops.fn_pgtap_crea_articolo('PGTAP-DG-' || v.s,
         p_listino_tipologia_id => (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA')) AS id
  FROM (VALUES ('O'), ('P')) v(s);

CREATE OR REPLACE FUNCTION pg_temp.art(p text) RETURNS uuid LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_dg_art WHERE s = p $fx$;

DO $fx$ BEGIN
  PERFORM dbops.fn_pgtap_listino_aggiungi_articoli((SELECT id FROM tmp_dg_ver),
    ARRAY[pg_temp.art('O'), pg_temp.art('P')], 100);
END $fx$;

-- O mensile; P senza periodicita' (la sua quota non puo' partire).
-- ⚠️ rev 2026-10-31 (20261031-39 e -51/-52): con una quota fissa a canone senza
--   periodicita' la versione non si attiva, e fuori dalla bozza la quota non la
--   perde. Il caso che la dashboard segnala nasce ancora da una strada sola: il
--   catalogo che cambia dopo l'attivazione. La fixture la costruisce cosi'
--   (brief-db-contratto-righe-periodiche-in-commessa §7.10).
UPDATE vendite.listini_righe
   SET periodicita = 'MENSILE'
 WHERE listino_versione_id = (SELECT id FROM tmp_dg_ver) AND articolo_id = pg_temp.art('O');

-- La tipologia QUOTA_FISSA, nella transazione, non si eroga a canone: in bozza
-- la quota senza periodicita' non e' «a canone», e la versione si attiva.
UPDATE config.listini_tipologie_erogazioni SET e_default = false
 WHERE tipologia_id = (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA')
   AND e_default IS TRUE;
INSERT INTO config.listini_tipologie_erogazioni (tipologia_id, tipo_erogazione, fonte_quantita_attesa, e_default)
SELECT t.id, 'UNA_TANTUM', 'FISSA', true FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA';

DO $fx$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni'::regclass, v.id, 'ATTIVA')
     FROM tmp_dg_ver v;
END $fx$;

-- Poi il catalogo torna com'era: la quota e' di nuovo un canone, senza periodicita'.
DELETE FROM config.listini_tipologie_erogazioni
 WHERE tipologia_id = (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA')
   AND tipo_erogazione = 'UNA_TANTUM' AND e_default IS TRUE;
UPDATE config.listini_tipologie_erogazioni SET e_default = true
 WHERE tipologia_id = (SELECT t.id FROM config.listini_tipologie t WHERE t.codice = 'QUOTA_FISSA')
   AND tipo_erogazione = 'CANONE' AND fonte_quantita_attesa = 'FISSA';

CREATE TEMP TABLE tmp_dg_ctr AS
SELECT m.k, (SELECT x.contratto_id
               FROM dbops.fn_pgtap_crea_contratto(
                      'dash giudizio contratti ' || m.k, 'DRAFT', m.billing_account_id, NULL,
                      date_trunc('month', script.fn_data_operativa())::date, NULL, NULL,
                      (SELECT id FROM tmp_dg_lst)) x) AS id
  FROM tmp_dg_mondo m;

CREATE OR REPLACE FUNCTION pg_temp.ctr(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_dg_ctr WHERE k = p $fx$;

-- L'OVERRIDE prende il posto della quota O. K1 e K3 escludono P; K2 e K4 non la
-- toccano, e la quota P del listino resta senza periodicita'.
INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
       tipo_erogazione, fonte_quantita_attesa, qta_operativa, quantita, periodicita)
VALUES (pg_temp.ctr('K1'), pg_temp.art('O'), 'OVERRIDE', 80,   'CANONE', 'FISSA', 1, 1, 'MENSILE'),
       (pg_temp.ctr('K2'), pg_temp.art('O'), 'OVERRIDE', 80,   'CANONE', 'FISSA', 1, 1, 'MENSILE'),
       (pg_temp.ctr('K3'), pg_temp.art('O'), 'OVERRIDE', 80,   'CANONE', 'FISSA', 1, 1, 'MENSILE'),
       (pg_temp.ctr('K4'), pg_temp.art('O'), 'OVERRIDE', 80,   'CANONE', 'FISSA', 1, 1, 'MENSILE');
INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione)
VALUES (pg_temp.ctr('K1'), pg_temp.art('P'), 'ESCLUSIONE'),
       (pg_temp.ctr('K3'), pg_temp.art('P'), 'ESCLUSIONE');

DO $fx$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, id, 'ATTIVO')
     FROM tmp_dg_ctr WHERE k IN ('K1', 'K2', 'K4');
END $fx$;

-- Scopo: l'invio di una riga del lister dalla madre, nella commessa del
--   contratto senza periodo (G-6).
CREATE OR REPLACE FUNCTION pg_temp.invia(v jsonb) RETURNS bigint LANGUAGE sql AS $fx$
  SELECT u.attivita_id
    FROM vendite.fn_upsert_commessa_attivita(
      p_commessa_id => vendite.fn_get_or_create_commessa(
         p_billing_account_id => (v ->> 'billing_account_id')::bigint,
         p_utility_id => (v ->> 'utility_id')::integer,
         p_tipo_commessa => 'AUTO', p_policy_fatturazione => 'DA_DOCUMENTO',
         p_fatturazione_immediata => (v ->> 'fatturazione_immediata')::boolean,
         p_priorita_operativa => 'NORMALE', p_competenza_dal => NULL, p_competenza_al => NULL,
         p_meta => '{}'::jsonb, p_force_new => false),
      p_segment_key => (v ->> 'segment_key')::varchar,
      p_articolo_id => (v ->> 'articolo_id')::uuid,
      p_istanza_utility_id => (v ->> 'istanza_utility_id')::bigint,
      p_data_attivita => (v ->> 'data_attivita')::date,
      p_uom_id => (v ->> 'uom_id')::bigint,
      p_quantita => (v ->> 'quantita')::numeric,
      p_competenza_mese => (v ->> 'competenza_mese')::date,
      p_competenza_dal => (v ->> 'competenza_dal')::date,
      p_competenza_al => (v ->> 'competenza_al')::date,
      p_prezzo_snapshot => (v ->> 'prezzo_snapshot')::numeric,
      p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
      p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
      p_promo_id => NULL, p_contratto_id => NULL,
      p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
      p_qta_operativa => (v ->> 'qta_operativa')::numeric,
      p_uom_operativa_id => (v ->> 'uom_operativa_id')::bigint,
      p_factor_to_base => (v ->> 'factor_to_base')::numeric,
      p_tipo_doc_fiscale_id => (v ->> 'tipo_doc_fiscale_id')::bigint,
      p_prezzo_bloccato => (v ->> 'prezzo_bloccato')::boolean,
      p_pricing_mode => (v ->> 'pricing_mode')::varchar,
      p_sorgente_tipo_id => (v ->> 'sorgente_tipo_id')::bigint,
      p_sorgente_uid => v ->> 'sorgente_uid',
      p_tipo_movimento => (v ->> 'tipo_movimento')::varchar,
      p_meta => COALESCE(v -> 'meta', '{}'::jsonb)) u
$fx$;

-- Scopo: la riga della vista per un contratto.
CREATE OR REPLACE FUNCTION pg_temp.dash(p text) RETURNS vendite.vw_dash_fatturazione_contratti
LANGUAGE sql STABLE AS
$fx$ SELECT d FROM vendite.vw_dash_fatturazione_contratti d WHERE d.documento_id = pg_temp.ctr(p) $fx$;

-- Scopo: la riga del Backlog per un contratto (NULL se non c'e').
CREATE OR REPLACE FUNCTION pg_temp.backlog(p text) RETURNS text LANGUAGE sql STABLE AS
$fx$ SELECT b.motivo_fermo || '/' || b.classe || '/' || b.azione
       FROM vendite.vw_dash_backlog_documenti b
      WHERE b.area = 'CONTRATTO' AND b.documento_id = pg_temp.ctr(p) $fx$;

-- Scopo: il contratto e' nella situazione aperta.
CREATE OR REPLACE FUNCTION pg_temp.aperto(p text) RETURNS boolean LANGUAGE sql STABLE AS
$fx$ SELECT EXISTS (SELECT 1 FROM vendite.vw_dash_aperto_documenti a
                     WHERE a.area = 'CONTRATTO' AND a.documento_id = pg_temp.ctr(p)) $fx$;

-- ============================================================
-- K1 — da mandare, poi mandato
-- ============================================================
SELECT ok(
  (pg_temp.dash('K1')).is_transitato IS FALSE
  AND (pg_temp.dash('K1')).unita_transitate = 0
  AND (pg_temp.dash('K1')).motivo_fermo = 'CANONE_NON_GENERATO',
  '1) K1, un canone maturato non in commessa: fermo, CANONE_NON_GENERATO');

SELECT is(
  pg_temp.backlog('K1'),
  'CANONE_NON_GENERATO/RECUPERABILE/Esegui il push dei canoni',
  '2) K1 nel Backlog: RECUPERABILE, «Esegui il push dei canoni» (F-13)');

SELECT is(
  (pg_temp.dash('K1')).data_riferimento,
  date_trunc('month', script.fn_data_operativa())::date,
  '3) K1 «fermo da»: l''addebito piu'' vecchio che aspetta, il primo del mese');

SELECT ok(pg_temp.aperto('K1'), '4) K1 fermo: e'' nella situazione aperta');

SELECT count(pg_temp.invia(to_jsonb(l)))
  FROM vendite.fn_list_contratti_da_pushare(p_contratto_id => pg_temp.ctr('K1')) l;

SELECT ok(
  (pg_temp.dash('K1')).is_transitato IS TRUE
  AND (pg_temp.dash('K1')).unita_transitate = 1
  AND (pg_temp.dash('K1')).motivo_fermo IS NULL
  AND (pg_temp.dash('K1')).data_riferimento = date_trunc('month', script.fn_data_operativa())::date,
  '5) K1 mandato il giro: transitato, nessun motivo, data di riferimento = inizio del contratto');

SELECT ok(
  NOT pg_temp.aperto('K1') AND pg_temp.backlog('K1') IS NULL,
  '6) K1 mandato: esce dalla situazione aperta e dal Backlog');

-- ============================================================
-- K2 — una riga che non puo' partire
-- ============================================================
SELECT ok(
  (pg_temp.dash('K2')).is_transitato IS FALSE
  AND (pg_temp.dash('K2')).motivo_fermo = 'CANONE_NON_GENERABILE',
  '7) K2, un canone da mandare e uno senza periodicita'': vince CANONE_NON_GENERABILE (F-14)');

SELECT is(
  pg_temp.backlog('K2'),
  'CANONE_NON_GENERABILE/ANOMALIA/Rivedi il contratto',
  '8) K2 nel Backlog: ANOMALIA, «Rivedi il contratto» (F-15)');

SELECT count(pg_temp.invia(to_jsonb(l)))
  FROM vendite.fn_list_contratti_da_pushare(p_contratto_id => pg_temp.ctr('K2')) l;

SELECT ok(
  (pg_temp.dash('K2')).motivo_fermo = 'CANONE_NON_GENERABILE'
  AND (SELECT count(*) = 0 FROM vendite.fn_list_contratti_da_pushare(p_contratto_id => pg_temp.ctr('K2'))),
  '9) K2 mandato quello che si puo'': il push non chiude la riga scartata, resta CANONE_NON_GENERABILE');

-- ============================================================
-- K3 — in bozza
-- ============================================================
SELECT ok(
  (pg_temp.dash('K3')).is_transitato IS NULL
  AND (pg_temp.dash('K3')).unita_transitate IS NULL
  AND (pg_temp.dash('K3')).motivo_fermo IS NULL
  AND pg_temp.aperto('K3'),
  '10) K3 in bozza: giudizio sospeso, resta nella situazione aperta');

-- ============================================================
-- K4 — la quota del listino che non puo' partire
-- ============================================================
SELECT is(
  (pg_temp.dash('K4')).motivo_fermo::text,
  'CANONE_NON_GENERABILE',
  '11) K4, nessuna riga su P: la quota P del listino senza periodicita'' non puo'' partire');

SELECT * FROM finish();
ROLLBACK;
