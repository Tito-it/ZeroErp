-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: tornare indietro — annullare la commessa riapre a monte, con la
--   segnalazione; il verso in avanti verso la commessa dal DB.
--   vendite.fn_annulla_commessa, vendite.fn_documento_legami('COMMESSA'),
--   vendite.fn_documento_ritira_legami (ramo COMMESSA, «prima cio' che
--   vieta»), vendite.fn_preventivo_proietta_stato_smistamento e il trigger
--   sulle righe di commessa, vendite.fn_rendi_commessa_emittibile,
--   script.fn_get_stato_push_segment (una riga ANNULLATA non occupa), le
--   viste del preventivo e la primitiva del ritiro limitata a una commessa.
-- ChangeSet: 20261012-08 … -24; 20261012-43 … -47 (il link documento -> commessa
--   nasce con la riga e conta solo la commessa aperta: §10 del brief)
-- Brief: brief-db-annullo-a-valle-riapre-a-monte (D-1 … D-10, D-12, D-13)
-- ------------------------------------------------------------
-- Indice test (plan 37):
--  A — la forma
--   1) gli oggetti nuovi esistono, i tre trigger sono montati, la primitiva
--      del ritiro ha il quarto parametro
--  B — preventivo -> commessa, andata e ritorno (D-1, D-5, D-10)
--   2) l'invio (lister + madre delle righe): il preventivo diventa EVASO DAL DB
--   2b) e la madre ha scritto il link documento -> commessa (D-13), ROOT
--   3) il pannello dice IN_COMMESSA per la riga mandata e non ancora emessa
--   4) dopo l'invio la commessa diventa emittibile dal DB: righe approvate,
--      PRONTA_FATTURAZIONE
--   5) il lettore della commessa: un legame PREVENTIVO di consumo
--   6) l'etichetta della commessa dal lettore di testata
--   7) l'annullo dal verbo di stato (la strada del backend) e' rifiutato:
--      E_DOC_ANNULLO_CON_LEGAMI
--   8) il verbo con una conferma che non corrisponde: stesso rifiuto
--   9) confermato: il verbo restituisce il legame
--  10) commessa ANNULLATA, riga ANNULLATA col registro
--  11) il preventivo torna ACCETTATO, la riga torna da mandare (residuo,
--      classificatore LIBERA, pannello RESIDUA), nessun legame verso la
--      commessa morta
--  12) un secondo invio in una commessa nuova riesce e riporta il preventivo EVASO
--      (dal 20261012-46 passa dalla porta del link: e' la prova del §10)
--  12b) il link verso la commessa annullata resta come storia; la commessa
--      aperta del documento e' la nuova
--  C — ordine -> commessa (D-6)
--  13) l'invio non cambia lo stato dell'ordine, e l'ordine non e' piu' da mandare
--  14) annullata la commessa con conferma, l'ordine resta CONFERMATO e torna da mandare
--  14c) con la sola commessa annullata il flag di fatturazione immediata
--      dell'ordine si cambia (D-14, 20261012-47)
--  14b) e si rimanda in una commessa nuova: chiave id::text, due link, una commessa aperta
--  14d) con la commessa nuova aperta il flag si blocca di nuovo
--  D — preventivo misto (§7.4 del brief)
--  15) merce all'ordine, servizi in commessa: EVASO solo quando tutte e due le strade sono vuote
--  16) annullata la commessa: ACCETTATO, l'ordine resta vivo con la sua riga
--  E — una sorgente in due commesse APERTE (D-12)
--  17) rifiutato: E_COMMESSA_SORGENTE_ALTRA_COMMESSA, e nella seconda non si scrive
--      niente (ne' la riga ne' il link)
--  17b) annullata la prima, le due righe vanno nella seconda e il preventivo e' EVASO
--  ⚠️ Fino al 20261012-46 questo caso metteva lo stesso preventivo in due
--    commesse vive e controllava la primitiva del ritiro limitata a una
--    commessa (20261012-18): era uno stato che il percorso vero non produce,
--    perche' il link lo scriveva il backend e qui non passava (§10.6 del
--    brief). La primitiva limitata resta: il verbo le passa la sua commessa.
--  ⚠️ CHIUSA e ANNULLATA hanno lo stesso chiude_commessa = true, ed e' quello
--    che la porta legge: il caso «invio parziale, commessa CHIUSA, invio del
--    resto» attraversa lo stesso ramo del 12, e qui non si costruisce (vorrebbe
--    la catena fino alla fattura).
--  F — gli oneri (D-7)
--  18) il legame dell'onere: ONERE, natura ANNULLO
--  19) l'annullo diretto e' rifiutato anche con i soli oneri
--  20) confermato: onere ANNULLATO col suo registro
--  G — prima cio' che vieta (D-3)
--  21) commessa con righe EMESSE: il verbo senza conferma parla di righe
--      emesse, non chiede la conferma
--  22) e non ha toccato niente: le righe non emesse restano NON_EMESSA
--  23) preventivo con un ordine vivo e righe in commessa: fn_annulla_preventivo
--      senza conferma solleva ORDINE_GIA_GENERATO, non la conferma
--  H — senza legami
--  24) una commessa vuota si annulla dal verbo senza conferma: 0 legami
--  I — i lettori del «gia' mandato» parlano una lingua sola (D-5)
--  25) classificatore: una riga ANNULLATA non occupa
--  26) classificatore: EMESSA + rettifica ANNULLATA -> EMESSA
--  27) vista smistabili e residuo dicono la stessa cosa del classificatore
--  J — il trigger tocca solo i preventivi
--  28) una riga di un'altra sorgente non muove il preventivo
--  K — la proiezione negli altri stati
--  29) un preventivo DRAFT con una riga che cambia stato non si muove
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO: cliente, articoli, preventivi, ordini e
--   commesse dai builder e dai verbi del dominio; l'invio in commessa come lo
--   fa l'orchestratore (il lister della sorgente, poi la madre delle righe).
--   Nessun documento preso dai dati.
-- ⚠️ IL RAMO RETTIFICA (il reso torna da accreditare) e' in un file suo,
--   vendite/test-annullo-commessa-rettifica-v1: vuole la catena ordine,
--   bolla, fattura, reso, accredito e il reset della riga fatturata.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: qui il COMMIT non arriva mai, e senza IMMEDIATE non
--   verrebbero esercitati.
SET CONSTRAINTS ALL IMMEDIATE;

