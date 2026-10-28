{% include-markdown "it/dbzero/config/manual/fn_get_stati_doc_fiscale.md" %}
# ⚙️ Funzione `fn_get_stati_doc_fiscale`

```sql
CREATE FUNCTION fn_get_stati_doc_fiscale(p_target text, p_from_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_get_stati_doc_fiscale(p_target text, p_from_id bigint DEFAULT NULL::bigint)
 RETURNS SETOF config.stati_doc_fiscale
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_target TEXT := upper(btrim(p_target));
BEGIN
    -- Guard: target valido
    IF v_target NOT IN ('LOTTO', 'FATTURA') THEN
        PERFORM script.fn_log_and_raise_error(
            'config',
            'fn_get_stati_doc_fiscale',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'p_target',
                'valore', p_target
            ),
            NULL::uuid,
            concat('p_target=', coalesce(p_target, 'NULL'), ' (ammessi: LOTTO, FATTURA)')
        );
    END IF;

    -- Senza filtro: tutti gli stati applicabili
    IF p_from_id IS NULL THEN
        RETURN QUERY
        SELECT s.*
          FROM config.stati_doc_fiscale s
         WHERE s.attivo
           AND (
             (v_target = 'LOTTO'   AND s.applica_lotto) OR
             (v_target = 'FATTURA' AND s.applica_fattura)
           )
         ORDER BY s.ordine NULLS LAST, s.id;
        RETURN;
    END IF;

    -- Con filtro: solo transizioni ammesse
    RETURN QUERY
    SELECT s.*
      FROM config.stati_doc_fiscale_transizioni t
      JOIN config.stati_doc_fiscale s
        ON s.id = t.stato_to_id
     WHERE t.ammesso
       AND t.stato_from_id = p_from_id
       AND (
         (v_target = 'LOTTO'   AND t.solo_fattura = false) OR
         (v_target = 'FATTURA' AND t.solo_lotto = false)
       )
       AND (
         (v_target = 'LOTTO'   AND s.applica_lotto) OR
         (v_target = 'FATTURA' AND s.applica_fattura)
       )
       AND s.attivo
     ORDER BY s.ordine NULLS LAST, s.id;
END;
$function$

COMMENT ON FUNCTION config.fn_get_stati_doc_fiscale(p_target text, p_from_id bigint)
IS 'Restituisce stati validi per lotto/fattura e transizioni ammesse.';
```

</div>

---
{% include-markdown "signature-core.md" %}
