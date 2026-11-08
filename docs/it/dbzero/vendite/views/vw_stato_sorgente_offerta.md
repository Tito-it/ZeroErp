{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_offerta.md" %}
# 🔍 View `vw_stato_sorgente_offerta`

> 📝 **Descrizione**
>
> Resolver dello stato dell'offerta commerciale per la proiezione di stato della sorgente polimorfa: per ogni offerta lo stato vivo, nativo (alias fedeli: stato_codice_interno per la logica, stato_codice e stato_descrizione per il display) e proiettato in fase / esito / terminale come li dichiara config.stati_doc_offerte. Una riga per offerta, read-time. Il tipo OFFERTA_COMMERCIALE e' a chiave uid (config.sorgenti.key_selector), agganciato per codice_interno e solo se attivo. La chiave esce in due forme: sorgente_chiave_uuid = uid (uuid), con sorgente_chiave_id NULL, e' la chiave nel suo tipo, quella che pratiche.fn_stato_sorgente confronta con la chiave tipizzata di pratiche.pratiche_sorgenti e quella da usare per cercare un documento (sotto RLS il confronto sul testo non arriva all'indice, uuid_out non e' leakproof); sorgente_uid e' lo stesso uid in testo, la chiave dei nodi della lineage e delle join. security_invoker: vale la RLS di chi legge. I consumatori la leggono da script.vw_stato_sorgente.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_offerta
WITH (security_invoker=on) AS
SELECT s.id AS sorgente_tipo_id,
    (oc.uid)::text AS sorgente_uid,
    sdo.codice_interno AS stato_codice_interno,
    sdo.codice AS stato_codice,
    sdo.descrizione AS stato_descrizione,
    sdo.fase,
    sdo.esito,
    sdo.terminale,
    oc.uid AS sorgente_chiave_uuid,
    NULL::bigint AS sorgente_chiave_id
   FROM ((vendite.offerte_commerciali oc
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_offerte sdo ON ((sdo.id = oc.stato_doc_offerta_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
