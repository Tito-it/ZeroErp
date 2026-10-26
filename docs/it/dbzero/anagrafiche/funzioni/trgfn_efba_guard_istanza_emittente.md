{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_efba_guard_istanza_emittente.md" %}
# ⚙️ Funzione `trgfn_efba_guard_istanza_emittente`

```sql
CREATE FUNCTION trgfn_efba_guard_istanza_emittente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_efba_guard_istanza_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_ba_id anagrafiche.billing_account.id%TYPE;
BEGIN
    -- Su DELETE il BA sta in OLD; in creazione in NEW.
    -- Una riga spostata da un BA a un altro: vanno verificati
    -- entrambi.
    IF TG_OP = 'UPDATE'
       AND NEW.billing_account_id IS DISTINCT FROM OLD.billing_account_id THEN
        PERFORM anagrafiche.fn_guard_istanza_ba_emittente(OLD.billing_account_id);
        PERFORM anagrafiche.fn_guard_istanza_ba_emittente(NEW.billing_account_id);
        IF OLD.billing_account_id IS NULL OR NEW.billing_account_id IS NULL THEN
            PERFORM anagrafiche.fn_guard_istanza_ba_gestore_globale();
        END IF;
        RETURN NULL;
    END IF;

    IF TG_OP = 'DELETE' THEN
        v_ba_id := OLD.billing_account_id;
    ELSE
        v_ba_id := NEW.billing_account_id;
    END IF;

    IF v_ba_id IS NOT NULL THEN
        -- Movimenti 1-3: collegamento di un BA creato, cambiato
        -- o tolto.
        PERFORM anagrafiche.fn_guard_istanza_ba_emittente(v_ba_id);
        RETURN NULL;
    END IF;

    -- Movimento 4: la riga senza billing_account_id e' quella
    -- del gestore globale. Raggio N.
    PERFORM anagrafiche.fn_guard_istanza_ba_gestore_globale();
    RETURN NULL;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_efba_guard_istanza_emittente()
IS 'Trigger AFTER su anagrafiche.emittenti_fiscali_billing_account: presidia i movimenti che cambiano l''emittente di un BA — collegamento creato, cambiato o tolto (fn_guard_istanza_ba_emittente) e riga del gestore globale (fn_guard_istanza_ba_gestore_globale, raggio N) — perche'' nessuna istanza finisca con billing account di due emittenti (E_ISTANZA_EMITTENTI_DIVERSI). Gemello di trgfn_efba_guard_albero_emittente, che presidia gli stessi movimenti per l''albero padre/figlio. AFTER perche'' il guard rilegge il collegamento. Brief: brief-db-istanza-nasce-col-ba (R-7).';
```

</div>

---
{% include-markdown "signature-core.md" %}
