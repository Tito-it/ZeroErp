{% include-markdown "it/dbzero/script/manual/trgfn_audit_data_user_generic.md" %}
# ⚙️ Funzione `trgfn_audit_data_user_generic`

```sql
CREATE FUNCTION trgfn_audit_data_user_generic()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_audit_data_user_generic()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Audit automatico su INSERT e UPDATE.
  --   Usa la GUC app.jwt_user impostata dal middleware Django
  --   per registrare l'utente reale (JWT).
  --   Fallback a CURRENT_USER se la GUC non e` impostata
  --   (script, cron, psql).
  --
  -- Regole:
  --   - INSERT: imposta user_insert + data_update/user_update
  --   - UPDATE: imposta solo data_update/user_update
  --   - current_setting(..., true): no errore se GUC assente
  -- =========================================================

  IF TG_OP = 'INSERT' THEN
    NEW.user_insert := COALESCE(
      NULLIF(current_setting('app.jwt_user', true), ''),
      CURRENT_USER
    );
  END IF;

  NEW.data_update := CURRENT_TIMESTAMP;
  NEW.user_update := COALESCE(
    NULLIF(current_setting('app.jwt_user', true), ''),
    CURRENT_USER
  );
  RETURN NEW;
END
$function$

COMMENT ON FUNCTION script.trgfn_audit_data_user_generic()
IS 'Audit data/user su INSERT e UPDATE. Usa GUC app.jwt_user (JWT reale) con fallback CURRENT_USER.';
```

</div>

---
{% include-markdown "signature-core.md" %}
