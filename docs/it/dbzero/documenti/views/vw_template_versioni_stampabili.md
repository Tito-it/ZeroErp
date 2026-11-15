{% include-markdown "it/dbzero/documenti/manual/vw_template_versioni_stampabili.md" %}
# 🔍 View `vw_template_versioni_stampabili`

> 📝 **Descrizione**
>
> I modelli che possono stampare oggi, una riga per modello con la versione con cui stampa: modello attivo, versione attiva fuori bozza (PUBBLICATA o OBSOLETA) e valida alla data operativa. La validita' decide, lo stato separa le versioni operative dalla BOZZA: una versione OBSOLETA, superata da una pubblicazione successiva, stampa fino all'ultimo giorno della sua validita', cioe' fino alla vigilia della nuova. Sede unica del predicato «puo' stampare»: la leggono documenti.fn_risolvi_template_applicabile (anche per il modello indicato), documenti.fn_template_esito_risoluzione, documenti.fn_personalizza_template_standard e documenti.vw_template_personalizzati_scarto. Una riga per modello per costruzione: ex_template_documenti_versioni_no_overlap_pubblicata, esteso alle OBSOLETE.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW documenti.vw_template_versioni_stampabili
WITH (security_invoker=true) AS
SELECT t.id AS template_documento_id,
    v.id AS template_versione_id,
    t.tipo_documento_output_id,
    t.sorgente_tipo_id,
    t.emittente_fiscale_id,
    t.standard,
    t.is_default
   FROM (documenti.template_documenti t
     JOIN documenti.template_documenti_versioni v ON (((v.template_documento_id = t.id) AND ((v.stato)::text = ANY ((ARRAY['PUBBLICATA'::character varying, 'OBSOLETA'::character varying])::text[])) AND v.attivo AND (v.validita @> ( SELECT script.fn_data_operativa() AS fn_data_operativa)))))
  WHERE t.attivo;
```

</div>


---
{% include-markdown "signature-core.md" %}
