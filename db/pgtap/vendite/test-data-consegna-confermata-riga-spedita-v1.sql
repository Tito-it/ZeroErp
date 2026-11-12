-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): l'ordine con le due righe (10 e 5, data di consegna confermata) dal builder dbops.fn_pgtap_crea_ordine_con_righe (p_righe, p_data_ordine, lo stato chiesto); niente resta a mano nella strada dell'ordine.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine (p_ordine_id, p_righe), l'emissione da dbops.fn_pgtap_porta_a_stato; restano scritti a mano gli ordini (due righe con la data di consegna confermata, che e' il caso) e l'annullo dal verbo (test 15).
-- pgTAP test per Zero ERP
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a, 20261019-40 … -79):
--   il documento passato ai lettori delle testate, ai legami e ai montaggi del
--   lock e' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA,
--   OFFERTA_COMMERCIALE, RESO_VENDITA). Restano corti i prefissi delle chiavi
--   (G-8), l'origine dei legami (V7) e l'ambito degli indirizzi (G-6).
-- Test: la data di consegna confermata di una riga d'ordine gia' spedita e' ferma
--   vendite.fn_ordine_riga_spedita, script.fn_check_ordine_riga_data_consegna_confermata,
--   vendite.trgfn_ordini_righe_guard_data_consegna_spedita, la colonna
--   data_consegna_confermata_blocco di vendite.vw_ordini_righe_dettaglio.
-- ChangeSet: 20261012-04 … -07
-- Brief: brief-db-date-consegna-righe-in-blocco (D-7, P-1, §4)
-- ------------------------------------------------------------
-- Indice test (plan 23):
--   1) gli oggetti esistono, il trigger e' montato, il lettore e' SECURITY DEFINER con search_path
--   2) il codice nuovo e' a catalogo, CONFLITTO_STATO
--   3) ⭐ §12.5.2 sulla forma: il guard CHIAMA la check e non contiene il predicato
--  A — ordine CONFERMATO, riga 1 (10) e riga 2 (5)
--   4) nessun DDT: check [], colonna NULL, la data cambia
--   5) DDT in BOZZA per 4 della riga 1: non conta — check [], la data cambia
--   6) DDT EMESSO (P-1: spedita in parte): il motivo RIGA_SPEDITA, intero
--   7) i valori del motivo sono quanti ne chiede il messaggio
--   8) la vista: riga 1 RIGA_SPEDITA, riga 2 NULL
--   9) D-7: UPDATE della data sulla riga 1 -> E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA
--  10) la frase che l'operatore legge
--  11) lo stesso valore non e' un cambio (WHEN): passa
--  12) la riga 2, non spedita, nello stesso ordine PARZIALMENTE_EVASO: la data cambia
--  13) ⭐ la forma dell'utility in blocco (quella del BE, BF-1): salta la sola riga spedita, scrive la riga 2
--  14) …e la riga 1 tiene la sua data
--  15) annullato il DDT col verbo (legame ritirato): la riga 1 torna libera
--  B — gli stati, che parlano prima
--  16) ordine EVASO (spedito per intero): il primo motivo e' lo STATO, non la riga
--  17) …e l'UPDATE lo rifiuta il lock (_a05_) col suo codice
--  18) ordine in DRAFT: check []
--  C — i bordi
--  19) vendite.fn_ordine_riga_spedita su un id assente: false
--  20) la check su un id assente: NULL
--  21) la check su un id non valido: E_VENDITE_CHIAMATA_NON_VALIDA
--  22) la check e' la stessa per il guard e per la vista: nessun motivo scritto nel guard
--  D — la forma dell'utility (2026-10-12, dopo il lato BE: brief §8 BF-1)
--  23) ⭐ in uno stato che non ammette la data (ANNULLATO) l'utility NON salta le righe in
--      silenzio: la riga va all'UPDATE e la rifiuta il lock col suo codice. Col filtro del
--      §5 (`check = '[]'`) qui si leggerebbe «aggiornate 0»: e' la mutazione che morde.
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO: il cliente dal builder, gli ordini (due righe
--   con la data di consegna confermata, nello stato chiesto) da
--   dbops.fn_pgtap_crea_ordine_con_righe, le bolle da dbops.fn_pgtap_crea_ddt_da_ordine
--   portate avanti per la matrice. L'articolo del builder NON e' gestito a
--   magazzino: l'emissione non chiede prelievi.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga non verrebbero mai esercitati (qui
--   il COMMIT non arriva mai, si chiude in ROLLBACK).
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE +
-- RLS attiva), non come owner.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(23);

