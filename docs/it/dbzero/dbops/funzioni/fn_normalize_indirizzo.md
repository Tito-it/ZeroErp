{% include-markdown "it/dbzero/dbops/manual/fn_normalize_indirizzo.md" %}
# ⚙️ Funzione `fn_normalize_indirizzo`

```sql
CREATE FUNCTION fn_normalize_indirizzo(p_comune_id integer, p_indirizzo_libero text)
```

**Definizione completa:**

<div data-search-exclude markdown>

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

        -- rev 2026-08-04 (bonifica riferimenti morti, F2): la colonna e'
        --   `codice` dal 2025-08-17 (20250817-24), non `codice_postale`.
        SELECT id INTO codice_postale_id
        FROM config.codici_postali
        WHERE codice = rec.cod_postale
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

</div>

---
{% include-markdown "signature-core.md" %}
