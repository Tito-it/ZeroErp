-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la PROVENIENZA dell'attivita' fatturabile e' la sua riga di commessa,
--   e la riga di fattura non ha una provenienza propria: la sua origine e' la
--   catena riga di fattura -> attivita' -> riga di commessa. Il pull ritrova la
--   riga gia' emessa per commessa_attivita_id, non per un'impronta della chiave
--   del segmento; chi leggeva le colonne sorgente_* dell'attivita' (il
--   normalize, la vista dello smistamento) legge la riga di commessa.
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto C, giro C.1 (D-1, D-3,
--   S-7, V-2, V-3); giro C.4 (D-2: ATTIVITA esce dalle sorgenti, 17-19)
--   rev 2026-11-08 (§7.3, giro finale bis, G-4, 20261110-31 e -32): la riga di
--   fattura perde le colonne sorgente_*, il CHECK di forma e il guard unico. Il
--   test 3 dice la forma nuova; i sei test sul guard unico della riga di fattura
--   (15-20 di prima: la riga di commessa giusta passa, quella di un'altra commessa,
--   l'impronta in sorgente_uid, il CHECK di forma, la commessa che non c'e', il
--   presidio degli orfani) escono: provavano una provenienza che la riga non ha
--   piu'. Al loro posto due test sulla catena che la sostituisce (15, 16).
-- ------------------------------------------------------------
-- Indice test (plan 19):
--   LA FORMA
--    1) attivita_fatturabili non ha piu' colonne sorgente_*
--    2) ... ed e' fuori dal perimetro della provenienza
--    3) fatture_righe: nessuna colonna sorgente_*, fuori dal perimetro e senza guard
--       unico; il lato «in uscita» resta (la riga di fattura e' la riga del tipo FATTURA)
--   IL PULL (V-3)
--    4) la prima emissione crea un'attivita' per la riga di commessa
--    5) 🔴 la chiave del segmento cambia sotto la riga emessa, la riga si libera
--       e il giro dopo la riprende: nessun errore
--    6) ... e' la STESSA attivita', aggiornata: nessuna seconda
--    7) ... il pull la conta come aggiornata, non come inserita
--    8) due commesse con la stessa chiave del segmento: ognuna ha la sua attivita'
--       (la ricerca non esce dalla commessa)
--   IL NORMALIZE
--    9) tipo_doc_fiscale_id mancante: dal tipo del documento della riga di commessa
--   10) ... e dal tipo COMMESSA per la riga di commessa senza documento
--   LO SMISTAMENTO (V-2)
--   11) la riga di preventivo mandata in commessa e non emessa: IN_COMMESSA
--   12) ... emessa: EMESSA_AF
--   13) ... fatturata: FATTURATA
--   14) ... la riga di commessa annullata non conta
--   L'ORIGINE DELLA RIGA DI FATTURA E' LA CATENA (G-4)
--   15) dalla riga di fattura, l'attivita' che la cita porta alla riga di commessa
--   16) ... e vendite.fn_fattura_origini ne dice il documento (il preventivo)
--   L'ATTIVITA' NON E' UNA PROVENIENZA (giro C.4)
--   17) ATTIVITA non e' piu' un tipo di config.sorgenti
--   18) ... e resta un'entita' di config.tipi_entita, non sorgente
--   19) ... e attivita_fatturabili non porta piu' il lato «in uscita»
--
-- ⚠️ Il mondo si COSTRUISCE: commesse, righe di commessa, preventivo, lotto e
--   fattura dai builder dbops.fn_pgtap_*. Gira come l'applicazione (operatore in
--   sessione, RLS attiva). Il cambio della chiave del segmento (5) si scrive a
--   mano: e' il caso che il cambio di formato delle chiavi ha prodotto su
--   righe gia' emesse, e nessun verbo lo fa.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(19);

