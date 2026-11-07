-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; resta scritto a mano l'annullo dal verbo (la bolla legata all'ordine non si annulla per UPDATE) e la bolla senza ordine e senza BA del test 17 (e' il caso).
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a, 20261019-40 … -79):
--   il documento passato ai lettori delle testate, ai legami e ai montaggi del
--   lock e' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA,
--   OFFERTA_COMMERCIALE, RESO_VENDITA). Restano corti i prefissi delle chiavi
--   (G-8), l'origine dei legami (V7) e l'ambito degli indirizzi (G-6).
-- Test: script.fn_available_actions_ddt — il push a commessa letto da UNA
--       fonte (vendite.fn_ddt_push_diagnosi): flag, precedenza sul segmento,
--       decomposizione del catch-all DDT_NON_PUSHABILE nelle sue cause.
-- Brief: brief-db-ddt-reason-push-catch-all §3 (changeset 20260719-15/16);
--        rev 2026-09-21 — brief-db-partita-merce-per-documento §10 (D4, forma
--        B2; changeSet 20260921-32/-33/-34).
-- ------------------------------------------------------------
-- Indice test (plan 16):
--   1) ⭐ ELEGGIBILE, costruito: la diagnosi dice motivo NULL, dose 10,
--      segment LIBERA e il BA del cliente costruito
--   2) ...e il lister porta QUELLA riga con quantita 10 (deriva dalla diagnosi)
--   3) ...e la capability dice can_push_commessa = true, reason e key NULL
--   4) DDT_FATTURA_DA_ORDINE: ordine CONFERMATO, DDT CONSEGNATO (il rilievo
--      originale DDT0000326) -> reason FATTURA_DA_ORDINE
--   5) DDT_MERCE_IN_VIAGGIO: ordine SPEDITO, DDT EMESSO (prima del trigger)
--   6) DDT_SOLO_TRASPORTO: causale non fatturabile (CONTO_LAVORO)
--   7) generico ANNULLATO: DDT annullato -> DDT_NON_PUSHABILE, non una frase
--      sullo stato
--   8) PRECEDENZA a due livelli: ANNULLATO (rank 1, documento) + ordine
--      CONFERMATO (rank 6, riga) -> vince il documento (generico)
--   9) ⭐ DDT_GIA_INVIATO: riga eleggibile con un'attivita' NON_EMESSA sul suo
--      segmento (ALLOCATA) -> can_push false, reason GIA_INVIATO; il lister
--      non la porta piu'
--  10) ⭐ DDT_GIA_FATTURATO: attivita' EMESSA sul segmento -> GIA_FATTURATO
--  11) ⭐ PRECEDENZA del segmento sul documento: DDT ANNULLATO con una riga
--      ALLOCATA dice GIA_INVIATO, non il generico — e' l'ordine di prima
--      (i due EXISTS venivano PRIMA della diagnosi) e B2 lo conserva
--  12) NAMESPACE: ogni reason_key emessa sta sotto vendite.ddt.push_commessa_reason.*
--  13) COERENZA rank <-> motivo su TUTTE le righe: nessun rank senza etichetta
--  14) COERENZA delle colonne nuove: motivo NULL => (segment LIBERA e dose > 0
--      e BA presente); ROUTED / SENZA_BA / CONTATORE coerenti con segment, BA, dose
--  15) ⭐ pin di forma di D4: il lister nomina la diagnosi e NON
--      fn_partite_merce ne' fn_get_stato_push_segment (nessun predicato suo);
--      la capability NON nomina il lister ne' il classificatore (una lettura);
--      la diagnosi e' BEGIN ATOMIC e non SECURITY DEFINER
--  17) ⭐ DDT_SENZA_BA COSTRUITO: un DDT senza ordine dietro e senza billing
--      account (la colonna e' NULLABLE) -> rank 3, motivo DDT_SENZA_BA,
--      billing_account_id NULL, capability spenta. Fino al 2026-09-22 il
--      ramo non era esercitato da nessuna riga viva (54 su 54 hanno un BA
--      visibile): la clausola SENZA_BA del test 14 era vera A VUOTO, e il
--      giro 7 riscrive proprio la lettura dei BA
--  18) ⭐ pin di forma di D-2 (brief-db-plancache, 20261012-03): nella diagnosi
--      la CTE `src` e' MATERIALIZED. Senza, nel ramo «tutti» si ricalcolava per
--      ogni riga esterna (righe² giri del LATERAL sotto RLS, ~1,05 s su 1,18
--      con 58 righe): i risultati restano giusti e solo il tempo se ne accorge,
--      quindi un CREATE OR REPLACE che perdesse la parola passerebbe ogni altro
--      test. Prima di 16 perche' 16 cambia il contesto.
--  16) scope: chi non vede il DDT ha zero righe di diagnosi e capability NULL
--      (⚠️ rosso da owner, che salta la RLS: gira come app; ULTIMO, cambia
--      il contesto)
--
-- Scopo:
--  - fino al 2026-09-21 il test 1 confrontava lister e diagnosi (EXCEPT nei
--    due versi): due copie della stessa regola tenute uguali da un pgTAP —
--    verde per sottrazione su un database da zero. Con la forma B2 il lister
--    DERIVA dalla diagnosi e quel confronto e' la stessa query: al suo posto
--    ci sono casi COSTRUITI (1-3, 9-11) e un pin di FORMA (15).
--  - ⭐ il mondo (cliente, articolo) e' COSTRUITO dai builder di dbops, non
--    pescato: la fixture «un BA a caso» moriva sullo scratch zeroerp_ci
--    (baseline-rossi-ci, ERRORE_FIXTURE — la malattia D7).
--  - ⛔ un predicato di eleggibilita' nuovo si aggiunge alla diagnosi come
--    rank e qui come caso costruito: nel lister non c'e' piu' un posto.
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

