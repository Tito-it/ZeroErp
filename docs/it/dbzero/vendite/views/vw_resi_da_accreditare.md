{% include-markdown "it/dbzero/vendite/manual/vw_resi_da_accreditare.md" %}
# 🔍 View `vw_resi_da_accreditare`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_resi_da_accreditare
WITH (security_invoker=on) AS
WITH acc AS (
         SELECT ct.ordine_riga_id,
            ct.tenuti,
            ct.fatturati,
            (- ct.differenza) AS accredito_partita
           FROM vendite.vw_contatore_merce ct
          WHERE (ct.differenza < (0)::numeric)
        ), dist AS (
         SELECT e.resi_riga_id,
            e.reso_id,
            e.ddt_riga_id,
            e.ordine_riga_id,
            e.riapre_residuo,
            e.quantita AS qta_resa,
            a.tenuti,
            a.fatturati,
            GREATEST((0)::numeric, LEAST(e.quantita, (a.accredito_partita - COALESCE(sum(e.quantita) OVER (PARTITION BY e.ordine_riga_id ORDER BY e.resi_riga_id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), (0)::numeric)))) AS accredito_dovuto
           FROM (vendite.vw_resi_righe_effettive e
             JOIN acc a ON ((a.ordine_riga_id = e.ordine_riga_id)))
        )
 SELECT x.resi_riga_id,
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
    x.ddt_riga_id,
    dr.ddt_id,
    d.numero AS ddt_numero,
    x.ordine_riga_id,
    x.tenuti,
    x.fatturati,
    x.accredito_dovuto,
    (
        CASE
            WHEN (x.riapre_residuo AND (vendite.fn_resi_riga_residuo_riconsegna(x.resi_riga_id) > (0)::numeric)) THEN 'FACOLTATIVA'::text
            ELSE 'DOVUTA'::text
        END)::character varying AS etichetta
   FROM (((((((dist x
     JOIN vendite.resi_righe rr ON ((rr.id = x.resi_riga_id)))
     JOIN vendite.resi r ON ((r.id = x.reso_id)))
     JOIN anagrafiche.soggetti_ruoli sr_dest ON ((sr_dest.id = r.destinatario_soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s_dest ON ((s_dest.id = sr_dest.soggetto_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = r.billing_account_id)))
     LEFT JOIN vendite.ddt_righe dr ON ((dr.id = x.ddt_riga_id)))
     LEFT JOIN vendite.ddt d ON ((d.id = dr.ddt_id)))
  WHERE (x.accredito_dovuto > (0)::numeric);
```


---
{% include-markdown "signature-core.md" %}
