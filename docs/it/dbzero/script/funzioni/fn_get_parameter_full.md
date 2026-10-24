{% include-markdown "it/dbzero/script/manual/fn_get_parameter_full.md" %}
# ⚙️ Funzione `fn_get_parameter_full`

```sql
CREATE FUNCTION fn_get_parameter_full(p_code text, p_emittente_fiscale_id bigint, p_django_user_id integer, p_group_ids integer[], p_session_key text, p_function_name text, p_categoria_cliente_id smallint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_parameter_full(p_code text, p_emittente_fiscale_id bigint DEFAULT NULL::bigint, p_django_user_id integer DEFAULT NULL::integer, p_group_ids integer[] DEFAULT NULL::integer[], p_session_key text DEFAULT NULL::text, p_function_name text DEFAULT NULL::text, p_categoria_cliente_id smallint DEFAULT NULL::smallint)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Cascata: user -> categoria_cliente -> group -> emittente -> session -> function -> default.
-- p_categoria_cliente_id e' l'ultimo parametro per backward compatibility:
-- i caller posizionali a 6 arg usano l'overload precedente senza modifiche.
-- Ogni subquery usa NULL-equality: se il param di scope e' NULL, la WHERE
-- restituisce 0 righe e quel livello viene saltato naturalmente.
-- p_group_ids resta integer[] esplicito: %TYPE[] non e' sintassi valida in PG.
DECLARE
    v_param_id  config.parameters.id%TYPE;
    v_default   config.parameters.default_value%TYPE;
    v_result    config.parameter_overrides.overridden_value%TYPE;
BEGIN
    SELECT id, default_value
      INTO v_param_id, v_default
      FROM config.parameters
     WHERE code = p_code;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_get_parameter_full',
            'E_ERRORE_PARAMETRI_TABELLA',
            jsonb_build_object(
                'codice_parametro', p_code,
                'nome_tabella',      'config.parameters'
            ),
            NULL::uuid,
            'config.parameters',
            p_code::text
        );
    END IF;

    SELECT COALESCE(
        -- 1. user (massima priorita')
        (SELECT po.overridden_value
           FROM config.parameter_overrides po
          WHERE po.parameter_id    = v_param_id
            AND po.django_user_id  = p_django_user_id
            AND po.attivo          = true
          LIMIT 1),
        -- 2. categoria_cliente (NUOVO: vince su group/emittente)
        (SELECT po.overridden_value
           FROM config.parameter_overrides po
          WHERE po.parameter_id         = v_param_id
            AND po.categoria_cliente_id = p_categoria_cliente_id
            AND po.attivo               = true
          LIMIT 1),
        -- 3. group
        (SELECT po.overridden_value
           FROM config.parameter_overrides po
          WHERE po.parameter_id    = v_param_id
            AND po.django_group_id = ANY(p_group_ids)
            AND po.attivo          = true
          ORDER BY po.id
          LIMIT 1),
        -- 4. emittente
        (SELECT po.overridden_value
           FROM config.parameter_overrides po
          WHERE po.parameter_id          = v_param_id
            AND po.emittente_fiscale_id  = p_emittente_fiscale_id
            AND po.attivo                = true
          LIMIT 1),
        -- 5. session
        (SELECT po.overridden_value
           FROM config.parameter_overrides po
          WHERE po.parameter_id  = v_param_id
            AND po.session_key   = p_session_key
            AND po.attivo        = true
          LIMIT 1),
        -- 6. function
        (SELECT po.overridden_value
           FROM config.parameter_overrides po
          WHERE po.parameter_id  = v_param_id
            AND po.function_name = p_function_name
            AND po.attivo        = true
          LIMIT 1),
        -- 7. default
        v_default
    ) INTO v_result;

    RETURN v_result;
END;
$function$

COMMENT ON FUNCTION script.fn_get_parameter_full(p_code text, p_emittente_fiscale_id bigint, p_django_user_id integer, p_group_ids integer[], p_session_key text, p_function_name text, p_categoria_cliente_id smallint)
IS 'Cascata 7 livelli: user -> categoria_cliente -> group -> emittente -> session -> function -> default. p_categoria_cliente_id (smallint, ultimo param) abilita il livello categoria cliente; a NULL il livello si salta da solo (NULL-equality). p_group_ids integer[] esplicito (%%TYPE[] non valido in PG). Usa config.parameter_overrides filtrato su attivo=TRUE. ⚠️ FIRMA UNICA, e deve restare tale: fino al 2026-07-27 conviveva un overload a 6 argomenti e, avendo entrambe i DEFAULT su tutti i parametri tranne il primo, OGNI chiamata con meno di 7 argomenti era ambigua — cast compreso. Due chiamanti erano rotti a runtime (ai_assistant/tool_registry.py con 1 arg, script.fn_get_default_by_param con 6). Per aggiungere un livello alla cascata NON creare un nuovo overload "backward compatible": si ricade nello stesso difetto. Estendere questa firma con un parametro opzionale in coda e aggiornare i chiamanti. rev 2026-07-27.';
```

</div>

---
{% include-markdown "signature-core.md" %}
