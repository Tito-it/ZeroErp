{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_psp_guard_ruolo_psp.md" %}
# ⚙️ Funzione `trgfn_psp_guard_ruolo_psp`

```sql
CREATE FUNCTION trgfn_psp_guard_ruolo_psp()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_psp_guard_ruolo_psp()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Verifica che NEW.soggetto_ruolo_id punti a un ruolo PSP
  --   valido usando la funzione centralizzata di guard ruolo.
  -- =========================================================

  NEW.soggetto_ruolo_id := script.fn_guard_soggetto_ruolo(
    p_soggetto_id       := NULL,
    p_soggetto_ruolo_id := NEW.soggetto_ruolo_id,
    p_cd_int_ruolo      := 'PSP'
  );

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_psp_guard_ruolo_psp()
IS 'Valida che soggetto_ruolo_id sia coerente con il ruolo PSP.';
```

</div>

---
{% include-markdown "signature-core.md" %}
