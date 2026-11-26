{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_identita_digitali_guard_ultimo_super_admin.md" %}
# ⚙️ Funzione `trgfn_identita_digitali_guard_ultimo_super_admin`

```sql
CREATE FUNCTION trgfn_identita_digitali_guard_ultimo_super_admin()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_was_super_admin boolean := false;  -- esito di un EXISTS: nessuna colonna dietro
BEGIN
    -- =========================================================
    -- Scopo: il sistema non resta senza un SUPER_ADMIN senza
    --   scadenza. Rifiuta la scrittura sulla veste di un
    --   amministratore che lo lascerebbe senza: spegnerla,
    --   darle una fine, spostarne l'inizio nel futuro, o
    --   spostarla (credenziale, ruolo anagrafico, tipo, tecnica).
    -- =========================================================
    IF NOT (   (OLD.attivo AND NOT NEW.attivo)
            OR (OLD.valido_al IS NULL AND NEW.valido_al IS NOT NULL)
            OR (OLD.valido_dal <= (SELECT script.fn_data_operativa())
                AND NEW.valido_dal > (SELECT script.fn_data_operativa()))
            OR (NEW.auth_user_id, NEW.soggetto_ruolo_id, NEW.ruolo_applicativo, NEW.tecnica)
               IS DISTINCT FROM
               (OLD.auth_user_id, OLD.soggetto_ruolo_id, OLD.ruolo_applicativo, OLD.tecnica))
    THEN
        RETURN NULL;
    END IF;

    SELECT EXISTS (
        SELECT 1
          FROM config.profili_accesso_bindings pab
          JOIN config.profili_accesso          pa
            ON pa.id = pab.profilo_accesso_id
         WHERE pab.identita_digitale_id = OLD.id
           AND pab.attivo = true
           AND pa.tipo    = 'SUPER_ADMIN'::config.tipo_profilo_accesso
           AND pa.attivo  = true
    )
    INTO v_was_super_admin;

    IF NOT v_was_super_admin THEN
        RETURN NULL;
    END IF;

    IF NOT script.fn_check_almeno_un_super_admin_attivo() THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            TG_NAME,
            'E_PROFILO_ULTIMO_SUPER_ADMIN',
            jsonb_build_object(
                'op', TG_OP,
                'identita_digitale_id', OLD.id,
                'auth_user_id', OLD.auth_user_id,
                'auth_user_id_nuovo', NEW.auth_user_id,
                'ruolo_applicativo', OLD.ruolo_applicativo,
                'attivo', NEW.attivo,
                'valido_dal', NEW.valido_dal,
                'valido_al', NEW.valido_al
            ),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]
        );
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin()
IS 'Guard anti-lockout sulla veste (AFTER UPDATE di attivo, valido_dal, valido_al, auth_user_id, soggetto_ruolo_id, ruolo_applicativo, tecnica): rifiuta una scrittura sulla veste con binding SUPER_ADMIN attivo che la spegne, le da'' una data di fine, ne sposta l''inizio nel futuro, o la sposta su un''altra credenziale, un altro ruolo anagrafico, un altro tipo o la fa tecnica, se dopo non resta nessun SUPER_ADMIN senza scadenza (script.fn_check_almeno_un_super_admin_attivo, che conosce credenziale bloccata, rapporto e utilizzabilita''). Le scritture che migliorano non si fermano mai. Codice E_PROFILO_ULTIMO_SUPER_ADMIN. Gemello di anagrafiche.trgfn_risorse_umane_guard_ultimo_super_admin e del guard dei binding.';
```

</div>

---
{% include-markdown "signature-core.md" %}