-- L'annullo di una bolla emessa passa dal verbo di stato, che chiede l'azione
-- emetti_ddt (rev 2026-10-11, D-8 di brief-db-ddt-righe-evase-dall-ordine).
DO $az_ann$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(
      NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ddt');
END $az_ann$;

SELECT plan(18);

-- ⛔ Niente `SET LOCAL app.current_user_id = '1'` dopo la riga di contesto:
--    l'operatore lo sceglie (o lo COSTRUISCE, su un database vuoto)
--    fn_pgtap_set_contesto_operatore, e l'utente 1 in CI non esiste (D7).

-- ============================================================
-- Il mondo si COSTRUISCE, non si cerca (guida pgTAP). Ordine obbligato:
-- PRIMA il contesto (la riga in testa), POI il cliente — il legame BA ->
-- emittente lo scrive il trigger z90 verso l'emittente di chi agisce, lo
-- stesso che risponde fn_pgtap_emittente_operatore. L'articolo NON gestito
-- a magazzino: il ciclo DDT non tocca il ledger.
-- ============================================================
CREATE TEMP TABLE tmp_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_reason_catchall');

CREATE TEMP TABLE tmp_refs AS
SELECT
  c.billing_account_id,
  c.utility_id,
  c.istanza_utility_id,
  c.soggetto_ruolo_id,
  script.fn_pgtap_emittente_operatore()                                                                AS emittente_fiscale_id,
  dbops.fn_pgtap_crea_articolo('PGT-RCA-ART', false)                                                   AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)              AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                             AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)                         AS iva_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA' AND s.attivo ORDER BY s.id LIMIT 1)           AS sorgente_root_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                           AS tipo_doc_fiscale_id,
  (SELECT c2.id FROM config.causali_trasporto c2 WHERE c2.codice='VENDITA'     ORDER BY c2.id LIMIT 1)                AS causale_vendita_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')                                                   AS tipo_ind_con_id
FROM tmp_cli c;

-- Commessa + ROOT: servono alle attivita' fatturabili dei casi 9-11.
CREATE TEMP TABLE tmp_com AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs),
  p_utility_id             => (SELECT utility_id FROM tmp_refs),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-07-01',
  p_competenza_al          => DATE '2026-07-31',
  p_meta                   => jsonb_build_object('test_scope','pgtap_reason_catchall'),
  p_force_new              => true) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_com),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs),
  p_sorgente_uid     => (SELECT commessa_id FROM tmp_com)::text,
  p_sorgente_riga    => NULL,
  p_meta             => '{}'::jsonb);

-- ============================================================
-- Helper
-- ============================================================

