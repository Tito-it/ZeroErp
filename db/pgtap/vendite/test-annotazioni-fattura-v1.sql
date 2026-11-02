-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: le annotazioni di legge della fattura, decise dal database
--   vendite.fn_annotazioni_fattura · vendite.fn_regime_fiscale_fattura ·
--   script.fn_regime_fiscale_documento (la regola del regime, estratta) ·
--   config.regimi_fiscali chk_regimi_fiscali_per_cassa_annotazione
-- Brief: brief-db-esigibilita-iva-per-cassa-emittente, sezione 11 (R-DB-3, AN-1)
-- ChangeSet: 20261002-02 ... -07
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   Una fattura di un emittente in IVA per cassa con righe a esigibilita'
--   differita deve stampare l'annotazione art. 32-bis; con sole righe
--   immediate non deve. Il test costruisce i casi (regola zero): nessun
--   confronto con le fatture che ci sono.
--
-- ⭐ Il testo atteso si legge dal CATALOGO, non si ricopia: il test prova che
--   la voce porta il testo del regime, non una frase.
-- ⭐ Il codice IVA non imponibile (N3.1) si FABBRICA (id 999902), come in
--   test-esigibilita-iva-per-cassa-v1: e' la riga che su un emittente per
--   cassa resta immediata (D-12).
--
-- Indice test
--  1) una sola funzione per nome: l'estrazione non ha creato overload
--  2) il catalogo: un regime per cassa porta sempre il testo (CHECK)
--  3) la regola del regime: il congelato prevale sul vivo
--  4) la regola del regime: un congelato fatto di spazi lascia il vivo
--  5) la regola del regime: ne' emittente ne' congelato -> NULL
--  6) fattura RF01, riga immediata: nessuna voce
--  7) ⭐ fattura RF17 SENZA snapshot, riga differita: la voce c'e' (regime vivo)
--  8) ⭐ fattura RF17 con sole righe immediate: nessuna voce (sezione 8.7)
--  9) ⭐ snapshot RF17, regime vivo RF01: la voce c'e' (regime congelato)
-- 10) il regime della fattura segue lo snapshot
-- 11) fattura inesistente: nessuna voce, regime NULL
-- 12) id NULL: E_VENDITE_CHIAMATA_NON_VALIDA
-- 13) id zero: E_VENDITE_CHIAMATA_NON_VALIDA
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: RLS attiva, come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(13);

-- ============================================================
-- La fixture
-- ============================================================
CREATE TEMP TABLE tmp_an AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('annotazioni fattura');

CREATE TEMP TABLE tmp_an_iva AS
SELECT (SELECT i.id FROM config.iva i
         WHERE i.attivo IS TRUE AND i.aliquota_iva > 0 AND i.natura_iva_id IS NULL
         ORDER BY i.id LIMIT 1)                                      AS iva_ord,
       999902                                                        AS iva_ni,
       (SELECT sr.soggetto_id FROM anagrafiche.soggetti_ruoli sr
         WHERE sr.id = (SELECT cliente_soggetto_ruolo_id FROM tmp_an)) AS cliente_soggetto_id,
       (SELECT rf.annotazione_documento FROM config.regimi_fiscali rf
         WHERE rf.codice_interno = 'RF17')                           AS testo_rf17;

-- Un codice NON imponibile (natura N3.1, aliquota zero): su un emittente per
-- cassa la riga resta immediata (D-12).
INSERT INTO config.iva (id, codice, descrizione, descrizione_breve, aliquota_iva,
                        natura_iva_id, codice_interno, attivo)
SELECT 999902, 'PGTAP_NI', 'pgTAP non imponibile', 'pgTAP NI', 0,
       n.id, 'PGTAP_NI', true
  FROM config.iva_natura n
 WHERE n.codice = 'N3.1';

CREATE OR REPLACE FUNCTION pg_temp.fx_riga(p_nr integer, p_iva integer)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta, prezzo_unitario, iva_id, competenza_dal, competenza_al)
  SELECT (SELECT fattura_id FROM tmp_an), p_nr, 'Riga ' || p_nr, 1, 100, p_iva, script.fn_data_operativa(), script.fn_data_operativa()
  RETURNING id;
$fx$;

-- Riscrive il codice IVA di tutte le righe: la derivazione pura (D-7)
-- ricalcola l'esigibilita' a ogni scrittura.
CREATE OR REPLACE FUNCTION pg_temp.fx_righe_iva(p_iva integer)
RETURNS void LANGUAGE sql AS $fx$
  UPDATE vendite.fatture_righe SET iva_id = p_iva
   WHERE fattura_id = (SELECT fattura_id FROM tmp_an);
$fx$;

CREATE OR REPLACE FUNCTION pg_temp.fx_regime(p_rf varchar)
RETURNS void LANGUAGE sql AS $fx$
  UPDATE anagrafiche.emittenti_fiscali SET regime_fiscale_rf = p_rf
   WHERE id = (SELECT emittente_fiscale_id FROM tmp_an);
$fx$;

-- Le voci, in una stringa: «codice|testo|ordine» separate da «;».
CREATE OR REPLACE FUNCTION pg_temp.fx_voci(p_fattura_id bigint)
RETURNS text LANGUAGE sql AS $fx$
  SELECT COALESCE(string_agg(a.codice || '|' || a.testo || '|' || a.ordine, ';'
                             ORDER BY a.ordine), '')
    FROM vendite.fn_annotazioni_fattura(p_fattura_id) a;
$fx$;

