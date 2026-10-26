{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_reso.md" %}
# 🔍 View `vw_stato_sorgente_reso`

> 📝 **Descrizione**
>
> Sesto ramo della proiezione di stato (brief-db-fatturazione-ddt-resi §4a, step 6b): traduce lo stato del reso nel vocabolario comune della sorgente polimorfa. Chiave = resi.id::text (config.sorgenti.key_selector = id per RESO_VENDITA). esito/terminale derivati come nel ramo DDT: is_abortito -&gt; NEGATIVO (ANNULLATO), fase CHIUSO non abortito -&gt; POSITIVO, altrimenti NULL. Dal 2026-07-18 il catalogo dichiara CONFERMATO fase CHIUSO (correzione Tid: un reso confermato E' concluso — la ri-consegna e' un altro documento) -&gt; un reso confermato proietta POSITIVO/terminale. La matrice ammette ancora CONFERMATO-&gt;ANNULLATO come storno guardato: terminale = conclusione commerciale, non lucchetto. rev 2026-07-18. ⭐ rev 2026-10-05 (20261005-23): espone in coda la chiave nel suo tipo — sorgente_chiave_id = id (bigint), sorgente_chiave_uuid NULL — accanto alla forma testuale sorgente_uid, che resta la chiave del lineage e delle join. Serve a chi cerca UN documento: sotto RLS il confronto sul testo non arriva all'indice (int8out non e' leakproof), quello sul bigint si'.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_reso
WITH (security_invoker=on) AS
SELECT s.id AS sorgente_tipo_id,
    (r.id)::text AS sorgente_uid,
    sdr.codice_interno AS stato_codice_interno,
    sdr.codice AS stato_codice,
    sdr.descrizione AS stato_descrizione,
    sdr.fase,
    (
        CASE
            WHEN sdr.is_abortito THEN 'NEGATIVO'::text
            WHEN ((sdr.fase)::text = 'CHIUSO'::text) THEN 'POSITIVO'::text
            ELSE NULL::text
        END)::character varying AS esito,
    ((sdr.fase)::text = 'CHIUSO'::text) AS terminale,
    NULL::uuid AS sorgente_chiave_uuid,
    r.id AS sorgente_chiave_id
   FROM ((vendite.resi r
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'RESO_VENDITA'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_reso sdr ON ((sdr.id = r.stato_doc_reso_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
