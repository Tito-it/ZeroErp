# 🔍 View `vw_resi_da_accreditare`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_resi_da_accreditare
WITH (security_invoker=on) AS
SELECT rr.id AS resi_riga_id,
    r.id AS reso_id,
    r.uid AS reso_uid,
    r.numero AS reso_numero,
    r.data,
    r.emittente_fiscale_id,
    r.billing_account_id,
    ba.codice AS ba_codice,
    r.destinatario_soggetto_ruolo_id,
    s_dest.ragione_sociale_completa AS destinatario_denominazione,
    rr.articolo_id,
    rr.descrizione,
    rr.quantita,
    rr.qta_operativa,
    rr.uom_operativa_id,
    rr.motivo,
    rr.ddt_riga_id,
    dr.ddt_id,
    d.numero AS ddt_numero,
    rr.ordine_riga_id
   FROM ((((((((vendite.resi_righe rr
     JOIN vendite.resi r ON ((r.id = rr.reso_id)))
     JOIN config.stati_doc_reso sr ON ((sr.id = r.stato_doc_reso_id)))
     JOIN config.tipi_reso tr ON ((tr.id = rr.tipo_reso_id)))
     JOIN vendite.ddt_righe dr ON ((dr.id = rr.ddt_riga_id)))
     JOIN vendite.ddt d ON ((d.id = dr.ddt_id)))
     JOIN anagrafiche.soggetti_ruoli sr_dest ON ((sr_dest.id = r.destinatario_soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s_dest ON ((s_dest.id = sr_dest.soggetto_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = r.billing_account_id)))
  WHERE (((sr.codice_interno)::text = 'CONFERMATO'::text) AND (tr.riapre_residuo = false) AND (rr.attivo IS TRUE));
```


---
{% include-markdown "signature-core.md" %}
