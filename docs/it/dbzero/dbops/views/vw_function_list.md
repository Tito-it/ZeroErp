{% include-markdown "it/dbzero/dbops/manual/vw_function_list.md" %}
# 🔍 View `vw_function_list`

> 📝 **Descrizione**
>
> Elenco completo delle funzioni negli schemi dbops e script. Include:
> - OID per identificare overload
> - Argomenti e tipo di ritorno
> - Numero di argomenti
> - Commenti/documentazione (se presenti)

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_function_list AS
SELECT n.nspname AS schema,
    p.oid AS function_oid,
    p.proname AS function_name,
    pg_get_function_arguments(p.oid) AS arguments,
    pg_get_function_result(p.oid) AS return_type,
    array_length(string_to_array(pg_get_function_arguments(p.oid), ','::text), 1) AS num_args,
    d.description AS comment
   FROM ((pg_proc p
     JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
     LEFT JOIN pg_description d ON ((p.oid = d.objoid)))
  WHERE (n.nspname = ANY (ARRAY['dbops'::name, 'script'::name]));
```

</div>


---
{% include-markdown "signature-core.md" %}
