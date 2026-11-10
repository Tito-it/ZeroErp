{% include-markdown "it/dbzero/dbops/manual/fn_indici_schema_nell_ambito.md" %}
# ⚙️ Funzione `fn_indici_schema_nell_ambito`

```sql
CREATE FUNCTION fn_indici_schema_nell_ambito(p_schema text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_indici_schema_nell_ambito(p_schema text)
 RETURNS boolean
 LANGUAGE sql
 STABLE PARALLEL SAFE
AS $function$
  SELECT EXISTS (SELECT 1
                   FROM dbops.automation_scope sc
                  WHERE sc.schema_name = p_schema);
$function$

COMMENT ON FUNCTION dbops.fn_indici_schema_nell_ambito(p_schema text)
IS 'Vero se lo schema e'' governato dalla politica degli indici delle FK: ha almeno una riga in dbops.automation_scope, qualunque sia table_like. La politica governa per schema, di proposito: l''indice di una FK serve a ogni tabella, mentre l''elenco delle tabelle serve ai trigger delle altre automazioni (dbops.fn_table_in_scope). La leggono dbops.vw_fk_senza_indice, dbops.vw_indici_ridondanti_prefisso, dbops.vw_duplicate_indexes, dbops.vw_fk_da_decidere e dbops.apply_fk_index_policy. Uno schema senza righe e'' fuori, e un NULL da'' falso.';
```

</div>

---
{% include-markdown "signature-core.md" %}
