{% include-markdown "it/dbzero/ui/manual/fn_configurazione_senza_codici.md" %}
# ⚙️ Funzione `fn_configurazione_senza_codici`

```sql
CREATE FUNCTION fn_configurazione_senza_codici(p_configurazione jsonb, p_elenco text, p_codici character varying[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_configurazione_senza_codici(p_configurazione jsonb, p_elenco text, p_codici character varying[])
 RETURNS jsonb
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    -- CASE: l'elenco si scompone solo se c'e' una voce da togliere;
    -- altrimenti la configurazione torna com'e' (anche un [] salvato).
    SELECT CASE
        WHEN jsonb_typeof(p_configurazione -> p_elenco) IS DISTINCT FROM 'array'
          OR NOT EXISTS (SELECT 1
                           FROM jsonb_array_elements(p_configurazione -> p_elenco) AS e(value)
                          WHERE (e.value ->> 'codice') = ANY (p_codici))
        THEN p_configurazione
        ELSE (SELECT CASE WHEN count(*) = 0 THEN p_configurazione - p_elenco
                          ELSE jsonb_set(p_configurazione, ARRAY[p_elenco],
                                         jsonb_agg(e.value ORDER BY e.ord))
                     END
                FROM jsonb_array_elements(p_configurazione -> p_elenco)
                     WITH ORDINALITY AS e(value, ord)
               WHERE ((e.value ->> 'codice') = ANY (p_codici)) IS NOT TRUE)
    END;
$function$

COMMENT ON FUNCTION ui.fn_configurazione_senza_codici(p_configurazione jsonb, p_elenco text, p_codici character varying[])
IS 'La configurazione di una preferenza senza le voci dell''elenco p_elenco (colonne o widget) il cui codice è in p_codici; le altre voci restano, nel loro ordine. L''elenco che resta vuoto esce, e la chiave torna a seguire il preset. Se l''elenco manca, non è un elenco o non ha voci di quei codici, la configurazione torna com''è. Non solleva. La leggono il ritiro di una colonna o di una card (ui.trgfn_voce_ritira_dalle_preferenze) e la bonifica che l''ha accompagnato. IMMUTABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
