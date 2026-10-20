# ⚙️ Funzione `trgfn_clienti_guard_chiave_unica`

```sql
CREATE FUNCTION trgfn_clienti_guard_chiave_unica()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_guard_chiave_unica()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Al COMMIT: il cliente scritto non duplica una fornitura
  -- (soggetto + utility + azienda) gia' occupata nel periodo.
  PERFORM anagrafiche.fn_guard_cliente_chiave_unica(NEW.id);
  RETURN NULL;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_guard_chiave_unica()
IS 'Constraint trigger function (AFTER INSERT OR UPDATE DEFERRABLE INITIALLY DEFERRED su anagrafiche.clienti): al COMMIT delega ad anagrafiche.fn_guard_cliente_chiave_unica (E_CLIENTE_STESSA_CHIAVE). Al COMMIT perche'' chiudere il cliente vecchio e attivare il nuovo nella stessa operazione resta libero nell''ordine. Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
