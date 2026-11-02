-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: un contratto arriva in commessa dalla madre delle righe.
--   vendite.fn_list_contratti_da_pushare -> vendite.fn_upsert_commessa_attivita,
--   e il ritiro di tipo_consumo dalla catena del push.
-- ChangeSet: 20261013-16 … -23
-- Segnalazione: smoke BE su dbdev del 2026-10-13 (push batch CONTRATTO in
--   ERRORE, «tipo_consumo non valido: UNA_TANTUM», commessa rimasta vuota).
-- rev 2026-10-30 (20261030-01, brief-db-contratto-righe-periodiche-in-commessa §6.12): la parte D prova il canone che parte a periodi (9, 10, 11, 12).
-- rev 2026-10-26 (brief-modello-documento-vendita §11): i due contratti (della madre e quello aperto) si attivano con dbops.fn_pgtap_porta_a_stato, non piu' con l'UPDATE diretto dello stato che la porta del contratto ora rifiuta.
-- ------------------------------------------------------------
-- Indice test (plan 12):
--  A — la forma
--   1) la madre ha una firma sola, senza p_tipo_consumo
--   2) nessuno dei cinque lister del push espone piu' la colonna tipo_consumo
--  B — il contratto, dal lister alla commessa
--   3) il lister lista la riga del contratto, con l'erogazione in
--      meta.tipo_erogazione (UNA_TANTUM)
--   4) l'invio dalla madre riesce: una riga di commessa per la riga del
--      contratto, con la sorgente CONTRATTO e il segmento del lister.
--      ⚠️ E' il caso che la segnalazione ha trovato rotto: fino al 20261013-16
--      la madre rifiutava l'erogazione messa in tipo_consumo, e nessun pgTAP
--      faceva questo passaggio (i test del lister non arrivavano alla madre).
--      ⚠️ Da solo NON pinna quel difetto: l'invio qui sotto non inoltra
--      tipo_consumo (dopo il ritiro non si puo' piu' scrivere), quindi sul
--      codice vecchio passerebbe col default della madre. Il difetto non torna
--      finche' il parametro e la colonna non tornano: lo tengono i test 1 e 2
--      (provato il 2026-10-13: senza i changeSet sono rossi 1, 2, 5, 7, 8)
--   5) la riga scritta porta l'erogazione in meta, e non tipo_consumo
--   6) la madre ha scritto il link contratto -> commessa (D-13 del
--      20261012-46), e il contratto non e' piu' da mandare
--  C — la chiave ritirata non rinasce
--   7) un meta in ingresso con tipo_consumo (il reso ricopia il meta della
--      riga d'origine, e le righe scritte prima del ritiro lo portano): la
--      madre lo toglie, e il resto del meta resta
--   8) un secondo invio dello stesso segmento (ramo ON CONFLICT) non rimette
--      la chiave
--  D — un contratto senza scadenza (20261013-24, D-1 e D-2 di Tid; rev
--      2026-10-30, 20261030-01: il canone parte, a periodi)
--   9) il lister lista la riga UNA_TANTUM e il primo pezzo della CANONE
--      (anticipata e mensile: il mese in corso, da oggi)
--  10) la competenza della riga una tantum e' il giorno di attivazione, in
--      tutte e due le colonne (prima: competenza_al = valido_al, cioe' NULL)
--  11) l'invio dalla madre riesce, con quella competenza. ⚠️ E' il caso della
--      segnalazione BE del 2026-10-13 (registro 2724): sul lister del
--      20261013-19 la madre cadeva sul NOT NULL di competenza_al
--  12) il pezzo del canone e' in commessa col suo periodo (da oggi a fine
--      mese) e la frazione del mese, e un secondo giro non lo rimanda.
--      ⚠️ Fino al 20261030-01 qui si provava il contrario (la CANONE non
--      partiva): il test racconta la regola, e la regola e' cambiata (§5 del
--      brief-db-contratto-righe-periodiche-in-commessa)
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO: cliente e articolo dai builder, contratto
--   composto in DRAFT e poi ATTIVO (come l'applicazione), commessa da
--   fn_get_or_create_commessa. L'invio come lo fa l'orchestratore: la riga del
--   lister, scritta dalla madre. ⚠️ Il pricing NON e' qui: il prezzo e' quello
--   della riga del contratto (prezzo_bloccato), e lo snapshot di audit che il
--   backend aggiunge (origine, versione di listino) resta a NULL. Questo test
--   prova il contratto DB fra lister e madre, non l'orchestratore.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: qui il COMMIT non arriva mai, e senza IMMEDIATE non
--   verrebbero esercitati.
SET CONSTRAINTS ALL IMMEDIATE;

-- Il test gira come l'applicazione (OPERATORE + RLS attiva).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ============================================================
-- A — La forma
-- ============================================================
SELECT ok(
  (SELECT count(*) = 1 AND bool_and(NOT ('p_tipo_consumo' = ANY (p.proargnames)))
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'fn_upsert_commessa_attivita'),
  '1) la madre ha una firma sola, senza p_tipo_consumo');

SELECT is(
  (SELECT count(*)::int
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname IN ('fn_list_contratti_da_pushare', 'fn_list_consumi_da_pushare',
                        'fn_list_ddt_da_pushare', 'fn_list_ordini_da_pushare',
                        'fn_list_preventivi_da_pushare')
      AND 'tipo_consumo' = ANY (p.proargnames)),
  0,
  '2) nessuno dei cinque lister del push espone la colonna tipo_consumo');

-- ============================================================
-- Fixture — COSTRUITE
-- ============================================================
CREATE TEMP TABLE tmp_pc_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('push contratto dalla madre');

CREATE TEMP TABLE tmp_pc_refs AS
SELECT
  c.billing_account_id, c.utility_id, c.istanza_utility_id,
  dbops.fn_pgtap_crea_articolo('PGT-PC-SERV', false)                                       AS articolo_id,
  (SELECT s.id FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'ATTIVO' AND s.attivo IS TRUE)                                 AS stato_attivo_id,
  (SELECT s.id FROM config.stati_doc_contratti s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE)                                  AS stato_draft_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'CONTRATTO')                 AS sorg_contratto_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA')                  AS sorg_commessa_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo ORDER BY t.id LIMIT 1)        AS tipo_doc_fiscale_id