-- La bolla dal builder: ordine del cliente costruito (trigger p_trigger, una
-- riga di 10 a 25 dell'articolo del file), causale p_causale, stato p_stato.
-- Ritorna il DDT; la sua riga si legge con rca_riga().
-- ⭐ ANNULLATO resta qui: la bolla nasce dall'ordine e ne porta il legame,
--   l'annullo diretto e' rifiutato (E_DOC_ANNULLO_CON_LEGAMI). Passa dal
--   verbo, dichiarando i legami letti da vendite.fn_documento_legami, come fa
--   la finestra di conferma (brief-db-annullo-documento-con-legami D-4).
CREATE OR REPLACE FUNCTION pg_temp.mk_caso(p_trigger varchar, p_stato varchar, p_causale varchar)
RETURNS bigint AS $$
DECLARE v_ddt bigint;
BEGIN
  SELECT b.ddt_id INTO v_ddt
    FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgtap_reason_catchall',
           CASE WHEN p_stato = 'ANNULLATO' THEN 'EMESSO' ELSE p_stato END,
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs),
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs),
           p_fatturazione_trigger => p_trigger,
           p_causale_codice       => p_causale) b;
  IF p_stato = 'ANNULLATO' THEN
    PERFORM vendite.fn_annulla_ddt(v_ddt,
        (SELECT count(*)::integer FROM vendite.fn_documento_legami('DDT_VENDITA', v_ddt) l));
  END IF;
  RETURN v_ddt;
END $$ LANGUAGE plpgsql;

-- La riga (unica) di un DDT costruito qui.
CREATE OR REPLACE FUNCTION pg_temp.rca_riga(p_ddt bigint) RETURNS bigint AS $$
  SELECT dr.id FROM vendite.ddt_righe dr WHERE dr.ddt_id = p_ddt ORDER BY dr.id LIMIT 1;
$$ LANGUAGE sql;

-- La segment_key di quella riga, come la compone il lister.
CREATE OR REPLACE FUNCTION pg_temp.rca_segment(p_ddt bigint) RETURNS varchar AS $$
  SELECT script.fn_segment_key('DDT_VENDITA', d.uid::text, pg_temp.rca_riga(p_ddt))
    FROM vendite.ddt d WHERE d.id = p_ddt;
$$ LANGUAGE sql;

-- Un'attivita' NORMALE, APPROVATA e NON_EMESSA sul segmento: la riga diventa
-- ALLOCATA agli occhi di fn_get_stato_push_segment. Chi la vuole EMESSA
-- chiama poi rca_emit().
CREATE OR REPLACE FUNCTION pg_temp.mk_af(p_segment varchar, p_qta numeric)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs;
  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
    p_sorgente_uid => ((SELECT commessa_id FROM tmp_com))::text,
    p_segment_key => p_segment, p_articolo_id => r.articolo_id,
    p_istanza_utility_id => r.istanza_utility_id, p_data_attivita => DATE '2026-07-15',
    p_uom_id => r.uom_id, p_quantita => p_qta,
    p_competenza_mese => DATE '2026-07-01',
    p_competenza_dal => DATE '2026-07-01', p_competenza_al => DATE '2026-07-31',
    p_prezzo_snapshot => 25, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL,
    p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id, p_valuta_id => r.valuta_id,
    p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => 'NORMALE');
END $$ LANGUAGE plpgsql;

-- Emette TUTTE le attivita' approvate e non emesse della commessa: va
-- chiamata PRIMA di costruire le ALLOCATA (9 e 11), o le emetterebbe.
CREATE OR REPLACE FUNCTION pg_temp.rca_emit() RETURNS void AS $$
  SELECT vendite.fn_emit_attivita_fatturabili_da_commessa((SELECT commessa_id FROM tmp_com), true, false);
$$ LANGUAGE sql;

-- I tre campi del push di un blob, in una stringa confrontabile. Prende il
-- BLOB e non il DDT: i test 3-12 lo leggono dalla fotografia _blob, il 17
-- (che viene dopo scritture nuove) dalla chiamata viva.
CREATE OR REPLACE FUNCTION pg_temp.rca_push(b jsonb) RETURNS text AS $$
  SELECT (b->>'can_push_commessa') || '|' || COALESCE(b->>'can_push_commessa_reason', '-')
         || '|' || COALESCE(b->>'can_push_commessa_reason_key', '-');
