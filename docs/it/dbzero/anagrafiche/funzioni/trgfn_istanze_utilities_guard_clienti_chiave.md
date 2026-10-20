# ⚙️ Funzione `trgfn_istanze_utilities_guard_clienti_chiave`

```sql
CREATE FUNCTION trgfn_istanze_utilities_guard_clienti_chiave()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_istanze_utilities_guard_clienti_chiave()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Al COMMIT: i clienti dell'istanza che e' entrata (o
  -- uscita) dalle fittizie.
  PERFORM anagrafiche.fn_guard_clienti_chiave_unica_di(NULL, NEW.id);
  RETURN NULL;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_istanze_utilities_guard_clienti_chiave()
IS 'Constraint trigger function (AFTER UPDATE DEFERRABLE INITIALLY DEFERRED su anagrafiche.istanze_utilities, quando fittizia cambia): i clienti dell''istanza entrano o escono dalla regola del cliente manuale; delega ad anagrafiche.fn_guard_clienti_chiave_unica_di (E_CLIENTE_STESSA_CHIAVE). Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
