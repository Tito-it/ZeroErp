-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la riga-onere dell'ordine nella copia in bolla e nel push in commessa.
--   vendite.fn_genera_ddt_da_ordine (l'onere passa INTERO nella prima bolla),
--   vendite.trgfn_ordini_ful_guard_consistenza (il legame dell'onere e'
--   intero), vendite.fn_list_ordini_da_pushare, vendite.fn_ddt_push_diagnosi,
--   vendite.fn_list_ddt_da_pushare (l'onere in commessa come ONERE, con la
--   causale dell'articolo e la sorgente del documento).
-- ChangeSet: 20261103-36 … -40 (e, per lo stato dell'ordine, 20261103-22/-23)
-- Brief: brief-db-addebito-trasporto-ordine §8.2, §8.1 (K-1, K-4, K-5, K-6).
-- ------------------------------------------------------------
-- Indice test (plan 17):
--  A — la copia, ordine alla consegna (merce 10 + onere 1)
--   1) la prima bolla, con la sola merce scelta (4), porta anche l'onere
--   2) l'onere e' passato INTERO (quantita' 1) e il legame porta 1
--   3) la riga di bolla porta la natura congelata dell'onere
--   4) la seconda bolla (il resto della merce) non lo porta: residuo 0
--   5) ⭐ l'ordine arriva a EVASO con la merce tutta spedita (prima: l'onere,
--      contato come residuo, lo teneva PARZIALMENTE_EVASO)
--  B — i rifiuti della copia
--   6) una bolla che porterebbe solo oneri: E_DDT_NIENTE_DA_EVADERE
--   7) un legame parziale sull'onere: E_ORD_FUL_ONERE_NON_INTERO
--  C — l'annullo della bolla
--   8) annullata la bolla, il legame si ritira e l'onere torna copiabile
--  D — push dell'ordine che fattura alla conferma
--   9) il lister dell'ordine: onere ONERE con la causale dell'articolo
--  10) ...e la merce NORMALE, senza causale
--  11) dal lister alla madre: in commessa ONERE, causale, sorgente l'ordine
--  12) la bolla di quell'ordine: l'onere copiato NON si pusha dalla bolla
--      (DDT_FATTURA_DA_ORDINE) e il lister della bolla non lo porta
--  E — push della bolla che fattura alla consegna
--  13) la diagnosi: l'onere copiato e' eleggibile, dose = la sua quantita'
--      (non cade in DDT_SENZA_PARTITA)
--  14) il lister della bolla: ONERE con la causale, sorgente la bolla
--  15) dal lister alla madre: in commessa ONERE, causale, sorgente la bolla
--  16) la merce della stessa bolla esce NORMALE, dose dalla partita
--  17) forma: il lister delle bolle espone causale_onere_id, quello degli
--      ordini anche (il contratto col backend)
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO: cliente dal mondo, causale e articolo-onere
--   costruiti (un articolo per causale: uq_articoli_causale_onere), ordini dal
--   builder con le righe, bolle dalla madre via dbops.fn_pgtap_crea_ddt_da_ordine.
--   L'invio in commessa come l'orchestratore: la riga del lister, scritta dalla
--   madre (ref: il lister e la madre si provano insieme). ⚠️ Il backend oggi
--   non passa causale_onere_id alla madre: qui lo si passa, come dovra' fare.
-- ------------------------------------------------------------

BEGIN;

-- La fixture costruisce in piu' istruzioni padre e satelliti: i vincoli
-- differiti si chiudono dopo la costruzione (sotto).
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP onere copia push');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(17);

-- Il codice di dominio dell'errore, dal canale CONSTRAINT (contratto di
-- script.fn_log_and_raise_error). NULL = nessun errore.
CREATE OR REPLACE FUNCTION pg_temp.codice(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN SQLSTATE 'P0001' THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME;
    RETURN v_c;
END $$;

-- Una causale e il suo articolo-onere (servizio una tantum, non a magazzino);
-- un articolo di merce.
CREATE TEMP TABLE _caus AS
WITH ins AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
    VALUES ('PGT_OCP_1', 'PGT_OCP_1', 'Fixture pgTAP: onere copia push')
    RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE _a AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-OCP-ONERE', false,
         p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                                  WHERE nv.codice_interno = 'SERVIZIO_UNA_TANTUM'),
         p_causale_onere_id  => (SELECT id FROM _caus)) AS onere,
       dbops.fn_pgtap_crea_articolo('PGT-OCP-MERCE', false) AS merce;

