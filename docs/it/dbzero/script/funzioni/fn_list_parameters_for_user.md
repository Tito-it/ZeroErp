{% include-markdown "it/dbzero/script/manual/fn_list_parameters_for_user.md" %}
# ⚙️ Funzione `fn_list_parameters_for_user`

```sql
CREATE FUNCTION fn_list_parameters_for_user(p_django_user_id integer, p_group_ids integer[], p_emittente_fiscale_id bigint, p_categoria_cliente_id smallint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_list_parameters_for_user(p_django_user_id integer, p_group_ids integer[] DEFAULT NULL::integer[], p_emittente_fiscale_id bigint DEFAULT NULL::bigint, p_categoria_cliente_id smallint DEFAULT NULL::smallint)
 RETURNS TABLE(code character varying, description text, default_value text, emittente_value text, emittente_override_id bigint, group_value text, user_value text, user_override_id bigint, categoria_cliente_value text, categoria_cliente_override_id bigint, resolved_value text)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- Scopo: restituisce tutti i parametri di config.parameters con il valore
    -- override a ciascun livello di scope (emittente, gruppo, utente,
    -- categoria_cliente) e il valore risolto finale.
    -- Destinata alla UI admin di gestione parametri: mostra da quale livello
    -- proviene il valore effettivo e gli ID per DELETE mirato degli override.
    --
    -- Cascata resolved_value (replica fn_get_parameter_full overload 7-arg,
    -- migration 20260515-08):
    --   user > categoria_cliente > group > emittente > default
    --
    -- Architettura display/resolver:
    --   - LEFT JOIN "puri": isolano il valore di ciascun livello per la
    --     visualizzazione UI (scope esclusivo). Mostrano solo override
    --     "di livello puro" (es. po_em richiede django_user_id IS NULL).
    --   - COALESCE per resolved_value: livello user riusa direttamente po_us
    --     (WHERE identica al JOIN display). Gli altri tre livelli usano
    --     subquery proprie perché i JOIN display hanno filtri IS NULL più
    --     restrittivi rispetto a fn_get_parameter_full (es. po_em ha
    --     django_user_id IS NULL, la subquery emittente non ce l'ha).
    --     La COALESCE short-circuits: se po_us non è NULL, le subquery
    --     successive non vengono eseguite.
    --
    -- Retro-compatibilita': p_categoria_cliente_id DEFAULT NULL ->
    --   NULL = NULL è sempre false -> po_cat e le subquery categoria non
    --   matchano nessuna riga -> colonne categoria NULL, cascata invariata.
    RETURN QUERY
    SELECT
        p.code,
        p.description,
        p.default_value,

        -- Livello emittente (scope puro: solo emittente, no user, no group)
        po_em.overridden_value        AS emittente_value,
        po_em.id                      AS emittente_override_id,

        -- Livello gruppo (LATERAL: multi-gruppo, tie-break deterministico per id)
        po_gr.overridden_value        AS group_value,

        -- Livello utente (scope più specifico nella cascata)
        po_us.overridden_value        AS user_value,
        po_us.id                      AS user_override_id,

        -- Livello categoria_cliente (scope puro: no user/group/emittente/session/function)
        po_cat.overridden_value       AS categoria_cliente_value,
        po_cat.id                     AS categoria_cliente_override_id,

        -- Valore risolto: replica la cascata di fn_get_parameter_full
        -- (coerenza tra UI e runtime garantita).
        -- Livello user: riusa po_us — WHERE identica al JOIN display,
        -- nessuna subquery aggiuntiva necessaria.
        -- Livelli categoria/group/emittente: subquery proprie perché i loro
        -- JOIN display hanno filtri IS NULL più restrittivi di fn_get_parameter_full
        -- (es. po_em richiede django_user_id IS NULL, la subquery no).
        -- La COALESCE short-circuits: se po_us non è NULL, le 3 subquery
        -- successive non vengono eseguite dal planner.
        COALESCE(
            -- 1. user: riusa il JOIN display (filtri identici, no subquery extra)
            po_us.overridden_value,
            -- 2. categoria_cliente (vince su group e emittente)
            --    NULL = NULL è false: se p_categoria_cliente_id IS NULL
            --    questa subquery non matcha righe, il livello viene saltato
            (SELECT po.overridden_value
               FROM config.parameter_overrides po
              WHERE po.parameter_id         = p.id
                AND po.categoria_cliente_id  = p_categoria_cliente_id
                AND po.attivo               = true
              LIMIT 1),
            -- 3. group (tie-break per id su multi-gruppo)
            (SELECT po.overridden_value
               FROM config.parameter_overrides po
              WHERE po.parameter_id    = p.id
                AND po.django_group_id = ANY(p_group_ids)
                AND po.attivo          = true
              ORDER BY po.id
              LIMIT 1),
            -- 4. emittente
            (SELECT po.overridden_value
               FROM config.parameter_overrides po
              WHERE po.parameter_id         = p.id
                AND po.emittente_fiscale_id  = p_emittente_fiscale_id
                AND po.attivo               = true
              LIMIT 1),
            -- 5. default globale
            p.default_value
        ) AS resolved_value

    FROM config.parameters p

    -- Override emittente puro (no user, no group; session/function non gestiti in lista)
    LEFT JOIN config.parameter_overrides po_em
      ON  po_em.parameter_id         = p.id
      AND po_em.emittente_fiscale_id  = p_emittente_fiscale_id
      AND po_em.django_user_id        IS NULL
      AND po_em.django_group_id       IS NULL
      AND po_em.attivo                = true

    -- Override gruppo: LATERAL per gestire più gruppi con tie-break per id
    LEFT JOIN LATERAL (
        SELECT o.overridden_value
          FROM config.parameter_overrides o
         WHERE o.parameter_id    = p.id
           AND o.django_group_id = ANY(p_group_ids)
           AND o.django_user_id  IS NULL
           AND o.attivo          = true
         ORDER BY o.id
         LIMIT 1
    ) po_gr ON p_group_ids IS NOT NULL

    -- Override utente
    LEFT JOIN config.parameter_overrides po_us
      ON  po_us.parameter_id   = p.id
      AND po_us.django_user_id  = p_django_user_id
      AND po_us.attivo          = true

    -- Override categoria_cliente puro:
    -- scope esclusivo (no user, no group, no emittente, no session, no function)
    -- per mostrare solo override "di categoria pura" nella UI admin.
    -- NULL = NULL è sempre false: se p_categoria_cliente_id IS NULL nessuna
    -- riga matcha e le colonne categoria restano NULL (retro-compatibile).
    LEFT JOIN config.parameter_overrides po_cat
      ON  po_cat.parameter_id         = p.id
      AND po_cat.categoria_cliente_id  = p_categoria_cliente_id
      AND po_cat.django_user_id        IS NULL
      AND po_cat.django_group_id       IS NULL
      AND po_cat.emittente_fiscale_id  IS NULL
      AND po_cat.session_key           IS NULL
      AND po_cat.function_name         IS NULL
      AND po_cat.attivo                = true

    ORDER BY p.code;
END;
$function$

COMMENT ON FUNCTION script.fn_list_parameters_for_user(p_django_user_id integer, p_group_ids integer[], p_emittente_fiscale_id bigint, p_categoria_cliente_id smallint)
IS 'Lista tutti i parametri con override per emittente, gruppo, utente e categoria_cliente. Restituisce il valore risolto con cascata user > categoria_cliente > group > emittente > default (coerente con fn_get_parameter_full overload 7-arg, migration 20260515-08). I LEFT JOIN usano scope puri (nessun overlap) per la visualizzazione UI; resolved_value calcolato con subquery indipendenti per coerenza con il runtime. Espone emittente_override_id, user_override_id e categoria_cliente_override_id (bigint) per DELETE mirato dalla UI admin. p_categoria_cliente_id = NULL: livello categoria saltato, retro-compatibile con la firma 3-arg.';
```

---
{% include-markdown "signature-core.md" %}
