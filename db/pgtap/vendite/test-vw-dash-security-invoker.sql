-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test ANTI-REGRESSIONE — security_invoker sull'intera famiglia
-- vendite.vw_dash_* (dashboard fatturazione: due lenti + situazione aperta).
--
-- PERCHE': le viste vw_dash_* leggono le 4 tabelle documentali in RLS
-- (preventivi/ordini/offerte_commerciali/contratti). Owned da titodb, che e'
-- anche owner di quelle tabelle ed esente dalla RLS non-forced: senza
-- security_invoker=on la vista gira come DEFINER e BYPASSA lo scope emittente
-- (fix V-1, changeSet 20260706-15). Un CREATE OR REPLACE VIEW successivo che
-- NON riporti `WITH (security_invoker = on)` AZZERA le reloptions e riapre il
-- buco su quella vista (e' successo su vw_dash_fatturazione_contratti col
-- 20260707-03; ripristino 20260707-10).
--
-- Questo assert legge DIRETTAMENTE pg_class.reloptions: intercetta la
-- regressione anche quando il seed non ha un secondo emittente su cui
-- verificare il comportamento, cosa che il test funzionale con FORCE RLS
-- (test-vw-dash-aperto-v1.sql #9, skip-conditional) non garantisce.
--
-- Assert DINAMICO: copre qualunque vista `vendite.vw_dash_%` presente ORA nel
-- DB, quindi si estende da solo alle viste future della famiglia.
--
-- ⚠️ E LE VISTE FUORI DAL PREFISSO? Il `LIKE` e' comodo ma non e' un criterio:
-- il criterio vero e' «legge tabelle in RLS». Una vista che lo fa senza
-- chiamarsi vw_dash_* resta fuori dalla rete, e il buco non si vedrebbe. Per
-- questo l'elenco ha una coda ESPLICITA, che va allungata quando ne nasce una:
--   · vw_lotti_gruppi_serviti (20260815-26) — legge fatture, fatture_righe e
--     commesse_attivita, tutte con RLS, ed e' il cancello di scope del
--     consuntivo dei giri (fn_esito_gruppi_giro).
--   · vendite.vw_stato_sorgente_* — SEI viste (contratto, ddt, offerta, ordine,
--     preventivo, reso), una per dominio, ciascuna sulla propria tabella
--     documentale in RLS.
--   · script.vw_stato_sorgente — la union delle sei.
--
-- ⭐ QUELLA CODA E' STATA SCRITTA E POI NON GUARDATA. Le sette viste
-- `*stato_sorgente*` violavano il criterio dal 1-2 luglio 2026 e nessuno se ne
-- era accorto: il fix V-1 delle vw_dash_* e' del 6 luglio, cinque giorni DOPO,
-- e il 18 luglio due rami nuovi (ddt, reso) sono stati aggiunti senza
-- ripensarci. Trovate il 2026-08-21 applicando il criterio a tutto il DB, non
-- alla famiglia gia' presidiata. Corrette da 20260821-08 e -09.
--
-- 🔴 IL PERIMETRO NON E' PIU' UN SOLO SCHEMA: la union sta in `script`, le
-- altre in `vendite`. `security_invoker` NON si propaga lungo la catena delle
-- viste — ogni anello va dichiarato — quindi vanno presidiati entrambi.
--
-- ⚠️ Il modo per trovarne altre non e' leggere questo elenco, e' rifare la
-- misura:
--     viste senza security_invoker che dipendono da tabelle con relrowsecurity
--     (pg_class -> pg_rewrite -> pg_depend -> pg_class).
-- Se ne esce una nuova, si aggiunge qui E si mette il flag.
--
-- Indice test (1..2):
--   1) La famiglia presidiata e' presente (guard: senza, "0 trasgressori"
--      passerebbe a vuoto se il filtro non matchasse nulla)
--   2) Nessuna vista presidiata e' priva di security_invoker=on
--      (in fallimento il messaggio NOMINA le viste trasgressori)
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

SELECT plan(2);

-- ============================================================
-- Perimetro presidiato — definito UNA volta sola.
--   ⭐ In temp table e non ripetuto in ogni asserzione: quando la coda si
--   allunga si tocca un punto solo. Con il predicato duplicato, allungarne uno
--   e dimenticare l'altro avrebbe lasciato il conteggio d'accordo con se stesso
--   e la verifica cieca sulla vista nuova.
-- ============================================================
CREATE TEMP TABLE tmp_si_presidiate AS
SELECT n.nspname AS schema_name, c.relname AS view_name, c.reloptions
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind = 'v'
   AND (
         (n.nspname = 'vendite' AND (   c.relname LIKE 'vw\_dash\_%'
                                     OR c.relname LIKE 'vw\_stato\_sorgente\_%'
                                     OR c.relname IN ('vw_lotti_gruppi_serviti')))
      OR (n.nspname = 'script'  AND c.relname IN ('vw_stato_sorgente'))
       );

-- ============================================================
-- 1) Guard: la famiglia esiste
--    ⚠️ La soglia sale da 13 a 20 con le sette *stato_sorgente*: se un giorno
--    una di quelle sparisse, il conteggio lo direbbe invece di lasciare la rete
--    piu' larga del pescato.
-- ============================================================
SELECT cmp_ok(
  (SELECT count(*)::integer FROM tmp_si_presidiate),
  '>=', 20,
  '1. Famiglia presidiata presente nel DB (vw_dash_* + vw_stato_sorgente_* + coda esplicita, >= 20 viste)'
);

-- ============================================================
-- 2) Ogni vista presidiata ha security_invoker=on.
--    string_agg dei trasgressori confrontato con NULL: se una vista ha perso
--    il flag (reloptions azzerate da un REPLACE senza WITH), il diagnostico
--    di pgTAP mostra "have: <nome vista> / want: NULL".
--    option_value e' memorizzato come 'on' (non 'true'): cast a boolean per
--    robustezza ('on'/'true'/'1' -> true; assenza -> false via COALESCE).
--    ⭐ Il nome e' qualificato con lo schema: da quando il perimetro copre due
--    schemi, un `relname` nudo non basterebbe a dire quale vista sia.
-- ============================================================
SELECT is(
  (SELECT string_agg(p.schema_name || '.' || p.view_name, ', '
                     ORDER BY p.schema_name, p.view_name)
     FROM tmp_si_presidiate p
     LEFT JOIN LATERAL pg_options_to_table(p.reloptions) ot
       ON ot.option_name = 'security_invoker'
    WHERE COALESCE(ot.option_value::boolean, false) = false),
  NULL,
  '2. Tutte le viste presidiate (due schemi) hanno security_invoker=on'
);

SELECT * FROM finish();
ROLLBACK;
