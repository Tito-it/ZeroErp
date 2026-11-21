{% include-markdown "it/dbzero/ui/manual/fn_dimensione_max_ammessa.md" %}
# ⚙️ Funzione `fn_dimensione_max_ammessa`

```sql
CREATE FUNCTION fn_dimensione_max_ammessa(p_valore integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_dimensione_max_ammessa(p_valore integer)
 RETURNS boolean
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    SELECT COALESCE(p_valore BETWEEN 1 AND 100, false);
$function$

COMMENT ON FUNCTION ui.fn_dimensione_max_ammessa(p_valore integer)
IS 'Vero se il numero di card della home è ammesso: da 1 a 100. NULL e ogni altro valore: falso. «Nessun tetto» non esiste: una dashboard ha sempre un massimo. La leggono il guard di forma delle preferenze (ui.fn_check_forma_configurazione, chiave dimensione_max) e ui.fn_resolve_dashboard_config, che a un valore non ammesso preferisce quello del preset o del catalogo. IMMUTABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
