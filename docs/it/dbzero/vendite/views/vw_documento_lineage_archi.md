{% include-markdown "it/dbzero/vendite/manual/vw_documento_lineage_archi.md" %}
# 🔍 View `vw_documento_lineage_archi`

> 📝 **Descrizione**
>
> Il grafo di genealogia e transito dei documenti di vendita, una riga per arco (padre -&gt; figlio), con i due estremi decorati. E' la proiezione di vendite.fn_documento_lineage_archi(NULL, NULL), cioe' di tutti gli archi: chi vuole una parte del grafo chiama la funzione col seme, e un arco nuovo si aggiunge li'. Le colonne dell'arco (from_tipo_id, from_uid, to_tipo_id, to_uid, ruolo, arco, is_ramo_inverso, rango_origine) vengono dalla funzione; la decorazione da vendite.vw_documento_lineage_nodi, letta una volta (CTE MATERIALIZED) e in LEFT JOIN sui due estremi: from_codice e from_natura_doc_codice_interno; to_codice, to_stato_codice_interno, to_fase, to_is_abortito e to_natura_doc_codice_interno. Un nodo che chi legge non vede lascia l'arco con la decorazione NULL. La chiave del nodo e' il tipo (config.sorgenti.id) e la chiave del documento in testo secondo il key_selector: l'uid per preventivo e offerta, l'id per ordine, contratto, DDT, fattura, commessa e reso. Le lettere sono quattordici: A preventivo -&gt; ordine, B preventivo -&gt; commessa, C offerta -&gt; contratto, D offerta -&gt; ordine, E ordine -&gt; commessa, F contratto -&gt; commessa, G commessa -&gt; fattura, H ordine -&gt; DDT, N fattura rettificata -&gt; nota di credito, R DDT -&gt; reso, S reso -&gt; nota di credito, T reso -&gt; DDT di ri-consegna, U DDT -&gt; commessa, V offerta -&gt; sua revisione; il vocabolario e' chiuso e lo enumera il pgTAP vendite/test-documento-lineage-v1. is_ramo_inverso e' vero per i rami di ritorno, R e N. rango_origine dice quale sorgente e' l'origine quando piu' archi in avanti entrano nello stesso nodo: 10 trattativa, 20 impegno, 30 esecuzione, 40 consegna, 50 ritorno, piu' basso = piu' origine; sulla fattura vince G su S, sulla bolla H su T; V ha 60 e non e' un'origine. ruolo e' il ruolo_link di vendite.commesse_sorgenti sui rami B, E, F, U, NULL sugli altri. security_invoker=on: la RLS di chi legge vale su ogni tabella letta.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_documento_lineage_archi
WITH (security_invoker=on) AS
WITH nodi AS MATERIALIZED (
         SELECT n.tipo_id,
            n.uid,
            n.codice,
            n.stato_codice_interno,
            n.fase,
            n.is_abortito,
            n.natura_doc_codice_interno
           FROM vendite.vw_documento_lineage_nodi n
        )
 SELECT a.from_tipo_id,
    a.from_uid,
    nf.codice AS from_codice,
    a.to_tipo_id,
    a.to_uid,
    nt.codice AS to_codice,
    nt.stato_codice_interno AS to_stato_codice_interno,
    nt.fase AS to_fase,
    nt.is_abortito AS to_is_abortito,
    a.ruolo,
    a.arco,
    a.is_ramo_inverso,
    nf.natura_doc_codice_interno AS from_natura_doc_codice_interno,
    nt.natura_doc_codice_interno AS to_natura_doc_codice_interno,
    a.rango_origine
   FROM ((vendite.fn_documento_lineage_archi(NULL::bigint[], NULL::text[]) a(from_tipo_id, from_uid, to_tipo_id, to_uid, ruolo, arco, is_ramo_inverso, rango_origine)
     LEFT JOIN nodi nf ON (((nf.tipo_id = a.from_tipo_id) AND (nf.uid = a.from_uid))))
     LEFT JOIN nodi nt ON (((nt.tipo_id = a.to_tipo_id) AND (nt.uid = a.to_uid))));
```

</div>


---
{% include-markdown "signature-core.md" %}
