-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso in bozza dal builder dbops.fn_pgtap_crea_reso; restano scritti a mano la conferma e l'annullo fn_annulla_reso, che sono i passi dei test 7 e 8 (per loro resta concessa conferma_reso).
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (CONSEGNATO, EMESSO; ANNULLATO = EMESSO + il verbo vendite.fn_annulla_ddt, che resta perche' l'annullo con legami passa da li'); il reso resta scritto a mano (giro 2).
-- pgTAP test per Zero ERP
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a, 20261019-40 … -79):
--   il documento passato ai lettori delle testate, ai legami e ai montaggi del
--   lock e' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA,
--   OFFERTA_COMMERCIALE, RESO_VENDITA). Restano corti i prefissi delle chiavi
--   (G-8), l'origine dei legami (V7) e l'ambito degli indirizzi (G-6).
-- Test: rami DDT e RESO della proiezione di stato (vw_stato_sorgente_*)
--       — step 6b, brief-db-fatturazione-ddt-resi §4a.
-- (changeset 20260718-09/-10)
-- ------------------------------------------------------------
-- Indice test (1..8):
--   1) ramo DDT: il documento proietta, risolto=true, via union
--   2) 🔑 LA CHIAVE E' `id`, NON l'uid: cercare per uid NON trova nulla.
--      E' l'asserzione che protegge dalla "ripulitura" della convenzione
--      polimorfa (key_selector), che romperebbe il ramo in silenzio
--   3) DDT CONSEGNATO -> esito POSITIVO, terminale true (fase CHIUSO)
--   4) DDT ANNULLATO  -> esito NEGATIVO, terminale true (is_abortito)
--   5) DDT EMESSO     -> esito NULL, terminale false (fase IN_CORSO)
--   6) ramo RESO: reso DRAFT -> esito NULL, terminale false (fase APERTO)
--   7) reso CONFERMATO -> esito POSITIVO, terminale true (correzione catalogo
--      2026-07-18: CONFERMATO ha fase CHIUSO — un reso confermato E' concluso,
--      la ri-consegna e' un altro documento; l'annullo resta come storno)
--   8) reso ANNULLATO -> esito NEGATIVO, terminale true
--   10) ramo a chiave id ATTRAVERSO fn_stato_sorgente: il DDT CONSEGNATO si
--       trova cercando la chiave numerica (rev 2026-10-05, 20261005-23)
--   11) la regola d'incontro: con id e uid del DDT si trova, col solo uid
--       (non e' la chiave del DDT) e' UNKNOWN (giro P.1)
--   12) la chiave nativa del ramo e' coerente col testo: sorgente_chiave_id =
--       ddt.id e sorgente_chiave_uuid NULL
--   13) script.vw_pratica_doc_sorgente risolve un collegamento a chiave id:
--       una pratica col DDT CONSEGNATO come ROOT proietta POSITIVO/terminale
--       (rev 2026-10-05, 20261005-24: la LATERAL per chiave nativa, ramo bigint)
--   9) unicita': al piu' una riga per (sorgente_tipo_id, sorgente_uid) su
--      entrambi i rami nuovi
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
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (in CI l'utente 1 non esiste;
--   anagrafiche e articoli sono vuoti). fn_pgtap_crea_mondo_cliente fa azienda,
--   operatore, cliente BA legato a quell'azienda e APRE il contesto da se'.
CREATE TEMP TABLE _m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP stato sorgente');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM _m)); END $ctx$;

