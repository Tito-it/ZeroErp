{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_soggetti_guard_indirizzi_required.md" %}
# ⚙️ Funzione `trgfn_soggetti_guard_indirizzi_required`

```sql
CREATE FUNCTION trgfn_soggetti_guard_indirizzi_required()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_indirizzi_required()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;

    PERFORM anagrafiche.fn_guard_indirizzi_obbligatori_soggetto(NEW.id, NEW.tx_id);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_indirizzi_required()
IS 'Constraint trigger DEFERRABLE su anagrafiche.soggetti, all''INSERT e all''UPDATE: il soggetto scritto deve avere i suoi indirizzi obbligatori. Il controllo e'' anagrafiche.fn_guard_indirizzi_obbligatori_soggetto (la matrice della natura, col ripiego; E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO al primo mancante), che chiama anche il trigger della cancellazione o del cambio di tipo di un indirizzo del soggetto (anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto). ⛔ Da NON confondere con anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required, il gemello del layer RUOLO.';
```

</div>

---
{% include-markdown "signature-core.md" %}
