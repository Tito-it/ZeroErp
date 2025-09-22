{% include-markdown "it/dbzero/script/manual/fn_get_messaggio.md" %}
# ⚙️ Funzione `fn_get_messaggio`

```sql
CREATE FUNCTION fn_get_messaggio(p_codice text, p_valore text, p_lingua text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_messaggio(p_codice text, p_valore text DEFAULT NULL::text, p_lingua text DEFAULT NULL::text)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
  DECLARE
    tmpl TEXT;
    lingua_eff text;
  BEGIN
    /* 
     Restituisce il testo messaggio
     
     Viene recupearto il messaggio se non esiste si rimanda l'errore messaggio non definito  , 
     se esiste vengono sotituiti tutti gli eventuali placeholder con l'array
  */
    -- Risolvo la lingua: 
    --   1) quella passata, 
    --   2) altrimenti la GUC myapp.user_language, 
    --   3) altrimenti 'it'
    lingua_eff := coalesce(
      p_lingua,
      current_setting('myapp.user_language', true),
      'it'
    );

    SELECT messaggio INTO tmpl
      FROM config.messaggi_errore
    WHERE codice  = p_codice
      AND lingua  = lingua_eff;

    IF tmpl IS NULL THEN
      RETURN '[MESSAGGIO NON DEFINITO: ' || p_codice || ']';
    END IF;

    IF p_valore IS NOT NULL THEN
      RETURN format(tmpl, p_valore);
    ELSE
      RETURN tmpl;
    END IF;
  END;
  $function$
```

---
{% include-markdown "signature-core.md" %}
