-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il kit sul listino e la periodicita' (brief-db-contratto-righe-periodiche-
--       in-commessa §7.7, lotti L11 … L16; decisioni di Tid del 2026-10-31:
--       D-2 (c), D-2-bis (B), D-3 (b); difetti D-6, D-7).
--       changeSet 20261031-29 … -43, seed tabelle_gestibili (riga 93).
--
-- ⭐ TUTTO COSTRUITO. Un listino di quota fissa con una quota semplice (Q,
--   mensile) e un kit (K = 2 x F1 + 1 x F2, prezzi 10 e 30: il kit vale 50,
--   trimestrale in vendite.listini_kit). Due contratti dal 2026-02-15: C1 prende
--   le quote fisse dal listino, C2 aderisce al kit. Giro di ottobre 2026
--   (p_competenza_mese): i numeri si leggono a mano.
--
-- Indice test (1..20):
--  Struttura
--    1) vendite.listini_kit ha la RLS accesa e la sua policy
--    2) config.periodicita e' nel lookup e non nel pannello (D-6)
--  La sede della periodicita' (vendite.fn_listino_periodicita_articolo)
--    3) il kit dalla sua riga in listini_kit, la quota dalla riga di listino
--  Il guard del kit sul listino
--    4) ⛔ un articolo semplice: E_LISTINO_KIT_NON_COMPOSITO
--  L'attivazione (D-3, script.fn_check_versione_listino_attivabile)
--    5) ⛔ la quota senza periodicita': motivo QUOTA_FISSA_SENZA_PERIODICITA su Q
--    6) ⛔ il kit senza la sua riga in listini_kit: lo stesso motivo, su K
--    7) tutto a posto: nessun motivo
--    8) ⛔ fuori dalla bozza il kit non si tocca: E_RIGA_LISTINO_VERSIONE_CHIUSA
--  La quota fissa non perde la periodicita' fuori dalla bozza (20261031-51/-52)
--   9) ⛔ toglierla su una versione ATTIVA: E_LISTINO_QUOTA_FISSA_PERIODICITA_FERMA
--  10) cambiarla con un'altra resta una rettifica: passa
--  Clona ed elimina
--  11) la versione clonata porta la periodicita' delle righe e il kit
--  12) la clonata, in bozza, si elimina coi suoi kit (eliminabile non li conta)
--  I componenti del kit dal listino (D-2)
--  13) due componenti, coefficiente e prezzo del listino, unita' del componente
--  Il lister (vendite.fn_contratti_addebiti_maturati)
--  14) C1: la quota fissa del KIT si addebita: 4 pezzi trimestrali a 50, senza riga
--  15) C2: l'ADESIONE sul kit eredita la periodicita' da listini_kit (L4b)
--  16) C2: e si addebita a 50, la somma dei componenti (prima: SENZA_PREZZO)
--  L'anteprima delle righe (D-7)
--  17) C1: periodicita' del listino sulle righe DA_LISTINO, kit compreso; nessuna generazione
--  18) C2: sull'ADESIONE la periodicita' e la generazione scritte sulla riga
--  19) il lettore delle eccezioni le porta (vendite.fn_documento_righe_eccezione)
--  La quota fissa che non si eroga a canone (§7.3)
--  20) il default della tipologia cambia dopo l'attivazione: C1 non perde le
--      quote in silenzio, escono con lo scarto QUOTA_FISSA_SENZA_CANONE
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(20);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.tip(p text) RETURNS smallint LANGUAGE sql STABLE AS
$fx$ SELECT t.id FROM config.listini_tipologie t WHERE t.codice = p $fx$;

-- Scopo: il prefisso fisso del messaggio di un codice, per throws_like.
CREATE OR REPLACE FUNCTION pg_temp.msg(p_codice text)
RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT split_part(m.messaggio, '%s', 1) || '%' FROM config.messaggi_errore m
   WHERE m.codice = p_codice AND m.lingua = 'it'
$fx$;

CREATE TEMP TABLE tmp_lk_mondo AS
SELECT v.k, m.*
  FROM (VALUES ('C1'), ('C2')) v(k),
       LATERAL dbops.fn_pgtap_crea_mondo_cliente('listino kit ' || v.k) m;