-- L'annullo di una bolla emessa e' un'azione (emetti_ddt) del verbo di stato (test 15).
DO $az$ BEGIN
  PERFORM dbops.fn_pgtap_concedi_azione(
      NULLIF(current_setting('app.current_user_id', true), '')::integer, 'emetti_ddt');
END $az$;

-- ============================================================
-- 1-3) Oggetti, codice, forma
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname, p.proname) IN (('vendite', 'fn_ordine_riga_spedita'),
                                     ('script',  'fn_check_ordine_riga_data_consegna_confermata'),
                                     ('vendite', 'trgfn_ordini_righe_guard_data_consegna_spedita')))
  + (SELECT count(*)::int FROM pg_trigger t
      WHERE NOT t.tgisinternal
        AND t.tgrelid = 'vendite.ordini_righe'::regclass
        AND t.tgname = 'trg_ordini_righe_a10_guard_data_consegna_spedita_upd')
  + (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite' AND p.proname = 'fn_ordine_riga_spedita'
        AND p.prosecdef
        AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search_path=%')),
  5,
  '1) le tre funzioni esistono, il trigger e'' montato, il lettore e'' SECURITY DEFINER con search_path');

SELECT is(
  (SELECT c.codice || '=' || c.classe FROM config.codici_errore c
    WHERE c.codice = 'E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA'),
  'E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA=CONFLITTO_STATO',
  '2) il codice nuovo e'' a catalogo, CONFLITTO_STATO');