$$ LANGUAGE sql;

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE f AS SELECT
  pg_temp.mk_caso('CONFERMATO', 'CONSEGNATO', 'VENDITA')      AS d_fattura_ordine,
  pg_temp.mk_caso('SPEDITO',    'EMESSO',     'VENDITA')      AS d_in_viaggio,
  pg_temp.mk_caso('SPEDITO',    'SPEDITO',    'CONTO_LAVORO') AS d_solo_trasporto,
  pg_temp.mk_caso('SPEDITO',    'ANNULLATO',  'VENDITA')      AS d_annullato,
  pg_temp.mk_caso('CONFERMATO', 'ANNULLATO',  'VENDITA')      AS d_prec,
  -- ⭐ i casi nuovi del 21-09: trigger CONSEGNATO + DDT CONSEGNATO + VENDITA
  --    = eleggibile (e' il caso A di test-fn-list-ddt-da-pushare-contatore-v1)
  pg_temp.mk_caso('CONSEGNATO', 'CONSEGNATO', 'VENDITA')      AS d_ok,
  pg_temp.mk_caso('CONSEGNATO', 'CONSEGNATO', 'VENDITA')      AS d_alloc,
  pg_temp.mk_caso('CONSEGNATO', 'CONSEGNATO', 'VENDITA')      AS d_emessa,
  pg_temp.mk_caso('SPEDITO',    'ANNULLATO',  'VENDITA')      AS d_prec_alloc;

-- EMESSA prima, poi le ALLOCATA (rca_emit emette tutto cio' che trova).
SELECT pg_temp.mk_af(pg_temp.rca_segment(d_emessa), 10) FROM f;
SELECT pg_temp.rca_emit();
SELECT pg_temp.mk_af(pg_temp.rca_segment(d_alloc), 10) FROM f;
SELECT pg_temp.mk_af(pg_temp.rca_segment(d_prec_alloc), 10) FROM f;

-- ⭐ UNA FOTOGRAFIA PER MOMENTO (2026-10-10). Da qui al test 15 il file non
--   crea e non scrive niente: e' un momento solo. Fino a oggi i test 3-12
--   chiedevano la capability 17 volte per 9 DDT (il 12 rifaceva le otto dei
--   test 4-11), e i test 13 e 14 calcolavano due volte la diagnosi di TUTTE le
--   righe — ~1,2 s l'una come app su dbdev, misurato il 2026-10-10. Le copie
--   contengono esattamente cio' che la chiamata viva risponde in questo momento,
--   con il contesto operatore gia' preso: cambia quante volte si paga, non cosa
--   si vede.
--   ⚠️ Restano VIVE le letture che vengono dopo una scrittura o un cambio di
--   contesto: il 17 (DDT costruito dopo) e il 16 (scope).
CREATE TEMP TABLE _blob AS
SELECT s.ddt_id, script.fn_available_actions_ddt(s.ddt_id) AS b
  FROM f CROSS JOIN LATERAL unnest(ARRAY[d_fattura_ordine, d_in_viaggio, d_solo_trasporto,
                                         d_annullato, d_prec, d_ok, d_alloc, d_emessa,
                                         d_prec_alloc]) AS s(ddt_id);

-- Il blob di un DDT costruito qui, dalla fotografia. ⚠️ Dopo la CREATE TABLE:
--   il corpo di una funzione SQL si valida alla creazione.
CREATE OR REPLACE FUNCTION pg_temp.rca_blob(p_ddt bigint) RETURNS jsonb AS $$
  SELECT b FROM _blob WHERE ddt_id = p_ddt;
$$ LANGUAGE sql;

CREATE TEMP TABLE _diagnosi AS
SELECT * FROM vendite.fn_ddt_push_diagnosi();

-- ============================================================
-- 1-3) ⭐ L'ELEGGIBILE, costruito: la fonte, chi ne deriva, chi la legge.
--      Prima del 21-09 qui c'era un EXCEPT lister/diagnosi sulle righe vive:
--      verde perche' nessuna riga attraversava la divergenza, non perche' la
--      divergenza non ci fosse.
-- ============================================================
SELECT is(
  (SELECT COALESCE(g.motivo, 'NULL') || '|' || (g.quantita_push = 10)::text || '|' || g.segment
          || '|' || (g.billing_account_id = (SELECT billing_account_id FROM tmp_refs))::text
     FROM vendite.fn_ddt_push_diagnosi((SELECT d_ok FROM f)) g
    WHERE g.riga_id = pg_temp.rca_riga((SELECT d_ok FROM f))),
  'NULL|true|LIBERA|true',
  '1) eleggibile costruito: la diagnosi dice motivo NULL, dose 10, segment LIBERA, il BA del cliente');

SELECT is(
  (SELECT quantita FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL, (SELECT d_ok FROM f))
    WHERE riga_id = pg_temp.rca_riga((SELECT d_ok FROM f))),
  10::numeric,
  '2) ...e il lister, che ne deriva, porta quella riga con quantita 10');

