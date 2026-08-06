-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_available_actions_ddt — decomposizione del catch-all
--       DDT_NON_PUSHABILE nelle 7 cause (fonte unica fn_ddt_push_diagnosi).
-- Brief: brief-db-ddt-reason-push-catch-all §3 (changeset 20260719-15/16)
-- ------------------------------------------------------------
-- Indice test (1..7):
--   1) EQUIVALENZA (garanzia fonte unica): l'insieme delle righe con
--      diagnosi motivo NULL coincide con l'output del lister. Se divergono
--      i predicati si sono sdoppiati -> rosso. Indipendente dai dati.
--   2) DDT_FATTURA_DA_ORDINE: ordine CONFERMATO, DDT CONSEGNATO (il rilievo
--      originale DDT0000326) -> reason FATTURA_DA_ORDINE, non piu' il falso
--      «dev'essere spedito o consegnato».
--   3) DDT_MERCE_IN_VIAGGIO: ordine SPEDITO, DDT EMESSO (prima del trigger)
--      -> reason MERCE_IN_VIAGGIO (l'unico caso in cui lo stato e' vero).
--   4) DDT_SOLO_TRASPORTO: causale non fatturabile (CONTO_LAVORO) -> reason
--      SOLO_TRASPORTO (non e' questione di stato).
--   5) generico ANNULLATO: DDT annullato -> DDT_NON_PUSHABILE (generico),
--      NON la frase sullo stato.
--   6) PRECEDENZA a due livelli: DDT ANNULLATO con ordine CONFERMATO -> due
--      cause (annullato rank1 doc, XOR rank6 riga) -> vince il documento
--      (generico), non FATTURA_DA_ORDINE.
--   7) NAMESPACE: ogni reason_key emessa sta sotto vendite.ddt.push_commessa_reason.*
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
SET LOCAL app.current_user_id = '1';

-- ============================================================
-- Riferimenti + helper mk_caso (adattato da test-fn-list-ddt-da-pushare-orfano)
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT ba.id FROM anagrafiche.billing_account ba
    WHERE ba.utility_id IS NOT NULL AND ba.istanza_utility_id IS NOT NULL
      AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
    ORDER BY ba.id LIMIT 1)                                              AS billing_account_id,
  (SELECT sr.id FROM anagrafiche.soggetti_ruoli sr ORDER BY sr.id LIMIT 1) AS soggetto_ruolo_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND COALESCE(a.is_composito, FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST LIMIT 1)                      AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)              AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef ORDER BY ef.id LIMIT 1)  AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='CONFERMATO' AND s.attivo LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO' AND s.attivo LIMIT 1)     AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='SPEDITO' AND s.attivo LIMIT 1)    AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo LIMIT 1) AS stato_ddt_consegnato_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='ANNULLATO' AND s.attivo LIMIT 1)  AS stato_ddt_annullato_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1)     AS causale_vendita_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='CONTO_LAVORO' LIMIT 1) AS causale_no_fatt_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')     AS tipo_ind_con_id;

-- Crea ordine + DDT con trigger e stato finale parametrici + causale scelta.
CREATE OR REPLACE FUNCTION pg_temp.mk_caso(p_trigger varchar, p_stato_finale bigint, p_causale bigint)
RETURNS bigint AS $$
DECLARE r RECORD; v_ord bigint; v_ddt bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_conf_id, r.valuta_id,
          DATE '2026-07-15', p_trigger, r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_reason_catchall'))
  RETURNING id INTO v_ord;
  UPDATE vendite.ordini SET fatturazione_trigger = p_trigger WHERE id = v_ord;
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga catchall', 10, 10, 25, r.iva_id, true, false,
          jsonb_build_object('test_scope','pgtap_reason_catchall'));
  v_ddt := vendite.fn_genera_ddt_da_ordine(v_ord);
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  UPDATE vendite.ddt SET causale_trasporto_id=p_causale WHERE id=v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_emesso_id WHERE id=v_ddt;  -- DRAFT->EMESSO
  IF p_stato_finale = r.stato_ddt_annullato_id THEN
    UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_annullato_id WHERE id=v_ddt;
  ELSIF p_stato_finale <> r.stato_ddt_emesso_id THEN
    UPDATE vendite.ddt SET stato_doc_ddt_id=r.stato_ddt_spedito_id WHERE id=v_ddt;
    IF p_stato_finale <> r.stato_ddt_spedito_id THEN
      UPDATE vendite.ddt SET stato_doc_ddt_id=p_stato_finale WHERE id=v_ddt;
    END IF;
  END IF;
  RETURN v_ddt;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- TEST 1) EQUIVALENZA fonte unica (indipendente dai dati)
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT g.riga_id FROM vendite.fn_ddt_push_diagnosi() g WHERE g.motivo IS NULL
    EXCEPT SELECT riga_id FROM vendite.fn_list_ddt_da_pushare()
  )
  AND NOT EXISTS (
    SELECT riga_id FROM vendite.fn_list_ddt_da_pushare()
    EXCEPT SELECT g.riga_id FROM vendite.fn_ddt_push_diagnosi() g WHERE g.motivo IS NULL
  ),
  '1) EQUIVALENZA: righe eleggibili (diagnosi motivo NULL) == output lister'
);

