-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: una fattura che ha gia' CONSUMATO plafond non si disfa piu' —
--   script.fn_check_fatture_con_plafond_consumato, le tre porte di reset e
--   il guard di vendite.fn_cleanup_fatture_by_ids.
--   Brief: brief-db-bom-flag-quantita-e-kit-in-fattura §14 (strada A di Tid,
--   2026-10-04). changeSet: 20261004-07 … -11; la reason_key della porta
--   singola: 20261004-16 (R-DB-A2, §15.4).
--
-- IL CASO: il plafond si consuma all'emissione PRIMA della numerazione. Una
--   fattura con un movimento nel registro e senza numero passava le tre porte
--   (che rifiutano solo i documenti NUMERATI) e faceva esplodere la pulizia
--   con un 23503 grezzo sulle FK NO ACTION del registro.
--
-- ⭐ I CASI SI COSTRUISCONO: cliente, due fatture DRAFT senza numero, un
--   lotto DRAFT che le contiene, un titolo con plafond e UN movimento sulla
--   prima. La seconda e' il controllo (nessun movimento).
--
-- Indice test (1..11):
--    1) la check esiste
--    2) su un insieme vuoto o NULL risponde [] (non e' un errore)
--    3) su una fattura senza movimenti risponde []
--    4) su una fattura con un movimento: E_FATTURE_PLAFOND_CONSUMATO, 1 fattura
--    5) porta «elimina fattura»: il motivo c'e', con la frase della FATTURA
--    6) porta «riporta a draft»: il motivo c'e', con la frase del LOTTO
--    7) porta «annulla lotto»: il motivo c'e', con la frase del LOTTO
--    8) la madre «elimina fattura» solleva il codice, non un 23503
--    9) la pulizia, chiamata direttamente, solleva il codice
--   10) la fattura senza movimenti si elimina dal lotto senza problemi
--   11) il codice e' a catalogo in lingua it
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come l'applicazione (RLS attiva). Il
-- registro dei movimenti ha una policy di perimetro emittente.
CREATE TEMP TABLE tmp_rpc_ctx AS
SELECT script.fn_pgtap_set_contesto_operatore() AS auth_user_id;

SELECT plan(11);

-- ============================================================
-- FIXTURE
-- ============================================================
CREATE TEMP TABLE tmp_rpc_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('reset plafond consumato');

CREATE TEMP TABLE tmp_rpc_fatt AS
SELECT (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura('reset plafond A', 'DRAFT',
            (SELECT m.billing_account_id FROM tmp_rpc_mondo m)) f) AS fa,
       (SELECT f.fattura_id FROM dbops.fn_pgtap_crea_fattura('reset plafond B', 'DRAFT',
            (SELECT m.billing_account_id FROM tmp_rpc_mondo m)) f) AS fb;

-- Il lotto DRAFT che le contiene, con i dati della prima fattura.
CREATE TEMP TABLE tmp_rpc_lotto AS
WITH ins AS (
  INSERT INTO vendite.fatturazione_lotti (
      lock_batch_id, competenza_mese, tipo_doc_fiscale_id, utility_id,
      billing_account_id, stato_doc_fiscale_id, emittente_soggetto_ruolo_id)
  SELECT gen_random_uuid(), date_trunc('month', script.fn_data_operativa())::date,
         f.tipo_doc_fiscale_id, f.utility_id, f.billing_account_id,
         f.stato_doc_fiscale_id, f.emittente_soggetto_ruolo_id
    FROM vendite.fatture f
   WHERE f.id = (SELECT fa FROM tmp_rpc_fatt)
  RETURNING id)
SELECT id FROM ins;

INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id, stato_doc_fiscale_id)
SELECT (SELECT id FROM tmp_rpc_lotto), f.id, f.stato_doc_fiscale_id
  FROM vendite.fatture f
 WHERE f.id IN ((SELECT fa FROM tmp_rpc_fatt), (SELECT fb FROM tmp_rpc_fatt));

-- Il titolo con plafond e il movimento FATTURA sulla prima fattura: e' cio'
-- che il task consuma_plafond_lotto lascia dietro di se'.
CREATE TEMP TABLE tmp_rpc_titolo AS
WITH ins AS (
  INSERT INTO anagrafiche.soggetti_titoli_iva
      (soggetto_id, emittente_fiscale_id, tipo_titolo_iva_id, iva_id,
       ambito, valido_dal, valido_al, protocollo, plafond)
  SELECT (SELECT m.cliente_soggetto_id FROM tmp_rpc_mondo m),
         (SELECT uef.emittente_fiscale_id
            FROM config.user_emittenti_fiscali uef
           WHERE uef.auth_user_id = (SELECT auth_user_id FROM tmp_rpc_ctx)
           ORDER BY uef.emittente_fiscale_id LIMIT 1),
         (SELECT t.id FROM config.tipi_titolo_iva t WHERE t.codice_interno = 'INTENTO'),
         (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1),
         'TUTTO', DATE '2050-01-01', DATE '2050-12-31', 'PGTAP-RPC-2050', 1000.00
  RETURNING id)
SELECT id FROM ins;

INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
    (titolo_iva_id, tipo_movimento, imponibile, data_movimento, fattura_id)
SELECT (SELECT id FROM tmp_rpc_titolo), 'FATTURA', 100.00, DATE '2050-06-15',
       (SELECT fa FROM tmp_rpc_fatt);

