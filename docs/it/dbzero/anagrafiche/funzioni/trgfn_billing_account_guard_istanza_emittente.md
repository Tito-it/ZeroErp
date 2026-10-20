{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_guard_istanza_emittente.md" %}
# ⚙️ Funzione `trgfn_billing_account_guard_istanza_emittente`

```sql
CREATE FUNCTION trgfn_billing_account_guard_istanza_emittente()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_guard_istanza_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Il lavoro sta nel guard, SECURITY DEFINER perche' deve
    -- vedere i fratelli di istanza anche fuori dal perimetro di
    -- chi scrive. Qui resta solo il quando.
    PERFORM anagrafiche.fn_guard_istanza_ba_emittente(NEW.id);
    RETURN NULL;   -- trigger AFTER: il valore di ritorno e' ignorato
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_billing_account_guard_istanza_emittente()
IS 'Trigger AFTER INSERT su anagrafiche.billing_account: delega ad anagrafiche.fn_guard_istanza_ba_emittente la verifica che il BA nuovo risolva allo stesso emittente degli altri BA della sua istanza (E_ISTANZA_EMITTENTI_DIVERSI). AFTER e z95 perche'' l''emittente del BA nasce dal collegamento creato da trg_billing_account_z90_link_ef_ins, AFTER INSERT. Solo INSERT: la coppia (istanza, utility) del BA e'' bloccata (E_BA_ISTANZA_IMMUTABILE) e l''emittente cambia solo dal collegamento (trgfn_efba_guard_istanza_emittente). Brief: brief-db-istanza-nasce-col-ba (R-7).';
```

</div>

---
{% include-markdown "signature-core.md" %}
