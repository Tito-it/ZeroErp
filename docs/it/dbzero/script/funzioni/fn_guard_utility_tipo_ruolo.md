{% include-markdown "it/dbzero/script/manual/fn_guard_utility_tipo_ruolo.md" %}
# ⚙️ Funzione `fn_guard_utility_tipo_ruolo`

```sql
CREATE FUNCTION fn_guard_utility_tipo_ruolo(p_utility_id integer, p_tipo_ruolo_id integer, p_context text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_guard_utility_tipo_ruolo(p_utility_id integer, p_tipo_ruolo_id integer, p_context text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_oggi config.utilities_tipi_ruolo.valido_dal%TYPE := script.fn_data_operativa();
BEGIN
    -- =========================================================
    -- Scopo: il tipo di ruolo tratta l'utility solo se la
    --   matrice config.utilities_tipi_ruolo lo ammette con una
    --   riga accesa e valida oggi. Senza righe per l'utility
    --   nessun tipo di ruolo e' ammesso.
    -- =========================================================
    IF p_utility_id IS NULL OR p_utility_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_guard_utility_tipo_ruolo',
            'E_ERRORE_PARAMETRI',
            jsonb_build_object(
                'detail', 'p_utility_id obbligatorio e > 0',
                'p_utility_id', p_utility_id,
                'context', p_context
            ),
            NULL::uuid,
            concat('p_utility_id non valido: ', p_utility_id::text, ' context: ', p_context)
        );
    END IF;

    IF p_tipo_ruolo_id IS NULL OR p_tipo_ruolo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_guard_utility_tipo_ruolo',
            'E_ERRORE_PARAMETRI',
            jsonb_build_object(
                'detail', 'p_tipo_ruolo_id obbligatorio e > 0',
                'p_tipo_ruolo_id', p_tipo_ruolo_id,
                'context', p_context
            ),
            NULL::uuid,
            concat('p_tipo_ruolo_id non valido: ', p_tipo_ruolo_id::text, ' context: ', p_context)
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM config.utilities_tipi_ruolo m
         WHERE m.utility_id = p_utility_id
           AND m.tipo_ruolo_id = p_tipo_ruolo_id
           AND m.attivo = true
           AND (m.valido_dal IS NULL OR m.valido_dal <= v_oggi)
           AND (m.valido_al  IS NULL OR m.valido_al  >= v_oggi)
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_guard_utility_tipo_ruolo',
            'E_UTILITY_RUOLO_NON_AMMESSO',
            jsonb_build_object(
                'utility_id', p_utility_id,
                'tipo_ruolo_id', p_tipo_ruolo_id,
                'context', p_context
            ),
            NULL::uuid,
            p_tipo_ruolo_id::text,
            p_utility_id::text
        );
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_guard_utility_tipo_ruolo(p_utility_id integer, p_tipo_ruolo_id integer, p_context text)
IS 'Guard: il tipo di ruolo tratta l''utility solo se config.utilities_tipi_ruolo lo ammette con una riga accesa e valida oggi (script.fn_data_operativa). Un''utility senza righe non e'' ammessa per nessuno, come nella tendina anagrafiche.fn_lookup_utilities_per_ba. Rifiuto: E_UTILITY_RUOLO_NON_AMMESSO; parametri nulli o non positivi: E_ERRORE_PARAMETRI. La chiamano i trigger del registro dbops.automazione_guard_utility_tipo_ruolo, attraverso script.trgfn_guard_utility_tipo_ruolo_by_cols.';
```

</div>

---
{% include-markdown "signature-core.md" %}
