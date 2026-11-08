{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_preventivo.md" %}
# 🔍 View `vw_stato_sorgente_preventivo`

> 📝 **Descrizione**
>
> Resolver dello stato del preventivo per la proiezione di stato della sorgente polimorfa: per ogni preventivo lo stato vivo, nativo (alias fedeli: stato_codice_interno per la logica, stato_codice e stato_descrizione per il display) e proiettato in fase / esito / terminale come li dichiara config.stati_doc_preventivi. Una riga per preventivo, read-time. Il tipo PREVENTIVO e' a chiave uid (config.sorgenti.key_selector), agganciato per codice_interno e solo se attivo. La chiave esce in due forme: sorgente_chiave_uuid = uid (uuid), con sorgente_chiave_id NULL, e' la chiave nel suo tipo, quella che pratiche.fn_stato_sorgente confronta con la chiave tipizzata di pratiche.pratiche_sorgenti e quella da usare per cercare un documento (sotto RLS il confronto sul testo non arriva all'indice, uuid_out non e' leakproof); sorgente_uid e' lo stesso uid in testo, la chiave dei nodi della lineage e delle join. Fotografa lo stato memorizzato: il passaggio EMESSO -&gt; SCADUTO e' asincrono (job notturno) e la vista non ricalcola la scadenza. security_invoker: vale la RLS di chi legge. I consumatori la leggono da script.vw_stato_sorgente.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_preventivo
WITH (security_invoker=on) AS
SELECT s.id AS sorgente_tipo_id,
    (p.uid)::text AS sorgente_uid,
    sdp.codice_interno AS stato_codice_interno,
    sdp.codice AS stato_codice,
    sdp.descrizione AS stato_descrizione,
    sdp.fase,
    sdp.esito,
    sdp.terminale,
    p.uid AS sorgente_chiave_uuid,
    NULL::bigint AS sorgente_chiave_id
   FROM ((vendite.preventivi p
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'PREVENTIVO'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_preventivi sdp ON ((sdp.id = p.stato_doc_preventivo_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
