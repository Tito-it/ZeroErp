# ⚙️ Funzione `fn_indirizzi_obbligatori_mancanti`

```sql
CREATE FUNCTION fn_indirizzi_obbligatori_mancanti(p_ambito text, p_tipi_presenti integer[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_indirizzi_obbligatori_mancanti(p_ambito text, p_tipi_presenti integer[])
 RETURNS text[]
 LANGUAGE sql
 STABLE
AS $function$
  -- Codici obbligatori dell'ambito non presenti tra i tipi passati.
  SELECT COALESCE(
           array_agg(t.codice_interno ORDER BY t.codice_interno),
           ARRAY[]::text[])
    FROM config.tipi_indirizzi_allowed a
    JOIN config.tipi_indirizzi t ON t.id = a.tipo_indirizzo_id
   WHERE a.ambito = p_ambito
     AND a.attivo IS TRUE
     AND a.obbligatorio IS TRUE
     AND NOT (a.tipo_indirizzo_id = ANY(COALESCE(p_tipi_presenti, ARRAY[]::integer[])));
$function$
```

---
{% include-markdown "signature-core.md" %}
