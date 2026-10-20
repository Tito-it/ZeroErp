{% include-markdown "it/dbzero/script/manual/vw_stradario_esteso.md" %}
# 🔍 View `vw_stradario_esteso`

> 📝 **Descrizione**
>
> Stradario esteso: tipo toponimo + nome strada, 
>         stato e indirizzo composito.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_stradario_esteso AS
SELECT v.id AS id_via,
    t.id AS id_toponomastica,
    t.descrizione AS tipo_toponimo,
    s.sigla_stato,
    v.descrizione AS nome_strada,
    v.descrizione_breve,
    concat(t.descrizione, ' ', v.descrizione) AS indirizzo_generale
   FROM ((config.stradario_generale v
     JOIN config.toponomastica t ON ((v.toponomastica_id = t.id)))
     LEFT JOIN config.stati s ON ((t.stato_id = s.id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
