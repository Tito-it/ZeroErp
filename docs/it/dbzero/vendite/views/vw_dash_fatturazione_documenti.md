{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_documenti.md" %}
# 🔍 View `vw_dash_fatturazione_documenti`

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_documenti AS
SELECT vw_dash_fatturazione_preventivi.area,
    vw_dash_fatturazione_preventivi.competenza_mese,
    vw_dash_fatturazione_preventivi.documento_id,
    vw_dash_fatturazione_preventivi.documento_uid,
    vw_dash_fatturazione_preventivi.codice,
    vw_dash_fatturazione_preventivi.emittente_fiscale_id,
    vw_dash_fatturazione_preventivi.emittente_soggetto_ruolo_id,
    vw_dash_fatturazione_preventivi.valore_totale,
    vw_dash_fatturazione_preventivi.valore_transitato,
    vw_dash_fatturazione_preventivi.unita_totali,
    vw_dash_fatturazione_preventivi.unita_transitate,
    vw_dash_fatturazione_preventivi.is_transitato,
    vw_dash_fatturazione_preventivi.is_abortito,
    vw_dash_fatturazione_preventivi.motivo_fermo,
    vw_dash_fatturazione_preventivi.stato_codice_interno,
    vw_dash_fatturazione_preventivi.stato_codice,
    vw_dash_fatturazione_preventivi.fase
   FROM vendite.vw_dash_fatturazione_preventivi
UNION ALL
 SELECT vw_dash_fatturazione_ordini.area,
    vw_dash_fatturazione_ordini.competenza_mese,
    vw_dash_fatturazione_ordini.documento_id,
    vw_dash_fatturazione_ordini.documento_uid,
    vw_dash_fatturazione_ordini.codice,
    vw_dash_fatturazione_ordini.emittente_fiscale_id,
    vw_dash_fatturazione_ordini.emittente_soggetto_ruolo_id,
    vw_dash_fatturazione_ordini.valore_totale,
    vw_dash_fatturazione_ordini.valore_transitato,
    vw_dash_fatturazione_ordini.unita_totali,
    vw_dash_fatturazione_ordini.unita_transitate,
    vw_dash_fatturazione_ordini.is_transitato,
    vw_dash_fatturazione_ordini.is_abortito,
    vw_dash_fatturazione_ordini.motivo_fermo,
    vw_dash_fatturazione_ordini.stato_codice_interno,
    vw_dash_fatturazione_ordini.stato_codice,
    vw_dash_fatturazione_ordini.fase
   FROM vendite.vw_dash_fatturazione_ordini
UNION ALL
 SELECT vw_dash_fatturazione_offerte.area,
    vw_dash_fatturazione_offerte.competenza_mese,
    vw_dash_fatturazione_offerte.documento_id,
    vw_dash_fatturazione_offerte.documento_uid,
    vw_dash_fatturazione_offerte.codice,
    vw_dash_fatturazione_offerte.emittente_fiscale_id,
    vw_dash_fatturazione_offerte.emittente_soggetto_ruolo_id,
    vw_dash_fatturazione_offerte.valore_totale,
    vw_dash_fatturazione_offerte.valore_transitato,
    vw_dash_fatturazione_offerte.unita_totali,
    vw_dash_fatturazione_offerte.unita_transitate,
    vw_dash_fatturazione_offerte.is_transitato,
    vw_dash_fatturazione_offerte.is_abortito,
    vw_dash_fatturazione_offerte.motivo_fermo,
    vw_dash_fatturazione_offerte.stato_codice_interno,
    vw_dash_fatturazione_offerte.stato_codice,
    vw_dash_fatturazione_offerte.fase
   FROM vendite.vw_dash_fatturazione_offerte
UNION ALL
 SELECT vw_dash_fatturazione_contratti.area,
    vw_dash_fatturazione_contratti.competenza_mese,
    vw_dash_fatturazione_contratti.documento_id,
    vw_dash_fatturazione_contratti.documento_uid,
    vw_dash_fatturazione_contratti.codice,
    vw_dash_fatturazione_contratti.emittente_fiscale_id,
    vw_dash_fatturazione_contratti.emittente_soggetto_ruolo_id,
    vw_dash_fatturazione_contratti.valore_totale,
    vw_dash_fatturazione_contratti.valore_transitato,
    vw_dash_fatturazione_contratti.unita_totali,
    vw_dash_fatturazione_contratti.unita_transitate,
    vw_dash_fatturazione_contratti.is_transitato,
    vw_dash_fatturazione_contratti.is_abortito,
    vw_dash_fatturazione_contratti.motivo_fermo,
    vw_dash_fatturazione_contratti.stato_codice_interno,
    vw_dash_fatturazione_contratti.stato_codice,
    vw_dash_fatturazione_contratti.fase
   FROM vendite.vw_dash_fatturazione_contratti
UNION ALL
 SELECT vw_dash_fatturazione_commesse.area,
    vw_dash_fatturazione_commesse.competenza_mese,
    vw_dash_fatturazione_commesse.documento_id,
    vw_dash_fatturazione_commesse.documento_uid,
    vw_dash_fatturazione_commesse.codice,
    vw_dash_fatturazione_commesse.emittente_fiscale_id,
    vw_dash_fatturazione_commesse.emittente_soggetto_ruolo_id,
    vw_dash_fatturazione_commesse.valore_totale,
    vw_dash_fatturazione_commesse.valore_transitato,
    vw_dash_fatturazione_commesse.unita_totali,
    vw_dash_fatturazione_commesse.unita_transitate,
    vw_dash_fatturazione_commesse.is_transitato,
    vw_dash_fatturazione_commesse.is_abortito,
    vw_dash_fatturazione_commesse.motivo_fermo,
    vw_dash_fatturazione_commesse.stato_codice_interno,
    vw_dash_fatturazione_commesse.stato_codice,
    vw_dash_fatturazione_commesse.fase
   FROM vendite.vw_dash_fatturazione_commesse;
```


---
{% include-markdown "signature-core.md" %}
