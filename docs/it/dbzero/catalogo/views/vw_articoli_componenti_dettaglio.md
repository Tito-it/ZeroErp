{% include-markdown "it/dbzero/catalogo/manual/vw_articoli_componenti_dettaglio.md" %}
# 🔍 View `vw_articoli_componenti_dettaglio`

```sql
CREATE OR REPLACE VIEW catalogo.vw_articoli_componenti_dettaglio AS
SELECT ac.id,
    ac.prodotto_id,
    ac.componente_id,
    ac.coeff_qta,
    ac.partecipa_qta,
    ac.obbligatorio,
    ac.valido_dal,
    ac.valido_al,
    ac.meta,
    ac.user_insert,
    ac.user_update,
    ac.data_insert,
    ac.data_update,
    ac.tx_id,
    ac.storicizza,
    ac.attivo,
    ac.note_target_tipo,
    ac.note_id,
    ap.codice AS prodotto_codice,
    ap.descrizione AS prodotto_descrizione,
    acmp.codice AS componente_codice,
    acmp.descrizione AS componente_descrizione
   FROM ((catalogo.articoli_componenti ac
     LEFT JOIN catalogo.articoli ap ON ((ap.id = ac.prodotto_id)))
     LEFT JOIN catalogo.articoli acmp ON ((acmp.id = ac.componente_id)));
```


---
{% include-markdown "signature-core.md" %}
