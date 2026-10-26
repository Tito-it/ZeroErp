{% include-markdown "it/dbzero/config/manual/vw_codici_errore.md" %}
# 🔍 View `vw_codici_errore`

> 📝 **Descrizione**
>
> Superficie di REVISIONE: la classe accanto alla frase, per vedere a occhio nudo una classe che contraddice il testo. LEFT JOIN di proposito — un codice senza messaggio deve comparire, e' uno dei difetti da vedere. ⚠️ UNA RIGA PER (codice, lingua): per contare i codici usare vw_codici_errore_identita. Non e' un cancello: il cancello e' classe NOT NULL.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW config.vw_codici_errore
WITH (security_invoker=true) AS
SELECT c.codice,
    c.classe,
    c.obsoleto_dal,
    c.note,
    m.lingua,
    m.messaggio,
    m.causa,
    m.soluzione
   FROM (config.codici_errore c
     LEFT JOIN config.messaggi_errore m ON ((m.codice = c.codice)));
```

</div>


---
{% include-markdown "signature-core.md" %}
