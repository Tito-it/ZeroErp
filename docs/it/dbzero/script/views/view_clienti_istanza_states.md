{% include-markdown "it/dbzero/script/manual/view_clienti_istanza_states.md" %}
# 🔍 View `view_clienti_istanza_states`

```sql
CREATE OR REPLACE VIEW script.view_clienti_istanza_states AS
SELECT i.id AS istanza_id,
    sc.id AS stato_id,
    sc.codice_interno AS cod_int_stato_cliente,
    sc.descrizione AS desc_stato_cliente,
    sc.descrizione_breve AS desc_breve_stato,
    sc.check_lettura,
    sc.abilita_fattura,
    sc.codice AS stato_cliente,
    sc.stato_cliente_ia,
    sc.data_insert AS stato_data_insert,
    sc.user_insert AS stato_user_insert,
    sc.data_update AS stato_data_update,
    sc.user_update AS stato_user_update
   FROM (anagrafiche.istanze_utilities i
     JOIN config.stati_cliente sc ON ((sc.id = script.fn_get_stato_cliente_by_istanza(i.id))));
```


---
{% include-markdown "signature-core.md" %}
