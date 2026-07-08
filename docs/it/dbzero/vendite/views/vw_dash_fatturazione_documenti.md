{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_documenti.md" %}
# 🔍 View `vw_dash_fatturazione_documenti`

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_documenti AS
SELECT p.area,
    p.competenza_mese,
    p.documento_id,
    p.documento_uid,
    p.codice,
    p.emittente_fiscale_id,
    p.emittente_soggetto_ruolo_id,
    p.valore_totale,
    p.valore_transitato,
    p.unita_totali,
    p.unita_transitate,
    p.is_transitato,
    p.is_abortito,
    p.motivo_fermo,
    p.stato_codice_interno,
    p.stato_codice,
    p.fase,
    p.cliente_display,
    p.data_riferimento
   FROM vendite.vw_dash_fatturazione_preventivi p
UNION ALL
 SELECT o.area,
    o.competenza_mese,
    o.documento_id,
    o.documento_uid,
    o.codice,
    o.emittente_fiscale_id,
    o.emittente_soggetto_ruolo_id,
    o.valore_totale,
    o.valore_transitato,
    o.unita_totali,
    o.unita_transitate,
    o.is_transitato,
    o.is_abortito,
    o.motivo_fermo,
    o.stato_codice_interno,
    o.stato_codice,
    o.fase,
    o.cliente_display,
    o.data_riferimento
   FROM vendite.vw_dash_fatturazione_ordini o
UNION ALL
 SELECT f.area,
    f.competenza_mese,
    f.documento_id,
    f.documento_uid,
    f.codice,
    f.emittente_fiscale_id,
    f.emittente_soggetto_ruolo_id,
    f.valore_totale,
    f.valore_transitato,
    f.unita_totali,
    f.unita_transitate,
    f.is_transitato,
    f.is_abortito,
    f.motivo_fermo,
    f.stato_codice_interno,
    f.stato_codice,
    f.fase,
    f.cliente_display,
    f.data_riferimento
   FROM vendite.vw_dash_fatturazione_offerte f
UNION ALL
 SELECT c.area,
    c.competenza_mese,
    c.documento_id,
    c.documento_uid,
    c.codice,
    c.emittente_fiscale_id,
    c.emittente_soggetto_ruolo_id,
    c.valore_totale,
    c.valore_transitato,
    c.unita_totali,
    c.unita_transitate,
    c.is_transitato,
    c.is_abortito,
    c.motivo_fermo,
    c.stato_codice_interno,
    c.stato_codice,
    c.fase,
    c.cliente_display,
    c.data_riferimento
   FROM vendite.vw_dash_fatturazione_contratti c
UNION ALL
 SELECT m.area,
    m.competenza_mese,
    m.documento_id,
    m.documento_uid,
    m.codice,
    m.emittente_fiscale_id,
    m.emittente_soggetto_ruolo_id,
    m.valore_totale,
    m.valore_transitato,
    m.unita_totali,
    m.unita_transitate,
    m.is_transitato,
    m.is_abortito,
    m.motivo_fermo,
    m.stato_codice_interno,
    m.stato_codice,
    m.fase,
    m.cliente_display,
    m.data_riferimento
   FROM vendite.vw_dash_fatturazione_commesse m;
```


---
{% include-markdown "signature-core.md" %}