-- Fixtures
CREATE TEMP TABLE f AS SELECT
  pg_temp.mk_caso('CONFERMATO', (SELECT stato_ddt_consegnato_id FROM tmp_refs), (SELECT causale_vendita_id FROM tmp_refs))  AS d_fattura_ordine,
  pg_temp.mk_caso('SPEDITO',    (SELECT stato_ddt_emesso_id FROM tmp_refs),     (SELECT causale_vendita_id FROM tmp_refs))  AS d_in_viaggio,
  pg_temp.mk_caso('SPEDITO',    (SELECT stato_ddt_spedito_id FROM tmp_refs),    (SELECT causale_no_fatt_id FROM tmp_refs))  AS d_solo_trasporto,
  pg_temp.mk_caso('SPEDITO',    (SELECT stato_ddt_annullato_id FROM tmp_refs),  (SELECT causale_vendita_id FROM tmp_refs))  AS d_annullato,
  pg_temp.mk_caso('CONFERMATO', (SELECT stato_ddt_annullato_id FROM tmp_refs),  (SELECT causale_vendita_id FROM tmp_refs))  AS d_prec;

-- 2) FATTURA_DA_ORDINE (il rilievo originale)
SELECT is(
  (SELECT script.fn_available_actions_ddt(d_fattura_ordine)->>'can_push_commessa_reason' FROM f),
  'DDT_FATTURA_DA_ORDINE',
  '2) ordine CONFERMATO + DDT CONSEGNATO -> DDT_FATTURA_DA_ORDINE (era il falso «spedito o consegnato»)'
);

-- 3) MERCE_IN_VIAGGIO
SELECT is(
  (SELECT script.fn_available_actions_ddt(d_in_viaggio)->>'can_push_commessa_reason' FROM f),
  'DDT_MERCE_IN_VIAGGIO',
  '3) ordine SPEDITO + DDT EMESSO (pre-trigger) -> DDT_MERCE_IN_VIAGGIO'
);

-- 4) SOLO_TRASPORTO
SELECT is(
  (SELECT script.fn_available_actions_ddt(d_solo_trasporto)->>'can_push_commessa_reason' FROM f),
  'DDT_SOLO_TRASPORTO',
  '4) causale non fatturabile (CONTO_LAVORO) -> DDT_SOLO_TRASPORTO'
);

-- 5) generico ANNULLATO
SELECT is(
  (SELECT script.fn_available_actions_ddt(d_annullato)->>'can_push_commessa_reason' FROM f),
  'DDT_NON_PUSHABILE',
  '5) DDT ANNULLATO -> generico DDT_NON_PUSHABILE (non la frase sullo stato)'
);

-- 6) PRECEDENZA a due livelli: documento (annullato) vince su riga (XOR)
SELECT is(
  (SELECT script.fn_available_actions_ddt(d_prec)->>'can_push_commessa_reason' FROM f),
  'DDT_NON_PUSHABILE',
  '6) ANNULLATO + ordine CONFERMATO: vince il documento (generico), non FATTURA_DA_ORDINE'
);

-- 7) NAMESPACE i18n
SELECT ok(
  (SELECT bool_and(k LIKE 'vendite.ddt.push_commessa_reason.%')
     FROM (VALUES ('d_fattura_ordine'),('d_in_viaggio'),('d_solo_trasporto'),('d_annullato')) s(col)
     CROSS JOIN LATERAL (
       SELECT script.fn_available_actions_ddt(
         CASE s.col WHEN 'd_fattura_ordine' THEN (SELECT d_fattura_ordine FROM f)
                    WHEN 'd_in_viaggio' THEN (SELECT d_in_viaggio FROM f)
                    WHEN 'd_solo_trasporto' THEN (SELECT d_solo_trasporto FROM f)
                    ELSE (SELECT d_annullato FROM f) END
       )->>'can_push_commessa_reason_key' AS k
     ) q
    WHERE k IS NOT NULL),
  '7) tutte le reason_key sotto vendite.ddt.push_commessa_reason.*'
);

SELECT * FROM finish();
ROLLBACK;
