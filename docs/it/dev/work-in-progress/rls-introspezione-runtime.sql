-- ============================================================
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- ZeroErp — Introspezione runtime pre-ENABLE RLS (scope emittente)
--
-- READ-ONLY: nessuna modifica. Esegui con:
--     psql "<connessione>" -f rls-introspezione-runtime.sql
-- oppure incolla le singole sezioni in una console.
--
-- Copre i punti [DA VERIFICARE SU DB] del brief
-- analisi-attivazione-rls-db.md:
--   A. Viste/matview DEFINER sulle tabelle del lotto (Fase 3, BLOCKER R1/C2)
--   B. Attributi ruoli (BYPASSRLS) — §10
--   C. NOT NULL colonne emittente sulle tabelle del lotto — §4
--   D. Indici EF presenti/mancanti — §6
--   E. Conteggio righe a emittente NULL (lotti) — sanazione §4 / migration -18
--   F. Stato RLS (enabled/forced) per tabella del lotto — §9
-- ============================================================

\pset pager off

-- Tabelle del lotto (Ondata 1 SR + Ondata 2 PK + billing_account).
-- Usata da piu' sezioni; ridefinita inline dove serve (script eseguibile a pezzi).

-- ------------------------------------------------------------
-- A. VISTE / MATVIEW che insistono sulle tabelle del lotto
--    DEFINER = RLS cosmetica (la vista bypassa la RLS della base).
--    MATVIEW = non supporta security_invoker -> decisione esplicita.
-- ------------------------------------------------------------
\echo '== A. Viste/matview sulle tabelle del lotto (rischio DEFINER) =='
WITH RECURSIVE
lotto(schema_name, table_name) AS (
    VALUES
        ('vendite','fatture'),
        ('vendite','fatture_scadenze'),
        ('vendite','fatturazione_lotti'),
        ('vendite','preventivi'),
        ('vendite','contratti'),
        ('vendite','offerte_commerciali'),
        ('vendite','ordini'),
        ('documenti','documenti_generati'),
        ('pratiche','pratiche'),
        ('anagrafiche','billing_account')
),
base AS (
    SELECT c.oid AS base_oid
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      JOIN lotto l ON l.schema_name = n.nspname AND l.table_name = c.relname
     WHERE c.relkind IN ('r','p')
),
rec(view_oid, base_oid) AS (
    -- ancora: viste/matview che leggono direttamente una base del lotto
    SELECT DISTINCT r.ev_class, d.refobjid
      FROM pg_depend d
      JOIN pg_rewrite r ON r.oid = d.objid
      JOIN base b       ON b.base_oid = d.refobjid
     WHERE d.classid    = 'pg_rewrite'::regclass
       AND d.refclassid = 'pg_class'::regclass
       AND r.ev_class  <> d.refobjid
  UNION
    -- transitivo: viste costruite su altre viste del lotto
    SELECT DISTINCT r.ev_class, rec.base_oid
      FROM pg_depend d
      JOIN pg_rewrite r ON r.oid = d.objid
      JOIN rec          ON rec.view_oid = d.refobjid
     WHERE d.classid    = 'pg_rewrite'::regclass
       AND d.refclassid = 'pg_class'::regclass
       AND r.ev_class  <> d.refobjid
)
SELECT
    n.nspname AS vista_schema,
    c.relname AS vista_nome,
    CASE c.relkind WHEN 'v' THEN 'view' WHEN 'm' THEN 'matview' END AS tipo,
    pg_get_userbyid(c.relowner) AS owner,
    COALESCE(
        (SELECT ot.option_value
           FROM pg_options_to_table(c.reloptions) ot
          WHERE ot.option_name = 'security_invoker'),
        'off'
    ) AS security_invoker,
    CASE
        WHEN c.relkind = 'm'
            THEN '** MATVIEW: no security_invoker -> smaterializzare/filtrare a monte'
        WHEN NOT COALESCE((SELECT ot.option_value FROM pg_options_to_table(c.reloptions) ot
                        WHERE ot.option_name='security_invoker'),'off')::boolean
            THEN '** DEFINER: RLS bypassata -> ALTER VIEW ... SET (security_invoker=on)'
        ELSE 'OK (invoker)'
    END AS azione,
    string_agg(DISTINCT bn.nspname||'.'||bc.relname, ', ') AS tabelle_lotto_lette
  FROM rec
  JOIN pg_class     c  ON c.oid  = rec.view_oid
  JOIN pg_namespace n  ON n.oid  = c.relnamespace
  JOIN pg_class     bc ON bc.oid = rec.base_oid
  JOIN pg_namespace bn ON bn.oid = bc.relnamespace
 WHERE c.relkind IN ('v','m')
 GROUP BY n.nspname, c.relname, c.relkind, c.relowner, c.reloptions
 ORDER BY azione DESC, vista_schema, vista_nome;

