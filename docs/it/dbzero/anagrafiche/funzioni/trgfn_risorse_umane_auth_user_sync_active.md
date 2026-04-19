{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_risorse_umane_auth_user_sync_active.md" %}
# ⚙️ Funzione `trgfn_risorse_umane_auth_user_sync_active`

```sql
CREATE FUNCTION trgfn_risorse_umane_auth_user_sync_active()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_sync_active()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Alla modifica di attivo sul bridge RUA (o all'inserimento
    -- di un nuovo collegamento), sincronizza auth_user.is_active
    -- usando la nuova firma (auth_user_id invece di
    -- risorsa_umana_id).
    PERFORM anagrafiche.fn_sync_auth_user_is_active(NEW.auth_user_id);
    RETURN NULL; -- AFTER trigger: ritorno ignorato
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_sync_active()
IS 'Trigger function: sincronizza auth_user.is_active al cambio stato del bridge RUA o al nuovo collegamento. Passa NEW.auth_user_id alla funzione sync (§4.5 WIP multi-face-auth).';
```

---
{% include-markdown "signature-core.md" %}
