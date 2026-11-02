-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
--
-- Test: il framework FK-surrogata dei parametri dopo la rev del 2026-08-31
--       (changeSet 20260831-36 + seed DEFAULT_IVA in parameter_fk_surrogate.csv
--        e parameters.csv — decisione A, brief-db-default-iva-chiave-naturale)
--
-- ⛔ IL PUNTO DI QUESTO FILE, e vale la pena leggerlo prima dei casi.
--   La rev ALLARGA un cancello: la stringa vuota smette di essere un valore da
--   verificare e diventa «nessun valore». Un file che provasse SOLO questo
--   direbbe che il cancello si e' aperto, non che regge ancora — ed e' la forma
--   classica in cui un presidio si spegne senza che nessuno se ne accorga.
--   ⇒ Meta' dei casi qui sotto verificano che il RIFIUTO funziona come prima.
--
-- Elenco test (plan 9: la fixture + gli 8 casi):
--  1) la stringa vuota passa: e' la rev, ed e' cio' che rende parameters.csv
--     di nuovo scrivibile
--  2) ⭐ E IL CANCELLO REGGE: un codice inesistente su un pattern attivo e'
--     ancora RIFIUTATO — senza questo si sta allargando senza controllare
--  3) un codice esistente passa (il ramo felice non si e' rotto)
--  4) ⚠️ il BIANCO resta rifiutato: e' una decisione, non una dimenticanza
--  5) il dispatcher non solleva piu' riscrivendo DEFAULT_UTILITY com'e' oggi —
--     e' il migrate che si fermava
--  6) ⛔ ma solleva su DEFAULT_IVA con un codice IVA inesistente: e' cio' che
--     la riga di registry compra, e senza questo caso si starebbe provando il
--     rename e non il registry
--  7) DEFAULT_IVA punta a un codice_interno che esiste davvero
--  8) ⭐ il gemello negativo del rename: DEFAULT_IVA_ID non esiste piu' a
--     catalogo — un lettore rimasto indietro non fallisce, prende il ripiego
--
-- ⚠️ Il valore nuovo e' `22`, che e' un NUMERO: un lettore vecchio che facesse
--   int() non fallirebbe, otterrebbe l'id 22. Oggi non esiste in config.iva, ma
--   il modello lo ammette — ed e' per questo che il caso 8 non e' una
--   formalita': e' l'unica prova che nessun lettore vecchio e' sopravvissuto
--   lato database.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: scattano al COMMIT, e qui il COMMIT non arriva mai.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

-- ============================================================
-- Fixture: un codice IVA che ESISTE e uno che NON esiste
-- ============================================================
-- ⚠️ Il codice inesistente si COSTRUISCE invece di sceglierne uno «strano»:
--   un valore inventato a mano potrebbe esistere davvero su un altro database,
--   e il caso 2 diventerebbe verde per sbaglio proprio dove deve mordere.
CREATE TEMP TABLE tmp_pfs AS
SELECT (SELECT i.codice_interno FROM config.iva i
         WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)      AS iva_esistente,
       'PGTAP-' || md5(clock_timestamp()::text)             AS iva_inesistente;

SELECT ok(
  (SELECT iva_esistente IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM config.iva i
                       WHERE i.codice_interno = (SELECT iva_inesistente FROM tmp_pfs))
     FROM tmp_pfs),
  'fixture: un codice_interno IVA che esiste, e uno costruito che non esiste');

-- ============================================================
-- 1) La rev: la stringa vuota passa
-- ============================================================
-- ⭐ E' quello che rende parameters.csv di nuovo scrivibile. L'argomento sta
--   sul modello: default_value e overridden_value sono ENTRAMBE NOT NULL,
--   quindi il vuoto e' l'unica forma che «nessun valore» puo' assumere.
SELECT ok(
  script.fn_check_parameter_fk_surrogate('DEFAULT_UTILITY', ''),
  '1) la stringa vuota passa: su un parametro il vuoto E l assenza');

