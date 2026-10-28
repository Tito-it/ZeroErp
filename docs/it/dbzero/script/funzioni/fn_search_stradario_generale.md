{% include-markdown "it/dbzero/script/manual/fn_search_stradario_generale.md" %}
# ⚙️ Funzione `fn_search_stradario_generale`

```sql
CREATE FUNCTION fn_search_stradario_generale(p_search text, p_toponomastica_id integer, p_limit integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_search_stradario_generale(p_search text DEFAULT NULL::text, p_toponomastica_id integer DEFAULT NULL::integer, p_limit integer DEFAULT 30)
 RETURNS TABLE(stradario_generale_id integer, toponomastica_id integer, toponimo character varying, denominazione character varying, indirizzo_normalizzato text)
 LANGUAGE plpgsql
 STABLE PARALLEL SAFE
AS $function$
DECLARE
    v_search  text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Ricerca vie su stradario_generale (senza comune/CAP).
    --   Serve per autocomplete "via nuova": l'utente cerca
    --   una via in tutta Italia, poi sceglie comune e CAP
    --   separatamente.
    --
    -- Parametri:
    --   p_search:           testo ILIKE su indirizzo_normalizzato
    --                       (obbligatorio, minimo 2 caratteri)
    --   p_toponomastica_id:  filtro opzionale per tipo strada
    --                       (es. solo VIA, solo PIAZZA)
    --   p_limit:             max righe (default 30)
    --
    -- JOIN:
    --   stradario_generale -> toponomastica
    --
    -- Performance:
    --   stradario_generale.indirizzo_normalizzato ha indice
    --   GIN trigram (ix_stradario_generale_norm_trgm).
    --   toponomastica_id ha indice btree.
    -- =========================================================

    -- =============================================================
    -- Normalizzazione parametro ricerca
    -- =============================================================

    v_search := NULLIF(BTRIM(p_search), '');

    -- =============================================================
    -- Guard: p_search obbligatorio e minimo 2 caratteri
    -- =============================================================

    IF v_search IS NULL OR LENGTH(v_search) < 2 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_search_stradario_generale',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('p_search', p_search),
            NULL::uuid,
            'p_search obbligatorio e minimo 2 caratteri.'
        );
    END IF;

    -- =============================================================
    -- Guard: p_toponomastica_id valido se fornito
    -- =============================================================

    IF p_toponomastica_id IS NOT NULL AND p_toponomastica_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_search_stradario_generale',
            'E_ADMIN_VALIDAZIONE',
            jsonb_build_object('parametro', 'p_toponomastica_id',
                              'valore', p_toponomastica_id),
            NULL::uuid,
            'p_toponomastica_id deve essere > 0.'
        );
    END IF;

    -- =============================================================
    -- Query principale
    -- Filtro toponomastica.attivo = true per escludere
    -- toponimi disattivati.
    -- =============================================================

    RETURN QUERY
    SELECT
        sg.id                       AS stradario_generale_id,
        t.id                        AS toponomastica_id,
        t.descrizione               AS toponimo,
        sg.descrizione              AS denominazione,
        sg.indirizzo_normalizzato   AS indirizzo_normalizzato
    FROM config.stradario_generale sg
    JOIN config.toponomastica t ON t.id = sg.toponomastica_id
    WHERE t.attivo = TRUE
      AND sg.indirizzo_normalizzato ILIKE '%' || v_search || '%'
      AND (p_toponomastica_id IS NULL OR sg.toponomastica_id = p_toponomastica_id)
    ORDER BY sg.indirizzo_normalizzato, sg.id
    LIMIT p_limit;

END;
$function$

COMMENT ON FUNCTION script.fn_search_stradario_generale(p_search text, p_toponomastica_id integer, p_limit integer)
IS 'Ricerca vie su stradario_generale per autocomplete via nuova. Filtra per testo fuzzy su indirizzo_normalizzato e opzionalmente per tipo strada. JOIN stradario_generale -> toponomastica. STABLE, PARALLEL SAFE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
