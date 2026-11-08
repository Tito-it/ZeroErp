-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: guard sorgente polimorfa MODELLO B (chiave unica testuale) +
--       normalizzazione della chiave in vendite.fn_link_commessa_sorgente
--       (brief-db-guard-sorgente-polimorfa, migrations 20260718-15..19).
--
--       Convenzione (config/manual/sorgenti.md §Convenzione chiave sorgente):
--       sorgente_uid TEXT = id::text per i tipi a key_selector='id',
--       uuid testuale per i tipi a key_selector='uid'.
--
--  ⚠️ rev 2026-11-07 (brief-db-sorgente-documento-e-riga giro C.2): il guard
--  testuale resta montato solo su pratiche.pratiche_sorgenti (lo ritira il lotto
--  P). vendite.commesse_sorgenti e' passata alle colonne tipizzate col guard
--  unico: i casi d'INSERT del guard testuale (7-11, 19-21) si scrivono su una
--  pratica costruita; i casi della porta del link (12-16, 22-24) restano e
--  rileggono la chiave in sorgente_id.
--
--  ⚠️ rev 2026-11-08 (brief-db-sorgente-documento-e-riga giro P.1): anche
--  pratiche.pratiche_sorgenti e' passata alle colonne tipizzate col guard unico,
--  e il guard testuale, rimasto senza montaggi, si ritira (20261108-87). Escono i
--  casi d'INSERT del guard (vecchi 7-11) e le forme canoniche della chiave
--  testuale (vecchi 19-21): con le colonne tipizzate non hanno piu' oggetto, e la
--  chiave sbagliata la rifiuta il guard unico (vendite/test-sorgente-commesse-sorgenti-v1,
--  pratiche/test-sorgente-pratiche-sorgenti-v1). Restano la porta del link, che
--  riceve ancora la chiave in testo e la normalizza, e i censimenti. Il nome del
--  file resta: lo conoscono la baseline e la storia del cantiere.
--
-- Indice test (1..16):
--   1)  riferimenti minimi disponibili (BA + tipi COMMESSA/PREVENTIVO/ORDINE)
--   2)  esiste script.trgfn_guard_sorgente_polimorfa_tipizzata (modello A)
--   3)  NON esiste piu' il vecchio nome trgfn_guard_sorgente_polimorfa
--   4)  NON esiste piu' script.trgfn_guard_sorgente_polimorfa_testuale (ritirato)
--   5)  pratiche.pratiche_sorgenti monta il guard unico
--   6)  vendite.commesse_sorgenti monta il guard unico
--   7)  fn_link canonico id::text -> l'id in sorgente_id (readback)
--   8)  fn_link uuid per COMMESSA (target senza colonna uid) ->
--       P0001 (E_SORG_NORM_NON_RISOLTA)
--   9)  fn_link testo non-uuid per PREVENTIVO -> P0001 (E_SORG_FORMATO)
--   10) fn_link uuid inesistente per ORDINE_VENDITA (target CON colonna uid)
--       -> P0001 (E_SORG_NORM_NON_RISOLTA)
--   11) fn_link uuid di un ordine COSTRUITO (libero per costruzione) ->
--       normalizzato all'id, in sorgente_id
--   12) censimento commesse_sorgenti: 0 righe con la chiave nella colonna sbagliata
--   13) censimento pratiche_sorgenti: 0 righe con la chiave nella colonna sbagliata
--   --- Forma CANONICA della chiave passata alla porta (rev 2026-10-05, 20261005-25) ---
--   14) fn_link id con zeri davanti -> E_SORG_FORMATO
--   15) fn_link uuid MAIUSCOLO per PREVENTIVO -> E_SORG_FORMATO
--   16) fn_link id con spazi attorno -> il rubinetto li toglie e stocca la
--       forma canonica (normalizzazione dichiarata)
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

SELECT plan(16);

