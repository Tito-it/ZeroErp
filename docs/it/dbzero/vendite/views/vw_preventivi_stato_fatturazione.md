{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_stato_fatturazione.md" %}
# 🔍 View `vw_preventivi_stato_fatturazione`

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_stato_fatturazione AS
SELECT preventivo_id,
    preventivo_uid,
    preventivo_numero,
    count(*) AS righe_totali,
    count(*) FILTER (WHERE in_commessa) AS righe_in_commessa,
    count(*) FILTER (WHERE emessa_af) AS righe_emesse_af,
    count(*) FILTER (WHERE fatturata) AS righe_fatturate
   FROM vendite.vw_preventivi_stato_fatturazione_righe
  GROUP BY preventivo_id, preventivo_uid, preventivo_numero;
```


---
{% include-markdown "signature-core.md" %}
