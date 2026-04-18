{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_risorse_umane_sync_auth_user_active.md" %}
# ⚙️ Funzione `trgfn_risorse_umane_sync_auth_user_active`

```sql
CREATE FUNCTION trgfn_risorse_umane_sync_auth_user_active()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_risorse_umane_sync_auth_user_active()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- %TYPE sulle colonne sorgente (policy ZeroErp).
    v_auth_user_id anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE;
BEGIN
    -- Risolve l'auth_user_id dal bridge. Se la risorsa non ha
    -- collegamento, il LIMIT 1 + FOUND salta il sync (nessun
    -- auth_user da aggiornare).
    SELECT rau.auth_user_id
      INTO v_auth_user_id
      FROM anagrafiche.risorse_umane_auth_user rau
     WHERE rau.risorsa_umana_id = NEW.id
     LIMIT 1;

    IF FOUND THEN
        PERFORM anagrafiche.fn_sync_auth_user_is_active(v_auth_user_id);
    END IF;

    RETURN NULL; -- AFTER trigger: ritorno ignorato
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_sync_auth_user_active()
IS 'Trigger function: sincronizza auth_user.is_active al cambio stato/finestra di risorse_umane. Risolve auth_user_id dal bridge RUA e delega a fn_sync_auth_user_is_active. (§4.5 WIP).';
```

---
{% include-markdown "signature-core.md" %}
