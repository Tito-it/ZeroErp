-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; resta scritto a mano il reso a credito (giro 2) e la commessa con la fattura, che sono il caso del test.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   l'origine dei legami della commessa e' il codice della sorgente: DDT_VENDITA per la riga
--   della bolla, RESO_VENDITA per la rettifica (erano DDT e RESO).
-- pgTAP test per Zero ERP
-- Test: annullare una commessa che porta la rettifica di un accredito — il
--   reso torna da accreditare (D-7), la bolla torna da mandare (D-5).
--   vendite.fn_annulla_commessa, vendite.fn_documento_legami('COMMESSA')
--   (origine RESO), vendite.fn_documento_ritira_legami (ramo RETTIFICA:
--   vendite.fn_annulla_accredito_riga_reso).
-- ChangeSet: 20261012-08 … -24
-- Brief: brief-db-annullo-a-valle-riapre-a-monte (D-7; §7.3)
-- ------------------------------------------------------------
-- ⚠️ PERCHE' LA FIXTURE E' LUNGA. La rettifica di un accredito nasce nella
--   STESSA commessa della riga fatturata che corregge
--   (vendite.fn_accredita_riga_reso), e quella riga e' EMESSA: finche' lo
--   resta, la commessa non si annulla (D-3, script.fn_check_commessa_annullabile).
--   Il ramo si raggiunge davvero solo dopo che la riga fatturata e' tornata
--   NON_EMESSA (il reset del lotto, «Riporta da emettere»). La catena intera:
--   ordine -> bolla consegnata -> riga di commessa della bolla (con la sua
--   sorgente, come il push) -> emissione -> fattura -> reso a credito ->
--   accredito -> reset della riga fatturata -> annullo della commessa.
--
-- Indice test (plan 6):
--   1) fixture: la commessa ha due legami, la riga della bolla (DDT) e la
--      rettifica (RESO, con la riga di reso)
--   2) l'annullo diretto e' rifiutato: E_DOC_ANNULLO_CON_LEGAMI
--   3) confermato: il verbo restituisce i due legami
--   4) commessa ANNULLATA, rettifica ANNULLATA, ponte dell'accredito vuoto,
--      registro ACCREDITO_ANNULLATO col motivo dell'annullo della commessa
--   5) la quota del reso non risulta piu' accreditata (da 3 a 0): torna
--      accreditabile, e lo sara' di nuovo quando la merce tornera' in fattura
--      (dopo il reset del lotto la merce non e' piu' fatturata: la coda
--      accrediti, giustamente, non la propone)
--   6) la riga della bolla e' ANNULLATA e il suo segmento torna LIBERO
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO coi builder e coi verbi del dominio: nessun
--   documento preso dai dati.
-- ------------------------------------------------------------

BEGIN;
SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(6);

-- L'operatore di fixture non ha azioni: emissione della bolla e conferma del
-- reso sono verbi che le applicano.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ddt');
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;

-- ============================================================
-- Riferimenti — costruiti
-- ============================================================
CREATE TEMP TABLE tmp_acr_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'annullo commessa rettifica',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_acr AS
SELECT
  c.billing_account_id, c.utility_id, c.istanza_utility_id,
  script.fn_pgtap_emittente_sr_operatore()     AS emittente_sr_id,
  dbops.fn_pgtap_crea_articolo('PGT-ACR-MERCE', false) AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)            AS iva_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo ORDER BY s.id LIMIT 1)       AS sorgente_ddt_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo ORDER BY s.id LIMIT 1)       AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_A_CREDITO' AND t.attivo ORDER BY t.id LIMIT 1)   AS tipo_credito_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                          AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno='DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_fatt_draft_id,
  script.fn_pgtap_registro_fattura()                                                                                 AS registro_id,
  (SELECT s.id FROM vendite.stati_commessa s WHERE s.codice_interno = 'ANNULLATA')                                   AS cm_annullata_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA' AND s.attivo ORDER BY s.id LIMIT 1)          AS sorgente_root_id