SELECT is(
  (SELECT pg_temp.rca_push(pg_temp.rca_blob(d_ok)) FROM f),
  'true|-|-',
  '3) ...e la capability dice can_push_commessa = true, senza reason ne'' key');

-- ============================================================
-- 4-8) Le cause del catch-all (invariate dal 2026-07-19)
-- ============================================================
SELECT is(
  (SELECT pg_temp.rca_blob(d_fattura_ordine)->>'can_push_commessa_reason' FROM f),
  'DDT_FATTURA_DA_ORDINE',
  '4) ordine CONFERMATO + DDT CONSEGNATO -> DDT_FATTURA_DA_ORDINE (era il falso «spedito o consegnato»)');

SELECT is(
  (SELECT pg_temp.rca_blob(d_in_viaggio)->>'can_push_commessa_reason' FROM f),
  'DDT_MERCE_IN_VIAGGIO',
  '5) ordine SPEDITO + DDT EMESSO (pre-trigger) -> DDT_MERCE_IN_VIAGGIO');

SELECT is(
  (SELECT pg_temp.rca_blob(d_solo_trasporto)->>'can_push_commessa_reason' FROM f),
  'DDT_SOLO_TRASPORTO',
  '6) causale non fatturabile (CONTO_LAVORO) -> DDT_SOLO_TRASPORTO');

SELECT is(
  (SELECT pg_temp.rca_blob(d_annullato)->>'can_push_commessa_reason' FROM f),
  'DDT_NON_PUSHABILE',
  '7) DDT ANNULLATO -> generico DDT_NON_PUSHABILE (non la frase sullo stato)');

SELECT is(
  (SELECT pg_temp.rca_blob(d_prec)->>'can_push_commessa_reason' FROM f),
  'DDT_NON_PUSHABILE',
  '8) ANNULLATO + ordine CONFERMATO: vince il documento (generico), non FATTURA_DA_ORDINE');

-- ============================================================
-- 9-11) ⭐ Il segmento: GIA_INVIATO / GIA_FATTURATO e la loro precedenza.
--       Prima del 21-09 erano due EXISTS della capability su ddt_righe, mai
--       costruiti da un pgTAP; ora si leggono dalla colonna `segment` della
--       diagnosi, e la precedenza (PRIMA del motivo) deve restare quella.
-- ============================================================
SELECT is(
  (SELECT pg_temp.rca_push(pg_temp.rca_blob(d_alloc)) FROM f)
    || '#' || (SELECT count(*) FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL, (SELECT d_alloc FROM f)))::text,
  'false|DDT_GIA_INVIATO|vendite.ddt.push_commessa_reason.gia_inviato#0',
  '9) riga instradata e non emessa (ALLOCATA): GIA_INVIATO, e il lister non la porta');

SELECT is(
  (SELECT pg_temp.rca_push(pg_temp.rca_blob(d_emessa)) FROM f),
  'false|DDT_GIA_FATTURATO|vendite.ddt.push_commessa_reason.gia_fatturato',
  '10) riga fatturata (EMESSA): GIA_FATTURATO');

SELECT is(
  (SELECT pg_temp.rca_push(pg_temp.rca_blob(d_prec_alloc)) FROM f),
  'false|DDT_GIA_INVIATO|vendite.ddt.push_commessa_reason.gia_inviato',
  '11) DDT ANNULLATO con una riga ALLOCATA: il segmento vince sul documento (GIA_INVIATO, come prima)');

-- ============================================================
-- 12) NAMESPACE i18n su tutte le reason_key emesse dalle fixture
-- ============================================================
SELECT ok(
  (SELECT bool_and(k LIKE 'vendite.ddt.push_commessa_reason.%') AND count(*) = 8
     FROM (SELECT unnest(ARRAY[d_fattura_ordine, d_in_viaggio, d_solo_trasporto, d_annullato,
                              d_prec, d_alloc, d_emessa, d_prec_alloc]) AS d FROM f) s
     CROSS JOIN LATERAL (
       SELECT pg_temp.rca_blob(s.d)->>'can_push_commessa_reason_key' AS k) q
    WHERE k IS NOT NULL),
  '12) le otto reason_key stanno tutte sotto vendite.ddt.push_commessa_reason.*');

