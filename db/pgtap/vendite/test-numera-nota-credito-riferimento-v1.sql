-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.fn_numera_fattura_opz_emessa — non si numera un documento che
--       rettifica una fattura ancora senza numero
--       (E_FATTURA_RETTIFICATA_SENZA_NUMERO, changeSet 20260821-05)
-- ------------------------------------------------------------
-- ⛔ Prima di 20260821-05 questo file e' ROSSO su UN test solo — il 2 — e vale
--    la pena sapere perche', misurato il 2026-08-21:
--      2  have E_FATTURA_NON_NUMERABILE_INCOERENTE, want
--         E_FATTURA_RETTIFICATA_SENZA_NUMERO   <- ⭐ l'unico che misura il difetto
--      3  VERDE anche senza la guardia, e NON perche' la guardia funzioni: la
--         numerazione si ferma comunque prima, su un'altra precondizione
--         (piano rate). Il numero resta NULL per un motivo che non c'entra.
--      1,4,5 verdi anche senza: sono invarianti, non misure.
--    ⚠️ Il 3 e' quindi VERDE PER SOTTRAZIONE in questa fixture, ed e' scritto
--    qui perche' chi legge «cinque test» sappia che il difetto lo misura UNO.
--    Resta utile: il giorno in cui la fixture soddisfacesse anche il piano rate,
--    il 3 diventerebbe l'unica prova che il numero non e' stato consumato.
--
-- 📌 E c'e' una conseguenza per chi valuta il rischio: oggi, sui dati veri, una
--    nota di credito non si numera comunque prima del tempo — la fermerebbe
--    quell'altra precondizione. Il difetto segnalato dal BE e' reale ma
--    MASCHERATO da un controllo che parla d'altro, e un controllo che protegge
--    per caso non e' un presidio: il giorno in cui il piano rate c'e', la nota
--    passerebbe. E' il motivo per cui la guardia si scrive lo stesso.
--    Con il changeSet applicato: 5/5.
--
-- Indice test (1..5):
--   1) fixture: due documenti, la NC rettifica riga per riga il padre, e
--      nessuno dei due e' numerato
--   2) ⭐ numerare la NC RIFIUTA, con E_FATTURA_RETTIFICATA_SENZA_NUMERO nel
--      canale CONSTRAINT
--   3) e la NC e' rimasta senza numero: il rifiuto arriva PRIMA che il numero
--      venga consumato — che e' l'unica cosa che non si torna indietro
--   4) nessuna regressione: su una fattura ORDINARIA la guardia non vede nulla
--   5) ⭐ dato un numero al padre, la guardia si spegne
--
-- ⚠️ PERCHE' IL TEST 5 NON DICE «la NC si numera». Numerare ha ALTRE
--    precondizioni che non c'entrano con questa guardia: la prima che si
--    incontra e' «piano rate assente», sollevata da vendite.fn_assign_numero_fattura
--    DOPO di noi. Soddisfarle qui vorrebbe dire costruire mezza fatturazione in
--    una fixture e collaudare quella invece di questa guardia. Si asserisce
--    quindi che il codice sollevato NON sia piu' il nostro: e' esattamente la
--    proprieta' che serve — la guardia si e' spenta — e non una di meno.
--
-- ⚠️ COSA QUESTO FILE NON MISURA, e va detto invece di sembrare coperto: il
--    ramo FAIL-CLOSED sulla visibilita'. La guardia usa dei LEFT JOIN e conta
--    come bloccante anche la riga il cui documento padre non e' VISIBILE
--    (RLS, perimetro emittente diverso). Per esercitarlo servirebbe una
--    seconda fattura intestata a un altro emittente e un operatore che non la
--    veda: una fixture a due perimetri, che e' un file a se'. E un puntatore
--    penzolante non si puo' fabbricare — fatture_righe.riga_rettificata_id ha
--    una chiave esterna (fk_fatture_righe_riga_rettificata).
--
-- ⚠️ Il codice di dominio si legge dal canale CONSTRAINT dell'eccezione, non
--    dal testo: e' il contratto di script.fn_log_and_raise_error, e cosi' il
--    file e' verde anche prima che il mirror CSV di 80_data carichi la riga
--    del codice nuovo.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

