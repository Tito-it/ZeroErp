{% include-markdown "it/dbzero/vendite/manual/trgfn_attivita_fatturabili_guard_commessa.md" %}
# ⚙️ Funzione `trgfn_attivita_fatturabili_guard_commessa`

```sql
CREATE FUNCTION trgfn_attivita_fatturabili_guard_commessa()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_fatturabili_guard_commessa()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_guard_enabled BOOLEAN := FALSE;
    v_bypass_setting TEXT;
    v_bypass_enabled BOOLEAN := FALSE;
    v_is_superuser BOOLEAN := FALSE;
    v_commessa_from_attivita vendite.commesse_attivita.commessa_id%TYPE;
BEGIN
    -- Config flag
    BEGIN
        SELECT COALESCE(NULLIF(btrim(p.default_value), ''), 'false')::BOOLEAN INTO v_guard_enabled
          FROM config.parameters p WHERE p.code = 'attivita_fatturabili_require_commessa' LIMIT 1;
    EXCEPTION WHEN OTHERS THEN v_guard_enabled := FALSE;
    END;

    -- Bypass solo superuser
    BEGIN
        SELECT usesuper INTO v_is_superuser FROM pg_user WHERE usename = current_user;
    EXCEPTION WHEN OTHERS THEN v_is_superuser := FALSE;
    END;

    IF v_is_superuser THEN
        BEGIN
            v_bypass_setting := current_setting('zeroerp.maintenance_allow_attivita_bypass', TRUE);
            IF v_bypass_setting IS NOT NULL AND btrim(v_bypass_setting) <> '' THEN v_bypass_enabled := v_bypass_setting::BOOLEAN; END IF;
        EXCEPTION WHEN OTHERS THEN v_bypass_enabled := FALSE;
        END;
    END IF;

    IF v_bypass_enabled OR NOT v_guard_enabled THEN RETURN NEW; END IF;

    -- Guard: coppia obbligatoria
    IF (NEW.commessa_id IS NULL AND NEW.commessa_attivita_id IS NOT NULL)
       OR (NEW.commessa_id IS NOT NULL AND NEW.commessa_attivita_id IS NULL) THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'trgfn_attivita_fatturabili_guard_commessa', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('commessa_id', NEW.commessa_id, 'commessa_attivita_id', NEW.commessa_attivita_id),
            NULL::uuid, 'commessa_id e commessa_attivita_id devono essere valorizzati a coppia');
    END IF;

    -- Guard: commessa obbligatoria
    IF NEW.commessa_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'trgfn_attivita_fatturabili_guard_commessa', 'E_COMMESSA_ATTIVITA_NON_COERENTE',
            jsonb_build_object('attivita_id', NEW.id), NULL::uuid, 'inserimento senza commessa non consentito');
    END IF;

    -- Guard: commessa_attivita_id deve esistere
    SELECT ca.commessa_id INTO v_commessa_from_attivita
      FROM vendite.commesse_attivita ca WHERE ca.id = NEW.commessa_attivita_id;

    IF v_commessa_from_attivita IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'trgfn_attivita_fatturabili_guard_commessa', 'E_COMMESSA_ATTIVITA_NON_COERENTE',
            jsonb_build_object('commessa_attivita_id', NEW.commessa_attivita_id), NULL::uuid, concat('commessa_attivita_id ', NEW.commessa_attivita_id, ' non trovata'));
    END IF;

    -- Guard: coerenza commessa_id ↔ commessa_attivita_id
    IF v_commessa_from_attivita <> NEW.commessa_id THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'trgfn_attivita_fatturabili_guard_commessa', 'E_COMMESSA_ATTIVITA_NON_COERENTE',
            jsonb_build_object('commessa_id', NEW.commessa_id, 'commessa_attivita_id', NEW.commessa_attivita_id, 'commessa_attesa', v_commessa_from_attivita),
            NULL::uuid, concat('attivita ', NEW.commessa_attivita_id, ' appartiene a commessa ', v_commessa_from_attivita, ' non a ', NEW.commessa_id));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_attivita_fatturabili_guard_commessa()
IS 'Guard anti-bypass: commessa_id+commessa_attivita_id obbligatori e coerenti. Bypass GUC solo superuser.';
```

</div>

---
{% include-markdown "signature-core.md" %}
