{% include-markdown "it/dbzero/script/manual/fn_guard_soggetto_ruolo.md" %}
# ⚙️ Funzione `fn_guard_soggetto_ruolo`

```sql
CREATE FUNCTION fn_guard_soggetto_ruolo(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_cd_int_ruolo character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_guard_soggetto_ruolo(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_cd_int_ruolo character varying)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo_ruolo_id  integer;
    v_count          integer;

BEGIN
    -- ------------------------------------------------------------
    -- Funzione di supporto per validare che un soggetto_ruolo_id sia coerente
    -- con il ruolo atteso (p_cd_int_ruolo) e, se specificato, con il soggetto (p_soggetto_id).
    --  In caso di incoerenza, utilizza script.fn_log_and_raise_error e solleva eccezione.
    -- In caso di esito positivo, restituisce p_soggetto_ruolo_id.
    -- Il parametro p_soggetto_id è opzionale: se NULL, non viene verificato.
    -- ------------------------------------------------------------

    -- 1) Validazione parametri minimi
    IF p_soggetto_ruolo_id IS NULL OR p_soggetto_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_guard_soggetto_ruolo',
            'E_SOGGETTI_RUOLI',
            jsonb_build_object(
                'soggetto_ruolo_id', p_soggetto_ruolo_id,
                'soggetto_id', p_soggetto_id,
                'codice_interno_ruolo', p_cd_int_ruolo
            ),
            NULL::uuid,
            coalesce(p_soggetto_ruolo_id::text, 'NULL'),
            coalesce(p_soggetto_id::text, 'NULL'),
            coalesce(p_cd_int_ruolo::text, 'NULL')
        );

    END IF;

    -- 2) Risolvo l'ID del ruolo da config.tipi_ruoli
    SELECT r.id
    INTO v_tipo_ruolo_id
    FROM config.tipi_ruoli r
    WHERE r.codice_interno = p_cd_int_ruolo
    LIMIT 1;

    IF v_tipo_ruolo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_guard_soggetto_ruolo',
            'E_COD_INT_RUOLO',
            jsonb_build_object('codice_interno', p_cd_int_ruolo),
            NULL::uuid,
            'codice_interno', coalesce(p_cd_int_ruolo::text, 'NULL')
        );

    END IF;

    -- 3) Verifica esistenza e coerenza del legame in anagrafiche.soggetti_ruoli
    IF p_soggetto_id IS NULL THEN
        -- Controllo solo id + ruolo_id
        SELECT COUNT(*)
        INTO v_count
        FROM anagrafiche.soggetti_ruoli sr
        WHERE sr.id       = p_soggetto_ruolo_id
        AND sr.tipo_ruolo_id = v_tipo_ruolo_id;
    ELSE
        -- Controllo anche soggetto_id
        SELECT COUNT(*)
        INTO v_count
        FROM anagrafiche.soggetti_ruoli sr
        WHERE sr.id          = p_soggetto_ruolo_id
        AND sr.tipo_ruolo_id    = v_tipo_ruolo_id
        AND sr.soggetto_id = p_soggetto_id;
    END IF;

    IF v_count = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_guard_soggetto_ruolo',
            'E_SOGGETTI_RUOLI',
            jsonb_build_object(
                'soggetto_ruolo_id', p_soggetto_ruolo_id,
                'soggetto_id',       p_soggetto_id,
                'ruolo_id',          v_tipo_ruolo_id,
                'codice_interno',    p_cd_int_ruolo
            ),
            NULL::uuid,
            coalesce(p_soggetto_ruolo_id::text, 'NULL'),
            coalesce(p_soggetto_id::text, 'NULL'),
            coalesce(v_tipo_ruolo_id::text, 'NULL'),
            coalesce(p_cd_int_ruolo::text, 'NULL')
        );

    END IF;

    -- 4) Tutto ok: ritorno l'ID passato
    RETURN p_soggetto_ruolo_id;
END;
$function$

COMMENT ON FUNCTION script.fn_guard_soggetto_ruolo(p_soggetto_id uuid, p_soggetto_ruolo_id bigint, p_cd_int_ruolo character varying)
IS 'Verifica che il soggetto_ruolo_id sia coerente con il ruolo atteso (p_cd_int_ruolo)
    e, se specificato, con il soggetto (p_soggetto_id).
    In caso di incoerenza, utilizza script.fn_log_and_raise_error e solleva eccezione.
    In caso di esito positivo, restituisce p_soggetto_ruolo_id.
    Il parametro p_soggetto_id è opzionale: se NULL, non viene verificato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
