-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: GUARDRAIL — coerenza fra config.sorgenti.area e il letterale `area`
--       scritto a mano dentro le 6 viste vw_dash_fatturazione_<sorgente>
-- Brief: brief-db-emissione-fattura-per-documento-sorgente (A7-ter, D-5)
-- ------------------------------------------------------------
-- Indice test (1..5):
--  1) tutte e 6 le viste proiettano un letterale `area` estraibile
--  2) ⭐ ogni letterale coincide con config.sorgenti.area della sua sorgente
--  3) nessuna area di config.sorgenti resta senza una vista che la proietti
--  4) config.sorgenti ha esattamente 6 aree valorizzate (le 6 documentali)
--  5) le sorgenti NON documentali hanno area NULL (scelta, non dimenticanza)
-- ------------------------------------------------------------
-- PERCHE' QUESTO FILE ESISTE, e perche' e' un guardrail e non una bonifica.
--
--   Fino al 2026-07-27 il vocabolario delle aree documentali NON esisteva come
--   dato: la stringa era scritta a mano dentro ciascuna delle 6 viste
--   per-sorgente ('PREVENTIVI'::varchar AS area, ...). Alla sesta occorrenza e'
--   stata estratta in config.sorgenti.area (decisione D-5), perche' serviva a
--   tradurre un gruppo fatturabile nel suo riferimento leggibile.
--
--   La bonifica vera — far leggere alle 6 viste la colonna invece del
--   letterale — e' stata RIMANDATA di proposito: sono sei CREATE OR REPLACE su
--   viste gia' in uso dalle dashboard, per ottenere un output IDENTICO. Rischio
--   reale, guadagno solo di igiene. Va fatta quando una di quelle viste verra'
--   toccata per un motivo suo, dove il costo marginale e' zero.
--
--   ⚠️ Nota onesta: la bonifica non eliminerebbe il letterale, lo SPOSTEREBBE
--   da 'PREVENTIVI' (area, vocabolario di display, modificabile) a 'PREVENTIVO'
--   (codice_interno, immutabile). E' comunque la regola di linee-guida-sql
--   §6d — confrontare contro la chiave stabile — ma non e' il salto da
--   "hardcoded" a "non hardcoded".
--
--   Nel frattempo il rischio concreto e' la DIVERGENZA: qualcuno cambia l'area
--   in un posto e non nell'altro, e il riferimento leggibile dei gruppi
--   fatturabili smette di risolvere IN SILENZIO (il join non trova nulla e il
--   codice del documento sparisce dall'elenco, sostituito dal fallback).
--   Questo test non impedisce la divergenza: la INTERCETTA. E' il 90% del
--   valore con lo 0% del rischio.
--
-- ⚠️ Il test legge le DEFINIZIONI (pg_get_viewdef), non i dati: e' quindi
--    indipendente dal contenuto del DB e non puo' passare "per fortuna" perche'
--    una vista e' vuota.
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

SELECT plan(5);

-- Mappa vista -> sorgente. E' l'unica cosa hardcoded qui, ed e' esattamente
-- l'asserzione che il test vuole fare: "questa vista rappresenta questa
-- sorgente". Una settima vista non coperta va aggiunta a questa lista.
CREATE TEMP TABLE tmp_area_map (vista text, codice_interno text);
INSERT INTO tmp_area_map (vista, codice_interno) VALUES
  ('vw_dash_fatturazione_preventivi', 'PREVENTIVO'),
  ('vw_dash_fatturazione_ordini',     'ORDINE_VENDITA'),
  ('vw_dash_fatturazione_contratti',  'CONTRATTO'),
  ('vw_dash_fatturazione_ddt',        'DDT_VENDITA'),
  ('vw_dash_fatturazione_offerte',    'OFFERTA_COMMERCIALE'),
  ('vw_dash_fatturazione_commesse',   'COMMESSA');

-- Letterale estratto dalla definizione di ciascuna vista.
CREATE TEMP TABLE tmp_area_letterali AS
SELECT
  m.vista,
  m.codice_interno,
  substring(
      pg_get_viewdef(('vendite.' || m.vista)::regclass)
      from '''([A-Z_]+)''::character varying AS area'
  ) AS area_letterale,
  (SELECT s.area FROM config.sorgenti s WHERE s.codice_interno = m.codice_interno) AS area_config
FROM tmp_area_map m;

-- ============================================================
-- TEST 1: il pattern regge su tutte e 6. Se una vista cambiasse forma
--   (es. l'area diventasse una colonna calcolata), l'estrazione tornerebbe
--   NULL e il test lo direbbe invece di far passare il confronto a vuoto.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM tmp_area_letterali WHERE area_letterale IS NOT NULL),
  6,
  '1) tutte e 6 le viste proiettano un letterale area estraibile'
);

-- ============================================================
-- TEST 2 ⭐ IL CUORE DEL GUARDRAIL.
--   Se qualcuno cambia l'area in config.sorgenti e non nella vista (o
--   viceversa), qui diventa rosso. Senza questo test la divergenza si
--   manifesterebbe solo come "il numero del documento non compare piu'
--   nell'elenco dei gruppi", senza indicare la causa.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM tmp_area_letterali
    WHERE area_letterale IS DISTINCT FROM area_config),
  0,
  '2) ogni letterale area delle 6 viste coincide con config.sorgenti.area'
);

-- ============================================================
-- TEST 3: il contrario. Un'area valorizzata in config.sorgenti ma che
--   nessuna vista proietta significa un riferimento leggibile che non
--   risolvera' mai — un gruppo che mostrera' sempre il fallback.
-- ============================================================
SELECT is(
  ARRAY(
    SELECT s.codice_interno::text
      FROM config.sorgenti s
     WHERE s.area IS NOT NULL
       AND NOT EXISTS (
           SELECT 1 FROM tmp_area_letterali l
            WHERE l.codice_interno = s.codice_interno::text)
     ORDER BY s.codice_interno
  ),
  ARRAY[]::text[],
  '3) nessuna area di config.sorgenti resta senza vista che la proietti'
);

-- ============================================================
-- TEST 4: il seed. Sei sorgenti documentali, non di piu' e non di meno.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM config.sorgenti WHERE area IS NOT NULL),
  6,
  '4) config.sorgenti ha esattamente 6 aree valorizzate'
);

-- ============================================================
-- TEST 5: l'implicazione inversa del test 3 — nessuna sorgente FUORI dalla
--   mappa ha un'area. Se qualcuno valorizzasse l'area di ATTIVITA, FATTURA o
--   di una sorgente _RIGA "per completezza", il riferimento leggibile
--   cercherebbe un documento che non esiste e il gruppo mostrerebbe sempre il
--   fallback, senza che nulla lo segnali.
--
--   ⚠️ Formulato come "le aree valorizzate sono ESATTAMENTE quelle mappate" e
--   NON come lista delle sorgenti senza area: config.sorgenti contiene piu'
--   righe di quelle del seed CSV — le cinque *_RIGA con scope ROW_VALIDATOR
--   arrivano da 20260225-44 e sono validatori di riga, non documenti. Elencare
--   il complemento renderebbe il test fragile a ogni nuova sorgente, per giunta
--   fallendo su qualcosa che non c'entra con l'area.
-- ============================================================
SELECT is(
  ARRAY(
    SELECT s.codice_interno::text FROM config.sorgenti s
     WHERE s.area IS NOT NULL ORDER BY s.codice_interno
  ),
  ARRAY(SELECT m.codice_interno FROM tmp_area_map m ORDER BY m.codice_interno),
  '5) le aree valorizzate sono esattamente quelle delle 6 sorgenti mappate'
);

SELECT * FROM finish();
ROLLBACK;
