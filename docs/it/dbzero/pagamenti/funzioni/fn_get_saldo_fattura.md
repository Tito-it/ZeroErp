{% include-markdown "it/dbzero/pagamenti/manual/fn_get_saldo_fattura.md" %}
# ⚙️ Funzione `fn_get_saldo_fattura`

```sql
CREATE FUNCTION fn_get_saldo_fattura(p_fattura_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_get_saldo_fattura(p_fattura_id bigint)
 RETURNS TABLE(saldo numeric, has_movimenti boolean)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_totale_a_pagare vendite.fatture.totale_a_pagare%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituisce il residuo fattura:
  --     saldo = totale_a_pagare - somma_movimenti_attivi
  --
  -- ⚠️ Finche' non esiste il posting (slice 1 del cantiere incassi)
  --    i movimenti sono zero e il residuo coincide col totale.
  --
  -- Rev 2026-08-21 (passo P-7): i due E_GENERICO passano ai codici
  -- registrati. Nessun predicato e' cambiato.
  -- =========================================================

  IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_saldo_fattura', 'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
      jsonb_build_object(
        'detail', 'fattura_id obbligatoria e maggiore di zero',
        'p_fattura_id', p_fattura_id
      ),
      NULL::uuid,
      'pagamenti.fn_get_saldo_fattura', 'p_fattura_id (obbligatorio, maggiore di zero)'
    );
  END IF;

  -- Recupera totale_a_pagare da fattura
  SELECT f.totale_a_pagare
    INTO v_totale_a_pagare
    FROM vendite.fatture f
   WHERE f.id = p_fattura_id;

  -- ⚠️ L'id e' valido: e' il documento a non esserci. Codice diverso
  -- dal guard di parametro perche' il rimedio e' diverso.
  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'database', 'pagamenti.fn_get_saldo_fattura', 'E_FATTURA_NON_TROVATA',
      jsonb_build_object('detail','Fattura non trovata', 'fattura_id', p_fattura_id),
      NULL::uuid,
      p_fattura_id::text
    );
  END IF;

  RETURN QUERY
  SELECT
    COALESCE(v_totale_a_pagare, 0)::numeric
    - COALESCE(SUM(m.importo), 0)::numeric AS saldo,
    (COUNT(*) > 0) AS has_movimenti
  FROM pagamenti.vendite_movimenti m
  WHERE m.fattura_id = p_fattura_id
    AND m.attivo IS TRUE;
END;
$function$

COMMENT ON FUNCTION pagamenti.fn_get_saldo_fattura(p_fattura_id bigint)
IS 'Restituisce il residuo fattura (totale_a_pagare - movimenti attivi) e il flag presenza movimenti. Rev 2026-08-21: guard di chiamata su E_PAGAMENTI_CHIAMATA_NON_VALIDA (TECNICO) e documento inesistente su E_FATTURA_NON_TROVATA (NON_TROVATO), al posto di due E_GENERICO; tipi ancorati con %TYPE in firma e RETURNS TABLE.';
```

---
{% include-markdown "signature-core.md" %}