-- ============================================================
-- LA FORMA
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pg_attribute a
    WHERE a.attrelid = 'vendite.attivita_fatturabili'::regclass
      AND a.attnum > 0 AND NOT a.attisdropped
      AND a.attname LIKE 'sorgente%'),
  0,
  '1) attivita_fatturabili non ha colonne sorgente_*: la provenienza e'' la riga di commessa (FK)');

-- ⚠️ Schema e nome da pg_class + pg_namespace, non da regclass::text: il testo
--   di un regclass dipende dal search_path di chi guarda.
SELECT ok(
  NOT EXISTS (SELECT 1 FROM dbops.fn_sorgenti_orfane_perimetro() p
               WHERE p.schema_tabella = 'vendite' AND p.nome_tabella = 'attivita_fatturabili'),
  '2) attivita_fatturabili e'' fuori dal perimetro della provenienza');

SELECT is(
  (SELECT concat_ws('|',
      (SELECT count(*) FROM pg_attribute a
        WHERE a.attrelid = 'vendite.fatture_righe'::regclass
          AND a.attnum > 0 AND NOT a.attisdropped
          AND a.attname LIKE 'sorgente%'),
      (SELECT count(*) FROM script.fn_sorgente_guard_montaggi() m
        WHERE m.schema_tabella = 'vendite' AND m.nome_tabella = 'fatture_righe'),
      (SELECT count(*) FROM dbops.fn_sorgenti_orfane_perimetro() p
        WHERE p.schema_tabella = 'vendite' AND p.nome_tabella = 'fatture_righe'),
      (SELECT count(*) FROM pg_trigger tg
        WHERE tg.tgrelid = 'vendite.fatture_righe'::regclass
          AND tg.tgfoid = 'script.trgfn_sorgente_in_uscita()'::regprocedure))),
  '0|0|0|1',
  '3) fatture_righe: nessuna colonna sorgente_*, fuori dal perimetro, senza guard unico; il lato «in uscita» resta');

-- ============================================================
-- Fixture: le commesse e le loro righe
-- ============================================================
CREATE TEMP TABLE _comm AS
SELECT v.k, c.*
  FROM (VALUES ('M1'), ('M2')) v(k),
       LATERAL dbops.fn_pgtap_crea_commessa('sorgente af ' || v.k, p_con_attivita => false,
                                            p_con_sorgente_root => true) c;

CREATE FUNCTION pg_temp.comm(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT commessa_id FROM _comm WHERE k = p $fx$;

-- La riga di commessa A (M1), emessa una volta.
CREATE TEMP TABLE _ca AS
SELECT 'A'::text AS k, a.attivita_id
  FROM dbops.fn_pgtap_crea_commessa_attivita(pg_temp.comm('M1'), 10) a;

CREATE TEMP TABLE _emit1 AS
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(p_commessa_id => pg_temp.comm('M1'));

CREATE TEMP TABLE _af1 AS
SELECT af.id FROM vendite.attivita_fatturabili af
 WHERE af.commessa_attivita_id = (SELECT attivita_id FROM _ca WHERE k = 'A');

-- ============================================================
-- IL PULL (V-3)
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM _af1),
  1,
  '4) la prima emissione crea un''attivita'' fatturabile per la riga di commessa');

-- Il caso V-3: la chiave del segmento cambia sotto la riga gia' emessa (come col
-- cambio di formato delle chiavi), la riga si libera, il giro dopo la riprende.
-- La chiave nuova nomina ancora il suo documento (il guard della chiave del push).
UPDATE vendite.commesse_attivita ca
   SET segment_key = (ca.segment_key || ':NUOVA')::varchar
 WHERE ca.id = (SELECT attivita_id FROM _ca WHERE k = 'A');

SELECT vendite.fn_libera_attivita_fatturabili(ARRAY(SELECT id FROM _af1));

CREATE TEMP TABLE _emit2 (r text);
INSERT INTO _emit2
SELECT COALESCE(dbops.fn_pgtap_codice_errore(format(
  'CREATE TEMP TABLE _emit2_esito AS SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(p_commessa_id => %s)',
  pg_temp.comm('M1'))), 'PASSA');

