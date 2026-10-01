-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: l'esigibilita' IVA col regime dell'emittente (IVA per cassa)
--   script.fn_esigibilita_iva (la regola) · script.fn_esigibilita_iva_documento ·
--   vendite.fn_esigibilita_iva_fattura · trigger di riga della fattura ·
--   vendite.fn_ricalcola_riepilogo_iva_fattura · vendite.fn_resolve_iva_riga ·
--   config.regimi_fiscali · emittenti_fiscali.regime_fiscale_rf (FK, NOT NULL,
--   conferma) · dbops.vw_emittenti_regime_non_confermato
-- Brief: brief-db-esigibilita-iva-per-cassa-emittente (D-1 ... D-11)
-- ChangeSet: 20261001-01 ... -17, 20261001-40 (D-12)
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   Un emittente in IVA per cassa emetteva tutte le fatture a esigibilita'
--   immediata senza un errore: la decisione guardava solo il cliente. Questo
--   file costruisce i casi — nessun confronto con la popolazione (regola zero).
--
-- ⭐ La MATRICE (casi 2-10) prova la regola sui valori: e' li' che stanno i
--   rami che i dati di oggi non sanno produrre (un privato verso un emittente
--   per cassa, una partita IVA fatta di spazi, un codice IVA assente).
-- ⭐ Il codice IVA in inversione contabile si FABBRICA (id 999901): il seed di
--   config.iva non ne ha nessuno (letto il 2026-10-01), e un test che lo
--   cercasse nel catalogo passerebbe a vuoto. Id esplicito: la sequence di
--   config.iva e' vergine rispetto al seed (memoria «id esplicito»).
-- ⭐ Il cliente della fixture e' una persona giuridica con partita IVA
--   (dbops.fn_pgtap_crea_soggetto_pg): e' lui il «soggetto IVA» dei casi
--   sulla fattura. Il privato si prova nella matrice: togliere la partita IVA
--   a una persona giuridica la farebbe fermare dal guard cf/piva.
--
-- Indice test
--  1) catalogo: RF17 e' l'UNICO regime per cassa, e porta l'annotazione
--  2) matrice: cliente non noto -> NULL/NULL
--  3) matrice: scissione su emittente per cassa -> S/true
--  4) matrice: regime ordinario -> I/false
--  5) matrice: per cassa verso un privato -> I
--  6) matrice: per cassa, partita IVA fatta di spazi -> I (non e' una partita IVA)
--  7) matrice: per cassa senza codice IVA -> NULL (natura ignota)
--  8) matrice: per cassa, codice imponibile -> D
--  9) matrice: per cassa, inversione contabile -> I
-- 9-bis) ⭐ D-12: per cassa, qualsiasi Natura (qui N3.1 non imponibile) -> I
-- 10) matrice: regime non noto, non scissa -> NULL/false
-- 11) fattura: emittente RF01 -> la riga nasce I
-- 12) fattura: emittente RF17 -> la riga nasce D
-- 13) ⭐ D-7: la riga nata I diventa D alla scrittura successiva (derivazione pura)
-- 14) fattura RF17: la riga in inversione contabile resta I
-- 15) ⭐ D-8: il ricalcolo del riepilogo riallinea le righe al regime cambiato
-- 16) ⭐ D-7: una D scritta a mano su un emittente ordinario NON sopravvive
-- 17) ⭐ D-8: con lo snapshot, la riga segue il regime CONGELATO, non quello vivo
-- 18) la parte documento: regime vivo, e il regime passato prevale
-- 19) il risolutore IVA risponde come la riga (stessa regola)
-- 20) la FK rifiuta un regime fuori catalogo (23503)
-- 21) il regime e' obbligatorio (23502)
-- 22) la conferma scritta col regime nuovo resta
-- 23) ⭐ il regime che cambia senza conferma azzera la conferma
-- 24) il presidio mostra l'emittente non confermato e tace dopo la conferma
-- 25) ⛔ una conferma senza autore e' rifiutata (23514)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: RLS attiva, come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(26);

-- ============================================================
-- La fixture
-- ============================================================
CREATE TEMP TABLE tmp_ec AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('esigibilita per cassa');

CREATE TEMP TABLE tmp_ec_iva AS
SELECT (SELECT i.id FROM config.iva i
         WHERE i.attivo IS TRUE AND i.aliquota_iva > 0 AND i.natura_iva_id IS NULL
         ORDER BY i.id LIMIT 1)                                      AS iva_ord,
       999901                                                        AS iva_rc,
       (SELECT sr.soggetto_id FROM anagrafiche.soggetti_ruoli sr
         WHERE sr.id = (SELECT cliente_soggetto_ruolo_id FROM tmp_ec)) AS cliente_soggetto_id;