FROM tmp_pc_cli c;

-- Il contratto si compone in bozza e poi si attiva: il pricing di un
-- contratto attivo e' fermo (lock delle righe fuori bozza).
CREATE TEMP TABLE tmp_pc_contratto AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al, stato_doc_contratto_id, data, meta)
  SELECT 'PGT-PC-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.istanza_utility_id, r.utility_id,
         date_trunc('month', script.fn_data_operativa())::date,
         (date_trunc('month', script.fn_data_operativa()) + interval '1 year - 1 day')::date,
         r.stato_draft_id, script.fn_data_operativa(),
         jsonb_build_object('test_scope', 'pgtap_push_contratto_madre')
    FROM tmp_pc_refs r
  RETURNING id, uid
)
SELECT * FROM ins;

-- UNA_TANTUM e non CANONE: CANONE era il vecchio ripiego del lister, e il
-- test passerebbe per coincidenza. AGGIUNTA: la riga ha un prezzo suo.
CREATE TEMP TABLE tmp_pc_riga AS
WITH ins AS (
  INSERT INTO vendite.contratti_righe (
    contratto_id, articolo_id, prezzo_unitario, tipo_erogazione,
    qta_operativa, quantita, fonte_quantita_attesa, tipo_eccezione, attivo, meta)
  SELECT c.id, r.articolo_id, 50, 'UNA_TANTUM',
         1, 1, 'FISSA', 'AGGIUNTA'::vendite.tipo_eccezione_contratto, true,
         jsonb_build_object('test_scope', 'pgtap_push_contratto_madre')
    FROM tmp_pc_contratto c, tmp_pc_refs r
  RETURNING id
)
SELECT * FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, id, 'ATTIVO')
  FROM tmp_pc_contratto;