CREATE TEMP TABLE tmp_lk_lst AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
  SELECT 'PGTAP_LK_' || substr(md5(clock_timestamp()::text || random()::text), 1, 10),
         'Fixture pgTAP: kit sul listino',
         (SELECT utility_id FROM tmp_lk_mondo WHERE k = 'C1'),
         pg_temp.tip('QUOTA_FISSA'), script.fn_pgtap_emittente_sr_operatore()
  RETURNING id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_lk_ver AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
  SELECT id, 'PGTAP_V1', date '2026-01-01' FROM tmp_lk_lst
  RETURNING id)
SELECT * FROM ins;

CREATE OR REPLACE FUNCTION pg_temp.ver() RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_lk_ver $fx$;

-- Q quota semplice; K kit di F1 e F2. Tutti di quota fissa.
CREATE TEMP TABLE tmp_lk_art AS
SELECT v.s, dbops.fn_pgtap_crea_articolo('PGTAP-LK-' || v.s,
         p_listino_tipologia_id => pg_temp.tip('QUOTA_FISSA'),
         p_is_composito         => v.s = 'K') AS id
  FROM (VALUES ('Q'), ('K'), ('F1'), ('F2')) v(s);

CREATE OR REPLACE FUNCTION pg_temp.art(p text) RETURNS uuid LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_lk_art WHERE s = p $fx$;

INSERT INTO catalogo.articoli_componenti (prodotto_id, componente_id, coeff_qta, valido_dal)
VALUES (pg_temp.art('K'), pg_temp.art('F1'), 2, '2020-01-01'),
       (pg_temp.art('K'), pg_temp.art('F2'), 1, '2020-01-01');

DO $fx$ BEGIN
  PERFORM dbops.fn_pgtap_listino_aggiungi_articoli(pg_temp.ver(), ARRAY[pg_temp.art('Q')], 100);
END $fx$;
UPDATE vendite.listini_righe SET periodicita = 'MENSILE'
 WHERE listino_versione_id = pg_temp.ver() AND articolo_id = pg_temp.art('Q');

-- Il kit sul listino: i prezzi dei componenti, e la sua periodicita'.
INSERT INTO vendite.listini_righe_componenti (listino_versione_id, articolo_componente_id,
       articolo_padre_id, articolo_figlio_id, prezzo, valido_dal)
SELECT pg_temp.ver(), ac.id, ac.prodotto_id, ac.componente_id,
       CASE WHEN ac.componente_id = pg_temp.art('F1') THEN 10 ELSE 30 END, date '2026-01-01'
  FROM catalogo.articoli_componenti ac
 WHERE ac.prodotto_id = pg_temp.art('K');
INSERT INTO vendite.listini_kit (listino_versione_id, articolo_padre_id, periodicita)
VALUES (pg_temp.ver(), pg_temp.art('K'), 'TRIMESTRALE');

-- ============================================================
-- Struttura
-- ============================================================
SELECT ok(
  (SELECT c.relrowsecurity FROM pg_class c WHERE c.oid = 'vendite.listini_kit'::regclass)
  AND EXISTS (SELECT 1 FROM pg_policy p
               WHERE p.polrelid = 'vendite.listini_kit'::regclass
                 AND p.polname = 'rls_listini_kit_ef_whitelist'),
  '1) vendite.listini_kit: RLS accesa e policy rls_listini_kit_ef_whitelist');

SELECT is(
  -- ⚠️ format() di un boolean scrive t/f: il cast a text scrive true/false.
  (SELECT format('%s|%s', g.lookup::text, g.pannello::text) FROM config.tabelle_gestibili g
    WHERE g.codice_interno = 'config.periodicita'),
  'true|false',
  '2) config.periodicita e'' nel lookup e non nel pannello (D-6)');

-- ============================================================
-- La sede della periodicita'
-- ============================================================
SELECT is(
  vendite.fn_listino_periodicita_articolo(pg_temp.ver(), pg_temp.art('K')) || '|'
  || vendite.fn_listino_periodicita_articolo(pg_temp.ver(), pg_temp.art('Q')),
  'TRIMESTRALE|MENSILE',
  '3) la periodicita'' del kit da listini_kit, della quota dalla riga di listino');

-- ============================================================
-- Il guard del kit sul listino
-- ============================================================
SELECT throws_like(
  format($$INSERT INTO vendite.listini_kit (listino_versione_id, articolo_padre_id, periodicita)
           VALUES (%s, %L, 'MENSILE')$$, pg_temp.ver(), pg_temp.art('Q')),
  pg_temp.msg('E_LISTINO_KIT_NON_COMPOSITO'),
  '4) un articolo semplice non ha un kit sul listino: E_LISTINO_KIT_NON_COMPOSITO');

