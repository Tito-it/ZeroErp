-- ============================================================
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- ZeroErp — Introspezione runtime pre-ENABLE RLS — VERSIONE pgAdmin
--
-- READ-ONLY. A differenza di rls-introspezione-runtime.sql (per psql),
-- questa NON usa comandi meta \echo/\pset (che pgAdmin non supporta) e
-- restituisce TUTTO in UN'UNICA griglia: colonne (sezione, azione, dettaglio).
-- Esegui tutto insieme (F5). Filtra/ordina sulla colonna "sezione".
--
-- Sezioni: A viste DEFINER, B ruoli, C NOT NULL, D indici EF,
--          E NULL emittente (lotti+ordini), F stato RLS.
-- Le righe con azione che inizia per '**' richiedono intervento.
-- ============================================================

-- A. Viste/matview sulle tabelle del lotto (rischio DEFINER)
WITH RECURSIVE
lotto(schema_name, table_name) AS (
    VALUES
        ('vendite','fatture'),('vendite','fatture_scadenze'),
        ('vendite','fatturazione_lotti'),('vendite','preventivi'),
        ('vendite','contratti'),('vendite','offerte_commerciali'),
        ('vendite','ordini'),('documenti','documenti_generati'),
        ('pratiche','pratiche'),('anagrafiche','billing_account')
),
base AS (
    SELECT c.oid AS base_oid
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      JOIN lotto l ON l.schema_name = n.nspname AND l.table_name = c.relname
     WHERE c.relkind IN ('r','p')
),
rec(view_oid, base_oid) AS (
    SELECT DISTINCT r.ev_class, d.refobjid
      FROM pg_depend d
      JOIN pg_rewrite r ON r.oid = d.objid
      JOIN base b       ON b.base_oid = d.refobjid
     WHERE d.classid='pg_rewrite'::regclass AND d.refclassid='pg_class'::regclass
       AND r.ev_class <> d.refobjid
  UNION
    SELECT DISTINCT r.ev_class, rec.base_oid
      FROM pg_depend d
      JOIN pg_rewrite r ON r.oid = d.objid
      JOIN rec          ON rec.view_oid = d.refobjid
     WHERE d.classid='pg_rewrite'::regclass AND d.refclassid='pg_class'::regclass
       AND r.ev_class <> d.refobjid
),
sez_a AS (
    SELECT
        n.nspname AS vista_schema, c.relname AS vista_nome,
        CASE c.relkind WHEN 'v' THEN 'view' WHEN 'm' THEN 'matview' END AS tipo,
        pg_get_userbyid(c.relowner) AS owner,
        COALESCE((SELECT ot.option_value FROM pg_options_to_table(c.reloptions) ot
                   WHERE ot.option_name='security_invoker'),'off') AS security_invoker,
        CASE
            WHEN c.relkind='m' THEN '** MATVIEW: no security_invoker -> smaterializzare/filtrare a monte'
            WHEN NOT COALESCE((SELECT ot.option_value FROM pg_options_to_table(c.reloptions) ot
                            WHERE ot.option_name='security_invoker'),'off')::boolean
                THEN '** DEFINER: RLS bypassata -> ALTER VIEW ... SET (security_invoker=on)'
            ELSE 'OK (invoker)'
        END AS azione,
        string_agg(DISTINCT bn.nspname||'.'||bc.relname, ', ') AS tabelle_lotto
      FROM rec
      JOIN pg_class c  ON c.oid=rec.view_oid
      JOIN pg_namespace n ON n.oid=c.relnamespace
      JOIN pg_class bc ON bc.oid=rec.base_oid
      JOIN pg_namespace bn ON bn.oid=bc.relnamespace
     WHERE c.relkind IN ('v','m')
     GROUP BY n.nspname,c.relname,c.relkind,c.relowner,c.reloptions
)
SELECT 'A. viste'::text AS sezione, azione, to_jsonb(sez_a) AS dettaglio FROM sez_a

UNION ALL
-- B. Ruoli (BYPASSRLS / SUPERUSER)
SELECT 'B. ruoli',
       CASE
           WHEN rolname='zeroerp_app' AND (bypassrls OR superuser)
               THEN '** zeroerp_app deve essere NOBYPASSRLS'
           WHEN rolname IN ('titodb','postgres') AND NOT (bypassrls OR superuser)
               THEN '** atteso esente (migrazioni filtrate)'
           ELSE 'ok'
       END,
       to_jsonb(t)
  FROM (
    SELECT rolname, rolsuper AS superuser, rolbypassrls AS bypassrls, rolcanlogin AS can_login
      FROM pg_roles
     WHERE rolname IN ('zeroerp_app','titodb','postgres','zeroerp_migration','zeroerp_admin')
  ) t

