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
    -- Scopo:
    --   Impedire le scritture su identita_digitali che
    --   lascerebbero il sistema senza un SUPER_ADMIN SENZA
    --   SCADENZA (script.fn_check_almeno_un_super_admin_attivo).
    --
    -- Regole:
    --   1. Short-circuit: solo le scritture che RIDUCONO la
    --      garanzia — spegnere la veste, darle una data di fine,
    --      spostarne l'inizio nel futuro. Rev 2026-10-07
    --      (brief-db-veste-utilizzabile, decisione di Tid): prima
    --      solo lo spegnimento, e il calendario passava.
    --   2. Short-circuit 2: solo se la veste porta un binding
    --      SUPER_ADMIN attivo. Altrimenti la garanzia non cambia.
    --   3. Se a rischio, verifica post-stato via fn_check.
    --      Se false, raise E_PROFILO_ULTIMO_SUPER_ADMIN.
    --
    -- rev 2026-06-29: profilo SUPER_ADMIN identificato per l'enum
    --   stabile tipo invece che per codice (mutabile) -- §4a.
    -- =========================================================

    IF NOT (   (OLD.attivo AND NOT NEW.attivo)
            OR (OLD.valido_al IS NULL AND NEW.valido_al IS NOT NULL)
            OR (OLD.valido_dal <= (SELECT script.fn_data_operativa()) AND NEW.valido_dal > (SELECT script.fn_data_operativa())))
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
IS 'Guard anti-lockout sulla veste (AFTER UPDATE di attivo, valido_dal, valido_al): rifiuta una scrittura che riduce la garanzia di una veste con binding SUPER_ADMIN attivo (spegnerla, darle una data di fine, spostarne l''inizio nel futuro) se dopo non resta nessun SUPER_ADMIN senza scadenza (script.fn_check_almeno_un_super_admin_attivo). Le scritture che migliorano non si fermano mai. Codice E_PROFILO_ULTIMO_SUPER_ADMIN. rev 2026-06-29: tipo invece di codice (§4a). Rev 2026-10-07 (brief-db-veste-utilizzabile, decisione di Tid): anche le date, perche'' il calendario non scrive e una data di fine messa all''ultimo amministratore lo avrebbe fatto scadere senza che nessun guard lo vedesse.';
```

</div>

---
{% include-markdown "signature-core.md" %}