-- ============================================================
-- 1-2) La struttura
-- ============================================================
SELECT is(
  (SELECT string_agg(p.proname || ':' || n_per_nome, ',' ORDER BY p.proname)
     FROM (SELECT p.proname, count(*) AS n_per_nome
             FROM pg_catalog.pg_proc p
             JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
            WHERE (n.nspname, p.proname) IN (('script',  'fn_regime_fiscale_documento'),
                                             ('script',  'fn_esigibilita_iva_documento'),
                                             ('vendite', 'fn_regime_fiscale_fattura'),
                                             ('vendite', 'fn_esigibilita_iva_fattura'),
                                             ('vendite', 'fn_annotazioni_fattura'))
            GROUP BY p.proname) p),
  'fn_annotazioni_fattura:1,fn_esigibilita_iva_documento:1,fn_esigibilita_iva_fattura:1,'
  'fn_regime_fiscale_documento:1,fn_regime_fiscale_fattura:1',
  '1) una sola funzione per nome: l''estrazione della regola non ha creato overload'
);

SELECT is(
  (SELECT pg_catalog.pg_get_constraintdef(c.oid)
     FROM pg_catalog.pg_constraint c
    WHERE c.conrelid = 'config.regimi_fiscali'::regclass
      AND c.conname  = 'chk_regimi_fiscali_per_cassa_annotazione'),
  'CHECK (((NOT iva_per_cassa) OR (annotazione_documento IS NOT NULL)))',
  '2) un regime per cassa porta sempre il testo dell''annotazione'
);

-- ============================================================
-- 3-5) La regola del regime, sui valori
-- ============================================================
UPDATE anagrafiche.soggetti SET split_payment = 'N'
 WHERE id = (SELECT cliente_soggetto_id FROM tmp_an_iva);
SELECT pg_temp.fx_regime('RF01');

SELECT is(script.fn_regime_fiscale_documento((SELECT emittente_fiscale_id FROM tmp_an), 'RF17'),
          'RF17', '3) il regime congelato prevale su quello vivo (RF01)');
SELECT is(script.fn_regime_fiscale_documento((SELECT emittente_fiscale_id FROM tmp_an), '   '),
          'RF01', '4) un congelato fatto di spazi non e'' un regime: vale quello vivo');
SELECT is(script.fn_regime_fiscale_documento(NULL, NULL),
          NULL, '5) ne'' emittente ne'' congelato: regime non noto');

-- ============================================================
-- 6-10) La fattura
-- ============================================================
SELECT pg_temp.fx_riga(1, (SELECT iva_ord FROM tmp_an_iva));

SELECT is(pg_temp.fx_voci((SELECT fattura_id FROM tmp_an)), '',
          '6) emittente RF01, riga immediata: nessuna annotazione');

-- ⭐ Nessuno snapshot: il regime della fattura e' quello vivo. La riga 2 nasce
--   differita (la riga 1 resta immediata finche' non si riscrive: basta una).
SELECT pg_temp.fx_regime('RF17');
SELECT pg_temp.fx_riga(2, (SELECT iva_ord FROM tmp_an_iva));

SELECT is(pg_temp.fx_voci((SELECT fattura_id FROM tmp_an)),
          'ESIGIBILITA_DIFFERITA|' || (SELECT testo_rf17 FROM tmp_an_iva) || '|10',
          '7) emittente RF17 senza snapshot, righe differite: una voce, col testo del catalogo');

-- ⭐ Stesso emittente per cassa, ma nessuna riga ha un'imposta da differire:
--   l'annotazione sarebbe falsa.
SELECT pg_temp.fx_righe_iva((SELECT iva_ni FROM tmp_an_iva));

SELECT is(pg_temp.fx_voci((SELECT fattura_id FROM tmp_an)), '',
          '8) emittente RF17 con sole righe immediate (Natura N3.1): nessuna annotazione');

-- ⭐ Lo snapshot dice RF17, l'anagrafica viva RF01. Le righe tornano
--   imponibili e seguono il regime congelato (D); l'annotazione legge lo
--   stesso regime delle righe.
SELECT pg_temp.fx_regime('RF01');
UPDATE vendite.fatture
   SET emittente_snapshot = jsonb_build_object('regime_fiscale_rf', 'RF17')
 WHERE id = (SELECT fattura_id FROM tmp_an);
SELECT pg_temp.fx_righe_iva((SELECT iva_ord FROM tmp_an_iva));

SELECT is(pg_temp.fx_voci((SELECT fattura_id FROM tmp_an)),
          'ESIGIBILITA_DIFFERITA|' || (SELECT testo_rf17 FROM tmp_an_iva) || '|10',
          '9) snapshot RF17 e regime vivo RF01: la voce c''e'', come le righe differite');

SELECT is(vendite.fn_regime_fiscale_fattura((SELECT fattura_id FROM tmp_an)),
          'RF17', '10) il regime della fattura e'' quello congelato nello snapshot');

-- ============================================================
-- 11-13) I bordi
-- ============================================================
SELECT is(
  pg_temp.fx_voci((SELECT max(id) + 1000 FROM vendite.fatture))
  || '|' || COALESCE(vendite.fn_regime_fiscale_fattura((SELECT max(id) + 1000 FROM vendite.fatture)),
                     'NULL'),
  '|NULL',
  '11) fattura inesistente: nessuna voce e regime non noto'
);

SELECT throws_like(
  $$ SELECT * FROM vendite.fn_annotazioni_fattura(NULL) $$,
  '%Chiamata non valida a vendite.fn_annotazioni_fattura%',
  '12) id NULL: E_VENDITE_CHIAMATA_NON_VALIDA (e'' il chiamante a essere rotto)'
);

SELECT throws_like(
  $$ SELECT * FROM vendite.fn_annotazioni_fattura(0) $$,
  '%Chiamata non valida a vendite.fn_annotazioni_fattura%',
  '13) id zero: E_VENDITE_CHIAMATA_NON_VALIDA'
);

SELECT * FROM finish();

ROLLBACK;
