{% include-markdown "it/dbzero/dbops/manual/vw_lock_columns_vivi.md" %}
# 🔍 View `vw_lock_columns_vivi`

> 📝 **Descrizione**
>
> I trigger di lock di colonna VIVI: una riga per ogni trigger su script.trgfn_lock_columns, in qualunque schema e con qualunque nome, montato dal runner o a mano. argomenti = le coppie (colonna, codice d'errore) che il trigger controlla, lette da pg_trigger.tgargs con dbops.fn_trigger_argomenti; colonne_update_of = le colonne di UPDATE OF, che restringono quando il trigger scatta ma non che cosa blocca; abilitato = il trigger scatta nelle sessioni normali (tgenabled O o A). Sede unica della lettura del lock vivo: la leggono dbops.fn_lock_columns_divergenze (il confronto col registro) e dbops.vw_non_editable_fields (il form). Inventario, non allarme.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_lock_columns_vivi
WITH (security_invoker=true) AS
SELECT tg.tgrelid AS tabella_oid,
    (n.nspname)::text AS schema_name,
    (c.relname)::text AS table_name,
    (c.relkind)::text AS tipo_tabella,
    tg.oid AS trigger_oid,
    (tg.tgname)::text AS trigger_name,
    (tg.tgtype)::integer AS trigger_tipo,
    (tg.tgenabled = ANY (ARRAY['O'::"char", 'A'::"char"])) AS abilitato,
    dbops.fn_trigger_argomenti(tg.tgargs) AS argomenti,
    ARRAY( SELECT (a.attname)::text AS attname
           FROM (unnest((tg.tgattr)::smallint[]) k(attnum)
             JOIN pg_attribute a ON (((a.attrelid = tg.tgrelid) AND (a.attnum = k.attnum))))
          ORDER BY ((a.attname)::text)) AS colonne_update_of
   FROM ((pg_trigger tg
     JOIN pg_class c ON ((c.oid = tg.tgrelid)))
     JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
  WHERE ((NOT tg.tgisinternal) AND (tg.tgfoid = ('script.trgfn_lock_columns()'::regprocedure)::oid));
```

</div>


---
{% include-markdown "signature-core.md" %}