-- Un ordine con merce e onere (merce alla riga 1, onere alla 2).
CREATE OR REPLACE FUNCTION pg_temp.ordine(p_etichetta text, p_trigger text,
                                          p_qta_merce numeric, p_qta_onere numeric)
RETURNS bigint LANGUAGE sql AS $$
  SELECT o.ordine_id
    FROM dbops.fn_pgtap_crea_ordine_con_righe(p_etichetta, 'CONFERMATO',
           (SELECT billing_account_id FROM _m),
           p_fatturazione_trigger => p_trigger,
           p_righe => jsonb_build_array(
               jsonb_build_object('articolo_id', (SELECT merce FROM _a), 'quantita', p_qta_merce, 'prezzo', 5),
               jsonb_build_object('articolo_id', (SELECT onere FROM _a), 'quantita', p_qta_onere, 'prezzo', 15))) o
$$;

CREATE OR REPLACE FUNCTION pg_temp.riga_ord(p_ordine bigint, p_onere boolean) RETURNS bigint
LANGUAGE sql AS $$
  SELECT r.id FROM vendite.ordini_righe r
   WHERE r.ordine_id = p_ordine
     AND r.articolo_id = CASE WHEN p_onere THEN (SELECT onere FROM _a) ELSE (SELECT merce FROM _a) END
$$;

CREATE OR REPLACE FUNCTION pg_temp.riga_ddt(p_ddt bigint, p_onere boolean) RETURNS bigint
LANGUAGE sql AS $$
  SELECT r.id FROM vendite.ddt_righe r
   WHERE r.ddt_id = p_ddt AND r.attivo IS TRUE
     AND r.articolo_id = CASE WHEN p_onere THEN (SELECT onere FROM _a) ELSE (SELECT merce FROM _a) END
$$;

CREATE OR REPLACE FUNCTION pg_temp.stato_ordine(p_ordine bigint) RETURNS text
LANGUAGE sql AS $$
  SELECT s.codice_interno FROM vendite.ordini o
    JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
   WHERE o.id = p_ordine
$$;

-- La commessa del cliente, come la apre il push; l'invio di una riga del
-- lister dalla madre, come l'orchestratore (causale compresa).
CREATE TEMP TABLE _comm AS
SELECT vendite.fn_get_or_create_commessa(
         p_billing_account_id     => (SELECT billing_account_id FROM _m),
         p_utility_id             => (SELECT utility_id FROM _m),
         p_tipo_commessa          => 'AUTO',
         p_policy_fatturazione    => 'DA_DOCUMENTO',
         p_fatturazione_immediata => false,
         p_priorita_operativa     => 'NORMALE',
         p_competenza_dal         => date_trunc('month', script.fn_data_operativa())::date,
         p_competenza_al          => (date_trunc('month', script.fn_data_operativa())
                                      + interval '1 month - 1 day')::date,
         p_meta                   => '{}'::jsonb,
         p_force_new              => true) AS id;

CREATE OR REPLACE FUNCTION pg_temp.invia(v jsonb) RETURNS bigint AS $$
  SELECT u.attivita_id
    FROM vendite.fn_upsert_commessa_attivita(
      p_commessa_id                   => (SELECT id FROM _comm),
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
      p_tipo_doc_fiscale_id           => (v ->> 'tipo_doc_fiscale_id')::bigint,
      p_valuta_id                     => (v ->> 'valuta_id')::integer,
      p_prezzo_bloccato               => (v ->> 'prezzo_bloccato')::boolean,
      p_pricing_mode                  => (v ->> 'pricing_mode')::varchar,
      p_stato_approvazione            => 'BOZZA',
      p_stato_emissione               => 'NON_EMESSA',
      p_sorgente_tipo_id              => (v ->> 'sorgente_tipo_id')::bigint,
      p_sorgente_uid                  => v ->> 'sorgente_uid',
      p_tipo_movimento                => (v ->> 'tipo_movimento')::varchar,
      p_meta                          => COALESCE(v -> 'meta', '{}'::jsonb),
      p_causale_onere_id              => (v ->> 'causale_onere_id')::bigint) u
