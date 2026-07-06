{% include-markdown "it/dbzero/vendite/manual/vw_dash_competenza_mensile.md" %}
# 🔍 View `vw_dash_competenza_mensile`

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_competenza_mensile AS
SELECT competenza_mese,
    stadio,
    stato_fattura_codice_interno,
    (count(*))::integer AS n_attivita,
    COALESCE(sum(valore), (0)::numeric) AS valore_tot,
    COALESCE(sum(valore_fatturato), (0)::numeric) AS valore_fatturato_tot,
    (count(*) FILTER (WHERE emessa_in_ritardo))::integer AS n_in_ritardo,
    COALESCE(sum(valore) FILTER (WHERE emessa_in_ritardo), (0)::numeric) AS valore_in_ritardo
   FROM vendite.vw_dash_competenza_attivita
  GROUP BY competenza_mese, stadio, stato_fattura_codice_interno;
```


---
{% include-markdown "signature-core.md" %}
