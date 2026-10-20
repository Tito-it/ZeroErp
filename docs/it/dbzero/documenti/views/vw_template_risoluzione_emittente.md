{% include-markdown "it/dbzero/documenti/manual/vw_template_risoluzione_emittente.md" %}
# 🔍 View `vw_template_risoluzione_emittente`

> 📝 **Descrizione**
>
> Per ogni emittente e ogni coppia (tipo di documento, sorgente) con almeno un modello standard o di quell'emittente, in qualunque stato: l'esito della risoluzione (EMITTENTE, SENZA_PREDEFINITO, STANDARD, NON_RISOLTO), il modello, la versione e quanti modelli suoi possono stampare (2026-10-21, brief-db-modelli-documento-standard §10.3 K-5). La regola e' documenti.fn_template_esito_risoluzione, la stessa della stampa: la vista aggiunge solo le righe. Lettura della lista Modelli documento.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW documenti.vw_template_risoluzione_emittente
WITH (security_invoker=true) AS
SELECT e.id AS emittente_fiscale_id,
    c.tipo_documento_output_id,
    c.sorgente_tipo_id,
    r.esito,
    r.template_documento_id,
    r.template_versione_id,
    r.modelli_stampabili
   FROM ((anagrafiche.emittenti_fiscali e
     CROSS JOIN LATERAL ( SELECT DISTINCT t.tipo_documento_output_id,
            t.sorgente_tipo_id
           FROM documenti.template_documenti t
          WHERE (t.standard OR (t.emittente_fiscale_id = e.id))) c)
     CROSS JOIN LATERAL documenti.fn_template_esito_risoluzione(e.id, c.tipo_documento_output_id, c.sorgente_tipo_id) r(esito, template_documento_id, template_versione_id, modelli_stampabili));
```


---
{% include-markdown "signature-core.md" %}