-- La commessa del cliente, come la apre il push.
CREATE TEMP TABLE tmp_pc_commessa AS
SELECT vendite.fn_get_or_create_commessa(
         p_billing_account_id     => r.billing_account_id,
         p_utility_id             => r.utility_id,
         p_tipo_commessa          => 'AUTO',
         p_policy_fatturazione    => 'DA_DOCUMENTO',
         p_fatturazione_immediata => false,
         p_priorita_operativa     => 'NORMALE',
         p_competenza_dal         => date_trunc('month', script.fn_data_operativa())::date,
         p_competenza_al          => (date_trunc('month', script.fn_data_operativa())
                                      + interval '1 month - 1 day')::date,
         p_meta                   => '{}'::jsonb,
         p_force_new              => true) AS id
  FROM tmp_pc_refs r;

-- L'invio di una riga del lister dalla madre, come l'orchestratore (vedi la
-- nota in testa sul pricing). p_meta_extra si fonde col meta del lister.
CREATE OR REPLACE FUNCTION pg_temp.pc_invia(v jsonb, p_meta_extra jsonb DEFAULT '{}'::jsonb,
                                            p_commessa bigint DEFAULT NULL)
RETURNS bigint AS $$
  SELECT u.attivita_id
    FROM vendite.fn_upsert_commessa_attivita(
      p_commessa_id                   => COALESCE(p_commessa, (SELECT id FROM tmp_pc_commessa)),
      p_segment_key                   => (v ->> 'segment_key')::varchar,
      p_articolo_id                   => (v ->> 'articolo_id')::uuid,
      p_istanza_utility_id            => (v ->> 'istanza_utility_id')::bigint,
      p_data_attivita                 => (v ->> 'data_attivita')::date,
      p_uom_id                        => (v ->> 'uom_id')::bigint,
      p_quantita                      => (v ->> 'quantita')::numeric,
      p_competenza_mese               => (v ->> 'competenza_mese')::date,
      p_competenza_dal                => (v ->> 'competenza_dal')::date,
      p_competenza_al                 => (v ->> 'competenza_al')::date,
      p_prezzo_snapshot               => (v ->> 'prezzo_snapshot')::numeric,
      p_prezzo_base_snapshot          => NULL,
      p_origine_prezzo                => NULL,
      p_tipo_variazione_applicata     => NULL,
      p_valore_variazione_applicata   => NULL,
      p_promo_id                      => NULL,
      p_contratto_id                  => NULL,
      p_categoria_cliente_id_snapshot => NULL,
      p_classe_utenza_id_snapshot     => NULL,
      p_qta_operativa                 => (v ->> 'qta_operativa')::numeric,
      p_uom_operativa_id              => (v ->> 'uom_operativa_id')::bigint,
      p_factor_to_base                => (v ->> 'factor_to_base')::numeric,
      p_tipo_doc_fiscale_id           => COALESCE((v ->> 'tipo_doc_fiscale_id')::bigint,
                                                  (SELECT tipo_doc_fiscale_id FROM tmp_pc_refs)),
      p_valuta_id                     => (v ->> 'valuta_id')::integer,
      p_prezzo_bloccato               => (v ->> 'prezzo_bloccato')::boolean,
      p_pricing_mode                  => (v ->> 'pricing_mode')::varchar,
      p_stato_approvazione            => 'BOZZA',
      p_stato_emissione               => 'NON_EMESSA',
      p_sorgente_tipo_id              => (v ->> 'sorgente_tipo_id')::bigint,
      p_sorgente_uid                  => v ->> 'sorgente_uid',
      p_tipo_movimento                => (v ->> 'tipo_movimento')::varchar,
      p_meta                          => COALESCE(v -> 'meta', '{}'::jsonb) || p_meta_extra) u
$$ LANGUAGE sql;

