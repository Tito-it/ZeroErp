-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d/2e): chiavi del push e ambito degli indirizzi col codice della sorgente.
-- rev 2026-10-24 (brief-modello-documento-vendita §4-octies): il mondo si COSTRUISCE. Prima la fixture pescava «il primo BA con utility», l'articolo, l'unita' di misura, il tipo documento e «il primo stato commessa per id», e usava un uuid sintetico come sorgente (che il guard sulle sorgenti oggi respinge): su un database ricostruito moriva al test 3. Ora: commessa dal builder, un preventivo VERO come sorgente, le due righe dal builder dell'attivita' con la chiave del dominio (script.fn_segment_key). Il caso provato non cambia.
-- pgTAP test per Zero ERP
-- Test: drop uq_commesse_attivita_src_uid_partial
-- ------------------------------------------------------------
-- Indice test (1..4):
-- 1) Indice uq_commesse_attivita_src_uid_partial non esiste piu`
-- 2) Indice uq_commesse_attivita_commessa_segment esiste (constraint corretto rimasto)
-- 3) Smoke multi-riga: 2 commesse_attivita con stessa sorgente ma segment_key diversi → accettati
-- 4) uq_commesse_sorgenti_src_uid_ruolo ancora attivo (semantica 1-doc → 1-commessa ROOT)
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

SELECT plan(4);

-- ============================================================
-- Setup riferimenti minimi
-- ============================================================
-- La commessa e il documento sorgente si costruiscono (rev 2026-10-24): un
-- preventivo VERO, perche' la tabella verifica che la chiave della sorgente
-- esista (guard sorgente polimorfa, 2026-07-18).
CREATE TEMP TABLE tmp_commessa_srcuid AS
SELECT c.commessa_id AS id, c.billing_account_id
  FROM dbops.fn_pgtap_crea_commessa('drop uq src uid') c;

CREATE TEMP TABLE tmp_prev_srcuid AS
SELECT p.preventivo_uid FROM dbops.fn_pgtap_crea_preventivo('drop uq src uid') p;

-- ============================================================
-- TEST 1) Indice ridondante non esiste piu`
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = 'vendite'
      AND tablename  = 'commesse_attivita'
      AND indexname  = 'uq_commesse_attivita_src_uid_partial'
  ),
  'uq_commesse_attivita_src_uid_partial non esiste (drop eseguito)'
);

-- ============================================================
-- TEST 2) Indice corretto (commessa_id, segment_key) ancora presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = 'vendite'
      AND tablename  = 'commesse_attivita'
      AND indexname  = 'uq_commesse_attivita_commessa_segment'
  ),
  'uq_commesse_attivita_commessa_segment esiste (constraint corretto rimasto)'
);

-- ============================================================
-- TEST 3) Multi-riga: 2 righe con stessa sorgente ma segment_key diversi
-- Verifica che il drop abiliti il pattern 1 documento → N righe commessa.
-- ============================================================
-- (la commessa e' gia' costruita in testa, dal builder)

SELECT lives_ok(
  $$
    DO $righe$
    BEGIN
      PERFORM dbops.fn_pgtap_crea_commessa_attivita(
          p_commessa_id      => (SELECT id FROM tmp_commessa_srcuid),
          p_sorgente_codice  => 'PREVENTIVO',
          p_sorgente_uid     => (SELECT preventivo_uid::text FROM tmp_prev_srcuid),
          -- due righe dello stesso preventivo, distinte dall'etichetta della chiave
          p_chiave_etichetta => v.riga::text,
          p_stato_approvazione => 'BOZZA')
        FROM (VALUES (1), (2)) AS v(riga);
    END $righe$;
  $$,
  'Multi-riga: 2 righe con stessa sorgente_uid ma segment_key diversi → inserimento accettato'
);

DO $conta$
BEGIN
  IF (SELECT count(DISTINCT ca.segment_key) FROM vendite.commesse_attivita ca
       WHERE ca.commessa_id = (SELECT id FROM tmp_commessa_srcuid)
         AND vendite.fn_documento_uid_di_attivita(ca.sorgente_tipo_id, ca.segment_key) = (SELECT preventivo_uid::text FROM tmp_prev_srcuid)) <> 2 THEN
    RAISE EXCEPTION 'fixture: attese 2 righe con la stessa sorgente e due chiavi diverse';
  END IF;
END $conta$;

-- ============================================================
-- TEST 4) uq_commesse_sorgenti_src_uid_ruolo ancora attivo
-- Verifica che la semantica "1 documento → 1 commessa ROOT" sia preservata.
-- ============================================================
-- NOTA 2026-07-18 (brief-db-guard-sorgente-polimorfa): il guard sorgente
-- valida esistenza e formato della chiave, quindi la sorgente del test e' la
-- commessa REALE del fixture (tipo COMMESSA, l'id in sorgente_id) — non
-- piu' l'uuid sintetico, che il guard respingerebbe (E_SORG_NOT_FOUND).
SELECT throws_ok(
  $$
    WITH ids AS (SELECT id FROM tmp_commessa_srcuid),
         refs AS (SELECT s.id AS sorgente_tipo_id FROM config.sorgenti s
                   WHERE s.codice_interno = 'COMMESSA' AND s.attivo IS TRUE LIMIT 1)
    INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_id, ruolo_link)
    SELECT ids.id, refs.sorgente_tipo_id, ids.id, 'ROOT'
    FROM ids, refs
    UNION ALL
    SELECT ids.id, refs.sorgente_tipo_id, ids.id, 'ROOT'
    FROM ids, refs;
  $$,
  '23505',
  NULL,
  'uq_commesse_sorgenti_src_uid_ruolo ancora attivo: duplicato ROOT bloccato'
);

SELECT * FROM finish();
ROLLBACK;
