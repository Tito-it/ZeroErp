{% include-markdown "it/dbzero/vendite/manual/vw_resi_righe_effettive.md" %}
# 🔍 View `vw_resi_righe_effettive`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_resi_righe_effettive
WITH (security_invoker=on) AS
SELECT rr.id AS resi_riga_id,
    rr.reso_id,
    rr.ddt_riga_id,
    rr.ordine_riga_id,
    rr.tipo_reso_id,
    tr.riapre_residuo,
    rr.quantita
   FROM (((vendite.resi_righe rr
     JOIN vendite.resi r ON ((r.id = rr.reso_id)))
     JOIN config.stati_doc_reso sr ON ((sr.id = r.stato_doc_reso_id)))
     JOIN config.tipi_reso tr ON ((tr.id = rr.tipo_reso_id)))
  WHERE (((sr.codice_interno)::text = 'CONFERMATO'::text) AND (rr.attivo IS TRUE));
```


---
{% include-markdown "signature-core.md" %}