$$ LANGUAGE sql;

-- ============================================================
-- A — la copia: ordine alla consegna, merce 10 + onere 1
-- ============================================================
CREATE TEMP TABLE _oa AS SELECT pg_temp.ordine('pgTAP OCP A', 'CONSEGNATO', 10, 1) AS id;

-- Prima bolla: l'operatore sceglie solo la merce, 4.
CREATE TEMP TABLE _ba1 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP OCP A1', 'CONSEGNATO',
         p_ordine_id => (SELECT id FROM _oa),
         p_righe => jsonb_build_array(jsonb_build_object(
             'ordine_riga_id', pg_temp.riga_ord((SELECT id FROM _oa), false),
             'qta_da_evadere', 4)));

SELECT is(
  (SELECT count(*) FROM vendite.ddt_righe dr WHERE dr.ddt_id = (SELECT ddt_id FROM _ba1) AND dr.attivo)::text
    || '|' || (pg_temp.riga_ddt((SELECT ddt_id FROM _ba1), true) IS NOT NULL)::text,
  '2|true',
  '1) la prima bolla, con la sola merce scelta, porta anche l''onere (K-5)');

SELECT is(
  (SELECT trim_scale(dr.quantita)::text || '|' || trim_scale(f.qta_evasa)::text
     FROM vendite.ddt_righe dr
     JOIN vendite.ordini_righe_fulfillment f ON f.ddt_riga_id = dr.id
    WHERE dr.id = pg_temp.riga_ddt((SELECT ddt_id FROM _ba1), true)),
  '1|1',
  '2) l''onere passa INTERO: quantita'' 1 e legame di 1 (K-4)');

SELECT is(
  (SELECT dr.natura_vendita_id FROM vendite.ddt_righe dr
    WHERE dr.id = pg_temp.riga_ddt((SELECT ddt_id FROM _ba1), true)),
  (SELECT r.natura_vendita_id FROM vendite.ordini_righe r
    WHERE r.id = pg_temp.riga_ord((SELECT id FROM _oa), true)),
  '3) la riga di bolla porta la natura congelata della riga d''ordine-onere');

-- Seconda bolla: tutto il residuo (p_righe NULL).
CREATE TEMP TABLE _ba2 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP OCP A2', 'DRAFT',
         p_ordine_id => (SELECT id FROM _oa));

SELECT is(
  (SELECT count(*) FROM vendite.ddt_righe dr WHERE dr.ddt_id = (SELECT ddt_id FROM _ba2) AND dr.attivo)::text
    || '|' || (pg_temp.riga_ddt((SELECT ddt_id FROM _ba2), true) IS NULL)::text,
  '1|true',
  '4) la seconda bolla porta solo la merce: l''onere e'' gia'' passato (residuo 0)');

SELECT is(
  pg_temp.stato_ordine((SELECT id FROM _oa)),
  'EVASO',
  '5) con la merce tutta spedita l''ordine e'' EVASO: l''onere non decide l''evasione');

-- ============================================================
-- B — i rifiuti della copia
-- ============================================================
CREATE TEMP TABLE _ob AS SELECT pg_temp.ordine('pgTAP OCP B', 'CONFERMATO', 2, 2) AS id;

SELECT is(
  pg_temp.codice(format(
    'SELECT vendite.fn_genera_ddt_da_ordine(%s, %L::jsonb)',
    (SELECT id FROM _ob),
    jsonb_build_array(jsonb_build_object(
        'ordine_riga_id', pg_temp.riga_ord((SELECT id FROM _ob), true),
        'qta_da_evadere', 2))::text)),
  'E_DDT_NIENTE_DA_EVADERE',
  '6) una bolla che porterebbe solo oneri non si genera: E_DDT_NIENTE_DA_EVADERE (K-2)');

-- Un legame scritto a mano su una bolla senza ordine, per meta' dell'onere.
CREATE TEMP TABLE _bc AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('pgTAP OCP C', 'DRAFT',
         (SELECT billing_account_id FROM _m));
INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, prezzo_unitario, iva_id)
VALUES ((SELECT ddt_id FROM _bc), 2, (SELECT onere FROM _a), 'Fixture pgTAP: onere a mano', 1, 15,
        (SELECT i.id FROM config.iva i WHERE i.attivo ORDER BY i.id LIMIT 1));