-- ============================================================
-- Fixture: riferimenti (BA con emittente fiscale) + tipi sorgente
--
-- rev 2026-09-23 (brief-db-fixture-che-costruiscono-giro-2, lotto 2).
--   Il BA si PESCAVA («il primo con utility, istanza ed emittente»): su un
--   database ricostruito (la CI) non ce n'e' nessuno e il file moriva alla
--   prima commessa (p_billing_account_id NULL). E il test 16 pescava «un
--   ordine reale libero», con skip se non c'era: da zero saltava SEMPRE.
--   Ora il cliente viene da dbops.fn_pgtap_crea_mondo_cliente (con il
--   contesto aperto riusa l'azienda di chi agisce, e il BA e' legato a quel
--   emittente), e l'ordine del test 16 si costruisce: e' libero per
--   costruzione, lo skip sparisce. ⛔ Cio' che il builder scrive si legge in
--   un'istruzione SEPARATA.
-- ============================================================
CREATE TEMP TABLE tmp_guard_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('guard sorgente polimorfa');

CREATE TEMP TABLE tmp_guard_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_guard_mondo) AS billing_account_id,
  (SELECT utility_id FROM tmp_guard_mondo) AS utility_id,
  (SELECT anagrafiche.fn_get_emittente_fiscale_id(m.billing_account_id)
     FROM tmp_guard_mondo m) AS emittente_soggetto_ruolo_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA' AND s.attivo LIMIT 1)       AS src_commessa,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo LIMIT 1)     AS src_preventivo,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA' AND s.attivo LIMIT 1) AS src_ordine;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND utility_id IS NOT NULL
      AND emittente_soggetto_ruolo_id IS NOT NULL
      AND src_commessa IS NOT NULL
      AND src_preventivo IS NOT NULL
      AND src_ordine IS NOT NULL
   FROM tmp_guard_refs),
  '1) riferimenti minimi disponibili (BA + tipi COMMESSA/PREVENTIVO/ORDINE)'
);

-- ============================================================
-- 2..6) oggetti in posto: la sorella tipizzata, la testuale ritirata, il guard unico montato
-- ============================================================
SELECT has_function('script', 'trgfn_guard_sorgente_polimorfa_tipizzata',
  '2) esiste il guard modello A (tipizzata, ex trgfn_guard_sorgente_polimorfa)');

SELECT hasnt_function('script', 'trgfn_guard_sorgente_polimorfa',
  '3) il vecchio nome generico non esiste piu'' (rinomina 20260718-16)');

SELECT hasnt_function('script', 'trgfn_guard_sorgente_polimorfa_testuale',
  '4) il guard modello B (testuale) non esiste piu'' (ritirato, 20261108-87)');

-- ⚠️ Schema e nome da pg_proc + pg_namespace, non da regproc::text: il testo
--   di un regproc dipende dal search_path di chi guarda.
SELECT is(
  (SELECT n.nspname || '.' || p.proname
     FROM pg_trigger t
     JOIN pg_proc p      ON p.oid = t.tgfoid
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE t.tgrelid = 'pratiche.pratiche_sorgenti'::regclass
      AND t.tgname = 'trg_pratiche_sorgenti_a10_guard_sorgente_ins_upd'),
  'script.trgfn_guard_sorgente',
  '5) pratiche_sorgenti monta il guard unico');

-- ⚠️ Schema e nome da pg_proc + pg_namespace, non da regproc::text: il testo
--   di un regproc dipende dal search_path di chi guarda.
SELECT is(
  (SELECT n.nspname || '.' || p.proname
     FROM pg_trigger t
     JOIN pg_proc p      ON p.oid = t.tgfoid
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE t.tgrelid = 'vendite.commesse_sorgenti'::regclass
      AND t.tgname = 'trg_commesse_sorgenti_a10_guard_sorgente_ins_upd'),
  'script.trgfn_guard_sorgente',
  '6) commesse_sorgenti monta il guard unico, non il testuale');

