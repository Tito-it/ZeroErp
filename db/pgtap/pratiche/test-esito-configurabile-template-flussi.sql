-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: esito configurabile sugli step di flusso (template_flussi).
--       Colonne modalita_esito (MANUALE/AUTOMATICO/CONTESTUALE/DOMINIO) +
--       esito_default; CHECK di dominio (20260617-01 + 20260702-15) e guard
--       parlante trg_template_flussi_a10_guard_modalita_esito_ins_upd
--       (20260617-02, esteso 20260702-16):
--         Inv1 = AUTOMATICO/CONTESTUALE => esito_default NOT NULL (494)
--         Inv2 = AUTOMATICO  => direzione INTERNA                 (495)
--         Inv3 = DOMINIO     => esito_default VIETATO             (505)
--         Inv4 = AUTOMATICO/CONTESTUALE => esito_default verdetto (506)
--       + regressione del guard esito al COMPLETATO (477) invariato.
--
-- Indice test:
-- 0)  Precondizioni (config data)
-- 1)  Setup: tipo prestazione + pratica
-- 2)  Inv1: AUTOMATICO + esito_default NULL -> errore (494)
-- 3)  Inv2: AUTOMATICO + direzione ENTRATA (esito_default valorizzato) -> errore (495)
-- 4)  OK: CONTESTUALE + ENTRATA + esito_default -> ammesso (CONTESTUALE libera direzione)
-- 5)  OK: MANUALE + esito_default NULL -> ammesso (default odierno)
-- 6)  OK: AUTOMATICO + INTERNA + esito_default -> ammesso
-- 7)  Inv2 su UPDATE: AUTOMATICO+INTERNA poi direzione->ENTRATA -> errore (495)
-- 8)  Dominio: modalita_esito non ammessa -> check_violation
-- 9)  Regressione: guard esito al COMPLETATO con esito NULL continua a bloccare
-- 10) Inv1 riformulata: DOMINIO + esito_default NULL -> ammesso (con la vecchia
--     Inv1 "<> MANUALE" sarebbe stato rifiutato)
-- 11) Inv3: DOMINIO + esito_default valorizzato -> errore (505)
-- 12) Inv4: AUTOMATICO + INTERNA + esito_default di ramo -> errore (506)
-- 13) Cleanup
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

SELECT plan(13);

-- =========================================================
-- 0) Precondizioni: provisioning config data (idempotente)
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA', 'BOZZA', 'Bozza', true)
ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.stati_flussi_pratiche (codice, codice_interno, descrizione, attivo)
VALUES
  ('DA_ESEGUIRE', 'DA_ESEGUIRE', 'Da eseguire', true),
  ('IN_CORSO', 'IN_CORSO', 'In corso', true),
  ('COMPLETATO', 'COMPLETATO', 'Completato', true)
ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true)
ON CONFLICT (codice_interno) DO NOTHING;

-- Esiti (FK di esito_default dal 20260701-02): POSITIVO verdetto, MERCE_PRESENTE
-- di ramo. is_verdetto ESPLICITO (default colonna false).
INSERT INTO config.esiti_flussi_pratiche (codice, codice_interno, descrizione, is_verdetto)
VALUES ('POSITIVO','POSITIVO','Esito positivo',true),
       ('MERCE_PRESENTE','MERCE_PRESENTE','Merce presente',false)
ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_ece_refs AS
SELECT
  script.fn_pgtap_emittente_operatore() AS emittente_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA') AS st_bozza,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'DA_ESEGUIRE') AS sf_da_eseguire,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'IN_CORSO') AS sf_in_corso,
  (SELECT id FROM config.stati_flussi_pratiche WHERE codice_interno = 'COMPLETATO') AS sf_completato,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id;

SELECT ok(
    (SELECT emittente_id IS NOT NULL
        AND st_bozza IS NOT NULL
        AND sf_da_eseguire IS NOT NULL
        AND sf_in_corso IS NOT NULL
        AND sf_completato IS NOT NULL
        AND priorita_id IS NOT NULL
       FROM tmp_ece_refs),
    '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Setup: tipo prestazione + pratica
-- =========================================================
CREATE TEMP TABLE tmp_ece_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_ECE', 'TEST_ECE', 'Tipo test esito configurabile', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

CREATE TEMP TABLE tmp_ece_pratica AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_ece_refs),
    (SELECT tp_id FROM tmp_ece_tp),
    (SELECT st_bozza FROM tmp_ece_refs),
    (SELECT priorita_id FROM tmp_ece_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT ok(
    (SELECT pratica_id IS NOT NULL FROM tmp_ece_pratica),
    '1. Setup completato: pratica creata'
);

-- =========================================================
-- 2) Inv1: AUTOMATICO + esito_default NULL -> errore parlante (494)
-- =========================================================
SELECT throws_ok(
  format($q$INSERT INTO pratiche.template_flussi
              (tipo_prestazione_id, codice, descrizione, sequenza, attivo, direzione, modalita_esito, esito_default)
            VALUES (%s, 'TF_ECE_AUTO_NOESITO', 'Auto senza esito', 10, true, 'INTERNA', 'AUTOMATICO', NULL)$q$,
    (SELECT tp_id FROM tmp_ece_tp)),
  NULL, NULL,
  '2. Inv1: AUTOMATICO con esito_default NULL e'' rifiutato (494)'
);

