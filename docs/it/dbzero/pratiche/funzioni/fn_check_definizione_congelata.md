{% include-markdown "it/dbzero/pratiche/manual/fn_check_definizione_congelata.md" %}
# ⚙️ Funzione `fn_check_definizione_congelata`

```sql
CREATE FUNCTION fn_check_definizione_congelata(p_definizione_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_check_definizione_congelata(p_definizione_id integer)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dire se una definizione e' un'edizione forkata pubblicata
--        (congelata dalla strategia «Leggera»). Funzione pura, no
--        raise: la usano i guard di immutabilita' strutturale.
DECLARE
  v_congelata boolean;
BEGIN
  IF p_definizione_id IS NULL THEN
    RETURN false;
  END IF;

  SELECT (wd.stato = 'PUBBLICATA'
          AND wd.emittente_fiscale_id IS NOT NULL)
    INTO v_congelata
    FROM pratiche.workflow_definizioni wd
   WHERE wd.id = p_definizione_id;

  RETURN COALESCE(v_congelata, false);
END;
$function$

COMMENT ON FUNCTION pratiche.fn_check_definizione_congelata(p_definizione_id integer)
IS 'TRUE sse la definizione workflow e'' un''edizione forkata (emittente_fiscale_id valorizzato) in stato PUBBLICATA: e'' congelata dall''immutabilita'' strutturale «Leggera». Il preset (emittente NULL) e le BOZZA/RITIRATA non sono mai congelati. Funzione pura (no raise); usata dai guard trgfn_template_flussi_guard_immutabile e trgfn_template_flussi_figli_guard_immutabile. NULL/non trovata => false.';
```

</div>

---
{% include-markdown "signature-core.md" %}
