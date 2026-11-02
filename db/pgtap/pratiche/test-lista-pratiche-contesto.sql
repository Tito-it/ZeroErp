-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: lente canonica per contesto (D1, analisi-pratiche-workflow-v2).
--       pratiche.fn_lista_pratiche_per_contesto: tre lenti mutuamente
--       alternative (ruolo / istanza / interne), bucket contesto
--       calcolato (RUOLO/ISTANZA/SOGGETTO/INTERNA), guard parametri.
--
-- Indice test:
-- 0) Precondizioni (provisioning + verifica)
-- 1) Setup: tipo prestazione + 4 pratiche (RUOLO, ISTANZA, SOGGETTO, INTERNA)
-- 2) Lente ruolo: ritorna la pratica del ruolo con bucket RUOLO (skip senza dati)
-- 3) Lente istanza: ritorna la pratica dell'istanza con bucket ISTANZA (skip senza dati)
-- 4) Lente interne: include la INTERNA, esclude le pratiche con soggetto
-- 5) Nessuna lente: tutte le pratiche di test presenti con bucket corretti
-- 6) Guard: due lenti insieme -> errore (mutua esclusivita')
-- 7) Guard: emittente NULL -> errore
-- 8) Cleanup
-- ------------------------------------------------------------

-- ⚠️ Transazione, e non e' una formalita'. Il cleanup di questo file sta in
--   coda: col runner vero (pg_prove gira con ON_ERROR_STOP) un fallimento a
--   meta' non ci arriva mai, e i dati di prova restano nel database a rompere
--   la corsa successiva — che vede un rosso non suo.
--   Brief: brief-db-pgtap-runner-rls-baseline §15.3.
BEGIN;

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file diventerebbe verde per sottrazione. Nel DB ce ne sono 365.
--   IMMEDIATE li riporta a scattare a fine di OGNI istruzione — cioe' esatta-
--   mente come si comportavano prima, quando il file girava in autocommit e
--   ogni istruzione era una transazione a se'. Messa in testa e non in coda
--   apposta: in coda scatterebbero tutti insieme DOPO il cleanup, su righe
--   ormai cancellate, e fallirebbero per un motivo che non riguarda il test.
--   Brief: brief-db-pgtap-runner-rls-baseline §17.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA', 'BOZZA', 'Bozza', true) ON CONFLICT (codice_interno) DO NOTHING;
INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true) ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_lc_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA') AS st_bozza,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id;

-- Contesti coerenti: ruolo (con il suo soggetto) e istanza (con il suo
-- soggetto), da righe reali — il guard contesto verifica l'appartenenza.
CREATE TEMP TABLE tmp_lc_ruolo AS
SELECT sr.id AS ruolo_id, sr.soggetto_id
  FROM anagrafiche.soggetti_ruoli sr
 ORDER BY sr.id
 LIMIT 1;

CREATE TEMP TABLE tmp_lc_istanza AS
SELECT iu.id AS istanza_id, iu.soggetto_id
  FROM anagrafiche.istanze_utilities iu
 ORDER BY iu.id
 LIMIT 1;

CREATE TEMP TABLE tmp_lc_sogg AS
SELECT (SELECT id FROM anagrafiche.soggetti ORDER BY id LIMIT 1) AS soggetto_id;

