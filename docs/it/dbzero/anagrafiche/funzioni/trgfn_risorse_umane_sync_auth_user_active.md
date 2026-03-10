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
BEGIN
-- ------------------------------------------------------------
-- Trigger function: trgfn_risorse_umane_sync_auth_user_active
--
-- Scopo:
--   Alla modifica di attivo, valido_dal o valido_al su risorse_umane,
--   sincronizza auth_user.is_active tramite fn_sync_auth_user_is_active.
--   Esegue solo se la risorsa ha un collegamento in risorse_umane_auth_user.
--
-- Evento: AFTER UPDATE OF attivo, valido_dal, valido_al
-- Tabella: anagrafiche.risorse_umane
-- ------------------------------------------------------------

    -- Verifica se la risorsa ha un collegamento auth_user
    IF EXISTS (
        SELECT 1
          FROM anagrafiche.risorse_umane_auth_user rau
         WHERE rau.risorsa_umana_id = NEW.id
    ) THEN
        PERFORM anagrafiche.fn_sync_auth_user_is_active(NEW.id);
    END IF;

    RETURN NULL; -- AFTER trigger, ritorno ignorato
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_sync_auth_user_active()
IS 'Trigger function: sincronizza auth_user.is_active al cambio stato risorsa umana.';
```

---
{% include-markdown "signature-core.md" %}
