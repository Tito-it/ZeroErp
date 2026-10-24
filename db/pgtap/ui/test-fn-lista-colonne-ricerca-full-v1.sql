-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: ui.fn_lista_colonne_ricerca_full — in quali colonne l'utente corrente
--       puo' fare la ricerca libera — e i due building block da cui dipende,
--       ui.fn_lista_colonne_livello e ui.fn_veste_corrente.
--       (changeSet 20260923-11 … -15; brief-db-ricerca-full-colonne-permessi)
--
-- Elenco test (plan 20):
--   1) la funzione esiste con la firma (varchar)
--   2) ed e' STABLE
--   3) colonna sensibile SENZA grant: esclusa
--   4) colonna non sensibile senza grant: inclusa, col suo campo_sorgente
--   5) colonna con grant BLOCCATO: esclusa
--   6) colonna non ricercabile: esclusa
--   7) colonna disattiva: esclusa
--   8) colonna con campo_sorgente '' (la forma che scrive il loader): esclusa
--   9) colonna con campo_sorgente NULL: esclusa
--  10) ⭐ due grant: TUTTO dal profilo AD_HOC (priorita' 1) e BLOCCATO dal
--      PORTALE (priorita' 3, era 2 fino al 20260925-80) — vince il piu' SPECIFICO, non il piu'
--      restrittivo: inclusa. E' la regola del BB, non solo il suo ripiego
--  11) la colonna sensibile con grant TUTTO: inclusa
--  12) la stessa con grant LETTURA: inclusa (LETTURA spegne l'export, non la vista)
--  13) ⭐ stessa decisione del risolutore: fra le colonne ricercabili della
--      fixture, quelle che la ricerca usa sono esattamente quelle che
--      ui.fn_resolve_lista_config mostra
--  14) lista inesistente: E_UI_LISTA_NON_TROVATA, dalla frase
--  15) ui.fn_veste_corrente() con la GUC valida: la veste
--  16) ui.fn_veste_corrente() con un valore fuori dominio: NULL, senza eccezione
--  17) e con la GUC vuota: NULL
--  18) ⭐ la veste si legge dalla GUC: sotto CLIENTE_PORTALE il grant legato
--      all'identita' OPERATORE non vale, la sensibile esce
--  19) ⭐ senza utente in sessione: nessun grant, la sensibile esce …
--  20) … e la non sensibile resta (fail-closed solo dove conta)
--
-- Scopo:
--  - La lettura nasce su richiesta del team BE (2026-09-23): la ricerca libera
--    delle liste passa dal catalogo a runtime, e deve cercare solo nelle
--    colonne che l'utente puo' vedere. Il livello viene dallo stesso building
--    block del risolutore delle liste: il test 13 lo prova sulla fixture.
--
--  - ⚠️ Il caso si COSTRUISCE: al 2026-09-23 il seed non ha colonne
--    ricercabili e sensibili, ne' grant di colonna. Due profili nuovi
--    (AD_HOC e PORTALE) per l'operatore di contesto, e otto colonne di prova
--    su una lista a catalogo. Tutto nasce e muore nella transazione.
--
--  - I test 16-20 cambiano il contesto di sessione: stanno in coda, e il 18
--    lo ripristina prima del 19.
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE. Senza, un fallimento a meta' lascia colonne e grant di
--   prova nel catalogo, e rompe ogni lista nelle corse successive.
BEGIN;

-- ⚠️ 2. CONTESTO APPLICATIVO. La funzione legge utente e veste dalle GUC di
--   sessione: senza contesto non c'e' nessun utente, e nessun grant vale.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ 3. VINCOLI DIFFERITI. Ogni istruzione della fixture e' un'unita' completa.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(20);

