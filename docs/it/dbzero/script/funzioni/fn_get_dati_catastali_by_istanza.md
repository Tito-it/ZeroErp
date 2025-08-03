# ⚙️ Funzione `fn_get_dati_catastali_by_istanza`

```sql
CREATE FUNCTION fn_get_dati_catastali_by_istanza(p_istanza_utilities_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_dati_catastali_by_istanza(p_istanza_utilities_id integer)
 RETURNS anagrafiche.dati_catastali
 LANGUAGE plpgsql
AS $function$
    DECLARE
        v_result anagrafiche.dati_catastali;
        v_indirizzo_id INTEGER;
    BEGIN
        -- Recupera l'indirizzo associato all'istanza (da tabella dati_catastali)
        SELECT indirizzo_dettaglio_id
          INTO STRICT v_indirizzo_id
          FROM anagrafiche.dati_catastali
        WHERE istanza_utilities_id = p_istanza_utilities_id;

        -- Prova a restituire il dato catastale specifico per istanza
        SELECT *
          INTO v_result
          FROM anagrafiche.dati_catastali
        WHERE istanza_utilities_id = p_istanza_utilities_id
        LIMIT 1;

        -- Fallback: se non trovato, restituisco il default per l'indirizzo
        IF NOT FOUND THEN
            SELECT *
              INTO v_result
              FROM anagrafiche.dati_catastali
            WHERE indirizzo_dettaglio_id = v_indirizzo_id
              AND istanza_utilities_id IS NULL
            LIMIT 1;
        END IF;

        RETURN v_result;
    END;
    $function$
```
---
{% include-markdown "signature-core.md" %}