-- ⭐ §12.5.2: il guard non riscrive il predicato, CHIAMA la check (il sorgente
--    senza commenti: la prosa che lo spiega nomina il fulfillment apposta).
SELECT ok(
  (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'script\.fn_check_ordine_riga_data_consegna_confermata\s*\('
      AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') ~ 'script\.fn_raise_primo_motivo_se_presente\s*\('
      AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') NOT LIKE '%ordini_righe_fulfillment%'
      AND regexp_replace(p.prosrc, '--[^\n]*', '', 'g') NOT LIKE '%stati_doc_ddt%'
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'trgfn_ordini_righe_guard_data_consegna_spedita'),
  '3) il guard chiama la check e ne solleva il primo motivo: il predicato non sta nel guard');

-- ============================================================
-- Fixture — COSTRUITE coi builder
-- ============================================================
CREATE TEMP TABLE tmp_cli_dc AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_data_cons_spedita');

CREATE TEMP TABLE tmp_fix(chiave text PRIMARY KEY, id bigint);

-- Un ordine con due righe (10 e 5 a 20, data di consegna confermata 2026-11-20)
-- dal builder, nello stato chiesto; qui si annotano gli id per chiave.
CREATE OR REPLACE FUNCTION pg_temp.dc_mk_ordine(p_chiave text, p_stato text)
RETURNS void AS $$
DECLARE v_ord bigint;
BEGIN
  SELECT o.ordine_id INTO v_ord
    FROM dbops.fn_pgtap_crea_ordine_con_righe('pgtap_data_cons_spedita', p_stato,
           (SELECT c.billing_account_id FROM tmp_cli_dc c),
           p_data_ordine => DATE '2026-10-01',
           p_righe       => jsonb_build_array(
               jsonb_build_object('quantita', 10, 'prezzo', 20, 'data_consegna_confermata', '2026-11-20'),
               jsonb_build_object('quantita', 5,  'prezzo', 20, 'data_consegna_confermata', '2026-11-20'))) o;
  INSERT INTO tmp_fix
  SELECT p_chiave || '_ord', v_ord
  UNION ALL
  SELECT p_chiave || '_r' || r.riga_nr, r.id
    FROM vendite.ordini_righe r
   WHERE r.ordine_id = v_ord;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.dc_fix(p_chiave text) RETURNS bigint
  AS $$ SELECT id FROM tmp_fix WHERE chiave = p_chiave $$ LANGUAGE sql;

-- La frase del rifiuto, per il test della frase.
CREATE OR REPLACE FUNCTION pg_temp.dc_frase(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
BEGIN
    EXECUTE p_sql;
    RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
    RETURN SQLERRM;
END
$f$;

CREATE OR REPLACE FUNCTION pg_temp.dc_set_data(p_riga bigint, p_data date) RETURNS text
  AS $$ SELECT COALESCE(dbops.fn_pgtap_codice_errore(format(
           'UPDATE vendite.ordini_righe SET data_consegna_confermata = %L WHERE id = %s', p_data, p_riga)), 'PASSA') $$
  LANGUAGE sql;

-- ⭐ L'utility «Aggiorna date di consegna» nella forma del BE
--   (RigheDocumentoRepositoryMixin.scrivi_data_consegna, brief §8 BF-1): salta
--   le sole righe col motivo RIGA_SPEDITA; un motivo di STATO non fa saltare
--   niente, la riga va all'UPDATE e decide il lock. Esito «aggiornate N |
--   saltate M», o il codice del rifiuto.
CREATE OR REPLACE FUNCTION pg_temp.dc_utility(p_ordine bigint, p_data date) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_agg bigint; v_salt bigint; v_s text; v_c text;
BEGIN
    WITH candidate AS (
        SELECT r.id,
               COALESCE(script.fn_check_ordine_riga_data_consegna_confermata(r.id)
                        @> '[{"reason":"RIGA_SPEDITA"}]'::jsonb, false) AS saltata
          FROM vendite.ordini_righe r
         WHERE r.ordine_id = p_ordine AND r.attivo IS TRUE
    ), scritte AS (
        UPDATE vendite.ordini_righe t
           SET data_consegna_confermata = p_data
          FROM candidate c
         WHERE t.id = c.id
           AND NOT c.saltata
        RETURNING t.id
    )
    SELECT (SELECT count(*) FROM scritte), (SELECT count(*) FROM candidate WHERE saltata)
      INTO v_agg, v_salt;
    RETURN format('aggiornate %s | saltate %s', v_agg, v_salt);
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' AND coalesce(v_c, '') <> '' THEN v_c
                ELSE v_s || coalesce(' ' || nullif(v_c, ''), '') END;
END
$f$;

-- ============================================================
-- A — ordine CONFERMATO, riga 1 (10) e riga 2 (5)
-- ============================================================
SELECT pg_temp.dc_mk_ordine('a', 'CONFERMATO');

SELECT is(
  script.fn_check_ordine_riga_data_consegna_confermata(pg_temp.dc_fix('a_r1'))::text
  || ' | ' || COALESCE((SELECT v.data_consegna_confermata_blocco FROM vendite.vw_ordini_righe_dettaglio v
                         WHERE v.id = pg_temp.dc_fix('a_r1')), 'NULL')
  || ' | ' || pg_temp.dc_set_data(pg_temp.dc_fix('a_r1'), DATE '2026-11-21'),
  '[] | NULL | PASSA',
  '4) nessun DDT: check vuota, colonna NULL, la data cambia');

-- Bolla in bozza per 4 della riga 1: la merce non e' ancora partita.
INSERT INTO tmp_fix
SELECT 'a1_ddt', b.ddt_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgtap_data_cons_spedita', 'DRAFT',
         p_ordine_id => pg_temp.dc_fix('a_ord'),
         p_righe     => jsonb_build_array(jsonb_build_object(
                            'ordine_riga_id', pg_temp.dc_fix('a_r1'), 'qta_da_evadere', 4)),
         p_data      => DATE '2026-10-02') b;

SELECT is(
  script.fn_check_ordine_riga_data_consegna_confermata(pg_temp.dc_fix('a_r1'))::text
  || ' | ' || pg_temp.dc_set_data(pg_temp.dc_fix('a_r1'), DATE '2026-11-22'),
  '[] | PASSA',
  '5) DDT in BOZZA: non conta, la data della riga cambia ancora');

-- Emessa: la merce e' partita, per 4 su 10 (P-1).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', pg_temp.dc_fix('a1_ddt'), 'EMESSO');

