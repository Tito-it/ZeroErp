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
    -- =========================================================
    -- Verifica SUPER_ADMIN operatore: ritorna true se esiste
    -- un'identita OPERATORE attiva per l'auth_user con un
    -- binding attivo a un profilo SUPER_ADMIN attivo.
    -- Post 20-04-2026 il filtro ruolo_applicativo=OPERATORE
    -- rende la fn coerente col modello multi-veste: un
    -- user con OPERATORE+SUPER_ADMIN + CLIENTE_PORTALE non
    -- eredita il bypass in contesto portale.
    -- Fail-closed: NULL o identita inesistente/inattiva
    -- -> false.
    -- =========================================================
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali id
          JOIN config.profili_accesso_bindings pab
            ON pab.identita_digitale_id = id.id
          JOIN config.profili_accesso pa
            ON pa.id = pab.profilo_accesso_id
         WHERE id.auth_user_id      = p_auth_user_id
           AND id.attivo            = true
           AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
           AND (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
           AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
           AND pab.attivo = true
           AND pa.attivo  = true
           AND pa.tipo    = 'SUPER_ADMIN'::config.tipo_profilo_accesso
    );
$function$

COMMENT ON FUNCTION script.fn_is_super_admin(p_auth_user_id integer)
IS 'SUPER_ADMIN check ristretto a identita OPERATORE (post 20-04-2026). Ritorna true se l''auth_user ha un''identita OPERATORE attiva nella finestra temporale con binding a profilo tipo SUPER_ADMIN attivo. Coerente con modello SSO multi-veste: il bypass non si attiva in contesti non-operatore. STABLE, inlineable, fail-closed.';
```

---
{% include-markdown "signature-core.md" %}
