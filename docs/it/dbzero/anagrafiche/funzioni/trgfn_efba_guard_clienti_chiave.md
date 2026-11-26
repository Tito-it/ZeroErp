{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_efba_guard_clienti_chiave.md" %}
# ⚙️ Funzione `trgfn_efba_guard_clienti_chiave`

```sql
CREATE FUNCTION trgfn_efba_guard_clienti_chiave()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_efba_guard_clienti_chiave()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- L'azienda di un BA e' nella chiave del cliente manuale: quando il
    -- collegamento nasce o cambia azienda, i clienti del BA si
    -- ricontrollano. La riga della predefinita e la cancellazione
    -- (rifiutata a05) non cambiano la chiave di nessun cliente.
    IF TG_OP <> 'DELETE' AND NEW.billing_account_id IS NOT NULL THEN
        PERFORM anagrafiche.fn_guard_clienti_chiave_unica_di(NEW.billing_account_id, NULL);
    END IF;
    RETURN NULL;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_efba_guard_clienti_chiave()
IS 'Constraint trigger function (AFTER INSERT OR UPDATE OR DELETE, DEFERRABLE INITIALLY DEFERRED) di anagrafiche.emittenti_fiscali_billing_account: l''azienda di un billing account e'' nella chiave del cliente manuale; quando il collegamento nasce o cambia azienda si ricontrollano i clienti del billing account (anagrafiche.fn_guard_clienti_chiave_unica_di, E_CLIENTE_STESSA_CHIAVE). La riga dell''azienda predefinita non si giudica: spostarla non cambia la chiave di nessun cliente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