-- ============================================================
-- Fixture 1: due profili a priorita' diversa per l'utente di contesto.
--   n=1  AD_HOC, legato alla sua identita' OPERATORE     -> priorita' 1
--   n=2  PORTALE, legato alla veste OPERATORE             -> priorita' 3
--        (2 fino al 20260925-80: D-3 di brief-db-pgtap-permessi-ereditati)
-- ⚠️ Il modello ammette UN binding per identita', UNO per veste e UNO per
--    unita' organizzativa (indici unici parziali): due profili alla STESSA
--    priorita' sotto una sola veste si avevano solo con PORTALE + REPARTO,
--    e dal 20260925-80 non si hanno piu' (REPARTO 2, PORTALE 3).
--    Il test 10 prova quindi l'altra meta' della regola — il piu'
--    specifico batte il piu' restrittivo — che e' quella che discrimina.
-- ⚠️ Stesso patto di test-fn-resolve-lista-config-contatore-colonne-nuove:
--    l'identita' dell'operatore di contesto e la veste OPERATORE non hanno
--    binding a catalogo (al 2026-09-23 il seed lega solo le tre vesti di
--    portale). Se un giorno li avessero, l'INSERT qui sotto e' un 23505
--    esplicito, non un verde a vuoto.
-- ============================================================
CREATE TEMP TABLE _t_profili AS
WITH ins AS (
    INSERT INTO config.profili_accesso (tipo, codice, descrizione, attivo)
    VALUES
      ('AD_HOC',
       '_PGTAP_RF_1_' || upper(substr(md5(clock_timestamp()::text || '1'), 1, 8)),
       'Profilo AD_HOC per la ricerca libera', TRUE),
      ('PORTALE',
       '_PGTAP_RF_2_' || upper(substr(md5(clock_timestamp()::text || '2'), 1, 8)),
       'Profilo PORTALE sulla veste OPERATORE per la ricerca libera', TRUE)
    RETURNING id, tipo
)
SELECT id AS profilo_id,
       CASE tipo WHEN 'AD_HOC' THEN 1 ELSE 2 END AS n
  FROM ins;

DO $lega$
BEGIN
    PERFORM config.fn_lega_profilo_identita(p.profilo_id, idg.id) FROM _t_profili p
 CROSS JOIN anagrafiche.identita_digitali idg
 WHERE p.n = 1
   AND idg.auth_user_id = NULLIF(current_setting('app.current_user_id', true), '')::integer
   AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
   AND idg.attivo;
END
$lega$;

INSERT INTO config.profili_accesso_bindings (profilo_accesso_id, ruolo_applicativo, attivo)
SELECT p.profilo_id, 'OPERATORE'::config.ruolo_applicativo, TRUE
  FROM _t_profili p
 WHERE p.n = 2;

-- ============================================================
-- Fixture 2: una lista a catalogo con un campo_sorgente vero.
-- ⚠️ `campo_sorgente` NON si inventa: il trigger a10 lo verifica contro la
--    vista della lista. Si riusa quello di una colonna gia' a catalogo (non
--    azione, non vuoto — la forma del guard). Il codice e' nuovo, ed e' il
--    codice a identificare la colonna.
-- ⭐ ORDER BY esplicito: un LIMIT 1 senza ordinamento scommette.
-- ============================================================
CREATE TEMP TABLE _t_ctx AS
SELECT ld.codice                                                         AS lista_codice,
       ld.id                                                             AS lista_id,
       NULLIF(current_setting('app.current_user_id', true), '')::integer AS auth_user_id,
       (SELECT lc.campo_sorgente
          FROM ui.lista_colonna lc
         WHERE lc.lista_id = ld.id
           AND lc.attivo
           AND lc.tipo_colonna <> 'azione'
           AND COALESCE(btrim(lc.campo_sorgente), '') <> ''
         ORDER BY lc.id
         LIMIT 1)                                                        AS campo_reale
  FROM ui.lista_definizione ld
 WHERE ld.attivo
   AND EXISTS (SELECT 1
                 FROM ui.lista_colonna lc
                WHERE lc.lista_id = ld.id
                  AND lc.attivo
                  AND lc.tipo_colonna <> 'azione'
                  AND COALESCE(btrim(lc.campo_sorgente), '') <> '')
 ORDER BY ld.id
 LIMIT 1;

-- Le otto colonne. (codice, campo_sorgente, ricercabile_full, sensibile, attivo)
INSERT INTO ui.lista_colonna (
    id, lista_id, codice, etichetta, campo_sorgente, tipo_colonna, tipo_dato,
    ordine_default, allineamento, ordinabile, ricercabile_full, sensibile,
    esportabile, attivo, larghezza_default, user_insert)