-- ============================================================
-- 1..4 — la check
-- ============================================================
SELECT ok(
    to_regprocedure('script.fn_check_fatture_con_plafond_consumato(bigint[])') IS NOT NULL,
    '1) script.fn_check_fatture_con_plafond_consumato esiste');

SELECT ok(
    script.fn_check_fatture_con_plafond_consumato(ARRAY[]::bigint[]) = '[]'::jsonb
    AND script.fn_check_fatture_con_plafond_consumato(NULL) = '[]'::jsonb,
    '2) su un insieme vuoto o NULL risponde []: un lotto senza fatture non e'' un errore');

SELECT is(
    script.fn_check_fatture_con_plafond_consumato(ARRAY[(SELECT fb FROM tmp_rpc_fatt)]),
    '[]'::jsonb,
    '3) una fattura senza movimenti non ha motivi');

SELECT is(
    (SELECT (m ->> 'codice') || '/' || (m ->> 'reason') || '/' || (m ->> 'dettaglio')
       FROM jsonb_array_elements(script.fn_check_fatture_con_plafond_consumato(
                ARRAY[(SELECT fa FROM tmp_rpc_fatt), (SELECT fb FROM tmp_rpc_fatt)])) m),
    'E_FATTURE_PLAFOND_CONSUMATO/PLAFOND_CONSUMATO/1',
    '4) con un movimento: E_FATTURE_PLAFOND_CONSUMATO, e il dettaglio conta le FATTURE (1 su 2)');

-- ============================================================
-- 5..7 — le tre porte di reset
-- ============================================================
-- ⭐ rev 2026-10-04 bis (R-DB-A2): si asserisce anche la reason_key. La domanda
--   e' una (la sede unica), le frasi due: la porta della fattura parla di
--   QUELLA fattura, le due del lotto del lotto. Tre test che guardassero il
--   solo codice resterebbero verdi con la frase sbagliata a video.
SELECT ok(
    script.fn_check_fattura_eliminabile_da_lotto(
        (SELECT id FROM tmp_rpc_lotto), (SELECT fa FROM tmp_rpc_fatt))
      @> '[{"codice": "E_FATTURE_PLAFOND_CONSUMATO",
            "reason_key": "vendite.lotti.azione_reason.fattura_plafond_consumato"}]'::jsonb,
    '5) «elimina fattura»: la fattura che ha consumato plafond porta il motivo, con la frase della fattura');

SELECT ok(
    script.fn_check_lotto_riportabile_a_draft((SELECT id FROM tmp_rpc_lotto))
      @> '[{"codice": "E_FATTURE_PLAFOND_CONSUMATO",
            "reason_key": "vendite.lotti.azione_reason.plafond_consumato"}]'::jsonb,
    '6) «riporta a draft»: il lotto con una fattura che ha consumato porta il motivo, con la frase del lotto');

SELECT ok(
    script.fn_check_lotto_annullabile((SELECT id FROM tmp_rpc_lotto))
      @> '[{"codice": "E_FATTURE_PLAFOND_CONSUMATO",
            "reason_key": "vendite.lotti.azione_reason.plafond_consumato"}]'::jsonb,
    '7) «annulla lotto»: il lotto con una fattura che ha consumato porta il motivo, con la frase del lotto');

-- ============================================================
-- 8..10 — le scritture si fermano col codice, non con un 23503
-- ============================================================
-- Il frammento e' la frase del messaggio: P0001 da solo passerebbe per
-- qualunque errore di dominio, e un 23503 non avrebbe questa frase.
SELECT throws_like(
    format('SELECT * FROM vendite.fn_elimina_fattura_da_lotto(%s, %s)',
           (SELECT id FROM tmp_rpc_lotto), (SELECT fa FROM tmp_rpc_fatt)),
    '%consumato il plafond%',
    '8) la madre «elimina fattura» solleva E_FATTURE_PLAFOND_CONSUMATO invece di esplodere sulla FK');

SELECT throws_like(
    format('SELECT * FROM vendite.fn_cleanup_fatture_by_ids(ARRAY[%s]::bigint[], NULL::uuid)',
           (SELECT fa FROM tmp_rpc_fatt)),
    '%consumato il plafond%',
    '9) la pulizia chiamata direttamente solleva il codice: e'' la difesa della quarta porta');

-- ⚠️ Il controllo: il motivo nuovo non deve fermare cio' che prima passava.
SELECT ok(
    (SELECT deleted_fatture = 1
       FROM vendite.fn_elimina_fattura_da_lotto(
                (SELECT id FROM tmp_rpc_lotto), (SELECT fb FROM tmp_rpc_fatt)))
    AND (SELECT count(*) = 1 FROM anagrafiche.soggetti_titoli_iva_movimenti m
          WHERE m.fattura_id = (SELECT fa FROM tmp_rpc_fatt)),
    '10) la fattura senza movimenti si elimina dal lotto; il movimento dell''altra resta');

SELECT is(
    (SELECT count(*)::integer FROM config.messaggi_errore m
      WHERE m.codice = 'E_FATTURE_PLAFOND_CONSUMATO' AND m.lingua = 'it'),
    1,
    '11) E_FATTURE_PLAFOND_CONSUMATO e'' a catalogo in lingua it');

SELECT * FROM finish();
ROLLBACK;