SELECT is(
  (SELECT m ->> 'codice' || '|' || (m ->> 'reason') || '|' || (m ->> 'reason_key') || '|'
          || (m -> 'dettaglio' ->> 'ordine_riga_id') || '|' || (m -> 'valori')::text
     FROM (SELECT script.fn_check_ordine_riga_data_consegna_confermata(pg_temp.dc_fix('a_r1')) AS ms) x,
          LATERAL (SELECT x.ms -> 0 AS m) y
    WHERE jsonb_array_length(x.ms) = 1),
  'E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA|RIGA_SPEDITA|vendite.ordini.data_consegna_confermata_reason.riga_spedita|'
  || pg_temp.dc_fix('a_r1')::text || '|'
  || jsonb_build_array(
         (SELECT t.etichetta FROM script.fn_get_stato_testata_documento('ORDINE_VENDITA', pg_temp.dc_fix('a_ord')) t),
         '1')::text,
  '6) DDT EMESSO per una parte della riga (P-1): un motivo solo, RIGA_SPEDITA, coi suoi valori');

SELECT is(
  jsonb_array_length(script.fn_check_ordine_riga_data_consegna_confermata(pg_temp.dc_fix('a_r1')) -> 0 -> 'valori'),
  (SELECT (length(me.messaggio) - length(replace(me.messaggio, '%s', ''))) / 2
     FROM config.messaggi_errore me
    WHERE me.codice = 'E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA' AND me.lingua = 'it'),
  '7) i valori del motivo sono quanti ne chiede il messaggio del codice');

SELECT results_eq(
  format($q$SELECT v.riga_nr, v.data_consegna_confermata_blocco
              FROM vendite.vw_ordini_righe_dettaglio v
             WHERE v.ordine_id = %s ORDER BY v.riga_nr$q$, pg_temp.dc_fix('a_ord')),
  $$VALUES (1, 'RIGA_SPEDITA'::text), (2, NULL::text)$$,
  '8) la vista: la riga 1 porta RIGA_SPEDITA, la riga 2 nessun motivo');

SELECT is(
  pg_temp.dc_set_data(pg_temp.dc_fix('a_r1'), DATE '2026-11-30'),
  'E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA',
  '9) D-7: la data confermata della riga gia'' spedita non cambia');

SELECT ok(
  pg_temp.dc_frase(format('UPDATE vendite.ordini_righe SET data_consegna_confermata = DATE ''2026-11-30'' WHERE id = %s',
                          pg_temp.dc_fix('a_r1')))
    LIKE '%riga 1: la merce e'' gia'' partita con un DDT%',
  '10) la frase dice quale riga e perche''');

SELECT is(
  dbops.fn_pgtap_codice_errore(format('UPDATE vendite.ordini_righe SET data_consegna_confermata = data_consegna_confermata WHERE id = %s',
                          pg_temp.dc_fix('a_r1'))),
  NULL,
  '11) lo stesso valore non e'' un cambio: il guard non scatta (WHEN)');

SELECT is(
  (SELECT s.codice_interno FROM vendite.ordini o JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
    WHERE o.id = pg_temp.dc_fix('a_ord'))
  || ' | ' || pg_temp.dc_set_data(pg_temp.dc_fix('a_r2'), DATE '2026-11-25'),
  'PARZIALMENTE_EVASO | PASSA',
  '12) la riga 2, non spedita, nello stesso ordine PARZIALMENTE_EVASO: la data cambia');

-- ⭐ La forma dell'utility del backend (BF-1): un UPDATE solo, che salta le spedite.
SELECT is(
  pg_temp.dc_utility(pg_temp.dc_fix('a_ord'), DATE '2026-12-01'),
  'aggiornate 1 | saltate 1',
  '13) utility in blocco (forma del BE): salta la riga 1 spedita e scrive la riga 2, senza rifiuti');

SELECT results_eq(
  format($q$SELECT r.riga_nr, r.data_consegna_confermata FROM vendite.ordini_righe r
             WHERE r.ordine_id = %s ORDER BY r.riga_nr$q$, pg_temp.dc_fix('a_ord')),
  $$VALUES (1, DATE '2026-11-22'), (2, DATE '2026-12-01')$$,
  '14) la riga 1 tiene la data con cui e'' partita, la riga 2 ha la nuova');

-- Il DDT annullato col verbo: il legame si ritira, la merce non e' piu' partita.
SELECT * FROM vendite.fn_annulla_ddt(pg_temp.dc_fix('a1_ddt'), 1);

