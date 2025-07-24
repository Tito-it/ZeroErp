# 🔍 View `vw_stradario_esteso`

```sql
CREATE OR REPLACE VIEW script.vw_stradario_esteso AS
SELECT v.id AS id_via,
    t.id AS id_toponomastica,
    t.descrizione AS tipo_toponimo,
    s.sigla_stato,
    v.descrizione AS nome_strada,
    v.descrizione_breve,
    concat(t.descrizione, ' ', v.descrizione) AS indirizzo_generale
   FROM ((stradario_generale v
     JOIN toponomastica t ON ((v.toponomastica_id = t.id)))
     LEFT JOIN stati s ON ((t.stato_id = s.id)));
```