-- Il test gira come l'applicazione (OPERATORE + RLS attiva).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(37);

-- ============================================================
-- A — La forma
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname, p.proname) IN (('vendite', 'fn_annulla_commessa'),
                                     ('vendite', 'fn_preventivo_proietta_stato_smistamento'),
                                     ('vendite', 'trgfn_commesse_attivita_proietta_stato_preventivo'),
                                     ('vendite', 'fn_rendi_commessa_emittibile')))
  + (SELECT count(*)::int FROM pg_trigger t
      WHERE NOT t.tgisinternal
        AND (t.tgrelid, t.tgname) IN (
              ('vendite.commesse'::regclass,          'trg_commesse_m10_guard_annullo_con_legami_upd'),
              ('vendite.commesse_attivita'::regclass, 'trg_commesse_attivita_z90_proietta_stato_preventivo_ins_dlt'),
              ('vendite.commesse_attivita'::regclass, 'trg_commesse_attivita_z90_proietta_stato_preventivo_upd')))
  + (SELECT max(p.pronargs)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite' AND p.proname = 'fn_ritira_commessa_attivita_da_sorgente'),
  11,
  '1) quattro funzioni nuove, tre trigger montati, la primitiva del ritiro con quattro parametri');

-- ============================================================
-- Fixture — COSTRUITE
-- ============================================================
CREATE TEMP TABLE tmp_ac_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'annullo commessa',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_ac_refs AS
SELECT
  c.billing_account_id, c.istanza_utility_id, c.utility_id, c.soggetto_ruolo_id,
  script.fn_pgtap_emittente_operatore()                                                   AS emittente_fiscale_id,
  -- La natura di riga la da' l'articolo: uno per strada, scelta alla nascita.
  dbops.fn_pgtap_crea_articolo('PGT-AC-MERCE', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'MERCE'))                         AS art_merce_id,
  dbops.fn_pgtap_crea_articolo('PGT-AC-SERV', false,
      p_natura_vendita_id => (SELECT id FROM config.nature_vendita
                               WHERE codice_interno = 'SERVIZIO_UNA_TANTUM'))           AS art_serv_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)            AS iva_id,
  (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT')       AS prev_draft_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'DRAFT')           AS ord_draft_id,
  (SELECT s.id FROM vendite.stati_commessa s WHERE s.codice_interno = 'ANNULLATA')        AS cm_annullata_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA')                AS sorg_commessa_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo ORDER BY t.id LIMIT 1)       AS tipo_doc_fiscale_id
FROM tmp_ac_cli c;

CREATE TEMP TABLE tmp_ac_fix(chiave text PRIMARY KEY, id bigint);
CREATE TEMP TABLE tmp_ac_esito(caso text PRIMARY KEY, sqlstate text, messaggio text, righe int);

CREATE OR REPLACE FUNCTION pg_temp.ac_fix(p_chiave text) RETURNS bigint
  AS $$ SELECT id FROM tmp_ac_fix WHERE chiave = p_chiave $$ LANGUAGE sql;

-- Esegue un'istruzione e ne cattura l'esito (righe toccate, o SQLSTATE + frase).
CREATE OR REPLACE FUNCTION pg_temp.ac_prova(p_caso text, p_sql text)
RETURNS void AS $$
DECLARE v_n int;
BEGIN
  BEGIN
    EXECUTE p_sql;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO tmp_ac_esito VALUES (p_caso, NULL, NULL, v_n);
  EXCEPTION WHEN OTHERS THEN
    INSERT INTO tmp_ac_esito VALUES (p_caso, SQLSTATE, SQLERRM, NULL);
  END;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.ac_rifiuto(p_caso text, p_frammento text) RETURNS boolean AS $$
  SELECT COALESCE(e.sqlstate = 'P0001' AND e.messaggio LIKE '%' || p_frammento || '%', false)
    FROM tmp_ac_esito e WHERE e.caso = p_caso
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION pg_temp.ac_stato(p_tabella text, p_id bigint) RETURNS text AS $$
DECLARE v text;
BEGIN
  EXECUTE CASE p_tabella
            WHEN 'ordini'     THEN 'SELECT s.codice_interno FROM vendite.ordini t JOIN config.stati_doc_ordini s ON s.id = t.stato_doc_ordine_id WHERE t.id = $1'
            WHEN 'preventivi' THEN 'SELECT s.codice_interno FROM vendite.preventivi t JOIN config.stati_doc_preventivi s ON s.id = t.stato_doc_preventivo_id WHERE t.id = $1'
            WHEN 'commesse'   THEN 'SELECT s.codice_interno FROM vendite.commesse t JOIN vendite.stati_commessa s ON s.id = t.stato_commessa_id WHERE t.id = $1'
          END
     INTO v USING p_id;
  RETURN v;
END $$ LANGUAGE plpgsql;

-- Un preventivo con p_merce righe MERCE e p_serv righe di servizio, nato
-- DRAFT (le righe si scrivono in bozza) e portato ACCETTATO.
CREATE OR REPLACE FUNCTION pg_temp.ac_mk_preventivo(p_chiave text, p_merce int, p_serv int,
                                                    p_stato text DEFAULT 'ACCETTATO')
RETURNS void AS $$
DECLARE r RECORD; v_prev bigint; v_riga bigint; i int;
BEGIN
  SELECT * INTO r FROM tmp_ac_refs;
  INSERT INTO vendite.preventivi (rev, billing_account_id, istanza_utility_id, utility_id,
      validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
      fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  VALUES (0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
          script.fn_data_operativa(), script.fn_data_operativa() + 30, r.valuta_id, r.prev_draft_id,
          script.fn_data_operativa(), false, false,
          jsonb_build_object('test_scope', 'pgtap_annullo_commessa'), r.emittente_fiscale_id)
  RETURNING id INTO v_prev;
  INSERT INTO tmp_ac_fix VALUES (p_chiave || '_prev', v_prev);
  FOR i IN 1 .. p_merce LOOP
    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario,
        iva_id, attivo, meta)
    VALUES (v_prev, r.art_merce_id, 4, 25, r.iva_id, true,
            jsonb_build_object('test_scope', 'pgtap_annullo_commessa'))
    RETURNING id INTO v_riga;
    INSERT INTO tmp_ac_fix VALUES (p_chiave || '_m' || i, v_riga);
  END LOOP;
  FOR i IN 1 .. p_serv LOOP
    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario,
        iva_id, attivo, meta)
    VALUES (v_prev, r.art_serv_id, 2, 30, r.iva_id, true,
            jsonb_build_object('test_scope', 'pgtap_annullo_commessa'))
    RETURNING id INTO v_riga;
    INSERT INTO tmp_ac_fix VALUES (p_chiave || '_s' || i, v_riga);
  END LOOP;
  IF p_stato <> 'DRAFT' THEN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', v_prev, p_stato);
  END IF;