FROM tmp_acr_cli c;

CREATE TEMP TABLE tmp_acr_fix(chiave text PRIMARY KEY, id bigint);
CREATE OR REPLACE FUNCTION pg_temp.acr(p_chiave text) RETURNS bigint
  AS $$ SELECT id FROM tmp_acr_fix WHERE chiave = p_chiave $$ LANGUAGE sql;

-- ============================================================
-- La catena: ordine -> bolla consegnata
-- ============================================================
-- La bolla CONSEGNATA dal builder: 10 a 25, trigger CONSEGNATO, del cliente
-- costruito sopra.
CREATE TEMP TABLE tmp_acr_bolla AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('annullo commessa rettifica',
                  p_billing_account_id   => (SELECT billing_account_id FROM tmp_acr),
                  p_quantita             => 10,
                  p_prezzo               => 25,
                  p_articolo_id          => (SELECT articolo_id FROM tmp_acr),
                  p_fatturazione_trigger => 'CONSEGNATO');
INSERT INTO tmp_acr_fix
SELECT 'ddt', b.ddt_id FROM tmp_acr_bolla b
UNION ALL
SELECT 'ddt_riga', b.ddt_riga_id FROM tmp_acr_bolla b;

-- ============================================================
-- La commessa, la riga della bolla (con la sua sorgente, come il push),
-- l'emissione e la fattura
-- ============================================================
DO $fatt$
DECLARE r RECORD; v_cm bigint; v_uid text; v_seg varchar; v_ca bigint; v_af bigint;
        v_fatt bigint; v_riga bigint; v_uom bigint;
BEGIN
  SELECT * INTO r FROM tmp_acr;
  SELECT a.uom_id INTO v_uom FROM catalogo.articoli a WHERE a.id = r.articolo_id;
  v_cm := vendite.fn_get_or_create_commessa(
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
  -- L'emissione vuole la sorgente ROOT della commessa, come la scrive il push.
  PERFORM vendite.fn_link_commessa_sorgente(
    p_commessa_id      => v_cm,
    p_sorgente_tipo_id => r.sorgente_root_id,
    p_sorgente_uid     => v_cm::text,
    p_sorgente_riga    => 1,
    p_meta             => '{}'::jsonb);
  SELECT d.uid::text INTO v_uid FROM vendite.ddt d WHERE d.id = pg_temp.acr('ddt');
  v_seg := ('DDT_VENDITA:' || v_uid || ':R:' || pg_temp.acr('ddt_riga'))::varchar;

  SELECT u.attivita_id INTO v_ca FROM vendite.fn_upsert_commessa_attivita(
    p_commessa_id                   => v_cm,
    p_segment_key                   => v_seg,
    p_articolo_id                   => r.articolo_id,
    p_istanza_utility_id            => r.istanza_utility_id,
    p_data_attivita                 => script.fn_data_operativa(),
    p_uom_id                        => v_uom,
    p_quantita                      => 10,
    p_competenza_mese               => date_trunc('month', script.fn_data_operativa())::date,
    p_competenza_dal                => date_trunc('month', script.fn_data_operativa())::date,
    p_competenza_al                 => (date_trunc('month', script.fn_data_operativa()) + interval '1 month - 1 day')::date,
    p_prezzo_snapshot               => 25,
    p_prezzo_base_snapshot          => NULL,
    p_origine_prezzo                => NULL,
    p_tipo_variazione_applicata     => NULL,
    p_valore_variazione_applicata   => NULL,
    p_promo_id                      => NULL,
    p_contratto_id                  => NULL,
    p_categoria_cliente_id_snapshot => NULL,
    p_classe_utenza_id_snapshot     => NULL,
    p_tipo_doc_fiscale_id           => r.tipo_doc_fiscale_id,
    p_valuta_id                     => r.valuta_id,
    p_stato_approvazione            => 'APPROVATA',
    p_stato_emissione               => 'NON_EMESSA',
    p_sorgente_tipo_id              => r.sorgente_ddt_id,
    p_sorgente_uid                  => v_uid,
    p_tipo_movimento                => 'NORMALE') u;

  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa(v_cm, true, false);

  SELECT af.id INTO v_af FROM vendite.attivita_fatturabili af
   WHERE af.commessa_attivita_id = v_ca ORDER BY af.id DESC LIMIT 1;

  INSERT INTO vendite.fatture (registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
      emittente_soggetto_ruolo_id, billing_account_id, utility_id, valuta_id, tasso_cambio, meta)
  VALUES (r.registro_id, script.fn_data_operativa(), r.tipo_doc_fiscale_id, r.stato_fatt_draft_id,
      r.emittente_sr_id, r.billing_account_id, r.utility_id, r.valuta_id, 1,
      jsonb_build_object('test_scope','pgtap_annullo_commessa_rettifica'))
  RETURNING id INTO v_fatt;
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione,
      uom_id, qta, prezzo_unitario, iva_id, imponibile_riga, competenza_dal, competenza_al)
  VALUES (v_fatt, 1, r.articolo_id, 'Riga fattura pgTAP', v_uom, 10, 25,
      r.iva_id, 250, script.fn_data_operativa(), script.fn_data_operativa())
  RETURNING id INTO v_riga;
  UPDATE vendite.attivita_fatturabili SET fattura_riga_id = v_riga WHERE id = v_af;

  INSERT INTO tmp_acr_fix VALUES ('cm', v_cm), ('ca_ddt', v_ca);
