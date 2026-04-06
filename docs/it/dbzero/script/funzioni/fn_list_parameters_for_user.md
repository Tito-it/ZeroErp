{% include-markdown "it/dbzero/script/manual/fn_list_parameters_for_user.md" %}
# ⚙️ Funzione `fn_list_parameters_for_user`

```sql
CREATE FUNCTION fn_list_parameters_for_user(p_django_user_id integer, p_group_ids integer[], p_emittente_fiscale_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_list_parameters_for_user(p_django_user_id integer, p_group_ids integer[] DEFAULT NULL::integer[], p_emittente_fiscale_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(code character varying, description text, default_value text, emittente_value text, emittente_override_id bigint, group_value text, user_value text, user_override_id bigint, resolved_value text)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- Scopo: restituisce per ogni parametro il valore a ciascun livello di
    -- scope (emittente, gruppo, utente) e il valore risolto con priorita':
    --   user > group > emittente > default.
    -- Espone anche gli ID degli override emittente e utente per consentire
    -- la rimozione mirata dalla UI (DELETE puntuale sull'override attivo).
    RETURN QUERY
    SELECT
        p.code,
        p.description,
        p.default_value,
        po_em.overridden_value   AS emittente_value,
        po_em.id                 AS emittente_override_id,
        po_gr.overridden_value   AS group_value,
        po_us.overridden_value   AS user_value,
        po_us.id                 AS user_override_id,
        COALESCE(
            po_us.overridden_value,
            po_gr.overridden_value,
            po_em.overridden_value,
            p.default_value
        )                        AS resolved_value
    FROM config.parameters p

    -- Override a livello emittente puro (no user, no group).
    -- Se p_emittente_fiscale_id e' NULL il confronto non matcha nessuna riga:
    -- comportamento voluto per preservare semantica esistente.
    LEFT JOIN config.parameter_overrides po_em
      ON  po_em.parameter_id         = p.id
      AND po_em.emittente_fiscale_id = p_emittente_fiscale_id
      AND po_em.django_user_id       IS NULL
      AND po_em.django_group_id      IS NULL
      AND po_em.attivo               = true

    -- Override a livello gruppo (no user).
    -- Se l'utente appartiene a piu' gruppi, prende il primo override trovato
    -- ordinando per id stabile (tie-break deterministico).
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

    -- Override a livello utente (scope piu' specifico, vince sempre nella COALESCE).
    LEFT JOIN config.parameter_overrides po_us
      ON  po_us.parameter_id   = p.id
      AND po_us.django_user_id = p_django_user_id
      AND po_us.attivo         = true

    ORDER BY p.code;
END;
$function$

COMMENT ON FUNCTION script.fn_list_parameters_for_user(p_django_user_id integer, p_group_ids integer[], p_emittente_fiscale_id bigint)
IS 'Lista tutti i parametri con override per emittente, gruppo e utente. Restituisce il valore risolto con priorita: user > group > emittente > default. Espone emittente_override_id e user_override_id per consentire DELETE mirato dalla UI.';
```

---
{% include-markdown "signature-core.md" %}
