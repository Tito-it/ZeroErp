{% include-markdown "it/dbzero/config/manual/trgfn_user_emittenti_fiscali_guard_delete.md" %}
# ⚙️ Funzione `trgfn_user_emittenti_fiscali_guard_delete`

```sql
CREATE FUNCTION trgfn_user_emittenti_fiscali_guard_delete()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.trgfn_user_emittenti_fiscali_guard_delete()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_is_active boolean;
BEGIN
    -- Override manutenzione (es. cleanup manuale autorizzato)
    IF current_setting('zeroerp.allow_user_emittente_delete_override', true) = 'on' THEN
        RETURN OLD;
    END IF;

    -- Stato attivo dell'utente Django associato.
    SELECT au.is_active
      INTO v_is_active
      FROM django.auth_user au
     WHERE au.id = OLD.auth_user_id;

    -- Se l'utente non esiste piu' (DELETE in cascata) consentiamo
    -- la rimozione del child: la cessazione e' implicita.
    IF v_is_active IS NULL THEN
        RETURN OLD;
    END IF;

    -- Utente ancora attivo => DELETE vietata.
    IF v_is_active = true THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_USER_EMITTENTE_DELETE_VIETATO',
            jsonb_build_object(
                'detail', 'DELETE su user_emittenti_fiscali consentita solo se l''utente e'' disattivato',
                'auth_user_id', OLD.auth_user_id,
                'emittente_fiscale_id', OLD.emittente_fiscale_id
            ),
            NULL::uuid,
            OLD.auth_user_id::text
        );
    END IF;

    RETURN OLD;
END
$function$

COMMENT ON FUNCTION config.trgfn_user_emittenti_fiscali_guard_delete()
IS 'Guard BEFORE DELETE su config.user_emittenti_fiscali: ammette la cancellazione solo se django.auth_user.is_active=false (cessazione utente). Override via GUC zeroerp.allow_user_emittente_delete_override=''on''. Solleva E_USER_EMITTENTE_DELETE_VIETATO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