-- =========================================================
-- 3) Inv2: AUTOMATICO + direzione ENTRATA (esito_default valorizzato) -> errore (495)
-- =========================================================
SELECT throws_ok(
  format($q$INSERT INTO pratiche.template_flussi
              (tipo_prestazione_id, codice, descrizione, sequenza, attivo, direzione, modalita_esito, esito_default)
            VALUES (%s, 'TF_ECE_AUTO_ENTRATA', 'Auto su entrata', 20, true, 'ENTRATA', 'AUTOMATICO', 'POSITIVO')$q$,
    (SELECT tp_id FROM tmp_ece_tp)),
  NULL, NULL,
  '3. Inv2: AUTOMATICO su direzione ENTRATA e'' rifiutato (495)'
);

-- =========================================================
-- 4) OK: CONTESTUALE + ENTRATA + esito_default -> ammesso
-- =========================================================
SELECT lives_ok(
  format($q$INSERT INTO pratiche.template_flussi
              (tipo_prestazione_id, codice, descrizione, sequenza, attivo, direzione, modalita_esito, esito_default)
            VALUES (%s, 'TF_ECE_CONTEST_ENTRATA', 'Contestuale su entrata', 30, true, 'ENTRATA', 'CONTESTUALE', 'POSITIVO')$q$,
    (SELECT tp_id FROM tmp_ece_tp)),
  '4. CONTESTUALE su ENTRATA con esito_default e'' ammesso (CONTESTUALE libera dalla direzione)'
);

-- =========================================================
-- 5) OK: MANUALE + esito_default NULL -> ammesso (default odierno)
-- =========================================================
SELECT lives_ok(
  format($q$INSERT INTO pratiche.template_flussi
              (tipo_prestazione_id, codice, descrizione, sequenza, attivo, direzione, modalita_esito, esito_default)
            VALUES (%s, 'TF_ECE_MANUALE', 'Manuale', 40, true, 'ENTRATA', 'MANUALE', NULL)$q$,
    (SELECT tp_id FROM tmp_ece_tp)),
  '5. MANUALE con esito_default NULL e'' ammesso (comportamento odierno)'
);

-- =========================================================
-- 6) OK: AUTOMATICO + INTERNA + esito_default -> ammesso
-- =========================================================
SELECT lives_ok(
  format($q$INSERT INTO pratiche.template_flussi
              (tipo_prestazione_id, codice, descrizione, sequenza, attivo, direzione, modalita_esito, esito_default)
            VALUES (%s, 'TF_ECE_AUTO_INTERNA', 'Auto interna', 50, true, 'INTERNA', 'AUTOMATICO', 'POSITIVO')$q$,
    (SELECT tp_id FROM tmp_ece_tp)),
  '6. AUTOMATICO su INTERNA con esito_default e'' ammesso'
);

-- =========================================================
-- 7) Inv2 su UPDATE: spostare a ENTRATA un AUTOMATICO/INTERNA -> errore (495)
-- =========================================================
SELECT throws_ok(
  format($q$UPDATE pratiche.template_flussi
               SET direzione = 'ENTRATA'
             WHERE tipo_prestazione_id = %s AND codice = 'TF_ECE_AUTO_INTERNA'$q$,
    (SELECT tp_id FROM tmp_ece_tp)),
  NULL, NULL,
  '7. Inv2 su UPDATE: cambiare direzione a ENTRATA su un AUTOMATICO e'' rifiutato (495)'
);

-- =========================================================
-- 8) Dominio: modalita_esito non ammessa -> check_violation
--    esito_default valorizzato per non far scattare prima il guard Inv1
--    (il guard BEFORE precede la valutazione del CHECK di dominio).
-- =========================================================
SELECT throws_ok(
  format($q$INSERT INTO pratiche.template_flussi
              (tipo_prestazione_id, codice, descrizione, sequenza, attivo, direzione, modalita_esito, esito_default)
            VALUES (%s, 'TF_ECE_BADMODE', 'Modalita non valida', 60, true, 'INTERNA', 'PIPPO', 'POSITIVO')$q$,
    (SELECT tp_id FROM tmp_ece_tp)),
  '23514', NULL,
  '8. Dominio: modalita_esito fuori CHECK e'' rifiutato (check_violation)'
);

