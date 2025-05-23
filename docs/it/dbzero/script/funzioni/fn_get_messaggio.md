# Funzione `fn_get_messaggio`

```sql
CREATE FUNCTION fn_get_messaggio(p_codice text, p_valore text, p_lingua text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_messaggio(p_codice text, p_valore text DEFAULT NULL::text, p_lingua text DEFAULT 'it'::text)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
  tmpl TEXT;
BEGIN

-- Restituisce il testo messaggio

  SELECT messaggio INTO tmpl
    FROM config.messaggi_errore
   WHERE codice = p_codice
     AND lingua = p_lingua;

  IF tmpl IS NULL THEN
    RETURN '[MESSAGGIO NON DEFINITO: ' || p_codice || ']';
  END IF;

  IF p_valore IS NOT NULL THEN
    RETURN REPLACE(tmpl, '%', p_valore);
  ELSE
    RETURN tmpl;
  END IF;
END;
$function$
```