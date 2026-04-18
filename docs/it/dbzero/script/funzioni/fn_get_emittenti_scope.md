{% include-markdown "it/dbzero/script/manual/fn_get_emittenti_scope.md" %}
# ⚙️ Funzione `fn_get_emittenti_scope`

```sql
CREATE FUNCTION fn_get_emittenti_scope(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_emittenti_scope(p_auth_user_id integer)
 RETURNS bigint[]
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_ids bigint[];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Restituisce gli ID emittenti fiscali autorizzati
    --   per un utente dalla whitelist user_emittenti_fiscali.
    --
    -- Semantica:
    --   NULL  = nessuna restrizione (whitelist vuota, vede tutto)
    --   array = limitato agli emittenti elencati
    --
    -- Nota §4.6.B.7: il gate DISABILITATO/ADMIN non e'
    -- applicato qui. ZeroERPPermission blocca DISABILITATO
    -- prima della chiamata; SUPER_ADMIN bypassa via NULL
    -- (whitelist vuota = vede tutto).
    -- =========================================================

    SELECT array_agg(uef.emittente_fiscale_id)
      INTO v_ids
      FROM config.user_emittenti_fiscali uef
     WHERE uef.auth_user_id = p_auth_user_id;

    -- Nessuna riga -> array_agg ritorna NULL -> nessuna restrizione
    RETURN v_ids;
END
$function$

COMMENT ON FUNCTION script.fn_get_emittenti_scope(p_auth_user_id integer)
IS 'Restituisce ID emittenti autorizzati per utente (NULL = nessuna restrizione). Refactor §4.6.B.7: firma slegata dal bridge legacy risorse_umane_auth_user.';
```

---
{% include-markdown "signature-core.md" %}
