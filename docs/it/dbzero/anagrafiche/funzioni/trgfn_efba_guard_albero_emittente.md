{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_efba_guard_albero_emittente.md" %}
# ⚙️ Funzione `trgfn_efba_guard_albero_emittente`

```sql
CREATE FUNCTION trgfn_efba_guard_albero_emittente()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_efba_guard_albero_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Il collegamento di un BA nasce o cambia azienda: padre e figli
    -- restano sulla stessa azienda. La riga della predefinita e la
    -- cancellazione (rifiutata a05) non toccano nessun albero.
    IF TG_OP <> 'DELETE' AND NEW.billing_account_id IS NOT NULL THEN
        PERFORM anagrafiche.fn_guard_albero_ba_emittente(NEW.billing_account_id);
    END IF;
    RETURN NULL;   -- trigger AFTER: il valore di ritorno e' ignorato
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_efba_guard_albero_emittente()
IS 'Trigger AFTER INSERT, UPDATE di anagrafiche.emittenti_fiscali_billing_account: quando il collegamento di un billing account nasce o cambia azienda, padre e figli restano sulla stessa azienda (anagrafiche.fn_guard_albero_ba_emittente, E_ALBERO_EMITTENTE_MISTO). La riga dell''azienda predefinita non si giudica: spostarla non cambia l''azienda di nessun cliente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
