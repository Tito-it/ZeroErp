# Funzione `fn_normalize_indirizzo`

```sql
CREATE FUNCTION fn_normalize_indirizzo(p_comune_id integer, p_indirizzo_libero text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_normalize_indirizzo(p_comune_id integer, p_indirizzo_libero text)
 RETURNS TABLE(indirizzo_dettaglio_id integer, via_norm text, civico_norm text, codice_postale_id integer, geoloc geometry)
 LANGUAGE plpgsql
AS $function$
DECLARE
    rec RECORD;
BEGIN

-- Usage Example:
-- SELECT * FROM dbops.fn_normalize_indirizzo(123, 'Via Roma 10');
-- Attenzione questa è una base perchè lastringa indirizzo sarà più 
-- complessa e successivamente dovrà prevedere più eccezioni.
-- esemmpi 'Via Roma 10/e batt.4 int.7 piano 4 ecc.'
    SELECT * INTO rec
    FROM script.fn_get_stradario(p_comune_id, p_indirizzo_libero)
    LIMIT 1;

    IF FOUND THEN
        indirizzo_dettaglio_id := rec.stradario_id;
        via_norm := UPPER(TRIM(rec.descrizione_completa));
        civico_norm := '';

        SELECT id INTO codice_postale_id 
        FROM config.codici_postali
        WHERE codice_postale = rec.cod_postale
          AND comune_id = p_comune_id
        LIMIT 1;

        geoloc := rec.geoloc;
    ELSE
        indirizzo_dettaglio_id := NULL;
        via_norm := NULL;
        civico_norm := NULL;
        codice_postale_id := NULL;
        geoloc := NULL;
    END IF;

    RETURN NEXT;
END;
$function$
```