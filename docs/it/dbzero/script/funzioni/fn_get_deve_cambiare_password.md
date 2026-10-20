{% include-markdown "it/dbzero/script/manual/fn_get_deve_cambiare_password.md" %}
# ⚙️ Funzione `fn_get_deve_cambiare_password`

```sql
CREATE FUNCTION fn_get_deve_cambiare_password(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_deve_cambiare_password(p_auth_user_id integer)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il cambio password obbligatorio della credenziale. La riga nasce
--   alla prima scrittura: la sua ASSENZA vale false, e questa e' la sola
--   sede di quel default.
DECLARE
    v_valore config.credenziali.deve_cambiare_password%TYPE;
BEGIN
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_deve_cambiare_password', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_auth_user_id', 'valore', p_auth_user_id),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_get_deve_cambiare_password',
                           'credenziale assente o non valida']);
    END IF;

    SELECT c.deve_cambiare_password
      INTO v_valore
      FROM config.credenziali c
     WHERE c.auth_user_id = p_auth_user_id;

    RETURN COALESCE(v_valore, false);
END;
$function$

COMMENT ON FUNCTION script.fn_get_deve_cambiare_password(p_auth_user_id integer)
IS 'Cambio password obbligatorio della CREDENZIALE (D-7: la password e'' una). La riga di config.credenziali nasce alla prima scrittura e la sua assenza vale false: questa e'' la sola sede di quel default (regola del 2), e la chiamano script.fn_get_user_profile, script.fn_get_operatore_detail e il backend. Parametro: django.auth_user.id (integer esplicito, niente %TYPE su Django); NULL o <= 0 -> E_AUTH_CHIAMATA_NON_VALIDA. INVOKER, STABLE. Brief: brief-db-blocco-login-per-credenziale §3.4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