-- ------------------------------------------------------------
-- B. RUOLI: attributi rilevanti per la RLS.
--    zeroerp_app deve essere NOBYPASSRLS; titodb (migrazioni) BYPASSRLS/superuser.
-- ------------------------------------------------------------
\echo '== B. Ruoli (BYPASSRLS / SUPERUSER) =='
SELECT rolname,
       rolsuper      AS superuser,
       rolbypassrls  AS bypassrls,
       rolcanlogin   AS can_login,
       CASE
           WHEN rolname = 'zeroerp_app' AND (rolbypassrls OR rolsuper)
               THEN '** ATTESO NOBYPASSRLS: ALTER ROLE zeroerp_app NOBYPASSRLS;'
           WHEN rolname IN ('titodb','postgres') AND NOT (rolbypassrls OR rolsuper)
               THEN '** ATTESO esente: migrazioni verrebbero filtrate dalla RLS'
           ELSE 'ok'
       END AS nota
  FROM pg_roles
 WHERE rolname IN ('zeroerp_app','titodb','postgres','zeroerp_migration','zeroerp_admin')
 ORDER BY rolname;

-- ------------------------------------------------------------
-- C. NULLABILITY colonne emittente sulle tabelle del lotto.
--    Atteso NOT NULL prima dell'ENABLE (no special-casing NULL nelle policy).
-- ------------------------------------------------------------
\echo '== C. Colonne emittente: NOT NULL? =='
SELECT table_schema, table_name, column_name, data_type,
       is_nullable,
       CASE WHEN is_nullable = 'YES'
            THEN '** NULLABLE: valutare backfill + SET NOT NULL prima dell ENABLE'
            ELSE 'ok' END AS nota
  FROM information_schema.columns
 WHERE (table_schema, table_name, column_name) IN (
        ('vendite','fatture','emittente_soggetto_ruolo_id'),
        ('vendite','fatture_scadenze','fattura_id'),
        ('vendite','fatturazione_lotti','emittente_soggetto_ruolo_id'),
        ('vendite','preventivi','emittente_fiscale_id'),
        ('vendite','contratti','emittente_fiscale_id'),
        ('vendite','offerte_commerciali','emittente_fiscale_id'),
        ('documenti','documenti_generati','emittente_fiscale_id'),
        ('pratiche','pratiche','emittente_fiscale_id'),
        ('vendite','ordini','emittente_fiscale_id')
       )
 ORDER BY table_schema, table_name;

-- ------------------------------------------------------------
-- D. INDICI sulle colonne emittente del lotto (filtri/perf, RLS come Filter).
-- ------------------------------------------------------------
\echo '== D. Indici sulle colonne emittente =='
WITH target(schema_name, table_name, col) AS (
    VALUES
        ('vendite','fatture','emittente_soggetto_ruolo_id'),
        ('vendite','fatturazione_lotti','emittente_soggetto_ruolo_id'),
        ('vendite','preventivi','emittente_fiscale_id'),
        ('vendite','contratti','emittente_fiscale_id'),
        ('vendite','offerte_commerciali','emittente_fiscale_id'),
        ('documenti','documenti_generati','emittente_fiscale_id'),
        ('pratiche','pratiche','emittente_fiscale_id'),
        ('vendite','ordini','emittente_fiscale_id')
)
SELECT t.schema_name, t.table_name, t.col,
       COALESCE(
           (SELECT string_agg(i.relname, ', ')
              FROM pg_index x
              JOIN pg_class i  ON i.oid = x.indexrelid
              JOIN pg_class tb ON tb.oid = x.indrelid
              JOIN pg_namespace ns ON ns.oid = tb.relnamespace
              JOIN pg_attribute a
                ON a.attrelid = tb.oid AND a.attnum = ANY(x.indkey)
             WHERE ns.nspname = t.schema_name
               AND tb.relname = t.table_name
               AND a.attname  = t.col),
           '** MANCANTE: creare ix_'||t.table_name||'_'||t.col
       ) AS indici_sulla_colonna
  FROM target t
 ORDER BY t.schema_name, t.table_name;

-- ------------------------------------------------------------
-- E. Conteggio righe fatturazione_lotti a emittente NULL (sanazione -18).
-- ------------------------------------------------------------
\echo '== E. fatturazione_lotti: righe a emittente NULL =='
SELECT count(*) FILTER (WHERE emittente_soggetto_ruolo_id IS NULL) AS lotti_emittente_null,
       count(*)                                                    AS lotti_totali,
       count(*) FILTER (WHERE emittente_soggetto_ruolo_id IS NULL
                          AND billing_account_id IS NULL
                          AND utility_id IS NULL)                  AS null_senza_ba_ne_utility
  FROM vendite.fatturazione_lotti;

-- ------------------------------------------------------------
-- F. Stato RLS per tabella del lotto (enabled / forced).
-- ------------------------------------------------------------
\echo '== F. Stato RLS per tabella del lotto =='
SELECT n.nspname AS schema, c.relname AS tabella,
       c.relrowsecurity  AS rls_enabled,
       c.relforcerowsecurity AS rls_forced,
       (SELECT count(*) FROM pg_policies p
         WHERE p.schemaname = n.nspname AND p.tablename = c.relname) AS num_policy
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE (n.nspname, c.relname) IN (
        ('vendite','fatture'),
        ('vendite','fatture_scadenze'),
        ('vendite','fatturazione_lotti'),
        ('vendite','preventivi'),
        ('vendite','contratti'),
        ('vendite','offerte_commerciali'),
        ('vendite','ordini'),
        ('documenti','documenti_generati'),
        ('pratiche','pratiche'),
        ('anagrafiche','billing_account')
       )
 ORDER BY n.nspname, c.relname;

\echo '== Fine introspezione =='