SELECT v.id, c.lista_id, v.codice, 'Prova ricerca libera',
       CASE v.sorgente WHEN 'reale' THEN c.campo_reale
                       WHEN 'vuota' THEN ''
                       ELSE NULL END,
       'informazione', 'string',
       9900 + (v.id - 900100), 'left', false, v.ricercabile, v.sensibile,
       true, v.attivo, 80, 'pgtap'
  FROM _t_ctx c
 CROSS JOIN (VALUES
   (900101, 'zz_rf_sensibile',       'reale', true,  true,  true),
   (900102, 'zz_rf_bloccata',        'reale', true,  false, true),
   (900103, 'zz_rf_libera',          'reale', true,  false, true),
   (900104, 'zz_rf_non_ricercabile', 'reale', false, false, true),
   (900105, 'zz_rf_spenta',          'reale', true,  false, false),
   (900106, 'zz_rf_sorgente_vuota',  'vuota', true,  false, true),
   (900107, 'zz_rf_sorgente_null',   'null',  true,  false, true),
   (900108, 'zz_rf_priorita',        'reale', true,  false, true)
 ) AS v(id, codice, sorgente, ricercabile, sensibile, attivo);

-- I grant: BLOCCATO sulla 102 (AD_HOC); sulla 108 TUTTO dall'AD_HOC e
-- BLOCCATO dal PORTALE.
INSERT INTO ui.lista_colonna_permesso (colonna_id, profilo_accesso_id, livello_accesso, user_insert)
SELECT g.colonna_id, p.profilo_id, g.livello::config.livello_accesso, 'pgtap'
  FROM (VALUES
    (900102, 1, 'BLOCCATO'),
    (900108, 1, 'TUTTO'),
    (900108, 2, 'BLOCCATO')
  ) AS g(colonna_id, n, livello)
  JOIN _t_profili p ON p.n = g.n;

-- La lettura sotto prova, ridotta ai codici della fixture.
CREATE OR REPLACE FUNCTION pg_temp.rf()
RETURNS SETOF text AS $$
  SELECT r.codice::text
    FROM ui.fn_lista_colonne_ricerca_full((SELECT lista_codice FROM _t_ctx)) r
   WHERE r.codice LIKE 'zz\_rf\_%';
$$ LANGUAGE sql;

-- ============================================================
-- 1-2) Contratto
-- ============================================================
SELECT has_function('ui', 'fn_lista_colonne_ricerca_full', ARRAY['character varying'],
  '1) ui.fn_lista_colonne_ricerca_full(varchar) esiste');

SELECT volatility_is('ui', 'fn_lista_colonne_ricerca_full', ARRAY['character varying'], 'stable',
  '2) ed e'' STABLE');

-- ============================================================
-- 3-10) Chi entra e chi no
-- ============================================================
SELECT ok(NOT EXISTS (SELECT 1 FROM pg_temp.rf() c WHERE c = 'zz_rf_sensibile'),
  '3) colonna sensibile senza grant: esclusa');

SELECT is(
  (SELECT r.campo_sorgente::text
     FROM ui.fn_lista_colonne_ricerca_full((SELECT lista_codice FROM _t_ctx)) r
    WHERE r.codice = 'zz_rf_libera'),
  (SELECT campo_reale::text FROM _t_ctx),
  '4) colonna non sensibile senza grant: inclusa, col suo campo_sorgente');

SELECT ok(NOT EXISTS (SELECT 1 FROM pg_temp.rf() c WHERE c = 'zz_rf_bloccata'),
  '5) colonna con grant BLOCCATO: esclusa');

SELECT ok(NOT EXISTS (SELECT 1 FROM pg_temp.rf() c WHERE c = 'zz_rf_non_ricercabile'),
  '6) colonna non ricercabile: esclusa');

SELECT ok(NOT EXISTS (SELECT 1 FROM pg_temp.rf() c WHERE c = 'zz_rf_spenta'),
  '7) colonna disattiva: esclusa');

SELECT ok(NOT EXISTS (SELECT 1 FROM pg_temp.rf() c WHERE c = 'zz_rf_sorgente_vuota'),
  '8) campo_sorgente stringa vuota: esclusa');

SELECT ok(NOT EXISTS (SELECT 1 FROM pg_temp.rf() c WHERE c = 'zz_rf_sorgente_null'),
  '9) campo_sorgente NULL: esclusa');

