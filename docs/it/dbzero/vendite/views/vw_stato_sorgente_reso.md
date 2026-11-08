{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_reso.md" %}
# 🔍 View `vw_stato_sorgente_reso`

> 📝 **Descrizione**
>
> Resolver dello stato del reso di vendita per la proiezione di stato della sorgente polimorfa: traduce lo stato nativo del reso (config.stati_doc_reso) nel vocabolario comune fase / esito / terminale. Una riga per reso, read-time. Il tipo RESO_VENDITA e' a chiave id (config.sorgenti.key_selector), agganciato per codice_interno e solo se attivo. La chiave esce in due forme: sorgente_chiave_id = id (bigint), con sorgente_chiave_uuid NULL, e' la chiave nel suo tipo, quella che pratiche.fn_stato_sorgente confronta con la chiave tipizzata di pratiche.pratiche_sorgenti e quella da usare per cercare un reso (sotto RLS il confronto sul testo non arriva all'indice, int8out non e' leakproof); sorgente_uid e' lo stesso id in testo, la chiave dei nodi della lineage e delle join. Le colonne sorgente_* del reso sono un'altra cosa: dicono da quale bolla nasce il reso, con l'id della bolla in sorgente_id, e non c'entrano con la chiave del reso. esito e terminale sono derivati, come nel ramo vendite.vw_stato_sorgente_ddt, perche' config.stati_doc_reso non li espone: is_abortito -&gt; NEGATIVO (ANNULLATO), fase CHIUSO non abortito -&gt; POSITIVO (CONFERMATO), altrimenti NULL (DRAFT); terminale = fase CHIUSO. Un reso confermato e' concluso: la riconsegna e' un altro documento. terminale e' la conclusione commerciale, non un lucchetto: la matrice ammette ancora CONFERMATO -&gt; ANNULLATO, lo storno del reso confermato (vendite.fn_annulla_reso). security_invoker: vale la RLS di chi legge. I consumatori la leggono da script.vw_stato_sorgente.

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
