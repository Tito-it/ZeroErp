{% include-markdown "it/dbzero/ui/manual/trgfn_preferenza_data_update.md" %}
# ⚙️ Funzione `trgfn_preferenza_data_update`

```sql
CREATE FUNCTION trgfn_preferenza_data_update()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_preferenza_data_update()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: data_update di una preferenza di lista o di dashboard e' l'ora
--   della scrittura; il valore che arriva da chi scrive non conta.
BEGIN
  NEW.data_update := CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION ui.trgfn_preferenza_data_update()
IS 'Scrive data_update di ui.lista_preferenza_utente e ui.dashboard_preferenza_utente a ogni INSERT e UPDATE, con l''ora della transazione: il valore passato da chi scrive non conta. Le preferenze non hanno audit, per scelta; questa e'' la sola sede della loro data di scrittura.';
```

</div>

---
{% include-markdown "signature-core.md" %}
