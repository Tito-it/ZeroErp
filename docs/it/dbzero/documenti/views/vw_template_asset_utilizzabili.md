{% include-markdown "it/dbzero/documenti/manual/vw_template_asset_utilizzabili.md" %}
# 🔍 View `vw_template_asset_utilizzabili`

> 📝 **Descrizione**
>
> Le risorse dei modelli (loghi, firme, immagini, PDF, fogli di stile) che si possono usare oggi: accese e valide alla data operativa. Una riga per risorsa, con le chiavi con cui la si cerca: azienda, tipo, codice interno. Sede unica della regola «utilizzabile oggi», per il render, che cerca la risorsa citata dal modello, e per il filtro delle risorse utilizzabili della lista. Si legge con i privilegi di chi interroga (security_invoker).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW documenti.vw_template_asset_utilizzabili
WITH (security_invoker=true) AS
SELECT id AS template_asset_id,
    emittente_fiscale_id,
    asset_tipo_id,
    codice_interno
   FROM documenti.template_asset a
  WHERE (attivo AND (validita @> ( SELECT script.fn_data_operativa() AS fn_data_operativa)));
```

</div>


---
{% include-markdown "signature-core.md" %}
