{% include-markdown "it/dbzero/script/manual/fn_get_indirizzi_by_soggetto.md" %}
# ⚙️ Funzione `fn_get_indirizzi_by_soggetto`

```sql
CREATE FUNCTION fn_get_indirizzi_by_soggetto(p_soggetto_id uuid)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzi_by_soggetto(p_soggetto_id uuid)
 RETURNS SETOF anagrafiche.vw_indirizzi_resolved_soggetto
 LANGUAGE sql
 STABLE
AS $function$
  SELECT *
  FROM anagrafiche.vw_indirizzi_resolved_soggetto
  WHERE soggetto_id = p_soggetto_id
  ORDER BY tipo_indirizzo_codice;
$function$
```

---
{% include-markdown "signature-core.md" %}
