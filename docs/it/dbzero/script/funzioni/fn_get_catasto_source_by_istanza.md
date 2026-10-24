{% include-markdown "it/dbzero/script/manual/fn_get_catasto_source_by_istanza.md" %}
# ⚙️ Funzione `fn_get_catasto_source_by_istanza`

```sql
CREATE FUNCTION fn_get_catasto_source_by_istanza(p_istanza_utilities_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_catasto_source_by_istanza(p_istanza_utilities_id bigint)
 RETURNS anagrafiche.catasto_unita_immobiliari
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_parent_istanza_id anagrafiche.istanze_utilities.parent_istanza_id%TYPE;
    v_catasto           anagrafiche.catasto_unita_immobiliari;
BEGIN
    -- ============================================================
    -- Funzione: script.fn_get_catasto_source_by_istanza
    --
    -- Scopo:
    --   - Recupera il record catastale "sorgente" da clonare
    --     per una istanza_utilities (subentro).
    --
    -- Regola di individuazione sorgente:
    --   - ESCLUSIVAMENTE tramite:
    --       istanze_utilities.parent_istanza_id
    --
    -- Note di modellazione (post-refactor):
    --   - Il legame ufficiale istanza -> catasto è:
    --       istanze_utilities.catasto_unita_immobiliare_id
    --   - La tabella catasto_unita_immobiliari NON contiene più
    --     il riferimento all'istanza (rimossa istanza_utility_id).
    --
    -- Ritorna:
    --   - record anagrafiche.catasto_unita_immobiliari (sorgente)
    --   - NULL se non esiste parent o se la parent non ha catasto agganciato
    --
    -- Side effects:
    --   - Nessuno (lookup puro).
    -- ============================================================

    IF p_istanza_utilities_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_get_catasto_source_by_istanza',
            'E_ERRORE_PARAMETRI',
            jsonb_build_object('p_istanza_utilities_id', 'NULL'),
            NULL,
            'Parametro p_istanza_utilities_id non può essere NULL'
        );
    END IF;

    -- 1) Recupero parent_istanza_id
    SELECT iu.parent_istanza_id
    INTO v_parent_istanza_id
    FROM anagrafiche.istanze_utilities iu
    WHERE iu.id = p_istanza_utilities_id;

    IF v_parent_istanza_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- 2) Recupero catasto agganciato alla parent istanza
    SELECT c.*
    INTO v_catasto
    FROM anagrafiche.istanze_utilities iu_parent
    JOIN anagrafiche.catasto_unita_immobiliari c
    ON c.id = iu_parent.catasto_unita_immobiliare_id
    WHERE iu_parent.id = v_parent_istanza_id
    LIMIT 1;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    RETURN v_catasto;
END;
$function$

COMMENT ON FUNCTION script.fn_get_catasto_source_by_istanza(p_istanza_utilities_id bigint)
IS 'Recupera il record catastale "sorgente" da clonare per una istanza_utilities.
  La sorgente è determinata ESCLUSIVAMENTE da:
  istanze_utilities.parent_istanza_id';
```

</div>

---
{% include-markdown "signature-core.md" %}
