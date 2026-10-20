{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_istanze_utilities_require_utility_dichiarata.md" %}
# ⚙️ Funzione `trgfn_istanze_utilities_require_utility_dichiarata`

```sql
CREATE FUNCTION trgfn_istanze_utilities_require_utility_dichiarata()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
  -- Constraint trigger al COMMIT: l'istanza appena inserita
  -- deve avere il suo billing account. Prima e dopo l'INSERT
  -- dell'istanza, nella stessa transazione, l'ordine e' libero.
  PERFORM anagrafiche.fn_guard_istanza_ha_ba(NEW.id);
  RETURN NULL;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata()
IS 'Constraint trigger function (DEFERRABLE INITIALLY DEFERRED, AFTER INSERT su anagrafiche.istanze_utilities): al COMMIT l''istanza appena nata deve avere almeno un billing account. Delega ad anagrafiche.fn_guard_istanza_ha_ba (E_ISTANZA_SENZA_BA), lo stesso guard del constraint trigger sulla cancellazione del BA. ⚠️ rev 2026-10-08: fino a quel giorno bastava uno fra tre satelliti (billing_account, istanze_dati_precontrattuali, clienti) e con la sola riga precontrattuale l''istanza nasceva senza BA. Regola di Tid: istanza e BA nascono insieme, sempre. Il nome resta: la utility e'' dichiarata dal billing account di quella utility. Brief: brief-db-istanza-nasce-col-ba (R-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
