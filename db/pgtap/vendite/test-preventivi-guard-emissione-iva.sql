-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_check_preventivo_emettibile + Regola 2 di
--       vendite.trgfn_preventivi_guard_transizione + lato lettura
--       script.fn_available_actions_preventivo   (I9 / §R-3)
-- ------------------------------------------------------------
-- Elenco test (plan 8):
-- 0) riferimenti minimi presenti                        (fixture non muta)
-- 1) riga CON aliquota -> la fn pura non trova motivi
-- 2) riga SENZA aliquota -> un motivo, col codice giusto
-- 3) il motivo porta la DESCRIZIONE della riga            (non un numero)
-- 4) ⭐ riga senza aliquota ma a quantita ZERO -> NESSUN motivo (perimetro)
-- 5) il bottone Emetti e' spento, con la reason
-- 6) ⭐ DRAFT->EMESSO con riga senza aliquota -> BLOCCA
-- 7) controllo: la stessa transizione con l'aliquota -> PASSA
--
-- Scopo:
--   Terzo gemello del gate «una riga valorizzata porta l'aliquota», dopo il DDT
--   (2026-08-28) e l'ordine (2026-08-29). Il difetto e' SILENZIOSO:
--   vendite.fn_ricalcola_riepilogo_iva_preventivo aggrega le righe con
--   `attivo IS TRUE AND quantita > 0` e calcola l'imposta con
--   COALESCE(config.fn_get_aliquota_iva(iva_id, stato), 0), quindi una riga
--   senza aliquota finisce in vendite.preventivi_riepiloghi_iva con imponibile
--   PIENO e imposta ZERO. Nessun errore: solo un numero sbagliato su un
--   documento emesso.
--
--   ⭐ IL TEST 4 E' QUELLO CHE VALE, e prova il lato che nessuno prova mai: che
--   il guard NON blocchi piu' di quanto serve. Il predicato della funzione pura
--   e' copiato dal consumatore (`attivo IS TRUE AND quantita > 0`), quindi una
--   riga a quantita zero senza aliquota — che nel riepilogo NON ENTRA — deve
--   lasciar passare l'emissione. Con un predicato copiato dalla gemella sugli
--   ordini quel caso bloccherebbe un preventivo sano, e nessun altro test se ne
--   accorgerebbe.
--   ⚠️ Il caso esiste sul modello: `preventivi_righe.quantita` e' NULLABILE e
--   NON ha un CHECK di positivita', mentre `vendite.ordini_righe` ce l'ha
--   (chk_ordini_v_r_qta_pos). E' la ragione per cui le due funzioni pure NON
--   sono una copia l'una dell'altra.
--
--   ⚠️ Il test 3 guarda la DESCRIZIONE e non un numero di riga:
--   `preventivi_righe` NON HA `riga_nr`, e la colonna `ordine` ha default 0 —
--   un messaggio che dicesse «la riga 0» non aiuterebbe nessuno.
--
--   Piano: brief-db-be-iva-risolutore-e-regime-cliente.md
--     I9 / §R-3 · changeSet 20260829-09 (fn pura), -10 (guard), -11 (capability)
--
--   rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): lo stato del
--   preventivo si cambia solo dal verbo vendite.fn_cambia_stato_preventivo: i
--   test 6-7 chiedono DRAFT -> EMESSO al verbo, che arriva al guard e prende la
--   sua frase (un UPDATE diretto lo ferma prima la porta,
--   E_DOC_STATO_SOLO_DAL_VERBO). L'operatore riceve emetti_preventivo prima del
--   test 5: senza, «Emetti» e' nascosto e il verbo rifiuta col permesso.
--   Attese invariate.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE: senza, un fallimento a meta' lascia la fixture nel database.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO: il test gira come gira l'applicazione (ruolo
--   OPERATORE + RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI: qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(9);

-- ============================================================
-- 0) Riferimenti
-- ============================================================
-- ⚠️ L'emittente si DERIVA dal BA (come per l'ordine): il guard
--   trgfn_preventivi_guard_emittente_ba pretende la coerenza, e sceglierlo per
--   conto proprio farebbe fallire il test su un errore che non c'entra.
-- ⚠️ Il BA si sceglie UNA volta in una CTE e sotto la veste dell'operatore:
--   due sotto-select indipendenti potrebbero pescarne due diversi.
CREATE TEMP TABLE tmp_pi_refs AS
WITH ba AS (
  SELECT b.id, b.istanza_utility_id, b.utility_id
    FROM anagrafiche.billing_account b
   WHERE b.utility_id IS NOT NULL
     AND b.istanza_utility_id IS NOT NULL
     AND anagrafiche.fn_get_emittente_fiscale_pk(b.id) IS NOT NULL
   ORDER BY b.id
   LIMIT 1
)
SELECT (SELECT id FROM ba)                                    AS billing_account_id,
       (SELECT istanza_utility_id FROM ba)                    AS istanza_utility_id,
       (SELECT utility_id FROM ba)                            AS utility_id,
       anagrafiche.fn_get_emittente_fiscale_pk((SELECT id FROM ba)) AS emittente_fiscale_id,
       (SELECT a.id FROM catalogo.articoli a
         WHERE a.attivo IS TRUE
           AND COALESCE(a.is_composito, FALSE) IS FALSE
         ORDER BY a.id LIMIT 1)                               AS articolo_id,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
       (SELECT i.id FROM config.iva i
         WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)        AS iva_id,
       (SELECT s.id FROM config.stati_doc_preventivi s
         WHERE s.codice_interno = 'DRAFT'  ORDER BY s.id LIMIT 1) AS stato_draft_id,
       (SELECT s.id FROM config.stati_doc_preventivi s
         WHERE s.codice_interno = 'EMESSO' ORDER BY s.id LIMIT 1) AS stato_emesso_id;

