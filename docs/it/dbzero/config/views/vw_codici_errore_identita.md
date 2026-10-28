{% include-markdown "it/dbzero/config/manual/vw_codici_errore_identita.md" %}
# 🔍 View `vw_codici_errore_identita`

> 📝 **Descrizione**
>
> Identita' dei codici errore: UNA riga per codice, nessun join con le traduzioni. Sorgente del generatore backend di error_policies_generated.py. L'ORDER BY e' una cintura: il contratto e' che il generatore metta il suo. Non usare vw_codici_errore al suo posto — quella moltiplica per lingua e filtrarla perde i codici senza messaggio.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW config.vw_codici_errore_identita
WITH (security_invoker=true) AS
SELECT codice,
    classe,
    obsoleto_dal,
    note
   FROM config.codici_errore c
  ORDER BY codice;
```

</div>


---
{% include-markdown "signature-core.md" %}
