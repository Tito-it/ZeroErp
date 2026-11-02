-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2c): la tabella della famiglia viene dalla sorgente (config.fn_sorgente_tabella); la famiglia del reso e' RESO_VENDITA.
-- pgTAP test per Zero ERP
-- Test: la CHIAVE DEL CONTATORE e gli assi dichiarati
--       vendite.registri_fatturazione_progressivi (20260901-08)
--       vendite.famiglie_documento.colonna_serie  (20260901-09)
--       script.fn_check_registro_serie_ammessa    (20260901-10)
--       vendite.trgfn_..._guard_serie_ammessa     (20260901-11)
--       vendite.fn_get_next_progressivo           (20260901-07)
--       Piano: brief-db-registri-numerazione-chiave-del-contatore
-- ------------------------------------------------------------
-- Elenco test (plan 9):
-- 1) ⛔ La colonna `mese` non esiste piu'
-- 2) ⛔ ...e nemmeno l'UNIQUE ridondante che il presidio non vedeva
-- 3) ⭐ La chiave del secchio e' a TRE assi
-- 4) ⭐⭐ DERIVATO: ogni famiglia che dichiara una serie ha davvero quella colonna
-- 5) ⭐⭐ DERIVATO: ...e quella colonna sta nel vincolo di unicita' del numero
-- 6) ⭐⭐ DERIVATO: nessun registro di una famiglia senza serie ha un serie_default
-- 7) ⛔ Il guard rifiuta una serie su una famiglia che non la gestisce
-- 8) ⭐ ...e la lascia passare su una che la gestisce (il gemello positivo)
-- 9) ⭐ reset_policy = NESSUNA: il contatore NON riparte cambiando anno
--
-- Scopo:
--   ⭐ L'INVARIANTE: tutto cio' che discrimina il CONTATORE deve poter
--   discriminare anche il DOCUMENTO. Il contatore vive su una chiave, e ogni
--   combinazione e' un secchio che riparte da 1: se il documento non porta uno
--   di quegli assi nel proprio vincolo di unicita', il contatore gli consegna un
--   numero che per lui e' gia' usato.
--
--   ⛔ E i due versi NON sono simmetrici: contatore con un asse in piu' =
--   COLLISIONE; documento con un asse in piu' = innocuo, e' solo piu' specifico.
--   E' la regola che dice quale asse va dichiarato.
--
--   ⭐⭐ I TEST 4-5-6 SONO IL PRESIDIO CHE CONTA, e sono DERIVATI. Un test che
--   verificasse «resi non ha la serie» proverebbe l'oggi: il difetto non e' una
--   colonna mancante, e' che NESSUNO CONTROLLA che i documenti numerati sui
--   registri portino la chiave del contatore. E' cosi' che resi e commesse sono
--   entrati col trasloco senza che niente diventasse rosso.
--   ⇒ Qui i due elenchi si derivano — gli assi da vendite.famiglie_documento, le
--   colonne da pg_attribute e dai vincoli — e si confrontano. Una famiglia nuova
--   che entra sui registri senza la chiave completa fa rosso PRIMA del merge.
--
--   ⭐ IL TEST 8 SERVE QUANTO IL 7: senza il gemello positivo, un guard che
--   rifiutasse SEMPRE passerebbe il 7 esattamente come quello giusto.
--
-- ⚠️ COSA QUESTO FILE NON PROVA: che `commesse` sia sana. La commessa dichiara
--   `colonna_serie` NULL, quindi i test 4-5 non la guardano e il 6 la protegge.
--   ⭐ Dal 2026-09-02 non e' piu' scoperta: registro_id e anno sono COLONNE
--   (changeSet 20260902-07) e l'invariante ha il suo presidio in
--   db/pgtap/vendite/test-commessa-chiave-numerazione-v1, che confronta il
--   codice con gli assi dichiarati.
--   ⚠️ La sua unicita' resta pero' su UNA STRINGA (uq_commesse_codice), ed e'
--   voluto: il codice porta la sigla dell'emittente, quindi e' unico
--   GLOBALMENTE — piu' stretto della chiave per registro delle altre quattro.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

-- ============================================================
-- 1/2/3) ⛔ Il mese non c'e' piu', e la chiave e' a tre assi
-- ============================================================
SELECT hasnt_column(
    'vendite', 'registri_fatturazione_progressivi', 'mese',
    '1) La colonna `mese` non esiste piu'': era un asse del contatore che nessun documento portava');

SELECT is(
    (SELECT count(*)::int FROM pg_class WHERE relname = 'uq_registri_progressivi_scope'),
    0,
    '2) ...e nemmeno uq_registri_progressivi_scope, duplicato che vw_duplicate_indexes non vedeva');

SELECT is(
    (SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'uq_regprog_key'),
    'UNIQUE (registro_id, anno, serie)',
    '3) La chiave del secchio e'' a TRE assi');

