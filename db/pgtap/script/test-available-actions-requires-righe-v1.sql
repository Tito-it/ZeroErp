-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: "documento vuoto non avanza di stato" (brief 2026-07-16)
--   §1a capability righe-aware (meta.requires_righe -> enabled/reason)
--   §1b guard DDT: emissione con 0 righe -> E_DDT_EMISSIONE_SENZA_RIGHE
-- ------------------------------------------------------------
-- Indice test (1..15):
--  1-5)  seed: meta.requires_righe=true sulla transizione di avanzamento
--        dei 5 domini (preventivi/ordini/ddt/reso/contratti)
--  6)    il flag NON e' finito su altre transizioni (esattamente 1 per dominio)
--  7)    codice errore E_DDT_EMISSIONE_SENZA_RIGHE registrato
--  8-9)  DDT vuoto: azione 'emetti' presente ma enabled=false + reason
-- 10)    DDT vuoto: guard blocca DRAFT->EMESSO (E_DDT_EMISSIONE_SENZA_RIGHE)
-- 11-12) DDT con riga: azione 'emetti' enabled=true, reason NULL
-- 13-14) SOLO presenza righe (decisione Tid 2026-07-16): nessun guard di
--        emissione vincola il totale; il guard preventivo non filtra qta>0
-- 15)    simmetria: tutti i guard di avanzamento contano righe ATTIVE
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

SELECT plan(15);

-- ============================================================
-- 1-5) Seed: requires_righe sulla transizione di avanzamento
-- ============================================================
SELECT is(
  (SELECT (t.meta->>'requires_righe')::boolean
     FROM config.transizioni_stati_preventivi t
    WHERE t.meta->>'action_key' = 'emetti'),
  true, '1) preventivi: emetti -> requires_righe=true');

SELECT is(
  (SELECT (t.meta->>'requires_righe')::boolean
     FROM config.transizioni_stati_ordini t
    WHERE t.meta->>'action_key' = 'conferma'),
  true, '2) ordini: conferma -> requires_righe=true');

SELECT is(
  (SELECT (t.meta->>'requires_righe')::boolean
     FROM config.transizioni_stati_ddt t
    WHERE t.meta->>'action_key' = 'emetti'),
  true, '3) ddt: emetti -> requires_righe=true');

SELECT is(
  (SELECT (t.meta->>'requires_righe')::boolean
     FROM config.transizioni_stati_reso t
    WHERE t.meta->>'action_key' = 'conferma'),
  true, '4) reso: conferma -> requires_righe=true');

SELECT is(
  (SELECT (t.meta->>'requires_righe')::boolean
     FROM config.transizioni_stati_contratti t
    WHERE t.meta->>'action_key' = 'attiva'),
  true, '5) contratti: attiva -> requires_righe=true');

-- ============================================================
-- 6) Il flag e' solo sulla transizione di avanzamento (1 per dominio):
--    blinda contro un requires_righe copiato per errore altrove.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM (
      SELECT 1 FROM config.transizioni_stati_preventivi WHERE meta ? 'requires_righe'
      UNION ALL
      SELECT 1 FROM config.transizioni_stati_ordini     WHERE meta ? 'requires_righe'
      UNION ALL
      SELECT 1 FROM config.transizioni_stati_ddt        WHERE meta ? 'requires_righe'
      UNION ALL
      SELECT 1 FROM config.transizioni_stati_reso       WHERE meta ? 'requires_righe'
      UNION ALL
      SELECT 1 FROM config.transizioni_stati_contratti  WHERE meta ? 'requires_righe'
  ) q),
  5, '6) requires_righe presente su esattamente 1 transizione per dominio (5 totali)');

-- ============================================================
-- 7) Codice errore del nuovo guard DDT registrato
-- ============================================================
SELECT ok(
  EXISTS (SELECT 1 FROM config.messaggi_errore
           WHERE codice = 'E_DDT_EMISSIONE_SENZA_RIGHE'),
  '7) E_DDT_EMISSIONE_SENZA_RIGHE registrato in config.messaggi_errore');

