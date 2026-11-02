-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: l'esigibilita' IVA col regime dell'emittente (IVA per cassa)
--   script.fn_esigibilita_iva (la regola) · script.fn_esigibilita_iva_documento ·
--   vendite.fn_esigibilita_iva_fattura · trigger di riga della fattura ·
--   vendite.fn_ricalcola_riepilogo_iva_fattura · vendite.fn_resolve_iva_riga ·
--   config.regimi_fiscali · emittenti_fiscali.regime_fiscale_rf (FK, NOT NULL,
--   conferma) · dbops.vw_emittenti_regime_non_confermato
-- Brief: brief-db-esigibilita-iva-per-cassa-emittente (D-1 ... D-11)
-- ChangeSet: 20261001-01 ... -17, 20261001-40 (D-12), 20261002-40 ... -42 (sezione 10)
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
-- 22-33) la conferma la scrive il database (sezione 10, 20261002-40/-41/-42):
-- 22) la INSERT non conferma, e il presidio mostra l'emittente
-- 23) un UPDATE che non nomina il regime non conferma
-- 24) ⭐ dichiarare il regime con lo stesso valore lo conferma (autore = GUC)
-- 25) il presidio tace dopo la dichiarazione
-- 26) cambiare il regime e' una dichiarazione, con l'autore nuovo
-- 27) un UPDATE che non nomina il regime non tocca la conferma data
-- 28) senza GUC l'autore e' CURRENT_USER
-- 29) ⛔ la data della conferma non si scrive da fuori
-- 30) ⛔ la forma di D-11 (regime + conferma insieme) e' rifiutata
-- 31) ⛔ una INSERT con la conferma e' rifiutata
-- 32) riscrivere le colonne uguali passa (il valore, non la menzione)
-- 33) il CHECK di coppia resta (struttura)
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: RLS attiva, come gira l'applicazione.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(34);

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
                                     iva_id, esigibilita, competenza_dal, competenza_al)
  SELECT (SELECT fattura_id FROM tmp_ec), p_nr, 'Riga ' || p_nr, 1, 100, p_iva, p_esig, script.fn_data_operativa(), script.fn_data_operativa()
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
     -- ⚠️ p_imponibile NULL (l'anteprima): dal 20261004-15 un importo e' rifiutato.
     FROM vendite.fn_resolve_iva_riga((SELECT articolo_id FROM tmp_ec_art), script.fn_data_operativa(), NULL,
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

-- ============================================================
-- 22-33) La conferma la scrive il database (sezione 10, 20261002-40/-41/-42)
-- ============================================================
-- ⭐ Un emittente NUOVO, non quello della fattura: quello e' l'azienda di chi
--   agisce, gia' esistente, e la sua conferma dipende dalla storia della
--   macchina. La riga nuova nasce da una INSERT, ed e' l'unico modo di avere
--   una conferma vuota (da fuori non si azzera).
CREATE TEMP TABLE tmp_rc AS
SELECT e.emittente_fiscale_id, e.soggetto_ruolo_id
  FROM dbops.fn_pgtap_crea_emittente() e;

CREATE OR REPLACE FUNCTION pg_temp.fx_conferma()
RETURNS text LANGUAGE sql AS $fx$
  SELECT ef.regime_fiscale_rf || '|'
         || COALESCE(ef.regime_fiscale_confermato_da, 'NULL') || '|'
         || CASE WHEN ef.regime_fiscale_confermato_il IS NULL THEN 'NULL'
                 WHEN ef.regime_fiscale_confermato_il = now() THEN 'ADESSO'
                 ELSE 'ALTRA_DATA' END
    FROM anagrafiche.emittenti_fiscali ef
   WHERE ef.id = (SELECT emittente_fiscale_id FROM tmp_rc);
$fx$;

CREATE OR REPLACE FUNCTION pg_temp.fx_nel_presidio()
RETURNS boolean LANGUAGE sql AS $fx$
  SELECT EXISTS (SELECT 1 FROM dbops.vw_emittenti_regime_non_confermato v
                  WHERE v.emittente_fiscale_id = (SELECT emittente_fiscale_id FROM tmp_rc));
$fx$;

SELECT is(
  pg_temp.fx_conferma() || '|' || pg_temp.fx_nel_presidio()::text,
  'RF01|NULL|NULL|true',
  '22) la INSERT non conferma: RF01 di default, nessuna conferma, e il presidio lo mostra'
);

UPDATE anagrafiche.emittenti_fiscali
   SET brand_meta = '{"pgtap": "regime"}'::jsonb
 WHERE id = (SELECT emittente_fiscale_id FROM tmp_rc);

SELECT is(
  pg_temp.fx_conferma(),
  'RF01|NULL|NULL',
  '23) un UPDATE che non nomina il regime non conferma'
);

-- ⭐ Lo STESSO valore: e' cosi' che l'operatore conferma un RF01 che nessuno
--   aveva dichiarato. L'autore viene dalla GUC, fissata qui per non dipendere
--   dal contesto.
SELECT set_config('app.jwt_user', 'pgtap.dichiarante', true);

UPDATE anagrafiche.emittenti_fiscali
   SET regime_fiscale_rf = 'RF01'
 WHERE id = (SELECT emittente_fiscale_id FROM tmp_rc);

SELECT is(
  pg_temp.fx_conferma(),
  'RF01|pgtap.dichiarante|ADESSO',
  '24) ⭐ dichiarare il regime con lo stesso valore lo conferma: data e autore li scrive il database'
);

SELECT is(
  pg_temp.fx_nel_presidio(),
  false,
  '25) il presidio tace sull''emittente dichiarato'
);

SELECT set_config('app.jwt_user', 'pgtap.altro', true);

UPDATE anagrafiche.emittenti_fiscali
   SET regime_fiscale_rf = 'RF17'
 WHERE id = (SELECT emittente_fiscale_id FROM tmp_rc);

SELECT is(
  pg_temp.fx_conferma(),
  'RF17|pgtap.altro|ADESSO',
  '26) cambiare il regime e'' una dichiarazione: la conferma passa a chi l''ha scritto'
);

SELECT set_config('app.jwt_user', 'pgtap.terzo', true);

UPDATE anagrafiche.emittenti_fiscali
   SET brand_meta = '{"pgtap": "regime-2"}'::jsonb
 WHERE id = (SELECT emittente_fiscale_id FROM tmp_rc);

SELECT is(
  pg_temp.fx_conferma(),
  'RF17|pgtap.altro|ADESSO',
  '27) un UPDATE che non nomina il regime non tocca la conferma data'
);

SELECT set_config('app.jwt_user', '', true);

UPDATE anagrafiche.emittenti_fiscali
   SET regime_fiscale_rf = 'RF01'
 WHERE id = (SELECT emittente_fiscale_id FROM tmp_rc);

SELECT is(
  pg_temp.fx_conferma(),
  'RF01|' || current_user || '|ADESSO',
  '28) senza la GUC app.jwt_user l''autore e'' il ruolo del database'
);

SELECT throws_like(
  format('UPDATE anagrafiche.emittenti_fiscali SET regime_fiscale_confermato_il = now() - interval ''1 day'' WHERE id = %s',
         (SELECT emittente_fiscale_id FROM tmp_rc)),
  '%la conferma del regime fiscale la scrive il database%',
  '29) ⛔ la data della conferma non si scrive da fuori (E_EMITTENTE_REGIME_CONFERMA_DERIVATA)'
);

-- La forma di D-11: regime e conferma nella stessa scrittura. Il guard a10
-- parla prima della derivazione a20, quindi vede i valori del chiamante.
SELECT throws_like(
  format('UPDATE anagrafiche.emittenti_fiscali SET regime_fiscale_rf = %L, '
         'regime_fiscale_confermato_il = now() - interval ''1 day'', '
         'regime_fiscale_confermato_da = %L WHERE id = %s',
         'RF17', 'pgtap.form', (SELECT emittente_fiscale_id FROM tmp_rc)),
  '%la conferma del regime fiscale la scrive il database%',
  '30) ⛔ la forma di D-11 (regime e conferma insieme) e'' rifiutata: si scrive solo il regime'
);

SELECT throws_like(
  format('INSERT INTO anagrafiche.emittenti_fiscali (soggetto_ruolo_id, codice, '
         'regime_fiscale_confermato_il, regime_fiscale_confermato_da) '
         'VALUES (%s, %L, now(), %L)',
         (SELECT soggetto_ruolo_id FROM tmp_rc), 'PGTAPRC', 'pgtap.form'),
  '%la conferma del regime fiscale la scrive il database%',
  '31) ⛔ una INSERT con la conferma e'' rifiutata: la creazione non conferma mai'
);

-- Il valore, non la menzione: un salvataggio che riscrive tutta la riga nomina
-- le due colonne con i valori che hanno gia'.
SELECT lives_ok(
  format('UPDATE anagrafiche.emittenti_fiscali '
         'SET regime_fiscale_confermato_il = regime_fiscale_confermato_il, '
         'regime_fiscale_confermato_da = regime_fiscale_confermato_da WHERE id = %s',
         (SELECT emittente_fiscale_id FROM tmp_rc)),
  '32) riscrivere le colonne di conferma con lo stesso valore passa'
);

-- ⚠️ Il guard ora parla prima del CHECK di coppia (23514), ma il CHECK
--   presidia le strade che i trigger non percorrono: lo si tiene con
--   un'asserzione sulla struttura.
SELECT is(
  (SELECT count(*)::integer FROM pg_catalog.pg_constraint c
    WHERE c.conrelid = 'anagrafiche.emittenti_fiscali'::regclass
      AND c.conname = 'chk_emittenti_fiscali_regime_conferma_coppia'
      AND c.contype = 'c'),
  1,
  '33) il CHECK di coppia della conferma resta'
);

SELECT * FROM finish();

ROLLBACK;