-- ============================================================
-- 4/5/6) ⭐⭐ I tre controlli DERIVATI dell'invariante
-- ============================================================
-- ⭐ Nessun elenco a mano: le famiglie si leggono da famiglie_documento, le
--   colonne da pg_attribute. Una famiglia nuova entra nel test da sola.
SELECT is(
    (SELECT count(*)::int
       FROM vendite.famiglie_documento f
      WHERE f.colonna_serie IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM pg_attribute a
             WHERE a.attrelid = (SELECT t.relid FROM config.fn_sorgente_tabella(f.codice_interno) t)
               AND NOT a.attisdropped
               AND a.attname = f.colonna_serie)),
    0,
    '4) Ogni famiglia che DICHIARA una serie ha davvero quella colonna sul documento');

-- ⚠️ La colonna dichiarata deve stare nel vincolo che protegge il NUMERO, non
--   solo esistere: e' li' che la serie distingue due numeri uguali. Si guardano
--   gli indici UNIQUE che nominano la colonna del numero della famiglia.
SELECT is(
    (SELECT count(*)::int
       FROM vendite.famiglie_documento f
      WHERE f.colonna_serie IS NOT NULL
        AND NOT EXISTS (
            SELECT 1
              FROM pg_index x
              JOIN pg_class c ON c.oid = x.indrelid
             WHERE c.oid = (SELECT t.relid FROM config.fn_sorgente_tabella(f.codice_interno) t)
               AND x.indisunique
               AND pg_get_indexdef(x.indexrelid) ~ ('\m' || f.colonna_numero || '\M')
               AND pg_get_indexdef(x.indexrelid) ~ ('\m' || f.colonna_serie  || '\M'))),
    0,
    '5) ...e quella colonna sta nel vincolo di unicita'' del numero');

SELECT is(
    (SELECT count(*)::int
       FROM vendite.registri_fatturazione r
       JOIN vendite.famiglie_documento f ON f.codice_interno = r.famiglia_documento
      WHERE f.colonna_serie IS NULL
        AND COALESCE(btrim(r.serie_default), '') <> ''),
    0,
    '6) Nessun registro di una famiglia SENZA serie porta un serie_default');

-- ============================================================
-- 7/8) ⛔ Il guard, e il suo gemello positivo
-- ============================================================
-- ⚠️ La fixture nasce su una utility valorizzata: lo slot
--   (famiglia, emittente, utility) «per tutte le utility» e' gia' preso dal
--   provisioning, e quell'indice non filtra su `attivo`.
CREATE TEMP TABLE tmp_ass AS
SELECT r.emittente_soggetto_ruolo_id AS sr,
       (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1) AS utility_id
  FROM vendite.registri_fatturazione r
 WHERE r.emittente_soggetto_ruolo_id IS NOT NULL
 ORDER BY r.id
 LIMIT 1;

PREPARE ass_reso_con_serie AS
INSERT INTO vendite.registri_fatturazione
    (codice, descrizione, emittente_soggetto_ruolo_id, famiglia_documento, serie_default, utility_id)
SELECT 'ASS-RESO-KO', 'pgTAP assi dichiarati', t.sr, 'RESO_VENDITA', 'X1', t.utility_id FROM tmp_ass t;

SELECT throws_ok(
    'EXECUTE ass_reso_con_serie',
    'P0001',
    NULL,
    '7) Un registro RESO con una serie viene rifiutato: quella famiglia non la registra');

SELECT lives_ok(
    $$INSERT INTO vendite.registri_fatturazione
          (codice, descrizione, emittente_soggetto_ruolo_id, famiglia_documento, serie_default, utility_id)
      SELECT 'ASS-FATT-OK', 'pgTAP assi dichiarati', t.sr, 'FATTURA', 'ZQS', NULL FROM tmp_ass t$$,
    '8) ...e su FATTURA, che la serie la registra, la stessa scrittura passa');

-- ============================================================
-- 9) ⭐ reset_policy = NESSUNA: la numerazione non riparte
-- ============================================================
-- ⭐ Il contatore si fa girare dal MOTORE, non inserendo a mano una riga.
-- ⚠️ Verbo in un'istruzione SEPARATA dall'asserzione: la funzione scrive.
CREATE TEMP TABLE tmp_ass_reg AS
WITH ins AS (
  INSERT INTO vendite.registri_fatturazione
      (codice, descrizione, emittente_soggetto_ruolo_id, famiglia_documento,
       prefisso, lunghezza_numero, reset_policy, utility_id)
  SELECT 'ASS-CONT', 'pgTAP contatore continuo', t.sr, 'FATTURA', 'ZQC', 7, 'NESSUNA', NULL
    FROM tmp_ass t
  RETURNING id)
SELECT id AS registro_id FROM ins;

CREATE TEMP TABLE tmp_ass_num AS
SELECT vendite.fn_get_next_progressivo((SELECT registro_id FROM tmp_ass_reg),
                                       DATE '2101-06-15', NULL, '', NULL, 'FATTURA') AS n1,
       vendite.fn_get_next_progressivo((SELECT registro_id FROM tmp_ass_reg),
                                       DATE '2102-06-15', NULL, '', NULL, 'FATTURA') AS n2;

SELECT is(
    (SELECT n2 FROM tmp_ass_num),
    2::bigint,
    '9) Con reset_policy = NESSUNA il contatore NON riparte cambiando anno');

SELECT * FROM finish();

ROLLBACK;
