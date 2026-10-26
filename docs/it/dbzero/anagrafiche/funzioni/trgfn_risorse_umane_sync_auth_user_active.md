{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_risorse_umane_sync_auth_user_active.md" %}
# ⚙️ Funzione `trgfn_risorse_umane_sync_auth_user_active`

```sql
CREATE FUNCTION trgfn_risorse_umane_sync_auth_user_active()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_risorse_umane_sync_auth_user_active()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- %TYPE sulle colonne sorgente (policy ZeroErp).
    v_auth_user_id anagrafiche.identita_digitali.auth_user_id%TYPE;
BEGIN
    -- Risolve l'auth_user_id dalla madre identita_digitali via
    -- l'helper condiviso (12-09-2026: la vista risorse_umane_auth_user
    -- e' stata ritirata). NULL = risorsa senza collegamento: nessun
    -- auth_user da aggiornare, il sync si salta.
    v_auth_user_id := script.fn_get_auth_user_id_for_risorsa_umana(NEW.id);

    IF v_auth_user_id IS NOT NULL THEN
        PERFORM anagrafiche.fn_sync_auth_user_is_active(v_auth_user_id);
    END IF;

    RETURN NULL; -- AFTER trigger: ritorno ignorato
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_sync_auth_user_active()
IS 'Trigger function: sincronizza auth_user.is_active al cambio stato/finestra di risorse_umane. Risolve l''auth_user da identita_digitali con script.fn_get_auth_user_id_for_risorsa_umana (dal 12-09-2026: la vista risorse_umane_auth_user e'' stata ritirata) e delega a fn_sync_auth_user_is_active.';
```

</div>

---
{% include-markdown "signature-core.md" %}