END $fatt$;

-- ============================================================
-- Reso a credito di 3 e il suo accredito: la rettifica nasce nella commessa
-- ============================================================
DO $reso$
DECLARE r RECORD; v_reso bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_acr;
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  VALUES (r.stato_reso_draft_id, r.sorgente_ddt_id,
          (SELECT d.uid FROM vendite.ddt d WHERE d.id = pg_temp.acr('ddt')), false,
          jsonb_build_object('test_scope','pgtap_annullo_commessa_rettifica'))
  RETURNING id INTO v_reso;
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
      articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base,
      tipo_reso_id, storicizza)
  SELECT v_reso, 1, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f
           WHERE f.ddt_riga_id = dr.id ORDER BY f.id LIMIT 1),
         dr.articolo_id, dr.descrizione, 3, dr.uom_operativa_id, dr.factor_to_base,
         r.tipo_credito_id, false
    FROM vendite.ddt_righe dr WHERE dr.id = pg_temp.acr('ddt_riga')
  RETURNING id INTO v_riga;
  PERFORM vendite.fn_conferma_reso(v_reso);
  INSERT INTO tmp_acr_fix VALUES ('reso', v_reso), ('resi_riga', v_riga);
END $reso$;

INSERT INTO tmp_acr_fix
SELECT 'ca_ret', a.commessa_attivita_id
  FROM vendite.fn_accredita_riga_reso(pg_temp.acr('resi_riga')) a
 LIMIT 1;

-- Il reset del lotto, nella forma di vendite.fn_cleanup_fatture_by_ids: la
-- riga fatturata torna NON_EMESSA e la sua attivita' fatturabile sopravvive
-- sbloccata. E' il solo modo in cui la commessa della rettifica si annulla.
-- ⚠️ La pulizia apre la sua porta (GUC zeroerp.maintenance_reset_lotto_draft,
--    letta da vendite.trgfn_attivita_fatturabili_guard_fatturato): senza,
--    l'attivita' fatturata non si sblocca. Aperta e chiusa intorno al reset.
SELECT set_config('zeroerp.maintenance_reset_lotto_draft', 'on', true);
UPDATE vendite.attivita_fatturabili
   SET lock_in_fatturazione = false, lock_batch_id = NULL, fattura_riga_id = NULL
 WHERE commessa_attivita_id = pg_temp.acr('ca_ddt');
