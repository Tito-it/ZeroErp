{% include-markdown "it/dbzero/script/manual/fn_is_super_admin.md" %}
# ⚙️ Funzione `fn_is_super_admin`

```sql
CREATE FUNCTION fn_is_super_admin(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_is_super_admin(p_auth_user_id integer)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- EXISTS su JOIN identita_digitali + profili_accesso_bindings
    -- + profili_accesso. Filtri:
    --   - identita attiva, in finestra temporale, non
    --     DISABILITATO
    --   - binding attivo
    --   - profilo attivo, tipo SUPER_ADMIN
    -- Fail-closed se p_auth_user_id e' NULL (la EXISTS
    -- restituisce false).
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali id
          JOIN config.profili_accesso_bindings pab
            ON pab.identita_digitale_id = id.id
          JOIN config.profili_accesso pa
            ON pa.id = pab.profilo_accesso_id
         WHERE id.auth_user_id = p_auth_user_id
           AND id.attivo = true
           AND id.ruolo_applicativo <> 'DISABILITATO'
           AND (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
           AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
           AND pab.attivo = true
           AND pa.attivo  = true
           AND pa.tipo    = 'SUPER_ADMIN'::config.tipo_profilo_accesso
    );
$function$

COMMENT ON FUNCTION script.fn_is_super_admin(p_auth_user_id integer)
IS 'Verifica se l''utente ha privilegio SUPER_ADMIN (bypass totale permessi) tramite binding attivo a profilo con tipo SUPER_ADMIN su identita digitale attiva e nella finestra temporale. Sostituisce il check ruolo_sistema=ADMIN legacy (§4.6 WIP multi-face-auth). LANGUAGE sql STABLE: inlineable, cache-friendly, fail-closed.';
```

---
{% include-markdown "signature-core.md" %}
