# ⚙️ Funzione `fn_componente_override`

```sql
CREATE FUNCTION fn_componente_override(p_valore jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_componente_override(p_valore jsonb)
 RETURNS TABLE(prezzo numeric, origine_prezzo character varying, listino_versione_id bigint, listino_riga_id bigint, prezzo_resolver_context jsonb)
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    SELECT CASE WHEN jsonb_typeof(p_valore) = 'object'
                THEN (p_valore ->> 'prezzo')::numeric
                ELSE (p_valore #>> '{}')::numeric END,
           CASE WHEN jsonb_typeof(p_valore) = 'object'
                THEN COALESCE(p_valore ->> 'origine_prezzo', 'MANUALE')
                ELSE 'MANUALE' END::varchar,
           CASE WHEN jsonb_typeof(p_valore) = 'object'
                THEN (p_valore ->> 'listino_versione_id')::bigint END,
           CASE WHEN jsonb_typeof(p_valore) = 'object'
                THEN (p_valore ->> 'listino_riga_id')::bigint END,
           CASE WHEN jsonb_typeof(p_valore) = 'object'
                THEN p_valore -> 'prezzo_resolver_context' END;
$function$

COMMENT ON FUNCTION vendite.fn_componente_override(p_valore jsonb)
IS 'Prezzo e provenienza di un override di componente, come lo ricevono le vendite.fn_*_riga_componenti_init: un prezzo (numero o testo numerico) e'' MANUALE senza listino; un oggetto {prezzo, origine_prezzo, listino_versione_id, listino_riga_id, prezzo_resolver_context} porta la provenienza che dichiara (MANUALE se non dichiara l''origine). Lo passa chi copia i componenti da un documento a monte. Non giudica la coerenza: lo fanno il CHECK e il guard del componente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