SELECT is(
  (SELECT r FROM _emit2),
  'PASSA',
  '5) chiave del segmento cambiata, riga liberata: il giro dopo la riprende senza errore');

SELECT is(
  (SELECT string_agg(af.id::text, ',') FROM vendite.attivita_fatturabili af
    WHERE af.commessa_attivita_id = (SELECT attivita_id FROM _ca WHERE k = 'A')),
  (SELECT id::text FROM _af1),
  '6) ... ed e'' la STESSA attivita'' fatturabile: nessuna seconda');

SELECT is(
  (SELECT inserted_rows || '/' || updated_rows FROM _emit2_esito),
  '0/1',
  '7) ... il pull la conta come aggiornata, non come inserita');

-- Due commesse con la stessa chiave del segmento: la riga B di M2 prende la
-- chiave della riga A di M1. La ricerca per riga di commessa non esce dalla
-- commessa: M2 ha la sua attivita', quella di M1 resta dov'e'.
INSERT INTO _ca
SELECT 'B', a.attivita_id
  FROM dbops.fn_pgtap_crea_commessa_attivita(pg_temp.comm('M2'), 20) a;

-- La chiave nomina il documento della riga: B prende da A provenienza e chiave
-- insieme (a mano, senza la porta del link: un documento sta in una sola commessa
-- aperta, e qui serve solo la stessa chiave in due commesse).
UPDATE vendite.commesse_attivita ca
   SET segment_key      = x.segment_key,
       sorgente_tipo_id = x.sorgente_tipo_id,
       sorgente_id      = x.sorgente_id,
       sorgente_uid     = x.sorgente_uid,
       sorgente_riga    = x.sorgente_riga
  FROM vendite.commesse_attivita x
 WHERE x.id = (SELECT attivita_id FROM _ca WHERE k = 'A')
   AND ca.id = (SELECT attivita_id FROM _ca WHERE k = 'B');

SELECT vendite.fn_libera_attivita_fatturabili(ARRAY(SELECT id FROM _af1));
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(p_commessa_id => pg_temp.comm('M2'));

SELECT is(
  (SELECT string_agg(c.k || '=' || (SELECT count(*) FROM vendite.attivita_fatturabili af
                                     WHERE af.commessa_attivita_id = c.attivita_id
                                       AND af.commessa_id = pg_temp.comm(CASE c.k WHEN 'A' THEN 'M1' ELSE 'M2' END)),
                     ',' ORDER BY c.k)
     FROM _ca c),
  'A=1,B=1',
  '8) stessa chiave del segmento in due commesse: ognuna ha la sua attivita'' fatturabile');

-- ============================================================
-- IL NORMALIZE
-- ============================================================
-- Il preventivo, con righe, sul conto di una commessa sua.
CREATE TEMP TABLE _prev AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo_con_righe('sorgente af prev');

INSERT INTO _comm
SELECT 'MP', c.*
  FROM dbops.fn_pgtap_crea_commessa('sorgente af MP',
         p_billing_account_id => (SELECT billing_account_id FROM _prev LIMIT 1),
         p_con_attivita => false, p_con_sorgente_root => true) c;

-- La riga di commessa nata dalla riga del preventivo: tipo PREVENTIVO, la
-- chiave del preventivo, il segmento PREVENTIVO:<uid>:R:<riga>.
INSERT INTO _ca
SELECT 'P', a.attivita_id
  FROM dbops.fn_pgtap_crea_commessa_attivita(pg_temp.comm('MP'), 30,
         p_sorgente_codice => 'PREVENTIVO',
         p_sorgente_chiave => (SELECT preventivo_uid::text FROM _prev LIMIT 1),
         p_sorgente_riga_id => (SELECT preventivo_riga_id FROM _prev ORDER BY preventivo_riga_id LIMIT 1)) a;

CREATE FUNCTION pg_temp.stato_smist() RETURNS text LANGUAGE sql STABLE AS $fx$
  SELECT v.stato_smistamento FROM vendite.vw_preventivi_smistamento_righe v
   WHERE v.riga_id = (SELECT preventivo_riga_id FROM _prev ORDER BY preventivo_riga_id LIMIT 1)
