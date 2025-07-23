# ⚙️ Funzione `fn_get_indirizzo`

```sql
CREATE FUNCTION fn_get_indirizzo(p_soggetto_ruolo_id integer, p_tipo_codice character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_indirizzo(p_soggetto_ruolo_id integer, p_tipo_codice character varying)
 RETURNS TABLE(indirizzo_completo text, geoloc geometry)
 LANGUAGE sql
 STABLE
AS $function$
SELECT indirizzo_completo, geoloc
FROM script.fn_get_indirizzi_by_ruolo(p_soggetto_ruolo_id)
WHERE tipo_indirizzo = p_tipo_codice
LIMIT 1;
$function$
```