END $$ LANGUAGE plpgsql;

-- Un ordine CONFERMATO con una riga MERCE, fatturato alla conferma (il
-- lister della commessa vuole fatturazione_trigger = CONFERMATO).
CREATE OR REPLACE FUNCTION pg_temp.ac_mk_ordine(p_chiave text) RETURNS void AS $$
DECLARE r RECORD; v_ord bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_ac_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, fatturazione_trigger, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.emittente_fiscale_id, r.ord_draft_id,
          r.valuta_id, script.fn_data_operativa(), 'CONFERMATO', false,
          jsonb_build_object('test_scope', 'pgtap_annullo_commessa'))
  RETURNING id INTO v_ord;
  UPDATE vendite.ordini SET fatturazione_trigger = 'CONFERMATO' WHERE id = v_ord;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
      qta_operativa, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.art_merce_id, 'Riga annullo commessa pgTAP', 3, 40, r.iva_id, true, false,
          jsonb_build_object('test_scope', 'pgtap_annullo_commessa'))
  RETURNING id INTO v_riga;
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', v_ord, 'CONFERMATO');
  INSERT INTO tmp_ac_fix VALUES (p_chiave || '_ord', v_ord), (p_chiave || '_ord_riga', v_riga);
END $$ LANGUAGE plpgsql;

-- Una commessa nuova del cliente (come il push: fn_get_or_create_commessa).
CREATE OR REPLACE FUNCTION pg_temp.ac_mk_commessa(p_chiave text) RETURNS bigint AS $$
DECLARE r RECORD; v bigint;
BEGIN
  SELECT * INTO r FROM tmp_ac_refs;
  v := vendite.fn_get_or_create_commessa(
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
         p_force_new              => true);
  INSERT INTO tmp_ac_fix VALUES (p_chiave, v);
  RETURN v;
END $$ LANGUAGE plpgsql;

-- L'invio in commessa come lo fa l'orchestratore: le righe del lister della
-- sorgente, scritte dalla madre delle righe. Ritorna gli id delle righe.
CREATE OR REPLACE FUNCTION pg_temp.ac_invia(p_sorgente text, p_id bigint, p_commessa bigint,
                                            p_righe bigint[] DEFAULT NULL)
RETURNS bigint[] AS $$
DECLARE v jsonb; v_ids bigint[] := ARRAY[]::bigint[]; v_id bigint;
BEGIN
  FOR v IN
    SELECT to_jsonb(x) FROM vendite.fn_list_preventivi_da_pushare(
             p_preventivo_id => p_id, p_righe_ids => p_righe) x
     WHERE p_sorgente = 'PREVENTIVO'
    UNION ALL
    SELECT to_jsonb(x) FROM vendite.fn_list_ordini_da_pushare(p_ordine_id => p_id) x
     WHERE p_sorgente = 'ORDINE'
  LOOP
    SELECT u.attivita_id INTO v_id
      FROM vendite.fn_upsert_commessa_attivita(
        p_commessa_id                   => p_commessa,
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
                                                    (SELECT tipo_doc_fiscale_id FROM tmp_ac_refs)),
        p_valuta_id                     => (v ->> 'valuta_id')::integer,
        p_prezzo_bloccato               => (v ->> 'prezzo_bloccato')::boolean,
        p_pricing_mode                  => (v ->> 'pricing_mode')::varchar,
        p_stato_approvazione            => 'BOZZA',
        p_stato_emissione               => 'NON_EMESSA',
        p_sorgente_tipo_id              => (v ->> 'sorgente_tipo_id')::bigint,
        p_sorgente_uid                  => v ->> 'sorgente_uid',
        p_tipo_movimento                => (v ->> 'tipo_movimento')::varchar,
        p_meta                          => v -> 'meta') u;
    v_ids := v_ids || v_id;
  END LOOP;
  RETURN v_ids;
