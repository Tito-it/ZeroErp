{% include-markdown "it/dbzero/vendite/manual/vw_documento_lineage_nodi.md" %}
# 🔍 View `vw_documento_lineage_nodi`

> 📝 **Descrizione**
>
> ⭐ rev 2026-10-11 (brief-db-lineage-seminata-per-chiave, giro 1): la vista e' la PROIEZIONE di vendite.fn_documento_lineage_nodi(NULL, NULL), un corpo solo; chi vuole una parte del grafo chiama la funzione col seme. Stesse colonne, stessi tipi. Lineage documenti vendite: dimensione nodo condivisa (una riga per documento nodo, chiave polimorfa tipo_id+uid::text per key_selector, stato/fase/is_abortito normalizzati, pipeline_rank per il tie-break frontiera). Base di vw_documento_lineage_archi, vw_documento_lineage e fn_documento_lineage. security_invoker=on. ⭐ rev 2026-08-29 — il `codice` del nodo FATTURA e' il NUMERO DOCUMENTO, non piu' il contatore nudo: lo compone la sede unica vendite.fn_numero_documento_fattura («numero - serie», senza anno). Prima usciva «1», che non e' sbagliato ma e' AMBIGUO — nello stesso anno possono esistere una fattura 1 e una nota di credito 1, e in lista erano indistinguibili. Per gli altri sei rami `numero` E' gia' il numero parlante (DDT0000031); per la fattura e' un bigint e l'identita' sta in tre colonne nullable. ⚠️ La funzione e' IMMUTABLE e prende i valori, quindi e' inlineata qui: non e' una lettura per riga. ⭐ rev 2026-08-20: il nodo porta anche natura_doc_codice_interno/natura_doc_descrizione (da config.nature_doc_fiscale.codice_interno/descrizione). Serve perche' il grafo e' nato quando FATTURA era una cosa sola: due nodi FATTURA della stessa commessa — la fattura e la nota di credito che la rettifica — erano indistinguibili, stesso tipo e stesso stato, con `codice` NULL finche' non numerati. La natura e' un ASSE DIVERSO dal tipo documento (il tipo dice da quale tabella viene il nodo, la natura che cosa e' fiscalmente) ed esiste solo per le fatture: negli altri sette rami e' NULL, ed e' corretto. LEFT JOIN sulla natura perche' natura_doc_id e' nullable: con un JOIN una fattura senza natura sparirebbe dal grafo.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

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