SET LOCAL app.ruolo_applicativo = 'OPERATORE';
SET LOCAL app.current_user_id = '1';

CREATE TEMP TABLE tmp_refs_nnc AS
SELECT
  ba.id                                    AS billing_account_id,
  ba.utility_id                            AS utility_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_sr_id,
  (SELECT a.id FROM catalogo.articoli a
    WHERE a.attivo IS TRUE AND COALESCE(a.is_composito, FALSE) IS FALSE
    ORDER BY a.data_insert DESC NULLS LAST, a.id DESC LIMIT 1)                            AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)            AS iva_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                               AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno='DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_draft_id,
  (SELECT r.id FROM vendite.registri_fatturazione r WHERE r.attivo IS TRUE ORDER BY r.id LIMIT 1)                         AS registro_id,
  config.fn_get_natura_doc_fiscale_id('FATTURA')      AS natura_fattura_id,
  config.fn_get_natura_doc_fiscale_id('NOTA_CREDITO') AS natura_nc_id
FROM anagrafiche.billing_account ba
WHERE ba.utility_id IS NOT NULL
  AND anagrafiche.fn_get_emittente_fiscale_id(ba.id) IS NOT NULL
ORDER BY ba.id
LIMIT 1;

-- Un documento con una riga. `p_natura_id` distingue il padre dalla nota, ma
-- la guardia NON lo legge: guarda le righe. Sta qui per realismo, non perche'
-- serva — ed e' il punto del §44.
CREATE OR REPLACE FUNCTION pg_temp.nnc_mk_doc(p_natura_id bigint, p_qta numeric, p_prezzo numeric)
RETURNS TABLE(fattura_id bigint, riga_id bigint) AS $$
DECLARE r RECORD; v_f bigint; v_r bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_nnc;
  INSERT INTO vendite.fatture (registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
      emittente_soggetto_ruolo_id, billing_account_id, utility_id, valuta_id, tasso_cambio,
      natura_doc_id, meta)
  VALUES (r.registro_id, DATE '2026-08-21', r.tipo_doc_fiscale_id, r.stato_draft_id,
      r.emittente_sr_id, r.billing_account_id, r.utility_id, r.valuta_id, 1,
      p_natura_id, jsonb_build_object('test_scope','pgtap_numera_nc'))
  RETURNING id INTO v_f;

  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione,
      uom_id, qta, prezzo_unitario, iva_id, imponibile_riga)
  VALUES (v_f, 1, r.articolo_id, 'Riga pgTAP numerazione NC', r.uom_id, p_qta, p_prezzo,
      r.iva_id, p_qta * p_prezzo)
  RETURNING id INTO v_r;

  RETURN QUERY SELECT v_f, v_r;
END $$ LANGUAGE plpgsql;

-- ⭐ L'esito della numerazione come CODICE di dominio (canale CONSTRAINT), o
--    'OK' se e' passata. E' il contratto di script.fn_log_and_raise_error e non
--    lega il test alla formulazione del catalogo.
CREATE OR REPLACE FUNCTION pg_temp.nnc_esito(p_fattura_id bigint)
RETURNS text AS $$
DECLARE v_cod text;
BEGIN
  PERFORM vendite.fn_numera_fattura_opz_emessa(p_fattura_id, false);
  RETURN 'OK';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_cod, ''), 'SQLSTATE:' || SQLSTATE);
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE: un padre e una nota che ne rettifica la riga.
-- ⚠️ Padre e figlio in DUE istruzioni: le CTE che scrivono condividono la
--    stessa snapshot, e una policy che risolve il perimetro dal padre non lo
--    troverebbe.
-- ============================================================
CREATE TEMP TABLE tmp_padre AS
SELECT * FROM pg_temp.nnc_mk_doc((SELECT natura_fattura_id FROM tmp_refs_nnc), 10, 25);