SELECT ok(
    (SELECT emittente_id IS NOT NULL
        AND st_bozza IS NOT NULL
        AND priorita_id IS NOT NULL
       FROM tmp_lc_refs)
    AND (SELECT soggetto_id IS NOT NULL FROM tmp_lc_sogg),
    '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup: tipo prestazione + 4 pratiche di contesto
-- =========================================================
CREATE TEMP TABLE tmp_lc_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_LC', 'TEST_LC', 'Tipo test lente contesto', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

-- Pratica RUOLO (solo se esiste un ruolo nel DB di test)
CREATE TEMP TABLE tmp_lc_p_ruolo AS WITH ins AS (
  INSERT INTO pratiche.pratiche (
      emittente_fiscale_id, tipo_prestazione_id, soggetto_id, soggetto_ruolo_id,
      stato_id, priorita_id, descrizione
  )
  SELECT
      (SELECT emittente_id FROM tmp_lc_refs),
      (SELECT tp_id FROM tmp_lc_tp),
      r.soggetto_id,
      r.ruolo_id,
      (SELECT st_bozza FROM tmp_lc_refs),
      (SELECT priorita_id FROM tmp_lc_refs),
      'test lente: pratica del ruolo'
    FROM tmp_lc_ruolo r
   WHERE r.ruolo_id IS NOT NULL
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- Pratica ISTANZA (solo se esiste un'istanza nel DB di test)
CREATE TEMP TABLE tmp_lc_p_istanza AS WITH ins AS (
  INSERT INTO pratiche.pratiche (
      emittente_fiscale_id, tipo_prestazione_id, soggetto_id, istanza_utility_id,
      stato_id, priorita_id, descrizione
  )
  SELECT
      (SELECT emittente_id FROM tmp_lc_refs),
      (SELECT tp_id FROM tmp_lc_tp),
      i.soggetto_id,
      i.istanza_id,
      (SELECT st_bozza FROM tmp_lc_refs),
      (SELECT priorita_id FROM tmp_lc_refs),
      'test lente: pratica dell''istanza'
    FROM tmp_lc_istanza i
   WHERE i.istanza_id IS NOT NULL
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- Pratica SOGGETTO (solo soggetto, senza ruolo ne' istanza)
CREATE TEMP TABLE tmp_lc_p_sogg AS WITH ins AS (
  INSERT INTO pratiche.pratiche (
      emittente_fiscale_id, tipo_prestazione_id, soggetto_id,
      stato_id, priorita_id, descrizione
  )
  VALUES (
      (SELECT emittente_id FROM tmp_lc_refs),
      (SELECT tp_id FROM tmp_lc_tp),
      (SELECT soggetto_id FROM tmp_lc_sogg),
      (SELECT st_bozza FROM tmp_lc_refs),
      (SELECT priorita_id FROM tmp_lc_refs),
      'test lente: pratica solo soggetto'
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

-- Pratica INTERNA (tutti i campi di contesto NULL)
CREATE TEMP TABLE tmp_lc_p_interna AS WITH ins AS (
  INSERT INTO pratiche.pratiche (
      emittente_fiscale_id, tipo_prestazione_id,
      stato_id, priorita_id, descrizione
  )
  VALUES (
      (SELECT emittente_id FROM tmp_lc_refs),
      (SELECT tp_id FROM tmp_lc_tp),
      (SELECT st_bozza FROM tmp_lc_refs),
      (SELECT priorita_id FROM tmp_lc_refs),
      'test lente: pratica interna'
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT ok(
    (SELECT pratica_id IS NOT NULL FROM tmp_lc_p_interna)
    AND (SELECT pratica_id IS NOT NULL FROM tmp_lc_p_sogg),
    '1. Setup completato: pratiche interna e solo-soggetto create'
);

-- =========================================================
-- 2) Lente ruolo: solo la pratica del ruolo, bucket RUOLO
-- =========================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lc_p_ruolo) THEN
    skip('2. Nessun soggetto con ruolo nel DB di test: lente ruolo non verificabile', 1)
  ELSE
    ok(
      (SELECT EXISTS (
         SELECT 1
           FROM pratiche.fn_lista_pratiche_per_contesto(
                  (SELECT emittente_id FROM tmp_lc_refs),
                  p_soggetto_ruolo_id := (SELECT ruolo_id FROM tmp_lc_ruolo)
                ) l
          WHERE l.pratica_id = (SELECT pratica_id FROM tmp_lc_p_ruolo)
            AND l.contesto = 'RUOLO'
       ))
      AND NOT EXISTS (
         SELECT 1
           FROM pratiche.fn_lista_pratiche_per_contesto(
                  (SELECT emittente_id FROM tmp_lc_refs),
                  p_soggetto_ruolo_id := (SELECT ruolo_id FROM tmp_lc_ruolo)
                ) l
          WHERE l.pratica_id IN (
                  (SELECT pratica_id FROM tmp_lc_p_sogg),
                  (SELECT pratica_id FROM tmp_lc_p_interna))
       ),
      '2. Lente ruolo: include la pratica del ruolo (bucket RUOLO), esclude le altre'
    )
END;

-- =========================================================
-- 3) Lente istanza: solo la pratica dell'istanza, bucket ISTANZA
-- =========================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_lc_p_istanza) THEN
    skip('3. Nessuna istanza utility nel DB di test: lente istanza non verificabile', 1)
  ELSE
    ok(
      (SELECT EXISTS (
         SELECT 1
           FROM pratiche.fn_lista_pratiche_per_contesto(
                  (SELECT emittente_id FROM tmp_lc_refs),
                  p_istanza_utility_id := (SELECT istanza_id FROM tmp_lc_istanza)
                ) l
          WHERE l.pratica_id = (SELECT pratica_id FROM tmp_lc_p_istanza)
            AND l.contesto = 'ISTANZA'
       ))
      AND NOT EXISTS (
         SELECT 1
           FROM pratiche.fn_lista_pratiche_per_contesto(
                  (SELECT emittente_id FROM tmp_lc_refs),
                  p_istanza_utility_id := (SELECT istanza_id FROM tmp_lc_istanza)
                ) l
          WHERE l.pratica_id IN (
                  (SELECT pratica_id FROM tmp_lc_p_sogg),
                  (SELECT pratica_id FROM tmp_lc_p_interna))
       ),
      '3. Lente istanza: include la pratica dell''istanza (bucket ISTANZA), esclude le altre'
    )
END;

-- =========================================================
-- 4) Lente interne: include la INTERNA, esclude chi ha soggetto
-- =========================================================
SELECT ok(
    (SELECT EXISTS (
       SELECT 1
         FROM pratiche.fn_lista_pratiche_per_contesto(
                (SELECT emittente_id FROM tmp_lc_refs),
                p_solo_interne := true
              ) l
        WHERE l.pratica_id = (SELECT pratica_id FROM tmp_lc_p_interna)
          AND l.contesto = 'INTERNA'
     ))
    AND NOT EXISTS (
       SELECT 1
         FROM pratiche.fn_lista_pratiche_per_contesto(
                (SELECT emittente_id FROM tmp_lc_refs),
                p_solo_interne := true
              ) l
        WHERE l.pratica_id = (SELECT pratica_id FROM tmp_lc_p_sogg)
     ),
    '4. Lente interne: include la pratica interna (bucket INTERNA), esclude chi ha soggetto'
);

-- =========================================================
-- 5) Nessuna lente: tutte le pratiche di test con bucket corretti
-- =========================================================
SELECT is(
    (SELECT count(*)::integer
       FROM pratiche.fn_lista_pratiche_per_contesto(
              (SELECT emittente_id FROM tmp_lc_refs)
            ) l
       JOIN pratiche.pratiche p ON p.id = l.pratica_id
      WHERE p.tipo_prestazione_id = (SELECT tp_id FROM tmp_lc_tp)
        AND l.contesto = CASE
              WHEN p.soggetto_ruolo_id IS NOT NULL THEN 'RUOLO'
              WHEN p.istanza_utility_id IS NOT NULL THEN 'ISTANZA'
              WHEN p.soggetto_id IS NOT NULL THEN 'SOGGETTO'
              ELSE 'INTERNA'
            END),
    (SELECT count(*)::integer
       FROM pratiche.pratiche p
      WHERE p.tipo_prestazione_id = (SELECT tp_id FROM tmp_lc_tp)),
    '5. Nessuna lente: tutte le pratiche di test presenti con bucket coerente'
);

-- =========================================================
-- 6) Guard: due lenti insieme -> errore
-- =========================================================
SELECT throws_ok(
    format(
      'SELECT * FROM pratiche.fn_lista_pratiche_per_contesto(%s, p_soggetto_ruolo_id := 1, p_solo_interne := true)',
      (SELECT emittente_id FROM tmp_lc_refs)),
    NULL, NULL,
    '6. Guard: due lenti valorizzate insieme rifiutate (mutua esclusivita'')'
);

-- =========================================================
-- 7) Guard: emittente NULL -> errore
-- =========================================================
SELECT throws_ok(
    'SELECT * FROM pratiche.fn_lista_pratiche_per_contesto(NULL)',
    NULL, NULL,
    '7. Guard: emittente_fiscale_id NULL rifiutato'
);

-- =========================================================
-- 8) Cleanup (resiliente)
-- =========================================================
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_lc_tp)
);
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_lc_tp);
DELETE FROM pratiche.tipi_prestazione
WHERE id = (SELECT tp_id FROM tmp_lc_tp);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
