{% include-markdown "it/dbzero/script/manual/fn_get_auth_user_id_for_email.md" %}
# ⚙️ Funzione `fn_get_auth_user_id_for_email`

```sql
CREATE FUNCTION fn_get_auth_user_id_for_email(p_email text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_auth_user_id_for_email(p_email text)
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dire quale credenziale (django.auth_user.id) porta questa email,
--   senza distinguere maiuscole e minuscole. NULL se nessuna.
-- Uso: v_auth_user_id := script.fn_get_auth_user_id_for_email(p_email);
DECLARE
    -- integer esplicito: e' django.auth_user.id (niente %TYPE su Django).
    v_id  integer;
    v_n   integer;
BEGIN
    -- Un'email vuota non e' una chiave: nessuna credenziale la «porta».
    IF p_email IS NULL OR btrim(p_email) = '' THEN
        RETURN NULL;
    END IF;

    -- ⭐ Stessa espressione e stesso predicato dell'indice unico
    --   ix_auth_user_email_lower_unique: lower(email) WHERE email <> ''.
    SELECT count(*), min(au.id)
      INTO v_n, v_id
      FROM django.auth_user au
     WHERE lower(au.email) = lower(btrim(p_email))
       AND au.email <> '';

    -- ⛔ Due credenziali con la stessa email: non se ne sceglie una.
    IF v_n > 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_get_auth_user_id_for_email',
            'E_CREDENZIALE_EMAIL_AMBIGUA',
            jsonb_build_object('email',        lower(btrim(p_email)),
                               'credenziali',  v_n),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION script.fn_get_auth_user_id_for_email(p_email text)
IS 'Building block: la credenziale (django.auth_user.id) che porta questa email, senza distinguere maiuscole e minuscole (D-9 di brief-db-blocco-login-per-credenziale: l''email e'' la chiave d''ingresso di portale e shop). Confronto lower(email) = lower(btrim(p_email)) su email <> '''': stessa espressione e stesso predicato dell''indice unico ix_auth_user_email_lower_unique, che la serve. Email NULL o vuota -> NULL (la stringa vuota e'' l''email mancante nel modello di Django, non una chiave). Due credenziali con la stessa email -> E_CREDENZIALE_EMAIL_AMBIGUA (TECNICO): dove l''indice non c''e'' (CI) il modello le ammette, e sceglierne una sarebbe un''ambiguita'', non una scelta. Consumatori: anagrafiche.fn_crea_auth_user (guard di unicita''), anagrafiche.fn_crea_operatore_v2 (riuso della credenziale, D-6), il backend dell''invito portale/shop. plpgsql e tipi espliciti perche'' nomina django.*. INVOKER, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