-- ============================================================
-- Fixture: DDT in DRAFT senza righe (via ordine -> fn_genera_ddt_da_ordine
-- non usabile qui: genererebbe righe). Inserimento diretto minimale.
-- ============================================================
CREATE TEMP TABLE tmp_refs_rr AS
SELECT
  (SELECT id FROM config.stati_doc_ddt WHERE codice_interno='DRAFT'  AND attivo IS TRUE LIMIT 1) AS stato_draft_id,
  (SELECT id FROM config.stati_doc_ddt WHERE codice_interno='EMESSO' AND attivo IS TRUE LIMIT 1) AS stato_emesso_id,
  (SELECT d.id FROM vendite.ddt d
     JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
    WHERE s.codice_interno = 'DRAFT'
      AND NOT EXISTS (SELECT 1 FROM vendite.ddt_righe r
                       WHERE r.ddt_id = d.id AND r.attivo IS TRUE)
    LIMIT 1) AS ddt_vuoto_id,
  (SELECT d.id FROM vendite.ddt d
     JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
    WHERE s.codice_interno = 'DRAFT'
      AND EXISTS (SELECT 1 FROM vendite.ddt_righe r
                   WHERE r.ddt_id = d.id AND r.attivo IS TRUE)
    LIMIT 1) AS ddt_pieno_id;

-- ============================================================
-- 8-9) DDT vuoto: azione 'emetti' presente ma disabilitata + reason.
--      Data-dependent: skip se il DB dev non ha un DDT DRAFT vuoto.
-- ============================================================
SELECT CASE WHEN (SELECT ddt_vuoto_id FROM tmp_refs_rr) IS NULL
  THEN pass('8) SKIP: nessun DDT DRAFT vuoto disponibile')
  ELSE is(
    (SELECT (elem->>'enabled')::boolean
       FROM jsonb_array_elements(
              script.fn_available_actions_ddt((SELECT ddt_vuoto_id FROM tmp_refs_rr))
              ->'available_actions') elem
      WHERE elem->>'key' = 'emetti'),
    false, '8) DDT vuoto: azione emetti presente con enabled=false')
END;

SELECT CASE WHEN (SELECT ddt_vuoto_id FROM tmp_refs_rr) IS NULL
  THEN pass('9) SKIP: nessun DDT DRAFT vuoto disponibile')
  ELSE is(
    (SELECT elem->>'reason'
       FROM jsonb_array_elements(
              script.fn_available_actions_ddt((SELECT ddt_vuoto_id FROM tmp_refs_rr))
              ->'available_actions') elem
      WHERE elem->>'key' = 'emetti'),
    'DOCUMENTO_SENZA_RIGHE', '9) DDT vuoto: reason=DOCUMENTO_SENZA_RIGHE')
END;

-- ============================================================
-- 10) Guard §1b: DDT vuoto non si emette.
-- ============================================================
SELECT CASE WHEN (SELECT ddt_vuoto_id FROM tmp_refs_rr) IS NULL
  THEN pass('10) SKIP: nessun DDT DRAFT vuoto disponibile')
  ELSE throws_ok(
    format($$UPDATE vendite.ddt SET stato_doc_ddt_id = %s WHERE id = %s$$,
           (SELECT stato_emesso_id FROM tmp_refs_rr),
           (SELECT ddt_vuoto_id FROM tmp_refs_rr)),
    'P0001', NULL,
    '10) DDT vuoto: DRAFT->EMESSO bloccato dal guard')
END;