-- ============================================================
-- L'attivazione (D-3)
-- ============================================================
UPDATE vendite.listini_righe SET periodicita = NULL
 WHERE listino_versione_id = pg_temp.ver() AND articolo_id = pg_temp.art('Q');
SELECT is(
  (SELECT m ->> 'reason' || '|' || (m -> 'dettaglio' ->> 'articolo_id')
     FROM jsonb_array_elements(script.fn_check_versione_listino_attivabile(pg_temp.ver())) m
    WHERE m ->> 'codice' = 'E_LISTINO_VERSIONE_QUOTA_FISSA_SENZA_PERIODICITA'),
  'QUOTA_FISSA_SENZA_PERIODICITA|' || pg_temp.art('Q')::text,
  '5) la quota fissa senza periodicita'': la versione non si attiva (motivo su Q)');
UPDATE vendite.listini_righe SET periodicita = 'MENSILE'
 WHERE listino_versione_id = pg_temp.ver() AND articolo_id = pg_temp.art('Q');

DELETE FROM vendite.listini_kit WHERE listino_versione_id = pg_temp.ver();
SELECT is(
  (SELECT m ->> 'reason' || '|' || (m -> 'dettaglio' ->> 'articolo_id')
     FROM jsonb_array_elements(script.fn_check_versione_listino_attivabile(pg_temp.ver())) m
    WHERE m ->> 'codice' = 'E_LISTINO_VERSIONE_QUOTA_FISSA_SENZA_PERIODICITA'),
  'QUOTA_FISSA_SENZA_PERIODICITA|' || pg_temp.art('K')::text,
  '6) il kit di quota fissa senza la sua riga in listini_kit: la versione non si attiva (motivo su K)');
INSERT INTO vendite.listini_kit (listino_versione_id, articolo_padre_id, periodicita)
VALUES (pg_temp.ver(), pg_temp.art('K'), 'TRIMESTRALE');

SELECT is(script.fn_check_versione_listino_attivabile(pg_temp.ver()), '[]'::jsonb,
  '7) quota e kit con la periodicita'': la versione si attiva');

DO $fx$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni'::regclass, pg_temp.ver(), 'ATTIVA');
END $fx$;

SELECT throws_like(
  format($$UPDATE vendite.listini_kit SET periodicita = 'MENSILE' WHERE listino_versione_id = %s$$,
         pg_temp.ver()),
  pg_temp.msg('E_RIGA_LISTINO_VERSIONE_CHIUSA'),
  '8) fuori dalla bozza la periodicita'' del kit non si cambia: E_RIGA_LISTINO_VERSIONE_CHIUSA');

SELECT throws_like(
  format($$UPDATE vendite.listini_righe SET periodicita = NULL
            WHERE listino_versione_id = %s AND articolo_id = %L$$, pg_temp.ver(), pg_temp.art('Q')),
  pg_temp.msg('E_LISTINO_QUOTA_FISSA_PERIODICITA_FERMA'),
  '9) su una versione ATTIVA la quota fissa non resta senza periodicita''');

UPDATE vendite.listini_righe SET periodicita = 'TRIMESTRALE'
 WHERE listino_versione_id = pg_temp.ver() AND articolo_id = pg_temp.art('Q');
SELECT is(
  vendite.fn_listino_periodicita_articolo(pg_temp.ver(), pg_temp.art('Q')),
  'TRIMESTRALE',
  '10) cambiarla con un''altra resta una rettifica, come il prezzo');
UPDATE vendite.listini_righe SET periodicita = 'MENSILE'
 WHERE listino_versione_id = pg_temp.ver() AND articolo_id = pg_temp.art('Q');

-- ============================================================
-- Clona ed elimina
-- ============================================================
CREATE TEMP TABLE tmp_lk_clone AS
SELECT * FROM vendite.fn_clona_versione_listino(pg_temp.ver(), 'PGTAP_V2', date '2027-01-01', NULL);

SELECT is(
  (SELECT lr.periodicita FROM vendite.listini_righe lr
    WHERE lr.listino_versione_id = (SELECT versione_id FROM tmp_lk_clone)
      AND lr.articolo_id = pg_temp.art('Q'))
  || '|' ||
  (SELECT k.periodicita FROM vendite.listini_kit k
    WHERE k.listino_versione_id = (SELECT versione_id FROM tmp_lk_clone)
      AND k.articolo_padre_id = pg_temp.art('K')),
  'MENSILE|TRIMESTRALE',
  '11) la versione clonata porta la periodicita'' della riga (persa prima del -38) e il kit');

