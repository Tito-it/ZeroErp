{% include-markdown "it/dbzero/dbops/manual/vw_catalogo_oggetti.md" %}
{% include-markdown "it/dbzero/dbops/manual/vw_catalogo_oggetti.md" %}
# 🔍 View `vw_catalogo_oggetti`

```sql
CREATE OR REPLACE VIEW dbops.vw_catalogo_oggetti AS
SELECT n.nspname AS schema,
    c.relkind AS tipo_oggetto,
    c.relname AS nome_oggetto,
        CASE c.relkind
            WHEN 'r'::"char" THEN 't'::"char"
            WHEN 'v'::"char" THEN 'v'::"char"
            WHEN 'm'::"char" THEN 'm'::"char"
            WHEN 'i'::"char" THEN 'i'::"char"
            WHEN 'S'::"char" THEN 's'::"char"
            WHEN 'f'::"char" THEN 'f'::"char"
            ELSE c.relkind
        END AS tipo_descrizione,
    pg_roles.rolname AS proprietario,
    obj_description(c.oid, 'pg_class'::name) AS descrizione
   FROM ((pg_class c
     JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
     LEFT JOIN pg_roles ON ((pg_roles.oid = c.relowner)))
  WHERE (n.nspname = ANY (ARRAY['dbops'::name, 'script'::name]));
```
