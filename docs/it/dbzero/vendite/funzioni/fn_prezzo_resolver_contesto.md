# ⚙️ Funzione `fn_prezzo_resolver_contesto`

```sql
CREATE FUNCTION fn_prezzo_resolver_contesto(p_risultato jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_prezzo_resolver_contesto(p_risultato jsonb)
 RETURNS jsonb
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    SELECT p_risultato - ARRAY['prezzo_finale', 'origine', 'listino_versione_id',
                               'listino_riga_id', 'esito_codice', 'esito_context',
                               'esito_valori'];
$function$

COMMENT ON FUNCTION vendite.fn_prezzo_resolver_contesto(p_risultato jsonb)
IS 'Dal risultato del resolver dei prezzi (to_jsonb di una riga di vendite.fn_resolve_prezzo_listino_v2 o _esito) il contesto da salvare in prezzo_resolver_context: le stesse chiavi, tranne quelle che hanno una sede loro (prezzo_finale, origine, listino_versione_id, listino_riga_id) e l''esito. Le chiavi restanti sono quelle che vendite.fn_provenienza_prezzo_esplosa legge.';
```

</div>

---
{% include-markdown "signature-core.md" %}
