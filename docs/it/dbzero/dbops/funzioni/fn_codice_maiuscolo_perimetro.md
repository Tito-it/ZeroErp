{% include-markdown "it/dbzero/dbops/manual/fn_codice_maiuscolo_perimetro.md" %}
# ⚙️ Funzione `fn_codice_maiuscolo_perimetro`

```sql
CREATE FUNCTION fn_codice_maiuscolo_perimetro(p_schemas text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_codice_maiuscolo_perimetro(p_schemas text[] DEFAULT NULL::text[])
 RETURNS TABLE(schema_name text, table_name text, rel regclass, nel_perimetro boolean, in_eccezione boolean, trigger_vivi text[], azione text)
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: lo stato atteso del trigger CODICE_MAIUSCOLO contro
    --   quello vivo, tabella per tabella, e l'azione che li allinea.
    WITH ambito AS (
        SELECT DISTINCT btrim(s) AS nspname
          FROM unnest(dbops.fn_resolve_scope(p_schemas)) AS u(s)
         WHERE btrim(s) <> 'storico'
    ),
    candidate AS (
        SELECT c.oid AS relid
          FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
          JOIN ambito am ON am.nspname = n.nspname
          JOIN pg_catalog.pg_attribute a
            ON a.attrelid = c.oid
           AND a.attname = 'codice'
           AND a.attnum > 0
           AND NOT a.attisdropped
           AND a.attgenerated = ''
          JOIN pg_catalog.pg_type t ON t.oid = a.atttypid
         WHERE c.relkind = 'r'
           AND t.typcategory = 'S'
           AND dbops.fn_table_in_scope(n.nspname, c.relname)
    ),
    vivi AS (
        SELECT tg.tgrelid AS relid,
               array_agg(tg.tgname::text ORDER BY tg.tgname) AS nomi
          FROM pg_catalog.pg_trigger tg
          JOIN pg_catalog.pg_proc p ON p.oid = tg.tgfoid
          JOIN pg_catalog.pg_namespace pn ON pn.oid = p.pronamespace
          JOIN pg_catalog.pg_class c ON c.oid = tg.tgrelid
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
          JOIN ambito am ON am.nspname = n.nspname
         WHERE NOT tg.tgisinternal
           AND pn.nspname = 'script'
           AND p.proname = 'trgfn_codice_maiuscolo'
         GROUP BY tg.tgrelid
    ),
    stato AS (
        SELECT n.nspname::text AS schema_name,
               c.relname::text AS table_name,
               c.oid::regclass AS rel,
               (ca.relid IS NOT NULL) AS nel_perimetro,
               (e.id IS NOT NULL) AS in_eccezione,
               COALESCE(v.nomi, ARRAY[]::text[]) AS trigger_vivi
          FROM (SELECT relid FROM candidate UNION SELECT relid FROM vivi) AS u
          JOIN pg_catalog.pg_class c ON c.oid = u.relid
          JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
          LEFT JOIN candidate ca ON ca.relid = u.relid
          LEFT JOIN vivi v ON v.relid = u.relid
          LEFT JOIN dbops.automazione_codice_eccezioni e
            ON e.schema_name = n.nspname
           AND e.table_name = c.relname
           AND e.column_name = 'codice'
    )
    SELECT s.schema_name,
           s.table_name,
           s.rel,
           s.nel_perimetro,
           s.in_eccezione,
           s.trigger_vivi,
           CASE
               WHEN s.nel_perimetro AND NOT s.in_eccezione
                    AND cardinality(s.trigger_vivi) = 0 THEN 'CREA'
               WHEN s.nel_perimetro AND NOT s.in_eccezione
                    AND cardinality(s.trigger_vivi) > 1 THEN 'RIGENERA'
               WHEN NOT (s.nel_perimetro AND NOT s.in_eccezione)
                    AND cardinality(s.trigger_vivi) > 0 THEN 'TOGLIE'
           END AS azione
      FROM stato s
     ORDER BY s.schema_name, s.table_name;
$function$

COMMENT ON FUNCTION dbops.fn_codice_maiuscolo_perimetro(p_schemas text[])
IS 'Automazione CODICE_MAIUSCOLO (decisione Tid 2026-11-04): per ogni tabella dell''ambito che ha una colonna codice, o che ha gia'' il trigger, dice se script.trgfn_codice_maiuscolo e'' DOVUTO, quali trigger su quella funzione sono vivi e l''azione che li allinea: CREA (dovuto, nessuno vivo), RIGENERA (dovuto, piu'' di uno), TOGLIE (non dovuto, vivo), NULL (a posto). Perimetro: relkind r, schemi di dbops.fn_resolve_scope(p_schemas) meno storico, dbops.fn_table_in_scope, colonna codice di tipo stringa non generata. Dovuto = nel perimetro e non in dbops.automazione_codice_eccezioni (regola per esclusione). Il trigger vivo si riconosce dalla funzione, mai dal nome; i vivi si cercano solo negli schemi della corsa. E'' la sede unica della regola: la leggono dbops.fn_run_automations_codice_maiuscolo, la convergenza di ogni migrate (90_end), il pgTAP di presidio e la bonifica una tantum delle righe gia'' scritte.';
```

</div>

---
{% include-markdown "signature-core.md" %}
