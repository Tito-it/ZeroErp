{% include-markdown "it/dbzero/vendite/manual/vw_documento_lineage_nodi.md" %}
# 🔍 View `vw_documento_lineage_nodi`

> 📝 **Descrizione**
>
> La dimensione nodo del grafo di genealogia dei documenti di vendita: una riga per documento delle otto testate-nodo (preventivo, offerta, ordine, contratto, DDT, fattura, commessa, reso), anche senza archi. E' la proiezione di vendite.fn_documento_lineage_nodi(NULL, NULL): stesse colonne, stessi tipi; chi vuole solo alcuni documenti chiama la funzione col seme. La chiave del nodo e' tipo_id (config.sorgenti.id, risolto per codice_interno) e uid, la chiave del documento in testo nella forma canonica del key_selector: l'uid per preventivo e offerta, l'id per gli altri (il nome della colonna non dice la chiave: per un ordine vale il suo id); tipo_codice_interno e' il codice del tipo. codice e' il numero leggibile del documento (per la fattura il numero composto da vendite.fn_numero_documento_fattura); stato_codice_interno, stato_codice e stato_descrizione lo stato nativo; fase e is_abortito la proiezione normalizzata; pipeline_rank la posizione del tipo nel flusso verso la fattura, lo spareggio della frontiera; natura_doc_codice_interno e natura_doc_descrizione la natura fiscale (config.nature_doc_fiscale, in LEFT JOIN), valorizzata solo sulla fattura: distingue la fattura dalla nota di credito. La legge vendite.vw_documento_lineage_archi per decorare gli estremi degli archi. security_invoker=on: la RLS di chi legge.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_documento_lineage_nodi
WITH (security_invoker=on) AS
SELECT tipo_id,
    uid,
    codice,
    stato_codice_interno,
    stato_codice,
    stato_descrizione,
    (fase)::character varying(20) AS fase,
    is_abortito,
    pipeline_rank,
    natura_doc_codice_interno,
    natura_doc_descrizione,
    (tipo_codice_interno)::character varying(50) AS tipo_codice_interno
   FROM vendite.fn_documento_lineage_nodi(NULL::bigint[], NULL::text[]) n(tipo_id, uid, codice, stato_codice_interno, stato_codice, stato_descrizione, fase, is_abortito, pipeline_rank, natura_doc_codice_interno, natura_doc_descrizione, tipo_codice_interno);
```

</div>


---
{% include-markdown "signature-core.md" %}
