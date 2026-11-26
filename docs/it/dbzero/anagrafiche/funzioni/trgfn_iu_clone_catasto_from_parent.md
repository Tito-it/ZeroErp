{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_iu_clone_catasto_from_parent.md" %}
# ⚙️ Funzione `trgfn_iu_clone_catasto_from_parent`

```sql
CREATE FUNCTION trgfn_iu_clone_catasto_from_parent()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_iu_clone_catasto_from_parent()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Idempotenza e logica principale sono dentro la funzione clone
  PERFORM script.fn_clone_catasto_from_parent_by_istanza(NEW.id);
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_iu_clone_catasto_from_parent()
IS 'Trigger AFTER su anagrafiche.istanze_utilities, quando nasce il legame con l''istanza precedente (all''INSERT con parent_istanza_id, all''UPDATE che lo cambia), con unita'' vuota e civico presente: clona l''unita'' catastale della precedente sull''istanza (script.fn_clone_catasto_from_parent_by_istanza, idempotente). Il clone copia cio'' che la precedente ha quando il legame nasce: un''unita'' che compare dopo sulla precedente non arriva, e l''istanza che ha gia'' l''unita'' la tiene. La regola sta nella guida catasto-delle-istanze.';
```

</div>

---
{% include-markdown "signature-core.md" %}
