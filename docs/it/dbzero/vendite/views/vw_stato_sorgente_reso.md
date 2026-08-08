{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_reso.md" %}
# 🔍 View `vw_stato_sorgente_reso`

> 📝 **Descrizione**
>
> Sesto ramo della proiezione di stato (brief-db-fatturazione-ddt-resi §4a, step 6b): traduce lo stato del reso nel vocabolario comune della sorgente polimorfa. Chiave = resi.id::text (config.sorgenti.key_selector = id per RESO_VENDITA). esito/terminale derivati come nel ramo DDT: is_abortito -&gt; NEGATIVO (ANNULLATO), fase CHIUSO non abortito -&gt; POSITIVO, altrimenti NULL. Dal 2026-07-18 il catalogo dichiara CONFERMATO fase CHIUSO (correzione Tid: un reso confermato E' concluso — la ri-consegna e' un altro documento) -&gt; un reso confermato proietta POSITIVO/terminale. La matrice ammette ancora CONFERMATO-&gt;ANNULLATO come storno guardato: terminale = conclusione commerciale, non lucchetto. rev 2026-07-18.

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_reso AS
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
    ((sdr.fase)::text = 'CHIUSO'::text) AS terminale
   FROM ((vendite.resi r
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'RESO_VENDITA'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_reso sdr ON ((sdr.id = r.stato_doc_reso_id)));
```


---
{% include-markdown "signature-core.md" %}