-- ============================================================
-- 13-14) COERENZA interna della diagnosi, su TUTTE le righe (vive + costruite)
-- ============================================================
--    ⚠️ Un `CASE` che dimentica un ramo non fallisce: restituisce NULL — e per
--    questa funzione un motivo NULL significa «eleggibile», il contrario del vero.
SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM _diagnosi g
     WHERE (g.motivo_rank IS NULL) <> (g.motivo IS NULL)
  ),
  '13) rank e motivo sono valorizzati insieme: nessun rank senza etichetta');

--    Le colonne nuove sono i valori che le rank 3, 4 e 11 hanno giudicato: se
--    divergessero, lister e capability leggerebbero una cosa e la diagnosi
--    ne avrebbe deciso un'altra.
--    (Un solo verso: una riga LIBERA con dose e BA puo' essere esclusa da
--    un'altra rank — annullato, in viaggio, fattura da ordine.)
SELECT ok(
  NOT EXISTS (
    SELECT 1 FROM _diagnosi g
     WHERE (g.motivo IS NULL
            AND NOT (g.segment = 'LIBERA' AND g.quantita_push > 0 AND g.billing_account_id IS NOT NULL))
        OR (g.motivo = 'DDT_ROUTED'    AND g.segment = 'LIBERA')
        OR (g.motivo = 'DDT_SENZA_BA'  AND g.billing_account_id IS NOT NULL)
        OR (g.motivo = 'DDT_CONTATORE' AND g.quantita_push > 0)
  ),
  '14) motivo NULL => segment LIBERA, dose > 0, BA presente; ROUTED / SENZA_BA / CONTATORE coerenti con segment, BA e dose');

-- ============================================================
-- 15) ⭐ Pin di FORMA di D4 (come il test 2 della chiusura pinna D1): si legge
--     il corpo SENZA i commenti — la storia nelle intestazioni nomina tutto.
-- ============================================================
SELECT ok(
  (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'fn_ddt_push_diagnosi'
      AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') !~ 'fn_partite_merce'
      AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') !~ 'fn_get_stato_push_segment'
     FROM pg_proc p WHERE p.oid = 'vendite.fn_list_ddt_da_pushare'::regproc)
  AND
  (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'fn_ddt_push_diagnosi'
      AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') !~ 'fn_list_ddt_da_pushare'
      AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') !~ 'fn_get_stato_push_segment'
     FROM pg_proc p WHERE p.oid = 'script.fn_available_actions_ddt'::regproc)
  AND
  (SELECT p.prosqlbody IS NOT NULL AND NOT p.prosecdef
     FROM pg_proc p WHERE p.oid = 'vendite.fn_ddt_push_diagnosi'::regproc),
  '15) forma D4: il lister deriva dalla diagnosi senza predicati suoi; la capability legge solo la diagnosi; la diagnosi e'' BEGIN ATOMIC e non DEFINER');

-- ============================================================
-- 17) ⭐ Il ramo della rank 3, COSTRUITO.
--     `vendite.ddt.billing_account_id` e' NULLABLE e una riga senza
--     fulfillment non ha un ordine da cui ereditarlo: COALESCE(NULL, NULL)
--     = NULL, ed e' la rank 3. Le rank che vengono prima non scattano —
--     il documento non e' abortito ne' RESO (1) e la causale e' VENDITA,
--     fatturabile (2).
--     ⚠️ Perche' COSTRUITO e non letto: su dbdev nessuna delle 54 righe
--     attive cade in DDT_SENZA_BA, quindi la clausola `motivo =
--     'DDT_SENZA_BA' AND billing_account_id IS NOT NULL` del test 14 e'
--     vera perche' non ha soggetti, non perche' la regola tenga.
--     ⛔ L'altra meta' della rank 3 — «il BA esiste ma chi legge non lo
--     vede» — NON si costruisce da un documento, ed e' una proprieta' del
--     modello, non una lacuna del test: `trgfn_<doc>_guard_emittente_ba`
--     vieta a un documento di portare il BA di un'altra azienda, quindi
--     un DDT visibile con un BA invisibile non e' uno stato raggiungibile.
--     Resta una cintura fail-closed: la diagnosi legge i billing account
--     come INVOKER (test 15 pinna che non e' DEFINER), quindi un BA fuori
--     scope non entra e la riga esce SENZA_BA.
-- ============================================================
CREATE TEMP TABLE tmp_noba AS
WITH ins AS (
  INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data,
      billing_account_id, valuta_id, causale_trasporto_id, emittente_fiscale_id,
      storicizza, meta)
  SELECT r.soggetto_ruolo_id,
         (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='DRAFT' LIMIT 1),
         DATE '2026-09-01', NULL, r.valuta_id, r.causale_vendita_id, r.emittente_fiscale_id,
         false, jsonb_build_object('test_scope','pgtap_reason_catchall')
    FROM tmp_refs r
  RETURNING id)
