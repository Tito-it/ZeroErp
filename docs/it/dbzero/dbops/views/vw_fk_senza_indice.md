{% include-markdown "it/dbzero/dbops/manual/vw_fk_senza_indice.md" %}
# 🔍 View `vw_fk_senza_indice`

> 📝 **Descrizione**
>
> Il fatto: le foreign key SENZA copertura di indice negli schemi governati dalla politica (dbops.fn_indici_schema_nell_ambito), qualunque decisione abbiano. decisione e' quella di dbops.fk_index_policy, NULL se la FK non ha riga. La FK e' coperta se le sue colonne coincidono, come insieme, con le prime N colonne chiave di un btree valido, e il predicato dell'indice e' assente oppure e' una congiunzione di soli "&lt;colonna della FK&gt; IS NOT NULL": il controllo referenziale cerca "fkcol = $1" con $1 mai NULL, quindi su una FK nullabile un indice parziale cosi' basta. Ogni altro predicato viene rifiutato, anche quando di fatto coprirebbe: l'errore possibile e' dire scoperta una FK coperta, mai il contrario. Non e' un presidio: una FK SENZA_INDICE e' scoperta per decisione. La leggono dbops.fn_populate_fk_index_policy (le FK senza riga), dbops.apply_fk_index_policy (crea solo se la FK e' ancora scoperta) e il presidio dbops.vw_fk_da_decidere.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_fk_senza_indice AS
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
          WHERE ((con.contype = 'f'::"char") AND dbops.fn_indici_schema_nell_ambito((nsp.nspname)::text))
        ), idx_prefix AS (
         SELECT ix.indrelid,
            p.n AS prefix_len,
            pg_get_expr(ix.indpred, ix.indrelid) AS predicato,
            ( SELECT array_agg(a.attname ORDER BY a.attname) AS array_agg
                   FROM (generate_series(1, p.n) g(k)
                     JOIN pg_attribute a ON (((a.attrelid = ix.indrelid) AND (a.attnum = ix.indkey[(g.k - 1)]))))) AS prefix_cols,
            ( SELECT bool_and((ix.indkey[(g.k - 1)] > 0)) AS bool_and
                   FROM generate_series(1, p.n) g(k)) AS solo_colonne
           FROM (((((pg_index ix
             JOIN pg_class i ON ((i.oid = ix.indexrelid)))
             JOIN pg_class t ON ((t.oid = ix.indrelid)))
             JOIN pg_namespace n ON ((n.oid = t.relnamespace)))
             JOIN pg_am am ON ((am.oid = i.relam)))
             CROSS JOIN LATERAL generate_series(1, (ix.indnkeyatts)::integer) p(n))
          WHERE ((i.relkind = 'i'::"char") AND (am.amname = 'btree'::name) AND ix.indisvalid AND ix.indisready AND dbops.fn_indici_schema_nell_ambito((n.nspname)::text))
        )
 SELECT fk.schema_name,
    fk.table_name,
    fk.constraint_name,
    fk.fk_cols,
    format('CREATE INDEX IF NOT EXISTS ix_%I_%s ON %I.%I(%s);'::text, fk.table_name, array_to_string(fk.fk_cols, '_'::text), fk.schema_name, fk.table_name, array_to_string(fk.fk_cols, ', '::text)) AS create_index_suggestion,
    pol.decisione
   FROM (fk_grouped fk
     LEFT JOIN dbops.fk_index_policy pol ON (((pol.schema_name = fk.schema_name) AND (pol.table_name = fk.table_name) AND (pol.constraint_name = fk.constraint_name))))
  WHERE (NOT (EXISTS ( SELECT 1
           FROM idx_prefix ip
          WHERE ((ip.indrelid = fk.conrelid) AND (ip.prefix_len = cardinality(fk.fk_cols)) AND ip.solo_colonne AND (ip.prefix_cols = fk.fk_cols) AND ((ip.predicato IS NULL) OR ( SELECT bool_and(((btrim(parte.parte, '() '::text) ~ '^"?[a-z_][a-z0-9_$]*"?[[:space:]]+IS NOT NULL$'::text) AND (replace(btrim(regexp_replace(parte.parte, '[[:space:]]+IS NOT NULL.*$'::text, ''::text), '() '::text), '"'::text, ''::text) = ANY (fk.fk_cols)))) AS bool_and
                   FROM regexp_split_to_table(ip.predicato, '[[:space:]]+AND[[:space:]]+'::text) parte(parte)))))))
  ORDER BY fk.schema_name, fk.table_name;
```

</div>


---
{% include-markdown "signature-core.md" %}