CREATE TEMP TABLE tmp_lk_elim AS
SELECT * FROM vendite.fn_elimina_versione_listino((SELECT versione_id FROM tmp_lk_clone));

SELECT ok(
  (SELECT righe_eliminate = 1 FROM tmp_lk_elim)
  AND NOT EXISTS (SELECT 1 FROM vendite.listini_kit k
                   WHERE k.listino_versione_id = (SELECT versione_id FROM tmp_lk_clone))
  AND NOT EXISTS (SELECT 1 FROM vendite.listini_versioni lv
                   WHERE lv.id = (SELECT versione_id FROM tmp_lk_clone)),
  '12) la clonata in bozza si elimina coi suoi kit: il kit non la trattiene');

-- ============================================================
-- I contratti
-- ============================================================
CREATE TEMP TABLE tmp_lk_ctr AS
SELECT m.k, (SELECT x.contratto_id
               FROM dbops.fn_pgtap_crea_contratto(
                      'listino kit ' || m.k, 'DRAFT', m.billing_account_id, NULL,
                      date '2026-02-15', NULL, NULL, (SELECT id FROM tmp_lk_lst)) x) AS id
  FROM tmp_lk_mondo m;

CREATE OR REPLACE FUNCTION pg_temp.ctr(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_lk_ctr WHERE k = p $fx$;

-- C2 aderisce al kit, senza dire la periodicita': la eredita (L4b). La
-- generazione e' scritta sulla riga (la stessa della testata: i pezzi non
-- cambiano), cosi' l'anteprima ha un valore scritto da dire.
INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione,
       tipo_erogazione, fonte_quantita_attesa, qta_operativa, quantita, generazione_canone)
VALUES (pg_temp.ctr('C2'), pg_temp.art('K'), 'ADESIONE', 'CANONE', 'FISSA', 1, 1, 'INIZIO_PERIODO');

DO $fx$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, id, 'ATTIVO') FROM tmp_lk_ctr;
END $fx$;

-- ============================================================
-- I componenti del kit dal listino (D-2)
-- ============================================================
SELECT is(
  (SELECT string_agg(format('%s:%s:%s:%s',
                            CASE k.componente_id WHEN pg_temp.art('F1') THEN 'F1' ELSE 'F2' END,
                            k.coeff_qta_snapshot::numeric(18,2), k.prezzo_unitario::numeric(18,2),
                            (k.uom_operativa_id = a.uom_id)::text),
                     ' ' ORDER BY k.coeff_qta_snapshot DESC)
     FROM vendite.fn_contratto_kit_componenti(pg_temp.ctr('C1'), pg_temp.art('K'), date '2026-03-01') k
     JOIN catalogo.articoli a ON a.id = k.componente_id),
  'F1:2.00:10.00:true F2:1.00:30.00:true',
  '13) i componenti del kit dal listino del contratto: coefficiente, prezzo del listino, unita'' del componente');

-- ============================================================
-- Il lister
-- ============================================================
CREATE TEMP TABLE tmp_lk_ott AS
SELECT c.k, a.s, to_jsonb(l) AS v
  FROM tmp_lk_ctr c
 CROSS JOIN LATERAL vendite.fn_contratti_addebiti_maturati(
         p_competenza_mese => date '2026-10-01', p_contratto_id => c.id) l
  LEFT JOIN tmp_lk_art a ON a.id = l.articolo_id;

-- Scopo: i pezzi di un articolo per un contratto, come testo «dal..al:quantita'@prezzo».
CREATE OR REPLACE FUNCTION pg_temp.pezzi(p_k text, p_s text) RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT string_agg((o.v ->> 'competenza_dal') || '..' || (o.v ->> 'competenza_al') || ':'
                    || ((o.v ->> 'quantita')::numeric)::numeric(18,6)::text || '@'
                    || ((o.v ->> 'prezzo_snapshot')::numeric)::numeric(18,2)::text,
                    ' ' ORDER BY o.v ->> 'competenza_dal')
    FROM tmp_lk_ott o WHERE o.k = p_k AND o.s = p_s AND o.v ->> 'scarto' IS NULL;
$fx$;