-- ============================================================
-- Fixture: commessa host + 2 commesse "sorgente" (documenti reali per i
-- link a chiave id: usare commesse evita fixture documento pesanti)
-- ============================================================
CREATE TEMP TABLE tmp_guard_commesse AS
SELECT
  vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_guard_refs),
    p_utility_id => (SELECT utility_id FROM tmp_guard_refs),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa => 'NORMALE',
    p_competenza_dal => DATE '2026-07-01',
    p_competenza_al => DATE '2026-07-31',
    p_meta => jsonb_build_object('test_scope', 'pgtap_guard_sorgente_host'),
    p_force_new => true
  ) AS commessa_host,
  vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_guard_refs),
    p_utility_id => (SELECT utility_id FROM tmp_guard_refs),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa => 'NORMALE',
    p_competenza_dal => DATE '2026-07-01',
    p_competenza_al => DATE '2026-07-31',
    p_meta => jsonb_build_object('test_scope', 'pgtap_guard_sorgente_src1'),
    p_force_new => true
  ) AS commessa_src1,
  vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_guard_refs),
    p_utility_id => (SELECT utility_id FROM tmp_guard_refs),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa => 'NORMALE',
    p_competenza_dal => DATE '2026-07-01',
    p_competenza_al => DATE '2026-07-31',
    p_meta => jsonb_build_object('test_scope', 'pgtap_guard_sorgente_src2'),
    p_force_new => true
  ) AS commessa_src2;

-- ============================================================
-- 7) fn_link canonico id::text -> stocca com'e' (readback identico)
--     Due passi: la riga inserita dalla fn non e' visibile allo scan
--     della STESSA statement (visibilita' per command id).
-- ============================================================
CREATE TEMP TABLE tmp_guard_link12 AS
SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id => (SELECT commessa_host FROM tmp_guard_commesse),
  p_sorgente_tipo_id => (SELECT src_commessa FROM tmp_guard_refs),
  p_sorgente_chiave => (SELECT commessa_src2::text FROM tmp_guard_commesse),
  p_sorgente_riga => NULL,
  p_meta => '{}'::jsonb
) AS link_id;

SELECT is(
  (SELECT concat_ws('|', cs.sorgente_id, coalesce(cs.sorgente_uid::text, 'NULL'))
     FROM vendite.commesse_sorgenti cs
    WHERE cs.id = (SELECT link_id FROM tmp_guard_link12)),
  (SELECT commessa_src2::text || '|NULL' FROM tmp_guard_commesse),
  '7) fn_link canonico id::text -> l''id in sorgente_id, sorgente_uid vuota'
);

-- ============================================================
-- 8) fn_link uuid per COMMESSA: target vendite.commesse NON ha colonna uid
--     -> la traduzione non e' possibile, errore parlante (no crash)
-- ============================================================
SELECT throws_ok(
  format(
    $$SELECT vendite.fn_link_commessa_sorgente(%s, %s, %L, NULL, '{}'::jsonb)$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_commessa FROM tmp_guard_refs),
    gen_random_uuid()::text
  ),
  'P0001',
  NULL,
  '8) fn_link uuid per tipo id a target senza colonna uid -> E_SORG_NORM_NON_RISOLTA'
);

-- ============================================================
-- 9) fn_link testo non-uuid per PREVENTIVO -> E_SORG_FORMATO (il rubinetto
--     non fa pass-through di spazzatura)
-- ============================================================
SELECT throws_ok(
  format(
    $$SELECT vendite.fn_link_commessa_sorgente(%s, %s, %L, NULL, '{}'::jsonb)$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_preventivo FROM tmp_guard_refs),
    'A-' || substr(md5(clock_timestamp()::text), 1, 14)
  ),
  'P0001',
  NULL,
  '9) fn_link testo non-uuid per PREVENTIVO -> E_SORG_FORMATO'
);

-- ============================================================
-- 10) fn_link uuid inesistente per ORDINE_VENDITA (target CON colonna uid):
--     la traduzione parte ma non risolve -> E_SORG_NORM_NON_RISOLTA
-- ============================================================
SELECT throws_ok(
  format(
    $$SELECT vendite.fn_link_commessa_sorgente(%s, %s, %L, NULL, '{}'::jsonb)$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_ordine FROM tmp_guard_refs),
    gen_random_uuid()::text
  ),
  'P0001',
  NULL,
  '10) fn_link uuid inesistente per ORDINE_VENDITA -> E_SORG_NORM_NON_RISOLTA'
);

