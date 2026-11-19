{% include-markdown "it/dbzero/config/manual/vw_email_account_seed.md" %}
# 🔍 View `vw_email_account_seed`

> 📝 **Descrizione**
>
> Il segno del seed di primo impianto sulle righe degli account di posta (config.email_account): una riga per riga (email_account_id). nata_dal_seed: la riga l'ha installata il software (dbops.fn_seed_riga), non l'azienda. campi_del_software: su una riga nata dal seed le colonne che l'installazione non modifica, dal montaggio del trigger (dbops.fn_seed_colonne_del_software), le stesse su cui il guard script.trgfn_seed_primo_impianto alza E_SEED_COLONNA_DEL_SOFTWARE; vuoto, mai NULL, su una riga dell'installazione o quando la forma della tabella non ne ha. Non elenca le colonne che altri meccanismi tengono ferme (script.trgfn_lock_columns). Nessuna azione di eliminazione: la riga non si cancella (dbops.automation_delete_block), si spegne con attivo. security_invoker. Si filtra per email_account_id.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW config.vw_email_account_seed
WITH (security_invoker=true) AS
SELECT ea.id AS email_account_id,
    seed.nata_dal_seed,
        CASE
            WHEN seed.nata_dal_seed THEN sw.colonne
            ELSE ARRAY[]::text[]
        END AS campi_del_software
   FROM ((config.email_account ea
     CROSS JOIN ( SELECT dbops.fn_seed_colonne_del_software('config.email_account'::regclass) AS colonne) sw)
     CROSS JOIN LATERAL ( SELECT (EXISTS ( SELECT 1
                   FROM dbops.fn_seed_riga('config.email_account'::regclass, (ea.id)::text) fn_seed_riga(seed_riga_id, schema_name, table_name, personalizzata_il))) AS nata_dal_seed) seed);
```

</div>


---
{% include-markdown "signature-core.md" %}