-- ============================================================
-- B — Il contratto, dal lister alla commessa
-- ============================================================
CREATE TEMP TABLE tmp_pc_lista AS
SELECT to_jsonb(x) AS v
  FROM vendite.fn_list_contratti_da_pushare(p_contratto_id => (SELECT id FROM tmp_pc_contratto)) x;

SELECT ok(
  (SELECT count(*) = 1
          AND bool_and((l.v ->> 'riga_id')::bigint = (SELECT id FROM tmp_pc_riga)
                       AND l.v -> 'meta' ->> 'tipo_erogazione' = 'UNA_TANTUM')
     FROM tmp_pc_lista l),
  '3) il lister lista la riga del contratto, con l''erogazione in meta.tipo_erogazione');

CREATE TEMP TABLE tmp_pc_ca AS
SELECT pg_temp.pc_invia(l.v) AS id, l.v ->> 'segment_key' AS segment_key
  FROM tmp_pc_lista l;

SELECT ok(
  (SELECT ca.commessa_id = (SELECT id FROM tmp_pc_commessa)
          AND ca.sorgente_tipo_id = (SELECT sorg_contratto_id FROM tmp_pc_refs)
          AND ca.sorgente_uid = (SELECT uid::text FROM tmp_pc_contratto)
          AND ca.segment_key = t.segment_key
     FROM tmp_pc_ca t JOIN vendite.commesse_attivita ca ON ca.id = t.id),
  '4) l''invio dalla madre scrive la riga di commessa del contratto (sorgente e segmento del lister)');

SELECT ok(
  (SELECT ca.meta ->> 'tipo_erogazione' = 'UNA_TANTUM' AND NOT (ca.meta ? 'tipo_consumo')
     FROM tmp_pc_ca t JOIN vendite.commesse_attivita ca ON ca.id = t.id),
  '5) la riga porta l''erogazione in meta.tipo_erogazione, e non tipo_consumo');

