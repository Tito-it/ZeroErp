{% include-markdown "it/dbzero/script/manual/fn_get_parameter_full.md" %}
# ⚙️ Funzione `fn_get_parameter_full`

```sql
CREATE FUNCTION fn_get_parameter_full(p_code character varying, p_emittente_fiscale_id bigint, p_django_user_id integer, p_group_ids integer[], p_function_name text, p_categoria_cliente_id smallint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_parameter_full(p_code character varying, p_emittente_fiscale_id bigint DEFAULT NULL::bigint, p_django_user_id integer DEFAULT NULL::integer, p_group_ids integer[] DEFAULT NULL::integer[], p_function_name text DEFAULT NULL::text, p_categoria_cliente_id smallint DEFAULT NULL::smallint)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Cascata: user -> categoria_cliente -> group -> emittente -> function -> default.
-- Ogni livello usa l'uguaglianza: se il suo ambito e' NULL non trova righe
-- e si salta da solo.
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
        -- 2. categoria_cliente (vince su group ed emittente)
        (SELECT po.overridden_value
           FROM config.parameter_overrides po
          WHERE po.parameter_id         = v_param_id
            AND po.categoria_cliente_id = p_categoria_cliente_id
            AND po.attivo               = true
          LIMIT 1),
        -- 3. group (tie-break per id)
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
        -- 5. function
        (SELECT po.overridden_value
           FROM config.parameter_overrides po
          WHERE po.parameter_id  = v_param_id
            AND po.function_name = p_function_name
            AND po.attivo        = true
          LIMIT 1),
        -- 6. default
        v_default
    ) INTO v_result;

    RETURN v_result;
END;
$function$

COMMENT ON FUNCTION script.fn_get_parameter_full(p_code character varying, p_emittente_fiscale_id bigint, p_django_user_id integer, p_group_ids integer[], p_function_name text, p_categoria_cliente_id smallint)
IS 'Cascata a 6 livelli: user -> categoria_cliente -> group -> emittente -> function -> default. Ogni livello si salta da solo quando il suo ambito e'' NULL (uguaglianza). p_group_ids integer[] esplicito (%%TYPE[] non valido in PG). Legge config.parameter_overrides con attivo = true. Il livello «sessione» e'' uscito dal modello il 2026-11-09 (decisione di Tid): un override e'' configurazione che resta, una sessione di login scade. ⚠️ FIRMA UNICA, e deve restare tale: due overload con i DEFAULT su tutti i parametri tranne il primo rendono ambigua ogni chiamata corta, cast compreso (successo fino al 2026-07-27). Per aggiungere un livello si estende questa firma con un parametro opzionale in coda e si aggiornano i chiamanti, mai un overload «compatibile».';
```

</div>

---
{% include-markdown "signature-core.md" %}