-- Il codice in inversione contabile: aliquota zero, natura N6.3.
INSERT INTO config.iva (id, codice, descrizione, descrizione_breve, aliquota_iva,
                        natura_iva_id, codice_interno, attivo)
SELECT 999901, 'PGTAP_RC', 'pgTAP inversione contabile', 'pgTAP RC', 0,
       n.id, 'PGTAP_RC', true
  FROM config.iva_natura n
 WHERE n.codice = 'N6.3';

-- ⭐ D-12: un codice NON imponibile (natura N3.1, aliquota zero). Fino al -40
--   la regola lo mandava a 'D' su un emittente per cassa: non e' in inversione
--   contabile, ma non ha nemmeno un'imposta da differire.
INSERT INTO config.iva (id, codice, descrizione, descrizione_breve, aliquota_iva,
                        natura_iva_id, codice_interno, attivo)
SELECT 999902, 'PGTAP_NI', 'pgTAP non imponibile', 'pgTAP NI', 0,
       n.id, 'PGTAP_NI', true
  FROM config.iva_natura n
 WHERE n.codice = 'N3.1';

CREATE OR REPLACE FUNCTION pg_temp.fx_riga(p_nr integer, p_iva integer, p_esig char DEFAULT NULL)
RETURNS bigint LANGUAGE sql AS $fx$
  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, descrizione, qta, prezzo_unitario,
                                     iva_id, esigibilita)
  SELECT (SELECT fattura_id FROM tmp_ec), p_nr, 'Riga ' || p_nr, 1, 100, p_iva, p_esig
  RETURNING id;
$fx$;

CREATE OR REPLACE FUNCTION pg_temp.fx_coppia(p_nr integer)
RETURNS text LANGUAGE sql AS $fx$
  SELECT COALESCE(r.esigibilita::text, 'NULL') || '/' || COALESCE(r.split_payment::text, 'NULL')
    FROM vendite.fatture_righe r
   WHERE r.fattura_id = (SELECT fattura_id FROM tmp_ec) AND r.riga_nr = p_nr;
$fx$;

CREATE OR REPLACE FUNCTION pg_temp.fx_regime(p_rf varchar)
RETURNS void LANGUAGE sql AS $fx$
  UPDATE anagrafiche.emittenti_fiscali SET regime_fiscale_rf = p_rf
   WHERE id = (SELECT emittente_fiscale_id FROM tmp_ec);
$fx$;

CREATE OR REPLACE FUNCTION pg_temp.fx_m(p_cassa boolean, p_split char, p_piva text, p_iva integer)
RETURNS text LANGUAGE sql AS $fx$
  SELECT COALESCE(e.esigibilita::text, 'NULL') || '/' || COALESCE(e.split_payment::text, 'NULL')
    FROM script.fn_esigibilita_iva(p_cassa, p_split, p_piva, p_iva) e;
$fx$;

-- ============================================================
-- 1) Il catalogo
-- ============================================================
SELECT is(
  (SELECT string_agg(codice_interno || ':' || (annotazione_documento IS NOT NULL)::text, ',')
     FROM config.regimi_fiscali WHERE iva_per_cassa),
  'RF17:true',
  '1) RF17 e'' l''unico regime per cassa, e porta l''annotazione da stampare'
);

-- ============================================================
-- 2-10) La matrice della regola, sui valori
-- ============================================================
SELECT is(pg_temp.fx_m(true, NULL, '01234567890', (SELECT iva_ord FROM tmp_ec_iva)),
          'NULL/NULL', '2) cliente non noto: la coppia dice «non lo so» insieme (D32)');
SELECT is(pg_temp.fx_m(true, 'S', '01234567890', (SELECT iva_ord FROM tmp_ec_iva)),
          'S/true', '3) la scissione prevale anche su un emittente per cassa');
SELECT is(pg_temp.fx_m(false, 'N', '01234567890', (SELECT iva_ord FROM tmp_ec_iva)),
          'I/false', '4) regime ordinario: immediata');
SELECT is(pg_temp.fx_m(true, 'N', NULL, (SELECT iva_ord FROM tmp_ec_iva)),
          'I/false', '5) per cassa verso un privato (nessuna partita IVA): immediata');
SELECT is(pg_temp.fx_m(true, 'N', '   ', (SELECT iva_ord FROM tmp_ec_iva)),
          'I/false', '6) una partita IVA fatta di spazi non e'' una partita IVA');
SELECT is(pg_temp.fx_m(true, 'N', '01234567890', NULL),
          'NULL/false', '7) per cassa senza codice IVA: la natura non e'' nota, esigibilita NULL');