SELECT is(
  pg_temp.codice(format(
    'INSERT INTO vendite.ordini_righe_fulfillment (ordine_riga_id, ddt_riga_id, qta_evasa) VALUES (%s, %s, 1)',
    pg_temp.riga_ord((SELECT id FROM _ob), true),
    pg_temp.riga_ddt((SELECT ddt_id FROM _bc), true))),
  'E_ORD_FUL_ONERE_NON_INTERO',
  '7) un legame parziale sull''onere (1 di 2) si rifiuta: E_ORD_FUL_ONERE_NON_INTERO');

-- ============================================================
-- C — l'annullo della bolla ritira il legame
-- ============================================================
CREATE TEMP TABLE _oh AS SELECT pg_temp.ordine('pgTAP OCP H', 'CONSEGNATO', 3, 1) AS id;
CREATE TEMP TABLE _bh AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP OCP H1', 'EMESSO',
         p_ordine_id => (SELECT id FROM _oh));
-- Due legami (merce e onere): l'annullo li vuole confermati.
SELECT vendite.fn_annulla_ddt((SELECT ddt_id FROM _bh), 2);
CREATE TEMP TABLE _bh2 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP OCP H2', 'DRAFT',
         p_ordine_id => (SELECT id FROM _oh));

SELECT is(
  (SELECT count(*) FROM vendite.ordini_righe_fulfillment f
    WHERE f.ordine_riga_id = pg_temp.riga_ord((SELECT id FROM _oh), true)
      AND f.ddt_riga_id <> COALESCE(pg_temp.riga_ddt((SELECT ddt_id FROM _bh2), true), 0))::text
    || '|' || (pg_temp.riga_ddt((SELECT ddt_id FROM _bh2), true) IS NOT NULL)::text,
  '0|true',
  '8) annullata la bolla il legame dell''onere si ritira, e la bolla nuova lo riporta');

-- ============================================================
-- D — push dell'ordine che fattura alla conferma
-- ============================================================
CREATE TEMP TABLE _lo AS
SELECT to_jsonb(x) AS v
  FROM vendite.fn_list_ordini_da_pushare(p_ordine_id => (SELECT id FROM _ob)) x;

SELECT is(
  (SELECT (l.v ->> 'tipo_movimento') || '|' || ((l.v ->> 'causale_onere_id')::bigint = (SELECT id FROM _caus))::text
     FROM _lo l WHERE (l.v ->> 'riga_id')::bigint = pg_temp.riga_ord((SELECT id FROM _ob), true)),
  'ONERE|true',
  '9) push dell''ordine alla conferma: l''onere esce ONERE con la causale dell''articolo (K-1)');

SELECT is(
  (SELECT (l.v ->> 'tipo_movimento') || '|' || COALESCE(l.v ->> 'causale_onere_id', 'NULL')
     FROM _lo l WHERE (l.v ->> 'riga_id')::bigint = pg_temp.riga_ord((SELECT id FROM _ob), false)),
  'NORMALE|NULL',
  '10) ...e la merce esce NORMALE, senza causale');

-- ⚠️ La riga scritta si legge DOPO, in un'istruzione sua: la madre scrive
--    dentro la SELECT e la stessa istruzione non vedrebbe la riga.
CREATE TEMP TABLE _io AS
SELECT pg_temp.invia(l.v) AS id FROM _lo l WHERE l.v ->> 'tipo_movimento' = 'ONERE';

SELECT is(
  (SELECT ca.tipo_movimento || '|' || (ca.causale_onere_id = (SELECT id FROM _caus))::text
          || '|' || s.codice_interno
          || '|' || (ca.sorgente_uid = (SELECT o.uid::text FROM vendite.ordini o WHERE o.id = (SELECT id FROM _ob)))::text
     FROM _io i
     JOIN vendite.commesse_attivita ca ON ca.id = i.id
     JOIN config.sorgenti s ON s.id = ca.sorgente_tipo_id),
  'ONERE|true|ORDINE_VENDITA|true',
  '11) dal lister alla madre: in commessa l''onere e'' ONERE, con la causale e l''ordine come sorgente');

