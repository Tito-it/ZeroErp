{% include-markdown "it/dbzero/anagrafiche/manual/fn_guard_fornitore_attivo.md" %}
# ⚙️ Funzione `fn_guard_fornitore_attivo`

```sql
CREATE FUNCTION fn_guard_fornitore_attivo(p_fornitore_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_fornitore_attivo(p_fornitore_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_attivo          anagrafiche.fornitori.attivo%TYPE;
    v_blocca_ordini   config.stati_fornitore.blocca_ordini%TYPE;
    v_stato_desc      config.stati_fornitore.descrizione%TYPE;
BEGIN
    -- Guard: parametro obbligatorio
    IF p_fornitore_id IS NULL OR p_fornitore_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.fn_guard_fornitore_attivo',
            'E_FORNITORE_ID_INVALIDO',
            jsonb_build_object(
                'detail', 'p_fornitore_id deve essere NOT NULL e > 0',
                'p_fornitore_id', p_fornitore_id
            ),
            NULL::uuid,
            p_fornitore_id::text
        );
    END IF;

    -- Recupera stato fornitore
    SELECT f.attivo,
           sf.blocca_ordini,
           sf.descrizione
    INTO   v_attivo,
           v_blocca_ordini,
           v_stato_desc
    FROM   anagrafiche.fornitori f
    LEFT JOIN config.stati_fornitore sf
      ON sf.id = f.stato_fornitore_id
    WHERE  f.id = p_fornitore_id;

    -- Guard: fornitore deve esistere
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.fn_guard_fornitore_attivo',
            'E_FORNITORE_NON_TROVATO',
            jsonb_build_object(
                'detail', format('Fornitore id=%s non trovato', p_fornitore_id),
                'p_fornitore_id', p_fornitore_id
            ),
            NULL::uuid,
            p_fornitore_id::text
        );
    END IF;

    -- Guard: fornitore deve essere attivo
    IF v_attivo IS DISTINCT FROM true THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.fn_guard_fornitore_attivo',
            'E_FORNITORE_NON_ATTIVO',
            jsonb_build_object(
                'detail', format('Fornitore id=%s non attivo', p_fornitore_id),
                'p_fornitore_id', p_fornitore_id,
                'attivo', v_attivo
            ),
            NULL::uuid,
            p_fornitore_id::text
        );
    END IF;

    -- Guard: stato non deve bloccare ordini
    IF v_blocca_ordini = true THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'fn_guard_fornitore_attivo',
            'E_FORNITORE_BLOCCATO',
            jsonb_build_object(
                'detail', format('Fornitore id=%s in stato "%s" - ordini bloccati',
                                 p_fornitore_id, v_stato_desc),
                'p_fornitore_id', p_fornitore_id,
                'stato_descrizione', v_stato_desc,
                'blocca_ordini', v_blocca_ordini
            ),
            NULL::uuid,
            format('Fornitore id=%s in stato "%s" - ordini bloccati',
                   p_fornitore_id, v_stato_desc)
        );
    END IF;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_fornitore_attivo(p_fornitore_id bigint)
IS 'Guard fail-fast: verifica che il fornitore sia attivo e il suo stato operativo non blocchi ordini/DDT. Raise via fn_log_and_raise_error se non valido.';
```

</div>

---
{% include-markdown "signature-core.md" %}
