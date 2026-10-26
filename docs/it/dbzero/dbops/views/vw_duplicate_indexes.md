{% include-markdown "it/dbzero/dbops/manual/vw_duplicate_indexes.md" %}
# 🔍 View `vw_duplicate_indexes`

> 📝 **Descrizione**
>
> Indici DUPLICATI ESATTI negli schemi in dbops.automation_scope. Raggruppa per firma normalizzata (pg_get_indexdef senza nome, senza WITH(...) e senza TABLESPACE): due indici nello stesso gruppo sono intercambiabili, quindi tutti tranne uno sono eliminabili. Prima del 2026-07-27 raggruppava per sole colonne e produceva 16 falsi positivi su 19 (GIN trgm contro btree, UNIQUE parziali disgiunte, colonne-espressione scartate). Il flag UNIQUE NON e' nella chiave di raggruppamento ma nel criterio di ordinamento: un btree non-unique identico a un UNIQUE e' ridondante e deve restare visibile. Usare indice_da_tenere / indici_da_droppare. NON copre la ridondanza per prefisso: per quella vedere dbops.vw_indici_ridondanti_prefisso.

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
          WHERE ((i.relkind = 'i'::"char") AND (NOT ix.indisprimary) AND ix.indisvalid AND (EXISTS ( SELECT 1
                   FROM dbops.automation_scope sc
                  WHERE (sc.schema_name = n.nspname))))
        )
 SELECT schema_name,
    table_name,
    index_columns,
    metodo,
    predicato,
    array_agg(index_name ORDER BY indisunique DESC, indexrelid) AS duplicate_index_names,
    count(*) AS count_of_indexes,
    (array_agg(index_name ORDER BY indisunique DESC, indexrelid))[1] AS indice_da_tenere,
    (array_agg(index_name ORDER BY indisunique DESC, indexrelid))[2:] AS indici_da_droppare
   FROM idx
  GROUP BY schema_name, table_name, index_columns, metodo, predicato, firma
 HAVING (count(*) > 1)
  ORDER BY schema_name, table_name;
```

</div>


---
{% include-markdown "signature-core.md" %}