$fx$;

CREATE TEMP TABLE _smist (k text, stato text);
INSERT INTO _smist SELECT 'prima', pg_temp.stato_smist();

SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(p_commessa_id => pg_temp.comm('MP'));
INSERT INTO _smist SELECT 'emessa', pg_temp.stato_smist();

CREATE FUNCTION pg_temp.af_di(p text) RETURNS bigint LANGUAGE sql STABLE AS $fx$
  SELECT af.id FROM vendite.attivita_fatturabili af
   WHERE af.commessa_attivita_id = (SELECT attivita_id FROM _ca WHERE k = p)
$fx$;

-- La riga di commessa senza documento: un onere, dalla sua porta, sulla
-- commessa M2 (sourceless: tipo_movimento ONERE, nessuna provenienza).
INSERT INTO _ca
SELECT 'O', vendite.fn_aggiungi_onere_commessa(
         p_commessa_id         => pg_temp.comm('M2'),
         p_istanza_utility_id  => (SELECT istanza_utility_id FROM _comm WHERE k = 'M2'),
         p_articolo_onere_id   => (SELECT id FROM catalogo.articoli WHERE codice = 'ONERE_TRASFERTA'),
         p_importo             => 15.00,
         p_tipo_doc_fiscale_id => (SELECT id FROM config.tipi_doc_fiscale WHERE attivo IS TRUE ORDER BY id LIMIT 1),
         p_motivo              => 'pgTAP sorgente af');
SELECT * FROM vendite.fn_emit_attivita_fatturabili_da_commessa(p_commessa_id => pg_temp.comm('M2'));

-- tipo_doc_fiscale_id tolto: il normalize lo rimette dal tipo del documento
-- della riga di commessa (P: PREVENTIVO) o, senza documento, da COMMESSA (O).
CREATE TEMP TABLE _norm (k text, r text);
INSERT INTO _norm SELECT 'P', COALESCE(dbops.fn_pgtap_codice_errore(format(
  'UPDATE vendite.attivita_fatturabili SET tipo_doc_fiscale_id = NULL WHERE id = %s', pg_temp.af_di('P'))), 'PASSA');
INSERT INTO _norm SELECT 'O', COALESCE(dbops.fn_pgtap_codice_errore(format(
  'UPDATE vendite.attivita_fatturabili SET tipo_doc_fiscale_id = NULL WHERE id = %s', pg_temp.af_di('O'))), 'PASSA');

SELECT is(
  (SELECT n.r || '/' || (af.tipo_doc_fiscale_id = s.tipo_doc_fiscale_id)::text
     FROM _norm n, vendite.attivita_fatturabili af, config.sorgenti s
    WHERE n.k = 'P' AND af.id = pg_temp.af_di('P') AND s.codice_interno = 'PREVENTIVO'),
  'PASSA/true',
  '9) tipo_doc_fiscale_id mancante: dal tipo del documento della riga di commessa (PREVENTIVO)');

SELECT is(
  (SELECT n.r || '/' || (af.tipo_doc_fiscale_id = s.tipo_doc_fiscale_id)::text
     FROM _norm n, vendite.attivita_fatturabili af, config.sorgenti s
    WHERE n.k = 'O' AND af.id = pg_temp.af_di('O') AND s.codice_interno = 'COMMESSA'),
  'PASSA/true',
  '10) ... e dal tipo COMMESSA per la riga di commessa senza documento');

-- ============================================================
-- LO SMISTAMENTO (V-2)
-- ============================================================
SELECT is(
  (SELECT stato FROM _smist WHERE k = 'prima'),
  'IN_COMMESSA',
  '11) riga di preventivo mandata in commessa e non emessa: IN_COMMESSA');

SELECT is(
  (SELECT stato FROM _smist WHERE k = 'emessa'),
  'EMESSA_AF',
  '12) ... emessa in un''attivita'' fatturabile: EMESSA_AF');

