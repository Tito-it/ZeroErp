{% include-markdown "it/dbzero/anagrafiche/manual/vw_clienti_codice_ba.md" %}
# 🔍 View `vw_clienti_codice_ba`

> 📝 **Descrizione**
>
> Vista flat clienti con codice da billing_account, stato e date ciclo vita. Usata per ricerca codice universale (entita_tabella in tipi_ruoli) e come source dati per dettaglio entita' CL. stato_codice_interno = codice_interno (logica), stato_codice = codice (display).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_clienti_codice_ba
WITH (security_invoker=on) AS
SELECT cl.soggetto_ruolo_id,
    cl.id,
    cl.id AS entita_id,
    cl.billing_account_id,
    ba.codice,
    cl.utility_id,
    cl.stato_cliente_id,
    sc.codice_interno AS stato_codice_interno,
    sc.codice AS stato_codice,
    sc.descrizione_breve AS stato_descrizione,
    cl.data_attivazione,
    cl.data_sospensione,
    cl.data_riattivazione,
    cl.data_chiusura
   FROM ((anagrafiche.clienti cl
     JOIN config.stati_cliente sc ON ((sc.id = cl.stato_cliente_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = cl.billing_account_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
