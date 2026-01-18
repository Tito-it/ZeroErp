{% include-markdown "it/dbzero/dbops/manual/vw_fk_con_indice_missing_policy.md" %}
# 🔍 View `vw_fk_con_indice_missing_policy`

```sql
CREATE OR REPLACE VIEW dbops.vw_fk_con_indice_missing_policy AS
WITH fk_columns AS (
         SELECT con.oid AS constraint_oid,
            con.conname AS constraint_name,
            nsp.nspname AS schema_name,
            rel.relname AS table_name,
            unnest(con.conkey) AS attnum,
            con.conrelid
           FROM ((pg_constraint con
             JOIN pg_class rel ON ((rel.oid = con.conrelid)))
             JOIN pg_namespace nsp ON ((nsp.oid = rel.relnamespace)))
          WHERE ((con.contype = 'f'::"char") AND (EXISTS ( SELECT 1
                   FROM dbops.automation_scope sc
                  WHERE (sc.schema_name = nsp.nspname))))
        ), fk_fields AS (
         SELECT fk_1.constraint_name,
            fk_1.schema_name,
            fk_1.table_name,
            a.attname AS column_name,
            fk_1.conrelid,
            fk_1.constraint_oid
           FROM (fk_columns fk_1
             JOIN pg_attribute a ON (((a.attrelid = fk_1.conrelid) AND (a.attnum = fk_1.attnum))))
        ), indexed_columns AS (
         SELECT i.relname AS index_name,
            n.nspname AS schema_name,
            t.relname AS table_name,
            array_agg(a.attname ORDER BY x.ordinality) AS indexed_cols
           FROM (((((pg_index ix
             JOIN pg_class i ON ((i.oid = ix.indexrelid)))
             JOIN pg_class t ON ((t.oid = ix.indrelid)))
             JOIN pg_namespace n ON ((n.oid = t.relnamespace)))
             JOIN LATERAL unnest(ix.indkey) WITH ORDINALITY x(attnum, ordinality) ON (true))
             JOIN pg_attribute a ON (((a.attrelid = t.oid) AND (a.attnum = x.attnum))))
          WHERE (EXISTS ( SELECT 1
                   FROM dbops.automation_scope sc
                  WHERE (sc.schema_name = n.nspname)))
          GROUP BY i.relname, n.nspname, t.relname
        ), fk_grouped AS (
         SELECT fk_1.constraint_name,
            fk_1.schema_name,
            fk_1.table_name,
            array_agg(fk_1.column_name ORDER BY fk_1.column_name) AS fk_cols
           FROM fk_fields fk_1
          GROUP BY fk_1.constraint_name, fk_1.schema_name, fk_1.table_name
        )
 SELECT fk.schema_name,
    fk.table_name,
    fk.constraint_name,
    fk.fk_cols,
    idx.index_name,
    format('CREATE INDEX IF NOT EXISTS ix_%I_%I_%s ON %I.%I(%s);'::text, fk.schema_name, fk.table_name, array_to_string(fk.fk_cols, '_'::text), fk.schema_name, fk.table_name, array_to_string(fk.fk_cols, ', '::text)) AS create_index_suggestion
   FROM ((fk_grouped fk
     JOIN indexed_columns idx ON (((fk.schema_name = idx.schema_name) AND (fk.table_name = idx.table_name) AND (fk.fk_cols = idx.indexed_cols))))
     LEFT JOIN dbops.fk_index_policy pol ON (((fk.schema_name = pol.schema_name) AND (fk.table_name = pol.table_name) AND (fk.constraint_name = pol.constraint_name))))
  WHERE ((pol.constraint_name IS NULL) AND (COALESCE(pol.consentito, true) = true))
  ORDER BY fk.schema_name, fk.table_name;
```


---
{% include-markdown "signature-core.md" %}
