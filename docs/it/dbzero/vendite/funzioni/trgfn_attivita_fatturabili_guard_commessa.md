{% include-markdown "it/dbzero/vendite/manual/trgfn_attivita_fatturabili_guard_commessa.md" %}
# ⚙️ Funzione `trgfn_attivita_fatturabili_guard_commessa`

```sql
CREATE FUNCTION trgfn_attivita_fatturabili_guard_commessa()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_fatturabili_guard_commessa()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_bypass_setting text;
    v_bypass_enabled boolean := false;
    v_is_superuser boolean := false;
    v_commessa_from_attivita vendite.commesse_attivita.commessa_id%TYPE;
BEGIN
    -- Bypass di manutenzione: solo superuser, con la GUC accesa.
    BEGIN
        SELECT usesuper INTO v_is_superuser FROM pg_user WHERE usename = current_user;
    EXCEPTION WHEN OTHERS THEN v_is_superuser := false;
    END;

    IF v_is_superuser THEN
        BEGIN
            v_bypass_setting := current_setting('zeroerp.maintenance_allow_attivita_bypass', true);
            IF v_bypass_setting IS NOT NULL AND btrim(v_bypass_setting) <> '' THEN
                v_bypass_enabled := v_bypass_setting::boolean;
            END IF;
        EXCEPTION WHEN OTHERS THEN v_bypass_enabled := false;
        END;
    END IF;

    IF v_bypass_enabled THEN
        RETURN NEW;
    END IF;

    -- Una delle due colonne vuota: la rifiuta il NOT NULL, che nomina la colonna.
    IF NEW.commessa_id IS NULL OR NEW.commessa_attivita_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- La riga di commessa esiste?
    SELECT ca.commessa_id INTO v_commessa_from_attivita
      FROM vendite.commesse_attivita ca WHERE ca.id = NEW.commessa_attivita_id;

    IF v_commessa_from_attivita IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'trgfn_attivita_fatturabili_guard_commessa', 'E_COMMESSA_ATTIVITA_NON_COERENTE',
            jsonb_build_object('commessa_attivita_id', NEW.commessa_attivita_id), NULL::uuid,
            concat('commessa_attivita_id ', NEW.commessa_attivita_id, ' non trovata'));
    END IF;

    -- E appartiene alla commessa dichiarata?
    IF v_commessa_from_attivita <> NEW.commessa_id THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'trgfn_attivita_fatturabili_guard_commessa', 'E_COMMESSA_ATTIVITA_NON_COERENTE',
            jsonb_build_object('commessa_id', NEW.commessa_id, 'commessa_attivita_id', NEW.commessa_attivita_id, 'commessa_attesa', v_commessa_from_attivita),
            NULL::uuid, concat('attivita ', NEW.commessa_attivita_id, ' appartiene a commessa ', v_commessa_from_attivita, ' non a ', NEW.commessa_id));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_attivita_fatturabili_guard_commessa()
IS 'Guard BEFORE INSERT OR UPDATE OF commessa_id, commessa_attivita_id su vendite.attivita_fatturabili: la riga di commessa dell''attivita'' (commessa_attivita_id) esiste e appartiene alla commessa dichiarata (commessa_id); altrimenti E_COMMESSA_ATTIVITA_NON_COERENTE. Controlla sempre: non dipende da un parametro. Le due colonne vuote le rifiuta il loro NOT NULL, non il guard. Bypass di manutenzione solo per un superuser con la GUC zeroerp.maintenance_allow_attivita_bypass accesa.';
```

</div>

---
{% include-markdown "signature-core.md" %}