SELECT ok(
    (SELECT billing_account_id IS NOT NULL AND emittente_fiscale_id IS NOT NULL
        AND articolo_id IS NOT NULL AND valuta_id IS NOT NULL AND iva_id IS NOT NULL
        AND stato_draft_id IS NOT NULL AND stato_emesso_id IS NOT NULL
       FROM tmp_pi_refs),
    'Riferimenti minimi presenti'
  );

-- ============================================================
-- Fixture: preventivo in DRAFT con UNA riga attiva, senza aliquota
-- ============================================================
-- ⚠️ Padre e figlio in DUE istruzioni, non in una CTE sola: le CTE che scrivono
--   condividono la stessa snapshot e una policy che risolve il perimetro dal
--   padre non lo troverebbe.
CREATE TEMP TABLE tmp_pi_prev AS
WITH ins AS (
  INSERT INTO vendite.preventivi (
      numero, rev, billing_account_id, istanza_utility_id, utility_id,
      validita_dal, validita_al, valuta_id,
      stato_doc_preventivo_id, data, emittente_fiscale_id, storicizza, meta)
  SELECT 'PGTAP-PREV-IVA', 0,
         r.billing_account_id, r.istanza_utility_id, r.utility_id,
         DATE '2080-01-01', DATE '2080-12-31', r.valuta_id,
         r.stato_draft_id, DATE '2080-01-01', r.emittente_fiscale_id, false,
         jsonb_build_object('test_scope', 'pgtap_preventivo_emissione_iva')
    FROM tmp_pi_refs r
  RETURNING id
)
SELECT * FROM ins;

INSERT INTO vendite.preventivi_righe (
    preventivo_id, articolo_id, descrizione, quantita, qta_operativa,
    prezzo_unitario, iva_id, attivo, ordine, meta)
SELECT (SELECT id FROM tmp_pi_prev), r.articolo_id, 'Voce senza aliquota',
       2.000000, 2.000000, 100.000000, NULL, true, 1,
       jsonb_build_object('test_scope', 'pgtap_preventivo_emissione_iva')
  FROM tmp_pi_refs r;

-- ============================================================
-- 1-3) La funzione pura
-- ============================================================
UPDATE vendite.preventivi_righe
   SET iva_id = (SELECT iva_id FROM tmp_pi_refs)
 WHERE preventivo_id = (SELECT id FROM tmp_pi_prev);

SELECT is(
    script.fn_check_preventivo_emettibile((SELECT id FROM tmp_pi_prev)),
    '[]'::jsonb,
    'Riga CON aliquota: nessun motivo ostativo all''emissione'
  );

UPDATE vendite.preventivi_righe
   SET iva_id = NULL
 WHERE preventivo_id = (SELECT id FROM tmp_pi_prev);

SELECT is(
    script.fn_check_preventivo_emettibile((SELECT id FROM tmp_pi_prev)) -> 0 ->> 'codice',
    'E_PREV_RIGA_IVA_MANCANTE',
    'Riga SENZA aliquota: un motivo, ed e'' quello giusto'
  );

-- ⚠️ La DESCRIZIONE e non un numero: preventivi_righe non ha riga_nr, e
--   `ordine` ha default 0. E' il valore che finisce nel VARIADIC, cioe' nella
--   frase che legge una persona.
SELECT is(
    script.fn_check_preventivo_emettibile((SELECT id FROM tmp_pi_prev))
      -> 0 -> 'dettaglio' ->> 'descrizione',
    'Voce senza aliquota',
    'Il motivo porta la DESCRIZIONE della riga, non un numero'
  );

