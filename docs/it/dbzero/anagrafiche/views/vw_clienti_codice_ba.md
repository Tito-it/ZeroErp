# 🔍 View `vw_clienti_codice_ba`

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_clienti_codice_ba AS
SELECT cl.soggetto_ruolo_id,
    cl.id,
    cl.id AS entita_id,
    cl.billing_account_id,
    ba.codice,
    cl.utility_id,
    cl.stato_cliente_id,
    sc.codice_interno AS stato_codice,
    sc.descrizione_breve AS stato_descrizione,
    cl.data_attivazione,
    cl.data_sospensione,
    cl.data_riattivazione,
    cl.data_chiusura
   FROM ((anagrafiche.clienti cl
     JOIN config.stati_cliente sc ON ((sc.id = cl.stato_cliente_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = cl.billing_account_id)));
```


---
{% include-markdown "signature-core.md" %}
