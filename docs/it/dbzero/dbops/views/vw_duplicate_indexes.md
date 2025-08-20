{% include-markdown "it/dbzero/dbops/manual/vw_duplicate_indexes.md" %}
# 🔍 View `vw_duplicate_indexes`

```sql
CREATE OR REPLACE VIEW dbops.vw_duplicate_indexes AS
WITH index_cols AS (
         SELECT i.oid AS index_oid,
            n.nspname AS schema_name,
            t.relname AS table_name,
            i.relname AS index_name,
            ix.indisunique AS is_unique,
            ix.indisprimary AS is_primary,
            array_agg(a.attname ORDER BY x.ordinality) AS cols
           FROM (((((pg_index ix
             JOIN pg_class i ON ((i.oid = ix.indexrelid)))
             JOIN pg_class t ON ((t.oid = ix.indrelid)))
             JOIN pg_namespace n ON ((n.oid = t.relnamespace)))
             JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY x(attnum, ordinality) ON (true))
             JOIN pg_attribute a ON (((a.attrelid = t.oid) AND (a.attnum = x.attnum))))
          WHERE ((NOT ix.indisprimary) AND (i.relkind = 'i'::"char"))
          GROUP BY i.oid, n.nspname, t.relname, i.relname, ix.indisunique, ix.indisprimary
        )
 SELECT schema_name,
    table_name,
    cols AS index_columns,
    array_agg(index_name) AS duplicate_index_names,
    count(*) AS count_of_indexes
   FROM index_cols
  GROUP BY schema_name, table_name, cols
 HAVING (count(*) > 1)
  ORDER BY schema_name, table_name, (count(*)) DESC;
```


---
{% include-markdown "signature-core.md" %}
