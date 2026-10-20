{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_ddt.md" %}
# 🔍 View `vw_stato_sorgente_ddt`

> 📝 **Descrizione**
>
> Quinto ramo della proiezione di stato (brief-db-fatturazione-ddt-resi §4a, step 6b): traduce lo stato del DDT nel vocabolario comune della sorgente polimorfa. Chiave = ddt.id::text, come dichiara config.sorgenti.key_selector per DDT_VENDITA (NON l'uid: quello e' la colonna tipizzata diretta resi.sorgente_uid, meccanismo diverso). esito e terminale sono DERIVATI, perche' config.stati_doc_ddt non li espone: is_abortito -&gt; NEGATIVO, fase CHIUSO non abortito -&gt; POSITIVO, altrimenti NULL; terminale = fase CHIUSO. Conseguenza voluta: lo stato RESO risulta POSITIVO/terminale, perche' il catalogo lo dichiara non abortito (merce tornata != documento annullato). Cambiare quella semantica e' materia di CATALOGO, non di questa vista. rev 2026-07-18. ⭐ rev 2026-10-05 (20261005-23): espone in coda la chiave nel suo tipo — sorgente_chiave_id = id (bigint), sorgente_chiave_uuid NULL — accanto alla forma testuale sorgente_uid, che resta la chiave del lineage e delle join. Serve a chi cerca UN documento: sotto RLS il confronto sul testo non arriva all'indice (int8out non e' leakproof), quello sul bigint si'.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_ddt
WITH (security_invoker=on) AS
SELECT s.id AS sorgente_tipo_id,
    (d.id)::text AS sorgente_uid,
    sdd.codice_interno AS stato_codice_interno,
    sdd.codice AS stato_codice,
    sdd.descrizione AS stato_descrizione,
    sdd.fase,
    (
        CASE
            WHEN sdd.is_abortito THEN 'NEGATIVO'::text
            WHEN ((sdd.fase)::text = 'CHIUSO'::text) THEN 'POSITIVO'::text
            ELSE NULL::text
        END)::character varying AS esito,
    ((sdd.fase)::text = 'CHIUSO'::text) AS terminale,
    NULL::uuid AS sorgente_chiave_uuid,
    d.id AS sorgente_chiave_id
   FROM ((vendite.ddt d
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'DDT_VENDITA'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_ddt sdd ON ((sdd.id = d.stato_doc_ddt_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