CREATE TEMP TABLE _fatt AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('sorgente af fattura',
                ARRAY[(SELECT attivita_id FROM _ca WHERE k = 'P')]);

SELECT is(
  pg_temp.stato_smist(),
  'FATTURATA',
  '13) ... fatturata: FATTURATA');

-- La riga di commessa annullata non conta, come per IN_COMMESSA. Si scrive lo
-- stato a mano: l'annullo vero vuole una riga mai emessa, qui serve la riga
-- con la sua attivita'.
UPDATE vendite.commesse_attivita ca SET stato_emissione = 'ANNULLATA'
 WHERE ca.id = (SELECT attivita_id FROM _ca WHERE k = 'P');

SELECT isnt(
  pg_temp.stato_smist(),
  'FATTURATA',
  '14) ... la riga di commessa annullata non conta');

UPDATE vendite.commesse_attivita ca SET stato_emissione = 'EMESSA'
 WHERE ca.id = (SELECT attivita_id FROM _ca WHERE k = 'P');

-- ============================================================
-- L'ORIGINE DELLA RIGA DI FATTURA E' LA CATENA (G-4)
-- ============================================================
-- La riga di fattura aggrega attivita' con provenienze diverse: non ne dichiara
-- una sua. Da lei si risale all'attivita' che la cita (fattura_riga_id), da
-- questa alla riga di commessa, e dalla riga di commessa al documento.
SELECT is(
  (SELECT string_agg(af.commessa_attivita_id::text, ',')
     FROM vendite.attivita_fatturabili af
    WHERE af.fattura_riga_id = (SELECT fattura_riga_id FROM _fatt LIMIT 1)),
  (SELECT attivita_id::text FROM _ca WHERE k = 'P'),
  '15) dalla riga di fattura, l''attivita'' che la cita porta alla sua riga di commessa');

SELECT ok(
  EXISTS (SELECT 1 FROM vendite.fn_fattura_origini((SELECT fattura_id FROM _fatt LIMIT 1)) o
           WHERE o.livello = 1
             AND o.tipo_codice_interno = 'PREVENTIVO'
             AND o.uid = (SELECT preventivo_uid::text FROM _prev LIMIT 1)),
  '16) ... e vendite.fn_fattura_origini ne dice il documento: il preventivo della riga di commessa, al livello 1');

-- ============================================================
-- L'ATTIVITA' NON E' UNA PROVENIENZA (giro C.4, D-2)
-- ============================================================
-- Niente nasce da un'attivita' fatturabile: la sua provenienza e' la riga di
-- commessa (1). Il tipo stava a catalogo solo come genitore della FK di
-- config.tipi_entita; l'entita' resta per le note.
SELECT is(
  (SELECT count(*)::int FROM config.sorgenti s WHERE s.codice_interno = 'ATTIVITA'),
  0,
  '17) ATTIVITA non e'' un tipo di config.sorgenti');

SELECT is(
  (SELECT format('%s|%s|%s', e.is_sorgente::text, (e.sorgente_codice_interno IS NULL)::text, e.etichetta_key)
     FROM config.tipi_entita e WHERE e.codice = 'ATTIVITA'),
  'false|true|config.tipi_entita.attivita',
  '18) ATTIVITA resta un''entita'' (note), con is_sorgente false e senza legame al catalogo delle sorgenti');

-- Il lato «in uscita» lo monta e lo smonta la convergenza di 90_end sul catalogo:
-- la tabella non e' piu' documento, righe o dettaglio di nessun tipo.
SELECT is(
  (SELECT count(*)::int FROM pg_trigger tg
    WHERE tg.tgrelid = 'vendite.attivita_fatturabili'::regclass
      AND tg.tgfoid = 'script.trgfn_sorgente_in_uscita()'::regprocedure),
  0,
  '19) attivita_fatturabili non porta il lato «in uscita»: nessun tipo la dichiara');

SELECT * FROM finish();
ROLLBACK;
