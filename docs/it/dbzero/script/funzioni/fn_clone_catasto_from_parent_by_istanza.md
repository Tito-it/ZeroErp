{% include-markdown "it/dbzero/script/manual/fn_clone_catasto_from_parent_by_istanza.md" %}
# ⚙️ Funzione `fn_clone_catasto_from_parent_by_istanza`

```sql
CREATE FUNCTION fn_clone_catasto_from_parent_by_istanza(p_istanza_utilities_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_clone_catasto_from_parent_by_istanza(p_istanza_utilities_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_parent_istanza_id     anagrafiche.istanze_utilities.parent_istanza_id%TYPE;
    v_curr_catasto_id       anagrafiche.istanze_utilities.catasto_unita_immobiliare_id%TYPE;
    v_src                   anagrafiche.catasto_unita_immobiliari;
    v_new_catasto_id        anagrafiche.catasto_unita_immobiliari.id%TYPE;
BEGIN
    -- Parametro obbligatorio
    IF p_istanza_utilities_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_clone_catasto_from_parent_by_istanza',
            'E_ERRORE_PARAMETRI',
            jsonb_build_object('p_istanza_utilities_id', 'NULL'),
            NULL,
            'Parametro p_istanza_utilities_id non puo'' essere NULL'
        );
    END IF;

    -- Lock riga istanza (anti race)
    SELECT iu.parent_istanza_id,
           iu.catasto_unita_immobiliare_id
      INTO v_parent_istanza_id,
           v_curr_catasto_id
    FROM anagrafiche.istanze_utilities iu
    WHERE iu.id = p_istanza_utilities_id
    FOR UPDATE;

    -- Idempotenza: istanza gia' agganciata a catasto
    IF v_curr_catasto_id IS NOT NULL THEN
        RETURN v_curr_catasto_id;
    END IF;

    -- Senza parent non c'e' sorgente da clonare
    IF v_parent_istanza_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- Lookup sorgente basato su parent_istanza_id
    SELECT *
      INTO v_src
    FROM script.fn_get_catasto_source_by_istanza(p_istanza_utilities_id);

    -- Parent senza catasto: no-op (non blocca il flusso cliente/istanza)
    IF v_src.id IS NULL THEN
        RETURN NULL;
    END IF;

    -- Clone catasto
    INSERT INTO anagrafiche.catasto_unita_immobiliari (
        sezione_catastale,
        foglio_catastale,
        particella,
        subalterno,
        categoria_catastale,
        classe_catastale,
        rendita_catastale,
        consistenza,
        tipo_accatastamento,
        immobile_rurale,
        destinazione_immobile,
        anno_protocollo,
        superficie,
        storicizza
    )
    VALUES (
        v_src.sezione_catastale,
        v_src.foglio_catastale,
        v_src.particella,
        v_src.subalterno,
        v_src.categoria_catastale,
        v_src.classe_catastale,
        v_src.rendita_catastale,
        v_src.consistenza,
        v_src.tipo_accatastamento,
        v_src.immobile_rurale,
        v_src.destinazione_immobile,
        v_src.anno_protocollo,
        v_src.superficie,
        COALESCE(v_src.storicizza, true)
    )
    RETURNING id INTO v_new_catasto_id;

    -- Aggancio su istanza corrente
    UPDATE anagrafiche.istanze_utilities iu
       SET catasto_unita_immobiliare_id = v_new_catasto_id
     WHERE iu.id = p_istanza_utilities_id
       AND iu.catasto_unita_immobiliare_id IS NULL;

    RETURN v_new_catasto_id;
END;
$function$

COMMENT ON FUNCTION script.fn_clone_catasto_from_parent_by_istanza(p_istanza_utilities_id bigint)
IS 'Clona il catasto dalla parent_istanza sulla istanza corrente. Se parent o sorgente non disponibili ritorna NULL senza errore.';
```

</div>

---
{% include-markdown "signature-core.md" %}
