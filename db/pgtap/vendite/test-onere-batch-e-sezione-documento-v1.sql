-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il percorso intero dell'onere fino alla fattura, dal wrapper batch
--   che usa il backend (non dalla madre chiamata a mano), e la sezione del
--   documento sulle tre letture di riga.
--   vendite.fn_batch_upsert_commessa_attivita (causale_onere_id dal payload),
--   vendite.vw_ordini_righe_dettaglio, vendite.vw_ddt_righe_dettaglio,
--   vendite.vw_fattura_righe_lista (tipo_movimento, e_onere, causale_onere_id,
--   sezione_documento).
-- ChangeSet: 20261103-49 (batch), -50 (fattura), -51 (ordine), -52 (bolla)
-- Brief: brief-db-addebito-trasporto-ordine §9.8 (richiesta BE, punti 1 e 2)
-- ------------------------------------------------------------
-- Indice test (plan 10):
--  A — l'ordine alla conferma, onere alla riga 1 e merce alla 2, spinto dal BATCH
--   1) ⭐ il batch inserisce le due righe, senza errori (prima: l'onere era
--      rifiutato, la causale non arrivava alla madre)
--   2) …la riga dell'onere e' ONERE, con la causale dell'articolo e la sorgente
--   3) controllo: la stessa riga SENZA la chiave causale_onere_id e' un errore
--      raccolto dal batch (la madre vuole ONERE <=> causale)
--  B — la sezione del documento
--   4) righe d'ordine: onere 2, merce 1
--   5) righe di bolla (l'onere copiato dall'ordine): onere 2, merce 1
--  C — la fattura delle due attivita' (onere prima, merce dopo)
--   6) riga dell'onere: e_onere, tipo_movimento ONERE, causale, sezione 2
--   7) riga della merce: non onere, NORMALE, sezione 1
--   8) ⭐ l'ordine del documento (sezione_documento, ordinamento, riga_nr):
--      l'onere, alla riga 1, sta in fondo
--   9) ordine del documento d'ordine (sezione_documento, riga_nr): onere in fondo
--  10) le colonne nuove sono in coda alla vista della fattura
-- ------------------------------------------------------------

BEGIN;

CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP onere batch sezione');
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(10);

CREATE TEMP TABLE _caus AS
WITH ins AS (
    INSERT INTO config.causali_onere (codice_interno, codice, descrizione)
    VALUES ('PGT_OBS_1', 'PGT_OBS_1', 'Fixture pgTAP: onere batch sezione')
    RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE _a AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-OBS-ONERE', false,
         p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                                  WHERE nv.codice_interno = 'SERVIZIO_UNA_TANTUM'),
         p_causale_onere_id  => (SELECT id FROM _caus)) AS onere,
       dbops.fn_pgtap_crea_articolo('PGT-OBS-MERCE', false) AS merce;

-- Ordine alla conferma: l'onere alla riga 1, la merce alla 2.
CREATE TEMP TABLE _o AS
SELECT o.ordine_id AS id
  FROM dbops.fn_pgtap_crea_ordine_con_righe('pgTAP OBS', 'CONFERMATO',
         (SELECT billing_account_id FROM _m),
         p_fatturazione_trigger => 'CONFERMATO',
         p_righe => jsonb_build_array(
             jsonb_build_object('articolo_id', (SELECT onere FROM _a), 'quantita', 1, 'prezzo', 15),
             jsonb_build_object('articolo_id', (SELECT merce FROM _a), 'quantita', 3, 'prezzo', 5))) o;

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

-- Il payload come lo compone il backend: le righe del lister, piu' la
-- commessa e lo stato. Approvate, perche' la fattura del caso C le emette.
CREATE TEMP TABLE _payload AS
SELECT jsonb_agg(to_jsonb(l) || jsonb_build_object(
           'commessa_id',        (SELECT id FROM _comm),
           'stato_approvazione', 'APPROVATA',
           'stato_emissione',    'NON_EMESSA') ORDER BY l.riga_id) AS righe
  FROM vendite.fn_list_ordini_da_pushare(p_ordine_id => (SELECT id FROM _o)) l;

CREATE TEMP TABLE _b AS
SELECT * FROM vendite.fn_batch_upsert_commessa_attivita((SELECT righe FROM _payload));

-- ============================================================
-- A — il push dal batch
-- ============================================================
SELECT is(
  (SELECT inserted::text || '|' || errors::text FROM _b),
  '2|[]',
  '1) il batch inserisce onere e merce, senza errori (prima: l''onere rifiutato, causale persa)');

CREATE TEMP TABLE _ca AS
SELECT ca.id, ca.articolo_id, ca.tipo_movimento, ca.causale_onere_id, ca.sorgente_uid
  FROM vendite.commesse_attivita ca
 WHERE ca.commessa_id = (SELECT id FROM _comm);

SELECT is(
  (SELECT c.tipo_movimento || '|' || (c.causale_onere_id = (SELECT id FROM _caus))::text || '|'
          || (c.sorgente_uid = (SELECT o.uid::text FROM vendite.ordini o WHERE o.id = (SELECT id FROM _o)))::text
     FROM _ca c WHERE c.articolo_id = (SELECT onere FROM _a)),
  'ONERE|true|true',
  '2) la riga dell''onere: ONERE, con la causale dell''articolo e la sorgente dell''ordine');