SELECT is(pg_temp.fx_m(true, 'N', '01234567890', (SELECT iva_ord FROM tmp_ec_iva)),
          'D/false', '8) per cassa, soggetto IVA, codice imponibile: differita');
SELECT is(pg_temp.fx_m(true, 'N', '01234567890', 999901),
          'I/false', '9) per cassa in inversione contabile (Natura N6.3): immediata');
SELECT is(pg_temp.fx_m(true, 'N', '01234567890', 999902),
          'I/false', '9-bis) D-12: per cassa, qualsiasi Natura (N3.1 non imponibile) va a immediata');
SELECT is(pg_temp.fx_m(NULL, 'N', '01234567890', (SELECT iva_ord FROM tmp_ec_iva)),
          'NULL/false', '10) regime non noto fuori dalla scissione: esigibilita NULL');

-- ============================================================
-- 11-17) La riga di fattura
-- ============================================================
UPDATE anagrafiche.soggetti SET split_payment = 'N'
 WHERE id = (SELECT cliente_soggetto_id FROM tmp_ec_iva);
SELECT pg_temp.fx_regime('RF01');
SELECT pg_temp.fx_riga(1, (SELECT iva_ord FROM tmp_ec_iva));

SELECT is(pg_temp.fx_coppia(1), 'I/false', '11) emittente RF01: la riga nasce immediata');

SELECT pg_temp.fx_regime('RF17');
SELECT pg_temp.fx_riga(2, (SELECT iva_ord FROM tmp_ec_iva));

SELECT is(pg_temp.fx_coppia(2), 'D/false',
          '12) emittente RF17, cliente con partita IVA: la riga nasce differita');

-- ⭐ La riga 1 e' nata 'I' quando l'emittente era ordinario. Con la vecchia
--   regola («solo il vuoto») sarebbe rimasta 'I' per sempre.
UPDATE vendite.fatture_righe SET descrizione = 'Riga 1 ritoccata'
 WHERE fattura_id = (SELECT fattura_id FROM tmp_ec) AND riga_nr = 1;

SELECT is(pg_temp.fx_coppia(1), 'D/false',
          '13) D-7: alla scrittura successiva la riga si riallinea al regime (derivazione pura)');

SELECT pg_temp.fx_riga(3, 999901);

SELECT is(pg_temp.fx_coppia(3), 'I/false',
          '14) emittente RF17: la riga in inversione contabile resta immediata');

-- ⭐ Il regime torna ordinario SENZA toccare le righe: le righe 1 e 2 restano
--   'D', stantie. Il ricalcolo del riepilogo deve riallinearle prima di
--   aggregarle, o la fattura direbbe due regimi.
SELECT pg_temp.fx_regime('RF01');
SELECT * FROM vendite.fn_ricalcola_riepilogo_iva_fattura((SELECT fattura_id FROM tmp_ec));

SELECT is(
  (SELECT string_agg(DISTINCT COALESCE(r.esigibilita::text, 'NULL'), ',')
     FROM vendite.fatture_righe r WHERE r.fattura_id = (SELECT fattura_id FROM tmp_ec))
  || '|' ||
  (SELECT string_agg(DISTINCT COALESCE(q.esigibilita::text, 'NULL'), ',')
     FROM vendite.fatture_riepiloghi_iva q WHERE q.fattura_id = (SELECT fattura_id FROM tmp_ec)),
  'I|I',
  '15) D-8: il ricalcolo riallinea righe e riepilogo al regime cambiato'
);

SELECT pg_temp.fx_riga(4, (SELECT iva_ord FROM tmp_ec_iva), 'D');

SELECT is(pg_temp.fx_coppia(4), 'I/false',
          '16) D-7: una D scritta a mano su un emittente ordinario non sopravvive');

-- ⭐ Lo snapshot dell'intestazione dice RF17, l'anagrafica viva RF01: la riga
--   segue la testata, perche' e' la testata che si stampa.
UPDATE vendite.fatture
   SET emittente_snapshot = jsonb_build_object('regime_fiscale_rf', 'RF17')
 WHERE id = (SELECT fattura_id FROM tmp_ec);
UPDATE vendite.fatture_righe SET descrizione = 'Riga 4 ritoccata'
 WHERE fattura_id = (SELECT fattura_id FROM tmp_ec) AND riga_nr = 4;

SELECT is(pg_temp.fx_coppia(4), 'D/false',
          '17) D-8: con lo snapshot la riga segue il regime CONGELATO (RF17), non quello vivo (RF01)');

