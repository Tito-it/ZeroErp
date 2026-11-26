{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_identita_digitali_sync_auth_user_active.md" %}
# ⚙️ Funzione `trgfn_identita_digitali_sync_auth_user_active`

```sql
CREATE FUNCTION trgfn_identita_digitali_sync_auth_user_active()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_identita_digitali_sync_auth_user_active()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo: dopo una scrittura su una veste, allinea
    --   auth_user.is_active della credenziale (o delle due
    --   credenziali, se la veste ha cambiato credenziale o se
    --   n'e' andata) con anagrafiche.fn_sync_auth_user_is_active.
    -- =========================================================
    IF TG_OP = 'DELETE'
       OR (TG_OP = 'UPDATE' AND OLD.auth_user_id IS DISTINCT FROM NEW.auth_user_id)
    THEN
        PERFORM anagrafiche.fn_sync_auth_user_is_active(OLD.auth_user_id);
    END IF;

    IF TG_OP <> 'DELETE' THEN
        PERFORM anagrafiche.fn_sync_auth_user_is_active(NEW.auth_user_id);
    END IF;

    RETURN NULL;  -- AFTER: ritorno ignorato
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_identita_digitali_sync_auth_user_active()
IS 'Trigger AFTER INSERT, UPDATE e DELETE su anagrafiche.identita_digitali: allinea django.auth_user.is_active con anagrafiche.fn_sync_auth_user_is_active (accesa se almeno una veste e'' utilizzabile oggi). All''INSERT e all''UPDATE sincronizza la credenziale della veste; al DELETE, e quando la veste passa a un''altra credenziale, anche quella di prima, che senza piu'' vesti utilizzabili si spegne. L''UPDATE scatta sulle colonne che script.fn_veste_utilizzabile legge: attivo, valido_dal, valido_al, ruolo_applicativo, auth_user_id, soggetto_ruolo_id, tecnica. Le date che arrivano senza scritture le riallinea anagrafiche.fn_sync_auth_user_expired.';
```

</div>

---
{% include-markdown "signature-core.md" %}