-- ============================================================
-- 11-12) DDT con almeno una riga attiva: azione abilitata, reason NULL.
-- ============================================================
-- 🔴 RIFORMULATO il 2026-08-18 — il test misurava troppo.
--   Asseriva `enabled = true`, cioe' «questo DDT e' emettibile». Ma
--   l'emittibilita' e' cresciuta dopo che il file e' stato scritto: oggi un
--   DDT DRAFT con righe risponde `CAUSALE_MANCANTE` (misurato su tutti quelli
--   in sviluppo), che e' CORRETTO e non c'entra niente col soggetto di questo
--   file.
--   ⚠️ Un test intitolato «requires_righe» che pretende l'abilitazione PIENA
--   diventa ostaggio di ogni regola futura sull'emissione: si rompe quando il
--   dominio si arricchisce, cioe' quando le cose vanno bene.
--   ⭐ Ora asserisce cio' che gli compete: un DDT CON righe non e' bloccato
--   PER MANCANZA DI RIGHE. Se e' bloccato per altro, e' affare di
--   test-fn-check-ddt-emittibile-v1.
SELECT CASE WHEN (SELECT ddt_pieno_id FROM tmp_refs_rr) IS NULL
  THEN pass('11) SKIP: nessun DDT DRAFT con righe disponibile')
  ELSE isnt(
    (SELECT elem->>'reason'
       FROM jsonb_array_elements(
              script.fn_available_actions_ddt((SELECT ddt_pieno_id FROM tmp_refs_rr))
              ->'available_actions') elem
      WHERE elem->>'key' = 'emetti'),
    'DOCUMENTO_SENZA_RIGHE',
    '11) DDT con righe: NON bloccato per mancanza di righe')
END;

SELECT CASE WHEN (SELECT ddt_pieno_id FROM tmp_refs_rr) IS NULL
  THEN pass('12) SKIP: nessun DDT DRAFT con righe disponibile')
  -- Stessa correzione del test 11: `reason IS NULL` significava «nessun
  -- ostacolo di NESSUN tipo», che questo file non ha titolo di pretendere.
  -- Qui si verifica che l'ostacolo, se c'e', sia dichiarato — cioe' che il
  -- documento non resti bloccato SENZA una ragione leggibile.
  ELSE ok(
    (SELECT (elem->>'enabled')::boolean
          OR (elem->>'reason') IS NOT NULL
       FROM jsonb_array_elements(
              script.fn_available_actions_ddt((SELECT ddt_pieno_id FROM tmp_refs_rr))
              ->'available_actions') elem
      WHERE elem->>'key' = 'emetti'),
    '12) DDT con righe: o e'' abilitato, o l''ostacolo ha una ragione dichiarata')
END;

-- ============================================================
-- 13-15) Regola "SOLO presenza di righe" (decisione Tid 2026-07-16):
--   un documento a totale zero deve poter essere emesso. Questi test
--   blindano la regola contro una re-introduzione futura del vincolo.
-- ============================================================

-- 13) Nessun guard di emissione deve piu' SOLLEVARE un errore sul totale.
--     PREV_TOTALE_NON_POSITIVO resta registrato in config.messaggi_errore
--     (lookup con storia) ma non deve essere sollevato da funzioni vive.
--     NB: si cerca il LITERAL QUOTATO ('PREV_TOTALE_NON_POSITIVO'), non il
--     nome nudo: prosrc include anche i commenti, e le funzioni citano il
--     codice a testo per documentarne la rimozione.
SELECT is(
  (SELECT count(*)::int
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname IN ('vendite', 'script')
      AND p.prosrc LIKE '%''PREV_TOTALE_NON_POSITIVO''%'),
  0, '13) nessuna funzione viva solleva PREV_TOTALE_NON_POSITIVO (totale zero emettibile)');

-- 14) Il guard preventivo non filtra piu' quantita > 0: conta la sola
--     presenza di righe attive (una riga a qta 0 e' comunque una riga).
--     Si cerca il predicato con alias (pr.quantita > 0), che compare solo
--     nel codice: il commento della fn cita "quantita > 0" senza alias.
SELECT ok(
  (SELECT p.prosrc NOT LIKE '%pr.quantita > 0%'
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_cambia_stato_preventivo'),
  '14) fn_cambia_stato_preventivo non filtra pr.quantita > 0 (solo presenza righe)');

-- 15) Simmetria: il guard ordini conta le righe ATTIVE come tutti gli altri.
SELECT ok(
  (SELECT p.prosrc LIKE '%r.attivo IS TRUE%'
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'trgfn_ordini_guard_transizione'),
  '15) trgfn_ordini_guard_transizione filtra r.attivo IS TRUE (simmetria domini)');

SELECT * FROM finish();
ROLLBACK;