-- ============================================================
-- 18-19) Gli altri chiamanti della regola
-- ============================================================
SELECT is(
  (SELECT COALESCE(a.esigibilita::text, 'NULL') FROM script.fn_esigibilita_iva_documento(
            (SELECT emittente_fiscale_id FROM tmp_ec), (SELECT billing_account_id FROM tmp_ec),
            (SELECT iva_ord FROM tmp_ec_iva)) a)
  || '|' ||
  (SELECT COALESCE(b.esigibilita::text, 'NULL') FROM script.fn_esigibilita_iva_documento(
            (SELECT emittente_fiscale_id FROM tmp_ec), (SELECT billing_account_id FROM tmp_ec),
            (SELECT iva_ord FROM tmp_ec_iva), 'RF17') b),
  'I|D',
  '18) la parte documento: col regime vivo (RF01) I, col regime passato (RF17) D'
);

SELECT pg_temp.fx_regime('RF17');
CREATE TEMP TABLE tmp_ec_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-ESIG-CASSA') AS articolo_id;
UPDATE catalogo.articoli SET iva_id = (SELECT iva_ord FROM tmp_ec_iva)
 WHERE id = (SELECT articolo_id FROM tmp_ec_art);

SELECT is(
  (SELECT COALESCE(r.esigibilita::text, 'NULL') || '/' || COALESCE(r.split_payment::text, 'NULL')
     FROM vendite.fn_resolve_iva_riga((SELECT articolo_id FROM tmp_ec_art), current_date, 100.00,
                                      NULL, NULL,
                                      (SELECT cliente_soggetto_id FROM tmp_ec_iva),
                                      (SELECT emittente_fiscale_id FROM tmp_ec)) r),
  'D/false',
  '19) il risolutore IVA risponde come la riga: RF17 e cliente con partita IVA -> D'
);

-- ============================================================
-- 20-25) Il regime dell'emittente e la sua conferma
-- ============================================================
SELECT throws_ok(
  format('UPDATE anagrafiche.emittenti_fiscali SET regime_fiscale_rf = %L WHERE id = %s',
         'RF99', (SELECT emittente_fiscale_id FROM tmp_ec)),
  '23503',
  NULL,
  '20) la FK rifiuta un regime fuori dal catalogo'
);

SELECT throws_ok(
  format('UPDATE anagrafiche.emittenti_fiscali SET regime_fiscale_rf = NULL WHERE id = %s',
         (SELECT emittente_fiscale_id FROM tmp_ec)),
  '23502',
  NULL,
  '21) il regime e'' obbligatorio'
);

UPDATE anagrafiche.emittenti_fiscali
   SET regime_fiscale_rf = 'RF01',
       regime_fiscale_confermato_il = now(),
       regime_fiscale_confermato_da = 'pgtap'
 WHERE id = (SELECT emittente_fiscale_id FROM tmp_ec);

SELECT is(
  (SELECT regime_fiscale_rf || '|' || regime_fiscale_confermato_da
     FROM anagrafiche.emittenti_fiscali WHERE id = (SELECT emittente_fiscale_id FROM tmp_ec)),
  'RF01|pgtap',
  '22) la conferma scritta insieme al regime nuovo resta'
);

CREATE TEMP TABLE tmp_ec_presidio AS
SELECT EXISTS (SELECT 1 FROM dbops.vw_emittenti_regime_non_confermato
                WHERE emittente_fiscale_id = (SELECT emittente_fiscale_id FROM tmp_ec)) AS confermato_visibile;

SELECT pg_temp.fx_regime('RF17');

SELECT is(
  (SELECT COALESCE(regime_fiscale_confermato_il::text, 'NULL') || '|'
          || COALESCE(regime_fiscale_confermato_da, 'NULL')
     FROM anagrafiche.emittenti_fiscali WHERE id = (SELECT emittente_fiscale_id FROM tmp_ec)),
  'NULL|NULL',
  '23) il regime che cambia senza una conferma nuova azzera la conferma'
);

SELECT is(
  (SELECT confermato_visibile FROM tmp_ec_presidio)::text || '|' ||
  EXISTS (SELECT 1 FROM dbops.vw_emittenti_regime_non_confermato
           WHERE emittente_fiscale_id = (SELECT emittente_fiscale_id FROM tmp_ec))::text,
  'false|true',
  '24) il presidio tace sull''emittente confermato e lo mostra quando la conferma si azzera'
);

SELECT throws_ok(
  format('UPDATE anagrafiche.emittenti_fiscali SET regime_fiscale_confermato_il = now() WHERE id = %s',
         (SELECT emittente_fiscale_id FROM tmp_ec)),
  '23514',
  NULL,
  '25) una conferma senza autore e'' rifiutata (chk_emittenti_fiscali_regime_conferma_coppia)'
);

SELECT * FROM finish();

ROLLBACK;