UPDATE vendite.commesse_attivita SET stato_emissione = 'NON_EMESSA'
 WHERE id = pg_temp.acr('ca_ddt');
SELECT set_config('zeroerp.maintenance_reset_lotto_draft', '', true);

SELECT ok(
  (SELECT count(*) = 2
          AND count(*) FILTER (WHERE l.origine = 'DDT_VENDITA' AND l.natura = 'CONSUMO'
                                 AND l.riga_id = pg_temp.acr('ca_ddt')
                                 AND l.origine_id = pg_temp.acr('ddt')) = 1
          AND count(*) FILTER (WHERE l.origine = 'RESO_VENDITA' AND l.natura = 'CONSUMO'
                                 AND l.riga_id = pg_temp.acr('ca_ret')
                                 AND l.origine_id = pg_temp.acr('reso')
                                 AND l.origine_riga_id = pg_temp.acr('resi_riga')) = 1
     FROM vendite.fn_documento_legami('COMMESSA', pg_temp.acr('cm')) l),
  '1) la commessa ha due legami: la riga della bolla (DDT) e la rettifica (RESO, con la riga di reso)');

-- La quota accreditata prima dell'annullo: la rettifica la porta.
INSERT INTO tmp_acr_fix
SELECT 'accreditato_prima', vendite.fn_resi_riga_accreditato_partita(pg_temp.acr('resi_riga'))::bigint;

SELECT throws_like(
  format('UPDATE vendite.commesse SET stato_commessa_id = %s WHERE id = %s',
         (SELECT cm_annullata_id FROM tmp_acr), pg_temp.acr('cm')),
  '%Serve una conferma%',
  '2) l''annullo diretto e'' rifiutato: E_DOC_ANNULLO_CON_LEGAMI');

SELECT is(vendite.fn_annulla_commessa(pg_temp.acr('cm'), 2), 2,
  '3) confermato: il verbo restituisce i due legami');

SELECT ok(
  (SELECT s.codice_interno = 'ANNULLATA' FROM vendite.commesse c
     JOIN vendite.stati_commessa s ON s.id = c.stato_commessa_id WHERE c.id = pg_temp.acr('cm'))
  AND (SELECT ca.stato_emissione = 'ANNULLATA' FROM vendite.commesse_attivita ca
        WHERE ca.id = pg_temp.acr('ca_ret'))
  AND NOT EXISTS (SELECT 1 FROM vendite.resi_righe_accrediti a
                   WHERE a.resi_riga_id = pg_temp.acr('resi_riga'))
  AND EXISTS (SELECT 1 FROM vendite.commesse_attivita_log l
               WHERE l.commessa_attivita_id = pg_temp.acr('ca_ret')
                 AND l.evento = 'ACCREDITO_ANNULLATO'
                 AND l.dettaglio ->> 'motivo' LIKE 'Ritiro all''annullo confermato della commessa%'),
  '4) commessa ANNULLATA, rettifica ANNULLATA, ponte vuoto, registro ACCREDITO_ANNULLATO col motivo');

SELECT is(
  pg_temp.acr('accreditato_prima') || '->'
    || vendite.fn_resi_riga_accreditato_partita(pg_temp.acr('resi_riga'))::bigint,
  '3->0',
  '5) la quota del reso non risulta piu'' accreditata (da 3 a 0): l''accredito si e'' annullato con la commessa');

SELECT ok(
  (SELECT ca.stato_emissione = 'ANNULLATA' FROM vendite.commesse_attivita ca
    WHERE ca.id = pg_temp.acr('ca_ddt'))
  AND script.fn_get_stato_push_segment(
        ('DDT_VENDITA:' || (SELECT d.uid FROM vendite.ddt d WHERE d.id = pg_temp.acr('ddt'))::text
         || ':R:' || pg_temp.acr('ddt_riga'))::varchar) = 'LIBERA',
  '6) la riga della bolla e'' ANNULLATA e il suo segmento torna LIBERO: la bolla torna da mandare');

SELECT * FROM finish();
ROLLBACK;