END $$ LANGUAGE plpgsql;

-- Le righe di commessa NON_EMESSA di un documento, dal lettore unico.
CREATE OR REPLACE FUNCTION pg_temp.ac_legami(p_documento text, p_id bigint) RETURNS int AS $$
  SELECT count(*)::int FROM vendite.fn_documento_legami(p_documento, p_id)
$$ LANGUAGE sql;

-- ============================================================
-- B — preventivo -> commessa, andata e ritorno
-- ============================================================
SELECT pg_temp.ac_mk_preventivo('b', 0, 1);
SELECT pg_temp.ac_mk_commessa('b_cm1');
INSERT INTO tmp_ac_fix
SELECT 'b_ca', (pg_temp.ac_invia('PREVENTIVO', pg_temp.ac_fix('b_prev'), pg_temp.ac_fix('b_cm1')))[1];

SELECT ok(
  pg_temp.ac_fix('b_ca') IS NOT NULL
  AND pg_temp.ac_stato('preventivi', pg_temp.ac_fix('b_prev')) = 'EVASO'
  AND NOT vendite.fn_preventivo_ha_residuo_commessa(pg_temp.ac_fix('b_prev')),
  '2) l''invio in commessa: il preventivo diventa EVASO dal DB, senza residuo');

-- Il link lo scrive la madre delle righe (D-13), con la chiave canonica del
-- preventivo (key_selector 'uid': l'uuid).
SELECT ok(
  (SELECT count(*) = 1 AND bool_and(cs.commessa_id = pg_temp.ac_fix('b_cm1') AND cs.ruolo_link = 'ROOT')
     FROM vendite.commesse_sorgenti cs
    WHERE cs.sorgente_tipo_id = (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')
      AND cs.sorgente_uid = (SELECT p.uid::text FROM vendite.preventivi p WHERE p.id = pg_temp.ac_fix('b_prev'))),
  '2b) la madre delle righe ha scritto il link preventivo -> commessa, ROOT (D-13)');

SELECT is(
  (SELECT v.stato_smistamento FROM vendite.vw_preventivi_smistamento_righe v
    WHERE v.riga_id = pg_temp.ac_fix('b_s1')),
  'IN_COMMESSA',
  '3) il pannello: la riga mandata e non ancora emessa e'' IN_COMMESSA (non piu'' RESIDUA)');

SELECT is(
  vendite.fn_rendi_commessa_emittibile(pg_temp.ac_fix('b_cm1'), ARRAY[pg_temp.ac_fix('b_ca')]),
  1,
  '4a) la commessa diventa emittibile dal DB: una riga approvata');
SELECT ok(
  pg_temp.ac_stato('commesse', pg_temp.ac_fix('b_cm1')) = 'PRONTA_FATTURAZIONE'
  AND (SELECT ca.stato_approvazione = 'APPROVATA' FROM vendite.commesse_attivita ca
        WHERE ca.id = pg_temp.ac_fix('b_ca')),
  '4) commessa PRONTA_FATTURAZIONE, riga APPROVATA');

SELECT ok(
  (SELECT count(*) = 1
          AND bool_and(l.origine = 'PREVENTIVO' AND l.natura = 'CONSUMO'
                       AND l.riga_id = pg_temp.ac_fix('b_ca')
                       AND l.origine_id = pg_temp.ac_fix('b_prev'))
     FROM vendite.fn_documento_legami('COMMESSA', pg_temp.ac_fix('b_cm1')) l),
  '5) il lettore della commessa: un legame PREVENTIVO di consumo, verso il preventivo');

SELECT ok(
  (SELECT t.etichetta LIKE 'Commessa %' AND t.stato = 'PRONTA_FATTURAZIONE'
     FROM script.fn_get_stato_testata_documento('COMMESSA', pg_temp.ac_fix('b_cm1')) t),
  '6) il lettore di testata conosce la commessa: «Commessa <codice>» e il suo stato');

SELECT pg_temp.ac_prova('7_verbo_stato',
  format('SELECT * FROM vendite.fn_cambia_stato_commessa(%s, ''ANNULLATA'', NULL)',
         pg_temp.ac_fix('b_cm1')));
SELECT ok(pg_temp.ac_rifiuto('7_verbo_stato', 'Serve una conferma'),
  '7) l''annullo dal verbo di stato (la strada del backend) e'' rifiutato: E_DOC_ANNULLO_CON_LEGAMI');

SELECT pg_temp.ac_prova('8_conferma_errata',
  format('SELECT vendite.fn_annulla_commessa(%s, 0)', pg_temp.ac_fix('b_cm1')));
SELECT ok(pg_temp.ac_rifiuto('8_conferma_errata', 'Serve una conferma'),
  '8) il verbo con una conferma che non corrisponde: stesso rifiuto');

SELECT is(vendite.fn_annulla_commessa(pg_temp.ac_fix('b_cm1'), 1), 1,
  '9) confermato: il verbo restituisce il legame confermato');

SELECT ok(
  pg_temp.ac_stato('commesse', pg_temp.ac_fix('b_cm1')) = 'ANNULLATA'
  AND (SELECT ca.stato_emissione = 'ANNULLATA' FROM vendite.commesse_attivita ca
        WHERE ca.id = pg_temp.ac_fix('b_ca'))
  AND EXISTS (SELECT 1 FROM vendite.commesse_attivita_log l
               WHERE l.commessa_attivita_id = pg_temp.ac_fix('b_ca')
                 AND l.evento = 'RIGA_RITIRATA_DA_SORGENTE'
                 AND l.dettaglio ->> 'motivo' LIKE 'Ritiro all''annullo confermato della commessa%'),
  '10) commessa ANNULLATA, riga ANNULLATA, registro col motivo');

SELECT ok(
  pg_temp.ac_stato('preventivi', pg_temp.ac_fix('b_prev')) = 'ACCETTATO'
  AND vendite.fn_preventivo_ha_residuo_commessa(pg_temp.ac_fix('b_prev'))
  AND script.fn_get_stato_push_segment(
        ('PREV:' || (SELECT p.uid FROM vendite.preventivi p WHERE p.id = pg_temp.ac_fix('b_prev'))::text
         || ':R:' || pg_temp.ac_fix('b_s1'))::varchar) = 'LIBERA'
  AND (SELECT v.stato_smistamento = 'RESIDUA' FROM vendite.vw_preventivi_smistamento_righe v
        WHERE v.riga_id = pg_temp.ac_fix('b_s1'))
  AND pg_temp.ac_legami('PREVENTIVO', pg_temp.ac_fix('b_prev')) = 0,
  '11) il preventivo torna ACCETTATO e la riga torna da mandare: residuo, LIBERA, RESIDUA, nessun legame verso la commessa morta');

SELECT pg_temp.ac_mk_commessa('b_cm2');
SELECT ok(
  cardinality(pg_temp.ac_invia('PREVENTIVO', pg_temp.ac_fix('b_prev'), pg_temp.ac_fix('b_cm2'))) = 1
  AND pg_temp.ac_stato('preventivi', pg_temp.ac_fix('b_prev')) = 'EVASO',
  '12) un secondo invio in una commessa nuova riesce e riporta il preventivo EVASO');

SELECT ok(
  (SELECT array_agg(cs.commessa_id ORDER BY cs.commessa_id)
          = ARRAY[pg_temp.ac_fix('b_cm1'), pg_temp.ac_fix('b_cm2')]
     FROM vendite.commesse_sorgenti cs
    WHERE cs.sorgente_tipo_id = (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')
      AND cs.sorgente_uid = (SELECT p.uid::text FROM vendite.preventivi p WHERE p.id = pg_temp.ac_fix('b_prev')))
  AND vendite.fn_commessa_viva_di_sorgente(
        (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO'),
        (SELECT p.uid::text FROM vendite.preventivi p WHERE p.id = pg_temp.ac_fix('b_prev')))
      = pg_temp.ac_fix('b_cm2'),
  '12b) il link verso la commessa annullata resta come storia; la commessa aperta del preventivo e'' la nuova');

-- ============================================================
-- C — ordine -> commessa (D-6)
-- ============================================================
SELECT pg_temp.ac_mk_ordine('c');
SELECT pg_temp.ac_mk_commessa('c_cm');
SELECT pg_temp.ac_invia('ORDINE', pg_temp.ac_fix('c_ord'), pg_temp.ac_fix('c_cm'));

SELECT ok(
  pg_temp.ac_stato('ordini', pg_temp.ac_fix('c_ord')) = 'CONFERMATO'
  AND NOT EXISTS (SELECT 1 FROM vendite.fn_list_ordini_da_pushare(p_ordine_id => pg_temp.ac_fix('c_ord'))),
  '13) l''invio non cambia lo stato dell''ordine (resta CONFERMATO), e l''ordine non e'' piu'' da mandare');

SELECT is(vendite.fn_annulla_commessa(pg_temp.ac_fix('c_cm'), 1), 1,
  '14a) annullata la commessa dell''ordine con conferma: un legame');
SELECT ok(
  pg_temp.ac_stato('ordini', pg_temp.ac_fix('c_ord')) = 'CONFERMATO'
  AND EXISTS (SELECT 1 FROM vendite.fn_list_ordini_da_pushare(p_ordine_id => pg_temp.ac_fix('c_ord'))),
  '14) l''ordine resta CONFERMATO e torna da mandare in commessa');

-- D-14: il flag di corsia si blocca solo con una commessa APERTA. Qui
-- l'ordine ha solo il link verso la commessa annullata (la storia): il flag
-- si cambia, e si rimette com'era per l'invio che segue.
SELECT pg_temp.ac_prova('14c_flag_avanti',
  format('UPDATE vendite.ordini SET fatturazione_immediata = NOT fatturazione_immediata WHERE id = %s',
         pg_temp.ac_fix('c_ord')));
SELECT pg_temp.ac_prova('14c_flag_indietro',
  format('UPDATE vendite.ordini SET fatturazione_immediata = NOT fatturazione_immediata WHERE id = %s',
         pg_temp.ac_fix('c_ord')));
SELECT ok(
  (SELECT count(*) = 2 AND bool_and(e.sqlstate IS NULL AND e.righe = 1)
     FROM tmp_ac_esito e WHERE e.caso IN ('14c_flag_avanti', '14c_flag_indietro')),
  '14c) con la sola commessa annullata il flag di fatturazione immediata dell''ordine si cambia (D-14)');

-- Il secondo invio dell'ordine (il controesempio del §10.1, lato ordine). La
-- chiave dell'ordine e' id::text (key_selector 'id'): la porta traduce l'uid
-- che il lister passa.
-- ⚠️ L'invio in un'istruzione sua: le sottoquery della stessa istruzione
--   leggerebbero la fotografia di prima dell'invio.
SELECT pg_temp.ac_mk_commessa('c_cm2');
INSERT INTO tmp_ac_fix
SELECT 'c_n_righe_cm2', cardinality(pg_temp.ac_invia('ORDINE', pg_temp.ac_fix('c_ord'), pg_temp.ac_fix('c_cm2')));
SELECT ok(
  pg_temp.ac_fix('c_n_righe_cm2') = 1
  AND NOT EXISTS (SELECT 1 FROM vendite.fn_list_ordini_da_pushare(p_ordine_id => pg_temp.ac_fix('c_ord')))
  AND (SELECT count(*) = 2
         FROM vendite.commesse_sorgenti cs
        WHERE cs.sorgente_tipo_id = (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA')
          AND cs.sorgente_uid = pg_temp.ac_fix('c_ord')::text)
  AND vendite.fn_commessa_viva_di_sorgente(
        (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA'),
        pg_temp.ac_fix('c_ord')::text) = pg_temp.ac_fix('c_cm2'),
  '14b) l''ordine si rimanda in una commessa nuova: due link (chiave id), aperta la nuova');

SELECT pg_temp.ac_prova('14d_flag_aperta',
  format('UPDATE vendite.ordini SET fatturazione_immediata = NOT fatturazione_immediata WHERE id = %s',
         pg_temp.ac_fix('c_ord')));
SELECT ok(pg_temp.ac_rifiuto('14d_flag_aperta', 'fatturazione immediata non e'' piu'' modificabile'),
  '14d) con la commessa nuova aperta il flag si blocca di nuovo: E_FATT_IMMEDIATA_NON_MODIFICABILE');

-- ============================================================
-- D — preventivo misto: merce all'ordine, servizi in commessa
-- ============================================================
SELECT pg_temp.ac_mk_preventivo('d', 1, 1);
INSERT INTO tmp_ac_fix
SELECT 'd_ord', vendite.fn_push_preventivo_a_ordine(pg_temp.ac_fix('d_prev'));
INSERT INTO tmp_ac_fix VALUES ('d_stato_dopo_ordine', NULL);
UPDATE tmp_ac_fix SET id = CASE pg_temp.ac_stato('preventivi', pg_temp.ac_fix('d_prev'))
                             WHEN 'ACCETTATO' THEN 1 ELSE 0 END
 WHERE chiave = 'd_stato_dopo_ordine';
SELECT pg_temp.ac_mk_commessa('d_cm');
SELECT pg_temp.ac_invia('PREVENTIVO', pg_temp.ac_fix('d_prev'), pg_temp.ac_fix('d_cm'));

SELECT ok(
  pg_temp.ac_fix('d_stato_dopo_ordine') = 1
  AND pg_temp.ac_stato('preventivi', pg_temp.ac_fix('d_prev')) = 'EVASO',
  '15) preventivo misto: ACCETTATO dopo l''ordine (resta la commessa), EVASO dopo la commessa');

SELECT vendite.fn_annulla_commessa(pg_temp.ac_fix('d_cm'), 1);
SELECT ok(
  pg_temp.ac_stato('preventivi', pg_temp.ac_fix('d_prev')) = 'ACCETTATO'
  AND pg_temp.ac_stato('ordini', pg_temp.ac_fix('d_ord')) = 'DRAFT'
  AND EXISTS (SELECT 1 FROM vendite.ordini_righe orr
               WHERE orr.ordine_id = pg_temp.ac_fix('d_ord')
                 AND orr.preventivo_riga_id = pg_temp.ac_fix('d_m1'))
  AND vendite.fn_preventivo_ha_residuo_commessa(pg_temp.ac_fix('d_prev'))
  AND NOT vendite.fn_preventivo_ha_residuo_ordine(pg_temp.ac_fix('d_prev')),
  '16) annullata la commessa: ACCETTATO, l''ordine resta vivo con la sua riga, si riapre solo la strada della commessa');

-- ============================================================
-- E — una sorgente in due commesse APERTE (D-12)
-- ============================================================
SELECT pg_temp.ac_mk_preventivo('e', 0, 2);
SELECT pg_temp.ac_mk_commessa('e_cm1');
SELECT pg_temp.ac_mk_commessa('e_cm2');
INSERT INTO tmp_ac_fix
SELECT 'e_ca1', (pg_temp.ac_invia('PREVENTIVO', pg_temp.ac_fix('e_prev'), pg_temp.ac_fix('e_cm1'),
                                  ARRAY[pg_temp.ac_fix('e_s1')]))[1];
SELECT pg_temp.ac_prova('17_due_aperte',
  format('SELECT pg_temp.ac_invia(''PREVENTIVO'', %s, %s, ARRAY[%s]::bigint[])',
         pg_temp.ac_fix('e_prev'), pg_temp.ac_fix('e_cm2'), pg_temp.ac_fix('e_s2')));

-- Il frammento e' comune al testo di prima e a quello del 2026-10-12
-- (messaggi_errore.csv): la prova pre-apply gira col catalogo di prima.
SELECT ok(
  pg_temp.ac_rifiuto('17_due_aperte', 'altra commessa')
  AND NOT EXISTS (SELECT 1 FROM vendite.commesse_attivita ca WHERE ca.commessa_id = pg_temp.ac_fix('e_cm2'))
  AND NOT EXISTS (SELECT 1 FROM vendite.commesse_sorgenti cs WHERE cs.commessa_id = pg_temp.ac_fix('e_cm2'))
  AND pg_temp.ac_stato('preventivi', pg_temp.ac_fix('e_prev')) = 'ACCETTATO',
  '17) lo stesso preventivo in una seconda commessa aperta e'' rifiutato, e nella seconda non si scrive niente');

SELECT vendite.fn_annulla_commessa(pg_temp.ac_fix('e_cm1'), 1);
INSERT INTO tmp_ac_fix
SELECT 'e_n_righe_cm2', cardinality(pg_temp.ac_invia('PREVENTIVO', pg_temp.ac_fix('e_prev'), pg_temp.ac_fix('e_cm2')));
SELECT ok(
  pg_temp.ac_fix('e_n_righe_cm2') = 2
  AND (SELECT ca.stato_emissione = 'ANNULLATA' FROM vendite.commesse_attivita ca WHERE ca.id = pg_temp.ac_fix('e_ca1'))
  AND pg_temp.ac_stato('preventivi', pg_temp.ac_fix('e_prev')) = 'EVASO',
  '17b) annullata la prima commessa, tutte e due le righe vanno nella seconda e il preventivo e'' EVASO');

-- ============================================================
-- F — gli oneri
-- ============================================================
SELECT pg_temp.ac_mk_commessa('f_cm');
INSERT INTO tmp_ac_fix
SELECT 'f_onere', vendite.fn_aggiungi_onere_commessa(
         p_commessa_id         => pg_temp.ac_fix('f_cm'),
         p_istanza_utility_id  => (SELECT istanza_utility_id FROM tmp_ac_refs),
         -- Gli articoli-onere sono seed di catalogo (con la loro causale).
         p_articolo_onere_id   => (SELECT a.id FROM catalogo.articoli a
                                    WHERE a.causale_onere_id IS NOT NULL AND a.attivo
                                    ORDER BY a.codice LIMIT 1),
         p_importo             => 12,
         p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_ac_refs),
         p_motivo              => 'onere pgTAP');

SELECT ok(
  (SELECT count(*) = 1
          AND bool_and(l.origine = 'ONERE' AND l.natura = 'ANNULLO'
                       AND l.riga_id = pg_temp.ac_fix('f_onere') AND l.origine_id IS NULL)
     FROM vendite.fn_documento_legami('COMMESSA', pg_temp.ac_fix('f_cm')) l),
  '18) il legame dell''onere: ONERE, natura ANNULLO, niente a monte');

SELECT pg_temp.ac_prova('19_onere_diretto',
  format('UPDATE vendite.commesse SET stato_commessa_id = %s WHERE id = %s',
         (SELECT cm_annullata_id FROM tmp_ac_refs), pg_temp.ac_fix('f_cm')));
SELECT ok(pg_temp.ac_rifiuto('19_onere_diretto', 'Serve una conferma'),
  '19) l''annullo diretto e'' rifiutato anche con i soli oneri');

SELECT vendite.fn_annulla_commessa(pg_temp.ac_fix('f_cm'), 1);
SELECT ok(
  pg_temp.ac_stato('commesse', pg_temp.ac_fix('f_cm')) = 'ANNULLATA'
  AND (SELECT ca.stato_emissione = 'ANNULLATA' FROM vendite.commesse_attivita ca
        WHERE ca.id = pg_temp.ac_fix('f_onere'))
  AND EXISTS (SELECT 1 FROM vendite.commesse_attivita_log l
               WHERE l.commessa_attivita_id = pg_temp.ac_fix('f_onere')
                 AND l.evento = 'RIGA_MANUALE_ANNULLATA'),
  '20) confermato: commessa ANNULLATA, onere ANNULLATO col suo registro');

-- ============================================================
-- G — prima cio' che vieta
-- ============================================================
-- Una commessa con due righe: una emessa (approvata e passata all'emissione),
-- una no.
SELECT pg_temp.ac_mk_preventivo('g', 0, 2);
SELECT pg_temp.ac_mk_commessa('g_cm');
INSERT INTO tmp_ac_fix
SELECT 'g_ca1', (pg_temp.ac_invia('PREVENTIVO', pg_temp.ac_fix('g_prev'), pg_temp.ac_fix('g_cm'),
                                  ARRAY[pg_temp.ac_fix('g_s1')]))[1];
SELECT vendite.fn_rendi_commessa_emittibile(pg_temp.ac_fix('g_cm'), ARRAY[pg_temp.ac_fix('g_ca1')]);
UPDATE vendite.commesse_attivita SET stato_emissione = 'EMESSA' WHERE id = pg_temp.ac_fix('g_ca1');
INSERT INTO tmp_ac_fix
SELECT 'g_ca2', (pg_temp.ac_invia('PREVENTIVO', pg_temp.ac_fix('g_prev'), pg_temp.ac_fix('g_cm'),
                                  ARRAY[pg_temp.ac_fix('g_s2')]))[1];

SELECT pg_temp.ac_prova('21_emesse',
  format('SELECT vendite.fn_annulla_commessa(%s, NULL)', pg_temp.ac_fix('g_cm')));
SELECT ok(
  pg_temp.ac_rifiuto('21_emesse', 'annullamento non consentito')
  AND NOT pg_temp.ac_rifiuto('21_emesse', 'Serve una conferma'),
  '21) commessa con righe EMESSE: il verbo senza conferma parla delle righe emesse, non chiede la conferma');

SELECT ok(
  (SELECT ca.stato_emissione = 'NON_EMESSA' FROM vendite.commesse_attivita ca WHERE ca.id = pg_temp.ac_fix('g_ca2'))
  AND pg_temp.ac_stato('commesse', pg_temp.ac_fix('g_cm')) <> 'ANNULLATA',
  '22) e non ha toccato niente: la riga non emessa resta NON_EMESSA, la commessa non e'' annullata');

-- Un preventivo con un ordine vivo e una riga di servizio in commessa: la
-- conferma non va chiesta, l'annullo e' vietato dall'ordine.
SELECT pg_temp.ac_mk_preventivo('h', 1, 2);
INSERT INTO tmp_ac_fix
SELECT 'h_ord', vendite.fn_push_preventivo_a_ordine(pg_temp.ac_fix('h_prev'));
SELECT pg_temp.ac_mk_commessa('h_cm');
SELECT pg_temp.ac_invia('PREVENTIVO', pg_temp.ac_fix('h_prev'), pg_temp.ac_fix('h_cm'),
                        ARRAY[pg_temp.ac_fix('h_s1')]);
SELECT pg_temp.ac_prova('23_ordine_vivo',
  format('SELECT vendite.fn_annulla_preventivo(%s, NULL)', pg_temp.ac_fix('h_prev')));
SELECT ok(
  pg_temp.ac_stato('preventivi', pg_temp.ac_fix('h_prev')) = 'ACCETTATO'
  AND pg_temp.ac_rifiuto('23_ordine_vivo', 'gia'' stato generato un ordine')
  AND NOT pg_temp.ac_rifiuto('23_ordine_vivo', 'Serve una conferma'),
  '23) preventivo con un ordine vivo e righe in commessa: si ferma su ORDINE_GIA_GENERATO, non chiede la conferma');

-- ============================================================
-- H — senza legami
-- ============================================================
SELECT pg_temp.ac_mk_commessa('k_cm');
SELECT ok(
  vendite.fn_annulla_commessa(pg_temp.ac_fix('k_cm'), NULL) = 0
  AND pg_temp.ac_stato('commesse', pg_temp.ac_fix('k_cm')) = 'ANNULLATA',
  '24) una commessa senza legami si annulla dal verbo senza conferma');

-- ============================================================
-- I — il «gia' mandato» parla una lingua sola
-- ============================================================
-- Segmenti costruiti sulla commessa del caso B2 (viva), con la madre delle righe.
CREATE OR REPLACE FUNCTION pg_temp.ac_riga(p_segment text, p_emissione text, p_movimento text DEFAULT 'NORMALE')
RETURNS bigint AS $$
DECLARE r RECORD; v bigint; v_uom bigint;
BEGIN
  SELECT * INTO r FROM tmp_ac_refs;
  SELECT a.uom_id INTO v_uom FROM catalogo.articoli a WHERE a.id = r.art_serv_id;
  SELECT u.attivita_id INTO v FROM vendite.fn_upsert_commessa_attivita(
      p_commessa_id => pg_temp.ac_fix('b_cm2'), p_segment_key => p_segment::varchar,
      p_articolo_id => r.art_serv_id, p_istanza_utility_id => r.istanza_utility_id,
      p_data_attivita => script.fn_data_operativa(), p_uom_id => v_uom, p_quantita => 1,
      p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
      p_competenza_dal => date_trunc('month', script.fn_data_operativa())::date,
      p_competenza_al => (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date,
      p_prezzo_snapshot => 5, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
      p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL, p_promo_id => NULL,
      p_contratto_id => NULL, p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
      p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id, p_valuta_id => r.valuta_id,
      p_stato_approvazione => 'BOZZA', p_stato_emissione => 'NON_EMESSA',
      p_sorgente_tipo_id => r.sorg_commessa_id, p_sorgente_uid => pg_temp.ac_fix('b_cm2')::text,
      p_tipo_movimento => 'NORMALE') u;
  IF p_emissione <> 'NON_EMESSA' THEN
    UPDATE vendite.commesse_attivita SET stato_emissione = p_emissione WHERE id = v;
  END IF;
  RETURN v;
END $$ LANGUAGE plpgsql;

SELECT pg_temp.ac_riga('PGT-AC-SEG:A', 'ANNULLATA');
SELECT pg_temp.ac_riga('PGT-AC-SEG:B', 'EMESSA');
SELECT pg_temp.ac_riga('PGT-AC-SEG:B#RET:1', 'ANNULLATA');

SELECT is(script.fn_get_stato_push_segment('PGT-AC-SEG:A'), 'LIBERA',
  '25) classificatore: un segmento con la sola riga ANNULLATA e'' LIBERA (D-5)');
SELECT is(script.fn_get_stato_push_segment('PGT-AC-SEG:B'), 'EMESSA',
  '26) classificatore: EMESSA con una rettifica ANNULLATA resta EMESSA (la ritirata non conta)');

SELECT ok(
  (SELECT bool_and(
            (EXISTS (SELECT 1 FROM vendite.vw_preventivi_righe_smistabili_commessa v WHERE v.id = pr.id))
            = (script.fn_get_stato_push_segment(
                 ('PREV:' || p.uid::text || ':R:' || pr.id::text)::varchar) = 'LIBERA'))
     FROM vendite.preventivi_righe pr
     JOIN vendite.preventivi p ON p.id = pr.preventivo_id
    WHERE pr.articolo_id = (SELECT art_serv_id FROM tmp_ac_refs)
      AND pr.attivo),
  '27) vista smistabili e classificatore dicono la stessa cosa su ogni riga di servizio della fixture');

-- ============================================================
-- J — il trigger tocca solo i preventivi
-- ============================================================
-- Il preventivo b e' EVASO (caso 12). Una riga di un'altra sorgente sulla
-- stessa commessa che cambia stato non lo muove.
UPDATE vendite.commesse_attivita SET stato_emissione = 'ANNULLATA'
 WHERE commessa_id = pg_temp.ac_fix('b_cm2') AND segment_key = 'PGT-AC-SEG:B';
SELECT is(pg_temp.ac_stato('preventivi', pg_temp.ac_fix('b_prev')), 'EVASO',
  '28) una riga di un''altra sorgente che cambia stato non muove il preventivo');

-- ============================================================
-- K — la proiezione negli altri stati
-- ============================================================
SELECT pg_temp.ac_mk_preventivo('m', 0, 1, 'DRAFT');
DO $m$ BEGIN
  PERFORM vendite.fn_preventivo_proietta_stato_smistamento(pg_temp.ac_fix('m_prev'));
END $m$;
SELECT is(pg_temp.ac_stato('preventivi', pg_temp.ac_fix('m_prev')), 'DRAFT',
  '29) la proiezione lascia stare un preventivo che non e'' ACCETTATO ne'' EVASO (qui DRAFT)');

SELECT * FROM finish();
ROLLBACK;
