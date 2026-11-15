# 🔍 View `vw_stati_doc_reso_merce_rientrata`

> 📝 **Descrizione**
>
> In questo stato del reso la merce e' rientrata? Una riga per ogni stato di config.stati_doc_reso; merce_rientrata = dallo stato di emissione in poi (ordine &gt;= quello dello stato con emissione = true) e non abortito (is_abortito false). La regola si legge dal vocabolario, non da un codice: uno stato nuovo dopo l'emissione entra da solo. Mai NULL: uno stato con ordine NULL, o un vocabolario senza stato di emissione, risponde false. Gemella di script.vw_stati_doc_ddt_merce_partita. Sede unica della regola: la leggono dbops.vw_resi_confermati_senza_carico, vendite.vw_resi_righe_effettive e vendite.vw_resi_da_riconsegnare. Chi filtra mette merce_rientrata in WHERE, chi distingue la proietta. security_invoker.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_stati_doc_reso_merce_rientrata
WITH (security_invoker=true) AS
SELECT s.id,
    s.codice_interno,
    COALESCE(((NOT s.is_abortito) AND (s.ordine >= c.ordine)), false) AS merce_rientrata
   FROM (config.stati_doc_reso s
     LEFT JOIN config.stati_doc_reso c ON (c.emissione));
```

</div>


---
{% include-markdown "signature-core.md" %}