-- ⭐ P-1 — LA FRASE RESA. E' l'unica verifica che vede l'ORDINE dei valori:
--   il ramo C di test-catalogo-messaggi-errore-completo.sql prova che sono
--   TANTI QUANTI i segnaposto, non che siano quelli giusti al posto giusto.
--   Il precedente e' del 2026-09-01 su E_REGISTRO_SERIE_NON_AMMESSA — due
--   valori, due segnaposto, «Registro X1» a video con la serie al posto della
--   famiglia — e nel 2026-09-09 lo stesso difetto e' stato trovato VIVO su due
--   siti di questo cantiere.
-- ⚠️ Si confronta con la frase composta dai valori letti dalla TABELLA: se la
--   check li emettesse invertiti, le due stringhe divergerebbero. Un `matches`
--   su un pezzo di frase non lo vedrebbe.
-- ⚠️ Il CASE con `coalesce` non e' pignoleria: senza, una check che smettesse
--   di emettere `valori` farebbe alzare 22023 a format() e ABORTIREBBE il file.
--   E scritto con un `<>` nudo non guarderebbe niente: `jsonb_typeof(NULL) <>
--   'array'` vale NULL, non vero.
SELECT is(
  (WITH v AS (SELECT script.fn_check_preventivo_emettibile((SELECT id FROM tmp_pi_prev)) -> 0 AS motivo)
   SELECT CASE
            WHEN coalesce(jsonb_typeof(v.motivo -> 'valori'), 'assente') <> 'array'
              THEN '(la check non emette valori)'
            ELSE format(
                   (SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_PREV_RIGA_IVA_MANCANTE' AND m.lingua = 'it'),
                   VARIADIC ARRAY(SELECT jsonb_array_elements_text(v.motivo -> 'valori')))
          END
     FROM v),
  (SELECT format((SELECT m.messaggio FROM config.messaggi_errore m
                     WHERE m.codice = 'E_PREV_RIGA_IVA_MANCANTE' AND m.lingua = 'it'),
                 p.numero, 'Voce senza aliquota')
     FROM vendite.preventivi p WHERE p.id = (SELECT id FROM tmp_pi_prev)),
  'La frase resa nomina il NUMERO del preventivo e poi la DESCRIZIONE, in quest''ordine'
  );

-- ============================================================
-- 4) ⭐ Il perimetro: quantita zero -> la riga non entra nel riepilogo
-- ============================================================
-- ⛔ Con un predicato copiato dalla gemella sugli ordini (che il `quantita > 0`
--   non ce l'ha, perche' li' un CHECK lo garantisce) questo caso bloccherebbe
--   un preventivo SANO: la riga a quantita zero in
--   preventivi_riepiloghi_iva non entra mai.
UPDATE vendite.preventivi_righe
   SET quantita = 0
 WHERE preventivo_id = (SELECT id FROM tmp_pi_prev);

SELECT is(
    script.fn_check_preventivo_emettibile((SELECT id FROM tmp_pi_prev)),
    '[]'::jsonb,
    'Riga senza aliquota ma a quantita ZERO: nessun motivo, non entra nel riepilogo'
  );

-- Si ripristina la quantita: i test seguenti provano il caso che deve bloccare.
UPDATE vendite.preventivi_righe
   SET quantita = 2.000000
 WHERE preventivo_id = (SELECT id FROM tmp_pi_prev);

-- ============================================================
-- 5) Il lato lettura: il bottone Emetti e' spento, e dice perche'
-- ============================================================
-- ⭐ Senza questo, l'operatore vedrebbe un bottone acceso e prenderebbe un
--   errore al click: guard e capability devono leggere la STESSA funzione.
-- ⚠️ rev 2026-10-25 (giro 6): «Emetti» porta il permesso emetti_preventivo e si
--   nasconde a chi non l'ha. Il file prova l'aliquota, non il permesso:
--   l'operatore lo riceve qui, e serve anche al verbo dei test 6-7.
DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_preventivo');
END $az$;

SELECT is(
    (SELECT a ->> 'reason'
       FROM jsonb_array_elements(
              script.fn_available_actions_preventivo((SELECT id FROM tmp_pi_prev))
                -> 'available_actions') a
      WHERE a ->> 'target_state' = 'EMESSO'),
    'RIGA_SENZA_ALIQUOTA',
    'Il bottone Emetti e'' spento ed espone la reason della riga senza aliquota'
  );

-- ============================================================
-- 6-7) Il guard: DRAFT -> EMESSO
-- ============================================================
-- ⚠️ throws_like e non throws_ok(...,'P0001'): su questa transizione il guard sa
--   sollevare anche E_PREV_TRANSIZIONE_NON_AMMESSA, e P0001 direbbe solo «e' un
--   errore di dominio», non QUALE. Il discriminante e' la frase.
-- ⚠️ Il pattern non attraversa i segnaposto.
-- ⚠️ rev 2026-10-25 (giro 6): il passaggio si chiede al VERBO
--   vendite.fn_cambia_stato_preventivo, che arriva al guard: un UPDATE diretto
--   lo fermerebbe prima la porta (E_DOC_STATO_SOLO_DAL_VERBO).
SELECT throws_like(
    format($$SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, 'EMESSO')$$,
           (SELECT id FROM tmp_pi_prev)),
    '%prezzo ma nessuna aliquota IVA%',
    'DRAFT->EMESSO con una riga senza aliquota: BLOCCA'
  );

-- Controllo: senza, un rosso del test 6 potrebbe venire dalla fixture.
UPDATE vendite.preventivi_righe
   SET iva_id = (SELECT iva_id FROM tmp_pi_refs)
 WHERE preventivo_id = (SELECT id FROM tmp_pi_prev);

SELECT lives_ok(
    format($$SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, 'EMESSO')$$,
           (SELECT id FROM tmp_pi_prev)),
    'DRAFT->EMESSO con l''aliquota: PASSA'
  );

SELECT * FROM finish();
ROLLBACK;
