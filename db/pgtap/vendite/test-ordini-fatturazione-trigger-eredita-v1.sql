-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: vendite.ordini.fatturazione_trigger — la TESTATA ha la precedenza,
--       il billing account e' il ripiego.
-- (changeset 20260817-01 funzione + 20260817-02 DROP DEFAULT)
--
-- Riferimenti: brief-be-fan-out-isolato-e-esito-parziale.md §13.2 ·
--              brief-design-fatturazione-due-lenti.md §6-quater, DL-19.
-- ------------------------------------------------------------
-- Indice test (1..5):
--   1) testata SPEDITO + BA che dice CONSEGNATO -> resta SPEDITO
--      (E' IL DIFETTO: prima trgfn_ordini_normalize sovrascriveva sempre)
--   2) colonna OMESSA + BA CONSEGNATO -> eredita CONSEGNATO
--      (discrimina dal vecchio DEFAULT 'CONFERMATO': se il default fosse
--       ancora li', qui uscirebbe CONFERMATO)
--   3) NULL esplicito + BA CONSEGNATO -> eredita CONSEGNATO
--      (dichiara che il NULL e' il modo di dire «non ho scelto»)
--   4) la colonna NON ha piu' un DEFAULT (presidio del changeSet -02: senza,
--      i test 2 e 3 non potrebbero passare, e si vuole sapere PERCHE')
--   5) il dominio regge ancora: valore fuori CHECK -> 23514
--
-- Scopo:
--  - Il campo «Trigger di fatturazione» del form ordine veniva scartato: la
--    scelta dell'operatore arrivava in testata e un BEFORE INSERT la
--    sovrascriveva con billing_account.fatturazione_ordini, sempre. Con tutti
--    i 42 BA a CONFERMATO nessun ordine poteva nascere SPEDITO/CONSEGNATO, e
--    il ramo order-backed di fn_list_ddt_da_pushare restava irraggiungibile.
--
--  - ⚠️ Il BA della fixture viene portato a CONSEGNATO dentro la transazione
--    APPOSTA: con i dati veri (BA e ordini tutti a CONFERMATO) i tre casi
--    darebbero lo stesso risultato per coincidenza, e il test sarebbe verde
--    anche col difetto in piedi. Il valore diverso e' cio' che rende le tre
--    asserzioni capaci di distinguere chi ha vinto.
--
--  - Il terzo ramo del COALESCE ('CONFERMATO', quando anche il BA tace) NON e'
--    asserito: billing_account.fatturazione_ordini e' NOT NULL, quindi si
--    raggiunge solo con un ordine SENZA billing account — zero su 92 nel
--    database. Costruirgli una fixture confermerebbe un ramo morto invece di
--    verificarne uno vivo.
--
-- ⚠️ PROVATO CONTRO IL DIFETTO, non solo scritto. Girato il 2026-08-17 sul
--    database PRIMA dell'apply dei due changeSet: 1, 4 e 5 falliscono, e
--    falliscono dicendo la cosa giusta —
--      test 1: «have: CONSEGNATO / want: SPEDITO», cioe' il difetto in atto;
--      test 4: il DEFAULT c'e' ancora;
--      test 5: «caught: no exception».
--    Non passa per il motivo sbagliato.
--
-- ⚠️ E il test 5 merita una riga in piu', perche' ha mostrato una conseguenza
--    che nessuno aveva descritto: OGGI un valore fuori dominio ('PIPPO') NON
--    solleva niente. Il trigger lo sovrascrive prima che il CHECK guardi,
--    quindi la colonna accetta spazzatura in INSERT e la ricicla in un valore
--    valido. Il CHECK non e' mai stato una difesa su questo percorso: lo
--    diventa con la correzione. Non era un buco (il valore veniva comunque
--    buttato) ma era una difesa che sembrava esserci e non c'era.
--
-- ⚠️ I test 2 e 3 passano ANCHE oggi, ed e' voluto: non guardano il difetto di
--    partenza ma quello INVERSO — un COALESCE messo senza togliere il DEFAULT
--    dalla colonna, che farebbe vincere sempre la testata e ucciderebbe
--    l'eredita' dal billing account. Con quella mezza correzione qui
--    uscirebbe CONFERMATO e i due diventerebbero rossi. Sono la rete
--    dell'altra meta' del lavoro.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Scattano al COMMIT, e qui il COMMIT non arriva mai (si chiude in
--   ROLLBACK): sarebbero saltati in silenzio e il file sarebbe verde per
--   sottrazione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza una veste dichiarata le
-- policy sono fail-closed e la fixture leggerebbe zero righe.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(5);

