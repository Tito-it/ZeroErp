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
-- ------------------------------------------------------------
-- Trigger function: trgfn_risorse_umane_auth_user_sync_active
--
-- Scopo:
--   Alla modifica di attivo su risorse_umane_auth_user o
--   all'inserimento di un nuovo bridge, sincronizza
--   auth_user.is_active tramite fn_sync_auth_user_is_active.
--
-- Evento: AFTER INSERT / AFTER UPDATE OF attivo
-- Tabella: anagrafiche.risorse_umane_auth_user
-- ------------------------------------------------------------

    PERFORM anagrafiche.fn_sync_auth_user_is_active(NEW.risorsa_umana_id);
    RETURN NULL; -- AFTER trigger, ritorno ignorato
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_sync_active()
IS 'Trigger function: sincronizza auth_user.is_active al cambio stato bridge o nuovo collegamento.';
```

---
{% include-markdown "signature-core.md" %}
