{% include-markdown "it/dbzero/dbops/manual/vw_fk_con_indice_missing_policy.md" %}
# 🔍 View `vw_fk_con_indice_missing_policy`

```sql
CREATE OR REPLACE VIEW dbops.vw_fk_con_indice_missing_policy AS
WITH fk_grouped AS (
         SELECT con.conname AS constraint_name,
            nsp.nspname AS schema_name,
            rel.relname AS table_name,
            con.conrelid,
            ( SELECT array_agg(a.attname ORDER BY a.attname) AS array_agg
                   FROM (unnest(con.conkey) k(att)
                     JOIN pg_attribute a ON (((a.attrelid = con.conrelid) AND (a.attnum = k.att))))) AS fk_cols
           FROM ((pg_constraint con
             JOIN pg_class rel ON ((rel.oid = con.conrelid)))
             JOIN pg_namespace nsp ON ((nsp.oid = rel.relnamespace)))
          WHERE ((con.contype = 'f'::"char") AND (EXISTS ( SELECT 1
                   FROM dbops.automation_scope sc
                  WHERE (sc.schema_name = nsp.nspname))))
        ), idx_dedicati AS (
         SELECT ix_1.indrelid,
            i.relname AS index_name,
            ( SELECT array_agg(a.attname ORDER BY a.attname) AS array_agg
                   FROM (generate_series(1, (ix_1.indnkeyatts)::integer) g(k)
                     JOIN pg_attribute a ON (((a.attrelid = ix_1.indrelid) AND (a.attnum = ix_1.indkey[(g.k - 1)]))))) AS cols_set,
            ( SELECT string_agg((a.attname)::text, ', '::text ORDER BY g.k) AS string_agg
                   FROM (generate_series(1, (ix_1.indnkeyatts)::integer) g(k)
                     JOIN pg_attribute a ON (((a.attrelid = ix_1.indrelid) AND (a.attnum = ix_1.indkey[(g.k - 1)]))))) AS cols_ordinate,
            ( SELECT bool_and((ix_1.indkey[(g.k - 1)] > 0)) AS bool_and
                   FROM generate_series(1, (ix_1.indnkeyatts)::integer) g(k)) AS solo_colonne
           FROM ((((pg_index ix_1
             JOIN pg_class i ON ((i.oid = ix_1.indexrelid)))
             JOIN pg_class t ON ((t.oid = ix_1.indrelid)))
             JOIN pg_namespace n ON ((n.oid = t.relnamespace)))
             JOIN pg_am am ON ((am.oid = i.relam)))
          WHERE ((i.relkind = 'i'::"char") AND (am.amname = 'btree'::name) AND ix_1.indisvalid AND ix_1.indisready AND (ix_1.indpred IS NULL) AND (ix_1.indnatts = ix_1.indnkeyatts) AND (NOT ix_1.indisunique) AND (NOT ix_1.indisprimary) AND (NOT ix_1.indisreplident) AND (NOT (EXISTS ( SELECT 1
                   FROM pg_constraint c
                  WHERE (c.conindid = ix_1.indexrelid)))) AND (EXISTS ( SELECT 1
                   FROM dbops.automation_scope sc
                  WHERE (sc.schema_name = n.nspname))))
        )
 SELECT DISTINCT ON (fk.conrelid, fk.constraint_name) fk.schema_name,
    fk.table_name,
    fk.constraint_name,
    fk.fk_cols,
    ix.index_name,
    format('CREATE INDEX IF NOT EXISTS %I ON %I.%I(%s);'::text, ix.index_name, fk.schema_name, fk.table_name, ix.cols_ordinate) AS create_index_suggestion
   FROM ((fk_grouped fk
     JOIN idx_dedicati ix ON (((ix.indrelid = fk.conrelid) AND ix.solo_colonne AND (ix.cols_set = fk.fk_cols))))
     LEFT JOIN dbops.fk_index_policy pol ON (((fk.schema_name = pol.schema_name) AND (fk.table_name = pol.table_name) AND (fk.constraint_name = pol.constraint_name))))
  WHERE (pol.constraint_name IS NULL)
  ORDER BY fk.conrelid, fk.constraint_name, ix.index_name;
```


---
{% include-markdown "signature-core.md" %}
