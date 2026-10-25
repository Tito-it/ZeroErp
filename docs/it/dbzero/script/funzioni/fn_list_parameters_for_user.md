{% include-markdown "it/dbzero/script/manual/fn_list_parameters_for_user.md" %}
# ⚙️ Funzione `fn_list_parameters_for_user`

```sql
CREATE FUNCTION fn_list_parameters_for_user(p_django_user_id integer, p_group_ids integer[], p_emittente_fiscale_id bigint, p_categoria_cliente_id smallint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_list_parameters_for_user(p_django_user_id integer, p_group_ids integer[] DEFAULT NULL::integer[], p_emittente_fiscale_id bigint DEFAULT NULL::bigint, p_categoria_cliente_id smallint DEFAULT NULL::smallint)
 RETURNS TABLE(code character varying, description text, default_value text, emittente_value text, emittente_override_id bigint, group_value text, user_value text, user_override_id bigint, categoria_cliente_value text, categoria_cliente_override_id bigint, resolved_value text, ammette_override boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- Scopo: tutti i parametri di config.parameters con, per ciascun
    -- livello mostrato (emittente, gruppo, utente, categoria_cliente),
    -- l'override di quel livello e il valore risolto dal runtime.
    -- Destinata alla UI admin: gli id servono alla DELETE del backend.
    --
    -- Ogni override ha esattamente un ambito
    -- (chk_parameter_overrides_un_ambito) e ce n'e' al piu' uno per
    -- parametro e ambito (uq_overrides_full_scope_v5, NULLS NOT
    -- DISTINCT): ogni LEFT JOIN trova al piu' una riga, e la lista ha
    -- una riga per parametro. Le regole stanno nei vincoli, qui non si
    -- ripetono.
    --
    -- ammette_override dice la famiglia: dove e' false il FE non offre
    -- l'override. Su quelle righe i livelli sono NULL e resolved_value
    -- e' il default per costruzione (i guard sugli override): qui non
    -- si ripete.
    --
    -- resolved_value NON ricopia la cascata: la chiede alla sua sede,
    -- script.fn_get_parameter_full (sessione e funzione NULL: la lista
    -- non li gestisce, e a NULL quei livelli si saltano da soli).
    --
    -- p_categoria_cliente_id NULL: NULL = NULL e' falso, il livello
    -- categoria non trova righe e le sue colonne restano NULL.
    RETURN QUERY
    SELECT
        p.code,
        p.description,
        p.default_value,
        po_em.overridden_value,
        po_em.id,
        po_gr.overridden_value,
        po_us.overridden_value,
        po_us.id,
        po_cat.overridden_value,
        po_cat.id,
        script.fn_get_parameter_full(
            p.code,
            p_emittente_fiscale_id,
            p_django_user_id,
            p_group_ids,
            NULL,
            NULL,
            p_categoria_cliente_id
        ),
        p.ammette_override
      FROM config.parameters p

      LEFT JOIN config.parameter_overrides po_em
        ON  po_em.parameter_id         = p.id
        AND po_em.emittente_fiscale_id = p_emittente_fiscale_id
        AND po_em.attivo               = true

      -- LATERAL: l'utente puo' stare in piu' gruppi
      -- (tie-break per id, lo stesso della cascata)
      LEFT JOIN LATERAL (
          SELECT o.overridden_value
            FROM config.parameter_overrides o
           WHERE o.parameter_id    = p.id
             AND o.django_group_id = ANY(p_group_ids)
             AND o.attivo          = true
           ORDER BY o.id
           LIMIT 1
      ) po_gr ON p_group_ids IS NOT NULL

      LEFT JOIN config.parameter_overrides po_us
        ON  po_us.parameter_id   = p.id
        AND po_us.django_user_id = p_django_user_id
        AND po_us.attivo         = true

      LEFT JOIN config.parameter_overrides po_cat
        ON  po_cat.parameter_id         = p.id
        AND po_cat.categoria_cliente_id = p_categoria_cliente_id
        AND po_cat.attivo               = true

     ORDER BY p.code;
END;
$function$

COMMENT ON FUNCTION script.fn_list_parameters_for_user(p_django_user_id integer, p_group_ids integer[], p_emittente_fiscale_id bigint, p_categoria_cliente_id smallint)
IS 'Lista tutti i parametri con l''override di ciascun livello mostrato (emittente, gruppo, utente, categoria_cliente), gli id (emittente_override_id, user_override_id, categoria_cliente_override_id) per la DELETE del backend e la famiglia del parametro (ammette_override: dove e'' false il FE non offre l''override). Una riga per parametro per costruzione del modello: ogni override ha esattamente un ambito (chk_parameter_overrides_un_ambito) e ce n''e'' al piu'' uno per parametro e ambito (uq_overrides_full_scope_v5, NULLS NOT DISTINCT). Sui parametri senza override i livelli sono NULL e resolved_value e'' il default per costruzione: i guard trgfn_parameter_overrides_guard_ammette_override e trgfn_parameters_guard_ammette_override impediscono che vi esista un override. resolved_value e'' script.fn_get_parameter_full con gli stessi ambiti (sessione e funzione NULL): il valore del runtime, non una sua copia. p_categoria_cliente_id NULL: livello categoria saltato. Rev 20261007-71 (brief-db-codici-sfilati-e-lista-parametri §3): livelli puri e cascata delegata (prima ricopiata). Rev 20261007-73 (§7.6): i filtri «puri» escono, li dicono i vincoli. Rev 20261025-86 (brief-db-parametri-senza-override §3): ammette_override in coda.';
```

</div>

---
{% include-markdown "signature-core.md" %}