-- La bolla di quell'ordine: l'onere copiato ha il legame, il trigger e' CONFERMATO.
CREATE TEMP TABLE _bb AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP OCP B1', 'CONSEGNATO',
         p_ordine_id => (SELECT id FROM _ob));

SELECT is(
  (SELECT g.motivo FROM vendite.fn_ddt_push_diagnosi((SELECT ddt_id FROM _bb)) g
    WHERE g.riga_id = pg_temp.riga_ddt((SELECT ddt_id FROM _bb), true))
    || '|' || (SELECT count(*) FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL, (SELECT ddt_id FROM _bb)))::text,
  'DDT_FATTURA_DA_ORDINE|0',
  '12) l''onere copiato su una bolla di un ordine alla conferma non si pusha dalla bolla (lo fattura l''ordine)');

-- ============================================================
-- E — push della bolla che fattura alla consegna (la prima bolla di A)
-- ============================================================
SELECT is(
  (SELECT COALESCE(g.motivo, 'NULL') || '|' || trim_scale(g.quantita_push)::text
     FROM vendite.fn_ddt_push_diagnosi((SELECT ddt_id FROM _ba1)) g
    WHERE g.riga_id = pg_temp.riga_ddt((SELECT ddt_id FROM _ba1), true)),
  'NULL|1',
  '13) la diagnosi: l''onere della bolla consegnata e'' eleggibile, dose = la sua quantita'' (non DDT_SENZA_PARTITA)');

CREATE TEMP TABLE _ld AS
SELECT to_jsonb(x) AS v
  FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL, (SELECT ddt_id FROM _ba1)) x;

SELECT is(
  (SELECT (l.v ->> 'tipo_movimento') || '|' || ((l.v ->> 'causale_onere_id')::bigint = (SELECT id FROM _caus))::text
          || '|' || trim_scale((l.v ->> 'quantita')::numeric)::text
          || '|' || (l.v ->> 'sorgente_uid' = (SELECT ddt_uid::text FROM _ba1))::text
     FROM _ld l WHERE (l.v ->> 'riga_id')::bigint = pg_temp.riga_ddt((SELECT ddt_id FROM _ba1), true)),
  'ONERE|true|1|true',
  '14) il lister della bolla: l''onere esce ONERE, con la causale, quantita'' 1, sorgente la bolla');

CREATE TEMP TABLE _id AS
SELECT pg_temp.invia(l.v) AS id FROM _ld l WHERE l.v ->> 'tipo_movimento' = 'ONERE';

SELECT is(
  (SELECT ca.tipo_movimento || '|' || (ca.causale_onere_id = (SELECT id FROM _caus))::text
          || '|' || s.codice_interno
          || '|' || (ca.sorgente_uid = (SELECT ddt_uid::text FROM _ba1))::text
     FROM _id i
     JOIN vendite.commesse_attivita ca ON ca.id = i.id
     JOIN config.sorgenti s ON s.id = ca.sorgente_tipo_id),
  'ONERE|true|DDT_VENDITA|true',
  '15) dal lister alla madre: in commessa l''onere e'' ONERE, con la causale e la bolla come sorgente');

SELECT is(
  (SELECT (l.v ->> 'tipo_movimento') || '|' || COALESCE(l.v ->> 'causale_onere_id', 'NULL')
          || '|' || trim_scale((l.v ->> 'quantita')::numeric)::text
     FROM _ld l WHERE (l.v ->> 'riga_id')::bigint = pg_temp.riga_ddt((SELECT ddt_id FROM _ba1), false)),
  'NORMALE|NULL|4',
  '16) la merce della stessa bolla esce NORMALE, con la dose della partita (4)');

SELECT ok(
  EXISTS (SELECT 1 FROM pg_proc p
           WHERE p.oid = 'vendite.fn_list_ddt_da_pushare(date,bigint,integer,bigint)'::regprocedure
             AND 'causale_onere_id' = ANY (p.proargnames))
  AND EXISTS (SELECT 1 FROM pg_proc p
           WHERE p.oid = 'vendite.fn_list_ordini_da_pushare(date,bigint,integer,bigint)'::regprocedure
             AND 'causale_onere_id' = ANY (p.proargnames)),
  '17) i due lister espongono causale_onere_id (il contratto col backend, PushableRow)');

SELECT * FROM finish();
ROLLBACK;