-- ============================================================
-- 11) fn_link con uuid di un ordine COSTRUITO (quindi non ancora
--     linkato) -> normalizzato a id::text (traduzione riuscita).
--     L'ordine e' del cliente del mondo, in DRAFT, sull'emittente di chi
--     agisce.
-- ============================================================
CREATE TEMP TABLE tmp_ordine_libero AS
WITH ins AS (
  INSERT INTO vendite.ordini (
      soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza
  )
  SELECT m.cliente_soggetto_ruolo_id, m.billing_account_id,
         script.fn_pgtap_emittente_operatore(),
         (SELECT so.id FROM config.stati_doc_ordini so
           WHERE so.codice_interno = 'DRAFT' AND so.attivo),
         (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1),
         DATE '2026-07-15', false
    FROM tmp_guard_mondo m
  RETURNING id, uid
)
SELECT id, uid FROM ins;

-- Due passi anche qui (visibilita' per command id).
CREATE TEMP TABLE tmp_guard_link16 AS
SELECT vendite.fn_link_commessa_sorgente(
    p_commessa_id => (SELECT commessa_host FROM tmp_guard_commesse),
    p_sorgente_tipo_id => (SELECT src_ordine FROM tmp_guard_refs),
    p_sorgente_chiave => (SELECT uid::text FROM tmp_ordine_libero),
    p_sorgente_riga => NULL,
    p_meta => '{}'::jsonb) AS link_id;

SELECT is(
    (SELECT concat_ws('|', cs.sorgente_id, coalesce(cs.sorgente_uid::text, 'NULL'))
       FROM vendite.commesse_sorgenti cs
      WHERE cs.id = (SELECT link_id FROM tmp_guard_link16)),
    (SELECT id::text || '|NULL' FROM tmp_ordine_libero),
    '11) fn_link uuid di un ordine costruito -> normalizzato all''id, in sorgente_id');

-- ============================================================
-- 12..13) censimento: tutte le righe vive rispettano la convenzione
--     (id-selector -> numerico; uid-selector -> uuid). Se questo test e'
--     rosso, PRIMA di applicare i trigger serve la pulizia manuale
--     (brief-db-guard-sorgente-polimorfa, Appendice A).
--     ⚠️ rev 2026-10-05 (20261005-25): «nella convenzione» vuol dire in FORMA
--     CANONICA, con gli stessi building block del guard e dei lettori. Prima
--     il censimento aveva la sua regex (btrim, maiuscole ammesse): una quarta
--     copia della regola, piu' larga di chi poi la chiave la cerca.
-- ============================================================
-- Dal giro C.2 la tabella ha le colonne tipizzate: la convenzione e' la
-- colonna giusta per il key_selector del tipo (la forma la tiene il CHECK).
SELECT is(
  (SELECT count(*)::int
     FROM vendite.commesse_sorgenti cs
     JOIN config.sorgenti s ON s.id = cs.sorgente_tipo_id
    WHERE (s.key_selector = 'id'  AND cs.sorgente_id IS NULL)
       OR (s.key_selector = 'uid' AND cs.sorgente_uid IS NULL)),
  0,
  '12) commesse_sorgenti: nessuna riga viva con la chiave nella colonna sbagliata'
);

-- Dal giro P.1 anche pratiche_sorgenti ha le colonne tipizzate.
SELECT is(
  (SELECT count(*)::int
     FROM pratiche.pratiche_sorgenti ps
     JOIN config.sorgenti s ON s.id = ps.sorgente_tipo_id
    WHERE (s.key_selector = 'id'  AND ps.sorgente_id IS NULL)
       OR (s.key_selector = 'uid' AND ps.sorgente_uid IS NULL)),
  0,
  '13) pratiche_sorgenti: nessuna riga viva con la chiave nella colonna sbagliata'
);


