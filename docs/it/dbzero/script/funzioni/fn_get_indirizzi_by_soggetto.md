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
  SELECT r.*
  FROM anagrafiche.vw_indirizzi_resolved_base r
  WHERE r.scope = 'SOGGETTO'
    AND r.soggetto_id = p_soggetto_id
  ORDER BY r.tipo_indirizzo_codice, r.indirizzo_id;
$function$

COMMENT ON FUNCTION script.fn_get_indirizzi_by_soggetto(p_soggetto_id uuid)
IS 'Indirizzi layer SOGGETTO (identitario) da vw_indirizzi_resolved_base.';
```

---
{% include-markdown "signature-core.md" %}
