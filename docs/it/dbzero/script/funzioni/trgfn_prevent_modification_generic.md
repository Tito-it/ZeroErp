{% include-markdown "it/dbzero/script/manual/trgfn_prevent_modification_generic.md" %}
# ⚙️ Funzione `trgfn_prevent_modification_generic`

```sql
CREATE FUNCTION trgfn_prevent_modification_generic()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.trgfn_prevent_modification_generic()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$

BEGIN
 
  PERFORM script.fn_log_and_raise_error(
      'database',
      'trgfn_prevent_parameters_audit_modification',
      'E_TABELLA_OP_NON_CONSENTITA',
      jsonb_build_object(
        'nome_tabella', TG_TABLE_NAME,
        'trigger_op',        TG_OP
      ),
      NULL::uuid,
      TG_TABLE_NAME::text,
      TG_OP::text
    );
END;
$function$
```
---
{% include-markdown "signature-core.md" %}