SELECT is(
  (SELECT jsonb_array_length(b.errors)
     FROM vendite.fn_batch_upsert_commessa_attivita((
            SELECT jsonb_build_array(
                     (r - 'causale_onere_id')
                     || jsonb_build_object('segment_key', (r ->> 'segment_key') || '#PGT'))
              FROM jsonb_array_elements((SELECT righe FROM _payload)) r
             WHERE r ->> 'tipo_movimento' = 'ONERE')) b),
  1,
  '3) controllo: la riga ONERE senza causale_onere_id e'' un errore raccolto (ONERE <=> causale)');

-- ============================================================
-- B — la sezione del documento su ordine e bolla
-- ============================================================
SELECT is(
  (SELECT string_agg(d.sezione_documento::text, ',' ORDER BY d.riga_nr)
     FROM vendite.vw_ordini_righe_dettaglio d WHERE d.ordine_id = (SELECT id FROM _o)),
  '2,1',
  '4) righe d''ordine: l''onere (riga 1) in sezione 2, la merce (riga 2) in sezione 1');

CREATE TEMP TABLE _d AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgTAP OBS bolla', 'DRAFT',
         p_ordine_id => (SELECT id FROM _o));

SELECT is(
  (SELECT string_agg(d.e_onere::text || ':' || d.sezione_documento::text, ',' ORDER BY d.e_onere)
     FROM vendite.vw_ddt_righe_dettaglio d WHERE d.ddt_id = (SELECT ddt_id FROM _d) AND d.attivo),
  'false:1,true:2',
  '5) righe di bolla: la merce in sezione 1, l''onere copiato in sezione 2');

-- ============================================================
-- C — la fattura delle due attivita', l'onere per primo
-- ============================================================
CREATE TEMP TABLE _f AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('pgTAP OBS fattura',
         ARRAY[(SELECT id FROM _ca WHERE articolo_id = (SELECT onere FROM _a)),
               (SELECT id FROM _ca WHERE articolo_id = (SELECT merce FROM _a))]);

SELECT is(
  (SELECT l.e_onere::text || '|' || l.tipo_movimento || '|'
          || (l.causale_onere_id = (SELECT id FROM _caus))::text || '|' || l.sezione_documento::text
     FROM vendite.vw_fattura_righe_lista l
    WHERE l.fattura_id = (SELECT DISTINCT fattura_id FROM _f) AND l.articolo_id = (SELECT onere FROM _a)),
  'true|ONERE|true|2',
  '6) fattura, riga dell''onere: e_onere, ONERE, la sua causale, sezione 2');

SELECT is(
  (SELECT l.e_onere::text || '|' || l.tipo_movimento || '|' || coalesce(l.causale_onere_id::text, 'NULL')
          || '|' || l.sezione_documento::text
     FROM vendite.vw_fattura_righe_lista l
    WHERE l.fattura_id = (SELECT DISTINCT fattura_id FROM _f) AND l.articolo_id = (SELECT merce FROM _a)),
  'false|NORMALE|NULL|1',
  '7) fattura, riga della merce: non onere, NORMALE, sezione 1');

SELECT is(
  (SELECT string_agg(a.codice, ',' ORDER BY l.sezione_documento, l.ordinamento, l.riga_nr)
          || ' / onere alla riga ' || min(l.riga_nr) FILTER (WHERE l.e_onere)::text
     FROM vendite.vw_fattura_righe_lista l
     JOIN catalogo.articoli a ON a.id = l.articolo_id
    WHERE l.fattura_id = (SELECT DISTINCT fattura_id FROM _f)),
  'PGT-OBS-MERCE,PGT-OBS-ONERE / onere alla riga 1',
  '8) l''ordine del documento della fattura mette l''onere (riga 1) in fondo');

SELECT is(
  (SELECT string_agg(d.articolo_codice, ',' ORDER BY d.sezione_documento, d.riga_nr)
     FROM vendite.vw_ordini_righe_dettaglio d WHERE d.ordine_id = (SELECT id FROM _o)),
  'PGT-OBS-MERCE,PGT-OBS-ONERE',
  '9) l''ordine del documento d''ordine mette l''onere in fondo');

-- Le colonne nuove in coda: CREATE OR REPLACE VIEW non le accetta altrove, e il
-- backend le legge per nome.
SELECT is(
  (SELECT string_agg(c.column_name::text, ',' ORDER BY c.ordinal_position)
     FROM information_schema.columns c
    WHERE c.table_schema = 'vendite' AND c.table_name = 'vw_fattura_righe_lista'
      AND c.ordinal_position > (SELECT max(c2.ordinal_position) - 4
                                  FROM information_schema.columns c2
                                 WHERE c2.table_schema = 'vendite'
                                   AND c2.table_name = 'vw_fattura_righe_lista')),
  'tipo_movimento,e_onere,causale_onere_id,sezione_documento',
  '10) vw_fattura_righe_lista: le quattro colonne nuove in coda');

SELECT * FROM finish();
ROLLBACK;
