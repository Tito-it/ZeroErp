{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_contratto.md" %}
# 🔍 View `vw_stato_sorgente_contratto`

> 📝 **Descrizione**
>
> Resolver dello stato del contratto per la proiezione di stato della sorgente polimorfa: per ogni contratto lo stato vivo, nativo (alias fedeli: stato_codice_interno per la logica, stato_codice e stato_descrizione per il display) e proiettato in fase / esito / terminale come li dichiara config.stati_doc_contratti. terminale e' un asse distinto da is_abortito: CESSATO e' terminale ma non abortito. Una riga per contratto, read-time. Il tipo CONTRATTO e' a chiave id (config.sorgenti.key_selector), agganciato per codice_interno e solo se attivo. La chiave esce in due forme: sorgente_chiave_id = id (bigint), con sorgente_chiave_uuid NULL, e' la chiave nel suo tipo, quella che pratiche.fn_stato_sorgente confronta con la chiave tipizzata di pratiche.pratiche_sorgenti e quella da usare per cercare un documento (sotto RLS il confronto sul testo non arriva all'indice, int8out non e' leakproof); sorgente_uid e' lo stesso id in testo, la chiave dei nodi della lineage e delle join. security_invoker: vale la RLS di chi legge. I consumatori la leggono da script.vw_stato_sorgente.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_contratto
WITH (security_invoker=on) AS
SELECT s.id AS sorgente_tipo_id,
    (c.id)::text AS sorgente_uid,
    sdc.codice_interno AS stato_codice_interno,
    sdc.codice AS stato_codice,
    sdc.descrizione AS stato_descrizione,
    sdc.fase,
    sdc.esito,
    sdc.terminale,
    NULL::uuid AS sorgente_chiave_uuid,
    c.id AS sorgente_chiave_id
   FROM ((vendite.contratti c
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'CONTRATTO'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_contratti sdc ON ((sdc.id = c.stato_doc_contratto_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