-- ============================================================
-- 14-16) La chiave passata alla porta si salva in FORMA CANONICA (rev 2026-10-05, 20261005-25)
--   Prima il guard controllava btrim(sorgente_uid) con regex larghe e salvava
--   il valore non ripulito: '007', ' 42 ' e un uuid maiuscolo passavano —
--   chiavi che esistono ma che nessun lettore (fn_stato_sorgente,
--   vw_pratica_doc_sorgente, lineage) ritrova mai. Ora la regola e' quella
--   con cui la chiave si cerca: script.fn_sorgente_chiave_id / _uuid.
--   Si asserisce il CODICE, non solo «solleva»: 21 e 23 prima sollevavano
--   gia', ma per E_SORG_NOT_FOUND — un rosso per il motivo sbagliato.
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.codice_errore_sorgente(p_sql text)
RETURNS text AS $fn$
-- ⚠️ `text` esplicito: e' il canale CONSTRAINT dell'eccezione, non una colonna.
DECLARE v_codice text;
BEGIN
  EXECUTE p_sql;
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_codice, ''), SQLSTATE);
END $fn$ LANGUAGE plpgsql;

SELECT is(
  pg_temp.codice_errore_sorgente(format(
    $$SELECT vendite.fn_link_commessa_sorgente(%s, %s, %L, NULL, '{}'::jsonb)$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_commessa FROM tmp_guard_refs),
    '0' || (SELECT commessa_src1::text FROM tmp_guard_commesse))),
  'E_SORG_FORMATO',
  '14) fn_link id con zeri davanti -> E_SORG_FORMATO'
);

SELECT is(
  pg_temp.codice_errore_sorgente(format(
    $$SELECT vendite.fn_link_commessa_sorgente(%s, %s, %L, NULL, '{}'::jsonb)$$,
    (SELECT commessa_host FROM tmp_guard_commesse),
    (SELECT src_preventivo FROM tmp_guard_refs),
    upper(gen_random_uuid()::text))),
  'E_SORG_FORMATO',
  '15) fn_link uuid MAIUSCOLO per PREVENTIVO -> E_SORG_FORMATO'
);

-- 16) Una terza commessa sorgente, libera per costruzione: gli spazi attorno
--     li toglie il rubinetto (btrim in testa, normalizzazione dichiarata), e
--     quello che arriva al guard e alla riga e' la forma canonica.
CREATE TEMP TABLE tmp_guard_src3 AS
SELECT vendite.fn_get_or_create_commessa(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_guard_refs),
    p_utility_id => (SELECT utility_id FROM tmp_guard_refs),
    p_tipo_commessa => 'AUTO',
    p_policy_fatturazione => 'DA_DOCUMENTO',
    p_fatturazione_immediata => false,
    p_priorita_operativa => 'NORMALE',
    p_competenza_dal => DATE '2026-07-01',
    p_competenza_al => DATE '2026-07-31',
    p_meta => jsonb_build_object('test_scope', 'pgtap_guard_sorgente_src3'),
    p_force_new => true
  ) AS commessa_src3;

-- Due passi (visibilita' per command id).
CREATE TEMP TABLE tmp_guard_link24 AS
SELECT vendite.fn_link_commessa_sorgente(
    p_commessa_id => (SELECT commessa_host FROM tmp_guard_commesse),
    p_sorgente_tipo_id => (SELECT src_commessa FROM tmp_guard_refs),
    p_sorgente_chiave => ' ' || (SELECT commessa_src3::text FROM tmp_guard_src3) || ' ',
    p_sorgente_riga => NULL,
    p_meta => '{}'::jsonb) AS link_id;

SELECT is(
  (SELECT cs.sorgente_id::text
     FROM vendite.commesse_sorgenti cs
    WHERE cs.id = (SELECT link_id FROM tmp_guard_link24)),
  (SELECT commessa_src3::text FROM tmp_guard_src3),
  '16) fn_link id con spazi attorno -> stoccato in forma canonica (il rubinetto normalizza)'
);

SELECT * FROM finish();
ROLLBACK;