-- =========================================================
-- 9) Regressione: guard esito al COMPLETATO con esito NULL blocca ancora
-- =========================================================
-- Usa il template MANUALE (test 5). Percorso matrice DA_ESEGUIRE->IN_CORSO->COMPLETATO.
INSERT INTO pratiche.flussi (pratica_id, template_flusso_id, stato_id)
VALUES (
  (SELECT pratica_id FROM tmp_ece_pratica),
  (SELECT id FROM pratiche.template_flussi
     WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ece_tp) AND codice = 'TF_ECE_MANUALE'),
  (SELECT sf_da_eseguire FROM tmp_ece_refs)
);
UPDATE pratiche.flussi
   SET stato_id = (SELECT sf_in_corso FROM tmp_ece_refs)
 WHERE pratica_id = (SELECT pratica_id FROM tmp_ece_pratica)
   AND template_flusso_id = (SELECT id FROM pratiche.template_flussi
     WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ece_tp) AND codice = 'TF_ECE_MANUALE');

SELECT throws_ok(
  format($q$UPDATE pratiche.flussi
               SET stato_id = %s
             WHERE pratica_id = %s
               AND template_flusso_id = (SELECT id FROM pratiche.template_flussi
                     WHERE tipo_prestazione_id = %s AND codice = 'TF_ECE_MANUALE')$q$,
    (SELECT sf_completato FROM tmp_ece_refs),
    (SELECT pratica_id FROM tmp_ece_pratica),
    (SELECT tp_id FROM tmp_ece_tp)),
  NULL, NULL,
  '9. Regressione: COMPLETATO con esito NULL resta bloccato (guard esito invariato)'
);

-- =========================================================
-- 10) Inv1 riformulata: DOMINIO + esito_default NULL -> ammesso.
--     Test chiave della riformulazione (20260702-16): con la vecchia Inv1
--     "modalita <> MANUALE => default obbligatorio" questo INSERT falliva.
-- =========================================================
SELECT lives_ok(
  format($q$INSERT INTO pratiche.template_flussi
              (tipo_prestazione_id, codice, descrizione, sequenza, attivo, direzione, modalita_esito, esito_default)
            VALUES (%s, 'TF_ECE_DOMINIO', 'Esito calcolato dal dominio', 70, true, 'INTERNA', 'DOMINIO', NULL)$q$,
    (SELECT tp_id FROM tmp_ece_tp)),
  '10. Inv1 riformulata: DOMINIO senza esito_default e'' ammesso'
);

-- =========================================================
-- 11) Inv3: DOMINIO + esito_default valorizzato -> errore parlante (505)
-- =========================================================
SELECT throws_like(
  format($q$INSERT INTO pratiche.template_flussi
              (tipo_prestazione_id, codice, descrizione, sequenza, attivo, direzione, modalita_esito, esito_default)
            VALUES (%s, 'TF_ECE_DOM_DEFAULT', 'Dominio con default', 80, true, 'INTERNA', 'DOMINIO', 'POSITIVO')$q$,
    (SELECT tp_id FROM tmp_ece_tp)),
  '%non ammette esito_default%',
  '11. Inv3: DOMINIO con esito_default valorizzato e'' rifiutato (505)'
);

-- =========================================================
-- 12) Inv4: AUTOMATICO + INTERNA + esito_default di ramo (is_verdetto=false)
--     -> errore parlante (506). Dal 20260701-02 esito_default e' FK senza
--     vincolo di classe: Inv4 lo reintroduce data-driven.
-- =========================================================
SELECT throws_like(
  format($q$INSERT INTO pratiche.template_flussi
              (tipo_prestazione_id, codice, descrizione, sequenza, attivo, direzione, modalita_esito, esito_default)
            VALUES (%s, 'TF_ECE_AUTO_RAMO', 'Auto con default di ramo', 85, true, 'INTERNA', 'AUTOMATICO', 'MERCE_PRESENTE')$q$,
    (SELECT tp_id FROM tmp_ece_tp)),
  '%richiedono un verdetto%',
  '12. Inv4: AUTOMATICO con esito_default di ramo e'' rifiutato (506)'
);

-- =========================================================
-- 13) Cleanup (resiliente)
-- =========================================================
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ece_tp)
);
DELETE FROM pratiche.flussi
WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ece_tp)
);
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ece_tp);
DELETE FROM pratiche.template_flussi
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_ece_tp);
DELETE FROM pratiche.tipi_prestazione
WHERE id = (SELECT tp_id FROM tmp_ece_tp);

SELECT * FROM finish();

-- Il ROLLBACK e' la garanzia: comunque vada — verde, rosso, o morto a meta' —
-- questo file non lascia nulla dietro di se'. Le DELETE del cleanup restano
-- perche' dove sono un'asserzione devono girare davvero.
ROLLBACK;