-- ⚠️ La chiave del link NON e' quella della riga: commesse_sorgenti segue il
--   key_selector della sorgente, e per il CONTRATTO e' l'id (la riga di
--   commessa porta invece l'uid, come tutte le sorgenti).
SELECT ok(
  EXISTS (SELECT 1 FROM vendite.commesse_sorgenti cs
           WHERE cs.commessa_id = (SELECT id FROM tmp_pc_commessa)
             AND cs.sorgente_tipo_id = (SELECT sorg_contratto_id FROM tmp_pc_refs)
             AND cs.sorgente_uid = (SELECT id::text FROM tmp_pc_contratto))
  AND NOT EXISTS (SELECT 1 FROM vendite.fn_list_contratti_da_pushare(
                    p_contratto_id => (SELECT id FROM tmp_pc_contratto))),
  '6) la madre ha scritto il link contratto -> commessa, e il contratto non e'' piu'' da mandare');

-- ============================================================
-- C — La chiave ritirata non rinasce
-- ============================================================
-- Una riga «della commessa» (sorgente COMMESSA con l'id della commessa, come
-- il builder dbops.fn_pgtap_crea_commessa_attivita: fuori dalla porta del link)
-- con un meta che porta ancora tipo_consumo, come quello che il reso ricopia
-- da una riga scritta prima del ritiro.
CREATE TEMP TABLE tmp_pc_vecchio AS
SELECT (SELECT v FROM tmp_pc_lista)
       || jsonb_build_object(
            'segment_key',      'PGT-PC-TC:' || substr(md5(clock_timestamp()::text), 1, 8),
            'sorgente_tipo_id', (SELECT sorg_commessa_id FROM tmp_pc_refs),
            'sorgente_uid',     (SELECT id::text FROM tmp_pc_commessa)) AS v;

CREATE TEMP TABLE tmp_pc_ca2 AS
SELECT pg_temp.pc_invia(v, jsonb_build_object('tipo_consumo', 'CONGUAGLIO', 'pgt_resta', 1)) AS id
  FROM tmp_pc_vecchio;

SELECT ok(
  (SELECT NOT (ca.meta ? 'tipo_consumo') AND ca.meta ->> 'pgt_resta' = '1'
     FROM tmp_pc_ca2 t JOIN vendite.commesse_attivita ca ON ca.id = t.id),
  '7) un meta in ingresso con tipo_consumo: la madre toglie la chiave, il resto resta');

SELECT ok(
  (SELECT pg_temp.pc_invia(v, jsonb_build_object('tipo_consumo', 'STORNO')) = (SELECT id FROM tmp_pc_ca2)
     FROM tmp_pc_vecchio)
  AND (SELECT NOT (ca.meta ? 'tipo_consumo')
         FROM tmp_pc_ca2 t JOIN vendite.commesse_attivita ca ON ca.id = t.id),
  '8) il secondo invio dello stesso segmento (ON CONFLICT) non rimette la chiave');

-- ============================================================
-- D — Un contratto senza scadenza (20261013-24)
-- ============================================================
-- valido_al NULL: e' il contratto che non finisce. Una riga UNA_TANTUM e una
-- CANONE (INIZIO_PERIODO, forzata sulla riga: vuota seguirebbe la testata, F-7).
-- ⚠️ Un cliente suo: due contratti della stessa fornitura non si sovrappongono
--   (ex_contratti_no_overlap), e quello del caso B copre gia' oggi.
CREATE TEMP TABLE tmp_pc_cli2 AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('push contratto senza scadenza');

CREATE TEMP TABLE tmp_pc_commessa2 AS
SELECT vendite.fn_get_or_create_commessa(
         p_billing_account_id     => c.billing_account_id,
         p_utility_id             => c.utility_id,
         p_tipo_commessa          => 'AUTO',
         p_policy_fatturazione    => 'DA_DOCUMENTO',
         p_fatturazione_immediata => false,
         p_priorita_operativa     => 'NORMALE',
         p_competenza_dal         => date_trunc('month', script.fn_data_operativa())::date,
         p_competenza_al          => (date_trunc('month', script.fn_data_operativa())
                                      + interval '1 month - 1 day')::date,
         p_meta                   => '{}'::jsonb,
         p_force_new              => true) AS id
  FROM tmp_pc_cli2 c;

CREATE TEMP TABLE tmp_pc_aperto AS
WITH ins AS (
  INSERT INTO vendite.contratti (
    numero, billing_account_id, istanza_utility_id, utility_id,
    valido_dal, valido_al, stato_doc_contratto_id, data, meta)
  SELECT 'PGT-PCA-' || substr(md5(clock_timestamp()::text), 1, 8),
         c2.billing_account_id, c2.istanza_utility_id, c2.utility_id,
         script.fn_data_operativa(), NULL,
         r.stato_draft_id, script.fn_data_operativa(),
         jsonb_build_object('test_scope', 'pgtap_push_contratto_madre')
    FROM tmp_pc_refs r, tmp_pc_cli2 c2
  RETURNING id, uid, valido_dal
)
SELECT * FROM ins;

-- La natura di riga la da' l'articolo: il canone vuole un servizio
-- ricorrente (config.nature_vendita_erogazioni), la MERCE del builder ammette
-- solo UNA_TANTUM. La natura si sceglie alla nascita.
CREATE TEMP TABLE tmp_pc_aperto_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-PCA-UT', false)  AS art_ut_id,
       dbops.fn_pgtap_crea_articolo('PGT-PCA-CAN', false,
           p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                                    WHERE codice_interno = 'SERVIZIO_RICORRENTE')) AS art_can_id;