SELECT ok(
  pg_temp.pezzi('C1', 'K') = '2026-02-15..2026-03-31:0.500000@50.00 2026-04-01..2026-06-30:1.000000@50.00 '
                          || '2026-07-01..2026-09-30:1.000000@50.00 2026-10-01..2026-12-31:1.000000@50.00'
  AND (SELECT bool_and(o.v ->> 'riga_id' IS NULL
                       AND o.v ->> 'segment_key' LIKE '%:A:' || pg_temp.art('K')::text || ':M:%')
         FROM tmp_lk_ott o WHERE o.k = 'C1' AND o.s = 'K'),
  '14) C1: la quota fissa del kit si addebita: 4 pezzi trimestrali a 50 (2 x 10 + 30), chiave sull''articolo');

SELECT is(
  (SELECT cr.periodicita FROM vendite.contratti_righe cr
    WHERE cr.contratto_id = pg_temp.ctr('C2') AND cr.articolo_id = pg_temp.art('K')),
  'TRIMESTRALE',
  '15) C2: l''ADESIONE sul kit eredita la periodicita'' da listini_kit');

SELECT ok(
  pg_temp.pezzi('C2', 'K') = '2026-02-15..2026-03-31:0.500000@50.00 2026-04-01..2026-06-30:1.000000@50.00 '
                          || '2026-07-01..2026-09-30:1.000000@50.00 2026-10-01..2026-12-31:1.000000@50.00'
  AND NOT EXISTS (SELECT 1 FROM tmp_lk_ott o WHERE o.k = 'C2' AND o.v ->> 'scarto' IS NOT NULL),
  '16) C2: l''ADESIONE sul kit si addebita a 50, la somma dei componenti (prima: SENZA_PREZZO)');

-- ============================================================
-- L'anteprima delle righe (D-7)
-- ============================================================
SELECT is(
  (SELECT string_agg(format('%s:%s:%s', CASE p.articolo_id WHEN pg_temp.art('K') THEN 'K' ELSE 'Q' END,
                            p.periodicita, COALESCE(p.generazione_canone, '-')),
                     ' ' ORDER BY p.articolo_codice)
     FROM vendite.fn_contratto_righe_preview(pg_temp.ctr('C1')) p
    WHERE p.origine = 'DA_LISTINO'),
  'K:TRIMESTRALE:- Q:MENSILE:-',
  '17) C1: sulle righe DA_LISTINO la periodicita'' del listino (il kit da listini_kit), nessuna generazione');

SELECT is(
  (SELECT format('%s:%s', p.periodicita, COALESCE(p.generazione_canone, '-'))
     FROM vendite.fn_contratto_righe_preview(pg_temp.ctr('C2')) p
    WHERE p.origine = 'ADESIONE'),
  'TRIMESTRALE:INIZIO_PERIODO',
  '18) C2: sull''ADESIONE la periodicita'' e la generazione scritte sulla riga (il form non le cancella)');

SELECT is(
  (SELECT format('%s:%s', e.periodicita, e.generazione_canone)
     FROM vendite.fn_documento_righe_eccezione('CONTRATTO', pg_temp.ctr('C2')) e
    WHERE e.articolo_id = pg_temp.art('K')),
  'TRIMESTRALE:INIZIO_PERIODO',
  '19) il lettore delle eccezioni porta periodicita'' e generazione della riga');

-- ============================================================
-- La quota fissa che non si eroga a canone (§7.3)
-- ============================================================
-- Il catalogo cambia DOPO l'attivazione: la tipologia QUOTA_FISSA passa a una
-- tantum di default. Il controllo all'attivazione non lo puo' vedere; il lister si'.
UPDATE config.listini_tipologie_erogazioni
   SET e_default = false
 WHERE tipologia_id = pg_temp.tip('QUOTA_FISSA') AND e_default IS TRUE;
INSERT INTO config.listini_tipologie_erogazioni (tipologia_id, tipo_erogazione, fonte_quantita_attesa, e_default)
VALUES (pg_temp.tip('QUOTA_FISSA'), 'UNA_TANTUM', 'FISSA', true);

SELECT is(
  (SELECT string_agg(CASE l.articolo_id WHEN pg_temp.art('K') THEN 'K' ELSE 'Q' END || ':' || l.scarto,
                     ' ' ORDER BY l.articolo_id = pg_temp.art('Q'))
     FROM vendite.fn_contratti_addebiti_maturati(
            p_competenza_mese => date '2026-11-01', p_contratto_id => pg_temp.ctr('C1')) l),
  'K:QUOTA_FISSA_SENZA_CANONE Q:QUOTA_FISSA_SENZA_CANONE',
  '20) la quota fissa che non si eroga piu'' a canone non sparisce: scarto QUOTA_FISSA_SENZA_CANONE');

SELECT * FROM finish();
ROLLBACK;
