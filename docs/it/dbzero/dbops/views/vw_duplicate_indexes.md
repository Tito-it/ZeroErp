{% include-markdown "it/dbzero/dbops/manual/vw_duplicate_indexes.md" %}
# 🔍 View `vw_duplicate_indexes`

> 📝 **Descrizione**
>
> Indici DUPLICATI ESATTI negli schemi governati dalla politica degli indici (dbops.fn_indici_schema_nell_ambito). Raggruppa per firma normalizzata (pg_get_indexdef senza nome, senza WITH(...) e senza TABLESPACE): due indici nello stesso gruppo sono intercambiabili (la chiave primaria non entra nel confronto). Il primo dell'ordinamento si tiene (indice_da_tenere), gli altri sono proposti in indici_da_droppare. L'ordinamento mette prima gli indici che reggono un vincolo (UNIQUE, EXCLUDE, o il riferito di una FK: pg_constraint.conindid) o la replica identity, poi gli UNIQUE: un indice di vincolo non e' mai proposto per il DROP, anche quando nel gruppo ce n'e' piu' d'uno. Il flag UNIQUE non e' nella chiave di raggruppamento: un btree non-unique identico a un UNIQUE e' ridondante e deve restare visibile. Non copre la ridondanza per prefisso: per quella c'e' dbops.vw_indici_ridondanti_prefisso.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_duplicate_indexes AS
WITH idx AS (
         SELECT ix.indexrelid,
            n.nspname AS schema_name,
            t.relname AS table_name,
            (i.relname)::text AS index_name,
            ix.indisunique,
            (ix.indisreplident OR (EXISTS ( SELECT 1
                   FROM pg_constraint co
                  WHERE (co.conindid = ix.indexrelid)))) AS regge_vincolo,
            (am.amname)::text AS metodo,
            pg_get_expr(ix.indpred, ix.indrelid) AS predicato,
            ( SELECT array_agg(pg_get_indexdef(ix.indexrelid, k.k, false) ORDER BY k.k) AS array_agg
                   FROM generate_series(1, (ix.indnkeyatts)::integer) k(k)) AS index_columns,
            regexp_replace(regexp_replace(regexp_replace(pg_get_indexdef(ix.indexrelid), '^CREATE (UNIQUE )?INDEX .*? ON '::text, 'ON '::text), ' WITH \(.*?\)'::text, ''::text), ' TABLESPACE \S+'::text, ''::text) AS firma
           FROM ((((pg_index ix
             JOIN pg_class i ON ((i.oid = ix.indexrelid)))
             JOIN pg_class t ON ((t.oid = ix.indrelid)))
             JOIN pg_namespace n ON ((n.oid = t.relnamespace)))
             JOIN pg_am am ON ((am.oid = i.relam)))
          WHERE ((i.relkind = 'i'::"char") AND (NOT ix.indisprimary) AND ix.indisvalid AND dbops.fn_indici_schema_nell_ambito((n.nspname)::text))
        )
 SELECT schema_name,
    table_name,
    index_columns,
    metodo,
    predicato,
    array_agg(index_name ORDER BY regge_vincolo DESC, indisunique DESC, indexrelid) AS duplicate_index_names,
    count(*) AS count_of_indexes,
    (array_agg(index_name ORDER BY regge_vincolo DESC, indisunique DESC, indexrelid))[1] AS indice_da_tenere,
        CASE
            WHEN bool_or(regge_vincolo) THEN COALESCE(array_agg(index_name ORDER BY indisunique DESC, indexrelid) FILTER (WHERE (NOT regge_vincolo)), ARRAY[]::text[])
            ELSE (array_agg(index_name ORDER BY indisunique DESC, indexrelid))[2:]
        END AS indici_da_droppare
   FROM idx
  GROUP BY schema_name, table_name, index_columns, metodo, predicato, firma
 HAVING (count(*) > 1)
  ORDER BY schema_name, table_name;
```

</div>


---
{% include-markdown "signature-core.md" %}
