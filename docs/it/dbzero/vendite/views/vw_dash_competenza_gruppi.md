{% include-markdown "it/dbzero/vendite/manual/vw_dash_competenza_gruppi.md" %}
# 🔍 View `vw_dash_competenza_gruppi`

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_competenza_gruppi
WITH (security_invoker=on) AS
WITH aggregato AS (
         SELECT a.competenza_mese,
            a.gruppo_key,
            a.sorgente_tipo_id,
            a.sorgente_uid,
            a.commessa_id,
            a.commessa_codice,
            a.emittente_soggetto_ruolo_id,
            a.cliente_display,
            a.stadio,
            a.commessa_emittibile,
            a.commessa_stato_codice_interno,
            count(*) AS n_attivita,
            COALESCE(sum(a.valore), (0)::numeric) AS valore,
            min(a.data_attivita) AS data_attivita_min,
            max(a.data_attivita) AS data_attivita_max,
            bool_or(((a.tipo_movimento)::text = 'ONERE'::text)) AS ha_oneri
           FROM vendite.vw_dash_competenza_attivita a
          GROUP BY a.competenza_mese, a.gruppo_key, a.sorgente_tipo_id, a.sorgente_uid, a.commessa_id, a.commessa_codice, a.emittente_soggetto_ruolo_id, a.cliente_display, a.stadio, a.commessa_emittibile, a.commessa_stato_codice_interno
        )
 SELECT g.competenza_mese,
    g.gruppo_key,
    COALESCE(s.codice_interno, 'ONERI_COMMESSA'::character varying) AS tipo_gruppo,
    s.area AS area_documento,
    COALESCE(doc.codice, g.commessa_codice, g.gruppo_key) AS riferimento,
    g.commessa_id,
    g.commessa_codice,
    g.emittente_soggetto_ruolo_id,
    g.cliente_display,
    g.stadio,
    g.n_attivita,
    g.valore,
    g.data_attivita_min,
    g.data_attivita_max,
    g.ha_oneri,
    g.sorgente_tipo_id,
    g.sorgente_uid,
    g.commessa_emittibile,
    g.commessa_stato_codice_interno
   FROM ((aggregato g
     LEFT JOIN config.sorgenti s ON ((s.id = g.sorgente_tipo_id)))
     LEFT JOIN LATERAL ( SELECT d.codice
           FROM vendite.vw_dash_fatturazione_documenti d
          WHERE ((s.area IS NOT NULL) AND ((d.area)::text = (s.area)::text) AND (d.documento_uid = g.sorgente_uid))
          ORDER BY d.competenza_mese DESC NULLS LAST
         LIMIT 1) doc ON (true));
```


---
{% include-markdown "signature-core.md" %}
