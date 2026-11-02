-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il lister dei contratti manda in commessa i canoni a periodi, e gli
--       storni della parte non goduta (vendite.fn_list_contratti_da_pushare,
--       changeSet 20261030-01 e 20261031-01, brief-db-contratto-righe-
--       periodiche-in-commessa §6.12 e §6.13). Decisioni di Tid: G-0, G-0-ter,
--       G-2, G-5, G-9 (2026-10-28), F-1, F-2, F-6, F-7 (2026-10-29), F-11
--       (2026-10-30).
-- rev 2026-10-31 (20261031-01): parte C, la fine che si sposta dopo il primo
--   storno (test 13-15).
--
-- ⭐ TUTTO COSTRUITO. Due listini (QUOTA_FISSA e SERVIZI: la coppia utility /
--   SERVIZI si ammette nella transazione), articoli dal builder, contratti in
--   DRAFT e poi ATTIVO. L'invio come l'orchestratore: la riga del lister scritta
--   dalla madre, nella commessa del contratto SENZA periodo (G-6: una commessa
--   viva per contratto; vedi la richiesta al BE nel §6.12 del brief).
-- ⭐ Parte A a date FISSE nel passato (contratti dal 2026-02-15, giri di
--   ottobre e novembre 2026 passati per p_competenza_mese): i numeri si leggono
--   a mano. Parte B a date RELATIVE a oggi: la cessazione non puo' essere nel
--   passato (E_CONTRATTO_VALIDO_AL_RETROATTIVO).
--
-- Indice test (1..15):
--  A — i canoni (C1 su quota fissa, C2 su servizi; giro di ottobre 2026)
--   1) la quota fissa del listino senza riga (Q, trimestrale): 4 pezzi, il primo
--      di mezzo trimestre (0,5), la chiave nomina l'articolo, prezzo dal listino
--   2) l'OVERRIDE su una quota fissa (O) prende il suo posto: mensile, 2 a
--      periodo (1 a meta' febbraio), al suo prezzo; nessun pezzo dal listino
--   3) l'ESCLUSIONE (E) e l'OVERRIDE fuori quota fissa (S2) non partono (F-1)
--   4) l'ADESIONE (S1): periodicita' dal listino, prezzo del listino
--   5) l'AGGIUNTA a durata in giorni (X): la quantita' sono i giorni del pezzo
--   6) competenza: il mese del giro; dal/al e data dell'attivita' = il pezzo
--   7) il meta del canone: erogazione, periodicita', generazione, origine
--   8) inviato il giro, un secondo giro non rimanda niente
--   9) il giro di novembre manda solo i pezzi nuovi
--  B — lo storno (C3, date relative a oggi)
--  10) la cessazione programmata dopo un addebito anticipato: una riga negativa
--      per ogni pezzo che va oltre valido_al, al prezzo addebitato, chiave #STO
--  11) inviati gli storni: niente da rimandare, e quanto resta e' il dovuto
--      fino a valido_al (mensile: 2 + 2 x frazione del mese, la frazione a 6
--      decimali come la scrive vendite.fn_canone_periodi)
--  12) dopo valido_al il giro non genera altro (gli storni non spostano il «da»)
--  C — la fine che si sposta dopo il primo storno (C3, finche' e' ATTIVO)
--  13) anticipata di 5 giorni: una seconda rettifica negativa, chiave #STO:2;
--      resta il dovuto fino alla fine nuova
--  14) spostata di 15 giorni in avanti: una rettifica positiva, chiave #STO:3
--  15) tolta: si riaddebita il pezzo intero (#STO:4)
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(15);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.tip(p text) RETURNS smallint LANGUAGE sql STABLE AS
$fx$ SELECT t.id FROM config.listini_tipologie t WHERE t.codice = p $fx$;
CREATE OR REPLACE FUNCTION pg_temp.uom(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT u.id FROM catalogo.unita_misura u WHERE u.codice = p $fx$;

CREATE TEMP TABLE tmp_can_mondo AS
SELECT v.k, m.*
  FROM (VALUES ('C1'), ('C2'), ('C3')) v(k),
       LATERAL dbops.fn_pgtap_crea_mondo_cliente('canoni in commessa ' || v.k) m;

-- I servizi a canone vivono su un listino SERVIZI: la coppia con l'utility
-- del mondo si ammette qui.
INSERT INTO config.listini_tipologie_utilities (utility_id, tipologia_id)
SELECT DISTINCT m.utility_id, pg_temp.tip('SERVIZI') FROM tmp_can_mondo m
 WHERE NOT EXISTS (SELECT 1 FROM config.listini_tipologie_utilities x
                    WHERE x.utility_id = m.utility_id AND x.tipologia_id = pg_temp.tip('SERVIZI'));

CREATE TEMP TABLE tmp_can_lst AS
WITH ins AS (
  INSERT INTO vendite.listini (codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
  SELECT 'PGTAP_CAN_' || v.k || '_' || substr(md5(clock_timestamp()::text || random()::text), 1, 10),
         'Fixture pgTAP: canoni ' || v.k,
         (SELECT utility_id FROM tmp_can_mondo WHERE k = 'C1'),
         pg_temp.tip(v.k), script.fn_pgtap_emittente_sr_operatore()
    FROM (VALUES ('QUOTA_FISSA'), ('SERVIZI')) v(k)
  RETURNING id, tipologia_id)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_can_ver AS
WITH ins AS (
  INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal)
  SELECT id, 'PGTAP_V1', date '2026-01-01' FROM tmp_can_lst
  RETURNING id, listino_id)
SELECT * FROM ins;

CREATE OR REPLACE FUNCTION pg_temp.lst(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_can_lst WHERE tipologia_id = pg_temp.tip(p) $fx$;
CREATE OR REPLACE FUNCTION pg_temp.ver(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_can_ver WHERE listino_id = pg_temp.lst(p) $fx$;

-- Q, O, E quote fisse; S1, S2 servizi del listino; X servizio a giorni, fuori listino.
CREATE TEMP TABLE tmp_can_art AS
SELECT v.s, dbops.fn_pgtap_crea_articolo('PGTAP-CAN-' || v.s,
         p_uom_id               => CASE WHEN v.s = 'X' THEN pg_temp.uom('GG') END,
         p_listino_tipologia_id => pg_temp.tip(v.t)) AS id
  FROM (VALUES ('Q', 'QUOTA_FISSA'), ('O', 'QUOTA_FISSA'), ('E', 'QUOTA_FISSA'),
               ('S1', 'SERVIZI'), ('S2', 'SERVIZI'), ('X', 'SERVIZI')) v(s, t);

CREATE OR REPLACE FUNCTION pg_temp.art(p text) RETURNS uuid LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_can_art WHERE s = p $fx$;

DO $fx$ BEGIN
  PERFORM dbops.fn_pgtap_listino_aggiungi_articoli(pg_temp.ver('QUOTA_FISSA'),
    ARRAY[pg_temp.art('Q'), pg_temp.art('O'), pg_temp.art('E')], 100);
  PERFORM dbops.fn_pgtap_listino_aggiungi_articoli(pg_temp.ver('SERVIZI'),
    ARRAY[pg_temp.art('S1'), pg_temp.art('S2')], 100);
END $fx$;

-- In bozza la riga di listino si scrive: Q e S1 trimestrali, gli altri mensili.
UPDATE vendite.listini_righe
   SET periodicita = CASE WHEN articolo_id IN (pg_temp.art('Q'), pg_temp.art('S1'))
                          THEN 'TRIMESTRALE' ELSE 'MENSILE' END
 WHERE listino_versione_id IN (SELECT id FROM tmp_can_ver);

DO $fx$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni'::regclass, v.id, 'ATTIVA')
     FROM tmp_can_ver v;
END $fx$;

-- C1 e C2 dal 2026-02-15, senza scadenza; C3 dal primo del mese in corso.
CREATE TEMP TABLE tmp_can_ctr AS
SELECT v.k, (SELECT x.contratto_id
               FROM dbops.fn_pgtap_crea_contratto(
                      'canoni in commessa ' || v.k, 'DRAFT', m.billing_account_id, NULL,
                      v.dal, NULL, NULL, pg_temp.lst(v.t)) x) AS id
  FROM (VALUES ('C1', 'QUOTA_FISSA', date '2026-02-15'),
               ('C2', 'SERVIZI',     date '2026-02-15'),
               ('C3', 'QUOTA_FISSA', date_trunc('month', script.fn_data_operativa())::date)) v(k, t, dal)
  JOIN tmp_can_mondo m ON m.k = v.k;

CREATE OR REPLACE FUNCTION pg_temp.ctr(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT id FROM tmp_can_ctr WHERE k = p $fx$;

INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario,
       tipo_erogazione, fonte_quantita_attesa, qta_operativa, quantita, periodicita)
VALUES (pg_temp.ctr('C1'), pg_temp.art('O'),  'OVERRIDE', 80,   'CANONE', 'FISSA',  2,    2,    'MENSILE'),
       (pg_temp.ctr('C2'), pg_temp.art('S1'), 'ADESIONE', NULL, 'CANONE', 'FISSA',  1,    1,    NULL),
       (pg_temp.ctr('C2'), pg_temp.art('S2'), 'OVERRIDE', 50,   'CANONE', 'FISSA',  1,    1,    'MENSILE'),
       (pg_temp.ctr('C2'), pg_temp.art('X'),  'AGGIUNTA', 2,    'CANONE', 'DURATA', NULL, NULL, 'MENSILE'),
       (pg_temp.ctr('C3'), pg_temp.art('O'),  'OVERRIDE', 80,   'CANONE', 'FISSA',  2,    2,    'MENSILE');
INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione)
VALUES (pg_temp.ctr('C1'), pg_temp.art('E'), 'ESCLUSIONE');

DO $fx$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, id, 'ATTIVO') FROM tmp_can_ctr;
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

-- Il giro di ottobre 2026 di C1 e C2.
CREATE TEMP TABLE tmp_can_ott AS
SELECT c.k, a.s, to_jsonb(l) AS v
  FROM tmp_can_ctr c
 CROSS JOIN LATERAL vendite.fn_list_contratti_da_pushare(
         p_competenza_mese => date '2026-10-01', p_contratto_id => c.id) l
  LEFT JOIN tmp_can_art a ON a.id = l.articolo_id
 WHERE c.k IN ('C1', 'C2');

-- Scopo: i pezzi di un articolo, come testo «dal..al:quantita'».
CREATE OR REPLACE FUNCTION pg_temp.pezzi(p_s text) RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT string_agg((o.v ->> 'competenza_dal') || '..' || (o.v ->> 'competenza_al') || ':'
                    || ((o.v ->> 'quantita')::numeric)::numeric(18,6)::text,
                    ' ' ORDER BY o.v ->> 'competenza_dal')
    FROM tmp_can_ott o WHERE o.s = p_s;
$fx$;

-- ============================================================
-- A — I canoni
-- ============================================================
SELECT ok(
  pg_temp.pezzi('Q') = '2026-02-15..2026-03-31:0.500000 2026-04-01..2026-06-30:1.000000 '
                    || '2026-07-01..2026-09-30:1.000000 2026-10-01..2026-12-31:1.000000'
  AND (SELECT bool_and(o.v ->> 'riga_id' IS NULL
                       AND o.v ->> 'segment_key' LIKE '%:A:' || pg_temp.art('Q')::text || ':M:%'
                       AND (o.v ->> 'prezzo_snapshot')::numeric = 100
                       AND (o.v ->> 'prezzo_bloccato')::boolean IS FALSE)
         FROM tmp_can_ott o WHERE o.s = 'Q'),
  '1) quota fissa del listino senza riga: 4 pezzi trimestrali (il primo 0,5), chiave sull''articolo, prezzo dal listino');

SELECT ok(
  (SELECT count(*) = 9
          AND bool_and((o.v ->> 'quantita')::numeric
                       = CASE WHEN o.v ->> 'competenza_dal' = '2026-02-15' THEN 1 ELSE 2 END
                       AND (o.v ->> 'prezzo_snapshot')::numeric = 80
                       AND (o.v ->> 'prezzo_bloccato')::boolean
                       AND o.v ->> 'segment_key' LIKE '%:R:%')
     FROM tmp_can_ott o WHERE o.s = 'O'),
  '2) l''OVERRIDE sulla quota fissa prende il posto della riga di listino: 9 mesi, 2 a periodo (1 a meta'' febbraio), a 80');

SELECT is(
  (SELECT count(*)::int FROM tmp_can_ott o WHERE o.s IN ('E', 'S2')),
  0,
  '3) l''ESCLUSIONE e l''OVERRIDE fuori quota fissa non partono (F-1: l''OVERRIDE e'' solo il prezzo del cliente)');

SELECT ok(
  pg_temp.pezzi('S1') = '2026-02-15..2026-03-31:0.500000 2026-04-01..2026-06-30:1.000000 '
                     || '2026-07-01..2026-09-30:1.000000 2026-10-01..2026-12-31:1.000000'
  AND (SELECT bool_and((o.v ->> 'prezzo_snapshot')::numeric = 100
                       AND (o.v ->> 'prezzo_bloccato')::boolean IS FALSE
                       AND o.v -> 'meta' ->> 'periodicita' = 'TRIMESTRALE')
         FROM tmp_can_ott o WHERE o.s = 'S1'),
  '4) l''ADESIONE: trimestrale dalla riga di listino, al prezzo del listino');

SELECT ok(
  (SELECT count(*) = 9
          AND sum((o.v ->> 'quantita')::numeric) = 259
          AND bool_and((o.v ->> 'quantita')::numeric
                       = (o.v ->> 'competenza_al')::date - (o.v ->> 'competenza_dal')::date + 1
                       AND (o.v ->> 'prezzo_snapshot')::numeric = 2)
     FROM tmp_can_ott o WHERE o.s = 'X'),
  '5) l''AGGIUNTA a durata in giorni: la quantita'' sono i giorni del pezzo (259 dal 15/02 al 31/10), al prezzo della riga');

SELECT ok(
  (SELECT count(*) = 26
          AND bool_and((o.v ->> 'competenza_mese')::date = date '2026-10-01'
                       AND o.v ->> 'data_attivita' = o.v ->> 'competenza_dal')
     FROM tmp_can_ott o),
  '6) competenza: il mese del giro; la data dell''attivita'' e'' l''inizio del pezzo');

SELECT ok(
  (SELECT bool_and(o.v -> 'meta' ->> 'tipo_erogazione' = 'CANONE'
                   AND o.v -> 'meta' ->> 'generazione_canone' = 'INIZIO_PERIODO'
                   AND o.v -> 'meta' ->> 'origine_canone'
                       = CASE WHEN o.s = 'Q' THEN 'LISTINO' ELSE 'RIGA' END)
     FROM tmp_can_ott o),
  '7) il meta del canone: erogazione, generazione dalla testata, origine (riga o listino)');

CREATE TEMP TABLE tmp_can_inviate AS
SELECT pg_temp.invia(o.v) AS id FROM tmp_can_ott o;

SELECT is(
  (SELECT count(*)::int
     FROM tmp_can_ctr c
    CROSS JOIN LATERAL vendite.fn_list_contratti_da_pushare(
            p_competenza_mese => date '2026-10-01', p_contratto_id => c.id) l
    WHERE c.k IN ('C1', 'C2')),
  0,
  '8) inviato il giro, un secondo giro dello stesso mese non rimanda niente');

CREATE TEMP TABLE tmp_can_nov AS
SELECT a.s, to_jsonb(l) AS v
  FROM tmp_can_ctr c
 CROSS JOIN LATERAL vendite.fn_list_contratti_da_pushare(
         p_competenza_mese => date '2026-11-01', p_contratto_id => c.id) l
  JOIN tmp_can_art a ON a.id = l.articolo_id
 WHERE c.k IN ('C1', 'C2');

SELECT is(
  (SELECT string_agg(n.s || ':' || (n.v ->> 'competenza_dal') || '..' || (n.v ->> 'competenza_al')
                     || ':' || ((n.v ->> 'quantita')::numeric)::numeric(18,6)::text, ' ' ORDER BY n.s)
     FROM tmp_can_nov n),
  'O:2026-11-01..2026-11-30:2.000000 X:2026-11-01..2026-11-30:30.000000',
  '9) il giro di novembre manda solo i pezzi nuovi (i trimestri sono gia'' addebitati fino a dicembre)');

-- ============================================================
-- B — Lo storno (C3: dal primo del mese in corso, giro del mese dopo)
-- ============================================================
CREATE TEMP TABLE tmp_can_b AS
SELECT date_trunc('month', script.fn_data_operativa())::date                        AS m0,
       (date_trunc('month', script.fn_data_operativa()) + interval '1 month')::date AS m1,
       (date_trunc('month', script.fn_data_operativa()) + interval '1 month 9 days')::date AS fine,
       extract(day FROM date_trunc('month', script.fn_data_operativa())
                        + interval '2 month - 1 day')::numeric                     AS giorni_m1;

SELECT count(pg_temp.invia(to_jsonb(l)))
  FROM vendite.fn_list_contratti_da_pushare(
         p_competenza_mese => (SELECT m1 FROM tmp_can_b), p_contratto_id => pg_temp.ctr('C3')) l;

-- La cessazione programmata al 10 del mese dopo: il mese dopo e' gia'
-- addebitato per intero (anticipato).
SELECT count(*) FROM vendite.fn_cessa_contratto(pg_temp.ctr('C3'), (SELECT fine FROM tmp_can_b));

CREATE TEMP TABLE tmp_can_sto AS
SELECT a.s, to_jsonb(l) AS v
  FROM vendite.fn_list_contratti_da_pushare(
         p_competenza_mese => (SELECT m1 FROM tmp_can_b), p_contratto_id => pg_temp.ctr('C3')) l
  JOIN tmp_can_art a ON a.id = l.articolo_id;

SELECT ok(
  (SELECT count(*) FILTER (WHERE t.s = 'O') = 1
          AND bool_and((t.v ->> 'quantita')::numeric < 0
                       AND t.v ->> 'riga_id' IS NULL
                       AND t.v ->> 'segment_key' LIKE '%#STO'
                       AND (t.v ->> 'prezzo_bloccato')::boolean
                       AND (t.v ->> 'competenza_dal')::date = b.fine + 1
                       AND t.v -> 'meta' ->> 'movimento' = 'STORNO_CANONE')
          AND bool_and((t.v ->> 'quantita')::numeric = round(2 * round(10 / b.giorni_m1, 6), 6) - 2
                       AND (t.v ->> 'prezzo_snapshot')::numeric = 80) FILTER (WHERE t.s = 'O')
     FROM tmp_can_sto t, tmp_can_b b),
  '10) cessazione dopo l''addebito anticipato: una riga negativa per pezzo oltre valido_al, al prezzo addebitato, chiave #STO');

CREATE TEMP TABLE tmp_can_sto_inviati AS
SELECT pg_temp.invia(t.v) AS id FROM tmp_can_sto t;

SELECT ok(
  (SELECT count(*) = 0
     FROM vendite.fn_list_contratti_da_pushare(
            p_competenza_mese => (SELECT m1 FROM tmp_can_b), p_contratto_id => pg_temp.ctr('C3')))
  AND (SELECT sum(ca.quantita) = 2 + round(2 * round(10 / b.giorni_m1, 6), 6)
         FROM vendite.commesse_attivita ca, tmp_can_b b
        WHERE ca.sorgente_uid = (SELECT k.uid::text FROM vendite.contratti k WHERE k.id = pg_temp.ctr('C3'))
          AND ca.articolo_id = pg_temp.art('O')
        GROUP BY b.giorni_m1),
  '11) inviati gli storni non c''e'' altro, e resta il dovuto fino a valido_al (2 + 2 x 10/giorni del mese)');

SELECT is(
  (SELECT count(*)::int
     FROM vendite.fn_list_contratti_da_pushare(
            p_competenza_mese => (SELECT (m1 + interval '2 month')::date FROM tmp_can_b),
            p_contratto_id => pg_temp.ctr('C3'))),
  0,
  '12) dopo valido_al il giro non genera altro: gli storni non spostano il «da» del canone');

-- ============================================================
-- C — La fine che si sposta dopo il primo storno (C3 resta ATTIVO)
-- ============================================================
-- Scopo: manda il giro del mese dopo di C3; ritorna le righe come jsonb.
CREATE OR REPLACE FUNCTION pg_temp.giro_c3() RETURNS SETOF jsonb LANGUAGE sql AS $fx$
  SELECT to_jsonb(l) || jsonb_build_object('inviata', pg_temp.invia(to_jsonb(l)))
    FROM vendite.fn_list_contratti_da_pushare(
           p_competenza_mese => (SELECT m1 FROM tmp_can_b), p_contratto_id => pg_temp.ctr('C3')) l;
$fx$;

-- Scopo: quanto c'e' in commessa per l'OVERRIDE di C3 (mese in corso + mese dopo).
CREATE OR REPLACE FUNCTION pg_temp.o_c3() RETURNS numeric LANGUAGE sql STABLE AS $fx$
  SELECT sum(ca.quantita)
    FROM vendite.commesse_attivita ca
   WHERE ca.sorgente_uid = (SELECT k.uid::text FROM vendite.contratti k WHERE k.id = pg_temp.ctr('C3'))
     AND ca.articolo_id = pg_temp.art('O');
$fx$;

SELECT count(*) FROM vendite.fn_cessa_contratto(pg_temp.ctr('C3'), (SELECT fine - 5 FROM tmp_can_b));
CREATE TEMP TABLE tmp_can_c13 AS SELECT * FROM pg_temp.giro_c3() v;

SELECT ok(
  (SELECT count(*) FILTER (WHERE t.v ->> 'articolo_id' = pg_temp.art('O')::text) = 1
          AND bool_and(t.v ->> 'segment_key' LIKE '%#STO:2' AND (t.v ->> 'quantita')::numeric < 0)
     FROM tmp_can_c13 t)
  AND (SELECT pg_temp.o_c3() = 2 + round(2 * round(5 / b.giorni_m1, 6), 6) FROM tmp_can_b b),
  '13) fine anticipata dopo il primo storno: una seconda rettifica negativa (#STO:2), resta il dovuto fino alla fine nuova');

SELECT count(*) FROM vendite.fn_cessa_contratto(pg_temp.ctr('C3'), (SELECT fine + 15 FROM tmp_can_b));
CREATE TEMP TABLE tmp_can_c14 AS SELECT * FROM pg_temp.giro_c3() v;

SELECT ok(
  (SELECT bool_and(t.v ->> 'segment_key' LIKE '%#STO:3' AND (t.v ->> 'quantita')::numeric > 0)
     FROM tmp_can_c14 t)
  AND (SELECT pg_temp.o_c3() = 2 + round(2 * round(25 / b.giorni_m1, 6), 6) FROM tmp_can_b b),
  '14) fine spostata in avanti: una rettifica positiva (#STO:3), il dovuto fino alla fine nuova');

UPDATE vendite.contratti SET valido_al = NULL WHERE id = pg_temp.ctr('C3');
CREATE TEMP TABLE tmp_can_c15 AS SELECT * FROM pg_temp.giro_c3() v;

SELECT ok(
  (SELECT count(*) > 0 AND bool_and(t.v ->> 'segment_key' LIKE '%#STO:4') FROM tmp_can_c15 t)
  AND pg_temp.o_c3() = 4
  AND (SELECT count(*) = 0 FROM pg_temp.giro_c3()),
  '15) fine tolta: si riaddebita il pezzo intero (#STO:4), e un altro giro non rimanda niente');

SELECT * FROM finish();
ROLLBACK;
