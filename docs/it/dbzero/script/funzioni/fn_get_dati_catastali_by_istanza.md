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
      -- Prova a recuperare i dati catastali specifici per l'istanza
      SELECT *
        INTO v_result
        FROM anagrafiche.dati_catastali
      WHERE istanza_utilities_id = p_istanza_utilities_id
      LIMIT 1;

      IF FOUND THEN
          RETURN v_result;
      END IF;

      -- Altrimenti recupera l’indirizzo legato a quella istanza da altri record
      SELECT indirizzo_dettaglio_id
        INTO v_indirizzo_id
        FROM anagrafiche.istanze_utilities
      WHERE id = p_istanza_utilities_id;

      -- Fallback su indirizzo generico (senza istanza)
      SELECT *
        INTO v_result
        FROM anagrafiche.dati_catastali
      WHERE istanza_utilities_id IS NULL
        AND indirizzo_dettaglio_id = v_indirizzo_id
      LIMIT 1;

      IF FOUND THEN
          RETURN v_result;
      END IF;

      -- Nessun dato catastale disponibile
      RETURN NULL;
  END;
  $function$
```
---
{% include-markdown "signature-core.md" %}
