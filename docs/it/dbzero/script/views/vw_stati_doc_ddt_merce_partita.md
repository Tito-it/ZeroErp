{% include-markdown "it/dbzero/script/manual/vw_stati_doc_ddt_merce_partita.md" %}
# 🔍 View `vw_stati_doc_ddt_merce_partita`

> 📝 **Descrizione**
>
> BB (2026-10-12, brief-db-date-consegna-righe-in-blocco §4.1, regola del 2, scelta (a) di Tid): in questo stato del DDT la merce e' partita? Una riga per ogni stato di config.stati_doc_ddt; merce_partita = uscito dalla bozza (ordine &gt;= quello di EMESSO) e non abortito (is_abortito false). Letta dal catalogo, non da un elenco di codici: uno stato nuovo fra EMESSO e CONSEGNATO entra da solo. ⛔ Mai NULL: uno stato con ordine NULL, o un catalogo senza EMESSO, risponde false. Sede unica della regola che viveva in quattro posti: vendite.fn_partite_merce (CTE riga e ponte_riga), vendite.fn_ordine_riga_spedita, dbops.vw_ddt_emessi_senza_scarico (che la scriveva come elenco EMESSO, SPEDITO, CONSEGNATO, RESO). Chi filtra mette merce_partita in WHERE, chi distingue la proietta. security_invoker.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_stati_doc_ddt_merce_partita
WITH (security_invoker=true) AS
SELECT s.id,
    s.codice_interno,
    COALESCE(((NOT s.is_abortito) AND (s.ordine >= e.ordine)), false) AS merce_partita
   FROM (config.stati_doc_ddt s
     LEFT JOIN config.stati_doc_ddt e ON (((e.codice_interno)::text = 'EMESSO'::text)));
```

</div>


---
{% include-markdown "signature-core.md" %}
