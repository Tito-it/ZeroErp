{% include-markdown "it/dbzero/pratiche/manual/fn_check_definizione_struttura_bloccata.md" %}
# ⚙️ Funzione `fn_check_definizione_struttura_bloccata`

```sql
CREATE FUNCTION fn_check_definizione_struttura_bloccata(p_definizione_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_check_definizione_struttura_bloccata(p_definizione_id integer)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dire se la STRUTTURA di una definizione e' bloccata
--        (edizione forkata gia' emessa: PUBBLICATA o RITIRATA).
--        Governa il blocco INSERT/UPDATE di template e figli.
--        Funzione pura, no raise.
DECLARE
  v_bloccata boolean;
BEGIN
  IF p_definizione_id IS NULL THEN
    RETURN false;
  END IF;

  SELECT (wd.stato <> 'BOZZA'
          AND wd.emittente_fiscale_id IS NOT NULL)
    INTO v_bloccata
    FROM pratiche.workflow_definizioni wd
   WHERE wd.id = p_definizione_id;

  RETURN COALESCE(v_bloccata, false);
END;
$function$

COMMENT ON FUNCTION pratiche.fn_check_definizione_struttura_bloccata(p_definizione_id integer)
IS 'TRUE sse la definizione workflow e'' un''edizione forkata (emittente_fiscale_id valorizzato) fuori da BOZZA (PUBBLICATA o RITIRATA): la struttura e'' bloccata (INSERT/UPDATE di template e figli vietati, strategia C). Piu'' ampia di fn_check_definizione_congelata (solo PUBBLICATA, blocco DELETE): una RITIRATA e'' struttura-bloccata ma cancellabile. Preset (emittente NULL) e BOZZA liberi. Funzione pura (no raise); usata dai guard di immutabilita'' strutturale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