-- L'annullo di una bolla emessa passa dal verbo di stato, che chiede l'azione
-- emetti_ddt (rev 2026-10-11, D-8 di brief-db-ddt-righe-evase-dall-ordine).
DO $az_ann$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(
      NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ddt');
END $az_ann$;

SELECT plan(13);

-- Dal 2026-09-28 conferma e annullo del reso sono verbi che applicano
-- l'azione conferma_reso (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f):
-- qui sono i passi dei test 7 e 8, e l'operatore di fixture non ha azioni: si
-- concede qui.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;

-- ============================================================
-- Riferimenti + helper
-- ============================================================
CREATE TEMP TABLE tmp_refs AS
SELECT
  -- ⛔ rev 2026-10-13: il BA del mondo costruito; l'articolo si costruisce
  --   (merce, non gestito: il test non misura il magazzino).
  (SELECT billing_account_id FROM _m)                                    AS billing_account_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-STATO-SORG', false)                AS articolo_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo LIMIT 1)  AS sorgente_ddt_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='RESO_VENDITA' AND s.attivo LIMIT 1) AS sorgente_reso_id;

-- ============================================================
-- FIXTURE
-- ============================================================
-- Le bolle dal builder, una per stato. Il guard del reso pretende la bolla
-- CONSEGNATA; l'annullata parte da EMESSA (la matrice ammette ANNULLATO solo da li').
CREATE TEMP TABLE tmp_cons AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('stato sorgente', 'CONSEGNATO',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO');
CREATE TEMP TABLE tmp_ann AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('stato sorgente', 'EMESSO',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO');
CREATE TEMP TABLE tmp_eme AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('stato sorgente', 'EMESSO',
         p_billing_account_id => (SELECT billing_account_id FROM tmp_refs),
         p_articolo_id => (SELECT articolo_id FROM tmp_refs), p_fatturazione_trigger => 'CONSEGNATO');

-- ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine, D-8): la bolla nasce
--   dall'ordine e ne porta il legame. L'annullo diretto e' rifiutato
--   (E_DOC_ANNULLO_CON_LEGAMI): passa dal verbo, dichiarando i legami letti
--   da vendite.fn_documento_legami, come fa la finestra di conferma
--   (rev 2026-10-11, brief-db-annullo-documento-con-legami D-4).
SELECT vendite.fn_annulla_ddt(a.ddt_id,
         (SELECT count(*)::integer FROM vendite.fn_documento_legami('DDT_VENDITA', a.ddt_id) l))
  FROM tmp_ann a;

-- Reso a credito di 3 in DRAFT sul DDT consegnato (il guard pretende il DDT
-- CONSEGNATO): conferma e annullo sono i passi dei test 7 e 8.
CREATE TEMP TABLE tmp_reso AS
SELECT * FROM dbops.fn_pgtap_crea_reso('stato sorgente', (SELECT ddt_id FROM tmp_cons), 3,
                                       p_stato_codice_interno => 'DRAFT',
                                       p_ddt_riga_id          => (SELECT ddt_riga_id FROM tmp_cons));

-- ============================================================
-- ASSERZIONI
-- ============================================================
-- 1) il ramo DDT arriva nella union
SELECT is(
  (SELECT v.risolto FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_ddt_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT ddt_id FROM tmp_cons)::text),
  true, '1) ramo DDT: il documento proietta in script.vw_stato_sorgente (risolto=true)');

-- 2) LA CHIAVE E' id, NON uid (key_selector='id' per DDT_VENDITA).
--    Se qualcuno "ripulisse" la convenzione passando all'uid, il ramo
--    smetterebbe di agganciare in silenzio: questa asserzione lo impedisce.
SELECT is(
  (SELECT COUNT(*)::int FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_ddt_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT ddt_uid FROM tmp_cons)::text),
  0, '2) la chiave del DDT e'' id::text, NON l''uid (convenzione polimorfa key_selector)');

-- 3-5) esito/terminale derivati da fase + is_abortito
SELECT is(
  (SELECT (v.esito, v.terminale) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_ddt_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT ddt_id FROM tmp_cons)::text),
  ('POSITIVO'::text, true), '3) DDT CONSEGNATO (fase CHIUSO, non abortito) -> POSITIVO / terminale');

SELECT is(
  (SELECT (v.esito, v.terminale) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_ddt_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT ddt_id FROM tmp_ann)::text),
  ('NEGATIVO'::text, true), '4) DDT ANNULLATO (is_abortito) -> NEGATIVO / terminale');

SELECT is(
  (SELECT (v.esito, v.terminale) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_ddt_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT ddt_id FROM tmp_eme)::text),
  (NULL::text, false), '5) DDT EMESSO (fase IN_CORSO) -> esito NULL / non terminale');

-- 6-7) ramo RESO
SELECT is(
  (SELECT (v.esito, v.terminale) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_reso_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT reso_id FROM tmp_reso)::text),
  (NULL::text, false), '6) ramo RESO: reso DRAFT (fase APERTO) -> esito NULL / non terminale');

-- 7) conferma -> CONFERMATO ha fase CHIUSO (correzione catalogo 2026-07-18):
--    il reso confermato E' concluso -> POSITIVO / terminale
SELECT vendite.fn_conferma_reso((SELECT reso_id FROM tmp_reso));
SELECT is(
  (SELECT (v.esito, v.terminale) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_reso_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT reso_id FROM tmp_reso)::text),
  ('POSITIVO'::text, true), '7) reso CONFERMATO (fase CHIUSO da correzione catalogo) -> POSITIVO / terminale');

-- 8) annullo (storno guardato, ammesso da CONFERMATO senza ri-consegne)
SELECT vendite.fn_annulla_reso((SELECT reso_id FROM tmp_reso));
SELECT is(
  (SELECT (v.esito, v.terminale) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_reso_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT reso_id FROM tmp_reso)::text),
  ('NEGATIVO'::text, true), '8) reso ANNULLATO (is_abortito) -> NEGATIVO / terminale');

-- 9) unicita' della chiave sui due rami nuovi
SELECT is(
  (SELECT COUNT(*)::int FROM (
      SELECT v.sorgente_tipo_id, v.sorgente_uid
        FROM script.vw_stato_sorgente v
       WHERE v.sorgente_tipo_id IN ((SELECT sorgente_ddt_id FROM tmp_refs),
                                    (SELECT sorgente_reso_id FROM tmp_refs))
       GROUP BY 1,2 HAVING COUNT(*) > 1) dup),
  0, '9) al piu'' una riga per (sorgente_tipo_id, sorgente_uid) sui rami DDT e RESO');