-- ============================================================
-- 2) ⭐ E IL CANCELLO REGGE ANCORA
-- ============================================================
-- ⛔ Il caso che distingue «ho allargato con criterio» da «ho spento un
--   presidio». Senza, il file direbbe solo che la porta si e' aperta.
SELECT ok(
  NOT script.fn_check_parameter_fk_surrogate('DEFAULT_IVA',
        (SELECT iva_inesistente FROM tmp_pfs)),
  '2) un codice inesistente su un pattern attivo e ancora RIFIUTATO');

-- ============================================================
-- 3) Il ramo felice non si e' rotto
-- ============================================================
SELECT ok(
  script.fn_check_parameter_fk_surrogate('DEFAULT_IVA',
        (SELECT iva_esistente FROM tmp_pfs)),
  '3) un codice_interno esistente passa');

-- ============================================================
-- 4) ⚠️ Il BIANCO resta rifiutato, ed e' una decisione
-- ============================================================
-- Un codice_interno non e' mai fatto di spazi: ' ' e' un refuso di battitura, e
-- questa check e' l'unica cosa che lo intercetta. Allargare a btrim() avrebbe
-- spento quel presidio in cambio di niente.
SELECT ok(
  NOT script.fn_check_parameter_fk_surrogate('DEFAULT_IVA', ' '),
  '4) il bianco NON e il vuoto: resta rifiutato');

-- ============================================================
-- 5) Il dispatcher: la riga che fermava il migrate ora si riscrive
-- ============================================================
-- ⚠️ Si riscrive il valore CON SE STESSO: e' esattamente cio' che fa il mirror
--   loadUpdateData quando si sveglia, ed e' li' che il migrate moriva.
SELECT lives_ok(
  $$UPDATE config.parameters SET default_value = default_value
     WHERE code = 'DEFAULT_UTILITY'$$,
  '5) riscrivere DEFAULT_UTILITY com e non solleva piu: e il migrate che si fermava');

-- ============================================================
-- 6) ⛔ MA SU UN VALORE SBAGLIATO IL DISPATCHER SOLLEVA
-- ============================================================
-- ⭐ E' cio' che la riga di registry COMPRA, ed e' il guadagno vero della voce —
--   piu' della chiave in se'. Prima nessuno verificava che quel 16 puntasse a
--   qualcosa. Senza questo caso si starebbe provando il rename, non il registry.
SELECT throws_ok(
  format($$UPDATE config.parameters SET default_value = %L
            WHERE code = 'DEFAULT_IVA'$$,
         (SELECT iva_inesistente FROM tmp_pfs)),
  'P0001',
  NULL::text,
  '6) DEFAULT_IVA con un codice IVA inesistente e RIFIUTATO dal dispatcher');

-- ============================================================
-- 7) Il seed punta a qualcosa che esiste
-- ============================================================
-- ⚠️ Struttura e non popolazione: il seed di 80_data e' contratto, non
--   fotografia. Se il valore del parametro non esistesse a catalogo, il
--   parametro mentirebbe — che e' esattamente il debito che questa voce chiude.
SELECT ok(
  EXISTS (SELECT 1 FROM config.parameters p
            JOIN config.iva i ON i.codice_interno = p.default_value
           WHERE p.code = 'DEFAULT_IVA'),
  '7) DEFAULT_IVA punta a un codice_interno che esiste davvero in config.iva');

-- ============================================================
-- 8) ⭐ IL GEMELLO NEGATIVO DEL RENAME
-- ============================================================
-- ⛔ Un rename che lascia indietro un lettore NON FALLISCE: quello cerca un
--   parametro che non c'e' piu' e prende il ripiego, in silenzio. Questo caso
--   presidia la meta' database del gemello; l'altra meta' — zero occorrenze di
--   DEFAULT_IVA_ID in backend/ — e' un grep, e sta nel brief.
SELECT ok(
  NOT EXISTS (SELECT 1 FROM config.parameters WHERE code = 'DEFAULT_IVA_ID'),
  '8) DEFAULT_IVA_ID non esiste piu a catalogo: nessun lettore vecchio serviti');

SELECT * FROM finish();

ROLLBACK;
