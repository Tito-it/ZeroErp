{% include-markdown "it/dbzero/script/manual/fn_guard_utility_tipo_ruolo.md" %}
# ⚙️ Funzione `fn_guard_utility_tipo_ruolo`

```sql
CREATE FUNCTION fn_guard_utility_tipo_ruolo(p_utility_id integer, p_tipo_ruolo_id integer, p_context text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_guard_utility_tipo_ruolo(p_utility_id integer, p_tipo_ruolo_id integer, p_context text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_has_matrix BOOLEAN := false;
    v_is_allowed BOOLEAN := false;
BEGIN
    -- Guard: parametri obbligatori e > 0
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

    -- NOTA: le due query EXISTS sulla matrice hanno condizioni
    -- identiche tranne tipo_ruolo_id. Scelta progettuale: si
    -- mantengono separate per rendere esplicito il pattern a 2 step
    -- (1: la matrice esiste? → fail-open se no; 2: il ruolo e'
    -- ammesso? → fail-close se no). Unificarle in una sola query
    -- con FILTER peggiorerebbe la leggibilita' senza beneficio
    -- prestazionale (tabella config con poche righe).

    -- 1) Esiste matrice attiva/valida per utility?
    SELECT EXISTS (
        SELECT 1
          FROM config.utilities_tipi_ruolo m
         WHERE m.utility_id = p_utility_id
           AND m.attivo = true
           AND (m.valido_dal IS NULL OR m.valido_dal <= (SELECT script.fn_data_operativa()))
           AND (m.valido_al IS NULL OR m.valido_al >= (SELECT script.fn_data_operativa()))
    )
    INTO v_has_matrix;

    -- Fail-open: nessuna regola attiva/valida → nessun vincolo
    IF NOT v_has_matrix THEN
        RETURN;
    END IF;

    -- 2) Matrice presente: il ruolo deve essere esplicitamente ammesso
    SELECT EXISTS (
        SELECT 1
          FROM config.utilities_tipi_ruolo m
         WHERE m.utility_id = p_utility_id
           AND m.tipo_ruolo_id = p_tipo_ruolo_id
           AND m.attivo = true
           AND (m.valido_dal IS NULL OR m.valido_dal <= (SELECT script.fn_data_operativa()))
           AND (m.valido_al IS NULL OR m.valido_al >= (SELECT script.fn_data_operativa()))
    )
    INTO v_is_allowed;

    IF NOT v_is_allowed THEN
        -- Fix: E_GENERICO → E_UTILITY_RUOLO_NON_AMMESSO
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
IS 'Guard utility→tipo_ruolo: fail-open se matrice assente; fail-close se presente e ruolo non ammesso. Errore: E_UTILITY_RUOLO_NON_AMMESSO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
