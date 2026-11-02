-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: Pulizia config.sorgenti — scope + trigger polimorfo + RIGA
-- ------------------------------------------------------------
-- Indice test (1..9):
--  1) Colonna scope presente su config.sorgenti
--  2) Constraint chk_sorgenti_scope attivo
--  3) scope NOT NULL su tutti i record
--  4) Sorgenti PUSH_COMMESSA: 5 record attivi
--  5) Sorgenti PIPELINE_MARKER: 2 record attivi
--  6) Sorgenti ROW_VALIDATOR: le SEI sorgenti di riga sono attive (D-L1-f)
--  7) Sorgente POST_INVOICE: FATTURA attiva
--  8) Trigger polimorfo rimosso da attivita_fatturabili
--  9) Nessuna sorgente porta piu' il marchio meta.archived
--
-- ⚠️ Rev 2026-09-15 (brief-db-magazzino-lotto-1-terreno-vuoto, D-L1-f). I test
--   6 e 9 pinnavano lo stato OPPOSTO: cinque *_RIGA «archiviate», attivo=false
--   e meta.archived=true. Quello stato era un UPDATE a mano su dbdev del
--   2026-02-25 che nessun changeSet registrava: su un DB da zero le cinque
--   righe non esistevano affatto, e questo file era in baseline-rossi-ci come
--   ASSERZIONE dal primo giorno — un ricordo di una macchina pinnato come
--   test. Il Lotto 1 le mette nel CSV di sorgenti ATTIVE e senza marchio
--   (piu' RESO_VENDITA_RIGA): config.sorgenti dice CHE COSA puo' essere
--   nominato come sorgente — sei tabelle di riga che esistono — non chi lo
--   nomina oggi; il guard tipizzato pretende attivo=true. Il file tiene il
--   nome storico (la pulizia dello scope resta il suo oggetto: test 1-5, 7, 8).
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

SELECT plan(9);

-- ============================================================
-- 1) Colonna scope presente su config.sorgenti
-- ============================================================
SELECT has_column(
  'config', 'sorgenti', 'scope',
  'Colonna scope presente su config.sorgenti'
);

-- ============================================================
-- 2) Constraint chk_sorgenti_scope attivo
-- ============================================================
SELECT col_has_check(
  'config', 'sorgenti', 'scope',
  'Check constraint su colonna scope'
);

-- ============================================================
-- 3) scope NOT NULL su tutti i record
-- ============================================================
SELECT col_not_null(
  'config', 'sorgenti', 'scope',
  'Colonna scope e` NOT NULL'
);

-- ============================================================
-- 4) Sorgenti PUSH_COMMESSA: 5 record attivi
-- ============================================================
SELECT ok(
  (
    SELECT count(*) = 5
    FROM config.sorgenti s
    WHERE s.scope = 'PUSH_COMMESSA'
      AND s.attivo IS TRUE
  ),
  'PUSH_COMMESSA: 5 sorgenti attive (PREVENTIVO, CONTRATTO, ORDINE_VENDITA, DDT_VENDITA, ATTIVITA_CONSUMI)'
);

-- ============================================================
-- 5) Sorgenti PIPELINE_MARKER: 2 record attivi
-- ============================================================
SELECT ok(
  (
    SELECT count(*) = 2
    FROM config.sorgenti s
    WHERE s.scope = 'PIPELINE_MARKER'
      AND s.attivo IS TRUE
  ),
  'PIPELINE_MARKER: 2 sorgenti attive (ATTIVITA, COMMESSA)'
);

-- ============================================================
-- 6) Sorgenti ROW_VALIDATOR: le sei sorgenti di riga sono attive (D-L1-f)
-- ============================================================
-- Per NOME e non per conteggio: un conteggio resta vero anche se una riga
-- sparisce e un'altra entra. L'insieme e' il contratto del CSV di sorgenti.
SELECT is(
  (
    SELECT string_agg(s.codice_interno, ',' ORDER BY s.id)
    FROM config.sorgenti s
    WHERE s.scope = 'ROW_VALIDATOR'
      AND s.attivo IS TRUE
  ),
  'PREVENTIVO_RIGA,CONTRATTO_RIGA,ORDINE_VENDITA_RIGA,DDT_VENDITA_RIGA,FATTURA_RIGA,RESO_VENDITA_RIGA',
  'ROW_VALIDATOR: le sei sorgenti di riga sono ATTIVE — il catalogo dice che cosa puo'' essere nominato (D-L1-f)'
);

-- ============================================================
-- 7) Sorgente POST_INVOICE: FATTURA attiva
-- ============================================================
SELECT ok(
  (
    SELECT count(*) = 1
    FROM config.sorgenti s
    WHERE s.scope = 'POST_INVOICE'
      AND s.codice = 'FATTURA'
      AND s.attivo IS TRUE
  ),
  'POST_INVOICE: FATTURA attiva'
);

-- ============================================================
-- 8) Trigger polimorfo rimosso da attivita_fatturabili
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM pg_trigger t
    WHERE t.tgrelid = 'vendite.attivita_fatturabili'::regclass
      AND t.tgname = 'trg_attivita_fatturabili_a10_guard_fonte_ins_upd'
  ),
  'Trigger polimorfo trg_attivita_fatturabili_a10_guard_fonte_ins_upd rimosso'
);

-- ============================================================
-- 9) Nessuna sorgente porta piu' il marchio meta.archived
-- ============================================================
-- Il marchio {"archived": true, "archived_reason": "…commessa-v2"} parlava di UN
-- consumatore, non del catalogo: e' uscito con D-L1-f. Su tutte le sorgenti,
-- non solo ROW_VALIDATOR: un marchio del genere non ha una sede legittima.
SELECT is(
  (
    SELECT count(*)::int
    FROM config.sorgenti s
    WHERE (s.meta->>'archived') IS NOT NULL
  ),
  0,
  'Nessuna sorgente porta meta.archived: l''archiviazione a mano del 2026-02-25 non e'' piu'' nel catalogo'
);

-- ============================================================
SELECT * FROM finish();
ROLLBACK;
