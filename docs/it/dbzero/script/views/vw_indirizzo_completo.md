{% include-markdown "it/dbzero/script/manual/vw_indirizzo_completo.md" %}
{% include-markdown "it/dbzero/script/manual/vw_indirizzo_completo.md" %}
# 🔍 View `vw_indirizzo_completo`

```sql
CREATE OR REPLACE VIEW script.vw_indirizzo_completo AS
SELECT s.id AS id_stradario,
    c.id AS id_comune,
    c.descrizione AS comune,
    p.sigla AS provincia,
    cp.codice_postale,
    ve.indirizzo_generale,
    s.geoloc,
    s.extra_info,
    ve.id_via,
    ve.tipo_toponimo,
    ve.nome_strada
   FROM ((((stradario s
     JOIN comuni c ON ((s.comune_id = c.id)))
     JOIN province p ON ((c.provincia_id = p.id)))
     JOIN codici_postali cp ON ((s.codice_postale_id = cp.id)))
     JOIN script.vw_stradario_esteso ve ON ((s.stradario_generale_id = ve.id_via)));
```