UNION ALL
-- C. Colonne emittente: NOT NULL?
SELECT 'C. not_null',
       CASE WHEN is_nullable='YES' THEN '** NULLABLE: backfill + SET NOT NULL prima dell ENABLE' ELSE 'ok' END,
       to_jsonb(t)
  FROM (
    SELECT table_schema, table_name, column_name, data_type, is_nullable
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
            ('vendite','ordini','emittente_fiscale_id'))
  ) t

UNION ALL
-- D. Indici sulle colonne emittente
SELECT 'D. indici',
       CASE WHEN idx IS NULL THEN '** MANCANTE: registrare in dbops.fk_index_policy / creare indice' ELSE 'ok' END,
       to_jsonb(t)
  FROM (
    SELECT x.schema_name, x.table_name, x.col,
           (SELECT string_agg(i.relname, ', ')
              FROM pg_index ix
              JOIN pg_class i  ON i.oid=ix.indexrelid
              JOIN pg_class tb ON tb.oid=ix.indrelid
              JOIN pg_namespace ns ON ns.oid=tb.relnamespace
              JOIN pg_attribute a ON a.attrelid=tb.oid AND a.attnum=ANY(ix.indkey)
             WHERE ns.nspname=x.schema_name AND tb.relname=x.table_name AND a.attname=x.col
           ) AS idx
      FROM (VALUES
            ('vendite','fatture','emittente_soggetto_ruolo_id'),
            ('vendite','fatturazione_lotti','emittente_soggetto_ruolo_id'),
            ('vendite','preventivi','emittente_fiscale_id'),
            ('vendite','contratti','emittente_fiscale_id'),
            ('vendite','offerte_commerciali','emittente_fiscale_id'),
            ('documenti','documenti_generati','emittente_fiscale_id'),
            ('pratiche','pratiche','emittente_fiscale_id'),
            ('vendite','ordini','emittente_fiscale_id')
           ) AS x(schema_name, table_name, col)
  ) t

UNION ALL
-- E. Righe a emittente NULL (lotti + ordini): residui per i backfill -18 / -24
SELECT 'E. null_emittente',
       CASE WHEN null_count > 0 THEN '** '||null_count||' righe NULL: il SET NOT NULL fallira finche non risolte' ELSE 'ok' END,
       to_jsonb(t)
  FROM (
    SELECT 'vendite.fatturazione_lotti' AS tabella,
           count(*) FILTER (WHERE emittente_soggetto_ruolo_id IS NULL) AS null_count,
           count(*) AS totali,
           count(*) FILTER (WHERE emittente_soggetto_ruolo_id IS NULL
                              AND billing_account_id IS NULL AND utility_id IS NULL) AS null_senza_ba_ne_utility
      FROM vendite.fatturazione_lotti
    UNION ALL
    SELECT 'vendite.ordini',
           count(*) FILTER (WHERE emittente_fiscale_id IS NULL),
           count(*),
           count(*) FILTER (WHERE emittente_fiscale_id IS NULL AND billing_account_id IS NULL)
      FROM vendite.ordini
  ) t

UNION ALL
-- F. Stato RLS per tabella del lotto
SELECT 'F. stato_rls', 'info',
       to_jsonb(t)
  FROM (
    SELECT n.nspname AS schema, c.relname AS tabella,
           c.relrowsecurity AS rls_enabled, c.relforcerowsecurity AS rls_forced,
           (SELECT count(*) FROM pg_policies p
             WHERE p.schemaname=n.nspname AND p.tablename=c.relname) AS num_policy
      FROM pg_class c
      JOIN pg_namespace n ON n.oid=c.relnamespace
     WHERE (n.nspname,c.relname) IN (
            ('vendite','fatture'),('vendite','fatture_scadenze'),
            ('vendite','fatturazione_lotti'),('vendite','preventivi'),
            ('vendite','contratti'),('vendite','offerte_commerciali'),
            ('vendite','ordini'),('documenti','documenti_generati'),
            ('pratiche','pratiche'),('anagrafiche','billing_account'))
  ) t

ORDER BY 1, 2 DESC;