SELECT ok(EXISTS (SELECT 1 FROM pg_temp.rf() c WHERE c = 'zz_rf_priorita'),
  '10) ⭐ TUTTO dall''AD_HOC contro BLOCCATO dal PORTALE: vince il piu'' specifico, inclusa');

-- ============================================================
-- 11-12) La sensibile col grant
-- ============================================================
INSERT INTO ui.lista_colonna_permesso (colonna_id, profilo_accesso_id, livello_accesso, user_insert)
SELECT 900101, p.profilo_id, 'TUTTO', 'pgtap'
  FROM _t_profili p
 WHERE p.n = 1;

SELECT ok(EXISTS (SELECT 1 FROM pg_temp.rf() c WHERE c = 'zz_rf_sensibile'),
  '11) colonna sensibile con grant TUTTO: inclusa');

UPDATE ui.lista_colonna_permesso
   SET livello_accesso = 'LETTURA'
 WHERE colonna_id = 900101;

SELECT ok(EXISTS (SELECT 1 FROM pg_temp.rf() c WHERE c = 'zz_rf_sensibile'),
  '12) la stessa con grant LETTURA: inclusa');

-- ============================================================
-- 13) ⭐ Stessa decisione del risolutore delle liste.
--     Fra le colonne della fixture ricercabili, attive e con un sorgente
--     (sensibile, bloccata, libera, priorita'), la ricerca usa esattamente
--     quelle che fn_resolve_lista_config mostra.
-- ============================================================
SELECT set_eq(
  'SELECT c FROM pg_temp.rf() c',
  $$SELECT e ->> 'codice'
      FROM jsonb_array_elements(
             ui.fn_resolve_lista_config(
               (SELECT lista_codice FROM _t_ctx),
               (SELECT auth_user_id FROM _t_ctx),
               NULL) -> 'colonne') e
     WHERE e ->> 'codice' IN ('zz_rf_sensibile', 'zz_rf_bloccata',
                              'zz_rf_libera',    'zz_rf_priorita')$$,
  '13) ⭐ la ricerca usa le colonne che la lista mostra, ne'' piu'' ne'' meno');

-- ============================================================
-- 14) Lista inesistente
-- ============================================================
SELECT throws_like(
  $$SELECT * FROM ui.fn_lista_colonne_ricerca_full('zz.pgtap.lista_che_non_esiste')$$,
  '%non trovata o non attiva%',
  '14) lista inesistente: E_UI_LISTA_NON_TROVATA');

-- ============================================================
-- 15-17) La veste dalla GUC (cambiano il contesto: in coda)
-- ============================================================
SELECT is(ui.fn_veste_corrente(), 'OPERATORE'::config.ruolo_applicativo,
  '15) ui.fn_veste_corrente(): la veste della GUC');

SELECT set_config('app.ruolo_applicativo', 'NON_UNA_VESTE', true);
SELECT is(ui.fn_veste_corrente(), NULL::config.ruolo_applicativo,
  '16) valore fuori dominio: NULL (= tutte le vesti), nessuna eccezione');

SELECT set_config('app.ruolo_applicativo', '', true);
SELECT is(ui.fn_veste_corrente(), NULL::config.ruolo_applicativo,
  '17) GUC vuota: NULL');

-- ============================================================
-- 18) ⭐ La veste decide quali grant valgono.
--     Il grant LETTURA sulla sensibile sta su un profilo legato all'identita'
--     OPERATORE: sotto CLIENTE_PORTALE non si applica.
-- ============================================================
SELECT set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
SELECT ok(NOT EXISTS (SELECT 1 FROM pg_temp.rf() c WHERE c = 'zz_rf_sensibile'),
  '18) ⭐ sotto un''altra veste il grant OPERATORE non vale: la sensibile esce');
SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true);

-- ============================================================
-- 19-20) ⭐ Senza utente in sessione (un command, un job)
-- ============================================================
SELECT set_config('app.current_user_id', '', true);

SELECT ok(NOT EXISTS (SELECT 1 FROM pg_temp.rf() c WHERE c = 'zz_rf_sensibile'),
  '19) ⭐ senza utente: nessun grant, la sensibile esce');

SELECT ok(EXISTS (SELECT 1 FROM pg_temp.rf() c WHERE c = 'zz_rf_libera'),
  '20) e la non sensibile resta: fail-closed solo dove conta');

SELECT * FROM finish();
ROLLBACK;