SELECT id AS ddt_id FROM ins;

INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
SELECT n.ddt_id, 1, r.articolo_id, 'Riga senza BA', 5, 5, 20, r.iva_id, true, false,
       jsonb_build_object('test_scope','pgtap_reason_catchall')
  FROM tmp_noba n, tmp_refs r;

INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
SELECT n.ddt_id, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb
  FROM tmp_noba n, tmp_refs r
ON CONFLICT DO NOTHING;

-- ⭐ rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-2): la bolla RESTA IN BOZZA.
--   Una VENDITA senza billing account non si emette piu' (motivo
--   E_DDT_CLIENTE_OBBLIGATORIO di script.fn_check_ddt_emittibile): lo stato che
--   questo caso costruiva — emessa senza BA — il modello non lo ammette. Il
--   ramo della rank 3 resta raggiungibile, e in bozza: la causale e' VENDITA
--   (la rank 2 non scatta) e il BA e' NULL, e la rank 3 precede la 5
--   (merce in viaggio) che una bozza altrimenti darebbe.

-- ⚠️ Il seme si passa come VALORE (sottoquery), non come colonna laterale
--    (`FROM tmp_noba n, fn_ddt_push_diagnosi(n.ddt_id)`): in forma laterale la
--    diagnosi viene incorporata nella query esterna e fn_partite_merce paga
--    ~4 s fissi come app, contro ~30 ms col valore (profilo del 2026-10-05).
--    La forma laterale non la usa nessun chiamante: lister e capability
--    passano un parametro.
SELECT results_eq(
  $q$SELECT g.motivo_rank, g.motivo, g.billing_account_id,
            pg_temp.rca_push(script.fn_available_actions_ddt(n.ddt_id))
       FROM tmp_noba n
       CROSS JOIN vendite.fn_ddt_push_diagnosi((SELECT ddt_id FROM tmp_noba)) g$q$,
  $q$VALUES (3, 'DDT_SENZA_BA', NULL::bigint,
             'false|DDT_NON_PUSHABILE|vendite.ddt.push_commessa_reason.non_pushabile')$q$,
  '17) DDT senza ordine e senza billing account: rank 3 DDT_SENZA_BA, BA NULL, capability spenta');

-- ============================================================
-- 18) Pin di forma di D-2: la CTE `src` della diagnosi e' MATERIALIZED. Il corpo
--     e' BEGIN ATOMIC (prosrc vuoto): si legge da pg_get_function_sqlbody, che lo
--     deparsa senza commenti — una menzione nella prosa non conta.
SELECT ok(
  (SELECT pg_get_function_sqlbody(p.oid) ~ '\msrc AS MATERIALIZED\M'
     FROM pg_proc p
    WHERE p.oid = 'vendite.fn_ddt_push_diagnosi(bigint)'::regprocedure),
  '18) forma D-2: nella diagnosi la CTE src e'' MATERIALIZED (senza, il ramo «tutti» la ricalcola per ogni riga)');

-- 16) Scope: chi non vede il documento non vede niente.
-- ⚠️ Il cancello e' `app.ruolo_applicativo`: con la veste OPERATORE e un
--    utente senza whitelist la RLS non fa vedere il DDT; la diagnosi
--    (INVOKER) risponde ZERO righe e la capability NULL (documento non
--    trovato), non un blob con dei «no». Ultimo test: cambia il contesto.
-- ============================================================
SELECT set_config('app.current_user_id', '999999999', true);

SELECT is(
  (SELECT count(*) FROM vendite.fn_ddt_push_diagnosi((SELECT d_ok FROM f)))::text
    || '|' || COALESCE((SELECT script.fn_available_actions_ddt(d_ok)::text FROM f), 'NULL'),
  '0|NULL',
  '16) scope che non vede il DDT: zero righe di diagnosi e capability NULL');

SELECT * FROM finish();
ROLLBACK;
