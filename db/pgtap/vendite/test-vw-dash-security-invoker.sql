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
-- 1) Guard: la famiglia esiste
--    ⚠️ La soglia sale da 12 a 13 con la coda esplicita: se un giorno
--    vw_lotti_gruppi_serviti sparisse, il conteggio lo direbbe invece di
--    lasciare la rete piu' larga del pescato.
-- ============================================================
SELECT cmp_ok(
  (SELECT count(*)::integer
     FROM pg_class c
     JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'vendite'
      AND c.relkind = 'v'
      AND (c.relname LIKE 'vw_dash\_%'
           OR c.relname IN ('vw_lotti_gruppi_serviti'))),
  '>=', 13,
  '1. Famiglia presidiata presente nel DB (vw_dash_* + coda esplicita, >= 13 viste)'
);

-- ============================================================
-- 2) Ogni vista vw_dash_* ha security_invoker=on.
--    string_agg dei trasgressori confrontato con NULL: se una vista ha perso
--    il flag (reloptions azzerate da un REPLACE senza WITH), il diagnostico
--    di pgTAP mostra "have: <nome vista> / want: NULL".
--    option_value e' memorizzato come 'on' (non 'true'): cast a boolean per
--    robustezza ('on'/'true'/'1' -> true; assenza -> false via COALESCE).
-- ============================================================
SELECT is(
  (SELECT string_agg(c.relname, ', ' ORDER BY c.relname)
     FROM pg_class c
     JOIN pg_namespace n ON n.oid = c.relnamespace
     LEFT JOIN LATERAL pg_options_to_table(c.reloptions) ot
       ON ot.option_name = 'security_invoker'
    WHERE n.nspname = 'vendite'
      AND c.relkind = 'v'
      AND (c.relname LIKE 'vw_dash\_%'
           OR c.relname IN ('vw_lotti_gruppi_serviti'))
      AND COALESCE(ot.option_value::boolean, false) = false),
  NULL,
  '2. Tutte le viste presidiate (vw_dash_* + coda esplicita) hanno security_invoker=on'
);

SELECT * FROM finish();
ROLLBACK;
