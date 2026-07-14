{% include-markdown "it/dbzero/vendite/manual/vw_dash_backlog_documenti.md" %}
# 🔍 View `vw_dash_backlog_documenti`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_backlog_documenti
WITH (security_invoker=on) AS
SELECT d.area,
    d.competenza_mese,
    d.documento_id,
    d.documento_uid,
    d.codice,
    d.cliente_display,
    d.emittente_fiscale_id,
    d.emittente_soggetto_ruolo_id,
    (d.valore_totale - d.valore_transitato) AS valore_fermo,
    (d.unita_totali - d.unita_transitate) AS unita_ferme,
    d.motivo_fermo,
    COALESCE(mf.classe, 'ANOMALIA'::character varying) AS classe,
    mf.azione,
    d.data_riferimento,
    (CURRENT_DATE - d.data_riferimento) AS anzianita_giorni,
    d.stato_codice_interno,
    d.stato_codice,
    d.fase
   FROM (vendite.vw_dash_fatturazione_documenti d
     LEFT JOIN config.motivi_fermo mf ON ((((mf.codice_interno)::text = (d.motivo_fermo)::text) AND (mf.attivo IS TRUE))))
  WHERE ((d.motivo_fermo IS NOT NULL) AND ((COALESCE(mf.classe, 'ANOMALIA'::character varying))::text <> 'FISIOLOGICO'::text));
```


---
{% include-markdown "signature-core.md" %}