SELECT is(
  script.fn_check_ordine_riga_data_consegna_confermata(pg_temp.dc_fix('a_r1'))::text
  || ' | ' || pg_temp.dc_set_data(pg_temp.dc_fix('a_r1'), DATE '2026-12-02'),
  '[] | PASSA',
  '15) annullato il DDT (legame ritirato): la riga 1 torna libera, come dice la soluzione del messaggio');

-- ============================================================
-- B — gli stati, che parlano prima
-- ============================================================
-- Spedito per intero: tutte e due le righe, l'ordine diventa EVASO.
SELECT pg_temp.dc_mk_ordine('b', 'CONFERMATO');
SELECT b.ddt_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('pgtap_data_cons_spedita', 'EMESSO',
         p_ordine_id => pg_temp.dc_fix('b_ord'),
         p_righe     => jsonb_build_array(
                            jsonb_build_object('ordine_riga_id', pg_temp.dc_fix('b_r1'), 'qta_da_evadere', 10),
                            jsonb_build_object('ordine_riga_id', pg_temp.dc_fix('b_r2'), 'qta_da_evadere', 5)),
         p_data      => DATE '2026-10-02') b;

SELECT is(
  (SELECT s.codice_interno FROM vendite.ordini o JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
    WHERE o.id = pg_temp.dc_fix('b_ord'))
  || ' | ' || (script.fn_check_ordine_riga_data_consegna_confermata(pg_temp.dc_fix('b_r1')) -> 0 ->> 'reason'),
  'EVASO | STATO_NON_AMMETTE',
  '16) ordine EVASO: il primo motivo e'' lo STATO (la check di documento), non la riga spedita');

SELECT is(
  pg_temp.dc_set_data(pg_temp.dc_fix('b_r1'), DATE '2026-12-03'),
  'E_RIGA_DOC_NON_BOZZA',
  '17) ordine EVASO: l''UPDATE lo rifiuta il lock (_a05_), col codice del primo motivo');

SELECT pg_temp.dc_mk_ordine('c', 'DRAFT');

SELECT is(
  script.fn_check_ordine_riga_data_consegna_confermata(pg_temp.dc_fix('c_r1'))::text,
  '[]',
  '18) ordine in DRAFT: nessun motivo (in bozza la riga si modifica tutta)');

-- ============================================================
-- C — i bordi
-- ============================================================
SELECT is(
  vendite.fn_ordine_riga_spedita((SELECT COALESCE(max(id), 0) + 1000000 FROM vendite.ordini_righe)),
  false,
  '19) il lettore su un id assente risponde falso');

SELECT is(
  script.fn_check_ordine_riga_data_consegna_confermata((SELECT COALESCE(max(id), 0) + 1000000 FROM vendite.ordini_righe)),
  NULL::jsonb,
  '20) la check su un id assente: NULL');

SELECT is(
  dbops.fn_pgtap_codice_errore('SELECT script.fn_check_ordine_riga_data_consegna_confermata(0)'),
  'E_VENDITE_CHIAMATA_NON_VALIDA',
  '21) la check su un id non valido: errore del chiamante, non un motivo');

SELECT ok(
  (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') !~ '''E_[A-Z_]+'''
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'trgfn_ordini_righe_guard_data_consegna_spedita'),
  '22) il guard non scrive codici letterali: il codice arriva dal primo motivo della check');

-- ============================================================
-- D — la forma dell'utility in uno stato che non ammette la data
-- ============================================================
-- ⭐ BF-1: un ordine annullato, righe mai spedite. Il motivo e' di STATO: l'utility
--   non salta niente, e il lock rifiuta col suo codice (non «0 aggiornate»).
SELECT pg_temp.dc_mk_ordine('d', 'ANNULLATO');

SELECT is(
  (script.fn_check_ordine_riga_data_consegna_confermata(pg_temp.dc_fix('d_r1')) -> 0 ->> 'reason')
  || ' | ' || pg_temp.dc_utility(pg_temp.dc_fix('d_ord'), DATE '2026-12-04'),
  'STATO_NON_AMMETTE | E_RIGA_DOC_NON_BOZZA',
  '23) BF-1: ordine ANNULLATO, il motivo e'' di stato: l''utility non salta, il lock rifiuta col suo codice');

SELECT * FROM finish();
ROLLBACK;
