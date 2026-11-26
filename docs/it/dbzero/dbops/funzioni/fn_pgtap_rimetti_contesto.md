{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_rimetti_contesto.md" %}
# ⚙️ Funzione `fn_pgtap_rimetti_contesto`

```sql
CREATE FUNCTION fn_pgtap_rimetti_contesto(p_prima jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_rimetti_contesto(p_prima jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: in un pgTAP, rimettere il contesto che
--   dbops.fn_pgtap_entra_come_super_admin ha restituito.
BEGIN
    IF p_prima IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_rimetti_contesto: manca il contesto di prima';
    END IF;

    PERFORM set_config('app.current_user_id', COALESCE(p_prima ->> 'utente', ''), false);
    PERFORM set_config('app.ruolo_applicativo', COALESCE(p_prima ->> 'ruolo', ''), false);
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_rimetti_contesto(p_prima jsonb)
IS 'Fixture dei pgTAP: rimette il contesto che dbops.fn_pgtap_entra_come_super_admin ha restituito: app.current_user_id e app.ruolo_applicativo tornano com''erano, anche vuoti. Un argomento NULL solleva: un builder che lo passa ha perso il contesto di prima.';
```

</div>

---
{% include-markdown "signature-core.md" %}