-- 10-12) La chiave si cerca nel suo TIPO (rev 2026-10-05, 20261005-23).
--   fn_stato_sorgente cerca sorgente_chiave_id (bigint), non il testo: e'
--   l'unico confronto che sotto RLS arriva all'indice. Il ramo a chiave id si
--   prova su un documento COSTRUITO qui, non su quelli che il DB contiene.
--   rev 2026-11-08 (giro P.1 di brief-db-sorgente-documento-e-riga): la firma
--   prende le colonne del modello (tipo, sorgente_id, sorgente_uid). Il vecchio
--   11 (id con lo zero davanti) non ha piu' oggetto, un bigint non ha forme
--   testuali: al suo posto la regola d'incontro.
SELECT results_eq(
  format($$SELECT risolto, esito, terminale FROM pratiche.fn_stato_sorgente(%s, %s, NULL)$$,
         (SELECT sorgente_ddt_id FROM tmp_refs), (SELECT ddt_id FROM tmp_cons)::bigint),
  $$VALUES (true, 'POSITIVO'::text, true)$$,
  '10) fn_stato_sorgente trova il DDT per chiave id (ramo bigint)');

SELECT results_eq(
  format($$SELECT a.risolto, b.risolto, b.stato_codice_interno
             FROM pratiche.fn_stato_sorgente(%1$s, %2$s, %3$L) a,
                  pratiche.fn_stato_sorgente(%1$s, NULL, %3$L) b$$,
         (SELECT sorgente_ddt_id FROM tmp_refs), (SELECT ddt_id FROM tmp_cons)::bigint,
         (SELECT ddt_uid FROM tmp_cons)),
  $$VALUES (true, false, 'UNKNOWN'::text)$$,
  '11) con id e uid del DDT: trovato; col solo uid, che non e'' la chiave del DDT: UNKNOWN');

SELECT is(
  (SELECT (v.sorgente_chiave_id, v.sorgente_chiave_uuid IS NULL) FROM script.vw_stato_sorgente v
    WHERE v.sorgente_tipo_id=(SELECT sorgente_ddt_id FROM tmp_refs)
      AND v.sorgente_uid=(SELECT ddt_id FROM tmp_cons)::text),
  ((SELECT ddt_id FROM tmp_cons)::bigint, true),
  '12) chiave nativa del ramo DDT coerente col testo: sorgente_chiave_id = id, uuid NULL');


-- 13) La vista per pratica risolve un collegamento a chiave id (20261005-24).
--   I test d'ancora di test-proiezione-stato-sorgente collegano solo preventivi
--   (chiave uid) e commesse (senza ramo): il ramo bigint della LATERAL di
--   vw_pratica_doc_sorgente si prova qui, su un DDT costruito da questo file.
--   Pratica minima come nei test d'ancora; emittente DERIVATO da chi agisce.
-- ⚠️ Tipo e pratica in DUE istruzioni: alla nascita del tipo il trigger di
--   bootstrap ne pubblica la definizione di workflow a fine istruzione, e una
--   pratica inserita nella stessa (CTE di scrittura) non la trova.
CREATE TEMP TABLE tmp_prat_ddt_tp AS
WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_PSS_DDT', 'TEST_PSS_DDT', 'Tipo test proiezione DDT', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
) SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_prat_ddt AS
WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, soggetto_id, stato_id, priorita_id)
  VALUES (script.fn_pgtap_emittente_operatore(), (SELECT tp_id FROM tmp_prat_ddt_tp),
          -- ⛔ rev 2026-10-13: il soggetto e' il cliente costruito, non il primo del DB.
          (SELECT cliente_soggetto_id FROM _m),
          (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'APERTA'),
          (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE'))
  RETURNING id
) SELECT id AS pratica_id FROM ins;

-- Il DDT ha chiave id: sorgente_id (giro P.1).
INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_id, ruolo_link, flusso_id)
VALUES ((SELECT pratica_id FROM tmp_prat_ddt), (SELECT sorgente_ddt_id FROM tmp_refs),
        (SELECT ddt_id FROM tmp_cons)::bigint, 'ROOT', NULL);

SELECT results_eq(
  $$SELECT risolto, esito, terminale
      FROM script.vw_pratica_doc_sorgente
     WHERE pratica_id = (SELECT pratica_id FROM tmp_prat_ddt)$$,
  $$VALUES (true, 'POSITIVO'::text, true)$$,
  '13) vw_pratica_doc_sorgente risolve il DDT collegato per chiave id (ramo bigint della LATERAL)');

SELECT * FROM finish();
ROLLBACK;
