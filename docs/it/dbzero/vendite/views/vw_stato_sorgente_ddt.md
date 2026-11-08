{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_ddt.md" %}
# 🔍 View `vw_stato_sorgente_ddt`

> 📝 **Descrizione**
>
> Resolver dello stato della bolla di vendita per la proiezione di stato della sorgente polimorfa: traduce lo stato nativo del DDT (config.stati_doc_ddt) nel vocabolario comune fase / esito / terminale. Una riga per bolla, read-time. Il tipo DDT_VENDITA e' a chiave id (config.sorgenti.key_selector), agganciato per codice_interno e solo se attivo. La chiave esce in due forme: sorgente_chiave_id = id (bigint), con sorgente_chiave_uuid NULL, e' la chiave nel suo tipo, quella che pratiche.fn_stato_sorgente confronta con la chiave tipizzata di pratiche.pratiche_sorgenti e quella da usare per cercare una bolla (sotto RLS il confronto sul testo non arriva all'indice, int8out non e' leakproof); sorgente_uid e' lo stesso id in testo, la chiave dei nodi della lineage e delle join. Ogni documento che nasce da una bolla, il reso compreso, la dichiara con l'id in sorgente_id: cercarla per uid non trova. esito e terminale sono derivati, perche' config.stati_doc_ddt non li espone: is_abortito -&gt; NEGATIVO, fase CHIUSO non abortito -&gt; POSITIVO, altrimenti NULL; terminale = fase CHIUSO. Lo stato RESO risulta POSITIVO e terminale, perche' il catalogo lo dichiara non abortito (merce tornata non e' documento annullato): cambiare quella semantica e' materia del catalogo, non della vista. security_invoker: vale la RLS di chi legge. I consumatori la leggono da script.vw_stato_sorgente.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

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