CREATE TEMP TABLE tmp_pc_aperto_righe AS
WITH ins AS (
  INSERT INTO vendite.contratti_righe (
    contratto_id, articolo_id, prezzo_unitario, tipo_erogazione,
    qta_operativa, quantita, fonte_quantita_attesa, tipo_eccezione,
    periodicita, generazione_canone, attivo, meta)
  SELECT c.id, a.articolo_id, a.prezzo, a.erogazione,
         1, 1, 'FISSA', 'AGGIUNTA'::vendite.tipo_eccezione_contratto,
         a.periodicita, a.generazione, true,
         jsonb_build_object('test_scope', 'pgtap_push_contratto_madre')
    FROM tmp_pc_aperto c,
         (VALUES ((SELECT art_ut_id FROM tmp_pc_aperto_art),  70::numeric, 'UNA_TANTUM', NULL, NULL),
                 ((SELECT art_can_id FROM tmp_pc_aperto_art), 20::numeric, 'CANONE', 'MENSILE', 'INIZIO_PERIODO'))
           AS a(articolo_id, prezzo, erogazione, periodicita, generazione)
  RETURNING id, tipo_erogazione
)
SELECT * FROM ins;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, id, 'ATTIVO')
  FROM tmp_pc_aperto;

CREATE TEMP TABLE tmp_pc_aperto_lista AS
SELECT to_jsonb(x) AS v
  FROM vendite.fn_list_contratti_da_pushare(p_contratto_id => (SELECT id FROM tmp_pc_aperto)) x;

SELECT is(
  (SELECT array_agg((l.v ->> 'riga_id')::bigint ORDER BY (l.v ->> 'riga_id')::bigint) FROM tmp_pc_aperto_lista l),
  (SELECT array_agg(r.id ORDER BY r.id) FROM tmp_pc_aperto_righe r),
  '9) contratto senza scadenza: il lister lista la riga UNA_TANTUM e il primo pezzo della CANONE');

SELECT ok(
  (SELECT (l.v ->> 'competenza_dal')::date = c.valido_dal
          AND (l.v ->> 'competenza_al')::date = c.valido_dal
     FROM tmp_pc_aperto_lista l, tmp_pc_aperto c, tmp_pc_aperto_righe r
    WHERE r.tipo_erogazione = 'UNA_TANTUM' AND (l.v ->> 'riga_id')::bigint = r.id),
  '10) la competenza della riga una tantum e'' il giorno di attivazione, dal e al');

CREATE TEMP TABLE tmp_pc_aperto_ca AS
SELECT pg_temp.pc_invia(l.v, '{}'::jsonb, (SELECT id FROM tmp_pc_commessa2)) AS id FROM tmp_pc_aperto_lista l;

SELECT ok(
  (SELECT ca.competenza_dal = c.valido_dal AND ca.competenza_al = c.valido_dal
          AND ca.sorgente_uid = c.uid::text
     FROM tmp_pc_aperto_ca t
     JOIN vendite.commesse_attivita ca ON ca.id = t.id, tmp_pc_aperto c
    WHERE ca.segment_key LIKE '%:R:' || (SELECT id FROM tmp_pc_aperto_righe
                                          WHERE tipo_erogazione = 'UNA_TANTUM') || ':%'),
  '11) l''invio dalla madre riesce, con la competenza del giorno di attivazione');

SELECT ok(
  (SELECT count(*) = 1
          AND bool_and(ca.competenza_dal = c.valido_dal
                       AND ca.competenza_al = (date_trunc('month', c.valido_dal)
                                               + interval '1 month - 1 day')::date
                       AND ca.quantita = round(((date_trunc('month', c.valido_dal)
                                                 + interval '1 month - 1 day')::date
                                                - c.valido_dal + 1)::numeric
                                               / extract(day FROM date_trunc('month', c.valido_dal)
                                                 + interval '1 month - 1 day')::numeric, 6))
          AND (SELECT count(*) FROM vendite.fn_list_contratti_da_pushare(p_contratto_id => c.id)) = 0
     FROM tmp_pc_aperto c
     JOIN vendite.commesse_attivita ca
       ON ca.sorgente_uid = c.uid::text
      AND ca.segment_key LIKE '%:R:' || (SELECT id FROM tmp_pc_aperto_righe
                                          WHERE tipo_erogazione = 'CANONE') || ':M:%'
    GROUP BY c.id),
  '12) il pezzo del canone e'' in commessa, da oggi a fine mese per la frazione del mese, e un secondo giro non lo rimanda');

SELECT * FROM finish();
ROLLBACK;