CREATE TEMP TABLE tmp_nc AS
SELECT * FROM pg_temp.nnc_mk_doc((SELECT natura_nc_id FROM tmp_refs_nnc), -4, 25);

UPDATE vendite.fatture_righe
   SET riga_rettificata_id = (SELECT riga_id FROM tmp_padre)
 WHERE id = (SELECT riga_id FROM tmp_nc);

SELECT is(
  (SELECT count(*)::int FROM vendite.fatture
    WHERE id IN ((SELECT fattura_id FROM tmp_padre), (SELECT fattura_id FROM tmp_nc))
      AND numero IS NULL)::text
  || '|' ||
  (SELECT (riga_rettificata_id = (SELECT riga_id FROM tmp_padre))::text
     FROM vendite.fatture_righe WHERE id = (SELECT riga_id FROM tmp_nc)),
  '2|true',
  '1) fixture: due documenti senza numero, e la nota rettifica la riga del padre'
);

-- ============================================================
-- IL RIFIUTO
-- ⚠️ Il verbo in un'istruzione SEPARATA dall'asserzione: la snapshot di
--    statement leggerebbe PRIMA delle scritture.
-- ============================================================
CREATE TEMP TABLE tmp_esito_1 AS
SELECT pg_temp.nnc_esito((SELECT fattura_id FROM tmp_nc)) AS esito;

SELECT is(
  (SELECT esito FROM tmp_esito_1),
  'E_FATTURA_RETTIFICATA_SENZA_NUMERO',
  '2) numerare la nota di credito e'' RIFIUTATO, col codice giusto'
);

-- ⭐ Il numero non e' stato consumato: il rifiuto arriva PRIMA
--    dell'assegnazione, che e' l'unico passo irreversibile del giro.
SELECT is(
  (SELECT numero FROM vendite.fatture WHERE id = (SELECT fattura_id FROM tmp_nc)),
  NULL::bigint,
  '3) e il numero non e'' stato consumato: la nota e'' ancora senza numero'
);

-- ============================================================
-- 4) NESSUNA REGRESSIONE su un documento che non rettifica niente.
--    Il padre non ha righe con riga_rettificata_id, quindi la guardia non deve
--    nemmeno vederlo. ⚠️ Non si asserisce 'OK': numerare ha altre
--    precondizioni (la prima e' «piano rate assente», da fn_assign_numero_fattura)
--    che non c'entrano con questo file. Si asserisce che il codice NON sia il
--    nostro — che e' la proprieta' che serve.
-- ============================================================
CREATE TEMP TABLE tmp_esito_2 AS
SELECT pg_temp.nnc_esito((SELECT fattura_id FROM tmp_padre)) AS esito;

SELECT isnt(
  (SELECT esito FROM tmp_esito_2),
  'E_FATTURA_RETTIFICATA_SENZA_NUMERO',
  '4) una fattura che non rettifica nulla non e'' toccata dalla guardia'
);

-- ============================================================
-- 5) ⭐ DATO UN NUMERO AL PADRE, LA GUARDIA SI SPEGNE.
--    Il numero si mette a mano: qui interessa che il padre RISULTI numerato,
--    non come ci sia arrivato — e passare dalla sua funzione vorrebbe dire
--    soddisfare precondizioni che non sono il soggetto di questo file.
-- ============================================================
UPDATE vendite.fatture
   SET numero = 999999, anno = 2026
 WHERE id = (SELECT fattura_id FROM tmp_padre);

CREATE TEMP TABLE tmp_esito_3 AS
SELECT pg_temp.nnc_esito((SELECT fattura_id FROM tmp_nc)) AS esito;

SELECT isnt(
  (SELECT esito FROM tmp_esito_3),
  'E_FATTURA_RETTIFICATA_SENZA_NUMERO',
  '5) numerato il padre, la guardia non morde piu'''
);

SELECT * FROM finish();
ROLLBACK;