-- ============================================================
-- Riferimenti
-- ============================================================
-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE. Prima si pescava
--   il primo BA con un emittente risolvibile: da zero non c'era, e il primo
--   INSERT moriva su «p_billing_account_id obbligatorio». Il BA costruito e'
--   legato all'azienda di chi agisce; il ruolo del cliente e' il suo. Gli
--   INSERT a mano negli ordini RESTANO: sono il caso sotto test (il trigger
--   sull'INSERT). Valuta e stato DRAFT sono catalogo di seed.
-- ⚠️ ORDER BY su ogni scelta: senza, la fixture non verifica — scommette su
--   quale riga il planner restituisce per prima.
CREATE TEMP TABLE tmp_cli_ft AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('ordini fatturazione trigger');

CREATE TEMP TABLE tmp_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_cli_ft)                              AS billing_account_id,
  -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-4/D-5): il ruolo del cliente
  --   e' quello del BA scelto qui (le FK composte verso il BA lo rifiutano
  --   scollegato).
  (SELECT soggetto_ruolo_id FROM tmp_cli_ft)                               AS soggetto_ruolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                 AS valuta_id,
  (SELECT s.id FROM config.stati_doc_ordini s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE
    ORDER BY s.id LIMIT 1)                                                 AS stato_ord_draft_id;

-- Il BA della fixture dice CONSEGNATO: e' il perno del test (vedi Scopo).
UPDATE anagrafiche.billing_account
   SET fatturazione_ordini = 'CONSEGNATO'
 WHERE id = (SELECT billing_account_id FROM tmp_refs);

-- Scopo: crea un ordine DRAFT sul BA della fixture. p_trigger = il valore da
--        mettere in testata; p_ometti = TRUE per non nominare affatto la
--        colonna (il caso «l'operatore non ha scelto»).
CREATE OR REPLACE FUNCTION pg_temp.mk_ordine(p_trigger text, p_ometti boolean DEFAULT false)
RETURNS vendite.ordini.fatturazione_trigger%TYPE AS $$
DECLARE
  r        RECORD;
  v_ord    vendite.ordini.id%TYPE;
  v_letto  vendite.ordini.fatturazione_trigger%TYPE;
BEGIN
  SELECT * INTO r FROM tmp_refs;

  IF p_ometti THEN
    INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id,
      stato_doc_ordine_id, valuta_id, data, emittente_fiscale_id, storicizza, meta)
    VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_draft_id,
      r.valuta_id, script.fn_data_operativa(),
      anagrafiche.fn_get_emittente_fiscale_pk(r.billing_account_id), false,
      jsonb_build_object('test_scope', 'pgtap_fatt_trigger'))
    RETURNING id INTO v_ord;
  ELSE
    INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id,
      stato_doc_ordine_id, valuta_id, data, fatturazione_trigger,
      emittente_fiscale_id, storicizza, meta)
    VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_draft_id,
      r.valuta_id, script.fn_data_operativa(), p_trigger::varchar,
      anagrafiche.fn_get_emittente_fiscale_pk(r.billing_account_id), false,
      jsonb_build_object('test_scope', 'pgtap_fatt_trigger'))
    RETURNING id INTO v_ord;
  END IF;

  SELECT o.fatturazione_trigger INTO v_letto
    FROM vendite.ordini o WHERE o.id = v_ord;
  RETURN v_letto;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- 1) La testata vince sul billing account
-- ============================================================
SELECT is(
  pg_temp.mk_ordine('SPEDITO'),
  'SPEDITO'::varchar,
  '1. testata SPEDITO su un BA che dice CONSEGNATO -> resta SPEDITO (la scelta dell''operatore sopravvive all''INSERT)'
);

-- ============================================================
-- 2) Colonna omessa -> eredita dal billing account
-- ============================================================
SELECT is(
  pg_temp.mk_ordine(NULL, p_ometti => true),
  'CONSEGNATO'::varchar,
  '2. colonna omessa -> eredita CONSEGNATO dal BA (se il DEFAULT fosse ancora sulla colonna, qui uscirebbe CONFERMATO)'
);

-- ============================================================
-- 3) NULL esplicito -> eredita dal billing account
-- ============================================================
SELECT is(
  pg_temp.mk_ordine(NULL),
  'CONSEGNATO'::varchar,
  '3. NULL esplicito in testata -> eredita CONSEGNATO dal BA (NULL significa «non ho scelto»)'
);

-- ============================================================
-- 4) Il DEFAULT non c'e' piu' — presidio del changeSet -02
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pg_attrdef d
     JOIN pg_attribute a ON a.attrelid = d.adrelid AND a.attnum = d.adnum
    WHERE d.adrelid = 'vendite.ordini'::regclass
      AND a.attname = 'fatturazione_trigger'),
  0,
  '4. vendite.ordini.fatturazione_trigger non ha un DEFAULT: e'' la condizione che rende distinguibile «non scelto» da «scelto CONFERMATO»'
);

-- ============================================================
-- 5) Il dominio regge ancora
-- ============================================================
-- ⚠️ SQLSTATE esplicito: throws_ok senza codice accetterebbe QUALUNQUE errore,
--   compreso un crash del trigger — che passerebbe per una validazione
--   riuscita. 23514 = violazione di CHECK.
SELECT throws_ok(
  $$ SELECT pg_temp.mk_ordine('PIPPO') $$,
  '23514',
  NULL,
  '5. un valore fuori dal dominio resta respinto dal CHECK (il trigger non e'' diventato una porta di servizio)'
);

SELECT * FROM finish();
ROLLBACK;
